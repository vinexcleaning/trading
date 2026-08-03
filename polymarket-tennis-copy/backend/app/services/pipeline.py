"""Analytics pipeline: transactions -> positions -> copyability -> metrics -> scores.

Each stage is separately runnable and idempotent, so a failure part-way through
leaves consistent state and a re-run repairs it rather than double-counting.

Stage order matters and is enforced by data dependency:

    reconstruct  ->  copyability  ->  metrics  ->  scores  ->  clusters

The population prior used for Bayesian shrinkage is computed across all wallets
*before* individual scores, so every wallet is shrunk toward the same reference.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..enums import PositionStatus, TennisMarketType
from ..logging_setup import get_logger
from ..models import (
    Market,
    NormalizedTransaction,
    Outcome,
    PositionLot,
    ReconstructedPosition,
    TradeCopyability,
    Wallet,
    WalletCluster,
    WalletClusterMember,
    WalletMetricHistory,
    WalletMetrics,
    WalletScore,
)
from .clustering import WalletActivitySignature, WalletClusterer
from .copyability import build_copyability_input, compute_follower_outcome, score_copyability
from .ingest import build_price_series
from .metrics import (
    MetricSet,
    PositionRecord,
    compute_scope_metrics,
    population_mean_copyable_roi,
)
from .reconstruction import (
    AccountingMethod,
    MarketContext,
    ReconstructedPositionData,
    TradeReconstructor,
    TxInput,
)
from .scoring import WalletScorer

log = get_logger(__name__)

ZERO = Decimal("0")


@dataclass
class PipelineStats:
    wallets_processed: int = 0
    positions_written: int = 0
    copyability_rows: int = 0
    metrics_written: int = 0
    scores_written: int = 0
    clusters_written: int = 0
    errors: list[str] = field(default_factory=list)


class AnalyticsPipeline:
    """Runs the analytics stages over the database."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    # -------------------------------------------------------- reconstruction
    def reconstruct_wallet(
        self,
        wallet: Wallet,
        *,
        accounting_method: AccountingMethod | None = None,
    ) -> int:
        """Rebuild all positions for one wallet.

        Existing positions are deleted and rebuilt rather than incrementally
        patched: reconstruction is cheap, and a full rebuild removes any chance of
        a partially-updated position double-counting a lot.
        """
        method = accounting_method or "fifo"

        transactions = list(
            self.session.scalars(
                select(NormalizedTransaction)
                .where(
                    NormalizedTransaction.wallet_id == wallet.id,
                    NormalizedTransaction.token_id.is_not(None),
                )
                .order_by(NormalizedTransaction.timestamp)
            )
        )
        if not transactions:
            return 0

        contexts = self._market_contexts(
            {t.condition_id for t in transactions if t.condition_id}
        )
        token_outcome_index = self._token_outcome_indexes(
            {t.token_id for t in transactions if t.token_id}
        )

        tx_inputs = [
            TxInput(
                id=t.id,
                timestamp=t.timestamp,
                activity_type=t.activity_type,
                size=t.size,
                side=t.side,
                price=t.price,
                usdc_size=t.usdc_size,
                fee_usdc=t.fee_usdc,
                token_id=t.token_id or "",
                condition_id=t.condition_id,
                outcome_index=t.outcome_index,
                market_phase=t.market_phase,
                transaction_hash=t.transaction_hash,
            )
            for t in transactions
        ]

        reconstructor = TradeReconstructor(method)
        positions = reconstructor.reconstruct(
            tx_inputs,
            contexts,
            token_outcome_index=token_outcome_index,
            wallet_portfolio_value=wallet.observed_portfolio_value,
        )

        # Cascade removes lots and copyability rows.
        self.session.execute(
            delete(ReconstructedPosition).where(
                ReconstructedPosition.wallet_id == wallet.id
            )
        )
        self.session.flush()

        market_ids = self._market_ids(contexts)
        outcome_ids = self._outcome_ids({p.token_id for p in positions})

        written = 0
        for data in positions:
            ctx = contexts.get(data.condition_id or "")
            row = self._to_orm_position(wallet, data, ctx, market_ids, outcome_ids)
            self.session.add(row)
            self.session.flush()
            for lot in data.lots:
                self.session.add(
                    PositionLot(
                        position_id=row.id,
                        transaction_id=lot.transaction_id,
                        lot_index=lot.lot_index,
                        acquired_ts=lot.acquired_ts,
                        acquired_at=datetime.fromtimestamp(
                            lot.acquired_ts, tz=timezone.utc
                        ),
                        shares=lot.shares,
                        shares_remaining=lot.shares_remaining,
                        entry_price=lot.entry_price,
                        cost_basis=lot.cost_basis,
                        realized_pnl=lot.realized_pnl,
                        fully_consumed=lot.fully_consumed,
                    )
                )
            written += 1

        self.session.flush()
        return written

    def _to_orm_position(
        self,
        wallet: Wallet,
        data: ReconstructedPositionData,
        ctx: MarketContext | None,
        market_ids: dict[str, int],
        outcome_ids: dict[str, int],
    ) -> ReconstructedPosition:
        pct_capital: float | None = None
        if wallet.observed_portfolio_value and wallet.observed_portfolio_value > ZERO:
            pct_capital = float(
                data.max_capital_at_risk / wallet.observed_portfolio_value
            )

        return ReconstructedPosition(
            wallet_id=wallet.id,
            market_id=market_ids.get(data.condition_id or ""),
            outcome_id=outcome_ids.get(data.token_id),
            token_id=data.token_id,
            condition_id=data.condition_id,
            outcome_index=data.outcome_index,
            sequence=data.sequence,
            status=data.status,
            accounting_method=data.accounting_method,
            opened_at=datetime.fromtimestamp(data.opened_ts, tz=timezone.utc),
            opened_ts=data.opened_ts,
            first_entry_price=data.first_entry_price,
            avg_entry_price=data.avg_entry_price,
            entry_tx_count=data.entry_tx_count,
            accumulated=data.accumulated,
            scaled_in_at_worse_prices=data.scaled_in_at_worse_prices,
            closed_at=(
                datetime.fromtimestamp(data.closed_ts, tz=timezone.utc)
                if data.closed_ts
                else None
            ),
            closed_ts=data.closed_ts,
            avg_exit_price=data.avg_exit_price,
            exit_tx_count=data.exit_tx_count,
            partial_exit_count=data.partial_exit_count,
            settled_by_redemption=data.settled_by_redemption,
            total_shares_bought=data.total_shares_bought,
            total_shares_sold=data.total_shares_sold,
            current_shares=data.current_shares,
            max_shares=data.max_shares,
            capital_committed=data.capital_committed,
            max_capital_at_risk=data.max_capital_at_risk,
            pct_of_wallet_capital=pct_capital,
            realized_pnl=data.realized_pnl,
            gross_pnl=data.realized_pnl,
            fees_paid=data.fees_paid,
            net_pnl=data.net_pnl,
            roi=data.roi,
            is_win=data.is_win,
            holding_seconds=data.holding_seconds,
            entry_phase=data.entry_phase,
            tennis_market_type=(
                ctx.tennis_market_type if ctx else TennisMarketType.UNKNOWN
            ),
            is_tennis=bool(ctx and ctx.is_tennis),
            behaviour=data.behaviour,
            flags=data.flags_json(),
            held_both_outcomes=data.held_both_outcomes,
            reconstruction_confidence=data.reconstruction_confidence,
            reconstruction_notes=data.notes_text(),
        )

    # ------------------------------------------------------------ copyability
    def compute_copyability(self, wallet: Wallet, *, only_tennis: bool = True) -> int:
        """Compute per-delay follower analysis for a wallet's positions."""
        query = select(ReconstructedPosition).where(
            ReconstructedPosition.wallet_id == wallet.id
        )
        if only_tennis:
            query = query.where(ReconstructedPosition.is_tennis.is_(True))
        positions = list(self.session.scalars(query))
        if not positions:
            return 0

        contexts = self._market_contexts(
            {p.condition_id for p in positions if p.condition_id}
        )
        market_rows = {
            m.condition_id: m
            for m in self.session.scalars(
                select(Market).where(
                    Market.condition_id.in_(
                        [p.condition_id for p in positions if p.condition_id]
                    )
                )
            )
        }

        # Cache series per token: several positions can share one token.
        series_cache: dict[str, object] = {}
        written = 0

        for position in positions:
            series = series_cache.get(position.token_id)
            if series is None:
                series = build_price_series(self.session, position.token_id)
                series_cache[position.token_id] = series

            ctx = contexts.get(position.condition_id or "")
            market = market_rows.get(position.condition_id or "")

            resolved_winner: bool | None = None
            if ctx and ctx.resolved and ctx.winning_outcome_index is not None:
                if position.outcome_index is not None:
                    resolved_winner = position.outcome_index == ctx.winning_outcome_index

            self.session.execute(
                delete(TradeCopyability).where(
                    TradeCopyability.position_id == position.id
                )
            )

            for delay in self.settings.follower_delays_seconds:
                data = build_copyability_input(
                    wallet_entry_price=position.first_entry_price,
                    wallet_entry_ts=position.opened_ts,
                    delay_seconds=delay,
                    series=series,
                    holding_seconds=position.holding_seconds,
                    market_phase=position.entry_phase,
                    spread=market.spread if market else None,
                    available_liquidity=market.liquidity if market else None,
                    classification_confidence=(
                        market.classification_confidence if market else 100.0
                    ),
                    slippage_bps=self.settings.modeled_slippage_bps,
                )
                result = score_copyability(data)

                follower = None
                if result.estimated_fill_price is not None:
                    follower = compute_follower_outcome(
                        result.estimated_fill_price,
                        wallet_exit_price=position.avg_exit_price,
                        resolved_winner=resolved_winner,
                        stake_usdc=self.settings.paper_stake_usdc,
                        fee_bps=self.settings.taker_fee_bps,
                    )

                self.session.add(
                    TradeCopyability(
                        position_id=position.id,
                        delay_seconds=delay,
                        wallet_entry_price=position.first_entry_price,
                        price_before=(
                            data.price_before.price if data.price_before else None
                        ),
                        price_after_delay=result.market_price_after_delay,
                        estimated_fill_price=result.estimated_fill_price,
                        price_deterioration=result.price_deterioration,
                        price_deterioration_pct=result.price_deterioration_pct,
                        slippage=result.slippage,
                        spread_at_entry=market.spread if market else None,
                        available_liquidity=market.liquidity if market else None,
                        follower_exit_price=follower.exit_price if follower else None,
                        follower_pnl=follower.pnl if follower else None,
                        follower_roi=follower.roi if follower else None,
                        follower_is_win=follower.is_win if follower else None,
                        copyability_score=result.score,
                        copyability_components=result.components_json(),
                        price_source_quality=result.price_source_quality.value,
                        data_confidence=result.data_confidence,
                        notes=result.notes_text(),
                    )
                )
                written += 1

        self.session.flush()
        return written

    # ---------------------------------------------------------------- metrics
    def build_position_records(self, wallet: Wallet) -> list[PositionRecord]:
        """Flatten a wallet's positions into metric inputs."""
        positions = list(
            self.session.scalars(
                select(ReconstructedPosition).where(
                    ReconstructedPosition.wallet_id == wallet.id
                )
            )
        )
        if not positions:
            return []

        position_ids = [p.id for p in positions]
        copy_rows: dict[int, dict[int, tuple]] = {}
        for row in self.session.scalars(
            select(TradeCopyability).where(
                TradeCopyability.position_id.in_(position_ids)
            )
        ):
            copy_rows.setdefault(row.position_id, {})[row.delay_seconds] = (
                row.follower_roi,
                row.follower_pnl,
                row.follower_is_win,
                row.copyability_score,
                row.data_confidence,
            )

        market_rows = {
            m.id: m
            for m in self.session.scalars(
                select(Market).where(
                    Market.id.in_([p.market_id for p in positions if p.market_id])
                )
            )
        }
        outcome_rows = {
            o.id: o
            for o in self.session.scalars(
                select(Outcome).where(
                    Outcome.id.in_([p.outcome_id for p in positions if p.outcome_id])
                )
            )
        }

        records: list[PositionRecord] = []
        for p in positions:
            market = market_rows.get(p.market_id) if p.market_id else None
            outcome = outcome_rows.get(p.outcome_id) if p.outcome_id else None
            event = market.event if market is not None else None

            records.append(
                PositionRecord(
                    position_id=p.id,
                    opened_ts=p.opened_ts,
                    closed_ts=p.closed_ts,
                    status=p.status,
                    is_tennis=p.is_tennis,
                    tennis_market_type=p.tennis_market_type,
                    entry_phase=p.entry_phase,
                    avg_entry_price=p.avg_entry_price,
                    capital_committed=p.capital_committed,
                    net_pnl=p.net_pnl,
                    roi=p.roi,
                    is_win=p.is_win,
                    holding_seconds=p.holding_seconds,
                    behaviour=p.behaviour,
                    max_shares=p.max_shares,
                    market_liquidity=market.liquidity if market else None,
                    tournament=event.tournament if event else None,
                    player=outcome.player_name if outcome else None,
                    reconstruction_confidence=p.reconstruction_confidence,
                    flags=json.loads(p.flags) if p.flags else [],
                    copyable=copy_rows.get(p.id, {}),
                )
            )
        return records

    def compute_metrics(
        self, wallet: Wallet, *, population_mean: float = 0.0
    ) -> dict[str, MetricSet]:
        records = self.build_position_records(wallet)
        if not records:
            return {}

        scopes = compute_scope_metrics(
            records,
            benchmark_delay_seconds=self.settings.benchmark_delay_seconds,
            population_mean_copyable_roi=population_mean,
        )
        for scope, metrics in scopes.items():
            self._persist_metrics(wallet, scope, metrics)
        return scopes

    def _persist_metrics(self, wallet: Wallet, scope: str, m: MetricSet) -> None:
        row = self.session.scalar(
            select(WalletMetrics).where(
                WalletMetrics.wallet_id == wallet.id, WalletMetrics.scope == scope
            )
        )
        if row is None:
            row = WalletMetrics(wallet_id=wallet.id, scope=scope)
            self.session.add(row)

        row.total_trades = m.total_trades
        row.total_positions = m.total_positions
        row.completed_positions = m.completed_positions
        row.open_positions = m.open_positions
        row.volume_usdc = m.volume_usdc
        row.capital_deployed = m.capital_deployed
        row.gross_profit = m.gross_profit
        row.gross_loss = m.gross_loss
        row.net_profit = m.net_profit
        row.fees_paid = m.fees_paid
        row.roi = m.roi
        row.roi_equal_weighted = m.roi_equal_weighted
        row.return_on_capital = m.return_on_capital
        row.win_rate = m.win_rate
        row.profit_factor = m.profit_factor
        row.avg_profit_per_trade = m.avg_profit_per_trade
        row.median_profit_per_trade = m.median_profit_per_trade
        row.expected_value_per_dollar = m.expected_value_per_dollar
        row.avg_entry_price = m.avg_entry_price
        row.avg_holding_seconds = m.avg_holding_seconds
        row.median_holding_seconds = m.median_holding_seconds
        row.max_drawdown = m.max_drawdown
        row.max_drawdown_usdc = m.max_drawdown_usdc
        row.longest_win_streak = m.longest_win_streak
        row.longest_loss_streak = m.longest_loss_streak
        row.pct_profit_from_largest_trade = m.pct_profit_from_largest_trade
        row.pct_profit_from_top5_trades = m.pct_profit_from_top5_trades
        row.pnl_std_dev = m.pnl_std_dev
        row.sharpe_like = m.sharpe_like
        row.benchmark_delay_seconds = m.benchmark_delay_seconds
        row.copyable_roi = m.copyable_roi
        row.copyable_roi_median = m.copyable_roi_median
        row.copyable_roi_trimmed = m.copyable_roi_trimmed
        row.copyable_outlier_dependence = m.copyable_outlier_dependence
        row.copyable_win_rate = m.copyable_win_rate
        row.copyable_net_profit = m.copyable_net_profit
        row.copyable_profit_factor = m.copyable_profit_factor
        row.avg_copyability_score = m.avg_copyability_score
        row.copyable_coverage = m.copyable_coverage
        row.avg_price_deterioration = None
        row.roi_by_delay = json.dumps(m.roi_by_delay, default=str) if m.roi_by_delay else None
        row.roi_ci_low = m.roi_ci_low
        row.roi_ci_high = m.roi_ci_high
        row.copyable_roi_ci_low = m.copyable_roi_ci_low
        row.copyable_roi_ci_high = m.copyable_roi_ci_high
        row.shrunk_copyable_roi = m.shrunk_copyable_roi
        row.prob_positive_edge = m.prob_positive_edge
        row.sample_confidence = m.sample_confidence
        row.performance_by_market_type = m.json_field("performance_by_market_type")
        row.performance_by_tournament = m.json_field("performance_by_tournament")
        row.performance_by_player = m.json_field("performance_by_player")
        row.performance_by_entry_bucket = m.json_field("performance_by_entry_bucket")
        row.performance_by_size_bucket = m.json_field("performance_by_size_bucket")
        row.performance_by_period = m.json_field("performance_by_period")
        row.data_quality_score = m.data_quality_score
        row.computed_at = datetime.now(timezone.utc)
        self.session.flush()

    # ----------------------------------------------------------------- scores
    def compute_score(self, wallet: Wallet, metrics: MetricSet) -> WalletScore:
        result = WalletScorer(self.settings).score(metrics)

        row = self.session.scalar(
            select(WalletScore).where(
                WalletScore.wallet_id == wallet.id, WalletScore.scope == metrics.scope
            )
        )
        previous_score = row.skill_score if row is not None else None
        if row is None:
            row = WalletScore(wallet_id=wallet.id, scope=metrics.scope)
            self.session.add(row)

        row.skill_score = result.skill_score
        row.base_score = result.base_score
        row.copyable_roi_score = result.components.get("copyable_roi", 0.0)
        row.profit_factor_score = result.components.get("profit_factor", 0.0)
        row.sample_confidence_score = result.components.get("sample_confidence", 0.0)
        row.consistency_score = result.components.get("consistency", 0.0)
        row.drawdown_score = result.components.get("drawdown", 0.0)
        row.recency_score = result.components.get("recency", 0.0)
        row.liquidity_fit_score = result.components.get("liquidity_fit", 0.0)
        row.concentration_score = result.components.get("concentration", 0.0)
        row.data_quality_score = result.components.get("data_quality", 0.0)
        row.penalties_applied = result.penalties_json()
        row.total_penalty_multiplier = result.total_penalty_multiplier
        row.risk_flags = result.risk_flags_json()
        row.qualified = result.qualified
        row.disqualification_reasons = result.reasons_json()
        row.confidence_level = result.confidence_level
        row.explanation = result.explanation
        row.formula_version = result.formula_version
        row.computed_at = datetime.now(timezone.utc)

        # Mirror wallet-level risk flags for fast filtering in the UI.
        if metrics.scope == "tennis":
            wallet.risk_flags = result.risk_flags_json()

        self.session.flush()
        self._snapshot_history(wallet, metrics, result.skill_score)
        row._previous_score = previous_score  # type: ignore[attr-defined]
        return row

    def _snapshot_history(
        self, wallet: Wallet, metrics: MetricSet, skill_score: float
    ) -> None:
        """One row per wallet/scope/day, used for trend and downgrade detection."""
        today = datetime.now(timezone.utc).date()
        row = self.session.scalar(
            select(WalletMetricHistory).where(
                WalletMetricHistory.wallet_id == wallet.id,
                WalletMetricHistory.scope == metrics.scope,
                WalletMetricHistory.snapshot_date == today,
            )
        )
        if row is None:
            row = WalletMetricHistory(
                wallet_id=wallet.id, scope=metrics.scope, snapshot_date=today
            )
            self.session.add(row)
        row.completed_positions = metrics.completed_positions
        row.net_profit = metrics.net_profit
        row.roi = metrics.roi
        row.copyable_roi = metrics.copyable_roi
        row.win_rate = metrics.win_rate
        row.max_drawdown = metrics.max_drawdown
        row.skill_score = skill_score
        self.session.flush()

    # --------------------------------------------------------------- clusters
    def compute_clusters(self, *, min_positions: int = 4) -> int:
        """Rebuild wallet clusters from tennis entry behaviour."""
        signatures: list[WalletActivitySignature] = []

        wallets = list(self.session.scalars(select(Wallet)))
        for wallet in wallets:
            rows = list(
                self.session.execute(
                    select(
                        ReconstructedPosition.token_id,
                        ReconstructedPosition.opened_ts,
                        ReconstructedPosition.capital_committed,
                        ReconstructedPosition.closed_ts,
                    ).where(
                        ReconstructedPosition.wallet_id == wallet.id,
                        ReconstructedPosition.is_tennis.is_(True),
                    )
                )
            )
            if len(rows) < min_positions:
                continue

            signature = WalletActivitySignature(
                wallet_id=wallet.id, address=wallet.address
            )
            for token_id, opened_ts, capital, closed_ts in rows:
                # Earliest entry per token: a later add is not a fresh decision.
                if (
                    token_id not in signature.entries
                    or opened_ts < signature.entries[token_id]
                ):
                    signature.entries[token_id] = opened_ts
                    signature.sizes[token_id] = capital or ZERO
                if closed_ts is not None:
                    signature.exits[token_id] = closed_ts
            signatures.append(signature)

        if len(signatures) < 2:
            return 0

        clusters, pairs = WalletClusterer(self.settings).build_clusters(signatures)

        # Rebuild: cluster identity is derived, not authored.
        self.session.execute(delete(WalletClusterMember))
        # synchronize_session="fetch" is required, not stylistic. With the bulk
        # update unsynchronised, already-loaded Wallet objects keep their old
        # cluster id in memory. On a second run in the same session SQLite reuses
        # the same cluster ids, so re-assigning the identical value registers as
        # "unchanged", no UPDATE is emitted, and the column silently stays NULL.
        # That would leave cluster_membership_map() blind and make the consensus
        # independence rule inert -- related wallets would count as separate
        # confirmations, the exact failure this module exists to prevent.
        self.session.query(Wallet).update(
            {Wallet.suspected_cluster_id: None}, synchronize_session="fetch"
        )
        self.session.execute(delete(WalletCluster))
        self.session.flush()

        pair_lookup = {(p.wallet_a, p.wallet_b): p for p in pairs}
        written = 0

        for cluster in clusters:
            row = WalletCluster(
                label=cluster.label,
                relation=cluster.relation,
                confidence=cluster.confidence,
                evidence=cluster.evidence_summary(),
                member_count=cluster.member_count,
            )
            self.session.add(row)
            self.session.flush()

            for wallet_id in sorted(cluster.wallet_ids):
                wallet = self.session.get(Wallet, wallet_id)
                if wallet is not None:
                    wallet.suspected_cluster_id = row.id

                best = None
                for (a, b), pair in pair_lookup.items():
                    if wallet_id in (a, b) and (
                        a in cluster.wallet_ids and b in cluster.wallet_ids
                    ):
                        if best is None or pair.confidence > best.confidence:
                            best = pair

                self.session.add(
                    WalletClusterMember(
                        cluster_id=row.id,
                        wallet_id=wallet_id,
                        shared_market_count=best.shared_markets if best else 0,
                        jaccard_similarity=best.jaccard if best else 0.0,
                        timing_correlation=best.timing_correlation if best else 0.0,
                        size_correlation=best.size_correlation if best else 0.0,
                        coordinated_exit_count=best.coordinated_exits if best else 0,
                    )
                )
            written += 1

        self.session.flush()
        return written

    # ------------------------------------------------------------------- full
    def run_full(self, *, wallet_ids: list[int] | None = None) -> PipelineStats:
        """Run every stage for the selected wallets (all active by default)."""
        stats = PipelineStats()

        query = select(Wallet)
        if wallet_ids:
            query = query.where(Wallet.id.in_(wallet_ids))
        wallets = list(self.session.scalars(query))

        # Pass 1: reconstruct and price, so the population prior can be computed
        # from complete information before any wallet is scored against it.
        interim: dict[int, dict[str, MetricSet]] = {}
        for wallet in wallets:
            try:
                stats.positions_written += self.reconstruct_wallet(wallet)
                stats.copyability_rows += self.compute_copyability(wallet)
                records = self.build_position_records(wallet)
                if records:
                    interim[wallet.id] = compute_scope_metrics(
                        records,
                        benchmark_delay_seconds=self.settings.benchmark_delay_seconds,
                    )
                stats.wallets_processed += 1
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"{wallet.address}: {exc}")
                log.warning(
                    "pipeline.wallet_failed", wallet=wallet.address, error=str(exc)
                )

        prior = population_mean_copyable_roi(
            m["tennis"] for m in interim.values() if "tennis" in m
        )
        log.info("pipeline.population_prior", copyable_roi=prior, wallets=len(interim))

        # Pass 2: persist metrics and scores using the shared prior.
        for wallet in wallets:
            if wallet.id not in interim:
                continue
            try:
                scopes = self.compute_metrics(wallet, population_mean=prior)
                stats.metrics_written += len(scopes)
                tennis = scopes.get("tennis")
                if tennis is not None:
                    self.compute_score(wallet, tennis)
                    stats.scores_written += 1
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"{wallet.address} metrics: {exc}")

        try:
            stats.clusters_written = self.compute_clusters()
        except Exception as exc:  # noqa: BLE001
            stats.errors.append(f"clustering: {exc}")

        return stats

    # -------------------------------------------------------------- internals
    def _market_contexts(self, condition_ids: set[str]) -> dict[str, MarketContext]:
        if not condition_ids:
            return {}
        rows = self.session.scalars(
            select(Market).where(Market.condition_id.in_(condition_ids))
        )
        return {
            m.condition_id: MarketContext(
                condition_id=m.condition_id,
                resolved=m.resolved,
                winning_outcome_index=m.winning_outcome_index,
                resolved_at=m.resolved_at,
                game_start_time=m.game_start_time,
                is_tennis=m.is_tennis,
                tennis_market_type=m.tennis_market_type,
                closed=m.closed,
            )
            for m in rows
        }

    def _market_ids(self, contexts: dict[str, MarketContext]) -> dict[str, int]:
        if not contexts:
            return {}
        rows = self.session.execute(
            select(Market.condition_id, Market.id).where(
                Market.condition_id.in_(contexts.keys())
            )
        )
        return {condition_id: market_id for condition_id, market_id in rows}

    def _outcome_ids(self, token_ids: set[str]) -> dict[str, int]:
        if not token_ids:
            return {}
        rows = self.session.execute(
            select(Outcome.token_id, Outcome.id).where(Outcome.token_id.in_(token_ids))
        )
        return {token_id: outcome_id for token_id, outcome_id in rows}

    def _token_outcome_indexes(self, token_ids: set[str]) -> dict[str, int]:
        if not token_ids:
            return {}
        rows = self.session.execute(
            select(Outcome.token_id, Outcome.outcome_index).where(
                Outcome.token_id.in_(token_ids)
            )
        )
        return {token_id: index for token_id, index in rows}


def qualified_wallet_ids(session: Session, scope: str = "tennis") -> list[int]:
    """Wallets currently passing every hard alert gate."""
    return list(
        session.scalars(
            select(WalletScore.wallet_id).where(
                WalletScore.scope == scope, WalletScore.qualified.is_(True)
            )
        )
    )


def cluster_membership_map(session: Session) -> dict[int, int | None]:
    """``wallet_id -> cluster_id`` for consensus de-duplication."""
    rows = session.execute(select(Wallet.id, Wallet.suspected_cluster_id))
    return {wallet_id: cluster_id for wallet_id, cluster_id in rows}


def data_quality_snapshot(session: Session) -> dict:
    """Pipeline completeness and confidence, for the health panel."""
    from ..models import DataQualityReport

    wallets = session.scalar(select(func.count(Wallet.id))) or 0
    stale_cutoff = datetime.now(timezone.utc).timestamp() - 86400
    stale = (
        session.scalar(
            select(func.count(Wallet.id)).where(
                (Wallet.last_sync_success_at.is_(None))
                | (
                    func.coalesce(Wallet.sync_cursor_ts, 0) < stale_cutoff
                )
            )
        )
        or 0
    )
    markets = session.scalar(select(func.count(Market.id))) or 0
    review = (
        session.scalar(
            select(func.count(Market.id)).where(Market.needs_review.is_(True))
        )
        or 0
    )
    transactions = session.scalar(select(func.count(NormalizedTransaction.id))) or 0
    unmatched = (
        session.scalar(
            select(func.count(NormalizedTransaction.id)).where(
                NormalizedTransaction.market_id.is_(None)
            )
        )
        or 0
    )
    positions = session.scalar(select(func.count(ReconstructedPosition.id))) or 0
    low_conf = (
        session.scalar(
            select(func.count(ReconstructedPosition.id)).where(
                ReconstructedPosition.reconstruction_confidence < 80
            )
        )
        or 0
    )

    quality_rows = session.execute(
        select(TradeCopyability.price_source_quality, func.count(TradeCopyability.id))
        .group_by(TradeCopyability.price_source_quality)
    )
    breakdown = {quality: count for quality, count in quality_rows}
    avg_conf = session.scalar(select(func.avg(TradeCopyability.data_confidence)))

    warnings: list[str] = []
    if review:
        warnings.append(f"{review} markets need classification review")
    if unmatched and transactions:
        # Wallets trade far more non-tennis than tennis, and only the tennis
        # universe is fully synced, so unmatched rows are expected. Only an
        # unusually high share suggests the market backfill is falling behind.
        share = unmatched / transactions
        if share > 0.9:
            warnings.append(
                f"{unmatched}/{transactions} transactions ({share:.0%}) are not "
                "joined to a known market. Expected for non-tennis activity, but "
                "check that tennis market sync is running if tennis coverage looks thin."
            )
    if low_conf:
        warnings.append(f"{low_conf} positions have low reconstruction confidence")
    modeled = breakdown.get("modeled", 0) + breakdown.get("nearest_trade", 0)
    total_copy = sum(breakdown.values())
    if total_copy and modeled / total_copy > 0.3:
        warnings.append(
            f"{modeled}/{total_copy} copyability rows rely on modelled or distant "
            "price evidence; short-delay figures are weak for these markets"
        )

    report = DataQualityReport(
        wallets_tracked=wallets,
        wallets_stale=stale,
        markets_tracked=markets,
        markets_needing_review=review,
        transactions_total=transactions,
        transactions_unmatched_market=unmatched,
        positions_total=positions,
        positions_low_confidence=low_conf,
        price_quality_breakdown_json=json.dumps(breakdown),
        avg_data_confidence=float(avg_conf) if avg_conf is not None else None,
        warnings_json=json.dumps(warnings),
    )
    session.add(report)
    session.flush()

    return {
        "wallets_tracked": wallets,
        "wallets_stale": stale,
        "markets_tracked": markets,
        "markets_needing_review": review,
        "transactions_total": transactions,
        "transactions_unmatched_market": unmatched,
        "positions_total": positions,
        "positions_low_confidence": low_conf,
        "price_quality_breakdown": breakdown,
        "avg_data_confidence": float(avg_conf) if avg_conf is not None else None,
        "warnings": warnings,
    }
