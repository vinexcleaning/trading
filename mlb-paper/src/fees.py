"""Series-aware fee lookup for this project. NO fee arithmetic lives here.

⚠ GUARD #6: `common/kalshi_fees.py` is the only fee implementation in this
repo and a test enforces it. This module contains no formula -- it looks up the
right RATE for a series and hands it to that module. If you find yourself
writing `0.07 * p * (100 - p)` here, stop.

⚠ WHAT THIS FIXES, found by the strategy factory and verified independently by
`coordinator` and by me against the live API on 2026-09-02:

**Kalshi charges HALF fee on the series these bots trade.** `fee_multiplier` is
**0.5** on `KXMLBGAME` and `KXMLBTOTAL`. I confirmed 1.0 on `KXATPMATCH`,
`KXNFLGAME` and `KXINXU`, so it is not a global change.

**Do NOT read this as "baseball is half fee".** Only the per-game and in-game
baseball series are 0.5; the season-long ones (`KXMLBWINS-*`, divisions,
All-Star) are full. **The true direction is: half-fee implies per-game
baseball, not the reverse.** Stating it backwards would put a wrong fee on the
season-long markets.

**And the second, separate error that stacked on top of it:** the edge
calculation used `fee_order_cents(price, 1)`, which applies Kalshi's
**per-ORDER round-up to a single contract**. `common/kalshi_fees.py` says in
its own docstring that `fee_rate_cents` is the one for expectancy arithmetic,
"where the per-order round-up is an artefact of order size rather than an
economic cost". The same misuse was found in `bot-forensics` the same week.

Together they made the entry gate demand about **3 cents** of edge in a market
whose real one-way cost is closer to **1**:

    price   subtracted before   real (half rate)   ratio
     20c         2.000c              0.560c         3.6x
     50c         2.000c              0.875c         2.3x
     95c         1.000c              0.166c         6.0x

⚠ **WE CANNOT DATE WHEN THE MULTIPLIER BECAME 0.5.** The only per-series
multiplier recorded anywhere in this repo is one snapshot, 2026-08-18. Kalshi
serves no historical series metadata. **True on 18 August, true today, unknown
before and unrecoverable.** Do not write that the whole archive was mispriced
from the start.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))

from common.kalshi_fees import (SeriesFees, fee_order_cents,   # noqa: E402
                                fee_rate_cents)

#: Verified live 2026-09-02. Refreshed by `refresh()`; never guessed.
_RATES: dict[str, Decimal] = {}

#: Only used when the API cannot be reached AND the series was verified.
#: A series that is not here and cannot be fetched raises -- it is not
#: defaulted to full rate, because a silent wrong fee is what this fixes.
_VERIFIED = {"KXMLBGAME": Decimal("0.5"), "KXMLBTOTAL": Decimal("0.5")}


def series_of(ticker: str) -> str:
    return ticker.split("-")[0] if ticker else ""


def rate_for(ticker_or_series: str) -> Decimal:
    """The taker rate for this series, multiplier included."""
    s = series_of(ticker_or_series) or ticker_or_series
    if s in _RATES:
        return _RATES[s]
    try:
        import kalshi as K
        obj = K.get(f"/series/{s}")
        sf = SeriesFees.from_api(obj.get("series") or obj)
        _RATES[s] = sf.taker_rate
        return _RATES[s]
    except Exception:                                   # noqa: BLE001
        if s in _VERIFIED:
            from common.kalshi_fees import TAKER_RATE
            _RATES[s] = TAKER_RATE * _VERIFIED[s]
            return _RATES[s]
        raise


def edge_fee_c(price_c, ticker) -> float:
    """Per-contract fee for EXPECTANCY. No per-order round-up. See the docstring."""
    return float(fee_rate_cents(price_c, rate_for(ticker)))


def order_fee_c(price_c, contracts, ticker) -> float:
    """What an order of `contracts` is actually BILLED. Rounded up per order."""
    return float(fee_order_cents(price_c, contracts, rate_for(ticker)))
