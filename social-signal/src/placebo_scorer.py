"""Does my own scoring survive a placebo? Two tests, both offline.

**Why this exists.** Mailbox 013 told me to carry two warnings to the `factory`:
that roughly 1 in 3 "has a real sample size" hits are just the phrase *"30
days"*, and that shuffling the words in 4,000 threads still scores half of them
as good. **Neither is mine.** I never measured either, and they appear nowhere in
my own documents.

Repeating an unmeasured warning is the same error as repeating an unmeasured
finding — it just feels safer because it points downward. So this measures them.
And a placebo arm is required by the programme's own method anyway: *"put a fake
control in there to make sure that everything works. If the pipeline finds an
edge in noise, the pipeline is broken."*

**Test 1 — is the denominator real?** `hunt_new.py` scores a post partly on a
count bound to a unit. Time windows (*"30 days"*, *"6 months"*) match that
pattern and are **not sample sizes** — they say how long someone watched, not how
many things they observed.

**Test 2 — the word shuffle.** Shuffle the words within each post, destroying
every sentence while keeping the exact vocabulary. **A scorer reading meaning
collapses. A scorer counting keywords does not move.** Whatever fraction of the
real score survives the shuffle is the fraction that was never reading anything.

    python src/placebo_scorer.py
"""
from __future__ import annotations

import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db          # noqa: E402
import hunt_new    # noqa: E402

# Units that measure TIME, not observations. "30 days" is a window; "30 games"
# is a sample. The distinction is the whole point of the denominator score.
TIME_UNITS = re.compile(r"^(days?|weeks?|months?|windows?)$", re.I)
SEED = 20260820          # fixed, so the placebo is reproducible


def main():
    con = db.connect()
    rows = con.execute("""
        SELECT p.post_id, p.title, COALESCE(p.selftext,'') AS body
        FROM rd_posts p JOIN rd_scores s ON s.post_id = p.post_id
        WHERE p.gate_status = 'PASS'""").fetchall()
    print(f"{len(rows):,} gated posts\n")

    # ---------- Test 1: are the "sample sizes" actually sample sizes? ----------
    hits = real = timey = 0
    posts_with = posts_time_only = 0
    for r in rows:
        text = f"{r['title']}\n{r['body']}"
        found = hunt_new.DENOM.findall(text)
        if not found:
            continue
        posts_with += 1
        t = [u for _n, u in found if TIME_UNITS.match(u)]
        o = [u for _n, u in found if not TIME_UNITS.match(u)]
        hits += len(found)
        timey += len(t)
        real += len(o)
        if t and not o:
            posts_time_only += 1

    print("TEST 1 — is the 'sample size' a sample size?")
    print(f"  posts with any denominator      {posts_with:>8,}")
    print(f"  total matches                   {hits:>8,}")
    print(f"    ...measuring OBSERVATIONS     {real:>8,}  "
          f"({real/max(hits,1)*100:.1f}%)")
    print(f"    ...measuring TIME only        {timey:>8,}  "
          f"({timey/max(hits,1)*100:.1f}%)")
    print(f"  posts whose ONLY denominator is a time window: "
          f"{posts_time_only:,} ({posts_time_only/max(posts_with,1)*100:.1f}% "
          f"of posts with one)")
    print("  ^ those posts score as 'carries a sample size' and do not.\n")

    # ---------- Test 2: the word shuffle ----------
    rnd = random.Random(SEED)
    kept = 0
    scored = 0
    real_pos = shuf_pos = 0
    for r in rows:
        text = f"{r['title']}\n{r['body']}"
        s_real, _p, _b = hunt_new.score(text)
        words = text.split()
        rnd.shuffle(words)
        s_shuf, _p2, _b2 = hunt_new.score(" ".join(words))
        scored += 1
        if s_real > 0:
            real_pos += 1
            if s_shuf > 0:
                kept += 1
        if s_shuf > 0:
            shuf_pos += 1

    print("TEST 2 — shuffle every word, keep the exact vocabulary")
    print(f"  posts scored                    {scored:>8,}")
    print(f"  scored ABOVE ZERO, real text    {real_pos:>8,}")
    print(f"  scored ABOVE ZERO, shuffled     {shuf_pos:>8,}")
    print(f"  of the real positives, still positive when shuffled: "
          f"{kept:,} ({kept/max(real_pos,1)*100:.1f}%)")
    print("""
  A scorer reading meaning collapses under this. A scorer counting keywords
  does not move. Whatever survives is the fraction that was never reading.""")

    out = os.path.join(db.REPORTS, "PLACEBO_SCORER.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Placebo test of my own scorer\n\n")
        fh.write(f"- gated posts: {len(rows):,}\n")
        fh.write(f"- denominator matches measuring TIME rather than "
                 f"observations: **{timey:,} of {hits:,} "
                 f"({timey/max(hits,1)*100:.1f}%)**\n")
        fh.write(f"- posts whose only denominator is a time window: "
                 f"**{posts_time_only:,} ({posts_time_only/max(posts_with,1)*100:.1f}%)**\n")
        fh.write(f"- real positives still positive after shuffling every word: "
                 f"**{kept:,} of {real_pos:,} "
                 f"({kept/max(real_pos,1)*100:.1f}%)**\n\n")
        fh.write("Seed %d, reproducible.\n" % SEED)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
