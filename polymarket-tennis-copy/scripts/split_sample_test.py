"""Does picking the best-looking wallet actually find edge?

The follow list was produced by screening a population and reporting the top of
it. That procedure returns a large number whether or not anyone in the
population has skill, because the maximum of many noisy records is high by
construction. This script tests the procedure rather than the wallet:

* rank every eligible wallet on the FIRST half of its record
* measure what following the winner from that point would actually have paid
* deal every trade out at random and re-run the whole screen, thousands of
  times, to see what the same procedure produces when nobody has an edge

The number that matters is ``p(out-of-sample)``. Beating zero is not evidence;
beating the null screen is.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/split_sample_test.py
    ... scripts/split_sample_test.py --metric raw --split time
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    ReconstructedPosition as RP,
    TradeCopyability as TC,
    Wallet,
)
from app.services.split_sample import (  # noqa: E402
    TradeRecord,
    build_splits,
    run_selection_test,
    winsorize,
)

# The current headline candidate, called out separately in the report.
FOCUS_WALLET = "0x4be1fa92e6ceaf886aac0bbec3be6c527133aa70"

COMPLETE = ("closed", "settled")


def load_copyable(session, delay: int, confidence_floor: float) -> list[TradeRecord]:
    """Delay-adjusted follower returns -- what a copier would have realised.

    Rows below the confidence floor are excluded for the same reason
    ``metrics.py`` excludes them: a modelled fill price averaged into a return
    fabricates edge rather than measuring it.
    """
    rows = session.execute(
        select(Wallet.address, RP.opened_ts, TC.follower_roi)
        .join(RP, RP.wallet_id == Wallet.id)
        .join(TC, TC.position_id == RP.id)
        .where(
            TC.delay_seconds == delay,
            TC.follower_roi.is_not(None),
            TC.data_confidence >= confidence_floor,
            RP.is_tennis.is_(True),
            RP.status.in_(COMPLETE),
        )
    ).all()
    return [TradeRecord(addr, ts, float(roi)) for addr, ts, roi in rows]


def load_raw(session) -> list[TradeRecord]:
    """The wallet's own per-trade return, equal-weighted.

    Equal-weighted deliberately: a follower stakes flat per signal, so the
    capital-weighted ``roi`` column is not the comparable quantity.
    """
    rows = session.execute(
        select(Wallet.address, RP.opened_ts, RP.net_pnl, RP.capital_committed)
        .join(RP, RP.wallet_id == Wallet.id)
        .where(
            RP.is_tennis.is_(True),
            RP.status.in_(COMPLETE),
            RP.net_pnl.is_not(None),
            RP.capital_committed > 0,
        )
    ).all()
    return [
        TradeRecord(addr, ts, float(pnl) / float(cap)) for addr, ts, pnl, cap in rows
    ]


def money(roi: float) -> str:
    """Per-trade ROI as the profit on a flat $100 stake."""
    return f"{roi * 100:+,.2f}"


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metric",
        choices=("copyable", "raw"),
        default="copyable",
        help="copyable = delay-adjusted follower return (default); raw = the wallet's own",
    )
    parser.add_argument("--delay", type=int, default=settings.benchmark_delay_seconds)
    parser.add_argument("--split", choices=("count", "time"), default="count")
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--min-half", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument(
        "--winsorize",
        type=float,
        default=100.0,
        metavar="PCT",
        help="cap returns at this pooled percentile (e.g. 95); 100 = off",
    )
    args = parser.parse_args()

    with session_scope() as session:
        if args.metric == "copyable":
            records = load_copyable(
                session, args.delay, settings.min_copyable_data_confidence
            )
            label = f"copyable ROI @ {args.delay}s delay"
        else:
            records = load_raw(session)
            label = "raw per-trade ROI (equal-weighted)"

    if args.winsorize < 100.0:
        records = winsorize(records, pct=args.winsorize)
        label += f", winsorized at p{args.winsorize:g}"

    splits = build_splits(
        records,
        mode=args.split,
        min_trades=args.min_trades,
        min_half=args.min_half,
    )
    result = run_selection_test(splits, iterations=args.iterations)

    print("=" * 100)
    print(f"SPLIT-SAMPLE SELECTION TEST  --  {label}")
    print("=" * 100)
    print(
        f"{len(records):,} trades loaded | {len(splits)} wallets eligible "
        f"(>={args.min_trades} trades, >={args.min_half} per half) | split by {args.split}"
    )
    if not splits:
        print("\nNo wallet has enough trades on both sides of the split.")
        return 1
    print()

    print(
        f"{'wallet':<16}{'n(1st)':>8}{'n(2nd)':>8}{'1st half':>11}{'2nd half':>11}"
        f"{'2nd med':>10}{'decay':>10}"
    )
    print("-" * 100)
    for s in splits:
        marker = " <" if s.wallet == FOCUS_WALLET else ""
        print(
            f"{s.wallet[:14]:<16}{s.n_in:>8}{s.n_out:>8}"
            f"{s.in_mean * 100:>10.1f}%{s.out_mean * 100:>10.1f}%"
            f"{s.out_median * 100:>9.1f}%{s.decay * 100:>+9.1f}pp{marker}"
        )

    if result is None:
        print("\nOnly one wallet is eligible -- there is no selection to validate.")
        return 1

    print()
    print("=" * 100)
    print("IS THE WINNER REAL, OR IS IT THE MAXIMUM OF A NOISY SCREEN?")
    print("=" * 100)
    print(f"population mean per trade      : {result.pooled_mean * 100:+.2f}%")
    print(
        f"selected wallet (1st-half rank): {result.winner[:14]}  "
        f"n={result.winner_n_in}/{result.winner_n_out}"
    )
    print()
    print(
        f"  in-sample  (how it was picked): {result.winner_in_mean * 100:+7.2f}%   "
        f"random screen would give {result.null_max_in_mean * 100:+.2f}% "
        f"(95th pct {result.null_max_in_p95 * 100:+.2f}%)   p={result.p_value_in_sample:.4f}"
    )
    print(
        f"  out-of-sample (what it PAID)  : {result.winner_out_mean * 100:+7.2f}%   "
        f"random screen would give {result.null_winner_out_mean * 100:+.2f}%"
        f"                     p={result.p_value_out_sample:.4f}"
    )
    if result.selection_share is not None:
        print(
            f"\n  share of the in-sample edge explained by selection alone: "
            f"{result.selection_share * 100:.0f}%"
        )

    rho = result.rank_correlation
    print()
    if rho is None:
        print("rank correlation between halves : undefined (too few wallets)")
    else:
        p_rho = result.p_value_rank_correlation
        p_txt = f"p={p_rho:.4f}" if p_rho is not None else "p=n/a"
        print(
            f"rank correlation between halves : {rho:+.3f}  "
            f"(null {result.null_rank_correlation:+.3f}, {p_txt})"
        )
        print(
            "  Does a good first half predict a good second one across wallets?"
            f"  {'Yes.' if rho > 0.3 and (p_rho or 1) < 0.05 else 'Not detectably.'}"
        )

    print()
    print("-" * 100)
    print("VERDICT")
    print("-" * 100)
    stake = 100
    won = result.winner_out_mean * stake
    if result.survives:
        print(
            f"The winner beats the selection null out of sample (p={result.p_value_out_sample:.4f})."
        )
        print(
            f"Staking ${stake} on every one of its {result.winner_n_out} second-half trades "
            f"returns {money(result.winner_out_mean)} per trade "
            f"({won * result.winner_n_out:+,.0f} total)."
        )
        print("This is the one result that would justify forward testing with real money.")
    else:
        print(
            f"The winner does NOT beat the selection null out of sample "
            f"(p={result.p_value_out_sample:.4f})."
        )
        print(
            f"Its first-half {result.winner_in_mean * 100:+.1f}% is consistent with the "
            f"{result.null_max_in_mean * 100:+.1f}% that dealing the same trades at random"
        )
        print("produces, and it is the number the screen selected on.")
        print(
            f"Staking ${stake} on every one of its {result.winner_n_out} second-half trades "
            f"returns {money(result.winner_out_mean)} per trade "
            f"({won * result.winner_n_out:+,.0f} total)."
        )
        print("No real money on this until something clears the out-of-sample null.")

    print()
    print(
        f"Permutations: {result.iterations:,} | seed fixed, so this verdict is reproducible."
    )
    print(
        "Note: this validates the SCREEN over the wallets in this database. Wallets"
    )
    print(
        "discovered but never deep-backfilled are absent, so the true selection"
    )
    print("pressure is somewhat higher than the count above.")
    return 0 if result.survives else 2


if __name__ == "__main__":
    raise SystemExit(main())
