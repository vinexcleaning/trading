"""Live signal feed, signal detail, scan trigger and the SSE stream."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..config import get_settings
from ..db import get_db, get_session_factory
from ..enums import SignalStatus
from ..logging_setup import get_logger
from ..models import Alert, Market, Signal, SignalWallet, Wallet
from ..providers import PolymarketProvider
from ..services.monitor import SignalMonitor, expire_stale_signals
from . import schemas as s
from .deps import load_json_dict, load_json_list

log = get_logger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])

# How often the SSE stream re-checks for new rows.
STREAM_POLL_SECONDS = 3.0


def _signal_out(
    signal: Signal,
    *,
    market_question: str | None = None,
    wallets: list[s.SignalWalletOut] | None = None,
) -> s.SignalOut:
    detail = load_json_list(signal.qualification_detail)
    return s.SignalOut(
        id=signal.id,
        signal_type=signal.signal_type,
        status=signal.status,
        qualified=signal.qualified,
        token_id=signal.token_id,
        condition_id=signal.condition_id,
        outcome_label=signal.outcome_label,
        market_question=market_question,
        market_phase=signal.market_phase,
        first_wallet_trade_at=signal.first_wallet_trade_at,
        detected_at=signal.detected_at,
        expires_at=signal.expires_at,
        signal_age_seconds=signal.signal_age_seconds,
        wallet_count=signal.wallet_count,
        independent_cluster_count=signal.independent_cluster_count,
        wallet_entry_price_min=signal.wallet_entry_price_min,
        wallet_entry_price_max=signal.wallet_entry_price_max,
        wallet_entry_price_median=signal.wallet_entry_price_median,
        current_price=signal.current_price,
        estimated_follower_price=signal.estimated_follower_price,
        price_deterioration=signal.price_deterioration,
        available_liquidity=signal.available_liquidity,
        spread=signal.spread,
        total_wallet_position_usdc=signal.total_wallet_position_usdc,
        median_skill_score=signal.median_skill_score,
        median_copyable_roi=signal.median_copyable_roi,
        copyability_score=signal.copyability_score,
        consensus_score=signal.consensus_score,
        estimated_edge=signal.estimated_edge,
        edge_method=signal.edge_method,
        data_confidence=signal.data_confidence,
        rejection_reasons=load_json_list(signal.rejection_reasons),
        risk_flags=load_json_list(signal.risk_flags),
        explanation=signal.explanation,
        qualification_detail=[d for d in detail if isinstance(d, dict)],
        wallets=wallets or [],
    )


def _market_questions(db: Session, market_ids: list[int]) -> dict[int, str | None]:
    ids = {m for m in market_ids if m}
    if not ids:
        return {}
    return {
        market_id: question
        for market_id, question in db.execute(
            select(Market.id, Market.question).where(Market.id.in_(ids))
        )
    }


def _signal_wallets(db: Session, signal_ids: list[int]) -> dict[int, list[s.SignalWalletOut]]:
    if not signal_ids:
        return {}
    rows = list(
        db.execute(
            select(SignalWallet, Wallet.address, Wallet.nickname)
            .join(Wallet, Wallet.id == SignalWallet.wallet_id)
            .where(SignalWallet.signal_id.in_(set(signal_ids)))
        )
    )
    out: dict[int, list[s.SignalWalletOut]] = {}
    for row, address, nickname in rows:
        out.setdefault(row.signal_id, []).append(
            s.SignalWalletOut(
                wallet_id=row.wallet_id,
                address=address,
                nickname=nickname,
                entry_price=row.entry_price,
                position_usdc=row.position_usdc,
                traded_at=row.traded_at,
                skill_score=row.skill_score,
                copyable_roi=row.copyable_roi,
                tennis_trade_count=row.tennis_trade_count,
                cluster_id=row.cluster_id,
                counted_as_independent=row.counted_as_independent,
                has_begun_exiting=row.has_begun_exiting,
            )
        )
    return out


# ------------------------------------------------------------------- listing


@router.get("", response_model=list[s.SignalOut])
def list_signals(
    db: Session = Depends(get_db),
    status: str | None = Query(None, description="observed|evaluating|qualified|rejected|expired|paper_entered|paper_exited"),
    qualified: bool | None = Query(None),
    signal_type: str | None = Query(None),
    token_id: str | None = Query(None),
    market_id: int | None = Query(None),
    since_id: int | None = Query(None, description="only signals with a higher id"),
    hours: int | None = Query(None, ge=1, le=8760, description="restrict to the last N hours"),
    include_wallets: bool = Query(True),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> list[s.SignalOut]:
    """The live feed. Rejected candidates are included by design: the rejection
    log is how alert thresholds get calibrated."""
    query = select(Signal)
    if status:
        query = query.where(Signal.status == status)
    if qualified is not None:
        query = query.where(Signal.qualified.is_(qualified))
    if signal_type:
        query = query.where(Signal.signal_type == signal_type)
    if token_id:
        query = query.where(Signal.token_id == token_id)
    if market_id:
        query = query.where(Signal.market_id == market_id)
    if since_id:
        query = query.where(Signal.id > since_id)
    if hours:
        query = query.where(
            Signal.detected_at >= datetime.now(timezone.utc) - timedelta(hours=hours)
        )

    rows = list(db.scalars(query.order_by(Signal.detected_at.desc()).limit(limit).offset(offset)))
    questions = _market_questions(db, [r.market_id for r in rows])
    wallets = _signal_wallets(db, [r.id for r in rows]) if include_wallets else {}

    return [
        _signal_out(
            r,
            market_question=questions.get(r.market_id),
            wallets=wallets.get(r.id, []),
        )
        for r in rows
    ]


@router.get("/stream")
async def stream_signals(
    request: Request,
    qualified_only: bool = Query(False),
) -> EventSourceResponse:
    """Server-sent events for the live dashboard.

    Polls rather than using database triggers: with SQLite the scheduler writes
    from another connection, so polling is the portable option and 3s granularity
    is well inside the shortest alert window.
    """
    factory = get_session_factory()

    def _latest_id() -> int:
        with factory() as session:
            return session.scalar(select(func.max(Signal.id))) or 0

    def _fetch(after_id: int) -> list[dict]:
        with factory() as session:
            query = select(Signal).where(Signal.id > after_id)
            if qualified_only:
                query = query.where(Signal.qualified.is_(True))
            rows = list(session.scalars(query.order_by(Signal.id).limit(50)))
            questions = _market_questions(session, [r.market_id for r in rows])
            wallets = _signal_wallets(session, [r.id for r in rows])
            return [
                _signal_out(
                    r,
                    market_question=questions.get(r.market_id),
                    wallets=wallets.get(r.id, []),
                ).model_dump(mode="json")
                for r in rows
            ]

    async def publisher():
        cursor = await asyncio.to_thread(_latest_id)
        yield {"event": "connected", "data": json.dumps({"cursor": cursor})}

        while True:
            if await request.is_disconnected():
                break
            try:
                payloads = await asyncio.to_thread(_fetch, cursor)
            except Exception as exc:  # noqa: BLE001 - a stream must not 500 the page
                log.warning("signals.stream_error", error=str(exc))
                payloads = []
            for payload in payloads:
                cursor = max(cursor, payload["id"])
                yield {"event": "signal", "data": json.dumps(payload)}
            await asyncio.sleep(STREAM_POLL_SECONDS)

    return EventSourceResponse(publisher())


@router.post("/scan", response_model=s.MessageOut)
def scan_signals(
    db: Session = Depends(get_db),
    lookback_seconds: int | None = Query(None, ge=60, le=86400),
    dispatch: bool = Query(True, description="send notifications for qualified signals"),
    paper: bool = Query(True, description="open simulated positions for qualified signals"),
    use_live_prices: bool = Query(True, description="fetch live order books"),
) -> s.MessageOut:
    """Run one monitoring pass immediately."""
    provider = PolymarketProvider() if use_live_prices else None
    try:
        monitor = SignalMonitor(db, provider)
        stats = monitor.scan(lookback_seconds=lookback_seconds, dispatch=dispatch, paper=paper)
        expired = expire_stale_signals(db)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(502, f"scan failed: {exc}") from exc
    finally:
        if provider is not None:
            provider.close()

    detail = stats.as_dict()
    detail["signals_expired"] = expired
    return s.MessageOut(
        message=(
            f"evaluated {stats.tokens_evaluated} outcome(s): "
            f"{stats.qualified} qualified, {stats.rejected} rejected"
        ),
        detail=detail,
    )


@router.get("/alerts", response_model=list[dict])
def list_alerts(
    db: Session = Depends(get_db),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
) -> list[dict]:
    """In-app notification feed."""
    query = select(Alert)
    if unread_only:
        query = query.where(Alert.read_at.is_(None))
    rows = list(db.scalars(query.order_by(Alert.created_at.desc()).limit(limit)))
    return [
        {
            "id": r.id,
            "signal_id": r.signal_id,
            "alert_type": r.alert_type,
            "channel": r.channel,
            "title": r.title,
            "body": r.body,
            "payload": load_json_dict(r.payload),
            "delivered": r.delivered,
            "delivery_error": r.delivery_error,
            "read_at": r.read_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/alerts/{alert_id}/read", response_model=s.MessageOut)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)) -> s.MessageOut:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(404, "alert not found")
    alert.read_at = datetime.now(timezone.utc)
    db.commit()
    return s.MessageOut(message="marked read")


@router.get("/{signal_id}", response_model=s.SignalOut)
def get_signal(signal_id: int, db: Session = Depends(get_db)) -> s.SignalOut:
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(404, "signal not found")
    market = db.get(Market, signal.market_id) if signal.market_id else None
    wallets = _signal_wallets(db, [signal.id])
    return _signal_out(
        signal,
        market_question=market.question if market else None,
        wallets=wallets.get(signal.id, []),
    )


@router.post("/expire", response_model=s.MessageOut)
def expire_signals(db: Session = Depends(get_db)) -> s.MessageOut:
    """Move past-expiry signals out of the actionable states."""
    count = expire_stale_signals(db)
    db.commit()
    settings = get_settings()
    return s.MessageOut(
        message=f"expired {count} signal(s)",
        detail={
            "live_window_seconds": settings.alert_max_age_live_seconds,
            "prematch_window_seconds": settings.alert_max_age_prematch_seconds,
            "statuses_affected": [SignalStatus.QUALIFIED, SignalStatus.EVALUATING],
        },
    )
