"""Data-source providers."""

from __future__ import annotations

from .base import (
    MarketDataProvider,
    ProviderActivity,
    ProviderBookLevel,
    ProviderEvent,
    ProviderLeaderboardEntry,
    ProviderMarket,
    ProviderOrderBook,
    ProviderOutcome,
    ProviderPosition,
    ProviderPricePoint,
    ProviderTrade,
)
from .http import (
    HttpClient,
    NotFoundError,
    ProviderError,
    RateLimitedError,
    RateLimiter,
    RequestStats,
    SchemaError,
)
from .polymarket import PolymarketProvider, parse_datetime

__all__ = [
    "MarketDataProvider",
    "ProviderActivity",
    "ProviderBookLevel",
    "ProviderEvent",
    "ProviderLeaderboardEntry",
    "ProviderMarket",
    "ProviderOrderBook",
    "ProviderOutcome",
    "ProviderPosition",
    "ProviderPricePoint",
    "ProviderTrade",
    "HttpClient",
    "RateLimiter",
    "RequestStats",
    "ProviderError",
    "RateLimitedError",
    "NotFoundError",
    "SchemaError",
    "PolymarketProvider",
    "parse_datetime",
    "get_provider",
]


def get_provider(name: str = "polymarket") -> MarketDataProvider:
    """Factory so callers never hardcode a vendor class."""
    if name == "polymarket":
        return PolymarketProvider()
    raise ValueError(f"Unknown provider: {name!r}")
