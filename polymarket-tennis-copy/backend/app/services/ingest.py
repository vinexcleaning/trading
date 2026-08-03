"""Ingestion orchestration: provider payloads -> normalized database rows.

Idempotence is the design requirement. Every sync can be re-run over any window
without creating duplicates or double-counting P&L, because:

* raw activity is keyed by ``(wallet_id, dedupe_key)``;
* normalized transactions carry a natural-key uniqueness constraint;
* wallets advance a ``sync_cursor_ts`` only after a successful commit, and the
  next run overlaps that cursor slightly rather than starting after it, so a row
  written mid-pagination upstream cannot be skipped.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..enums import (
    ActivityType,
    JobStatus,
    MarketPhase,
    SportCategory,
    TradeSide,
    WalletSource,
    WalletStatus,
)
from ..logging_setup import get_logger, job_id_var
from ..models import (
    Event,
    IngestionJob,
    LiquiditySnapshot,
    Market,
    MarketPrice,
    NormalizedTransaction,
    Outcome,
    PriceObservationKind,
    RawActivity,
    SchemaDriftEvent,
    SystemError,
    Wallet,
)
from ..providers.base import (
    MarketDataProvider,
    ProviderActivity,
    ProviderEvent,
    ProviderMarket,
)
from .classification import TennisClassifier, match_outcome_to_player

log = get_logger(__name__)

ZERO = Decimal("0")

# Re-read this far behind the cursor so a row inserted upstream while we were
# paginating is not permanently missed.
CURSOR_OVERLAP_SECONDS = 300

# Unknown markets resolved per wallet sync. Bounded because there is no verified
# batch-by-condition-id endpoint, so each one costs a request.
MARKET_BACKFILL_PER_SYNC = 40


@dataclass
class IngestStats:
    """Counters recorded on the ingestion_jobs row."""

    fetched: int = 0
    inserted: int = 0
    duplicates: int = 0
    failed: int = 0
    pages: int = 0
    markets_upserted: int = 0
    events_upserted: int = 0
    notes: list[str] = field(default_factory=list)

    def merge(self, other: IngestStats) -> None:
        self.fetched += other.fetched
        self.inserted += other.inserted
        self.duplicates += other.duplicates
        self.failed += other.failed
        self.pages += other.pages
        self.markets_upserted += other.markets_upserted
        self.events_upserted += other.events_upserted
        self.notes.extend(other.notes)


def http_stats_delta(provider: MarketDataProvider, before: dict | None):
    """HTTP counters attributable to one job.

    A provider's counters are cumulative for its lifetime, so recording the raw
    totals would attribute every earlier request to whichever job finished last.
    """
    from ..providers.http import RequestStats

    current = getattr(provider, "http", None)
    if current is None or not hasattr(current, "stats"):
        return None
    now = current.stats
    if before is None:
        return now
    return RequestStats(
        requests=now.requests - before["requests"],
        retries=now.retries - before["retries"],
        rate_limit_events=now.rate_limit_events - before["rate_limit_events"],
        total_latency_ms=now.total_latency_ms - before["total_latency_ms"],
        failures=now.failures - before["failures"],
    )


def http_stats_snapshot(provider: MarketDataProvider) -> dict | None:
    """Capture cumulative HTTP counters so a job can report only its own."""
    client = getattr(provider, "http", None)
    if client is None or not hasattr(client, "stats"):
        return None
    s = client.stats
    return {
        "requests": s.requests,
        "retries": s.retries,
        "rate_limit_events": s.rate_limit_events,
        "total_latency_ms": s.total_latency_ms,
        "failures": s.failures,
    }


class JobRecorder:
    """Creates and finalises an ``ingestion_jobs`` row with a correlation id."""

    def __init__(
        self, session: Session, job_type: str, target: str | None = None,
        wallet_id: int | None = None,
    ) -> None:
        self.session = session
        self.job_uid = uuid.uuid4().hex[:16]
        self.job = IngestionJob(
            job_type=job_type,
            job_uid=self.job_uid,
            status=JobStatus.RUNNING,
            target=target,
            wallet_id=wallet_id,
        )
        session.add(self.job)
        session.flush()
        self._token = job_id_var.set(self.job_uid)
        self._started = datetime.now(timezone.utc)

    def finish(
        self,
        status: JobStatus,
        stats: IngestStats | None = None,
        *,
        error: str | None = None,
        http_stats=None,
    ) -> None:
        job = self.job
        job.status = status
        job.finished_at = datetime.now(timezone.utc)
        job.duration_ms = int(
            (job.finished_at - self._started).total_seconds() * 1000
        )
        if stats is not None:
            job.records_fetched = stats.fetched
            job.records_inserted = stats.inserted
            job.records_skipped_duplicate = stats.duplicates
            job.records_failed = stats.failed
            job.pages_fetched = stats.pages
            if stats.notes:
                job.detail = json.dumps(stats.notes[:50])
        if http_stats is not None:
            job.http_requests = http_stats.requests
            job.http_retries = http_stats.retries
            job.rate_limit_events = http_stats.rate_limit_events
            job.total_latency_ms = http_stats.total_latency_ms
        if error:
            job.error = error[:4000]
        job_id_var.reset(self._token)


def record_error(
    session: Session,
    *,
    category: str,
    component: str,
    message: str,
    detail: str | None = None,
    severity: str = "error",
    job_uid: str | None = None,
) -> None:
    """Upsert a system error, deduplicated by fingerprint.

    Repeated identical failures increment a counter instead of flooding the table,
    so the error dashboard stays readable during an outage.
    """
    import hashlib

    fingerprint = hashlib.sha256(
        f"{category}|{component}|{message[:200]}".encode()
    ).hexdigest()[:64]

    existing = session.scalar(
        select(SystemError).where(SystemError.fingerprint == fingerprint)
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.occurrence_count += 1
        existing.last_seen_at = now
        existing.resolved = False
        if detail:
            existing.detail = detail[:4000]
    else:
        session.add(
            SystemError(
                severity=severity,
                category=category,
                component=component,
                message=message[:2000],
                detail=(detail or "")[:4000] or None,
                fingerprint=fingerprint,
                job_uid=job_uid,
                first_seen_at=now,
                last_seen_at=now,
            )
        )


def record_schema_drift(session: Session, warnings: list[dict]) -> None:
    """Persist provider schema-drift warnings for operator review."""
    for warning in warnings:
        endpoint = warning.get("endpoint", "unknown")
        missing = json.dumps(warning.get("missing_fields")) if warning.get("missing_fields") else None
        new = json.dumps(warning.get("new_fields")) if warning.get("new_fields") else None

        existing = session.scalar(
            select(SchemaDriftEvent).where(
                SchemaDriftEvent.endpoint == endpoint,
                SchemaDriftEvent.missing_fields == missing,
                SchemaDriftEvent.new_fields == new,
            )
        )
        if existing is not None:
            existing.occurrence_count += 1
            existing.detected_at = datetime.now(timezone.utc)
        else:
            session.add(
                SchemaDriftEvent(
                    endpoint=endpoint, missing_fields=missing, new_fields=new
                )
            )


class MarketIngestor:
    """Upserts events, markets and outcomes, applying classification."""

    def __init__(
        self,
        session: Session,
        provider: MarketDataProvider,
        classifier: TennisClassifier | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.classifier = classifier or TennisClassifier()

    # ------------------------------------------------------------------ sync
    def sync_tennis_markets(
        self, *, closed: bool | None = None, max_pages: int = 5, limit: int = 50
    ) -> IngestStats:
        """Ingest tennis events by tag, both open and resolved."""
        stats = IngestStats()
        targets = [closed] if closed is not None else [False, True]
        recorder = JobRecorder(self.session, "market_sync", target="tennis")
        http_before = http_stats_snapshot(self.provider)

        try:
            for closed_flag in targets:
                for event in self.provider.iter_events(
                    tag_id=self.settings.tennis_tag_id,
                    closed=closed_flag,
                    limit=limit,
                    max_pages=max_pages,
                ):
                    stats.fetched += 1
                    try:
                        self.upsert_event(event)
                        stats.events_upserted += 1
                        for market in event.markets:
                            self.upsert_market(market, event_slug=event.slug)
                            stats.markets_upserted += 1
                    except Exception as exc:  # noqa: BLE001
                        stats.failed += 1
                        log.warning(
                            "ingest.market_failed", event=event.event_id, error=str(exc)
                        )
        except Exception as exc:
            recorder.finish(
                JobStatus.FAILED,
                stats,
                error=str(exc),
                http_stats=http_stats_delta(self.provider, http_before),
            )
            self.session.flush()
            raise

        recorder.finish(
            JobStatus.PARTIAL if stats.failed else JobStatus.SUCCESS,
            stats,
            http_stats=http_stats_delta(self.provider, http_before),
        )
        self.session.flush()
        return stats

    def upsert_event(self, data: ProviderEvent) -> Event:
        event = self.session.scalar(
            select(Event).where(Event.gamma_event_id == data.event_id)
        )
        if event is None:
            event = Event(gamma_event_id=data.event_id)
            self.session.add(event)

        event.slug = data.slug
        event.ticker = data.ticker
        event.title = data.title
        event.description = data.description
        event.tags = json.dumps(data.tags) if data.tags else None
        event.start_date = data.start_date
        event.end_date = data.end_date
        event.active = data.active
        event.closed = data.closed
        event.liquidity = data.liquidity
        event.volume = data.volume
        event.volume_24hr = data.volume_24hr
        event.synced_at = datetime.now(timezone.utc)

        # Event-level tennis metadata is taken from the first market that
        # classifies confidently, since match titles live on markets.
        if data.markets:
            result = self.classifier.classify(data.markets[0])
            event.sport_category = result.sport_category
            event.tournament = result.tournament
            event.player_a = result.player_a
            event.player_b = result.player_b
            event.best_of = result.best_of
            event.surface = result.surface
            event.tour = result.tour
        else:
            tags = {t.lower() for t in data.tags}
            event.sport_category = (
                SportCategory.TENNIS
                if self.settings.tennis_tag_slug in tags
                else SportCategory.UNKNOWN
            )

        self.session.flush()
        return event

    def upsert_market(
        self, data: ProviderMarket, *, event_slug: str | None = None
    ) -> Market:
        market = self.session.scalar(
            select(Market).where(Market.condition_id == data.condition_id)
        )
        if market is None:
            market = Market(condition_id=data.condition_id)
            self.session.add(market)

        result = self.classifier.classify(data)

        market.gamma_market_id = data.gamma_market_id
        market.question_id = data.question_id
        market.slug = data.slug
        market.question = data.question
        market.description = data.description

        if data.event_id:
            event = self.session.scalar(
                select(Event).where(Event.gamma_event_id == data.event_id)
            )
            if event is not None:
                market.event_id = event.id

        # A human review decision outranks re-classification.
        if not market.reviewed_by_human:
            market.sport_category = result.sport_category
            market.is_tennis = result.is_tennis
            market.tennis_market_type = result.market_type
            market.classification_confidence = result.confidence
            market.classification_methods = result.methods_json()
            market.classification_notes = result.notes_text()
            market.needs_review = result.needs_review
            market.period_number = result.period_number
        market.sports_market_type_raw = data.sports_market_type

        market.game_start_time = data.game_start_time
        market.start_date = data.start_date
        market.end_date = data.end_date

        market.active = data.active
        market.closed = data.closed
        market.archived = data.archived
        market.accepting_orders = data.accepting_orders
        market.enable_order_book = data.enable_order_book
        market.neg_risk = data.neg_risk

        market.resolved = data.resolved
        market.winning_outcome_index = data.winning_outcome_index
        market.uma_resolution_statuses = data.uma_resolution_statuses
        if data.resolved and market.resolved_at is None:
            # Best available proxy: the venue does not expose a resolution time.
            market.resolved_at = data.end_date or datetime.now(timezone.utc)

        market.liquidity = data.liquidity
        market.volume = data.volume
        market.volume_24hr = data.volume_24hr
        market.spread = data.spread
        market.best_bid = data.best_bid
        market.best_ask = data.best_ask
        market.last_trade_price = data.last_trade_price
        market.tick_size = data.tick_size
        market.min_order_size = data.min_order_size
        market.maker_fee_bps = data.maker_fee_bps
        market.taker_fee_bps = data.taker_fee_bps
        market.synced_at = datetime.now(timezone.utc)

        self.session.flush()

        for outcome_data in data.outcomes:
            outcome = self.session.scalar(
                select(Outcome).where(Outcome.token_id == outcome_data.token_id)
            )
            if outcome is None:
                outcome = Outcome(
                    token_id=outcome_data.token_id,
                    market_id=market.id,
                    outcome_index=outcome_data.outcome_index,
                    label=outcome_data.label,
                )
                self.session.add(outcome)
            outcome.market_id = market.id
            outcome.label = outcome_data.label
            outcome.outcome_index = outcome_data.outcome_index
            outcome.last_price = outcome_data.price
            outcome.player_name = match_outcome_to_player(
                outcome_data.label, result.player_a, result.player_b
            )
            if data.winning_outcome_index is not None:
                outcome.is_winner = outcome_data.outcome_index == data.winning_outcome_index

        self.session.flush()
        return market

    # ---------------------------------------------------------------- prices
    def ingest_market_trades(self, market: Market, *, max_pages: int = 2) -> IngestStats:
        """Ingest the public trade tape -- the second-level price evidence."""
        stats = IngestStats()
        trades = self.provider.get_market_trades(
            market.condition_id, limit=self.settings.trades_page_size, max_pages=max_pages
        )
        stats.fetched = len(trades)
        if not trades:
            stats.notes.append(
                f"no trade prints for {market.condition_id[:12]}...; sub-minute "
                "delay analysis is unavailable for this market"
            )
            return stats

        # Existing (token, ts, price) keys, so re-ingesting a window is a no-op.
        existing = {
            (row[0], row[1], str(row[2]))
            for row in self.session.execute(
                select(MarketPrice.token_id, MarketPrice.timestamp, MarketPrice.price).where(
                    MarketPrice.market_id == market.id,
                    MarketPrice.kind == PriceObservationKind.TRADE_PRINT,
                )
            )
        }

        for trade in trades:
            key = (trade.token_id, trade.timestamp, str(trade.price))
            if key in existing:
                stats.duplicates += 1
                continue
            existing.add(key)
            self.session.add(
                MarketPrice(
                    token_id=trade.token_id,
                    market_id=market.id,
                    timestamp=trade.timestamp,
                    observed_at=datetime.fromtimestamp(trade.timestamp, tz=timezone.utc),
                    kind=PriceObservationKind.TRADE_PRINT,
                    price=trade.price,
                    size=trade.size,
                    side=trade.side,
                    source=self.provider.name,
                )
            )
            stats.inserted += 1
        self.session.flush()
        return stats

    def ingest_price_history(
        self,
        outcome: Outcome,
        *,
        interval: str = "1d",
        fidelity_minutes: int = 1,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> IngestStats:
        """Ingest minute bars. Never finer than 1 minute -- a venue limit.

        When a window is given, the explicit ``startTs``/``endTs`` form is used: it
        returns 1-minute resolution over spans of a week or more, whereas the
        named-interval form is clamped to a coarser minimum (5 minutes for ``1w``,
        10 for ``1m``). Finer bars mean better delay analysis, so a window is
        always preferable when the range of interest is known.
        """
        stats = IngestStats()
        points = self.provider.get_price_history(
            outcome.token_id,
            interval=interval,
            fidelity_minutes=fidelity_minutes,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        stats.fetched = len(points)

        existing = {
            row[0]
            for row in self.session.execute(
                select(MarketPrice.timestamp).where(
                    MarketPrice.token_id == outcome.token_id,
                    MarketPrice.kind == PriceObservationKind.MINUTE_BAR,
                )
            )
        }
        for point in points:
            if point.timestamp in existing:
                stats.duplicates += 1
                continue
            existing.add(point.timestamp)
            self.session.add(
                MarketPrice(
                    token_id=outcome.token_id,
                    market_id=outcome.market_id,
                    timestamp=point.timestamp,
                    observed_at=datetime.fromtimestamp(point.timestamp, tz=timezone.utc),
                    kind=PriceObservationKind.MINUTE_BAR,
                    price=point.price,
                    source=self.provider.name,
                )
            )
            stats.inserted += 1
        self.session.flush()
        return stats

    def snapshot_liquidity(self, outcome: Outcome) -> LiquiditySnapshot | None:
        """Capture book depth, which is what actually limits a follower."""
        book = self.provider.get_order_book(outcome.token_id)
        if book is None:
            return None

        existing = self.session.scalar(
            select(LiquiditySnapshot).where(
                LiquiditySnapshot.token_id == outcome.token_id,
                LiquiditySnapshot.timestamp == book.timestamp,
            )
        )
        if existing is not None:
            return existing

        snapshot = LiquiditySnapshot(
            token_id=outcome.token_id,
            market_id=outcome.market_id,
            timestamp=book.timestamp,
            observed_at=datetime.fromtimestamp(book.timestamp, tz=timezone.utc),
            best_bid=book.best_bid,
            best_ask=book.best_ask,
            midpoint=book.midpoint,
            spread=book.spread,
            bid_depth_usdc=book.bid_depth_usdc(),
            ask_depth_usdc=book.ask_depth_usdc(),
            # Depth near touch is the practically fillable size; total depth
            # overstates it by orders of magnitude on thin markets.
            ask_depth_1c_usdc=book.ask_depth_usdc(Decimal("0.01")),
            ask_depth_5c_usdc=book.ask_depth_usdc(Decimal("0.05")),
            tick_size=book.tick_size,
            bids_json=json.dumps([[str(l.price), str(l.size)] for l in book.bids[:20]]),
            asks_json=json.dumps([[str(l.price), str(l.size)] for l in book.asks[:20]]),
            source=self.provider.name,
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot


def backfill_price_evidence(
    session: Session,
    provider: MarketDataProvider,
    *,
    max_markets: int = 25,
    window_days: int = 30,
    settings: Settings | None = None,
) -> IngestStats:
    """Ingest price evidence for tennis markets where wallets hold positions.

    This is the job that makes copyability measurable. Without it, positions fall
    back to modelled prices, which are excluded from copyable ROI by design -- so
    every wallet reads as unassessable no matter how good it is.

    Markets are prioritised by how many tracked positions they contain, so the
    evidence that unlocks the most analysis is fetched first. Both sources are
    ingested because they answer different questions:

    * trade prints -- second-level, the only usable evidence for short delays;
    * minute bars  -- dense coverage for longer delays and for gaps in the tape.
    """
    from ..models import ReconstructedPosition

    cfg = settings or get_settings()
    stats = IngestStats()
    ingestor = MarketIngestor(session, provider, settings=cfg)
    recorder = JobRecorder(session, "price_backfill", target="tennis_positions")
    http_before = http_stats_snapshot(provider)

    def _finish(status: JobStatus, error: str | None = None) -> None:
        recorder.finish(
            status, stats, error=error, http_stats=http_stats_delta(provider, http_before)
        )
        session.flush()

    # Markets holding tracked tennis positions, busiest first.
    rows = session.execute(
        select(
            ReconstructedPosition.market_id,
            func.count(ReconstructedPosition.id).label("n"),
            func.min(ReconstructedPosition.opened_ts).label("first_ts"),
            func.max(func.coalesce(ReconstructedPosition.closed_ts,
                                   ReconstructedPosition.opened_ts)).label("last_ts"),
        )
        .where(
            ReconstructedPosition.is_tennis.is_(True),
            ReconstructedPosition.market_id.is_not(None),
        )
        .group_by(ReconstructedPosition.market_id)
        .order_by(func.count(ReconstructedPosition.id).desc())
        .limit(max_markets)
    ).all()

    if not rows:
        stats.notes.append("no tennis positions yet; nothing to backfill")
        _finish(JobStatus.SUCCESS)
        return stats

    for market_id, position_count, first_ts, last_ts in rows:
        market = session.get(Market, market_id)
        if market is None:
            continue

        try:
            trade_stats = ingestor.ingest_market_trades(market, max_pages=2)
            stats.merge(trade_stats)
        except Exception as exc:  # noqa: BLE001
            stats.failed += 1
            log.warning(
                "ingest.trade_backfill_failed",
                condition_id=market.condition_id,
                error=str(exc),
            )

        # Window the bar request around the positions, padded so the delay
        # windows at either end are covered. The explicit-window form returns
        # 1-minute bars regardless of span; the named-interval form would be
        # clamped coarser.
        pad = 3600
        start_ts = max(0, int(first_ts) - pad)
        end_ts = int(last_ts) + pad
        # Bound the span so a long-dormant position cannot request a huge range.
        max_span = window_days * 86400
        if end_ts - start_ts > max_span:
            start_ts = end_ts - max_span

        for outcome in session.scalars(
            select(Outcome).where(Outcome.market_id == market.id)
        ):
            try:
                bar_stats = ingestor.ingest_price_history(
                    outcome, fidelity_minutes=1, start_ts=start_ts, end_ts=end_ts
                )
                stats.merge(bar_stats)
                if not market.closed:
                    # Depth only matters for markets still tradeable.
                    ingestor.snapshot_liquidity(outcome)
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                log.warning(
                    "ingest.bar_backfill_failed",
                    token_id=outcome.token_id,
                    error=str(exc),
                )

        log.debug(
            "ingest.price_backfill_market",
            condition_id=market.condition_id,
            positions=position_count,
        )

    _finish(JobStatus.PARTIAL if stats.failed else JobStatus.SUCCESS)
    return stats


class WalletIngestor:
    """Ingests wallet activity and normalizes it."""

    def __init__(
        self,
        session: Session,
        provider: MarketDataProvider,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.market_ingestor = MarketIngestor(session, provider, settings=self.settings)

    def sync_wallet(
        self, wallet: Wallet, *, full_backfill: bool = False, max_pages: int | None = None
    ) -> IngestStats:
        """Fetch and store new activity for one wallet.

        Incremental by default: starts slightly *before* the stored cursor so a
        row inserted upstream mid-pagination cannot be skipped. Duplicates are
        absorbed by the dedupe constraint, which makes the overlap free.
        """
        recorder = JobRecorder(
            self.session, "wallet_sync", target=wallet.address, wallet_id=wallet.id
        )
        http_before = http_stats_snapshot(self.provider)
        try:
            stats = self._sync_wallet_inner(
                wallet, full_backfill=full_backfill, max_pages=max_pages
            )
        except Exception as exc:
            recorder.finish(
                JobStatus.FAILED,
                error=str(exc),
                http_stats=http_stats_delta(self.provider, http_before),
            )
            self.session.flush()
            raise
        recorder.finish(
            JobStatus.PARTIAL if stats.failed else JobStatus.SUCCESS,
            stats,
            http_stats=http_stats_delta(self.provider, http_before),
        )
        self.session.flush()
        return stats

    def _sync_wallet_inner(
        self, wallet: Wallet, *, full_backfill: bool = False, max_pages: int | None = None
    ) -> IngestStats:
        stats = IngestStats()

        start_ts: int | None = None
        if not full_backfill and wallet.sync_cursor_ts:
            start_ts = max(0, wallet.sync_cursor_ts - CURSOR_OVERLAP_SECONDS)
        elif not wallet.backfill_complete:
            cutoff = datetime.now(timezone.utc) - timedelta(
                days=self.settings.wallet_backfill_days
            )
            start_ts = int(cutoff.timestamp())

        highest_ts = wallet.sync_cursor_ts or 0
        activities: list[ProviderActivity] = []

        for activity in self.provider.iter_wallet_activity(
            wallet.address, start_ts=start_ts, max_pages=max_pages
        ):
            stats.fetched += 1
            activities.append(activity)
            highest_ts = max(highest_ts, activity.timestamp)

        if not activities:
            wallet.last_synced_at = datetime.now(timezone.utc)
            wallet.last_sync_success_at = wallet.last_synced_at
            self.session.flush()
            return stats

        # Ensure markets exist before normalizing, so transactions can be joined.
        self._ensure_markets(activities, stats)

        for activity in activities:
            try:
                inserted = self._store_activity(wallet, activity)
                if inserted:
                    stats.inserted += 1
                else:
                    stats.duplicates += 1
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                log.warning(
                    "ingest.activity_failed",
                    wallet=wallet.address,
                    tx=activity.transaction_hash,
                    error=str(exc),
                )

        now = datetime.now(timezone.utc)
        wallet.sync_cursor_ts = highest_ts
        wallet.last_synced_at = now
        wallet.last_sync_success_at = now
        wallet.last_sync_error = None
        wallet.last_activity_at = datetime.fromtimestamp(highest_ts, tz=timezone.utc)
        if wallet.first_activity_at is None:
            lowest = min(a.timestamp for a in activities)
            wallet.first_activity_at = datetime.fromtimestamp(lowest, tz=timezone.utc)
        if full_backfill or start_ts is None:
            wallet.backfill_complete = True

        try:
            value = self.provider.get_wallet_value(wallet.address)
            if value is not None:
                wallet.observed_portfolio_value = value
        except Exception as exc:  # noqa: BLE001
            # Portfolio value is contextual, not required; never fail a sync on it.
            log.debug("ingest.value_unavailable", wallet=wallet.address, error=str(exc))

        self.session.flush()
        return stats

    def _ensure_markets(self, activities: list[ProviderActivity], stats: IngestStats) -> None:
        """Backfill markets referenced by activity but not yet stored.

        Most wallets trade far more non-tennis markets than tennis ones, and there
        is no verified batch-by-condition-id endpoint, so an unbounded backfill
        would issue thousands of requests to learn that markets are irrelevant.

        Instead the tennis universe is populated from Gamma by tag, and this only
        tops up a bounded number of unknown ids per run -- ordered by how often the
        wallet touched them, so the markets it actually trades are resolved first.
        Successive syncs converge. Activity against a still-unknown market keeps
        ``market_id = NULL`` and ``is_tennis = False``, which is accurate rather
        than a gap.
        """
        counts: dict[str, int] = {}
        for activity in activities:
            if activity.condition_id:
                counts[activity.condition_id] = counts.get(activity.condition_id, 0) + 1
        if not counts:
            return

        known = {
            row[0]
            for row in self.session.execute(
                select(Market.condition_id).where(Market.condition_id.in_(counts.keys()))
            )
        }
        missing = [c for c in counts if c not in known]
        if not missing:
            return

        # Most-traded first, then deterministic by id for reproducible runs.
        missing.sort(key=lambda c: (-counts[c], c))
        batch = missing[: MARKET_BACKFILL_PER_SYNC]
        deferred = len(missing) - len(batch)

        try:
            markets = self.provider.get_markets_by_condition_ids(batch)
            for market in markets:
                self.market_ingestor.upsert_market(market)
                stats.markets_upserted += 1
        except Exception as exc:  # noqa: BLE001
            stats.notes.append(f"market backfill failed for {len(batch)} markets: {exc}")
            log.warning("ingest.market_backfill_failed", count=len(batch), error=str(exc))
            return

        if deferred:
            # Never silently truncate: the operator sees what was left behind.
            stats.notes.append(
                f"{deferred} unknown markets deferred to a later sync "
                f"(cap {MARKET_BACKFILL_PER_SYNC}/run)"
            )
            log.info("ingest.market_backfill_deferred", deferred=deferred)

    def _store_activity(self, wallet: Wallet, activity: ProviderActivity) -> bool:
        """Store raw + normalized rows. Returns False when already present."""
        existing = self.session.scalar(
            select(RawActivity.id).where(
                RawActivity.wallet_id == wallet.id,
                RawActivity.dedupe_key == activity.dedupe_key,
            )
        )
        if existing is not None:
            return False

        raw_id: int | None = None
        if self.settings.store_raw_responses:
            raw = RawActivity(
                wallet_id=wallet.id,
                source=self.provider.name,
                endpoint="data/activity",
                dedupe_key=activity.dedupe_key,
                transaction_hash=activity.transaction_hash,
                activity_timestamp=activity.timestamp,
                payload=json.dumps(activity.raw, default=str),
            )
            self.session.add(raw)
            try:
                self.session.flush()
                raw_id = raw.id
            except IntegrityError:
                # Concurrent insert of the same row: treat as duplicate.
                self.session.rollback()
                return False

        market = None
        outcome = None
        if activity.condition_id:
            market = self.session.scalar(
                select(Market).where(Market.condition_id == activity.condition_id)
            )
        if activity.token_id:
            outcome = self.session.scalar(
                select(Outcome).where(Outcome.token_id == activity.token_id)
            )

        phase = MarketPhase.UNKNOWN
        seconds_to_start: int | None = None
        occurred_at = datetime.fromtimestamp(activity.timestamp, tz=timezone.utc)
        if market is not None and market.game_start_time is not None:
            delta = (market.game_start_time - occurred_at).total_seconds()
            seconds_to_start = int(delta)
            phase = MarketPhase.PREMATCH if delta > 0 else MarketPhase.LIVE

        try:
            activity_type = ActivityType(activity.activity_type)
        except ValueError:
            activity_type = ActivityType.UNKNOWN

        tx = NormalizedTransaction(
            wallet_id=wallet.id,
            raw_activity_id=raw_id,
            market_id=market.id if market is not None else None,
            outcome_id=outcome.id if outcome is not None else None,
            condition_id=activity.condition_id,
            token_id=activity.token_id,
            outcome_index=(
                activity.outcome_index
                if activity.outcome_index is not None
                else (outcome.outcome_index if outcome is not None else None)
            ),
            activity_type=activity_type,
            side=(
                TradeSide(activity.side).value
                if activity.side in (TradeSide.BUY, TradeSide.SELL)
                else None
            ),
            size=activity.size,
            price=activity.price,
            usdc_size=activity.usdc_size,
            timestamp=activity.timestamp,
            occurred_at=occurred_at,
            transaction_hash=activity.transaction_hash,
            market_phase=phase,
            seconds_to_start=seconds_to_start,
            is_tennis=bool(market is not None and market.is_tennis),
        )
        self.session.add(tx)
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            return False
        return True


class WalletRegistry:
    """Wallet CRUD, CSV import and discovery.

    Discovery never auto-approves. A leaderboard position reflects total volume
    or profit across every category on the platform and says nothing about tennis
    skill or copyability, so discovered wallets land unapproved and inactive for
    alerting until a human or the metrics pipeline promotes them.
    """

    def __init__(
        self,
        session: Session,
        provider: MarketDataProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()

    def add_wallet(
        self,
        address: str,
        *,
        nickname: str | None = None,
        source: str = WalletSource.MANUAL,
        source_detail: str | None = None,
        manually_approved: bool = False,
        notes: str | None = None,
        on_watchlist: bool = False,
        sync_priority: int = 100,
    ) -> tuple[Wallet, bool]:
        """Add or fetch a wallet. Returns ``(wallet, created)``."""
        normalized = self._normalise_address(address)
        existing = self.session.scalar(
            select(Wallet).where(Wallet.address == normalized)
        )
        if existing is not None:
            return existing, False

        wallet = Wallet(
            address=normalized,
            nickname=nickname,
            source=source,
            source_detail=source_detail,
            manually_approved=manually_approved,
            approved_at=datetime.now(timezone.utc) if manually_approved else None,
            notes=notes,
            on_watchlist=on_watchlist,
            sync_priority=sync_priority,
            status=WalletStatus.ACTIVE,
        )
        self.session.add(wallet)
        self.session.flush()
        log.info(
            "registry.wallet_added",
            address=normalized,
            source=source,
            approved=manually_approved,
        )
        return wallet, True

    def import_csv(self, content: str) -> dict:
        """Import wallets from CSV.

        Accepts ``address`` plus optional ``nickname``, ``notes``, ``tags``.
        Malformed rows are reported rather than silently dropped.
        """
        import csv
        import io

        reader = csv.DictReader(io.StringIO(content))
        added = 0
        skipped = 0
        errors: list[str] = []

        for line_no, row in enumerate(reader, start=2):
            normalized_row = {
                (k or "").strip().lower(): (v or "").strip() for k, v in row.items()
            }
            address = normalized_row.get("address") or normalized_row.get("wallet")
            if not address:
                errors.append(f"line {line_no}: missing address column")
                continue
            if not self._is_valid_address(address):
                errors.append(f"line {line_no}: {address!r} is not a valid address")
                continue

            _, created = self.add_wallet(
                address,
                nickname=normalized_row.get("nickname") or None,
                notes=normalized_row.get("notes") or None,
                source=WalletSource.CSV_IMPORT,
                source_detail=f"csv line {line_no}",
                # Import is an explicit human act, so approval is implied.
                manually_approved=True,
            )
            if created:
                added += 1
            else:
                skipped += 1

        return {"added": added, "skipped_existing": skipped, "errors": errors}

    def discover_from_leaderboard(
        self, *, metric: str = "volume", window: str = "30d", limit: int = 50
    ) -> dict:
        """Add leaderboard wallets as unapproved candidates."""
        if self.provider is None:
            raise RuntimeError("discovery requires a provider")

        entries = self.provider.get_leaderboard(metric=metric, window=window, limit=limit)
        added = 0
        for entry in entries:
            _, created = self.add_wallet(
                entry.wallet_address,
                nickname=entry.pseudonym or None,
                source=(
                    WalletSource.LEADERBOARD_PROFIT
                    if metric.startswith("profit")
                    else WalletSource.LEADERBOARD_VOLUME
                ),
                source_detail=f"{metric} {window}: {entry.amount}",
                # Never trusted: platform-wide volume says nothing about tennis.
                manually_approved=False,
                sync_priority=50,
                notes=(
                    "Discovered from a public leaderboard. Platform-wide ranking "
                    "is not evidence of tennis skill or copyability."
                ),
            )
            if created:
                added += 1
        return {"candidates": len(entries), "added": added, "auto_approved": 0}

    def discover_from_tennis_markets(self, *, limit_per_market: int = 25) -> dict:
        """Find wallets active in tennis markets specifically.

        A far better discovery source than a global leaderboard, because it starts
        from the category we actually care about.
        """
        if self.provider is None:
            raise RuntimeError("discovery requires a provider")

        markets = list(
            self.session.scalars(
                select(Market)
                .where(Market.is_tennis.is_(True), Market.closed.is_(False))
                .order_by(Market.volume_24hr.desc().nullslast())
                .limit(10)
            )
        )
        added = 0
        seen = 0
        for market in markets:
            try:
                trades = self.provider.get_market_trades(
                    market.condition_id, limit=limit_per_market, max_pages=1
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "registry.discovery_failed",
                    market=market.condition_id,
                    error=str(exc),
                )
                continue
            for address in {t.wallet_address for t in trades if t.wallet_address}:
                seen += 1
                _, created = self.add_wallet(
                    address,
                    source=WalletSource.MARKET_ACTIVITY,
                    source_detail=f"active in {market.slug or market.condition_id[:12]}",
                    manually_approved=False,
                    sync_priority=75,
                    notes="Discovered trading a tennis market. Unverified.",
                )
                if created:
                    added += 1
        return {"candidates": seen, "added": added, "auto_approved": 0}

    def wallets_due_for_sync(self, limit: int | None = None) -> list[Wallet]:
        """Active wallets ordered by priority then staleness."""
        cap = limit or self.settings.max_wallets_per_sync_cycle
        return list(
            self.session.scalars(
                select(Wallet)
                .where(Wallet.status == WalletStatus.ACTIVE)
                .order_by(
                    Wallet.sync_priority.desc(),
                    Wallet.last_sync_success_at.asc().nullsfirst(),
                )
                .limit(cap)
            )
        )

    @staticmethod
    def _normalise_address(address: str) -> str:
        return address.strip().lower()

    @staticmethod
    def _is_valid_address(address: str) -> bool:
        candidate = address.strip()
        if not candidate.startswith("0x") or len(candidate) != 42:
            return False
        try:
            int(candidate, 16)
        except ValueError:
            return False
        return True


def load_manual_overrides(session: Session) -> dict[str, dict[str, str]]:
    """Build the ``condition_id -> {field: value}`` map for the classifier."""
    from ..models import ManualOverride

    overrides: dict[str, dict[str, str]] = {}
    rows = session.scalars(
        select(ManualOverride).where(
            ManualOverride.entity_type == "market", ManualOverride.active.is_(True)
        )
    )
    for row in rows:
        overrides.setdefault(row.entity_key, {})[row.field] = row.value or ""
    return overrides


def build_price_series(session: Session, token_id: str):
    """Load a :class:`PriceSeries` for one token from stored observations."""
    from .prices import PriceSeries

    series = PriceSeries(token_id=token_id)
    rows = session.execute(
        select(MarketPrice.timestamp, MarketPrice.price, MarketPrice.size, MarketPrice.kind)
        .where(MarketPrice.token_id == token_id)
        .order_by(MarketPrice.timestamp)
    )
    for timestamp, price, size, kind in rows:
        if kind == PriceObservationKind.TRADE_PRINT:
            series.trade_ts.append(timestamp)
            series.trade_px.append(price)
            series.trade_size.append(size or ZERO)
        elif kind == PriceObservationKind.MINUTE_BAR:
            series.bar_ts.append(timestamp)
            series.bar_px.append(price)
    return series


def data_freshness(session: Session) -> dict:
    """Freshness indicators for the health endpoint."""
    now = datetime.now(timezone.utc)
    last_market_sync = session.scalar(select(func.max(Market.synced_at)))
    last_wallet_sync = session.scalar(select(func.max(Wallet.last_sync_success_at)))
    last_job = session.scalar(select(func.max(IngestionJob.finished_at)))

    def age(value: datetime | None) -> float | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return round((now - value).total_seconds(), 1)

    return {
        "last_market_sync": last_market_sync.isoformat() if last_market_sync else None,
        "last_market_sync_age_seconds": age(last_market_sync),
        "last_wallet_sync": last_wallet_sync.isoformat() if last_wallet_sync else None,
        "last_wallet_sync_age_seconds": age(last_wallet_sync),
        "last_job_finished": last_job.isoformat() if last_job else None,
        "last_job_age_seconds": age(last_job),
    }
