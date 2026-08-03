"""Does the price move in a wallet's favour right after it buys?

Every other test in this project scores bets held to resolution. That makes a
profitable short-term trader invisible: buy at 0.40, sell at 0.48 twenty minutes
later, and if the player then loses the resolution-based test records a loss on a
trade that actually made money. The best-behaved wallet found so far holds
everything to settlement, so the blind spot was easy to miss -- but a scalper is
exactly as copyable as a holder, arguably more so, since the follower is not
locked up until the match ends.

This measures informed flow instead of outcomes. For every buy, it looks at what
the same side of the same match traded at over the following window, and reports
the average move. A wallet whose buys are consistently followed by the price
rising is getting in before the market does -- which is the thing worth copying,
whatever it does with the position afterwards.

Read it as a signal, not a P&L: the follower has to pay the spread and cannot
always exit at the observed price. A wallet must beat a comfortable margin here
before it means anything, and the comparison is against the market-wide average
move over the same window, not against zero -- tennis prices drift, and drift is
not skill.

Usage:
    python scripts/follow_through.py
    python scripts/follow_through.py --window-minutes 30 --min-calls 100
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

DEFAULT_STORE = REPO_ROOT / "data" / "tape_scan.db"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", type=Path, default=DEFAULT_STORE)
    p.add_argument("--window-minutes", type=float, default=15.0)
    p.add_argument("--min-calls", type=int, default=50)
    p.add_argument("--delay-seconds", type=float, default=15.0,
                   help="follower delay; 0 measures from the wallet's own fill")
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args()

    if not args.store.exists():
        print(f"No sweep data at {args.store}.")
        return 1

    window = int(args.window_minutes * 60)
    conn = sqlite3.connect(args.store)

    print("Loading tape...", flush=True)
    rows = conn.execute(
        "SELECT wallet, condition_id, won, ts, price FROM tape_bets"
    ).fetchall()
    if not rows:
        print("No bets recorded.")
        return 1

    wallets = np.array([r[0] for r in rows], dtype=object)
    # (market, side) identifies a price series: within a match, the winning and
    # losing outcome are the two tradable tokens.
    series_key = np.array([f"{r[1]}|{r[2]}" for r in rows], dtype=object)
    ts = np.asarray([r[3] for r in rows], dtype=np.int64)
    price = np.asarray([r[4] for r in rows], dtype=np.float64)

    print(f"{len(rows):,} trades across {len(set(series_key)):,} price series", flush=True)

    def window_sums(
        group_keys: np.ndarray, lo_off: int, hi_off: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Sum and count of prices in (t+lo_off, t+hi_off] within each group.

        Returned in ORIGINAL row order so two groupings can be combined.
        """
        order = np.lexsort((ts, group_keys))
        g, t_s, p_s = group_keys[order], ts[order], price[order]
        sums = np.zeros(len(rows))
        counts = np.zeros(len(rows), dtype=np.int64)
        changes = np.flatnonzero(g[1:] != g[:-1]) + 1
        for s, e in zip(np.concatenate([[0], changes]), np.concatenate([changes, [len(rows)]])):
            seg_ts, seg_px = t_s[s:e], p_s[s:e]
            csum = np.concatenate([[0.0], np.cumsum(seg_px)])
            lo = np.searchsorted(seg_ts, seg_ts + lo_off, side="right")
            hi = np.searchsorted(seg_ts, seg_ts + hi_off, side="right")
            sums[order[s:e]] = csum[hi] - csum[lo]
            counts[order[s:e]] = hi - lo
        return sums, counts

    # A wallet's OWN later buys must not count as the price moving for it. With
    # 32,000 trades, a heavy participant simply *is* the later price in every
    # match it touches, and would score as clairvoyant by measuring itself.
    own_key = np.array([f"{k}|{w}" for k, w in zip(series_key, wallets)], dtype=object)

    def excl_mean(lo_off: int, hi_off: int) -> np.ndarray:
        s_all, c_all = window_sums(series_key, lo_off, hi_off)
        s_own, c_own = window_sums(own_key, lo_off, hi_off)
        c, s = c_all - c_own, s_all - s_own
        out = np.full(len(rows), np.nan)
        good = c > 0
        out[good] = s[good] / c[good]
        return out

    delay = int(args.delay_seconds)
    if delay > 0:
        # The copyable portion only. If the wallet is merely FAST -- in-play, a
        # break of serve, a second ahead of the tape -- the move is complete
        # before a follower can act, and measuring from the wallet's own fill
        # credits the follower with a gain it could never take. So the entry is
        # what the market traded at AFTER the delay, and only what happens from
        # there belongs to the copier.
        print(f"Measuring the copier's portion ({delay}s behind)...", flush=True)
        entry = excl_mean(0, delay)
        later = excl_mean(delay, window)
    else:
        print("Measuring follow-through from the wallet's own fill...", flush=True)
        entry = price.copy()
        later = excl_mean(0, window)

    moves = later - entry
    ok = ~np.isnan(moves)
    baseline = float(moves[ok].mean())
    print(
        f"{ok.sum():,} trades have a later print within {args.window_minutes:g} min. "
        f"Market-wide average move: {baseline*100:+.3f}c"
    )
    print("(that drift is the benchmark -- beating zero is not skill)\n")

    # ONE MATCH = ONE OBSERVATION, again. Twenty trades by one wallet inside one
    # match all watch the same subsequent price move: they are one observation,
    # not twenty. Treating them as independent produced t-statistics of 90 and
    # 408 -- numbers no financial signal ever legitimately reaches, and the
    # giveaway that the sample size was fictional.
    per_match: dict[tuple[str, str], list[float]] = {}
    for w, k, m, good in zip(wallets, series_key, moves, ok):
        if good:
            per_match.setdefault((w, k.split("|")[0]), []).append(m)

    by_wallet: dict[str, list[float]] = {}
    for (wallet, _market), vals in per_match.items():
        by_wallet.setdefault(wallet, []).append(float(np.mean(vals)))

    table = []
    for wallet, vals in by_wallet.items():
        if len(vals) < args.min_calls:
            continue
        arr = np.asarray(vals)
        n = arr.size
        mean = float(arr.mean())
        sd = float(arr.std(ddof=1)) if n > 1 else 0.0
        # t-statistic against the market drift, not against zero.
        t = (mean - baseline) / (sd / np.sqrt(n)) if sd > 0 else 0.0
        table.append({"wallet": wallet, "n": n, "mean": mean,
                      "excess": mean - baseline, "t": t})

    if not table:
        print("No wallet has enough trades with a later print.")
        return 1

    table.sort(key=lambda r: r["t"], reverse=True)
    print(f"{len(table):,} wallets with {args.min_calls}+ measurable trades\n")
    print(f"{'#':<5}{'wallet':<16}{'trades':>8}{'move':>10}{'vs market':>12}{'t-stat':>9}")
    print("-" * 62)
    for i, r in enumerate(table[: args.top], start=1):
        print(
            f"{i:<5}{r['wallet'][:14]:<16}{r['n']:>8}{r['mean']*100:>+9.2f}c"
            f"{r['excess']*100:>+11.2f}c{r['t']:>9.2f}"
        )

    # With this many wallets, |t| > 3 happens by chance. Report the count against
    # the number expected so the reader is not invited to over-read the top row.
    n_tests = len(table)
    for thresh in (3.0, 4.0, 5.0):
        obs = sum(1 for r in table if r["t"] > thresh)
        # One-sided normal tail.
        from math import erfc, sqrt

        exp = n_tests * 0.5 * erfc(thresh / sqrt(2))
        print(
            f"\nt > {thresh:.0f}: {obs} observed, {exp:.2f} expected by chance"
            + ("  <- excess" if obs > 3 * max(exp, 0.01) else "")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
