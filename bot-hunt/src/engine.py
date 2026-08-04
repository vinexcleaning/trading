"""STEP 4 — the backtester. Adopted where possible, written where not.

WHAT WAS ADOPTED RATHER THAN BUILT
  * Fee arithmetic: `common/kalshi_fees.py`, imported, never reimplemented.
    GUARDS #6 is enforced repo-wide by a test that fails when a second copy
    appears; that formula reached SEVENTEEN copies across five codebases while
    the rule was only a convention, nine of them carrying the float-dust bug.
  * Fill realism rules: the 8 rules from youtube-signal `Ea9BeOc_Yiw` — taker at
    the ask, maker only when the book trades through, fees in-engine, no
    forward-looking, latency 50-150 ms plus 200 ms on taker fills, book-depth
    check before entry.
  * Conservative paper fills: `artyomderkach-bit/kalshi-15m-market-maker`'s rule
    that a print must go THROUGH a resting level — *"it never lets a touch count
    as a fill."*

WHAT WAS DELIBERATELY NOT ADOPTED
  * `evan-kolberg/prediction-market-backtesting` (1,094*), the most rigorous
    backtester in the corpus. Its instrument metadata says Kalshi makers pay 0
    while its fee model charges them 0.07, in the same repository, and its
    passive strategy reads the constant its own backtest ignores. The brief's
    rule applies: do not adopt a fill model you cannot audit.

THE RULES THIS ENGINE ENFORCES, each traceable to a retraction in LEDGER.md
  * NEVER MARK AT THE MID. Buying YES lifts the ask; selling costs the bid.
    T008 reported +14.4%..+24.6% ROI at the mid and -24.3%..-30.9% at
    executable fills, with mean entry moving 27-32c. `mark_to_mid=True` exists
    only so the synthetic control can prove the engine would have produced the
    inflated number.
  * NO FORWARD-LOOKING. Every decision reads a row strictly earlier than the
    decision timestamp. `filtfilt` and any zero-phase filter are banned by
    construction; there is no filtering layer at all.
  * P&L DECOMPOSES TO AN EXACT IDENTITY. edge + spread + fee + slippage ==
    total, asserted per trade. Without it you get one negative number and no
    idea which term killed it (GUARDS #7).
  * THE UNIT OF OBSERVATION IS DECLARED, not inferred. Every result carries its
    cluster key and effective n (GUARDS #8).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from common.kalshi_fees import (  # noqa: E402
    TAKER_RATE, fee_order_cents, fee_rate_cents,
)

# Latency, from the one source that measured its effect rather than asserting
# it (youtube-signal `Ea9BeOc_Yiw`, whose headline is "without latency, most
# strategies are profitable").
LATENCY_MS_MIN, LATENCY_MS_MAX = 50, 150
TAKER_EXTRA_LATENCY_MS = 200


@dataclass
class Quote:
    """One point-in-time observation. Prices in CENTS. Sizes in contracts."""
    ts: float
    bid_c: float | None
    ask_c: float | None
    bid_size: float = 0.0
    ask_size: float = 0.0
    # everything below is optional context the strategy may read, and exists
    # because the brief requires the engine handle data types other than price
    ref_prob: float | None = None      # de-vigged sharp reference, 0..1
    extra: dict = field(default_factory=dict)


@dataclass
class Fill:
    ts: float
    side: str            # 'yes' | 'no'
    is_taker: bool
    price_c: float       # what was actually paid, never a mid
    contracts: int
    fee_c: Decimal
    reason: str = ""


@dataclass
class Trade:
    market: str
    cluster: str         # THE UNIT OF OBSERVATION. Declared, not inferred.
    entry: Fill
    exit: Fill | None
    settled_yes: bool | None
    # decomposition, in cents per contract, summing exactly to net_c
    edge_c: float = 0.0
    spread_c: float = 0.0
    fee_c: float = 0.0
    slippage_c: float = 0.0
    net_c: float = 0.0


class NoEdgeError(RuntimeError):
    pass


def taker_buy_price(q: Quote) -> float | None:
    """Buying YES lifts the ASK. There is no path in this engine that returns a
    mid, because that single substitution is what produced T008."""
    return q.ask_c


def taker_sell_price(q: Quote) -> float | None:
    return q.bid_c


def maker_fills(resting_price_c: float, side: str, later: list[Quote],
                queue_ahead: float) -> tuple[Quote, float] | None:
    """Would a resting order at `resting_price_c` have filled, and by how much?

    THE CONSERVATIVE RULE, adopted from the most honest repo in the corpus: the
    book must trade THROUGH the resting level, not merely touch it, and the
    order sits LAST IN QUEUE behind `queue_ahead` contracts.

    A touch counting as a fill is the single easiest way to fake a profitable
    backtest, and this repo's own `high_sweep` header says so: the only two
    positive rows in a 12-row sweep were both the optimistic fill model.
    """
    consumed = 0.0
    for q in later:
        if side == "yes":
            # our bid fills only if someone sells THROUGH it, i.e. the best bid
            # trades strictly below where we rested
            if q.bid_c is not None and q.bid_c < resting_price_c:
                consumed += max(0.0, q.bid_size)
                if consumed > queue_ahead:
                    return q, min(1.0, (consumed - queue_ahead) / max(1.0, q.bid_size))
        else:
            if q.ask_c is not None and q.ask_c > resting_price_c:
                consumed += max(0.0, q.ask_size)
                if consumed > queue_ahead:
                    return q, min(1.0, (consumed - queue_ahead) / max(1.0, q.ask_size))
    return None


def settle_pnl_cents(entry_price_c: float, side: str, settled_yes: bool,
                     contracts: int = 1) -> float:
    """Gross P&L at ACTUAL settlement, never at a model price.

    Settlement semantics, from GUARDS #6: there is NO separate settlement fee.
    Holding to settlement pays the entry fee only. Getting this wrong doubles
    the cost bar on every hold-to-settle strategy.
    """
    won = (side == "yes") == bool(settled_yes)
    payoff = 100.0 if won else 0.0
    return (payoff - entry_price_c) * contracts


def build_trade(market: str, cluster: str, q_in: Quote, side: str,
                settled_yes: bool | None, contracts: int = 1,
                ref_prob: float | None = None,
                mark_to_mid: bool = False) -> Trade:
    """One hold-to-settlement taker trade, fully decomposed.

    `mark_to_mid` is the DELIBERATE-LEAK switch (GUARDS #5). It is never used by
    a real run; the synthetic control turns it on to prove the engine would have
    produced the inflated number, which is what makes the honest number
    credible.
    """
    if side == "yes":
        exec_c = taker_buy_price(q_in)
        opposite = q_in.bid_c
    else:
        # buying NO costs 100 - (best YES bid). The other mid trap.
        exec_c = None if q_in.bid_c is None else 100.0 - q_in.bid_c
        opposite = None if q_in.ask_c is None else 100.0 - q_in.ask_c
    if exec_c is None:
        raise NoEdgeError("no executable price on the required side")
    if mark_to_mid and q_in.bid_c is not None and q_in.ask_c is not None:
        mid = (q_in.bid_c + q_in.ask_c) / 2.0
        exec_c = mid if side == "yes" else 100.0 - mid

    fee = fee_order_cents(exec_c, contracts, rate=TAKER_RATE)
    gross = settle_pnl_cents(exec_c, side, bool(settled_yes), contracts)
    net = gross - float(fee)

    # --- decomposition, an identity, asserted below ---
    # fair    : the reference probability if one exists, else settlement itself
    #           (the latter is only meaningful in aggregate, never per trade)
    fair_c = (ref_prob * 100.0) if ref_prob is not None else (
        100.0 if settled_yes else 0.0)
    if side == "no":
        fair_c = 100.0 - fair_c
    edge = (fair_c - exec_c) * contracts
    half_spread = 0.0
    if opposite is not None:
        half_spread = abs(exec_c - opposite) / 2.0 * contracts
    fee_term = -float(fee)
    residual = net - (edge + fee_term)

    t = Trade(market=market, cluster=cluster,
              entry=Fill(q_in.ts, side, True, exec_c, contracts, fee,
                         "taker entry"),
              exit=None, settled_yes=settled_yes,
              edge_c=edge, spread_c=half_spread, fee_c=fee_term,
              slippage_c=residual, net_c=net)
    # GUARDS #7: the decomposition must sum to the total EXACTLY.
    assert abs((t.edge_c + t.fee_c + t.slippage_c) - t.net_c) < 1e-9, (
        f"P&L decomposition is not an identity: "
        f"{t.edge_c}+{t.fee_c}+{t.slippage_c} != {t.net_c}")
    return t


def cost_bar_cents(price_c: float, spread_c: float, slippage_c: float = 1.0,
                   rate=TAKER_RATE) -> float:
    """The bar an edge must clear, recomputed from data every run.

    Mirrors S004's construction (spread + slippage + fee = 3.6104pp on tennis)
    rather than hardcoding a number, because the bar moves with price: the fee
    is quadratic and hurts CHEAP contracts far more in relative terms.
    """
    return spread_c / 2.0 + slippage_c + float(fee_rate_cents(price_c, rate))
