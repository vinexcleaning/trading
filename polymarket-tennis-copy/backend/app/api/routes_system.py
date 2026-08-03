"""Dashboard summaries, health, data quality, settings, errors and reports."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings, reset_settings_cache
from ..db import get_db, get_engine
from ..enums import PaperTradeStatus, SignalStatus
from ..logging_setup import get_logger
from ..models import (
    Alert,
    ApplicationSetting,
    IngestionJob,
    Market,
    PaperTrade,
    SchemaDriftEvent,
    Signal,
    SystemError,
    Wallet,
    WalletMetrics,
    WalletScore,
)
from ..services.ingest import data_freshness
from ..services.notifications import NotificationDispatcher
from ..services.paper import summarise_paper_trades
from ..services.pipeline import data_quality_snapshot
from . import schemas as s
from .deps import DISCLAIMER, load_json_dict, load_json_list

log = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["system"])

APP_VERSION = "1.0.0"

# Settings an operator may change at runtime. Anything absent from this map is
# environment-only, which is how credentials stay unreachable through the API.
EDITABLE_SETTINGS: dict[str, str] = {
    "alert_min_tennis_trades": "int",
    "alert_min_skill_score": "float",
    "alert_min_copyable_roi": "float",
    "alert_min_data_confidence": "float",
    "alert_max_drawdown": "float",
    "alert_max_price_deterioration": "decimal",
    "alert_min_liquidity_usdc": "decimal",
    "alert_max_spread": "decimal",
    "alert_max_age_live_seconds": "int",
    "alert_max_age_prematch_seconds": "int",
    "alert_min_copyability_score": "float",
    "alert_min_position_usdc": "decimal",
    "consensus_min_wallets": "int",
    "consensus_min_independent_clusters": "int",
    "consensus_window_seconds": "int",
    "consensus_min_median_skill": "float",
    "consensus_min_median_copyability": "float",
    "consensus_max_price_deterioration": "decimal",
    "benchmark_delay_seconds": "int",
    "modeled_slippage_bps": "int",
    "min_copyable_data_confidence": "float",
    "paper_trading_enabled": "bool",
    "paper_execution_delay_seconds": "int",
    "paper_stake_usdc": "decimal",
    "paper_max_exposure_per_market_usdc": "decimal",
    "paper_max_total_exposure_usdc": "decimal",
    "paper_max_open_positions": "int",
    "paper_daily_loss_cap_usdc": "decimal",
    "paper_default_exit_strategy": "str",
    "paper_allow_duplicate_signals": "bool",
    "sync_interval_seconds": "int",
    "live_sync_interval_seconds": "int",
    "market_refresh_interval_seconds": "int",
    "metrics_recompute_interval_seconds": "int",
    "max_wallets_per_sync_cycle": "int",
    "raw_response_retention_days": "int",
    "log_level": "str",
    "notifications_enabled": "bool",
}


# ------------------------------------------------------------------ overview


@router.get("/overview", response_model=s.OverviewOut)
def overview(db: Session = Depends(get_db)) -> s.OverviewOut:
    """Headline dashboard numbers."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    day_start = now - timedelta(days=1)

    wallets_tracked = db.scalar(select(func.count(Wallet.id))) or 0
    wallets_approved = (
        db.scalar(select(func.count(Wallet.id)).where(Wallet.manually_approved.is_(True))) or 0
    )
    wallets_qualified = (
        db.scalar(
            select(func.count(WalletScore.id)).where(
                WalletScore.scope == "tennis", WalletScore.qualified.is_(True)
            )
        )
        or 0
    )

    tennis_markets = (
        db.scalar(select(func.count(Market.id)).where(Market.is_tennis.is_(True))) or 0
    )
    tennis_open = (
        db.scalar(
            select(func.count(Market.id)).where(
                Market.is_tennis.is_(True), Market.closed.is_(False)
            )
        )
        or 0
    )

    active_signals = (
        db.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_((SignalStatus.QUALIFIED, SignalStatus.PAPER_ENTERED))
            )
        )
        or 0
    )
    signals_today = (
        db.scalar(select(func.count(Signal.id)).where(Signal.detected_at >= day_start)) or 0
    )
    qualified_today = (
        db.scalar(
            select(func.count(Signal.id)).where(
                Signal.detected_at >= day_start, Signal.qualified.is_(True)
            )
        )
        or 0
    )
    rejected_today = signals_today - qualified_today

    paper_rows = list(
        db.execute(
            select(
                PaperTrade.status,
                PaperTrade.stake_usdc,
                PaperTrade.realized_pnl,
                PaperTrade.unrealized_pnl,
                PaperTrade.is_win,
                PaperTrade.roi_gap_vs_wallet,
                PaperTrade.rejection_reason,
            ).where(PaperTrade.is_backtest.is_(False))
        )
    )
    paper = summarise_paper_trades(
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
            for r in paper_rows
        ]
    )

    # Median copyable ROI across qualified wallets, coverage-gated upstream.
    copyable = sorted(
        v
        for v in db.scalars(
            select(WalletMetrics.copyable_roi)
            .join(WalletScore, WalletScore.wallet_id == WalletMetrics.wallet_id)
            .where(
                WalletMetrics.scope == "tennis",
                WalletScore.scope == "tennis",
                WalletScore.qualified.is_(True),
                WalletMetrics.copyable_roi.is_not(None),
            )
        )
        if v is not None
    )
    median_copyable = copyable[len(copyable) // 2] if copyable else None

    freshness = data_freshness(db)

    return s.OverviewOut(
        wallets_tracked=wallets_tracked,
        wallets_approved=wallets_approved,
        wallets_qualified=wallets_qualified,
        tennis_markets_tracked=tennis_markets,
        tennis_markets_open=tennis_open,
        active_signals=active_signals,
        signals_today=signals_today,
        qualified_signals_today=qualified_today,
        rejected_signals_today=rejected_today,
        paper_open_positions=paper.open_trades,
        paper_realized_pnl=paper.realized_pnl,
        paper_unrealized_pnl=paper.unrealized_pnl,
        paper_win_rate=paper.win_rate,
        paper_roi=paper.roi,
        median_qualified_copyable_roi=median_copyable,
        current_drawdown=_current_paper_drawdown(db),
        last_market_sync=(
            datetime.fromisoformat(freshness["last_market_sync"])
            if freshness["last_market_sync"]
            else None
        ),
        last_wallet_sync=(
            datetime.fromisoformat(freshness["last_wallet_sync"])
            if freshness["last_wallet_sync"]
            else None
        ),
        benchmark_delay_seconds=settings.benchmark_delay_seconds,
        disclaimer=DISCLAIMER,
    )


def _current_paper_drawdown(db: Session) -> float | None:
    """Drawdown of the simulated equity curve, in fractions of peak equity."""
    rows = list(
        db.execute(
            select(PaperTrade.realized_pnl, PaperTrade.exited_at)
            .where(
                PaperTrade.is_backtest.is_(False),
                PaperTrade.status.in_((PaperTradeStatus.CLOSED, PaperTradeStatus.SETTLED)),
                PaperTrade.realized_pnl.is_not(None),
            )
            .order_by(PaperTrade.exited_at)
        )
    )
    if not rows:
        return None

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = 0.0
    # Peak equity can be zero or negative early on, so the drawdown base falls
    # back to total staked rather than dividing by a meaningless peak.
    total_staked = db.scalar(
        select(func.sum(PaperTrade.stake_usdc)).where(PaperTrade.is_backtest.is_(False))
    ) or Decimal("1")

    for pnl, _ in rows:
        equity += pnl or Decimal("0")
        peak = max(peak, equity)
        base = peak if peak > 0 else total_staked
        if base > 0:
            max_dd = max(max_dd, float((peak - equity) / base))
    return round(max_dd, 6)


# -------------------------------------------------------------------- health


@router.get("/health", response_model=s.HealthOut)
def health(db: Session = Depends(get_db)) -> s.HealthOut:
    """Liveness plus the freshness and error indicators the spec requires."""
    settings = get_settings()

    database = "ok"
    try:
        db.execute(select(1))
    except Exception as exc:  # noqa: BLE001
        database = f"error: {type(exc).__name__}"

    from ..scheduler import scheduler_status

    sched = scheduler_status()
    recent_errors = (
        db.scalar(
            select(func.count(SystemError.id)).where(
                SystemError.resolved.is_(False),
                SystemError.last_seen_at >= datetime.now(timezone.utc) - timedelta(hours=24),
            )
        )
        or 0
    )
    drift = (
        db.scalar(
            select(func.count(SchemaDriftEvent.id)).where(
                SchemaDriftEvent.acknowledged.is_(False)
            )
        )
        or 0
    )

    freshness = data_freshness(db)
    status = "ok"
    if database != "ok":
        status = "error"
    elif recent_errors or drift:
        status = "degraded"

    return s.HealthOut(
        status=status,
        version=APP_VERSION,
        environment=settings.app_env,
        database=database,
        scheduler_running=bool(sched.get("running")),
        jobs=sched.get("jobs", []),
        freshness=freshness,
        recent_errors=recent_errors,
        unacknowledged_drift=drift,
        notification_channels=NotificationDispatcher().configured_channels(),
    )


@router.get("/data-quality", response_model=s.DataQualityOut)
def data_quality(db: Session = Depends(get_db)) -> s.DataQualityOut:
    """Pipeline completeness and price-evidence mix."""
    snapshot = data_quality_snapshot(db)
    db.commit()
    return s.DataQualityOut(**snapshot)


@router.get("/errors", response_model=list[s.SystemErrorOut])
def list_errors(
    db: Session = Depends(get_db),
    unresolved_only: bool = Query(True),
    limit: int = Query(100, le=500),
) -> list[s.SystemErrorOut]:
    query = select(SystemError)
    if unresolved_only:
        query = query.where(SystemError.resolved.is_(False))
    rows = db.scalars(query.order_by(SystemError.last_seen_at.desc()).limit(limit))
    return [
        s.SystemErrorOut(
            id=r.id,
            severity=r.severity,
            category=r.category,
            component=r.component,
            message=r.message,
            occurrence_count=r.occurrence_count,
            first_seen_at=r.first_seen_at,
            last_seen_at=r.last_seen_at,
            resolved=r.resolved,
        )
        for r in rows
    ]


@router.post("/errors/{error_id}/resolve", response_model=s.MessageOut)
def resolve_error(error_id: int, db: Session = Depends(get_db)) -> s.MessageOut:
    row = db.get(SystemError, error_id)
    if row is None:
        raise HTTPException(404, "error not found")
    row.resolved = True
    db.commit()
    return s.MessageOut(message="marked resolved")


@router.get("/jobs", response_model=list[s.IngestionJobOut])
def list_jobs(
    db: Session = Depends(get_db),
    job_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
) -> list[s.IngestionJobOut]:
    query = select(IngestionJob)
    if job_type:
        query = query.where(IngestionJob.job_type == job_type)
    if status:
        query = query.where(IngestionJob.status == status)
    rows = db.scalars(query.order_by(IngestionJob.started_at.desc()).limit(limit))
    return [
        s.IngestionJobOut(
            id=r.id,
            job_type=r.job_type,
            job_uid=r.job_uid,
            status=r.status,
            target=r.target,
            records_fetched=r.records_fetched,
            records_inserted=r.records_inserted,
            records_skipped_duplicate=r.records_skipped_duplicate,
            records_failed=r.records_failed,
            http_requests=r.http_requests,
            http_retries=r.http_retries,
            rate_limit_events=r.rate_limit_events,
            started_at=r.started_at,
            finished_at=r.finished_at,
            duration_ms=r.duration_ms,
            error=r.error,
        )
        for r in rows
    ]


# ------------------------------------------------------------------ settings


@router.get("/settings", response_model=s.SettingsOut)
def get_settings_endpoint(db: Session = Depends(get_db)) -> s.SettingsOut:
    """Non-secret configuration. Credentials are never returned."""
    c = get_settings()
    overrides = {
        row.key: row.value for row in db.scalars(select(ApplicationSetting))
    }

    def value(key: str):
        return overrides.get(key, getattr(c, key, None))

    return s.SettingsOut(
        follower_delays_seconds=c.follower_delays_seconds,
        benchmark_delay_seconds=c.benchmark_delay_seconds,
        modeled_slippage_bps=c.modeled_slippage_bps,
        score_weights=c.score_weights,
        alert_thresholds={
            "min_tennis_trades": value("alert_min_tennis_trades"),
            "min_skill_score": value("alert_min_skill_score"),
            "min_copyable_roi": value("alert_min_copyable_roi"),
            "min_data_confidence": value("alert_min_data_confidence"),
            "max_drawdown": value("alert_max_drawdown"),
            "max_price_deterioration": str(value("alert_max_price_deterioration")),
            "min_liquidity_usdc": str(value("alert_min_liquidity_usdc")),
            "max_spread": str(value("alert_max_spread")),
            "max_age_live_seconds": value("alert_max_age_live_seconds"),
            "max_age_prematch_seconds": value("alert_max_age_prematch_seconds"),
            "min_copyability_score": value("alert_min_copyability_score"),
            "min_position_usdc": str(value("alert_min_position_usdc")),
        },
        consensus_thresholds={
            "min_wallets": value("consensus_min_wallets"),
            "min_independent_clusters": value("consensus_min_independent_clusters"),
            "window_seconds": value("consensus_window_seconds"),
            "min_median_skill": value("consensus_min_median_skill"),
            "min_median_copyability": value("consensus_min_median_copyability"),
            "max_price_deterioration": str(value("consensus_max_price_deterioration")),
        },
        paper_settings={
            "enabled": value("paper_trading_enabled"),
            "execution_delay_seconds": value("paper_execution_delay_seconds"),
            "stake_usdc": str(value("paper_stake_usdc")),
            "max_exposure_per_market_usdc": str(value("paper_max_exposure_per_market_usdc")),
            "max_total_exposure_usdc": str(value("paper_max_total_exposure_usdc")),
            "max_open_positions": value("paper_max_open_positions"),
            "daily_loss_cap_usdc": str(value("paper_daily_loss_cap_usdc")),
            "default_exit_strategy": value("paper_default_exit_strategy"),
            "allow_duplicate_signals": value("paper_allow_duplicate_signals"),
        },
        sync_intervals={
            "wallet_sync_seconds": c.sync_interval_seconds,
            "live_sync_seconds": c.live_sync_interval_seconds,
            "market_refresh_seconds": c.market_refresh_interval_seconds,
            "metrics_recompute_seconds": c.metrics_recompute_interval_seconds,
        },
        notification_channels_configured=c.configured_notification_channels(),
        min_copyable_data_confidence=c.min_copyable_data_confidence,
    )


@router.patch("/settings", response_model=s.MessageOut)
def update_setting(payload: s.SettingUpdate, db: Session = Depends(get_db)) -> s.MessageOut:
    """Persist a runtime override for one non-secret setting."""
    kind = EDITABLE_SETTINGS.get(payload.key)
    if kind is None:
        raise HTTPException(
            422,
            f"'{payload.key}' is not runtime-editable. Editable keys: "
            f"{sorted(EDITABLE_SETTINGS)}",
        )

    # Validate by coercion before storing, so a bad value is rejected here
    # rather than crashing a scheduler job later.
    raw = payload.value.strip()
    try:
        if kind == "int":
            int(raw)
        elif kind == "float":
            float(raw)
        elif kind == "decimal":
            Decimal(raw)
        elif kind == "bool":
            if raw.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise ValueError("expected a boolean")
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(422, f"invalid {kind} value for {payload.key}: {exc}") from exc

    row = db.scalar(select(ApplicationSetting).where(ApplicationSetting.key == payload.key))
    if row is None:
        row = ApplicationSetting(key=payload.key, category="runtime")
        db.add(row)
    row.value = raw
    row.value_type = kind
    db.commit()

    log.info("settings.updated", key=payload.key)
    return s.MessageOut(
        message=f"{payload.key} set to {raw}",
        detail={
            "note": (
                "Stored as a runtime override. Restart or re-read settings for "
                "jobs that cache configuration at startup."
            )
        },
    )


@router.delete("/settings/{key}", response_model=s.MessageOut)
def clear_setting(key: str, db: Session = Depends(get_db)) -> s.MessageOut:
    row = db.scalar(select(ApplicationSetting).where(ApplicationSetting.key == key))
    if row is None:
        raise HTTPException(404, "no override stored for that key")
    db.delete(row)
    db.commit()
    reset_settings_cache()
    return s.MessageOut(message=f"cleared override for {key}")


# ------------------------------------------------------------------- reports


@router.get("/reports/{period}", response_model=s.ReportOut)
def get_report(
    period: str,
    db: Session = Depends(get_db),
) -> s.ReportOut:
    """Daily or weekly operating report."""
    if period not in ("daily", "weekly"):
        raise HTTPException(422, "period must be 'daily' or 'weekly'")
    return _build_report(db, period)


@router.get("/reports/{period}/export")
def export_report(
    period: str,
    fmt: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
) -> Response:
    """Export a report as JSON or CSV."""
    if period not in ("daily", "weekly"):
        raise HTTPException(422, "period must be 'daily' or 'weekly'")
    report = _build_report(db, period)
    payload = report.model_dump(mode="json")

    if fmt == "json":
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{period}-report.json"'
            },
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    for key, value in payload.items():
        writer.writerow(
            [key, json.dumps(value, default=str) if isinstance(value, (dict, list)) else value]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{period}-report.csv"'},
    )


def _build_report(db: Session, period: str) -> s.ReportOut:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=1 if period == "daily" else 7)

    wallets_added = (
        db.scalar(select(func.count(Wallet.id)).where(Wallet.created_at >= since)) or 0
    )

    signals = list(
        db.execute(
            select(Signal.qualified, Signal.rejection_reasons).where(
                Signal.detected_at >= since
            )
        )
    )
    generated = sum(1 for q, _ in signals if q)
    rejected = len(signals) - generated
    reasons: dict[str, int] = {}
    for qualified, payload in signals:
        if qualified:
            continue
        for reason in load_json_list(payload):
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1

    scored = list(
        db.execute(
            select(
                Wallet.id,
                Wallet.address,
                Wallet.nickname,
                WalletScore.skill_score,
                WalletScore.qualified,
                WalletScore.confidence_level,
                WalletMetrics.copyable_roi,
                WalletMetrics.roi,
                WalletMetrics.completed_positions,
                WalletMetrics.copyable_coverage,
            )
            .join(WalletScore, WalletScore.wallet_id == Wallet.id)
            .outerjoin(
                WalletMetrics,
                (WalletMetrics.wallet_id == Wallet.id) & (WalletMetrics.scope == "tennis"),
            )
            .where(WalletScore.scope == "tennis")
        )
    )

    def row_dict(row) -> dict:
        return {
            "wallet_id": row[0],
            "address": row[1],
            "nickname": row[2],
            "skill_score": row[3],
            "qualified": row[4],
            "confidence": row[5],
            "copyable_roi": row[6],
            "raw_roi": row[7],
            "completed_positions": row[8],
            "copyable_coverage": row[9],
        }

    ranked = sorted(scored, key=lambda r: r[3] or 0.0, reverse=True)
    best = [row_dict(r) for r in ranked[:5]]
    worst = [row_dict(r) for r in ranked[-5:]] if len(ranked) > 5 else []
    new_qualifying = [row_dict(r) for r in scored if r[4]]
    downgraded = [
        row_dict(r)
        for r in scored
        if not r[4] and (r[3] or 0.0) >= get_settings().alert_min_skill_score * 0.8
    ]

    paper_rows = list(
        db.execute(
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
    paper = summarise_paper_trades(
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
            for r in paper_rows
        ]
    )

    raw_rois = [r[7] for r in scored if r[7] is not None]
    copy_rois = [r[6] for r in scored if r[6] is not None]
    raw_median = sorted(raw_rois)[len(raw_rois) // 2] if raw_rois else None
    copy_median = sorted(copy_rois)[len(copy_rois) // 2] if copy_rois else None

    quality = data_quality_snapshot(db)
    db.commit()

    errors = (
        db.scalar(
            select(func.count(SystemError.id)).where(
                SystemError.last_seen_at >= since, SystemError.resolved.is_(False)
            )
        )
        or 0
    )

    return s.ReportOut(
        period=period,
        generated_at=now,
        wallets_added=wallets_added,
        wallets_downgraded=downgraded,
        new_qualifying_wallets=new_qualifying,
        best_wallets=best,
        worst_wallets=worst,
        alerts_generated=generated,
        alerts_rejected=rejected,
        rejection_reasons=reasons,
        paper_summary={
            "trades": paper.trades,
            "open": paper.open_trades,
            "closed": paper.closed_trades,
            "wins": paper.wins,
            "losses": paper.losses,
            "realized_pnl": str(paper.realized_pnl),
            "unrealized_pnl": str(paper.unrealized_pnl),
            "roi": paper.roi,
            "win_rate": paper.win_rate,
            "rejected": paper.rejected,
            "rejection_reasons": paper.rejection_reasons,
        },
        raw_vs_follower={
            "median_raw_roi": raw_median,
            "median_copyable_roi": copy_median,
            "median_delay_cost": (
                round(raw_median - copy_median, 6)
                if raw_median is not None and copy_median is not None
                else None
            ),
            "note": (
                "Copyable ROI is measured at the benchmark follower delay and only "
                "counts trades with sufficient price evidence."
            ),
        },
        delay_impact={
            "benchmark_delay_seconds": get_settings().benchmark_delay_seconds,
            "avg_paper_roi_gap_vs_wallet": paper.avg_roi_gap_vs_wallet,
        },
        data_quality_issues=list(quality.get("warnings", [])),
        system_errors=errors,
    )


@router.get("/alerts/count", response_model=dict)
def alert_counts(db: Session = Depends(get_db)) -> dict:
    """Small counter payload for the header badge."""
    day_start = datetime.now(timezone.utc) - timedelta(days=1)
    return {
        "unread": db.scalar(select(func.count(Alert.id)).where(Alert.read_at.is_(None))) or 0,
        "today": db.scalar(select(func.count(Alert.id)).where(Alert.created_at >= day_start))
        or 0,
    }


@router.get("/db-info", response_model=dict)
def db_info() -> dict:
    """Which database the app is actually using (no credentials returned)."""
    engine = get_engine()
    return {
        "dialect": engine.dialect.name,
        "driver": engine.dialect.driver,
        "database": engine.url.database,
    }
