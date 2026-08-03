"""Load a hand-read extraction into the DB.

This is the free path in practice. Instead of an API call producing the JSON,
Claude reads the transcript in-session and the extraction is written here. Same
schema, same evidence rule, same n-check. The only difference is who did the
reading and that it cost nothing.

The evidence rule is enforced HERE, not trusted: a score component without a
timestamp and a verbatim quote under 15 words is rejected, whoever produced it.

Usage:  python src/load_extraction.py reports/extractions/<video_id>.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db as _db  # noqa: E402
import db_phase2  # noqa: E402
import ncheck  # noqa: E402
import read_video as RV  # noqa: E402


def load(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    vid = doc["video_id"]
    con = db_phase2.connect()

    clean, rejects = RV.validate_response(doc)
    for axis, comp, why in rejects:
        print(f"  REJECTED {axis} {comp}: {why}")

    s, h = RV.totals(clean)
    dur = con.execute("SELECT duration_s FROM videos WHERE video_id=?",
                      (vid,)).fetchone()
    dur = dur["duration_s"] if dur else None
    verdict = RV.verdict(s, h, bool(clean.get("visual_dependent")),
                         duration_s=dur, teaching_quality=doc.get("teaching_quality"))

    con.execute("DELETE FROM score_evidence WHERE video_id=?", (vid,))
    con.execute("DELETE FROM claims WHERE video_id=?", (vid,))
    con.execute("DELETE FROM methods WHERE video_id=?", (vid,))
    con.execute("DELETE FROM watch_segments WHERE video_id=?", (vid,))

    con.execute(
        """INSERT INTO scores (video_id, s_total, h_total, verdict, visual_dependent,
               model, input_tokens, output_tokens, cost_usd, scored_utc)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(video_id) DO UPDATE SET
             s_total=excluded.s_total, h_total=excluded.h_total,
             verdict=excluded.verdict, visual_dependent=excluded.visual_dependent,
             model=excluded.model, scored_utc=excluded.scored_utc""",
        (vid, s, h, verdict, 1 if clean.get("visual_dependent") else 0,
         doc.get("model", "claude-opus-5 (in-session, no API)"), 0, 0, 0.0, _db.now()))

    for axis, key, weights in (("S", "s_components", RV.S_WEIGHTS),
                               ("H", "h_components", RV.H_WEIGHTS)):
        for c in clean.get(key, []):
            con.execute(
                "INSERT OR REPLACE INTO score_evidence (video_id, axis, component,"
                " weight, timestamp_s, quote) VALUES (?,?,?,?,?,?)",
                (vid, axis, c["component"], weights[c["component"]],
                 c["timestamp_s"], c["quote"]))

    for t in doc.get("tools", []):
        con.execute(
            """INSERT INTO tools (name, url, claimed_purpose, is_creators_own,
                   is_referral_link, first_seen_video, mention_count, resolution)
               VALUES (?,?,?,?,?,?,?, 'not_checked')
               ON CONFLICT(name, url) DO UPDATE SET
                   mention_count = tools.mention_count + 1""",
            (t["name"], t.get("url"), t.get("claimed_purpose"),
             t.get("is_creators_own", "no"), 1 if t.get("is_referral_link") else 0,
             vid, 1))

    clean = RV.run_ncheck_on_claims(clean)
    for c in clean.get("claims", []):
        con.execute(
            """INSERT INTO claims (video_id, timestamp_s, claim_text, claim_type,
                   stated_n, stated_period, stated_capital, stated_win_rate,
                   n_check_verdict, n_check_detail, expires_after_months, confidence)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (vid, c.get("timestamp_s"), c["claim_text"], c.get("claim_type"),
             c.get("stated_n"), c.get("stated_period"), c.get("stated_capital"),
             c.get("stated_win_rate"), c.get("n_check_verdict"),
             c.get("n_check_detail"), c.get("expires_after_months"),
             c.get("confidence")))

    for m in doc.get("methods", []):
        con.execute(
            "INSERT INTO methods (video_id, title, steps_json, ts_start, ts_end)"
            " VALUES (?,?,?,?,?)",
            (vid, m.get("title"), json.dumps(m["steps"]),
             m.get("ts_start"), m.get("ts_end")))

    for w in doc.get("watch_segments", []):
        con.execute(
            "INSERT INTO watch_segments (video_id, ts_start, ts_end, why)"
            " VALUES (?,?,?,?)", (vid, w["ts_start"], w["ts_end"], w.get("why")))

    con.commit()

    dur = dur or 0
    watch = sum(w["ts_end"] - w["ts_start"] for w in doc.get("watch_segments", []))
    print(f"\n{vid}  S={s}/10  H={h}  ->  {verdict}")
    print(f"  tools {len(doc.get('tools', []))}  claims {len(clean.get('claims', []))}"
          f"  methods {len(doc.get('methods', []))}"
          f"  watch_segments {len(doc.get('watch_segments', []))}")
    if dur:
        print(f"  runtime {dur/60:.0f} min -> watch {watch/60:.1f} min "
              f"({100*watch/dur:.0f}%)  COMPRESSION {dur/max(watch,1):.0f}x")
    for c in clean.get("claims", []):
        if c.get("n_check_verdict"):
            print(f"  n-check: {c['n_check_verdict']} -- {c['claim_text'][:56]}")
    con.close()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        load(p)
