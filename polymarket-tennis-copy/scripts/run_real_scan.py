"""Point the system at real Polymarket wallets and report what it finds.

Read-only. Discovers wallets from public tennis-market activity, syncs their
history, backfills price evidence, then scores them. Prints the honest answer to
"is anyone actually copyable", including when the answer is "not enough
evidence to say".

Usage:
    DATABASE_URL="sqlite:///./data/real.db" python scripts/run_real_scan.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import Base, get_engine, session_scope  # noqa: E402
from app.models import Market, NormalizedTransaction, Wallet, WalletMetrics, WalletScore  # noqa: E402
from app.providers import PolymarketProvider  # noqa: E402

# Bounded so a single run cannot hammer the upstream API.
MAX_WALLETS = 40
ACTIVITY_PAGES = 4
BACKFILL_MARKETS = 30


def main() -> int:
    Base.metadata.create_all(get_engine())
    started = time.time()

    def elapsed() -> str:
        return f"[{time.time() - started:6.1f}s]"

    provider = PolymarketProvider()
    try:
        # ---------------------------------------------------------- markets
        print(f"{elapsed()} Syncing tennis markets from Gamma...")
        with session_scope() as session:
            from app.services.ingest import MarketIngestor

            stats = MarketIngestor(session, provider).sync_tennis_markets(max_pages=8)
            print(f"{elapsed()}   {stats.markets_upserted} markets, {stats.events_upserted} events")

        # -------------------------------------------------------- discovery
        print(f"{elapsed()} Discovering wallets from public tennis activity...")
        with session_scope() as session:
            from app.services.ingest import WalletRegistry

            registry = WalletRegistry(session, provider)
            result = registry.discover_from_tennis_markets(limit_per_market=25)
            print(
                f"{elapsed()}   {result['added']} added from {result['candidates']} observed"
            )

        # ------------------------------------------------------------ sync
        with session_scope() as session:
            wallets = list(
                session.scalars(select(Wallet).order_by(Wallet.id).limit(MAX_WALLETS))
            )
            addresses = [(w.id, w.address) for w in wallets]
        print(f"{elapsed()} Syncing history for {len(addresses)} wallets...")

        for index, (wallet_id, address) in enumerate(addresses, start=1):
            try:
                with session_scope() as session:
                    from app.services.ingest import WalletIngestor

                    wallet = session.get(Wallet, wallet_id)
                    s = WalletIngestor(session, provider).sync_wallet(
                        wallet, max_pages=ACTIVITY_PAGES
                    )
                if index % 5 == 0 or index == len(addresses):
                    print(f"{elapsed()}   {index}/{len(addresses)} wallets synced")
            except Exception as exc:  # noqa: BLE001
                print(f"{elapsed()}   ! {address[:12]} failed: {exc}")

        with session_scope() as session:
            tennis_tx = session.scalar(
                select(NormalizedTransaction)
                .where(NormalizedTransaction.is_tennis.is_(True))
                .limit(1)
            )
            total_tx = session.query(NormalizedTransaction).count()
            tennis_count = (
                session.query(NormalizedTransaction)
                .filter(NormalizedTransaction.is_tennis.is_(True))
                .count()
            )
        print(f"{elapsed()} {total_tx} transactions stored, {tennis_count} tennis")
        if not tennis_tx:
            print("No tennis activity found. Nothing to score.")
            return 1

        # ----------------------------------------------- first reconstruction
        print(f"{elapsed()} Reconstructing positions...")
        with session_scope() as session:
            from app.services.pipeline import AnalyticsPipeline

            pipeline = AnalyticsPipeline(session)
            for wallet in session.scalars(select(Wallet)):
                pipeline.reconstruct_wallet(wallet)

        # --------------------------------------------------- price evidence
        print(f"{elapsed()} Backfilling price evidence (the slow part)...")
        with session_scope() as session:
            from app.services.ingest import backfill_price_evidence

            stats = backfill_price_evidence(
                session, provider, max_markets=BACKFILL_MARKETS, window_days=45
            )
            print(f"{elapsed()}   {stats.inserted} price observations stored")
    finally:
        provider.close()

    # ------------------------------------------------------------ analytics
    print(f"{elapsed()} Computing metrics, scores and clusters...")
    with session_scope() as session:
        from app.services.pipeline import AnalyticsPipeline

        pipeline = AnalyticsPipeline(session)
        stats = pipeline.run_full()
        print(
            f"{elapsed()}   {stats.positions_written} positions, "
            f"{stats.copyability_rows} copyability rows, {stats.scores_written} scored"
        )

    # -------------------------------------------------------------- report
    with session_scope() as session:
        rows = session.execute(
            select(
                Wallet.address,
                WalletScore.skill_score,
                WalletScore.qualified,
                WalletScore.confidence_level,
                WalletMetrics.completed_positions,
                WalletMetrics.roi,
                WalletMetrics.copyable_roi,
                WalletMetrics.copyable_coverage,
                WalletMetrics.prob_positive_edge,
                WalletMetrics.max_drawdown,
                WalletMetrics.performance_by_period,
            )
            .join(WalletScore, WalletScore.wallet_id == Wallet.id)
            .outerjoin(
                WalletMetrics,
                (WalletMetrics.wallet_id == Wallet.id) & (WalletMetrics.scope == "tennis"),
            )
            .where(WalletScore.scope == "tennis")
            .order_by(WalletScore.skill_score.desc())
        ).all()

        print("\n" + "=" * 100)
        print("REAL POLYMARKET WALLETS -- tennis")
        print("=" * 100)
        print(
            f"{'address':<16}{'score':>7}{'qual':>6}{'n':>5}{'raw ROI':>10}"
            f"{'copy ROI':>10}{'cover':>8}{'P(edge)':>9}{'maxDD':>8}  confidence"
        )
        for (
            address, score, qualified, confidence, n, roi, copy_roi, coverage,
            p_edge, dd, _periods,
        ) in rows:
            print(
                f"{address[:14]:<16}{score:>7.1f}{str(bool(qualified)):>6}{(n or 0):>5}"
                f"{_pct(roi):>10}{_pct(copy_roi):>10}{_pct(coverage):>8}"
                f"{_pct(p_edge):>9}{_pct(dd):>8}  {confidence}"
            )

        qualified_rows = [r for r in rows if r[2]]
        scored = [r for r in rows if (r[4] or 0) >= 20]
        with_copyable = [r for r in rows if r[6] is not None]

        print("\n" + "-" * 100)
        print(f"wallets scored                      : {len(rows)}")
        print(f"with 20+ completed tennis trades    : {len(scored)}")
        print(f"with a measurable copyable ROI      : {len(with_copyable)}")
        print(f"passing every alert gate (qualified): {len(qualified_rows)}")

        if not qualified_rows:
            print(
                "\nNo wallet cleared every gate. That is a finding, not a failure:\n"
                "it means none of the wallets sampled showed a large enough,\n"
                "well-evidenced, delay-surviving edge to justify following."
            )
        else:
            print("\nQualified wallets (treat as candidates to watch, not to trust):")
            for r in qualified_rows:
                print(f"  {r[0]}  score {r[1]:.1f}  n={r[4]}  copyable ROI {_pct(r[6])}")

    print(f"\n{elapsed()} done")
    return 0


def _pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
