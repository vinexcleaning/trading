"""Read-only progress peek at the DB while a long run is in flight."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

con = db.connect()
q = lambda s: con.execute(s).fetchone()[0]  # noqa: E731

print(f"search calls logged : {q('SELECT COUNT(*) FROM retrieval_log')}")
print(f"  failed            : {q('SELECT COUNT(*) FROM retrieval_log WHERE ok=0')}")
print(f"hits recorded       : {q('SELECT COUNT(*) FROM retrieval_hits')}")
print(f"unique videos       : {q('SELECT COUNT(*) FROM videos')}")
print(f"  metadata fetched  : {q('SELECT COUNT(*) FROM videos WHERE metadata_fetched=1')}")
print(f"  gated             : {q('SELECT COUNT(*) FROM videos WHERE gate_status IS NOT NULL')}")
print("\nper round:")
for r in con.execute(
    "SELECT run_idx, COUNT(*) n, ROUND(AVG(n_results),1) avg_res,"
    " ROUND(AVG(seconds),2) avg_s FROM retrieval_log GROUP BY run_idx"
):
    print(f"  round {r['run_idx']}: {r['n']:>3} calls, avg {r['avg_res']} results, {r['avg_s']}s")
print("\nper family (union so far):")
for r in con.execute(
    "SELECT family, COUNT(DISTINCT video_id) n FROM retrieval_hits GROUP BY family"
):
    print(f"  {r['family']}: {r['n']} unique videos")
print("\ngate status:")
for r in con.execute(
    "SELECT gate_status, COUNT(*) n FROM videos WHERE gate_status IS NOT NULL"
    " GROUP BY gate_status ORDER BY n DESC"
):
    print(f"  {r['gate_status']:<26} {r['n']}")
con.close()
