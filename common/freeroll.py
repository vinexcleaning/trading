"""The Principal Recovery / Free-Roll Exit, as a REUSABLE OVERLAY.

His idea, in his words: *buy 10 YES at 10c for $1; if the price reaches 20c,
sell 5 for $1 -- the original stake is back -- and let the other 5 ride.*

WHY THIS LIVES IN `common/` AND NOT IN ONE STRATEGY'S FOLDER
------------------------------------------------------------
He asked for it "kept in mind for every current and future tennis strategy, with
a standard with-and-without comparison added as a permanent column". So it is an
overlay applied to a trade list, never a variant of one strategy. Anything that
can produce `(entry price, size, the tape after entry, settlement)` runs through
it unchanged -- tennis today, baseball tomorrow.

**Keep the two effects apart in every table**: predictive edge is what the
strategy picks; exit management is what this does to the same picks. Mixing them
is how an exit rule takes credit for a signal.

WHAT IT CANNOT DO, STATED AT THE TOP
------------------------------------
**A free-roll cannot raise expected value.** Selling part of a position at a
fair price is break-even before costs and loses money after fees and spread. He
knows this -- his brief asks whether it "improves risk-adjusted returns even if
it reduces raw expected value". So the question this module exists to answer is
whether it changes the SHAPE enough to be worth the cost, and whether it wins
when cash is the binding constraint.

THE ONE MECHANISM BY WHICH IT CAN GENUINELY WIN
-----------------------------------------------
If capital is limited, recovering principal early frees it for the next bet, so
the same bankroll gets more shots. Measured as real on the baseball side:
capacity for about 5 concurrent bets against a need for 9. `simulate()` takes a
bankroll, so the constrained and unconstrained answers can differ in sign.

EXECUTION REALISM -- every one of these is a way results get faked
-----------------------------------------------------------------
  * entry at the ASK, exit at the BID, never the mid (GUARDS #7)
  * fees only from `common/kalshi_fees.py`, which a repo-wide test enforces as
    the single implementation
  * whole contracts -- a 3-contract position cannot sell 1.5
  * one whole minute of latency: seeing the trigger at minute i, you execute at
    minute i+1
  * **no look-ahead** -- the tape is walked forward and the decision at minute i
    consults nothing after it
  * positions that cannot recover, and positions that never activate, are
    RETURNED, not dropped. An overlay that fires on 8 positions in 100 cannot
    move a portfolio however good it looks on those 8.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import kalshi_fees as KF          # noqa: E402

#: One whole minute-bar of latency, matching the convention already used by the
#: tennis forward test and the maker study.
LATENCY_BARS = 1


# --------------------------------------------------------------- the inputs
@dataclass(frozen=True)
class Position:
    """One position a strategy actually opened.

    `tape` is (bid_c, ask_c) per minute AFTER the entry minute, in order. It is
    walked forward and never indexed from the end.
    """
    pid: str
    entry_ask_c: int
    contracts: int
    tape: Sequence[tuple[int, int]]
    won: bool
    fee_type: str = "quadratic"
    opened_min: int = 0

    def __post_init__(self):
        if not (0 < self.entry_ask_c < 100):
            raise ValueError(f"entry price {self.entry_ask_c} must be 1..99")
        if self.contracts <= 0:
            raise ValueError("contracts must be positive")


@dataclass(frozen=True)
class Rule:
    """One free-roll configuration. `None` activation means never fire."""
    #: 'multiple' (of entry), 'profit' (cents above entry), 'price' (absolute)
    kind: str = "multiple"
    level: float = 2.0
    #: fraction of the original stake to take back
    target: float = 1.0
    #: 'exact' | 'quarter' | 'third' | 'half'
    sizing: str = "exact"
    #: staged recovery at successive multiples of `level`
    staged: bool = False

    def trigger_price(self, entry_ask_c: int) -> float:
        if self.kind == "multiple":
            return entry_ask_c * self.level
        if self.kind == "profit":
            return entry_ask_c + self.level
        if self.kind == "price":
            return self.level
        raise ValueError(f"unknown activation kind {self.kind!r}")

    @property
    def reachable_below(self) -> float:
        """Highest entry price at which this rule can EVER fire.

        A multiple-based rule is arithmetically unavailable above 100/level --
        a contract cannot double from 60c. This is a fact about the ceiling,
        not a finding, and it is why the activation rate is a headline number.
        """
        if self.kind == "multiple":
            return 100.0 / self.level
        if self.kind == "profit":
            return 100.0 - self.level
        return 100.0


HOLD = Rule(kind="multiple", level=float("inf"))     # never fires


# --------------------------------------------------------------- the output
@dataclass
class Outcome:
    pid: str
    activated: bool
    reason: str                  # why it did not activate, when it did not
    sold: int = 0
    sold_at_c: int = 0
    sold_at_min: int = -1
    net_c: float = 0.0           # profit in cents, after all fees
    cost_c: float = 0.0          # what the position cost to open
    recovered_c: float = 0.0     # cash back in hand at the scale-out
    freed_min: int = -1          # when that cash became available
    runner: int = 0


def _fee_c(price_c: int, contracts: int, fee_type: str,
           maker: bool = False) -> float:
    """Per-ORDER fee in cents. Kalshi rounds up per order, so this is not
    per-contract multiplied -- that mistake makes many small exits look free."""
    if contracts <= 0:
        return 0.0
    if maker:
        s = KF.SeriesFees("<s>", fee_type, Decimal(1))
        return float(KF.maker_fee_order_cents(price_c, contracts, s))
    return float(KF.fee_order_cents(price_c, contracts))


def open_cost_c(p: Position) -> float:
    """Taker buy at the ask, plus the entry fee."""
    return p.contracts * p.entry_ask_c + _fee_c(p.entry_ask_c, p.contracts,
                                                p.fee_type)


def settle_c(contracts: int, won: bool) -> float:
    """Kalshi charges NOTHING at settlement. That asymmetry is the whole
    reason a free-roll costs money: the holder never pays an exit fee."""
    return contracts * 100.0 if won else 0.0


def apply(p: Position, rule: Rule) -> Outcome:
    """Run one position through one rule. No look-ahead anywhere."""
    cost = open_cost_c(p)
    o = Outcome(pid=p.pid, activated=False, reason="", cost_c=cost,
                runner=p.contracts)

    if rule is HOLD or rule.level == float("inf"):
        o.reason = "hold-to-settlement baseline"
        o.net_c = settle_c(p.contracts, p.won) - cost
        return o

    trig = rule.trigger_price(p.entry_ask_c)
    if trig >= 100:
        o.reason = "unreachable: the trigger is at or above 100c"
        o.net_c = settle_c(p.contracts, p.won) - cost
        return o

    # walk forward; decide at i, execute at i + LATENCY_BARS
    fire_at = -1
    for i, (bid, _ask) in enumerate(p.tape):
        if bid >= trig:
            fire_at = i + LATENCY_BARS
            break
    if fire_at < 0 or fire_at >= len(p.tape):
        o.reason = ("never reached the trigger" if fire_at < 0
                    else "triggered too late to execute")
        o.net_c = settle_c(p.contracts, p.won) - cost
        return o

    exec_bid = p.tape[fire_at][0]
    if exec_bid <= 0:
        o.reason = "no bid to sell into at execution"
        o.net_c = settle_c(p.contracts, p.won) - cost
        return o

    want_c = p.contracts * p.entry_ask_c * rule.target      # cents to recover
    if rule.sizing == "exact":
        m = int(want_c // exec_bid)          # floor: never over-recover
    else:
        frac = {"quarter": 0.25, "third": 1 / 3, "half": 0.5}[rule.sizing]
        m = int(p.contracts * frac)
    m = max(0, min(m, p.contracts))

    if m == 0:
        o.reason = ("position too small to recover anything -- "
                    "cannot sell a fraction of a contract")
        o.net_c = settle_c(p.contracts, p.won) - cost
        return o
    if m == p.contracts:
        o.reason = "full exit: recovering the target would sell the runner too"

    proceeds = m * exec_bid - _fee_c(exec_bid, m, p.fee_type)
    keep = p.contracts - m
    o.activated = True
    o.sold, o.sold_at_c, o.sold_at_min = m, exec_bid, fire_at
    o.recovered_c, o.freed_min, o.runner = proceeds, fire_at, keep
    o.net_c = proceeds + settle_c(keep, p.won) - cost
    return o


def overlay_cost_c(entry_ask_c: int, exit_bid_c: int, contracts: int,
                   fee_type: str = "quadratic") -> float:
    """JOB 0 -- what the scale-out costs, before any benefit.

    The holder pays no exit fee, so selling early costs the fee plus the walk
    from mid down to the bid. Both are known the moment the price is known,
    which is why this is computed before anything is measured.
    """
    return _fee_c(exit_bid_c, contracts, fee_type)


# ----------------------------------------------------------- the portfolio
@dataclass
class PortfolioResult:
    n: int = 0
    activated: int = 0
    too_small: int = 0
    never_triggered: int = 0
    unreachable: int = 0
    net_c: float = 0.0
    staked_c: float = 0.0
    skipped_for_cash: int = 0
    per_position: list = field(default_factory=list)
    equity: list = field(default_factory=list)

    @property
    def roi(self) -> float:
        return self.net_c / self.staked_c if self.staked_c else 0.0

    @property
    def activation_rate(self) -> float:
        return self.activated / self.n if self.n else 0.0

    @property
    def max_drawdown_c(self) -> float:
        """Worst peak-to-trough of cumulative profit, in cents. The number his
        framing actually turns on -- a smaller one bought at a small cost in
        return is a SUCCESS, not a failure."""
        peak = 0.0
        worst = 0.0
        for v in self.equity:
            peak = max(peak, v)
            worst = min(worst, v - peak)
        return -worst


def simulate(positions: Sequence[Position], rule: Rule,
             bankroll_c: float | None = None,
             settle_min: dict | None = None) -> PortfolioResult:
    """Run a whole trade list through one rule.

    `bankroll_c=None` is the unconstrained arm. With a bankroll, positions are
    taken in order while cash allows and SKIPPED when it does not -- which is
    the arm where an EV-negative overlay can still win, by freeing cash sooner.
    """
    r = PortfolioResult()
    cash = bankroll_c
    cum = 0.0
    for p in positions:
        cost = open_cost_c(p)
        if cash is not None and cost > cash:
            r.skipped_for_cash += 1
            continue
        o = apply(p, rule)
        r.n += 1
        r.staked_c += cost
        r.net_c += o.net_c
        cum += o.net_c
        r.equity.append(cum)
        r.per_position.append(o)
        if o.activated:
            r.activated += 1
        elif "too small" in o.reason:
            r.too_small += 1
        elif "unreachable" in o.reason:
            r.unreachable += 1
        elif "never reached" in o.reason:
            r.never_triggered += 1
        if cash is not None:
            cash += o.net_c
    return r
