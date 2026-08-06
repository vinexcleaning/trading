"""Prove the k_names write path works, against a SCRATCH db.

Does not touch data/record.db — the live recorder is mid-cycle and holding it.
Runs the real `kalshi_cycle` against a throwaway file with a single small
series, so a failure shows up here in two minutes instead of being inferred from
an empty table.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record as R  # noqa: E402

tmp = Path(tempfile.gettempdir()) / "bot_hunt_names_test.db"
if tmp.exists():
    tmp.unlink()
R.DB = tmp
con = R.connect()
con.execute("insert into cycles (started_utc) values (?)", (R.now(),))
con.commit()

R.KALSHI_SERIES = ["KXCS2GAME"]          # one series is enough to prove it
R.kalshi_cycle(con, 1)

n = con.execute("select count(1) from k_names").fetchone()[0]
named = con.execute("select count(1) from k_names where yes_sub_title is not "
                    "null and yes_sub_title <> ''").fetchone()[0]
print(f"k_names rows: {n}   with a full outcome name: {named}")
for tk, sub in con.execute("select ticker, yes_sub_title from k_names "
                           "where yes_sub_title is not null limit 5"):
    print(f"   {tk.rsplit('-',1)[-1]:<12} -> {sub!r}")
kb = con.execute("select count(1) from k_book").fetchone()[0]
print(f"k_book rows: {kb}")
con.close()
print("\nPASS — the write path works" if named > 0 else
      "\nFAIL — names are not being written")
