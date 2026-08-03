from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    bankroll_usd: float = 100.0
    max_trade_fraction: float = 0.02
    max_total_fraction: float = 0.20
    max_market_fraction: float = 0.05
    max_trader_fraction: float = 0.10


def check_entry(
    requested_notional: float,
    total_exposure: float,
    market_exposure: float,
    trader_exposure: float,
    limits: RiskLimits,
) -> str | None:
    if requested_notional <= 0:
        return "invalid_position_size"
    if requested_notional > limits.bankroll_usd * limits.max_trade_fraction:
        return "trade_risk_limit"
    if total_exposure + requested_notional > limits.bankroll_usd * limits.max_total_fraction:
        return "total_exposure_limit"
    if market_exposure + requested_notional > limits.bankroll_usd * limits.max_market_fraction:
        return "market_exposure_limit"
    if trader_exposure + requested_notional > limits.bankroll_usd * limits.max_trader_fraction:
        return "trader_exposure_limit"
    return None
