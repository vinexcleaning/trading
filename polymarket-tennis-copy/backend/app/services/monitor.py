"""Live signal monitoring and paper-trade management.

This module is the bridge between the pure decision services (:mod:`signals`,
:mod:`copyability`, :mod:`paper`) and the database. The services deliberately
know nothing about SQLAlchemy so they stay unit-testable; this module supplies
them with state and persists what they decide.

Two design choices are worth stating explicitly.

**Only analysed wallets can produce signals.** A wallet with no computed tennis
score has not been evaluated yet, and scanning it would emit a rejection row per
trade -- noise that buries the rejection log the operator actually needs. Wallets
without a score are counted and reported, never silently dropped.

**Consensus is evaluated before singles.** When several wallets hit the same
outcome inside the consensus window, the group is judged as a consensus
candidate first. Its members only get individual single-wallet evaluations if
the consensus did not qualify, so one underlying cluster of activity cannot
produce a consensus alert *and* a stack of single-wallet alerts for the same
trades.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..enums import (
    ActivityType,
    PaperEventType,
    PaperTradeStatus,
    PositionStatus,
    PriceSourceQuality,
    SignalStatus,
    SignalType,
    TradeSide,
)
from ..logging_setup import get_logger
from ..models import (
    Alert,
    Market,
    MarketPrice,
    NormalizedTransaction,
    Outcome,
    PaperDailyStat,
    PaperTrade,
    PaperTradeEvent,
    ReconstructedPosition,
    Signal,
    SignalWallet,
    Wallet,
    WalletMetrics,
    WalletScore,
)
from ..providers import PolymarketProvider
from .copyability import CopyabilityInput, score_copyability
from .ingest import build_price_series
from .notifications import (
    NotificationDispatcher,
    NotificationType,
    build_signal_notification,
)
from .paper import PaperTradingEngine, RiskState, today_utc
from .pipeline import cluster_membership_map
from .prices import ResolvedPrice, estimate_follower_fill
from .signals import (
    MarketConditions,
    SignalEngine,
    WalletSignalCandidate,
    group_into_consensus_windows,
)

log = get_logger(__name__)

ZERO = Decimal("0")
ONE = Decimal("1")
# Depth within this distance of best ask counts as reachable liquidity. Total
# book depth is a misleading number: a probe showed $14 within a cent of touch
# against $2,178 across the whole ladder.
LIQUIDITY_BAND = Decimal("0.02")


@dataclass
class ScanStats:
    """What one monitoring pass did."""

    wallets_considered: int = 0
    wallets_without_score: int = 0
    transactions_considered: int = 0
    tokens_evaluated: int = 0
    signals_created: int = 0
    signals_updated: int = 0
    qualified: int = 0
    rejected: int = 0
    expired: int = 0
    alerts_dispatched: int = 0
    paper_entered: int = 0
    paper_rejected: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "wallets_considered": self.wallets_considered,
            "wallets_without_score": self.wallets_without_score,
            "transactions_considered": self.transactions_considered,
            "tokens_evaluated": self.tokens_evaluated,
            "signals_created": self.signals_created,
            "signals_updated": self.signals_updated,
            "qualified": self.qualified,
            "rejected": self.rejected,
            "expired": self.expired,
            "alerts_dispatched": self.alerts_dispatched,
            "paper_entered": self.paper_entered,
            "paper_rejected": self.paper_rejected,
            "notes": self.notes,
        }


@dataclass(slots=True)
class _WalletContext:
    """Cached per-wallet analytics used to build candidates."""

    wallet: Wallet
    score: WalletScore | None
    metrics: WalletMetrics | None


class SignalMonitor:
    """Detects, qualifies and persists live signals."""

    def __init__(
        self,
        session: Session,
        provider: PolymarketProvider | None = None,
        settings: Settings | None = None,
        *,
        dispatcher: NotificationDispatcher | None = None,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.now = now or datetime.now(timezone.utc)
        self.engine = SignalEngine(self.settings, now=self.now)
        self.dispatcher = dispatcher
        self._book_cache: dict[str, object] = {}

    # ------------------------------------------------------------------ scan
    def scan(
        self,
        *,
        lookback_seconds: int | None = None,
        dispatch: bool = True,
        paper: bool = True,
    ) -> ScanStats:
        """Evaluate recent qualified-wallet tennis buys and persist the verdicts."""
        s = self.settings
        stats = ScanStats()

        window = lookback_seconds or max(
            s.alert_max_age_prematch_seconds * 2, s.consensus_window_seconds * 4, 900
        )
        cutoff_ts = int((self.now - timedelta(seconds=window)).timestamp())

        candidates_by_token = self._collect_candidates(cutoff_ts, stats)
        if not candidates_by_token:
            stats.notes.append("no recent tennis entries from analysed wallets")
            return stats

        membership = cluster_membership_map(self.session)

        for token_id, candidates in candidates_by_token.items():
            conditions = self._market_conditions(token_id, candidates)
            if conditions is None:
                stats.notes.append(f"no market metadata for token {token_id[:12]}...")
                continue
            stats.tokens_evaluated += 1

            covered: set[int] = set()
            for group in group_into_consensus_windows(
                candidates, s.consensus_window_seconds
            ):
                if len(group) > 1:
                    evaluation = self.engine.evaluate(
                        group, conditions, cluster_membership=membership
                    )
                    self._persist(evaluation, conditions, stats, dispatch=dispatch, paper=paper)
                    if evaluation.qualified:
                        # A qualified consensus already speaks for these wallets.
                        covered.update(c.wallet_id for c in group)

                for candidate in group:
                    if candidate.wallet_id in covered:
                        continue
                    evaluation = self.engine.evaluate(
                        [candidate],
                        conditions,
                        cluster_membership=membership,
                        signal_type=SignalType.SINGLE_WALLET,
                    )
                    self._persist(
                        evaluation, conditions, stats, dispatch=dispatch, paper=paper
                    )

        log.info("monitor.scan", **{k: v for k, v in stats.as_dict().items() if k != "notes"})
        return stats

    # ------------------------------------------------------------ candidates
    def _collect_candidates(
        self, cutoff_ts: int, stats: ScanStats
    ) -> dict[str, list[WalletSignalCandidate]]:
        """Aggregate recent buys into one candidate per (wallet, token)."""
        rows = list(
            self.session.execute(
                select(NormalizedTransaction, Wallet)
                .join(Wallet, Wallet.id == NormalizedTransaction.wallet_id)
                .where(
                    NormalizedTransaction.is_tennis.is_(True),
                    NormalizedTransaction.activity_type == ActivityType.TRADE,
                    NormalizedTransaction.side == TradeSide.BUY,
                    NormalizedTransaction.timestamp >= cutoff_ts,
                    NormalizedTransaction.token_id.is_not(None),
                    Wallet.status == "active",
                )
                .order_by(NormalizedTransaction.timestamp)
            )
        )
        stats.transactions_considered = len(rows)
        if not rows:
            return {}

        contexts = self._wallet_contexts({w.id for _, w in rows})

        # Aggregate: several fills of the same intent are one entry, not several.
        grouped: dict[tuple[int, str], list[NormalizedTransaction]] = {}
        for tx, wallet in rows:
            ctx = contexts.get(wallet.id)
            if ctx is None or ctx.score is None:
                continue
            grouped.setdefault((wallet.id, tx.token_id), []).append(tx)

        stats.wallets_considered = len({wid for wid, _ in grouped})
        stats.wallets_without_score = len(
            {w.id for _, w in rows if contexts.get(w.id) and contexts[w.id].score is None}
        )
        if stats.wallets_without_score:
            stats.notes.append(
                f"{stats.wallets_without_score} wallet(s) traded tennis but have no "
                "computed score yet and were not evaluated"
            )

        by_token: dict[str, list[WalletSignalCandidate]] = {}
        for (wallet_id, token_id), txs in grouped.items():
            ctx = contexts[wallet_id]
            candidate = self._build_candidate(ctx, token_id, txs)
            if candidate is not None:
                by_token.setdefault(token_id, []).append(candidate)
        return by_token

    def _wallet_contexts(self, wallet_ids: set[int]) -> dict[int, _WalletContext]:
        if not wallet_ids:
            return {}
        wallets = {
            w.id: w for w in self.session.scalars(select(Wallet).where(Wallet.id.in_(wallet_ids)))
        }
        scores = {
            row.wallet_id: row
            for row in self.session.scalars(
                select(WalletScore).where(
                    WalletScore.wallet_id.in_(wallet_ids), WalletScore.scope == "tennis"
                )
            )
        }
        metrics = {
            row.wallet_id: row
            for row in self.session.scalars(
                select(WalletMetrics).where(
                    WalletMetrics.wallet_id.in_(wallet_ids),
                    WalletMetrics.scope == "tennis",
                )
            )
        }
        return {
            wid: _WalletContext(wallet, scores.get(wid), metrics.get(wid))
            for wid, wallet in wallets.items()
        }

    def _build_candidate(
        self, ctx: _WalletContext, token_id: str, txs: list[NormalizedTransaction]
    ) -> WalletSignalCandidate | None:
        shares = sum((tx.size for tx in txs), ZERO)
        notional = sum(
            (tx.usdc_size if tx.usdc_size is not None else tx.size * (tx.price or ZERO))
            for tx in txs
        )
        if shares <= ZERO or notional <= ZERO:
            return None

        # Size-weighted average: the price a follower would have had to match.
        entry_price = notional / shares
        first = min(txs, key=lambda t: t.timestamp)

        position = self.session.scalar(
            select(ReconstructedPosition)
            .where(
                ReconstructedPosition.wallet_id == ctx.wallet.id,
                ReconstructedPosition.token_id == token_id,
            )
            .order_by(ReconstructedPosition.opened_ts.desc())
            .limit(1)
        )

        is_increase = bool(position is not None and position.opened_ts < first.timestamp)
        has_exited = self._has_begun_exiting(ctx.wallet.id, token_id, first.timestamp, position)

        score = ctx.score
        metrics = ctx.metrics
        return WalletSignalCandidate(
            wallet_id=ctx.wallet.id,
            address=ctx.wallet.address,
            nickname=ctx.wallet.nickname,
            traded_at=first.occurred_at,
            entry_price=entry_price,
            position_usdc=notional,
            skill_score=score.skill_score if score else 0.0,
            copyable_roi=metrics.copyable_roi if metrics else None,
            tennis_trade_count=metrics.completed_positions if metrics else 0,
            qualified_wallet=bool(score and score.qualified),
            cluster_id=ctx.wallet.suspected_cluster_id,
            risk_flags=_json_list(score.risk_flags) if score else [],
            is_position_increase=is_increase,
            has_begun_exiting=has_exited,
            position_id=position.id if position else None,
            max_drawdown=metrics.max_drawdown if metrics else None,
            data_confidence=(metrics.data_quality_score or 0.0) if metrics else 0.0,
        )

    def _has_begun_exiting(
        self,
        wallet_id: int,
        token_id: str,
        since_ts: int,
        position: ReconstructedPosition | None,
    ) -> bool:
        """Has the wallet started reducing since the entry we are considering?"""
        sold = self.session.scalar(
            select(func.count())
            .select_from(NormalizedTransaction)
            .where(
                NormalizedTransaction.wallet_id == wallet_id,
                NormalizedTransaction.token_id == token_id,
                NormalizedTransaction.side == TradeSide.SELL,
                NormalizedTransaction.timestamp >= since_ts,
            )
        )
        if sold:
            return True
        if position is not None and position.status in (
            PositionStatus.CLOSED,
            PositionStatus.SETTLED,
            PositionStatus.REVERSED,
        ):
            return True
        return False

    # ------------------------------------------------------- market snapshot
    def _market_conditions(
        self, token_id: str, candidates: list[WalletSignalCandidate]
    ) -> MarketConditions | None:
        outcome = self.session.scalar(select(Outcome).where(Outcome.token_id == token_id))
        if outcome is None:
            return None
        market = self.session.get(Market, outcome.market_id)
        if market is None:
            return None

        book = self._order_book(token_id)
        current_price = None
        quality = PriceSourceQuality.UNAVAILABLE
        note = None

        if book is not None and book.midpoint is not None:
            current_price = book.midpoint
            # A live book is a direct measurement at decision time, not a
            # reconstruction, so it earns the top evidence tier.
            quality = PriceSourceQuality.OBSERVED_TRADE
            note = "live order-book midpoint"
        else:
            series = build_price_series(self.session, token_id)
            resolved = series.resolve(int(self.now.timestamp()))
            if resolved.is_usable:
                current_price = resolved.price
                quality = resolved.quality
                note = resolved.note or "stored price observation"
            elif outcome.last_price is not None:
                current_price = outcome.last_price
                quality = PriceSourceQuality.MODELED
                note = "last known outcome price"

        spread = book.spread if book is not None else market.spread
        liquidity = (
            book.ask_depth_usdc(within=LIQUIDITY_BAND) if book is not None else market.liquidity
        )

        follower_price = None
        fill = None
        if current_price is not None:
            fill = estimate_follower_fill(
                current_price,
                self.settings.paper_stake_usdc,
                book=book,
                spread=spread,
                slippage_bps=self.settings.modeled_slippage_bps,
                price_quality=quality,
            )
            follower_price = fill.fill_price

        phase = market.phase_at(self.now)
        reference_entry = _median_decimal([c.entry_price for c in candidates])
        first_ts = int(min(c.traded_at for c in candidates).timestamp())

        copyability = None
        if current_price is not None and reference_entry is not None:
            copyability = score_copyability(
                CopyabilityInput(
                    wallet_entry_price=reference_entry,
                    wallet_entry_ts=first_ts,
                    # Judge the trade at the delay we hold ourselves to.
                    delay_seconds=self.settings.benchmark_delay_seconds,
                    price_after_delay=ResolvedPrice(
                        price=current_price,
                        quality=quality,
                        distance_seconds=0,
                        note=note,
                    ),
                    fill=fill,
                    available_liquidity=liquidity,
                    spread=spread,
                    market_phase=phase,
                    wallet_exited_within_delay=any(c.has_begun_exiting for c in candidates),
                    wallet_position_usdc=sum((c.position_usdc for c in candidates), ZERO),
                    follower_stake=self.settings.paper_stake_usdc,
                    classification_confidence=market.classification_confidence,
                )
            ).score

        return MarketConditions(
            token_id=token_id,
            condition_id=market.condition_id,
            market_id=market.id,
            outcome_label=outcome.label,
            current_price=current_price,
            estimated_follower_price=follower_price,
            spread=spread,
            available_liquidity=liquidity,
            market_phase=phase,
            classification_confidence=market.classification_confidence,
            closed=market.closed or market.resolved or market.blacklisted,
            accepting_orders=market.accepting_orders,
            price_source_quality=quality,
            copyability_score=copyability,
            game_start_time=market.game_start_time,
        )

    def _order_book(self, token_id: str):
        if self.provider is None:
            return None
        if token_id in self._book_cache:
            return self._book_cache[token_id]
        try:
            book = self.provider.get_order_book(token_id)
        except Exception as exc:  # noqa: BLE001 - a book failure must not stop the scan
            log.warning("monitor.book_failed", token=token_id[:12], error=str(exc))
            book = None
        self._book_cache[token_id] = book
        return book

    # -------------------------------------------------------------- persist
    def _persist(
        self,
        evaluation,
        conditions: MarketConditions,
        stats: ScanStats,
        *,
        dispatch: bool,
        paper: bool,
    ) -> Signal:
        existing = self.session.scalar(
            select(Signal).where(Signal.dedupe_key == evaluation.dedupe_key)
        )
        created = existing is None
        signal = existing or Signal(dedupe_key=evaluation.dedupe_key)

        first_trade = min(c.traded_at for c in evaluation.wallets)
        last_trade = max(c.traded_at for c in evaluation.wallets)

        signal.signal_type = evaluation.signal_type
        signal.market_id = conditions.market_id
        signal.token_id = conditions.token_id
        signal.condition_id = conditions.condition_id
        signal.outcome_label = conditions.outcome_label
        signal.first_wallet_trade_at = first_trade
        signal.last_wallet_trade_at = last_trade
        signal.evaluated_at = self.now
        signal.expires_at = evaluation.expires_at
        signal.signal_age_seconds = evaluation.signal_age_seconds
        signal.market_phase = evaluation.market_phase
        signal.wallet_entry_price_min = evaluation.wallet_entry_price_min
        signal.wallet_entry_price_max = evaluation.wallet_entry_price_max
        signal.wallet_entry_price_median = evaluation.wallet_entry_price_median
        signal.current_price = conditions.current_price
        signal.estimated_follower_price = conditions.estimated_follower_price
        signal.price_deterioration = evaluation.price_deterioration
        signal.available_liquidity = conditions.available_liquidity
        signal.spread = conditions.spread
        signal.total_wallet_position_usdc = evaluation.total_wallet_position_usdc
        signal.wallet_count = len(evaluation.wallets)
        signal.independent_cluster_count = evaluation.independent_cluster_count
        signal.median_skill_score = evaluation.median_skill_score
        signal.median_copyable_roi = evaluation.median_copyable_roi
        signal.copyability_score = evaluation.copyability_score
        signal.consensus_score = evaluation.consensus_score
        signal.estimated_edge = evaluation.estimated_edge
        signal.edge_method = evaluation.edge_method
        signal.data_confidence = evaluation.data_confidence
        signal.qualified = evaluation.qualified
        signal.rejection_reasons = evaluation.rejection_json()
        signal.risk_flags = evaluation.risk_flags_json()
        signal.explanation = evaluation.explanation
        signal.qualification_detail = evaluation.checks_json()

        # Never walk a paper-traded signal back to a pre-trade state.
        if signal.status not in (SignalStatus.PAPER_ENTERED, SignalStatus.PAPER_EXITED):
            signal.status = evaluation.status

        if created:
            signal.detected_at = self.now
            self.session.add(signal)
            stats.signals_created += 1
        else:
            stats.signals_updated += 1

        self.session.flush()
        self._persist_signal_wallets(signal, evaluation)

        if evaluation.status == SignalStatus.QUALIFIED:
            stats.qualified += 1
        elif evaluation.status == SignalStatus.EXPIRED:
            stats.expired += 1
        else:
            stats.rejected += 1

        if evaluation.qualified and evaluation.status == SignalStatus.QUALIFIED:
            if dispatch:
                stats.alerts_dispatched += self._dispatch_alert(signal, evaluation)
            if paper and self.settings.paper_trading_enabled:
                manager = PaperTradeManager(
                    self.session, self.provider, self.settings, now=self.now
                )
                trade = manager.enter_from_signal(signal, evaluation)
                if trade is not None and trade.status == PaperTradeStatus.OPEN:
                    stats.paper_entered += 1
                elif trade is not None:
                    stats.paper_rejected += 1
        return signal

    def _persist_signal_wallets(self, signal: Signal, evaluation) -> None:
        existing = {
            row.wallet_id: row
            for row in self.session.scalars(
                select(SignalWallet).where(SignalWallet.signal_id == signal.id)
            )
        }
        for candidate in evaluation.wallets:
            row = existing.get(candidate.wallet_id)
            if row is None:
                row = SignalWallet(signal_id=signal.id, wallet_id=candidate.wallet_id)
                self.session.add(row)
            row.position_id = candidate.position_id
            row.entry_price = candidate.entry_price
            row.position_usdc = candidate.position_usdc
            row.traded_at = candidate.traded_at
            row.skill_score = candidate.skill_score
            row.copyable_roi = candidate.copyable_roi
            row.tennis_trade_count = candidate.tennis_trade_count
            row.cluster_id = candidate.cluster_id
            row.counted_as_independent = candidate.wallet_id in evaluation.counted_wallet_ids
            row.is_position_increase = candidate.is_position_increase
            row.has_begun_exiting = candidate.has_begun_exiting

    # --------------------------------------------------------------- alerts
    def _dispatch_alert(self, signal: Signal, evaluation) -> int:
        dispatcher = self.dispatcher or NotificationDispatcher()
        market = self.session.get(Market, signal.market_id) if signal.market_id else None

        notification = build_signal_notification(
            signal_type=signal.signal_type,
            market_title=(market.question if market else None) or "unknown market",
            outcome_label=signal.outcome_label or "unknown outcome",
            wallet_count=len(evaluation.counted_wallet_ids) or signal.wallet_count,
            independent_groups=signal.independent_cluster_count,
            wallet_entry_min=signal.wallet_entry_price_min,
            wallet_entry_max=signal.wallet_entry_price_max,
            current_price=signal.current_price,
            follower_price=signal.estimated_follower_price,
            price_deterioration=signal.price_deterioration,
            liquidity=signal.available_liquidity,
            spread=signal.spread,
            median_copyable_roi=signal.median_copyable_roi,
            copyability_score=signal.copyability_score,
            consensus_score=signal.consensus_score,
            skill_score=signal.median_skill_score,
            estimated_edge=signal.estimated_edge,
            sample_size=min(
                (c.tennis_trade_count for c in evaluation.wallets), default=None
            ),
            signal_age_seconds=signal.signal_age_seconds,
            data_confidence=signal.data_confidence,
            risk_flags=evaluation.risk_flags,
            explanation=signal.explanation or "",
            market_phase=signal.market_phase,
        )

        alert_type = (
            NotificationType.MULTI_WALLET_CONSENSUS
            if signal.signal_type == SignalType.CONSENSUS
            else NotificationType.NEW_QUALIFYING_ENTRY
        )
        results = dispatcher.dispatch(notification)
        sent = 0
        for result in results:
            existing = self.session.scalar(
                select(Alert).where(
                    Alert.signal_id == signal.id,
                    Alert.channel == result.channel,
                    Alert.alert_type == alert_type.value,
                )
            )
            if existing is not None:
                continue
            self.session.add(
                Alert(
                    signal_id=signal.id,
                    alert_type=alert_type.value,
                    channel=result.channel,
                    title=notification.title,
                    body=notification.body,
                    payload=notification.payload_json(),
                    delivered=result.delivered,
                    delivered_at=self.now if result.delivered else None,
                    delivery_error=result.error,
                    attempts=1,
                )
            )
            if result.delivered:
                sent += 1
        return sent


class PaperTradeManager:
    """Opens, marks and closes simulated follower positions."""

    def __init__(
        self,
        session: Session,
        provider: PolymarketProvider | None = None,
        settings: Settings | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.now = now or datetime.now(timezone.utc)
        self.engine = PaperTradingEngine(self.settings)

    # ---------------------------------------------------------------- entry
    def enter_from_signal(self, signal: Signal, evaluation=None) -> PaperTrade | None:
        """Simulate a follower entry for a qualified signal."""
        if not self.settings.paper_trading_enabled:
            return None

        if not self.settings.paper_allow_duplicate_signals:
            duplicate = self.session.scalar(
                select(PaperTrade).where(
                    PaperTrade.signal_id == signal.id,
                    PaperTrade.is_backtest.is_(False),
                )
            )
            if duplicate is not None:
                return duplicate
            # Also refuse a second live position on the same outcome.
            same_token = self.session.scalar(
                select(PaperTrade).where(
                    PaperTrade.token_id == signal.token_id,
                    PaperTrade.is_backtest.is_(False),
                    PaperTrade.status.in_(
                        (PaperTradeStatus.OPEN, PaperTradeStatus.PENDING)
                    ),
                )
            )
            if same_token is not None:
                return same_token

        series = build_price_series(self.session, signal.token_id)
        book = None
        if self.provider is not None:
            try:
                book = self.provider.get_order_book(signal.token_id)
            except Exception as exc:  # noqa: BLE001
                log.warning("paper.book_failed", token=signal.token_id[:12], error=str(exc))

        # The live book is the best evidence of what a follower could get now, so
        # feed it into the series as an observation at the decision time.
        if book is not None and book.midpoint is not None:
            series.add_trade(int(self.now.timestamp()), book.midpoint, ZERO)

        market_key = signal.condition_id or signal.token_id
        entry = self.engine.simulate_entry(
            signal_detected_at=signal.detected_at or self.now,
            series=series,
            wallet_entry_price=signal.wallet_entry_price_median,
            risk_state=self.risk_state(),
            market_key=market_key,
            book=book,
            spread=signal.spread,
        )

        trade = PaperTrade(
            signal_id=signal.id,
            market_id=signal.market_id,
            token_id=signal.token_id,
            outcome_label=signal.outcome_label,
            exit_strategy=self.settings.paper_default_exit_strategy,
            signal_detected_at=signal.detected_at or self.now,
            execution_delay_seconds=self.settings.paper_execution_delay_seconds,
            wallet_entry_price=signal.wallet_entry_price_median,
            stake_usdc=entry.stake_usdc,
            price_source_quality=entry.price_source_quality,
            data_confidence=entry.data_confidence,
            notes=entry.note,
        )

        if not entry.accepted:
            trade.status = PaperTradeStatus.REJECTED
            trade.rejection_reason = entry.rejection_reason
            self.session.add(trade)
            self.session.flush()
            self._event(trade, PaperEventType.REJECTED, detail=entry.note)
            self._daily_stat().entries_blocked_by_risk += 1
            log.info(
                "paper.entry_rejected",
                signal_id=signal.id,
                reason=entry.rejection_reason,
            )
            return trade

        trade.status = PaperTradeStatus.OPEN
        trade.entered_at = entry.entered_at
        trade.reference_price = entry.reference_price
        trade.fill_price = entry.fill_price
        trade.shares = entry.shares
        trade.slippage_applied = entry.slippage
        trade.fees_applied = entry.fees
        trade.stake_reduced_for_liquidity = entry.stake_reduced_for_liquidity
        self.session.add(trade)
        self.session.flush()
        self._event(
            trade,
            PaperEventType.FILLED,
            price=entry.fill_price,
            shares=entry.shares,
            detail=entry.note,
        )

        stat = self._daily_stat()
        stat.trades_entered += 1
        stat.stake_deployed += entry.stake_usdc

        signal.status = SignalStatus.PAPER_ENTERED
        log.info(
            "paper.entered",
            signal_id=signal.id,
            stake=str(entry.stake_usdc),
            fill=str(entry.fill_price),
        )
        return trade

    # ----------------------------------------------------------- management
    def manage_open_trades(self) -> dict:
        """Mark open positions and close any whose exit rule has triggered."""
        trades = list(
            self.session.scalars(
                select(PaperTrade).where(
                    PaperTrade.is_backtest.is_(False),
                    PaperTrade.status == PaperTradeStatus.OPEN,
                )
            )
        )
        result = {"examined": len(trades), "closed": 0, "settled": 0, "marked": 0}

        for trade in trades:
            if trade.fill_price is None or trade.shares is None:
                continue

            market = self.session.get(Market, trade.market_id) if trade.market_id else None
            outcome = self.session.scalar(
                select(Outcome).where(Outcome.token_id == trade.token_id)
            )
            current = self._current_price(trade.token_id, market)

            resolved = bool(market is not None and market.resolved)
            won: bool | None = None
            if resolved:
                if outcome is not None and outcome.is_winner is not None:
                    won = outcome.is_winner
                elif (
                    market is not None
                    and market.winning_outcome_index is not None
                    and outcome is not None
                ):
                    won = market.winning_outcome_index == outcome.outcome_index
                if won is None:
                    # Resolved but we cannot tell which side won: hold rather
                    # than book an invented result.
                    resolved = False

            wallet_exited, wallet_reduced = self._wallet_exit_state(trade)

            exit_decision = self.engine.evaluate_exit(
                strategy=trade.exit_strategy,
                entered_at=trade.entered_at or trade.signal_detected_at,
                fill_price=trade.fill_price,
                shares=trade.shares,
                stake_usdc=trade.stake_usdc,
                now=self.now,
                current_price=current,
                peak_price=self._peak_price(trade),
                market_resolved=resolved,
                won=won,
                wallet_has_exited=wallet_exited,
                wallet_reduced=wallet_reduced,
                profit_target=self.settings.paper_profit_target,
                stop_loss=self.settings.paper_stop_loss,
                max_hold_seconds=self.settings.paper_max_hold_seconds,
            )

            if exit_decision.exited:
                self._close_trade(trade, exit_decision)
                result["settled" if exit_decision.settled_by_resolution else "closed"] += 1
            elif current is not None:
                trade.unrealized_pnl = self.engine.mark_to_market(
                    trade.fill_price, trade.shares, current
                )
                self._event(
                    trade,
                    PaperEventType.MARK_TO_MARKET,
                    price=current,
                    pnl=trade.unrealized_pnl,
                )
                result["marked"] += 1

        log.info("paper.managed", **result)
        return result

    def _close_trade(self, trade: PaperTrade, decision) -> None:
        trade.status = (
            PaperTradeStatus.SETTLED
            if decision.settled_by_resolution
            else PaperTradeStatus.CLOSED
        )
        trade.exited_at = decision.exited_at
        trade.exit_price = decision.exit_price
        trade.exit_reason = decision.reason
        trade.settled_by_resolution = decision.settled_by_resolution
        trade.realized_pnl = decision.realized_pnl
        trade.unrealized_pnl = ZERO
        trade.roi = decision.roi
        trade.is_win = (
            None if decision.realized_pnl is None else decision.realized_pnl > ZERO
        )
        if trade.entered_at and decision.exited_at:
            trade.holding_seconds = int(
                (decision.exited_at - trade.entered_at).total_seconds()
            )

        # The headline comparison: what the follower made versus the wallet.
        wallet_roi = self._wallet_roi(trade)
        if wallet_roi is not None:
            trade.wallet_roi = wallet_roi
            if trade.roi is not None:
                trade.roi_gap_vs_wallet = round(trade.roi - wallet_roi, 6)

        self._event(
            trade,
            PaperEventType.SETTLED if decision.settled_by_resolution else PaperEventType.EXITED,
            price=decision.exit_price,
            shares=trade.shares,
            pnl=decision.realized_pnl,
            detail=decision.reason,
        )

        stat = self._daily_stat()
        stat.trades_closed += 1
        stat.realized_pnl += decision.realized_pnl or ZERO
        if trade.is_win is True:
            stat.wins += 1
        elif trade.is_win is False:
            stat.losses += 1

        if trade.signal_id:
            signal = self.session.get(Signal, trade.signal_id)
            if signal is not None:
                signal.status = SignalStatus.PAPER_EXITED

    # -------------------------------------------------------------- helpers
    def risk_state(self) -> RiskState:
        """Current exposure, read from the database rather than assumed."""
        open_trades = list(
            self.session.scalars(
                select(PaperTrade).where(
                    PaperTrade.is_backtest.is_(False),
                    PaperTrade.status == PaperTradeStatus.OPEN,
                )
            )
        )
        exposure_by_market: dict[str, Decimal] = {}
        total = ZERO
        for trade in open_trades:
            key = trade.token_id
            market = self.session.get(Market, trade.market_id) if trade.market_id else None
            if market is not None:
                key = market.condition_id
            exposure_by_market[key] = exposure_by_market.get(key, ZERO) + trade.stake_usdc
            total += trade.stake_usdc

        stat = self._daily_stat()
        return RiskState(
            open_positions=len(open_trades),
            total_exposure=total,
            exposure_by_market=exposure_by_market,
            realized_pnl_today=stat.realized_pnl,
            entries_today=stat.trades_entered,
        )

    def _daily_stat(self) -> PaperDailyStat:
        today = today_utc()
        stat = self.session.scalar(
            select(PaperDailyStat).where(PaperDailyStat.stat_date == today)
        )
        if stat is None:
            stat = PaperDailyStat(stat_date=today)
            self.session.add(stat)
            self.session.flush()
        return stat

    def _current_price(self, token_id: str, market: Market | None) -> Decimal | None:
        if self.provider is not None:
            try:
                book = self.provider.get_order_book(token_id)
            except Exception:  # noqa: BLE001
                book = None
            if book is not None and book.midpoint is not None:
                return book.midpoint

        latest = self.session.scalar(
            select(MarketPrice.price)
            .where(MarketPrice.token_id == token_id)
            .order_by(MarketPrice.timestamp.desc())
            .limit(1)
        )
        if latest is not None:
            return latest

        outcome = self.session.scalar(select(Outcome).where(Outcome.token_id == token_id))
        return outcome.last_price if outcome is not None else None

    def _peak_price(self, trade: PaperTrade) -> Decimal | None:
        """Highest observed price since entry, for trailing logic."""
        if trade.entered_at is None:
            return None
        since = int(trade.entered_at.timestamp())
        return self.session.scalar(
            select(func.max(MarketPrice.price)).where(
                MarketPrice.token_id == trade.token_id,
                MarketPrice.timestamp >= since,
            )
        )

    def _wallet_exit_state(self, trade: PaperTrade) -> tuple[bool, bool]:
        """Have the source wallets exited, or begun reducing?"""
        if not trade.signal_id:
            return False, False
        rows = list(
            self.session.scalars(
                select(SignalWallet).where(SignalWallet.signal_id == trade.signal_id)
            )
        )
        if not rows:
            return False, False

        exited = 0
        reduced = 0
        for row in rows:
            position = self.session.scalar(
                select(ReconstructedPosition)
                .where(
                    ReconstructedPosition.wallet_id == row.wallet_id,
                    ReconstructedPosition.token_id == trade.token_id,
                )
                .order_by(ReconstructedPosition.opened_ts.desc())
                .limit(1)
            )
            if position is None:
                continue
            if position.status in (
                PositionStatus.CLOSED,
                PositionStatus.SETTLED,
                PositionStatus.REVERSED,
            ):
                exited += 1
            elif position.status == PositionStatus.PARTIALLY_CLOSED:
                reduced += 1

        # "The wallet exited" means every source wallet is out, not just one of
        # several -- otherwise a single member leaving a consensus closes a
        # position the rest of the group still holds.
        return exited == len(rows), (exited + reduced) > 0

    def _wallet_roi(self, trade: PaperTrade) -> float | None:
        """Realised ROI of the source wallets on this outcome, for comparison."""
        if not trade.signal_id:
            return None
        wallet_ids = list(
            self.session.scalars(
                select(SignalWallet.wallet_id).where(
                    SignalWallet.signal_id == trade.signal_id
                )
            )
        )
        if not wallet_ids:
            return None
        rois = list(
            self.session.scalars(
                select(ReconstructedPosition.roi).where(
                    ReconstructedPosition.wallet_id.in_(wallet_ids),
                    ReconstructedPosition.token_id == trade.token_id,
                    ReconstructedPosition.roi.is_not(None),
                )
            )
        )
        if not rois:
            return None
        return round(sum(rois) / len(rois), 6)

    def _event(
        self,
        trade: PaperTrade,
        event_type: PaperEventType,
        *,
        price: Decimal | None = None,
        shares: Decimal | None = None,
        pnl: Decimal | None = None,
        detail: str | None = None,
    ) -> None:
        self.session.add(
            PaperTradeEvent(
                paper_trade_id=trade.id,
                event_type=event_type,
                occurred_at=self.now,
                price=price,
                shares=shares,
                pnl=pnl,
                detail=detail,
            )
        )


def expire_stale_signals(session: Session, *, now: datetime | None = None) -> int:
    """Move past-expiry signals out of the actionable states."""
    moment = now or datetime.now(timezone.utc)
    rows = list(
        session.scalars(
            select(Signal).where(
                Signal.status.in_((SignalStatus.QUALIFIED, SignalStatus.EVALUATING)),
                Signal.expires_at.is_not(None),
                Signal.expires_at < moment,
            )
        )
    )
    for signal in rows:
        signal.status = SignalStatus.EXPIRED
    if rows:
        log.info("monitor.expired_signals", count=len(rows))
    return len(rows)


def _median_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return [str(x) for x in parsed] if isinstance(parsed, list) else []


__all__ = [
    "LIQUIDITY_BAND",
    "PaperTradeManager",
    "ScanStats",
    "SignalMonitor",
    "expire_stale_signals",
]
