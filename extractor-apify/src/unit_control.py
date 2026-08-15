"""Control 1: is the Reddit-vs-Mastodon gap a platform difference or a unit one?

`social-signal/PLATFORMS.md` publishes this comparison:

    reddit    39,633 items   11% PASS    282 recommend-grade  (6.4% of PASS)
    mastodon   6,727 items   33% PASS      4 recommend-grade  (0.18% of PASS)

and reads a 35x difference off it as a property of the two platforms.

It cannot be read that way yet, because the two rows are not the same object.
`reddit_score.py` scores a post **plus its comment thread**. `social.db` holds
12,846 comments and **every one of them belongs to a Reddit post** — Mastodon
has zero. So the table compares Reddit threads against Mastodon posts.

This re-scores Reddit on **post text only** and prints the gap again. If most of
it disappears, the published ranking is measuring the unit of observation.

Read-only. Opens the sibling database with `mode=ro` and writes nothing to it.

    py -3 extractor-apify\\src\\unit_control.py
"""
from __future__ import annotations

import collections
import os
import random
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "social-signal", "src"))
import rubric  # noqa: E402

SOCIAL_DB = os.path.join(ROOT, "social-signal", "data", "social.db")

# Copied verbatim from reddit_score.py so the two are scored by one gate.
MIN_CHARS = 200
ONTOPIC = ("kalshi", "polymarket", "prediction market", "predictionmarket",
           "event contract", "sportsbook", "betfair", "arbitrage",
           "market maker", "order book", "backtest", "algotrading",
           "trading bot", "clob")

RECOMMEND = {"BUILD_AND_RECOMMEND", "ABSORB_AND_RECOMMEND"}


def gate(text: str) -> str:
    if len(text) < MIN_CHARS:
        return "DROP_G1_THIN"
    low = text.lower()
    if not any(t in low for t in ONTOPIC):
        return "DROP_G3_OFF_TOPIC"
    return "PASS"


def tally(texts):
    """Gate + score a bag of documents. Returns a counter and S3 firings."""
    c = collections.Counter()
    s3 = 0
    for t in texts:
        g = gate(t)
        c[g] += 1
        if g != "PASS":
            continue
        s, b, h, comps = rubric.score(t)
        v = rubric.verdict(s, b, h)
        c[v] += 1
        if v in RECOMMEND:
            c["RECOMMEND"] += 1
        if any(x["component"] == "S3" for x in comps):
            s3 += 1
    c["S3"] = s3
    return c


def line(name, c, n):
    p = c["PASS"]
    return (f"  {name:<34} {n:>7}  PASS {p:>6} ({100 * p / max(n, 1):>5.1f}%)"
            f"  recommend {c['RECOMMEND']:>4}"
            f" ({100 * c['RECOMMEND'] / max(p, 1):>5.2f}% of PASS)"
            f"  sample-size {c['S3']:>5}"
            f" ({100 * c['S3'] / max(p, 1):>5.1f}% of PASS)")


def main() -> int:
    if not os.path.exists(SOCIAL_DB):
        print(f"  sibling database not found: {SOCIAL_DB}")
        return 1
    con = sqlite3.connect(f"file:{SOCIAL_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    by_post = collections.defaultdict(list)
    for c in con.execute("SELECT post_id, body FROM rd_comments"):
        by_post[c["post_id"]].append(c["body"] or "")

    reddit_thread, reddit_post, mastodon = [], [], []
    for p in con.execute("SELECT post_id, platform, title, selftext "
                         "FROM rd_posts"):
        head = "\n".join([p["title"] or "", p["selftext"] or ""])
        if p["platform"] == "reddit":
            reddit_post.append(head)
            reddit_thread.append("\n".join([head] + by_post.get(p["post_id"],
                                                                [])))
        else:
            mastodon.append(head)

    print(f"  {len(reddit_thread)} reddit, {len(mastodon)} mastodon, "
          f"{sum(len(v) for v in by_post.values())} comments\n")

    tr = tally(reddit_thread)
    tp = tally(reddit_post)
    tm = tally(mastodon)

    print("  AS PUBLISHED — reddit scored on threads, mastodon on posts")
    print(line("reddit (post + comments)", tr, len(reddit_thread)))
    print(line("mastodon (post only)", tm, len(mastodon)))
    print()
    print("  SAME UNIT — both scored on post text only")
    print(line("reddit (post only)", tp, len(reddit_post)))
    print(line("mastodon (post only)", tm, len(mastodon)))
    print()

    def rate(c, n):
        return 100 * c["RECOMMEND"] / max(c["PASS"], 1)

    pub = rate(tr, len(reddit_thread)) / max(rate(tm, len(mastodon)), 1e-9)
    fair = rate(tp, len(reddit_post)) / max(rate(tm, len(mastodon)), 1e-9)
    print(f"  reddit/mastodon recommend-rate ratio")
    print(f"    as published (thread vs post):  {pub:>6.1f}x")
    print(f"    same unit    (post vs post):    {fair:>6.1f}x")
    print(f"    so {100 * (1 - fair / max(pub, 1e-9)):.0f}% of the published "
          f"gap was the unit of observation, not the platform")

    # Control 2 on the sibling corpus too: shuffle the words inside each
    # document. Every rubric component is a phrase pattern, so a lexicon that
    # survives shuffling is counting single words.
    rnd = random.Random(20260814)
    sample = reddit_thread[:4000]

    def shuffle(t):
        w = t.split()
        rnd.shuffle(w)
        return " ".join(w)

    ts = tally(shuffle(t) for t in sample)
    tn = tally(sample)
    print()
    print("  CONTROL 2 — the same 4,000 reddit threads, words shuffled")
    print(line("real word order", tn, len(sample)))
    print(line("shuffled", ts, len(sample)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
