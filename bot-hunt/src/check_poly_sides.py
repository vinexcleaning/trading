"""Did the both-tokens fix take? Verified against the live DB, not assumed.

Before the fix a census read "slugs with >=2 recorded outcomes: 0 of 436",
because `poly_cycle` probed only `toks[0]`. GUARDS #13: assert something about
the CONTENT, not that the function returned.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "record.db"
c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=180)

cut = c.execute("select max(cycle_id) from cycles").fetchone()[0]
print(f"latest cycle: {cut}")
for label, where in (("ALL cycles", ""),
                     ("since the fix", f"and cycle_id >= {cut - 1}")):
    rows = c.execute(
        f"select slug, count(distinct token_id) from p_book "
        f"where tag in ('cs2','dota-2','valorant') {where} group by slug"
    ).fetchall()
    two = sum(1 for _, n in rows if n >= 2)
    print(f"  {label:16} slugs={len(rows):>5}  with >=2 tokens: {two:>5}")

print("\nsample of two-sided markets recorded since the fix:")
for slug, n in c.execute(
        f"select slug, count(distinct token_id) n from p_book "
        f"where tag in ('cs2','dota-2','valorant') and cycle_id >= {cut - 1} "
        f"group by slug having n >= 2 limit 5"):
    outs = c.execute("select distinct outcome, bid_c, ask_c from p_book "
                     "where slug=? and cycle_id >= ?",
                     (slug, cut - 1)).fetchall()
    print(f"  {slug[:46]:46}")
    for o, b, a in outs[:2]:
        print(f"      {str(o)[:22]:22} bid={b} ask={a}")
c.close()
