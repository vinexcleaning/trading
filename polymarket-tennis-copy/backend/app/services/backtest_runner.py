"""Database glue for the backtester.

The :mod:`backtest` module is deliberately pure -- it takes candidates, a price
lookup and wallet history, and returns a result. This module loads those inputs
from the database and persists what comes back.

One rule is enforced here rather than left to the caller: liquidity and spread
attached to a candidate are read from the *historical* snapshot nearest the entry
time when one exists. Falling back to the market's current liquidity column would
quietly hand a 2026 order book to a 2025 decision, which is look-ahead by a less
obvious route than reading a future price.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..enums import ExitStrategy, JobStatus
from ..logging_setup import get_logger
from ..models import (
    BacktestRun,
    BacktestTrade,
    LiquiditySnapshot,
    Market,
    Outcome,
    ReconstructedPosition,
    Wallet,
)
from .backtest import BacktestCandidate, BacktestConfig, Backtester, BacktestResult
from .ingest import build_price_series
from .pipeline import AnalyticsPipeline

log = get_logger(__name__)


class BacktestRunner:
    """Creates, executes and persists backtest runs."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        # Candidates for which no historical order-book snapshot exists.
        self._candidates_without_depth = 0

    # ---------------------------------------------------------------- create
    def create_run(self, config: BacktestConfig) -> BacktestRun:
        """Persist a queued run so its id can be polled immediately."""
        train_end, validation_end = config.split_boundaries()
        run = BacktestRun(
            name=config.name,
            status=JobStatus.RUNNING,
            config_json=config.to_json(),
            delay_seconds=config.delay_seconds,
            slippage_bps=config.slippage_bps,
            fee_bps=config.fee_bps,
            exit_strategy=config.exit_strategy.value,
            stake_usdc=config.stake_usdc,
            consensus_required=config.consensus_required,
            period_start=config.period_start,
            period_end=config.period_end,
            train_end=train_end,
            validation_end=validation_end,
            progress_pct=0.0,
        )
        self.session.add(run)
        self.session.flush()
        return run

    # --------------------------------------------------------------- execute
    def execute(self, run: BacktestRun, config: BacktestConfig) -> BacktestRun:
        """Run the replay and store the outcome."""
        try:
            candidates = self._load_candidates(config)
            history = self._wallet_history(config, candidates)

            def progress(fraction: float) -> None:
                run.progress_pct = round(min(100.0, max(0.0, fraction * 100)), 1)
                self.session.flush()

            result = Backtester(self.settings).run(
                config,
                candidates,
                self._series_provider(),
                history,
                progress=progress,
            )

            if self._candidates_without_depth:
                # The minimum-liquidity gate cannot fire without depth data, so
                # those candidates cleared it by default. Say so rather than
                # letting the run imply the constraint was tested everywhere.
                share = self._candidates_without_depth / max(len(candidates), 1)
                result.warnings.append(
                    f"{self._candidates_without_depth} of {len(candidates)} candidates "
                    f"({share:.0%}) had no historical order-book snapshot; the "
                    f"min_liquidity_usdc={config.min_liquidity_usdc} gate was not "
                    "applied to them (copyability still scored their depth as unknown)"
                )

            self._persist_result(run, result)
            run.status = JobStatus.SUCCESS if result.is_valid else JobStatus.FAILED
            if not result.is_valid:
                run.error = (
                    f"{result.lookahead_violations} look-ahead violation(s) detected; "
                    "results are not usable"
                )
        except Exception as exc:  # noqa: BLE001 - the run records its own failure
            run.status = JobStatus.FAILED
            run.error = str(exc)[:4000]
            log.exception("backtest.failed", run_id=run.id)
        finally:
            run.finished_at = datetime.now(timezone.utc)
            run.progress_pct = 100.0
        return run

    # ------------------------------------------------------------ input load
    def _load_candidates(self, config: BacktestConfig) -> list[BacktestCandidate]:
        query = (
            select(ReconstructedPosition, Market, Outcome)
            .join(Market, Market.id == ReconstructedPosition.market_id)
            .outerjoin(Outcome, Outcome.token_id == ReconstructedPosition.token_id)
            .where(
                ReconstructedPosition.is_tennis.is_(True),
                ReconstructedPosition.opened_at >= config.period_start,
                ReconstructedPosition.opened_at <= config.period_end,
            )
        )
        if config.wallet_ids:
            query = query.where(ReconstructedPosition.wallet_id.in_(config.wallet_ids))

        rows = list(self.session.execute(query.order_by(ReconstructedPosition.opened_ts)))
        cluster_by_wallet = {
            wid: cid
            for wid, cid in self.session.execute(
                select(Wallet.id, Wallet.suspected_cluster_id)
            )
        }

        candidates: list[BacktestCandidate] = []
        for position, market, outcome in rows:
            won: bool | None = None
            if market.resolved:
                if outcome is not None and outcome.is_winner is not None:
                    won = outcome.is_winner
                elif market.winning_outcome_index is not None and position.outcome_index is not None:
                    won = market.winning_outcome_index == position.outcome_index

            liquidity, spread = self._historical_liquidity(position.token_id, position.opened_ts)

            candidates.append(
                BacktestCandidate(
                    wallet_id=position.wallet_id,
                    position_id=position.id,
                    token_id=position.token_id,
                    condition_id=position.condition_id,
                    market_id=position.market_id,
                    entry_ts=position.opened_ts,
                    entry_price=position.avg_entry_price,
                    position_usdc=position.capital_committed,
                    holding_seconds=position.holding_seconds,
                    market_phase=position.entry_phase,
                    market_type=position.tennis_market_type,
                    liquidity=liquidity,
                    spread=spread,
                    resolved=bool(market.resolved),
                    won=won,
                    wallet_exit_price=position.avg_exit_price,
                    wallet_roi=position.roi,
                    classification_confidence=market.classification_confidence,
                    cluster_id=cluster_by_wallet.get(position.wallet_id),
                )
            )
        return candidates

    def _historical_liquidity(
        self, token_id: str, entry_ts: int
    ) -> tuple[Decimal | None, Decimal | None]:
        """Depth and spread as they stood at (or just before) the entry."""
        snapshot = self.session.scalar(
            select(LiquiditySnapshot)
            .where(
                LiquiditySnapshot.token_id == token_id,
                LiquiditySnapshot.timestamp <= entry_ts,
            )
            .order_by(LiquiditySnapshot.timestamp.desc())
            .limit(1)
        )
        if snapshot is None:
            # No historical depth: report absence rather than substituting a
            # present-day figure the decision could not have seen.
            self._candidates_without_depth += 1
            return None, None
        liquidity = (
            snapshot.ask_depth_5c_usdc
            if snapshot.ask_depth_5c_usdc is not None
            else snapshot.ask_depth_usdc
        )
        return liquidity, snapshot.spread

    def _wallet_history(
        self, config: BacktestConfig, candidates: list[BacktestCandidate]
    ) -> dict[int, list]:
        """Full position history per wallet, for point-in-time recomputation."""
        wallet_ids = set(config.wallet_ids) | {c.wallet_id for c in candidates}
        if not wallet_ids:
            return {}
        pipeline = AnalyticsPipeline(self.session, self.settings)
        history: dict[int, list] = {}
        for wallet in self.session.scalars(select(Wallet).where(Wallet.id.in_(wallet_ids))):
            history[wallet.id] = pipeline.build_position_records(wallet)
        return history

    def _series_provider(self):
        cache: dict[str, object] = {}

        def provider(token_id: str):
            if token_id not in cache:
                series = build_price_series(self.session, token_id)
                cache[token_id] = series if series.has_evidence else None
            return cache[token_id]

        return provider

    # -------------------------------------------------------------- persist
    def _persist_result(self, run: BacktestRun, result: BacktestResult) -> None:
        run.total_trades = len(result.trades)
        run.wins = result.wins
        run.losses = result.losses
        run.total_staked = result.total_staked
        run.total_pnl = result.total_pnl
        run.total_return = result.total_return
        run.win_rate = result.win_rate
        run.profit_factor = result.profit_factor
        run.max_drawdown = result.max_drawdown
        run.avg_trade_pnl = result.avg_trade_pnl
        run.median_trade_pnl = result.median_trade_pnl
        run.sharpe_like = result.sharpe_like
        run.in_sample_return = result.in_sample_return
        run.validation_return = result.validation_return
        run.out_of_sample_return = result.out_of_sample_return
        run.walk_forward_json = json.dumps(result.walk_forward, default=str)
        run.equity_curve_json = json.dumps(result.equity_curve)
        run.drawdown_curve_json = json.dumps(result.drawdown_curve)
        run.delay_sensitivity_json = json.dumps(
            {str(k): v for k, v in result.delay_sensitivity.items()}, default=str
        )
        run.outcome_distribution_json = json.dumps(result.outcome_distribution)
        run.by_market_type_json = json.dumps(result.by_market_type, default=str)
        run.by_wallet_json = json.dumps(
            {str(k): v for k, v in result.by_wallet.items()}, default=str
        )
        run.return_ci_low = result.return_ci_low
        run.return_ci_high = result.return_ci_high
        run.pct_pnl_from_top_trade = result.pct_pnl_from_top_trade
        run.lookahead_violations = result.lookahead_violations
        run.skipped_trades = result.skipped
        run.skip_reasons_json = json.dumps(result.skip_reasons)
        run.data_quality_warnings = json.dumps(result.warnings)

        for trade in result.trades:
            self.session.add(
                BacktestTrade(
                    run_id=run.id,
                    wallet_id=trade.wallet_id,
                    market_id=trade.market_id,
                    position_id=trade.position_id,
                    token_id=trade.token_id,
                    decision_at=trade.decision_at,
                    entered_at=trade.entered_at,
                    exited_at=trade.exited_at,
                    wallet_entry_price=trade.wallet_entry_price,
                    fill_price=trade.fill_price,
                    exit_price=trade.exit_price,
                    stake_usdc=trade.stake_usdc,
                    pnl=trade.pnl,
                    roi=trade.roi,
                    is_win=trade.is_win,
                    exit_reason=trade.exit_reason,
                    market_type=trade.market_type,
                    market_phase=trade.market_phase,
                    copyability_score=trade.copyability_score,
                    price_source_quality=trade.price_source_quality,
                    split=trade.split,
                    decision_inputs_json=trade.inputs_json(),
                )
            )


def config_from_payload(payload, settings: Settings | None = None) -> BacktestConfig:
    """Build a :class:`BacktestConfig` from the API request model."""
    s = settings or get_settings()
    try:
        strategy = ExitStrategy(payload.exit_strategy)
    except ValueError as exc:
        raise ValueError(
            f"unknown exit_strategy '{payload.exit_strategy}'; expected one of "
            f"{[e.value for e in ExitStrategy]}"
        ) from exc

    start = payload.period_start
    end = payload.period_end
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    return BacktestConfig(
        name=payload.name,
        period_start=start,
        period_end=end,
        delay_seconds=payload.delay_seconds,
        slippage_bps=payload.slippage_bps,
        fee_bps=payload.fee_bps,
        stake_usdc=payload.stake_usdc,
        exit_strategy=strategy,
        min_wallet_trades=payload.min_wallet_trades,
        min_wallet_score=payload.min_wallet_score,
        min_copyable_roi=payload.min_copyable_roi,
        max_price_deterioration=payload.max_price_deterioration,
        min_liquidity_usdc=payload.min_liquidity_usdc,
        min_copyability=payload.min_copyability,
        consensus_required=payload.consensus_required,
        wallet_ids=list(payload.wallet_ids),
        train_fraction=payload.train_fraction,
        validation_fraction=payload.validation_fraction,
        profit_target=s.paper_profit_target,
        stop_loss=s.paper_stop_loss,
        max_hold_seconds=s.paper_max_hold_seconds,
    )
