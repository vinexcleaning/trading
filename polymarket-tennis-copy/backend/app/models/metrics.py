"""Wallet metrics, historical snapshots and scores."""

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
from sqlalchemy.orm import Mapped, mapped_column

from ..db import UtcDateTime, Base, Money, Price


class WalletMetrics(Base):
    """Current metric set for one wallet under one scope.

    ``scope`` lets the same table hold overall, tennis-only and sliced views
    (e.g. ``tennis``, ``tennis:live``, ``tennis:prematch``,
    ``tennis:match_winner``, ``tennis:30d``) without a wide sparse schema.
    """

    __tablename__ = "wallet_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    # --- volume / counts ------------------------------------------------
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    volume_usdc: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    capital_deployed: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)

    # --- raw P&L --------------------------------------------------------
    gross_profit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    gross_loss: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    net_profit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    fees_paid: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)

    roi: Mapped[float | None] = mapped_column(Float)
    # Equal-weighted mean of per-trade ROI. The only raw figure directly
    # comparable to copyable ROI, which is equal-weighted because a follower
    # stakes a flat amount per signal.
    roi_equal_weighted: Mapped[float | None] = mapped_column(Float)
    return_on_capital: Mapped[float | None] = mapped_column(Float)
    win_rate: Mapped[float | None] = mapped_column(Float)
    profit_factor: Mapped[float | None] = mapped_column(Float)
    avg_profit_per_trade: Mapped[Decimal | None] = mapped_column(Money)
    median_profit_per_trade: Mapped[Decimal | None] = mapped_column(Money)
    # Expected value per $1 staked -- the metric that survives the
    # "90% win rate buying at $0.95" trap.
    expected_value_per_dollar: Mapped[float | None] = mapped_column(Float)

    avg_entry_price: Mapped[Decimal | None] = mapped_column(Price)
    avg_holding_seconds: Mapped[int | None] = mapped_column(Integer)
    median_holding_seconds: Mapped[int | None] = mapped_column(Integer)

    # --- risk -----------------------------------------------------------
    max_drawdown: Mapped[float | None] = mapped_column(Float)
    max_drawdown_usdc: Mapped[Decimal | None] = mapped_column(Money)
    longest_win_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_loss_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pct_profit_from_largest_trade: Mapped[float | None] = mapped_column(Float)
    pct_profit_from_top5_trades: Mapped[float | None] = mapped_column(Float)
    pnl_std_dev: Mapped[float | None] = mapped_column(Float)
    sharpe_like: Mapped[float | None] = mapped_column(Float)

    # --- copyable (delay-adjusted) -------------------------------------
    benchmark_delay_seconds: Mapped[int | None] = mapped_column(Integer)
    copyable_roi: Mapped[float | None] = mapped_column(Float)
    # Robust companions: mean-of-ROI is convex on binary outcomes, so a handful
    # of cheap fills on winners can manufacture an edge.
    copyable_roi_median: Mapped[float | None] = mapped_column(Float)
    copyable_roi_trimmed: Mapped[float | None] = mapped_column(Float)
    copyable_outlier_dependence: Mapped[float | None] = mapped_column(Float)
    copyable_win_rate: Mapped[float | None] = mapped_column(Float)
    copyable_net_profit: Mapped[Decimal | None] = mapped_column(Money)
    copyable_profit_factor: Mapped[float | None] = mapped_column(Float)
    avg_copyability_score: Mapped[float | None] = mapped_column(Float)
    # Fraction of completed positions with price evidence strong enough to assess
    # copyability. Low coverage means the copyable figures cover a partial record.
    copyable_coverage: Mapped[float | None] = mapped_column(Float)
    avg_price_deterioration: Mapped[Decimal | None] = mapped_column(Price)
    # JSON: {delay_seconds: {roi, win_rate, net_profit, n}} for the curve.
    roi_by_delay: Mapped[str | None] = mapped_column(Text)

    # --- statistical confidence ----------------------------------------
    roi_ci_low: Mapped[float | None] = mapped_column(Float)
    roi_ci_high: Mapped[float | None] = mapped_column(Float)
    copyable_roi_ci_low: Mapped[float | None] = mapped_column(Float)
    copyable_roi_ci_high: Mapped[float | None] = mapped_column(Float)
    shrunk_copyable_roi: Mapped[float | None] = mapped_column(Float)
    # Probability that copyable edge > 0, from the bootstrap distribution.
    prob_positive_edge: Mapped[float | None] = mapped_column(Float)
    sample_confidence: Mapped[float | None] = mapped_column(Float)

    # --- breakdowns (JSON, rendered as tables in the UI) ---------------
    performance_by_market_type: Mapped[str | None] = mapped_column(Text)
    performance_by_tournament: Mapped[str | None] = mapped_column(Text)
    performance_by_player: Mapped[str | None] = mapped_column(Text)
    performance_by_entry_bucket: Mapped[str | None] = mapped_column(Text)
    performance_by_size_bucket: Mapped[str | None] = mapped_column(Text)
    performance_by_period: Mapped[str | None] = mapped_column(Text)

    data_quality_score: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("wallet_id", "scope", name="uq_wallet_metrics_scope"),
        Index("ix_wallet_metrics_scope_roi", "scope", "copyable_roi"),
    )


class WalletMetricHistory(Base):
    """Daily snapshot of headline metrics, for trend and degradation detection."""

    __tablename__ = "wallet_metric_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(60), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    completed_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_profit: Mapped[Decimal | None] = mapped_column(Money)
    roi: Mapped[float | None] = mapped_column(Float)
    copyable_roi: Mapped[float | None] = mapped_column(Float)
    win_rate: Mapped[float | None] = mapped_column(Float)
    max_drawdown: Mapped[float | None] = mapped_column(Float)
    skill_score: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "wallet_id", "scope", "snapshot_date", name="uq_metric_history_day"
        ),
    )


class WalletScore(Base):
    """Adjusted Tennis Skill Score with every component exposed.

    Storing the components (not just the total) is what makes the ranking
    explainable in the UI -- a score with no visible derivation is exactly the
    kind of opaque authority this system is meant to avoid.
    """

    __tablename__ = "wallet_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(60), default="tennis", nullable=False)

    # Final 0-100 score after weighting and penalties.
    skill_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    # Weighted sum before penalties, useful for diagnosing penalty impact.
    base_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- components (each 0-100) ---------------------------------------
    copyable_roi_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    profit_factor_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sample_confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    drawdown_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    liquidity_fit_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    concentration_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    data_quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # JSON: {penalty_name: multiplier} actually applied.
    penalties_applied: Mapped[str | None] = mapped_column(Text)
    total_penalty_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # JSON-encoded list[str] of RiskFlag values.
    risk_flags: Mapped[str | None] = mapped_column(Text)
    # Gate for alerting: passes every hard minimum in settings.
    qualified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    disqualification_reasons: Mapped[str | None] = mapped_column(Text)

    confidence_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)

    # Formula version, so historical scores remain interpretable after tuning.
    formula_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("wallet_id", "scope", name="uq_wallet_score_scope"),
        Index("ix_wallet_score_rank", "scope", "qualified", "skill_score"),
    )

