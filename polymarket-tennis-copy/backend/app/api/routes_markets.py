"""Market search, detail, price history and classification review."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import TennisMarketType
from ..models import (
    Event,
    LiquiditySnapshot,
    ManualOverride,
    Market,
    MarketPrice,
    NormalizedTransaction,
    Outcome,
    PaperTrade,
    ReconstructedPosition,
    Signal,
    Wallet,
)
from . import schemas as s
from .deps import load_json_list

router = APIRouter(prefix="/api/markets", tags=["markets"])


def _market_out(db: Session, market: Market) -> s.MarketOut:
    event = db.get(Event, market.event_id) if market.event_id else None
    return s.MarketOut(
        id=market.id,
        condition_id=market.condition_id,
        slug=market.slug,
        question=market.question,
        is_tennis=market.is_tennis,
        tennis_market_type=market.tennis_market_type,
        sports_market_type_raw=market.sports_market_type_raw,
        classification_confidence=market.classification_confidence,
        classification_methods=load_json_list(market.classification_methods),
        classification_notes=market.classification_notes,
        needs_review=market.needs_review,
        reviewed_by_human=market.reviewed_by_human,
        period_number=market.period_number,
        game_start_time=market.game_start_time,
        closed=market.closed,
        resolved=market.resolved,
        winning_outcome_index=market.winning_outcome_index,
        accepting_orders=market.accepting_orders,
        liquidity=market.liquidity,
        volume_24hr=market.volume_24hr,
        spread=market.spread,
        best_bid=market.best_bid,
        best_ask=market.best_ask,
        tick_size=market.tick_size,
        outcomes=[
            s.OutcomeOut(
                token_id=o.token_id,
                outcome_index=o.outcome_index,
                label=o.label,
                player_name=o.player_name,
                is_winner=o.is_winner,
                last_price=o.last_price,
            )
            for o in sorted(market.outcomes, key=lambda x: x.outcome_index)
        ],
        tournament=event.tournament if event else None,
        player_a=event.player_a if event else None,
        player_b=event.player_b if event else None,
        surface=event.surface if event else None,
        tour=event.tour if event else None,
        best_of=event.best_of if event else None,
    )


@router.get("", response_model=list[s.MarketOut])
def search_markets(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="question or slug substring"),
    tennis_only: bool = Query(True),
    market_type: str | None = Query(None),
    closed: bool | None = Query(None),
    resolved: bool | None = Query(None),
    needs_review: bool | None = Query(None),
    min_liquidity: float | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> list[s.MarketOut]:
    query = select(Market)
    if tennis_only:
        query = query.where(Market.is_tennis.is_(True))
    if q:
        pattern = f"%{q.lower()}%"
        query = query.where(
            func.lower(func.coalesce(Market.question, "")).like(pattern)
            | func.lower(func.coalesce(Market.slug, "")).like(pattern)
        )
    if market_type:
        if market_type not in tuple(TennisMarketType):
            raise HTTPException(422, f"invalid market_type: {market_type}")
        query = query.where(Market.tennis_market_type == market_type)
    if closed is not None:
        query = query.where(Market.closed.is_(closed))
    if resolved is not None:
        query = query.where(Market.resolved.is_(resolved))
    if needs_review is not None:
        query = query.where(Market.needs_review.is_(needs_review))
    if min_liquidity is not None:
        query = query.where(Market.liquidity >= min_liquidity)

    query = (
        query.order_by(Market.game_start_time.desc().nullslast(), Market.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_market_out(db, m) for m in db.scalars(query)]


@router.get("/review-queue", response_model=list[s.MarketOut])
def review_queue(
    db: Session = Depends(get_db), limit: int = Query(50, le=200)
) -> list[s.MarketOut]:
    """Markets whose classification is ambiguous and needs a human decision."""
    rows = db.scalars(
        select(Market)
        .where(Market.needs_review.is_(True), Market.reviewed_by_human.is_(False))
        .order_by(Market.classification_confidence.asc())
        .limit(limit)
    )
    return [_market_out(db, m) for m in rows]


@router.get("/{market_id}", response_model=s.MarketDetailOut)
def get_market(
    market_id: int,
    db: Session = Depends(get_db),
    price_points: int = Query(2000, le=20000),
) -> s.MarketDetailOut:
    market = db.get(Market, market_id)
    if market is None:
        raise HTTPException(404, "market not found")

    token_ids = [o.token_id for o in market.outcomes]

    history = [
        s.PricePointOut(
            token_id=p.token_id,
            timestamp=p.timestamp,
            price=p.price,
            kind=p.kind,
            size=p.size,
        )
        for p in db.scalars(
            select(MarketPrice)
            .where(MarketPrice.token_id.in_(token_ids))
            .order_by(MarketPrice.timestamp)
            .limit(price_points)
        )
    ]

    # Wallet entries/exits, for overlay on the price chart.
    activity: list[dict] = []
    for tx in db.scalars(
        select(NormalizedTransaction)
        .where(NormalizedTransaction.market_id == market_id)
        .order_by(NormalizedTransaction.timestamp)
        .limit(500)
    ):
        wallet = db.get(Wallet, tx.wallet_id)
        activity.append(
            {
                "wallet_id": tx.wallet_id,
                "address": wallet.address if wallet else None,
                "nickname": wallet.nickname if wallet else None,
                "timestamp": tx.timestamp,
                "side": tx.side,
                "size": str(tx.size),
                "price": str(tx.price) if tx.price is not None else None,
                "usdc_size": str(tx.usdc_size) if tx.usdc_size is not None else None,
                "token_id": tx.token_id,
                "activity_type": tx.activity_type,
                "market_phase": tx.market_phase,
            }
        )

    open_positions: list[dict] = []
    for pos in db.scalars(
        select(ReconstructedPosition).where(
            ReconstructedPosition.market_id == market_id,
            ReconstructedPosition.status.in_(("open", "partially_closed")),
        )
    ):
        wallet = db.get(Wallet, pos.wallet_id)
        open_positions.append(
            {
                "wallet_id": pos.wallet_id,
                "address": wallet.address if wallet else None,
                "token_id": pos.token_id,
                "avg_entry_price": str(pos.avg_entry_price),
                "current_shares": str(pos.current_shares),
                "capital_committed": str(pos.capital_committed),
                "opened_at": pos.opened_at.isoformat(),
                "behaviour": pos.behaviour,
            }
        )

    liquidity = None
    snapshot = db.scalar(
        select(LiquiditySnapshot)
        .where(LiquiditySnapshot.token_id.in_(token_ids))
        .order_by(LiquiditySnapshot.timestamp.desc())
    )
    if snapshot is not None:
        liquidity = {
            "token_id": snapshot.token_id,
            "observed_at": snapshot.observed_at.isoformat(),
            "best_bid": str(snapshot.best_bid) if snapshot.best_bid else None,
            "best_ask": str(snapshot.best_ask) if snapshot.best_ask else None,
            "midpoint": str(snapshot.midpoint) if snapshot.midpoint else None,
            "spread": str(snapshot.spread) if snapshot.spread else None,
            "ask_depth_total_usdc": str(snapshot.ask_depth_usdc or 0),
            # Depth near touch is what a follower can realistically take.
            "ask_depth_within_1c_usdc": str(snapshot.ask_depth_1c_usdc or 0),
            "ask_depth_within_5c_usdc": str(snapshot.ask_depth_5c_usdc or 0),
            "bids": load_json_list(snapshot.bids_json),
            "asks": load_json_list(snapshot.asks_json),
        }

    from .routes_paper import _trade_out
    from .routes_signals import _signal_out, _signal_wallets

    signal_rows = list(
        db.scalars(
            select(Signal)
            .where(Signal.market_id == market_id)
            .order_by(Signal.detected_at.desc())
            .limit(50)
        )
    )
    wallets_by_signal = _signal_wallets(db, [row.id for row in signal_rows])
    signals = [
        _signal_out(
            row,
            market_question=market.question,
            wallets=wallets_by_signal.get(row.id, []),
        )
        for row in signal_rows
    ]
    paper = [
        _trade_out(t, market.question)
        for t in db.scalars(
            select(PaperTrade)
            .where(PaperTrade.market_id == market_id)
            .order_by(PaperTrade.created_at.desc())
            .limit(50)
        )
    ]

    return s.MarketDetailOut(
        market=_market_out(db, market),
        price_history=history,
        wallet_activity=activity,
        open_positions=open_positions,
        liquidity=liquidity,
        signals=signals,
        paper_trades=paper,
    )


@router.post("/{market_id}/override", response_model=s.MarketOut)
def override_classification(
    market_id: int,
    db: Session = Depends(get_db),
    is_tennis: bool | None = Body(None),
    tennis_market_type: str | None = Body(None),
    reason: str | None = Body(None),
) -> s.MarketOut:
    """Record a human classification decision.

    Stored as an override row *and* applied to the market, with
    ``reviewed_by_human`` set so re-classification will not overwrite it.
    """
    market = db.get(Market, market_id)
    if market is None:
        raise HTTPException(404, "market not found")
    if tennis_market_type is not None and tennis_market_type not in tuple(TennisMarketType):
        raise HTTPException(422, f"invalid tennis_market_type: {tennis_market_type}")

    fields: dict[str, str] = {}
    if is_tennis is not None:
        fields["is_tennis"] = str(is_tennis).lower()
        market.is_tennis = is_tennis
    if tennis_market_type is not None:
        fields["tennis_market_type"] = tennis_market_type
        market.tennis_market_type = tennis_market_type

    if not fields:
        raise HTTPException(422, "provide is_tennis and/or tennis_market_type")

    for field, value in fields.items():
        existing = db.scalar(
            select(ManualOverride).where(
                ManualOverride.entity_type == "market",
                ManualOverride.entity_key == market.condition_id,
                ManualOverride.field == field,
            )
        )
        if existing is None:
            db.add(
                ManualOverride(
                    entity_type="market",
                    entity_key=market.condition_id,
                    field=field,
                    value=value,
                    reason=reason,
                )
            )
        else:
            existing.value = value
            existing.reason = reason
            existing.active = True

    market.reviewed_by_human = True
    market.needs_review = False
    market.classification_confidence = 100.0
    db.commit()
    db.refresh(market)
    return _market_out(db, market)
