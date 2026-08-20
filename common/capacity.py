"""capacity.py — what a Kalshi market family can actually absorb.

    py -3 common/capacity.py --series KXITFMATCH KXATPMATCH
    py -3 common/capacity.py --top 25

WHY THIS IS SHARED AND NOT IN ONE PROJECT
    `STRATEGY_FACTORY.md` stage 3 makes capacity a screening rule for every
    strategy the factory generates: *"what if I put $500 into this thin market
    — walk the book, report what it actually costs to fill"*, and stage 6 says
    *"a great edge in a market that takes $12 is a hobby."* That question is
    identical for tennis, baseball, crypto and weather, so it is answered once
    here rather than per project.

    The tennis chat wrote the first version inline while answering a question
    about ITF. Generalising it cost twenty minutes and removes the reason for
    anyone to write a second.

THE MEASUREMENT, AND WHY IT IS BUCKETED BY TIME
    A single median over a family's whole life is close to meaningless, and the
    tennis case shows why. Measured flat, `KXITFMATCH` looks untradeable: 10.1c
    mean spread, $47 at the touch. Bucketed by how long before that market
    stopped quoting, it splits into three different markets:

        KXITFMATCH   >12h out   19.9c   $13
                     2-12h       9.7c   $46
                     last 2h     5.6c  $123

    The flat number is an average over a book that barely exists and a book
    that does. **"ITF is untradeable" and "ITF is tradeable only in the last
    two hours, at about $123 a click" are different findings, and only the
    second one is true.**

    Compare KXATPMATCH over the same buckets: 3.8c/$1,002, 1.4c/$6,642,
    1.2c/$9,599. Roughly eighty times the size at a quarter of the spread.

WHAT IT DOES NOT DO
    It reports the money resting at the touch and across five levels, at the
    times we observed. It does NOT model what happens when you take it — a
    resting order is not a promise, and this repo has measured a fill rate
    nearer 30% on passive quoting. Treat these as a CEILING on capacity, never
    as a fill.
"""

from __future__ import annotations

import argparse
import sqlite3
import statistics as st
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO / "bot-hunt" / "data" / "record.db"

#: Hours-before-last-quote buckets. The names are what a human reads.
BUCKETS = (("last 2h", 0.0, 2.0), ("2-12h", 2.0, 12.0), ("over 12h", 12.0, 1e9))


@dataclass
class Slice:
    bucket: str
    n: int
    mean_spread_c: float
    median_touch_usd: float
    median_depth5_usd: float
    median_ask_size: float

    def line(self) -> str:
        return ("   %-9s n=%7d  spread %5.1fc  touch $%8.0f  5 levels $%9.0f"
                % (self.bucket, self.n, self.mean_spread_c,
                   self.median_touch_usd, self.median_depth5_usd))


def _hours(a: str, b: str) -> float:
    fa = datetime.fromisoformat(a.replace("Z", "+00:00"))
    fb = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return (fb - fa).total_seconds() / 3600.0


def measure(series: str, db: Path = DEFAULT_DB) -> list[Slice]:
    """Spread and money-at-touch for one family, bucketed by time to last quote.

    Read-only. Opens the recorder's database in read-only mode so a running
    recorder cannot be disturbed - that database is the one asset in this repo
    that accrues in wall-clock time and cannot be re-pulled.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = list(con.execute(
        "select ticker, ts_utc, yes_bid_c, yes_ask_c, ask_size, depth5_yes "
        "from k_book where series=? and status='active' "
        "  and yes_bid_c>0 and yes_ask_c>0 and yes_ask_c<100", (series,)))
    con.close()
    if not rows:
        return []

    last: dict[str, str] = {}
    for t, ts, *_ in rows:
        if t not in last or ts > last[t]:
            last[t] = ts

    packed: dict[str, list] = {b[0]: [] for b in BUCKETS}
    for t, ts, bid, ask, asz, d5 in rows:
        h = _hours(ts, last[t])
        for name, lo, hi in BUCKETS:
            if lo <= h < hi:
                packed[name].append((ask - bid, asz or 0, d5 or 0, ask))
                break

    out = []
    for name, _lo, _hi in BUCKETS:
        v = packed[name]
        if not v:
            continue
        out.append(Slice(
            bucket=name, n=len(v),
            mean_spread_c=st.mean(s for s, _, _, _ in v),
            median_touch_usd=st.median([(a * sz) / 100.0
                                        for _, sz, _, a in v] or [0]),
            median_depth5_usd=st.median([(a * d) / 100.0
                                         for _, _, d, a in v] or [0]),
            median_ask_size=st.median([sz for _, sz, _, _ in v] or [0]),
        ))
    return out


def verdict(slices: list[Slice], want_usd: float = 100.0,
            max_spread_c: float = 5.0) -> str:
    """Plain English, and it names the bucket rather than averaging over them."""
    if not slices:
        return "NO DATA - this family is not in the recorder"
    best = max(slices, key=lambda s: s.median_touch_usd)
    if best.median_touch_usd < want_usd:
        return (f"TOO THIN AT ANY TIME - the best bucket ({best.bucket}) shows "
                f"${best.median_touch_usd:,.0f} at the touch against the "
                f"${want_usd:,.0f} asked for")
    if best.mean_spread_c > max_spread_c:
        return (f"WIDE - ${best.median_touch_usd:,.0f} is there in {best.bucket} "
                f"but it costs {best.mean_spread_c:.1f}c of spread to reach")
    return (f"TRADEABLE IN {best.bucket.upper()} - ${best.median_touch_usd:,.0f} "
            f"at the touch, {best.mean_spread_c:.1f}c spread. Outside that "
            f"bucket it is a different market.")


def families(db: Path = DEFAULT_DB, limit: int = 25) -> list[tuple[str, int]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = list(con.execute(
        "select series, count(*) c from k_book group by series "
        "order by c desc limit ?", (limit,)))
    con.close()
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--series", nargs="*", help="families to measure")
    ap.add_argument("--top", type=int, help="measure the N most-recorded")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--want-usd", type=float, default=100.0)
    a = ap.parse_args()

    if not a.db.exists():
        print(f"no recorder database at {a.db}")
        return 2

    names = list(a.series or [])
    if a.top:
        names += [s for s, _ in families(a.db, a.top) if s not in names]
    if not names:
        print("nothing to measure. --series NAME... or --top N")
        for s, c in families(a.db, 15):
            print(f"   {s:22s} {c:9,d} rows")
        return 1

    for s in names:
        sl = measure(s, a.db)
        print(f"\n{s}")
        for x in sl:
            print(x.line())
        print("   -> " + verdict(sl, a.want_usd))
    print("\nMoney shown is what was RESTING at those prices, which is a "
          "ceiling on capacity and not a fill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
