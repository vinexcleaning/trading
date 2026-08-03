"""Top wallets by winning percentage, plainly.

Winning percentage here is the user's definition, which is the right one: if a
wallet backs 50c chances and wins 80% of the time, that is +30 points. Betting
50c chances and winning 50% of the time is zero, however busy it looks.

The price used is what a FOLLOWER pays after the copy delay, not what the wallet
itself paid, so the number is the copier's to keep.

A minimum trade count applies because an unfiltered ranking is meaningless -- a
wallet with one lucky bet shows +62 points and tops any list. Lower it with
--min-trades to see for yourself.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/leaderboard.py
    ... scripts/leaderboard.py --min-trades 100 --top 20
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
from app.services.split_sample import binomial_tail, copier_edge, luck_bar  # noqa: E402

DAY = 86_400


def main() -> int:
    settings = get_settings()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--delay", type=int, default=15)
    p.add_argument("--min-trades", type=int, default=20)
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args()

    with session_scope() as session:
        rows = session.execute(
            select(
                Wallet.address,
                TC.follower_is_win,
                TC.estimated_fill_price,
                RP.opened_ts,
                RP.held_both_outcomes,
            )
            .join(RP, RP.wallet_id == Wallet.id)
            .join(TC, TC.position_id == RP.id)
            .where(
                TC.delay_seconds == args.delay,
                TC.follower_is_win.is_not(None),
                TC.estimated_fill_price.is_not(None),
                TC.data_confidence >= settings.min_copyable_data_confidence,
                RP.is_tennis.is_(True),
                RP.status.in_(("closed", "settled")),
            )
        ).all()

    if not rows:
        print("No measured tennis trades in this database.")
        return 1

    latest = max(r[3] for r in rows)
    by_wallet: dict[str, list] = {}
    for r in rows:
        by_wallet.setdefault(r[0], []).append(r)

    table = []
    for address, rs in by_wallet.items():
        implied, realised, edge = copier_edge(
            [bool(r[1]) for r in rs], [float(r[2]) for r in rs]
        )
        wins = sum(1 for r in rs if r[1])
        table.append({
            "address": address,
            "n": len(rs),
            "implied": implied,
            "realised": realised,
            "edge": edge,
            "p": binomial_tail(wins, len(rs), implied),
            "quiet": (latest - max(r[3] for r in rs)) / DAY,
            "both": sum(1 for r in rs if r[4]) / len(rs),
        })

    eligible = sorted(
        (t for t in table if t["n"] >= args.min_trades),
        key=lambda t: t["edge"],
        reverse=True,
    )

    print("=" * 104)
    print(
        f"TOP {args.top} WALLETS BY WINNING PERCENTAGE  "
        f"(win rate minus the price a copier pays, {args.delay}s delay)"
    )
    print("=" * 104)
    print(f"{len(eligible)} wallets have {args.min_trades}+ measured tennis bets.\n")
    print(
        f"{'#':<4}{'wallet':<16}{'bets':>7}{'avg price':>11}{'win rate':>10}"
        f"{'WIN %':>9}{'p(luck)':>10}{'quiet':>8}{'both sides':>12}"
    )
    print("-" * 104)
    for i, t in enumerate(eligible[: args.top], start=1):
        flag = "  <- hedger" if t["both"] > 0.5 else ""
        print(
            f"{i:<4}{t['address'][:14]:<16}{t['n']:>7}${t['implied']:>10.2f}"
            f"{t['realised']*100:>9.1f}%{t['edge']*100:>+8.1f}p{t['p']:>10.4f}"
            f"{t['quiet']:>7.1f}d{t['both']*100:>11.0f}%{flag}"
        )

    if eligible:
        bar = luck_bar([t["n"] for t in eligible])
        best = eligible[0]
        print()
        print(
            f"Luck bar for {len(eligible)} wallets this size: "
            f"+{bar*100:.1f} points. Top wallet is {best['edge']*100:+.1f}."
        )
        stake = 100
        profit = (best["realised"] / best["implied"] - 1) * stake * best["n"]
        print(
            f"${stake} on each of {best['address'][:14]}'s {best['n']} bets: "
            f"${profit:+,.0f}."
        )

    # Show what dropping the floor does, so the floor is visibly earned.
    junk = sorted(
        (t for t in table if t["n"] < args.min_trades),
        key=lambda t: t["edge"],
        reverse=True,
    )[:3]
    if junk:
        print()
        print("For contrast, the best wallets below the trade minimum:")
        for t in junk:
            print(
                f"   {t['address'][:14]}  {t['n']:>3} bets  {t['edge']*100:+.1f}p  "
                f"-- too few bets to mean anything"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
