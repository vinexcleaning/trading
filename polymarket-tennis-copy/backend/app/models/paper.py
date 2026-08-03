"""Paper-trading positions and their event log.

Simulation only. Nothing in this module places a real order, and the schema
records the assumptions behind every fill so results are never mistaken for
achieved performance.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
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
from ..enums import ExitStrategy, PaperTradeStatus


class PaperTrade(Base):
    """A simulated follower position derived from a qualified signal."""

    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(
        ForeignKey("signals.id", ondelete="SET NULL"), index=True
    )
    market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="SET NULL"), index=True
    )
    token_id: Mapped[str] = mapped_column(String(90), nullable=False, index=True)
    outcome_label: Mapped[str | None] = mapped_column(String(200))

    status: Mapped[str] = mapped_column(
        String(20), default=PaperTradeStatus.PENDING, nullable=False, index=True
    )
    exit_strategy: Mapped[str] = mapped_column(
        String(30), default=ExitStrategy.HOLD_TO_RESOLUTION, nullable=False
    )

    # --- entry assumptions (recorded, not inferred later) ---------------
    signal_detected_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False
    )
    execution_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    entered_at: Mapped[datetime | None] = mapped_column(UtcDateTime, index=True)

    wallet_entry_price: Mapped[Decimal | None] = mapped_column(Price)
    # Market price at the moment the simulated order would have been sent.
    reference_price: Mapped[Decimal | None] = mapped_column(Price)
    fill_price: Mapped[Decimal | None] = mapped_column(Price)
    slippage_applied: Mapped[Decimal | None] = mapped_column(Price)
    fees_applied: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)

    stake_usdc: Mapped[Decimal] = mapped_column(Money, nullable=False)
    shares: Mapped[Decimal | None] = mapped_column(Qty)
    # Set when modeled depth could not absorb the full intended stake.
    stake_reduced_for_liquidity: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # --- exit -----------------------------------------------------------
    exited_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    exit_price: Mapped[Decimal | None] = mapped_column(Price)
    exit_reason: Mapped[str | None] = mapped_column(String(60))
    settled_by_resolution: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    realized_pnl: Mapped[Decimal | None] = mapped_column(Money)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Money)
    roi: Mapped[float | None] = mapped_column(Float)
    is_win: Mapped[bool | None] = mapped_column(Boolean)
    holding_seconds: Mapped[int | None] = mapped_column(Integer)

    # --- comparison against the wallet we copied -----------------------
    wallet_roi: Mapped[float | None] = mapped_column(Float)
    # follower_roi - wallet_roi: the cost of being late.
    roi_gap_vs_wallet: Mapped[float | None] = mapped_column(Float)

    price_source_quality: Mapped[str | None] = mapped_column(String(25))
    data_confidence: Mapped[float | None] = mapped_column(Float)
    rejection_reason: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)

    # Distinguishes live paper trading from backtest-generated rows.
    is_backtest: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    backtest_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    events: Mapped[list[PaperTradeEvent]] = relationship(
        back_populates="trade", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_paper_status_entered", "status", "entered_at"),
        Index("ix_paper_live", "is_backtest", "status"),
    )


class PaperTradeEvent(Base):
    """Append-only audit trail for a paper trade."""

    __tablename__ = "paper_trade_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_trade_id: Mapped[int] = mapped_column(
        ForeignKey("paper_trades.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)

    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Price)
    shares: Mapped[Decimal | None] = mapped_column(Qty)
    pnl: Mapped[Decimal | None] = mapped_column(Money)
    detail: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    trade: Mapped[PaperTrade] = relationship(back_populates="events")


class PaperDailyStat(Base):
    """Per-day roll-up used to enforce the daily loss cap and build reports."""

    __tablename__ = "paper_daily_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    trades_entered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trades_closed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stake_deployed: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    entries_blocked_by_risk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("stat_date", name="uq_paper_daily_date"),)

