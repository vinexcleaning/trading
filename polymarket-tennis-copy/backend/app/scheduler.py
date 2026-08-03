"""Background job scheduling.

APScheduler runs in-process: this is a single-operator analytics tool, and a
Celery broker would add failure modes without buying anything. Each job owns its
own session and swallows its own exceptions so one failing job cannot take the
scheduler -- or the API -- down with it.

Jobs are deliberately ordered by dependency. Price backfill must run before
metrics, because copyable ROI only counts trades with real price evidence; a
metrics pass over un-backfilled markets produces "unassessable" for every wallet.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete, func, select

from .config import get_settings
from .db import session_scope
from .logging_setup import get_logger
from .providers import PolymarketProvider

log = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None
# Last outcome per job, surfaced by the health endpoint.
_last_runs: dict[str, dict[str, Any]] = {}


def _record(job_id: str, *, ok: bool, detail: Any = None, error: str | None = None) -> None:
    _last_runs[job_id] = {
        "job": job_id,
        "ok": ok,
        "at": datetime.now(timezone.utc).isoformat(),
        "detail": detail,
        "error": error,
    }


def _job(job_id: str):
    """Wrap a job so failures are recorded, logged and contained."""

    def decorator(fn):
        def wrapper(*args, **kwargs):
            started = datetime.now(timezone.utc)
            try:
                result = fn(*args, **kwargs)
                _record(job_id, ok=True, detail=result)
                log.info(
                    "job.completed",
                    job=job_id,
                    seconds=round((datetime.now(timezone.utc) - started).total_seconds(), 2),
                )
                return result
            except Exception as exc:  # noqa: BLE001 - the scheduler must survive
                _record(job_id, ok=False, error=str(exc)[:500])
                log.exception("job.failed", job=job_id)
                _notify_failure(job_id, exc)
                return None

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator


def _notify_failure(job_id: str, exc: Exception) -> None:
    """Tell the operator when the data pipeline breaks."""
    try:
        from .services.notifications import (
            NotificationDispatcher,
            build_pipeline_failure_notification,
        )

        dispatcher = NotificationDispatcher()
        dispatcher.dispatch(build_pipeline_failure_notification(job_id, str(exc)[:500]))
    except Exception:  # noqa: BLE001 - never let alerting failures mask the real error
        log.warning("job.failure_notification_failed", job=job_id)


# ------------------------------------------------------------------- the jobs


@_job("market_sync")
def sync_markets() -> dict:
    """Refresh tennis events, markets and outcomes from Gamma."""
    from .services.ingest import MarketIngestor

    provider = PolymarketProvider()
    try:
        with session_scope() as session:
            stats = MarketIngestor(session, provider).sync_tennis_markets(max_pages=6)
            return {
                "fetched": stats.fetched,
                "inserted": stats.inserted,
                "markets_upserted": stats.markets_upserted,
            }
    finally:
        provider.close()


@_job("wallet_sync")
def sync_wallets() -> dict:
    """Incrementally sync activity for the wallets due for a refresh."""
    from .services.ingest import WalletIngestor, WalletRegistry

    provider = PolymarketProvider()
    synced = 0
    failed = 0
    try:
        with session_scope() as session:
            registry = WalletRegistry(session, provider)
            due = registry.wallets_due_for_sync()
            ingestor = WalletIngestor(session, provider)
            for wallet in due:
                try:
                    ingestor.sync_wallet(wallet, max_pages=3)
                    session.flush()
                    synced += 1
                except Exception as exc:  # noqa: BLE001 - isolate per wallet
                    failed += 1
                    wallet.last_sync_error = str(exc)[:2000]
                    log.warning(
                        "job.wallet_sync_failed", address=wallet.address, error=str(exc)
                    )
            return {"due": len(due), "synced": synced, "failed": failed}
    finally:
        provider.close()


@_job("price_backfill")
def backfill_prices() -> dict:
    """Fetch price evidence for markets where tracked wallets hold positions."""
    from .services.ingest import backfill_price_evidence

    provider = PolymarketProvider()
    try:
        with session_scope() as session:
            stats = backfill_price_evidence(session, provider, max_markets=15)
            return {"fetched": stats.fetched, "inserted": stats.inserted}
    finally:
        provider.close()


@_job("analytics")
def recompute_analytics() -> dict:
    """Reconstruct positions, score copyability, recompute metrics and scores."""
    from .services.pipeline import AnalyticsPipeline

    with session_scope() as session:
        pipeline = AnalyticsPipeline(session)
        stats = pipeline.run_full()
        clusters = pipeline.compute_clusters()
        return {
            "positions": stats.positions_written,
            "copyability_rows": stats.copyability_rows,
            "wallets_scored": stats.wallets_scored,
            "clusters": clusters,
        }


@_job("signal_scan")
def scan_signals() -> dict:
    """Evaluate recent qualified-wallet activity and emit alerts."""
    from .services.monitor import SignalMonitor, expire_stale_signals

    provider = PolymarketProvider()
    try:
        with session_scope() as session:
            stats = SignalMonitor(session, provider).scan()
            expired = expire_stale_signals(session)
            payload = stats.as_dict()
            payload["expired"] = expired
            return payload
    finally:
        provider.close()


@_job("paper_manage")
def manage_paper_trades() -> dict:
    """Mark open simulated positions and apply exit rules."""
    from .services.monitor import PaperTradeManager

    provider = PolymarketProvider()
    try:
        with session_scope() as session:
            return PaperTradeManager(session, provider).manage_open_trades()
    finally:
        provider.close()


@_job("data_quality")
def snapshot_data_quality() -> dict:
    """Record a data-quality snapshot for the health panel."""
    from .services.pipeline import data_quality_snapshot

    with session_scope() as session:
        snapshot = data_quality_snapshot(session)
        return {
            "warnings": len(snapshot.get("warnings", [])),
            "avg_data_confidence": snapshot.get("avg_data_confidence"),
        }


@_job("daily_summary")
def send_daily_summary() -> dict:
    """Send the daily paper-trading summary."""
    from .models import PaperTrade, Signal
    from .services.notifications import (
        NotificationDispatcher,
        build_daily_summary_notification,
    )
    from .services.paper import summarise_paper_trades

    with session_scope() as session:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        rows = list(
            session.execute(
                select(
                    PaperTrade.status,
                    PaperTrade.stake_usdc,
                    PaperTrade.realized_pnl,
                    PaperTrade.unrealized_pnl,
                    PaperTrade.is_win,
                    PaperTrade.roi_gap_vs_wallet,
                    PaperTrade.rejection_reason,
                ).where(PaperTrade.is_backtest.is_(False), PaperTrade.created_at >= since)
            )
        )
        summary = summarise_paper_trades(
            [
                {
                    "status": r[0],
                    "stake_usdc": r[1],
                    "realized_pnl": r[2],
                    "unrealized_pnl": r[3],
                    "is_win": r[4],
                    "roi_gap_vs_wallet": r[5],
                    "rejection_reason": r[6],
                }
                for r in rows
            ]
        )
        signals = (
            session.scalar(
                select(func.count(Signal.id)).where(Signal.detected_at >= since)
            )
            or 0
        )
        qualified = (
            session.scalar(
                select(func.count(Signal.id)).where(
                    Signal.detected_at >= since, Signal.qualified.is_(True)
                )
            )
            or 0
        )

        stats = {
            "signals": signals,
            "qualified": qualified,
            "rejected": signals - qualified,
            "paper_trades": summary.trades,
            "paper_closed": summary.closed_trades,
            "paper_realized_pnl": str(summary.realized_pnl),
            "paper_roi": summary.roi,
            "paper_win_rate": summary.win_rate,
            "avg_roi_gap_vs_wallet": summary.avg_roi_gap_vs_wallet,
        }
        NotificationDispatcher().dispatch(build_daily_summary_notification(stats))
        return stats


@_job("retention")
def prune_raw_responses() -> dict:
    """Drop raw API payloads past the retention window."""
    from .models import RawActivity

    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.raw_response_retention_days)
    with session_scope() as session:
        result = session.execute(delete(RawActivity).where(RawActivity.ingested_at < cutoff))
        return {"deleted": result.rowcount or 0, "cutoff": cutoff.isoformat()}


# ---------------------------------------------------------------- scheduling


def build_scheduler() -> BackgroundScheduler:
    """Create the scheduler with every job registered."""
    settings = get_settings()
    scheduler = BackgroundScheduler(
        timezone="UTC",
        executors={"default": ThreadPoolExecutor(4)},
        job_defaults={
            # Jobs are idempotent, so a missed run should be skipped rather than
            # replayed in a burst; overlapping runs would double-count nothing but
            # would waste rate-limit budget.
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 120,
        },
    )

    scheduler.add_job(
        sync_markets,
        "interval",
        seconds=settings.market_refresh_interval_seconds,
        id="market_sync",
        name="Sync tennis markets",
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=10),
    )
    scheduler.add_job(
        sync_wallets,
        "interval",
        seconds=settings.sync_interval_seconds,
        id="wallet_sync",
        name="Sync wallet activity",
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=45),
    )
    scheduler.add_job(
        scan_signals,
        "interval",
        seconds=settings.live_sync_interval_seconds,
        id="signal_scan",
        name="Scan for signals",
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=90),
    )
    scheduler.add_job(
        manage_paper_trades,
        "interval",
        seconds=max(60, settings.live_sync_interval_seconds * 2),
        id="paper_manage",
        name="Manage paper trades",
    )
    scheduler.add_job(
        backfill_prices,
        "interval",
        seconds=max(600, settings.metrics_recompute_interval_seconds // 2),
        id="price_backfill",
        name="Backfill price evidence",
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    scheduler.add_job(
        recompute_analytics,
        "interval",
        seconds=settings.metrics_recompute_interval_seconds,
        id="analytics",
        name="Recompute metrics and scores",
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    scheduler.add_job(
        snapshot_data_quality,
        "interval",
        hours=1,
        id="data_quality",
        name="Data-quality snapshot",
    )
    scheduler.add_job(
        send_daily_summary,
        "cron",
        hour=23,
        minute=55,
        id="daily_summary",
        name="Daily paper-trading summary",
    )
    scheduler.add_job(
        prune_raw_responses,
        "cron",
        hour=3,
        minute=15,
        id="retention",
        name="Prune raw responses",
    )
    return scheduler


def start_scheduler() -> BackgroundScheduler | None:
    """Start background jobs. Disabled in test mode."""
    global _scheduler
    settings = get_settings()
    if settings.app_env == "test":
        log.info("scheduler.disabled", reason="test environment")
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = build_scheduler()
    _scheduler.start()
    log.info(
        "scheduler.started",
        jobs=[j.id for j in _scheduler.get_jobs()],
        market_refresh_s=settings.market_refresh_interval_seconds,
        wallet_sync_s=settings.sync_interval_seconds,
        signal_scan_s=settings.live_sync_interval_seconds,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("scheduler.stopped")
    _scheduler = None


def scheduler_status() -> dict:
    """Job inventory and last-run outcomes, for the health endpoint."""
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "jobs": list(_last_runs.values())}

    jobs = []
    for job in _scheduler.get_jobs():
        last = _last_runs.get(job.id, {})
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run_at": last.get("at"),
                "last_run_ok": last.get("ok"),
                "last_error": last.get("error"),
                "last_detail": last.get("detail"),
            }
        )
    return {"running": True, "jobs": jobs}


def run_job_now(job_id: str) -> dict:
    """Trigger one job synchronously. Used by the API and CLI."""
    jobs = {
        "market_sync": sync_markets,
        "wallet_sync": sync_wallets,
        "price_backfill": backfill_prices,
        "analytics": recompute_analytics,
        "signal_scan": scan_signals,
        "paper_manage": manage_paper_trades,
        "data_quality": snapshot_data_quality,
        "daily_summary": send_daily_summary,
        "retention": prune_raw_responses,
    }
    fn = jobs.get(job_id)
    if fn is None:
        raise KeyError(f"unknown job '{job_id}'; known jobs: {sorted(jobs)}")
    result = fn()
    return {"job": job_id, "result": result, "status": _last_runs.get(job_id, {})}
