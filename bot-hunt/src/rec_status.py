"""Content-level health readout for the recorder (GUARDS #12).

Row counts were right in BOTH of this project's silent-recorder incidents, so
this reports non-empty fractions, two-sided fractions and staleness — never a
bare row count.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "record.db"
con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=60)

print("== cycles")
for r in con.execute("select cycle_id, started_utc, finished_utc, seconds, "
                     "substr(coalesce(note,''),1,90) from cycles "
                     "order by cycle_id desc limit 8"):
    print(f"  {r[0]:>4} {r[1]} -> {r[2]}  {r[3]}s  {r[4]}")

last = con.execute("select max(cycle_id) from cycles").fetchone()[0]
print(f"\n== health, cycle {last}")
print(f"  {'source':28} {'listed':>7} {'ok':>6} {'rows':>7} {'2sided':>7} {'2s%':>6}")
for r in con.execute(
        "select source, n_attempted, n_ok, n_nonempty, n_two_sided from health "
        "where cycle_id=? order by source", (last,)):
    src, att, ok, ne, two = r
    pct = f"{100*two/ne:.0f}%" if (two is not None and ne) else "-"
    print(f"  {src:28} {str(att):>7} {str(ok):>6} {str(ne):>7} "
          f"{str(two):>7} {pct:>6}")

print("\n== table totals")
for t in ("pin_matchup", "pin_market", "k_book", "p_book"):
    n = con.execute(f"select count(*) from {t}").fetchone()[0]
    d = con.execute(f"select count(distinct cycle_id) from {t}").fetchone()[0]
    print(f"  {t:14} rows={n:>9}  cycles={d}")

print("\n== Kalshi two-sided uptime by series (all cycles)")
for r in con.execute(
        "select series, count(*) n, "
        " sum(case when yes_bid_c is not null and yes_ask_c is not null "
        "     then 1 else 0 end) two, "
        " count(distinct ticker) tk from k_book group by series order by n desc"):
    s, n, two, tk = r
    print(f"  {s:22} n={n:>6} tickers={tk:>4} two-sided={100*two/n:>5.1f}%")

print("\n== Polymarket by tag (all cycles)")
for r in con.execute(
        "select tag, count(*) n, "
        " sum(case when bid_c is not null and ask_c is not null then 1 else 0 end) two,"
        " count(distinct token_id) tk from p_book group by tag order by n desc"):
    t, n, two, tk = r
    print(f"  {t:22} n={n:>6} tokens={tk:>4} two-sided={100*two/n:>5.1f}%")

print("\n== Pinnacle priced records by sport (all cycles)")
for r in con.execute(
        "select sport, count(*) n, count(distinct matchup_id) mu, "
        " sum(case when price_american is not null then 1 else 0 end) priced "
        "from pin_market group by sport order by n desc"):
    print(f"  {r[0]:22} rows={r[1]:>7} matchups={r[2]:>5} priced={r[3]:>7}")
con.close()
