"""Reconstructed positions and their constituent lots."""

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
from ..enums import MarketPhase, PositionBehaviour, PositionStatus, TennisMarketType


class ReconstructedPosition(Base):
    """A wallet's complete round trip in one outcome token.

    A new position row is opened when exposure goes from flat to non-zero, and
    closed when it returns to flat (or the market settles). Adds are folded into
    the same row via lots, which is what prevents a scaled-in entry from being
    counted as several independent trades.
    """

    __tablename__ = "reconstructed_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="SET NULL"), index=True
    )
    outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("outcomes.id", ondelete="SET NULL"), index=True
    )
    token_id: Mapped[str] = mapped_column(String(90), nullable=False, index=True)
    condition_id: Mapped[str | None] = mapped_column(String(80), index=True)
    outcome_index: Mapped[int | None] = mapped_column(Integer)

    # Distinguishes successive round trips in the same token.
    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default=PositionStatus.OPEN, nullable=False, index=True
    )
    accounting_method: Mapped[str] = mapped_column(String(20), default="fifo", nullable=False)

    # --- entry ----------------------------------------------------------
    opened_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, index=True)
    opened_ts: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    first_entry_price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    avg_entry_price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    entry_tx_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    accumulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scaled_in_at_worse_prices: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # --- exit -----------------------------------------------------------
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, index=True)
    closed_ts: Mapped[int | None] = mapped_column(Integer)
    avg_exit_price: Mapped[Decimal | None] = mapped_column(Price)
    exit_tx_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    partial_exit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    settled_by_redemption: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- size -----------------------------------------------------------
    total_shares_bought: Mapped[Decimal] = mapped_column(Qty, default=Decimal("0"), nullable=False)
    total_shares_sold: Mapped[Decimal] = mapped_column(Qty, default=Decimal("0"), nullable=False)
    current_shares: Mapped[Decimal] = mapped_column(Qty, default=Decimal("0"), nullable=False)
    max_shares: Mapped[Decimal] = mapped_column(Qty, default=Decimal("0"), nullable=False)
    capital_committed: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    max_capital_at_risk: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("0"), nullable=False
    )
    # Share of the wallet's observed portfolio value, when estimable.
    pct_of_wallet_capital: Mapped[float | None] = mapped_column(Float)

    # --- P&L ------------------------------------------------------------
    realized_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Money)
    gross_pnl: Mapped[Decimal | None] = mapped_column(Money)
    fees_paid: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    net_pnl: Mapped[Decimal | None] = mapped_column(Money)
    roi: Mapped[float | None] = mapped_column(Float)
    is_win: Mapped[bool | None] = mapped_column(Boolean)

    # --- context --------------------------------------------------------
    holding_seconds: Mapped[int | None] = mapped_column(Integer)
    entry_phase: Mapped[str] = mapped_column(
        String(15), default=MarketPhase.UNKNOWN, nullable=False, index=True
    )
    tennis_market_type: Mapped[str] = mapped_column(
        String(30), default=TennisMarketType.UNKNOWN, nullable=False, index=True
    )
    is_tennis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # --- behavioural flags (indicative, not verdicts) -------------------
    behaviour: Mapped[str] = mapped_column(
        String(30), default=PositionBehaviour.DIRECTIONAL, nullable=False, index=True
    )
    # JSON-encoded list[str] of RiskFlag values.
    flags: Mapped[str | None] = mapped_column(Text)
    # True when the wallet also held the opposing token during this window.
    held_both_outcomes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconstruction_confidence: Mapped[float] = mapped_column(
        Float, default=100.0, nullable=False
    )
    reconstruction_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    lots: Mapped[list[PositionLot]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )
    copyability: Mapped[list[TradeCopyability]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("wallet_id", "token_id", "sequence", name="uq_position_seq"),
        Index("ix_position_wallet_tennis", "wallet_id", "is_tennis", "status"),
        Index("ix_position_tennis_closed", "is_tennis", "status", "closed_ts"),
        Index("ix_position_opened", "is_tennis", "opened_ts"),
    )

    @property
    def is_complete(self) -> bool:
        return self.status in (PositionStatus.CLOSED, PositionStatus.SETTLED)


class PositionLot(Base):
    """An individual acquisition tranche, consumed by exits per the accounting
    method. Retaining lots is what lets us report FIFO and weighted-average
    results from the same ingested data."""

    __tablename__ = "position_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position_id: Mapped[int] = mapped_column(
        ForeignKey("reconstructed_positions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_transactions.id", ondelete="SET NULL")
    )

    lot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    acquired_ts: Mapped[int] = mapped_column(Integer, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    shares: Mapped[Decimal] = mapped_column(Qty, nullable=False)
    shares_remaining: Mapped[Decimal] = mapped_column(Qty, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Money, nullable=False)

    realized_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    fully_consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    position: Mapped[ReconstructedPosition] = relationship(back_populates="lots")

    __table_args__ = (
        UniqueConstraint("position_id", "lot_index", name="uq_lot_index"),
    )


class TradeCopyability(Base):
    """Per-(position, delay) follower-realism analysis.

    One row per follower delay so the UI can show a delay-sensitivity curve and
    the alerting layer can key off a single benchmark delay.
    """

    __tablename__ = "trade_copyability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position_id: Mapped[int] = mapped_column(
        ForeignKey("reconstructed_positions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    wallet_entry_price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    # Best-available market price immediately before the wallet's fill.
    price_before: Mapped[Decimal | None] = mapped_column(Price)
    price_after_delay: Mapped[Decimal | None] = mapped_column(Price)
    # What the follower would actually pay, after spread and depth walking.
    estimated_fill_price: Mapped[Decimal | None] = mapped_column(Price)

    price_deterioration: Mapped[Decimal | None] = mapped_column(Price)
    price_deterioration_pct: Mapped[float | None] = mapped_column(Float)
    slippage: Mapped[Decimal | None] = mapped_column(Price)
    spread_at_entry: Mapped[Decimal | None] = mapped_column(Price)
    available_liquidity: Mapped[Decimal | None] = mapped_column(Money)

    # Follower outcome using the same exit as the wallet (or resolution).
    follower_exit_price: Mapped[Decimal | None] = mapped_column(Price)
    follower_pnl: Mapped[Decimal | None] = mapped_column(Money)
    follower_roi: Mapped[float | None] = mapped_column(Float)
    follower_is_win: Mapped[bool | None] = mapped_column(Boolean)

    copyability_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # JSON-encoded {factor: contribution} for UI explainability.
    copyability_components: Mapped[str | None] = mapped_column(Text)

    price_source_quality: Mapped[str] = mapped_column(String(25), nullable=False)
    data_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    computed_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    position: Mapped[ReconstructedPosition] = relationship(back_populates="copyability")

    __table_args__ = (
        UniqueConstraint("position_id", "delay_seconds", name="uq_copyability_delay"),
    )

