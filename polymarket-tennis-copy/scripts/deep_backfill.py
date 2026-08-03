"""Deep-backfill a shortlist of wallets so their record can actually be judged.

The shallow scan capped activity at 4 pages per wallet and price evidence at 30
markets, which left copyable-ROI coverage in the single digits -- too thin to
support any conclusion. This pulls full history for a handful of wallets and
price evidence for every tennis market they touched.

It is deliberately slow: requests are paced, and this is expected to run for
hours rather than minutes.

Usage:
    DATABASE_URL="sqlite:///./data/real.db" python scripts/deep_backfill.py
    DATABASE_URL="sqlite:///./data/best.db" python scripts/deep_backfill.py 0xabc 0xdef

With no arguments it falls back to the original shortlist.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.db import get_engine, session_scope  # noqa: E402
from app.models import (  # noqa: E402
    Market,
    MarketPrice,
    Outcome,
    ReconstructedPosition,
    Wallet,
    WalletMetrics,
    WalletScore,
)
from app.providers import PolymarketProvider  # noqa: E402

# Chosen for sample size, not for flattering returns. One of them
# (0xb8fc63b6b017) looked clearly negative on the shallow pass and is included
# precisely so the deep run can confirm or overturn that.
DEFAULT_TARGETS = (
    "0x4e2c49398dd9",
    "0xcd96b01fac62",
    "0x8fb021f6e9e2",
    "0xb8fc63b6b017",
)

# Address prefixes are accepted so a shortlist can be pasted in truncated form.
TARGETS = tuple(a.lower() for a in sys.argv[1:]) or DEFAULT_TARGETS

STARTED = time.time()


def log(message: str) -> None:
    print(f"[{time.time() - STARTED:7.1f}s] {message}", flush=True)


def main() -> int:
    with session_scope() as session:
        wallets = [
            (w.id, w.address)
            for w in session.scalars(select(Wallet))
            if w.address.startswith(TARGETS)
        ]
    if not wallets:
        print("None of the target wallets are in this database.")
        return 1

    log(f"Deep backfill for {len(wallets)} wallets")

    provider = PolymarketProvider()
    try:
        # ------------------------------------------------ full trade history
        for wallet_id, address in wallets:
            log(f"Full history: {address[:14]}")
            try:
                with session_scope() as session:
                    from app.services.ingest import WalletIngestor

                    wallet = session.get(Wallet, wallet_id)
                    # max_pages=None removes the cap: fetch until the API runs dry.
                    stats = WalletIngestor(session, provider).sync_wallet(
                        wallet, full_backfill=True, max_pages=None
                    )
                log(
                    f"   fetched={stats.fetched} inserted={stats.inserted} "
                    f"dupes={stats.duplicates} markets={stats.markets_upserted}"
                )
            except Exception as exc:  # noqa: BLE001
                log(f"   ! failed: {exc}")

        # ------------------------------------------------- rebuild positions
        log("Reconstructing positions from the fuller history...")
        with session_scope() as session:
            from app.services.pipeline import AnalyticsPipeline

            pipeline = AnalyticsPipeline(session)
            for wallet_id, _ in wallets:
                pipeline.reconstruct_wallet(session.get(Wallet, wallet_id))

        # --------------------------------------------------- price evidence
        with session_scope() as session:
            market_ids = [
                row[0]
                for row in session.execute(
                    select(ReconstructedPosition.market_id)
                    .where(
                        ReconstructedPosition.wallet_id.in_([w for w, _ in wallets]),
                        ReconstructedPosition.is_tennis.is_(True),
                        ReconstructedPosition.market_id.is_not(None),
                    )
                    .group_by(ReconstructedPosition.market_id)
                    .order_by(func.count(ReconstructedPosition.id).desc())
                ).all()
            ]
        log(f"Price evidence needed for {len(market_ids)} tennis markets")

        from app.services.ingest import MarketIngestor

        for index, market_id in enumerate(market_ids, start=1):
            try:
                with session_scope() as session:
                    ingestor = MarketIngestor(session, provider)
                    market = session.get(Market, market_id)
                    if market is None:
                        continue

                    # Trade prints: the only evidence that can answer sub-minute
                    # follower delays.
                    ingestor.ingest_market_trades(market, max_pages=3)

                    # Minute bars windowed around the actual holding period.
                    bounds = session.execute(
                        select(
                            func.min(ReconstructedPosition.opened_ts),
                            func.max(
                                func.coalesce(
                                    ReconstructedPosition.closed_ts,
                                    ReconstructedPosition.opened_ts,
                                )
                            ),
                        ).where(ReconstructedPosition.market_id == market_id)
                    ).one()
                    first_ts, last_ts = bounds
                    if first_ts:
                        pad = 3600
                        start_ts = max(0, int(first_ts) - pad)
                        end_ts = int(last_ts or first_ts) + pad
                        for outcome in session.scalars(
                            select(Outcome).where(Outcome.market_id == market_id)
                        ):
                            ingestor.ingest_price_history(
                                outcome, fidelity_minutes=1,
                                start_ts=start_ts, end_ts=end_ts,
                            )
            except Exception as exc:  # noqa: BLE001
                log(f"   ! market {market_id} failed: {exc}")

            if index % 25 == 0 or index == len(market_ids):
                log(f"   {index}/{len(market_ids)} markets backfilled")
    finally:
        provider.close()

    # ------------------------------------------------------------ analytics
    log("Recomputing metrics and scores...")
    with session_scope() as session:
        from app.services.pipeline import AnalyticsPipeline

        stats = AnalyticsPipeline(session).run_full()
        log(
            f"   {stats.positions_written} positions, "
            f"{stats.copyability_rows} copyability rows, {stats.scores_written} scored"
        )

    # --------------------------------------------------------------- report
    with session_scope() as session:
        prices = session.scalar(select(func.count(MarketPrice.id)))
        log(f"   {prices} total price observations in the database")

        print("\n" + "=" * 104)
        print("DEEP-BACKFILLED WALLETS -- tennis")
        print("=" * 104)
        print(
            f"{'address':<16}{'score':>7}{'qual':>6}{'n':>5}{'raw ROI':>10}"
            f"{'copy ROI':>10}{'cover':>8}{'P(edge)':>9}{'maxDD':>8}  confidence"
        )
        for address, score, qualified, confidence, n, roi, copy_roi, cover, p_edge, dd in (
            session.execute(
                select(
                    Wallet.address, WalletScore.skill_score, WalletScore.qualified,
                    WalletScore.confidence_level, WalletMetrics.completed_positions,
                    WalletMetrics.roi, WalletMetrics.copyable_roi,
                    WalletMetrics.copyable_coverage, WalletMetrics.prob_positive_edge,
                    WalletMetrics.max_drawdown,
                )
                .join(WalletScore, WalletScore.wallet_id == Wallet.id)
                .outerjoin(
                    WalletMetrics,
                    (WalletMetrics.wallet_id == Wallet.id)
                    & (WalletMetrics.scope == "tennis"),
                )
                .where(WalletScore.scope == "tennis")
                .order_by(WalletScore.skill_score.desc())
            ).all()
        ):
            if not address.startswith(TARGETS):
                continue
            print(
                f"{address[:14]:<16}{score:>7.1f}{str(bool(qualified)):>6}{(n or 0):>5}"
                f"{_pct(roi):>10}{_pct(copy_roi):>10}{_pct(cover):>8}"
                f"{_pct(p_edge):>9}{_pct(dd):>8}  {confidence}"
            )

        print("\nHonest-hold profile (settlement holds are not a 'hold' decision):")
        for wallet_id, address in wallets:
            traded = session.execute(
                select(func.count(ReconstructedPosition.id),
                       func.avg(ReconstructedPosition.holding_seconds))
                .where(ReconstructedPosition.wallet_id == wallet_id,
                       ReconstructedPosition.is_tennis.is_(True),
                       ReconstructedPosition.settled_by_redemption.is_(False),
                       ReconstructedPosition.holding_seconds.is_not(None))
            ).one()
            settled = session.scalar(
                select(func.count(ReconstructedPosition.id))
                .where(ReconstructedPosition.wallet_id == wallet_id,
                       ReconstructedPosition.is_tennis.is_(True),
                       ReconstructedPosition.settled_by_redemption.is_(True))
            )
            n_traded, avg_traded = traded
            hold = f"{avg_traded/3600:.1f}h" if avg_traded else "n/a"
            print(
                f"   {address[:14]}  traded-out={n_traded or 0:<5} avg={hold:<9} "
                f"held-to-settlement={settled or 0}"
            )

    log("done")
    return 0


def _pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
