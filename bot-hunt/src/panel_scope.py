"""DIMENSION E, measured on the real pulled universe rather than on a weekly rate.

`market-selection` reported 40-101 settlements/week for these series from the
24h tape. That is a RATE. What a backtest can actually use is the number of
SETTLED EVENTS still listed inside Kalshi's retention window, and the unit of
observation is the MATCH, not the market.

LEDGER K014 is the bar this has to clear: **481 settlements** to detect a 5pp
edge at 80% power, **2,084** to clear a 2.4c cost bar. GUARDS #8 — row count is
not evidence count, and this is the failure mode responsible for more retracted
claims in this repo than any other.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "kalshi_soccer.db"
c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)

print("== markets per EVENT (an event is one match; a market is one outcome)")
for series, in c.execute("select distinct series from markets order by 1"):
    rows = c.execute(
        "select event_ticker, count(*), "
        " sum(case when result in ('yes','no') then 1 else 0 end), "
        " group_concat(distinct status) "
        "from markets where series=? group by event_ticker", (series,)).fetchall()
    per = Counter(r[1] for r in rows)
    settled_events = sum(1 for r in rows if r[2] and r[2] == r[1])
    print(f"  {series:22} events={len(rows):>4} settled_events={settled_events:>4} "
          f"markets/event={dict(per)}")

print("\n== settled EVENTS by week (unit of observation = the match)")
tot = 0
for series, in c.execute("select distinct series from markets order by 1"):
    rows = c.execute(
        "select event_ticker, min(close_time), count(*), "
        " sum(case when result in ('yes','no') then 1 else 0 end) "
        "from markets where series=? group by event_ticker", (series,)).fetchall()
    weeks = Counter()
    n_set = 0
    for ev, ct, n, ns in rows:
        if not ct or not ns or ns != n:
            continue
        n_set += 1
        weeks[ct[:7]] += 1
    tot += n_set
    span = f"{min(weeks) if weeks else '-'}..{max(weeks) if weeks else '-'}"
    print(f"  {series:22} settled_events={n_set:>4}  by month={dict(sorted(weeks.items()))}")
print(f"\n  TOTAL SETTLED EVENTS AVAILABLE = {tot}")
print(f"  LEDGER K014 bar: 481 for a 5pp edge, 2,084 to clear a 2.4c cost bar")
print(f"  -> {tot/481:.2f}x the 5pp bar, {tot/2084:.3f}x the cost bar")

print("\n== earliest close_time actually LISTED, per series")
for r in c.execute("select series, min(close_time), max(close_time), count(*) "
                   "from markets group by series"):
    print(f"  {r[0]:22} {str(r[1])[:19]} -> {str(r[2])[:19]}  n={r[3]}")

print("\n== a sample settled event, to see the market structure")
row = c.execute(
    "select event_ticker from markets where result in ('yes','no') "
    "and series='KXLIGAMXGAME' limit 1").fetchone()
if row:
    for r in c.execute(
            "select ticker, title, yes_sub_title, no_sub_title, result, "
            "status, volume, close_time from markets where event_ticker=?",
            (row[0],)):
        print(f"  {r[0]}")
        print(f"     title={r[1]!r}")
        print(f"     yes={r[2]!r} no={r[3]!r} result={r[4]} status={r[5]} "
              f"vol={r[6]} close={r[7]}")
c.close()
