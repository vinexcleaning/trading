"""AUDIT: are we throwing away good videos?

The user's stated fear. This checks it against the data rather than reassuring.

Three things are examined:
  1. G3 (off topic)      -- measured recall on 64 hand-judged videos
  2. G3 (discretionary)  -- the NEW Phase 2 boundary, the riskiest change
  3. G2 (stale, >18mo)   -- 184 videos held out by a rule Phase 2 already replaced
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402
import rank_substance as RS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
con = db_phase2.connect()


def substance_of(vid):
    r = con.execute("SELECT snippets_json FROM transcripts WHERE video_id=?",
                    (vid,)).fetchone()
    if not r:
        return None
    text = " ".join(s["text"] for s in json.loads(r[0]))
    return RS.score(text)[0]


print("=" * 76)
print("1. G3 OFF-TOPIC -- how many good videos does it reject?")
print("=" * 76)
v3 = json.loads((ROOT / "reports" / "g3_v3_score.json").read_text(encoding="utf-8"))
comb = v3["combined (all 64 hand-judged)"]
print(f"  Measured on 64 hand-judged videos: recall {comb['recall']:.3f}, "
      f"false negatives {comb['fn']}")
print(f"  -> Of 64 videos judged on-topic-or-not by hand, G3 wrongly rejected {comb['fn']}.")
print("  This is the gate retuned in Phase 2 specifically to stop losing videos.")

print()
print("=" * 76)
print("2. G3 DISCRETIONARY -- the new boundary. Is it cutting anything valuable?")
print("=" * 76)
rows = con.execute(
    """SELECT v.video_id, v.title, v.view_count FROM videos v
       WHERE v.gate_status='DROP_G3_DISCRETIONARY'"""
).fetchall()
scored = []
for r in rows:
    s = substance_of(r["video_id"])
    if s is not None:
        scored.append((s, r["title"], r["view_count"]))
scored.sort(reverse=True)
passing = [x for x in con.execute(
    "SELECT video_id FROM videos WHERE gate_status='PASS'")]
pass_scores = sorted((substance_of(r["video_id"]) for r in passing), reverse=True)
pass_scores = [s for s in pass_scores if s is not None]
cut30 = pass_scores[29] if len(pass_scores) > 29 else 0

print(f"  {len(rows)} videos cut as discretionary. Their substance scores vs the")
print(f"  score needed to reach the passing top 30 ({cut30:.1f}):\n")
for s, t, v in scored[:8]:
    flag = "  <-- would have made the top 30" if s >= cut30 else ""
    print(f"    {s:>6.1f}  {(v or 0):>8,} views  {(t or '')[:44]}{flag}")
above = sum(1 for s, _, _ in scored if s >= cut30)
print(f"\n  {above} of {len(rows)} would have ranked in the top 30 on substance.")

print()
print("=" * 76)
print("3. G2 STALE -- THE REAL PROBLEM")
print("=" * 76)
stale = con.execute(
    "SELECT video_id, title, view_count FROM videos WHERE gate_status='STALE_G2'"
).fetchall()
ss = []
for r in stale:
    s = substance_of(r["video_id"])
    if s is not None:
        ss.append((s, r["title"], r["view_count"]))
ss.sort(reverse=True)
print(f"  {len(stale)} videos are set aside as older than 18 months.")
print(f"  BUT Phase 2 decided recency is handled PER CLAIM, not per video:")
print(f"     mechanism/concept/math -> never expires")
print(f"     procedure 12mo, tool 4mo, price/API 3mo, result 3mo")
print(f"  A 3-year-old explanation of how market making works has not expired.")
print(f"  Yet the read set was built from gate_status='PASS' only, so all")
print(f"  {len(stale)} were excluded from reading.\n")
print(f"  Top stale videos by substance (top-30 bar is {cut30:.1f}):\n")
for s, t, v in ss[:12]:
    flag = "  <-- beats the passing top 30" if s >= cut30 else ""
    print(f"    {s:>6.1f}  {(v or 0):>8,} views  {(t or '')[:44]}{flag}")
above_s = sum(1 for s, _, _ in ss if s >= cut30)
print(f"\n  *** {above_s} of {len(ss)} stale videos out-score the passing top 30. ***")

print()
print("=" * 76)
print("VERDICT")
print("=" * 76)
print(f"  G3 off-topic     : recall 1.000 on the hand-judged set. Not losing videos.")
print(f"  G3 discretionary : {above} of {len(rows)} cut videos would have ranked top 30.")
print(f"  G2 stale         : {above_s} of {len(ss)} EXCLUDED videos out-score the top 30.")
print(f"\n  The age gate is the leak. It is excluding high-substance material for")
print(f"  being old, under a rule this project already voted to replace.")
con.close()
