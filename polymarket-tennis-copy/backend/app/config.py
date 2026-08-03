"""Application configuration.

Every tunable threshold named in the product spec lives here so that scoring,
alerting and paper-trading behaviour can be changed without touching logic.
Secrets come from the environment only -- never from code.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    """Runtime configuration, validated at startup."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------------------------------------------- runtime
    app_env: Literal["development", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --------------------------------------------------------------- database
    # SQLite is the local default; set DATABASE_URL to a postgresql+psycopg URL
    # for production.
    database_url: str = f"sqlite:///{(DATA_DIR / 'tennis_copy_trade.db').as_posix()}"
    db_echo: bool = False

    # ------------------------------------------------------------ data source
    gamma_base_url: str = "https://gamma-api.polymarket.com"
    data_api_base_url: str = "https://data-api.polymarket.com"
    clob_base_url: str = "https://clob.polymarket.com"
    leaderboard_base_url: str = "https://lb-api.polymarket.com"

    # Verified 2026-07-29: Gamma tag id for Tennis.
    tennis_tag_id: int = 864
    tennis_tag_slug: str = "tennis"

    http_timeout_seconds: float = 25.0
    http_max_retries: int = 4
    http_backoff_base_seconds: float = 0.75
    http_backoff_max_seconds: float = 20.0
    # Self-imposed throttle: Polymarket exposes no rate-limit headers, so we
    # stay deliberately conservative rather than probing for the ceiling.
    http_requests_per_second: float = 6.0
    http_user_agent: str = "tennis-copy-trade/1.0 (read-only analytics)"

    # Verified: /activity and /trades cap the page size at 500 and 1000.
    activity_page_size: int = 500
    trades_page_size: int = 500
    store_raw_responses: bool = True
    raw_response_retention_days: int = 30

    # --------------------------------------------------------------- ingestion
    sync_interval_seconds: int = 300
    live_sync_interval_seconds: int = 30
    market_refresh_interval_seconds: int = 900
    metrics_recompute_interval_seconds: int = 1800
    wallet_backfill_days: int = 365
    max_wallets_per_sync_cycle: int = 25

    # ------------------------------------------------------- follower delays
    # Seconds. 0 is retained only as a theoretical upper bound and is never the
    # benchmark used for alerting decisions.
    follower_delays_seconds: list[int] = Field(
        default_factory=lambda: [0, 2, 5, 10, 15, 30, 60, 120, 300]
    )
    # The delay used as the headline "could a follower really do this" number.
    benchmark_delay_seconds: int = 15
    # Minimum per-trade data confidence for a copyability row to count toward
    # copyable ROI. Modelled-price rows score ~44 and are excluded: they are
    # assumptions, not measurements, and averaging them into the headline number
    # would manufacture an edge (or erase one) out of nothing. Minute-bar
    # evidence scores ~72 and is kept.
    min_copyable_data_confidence: float = 55.0

    # ------------------------------------------------------------- execution
    # Slippage applied on top of book-walk when depth data is unavailable.
    modeled_slippage_bps: int = 150
    taker_fee_bps: int = 0  # Polymarket taker fees are market-specific; 0 default.
    min_order_size_usdc: Decimal = Decimal("1")

    # ------------------------------------------------------- scoring weights
    # Adjusted Tennis Skill Score component weights. Must sum to 1.0.
    score_weight_copyable_roi: float = 0.25
    score_weight_profit_factor: float = 0.15
    score_weight_sample_confidence: float = 0.15
    score_weight_consistency: float = 0.10
    score_weight_drawdown: float = 0.10
    score_weight_recency: float = 0.10
    score_weight_liquidity_fit: float = 0.05
    score_weight_concentration: float = 0.05
    score_weight_data_quality: float = 0.05

    # Skill-vs-luck controls.
    min_trades_for_full_confidence: int = 100
    min_trades_soft_floor: int = 20
    bayesian_shrinkage_strength: float = 30.0
    bootstrap_iterations: int = 2000
    recency_halflife_days: float = 90.0

    # Penalty magnitudes (multiplicative, applied to the 0-100 score).
    penalty_below_min_trades: float = 0.60
    penalty_high_concentration: float = 0.80
    penalty_severe_drawdown: float = 0.80
    penalty_negative_30d: float = 0.85
    penalty_negative_copyable: float = 0.55
    penalty_market_making: float = 0.65
    penalty_low_liquidity: float = 0.90
    penalty_ambiguous_reconstruction: float = 0.85
    # Favourite-longshot shape: wins small and often, loses big and rarely. The
    # observed record flatters it because the losses that define its risk have
    # barely happened yet.
    penalty_tail_risk_asymmetry: float = 0.80

    # ---------------------------------------------------- alert qualification
    alert_min_tennis_trades: int = 30
    alert_min_skill_score: float = 75.0
    alert_min_copyable_roi: float = 0.0
    alert_min_data_confidence: float = 80.0
    alert_max_drawdown: float = 0.40
    alert_max_price_deterioration: Decimal = Decimal("0.03")
    alert_min_liquidity_usdc: Decimal = Decimal("500")
    alert_max_spread: Decimal = Decimal("0.05")
    alert_max_age_live_seconds: int = 60
    alert_max_age_prematch_seconds: int = 600
    alert_min_copyability_score: float = 60.0
    alert_min_position_usdc: Decimal = Decimal("100")

    # Consensus alerts.
    consensus_min_wallets: int = 3
    consensus_min_independent_clusters: int = 2
    consensus_window_seconds: int = 90
    consensus_min_median_skill: float = 70.0
    consensus_min_median_copyability: float = 70.0
    consensus_max_price_deterioration: Decimal = Decimal("0.04")

    # ------------------------------------------------------ clustering limits
    cluster_min_shared_markets: int = 4
    cluster_jaccard_threshold: float = 0.55
    cluster_timing_window_seconds: int = 120
    cluster_timing_ratio_threshold: float = 0.50

    # --------------------------------------------------------- paper trading
    paper_trading_enabled: bool = True
    paper_execution_delay_seconds: int = 15
    paper_stake_usdc: Decimal = Decimal("5")
    paper_max_exposure_per_market_usdc: Decimal = Decimal("20")
    paper_max_total_exposure_usdc: Decimal = Decimal("50")
    paper_max_open_positions: int = 10
    paper_daily_loss_cap_usdc: Decimal = Decimal("25")
    paper_default_exit_strategy: str = "hold_to_resolution"
    paper_profit_target: Decimal = Decimal("0.25")
    paper_stop_loss: Decimal = Decimal("0.40")
    paper_max_hold_seconds: int = 86_400
    paper_allow_duplicate_signals: bool = False

    # --------------------------------------------------------- notifications
    discord_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    notifications_enabled: bool = True

    # ---------------------------------------------------------------- helpers
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("follower_delays_seconds", mode="before")
    @classmethod
    def _split_delays(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [int(p.strip()) for p in v.split(",") if p.strip()]
        return v

    @field_validator("follower_delays_seconds")
    @classmethod
    def _sorted_unique_delays(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("follower_delays_seconds must not be empty")
        if any(d < 0 for d in v):
            raise ValueError("follower delays must be non-negative")
        return sorted(set(v))

    @model_validator(mode="after")
    def _validate_consistency(self) -> Settings:
        weights = self.score_weights
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Adjusted Tennis Skill Score weights must sum to 1.0, got {total:.6f}"
            )
        if self.benchmark_delay_seconds not in self.follower_delays_seconds:
            raise ValueError(
                f"benchmark_delay_seconds={self.benchmark_delay_seconds} must be one of "
                f"follower_delays_seconds={self.follower_delays_seconds}"
            )
        if self.benchmark_delay_seconds == 0:
            raise ValueError(
                "benchmark_delay_seconds must be greater than 0: a zero-delay "
                "benchmark is not achievable by a real follower."
            )
        if self.paper_max_exposure_per_market_usdc > self.paper_max_total_exposure_usdc:
            raise ValueError(
                "paper_max_exposure_per_market_usdc cannot exceed "
                "paper_max_total_exposure_usdc"
            )
        if self.paper_stake_usdc <= 0:
            raise ValueError("paper_stake_usdc must be positive")
        return self

    @property
    def score_weights(self) -> dict[str, float]:
        """Component weights for the Adjusted Tennis Skill Score."""
        return {
            "copyable_roi": self.score_weight_copyable_roi,
            "profit_factor": self.score_weight_profit_factor,
            "sample_confidence": self.score_weight_sample_confidence,
            "consistency": self.score_weight_consistency,
            "drawdown": self.score_weight_drawdown,
            "recency": self.score_weight_recency,
            "liquidity_fit": self.score_weight_liquidity_fit,
            "concentration": self.score_weight_concentration,
            "data_quality": self.score_weight_data_quality,
        }

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def configured_notification_channels(self) -> list[str]:
        """Channels with enough configuration to actually deliver."""
        channels = ["in_app"]
        if self.discord_webhook_url:
            channels.append("discord")
        if self.telegram_bot_token and self.telegram_chat_id:
            channels.append("telegram")
        if self.smtp_host and self.smtp_from and self.smtp_to:
            channels.append("email")
        return channels


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Raises a readable error on bad configuration."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()


def reset_settings_cache() -> None:
    """Test hook: forget cached settings so env changes take effect."""
    get_settings.cache_clear()
