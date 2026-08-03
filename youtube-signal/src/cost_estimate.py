"""Cost estimate for Step 2, computed from the ACTUAL transcripts of the actual
selected videos rather than from a guessed average.

Token counts are estimated at 4 characters per token. The real tokeniser lives
behind the API, which is the thing we do not have access to, so this is an
approximation -- treated as +/-20% and reported as a range, not a point.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402

CHARS_PER_TOKEN = 4.0

# Published per-million-token prices, USD.
PRICING = {
    "claude-sonnet-5":   {"in": 3.00, "out": 15.00},
    "claude-opus-5":     {"in": 15.00, "out": 75.00},
    "claude-haiku-4-5":  {"in": 1.00, "out": 5.00},
}

# The read emits one structured JSON per video: scores with evidence quotes,
# tools, claims, methods, watch_segments. Measured against the schema, a
# well-populated response is roughly 1,200-2,500 output tokens. 2,000 is used.
OUTPUT_TOKENS_PER_VIDEO = 2_000
PROMPT_OVERHEAD_TOKENS = 1_800     # the scoring rubric sent with every call

con = db_phase2.connect()
rows = con.execute(
    """SELECT r.video_id, v.title, v.duration_s, t.n_words, t.snippets_json
       FROM read_set r
       JOIN videos v ON v.video_id = r.video_id
       LEFT JOIN transcripts t ON t.video_id = r.video_id"""
).fetchall()

if not rows:
    print("read_set is empty -- run select_read_set.py first")
    raise SystemExit(1)

chars, words, missing = [], [], 0
for r in rows:
    if not r["snippets_json"]:
        missing += 1
        continue
    snips = json.loads(r["snippets_json"])
    text = " ".join(s["text"] for s in snips)
    chars.append(len(text))
    words.append(len(text.split()))

n = len(chars)
tok = [c / CHARS_PER_TOKEN for c in chars]
total_in = sum(tok) + PROMPT_OVERHEAD_TOKENS * n
total_out = OUTPUT_TOKENS_PER_VIDEO * n

print(f"read set: {len(rows)} videos, {n} with a cached transcript"
      f"{f', {missing} missing' if missing else ''}\n")
print(f"  transcript words : total {sum(words):,}  mean {sum(words)/n:,.0f}  "
      f"max {max(words):,}")
print(f"  input tokens est : total {total_in:,.0f}  mean {total_in/n:,.0f}/video")
print(f"  output tokens est: total {total_out:,}  ({OUTPUT_TOKENS_PER_VIDEO}/video)")
print(f"  (input includes a {PROMPT_OVERHEAD_TOKENS}-token rubric per call)\n")

print(f"  {'model':<20}{'input $':>10}{'output $':>10}{'TOTAL $':>10}{'range +/-20%':>18}")
out = {}
for model, p in PRICING.items():
    ci = total_in / 1e6 * p["in"]
    co = total_out / 1e6 * p["out"]
    tot = ci + co
    out[model] = round(tot, 2)
    print(f"  {model:<20}{ci:>10.2f}{co:>10.2f}{tot:>10.2f}"
          f"{f'{0.8*tot:.2f} - {1.2*tot:.2f}':>18}")

print(f"\n  per-video on Sonnet: ${out['claude-sonnet-5']/n:.4f}")
print(f"  a full re-read of all {con.execute(chr(83)+'ELECT COUNT(*) c FROM videos').fetchone()['c']:,} "
      f"known videos would be ~{out['claude-sonnet-5'] * con.execute('SELECT COUNT(*) c FROM videos').fetchone()['c'] / n:,.0f} USD on Sonnet")

(Path(__file__).resolve().parent.parent / "reports" / "cost_estimate.json").write_text(
    json.dumps({"n_videos": n, "input_tokens": round(total_in),
                "output_tokens": total_out, "usd": out,
                "chars_per_token_assumed": CHARS_PER_TOKEN}, indent=2),
    encoding="utf-8")
con.close()
