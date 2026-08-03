"""Pydantic response/request schemas for the public API.

Decimals are serialised as strings so JavaScript's float parsing cannot silently
round a monetary value. Every response that carries a performance figure also
carries the evidence behind it (coverage, confidence, sample size), because a
number without its provenance is exactly what this system exists to avoid.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ApiModel(BaseModel):
    """Base with ORM support and string-serialised Decimals."""

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json")
    def _serialize_decimal(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        return value


# ------------------------------------------------------------------ wallets


class WalletTagOut(ApiModel):
    tag: str


class WalletCreate(BaseModel):
    address: str = Field(..., description="0x-prefixed 42-character wallet address")
    nickname: str | None = None
    notes: str | None = None
    manually_approved: bool = False
    on_watchlist: bool = False
    sync_priority: int = 100
    tags: list[str] = Field(default_factory=list)

    @field_validator("address")
    @classmethod
    def _validate_address(cls, v: str) -> str:
        candidate = v.strip().lower()
        if not candidate.startswith("0x") or len(candidate) != 42:
            raise ValueError("address must be a 0x-prefixed 42-character hex string")
        try:
            int(candidate, 16)
        except ValueError as exc:
            raise ValueError("address is not valid hexadecimal") from exc
        return candidate


class WalletUpdate(BaseModel):
    nickname: str | None = None
    notes: str | None = None
    status: str | None = None
    manually_approved: bool | None = None
    on_watchlist: bool | None = None
    sync_priority: int | None = None


class WalletOut(ApiModel):
    id: int
    address: str
    nickname: str | None
    pseudonym: str | None
    source: str
    source_detail: str | None
    status: str
    manually_approved: bool
    on_watchlist: bool
    notes: str | None
    risk_flags: list[str] = Field(default_factory=list)
    suspected_cluster_id: int | None
    first_activity_at: datetime | None
    last_activity_at: datetime | None
    last_sync_success_at: datetime | None
    last_sync_error: str | None
    backfill_complete: bool
    observed_portfolio_value: Decimal | None
    sync_priority: int
    created_at: datetime


class ScoreComponentsOut(ApiModel):
    """Every component of the Adjusted Tennis Skill Score, for explainability."""

    copyable_roi: float
    profit_factor: float
    sample_confidence: float
    consistency: float
    drawdown: float
    recency: float
    liquidity_fit: float
    concentration: float
    data_quality: float


class WalletScoreOut(ApiModel):
    skill_score: float
    base_score: float
    components: ScoreComponentsOut
    penalties_applied: dict[str, float] = Field(default_factory=dict)
    total_penalty_multiplier: float
    risk_flags: list[str] = Field(default_factory=list)
    qualified: bool
    disqualification_reasons: list[str] = Field(default_factory=list)
    confidence_level: str
    explanation: str | None
    formula_version: str
    computed_at: datetime


class WalletMetricsOut(ApiModel):
    scope: str
    total_positions: int
    completed_positions: int
    open_positions: int
    volume_usdc: Decimal
    capital_deployed: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal

    roi: float | None
    # Equal-weighted per-trade ROI: the figure comparable to copyable ROI.
    roi_equal_weighted: float | None = None
    win_rate: float | None
    profit_factor: float | None
    avg_profit_per_trade: Decimal | None
    median_profit_per_trade: Decimal | None
    expected_value_per_dollar: float | None
    avg_entry_price: Decimal | None
    avg_holding_seconds: int | None

    max_drawdown: float | None
    max_drawdown_usdc: Decimal | None
    longest_win_streak: int
    longest_loss_streak: int
    pct_profit_from_largest_trade: float | None
    pct_profit_from_top5_trades: float | None
    sharpe_like: float | None

    benchmark_delay_seconds: int | None
    copyable_roi: float | None
    copyable_win_rate: float | None
    copyable_net_profit: Decimal | None
    copyable_profit_factor: float | None
    avg_copyability_score: float | None
    copyable_coverage: float | None
    roi_by_delay: dict[str, Any] = Field(default_factory=dict)

    roi_ci_low: float | None
    roi_ci_high: float | None
    copyable_roi_ci_low: float | None
    copyable_roi_ci_high: float | None
    shrunk_copyable_roi: float | None
    prob_positive_edge: float | None
    sample_confidence: float | None
    data_quality_score: float | None

    performance_by_market_type: dict[str, Any] = Field(default_factory=dict)
    performance_by_tournament: dict[str, Any] = Field(default_factory=dict)
    performance_by_player: dict[str, Any] = Field(default_factory=dict)
    performance_by_entry_bucket: dict[str, Any] = Field(default_factory=dict)
    performance_by_size_bucket: dict[str, Any] = Field(default_factory=dict)
    performance_by_period: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime


class WalletDetailOut(ApiModel):
    wallet: WalletOut
    score: WalletScoreOut | None
    metrics: dict[str, WalletMetricsOut] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    cluster: ClusterOut | None = None
    behavioural_profile: dict[str, Any] = Field(default_factory=dict)


class RankingRowOut(ApiModel):
    rank: int
    wallet_id: int
    address: str
    nickname: str | None
    skill_score: float
    qualified: bool
    confidence_level: str
    completed_positions: int
    roi: float | None
    copyable_roi: float | None
    shrunk_copyable_roi: float | None
    copyable_coverage: float | None
    net_profit: Decimal | None
    max_drawdown: float | None
    prob_positive_edge: float | None
    last_activity_at: datetime | None
    risk_flags: list[str] = Field(default_factory=list)
    cluster_id: int | None


class RankingOut(ApiModel):
    key: str
    label: str
    description: str
    scope: str
    rows: list[RankingRowOut]
    # Repeated on every ranking so a leaderboard is never read as a recommendation.
    caveat: str


class ClusterMemberOut(ApiModel):
    wallet_id: int
    address: str
    shared_market_count: int
    jaccard_similarity: float
    timing_correlation: float
    size_correlation: float
    coordinated_exit_count: int


class ClusterOut(ApiModel):
    id: int
    label: str
    relation: str
    confidence: float
    evidence: str | None
    member_count: int
    members: list[ClusterMemberOut] = Field(default_factory=list)


# ------------------------------------------------------------------ markets


class OutcomeOut(ApiModel):
    token_id: str
    outcome_index: int
    label: str
    player_name: str | None
    is_winner: bool | None
    last_price: Decimal | None


class MarketOut(ApiModel):
    id: int
    condition_id: str
    slug: str | None
    question: str | None
    is_tennis: bool
    tennis_market_type: str
    sports_market_type_raw: str | None
    classification_confidence: float
    classification_methods: list[str] = Field(default_factory=list)
    classification_notes: str | None
    needs_review: bool
    reviewed_by_human: bool
    period_number: int | None
    game_start_time: datetime | None
    closed: bool
    resolved: bool
    winning_outcome_index: int | None
    accepting_orders: bool
    liquidity: Decimal | None
    volume_24hr: Decimal | None
    spread: Decimal | None
    best_bid: Decimal | None
    best_ask: Decimal | None
    tick_size: Decimal | None
    outcomes: list[OutcomeOut] = Field(default_factory=list)
    tournament: str | None = None
    player_a: str | None = None
    player_b: str | None = None
    surface: str | None = None
    tour: str | None = None
    best_of: int | None = None


class PricePointOut(ApiModel):
    # token_id is required for charting: a binary market has two outcomes whose
    # prices are complements, so plotting them as one series would be nonsense.
    token_id: str
    timestamp: int
    price: Decimal
    kind: str
    size: Decimal | None = None


class MarketDetailOut(ApiModel):
    market: MarketOut
    price_history: list[PricePointOut] = Field(default_factory=list)
    wallet_activity: list[dict[str, Any]] = Field(default_factory=list)
    open_positions: list[dict[str, Any]] = Field(default_factory=list)
    liquidity: dict[str, Any] | None = None
    signals: list[SignalOut] = Field(default_factory=list)
    paper_trades: list[PaperTradeOut] = Field(default_factory=list)


# ------------------------------------------------------------------ positions


class PositionOut(ApiModel):
    id: int
    token_id: str
    condition_id: str | None
    market_question: str | None = None
    outcome_label: str | None = None
    status: str
    tennis_market_type: str
    entry_phase: str
    opened_at: datetime
    closed_at: datetime | None
    first_entry_price: Decimal
    avg_entry_price: Decimal
    avg_exit_price: Decimal | None
    entry_tx_count: int
    accumulated: bool
    partial_exit_count: int
    capital_committed: Decimal
    max_shares: Decimal
    realized_pnl: Decimal
    net_pnl: Decimal | None
    roi: float | None
    is_win: bool | None
    holding_seconds: int | None
    behaviour: str
    flags: list[str] = Field(default_factory=list)
    reconstruction_confidence: float
    pct_of_wallet_capital: float | None
    copyability: list[CopyabilityOut] = Field(default_factory=list)


class CopyabilityOut(ApiModel):
    delay_seconds: int
    wallet_entry_price: Decimal
    price_after_delay: Decimal | None
    estimated_fill_price: Decimal | None
    price_deterioration: Decimal | None
    slippage: Decimal | None
    available_liquidity: Decimal | None
    follower_roi: float | None
    follower_is_win: bool | None
    copyability_score: float
    price_source_quality: str
    data_confidence: float
    notes: str | None


class TransactionOut(ApiModel):
    id: int
    timestamp: int
    occurred_at: datetime
    activity_type: str
    side: str | None
    size: Decimal
    price: Decimal | None
    usdc_size: Decimal | None
    token_id: str | None
    condition_id: str | None
    market_question: str | None = None
    outcome_label: str | None = None
    market_phase: str
    is_tennis: bool
    transaction_hash: str | None


# ------------------------------------------------------------------- signals


class SignalWalletOut(ApiModel):
    wallet_id: int
    address: str
    nickname: str | None
    entry_price: Decimal | None
    position_usdc: Decimal | None
    traded_at: datetime
    skill_score: float | None
    copyable_roi: float | None
    tennis_trade_count: int | None
    cluster_id: int | None
    counted_as_independent: bool
    has_begun_exiting: bool


class SignalOut(ApiModel):
    id: int
    signal_type: str
    status: str
    qualified: bool
    token_id: str
    condition_id: str | None
    outcome_label: str | None
    market_question: str | None = None
    market_phase: str

    first_wallet_trade_at: datetime
    detected_at: datetime
    expires_at: datetime | None
    signal_age_seconds: int | None

    wallet_count: int
    independent_cluster_count: int
    wallet_entry_price_min: Decimal | None
    wallet_entry_price_max: Decimal | None
    wallet_entry_price_median: Decimal | None
    current_price: Decimal | None
    estimated_follower_price: Decimal | None
    price_deterioration: Decimal | None
    available_liquidity: Decimal | None
    spread: Decimal | None
    total_wallet_position_usdc: Decimal | None

    median_skill_score: float | None
    median_copyable_roi: float | None
    copyability_score: float | None
    consensus_score: float | None
    estimated_edge: float | None
    edge_method: str | None
    data_confidence: float | None

    rejection_reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    explanation: str | None
    qualification_detail: list[dict[str, Any]] = Field(default_factory=list)
    wallets: list[SignalWalletOut] = Field(default_factory=list)


# -------------------------------------------------------------- paper trading


class PaperTradeOut(ApiModel):
    id: int
    signal_id: int | None
    token_id: str
    outcome_label: str | None
    market_question: str | None = None
    status: str
    exit_strategy: str
    signal_detected_at: datetime
    execution_delay_seconds: int
    entered_at: datetime | None
    exited_at: datetime | None
    wallet_entry_price: Decimal | None
    reference_price: Decimal | None
    fill_price: Decimal | None
    slippage_applied: Decimal | None
    exit_price: Decimal | None
    exit_reason: str | None
    stake_usdc: Decimal
    shares: Decimal | None
    stake_reduced_for_liquidity: bool
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    roi: float | None
    is_win: bool | None
    wallet_roi: float | None
    roi_gap_vs_wallet: float | None
    price_source_quality: str | None
    data_confidence: float | None
    rejection_reason: str | None
    notes: str | None


class PaperSummaryOut(ApiModel):
    trades: int
    open_trades: int
    closed_trades: int
    wins: int
    losses: int
    total_staked: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    net_pnl: Decimal
    roi: float | None
    win_rate: float | None
    rejected: int
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    avg_roi_gap_vs_wallet: float | None
    disclaimer: str


# ---------------------------------------------------------------- backtesting


class BacktestCreate(BaseModel):
    name: str = Field(..., max_length=200)
    period_start: datetime
    period_end: datetime
    delay_seconds: int = 15
    slippage_bps: int = 150
    fee_bps: int = 0
    stake_usdc: Decimal = Decimal("5")
    exit_strategy: str = "hold_to_resolution"
    min_wallet_trades: int = 30
    min_wallet_score: float = 75.0
    min_copyable_roi: float = 0.0
    max_price_deterioration: Decimal = Decimal("0.03")
    min_liquidity_usdc: Decimal = Decimal("500")
    min_copyability: float = 60.0
    consensus_required: int = 1
    wallet_ids: list[int] = Field(default_factory=list)
    train_fraction: float = 0.5
    validation_fraction: float = 0.25

    @field_validator("period_end")
    @classmethod
    def _validate_period(cls, v: datetime, info: Any) -> datetime:
        start = info.data.get("period_start")
        if start is not None and v <= start:
            raise ValueError("period_end must be after period_start")
        return v

    @field_validator("delay_seconds")
    @classmethod
    def _warn_zero_delay(cls, v: int) -> int:
        if v < 0:
            raise ValueError("delay_seconds cannot be negative")
        return v


class BacktestTradeOut(ApiModel):
    wallet_id: int | None
    token_id: str
    decision_at: datetime
    entered_at: datetime | None
    exited_at: datetime | None
    wallet_entry_price: Decimal | None
    fill_price: Decimal | None
    exit_price: Decimal | None
    stake_usdc: Decimal | None
    pnl: Decimal | None
    roi: float | None
    is_win: bool | None
    exit_reason: str | None
    market_type: str | None
    market_phase: str | None
    copyability_score: float | None
    price_source_quality: str | None
    split: str | None
    decision_inputs: dict[str, Any] = Field(default_factory=dict)


class BacktestRunOut(ApiModel):
    id: int
    name: str
    status: str
    progress_pct: float
    config: dict[str, Any] = Field(default_factory=dict)
    period_start: datetime
    period_end: datetime
    delay_seconds: int

    total_trades: int
    wins: int
    losses: int
    total_staked: Decimal | None
    total_pnl: Decimal | None
    total_return: float | None
    win_rate: float | None
    profit_factor: float | None
    max_drawdown: float | None
    avg_trade_pnl: Decimal | None
    median_trade_pnl: Decimal | None
    sharpe_like: float | None

    in_sample_return: float | None
    validation_return: float | None
    out_of_sample_return: float | None
    walk_forward: list[dict[str, Any]] = Field(default_factory=list)

    equity_curve: list[float] = Field(default_factory=list)
    drawdown_curve: list[float] = Field(default_factory=list)
    delay_sensitivity: dict[str, Any] = Field(default_factory=dict)
    outcome_distribution: dict[str, int] = Field(default_factory=dict)
    by_market_type: dict[str, Any] = Field(default_factory=dict)
    by_wallet: dict[str, Any] = Field(default_factory=dict)

    return_ci_low: float | None
    return_ci_high: float | None
    pct_pnl_from_top_trade: float | None
    # Non-zero means the run is not a valid result.
    lookahead_violations: int
    skipped_trades: int
    skip_reasons: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: str | None
    started_at: datetime
    finished_at: datetime | None


# --------------------------------------------------------------- dashboard


class OverviewOut(ApiModel):
    wallets_tracked: int
    wallets_approved: int
    wallets_qualified: int
    tennis_markets_tracked: int
    tennis_markets_open: int
    active_signals: int
    signals_today: int
    qualified_signals_today: int
    rejected_signals_today: int
    paper_open_positions: int
    paper_realized_pnl: Decimal
    paper_unrealized_pnl: Decimal
    paper_win_rate: float | None
    paper_roi: float | None
    median_qualified_copyable_roi: float | None
    current_drawdown: float | None
    last_market_sync: datetime | None
    last_wallet_sync: datetime | None
    benchmark_delay_seconds: int
    disclaimer: str


class HealthOut(ApiModel):
    status: str
    version: str
    environment: str
    database: str
    scheduler_running: bool
    jobs: list[dict[str, Any]] = Field(default_factory=list)
    freshness: dict[str, Any] = Field(default_factory=dict)
    recent_errors: int
    unacknowledged_drift: int
    notification_channels: list[str] = Field(default_factory=list)


class DataQualityOut(ApiModel):
    wallets_tracked: int
    wallets_stale: int
    markets_tracked: int
    markets_needing_review: int
    transactions_total: int
    transactions_unmatched_market: int
    positions_total: int
    positions_low_confidence: int
    price_quality_breakdown: dict[str, int] = Field(default_factory=dict)
    avg_data_confidence: float | None
    warnings: list[str] = Field(default_factory=list)


class SettingsOut(ApiModel):
    """Non-secret configuration. Credentials are never returned."""

    follower_delays_seconds: list[int]
    benchmark_delay_seconds: int
    modeled_slippage_bps: int
    score_weights: dict[str, float]
    alert_thresholds: dict[str, Any]
    consensus_thresholds: dict[str, Any]
    paper_settings: dict[str, Any]
    sync_intervals: dict[str, int]
    notification_channels_configured: list[str]
    min_copyable_data_confidence: float


class SettingUpdate(BaseModel):
    key: str
    value: str


class SystemErrorOut(ApiModel):
    id: int
    severity: str
    category: str
    component: str
    message: str
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    resolved: bool


class IngestionJobOut(ApiModel):
    id: int
    job_type: str
    job_uid: str
    status: str
    target: str | None
    records_fetched: int
    records_inserted: int
    records_skipped_duplicate: int
    records_failed: int
    http_requests: int
    http_retries: int
    rate_limit_events: int
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    error: str | None


class ReportOut(ApiModel):
    period: str
    generated_at: datetime
    wallets_added: int
    wallets_downgraded: list[dict[str, Any]] = Field(default_factory=list)
    new_qualifying_wallets: list[dict[str, Any]] = Field(default_factory=list)
    best_wallets: list[dict[str, Any]] = Field(default_factory=list)
    worst_wallets: list[dict[str, Any]] = Field(default_factory=list)
    alerts_generated: int
    alerts_rejected: int
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    paper_summary: dict[str, Any] = Field(default_factory=dict)
    raw_vs_follower: dict[str, Any] = Field(default_factory=dict)
    delay_impact: dict[str, Any] = Field(default_factory=dict)
    data_quality_issues: list[str] = Field(default_factory=list)
    system_errors: int


class ImportResultOut(ApiModel):
    added: int
    skipped_existing: int
    errors: list[str] = Field(default_factory=list)


class MessageOut(ApiModel):
    message: str
    detail: dict[str, Any] | None = None


# Resolve forward references.
WalletDetailOut.model_rebuild()
MarketDetailOut.model_rebuild()
