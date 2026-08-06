"""Prove the both-tokens write path works, against a SCRATCH db.

The live table cannot answer yet — cycles run ~14 min and Polymarket is the last
stage — and "the table is empty" would wrongly read as "the edit is broken".
That inference was already wrong once today for `k_names`.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record as R  # noqa: E402

tmp = Path(tempfile.gettempdir()) / "bot_hunt_poly_test.db"
if tmp.exists():
    tmp.unlink()
R.DB = tmp
con = R.connect()
con.execute("insert into cycles (started_utc) values (?)", (R.now(),))
con.commit()

R.POLY_TAGS = ["dota-2"]
R.poly_cycle(con, 1)

rows = con.execute(
    "select slug, count(distinct token_id) n from p_book group by slug"
).fetchall()
two = [r for r in rows if r[1] >= 2]
print(f"slugs recorded: {len(rows)}   with >=2 tokens: {len(two)}")
for slug, n in two[:4]:
    print(f"  {slug[:52]:52}")
    for o, b, a in con.execute(
            "select outcome, bid_c, ask_c from p_book where slug=?", (slug,)):
        print(f"      {str(o)[:24]:24} bid={b} ask={a}")
con.close()
print("\nPASS — both sides recorded" if two else
      "\nFAIL — still one side per market")
