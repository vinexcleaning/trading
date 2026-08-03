"""Backtest runs and their trade-level results."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import UtcDateTime, Base, Money, Price
from ..enums import JobStatus


class BacktestRun(Base):
    """One reproducible historical replay.

    The chronological split fields are mandatory rather than optional: reporting
    an in-sample result as evidence is the single easiest way to make a copy-trading
    system look profitable when it is not.
    """

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.RUNNING, nullable=False, index=True
    )

    # --- configuration (full snapshot, so a run is reproducible) --------
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    # Convenience columns for filtering the run list.
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    slippage_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fee_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exit_strategy: Mapped[str] = mapped_column(String(30), nullable=False)
    stake_usdc: Mapped[Decimal] = mapped_column(Money, nullable=False)
    consensus_required: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    period_start: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    # Chronological boundaries. train < validation < test, never shuffled.
    train_end: Mapped[datetime | None] = mapped_column(UtcDateTime)
    validation_end: Mapped[datetime | None] = mapped_column(UtcDateTime)

    # --- aggregate results ---------------------------------------------
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_staked: Mapped[Decimal | None] = mapped_column(Money)
    total_pnl: Mapped[Decimal | None] = mapped_column(Money)
    total_return: Mapped[float | None] = mapped_column(Float)
    win_rate: Mapped[float | None] = mapped_column(Float)
    profit_factor: Mapped[float | None] = mapped_column(Float)
    max_drawdown: Mapped[float | None] = mapped_column(Float)
    avg_trade_pnl: Mapped[Decimal | None] = mapped_column(Money)
    median_trade_pnl: Mapped[Decimal | None] = mapped_column(Money)
    sharpe_like: Mapped[float | None] = mapped_column(Float)

    # --- split-aware results -------------------------------------------
    in_sample_return: Mapped[float | None] = mapped_column(Float)
    out_of_sample_return: Mapped[float | None] = mapped_column(Float)
    validation_return: Mapped[float | None] = mapped_column(Float)
    # JSON: [{window_start, window_end, return, trades}, ...]
    walk_forward_json: Mapped[str | None] = mapped_column(Text)

    # --- curves and sensitivity (JSON for direct charting) -------------
    equity_curve_json: Mapped[str | None] = mapped_column(Text)
    drawdown_curve_json: Mapped[str | None] = mapped_column(Text)
    delay_sensitivity_json: Mapped[str | None] = mapped_column(Text)
    parameter_sensitivity_json: Mapped[str | None] = mapped_column(Text)
    outcome_distribution_json: Mapped[str | None] = mapped_column(Text)
    by_market_type_json: Mapped[str | None] = mapped_column(Text)
    by_wallet_json: Mapped[str | None] = mapped_column(Text)

    return_ci_low: Mapped[float | None] = mapped_column(Float)
    return_ci_high: Mapped[float | None] = mapped_column(Float)
    # Share of total P&L from the single best trade -- outlier dependence.
    pct_pnl_from_top_trade: Mapped[float | None] = mapped_column(Float)

    # --- integrity -----------------------------------------------------
    lookahead_violations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_quality_warnings: Mapped[str | None] = mapped_column(Text)
    skipped_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skip_reasons_json: Mapped[str | None] = mapped_column(Text)

    error: Mapped[str | None] = mapped_column(Text)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    trades: Mapped[list[BacktestTrade]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_backtest_status_created", "status", "created_at"),)


class BacktestTrade(Base):
    """One simulated trade inside a backtest, with its decision inputs.

    ``decision_inputs_json`` stores the metric values that were available *as of*
    the decision timestamp, which is what makes look-ahead auditable after the
    fact instead of merely asserted.
    """

    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[int | None] = mapped_column(
        ForeignKey("wallets.id", ondelete="SET NULL"), index=True
    )
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id", ondelete="SET NULL"))
    position_id: Mapped[int | None] = mapped_column(
        ForeignKey("reconstructed_positions.id", ondelete="SET NULL")
    )
    token_id: Mapped[str] = mapped_column(String(90), nullable=False)

    decision_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, index=True
    )
    entered_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    exited_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    wallet_entry_price: Mapped[Decimal | None] = mapped_column(Price)
    fill_price: Mapped[Decimal | None] = mapped_column(Price)
    exit_price: Mapped[Decimal | None] = mapped_column(Price)
    stake_usdc: Mapped[Decimal | None] = mapped_column(Money)
    pnl: Mapped[Decimal | None] = mapped_column(Money)
    roi: Mapped[float | None] = mapped_column(Float)
    is_win: Mapped[bool | None] = mapped_column(Boolean)

    exit_reason: Mapped[str | None] = mapped_column(String(60))
    market_type: Mapped[str | None] = mapped_column(String(30))
    market_phase: Mapped[str | None] = mapped_column(String(15))
    copyability_score: Mapped[float | None] = mapped_column(Float)
    price_source_quality: Mapped[str | None] = mapped_column(String(25))
    split: Mapped[str | None] = mapped_column(String(12), index=True)  # train/validation/test

    decision_inputs_json: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    run: Mapped[BacktestRun] = relationship(back_populates="trades")

    __table_args__ = (Index("ix_backtest_trade_run_time", "run_id", "decision_at"),)

