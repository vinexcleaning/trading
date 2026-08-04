"""T5 — the unified tool reputation table, and the fourth bucket.

Everything above this file produces evidence. This file produces the two things
the user actually reads:

**1. One row per tool, every platform in one place.** YouTube's promotion and
its promoter's honesty score, GitHub's liveness and fee correctness, whether any
of 3,000 whole-repo source archives references it, whether its URL answers when
fetched, and what a room of critics says. Sorted by how much it should change
what he does, not alphabetically.

**2. The fourth bucket, which only exists once the join exists: sources whose
promoted tools have already been shown to be bad somewhere else.** A creator can
be substantive, honest about their own results, and still be routing viewers to
a dead library or an unverifiable product. Single-platform scoring cannot see
that; it is invisible until the reputation table is built, and it is the thing
that stops money being wasted.

    python src/unified_table.py
"""
from __future__ import annotations

import argparse
import collections
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

TRADING = os.path.dirname(db.ROOT)
YT_DBS = [
    ("yt_broad", os.path.join(TRADING, "youtube-signal", "data", "signal.db")),
    ("yt_kalshi_edge", os.path.join(TRADING, "youtube-signal", "data",
                                    "signal_kalshi_edge.db")),
]

ORDER = {"CONTRADICTION": 0, "AGREE_NEGATIVE": 1, "UNDISCLOSED": 2,
         "SINGLE_SOURCE": 3, "AGREE_POSITIVE": 4, "NOT_SOFTWARE": 5}

# Verdicts that make a promotion worth flagging back to its promoter.
BAD = {"CONTRADICTION", "AGREE_NEGATIVE"}
UNVERIFIED = {"UNDISCLOSED"}


def cell(obs, platform, stances=None, join=" "):
    sel = [o for o in obs if o["platform"] == platform
           and (stances is None or o["stance"] in stances)]
    if not sel:
        return "—"
    return join.join(f"{o['stance']}" + (f"×{int(o['strength'])}"
                                         if o["strength"] and o["strength"] > 1
                                         else "")
                     for o in sel)


def video_titles():
    """video_id -> (title, channel, S, B, H, verdict) across both corpora."""
    out = {}
    for corpus, path in YT_DBS:
        if not os.path.exists(path):
            continue
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        for r in con.execute("""
                SELECT v.video_id, v.title, v.channel_name, v.view_count,
                       s.s_total, s.b_total, s.h_total, s.verdict
                FROM videos v LEFT JOIN scores s ON s.video_id = v.video_id"""):
            out[r["video_id"]] = dict(r, corpus=corpus)
        con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    con = db.connect()
    now = datetime.datetime.now(datetime.timezone.utc)
    vids = video_titles()

    rows = con.execute("""
        SELECT e.*, v.verdict, v.reason, v.n_platforms
        FROM entities e JOIN verdicts v ON v.entity_id = e.entity_id""").fetchall()
    obs_by = collections.defaultdict(list)
    for o in con.execute("SELECT * FROM observations"):
        obs_by[o["entity_id"]].append(o)

    rows = sorted(rows, key=lambda r: (ORDER.get(r["verdict"], 9),
                                       r["display"].lower()))
    counts = collections.Counter(r["verdict"] for r in rows)

    out = args.out or os.path.join(db.REPORTS, "TOOL_REPUTATION.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Unified tool reputation — every platform in one table\n\n")
        fh.write(f"Built {now:%Y-%m-%d} UTC from `social-signal/data/social.db`. "
                 "Sources: `youtube-signal` (2 corpora), `signal-github` "
                 "(repos + whole-repo source archives), the Arctic Shift Reddit "
                 "archive, and a live fetch of every URL any of them recorded.\n\n")
        fh.write("Read the verdict column first. `NO_FOOTPRINT` on the Reddit "
                 "column is **not** a clean bill of health — it is absence of "
                 "evidence, and it is stored separately from a positive for "
                 "exactly that reason.\n\n")

        fh.write("| verdict | n | what it means |\n|---|---|---|\n")
        MEANS = {
            "CONTRADICTION": "one source promotes it, another shows it dead, "
                             "broken, flagged or criticised",
            "AGREE_NEGATIVE": "every source with an opinion is negative",
            "UNDISCLOSED": "promoted with an incentive, corroborated by nobody "
                           "independent",
            "SINGLE_SOURCE": "exactly one platform has ever mentioned it",
            "AGREE_POSITIVE": "promoted somewhere and independently "
                              "corroborated, nothing against",
            "NOT_SOFTWARE": "an exchange, an institution or an idea",
        }
        for k in sorted(counts, key=lambda k: ORDER.get(k, 9)):
            fh.write(f"| **{k}** | {counts[k]} | {MEANS.get(k,'')} |\n")
        fh.write("\n---\n\n## The table\n\n")
        fh.write("| tool | verdict | YouTube | GitHub | in 3k repo sources | "
                 "live fetch | Reddit |\n|---|---|---|---|---|---|---|\n")
        for r in rows:
            if r["verdict"] == "NOT_SOFTWARE":
                continue
            o = obs_by[r["entity_id"]]
            fh.write(f"| {r['display'][:52]} | **{r['verdict']}** | "
                     f"{cell(o, 'youtube')} | {cell(o, 'github')} | "
                     f"{cell(o, 'github_corpus')} | {cell(o, 'live')} | "
                     f"{cell(o, 'reddit')} |\n")

        # ------------------------------------------------------------------
        # The fourth bucket
        # ------------------------------------------------------------------
        fh.write("\n---\n\n## The fourth bucket — sources that promoted "
                 "something already shown bad elsewhere\n\n")
        fh.write("This section cannot be produced by any single platform. It is "
                 "the whole reason the join exists: a creator can be "
                 "substantive, honest about their own results, and still be "
                 "routing viewers to a dead library or an unverifiable "
                 "product.\n\n")
        promoters = collections.defaultdict(list)
        for r in rows:
            if r["verdict"] not in BAD | UNVERIFIED:
                continue
            for o in obs_by[r["entity_id"]]:
                if o["platform"] != "youtube" or not o["source_id"]:
                    continue
                promoters[o["source_id"]].append((r["display"], r["verdict"],
                                                  o["stance"]))
        ranked = sorted(promoters.items(),
                        key=lambda kv: (-sum(1 for x in kv[1] if x[1] in BAD),
                                        -len(kv[1])))
        fh.write("| source | channel | its own S/B/H | promoted | verdict |\n")
        fh.write("|---|---|---|---|---|\n")
        for vid, items in ranked:
            v = vids.get(vid, {})
            sbh = (f"S={v.get('s_total')} B={v.get('b_total')} "
                   f"H={v.get('h_total')}" if v.get("s_total") is not None
                   else "not scored")
            for i, (tool, verdict, stance) in enumerate(items):
                title = (v.get("title") or vid)[:60] if i == 0 else ""
                chan = (v.get("channel_name") or "") if i == 0 else ""
                fh.write(f"| {title} | {chan} | {sbh if i == 0 else ''} | "
                         f"{tool[:44]} | **{verdict}** |\n")
        fh.write("\n**How to read this.** A row is not an accusation of bad "
                 "faith. A `CONTRADICTION` is usually a video that was correct "
                 "when it was filmed — the archetype in this corpus is a "
                 "well-taught Polymarket tutorial teaching a client library the "
                 "venue archived three months later. Nothing in it is wrong and "
                 "following it today produces a bot that cannot sign an order. "
                 "An `UNDISCLOSED` row is weaker still: it means nobody "
                 "independent has corroborated the product, which is a "
                 "statement about the evidence available, not about the "
                 "product.\n")

        # ------------------------------------------------------------------
        # Coverage, stated rather than implied
        # ------------------------------------------------------------------
        fh.write("\n---\n\n## Coverage — what this table does NOT cover\n\n")
        n_no_url = sum(1 for r in rows
                       if not r["canonical_url"] and not r["github_repo"])
        n_reddit = len({o["entity_id"] for o in con.execute(
            "SELECT entity_id FROM observations WHERE platform='reddit' "
            "AND stance != 'NO_FOOTPRINT'")})
        n_posts = con.execute("SELECT COUNT(*) c FROM rd_posts").fetchone()["c"]
        n_comm = con.execute("SELECT COUNT(*) c FROM rd_comments").fetchone()["c"]
        fh.write("| | |\n|---|---|\n")
        fh.write(f"| entities in the table | {len(rows)} |\n")
        fh.write(f"| **carry no URL of any kind** | **{n_no_url}** — cannot be "
                 "verified by fetching; this is a gap in `youtube-signal`'s "
                 "extraction, which records a URL only when one is spoken or "
                 "shown |\n")
        fh.write(f"| have a Reddit footprint | {n_reddit} |\n")
        fh.write(f"| Reddit corpus | {n_posts} posts, {n_comm} comments |\n")
        fh.write("\nThe YouTube corpora are a **snapshot**: a sibling session "
                 "was actively reading and scoring videos while this join ran, "
                 "so the tool count grew mid-run (10 -> 19 -> 25 in one corpus). "
                 "Re-run `join_corpora.py` to refresh; it is idempotent.\n")

    print(f"  wrote {out}")
    for k in sorted(counts, key=lambda k: ORDER.get(k, 9)):
        print(f"    {k:<16} {counts[k]}")
    print(f"    fourth bucket: {len(promoters)} sources")
    db.log(con, "unified_table",
           " ".join(f"{k}={v}" for k, v in counts.most_common())
           + f" promoters={len(promoters)}")
    con.close()


if __name__ == "__main__":
    main()
