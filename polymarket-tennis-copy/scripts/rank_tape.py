"""Rank every wallet found by the tape sweep, cheapest filter first.

Deliberately few gates. Every extra knob is another chance to tune the screen
until it flatters somebody, and that failure mode has already bitten this project
twice. Each gate below earns its place; everything else is *displayed* so it can
be judged by eye rather than silently filtered.

The funnel, in this order:

1. **Enough calls.** One match = one call, however many times the wallet traded
   it. This is the noise killer and it costs nothing, so it goes first.
2. **Win percentage** -- win rate minus the average price paid. Backing 50c
   chances and winning 80% of the time is +30 points; backing 96c favourites and
   winning 97% is +1. This measure handles the favourite-buyers on its own.
3. **Still playing** -- bet recently, and across several recent weeks rather than
   in one burst.
4. **Backs one player, not both.** Holding both sides is a spread: profitable,
   very possibly the bulk of who makes money here, and *uncopyable*, because a
   follower taking one leg carries precisely the risk the other leg cancelled.
5. **Holds up across its own record.** Split each wallet's calls in half by time;
   both halves must be positive. One hot streak followed by mediocrity is the
   single most common way a screened wallet fools you, and it is nearly free to
   check.

The luck bar is printed throughout: search enough wallets and someone looks
brilliant by accident, so a number only counts once it clears what chance alone
produces across a field this size.

Usage:
    python scripts/rank_tape.py
    python scripts/rank_tape.py --min-calls 200 --top 50 --no-gates
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.split_sample import binomial_tail, copier_edge, luck_bar  # noqa: E402
from app.services.statistics import active_periods  # noqa: E402

DEFAULT_STORE = REPO_ROOT / "data" / "tape_scan.db"
DAY = 86_400


def build_calls(conn: sqlite3.Connection) -> None:
    """Fold raw trades into one call per (wallet, match, side).

    Scaling into a single match across 70 trades is one judgement, right or
    wrong, not 70. Counting trades instead produced a leaderboard topped by a
    wallet showing "98% over 57 bets" that had in fact backed one player in two
    matches. The price is stake-weighted, which is what the wallet actually paid.
    """
    conn.executescript(
        """
        DROP TABLE IF EXISTS temp_calls;
        CREATE TEMP TABLE temp_calls AS
        SELECT wallet, condition_id, won,
               CASE WHEN SUM(size) > 0 THEN SUM(size * price) / SUM(size)
                    ELSE AVG(price) END AS price,
               SUM(size * price)        AS staked,
               MAX(ts)                  AS ts,
               COUNT(*)                 AS trades
        FROM tape_bets
        GROUP BY wallet, condition_id, won;
        CREATE INDEX ix_temp_calls_wallet ON temp_calls(wallet);
        """
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", type=Path, default=DEFAULT_STORE)
    p.add_argument("--min-calls", type=int, default=100)
    p.add_argument("--top", type=int, default=100)
    p.add_argument("--max-quiet-days", type=float, default=7.0)
    p.add_argument("--min-active-weeks", type=int, default=4)
    p.add_argument("--max-both-sides", type=float, default=0.35)
    p.add_argument("--max-avg-price", type=float, default=0.85)
    p.add_argument("--no-gates", action="store_true",
                   help="rank on calls + win%% only, skip the rest")
    p.add_argument("--csv", type=Path)
    args = p.parse_args()

    if not args.store.exists():
        print(f"No sweep data at {args.store}. Run scripts/sweep_tennis_tape.py first.")
        return 1

    conn = sqlite3.connect(args.store)
    scanned = conn.execute("SELECT COUNT(*) FROM scanned_markets").fetchone()[0]
    raw_trades = conn.execute("SELECT COUNT(*) FROM tape_bets").fetchone()[0]
    latest = conn.execute("SELECT MAX(ts) FROM tape_bets").fetchone()[0] or int(time.time())
    build_calls(conn)

    eligible = [
        r[0]
        for r in conn.execute(
            "SELECT wallet FROM temp_calls GROUP BY wallet HAVING COUNT(*) >= ?",
            (args.min_calls,),
        )
    ]
    total_wallets = conn.execute(
        "SELECT COUNT(DISTINCT wallet) FROM temp_calls"
    ).fetchone()[0]

    print("=" * 122)
    print("TENNIS WALLETS BY WINNING PERCENTAGE  (win rate minus the price they paid)")
    print("=" * 122)
    print(
        f"{scanned:,} matches swept | {raw_trades:,} trades -> one call per match | "
        f"{total_wallets:,} wallets seen | {len(eligible):,} with {args.min_calls}+ calls"
    )
    if not eligible:
        print("\nNobody has enough calls yet. The sweep may still be running.")
        return 1

    rows = []
    for wallet in eligible:
        calls = conn.execute(
            "SELECT ts, price, won, staked, condition_id FROM temp_calls "
            "WHERE wallet = ? ORDER BY ts",
            (wallet,),
        ).fetchall()
        n = len(calls)
        prices = [c[1] for c in calls]
        wins = [bool(c[2]) for c in calls]
        avg_price, realised, edge = copier_edge(wins, prices)

        # Both halves of the record, by time. A wallet carried by one hot spell
        # shows a strong total and a weak second half.
        mid = n // 2
        _, _, first_edge = copier_edge(wins[:mid], prices[:mid])
        _, _, second_edge = copier_edge(wins[mid:], prices[mid:])

        by_market: dict[str, int] = {}
        for c in calls:
            by_market[c[4]] = by_market.get(c[4], 0) + 1
        both_share = sum(1 for v in by_market.values() if v > 1) / len(by_market)

        rows.append({
            "wallet": wallet, "n": n, "avg_price": avg_price, "realised": realised,
            "edge": edge, "first_edge": first_edge, "second_edge": second_edge,
            "quiet": (latest - calls[-1][0]) / DAY,
            "active": active_periods([c[0] for c in calls], now_ts=latest),
            "both_share": both_share,
            "staked": sum(c[3] or 0 for c in calls),
            "p": binomial_tail(sum(wins), n, avg_price),
        })

    bar_all = luck_bar([r["n"] for r in rows])
    print(
        f"Luck bar across all {len(rows):,} eligible wallets: +{bar_all*100:.1f} points."
    )

    def gate(r) -> list[str]:
        f = []
        if r["edge"] <= 0:
            f.append("losing")
        if r["quiet"] > args.max_quiet_days:
            f.append(f"quiet {r['quiet']:.0f}d")
        if r["active"] < args.min_active_weeks:
            f.append(f"active {r['active']}/8w")
        if r["both_share"] > args.max_both_sides:
            f.append(f"both sides {r['both_share']*100:.0f}%")
        if r["avg_price"] > args.max_avg_price:
            f.append(f"favourites ${r['avg_price']:.2f}")
        if r["first_edge"] <= 0 or r["second_edge"] <= 0:
            f.append("fails half-split")
        return f

    survivors = rows if args.no_gates else [r for r in rows if not gate(r)]
    survivors.sort(key=lambda r: r["edge"], reverse=True)

    if not args.no_gates:
        print(
            f"After gates: {len(survivors):,} survive "
            f"(active <={args.max_quiet_days:g}d, >={args.min_active_weeks}/8 weeks, "
            f"both-sides <{args.max_both_sides:.0%}, avg price <${args.max_avg_price:.2f}, "
            f"both halves positive)"
        )
        # Where the field died, so the gates are visible rather than silent.
        reasons: dict[str, int] = {}
        for r in rows:
            for why in gate(r):
                key = why.split()[0] if why[0].islower() else why
                reasons[key] = reasons.get(key, 0) + 1
        if reasons:
            print("  cut by: " + ", ".join(
                f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])
            ))
    print()

    if not survivors:
        print("Nothing survives the gates.")
        return 2

    print(
        f"{'#':<5}{'wallet':<16}{'calls':>7}{'avg $':>8}{'win%':>8}{'WIN %':>9}"
        f"{'1st half':>10}{'2nd half':>10}{'p(luck)':>10}{'quiet':>7}{'both':>7}{'staked':>12}"
    )
    print("-" * 122)
    for i, r in enumerate(survivors[: args.top], start=1):
        star = "  **" if r["edge"] > bar_all else ""
        print(
            f"{i:<5}{r['wallet'][:14]:<16}{r['n']:>7}{r['avg_price']:>8.2f}"
            f"{r['realised']*100:>7.1f}%{r['edge']*100:>+8.1f}p"
            f"{r['first_edge']*100:>+9.1f}p{r['second_edge']*100:>+9.1f}p"
            f"{r['p']:>10.4f}{r['quiet']:>6.1f}d{r['both_share']*100:>6.0f}%"
            f"{r['staked']:>12,.0f}{star}"
        )

    beats = [r for r in survivors if r["edge"] > bar_all]
    print()
    print(f"Clearing the +{bar_all*100:.1f} luck bar: {len(beats)}")
    for r in beats[:10]:
        profit = (r["realised"] / r["avg_price"] - 1) * 100 * r["n"]
        print(
            f"   {r['wallet']}  {r['n']} calls  {r['edge']*100:+.1f}p  "
            f"halves {r['first_edge']*100:+.1f}/{r['second_edge']*100:+.1f}  "
            f"$100/call -> ${profit:+,.0f}"
        )
    if not beats:
        print("   (none -- nobody is yet distinguishable from the luckiest fluke)")

    if args.csv:
        import csv as _csv

        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["edge"], reverse=True))
        print(f"\nFull ranking -> {args.csv} ({len(rows):,} wallets)")

    print()
    print(
        "This is the price the WALLET paid, held to resolution -- a shortlist to "
        "deep-backfill, not a follow list. What a copier pays after delay is a "
        "different number and still has to be measured."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
