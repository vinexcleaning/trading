"""Diagnose the 5 G3 false negatives before changing anything.

Hypothesis A: the term regex requires an exact match, so the plural
              "prediction markets" never matches the core term "prediction market".
Hypothesis B: "walk forward" sits in METHOD, not CORE, so walk-forward-analysis
              trading education needs a second method term it often lacks.

Also checks whether promoting "walk forward" to CORE would wrongly admit the four
"Backtesting Walk Forward Optimization Global N Futures" uploads, whose captions
are almost entirely [Music] tags -- i.e. whether the right fix is in G3 at all.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import gates  # noqa: E402

TAG = re.compile(r"\[[^\]]*\]|\([^)]*\)")

print("A. does the plural break the match?")
for probe in ["prediction market", "prediction markets", "Prediction Markets Are Now Live"]:
    hits = gates._hits(probe.lower(), gates.CORE)
    print(f"   {probe!r:<40} -> core hits {hits}")

print("\nB. the four music-caption uploads: how much real speech is there?")
con = db.connect()
rows = con.execute(
    """SELECT v.video_id, v.title, t.n_words, t.snippets_json
       FROM videos v JOIN transcripts t ON t.video_id=v.video_id
       WHERE v.title LIKE 'Backtesting Walk Forward Optimization Global%'"""
).fetchall()
for r in rows:
    snips = json.loads(r["snippets_json"])
    full = " ".join(s["text"] for s in snips)
    real = TAG.sub(" ", full).split()
    total_tokens = len(full.split())
    print(f"   {r['video_id']}  {r['title'][:52]}")
    print(f"      total tokens {total_tokens:>6}   real words {len(real):>6}   "
          f"tag share {100*(1-len(real)/max(total_tokens,1)):.0f}%")

print("\n   for contrast, a few genuine videos:")
for r in con.execute(
    """SELECT v.video_id, v.title, t.snippets_json FROM videos v
       JOIN transcripts t ON t.video_id=v.video_id
       WHERE v.gate_status='PASS' LIMIT 5"""
):
    snips = json.loads(r["snippets_json"])
    full = " ".join(s["text"] for s in snips)
    real = TAG.sub(" ", full).split()
    total = len(full.split())
    print(f"      {r['title'][:46]:<48} real {len(real):>6}  "
          f"tag share {100*(1-len(real)/max(total,1)):.0f}%")
con.close()
