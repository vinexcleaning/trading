"""Kalshi fee calculations.

Verified against the live API `series` object in Phase 0 (2026-07-30):
every series carries `fee_type` in {"quadratic", "quadratic_with_maker_fees"}
and `fee_multiplier` in {0, 1}. See docs/contract_spec.md.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from decimal import Decimal

# The quadratic fee itself is not reimplemented here — it lives in
# common/kalshi_fees.py, the single implementation for the whole repo.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "common"))
from kalshi_fees import fee_order_from_price as _shared_order_cents  # noqa: E402

TAKER_RATE = 0.07
MAKER_RATE = 0.0175  # one quarter of taker, only on quadratic_with_maker_fees series


def _quadratic_fee_dollars(rate: float, contracts: int, price: float) -> float:
    """ceil-to-the-cent quadratic fee. price is in dollars (0..1).

    Exact Decimal via common/kalshi_fees.py: 0.07*100*0.5*0.5 evaluates to
    1.7500000000000002 in binary floating point, and a naive ceil turns the
    correct $1.75 fee into $1.76. Money gets exact arithmetic.
    """
    if not 0.0 <= price <= 1.0:
        raise ValueError(f"price must be in [0,1] dollars, got {price}")
    if contracts < 0:
        raise ValueError(f"contracts must be non-negative, got {contracts}")
    return float(_shared_order_cents(price, contracts, Decimal(str(rate)))) / 100.0


def taker_fee_dollars(contracts: int, price: float, multiplier: float = 1.0) -> float:
    return _quadratic_fee_dollars(TAKER_RATE * multiplier, contracts, price)


def maker_fee_dollars(
    contracts: int, price: float, multiplier: float = 1.0, charges_maker: bool = False
) -> float:
    if not charges_maker:
        return 0.0
    return _quadratic_fee_dollars(MAKER_RATE * multiplier, contracts, price)


def round_trip_taker_cents(contracts: int, price: float, multiplier: float = 1.0) -> float:
    """Cost in cents to enter and exit as taker at the same price.

    Both legs are rounded independently because Kalshi charges per fill.
    Exit at price p on the opposite side costs the same, since p(1-p) is symmetric.
    """
    entry = taker_fee_dollars(contracts, price, multiplier)
    exit_ = taker_fee_dollars(contracts, price, multiplier)
    return (entry + exit_) * 100.0


def breakeven_edge_cents(
    price: float,
    spread_cents: float,
    slippage_cents: float = 0.0,
    contracts: int = 100,
    multiplier: float = 1.0,
) -> float:
    """Probability edge (in cents of a $1 contract) required to break even.

    Reported per contract. Uses contracts=100 by default so the per-contract fee
    reflects the continuous quadratic curve rather than the 1-contract ceiling
    artifact (at C=1 the ceil dominates and every price looks like 1c).
    """
    fee_cents_per_contract = round_trip_taker_cents(contracts, price, multiplier) / contracts
    # crossing the spread once on entry; assume exit also crosses
    return fee_cents_per_contract + spread_cents + slippage_cents


@dataclass(frozen=True)
class SeriesFeeSpec:
    ticker: str
    fee_type: str
    fee_multiplier: float

    @property
    def charges_maker(self) -> bool:
        return self.fee_type == "quadratic_with_maker_fees"

    @property
    def effective_multiplier(self) -> float:
        # fee_multiplier == 0 observed on some series; treat as literal zero fees.
        return float(self.fee_multiplier)
