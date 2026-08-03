"""Measure edge the right way: realised win rate versus the price paid.

The earlier "remove the top 5% of trades" test was wrong for convex strategies.
A wallet buying longshots at $0.35 *makes its money* on rare large winners, so
deleting them destroys the mechanism rather than exposing luck. That test cannot
distinguish "got lucky" from "designed around asymmetric payoffs".

The price-implied test works at any entry price. A market price is a probability:
pay $0.35 and you need to win 35% of the time to break even. Beat that
consistently and you have an edge, however lumpy the returns look.

For each wallet this reports:

* implied breakeven win rate  = capital-weighted mean entry price
* realised win rate
* edge (percentage points)    = realised - implied
* a binomial p-value          = probability of a record this good by chance
* split-half stability        = does the edge hold in both halves of the record

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/edge_analysis.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import session_scope  # noqa: E402
from app.models import ReconstructedPosition as RP, Wallet  # noqa: E402

MIN_TRADES = 30


def binomial_tail(wins: int, n: int, p: float) -> float:
    """P(X >= wins) under Binomial(n, p) -- the luck hypothesis.

    Small values mean the record is hard to explain by chance alone. This is a
    one-sided test and makes no multiple-comparison correction; with many wallets
    screened, see the note printed at the end.
    """
    if n == 0:
        return 1.0
    p = min(max(p, 1e-9), 1 - 1e-9)
    total = 0.0
    for k in range(wins, n + 1):
        total += math.comb(n, k) * (p**k) * ((1 - p) ** (n - k))
    return min(1.0, total)


def analyse(rows) -> dict | None:
    """rows: (entry_price, is_win, capital, net_pnl, opened_ts)"""
    usable = [r for r in rows if r[1] is not None and r[0] is not None]
    if len(usable) < MIN_TRADES:
        return None

    n = len(usable)
    wins = sum(1 for r in usable if r[1])

    # Capital-weighted implied probability: a big bet at $0.9 should dominate a
    # tiny bet at $0.1 when asking "what did this wallet pay on average".
    total_cap = sum(float(r[2] or 0) for r in usable) or 1.0
    implied = sum(float(r[0]) * float(r[2] or 0) for r in usable) / total_cap
    # Unweighted too, since the binomial test treats every trade equally.
    implied_flat = sum(float(r[0]) for r in usable) / n

    realised = wins / n
    edge = realised - implied_flat
    p_value = binomial_tail(wins, n, implied_flat)

    # Split-half: does the edge appear in both halves of the record?
    ordered = sorted(usable, key=lambda r: r[4])
    mid = len(ordered) // 2
    halves = []
    for half in (ordered[:mid], ordered[mid:]):
        if not half:
            halves.append(None)
            continue
        hw = sum(1 for r in half if r[1])
        hi = sum(float(r[0]) for r in half) / len(half)
        halves.append(hw / len(half) - hi)

    pnl = sum(float(r[3] or 0) for r in usable)
    return {
        "n": n,
        "wins": wins,
        "implied": implied,
        "implied_flat": implied_flat,
        "realised": realised,
        "edge": edge,
        "p_value": p_value,
        "first_half_edge": halves[0],
        "second_half_edge": halves[1],
        "pnl": pnl,
        "capital": total_cap,
        "roi": pnl / total_cap if total_cap else 0.0,
    }


def main() -> int:
    with session_scope() as session:
        results = []
        for wallet in session.scalars(select(Wallet)):
            rows = session.execute(
                select(RP.avg_entry_price, RP.is_win, RP.capital_committed,
                       RP.net_pnl, RP.opened_ts)
                .where(
                    RP.wallet_id == wallet.id,
                    RP.is_tennis.is_(True),
                    RP.status.in_(("closed", "settled")),
                )
            ).all()
            stats = analyse(rows)
            if stats:
                stats["address"] = wallet.address
                results.append(stats)

    if not results:
        print(f"No wallet has {MIN_TRADES}+ completed tennis positions.")
        return 1

    results.sort(key=lambda r: r["p_value"])

    print("=" * 116)
    print("EDGE vs THE PRICE THEY PAID  (does the win rate beat the implied probability?)")
    print("=" * 116)
    print(
        f"{'wallet':<16}{'n':>5}{'implied':>9}{'realised':>10}{'edge':>8}"
        f"{'p(luck)':>10}{'1st half':>10}{'2nd half':>10}{'ROI':>9}{'P&L':>12}"
    )
    for r in results:
        h1 = "n/a" if r["first_half_edge"] is None else f"{r['first_half_edge']*100:+.1f}pp"
        h2 = "n/a" if r["second_half_edge"] is None else f"{r['second_half_edge']*100:+.1f}pp"
        print(
            f"{r['address'][:14]:<16}{r['n']:>5}{r['implied_flat']*100:>8.1f}%"
            f"{r['realised']*100:>9.1f}%{r['edge']*100:>+7.1f}pp{r['p_value']:>10.4f}"
            f"{h1:>10}{h2:>10}{r['roi']*100:>8.1f}%{r['pnl']:>12,.0f}"
        )

    significant = [r for r in results if r["p_value"] < 0.05]
    consistent = [
        r
        for r in significant
        if r["first_half_edge"] is not None
        and r["second_half_edge"] is not None
        and r["first_half_edge"] > 0
        and r["second_half_edge"] > 0
    ]

    print()
    print(f"wallets with {MIN_TRADES}+ completed tennis trades : {len(results)}")
    print(f"beating their implied price at p < 0.05    : {len(significant)}")
    print(f"...and positive in BOTH halves of record   : {len(consistent)}")
    if consistent:
        print()
        print("Consistent edge candidates:")
        for r in consistent:
            print(
                f"  {r['address']}  n={r['n']}  edge {r['edge']*100:+.1f}pp  "
                f"p={r['p_value']:.4f}  halves {r['first_half_edge']*100:+.1f}/"
                f"{r['second_half_edge']*100:+.1f}pp"
            )

    print()
    print("CAVEAT: these p-values are uncorrected. Screening N wallets means")
    print(f"roughly {len(results) * 0.05:.0f} would clear p<0.05 by chance alone.")
    print("The split-half check is the guard against that -- luck rarely repeats")
    print("in both halves of a record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
