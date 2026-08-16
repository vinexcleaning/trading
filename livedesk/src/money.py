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
BANKROLL_START = 83.00

# ⚠ CHANGED 2026-08-16 ON HIS INSTRUCTION: "just make it ten percent stake of
# my balance".
#
# It used to be a flat $4.15 -- 5% of a FIXED $83 -- and the reason is written
# down: the paper bots drifted from 3 contracts to 25 on their own, and a
# stake that grows with the balance is how a small edge becomes a large loss.
# That reason has not gone away. He has heard it and decided, and it is his
# money, so this is now a percentage of what he actually has.
#
# What the change really does: at $100 it bets $10 instead of $4.15, and if
# the account doubles so does every bet. The downside is bounded by the cut-off
# in ledger.py, not by the stake -- which matters MORE now, not less.
STAKE_PCT = 10.0

# The old flat figure, kept as the value used when nothing better is known.
STAKE_USD = round(BANKROLL_START * 5.0 / 100.0, 2)           # $4.15

# ⚠ AN ABSOLUTE CEILING ON ONE BET, and it is not decoration.
#
# `size_bet` used to clamp to a module CONSTANT, which made "no caller can ask
# for more" true by construction. A percentage of a live balance cannot work
# that way, so the clamp has to become an explicit number instead of
# disappearing. Set equal to the daily cap: **one bet can never spend a whole
# day's budget**, whatever the balance says, and whatever a caller passes.
MAX_STAKE_USD = 50.00


# ⚠ TIERED STAKES, his decision 2026-08-16: "ten percent on agreed games, five
# percent on everything else".
#
# He also said "and then we don't even bet on the alone games". THAT HALF IS
# NOT BUILT and must not be. The coordinator has put the arithmetic to him and
# he has not answered: skipping the alone games cuts him from 28 bets to 8 --
# a better return on a much smaller amount of action. If he confirms it after
# reading, it is one line on top of this.
STAKE_PCT_AGREED = 10.0      # another approach took the same side
STAKE_PCT_OTHER = 5.0        # it took the other side, OR nothing else is on it

# The buckets, named so the card can say which one a bet is in.
BUCKET_AGREED = "agreed"
BUCKET_OPPOSITE = "opposite"
BUCKET_ALONE = "alone"
BUCKET_UNKNOWN = "unknown"


def bucket_for(alone, consensus: str = "") -> str:
    """Which tier this bet is in, from the who-else flag.

    ⚠ AN UNKNOWN FLAG IS TREATED AS `alone`, WHICH IS THE SMALL STAKE. It must
    never fail to the big one, and it must never fail to no-bet either -- that
    would silently reproduce the 24 bets that went missing tonight when a guard
    quietly refused everything.
    """
    if alone is None:
        return BUCKET_UNKNOWN
    if alone:
        return BUCKET_ALONE
    # Not alone: somebody else is on this game. Which side did they take?
    text = (consensus or "").lower()
    if "other side" in text or "oppose" in text:
        return BUCKET_OPPOSITE
    return BUCKET_AGREED


def stake_pct_for(alone, consensus: str = "") -> float:
    """The percentage this bet is sized at. Only `agreed` gets the big one."""
    return (STAKE_PCT_AGREED if bucket_for(alone, consensus) == BUCKET_AGREED
            else STAKE_PCT_OTHER)


def stake_for_bucket(balance_usd, alone, consensus: str = "") -> float:
    """What one bet may cost, given his balance and which tier it is in."""
    pct = stake_pct_for(alone, consensus)
    try:
        balance = float(balance_usd)
    except (TypeError, ValueError):
        return 0.0
    if balance <= 0:
        return 0.0
    return round(min(balance * pct / 100.0, MAX_STAKE_USD), 2)


def stake_for(balance_usd) -> float:
    """What one bet is allowed to cost, given his real balance.

    **Fails closed.** An unknown or nonsense balance returns 0.00, which sizes
    to no bet at all. The alternative -- falling back to some default -- is how
    a tool keeps trading on a number it does not actually have.
    """
    try:
        balance = float(balance_usd)
    except (TypeError, ValueError):
        return 0.0
    if balance <= 0:
        return 0.0
    return round(min(balance * STAKE_PCT / 100.0, MAX_STAKE_USD), 2)

# Guard 2 -- the cut-off -- lives in ledger.py, not here. It was a fixed
# -$33 until he corrected it on 2026-08-12: "It can't be cut off at thirty,
# because let's say the bot keeps going and makes three hundred, and then we
# lose thirty. That's only ten percent." It is now an absolute $50 floor plus
# a 35% trailing drop, and both need the ledger to compute.


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
    """How many contracts `stake_usd` buys at this price, and what happens
    either way.

    Contracts are floored, never rounded up: going over the stake to buy one
    more contract is exactly the drift Guard 3 exists to stop.

    ⚠ THE CLAMP MOVED, IT DID NOT GO AWAY. This used to clamp to the module
    constant, which made "no caller can ask for more" true by construction.
    Since the stake became a percentage of a live balance that is no longer
    possible, so it now clamps to `MAX_STAKE_USD` -- an explicit absolute
    ceiling equal to the daily cap. A caller passing a wrong or enormous number
    still cannot spend more than one day's budget on one bet.

    A nonsense stake sizes to no bet, rather than to a default one.
    """
    try:
        stake_usd = float(stake_usd)
    except (TypeError, ValueError):
        return Bet(int(price_c), 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    stake_usd = min(stake_usd, MAX_STAKE_USD)
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
