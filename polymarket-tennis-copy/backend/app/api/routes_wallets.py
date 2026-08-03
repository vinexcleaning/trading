"""Wallet CRUD, import, sync, metrics, activity, positions and rankings."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..enums import WalletStatus
from ..logging_setup import get_logger
from ..models import (
    Market,
    NormalizedTransaction,
    Outcome,
    ReconstructedPosition,
    TradeCopyability,
    Wallet,
    WalletCluster,
    WalletClusterMember,
    WalletMetrics,
    WalletScore,
    WalletTag,
)
from ..providers import PolymarketProvider
from ..services.ingest import WalletIngestor, WalletRegistry
from ..services.pipeline import AnalyticsPipeline
from ..services.scoring import RANKING_DEFINITIONS
from . import schemas as s
from .deps import LEADERBOARD_CAVEAT, load_json_dict, load_json_list

log = get_logger(__name__)
router = APIRouter(prefix="/api/wallets", tags=["wallets"])

# Rankings that read as "these are the good wallets". Under-sampled wallets are
# filtered out of these; they belong in "emerging" instead. "highest_raw_profit"
# is deliberately excluded from this set: it is explicitly labelled as not a
# measure of copyability, and hiding big-P&L wallets from it would be its own
# distortion.
PERFORMANCE_RANKINGS = frozenset(
    {
        "best_overall",
        "best_copyable",
        "best_live",
        "best_prematch",
        "best_match_winner",
        "best_set_market",
        "best_recent",
        "most_consistent",
        "highest_adjusted_roi",
        "lowest_drawdown",
    }
)


def _wallet_out(wallet: Wallet) -> s.WalletOut:
    return s.WalletOut(
        id=wallet.id,
        address=wallet.address,
        nickname=wallet.nickname,
        pseudonym=wallet.pseudonym,
        source=wallet.source,
        source_detail=wallet.source_detail,
        status=wallet.status,
        manually_approved=wallet.manually_approved,
        on_watchlist=wallet.on_watchlist,
        notes=wallet.notes,
        risk_flags=load_json_list(wallet.risk_flags),
        suspected_cluster_id=wallet.suspected_cluster_id,
        first_activity_at=wallet.first_activity_at,
        last_activity_at=wallet.last_activity_at,
        last_sync_success_at=wallet.last_sync_success_at,
        last_sync_error=wallet.last_sync_error,
        backfill_complete=wallet.backfill_complete,
        observed_portfolio_value=wallet.observed_portfolio_value,
        sync_priority=wallet.sync_priority,
        created_at=wallet.created_at,
    )


def _metrics_out(row: WalletMetrics) -> s.WalletMetricsOut:
    return s.WalletMetricsOut(
        scope=row.scope,
        total_positions=row.total_positions,
        completed_positions=row.completed_positions,
        open_positions=row.open_positions,
        volume_usdc=row.volume_usdc,
        capital_deployed=row.capital_deployed,
        gross_profit=row.gross_profit,
        gross_loss=row.gross_loss,
        net_profit=row.net_profit,
        roi=row.roi,
        roi_equal_weighted=row.roi_equal_weighted,
        win_rate=row.win_rate,
        profit_factor=row.profit_factor,
        avg_profit_per_trade=row.avg_profit_per_trade,
        median_profit_per_trade=row.median_profit_per_trade,
        expected_value_per_dollar=row.expected_value_per_dollar,
        avg_entry_price=row.avg_entry_price,
        avg_holding_seconds=row.avg_holding_seconds,
        max_drawdown=row.max_drawdown,
        max_drawdown_usdc=row.max_drawdown_usdc,
        longest_win_streak=row.longest_win_streak,
        longest_loss_streak=row.longest_loss_streak,
        pct_profit_from_largest_trade=row.pct_profit_from_largest_trade,
        pct_profit_from_top5_trades=row.pct_profit_from_top5_trades,
        sharpe_like=row.sharpe_like,
        benchmark_delay_seconds=row.benchmark_delay_seconds,
        copyable_roi=row.copyable_roi,
        copyable_win_rate=row.copyable_win_rate,
        copyable_net_profit=row.copyable_net_profit,
        copyable_profit_factor=row.copyable_profit_factor,
        avg_copyability_score=row.avg_copyability_score,
        copyable_coverage=row.copyable_coverage,
        roi_by_delay=load_json_dict(row.roi_by_delay),
        roi_ci_low=row.roi_ci_low,
        roi_ci_high=row.roi_ci_high,
        copyable_roi_ci_low=row.copyable_roi_ci_low,
        copyable_roi_ci_high=row.copyable_roi_ci_high,
        shrunk_copyable_roi=row.shrunk_copyable_roi,
        prob_positive_edge=row.prob_positive_edge,
        sample_confidence=row.sample_confidence,
        data_quality_score=row.data_quality_score,
        performance_by_market_type=load_json_dict(row.performance_by_market_type),
        performance_by_tournament=load_json_dict(row.performance_by_tournament),
        performance_by_player=load_json_dict(row.performance_by_player),
        performance_by_entry_bucket=load_json_dict(row.performance_by_entry_bucket),
        performance_by_size_bucket=load_json_dict(row.performance_by_size_bucket),
        performance_by_period=load_json_dict(row.performance_by_period),
        computed_at=row.computed_at,
    )


def _score_out(row: WalletScore) -> s.WalletScoreOut:
    return s.WalletScoreOut(
        skill_score=row.skill_score,
        base_score=row.base_score,
        components=s.ScoreComponentsOut(
            copyable_roi=row.copyable_roi_score,
            profit_factor=row.profit_factor_score,
            sample_confidence=row.sample_confidence_score,
            consistency=row.consistency_score,
            drawdown=row.drawdown_score,
            recency=row.recency_score,
            liquidity_fit=row.liquidity_fit_score,
            concentration=row.concentration_score,
            data_quality=row.data_quality_score,
        ),
        penalties_applied=load_json_dict(row.penalties_applied),
        total_penalty_multiplier=row.total_penalty_multiplier,
        risk_flags=load_json_list(row.risk_flags),
        qualified=row.qualified,
        disqualification_reasons=load_json_list(row.disqualification_reasons),
        confidence_level=row.confidence_level,
        explanation=row.explanation,
        formula_version=row.formula_version,
        computed_at=row.computed_at,
    )


# ------------------------------------------------------------------- listing


@router.get("", response_model=list[s.WalletOut])
def list_wallets(
    db: Session = Depends(get_db),
    status: str | None = Query(None, description="active | inactive | blocked"),
    approved: bool | None = Query(None),
    watchlist: bool | None = Query(None),
    search: str | None = Query(None, description="address or nickname substring"),
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
) -> list[s.WalletOut]:
    query = select(Wallet)
    if status:
        query = query.where(Wallet.status == status)
    if approved is not None:
        query = query.where(Wallet.manually_approved.is_(approved))
    if watchlist is not None:
        query = query.where(Wallet.on_watchlist.is_(watchlist))
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            func.lower(Wallet.address).like(pattern)
            | func.lower(func.coalesce(Wallet.nickname, "")).like(pattern)
        )
    query = query.order_by(Wallet.sync_priority.desc(), Wallet.id).limit(limit).offset(offset)
    return [_wallet_out(w) for w in db.scalars(query)]


@router.post("", response_model=s.WalletOut, status_code=201)
def create_wallet(payload: s.WalletCreate, db: Session = Depends(get_db)) -> s.WalletOut:
    registry = WalletRegistry(db)
    wallet, created = registry.add_wallet(
        payload.address,
        nickname=payload.nickname,
        notes=payload.notes,
        manually_approved=payload.manually_approved,
        on_watchlist=payload.on_watchlist,
        sync_priority=payload.sync_priority,
    )
    for tag in payload.tags:
        if not db.scalar(
            select(WalletTag).where(WalletTag.wallet_id == wallet.id, WalletTag.tag == tag)
        ):
            db.add(WalletTag(wallet_id=wallet.id, tag=tag))
    db.commit()
    db.refresh(wallet)
    if not created:
        log.info("api.wallet_exists", address=wallet.address)
    return _wallet_out(wallet)


@router.post("/import", response_model=s.ImportResultOut)
async def import_wallets(
    file: UploadFile = File(..., description="CSV with an 'address' column"),
    db: Session = Depends(get_db),
) -> s.ImportResultOut:
    content = (await file.read()).decode("utf-8", errors="replace")
    result = WalletRegistry(db).import_csv(content)
    db.commit()
    return s.ImportResultOut(**result)


@router.post("/discover", response_model=s.MessageOut)
def discover_wallets(
    db: Session = Depends(get_db),
    source: str = Query("tennis_markets", description="tennis_markets | leaderboard"),
    metric: str = Query("volume", description="leaderboard only: volume | profit"),
    window: str = Query("30d"),
    limit: int = Query(50, le=200),
) -> s.MessageOut:
    """Discover candidate wallets. Never auto-approves."""
    provider = PolymarketProvider()
    try:
        registry = WalletRegistry(db, provider)
        if source == "leaderboard":
            result = registry.discover_from_leaderboard(
                metric=metric, window=window, limit=limit
            )
        else:
            result = registry.discover_from_tennis_markets()
        db.commit()
    finally:
        provider.close()
    return s.MessageOut(
        message=(
            f"Discovered {result['added']} new candidate wallets from {result['candidates']} "
            "observed. None were auto-approved: discovery is not evidence of tennis skill."
        ),
        detail=result,
    )


# -------------------------------------------------------------------- detail


@router.get("/rankings", response_model=list[s.RankingOut])
def get_rankings(
    db: Session = Depends(get_db),
    keys: str | None = Query(None, description="comma-separated ranking keys"),
    limit: int = Query(25, le=200),
    qualified_only: bool = Query(False),
    min_sample: int = Query(0, ge=0),
) -> list[s.RankingOut]:
    """Multiple rankings rather than one misleading leaderboard."""
    requested = (
        [k.strip() for k in keys.split(",") if k.strip()]
        if keys
        else list(RANKING_DEFINITIONS)
    )

    out: list[s.RankingOut] = []
    for key in requested:
        definition = RANKING_DEFINITIONS.get(key)
        if definition is None:
            continue
        scope = definition["scope"]
        sort = definition["sort"]

        query = (
            select(Wallet, WalletScore, WalletMetrics)
            .join(WalletScore, WalletScore.wallet_id == Wallet.id)
            .outerjoin(
                WalletMetrics,
                (WalletMetrics.wallet_id == Wallet.id) & (WalletMetrics.scope == scope),
            )
            .where(WalletScore.scope == "tennis")
        )
        if qualified_only:
            query = query.where(WalletScore.qualified.is_(True))
        if min_sample:
            query = query.where(WalletMetrics.completed_positions >= min_sample)

        rows = list(db.execute(query))

        def sort_key(row) -> tuple:
            _, score, metrics = row
            if sort == "skill_score":
                return (score.skill_score,)
            if sort == "consistency":
                return (score.consistency_score,)
            if sort == "emerging":
                # Promising but under-sampled: rank by score, restricted below.
                return (score.skill_score,)
            if sort == "-max_drawdown":
                return (-(metrics.max_drawdown if metrics and metrics.max_drawdown is not None else 1.0),)
            value = getattr(metrics, sort, None) if metrics else None
            # Missing values sort last rather than being treated as zero.
            return (value if value is not None else float("-inf"),)

        if key == "emerging":
            floor = get_settings().alert_min_tennis_trades
            rows = [
                r
                for r in rows
                if r[2] is not None and 0 < r[2].completed_positions < floor
            ]
        elif key == "highest_confidence":
            rows = [r for r in rows if r[2] is not None and r[2].prob_positive_edge is not None]
        elif key in PERFORMANCE_RANKINGS:
            # Under-sampled wallets are excluded from rankings that read as a
            # recommendation. Eight lucky wins can produce a huge ROI, and
            # letting that top "best copyable wallets" is precisely the
            # misleading leaderboard this system is built to avoid. Those wallets
            # are not hidden -- they appear under "Emerging", labelled unproven.
            soft_floor = get_settings().min_trades_soft_floor
            rows = [
                r
                for r in rows
                if r[2] is not None and r[2].completed_positions >= soft_floor
            ]

        rows.sort(key=sort_key, reverse=True)

        ranking_rows: list[s.RankingRowOut] = []
        for index, (wallet, score, metrics) in enumerate(rows[:limit], start=1):
            ranking_rows.append(
                s.RankingRowOut(
                    rank=index,
                    wallet_id=wallet.id,
                    address=wallet.address,
                    nickname=wallet.nickname,
                    skill_score=score.skill_score,
                    qualified=score.qualified,
                    confidence_level=score.confidence_level,
                    completed_positions=metrics.completed_positions if metrics else 0,
                    roi=metrics.roi if metrics else None,
                    copyable_roi=metrics.copyable_roi if metrics else None,
                    shrunk_copyable_roi=metrics.shrunk_copyable_roi if metrics else None,
                    copyable_coverage=metrics.copyable_coverage if metrics else None,
                    net_profit=metrics.net_profit if metrics else None,
                    max_drawdown=metrics.max_drawdown if metrics else None,
                    prob_positive_edge=metrics.prob_positive_edge if metrics else None,
                    last_activity_at=wallet.last_activity_at,
                    risk_flags=load_json_list(score.risk_flags),
                    cluster_id=wallet.suspected_cluster_id,
                )
            )

        caveat = definition["description"] + " " + LEADERBOARD_CAVEAT
        if key == "highest_raw_profit":
            caveat = (
                "Raw profit ignores whether a follower could have captured it. "
                + LEADERBOARD_CAVEAT
            )
        elif key == "emerging":
            caveat = (
                "These wallets are below the minimum sample size and are explicitly "
                "unproven. " + LEADERBOARD_CAVEAT
            )

        out.append(
            s.RankingOut(
                key=key,
                label=definition["label"],
                description=definition["description"],
                scope=scope,
                rows=ranking_rows,
                caveat=caveat,
            )
        )
    return out


@router.get("/rotation", response_model=dict)
def get_rotation(
    db: Session = Depends(get_db),
    min_lifetime_trades: int = Query(10, ge=1, le=500),
) -> dict:
    """Who to follow right now, and who to stop following.

    Ranks *current* followability rather than lifetime quality. A wallet that has
    stopped trading is dropped whatever its record -- the static leaderboard
    ranked a 57-day-silent wallet first, which is the failure this replaces.
    """
    from ..services.allocation import AllocationEngine, rotation_report

    report = rotation_report(db)
    if min_lifetime_trades != 10:
        engine = AllocationEngine(db)
        states = engine.evaluate_all(min_lifetime_trades=min_lifetime_trades)
        buckets: dict[str, list[dict]] = {}
        for state in states:
            buckets.setdefault(state.stance.value, []).append(state.as_dict())
        report.update({k: buckets.get(k, []) for k in
                       ("follow", "probation", "watch", "pause", "drop")})
        report["summary"]["evaluated"] = len(states)
        report["summary"]["followable"] = len(report["follow"])
    return report


@router.get("/{wallet_id}", response_model=s.WalletDetailOut)
def get_wallet(wallet_id: int, db: Session = Depends(get_db)) -> s.WalletDetailOut:
    wallet = db.get(Wallet, wallet_id)
    if wallet is None:
        raise HTTPException(404, "wallet not found")

    metrics = {
        row.scope: _metrics_out(row)
        for row in db.scalars(
            select(WalletMetrics).where(WalletMetrics.wallet_id == wallet_id)
        )
    }
    score_row = db.scalar(
        select(WalletScore).where(
            WalletScore.wallet_id == wallet_id, WalletScore.scope == "tennis"
        )
    )
    tags = [t.tag for t in wallet.tags]

    cluster_out = None
    if wallet.suspected_cluster_id:
        cluster = db.get(WalletCluster, wallet.suspected_cluster_id)
        if cluster is not None:
            members = []
            for member in db.scalars(
                select(WalletClusterMember).where(
                    WalletClusterMember.cluster_id == cluster.id
                )
            ):
                peer = db.get(Wallet, member.wallet_id)
                members.append(
                    s.ClusterMemberOut(
                        wallet_id=member.wallet_id,
                        address=peer.address if peer else "unknown",
                        shared_market_count=member.shared_market_count,
                        jaccard_similarity=member.jaccard_similarity,
                        timing_correlation=member.timing_correlation,
                        size_correlation=member.size_correlation,
                        coordinated_exit_count=member.coordinated_exit_count,
                    )
                )
            cluster_out = s.ClusterOut(
                id=cluster.id,
                label=cluster.label,
                relation=cluster.relation,
                confidence=cluster.confidence,
                evidence=cluster.evidence,
                member_count=cluster.member_count,
                members=members,
            )

    return s.WalletDetailOut(
        wallet=_wallet_out(wallet),
        score=_score_out(score_row) if score_row else None,
        metrics=metrics,
        tags=tags,
        cluster=cluster_out,
        behavioural_profile=_behavioural_profile(db, wallet_id),
    )


def _behavioural_profile(db: Session, wallet_id: int) -> dict:
    """Descriptive behaviour summary for the wallet profile page."""
    rows = list(
        db.execute(
            select(
                ReconstructedPosition.behaviour,
                ReconstructedPosition.entry_phase,
                ReconstructedPosition.tennis_market_type,
                ReconstructedPosition.capital_committed,
                ReconstructedPosition.holding_seconds,
                ReconstructedPosition.accumulated,
                ReconstructedPosition.scaled_in_at_worse_prices,
                ReconstructedPosition.held_both_outcomes,
                ReconstructedPosition.net_pnl,
                ReconstructedPosition.settled_by_redemption,
            ).where(
                ReconstructedPosition.wallet_id == wallet_id,
                ReconstructedPosition.is_tennis.is_(True),
            )
        )
    )
    if not rows:
        return {"positions": 0}

    def share(predicate) -> float:
        return round(sum(1 for r in rows if predicate(r)) / len(rows), 4)

    sizes = sorted(float(r[3] or 0) for r in rows)

    # Hold time must be split by how the position closed. A position closed by
    # redemption is timed to settlement bookkeeping, which is days after the
    # match ends -- averaging that together with genuine sells produces a hold
    # figure that describes neither. The distinction also matters on its own:
    # a wallet that never sells early cannot strand a follower.
    traded_holds = sorted(r[4] for r in rows if r[4] is not None and not r[9])
    settled_count = sum(1 for r in rows if r[9])
    holds = sorted(r[4] for r in rows if r[4] is not None)

    behaviours: dict[str, int] = {}
    phases: dict[str, int] = {}
    types: dict[str, int] = {}
    for r in rows:
        behaviours[r[0]] = behaviours.get(r[0], 0) + 1
        phases[r[1]] = phases.get(r[1], 0) + 1
        types[r[2]] = types.get(r[2], 0) + 1

    # Do large trades outperform small ones? Split at the median stake.
    midpoint = len(sizes) // 2
    threshold = sizes[midpoint] if sizes else 0.0
    large = [float(r[8] or 0) for r in rows if float(r[3] or 0) >= threshold]
    small = [float(r[8] or 0) for r in rows if float(r[3] or 0) < threshold]

    return {
        "positions": len(rows),
        "behaviours": behaviours,
        "phases": phases,
        "market_types": types,
        "median_position_usdc": round(sizes[midpoint], 2) if sizes else None,
        "largest_position_usdc": round(sizes[-1], 2) if sizes else None,
        "median_hold_seconds": holds[len(holds) // 2] if holds else None,
        # How long the wallet actually held risk before selling out.
        "median_hold_seconds_traded_out": (
            traded_holds[len(traded_holds) // 2] if traded_holds else None
        ),
        "positions_traded_out": len(traded_holds),
        "positions_held_to_settlement": settled_count,
        "pct_held_to_settlement": round(settled_count / len(rows), 4) if rows else None,
        "scales_into_positions": share(lambda r: r[5]),
        "averages_down": share(lambda r: r[6]),
        "holds_both_outcomes": share(lambda r: r[7]),
        "avg_pnl_large_trades": round(sum(large) / len(large), 4) if large else None,
        "avg_pnl_small_trades": round(sum(small) / len(small), 4) if small else None,
        "large_trades_outperform": (
            (sum(large) / len(large)) > (sum(small) / len(small))
            if large and small
            else None
        ),
    }


@router.patch("/{wallet_id}", response_model=s.WalletOut)
def update_wallet(
    wallet_id: int, payload: s.WalletUpdate, db: Session = Depends(get_db)
) -> s.WalletOut:
    wallet = db.get(Wallet, wallet_id)
    if wallet is None:
        raise HTTPException(404, "wallet not found")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in tuple(WalletStatus):
        raise HTTPException(422, f"invalid status: {data['status']}")
    if data.get("manually_approved") and not wallet.manually_approved:
        wallet.approved_at = datetime.now(timezone.utc)
    for key, value in data.items():
        setattr(wallet, key, value)
    db.commit()
    db.refresh(wallet)
    return _wallet_out(wallet)


@router.delete("/{wallet_id}", response_model=s.MessageOut)
def delete_wallet(wallet_id: int, db: Session = Depends(get_db)) -> s.MessageOut:
    wallet = db.get(Wallet, wallet_id)
    if wallet is None:
        raise HTTPException(404, "wallet not found")
    address = wallet.address
    db.delete(wallet)
    db.commit()
    return s.MessageOut(message=f"deleted wallet {address}")


# ---------------------------------------------------------------------- sync


@router.post("/{wallet_id}/sync", response_model=s.MessageOut)
def sync_wallet(
    wallet_id: int,
    db: Session = Depends(get_db),
    full_backfill: bool = Query(False),
    max_pages: int = Query(5, le=50),
    run_analytics: bool = Query(True),
) -> s.MessageOut:
    wallet = db.get(Wallet, wallet_id)
    if wallet is None:
        raise HTTPException(404, "wallet not found")

    provider = PolymarketProvider()
    try:
        stats = WalletIngestor(db, provider).sync_wallet(
            wallet, full_backfill=full_backfill, max_pages=max_pages
        )
        db.commit()

        detail = {
            "fetched": stats.fetched,
            "inserted": stats.inserted,
            "duplicates": stats.duplicates,
            "failed": stats.failed,
            "markets_upserted": stats.markets_upserted,
            "notes": stats.notes,
        }

        if run_analytics:
            pipeline = AnalyticsPipeline(db)
            detail["positions"] = pipeline.reconstruct_wallet(wallet)
            detail["copyability_rows"] = pipeline.compute_copyability(wallet)
            scopes = pipeline.compute_metrics(wallet)
            if "tennis" in scopes:
                pipeline.compute_score(wallet, scopes["tennis"])
            db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        wallet = db.get(Wallet, wallet_id)
        if wallet is not None:
            wallet.last_sync_error = str(exc)[:2000]
            db.commit()
        raise HTTPException(502, f"sync failed: {exc}") from exc
    finally:
        provider.close()

    return s.MessageOut(message=f"synced {wallet.address}", detail=detail)


# ------------------------------------------------------------------- metrics


@router.get("/{wallet_id}/metrics", response_model=dict[str, s.WalletMetricsOut])
def get_wallet_metrics(
    wallet_id: int, db: Session = Depends(get_db), scope: str | None = Query(None)
) -> dict[str, s.WalletMetricsOut]:
    query = select(WalletMetrics).where(WalletMetrics.wallet_id == wallet_id)
    if scope:
        query = query.where(WalletMetrics.scope == scope)
    rows = list(db.scalars(query))
    if not rows:
        raise HTTPException(404, "no metrics for this wallet; run a sync first")
    return {row.scope: _metrics_out(row) for row in rows}


@router.get("/{wallet_id}/activity", response_model=list[s.TransactionOut])
def get_wallet_activity(
    wallet_id: int,
    db: Session = Depends(get_db),
    tennis_only: bool = Query(False),
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
) -> list[s.TransactionOut]:
    query = select(NormalizedTransaction).where(
        NormalizedTransaction.wallet_id == wallet_id
    )
    if tennis_only:
        query = query.where(NormalizedTransaction.is_tennis.is_(True))
    query = (
        query.order_by(NormalizedTransaction.timestamp.desc()).limit(limit).offset(offset)
    )
    rows = list(db.scalars(query))

    market_titles = _market_titles(db, [r.market_id for r in rows if r.market_id])
    outcome_labels = _outcome_labels(db, [r.token_id for r in rows if r.token_id])

    return [
        s.TransactionOut(
            id=r.id,
            timestamp=r.timestamp,
            occurred_at=r.occurred_at,
            activity_type=r.activity_type,
            side=r.side,
            size=r.size,
            price=r.price,
            usdc_size=r.usdc_size,
            token_id=r.token_id,
            condition_id=r.condition_id,
            market_question=market_titles.get(r.market_id),
            outcome_label=outcome_labels.get(r.token_id),
            market_phase=r.market_phase,
            is_tennis=r.is_tennis,
            transaction_hash=r.transaction_hash,
        )
        for r in rows
    ]


@router.get("/{wallet_id}/positions", response_model=list[s.PositionOut])
def get_wallet_positions(
    wallet_id: int,
    db: Session = Depends(get_db),
    tennis_only: bool = Query(True),
    status: str | None = Query(None),
    include_copyability: bool = Query(True),
    limit: int = Query(200, le=1000),
) -> list[s.PositionOut]:
    query = select(ReconstructedPosition).where(
        ReconstructedPosition.wallet_id == wallet_id
    )
    if tennis_only:
        query = query.where(ReconstructedPosition.is_tennis.is_(True))
    if status:
        query = query.where(ReconstructedPosition.status == status)
    rows = list(db.scalars(query.order_by(ReconstructedPosition.opened_ts.desc()).limit(limit)))

    market_titles = _market_titles(db, [r.market_id for r in rows if r.market_id])
    outcome_labels = _outcome_labels(db, [r.token_id for r in rows])

    copy_map: dict[int, list[s.CopyabilityOut]] = {}
    if include_copyability and rows:
        for c in db.scalars(
            select(TradeCopyability)
            .where(TradeCopyability.position_id.in_([r.id for r in rows]))
            .order_by(TradeCopyability.delay_seconds)
        ):
            copy_map.setdefault(c.position_id, []).append(
                s.CopyabilityOut(
                    delay_seconds=c.delay_seconds,
                    wallet_entry_price=c.wallet_entry_price,
                    price_after_delay=c.price_after_delay,
                    estimated_fill_price=c.estimated_fill_price,
                    price_deterioration=c.price_deterioration,
                    slippage=c.slippage,
                    available_liquidity=c.available_liquidity,
                    follower_roi=c.follower_roi,
                    follower_is_win=c.follower_is_win,
                    copyability_score=c.copyability_score,
                    price_source_quality=c.price_source_quality,
                    data_confidence=c.data_confidence,
                    notes=c.notes,
                )
            )

    return [
        s.PositionOut(
            id=r.id,
            token_id=r.token_id,
            condition_id=r.condition_id,
            market_question=market_titles.get(r.market_id),
            outcome_label=outcome_labels.get(r.token_id),
            status=r.status,
            tennis_market_type=r.tennis_market_type,
            entry_phase=r.entry_phase,
            opened_at=r.opened_at,
            closed_at=r.closed_at,
            first_entry_price=r.first_entry_price,
            avg_entry_price=r.avg_entry_price,
            avg_exit_price=r.avg_exit_price,
            entry_tx_count=r.entry_tx_count,
            accumulated=r.accumulated,
            partial_exit_count=r.partial_exit_count,
            capital_committed=r.capital_committed,
            max_shares=r.max_shares,
            realized_pnl=r.realized_pnl,
            net_pnl=r.net_pnl,
            roi=r.roi,
            is_win=r.is_win,
            holding_seconds=r.holding_seconds,
            behaviour=r.behaviour,
            flags=load_json_list(r.flags),
            reconstruction_confidence=r.reconstruction_confidence,
            pct_of_wallet_capital=r.pct_of_wallet_capital,
            copyability=copy_map.get(r.id, []),
        )
        for r in rows
    ]


def _market_titles(db: Session, market_ids: list[int]) -> dict[int, str | None]:
    if not market_ids:
        return {}
    rows = db.execute(
        select(Market.id, Market.question).where(Market.id.in_(set(market_ids)))
    )
    return {market_id: question for market_id, question in rows}


def _outcome_labels(db: Session, token_ids: list[str]) -> dict[str, str]:
    clean = [t for t in token_ids if t]
    if not clean:
        return {}
    rows = db.execute(
        select(Outcome.token_id, Outcome.label).where(Outcome.token_id.in_(set(clean)))
    )
    return {token_id: label for token_id, label in rows}
