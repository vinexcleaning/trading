from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionPolicy:
    requested_notional_usd: float = 1.0
    max_spread: float = 0.03
    max_price_deterioration: float = 0.02
    minimum_gross_upside: float = 0.03
    allow_partial_fill: bool = False


@dataclass(frozen=True)
class ExecutionResult:
    accepted: bool
    rejection_reason: str | None
    requested_notional_usd: float
    filled_notional_usd: float
    filled_shares: float
    average_fill_price: float | None
    best_bid: float | None
    best_ask: float | None
    fee_usd: float
    slippage_usd: float


def taker_fee(shares: float, price: float, fee_rate_decimal: float) -> float:
    if shares < 0 or not 0 <= price <= 1 or fee_rate_decimal < 0:
        raise ValueError("invalid fee input")
    return shares * fee_rate_decimal * price * (1.0 - price)


def simulate_buy(
    book: dict[str, Any],
    original_price: float,
    fee_rate_decimal: float,
    policy: ExecutionPolicy,
) -> ExecutionResult:
    bids = sorted(
        ((float(row["price"]), float(row["size"])) for row in book.get("bids", [])),
        reverse=True,
    )
    asks = sorted(
        (float(row["price"]), float(row["size"])) for row in book.get("asks", [])
    )
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None

    def rejected(reason: str) -> ExecutionResult:
        return ExecutionResult(
            False, reason, policy.requested_notional_usd, 0.0, 0.0, None,
            best_bid, best_ask, 0.0, 0.0,
        )

    if best_bid is None or best_ask is None:
        return rejected("missing_book_side")
    if best_ask < best_bid:
        return rejected("crossed_book")
    if best_ask - best_bid > policy.max_spread:
        return rejected("spread_too_wide")
    if best_ask - original_price > policy.max_price_deterioration:
        return rejected("price_moved_too_far")
    if 1.0 - best_ask < policy.minimum_gross_upside:
        return rejected("insufficient_remaining_upside")

    remaining = policy.requested_notional_usd
    shares = 0.0
    cost = 0.0
    fee = 0.0
    for price, available_shares in asks:
        if price <= 0:
            continue
        level_shares = min(available_shares, remaining / price)
        level_cost = level_shares * price
        shares += level_shares
        cost += level_cost
        fee += taker_fee(level_shares, price, fee_rate_decimal)
        remaining -= level_cost
        if remaining <= 1e-9:
            break

    if shares <= 0:
        return rejected("insufficient_liquidity")
    if remaining > 1e-6 and not policy.allow_partial_fill:
        return rejected("insufficient_liquidity")
    average = cost / shares
    slippage = max(0.0, cost - shares * best_ask)
    return ExecutionResult(
        True,
        None,
        policy.requested_notional_usd,
        cost,
        shares,
        average,
        best_bid,
        best_ask,
        fee,
        slippage,
    )
