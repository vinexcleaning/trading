"""Signals, their contributing wallets, and emitted alerts."""

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

from ..db import UtcDateTime, Base, Money, Price
from ..enums import MarketPhase, SignalStatus, SignalType


class Signal(Base):
    """A candidate copy-trade opportunity.

    Every candidate is persisted -- including rejections -- because the rejection
    reasons are themselves a product surface (the daily report shows what was
    filtered and why, which is how a user calibrates trust in the thresholds).
    """

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_type: Mapped[str] = mapped_column(
        String(25), default=SignalType.SINGLE_WALLET, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SignalStatus.OBSERVED, nullable=False, index=True
    )

    market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="SET NULL"), index=True
    )
    outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("outcomes.id", ondelete="SET NULL")
    )
    token_id: Mapped[str] = mapped_column(String(90), nullable=False, index=True)
    condition_id: Mapped[str | None] = mapped_column(String(80), index=True)
    outcome_label: Mapped[str | None] = mapped_column(String(200))

    # Idempotency key: stops the same underlying wallet action from producing
    # duplicate signals across scheduler ticks.
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    # --- timing ---------------------------------------------------------
    # Earliest contributing wallet trade.
    first_wallet_trade_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, index=True
    )
    last_wallet_trade_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False, index=True
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # Detection lag: how stale the signal already was when we first saw it.
    signal_age_seconds: Mapped[int | None] = mapped_column(Integer)

    market_phase: Mapped[str] = mapped_column(
        String(15), default=MarketPhase.UNKNOWN, nullable=False
    )

    # --- prices ---------------------------------------------------------
    wallet_entry_price_min: Mapped[Decimal | None] = mapped_column(Price)
    wallet_entry_price_max: Mapped[Decimal | None] = mapped_column(Price)
    wallet_entry_price_median: Mapped[Decimal | None] = mapped_column(Price)
    current_price: Mapped[Decimal | None] = mapped_column(Price)
    estimated_follower_price: Mapped[Decimal | None] = mapped_column(Price)
    price_deterioration: Mapped[Decimal | None] = mapped_column(Price)

    # --- market conditions ---------------------------------------------
    available_liquidity: Mapped[Decimal | None] = mapped_column(Money)
    spread: Mapped[Decimal | None] = mapped_column(Price)
    total_wallet_position_usdc: Mapped[Decimal | None] = mapped_column(Money)

    # --- scores ---------------------------------------------------------
    wallet_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    independent_cluster_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    median_skill_score: Mapped[float | None] = mapped_column(Float)
    median_copyable_roi: Mapped[float | None] = mapped_column(Float)
    copyability_score: Mapped[float | None] = mapped_column(Float)
    consensus_score: Mapped[float | None] = mapped_column(Float)
    # Heuristic edge estimate. Explicitly not a calibrated probability.
    estimated_edge: Mapped[float | None] = mapped_column(Float)
    edge_method: Mapped[str | None] = mapped_column(String(40))
    data_confidence: Mapped[float | None] = mapped_column(Float)

    # --- decision -------------------------------------------------------
    qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # JSON-encoded list[RejectionReason].
    rejection_reasons: Mapped[str | None] = mapped_column(Text)
    # JSON-encoded list[str] of RiskFlag values.
    risk_flags: Mapped[str | None] = mapped_column(Text)
    # Human-readable "why this qualified / why it did not".
    explanation: Mapped[str | None] = mapped_column(Text)
    # JSON: every threshold checked with its value and verdict.
    qualification_detail: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    wallets: Mapped[list[SignalWallet]] = relationship(
        back_populates="signal", cascade="all, delete-orphan", lazy="selectin"
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_signals_feed", "status", "detected_at"),
        Index("ix_signals_qualified_time", "qualified", "detected_at"),
    )


class SignalWallet(Base):
    """One wallet's contribution to a signal."""

    __tablename__ = "signal_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_id: Mapped[int | None] = mapped_column(
        ForeignKey("reconstructed_positions.id", ondelete="SET NULL")
    )

    entry_price: Mapped[Decimal | None] = mapped_column(Price)
    position_usdc: Mapped[Decimal | None] = mapped_column(Money)
    traded_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    skill_score: Mapped[float | None] = mapped_column(Float)
    copyable_roi: Mapped[float | None] = mapped_column(Float)
    tennis_trade_count: Mapped[int | None] = mapped_column(Integer)
    cluster_id: Mapped[int | None] = mapped_column(Integer)
    # False when this wallet was suppressed as a duplicate of a cluster peer.
    counted_as_independent: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_position_increase: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_begun_exiting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    signal: Mapped[Signal] = relationship(back_populates="wallets")

    __table_args__ = (
        UniqueConstraint("signal_id", "wallet_id", name="uq_signal_wallet"),
    )


class Alert(Base):
    """A delivered (or attempted) notification for a qualified signal."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    alert_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured payload mirroring the message, for the in-app feed.
    payload: Mapped[str | None] = mapped_column(Text)

    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    delivery_error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False, index=True
    )

    signal: Mapped[Signal] = relationship(back_populates="alerts")

    __table_args__ = (
        UniqueConstraint("signal_id", "channel", "alert_type", name="uq_alert_channel"),
        Index("ix_alerts_created", "created_at", "delivered"),
    )

