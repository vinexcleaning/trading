"""Score the Bluesky corpus on the sibling rubric, with the placebo beside it.

Nothing new is invented here. `social-signal/src/rubric.py` is imported, and
the gate is copied verbatim from `social-signal/src/reddit_score.py`, so the
numbers land on the same axis as the Reddit and Mastodon rows already
published in `PLATFORMS.md`.

Three things are reported and the third is the one that decides anything:

1. **post only** — the Mastodon unit.
2. **post + replies** — the Reddit unit. Reported separately, never averaged
   with the first: they are different objects.
3. **the shuffled placebo** — the same documents with the words shuffled
   inside each one. Every rubric component is a phrase pattern, so a score that
   survives shuffling was never reading phrases. This is `CLAUDE.md` §9c Step 4
   applied to the instrument instead of to the strategy.

And the number the mail actually asked for: **how many items carry a claim with
a sample size attached** — component `S3`. That is what separates a study from
an opinion, and it is the bar the Reddit corpus set.

    py -3 extractor-apify\\src\\score_corpus.py
"""
from __future__ import annotations

import argparse
import collections
import os
import random
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "social-signal", "src"))
import rubric  # noqa: E402

DB = os.path.join(os.path.dirname(HERE), "data", "bluesky.db")
REPORTS = os.path.join(os.path.dirname(HERE), "reports")

MIN_CHARS = 200
ONTOPIC = ("kalshi", "polymarket", "prediction market", "predictionmarket",
           "event contract", "sportsbook", "betfair", "arbitrage",
           "market maker", "order book", "backtest", "algotrading",
           "trading bot", "clob")
RECOMMEND = {"BUILD_AND_RECOMMEND", "ABSORB_AND_RECOMMEND"}


def gate(text: str) -> str:
    if len(text) < MIN_CHARS:
        return "DROP_G1_THIN"
    if not any(t in text.lower() for t in ONTOPIC):
        return "DROP_G3_OFF_TOPIC"
    return "PASS"


def tally(docs):
    """Gate + score. Returns (counter, list of (score, uri, verdict))."""
    c = collections.Counter()
    best = []
    for uri, text in docs:
        g = gate(text)
        c[g] += 1
        if g != "PASS":
            continue
        s, b, h, comps = rubric.score(text)
        v = rubric.verdict(s, b, h)
        c[v] += 1
        if v in RECOMMEND:
            c["RECOMMEND"] += 1
        fired = {x["component"] for x in comps}
        for comp in fired:
            c["comp_" + comp] += 1
        if "S3" in fired:
            c["S3"] += 1
        best.append((max(s, b), h, uri, v, sorted(fired)))
    best.sort(reverse=True)
    return c, best


def line(name, c, n):
    p = c["PASS"]
    return (f"  {name:<26} {n:>6}  PASS {p:>5} ({100 * p / max(n, 1):>5.1f}%)"
            f"  recommend {c['RECOMMEND']:>3}"
            f" ({100 * c['RECOMMEND'] / max(p, 1):>5.2f}% of PASS)"
            f"  sample-size {c['S3']:>4}"
            f" ({100 * c['S3'] / max(p, 1):>5.1f}% of PASS)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    if not os.path.exists(DB):
        print("  no corpus yet — run src/bluesky_fetch.py first")
        return 1
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    replies = collections.defaultdict(list)
    for r in con.execute("SELECT root_uri, text FROM bs_replies "
                         "ORDER BY depth, created_utc"):
        replies[r["root_uri"]].append(r["text"] or "")

    posts = con.execute("SELECT uri, handle, text, reply_count, like_count "
                        "FROM bs_posts").fetchall()
    rng_row = con.execute("SELECT MIN(created_utc), MAX(created_utc) "
                          "FROM bs_posts").fetchone()

    post_only = [(p["uri"], p["text"] or "") for p in posts]
    threaded = [(p["uri"], "\n".join([p["text"] or ""] + replies.get(p["uri"],
                                                                    [])))
                for p in posts]
    # The honest denominator for the thread unit is the threads that actually
    # have replies attached. Counting a reply-less post as a "thread" would
    # dilute the very effect being measured.
    with_replies = [(u, t) for (u, t) in threaded if replies.get(u)]

    print(f"  {len(posts)} posts, {sum(len(v) for v in replies.values())} "
          f"replies across {len(replies)} threads")
    print(f"  date range {rng_row[0]} .. {rng_row[1]}\n")

    cp, _ = tally(post_only)
    ct, bt = tally(threaded)
    cw, _ = tally(with_replies)

    print("  BLUESKY")
    print(line("post only", cp, len(post_only)))
    print(line("post + replies (all)", ct, len(threaded)))
    print(line("post + replies (only", cw, len(with_replies)))
    print(f"  {'  threads with replies)':<26}")
    print()

    # The placebo. Same documents, words shuffled inside each one.
    rnd = random.Random(20260814)

    def shuffled(docs):
        out = []
        for u, t in docs:
            w = t.split()
            rnd.shuffle(w)
            out.append((u, " ".join(w)))
        return out

    cs, _ = tally(shuffled(threaded))
    print("  PLACEBO — the same documents, words shuffled inside each")
    print(line("real word order", ct, len(threaded)))
    print(line("shuffled", cs, len(threaded)))
    surv = (100 * cs["RECOMMEND"] / max(ct["RECOMMEND"], 1))
    print(f"  {surv:.0f}% of the recommend-grade verdicts survive destroying "
          f"the word order entirely.")
    print()

    print("  COMPONENT FIRING RATES, of everything that cleared the gate")
    for comp in ["S1", "S2", "S3", "S4", "S5", "B1", "B2", "B3", "B4", "B5",
                 "H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H10"]:
        n = ct["comp_" + comp]
        print(f"    {comp:<5} {rubric.MEANING[comp][:52]:<54} "
              f"{100 * n / max(ct['PASS'], 1):>5.1f}%")
    print()

    print(f"  TOP {args.top} ITEMS, best first")
    for score, h, uri, v, fired in bt[:args.top]:
        row = con.execute("SELECT handle, reply_count, like_count, text "
                          "FROM bs_posts WHERE uri=?", (uri,)).fetchone()
        rkey = uri.split("/")[-1]
        link = f"https://bsky.app/profile/{row['handle']}/post/{rkey}"
        print(f"    max(S,B)={score} H={h:>3} {v:<26} "
              f"{row['reply_count']:>3}r {row['like_count']:>4}L  {link}")
        print(f"        {' '.join((row['text'] or '').split())[:150]}")
        print(f"        fired: {','.join(fired)}")

    os.makedirs(REPORTS, exist_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
