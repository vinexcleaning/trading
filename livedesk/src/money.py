"""What a bet costs, what it pays, and what it has to win to be worth doing.

Every number this window shows about money comes from here, so there is one
place to check it. Fees come from `common/kalshi_fees.py` and are NOT
reimplemented -- GUARDS #6, and the repo test that enforces it.

Guard 3 lives here: a flat stake that never grows.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

TRADING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRADING_ROOT))

from common.kalshi_fees import fee_order_cents      # noqa: E402

# --- Guard 3 -------------------------------------------------------------
# The user set both of these. Bankroll is $83, not $100 -- he lost some of it
# on his own tennis bets before this tool existed.
BANKROLL_START = 83.00
STAKE_PCT = 5.0
# The flat dollar stake. Deliberately a CONSTANT and not a function of the
# running balance: the paper bots drifted from 3 contracts to 25 on their own
# and that is how a small edge turns into a large loss. It does not grow when
# he is winning and it does not shrink when he is losing -- the cut-off in
# ledger.py is what bounds the downside, not the stake.
STAKE_USD = round(BANKROLL_START * STAKE_PCT / 100.0, 2)     # $4.15

# --- Guard 2 -------------------------------------------------------------
# Stop everything when THIS TOOL's own running total is down this much. Not
# the account balance: he can move the account himself and that must never be
# read as the strategy failing.
CUTOFF_LOSS_USD = 33.00


@dataclass(frozen=True)
class Bet:
    """Everything about one proposed bet, in dollars, already costed."""
    price_c: int
    contracts: int
    cost_usd: float            # what leaves the account, fee included
    fee_usd: float
    win_profit_usd: float      # profit if it settles YES, fee already taken off
    lose_usd: float            # what he loses if it settles NO
    breakeven_out_of_100: float

    @property
    def placeable(self) -> bool:
        return self.contracts > 0


def size_bet(price_c: int, stake_usd: float = STAKE_USD) -> Bet:
    """How many contracts $4.15 buys at this price, and what happens either way.

    Contracts are floored, never rounded up: going over the flat stake to buy
    one more contract is exactly the drift Guard 3 exists to stop.

    `stake_usd` exists so the tests can drive smaller sizes. It is CLAMPED to
    STAKE_USD, not merely defaulted to it -- "the sizing function has no
    parameter that could carry a rising bankroll" was a claim about a function
    that plainly had one, and a caller passing a bigger number is the whole
    failure mode Guard 3 describes. It cannot go up. It can go down.
    """
    stake_usd = min(float(stake_usd), STAKE_USD)
    price_c = int(price_c)
    if price_c <= 0 or price_c >= 100 or stake_usd <= 0:
        return Bet(price_c, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    contracts = int(stake_usd / (price_c / 100.0))
    if contracts < 1:
        return Bet(price_c, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    fee_c = float(fee_order_cents(price_c, contracts))
    stake_c = contracts * price_c
    cost_c = stake_c + fee_c
    payout_c = contracts * 100.0

    return Bet(
        price_c=price_c,
        contracts=contracts,
        cost_usd=round(cost_c / 100.0, 2),
        fee_usd=round(fee_c / 100.0, 2),
        win_profit_usd=round((payout_c - cost_c) / 100.0, 2),
        lose_usd=round(cost_c / 100.0, 2),
        # Out of 100 tries, how many must win just to come out level. The fee
        # is in it -- quoting the price alone understates the bar, which is the
        # error the mlb chat corrected on 2026-08-08 (52 was really 53.7).
        breakeven_out_of_100=round(cost_c / contracts, 1),
    )


def usd(x: float) -> str:
    """'+$3.23' / '-$3.77'. Never '$+3.23', which is what an f-string sign
    flag produces and which reads as a typo at 3am."""
    return f"{'-' if x < -0.004 else '+'}${abs(x):.2f}"


def settle_usd(bet: Bet, won: bool) -> float:
    """Profit or loss in dollars once the game is final. Holding to settlement
    pays the entry fee only -- there is no separate settlement fee."""
    return bet.win_profit_usd if won else -bet.lose_usd
