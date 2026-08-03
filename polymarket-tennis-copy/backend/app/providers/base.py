"""Data-source abstraction.

Concrete providers translate a vendor's payloads into the DTOs below. Nothing
downstream imports a vendor module directly, so a second venue (or a recorded
fixture replay) can be substituted without touching analytics code.

Every DTO keeps the raw payload alongside the normalized fields so ingestion can
persist an audit copy and detect upstream schema drift.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class ProviderOutcome:
    """One side of a market."""

    token_id: str
    outcome_index: int
    label: str
    price: Decimal | None = None


@dataclass(slots=True)
class ProviderMarket:
    """Normalized market metadata."""

    condition_id: str
    outcomes: list[ProviderOutcome]
    gamma_market_id: str | None = None
    question_id: str | None = None
    slug: str | None = None
    question: str | None = None
    description: str | None = None

    event_id: str | None = None
    event_slug: str | None = None
    event_title: str | None = None
    tags: list[str] = field(default_factory=list)

    # Official sports metadata when present -- the strongest classification
    # signal available (e.g. "tennis_set_winner").
    sports_market_type: str | None = None
    game_start_time: datetime | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    active: bool = True
    closed: bool = False
    archived: bool = False
    accepting_orders: bool = True
    enable_order_book: bool = True
    neg_risk: bool = False

    resolved: bool = False
    winning_outcome_index: int | None = None
    uma_resolution_statuses: str | None = None

    liquidity: Decimal | None = None
    volume: Decimal | None = None
    volume_24hr: Decimal | None = None
    spread: Decimal | None = None
    best_bid: Decimal | None = None
    best_ask: Decimal | None = None
    last_trade_price: Decimal | None = None
    tick_size: Decimal | None = None
    min_order_size: Decimal | None = None
    maker_fee_bps: int | None = None
    taker_fee_bps: int | None = None

    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderEvent:
    """Normalized event metadata (one tennis match, typically)."""

    event_id: str
    slug: str | None = None
    ticker: str | None = None
    title: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    start_date: datetime | None = None
    end_date: datetime | None = None
    active: bool = True
    closed: bool = False
    liquidity: Decimal | None = None
    volume: Decimal | None = None
    volume_24hr: Decimal | None = None
    markets: list[ProviderMarket] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderActivity:
    """One wallet action.

    ``dedupe_key`` is computed by the provider because only it knows which
    payload fields uniquely identify a fill. A transaction hash alone is not
    unique -- one hash can carry several fills.
    """

    wallet_address: str
    activity_type: str
    timestamp: int
    dedupe_key: str
    size: Decimal
    condition_id: str | None = None
    token_id: str | None = None
    outcome_index: int | None = None
    outcome_label: str | None = None
    side: str | None = None
    price: Decimal | None = None
    usdc_size: Decimal | None = None
    transaction_hash: str | None = None
    title: str | None = None
    slug: str | None = None
    event_slug: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderPosition:
    """A wallet's currently held position, as reported by the venue.

    Used to cross-check our own reconstruction rather than to replace it.
    """

    wallet_address: str
    token_id: str
    condition_id: str
    size: Decimal
    avg_price: Decimal | None = None
    initial_value: Decimal | None = None
    current_value: Decimal | None = None
    cash_pnl: Decimal | None = None
    realized_pnl: Decimal | None = None
    total_bought: Decimal | None = None
    current_price: Decimal | None = None
    outcome_index: int | None = None
    outcome_label: str | None = None
    redeemable: bool = False
    title: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderTrade:
    """A public trade print. The second-level tape used for delay analysis."""

    token_id: str
    condition_id: str
    timestamp: int
    price: Decimal
    size: Decimal
    side: str | None = None
    wallet_address: str | None = None
    outcome_index: int | None = None
    transaction_hash: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderPricePoint:
    """A historical price sample.

    ``fidelity_minutes`` records the coarseness of the source series, which the
    price resolver needs in order to downgrade confidence honestly.
    """

    token_id: str
    timestamp: int
    price: Decimal
    fidelity_minutes: int = 1


@dataclass(slots=True)
class ProviderBookLevel:
    price: Decimal
    size: Decimal


@dataclass(slots=True)
class ProviderOrderBook:
    """Order-book depth snapshot."""

    token_id: str
    timestamp: int
    bids: list[ProviderBookLevel] = field(default_factory=list)
    asks: list[ProviderBookLevel] = field(default_factory=list)
    tick_size: Decimal | None = None
    min_order_size: Decimal | None = None
    neg_risk: bool = False
    last_trade_price: Decimal | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def best_bid(self) -> Decimal | None:
        return max((lvl.price for lvl in self.bids), default=None)

    @property
    def best_ask(self) -> Decimal | None:
        return min((lvl.price for lvl in self.asks), default=None)

    @property
    def midpoint(self) -> Decimal | None:
        bid, ask = self.best_bid, self.best_ask
        if bid is None or ask is None:
            return None
        return (bid + ask) / Decimal("2")

    @property
    def spread(self) -> Decimal | None:
        bid, ask = self.best_bid, self.best_ask
        if bid is None or ask is None:
            return None
        return ask - bid

    def ask_depth_usdc(self, within: Decimal | None = None) -> Decimal:
        """Notional available on the ask side, optionally within ``within`` of touch.

        Notional (price x size) rather than share count, because a follower's
        constraint is dollars they can deploy.
        """
        best = self.best_ask
        if best is None:
            return Decimal("0")
        limit = best + within if within is not None else None
        total = Decimal("0")
        for lvl in self.asks:
            if limit is not None and lvl.price > limit:
                continue
            total += lvl.price * lvl.size
        return total

    def bid_depth_usdc(self, within: Decimal | None = None) -> Decimal:
        best = self.best_bid
        if best is None:
            return Decimal("0")
        limit = best - within if within is not None else None
        total = Decimal("0")
        for lvl in self.bids:
            if limit is not None and lvl.price < limit:
                continue
            total += lvl.price * lvl.size
        return total


@dataclass(slots=True)
class ProviderLeaderboardEntry:
    """A candidate wallet from a public leaderboard. Never auto-trusted."""

    wallet_address: str
    amount: Decimal
    metric: str
    window: str
    pseudonym: str | None = None
    name: str | None = None


class MarketDataProvider(ABC):
    """Interface every data source must satisfy."""

    name: str = "abstract"

    # ------------------------------------------------------------ markets
    @abstractmethod
    def iter_events(
        self,
        *,
        tag_id: int | None = None,
        closed: bool | None = None,
        limit: int = 100,
        max_pages: int | None = None,
        start_date_min: datetime | None = None,
    ) -> Iterator[ProviderEvent]:
        """Yield events, transparently paginating."""

    @abstractmethod
    def get_market(self, condition_id: str) -> ProviderMarket | None:
        """Fetch a single market by condition id."""

    @abstractmethod
    def get_markets_by_condition_ids(
        self, condition_ids: list[str]
    ) -> list[ProviderMarket]:
        """Batch market lookup."""

    # ------------------------------------------------------------ wallets
    @abstractmethod
    def iter_wallet_activity(
        self,
        wallet_address: str,
        *,
        start_ts: int | None = None,
        end_ts: int | None = None,
        max_pages: int | None = None,
    ) -> Iterator[ProviderActivity]:
        """Yield a wallet's activity, oldest-first where the venue allows."""

    @abstractmethod
    def get_wallet_positions(self, wallet_address: str) -> list[ProviderPosition]:
        """Current open positions for a wallet."""

    @abstractmethod
    def get_wallet_value(self, wallet_address: str) -> Decimal | None:
        """Total portfolio value, used to estimate position sizing context."""

    # ------------------------------------------------------------- prices
    @abstractmethod
    def get_market_trades(
        self,
        condition_id: str,
        *,
        limit: int = 500,
        max_pages: int | None = None,
    ) -> list[ProviderTrade]:
        """Public trade tape for a market (second-level timestamps)."""

    @abstractmethod
    def get_price_history(
        self,
        token_id: str,
        *,
        interval: str = "1d",
        fidelity_minutes: int = 1,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[ProviderPricePoint]:
        """Historical price series. Fidelity is bounded by the venue."""

    @abstractmethod
    def get_order_book(self, token_id: str) -> ProviderOrderBook | None:
        """Current order-book depth."""

    # -------------------------------------------------------- discovery
    @abstractmethod
    def get_leaderboard(
        self, *, metric: str = "volume", window: str = "30d", limit: int = 50
    ) -> list[ProviderLeaderboardEntry]:
        """Public leaderboard entries as *candidates* for the registry."""
