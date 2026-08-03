"""Why did these two fail G3? Both look like they had enough evidence."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import gates  # noqa: E402

con = db.connect()
for vid in ("6njREUQAFdg", "3MOaUKnQzto"):
    r = con.execute(
        """SELECT v.title, t.snippets_json FROM videos v
           JOIN transcripts t ON t.video_id=v.video_id WHERE v.video_id=?""", (vid,)
    ).fetchone()
    head = gates.head_words(json.loads(r["snippets_json"]), 500)
    ok, ev = gates.g3_on_topic(r["title"], head)
    print(f"\n{vid}  {r['title'][:60]}")
    print(f"  decision={ok}  rule={ev['rule']}")
    for k in ("core", "context", "method", "negative"):
        print(f"  {k:<9} {ev[k]}")
    text = f"{r['title']} \n {head}".lower()
    for neg in ev["negative"]:
        i = text.find(neg.rstrip())
        print(f"  NEGATIVE {neg!r} matched at {i}: ...{text[max(0,i-70):i+40]}...")
con.close()
