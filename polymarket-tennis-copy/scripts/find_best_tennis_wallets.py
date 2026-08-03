"""Find the best *tennis* traders, rather than a random sample of participants.

The first scan sampled whoever happened to hold positions in ten tennis markets
and unsurprisingly found the population average (negative). This searches
deliberately, from three directions:

1. **Tennis trade tape** -- scan the tape across many tennis markets and rank
   wallets by how much tennis they actually trade. This is the "tennis niche"
   ranking and the most targeted of the three.
2. **Platform profit leaderboard** -- top earners across all of Polymarket, then
   filtered to those with real tennis activity. Broad, and heavily
   survivorship-biased, which is why it is only a candidate source.
3. **Platform volume leaderboard** -- large operators who may run tennis books.

Candidates are then synced and ranked by their raw tennis record. Raw ROI is not
the verdict -- it is a funnel. The winners get deep-backfilled separately so
their *copyable* edge can be measured honestly.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/find_best_tennis_wallets.py
"""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import Integer, cast, func, select  # noqa: E402

from app.db import Base, get_engine, session_scope  # noqa: E402
from app.enums import WalletSource  # noqa: E402
from app.models import (  # noqa: E402
    Market,
    NormalizedTransaction,
    ReconstructedPosition,
    Wallet,
    WalletMetrics,
    WalletScore,
)
from app.providers import PolymarketProvider  # noqa: E402

# How many tennis markets to scan for the trade tape.
TAPE_MARKETS = 160
# Wallets to keep from the tape ranking.
TOP_TENNIS_TRADERS = 60
# Leaderboard depth per metric/window.
LEADERBOARD_LIMIT = 40
# Activity pages per wallet during the funnel pass (deep pass comes later).
SYNC_PAGES = 4

STARTED = time.time()


def log(message: str) -> None:
    print(f"[{time.time() - STARTED:7.1f}s] {message}", flush=True)


def main() -> int:
    Base.metadata.create_all(get_engine())
    provider = PolymarketProvider()

    try:
        # ------------------------------------------------------ tennis markets
        with session_scope() as session:
            known = session.scalar(
                select(func.count(Market.id)).where(Market.is_tennis.is_(True))
            )
        if not known:
            log("Syncing tennis markets first...")
            with session_scope() as session:
                from app.services.ingest import MarketIngestor

                stats = MarketIngestor(session, provider).sync_tennis_markets(max_pages=8)
                log(f"   {stats.markets_upserted} markets")

        # ---------------------------------------- 1. rank by tennis trade tape
        log(f"Scanning the trade tape across {TAPE_MARKETS} tennis markets...")
        with session_scope() as session:
            markets = list(
                session.execute(
                    select(Market.condition_id, Market.slug)
                    .where(Market.is_tennis.is_(True))
                    .order_by(
                        Market.volume.desc().nullslast(),
                        Market.volume_24hr.desc().nullslast(),
                    )
                    .limit(TAPE_MARKETS)
                ).all()
            )

        trade_count: dict[str, int] = defaultdict(int)
        notional: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for index, (condition_id, _slug) in enumerate(markets, start=1):
            try:
                trades = provider.get_market_trades(condition_id, limit=500, max_pages=2)
            except Exception as exc:  # noqa: BLE001
                log(f"   ! tape failed for {condition_id[:12]}: {exc}")
                continue
            for t in trades:
                if not t.wallet_address:
                    continue
                trade_count[t.wallet_address] += 1
                notional[t.wallet_address] += (t.size or Decimal("0")) * (
                    t.price or Decimal("0")
                )
            if index % 40 == 0 or index == len(markets):
                log(f"   {index}/{len(markets)} markets scanned, {len(trade_count)} wallets seen")

        ranked = sorted(
            trade_count.items(), key=lambda kv: (notional[kv[0]], kv[1]), reverse=True
        )
        top_traders = [addr for addr, _ in ranked[:TOP_TENNIS_TRADERS]]
        log(f"   top {len(top_traders)} tennis traders by notional traded")

        # ------------------------------------------------- 2/3. leaderboards
        with session_scope() as session:
            from app.services.ingest import WalletRegistry

            registry = WalletRegistry(session, provider)

            for address in top_traders:
                registry.add_wallet(
                    address,
                    source=WalletSource.MARKET_ACTIVITY,
                    source_detail=(
                        f"tennis tape: {trade_count[address]} trades, "
                        f"${notional[address]:.0f} notional"
                    ),
                    manually_approved=False,
                    sync_priority=90,
                    notes="Ranked by observed tennis trading volume. Unverified.",
                )

            for metric, window in (
                ("profit", "all"), ("profit", "30d"), ("volume", "30d")
            ):
                try:
                    result = registry.discover_from_leaderboard(
                        metric=metric, window=window, limit=LEADERBOARD_LIMIT
                    )
                    log(f"   leaderboard {metric}/{window}: +{result['added']} new")
                except Exception as exc:  # noqa: BLE001
                    log(f"   ! leaderboard {metric}/{window} failed: {exc}")

            total = session.scalar(select(func.count(Wallet.id)))
        log(f"Candidate pool: {total} wallets")

        # -------------------------------------------------------------- sync
        with session_scope() as session:
            pending = [
                (w.id, w.address)
                for w in session.scalars(
                    select(Wallet).order_by(Wallet.sync_priority.desc(), Wallet.id)
                )
            ]
        log(f"Syncing {len(pending)} wallets ({SYNC_PAGES} pages each)...")

        for index, (wallet_id, address) in enumerate(pending, start=1):
            try:
                with session_scope() as session:
                    from app.services.ingest import WalletIngestor

                    WalletIngestor(session, provider).sync_wallet(
                        session.get(Wallet, wallet_id), max_pages=SYNC_PAGES
                    )
            except Exception as exc:  # noqa: BLE001
                log(f"   ! {address[:12]} failed: {exc}")
            if index % 20 == 0 or index == len(pending):
                log(f"   {index}/{len(pending)} synced")
    finally:
        provider.close()

    # ------------------------------------------------------ reconstruct only
    # Raw record is enough to rank the funnel; copyability needs the deep pass.
    log("Reconstructing positions...")
    with session_scope() as session:
        from app.services.pipeline import AnalyticsPipeline

        pipeline = AnalyticsPipeline(session)
        for wallet in session.scalars(select(Wallet)):
            try:
                pipeline.reconstruct_wallet(wallet)
            except Exception as exc:  # noqa: BLE001
                log(f"   ! reconstruct failed for {wallet.address[:12]}: {exc}")

    # ------------------------------------------------------------- ranking
    log("Ranking by raw tennis record...")
    with session_scope() as session:
        rows = session.execute(
            select(
                Wallet.address,
                Wallet.source,
                func.count(ReconstructedPosition.id).label("n"),
                func.sum(ReconstructedPosition.net_pnl).label("pnl"),
                func.sum(ReconstructedPosition.capital_committed).label("capital"),
                func.avg(ReconstructedPosition.avg_entry_price).label("avg_entry"),
                # cast() is required: without it SQLAlchemy applies the Boolean
                # column type to the SUM result and coerces it back to True/False,
                # silently reporting 19 wins as 1.
                func.sum(
                    cast(func.coalesce(ReconstructedPosition.is_win, 0), Integer)
                ).label("wins"),
            )
            .join(ReconstructedPosition, ReconstructedPosition.wallet_id == Wallet.id)
            .where(
                ReconstructedPosition.is_tennis.is_(True),
                ReconstructedPosition.status.in_(("closed", "settled")),
            )
            .group_by(Wallet.id)
            .having(func.count(ReconstructedPosition.id) >= 20)
        ).all()

        scored = []
        for address, source, n, pnl, capital, avg_entry, wins in rows:
            capital = float(capital or 0)
            pnl = float(pnl or 0)
            if capital <= 0:
                continue
            scored.append(
                {
                    "address": address,
                    "source": source,
                    "n": n,
                    "pnl": pnl,
                    "roi": pnl / capital,
                    "capital": capital,
                    "win_rate": (wins or 0) / n if n else 0,
                    "avg_entry": float(avg_entry or 0),
                }
            )
        scored.sort(key=lambda r: r["pnl"], reverse=True)

        print("\n" + "=" * 112)
        print("TENNIS TRADERS RANKED BY RAW RECORD  (funnel only -- copyability not yet measured)")
        print("=" * 112)
        print(
            f"{'address':<16}{'trades':>7}{'net P&L':>13}{'capital':>13}"
            f"{'raw ROI':>10}{'win%':>8}{'avg entry':>11}  source"
        )
        for r in scored[:30]:
            print(
                f"{r['address'][:14]:<16}{r['n']:>7}{r['pnl']:>13,.0f}{r['capital']:>13,.0f}"
                f"{r['roi']*100:>9.1f}%{r['win_rate']*100:>7.0f}%"
                f"{r['avg_entry']:>11.3f}  {r['source']}"
            )

        print(f"\nwallets with 20+ completed tennis positions: {len(scored)}")
        profitable = [r for r in scored if r["pnl"] > 0]
        print(f"of those, profitable on raw P&L            : {len(profitable)}")
        if scored:
            total_pnl = sum(r["pnl"] for r in scored)
            total_cap = sum(r["capital"] for r in scored)
            print(f"aggregate raw ROI across the group          : {total_pnl/total_cap*100:.2f}%")

        print("\nNEXT: deep-backfill the top names to measure copyable ROI.")
        print("Raw P&L is a funnel, not a verdict -- the first scan's top raw")
        print("performer turned out to be buying $0.95 favourites.")

    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
