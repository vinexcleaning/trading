"""Paper-trading positions, history, summary and management.

Simulation only. No endpoint in this module places a real order.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..enums import PaperTradeStatus
from ..logging_setup import get_logger
from ..models import Market, PaperDailyStat, PaperTrade, PaperTradeEvent
from ..providers import PolymarketProvider
from ..services.monitor import PaperTradeManager
from ..services.paper import summarise_paper_trades
from . import schemas as s

log = get_logger(__name__)
router = APIRouter(prefix="/api/paper", tags=["paper-trading"])

PAPER_DISCLAIMER = (
    "Simulated results. Fills are modelled from observed prices and order-book "
    "depth after a configured delay, so they may differ materially from real "
    "execution. Nothing here is a real order or financial advice."
)


def _trade_out(trade: PaperTrade, market_question: str | None = None) -> s.PaperTradeOut:
    return s.PaperTradeOut(
        id=trade.id,
        signal_id=trade.signal_id,
        token_id=trade.token_id,
        outcome_label=trade.outcome_label,
        market_question=market_question,
        status=trade.status,
        exit_strategy=trade.exit_strategy,
        signal_detected_at=trade.signal_detected_at,
        execution_delay_seconds=trade.execution_delay_seconds,
        entered_at=trade.entered_at,
        exited_at=trade.exited_at,
        wallet_entry_price=trade.wallet_entry_price,
        reference_price=trade.reference_price,
        fill_price=trade.fill_price,
        slippage_applied=trade.slippage_applied,
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason,
        stake_usdc=trade.stake_usdc,
        shares=trade.shares,
        stake_reduced_for_liquidity=trade.stake_reduced_for_liquidity,
        realized_pnl=trade.realized_pnl,
        unrealized_pnl=trade.unrealized_pnl,
        roi=trade.roi,
        is_win=trade.is_win,
        wallet_roi=trade.wallet_roi,
        roi_gap_vs_wallet=trade.roi_gap_vs_wallet,
        price_source_quality=trade.price_source_quality,
        data_confidence=trade.data_confidence,
        rejection_reason=trade.rejection_reason,
        notes=trade.notes,
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


@router.get("/trades", response_model=list[s.PaperTradeOut])
def list_paper_trades(
    db: Session = Depends(get_db),
    status: str | None = Query(None, description="pending|open|closed|settled|rejected"),
    open_only: bool = Query(False),
    include_rejected: bool = Query(True),
    include_backtest: bool = Query(False),
    days: int | None = Query(None, ge=1, le=3650),
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
) -> list[s.PaperTradeOut]:
    query = select(PaperTrade)
    if not include_backtest:
        query = query.where(PaperTrade.is_backtest.is_(False))
    if status:
        query = query.where(PaperTrade.status == status)
    if open_only:
        query = query.where(PaperTrade.status == PaperTradeStatus.OPEN)
    if not include_rejected:
        query = query.where(PaperTrade.status != PaperTradeStatus.REJECTED)
    if days:
        query = query.where(
            PaperTrade.created_at >= datetime.now(timezone.utc) - timedelta(days=days)
        )

    rows = list(
        db.scalars(query.order_by(PaperTrade.created_at.desc()).limit(limit).offset(offset))
    )
    questions = _market_questions(db, [r.market_id for r in rows])
    return [_trade_out(r, questions.get(r.market_id)) for r in rows]


@router.get("/summary", response_model=s.PaperSummaryOut)
def paper_summary(
    db: Session = Depends(get_db),
    days: int | None = Query(None, ge=1, le=3650),
    include_backtest: bool = Query(False),
) -> s.PaperSummaryOut:
    """Aggregate paper performance, including the follower-versus-wallet gap."""
    query = select(PaperTrade)
    if not include_backtest:
        query = query.where(PaperTrade.is_backtest.is_(False))
    if days:
        query = query.where(
            PaperTrade.created_at >= datetime.now(timezone.utc) - timedelta(days=days)
        )
    rows = list(db.scalars(query))

    summary = summarise_paper_trades(
        [
            {
                "status": r.status,
                "stake_usdc": r.stake_usdc,
                "realized_pnl": r.realized_pnl,
                "unrealized_pnl": r.unrealized_pnl,
                "is_win": r.is_win,
                "roi_gap_vs_wallet": r.roi_gap_vs_wallet,
                "rejection_reason": r.rejection_reason,
            }
            for r in rows
        ]
    )

    return s.PaperSummaryOut(
        trades=summary.trades,
        open_trades=summary.open_trades,
        closed_trades=summary.closed_trades,
        wins=summary.wins,
        losses=summary.losses,
        total_staked=summary.total_staked,
        realized_pnl=summary.realized_pnl,
        unrealized_pnl=summary.unrealized_pnl,
        net_pnl=summary.net_pnl,
        roi=summary.roi,
        win_rate=summary.win_rate,
        rejected=summary.rejected,
        rejection_reasons=summary.rejection_reasons,
        avg_roi_gap_vs_wallet=summary.avg_roi_gap_vs_wallet,
        disclaimer=PAPER_DISCLAIMER,
    )


@router.get("/daily", response_model=list[dict])
def paper_daily_stats(
    db: Session = Depends(get_db), days: int = Query(30, ge=1, le=365)
) -> list[dict]:
    """Per-day roll-up used by the daily loss cap and the reports."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    rows = list(
        db.scalars(
            select(PaperDailyStat)
            .where(PaperDailyStat.stat_date >= cutoff)
            .order_by(PaperDailyStat.stat_date.desc())
        )
    )
    return [
        {
            "date": r.stat_date.isoformat(),
            "trades_entered": r.trades_entered,
            "trades_closed": r.trades_closed,
            "realized_pnl": str(r.realized_pnl),
            "wins": r.wins,
            "losses": r.losses,
            "stake_deployed": str(r.stake_deployed),
            "entries_blocked_by_risk": r.entries_blocked_by_risk,
        }
        for r in rows
    ]


@router.get("/risk", response_model=dict)
def paper_risk_state(db: Session = Depends(get_db)) -> dict:
    """Live exposure against the configured simulation limits."""
    settings = get_settings()
    state = PaperTradeManager(db).risk_state()
    return {
        "enabled": settings.paper_trading_enabled,
        "open_positions": state.open_positions,
        "max_open_positions": settings.paper_max_open_positions,
        "total_exposure": str(state.total_exposure),
        "max_total_exposure": str(settings.paper_max_total_exposure_usdc),
        "max_exposure_per_market": str(settings.paper_max_exposure_per_market_usdc),
        "exposure_by_market": {k: str(v) for k, v in state.exposure_by_market.items()},
        "realized_pnl_today": str(state.realized_pnl_today),
        "daily_loss_cap": str(settings.paper_daily_loss_cap_usdc),
        "entries_today": state.entries_today,
        "stake_per_signal": str(settings.paper_stake_usdc),
        "execution_delay_seconds": settings.paper_execution_delay_seconds,
        "default_exit_strategy": settings.paper_default_exit_strategy,
        "disclaimer": PAPER_DISCLAIMER,
    }


@router.post("/manage", response_model=s.MessageOut)
def manage_paper_trades(
    db: Session = Depends(get_db),
    use_live_prices: bool = Query(True),
) -> s.MessageOut:
    """Mark open simulated positions and close any whose exit rule triggered."""
    provider = PolymarketProvider() if use_live_prices else None
    try:
        result = PaperTradeManager(db, provider).manage_open_trades()
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(502, f"paper management failed: {exc}") from exc
    finally:
        if provider is not None:
            provider.close()
    return s.MessageOut(
        message=(
            f"examined {result['examined']} open position(s): "
            f"{result['closed']} closed, {result['settled']} settled"
        ),
        detail=result,
    )


@router.get("/trades/{trade_id}", response_model=dict)
def get_paper_trade(trade_id: int, db: Session = Depends(get_db)) -> dict:
    """One simulated position with its full event log."""
    trade = db.get(PaperTrade, trade_id)
    if trade is None:
        raise HTTPException(404, "paper trade not found")
    market = db.get(Market, trade.market_id) if trade.market_id else None
    events = list(
        db.scalars(
            select(PaperTradeEvent)
            .where(PaperTradeEvent.paper_trade_id == trade_id)
            .order_by(PaperTradeEvent.occurred_at)
        )
    )
    return {
        "trade": _trade_out(trade, market.question if market else None).model_dump(mode="json"),
        "events": [
            {
                "event_type": e.event_type,
                "occurred_at": e.occurred_at.isoformat(),
                "price": str(e.price) if e.price is not None else None,
                "shares": str(e.shares) if e.shares is not None else None,
                "pnl": str(e.pnl) if e.pnl is not None else None,
                "detail": e.detail,
            }
            for e in events
        ],
        "disclaimer": PAPER_DISCLAIMER,
    }
