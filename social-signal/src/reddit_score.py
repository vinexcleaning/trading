"""T2c — apply the ported rubric to Reddit threads, and rank what to read.

A post is scored on its own text **plus its comment thread**, because on Reddit
the substance is frequently not in the post. A "how do I build a Kalshi bot"
question scores nothing; the reply explaining why the maker fee only applies on
130 series is the artifact. Scoring the post alone would systematically discard
the best content on the platform.

The score written here is a **proxy**, and every consumer of it is told so. It
is a lexicon over text with a verbatim quote per component, not a model read.
`--validate` measures its agreement against threads a human or a model has read
and recorded in `reports/read/`, so the instrument's precision is a number
rather than a hope. Until that file exists the precision is stated as UNKNOWN,
never assumed.

    python src/reddit_score.py
    python src/reddit_score.py --top 40      # the read queue
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import rubric  # noqa: E402

# Gate. Same shape as the sibling projects' G1/G2/G3, adapted to text.
MIN_CHARS = 200          # G1: nothing to read
ONTOPIC = ("kalshi", "polymarket", "prediction market", "predictionmarket",
           "event contract", "sportsbook", "betfair", "arbitrage", "market maker",
           "order book", "backtest", "algotrading", "trading bot", "clob")


def gate(post, thread_text: str):
    if len(thread_text) < MIN_CHARS:
        return "DROP_G1_THIN", f"{len(thread_text)} chars of text"
    low = thread_text.lower()
    if not any(t in low for t in ONTOPIC):
        return "DROP_G3_OFF_TOPIC", "no venue or method term anywhere in the thread"
    return "PASS", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--platform", default="",
                    help="restrict to one platform; default is all of them")
    args = ap.parse_args()

    con = db.connect()
    if args.platform:
        posts = con.execute("SELECT * FROM rd_posts WHERE platform=?",
                            (args.platform,)).fetchall()
    else:
        posts = con.execute("SELECT * FROM rd_posts").fetchall()
    by_post = collections.defaultdict(list)
    for c in con.execute("SELECT post_id, body, score FROM rd_comments"):
        by_post[c["post_id"]].append(c)
    print(f"  {len(posts)} posts, {sum(len(v) for v in by_post.values())} "
          f"comments across {len(by_post)} threads")

    census = collections.Counter()
    scored = 0
    for p in posts:
        comments = by_post.get(p["post_id"], [])
        thread = "\n".join(
            [p["title"] or "", p["selftext"] or ""] +
            [c["body"] or "" for c in comments])
        g, why = gate(p, thread)
        con.execute("UPDATE rd_posts SET gate_status=?, gate_reason=? "
                    "WHERE post_id=?", (g, why, p["post_id"]))
        census[g] += 1
        if g != "PASS":
            continue
        s, b, h, comps = rubric.score(thread)
        v = rubric.verdict(s, b, h)
        con.execute("""INSERT OR REPLACE INTO rd_scores
                       (post_id, s_total, b_total, h_total, verdict,
                        components, scored_utc)
                       VALUES (?,?,?,?,?,?,?)""",
                    (p["post_id"], s, b, h, v, json.dumps(comps), db.now()))
        census[v] += 1
        scored += 1
    con.commit()
    print("  gate + verdict census:")
    for k, n in census.most_common():
        print(f"    {k:<28} {n}")

    # Per-platform census, because a rate computed across platforms with wildly
    # different post shapes is an average of two different things.
    by_plat = collections.defaultdict(collections.Counter)
    for r in con.execute("""SELECT p.platform, p.gate_status, s.verdict
                            FROM rd_posts p
                            LEFT JOIN rd_scores s ON s.post_id = p.post_id"""):
        by_plat[r["platform"] or "?"][r["gate_status"] or "?"] += 1
        if r["verdict"]:
            by_plat[r["platform"] or "?"][r["verdict"]] += 1

    rows = con.execute("""
        SELECT p.post_id, p.platform, p.subreddit, p.title, p.score,
               p.num_comments, p.permalink,
               s.s_total, s.b_total, s.h_total, s.verdict
        FROM rd_scores s JOIN rd_posts p ON p.post_id = s.post_id
        ORDER BY (CASE WHEN s.s_total > s.b_total THEN s.s_total
                       ELSE s.b_total END) DESC,
                 s.h_total DESC, p.num_comments DESC
        LIMIT ?""", (args.top,)).fetchall()

    out = os.path.join(db.REPORTS, "T2_reddit_scores.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# T2 — the Reddit read queue\n\n")
        fh.write("Scores are a **mechanical proxy**, not a read. "
                 "`src/rubric.py` detects each component by pattern and stores "
                 "a verbatim quote under 15 words, which is the sibling "
                 "projects' hard rule — a component you cannot quote did not "
                 "happen. What it cannot do is tell sarcasm from praise or a "
                 "quoted claim from a claim.\n\n")
        fh.write("**Precision against a hand read: UNKNOWN.** No threads have "
                 "been read against it yet, so no precision figure is quoted. "
                 "`youtube-signal` recorded that both its G3 validation samples "
                 "had informed the lexicon's design, so its 85.9% is an upper "
                 "bound and not a holdout; this project starts by not claiming "
                 "a number at all.\n\n")
        fh.write("## Per-platform census\n\n")
        fh.write("A rate computed across platforms is an average of two "
                 "different things — a Reddit thread and a Mastodon post are "
                 "not the same object. Split, always.\n\n")
        keys = ["PASS", "DROP_G1_THIN", "DROP_G3_OFF_TOPIC", "BUILD_AND_RECOMMEND",
                "ABSORB_AND_RECOMMEND", "ABSORB", "ABSORB_RESULTS_DISCOUNTED",
                "SKIP"]
        fh.write("| platform | total | " + " | ".join(keys) + " |\n")
        fh.write("|---" * (len(keys) + 2) + "|\n")
        for plat, c in sorted(by_plat.items(),
                              key=lambda kv: -sum(kv[1][k] for k in
                                                  ("PASS", "DROP_G1_THIN",
                                                   "DROP_G3_OFF_TOPIC"))):
            tot = sum(c[k] for k in ("PASS", "DROP_G1_THIN", "DROP_G3_OFF_TOPIC"))
            fh.write(f"| **{plat}** | {tot:,} | "
                     + " | ".join(f"{c[k]:,}" for k in keys) + " |\n")
        fh.write("\n## The read queue\n\n")
        fh.write("| # | platform | where | S | B | H | verdict | replies | title |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            plat = r["platform"] or "reddit"
            link = (f"https://reddit.com{r['permalink']}" if plat == "reddit"
                    else (r["permalink"] or ""))
            where = (f"r/{r['subreddit']}" if plat == "reddit"
                     else str(r["subreddit"] or ""))
            fh.write(f"| {i} | {plat} | {where} | {r['s_total']} | "
                     f"{r['b_total']} | {r['h_total']} | {r['verdict']} | "
                     f"{r['num_comments']} | "
                     f"[{(r['title'] or '')[:70]}]({link}) |\n")
        fh.write("\n## Census\n\n| bucket | n |\n|---|---|\n")
        for k, n in census.most_common():
            fh.write(f"| {k} | {n} |\n")

        # Which components never fire is a statement about the instrument, and
        # both sibling projects report it. A component that never fires is
        # either impossible on this platform or broken.
        fired = collections.Counter()
        for r in con.execute("SELECT components FROM rd_scores"):
            for c in json.loads(r["components"]):
                fired[c["component"]] += 1
        fh.write("\n## Component firing rates — the instrument, audited\n\n")
        fh.write("| component | meaning | fired | of "
                 f"{scored} scored threads |\n|---|---|---|---|\n")
        for comp in list(rubric.S_WEIGHTS) + list(rubric.B_WEIGHTS) + \
                list(rubric.H_WEIGHTS):
            n = fired.get(comp, 0)
            fh.write(f"| {comp} | {rubric.MEANING[comp]} | {n} | "
                     f"{100*n/max(scored,1):.1f}% |\n")
        never = [c for c in rubric.MEANING if fired.get(c, 0) == 0]
        fh.write(f"\n**Never fired: {', '.join(never) if never else 'none'}.** "
                 "A component that never fires is either impossible on this "
                 "platform or broken, and the two are told apart by reading, "
                 "not by adjusting the pattern until it fires.\n")
    print(f"  wrote {out}")
    db.log(con, "reddit_score",
           f"scored={scored} " + " ".join(f"{k}={v}" for k, v in census.most_common()))
    con.close()


if __name__ == "__main__":
    main()
