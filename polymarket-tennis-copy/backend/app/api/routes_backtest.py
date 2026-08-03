"""Backtest creation, status polling and results."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db, session_scope
from ..enums import JobStatus
from ..logging_setup import get_logger
from ..models import BacktestRun, BacktestTrade
from ..services.backtest_runner import BacktestRunner, config_from_payload
from . import schemas as s
from .deps import load_json_dict, load_json_list

log = get_logger(__name__)
router = APIRouter(prefix="/api/backtests", tags=["backtesting"])

ZERO_DELAY_WARNING = (
    "delay_seconds=0 is a theoretical reference only. No follower can detect, "
    "decide and execute instantly, so a zero-delay result overstates what was "
    "achievable."
)


def _run_out(run: BacktestRun) -> s.BacktestRunOut:
    warnings = load_json_list(run.data_quality_warnings)
    config = load_json_dict(run.config_json)
    if run.delay_seconds == 0:
        warnings = [ZERO_DELAY_WARNING, *warnings]
    if run.lookahead_violations:
        warnings = [
            f"{run.lookahead_violations} look-ahead violation(s): this run is not "
            "a valid result.",
            *warnings,
        ]

    delay_sensitivity = load_json_dict(run.delay_sensitivity_json)
    return s.BacktestRunOut(
        id=run.id,
        name=run.name,
        status=run.status,
        progress_pct=run.progress_pct,
        config=config,
        period_start=run.period_start,
        period_end=run.period_end,
        delay_seconds=run.delay_seconds,
        total_trades=run.total_trades,
        wins=run.wins,
        losses=run.losses,
        total_staked=run.total_staked,
        total_pnl=run.total_pnl,
        total_return=run.total_return,
        win_rate=run.win_rate,
        profit_factor=run.profit_factor,
        max_drawdown=run.max_drawdown,
        avg_trade_pnl=run.avg_trade_pnl,
        median_trade_pnl=run.median_trade_pnl,
        sharpe_like=run.sharpe_like,
        in_sample_return=run.in_sample_return,
        validation_return=run.validation_return,
        out_of_sample_return=run.out_of_sample_return,
        walk_forward=[w for w in load_json_list(run.walk_forward_json) if isinstance(w, dict)],
        equity_curve=[float(x) for x in load_json_list(run.equity_curve_json)],
        drawdown_curve=[float(x) for x in load_json_list(run.drawdown_curve_json)],
        delay_sensitivity=delay_sensitivity,
        outcome_distribution=load_json_dict(run.outcome_distribution_json),
        by_market_type=load_json_dict(run.by_market_type_json),
        by_wallet=load_json_dict(run.by_wallet_json),
        return_ci_low=run.return_ci_low,
        return_ci_high=run.return_ci_high,
        pct_pnl_from_top_trade=run.pct_pnl_from_top_trade,
        lookahead_violations=run.lookahead_violations,
        skipped_trades=run.skipped_trades,
        skip_reasons={k: int(v) for k, v in load_json_dict(run.skip_reasons_json).items()},
        warnings=[str(w) for w in warnings],
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _execute_run(run_id: int, payload_dict: dict) -> None:
    """Background execution against its own session."""
    from ..api.schemas import BacktestCreate

    try:
        with session_scope() as session:
            run = session.get(BacktestRun, run_id)
            if run is None:
                return
            config = config_from_payload(BacktestCreate(**payload_dict))
            BacktestRunner(session).execute(run, config)
    except Exception:  # noqa: BLE001
        log.exception("backtest.background_failed", run_id=run_id)
        with session_scope() as session:
            run = session.get(BacktestRun, run_id)
            if run is not None and run.status == JobStatus.RUNNING:
                run.status = JobStatus.FAILED
                run.error = "background execution failed; see server logs"


@router.post("", response_model=s.BacktestRunOut, status_code=202)
def create_backtest(
    payload: s.BacktestCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    run_async: bool = Query(True, description="run in the background and poll for status"),
) -> s.BacktestRunOut:
    """Queue a backtest. Poll ``GET /api/backtests/{id}`` for progress."""
    try:
        config = config_from_payload(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    runner = BacktestRunner(db)
    run = runner.create_run(config)
    db.commit()

    if run_async:
        background.add_task(_execute_run, run.id, payload.model_dump(mode="json"))
        db.refresh(run)
        return _run_out(run)

    runner.execute(run, config)
    db.commit()
    db.refresh(run)
    return _run_out(run)


@router.get("", response_model=list[s.BacktestRunOut])
def list_backtests(
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[s.BacktestRunOut]:
    query = select(BacktestRun)
    if status:
        query = query.where(BacktestRun.status == status)
    rows = db.scalars(query.order_by(BacktestRun.created_at.desc()).limit(limit).offset(offset))
    return [_run_out(r) for r in rows]


@router.get("/{run_id}", response_model=s.BacktestRunOut)
def get_backtest(run_id: int, db: Session = Depends(get_db)) -> s.BacktestRunOut:
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(404, "backtest run not found")
    return _run_out(run)


@router.get("/{run_id}/trades", response_model=list[s.BacktestTradeOut])
def get_backtest_trades(
    run_id: int,
    db: Session = Depends(get_db),
    split: str | None = Query(None, description="train | validation | test"),
    wins_only: bool | None = Query(None),
    limit: int = Query(500, le=5000),
    offset: int = Query(0, ge=0),
) -> list[s.BacktestTradeOut]:
    if db.get(BacktestRun, run_id) is None:
        raise HTTPException(404, "backtest run not found")

    query = select(BacktestTrade).where(BacktestTrade.run_id == run_id)
    if split:
        query = query.where(BacktestTrade.split == split)
    if wins_only is not None:
        query = query.where(BacktestTrade.is_win.is_(wins_only))

    rows = db.scalars(query.order_by(BacktestTrade.decision_at).limit(limit).offset(offset))
    return [
        s.BacktestTradeOut(
            wallet_id=r.wallet_id,
            token_id=r.token_id,
            decision_at=r.decision_at,
            entered_at=r.entered_at,
            exited_at=r.exited_at,
            wallet_entry_price=r.wallet_entry_price,
            fill_price=r.fill_price,
            exit_price=r.exit_price,
            stake_usdc=r.stake_usdc,
            pnl=r.pnl,
            roi=r.roi,
            is_win=r.is_win,
            exit_reason=r.exit_reason,
            market_type=r.market_type,
            market_phase=r.market_phase,
            copyability_score=r.copyability_score,
            price_source_quality=r.price_source_quality,
            split=r.split,
            decision_inputs=load_json_dict(r.decision_inputs_json),
        )
        for r in rows
    ]


@router.delete("/{run_id}", response_model=s.MessageOut)
def delete_backtest(run_id: int, db: Session = Depends(get_db)) -> s.MessageOut:
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(404, "backtest run not found")
    name = run.name
    db.delete(run)
    db.commit()
    return s.MessageOut(message=f"deleted backtest '{name}'")
