"""Merge the laptop's 19 read extractions into this machine's DB.

WHAT IS AND IS NOT MERGED, and why.

MERGED -- the extractions themselves (claims, tools, methods, watch segments,
score evidence). These are properties of a VIDEO, not of a retrieval run, so they
transfer cleanly and every one of them is a video that never has to be read
again.

MERGED -- video metadata and transcripts for the 4 laptop-read videos this
machine's retrieval never returned, because build_knowledge.py inner-joins
`videos` and would otherwise silently drop them. They are inserted with
source='laptop_import', NOT 'search', so that every retrieval statistic in
retrieval_payoff.py Part A and every read-set query keeps counting only videos
this machine actually retrieved.

NOT MERGED -- the laptop's `retrieval_hits`. Family attribution is the
independent variable of the retrieval test and must describe ONE retrieval run.
Mixing two runs' hits would make the buckets uninterpretable.

NOT MERGED -- the laptop's `read_set`. This machine has its own seeded sample.

WHY THE LAPTOP'S 19 MOSTLY DO NOT ENTER THE STATISTICAL TEST

Only 5 of the laptop's 19 came from its own read_set; the other 14 were chosen
top-down by `rank_substance.py`'s proxy score. That proxy is built from the same
surface features the S axis rewards -- cost terms, sample-size language,
mechanism language, URLs -- so those 14 are SELECTED ON A CORRELATE OF THE
OUTCOME. Pooling them into retrieval_payoff.py would import exactly the bias
next_reads.py exists to avoid.

So they enrich KNOWLEDGE.md, which is what they are good for, and they are not
pooled into the test. The ones that DO enter the test are only those that happen
to be in this machine's read_set, which the Part B query already handles by
joining on read_set -- no special casing needed here.
"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db as _db  # noqa: E402
import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAPTOP_DB = ROOT / "_from_laptop" / "signal.db"
LAPTOP_EXT = ROOT / "_from_laptop" / "reports" / "extractions"
PY = sys.executable


def main():
    if not LAPTOP_DB.exists():
        raise SystemExit(f"no laptop DB at {LAPTOP_DB}")

    lc = sqlite3.connect(LAPTOP_DB)
    lc.row_factory = sqlite3.Row
    dc = db_phase2.connect()

    files = sorted(LAPTOP_EXT.glob("*.json"))
    ids = [p.stem for p in files]
    print(f"laptop extractions found: {len(files)}")

    have = {r["video_id"] for r in dc.execute("SELECT video_id FROM videos")}
    missing = [v for v in ids if v not in have]
    print(f"already in this corpus: {len(ids) - len(missing)}   "
          f"missing, will import: {len(missing)}")

    for vid in missing:
        r = lc.execute("SELECT * FROM videos WHERE video_id=?", (vid,)).fetchone()
        if not r:
            print(f"  {vid}: not in laptop videos table either, skipped")
            continue
        dc.execute(
            """INSERT OR IGNORE INTO videos (video_id, channel_id, channel_name,
                   title, view_count, duration_s, upload_date, age_months,
                   source, transcript_words, transcript_via, is_stale,
                   gate_status, metadata_fetched, created_utc, description)
               VALUES (?,?,?,?,?,?,?,?, 'laptop_import', ?,?,?,?,1,?,?)""",
            (r["video_id"], r["channel_id"], r["channel_name"], r["title"],
             r["view_count"], r["duration_s"], r["upload_date"], r["age_months"],
             r["transcript_words"], r["transcript_via"], r["is_stale"],
             r["gate_status"], _db.now(),
             r["description"] if "description" in r.keys() else None))
        t = lc.execute("SELECT * FROM transcripts WHERE video_id=?", (vid,)).fetchone()
        if t:
            dc.execute(
                "INSERT OR IGNORE INTO transcripts (video_id, via, n_snippets,"
                " n_words, snippets_json, fetched_utc) VALUES (?,?,?,?,?,?)",
                (t["video_id"], t["via"], t["n_snippets"], t["n_words"],
                 t["snippets_json"], t["fetched_utc"]))
        print(f"  imported {vid}  {(r['title'] or '?')[:52]}")
    dc.commit()

    # Keep the laptop's own scores so the reload can be verified against them.
    lap_scores = {r["video_id"]: dict(r) for r in lc.execute(
        "SELECT video_id, s_total, h_total, COALESCE(b_total,0) b_total,"
        " verdict FROM scores")}
    lc.close(); dc.close()

    print("\nloading extractions through load_extraction.py "
          "(same validator, same evidence rule)...")
    for p in files:
        subprocess.run([PY, str(ROOT / "src" / "load_extraction.py"), str(p)],
                       check=False)

    # ---- verification: does this machine reproduce the laptop's scores? ----
    dc = db_phase2.connect()
    print("\n" + "=" * 70)
    print("VERIFICATION -- do the reloaded scores match the laptop's?")
    print("=" * 70)
    same = diff = 0
    for vid, lap in lap_scores.items():
        r = dc.execute("SELECT s_total, h_total, COALESCE(b_total,0) b_total,"
                       " verdict FROM scores WHERE video_id=?", (vid,)).fetchone()
        if not r:
            print(f"  {vid}  MISSING after load")
            diff += 1
            continue
        ok = (r["s_total"] == lap["s_total"] and r["h_total"] == lap["h_total"]
              and r["b_total"] == lap["b_total"] and r["verdict"] == lap["verdict"])
        if ok:
            same += 1
        else:
            diff += 1
            print(f"  {vid}  laptop S={lap['s_total']} B={lap['b_total']} "
                  f"H={lap['h_total']} {lap['verdict']}")
            print(f"  {' ' * len(vid)}  here   S={r['s_total']} B={r['b_total']} "
                  f"H={r['h_total']} {r['verdict']}")
    print(f"\n  identical: {same}/{len(lap_scores)}   differing: {diff}")
    if diff == 0:
        print("  This machine reproduces the laptop's scoring exactly from the "
              "same inputs.\n  The scoring pipeline is deterministic across "
              "machines.")
    dc.close()


if __name__ == "__main__":
    main()
