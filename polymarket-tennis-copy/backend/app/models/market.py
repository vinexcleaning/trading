"""Events, markets, outcomes and classification state."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import UtcDateTime, Base, Money, Price, Qty
from ..enums import MarketPhase, SportCategory, TennisMarketType


class Event(Base):
    """A Polymarket event -- for tennis, normally one match."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gamma_event_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    slug: Mapped[str | None] = mapped_column(String(255), index=True)
    ticker: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # JSON-encoded list[str] of tag slugs.
    tags: Mapped[str | None] = mapped_column(Text)

    start_date: Mapped[datetime | None] = mapped_column(UtcDateTime)
    end_date: Mapped[datetime | None] = mapped_column(UtcDateTime)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    liquidity: Mapped[Decimal | None] = mapped_column(Money)
    volume: Mapped[Decimal | None] = mapped_column(Money)
    volume_24hr: Mapped[Decimal | None] = mapped_column(Money)

    # --- tennis-specific derived metadata -------------------------------
    sport_category: Mapped[str] = mapped_column(
        String(20), default=SportCategory.UNKNOWN, nullable=False, index=True
    )
    tournament: Mapped[str | None] = mapped_column(String(200), index=True)
    player_a: Mapped[str | None] = mapped_column(String(120), index=True)
    player_b: Mapped[str | None] = mapped_column(String(120), index=True)
    # ATP matches are best-of-3 except men's Grand Slams (best-of-5).
    best_of: Mapped[int | None] = mapped_column(Integer)
    surface: Mapped[str | None] = mapped_column(String(20))
    tour: Mapped[str | None] = mapped_column(String(20))  # ATP / WTA / ITF / CH

    synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    markets: Mapped[list[Market]] = relationship(back_populates="event")

    __table_args__ = (Index("ix_events_sport_closed", "sport_category", "closed"),)


class Market(Base):
    """A single binary market. ``condition_id`` is the durable on-chain key."""

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condition_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    gamma_market_id: Mapped[str | None] = mapped_column(String(40), index=True)
    question_id: Mapped[str | None] = mapped_column(String(80))
    slug: Mapped[str | None] = mapped_column(String(255), index=True)
    question: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), index=True
    )

    # --- classification -------------------------------------------------
    sport_category: Mapped[str] = mapped_column(
        String(20), default=SportCategory.UNKNOWN, nullable=False, index=True
    )
    is_tennis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    tennis_market_type: Mapped[str] = mapped_column(
        String(30), default=TennisMarketType.UNKNOWN, nullable=False, index=True
    )
    # Raw ``sportsMarketType`` from Gamma, kept verbatim for auditability.
    sports_market_type_raw: Mapped[str | None] = mapped_column(String(60))
    # 0-100. Below the review threshold the market is excluded from alerting.
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # JSON-encoded list[ClassificationMethod] that contributed.
    classification_methods: Mapped[str | None] = mapped_column(Text)
    classification_notes: Mapped[str | None] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Which set/game this market refers to, when applicable.
    period_number: Mapped[int | None] = mapped_column(Integer)
    handicap_line: Mapped[Decimal | None] = mapped_column(Price)
    total_line: Mapped[Decimal | None] = mapped_column(Price)

    # --- timing ---------------------------------------------------------
    game_start_time: Mapped[datetime | None] = mapped_column(
        UtcDateTime, index=True
    )
    start_date: Mapped[datetime | None] = mapped_column(UtcDateTime)
    end_date: Mapped[datetime | None] = mapped_column(UtcDateTime)

    # --- state ----------------------------------------------------------
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepting_orders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_order_book: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    neg_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # Index of the winning outcome, derived from outcomePrices == 1.
    winning_outcome_index: Mapped[int | None] = mapped_column(Integer)
    resolved_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    uma_resolution_statuses: Mapped[str | None] = mapped_column(String(120))

    # --- market quality snapshot (latest known) -------------------------
    liquidity: Mapped[Decimal | None] = mapped_column(Money)
    volume: Mapped[Decimal | None] = mapped_column(Money)
    volume_24hr: Mapped[Decimal | None] = mapped_column(Money)
    spread: Mapped[Decimal | None] = mapped_column(Price)
    best_bid: Mapped[Decimal | None] = mapped_column(Price)
    best_ask: Mapped[Decimal | None] = mapped_column(Price)
    last_trade_price: Mapped[Decimal | None] = mapped_column(Price)
    tick_size: Mapped[Decimal | None] = mapped_column(Price)
    min_order_size: Mapped[Decimal | None] = mapped_column(Qty)

    maker_fee_bps: Mapped[int | None] = mapped_column(Integer)
    taker_fee_bps: Mapped[int | None] = mapped_column(Integer)

    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event: Mapped[Event | None] = relationship(back_populates="markets")
    outcomes: Mapped[list[Outcome]] = relationship(
        back_populates="market", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_markets_tennis_type", "is_tennis", "tennis_market_type"),
        Index("ix_markets_tennis_open", "is_tennis", "closed", "game_start_time"),
    )

    def phase_at(self, when: datetime) -> MarketPhase:
        """Prematch / live / post-match relative to ``game_start_time``.

        Without a known start time we return UNKNOWN rather than guessing, since
        the live-vs-prematch distinction drives alert expiry windows.
        """
        if self.game_start_time is None:
            return MarketPhase.UNKNOWN
        if when < self.game_start_time:
            return MarketPhase.PREMATCH
        if self.resolved and self.resolved_at and when > self.resolved_at:
            return MarketPhase.POST_MATCH
        return MarketPhase.LIVE


class Outcome(Base):
    """One side of a market, keyed by its CLOB ERC-1155 token id."""

    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(
        ForeignKey("markets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Token ids are 77-digit integers -- always handled as strings.
    token_id: Mapped[str] = mapped_column(String(90), nullable=False, unique=True, index=True)
    outcome_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    # Normalised player name when this outcome maps to a competitor.
    player_name: Mapped[str | None] = mapped_column(String(120), index=True)

    is_winner: Mapped[bool | None] = mapped_column(Boolean)
    last_price: Mapped[Decimal | None] = mapped_column(Price)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    market: Mapped[Market] = relationship(back_populates="outcomes")

    __table_args__ = (
        UniqueConstraint("market_id", "outcome_index", name="uq_outcome_market_index"),
    )

