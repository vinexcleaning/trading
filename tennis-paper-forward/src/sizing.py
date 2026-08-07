"""sizing.py — how much each bot stakes, and why.

EVERY BOT CHOOSES ITS OWN STAKE, WITHIN A FIXED BANKROLL
    Each bot has the same paper bankroll and never adds to it. What it varies
    is the fraction of that bankroll it puts on each trade, from its own
    confidence. The stake and its reasoning are logged on every trade, so the
    two skills come apart afterwards:

      selection skill  = mean profit per CONTRACT, every match weighted equally
      sizing skill     = whether weighting by stake beats weighting equally

    Those are different questions and a single P&L number answers neither. A
    bot can pick well and size badly, and the combined figure will look like a
    bot that picks badly.

    ⚠ THIS IS THE ONE PLACE WHERE THIS DESIGN CARRIES REAL RISK, AND IT IS
      WORTH SAYING PLAINLY. Variable sizing is how the live bot in this repo
      lost money fastest. It sized by DOLLARS: `qty = int(stake / price)`. A
      fixed dollar stake buys more contracts as the price falls, so
      re-entering a falling market martingales automatically - nobody designed
      it, and it cost -$7.56 on one match in fifty minutes across three legs
      of 12, 20 and 32 contracts. Sizing by confidence reintroduces exactly
      that arithmetic, because a stake in cents still divides by a price.

      Three guards, all enforced below and all pre-registered:
        1. a re-entry may never be LARGER in contracts than the first entry on
           that event (`first_entry_contracts`). This alone kills the 12->20->32
           sequence.
        2. total open exposure is capped at the bankroll; a bot cannot spend
           what it does not have, so a losing run shrinks its own sizing.
        3. a hard per-trade ceiling in contracts and in bankroll fraction.

FRACTIONAL KELLY WHERE THERE IS A PROBABILITY, CONVICTION WHERE THERE IS NOT
    A bot that estimates a fair probability has everything Kelly needs, and
    Kelly is the only principled answer to "how much". It is applied at a
    quarter, and the fee is inside the payoff rather than ignored - staking
    `ask + fee` to win `100 - ask - fee`, not `ask` to win `100 - ask`.

    Momentum has no probability estimate. It sizes on conviction relative to
    its own entry bar, which is honest about being a heuristic.

    Kelly on an estimate this weak is not a licence to bet big. The archive is
    explicit that a far better tennis model than this one still loses to the
    bookmakers, so the Kelly fraction here is a way of ORDERING bets by
    confidence, not a claim that the edge is real. The cap does the work.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from math import floor
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from common.kalshi_fees import TAKER_RATE, fee_rate_cents  # noqa: E402

BANKROLL_CENTS = 50_000          # $500 of paper, per bot, never topped up
KELLY_FRACTION = 0.25            # quarter Kelly

# THE MODEL'S WEIGHT IN THE SIZING PROBABILITY. DECLARED IN ADVANCE, NOT FITTED.
#
# The first live tick exposed the problem this fixes. The archive's elo made a
# favourite a 95.2% chance while the market asked 83c. Kelly on a 12-point
# disagreement returns a full-Kelly fraction of 0.70, so EVERY trade pinned to
# the 6% cap and the stake carried no information at all - which would have made
# "sizing skill" unmeasurable by construction, since a constant cannot correlate
# with anything.
#
# The cause is not a bug, it is that a crude elo is overconfident, and this repo
# has already measured that a FAR better tennis model (50 features, 1.5M
# matches) still loses the accuracy contest to the bookmakers by +0.01922 Brier
# on n=2,645. A model that loses to the market does not deserve to outvote it.
#
# So the probability Kelly is given is a blend, with the model in the minority:
#
#     p_size = MODEL_WEIGHT * p_model + (1 - MODEL_WEIGHT) * p_market
#
# This is a prior, chosen before any result was seen, and it is deliberately
# NOT tuned - tuning it against outcomes is the whole failure mode this repo
# has recorded forty-five times. Note what it does and does not touch: SIZING
# only. A bot's decision to enter still uses its own raw read of the brief, so
# selection and sizing stay separable, which is the entire point.
MODEL_WEIGHT = 0.35
MIN_FRACTION = 0.005             # 0.5% of bankroll
MAX_FRACTION = 0.06              # 6% of bankroll
MAX_CONTRACTS = 200              # absolute ceiling on one entry
MIN_CONTRACTS = 1
MAX_OPEN_FRACTION = 1.00         # total open exposure may not exceed bankroll


@dataclass
class Stake:
    contracts: int
    stake_cents: int
    fraction: float
    basis: str                   # "kelly" | "conviction" | "floor"
    kelly_full: float | None
    edge_cents: float | None
    rationale: str
    capped_by: list[str]
    p_size: float | None = None  # the blended probability Kelly actually used


def _kelly(fair: float, ask_cents: int) -> tuple[float, float]:
    """Full-Kelly fraction and the per-contract edge, with the fee inside.

    Stake per contract is `ask + fee`; the win pays `100 - ask - fee`. Using
    `ask` and `100 - ask` instead would overstate the odds by the whole fee,
    which is the largest single term at these prices.
    """
    fee = float(fee_rate_cents(ask_cents, TAKER_RATE))
    cost = ask_cents + fee
    win = 100.0 - ask_cents - fee
    if cost <= 0 or win <= 0:
        return 0.0, 0.0
    b = win / cost
    f = (fair * b - (1.0 - fair)) / b
    edge = fair * win - (1.0 - fair) * cost
    return f, edge


def choose_stake(*, conviction: float, enter_at: float, fair: float | None,
                 ask_cents: int, bankroll_cents: int = BANKROLL_CENTS,
                 open_exposure_cents: int = 0,
                 first_entry_contracts: int | None = None,
                 depth_cap_contracts: int | None = None,
                 market_prob: float | None = None) -> Stake:
    capped: list[str] = []
    kelly_full: float | None = None
    edge: float | None = None
    p_size: float | None = None

    if fair is not None:
        # blend toward the market before sizing. See MODEL_WEIGHT above.
        p_mkt = market_prob if market_prob is not None else (ask_cents / 100.0)
        p_size = MODEL_WEIGHT * fair + (1.0 - MODEL_WEIGHT) * p_mkt
        kelly_full, edge = _kelly(p_size, ask_cents)
        conf = max(0.5, min(2.0, conviction / max(0.1, enter_at)))
        frac = kelly_full * KELLY_FRACTION * conf
        basis = "kelly"
        why = (f"the brief's own estimate is {100*fair:.1f}% and the market is asking "
               f"{ask_cents}c; sizing uses {100*MODEL_WEIGHT:.0f}% of the model and "
               f"{100*(1-MODEL_WEIGHT):.0f}% of the market, which is {100*p_size:.1f}%. "
               f"Quarter-Kelly on that (fee inside the payoff) gives a full-Kelly "
               f"fraction of {kelly_full:.4f}, scaled by {conf:.2f} for a conviction of "
               f"{conviction:.2f} against a bar of {enter_at:.1f}")
        if kelly_full <= 0:
            why += (". Kelly is NOT positive once the model is put in the minority, so "
                    "the stake falls to the floor - the trade happens at all only "
                    "because the disposition's conviction bar was met on other grounds, "
                    "and the size says so")
    else:
        span = max(0.1, enter_at)
        over = max(0.0, (conviction - enter_at) / span)
        frac = MIN_FRACTION + (MAX_FRACTION - MIN_FRACTION) * min(1.0, over)
        basis = "conviction"
        why = (f"no probability estimate is available, so the stake scales on conviction "
               f"alone: {conviction:.2f} against a bar of {enter_at:.1f} is {over:.2f} bars "
               f"of excess")

    if frac < MIN_FRACTION:
        frac, basis = MIN_FRACTION, "floor"
        capped.append("min_fraction")
    if frac > MAX_FRACTION:
        frac = MAX_FRACTION
        capped.append("max_fraction")

    # exposure cap: a bot cannot stake what it has already committed
    room = max(0, int(bankroll_cents * MAX_OPEN_FRACTION) - open_exposure_cents)
    stake = int(bankroll_cents * frac)
    if stake > room:
        stake = room
        capped.append("open_exposure")

    contracts = floor(stake / max(1, ask_cents))
    if contracts > MAX_CONTRACTS:
        contracts = MAX_CONTRACTS
        capped.append("max_contracts")

    # THE ANTI-MARTINGALE GUARD. A re-entry may not be larger than the first
    # entry on the same event. Without this, a falling price mechanically buys
    # more contracts for the same stake and the bot martingales without ever
    # deciding to.
    if first_entry_contracts is not None and contracts > first_entry_contracts:
        contracts = first_entry_contracts
        capped.append("no_larger_than_first_entry")

    if depth_cap_contracts is not None and contracts > depth_cap_contracts:
        contracts = depth_cap_contracts
        capped.append("book_depth")

    if contracts < MIN_CONTRACTS:
        contracts = 0 if (room < ask_cents or (depth_cap_contracts == 0)) else MIN_CONTRACTS
        if contracts:
            capped.append("min_contracts")

    stake_actual = contracts * ask_cents
    rationale = (
        f"{why}. Fraction {frac:.4f} of a {bankroll_cents/100:.0f} dollar bankroll is "
        f"{stake/100:.2f} dollars, which at {ask_cents}c buys {contracts} contracts"
        + (f" after caps: {', '.join(capped)}" if capped else "")
        + "."
    )
    return Stake(contracts=contracts, stake_cents=stake_actual, fraction=frac,
                 basis=basis, kelly_full=kelly_full, edge_cents=edge,
                 rationale=rationale, capped_by=capped, p_size=p_size)
