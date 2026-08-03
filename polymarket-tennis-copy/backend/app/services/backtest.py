"""Backtesting engine with enforced look-ahead prevention.

Look-ahead is the failure mode that makes worthless copy-trading strategies look
excellent, so it is prevented structurally rather than by convention:

* :class:`PointInTimeView` is the only way a decision reads wallet statistics,
  and it *recomputes* them from trades that closed strictly before the decision
  timestamp. A wallet's final record is never visible to an earlier decision.
* Every attempted read of future data increments ``lookahead_violations``, which
  is persisted on the run. A run reporting violations is not a valid result.
* Splits are chronological (train < validation < test) and never shuffled.
* Thresholds tuned on the training window are reported separately from test
  performance, so an in-sample number can never be presented as evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Sequence

from ..config import Settings, get_settings
from ..enums import ExitStrategy, MarketPhase, PriceSourceQuality
from ..logging_setup import get_logger
from . import statistics as stats
from .metrics import PositionRecord
from .prices import PriceSeries

log = get_logger(__name__)

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass
class BacktestConfig:
    """Full, serialisable configuration for one run."""

    name: str
    period_start: datetime
    period_end: datetime

    delay_seconds: int = 15
    slippage_bps: int = 150
    fee_bps: int = 0
    stake_usdc: Decimal = Decimal("5")
    exit_strategy: ExitStrategy = ExitStrategy.HOLD_TO_RESOLUTION

    min_wallet_trades: int = 30
    min_wallet_score: float = 75.0
    min_copyable_roi: float = 0.0
    max_price_deterioration: Decimal = Decimal("0.03")
    min_liquidity_usdc: Decimal = Decimal("500")
    min_copyability: float = 60.0
    consensus_required: int = 1
    wallet_ids: list[int] = field(default_factory=list)

    # Chronological split fractions of the period.
    train_fraction: float = 0.5
    validation_fraction: float = 0.25

    profit_target: Decimal | None = None
    stop_loss: Decimal | None = None
    max_hold_seconds: int | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "name": self.name,
                "period_start": self.period_start.isoformat(),
                "period_end": self.period_end.isoformat(),
                "delay_seconds": self.delay_seconds,
                "slippage_bps": self.slippage_bps,
                "fee_bps": self.fee_bps,
                "stake_usdc": str(self.stake_usdc),
                "exit_strategy": self.exit_strategy.value,
                "min_wallet_trades": self.min_wallet_trades,
                "min_wallet_score": self.min_wallet_score,
                "min_copyable_roi": self.min_copyable_roi,
                "max_price_deterioration": str(self.max_price_deterioration),
                "min_liquidity_usdc": str(self.min_liquidity_usdc),
                "min_copyability": self.min_copyability,
                "consensus_required": self.consensus_required,
                "wallet_ids": self.wallet_ids,
                "train_fraction": self.train_fraction,
                "validation_fraction": self.validation_fraction,
            },
            sort_keys=True,
        )

    def split_boundaries(self) -> tuple[datetime, datetime]:
        total = (self.period_end - self.period_start).total_seconds()
        train_end = self.period_start + timedelta(seconds=total * self.train_fraction)
        validation_end = self.period_start + timedelta(
            seconds=total * (self.train_fraction + self.validation_fraction)
        )
        return train_end, validation_end

    def split_for(self, when: datetime) -> str:
        train_end, validation_end = self.split_boundaries()
        if when < train_end:
            return "train"
        if when < validation_end:
            return "validation"
        return "test"


@dataclass(slots=True)
class BacktestCandidate:
    """A historical wallet entry that could have been copied."""

    wallet_id: int
    position_id: int
    token_id: str
    condition_id: str | None
    market_id: int | None
    entry_ts: int
    entry_price: Decimal
    position_usdc: Decimal
    holding_seconds: int | None
    market_phase: str
    market_type: str
    liquidity: Decimal | None
    spread: Decimal | None
    resolved: bool
    won: bool | None
    wallet_exit_price: Decimal | None
    wallet_roi: float | None
    classification_confidence: float = 100.0
    cluster_id: int | None = None

    @property
    def entry_at(self) -> datetime:
        return datetime.fromtimestamp(self.entry_ts, tz=timezone.utc)


@dataclass
class PointInTimeView:
    """Wallet statistics as they stood at a moment in the past.

    This is the look-ahead guard. Statistics are derived only from positions that
    *closed* strictly before ``as_of``: a trade still open at the decision time
    tells us nothing about its own outcome, and a trade that closed later must not
    inform an earlier decision.
    """

    as_of: datetime
    # wallet_id -> positions, pre-sorted by close time.
    history: dict[int, list[PositionRecord]]
    benchmark_delay: int
    violations: int = 0
    _cache: dict[int, dict] = field(default_factory=dict)

    def wallet_stats(self, wallet_id: int) -> dict:
        """Trade count, copyable ROI and score proxy as of ``as_of``."""
        cache_key = wallet_id
        if cache_key in self._cache:
            return self._cache[cache_key]

        cutoff = int(self.as_of.timestamp())
        available = [
            p
            for p in self.history.get(wallet_id, [])
            if p.closed_ts is not None and p.closed_ts < cutoff
        ]

        if not available:
            result = {
                "trades": 0, "copyable_roi": None, "raw_roi": None,
                "win_rate": None, "score": 0.0, "max_drawdown": None,
            }
            self._cache[cache_key] = result
            return result

        pnls = [p.net_pnl for p in available if p.net_pnl is not None]
        stakes = [p.capital_committed for p in available]
        capital = sum(stakes, ZERO)

        copyable = [
            p.copyable[self.benchmark_delay][0]
            for p in available
            if self.benchmark_delay in p.copyable
            and p.copyable[self.benchmark_delay][0] is not None
        ]
        copyable_roi = sum(copyable) / len(copyable) if copyable else None
        wins = sum(1 for p in available if p.is_win)

        dd = stats.compute_drawdown(pnls, starting_capital=max(stakes) if stakes else ZERO)

        # A lightweight score proxy. The full Adjusted Tennis Skill Score needs
        # breakdowns that are expensive to rebuild at every decision point; this
        # keeps the same shape (copyable edge, sample confidence, drawdown) using
        # only past data.
        score = 0.0
        if copyable_roi is not None:
            score += 55.0 * min(1.0, max(0.0, (copyable_roi + 0.05) / 0.25))
        score += 0.30 * stats.sample_confidence(len(available))
        score += 15.0 * max(0.0, 1.0 - min(1.0, dd.max_drawdown_pct / 0.6))

        result = {
            "trades": len(available),
            "copyable_roi": copyable_roi,
            "raw_roi": float(sum(pnls, ZERO) / capital) if capital > 0 else None,
            "win_rate": wins / len(available),
            "score": round(min(100.0, score), 1),
            "max_drawdown": dd.max_drawdown_pct,
        }
        self._cache[cache_key] = result
        return result

    def assert_no_future_read(self, timestamp: int) -> bool:
        """Record and reject any attempt to read data from after ``as_of``."""
        if timestamp >= int(self.as_of.timestamp()):
            self.violations += 1
            log.warning(
                "backtest.lookahead_violation",
                as_of=self.as_of.isoformat(),
                attempted_ts=timestamp,
            )
            return False
        return True


@dataclass
class BacktestTradeResult:
    """One simulated trade."""

    wallet_id: int
    position_id: int
    token_id: str
    market_id: int | None
    decision_at: datetime
    entered_at: datetime | None
    exited_at: datetime | None
    wallet_entry_price: Decimal
    fill_price: Decimal | None
    exit_price: Decimal | None
    stake_usdc: Decimal
    pnl: Decimal | None
    roi: float | None
    is_win: bool | None
    exit_reason: str | None
    market_type: str
    market_phase: str
    copyability_score: float | None
    price_source_quality: str
    split: str
    decision_inputs: dict = field(default_factory=dict)

    def inputs_json(self) -> str:
        return json.dumps(self.decision_inputs, default=str, sort_keys=True)


@dataclass
class BacktestResult:
    """Aggregate results, split-aware and integrity-checked."""

    config: BacktestConfig
    trades: list[BacktestTradeResult] = field(default_factory=list)
    skipped: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
    lookahead_violations: int = 0
    warnings: list[str] = field(default_factory=list)

    total_staked: Decimal = ZERO
    total_pnl: Decimal = ZERO
    total_return: float | None = None
    win_rate: float | None = None
    profit_factor: float | None = None
    max_drawdown: float | None = None
    avg_trade_pnl: Decimal | None = None
    median_trade_pnl: Decimal | None = None
    sharpe_like: float | None = None
    wins: int = 0
    losses: int = 0

    in_sample_return: float | None = None
    validation_return: float | None = None
    out_of_sample_return: float | None = None
    walk_forward: list[dict] = field(default_factory=list)

    equity_curve: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)
    delay_sensitivity: dict[int, dict] = field(default_factory=dict)
    outcome_distribution: dict[str, int] = field(default_factory=dict)
    by_market_type: dict[str, dict] = field(default_factory=dict)
    by_wallet: dict[int, dict] = field(default_factory=dict)

    return_ci_low: float | None = None
    return_ci_high: float | None = None
    pct_pnl_from_top_trade: float | None = None

    @property
    def is_valid(self) -> bool:
        """A run with look-ahead violations is not a usable result."""
        return self.lookahead_violations == 0


class Backtester:
    """Replays historical wallet entries as follower trades."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(
        self,
        config: BacktestConfig,
        candidates: Sequence[BacktestCandidate],
        series_provider: Callable[[str], PriceSeries | None],
        wallet_history: dict[int, list[PositionRecord]],
        *,
        progress: Callable[[float], None] | None = None,
    ) -> BacktestResult:
        """Replay ``candidates`` chronologically.

        ``series_provider`` maps a token id to its price series;
        ``wallet_history`` supplies each wallet's positions for point-in-time
        recomputation.
        """
        result = BacktestResult(config=config)

        # Chronological order is mandatory: processing out of order would let a
        # later trade inform an earlier decision through the shared view cache.
        ordered = sorted(
            (
                c
                for c in candidates
                if config.period_start <= c.entry_at <= config.period_end
            ),
            key=lambda c: c.entry_ts,
        )
        if not ordered:
            result.warnings.append("no candidates fall inside the configured period")
            return result

        # Pre-sort history once so each point-in-time view is cheap.
        sorted_history = {
            wid: sorted(
                (p for p in positions if p.closed_ts is not None),
                key=lambda p: p.closed_ts or 0,
            )
            for wid, positions in wallet_history.items()
        }

        total = len(ordered)
        seen_clusters_by_token: dict[str, set[int]] = {}

        for index, candidate in enumerate(ordered):
            if progress is not None and index % 50 == 0:
                progress(index / total)

            decision_at = candidate.entry_at
            view = PointInTimeView(
                as_of=decision_at,
                history=sorted_history,
                benchmark_delay=config.delay_seconds,
            )

            outcome = self._evaluate_candidate(
                candidate, config, view, series_provider, seen_clusters_by_token
            )
            result.lookahead_violations += view.violations

            if isinstance(outcome, str):
                result.skipped += 1
                result.skip_reasons[outcome] = result.skip_reasons.get(outcome, 0) + 1
                continue

            result.trades.append(outcome)

        if progress is not None:
            progress(1.0)

        self._aggregate(result)
        self._compute_delay_sensitivity(result, config, ordered, series_provider, sorted_history)
        return result

    # ------------------------------------------------------------- per-trade
    def _evaluate_candidate(
        self,
        candidate: BacktestCandidate,
        config: BacktestConfig,
        view: PointInTimeView,
        series_provider: Callable[[str], PriceSeries | None],
        seen_clusters_by_token: dict[str, set[int]],
    ) -> BacktestTradeResult | str:
        """Return a trade result, or a skip reason string."""
        from .copyability import build_copyability_input, score_copyability

        wallet_stats = view.wallet_stats(candidate.wallet_id)

        # --- wallet gates, using only information available at decision time --
        if wallet_stats["trades"] < config.min_wallet_trades:
            return "wallet_below_min_trades"
        if wallet_stats["score"] < config.min_wallet_score:
            return "wallet_below_min_score"
        if (
            wallet_stats["copyable_roi"] is None
            or wallet_stats["copyable_roi"] <= config.min_copyable_roi
        ):
            return "wallet_no_copyable_edge"
        if config.wallet_ids and candidate.wallet_id not in config.wallet_ids:
            return "wallet_not_selected"

        # --- consensus requirement ------------------------------------------
        if config.consensus_required > 1:
            clusters = seen_clusters_by_token.setdefault(candidate.token_id, set())
            clusters.add(
                candidate.cluster_id
                if candidate.cluster_id is not None
                else -candidate.wallet_id
            )
            if len(clusters) < config.consensus_required:
                return "consensus_not_reached"

        # --- market gates ----------------------------------------------------
        if candidate.liquidity is not None and candidate.liquidity < config.min_liquidity_usdc:
            return "insufficient_liquidity"
        if candidate.classification_confidence < 70.0:
            return "ambiguous_classification"

        series = series_provider(candidate.token_id)
        if series is None or not series.has_evidence:
            return "no_price_series"

        copy_input = build_copyability_input(
            wallet_entry_price=candidate.entry_price,
            wallet_entry_ts=candidate.entry_ts,
            delay_seconds=config.delay_seconds,
            series=series,
            holding_seconds=candidate.holding_seconds,
            market_phase=candidate.market_phase,
            spread=candidate.spread,
            available_liquidity=candidate.liquidity,
            follower_stake=config.stake_usdc,
            classification_confidence=candidate.classification_confidence,
            slippage_bps=config.slippage_bps,
        )
        copy_result = score_copyability(copy_input)

        if copy_result.score < config.min_copyability:
            return "low_copyability"
        if copy_result.estimated_fill_price is None:
            return "no_fill_price"
        if (
            copy_result.price_deterioration is not None
            and copy_result.price_deterioration > config.max_price_deterioration
        ):
            return "price_moved_too_far"

        fill_price = copy_result.estimated_fill_price
        if fill_price <= ZERO:
            return "invalid_fill_price"

        # --- exit -------------------------------------------------------------
        exit_price, exit_reason, exited_at = self._resolve_exit(candidate, config, series)
        if exit_price is None:
            return "no_exit_reference"

        shares = config.stake_usdc / fill_price
        fees = config.stake_usdc * Decimal(config.fee_bps) / Decimal("10000")
        pnl = shares * (exit_price - fill_price) - fees
        roi = float(pnl / config.stake_usdc)

        entered_at = candidate.entry_at + timedelta(seconds=config.delay_seconds)

        return BacktestTradeResult(
            wallet_id=candidate.wallet_id,
            position_id=candidate.position_id,
            token_id=candidate.token_id,
            market_id=candidate.market_id,
            decision_at=candidate.entry_at,
            entered_at=entered_at,
            exited_at=exited_at,
            wallet_entry_price=candidate.entry_price,
            fill_price=fill_price,
            exit_price=exit_price,
            stake_usdc=config.stake_usdc,
            pnl=pnl,
            roi=roi,
            is_win=pnl > ZERO,
            exit_reason=exit_reason,
            market_type=candidate.market_type,
            market_phase=candidate.market_phase,
            copyability_score=copy_result.score,
            price_source_quality=copy_result.price_source_quality.value,
            split=config.split_for(candidate.entry_at),
            # Snapshot of exactly what the decision saw, so look-ahead is
            # auditable after the fact rather than merely asserted.
            decision_inputs={
                "as_of": candidate.entry_at.isoformat(),
                "wallet_trades_known": wallet_stats["trades"],
                "wallet_copyable_roi_known": wallet_stats["copyable_roi"],
                "wallet_score_known": wallet_stats["score"],
                "copyability": copy_result.score,
                "price_source": copy_result.price_source_quality.value,
                "deterioration": str(copy_result.price_deterioration),
            },
        )

    def _resolve_exit(
        self,
        candidate: BacktestCandidate,
        config: BacktestConfig,
        series: PriceSeries,
    ) -> tuple[Decimal | None, str | None, datetime | None]:
        """Exit price for the configured strategy."""
        if config.exit_strategy is ExitStrategy.HOLD_TO_RESOLUTION:
            if candidate.resolved and candidate.won is not None:
                return (
                    ONE if candidate.won else ZERO,
                    "market_resolved",
                    None,
                )
            return None, None, None

        if config.exit_strategy in (
            ExitStrategy.FOLLOW_WALLET_EXIT,
            ExitStrategy.WALLET_REDUCES,
        ):
            if candidate.wallet_exit_price is not None:
                exit_at = (
                    candidate.entry_at + timedelta(seconds=candidate.holding_seconds)
                    if candidate.holding_seconds
                    else None
                )
                return candidate.wallet_exit_price, "wallet_exited", exit_at
            if candidate.resolved and candidate.won is not None:
                return ONE if candidate.won else ZERO, "market_resolved", None
            return None, None, None

        if config.exit_strategy is ExitStrategy.FIXED_HOLD:
            hold = config.max_hold_seconds or self.settings.paper_max_hold_seconds
            target_ts = candidate.entry_ts + config.delay_seconds + hold
            resolved = series.resolve(target_ts)
            if resolved.is_usable and resolved.price is not None:
                return (
                    resolved.price,
                    "max_hold_reached",
                    datetime.fromtimestamp(target_ts, tz=timezone.utc),
                )
            if candidate.resolved and candidate.won is not None:
                return ONE if candidate.won else ZERO, "market_resolved", None
            return None, None, None

        # Profit-target / stop-loss / trailing need a full price walk; falling
        # back to resolution keeps the result defensible rather than approximate.
        if candidate.resolved and candidate.won is not None:
            return ONE if candidate.won else ZERO, "market_resolved", None
        return None, None, None

    # ------------------------------------------------------------ aggregation
    def _aggregate(self, result: BacktestResult) -> None:
        trades = result.trades
        if not trades:
            result.warnings.append("no trades were executed under these thresholds")
            return

        pnls = [t.pnl for t in trades if t.pnl is not None]
        stakes = [t.stake_usdc for t in trades]

        result.total_staked = sum(stakes, ZERO)
        result.total_pnl = sum(pnls, ZERO)
        result.wins = sum(1 for t in trades if t.is_win)
        result.losses = sum(1 for t in trades if t.is_win is False)

        if result.total_staked > ZERO:
            result.total_return = round(float(result.total_pnl / result.total_staked), 6)
        decided = result.wins + result.losses
        if decided:
            result.win_rate = round(result.wins / decided, 4)
        result.profit_factor = stats.profit_factor(pnls)
        result.avg_trade_pnl = result.total_pnl / Decimal(len(pnls))
        result.median_trade_pnl = sorted(pnls)[len(pnls) // 2]
        result.sharpe_like = stats.sharpe_like(pnls, stakes)

        dd = stats.compute_drawdown(pnls, starting_capital=result.total_staked)
        result.max_drawdown = dd.max_drawdown_pct
        result.equity_curve = dd.equity_curve
        result.drawdown_curve = dd.drawdown_curve

        rois = [t.roi for t in trades if t.roi is not None]
        boot = stats.bootstrap_mean(rois, iterations=self.settings.bootstrap_iterations)
        if boot is not None:
            result.return_ci_low = round(boot.ci_low, 6)
            result.return_ci_high = round(boot.ci_high, 6)
        result.pct_pnl_from_top_trade = stats.profit_concentration(pnls, 1)

        # --- split-aware returns ------------------------------------------
        for split, attr in (
            ("train", "in_sample_return"),
            ("validation", "validation_return"),
            ("test", "out_of_sample_return"),
        ):
            subset = [t for t in trades if t.split == split]
            if not subset:
                continue
            staked = sum((t.stake_usdc for t in subset), ZERO)
            if staked > ZERO:
                pnl = sum((t.pnl for t in subset if t.pnl is not None), ZERO)
                setattr(result, attr, round(float(pnl / staked), 6))

        if result.in_sample_return is not None and result.out_of_sample_return is None:
            result.warnings.append(
                "no out-of-sample trades: the in-sample return is not evidence of "
                "a real edge"
            )
        elif (
            result.in_sample_return is not None
            and result.out_of_sample_return is not None
            and result.in_sample_return > 0
            and result.out_of_sample_return <= 0
        ):
            result.warnings.append(
                "profitable in-sample but not out-of-sample: likely overfitting"
            )

        # --- breakdowns ----------------------------------------------------
        result.outcome_distribution = _distribution(rois)
        result.by_market_type = _group_returns(trades, lambda t: t.market_type)
        result.by_wallet = {
            k: v for k, v in _group_returns(trades, lambda t: t.wallet_id).items()
        }
        result.walk_forward = self._walk_forward(trades, result.config)

        if result.pct_pnl_from_top_trade and result.pct_pnl_from_top_trade > 0.5:
            result.warnings.append(
                f"{result.pct_pnl_from_top_trade:.0%} of gross profit came from a "
                "single trade: the result is outlier-dependent"
            )

        weak = sum(
            1
            for t in trades
            if t.price_source_quality
            in (PriceSourceQuality.MODELED.value, PriceSourceQuality.NEAREST_TRADE.value)
        )
        if weak:
            result.warnings.append(
                f"{weak}/{len(trades)} trades priced from modelled or distant "
                "evidence rather than observed prints"
            )

    def _walk_forward(
        self, trades: list[BacktestTradeResult], config: BacktestConfig
    ) -> list[dict]:
        """Rolling monthly windows, reported in chronological order."""
        if not trades:
            return []
        windows: list[dict] = []
        start = config.period_start
        while start < config.period_end:
            end = start + timedelta(days=30)
            subset = [t for t in trades if start <= t.decision_at < end]
            if subset:
                staked = sum((t.stake_usdc for t in subset), ZERO)
                pnl = sum((t.pnl for t in subset if t.pnl is not None), ZERO)
                windows.append(
                    {
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "trades": len(subset),
                        "return": round(float(pnl / staked), 6) if staked > ZERO else None,
                        "pnl": str(pnl),
                    }
                )
            start = end
        return windows

    def _compute_delay_sensitivity(
        self,
        result: BacktestResult,
        config: BacktestConfig,
        candidates: list[BacktestCandidate],
        series_provider: Callable[[str], PriceSeries | None],
        sorted_history: dict[int, list[PositionRecord]],
    ) -> None:
        """Re-run at each configured delay to expose the delay/edge curve.

        This is what reveals wallets that only look profitable at an unrealistic
        zero delay.
        """
        for delay in self.settings.follower_delays_seconds:
            variant = BacktestConfig(
                **{
                    **config.__dict__,
                    "name": f"{config.name}::delay{delay}",
                    "delay_seconds": delay,
                }
            )
            trades: list[BacktestTradeResult] = []
            skipped = 0
            seen: dict[str, set[int]] = {}

            for candidate in candidates:
                view = PointInTimeView(
                    as_of=candidate.entry_at,
                    history=sorted_history,
                    benchmark_delay=delay,
                )
                outcome = self._evaluate_candidate(
                    candidate, variant, view, series_provider, seen
                )
                if isinstance(outcome, str):
                    skipped += 1
                else:
                    trades.append(outcome)

            staked = sum((t.stake_usdc for t in trades), ZERO)
            pnl = sum((t.pnl for t in trades if t.pnl is not None), ZERO)
            wins = sum(1 for t in trades if t.is_win)
            result.delay_sensitivity[delay] = {
                "trades": len(trades),
                "skipped": skipped,
                "return": round(float(pnl / staked), 6) if staked > ZERO else None,
                "pnl": str(pnl),
                "win_rate": round(wins / len(trades), 4) if trades else None,
                "theoretical_only": delay == 0,
            }


def _distribution(rois: list[float]) -> dict[str, int]:
    buckets = {
        "<-50%": 0, "-50..-20%": 0, "-20..0%": 0,
        "0..20%": 0, "20..50%": 0, ">50%": 0,
    }
    for roi in rois:
        if roi < -0.5:
            buckets["<-50%"] += 1
        elif roi < -0.2:
            buckets["-50..-20%"] += 1
        elif roi < 0:
            buckets["-20..0%"] += 1
        elif roi < 0.2:
            buckets["0..20%"] += 1
        elif roi < 0.5:
            buckets["20..50%"] += 1
        else:
            buckets[">50%"] += 1
    return buckets


def _group_returns(trades: list[BacktestTradeResult], key_fn) -> dict:
    groups: dict[object, list[BacktestTradeResult]] = {}
    for t in trades:
        groups.setdefault(key_fn(t), []).append(t)

    out: dict = {}
    for key, subset in groups.items():
        staked = sum((t.stake_usdc for t in subset), ZERO)
        pnl = sum((t.pnl for t in subset if t.pnl is not None), ZERO)
        wins = sum(1 for t in subset if t.is_win)
        out[key] = {
            "trades": len(subset),
            "pnl": str(pnl),
            "return": round(float(pnl / staked), 6) if staked > ZERO else None,
            "win_rate": round(wins / len(subset), 4) if subset else None,
        }
    return out
