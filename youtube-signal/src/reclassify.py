"""Re-apply the gates to the union set from CACHED transcripts.

No network. This is why transcripts are stored: a gate-logic change costs seconds
instead of another 35-minute fetch.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import gates  # noqa: E402

con = db.connect()
rows = con.execute(
    """SELECT v.video_id, v.title, v.age_months, v.gate_status AS old,
              t.snippets_json
       FROM videos v LEFT JOIN transcripts t ON t.video_id = v.video_id
       WHERE v.source='search' AND v.gate_status IS NOT NULL
         AND v.gate_status != 'DROP_META'"""
).fetchall()

print(f"re-classifying {len(rows)} videos from cache\n")
counts, moved = {}, {}
con.execute("DELETE FROM drops")
for r in rows:
    snips = json.loads(r["snippets_json"]) if r["snippets_json"] else None
    status, detail = gates.classify(
        {"title": r["title"], "age_months": r["age_months"]}, snips
    )
    counts[status] = counts.get(status, 0) + 1
    if status != r["old"]:
        moved[f"{r['old']} -> {status}"] = moved.get(f"{r['old']} -> {status}", 0) + 1
    con.execute(
        "UPDATE videos SET gate_status=?, is_stale=? WHERE video_id=?",
        (status, 1 if status == "STALE_G2" else 0, r["video_id"]),
    )
    if status.startswith("DROP") or status == "STALE_G2":
        gate = "G1" if "G1" in status else "G3" if "G3" in status else "G2"
        reason = {
            "DROP_G1_NO_TRANSCRIPT": "no english transcript on either path",
            "DROP_G1_EMPTY_TRANSCRIPT": f"only {detail.get('real_words')} real words "
                                        f"(<{gates.MIN_REAL_WORDS}); caption track is "
                                        f"almost all sound tags",
            "DROP_G3_OFF_TOPIC": f"g3 rule: {detail.get('g3', {}).get('rule')}",
            "DROP_G3_DISCRETIONARY": f"out of Phase 2 scope: {detail.get('g3', {}).get('rule')}",
            "DROP_G2_NO_DATE": "no upload_date available",
            "STALE_G2": f"age {detail.get('age_months')} mo > {gates.STALE_MONTHS}",
        }.get(status, status)
        con.execute(
            "INSERT OR REPLACE INTO drops (video_id, gate, reason, ts_utc)"
            " VALUES (?,?,?,?)", (r["video_id"], gate, reason, db.now())
        )
con.commit()

print("new census:")
for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"  {k:<28} {v:>5}")
print("\nchanges vs the pre-fix gates:")
for k, v in sorted(moved.items(), key=lambda kv: -kv[1]):
    print(f"  {k:<44} {v:>4}")
if not moved:
    print("  none")
con.close()
