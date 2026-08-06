"""Did the k_names fix actually work? Verified, not assumed.

The fix exists because the cross-venue join failed: matching Pinnacle to Kalshi
on the TICKER matched 3 of 218 events, since Kalshi's outcome codes are 2-4
letter abbreviations while every other venue uses full team names. The names
live in `yes_sub_title` and nothing was storing them.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "record.db"
c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=180)

n = c.execute("select count(1) from k_names").fetchone()[0]
named = c.execute("select count(1) from k_names "
                  "where yes_sub_title is not null and yes_sub_title <> ''"
                  ).fetchone()[0]
print(f"k_names rows: {n}   with a full outcome name: {named}")

for r in c.execute("select series, count(1) from k_names group by series "
                   "order by 2 desc limit 8"):
    print(f"   {r[0]:22} {r[1]:>6}")

print("\nsample — the abbreviation problem, and the fix, side by side:")
for tk, sub, title in c.execute(
        "select ticker, yes_sub_title, title from k_names "
        "where yes_sub_title is not null and series like 'KX%GAME' limit 6"):
    code = tk.rsplit("-", 1)[-1]
    print(f"   ticker code {code:<10} -> {sub!r}")

cy = c.execute("select cycle_id, started_utc, finished_utc, seconds, "
               "substr(coalesce(note,''),1,200) from cycles "
               "order by cycle_id desc limit 3").fetchall()
print("\nrecent cycles:")
for r in cy:
    print(f"   {r[0]} {r[1]} -> {r[2]} {r[3]}s {r[4]}")
c.close()
