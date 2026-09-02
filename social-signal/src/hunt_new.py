"""Hunt for strategies and data sources this programme has NEVER tried.

**A change of emphasis, on the user's instruction:** *"You're using it right now
mainly just to test stuff that we already know. Use it to find huge strategies.
Use it to find more stuff."*

He is right about what was happening. The stop-loss reconciliation and the
between-candles finding were both good and both were **defence** — checks on
things already believed. This ranks for **attack**.

**The ranking, and why it is not "find me a contradiction".** A queue that hunts
for disagreement will find disagreement whether or not it is there, and this
project's own lexicon already cannot tell a claim from a quoted claim. So the
score is built from two things a rigorous post has and a loud one does not:

  DENOMINATOR   a count attached to a unit — "4,604 markets", "16,024 trades",
                "180 round trips". This is the single strongest filter found so
                far: both items that corrected a rule had one.
  COST SIDE     fees, spread, slippage, vig. Someone who mentions what it costs
                has usually tried it for real.

and two that mark novelty rather than rehearsal:

  NEW VENUE     a market or instrument outside this repo's recorded work
  DATA SOURCE   names a feed, dump, archive or API — he asked explicitly for
                data, and a free feed nobody here knows about outranks most
                strategies

Posts already read are excluded. Everything is offline over the local corpus,
so this costs nothing and can be re-run with different weights.

    python src/hunt_new.py --top 25
    python src/hunt_new.py --top 25 --require-data
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

# A number bound to a unit. Bare numbers are worthless — "up 400%" is not a
# denominator, "400 trades" is.
# **Observation units and TIME units are now separate. Corrected 2026-09-01.**
# `placebo_scorer.py` measured what lumping them together cost: of 987 matches
# in the corpus, **428 (43.4%) were time windows rather than observations**, and
# 199 posts — 38.8% of those carrying any denominator — had nothing but a time
# window. **"30 days" is how long someone watched; "30 trades" is how many
# things he saw.** Only the second is a sample size and only the second should
# score as one. Flagged by the `reopen` audit as item 10.
OBS_UNITS = (r"trades?|bets?|markets?|matches|games|samples?|observations?|"
             r"contracts?|fills?|events?|round[- ]trips?")
TIME_UNITS = r"days?|weeks?|months?|years?|windows?|sessions?"
DENOM = re.compile(
    r"\b(\d{2,3}(?:,\d{3})+|\d{2,7})\s*(" + OBS_UNITS + r")\b", re.I)
# Kept separately so a time window can still be REPORTED as context. It is a
# fact about the study, just not a sample size.
DENOM_TIME = re.compile(
    r"\b(\d{2,3}(?:,\d{3})+|\d{2,7})\s*(" + TIME_UNITS + r")\b", re.I)
COST = re.compile(r"\b(fees?|spread|slippage|commission|vig|juice|rake|"
                  r"break[- ]?even|transaction cost|gas)\b", re.I)
# Venues and instruments this repo has NOT worked on. Kalshi, Polymarket and
# the 15-minute crypto market are deliberately absent — those are rehearsal.
NEW_VENUE = re.compile(
    r"\b(betfair|smarkets|matchbook|pinnacle|prophet ?x|novig|sporttrade|"
    r"railbird|drift|hyperliquid|deribit|manifold|metaculus|insight ?prediction|"
    r"limitless|myriad|azuro|thales|overtime ?markets|sx ?bet|betdex)\b", re.I)
DATA_SRC = re.compile(
    r"\b(dataset|data ?dump|archive|parquet|s3 bucket|open ?data|api|feed|"
    r"csv|historical data|tick data|order ?book data|scraper|hugging ?face|"
    r"kaggle|academic torrent)\b", re.I)
# Words that mark somebody showing their working rather than asserting.
WORKING = re.compile(r"\b(github\.com|repo|notebook|colab|methodology|"
                     r"out[- ]of[- ]sample|walk[- ]?forward|holdout|"
                     r"here'?s the (code|data)|reproduc)\b", re.I)
SELLING = re.compile(r"\b(dm me|join (my|the) (discord|group)|link in bio|"
                     r"my (course|signals|picks)|subscribe|promo code|"
                     r"limited (spots|time))\b", re.I)


def score(text: str):
    d = DENOM.findall(text)
    parts = {
        "denominator": min(len(d), 4) * 3,
        "cost_side": 3 if COST.search(text) else 0,
        "new_venue": 4 if NEW_VENUE.search(text) else 0,
        "data_source": 3 if DATA_SRC.search(text) else 0,
        "shows_working": 2 if WORKING.search(text) else 0,
        "selling": -5 if SELLING.search(text) else 0,
    }
    biggest = ""
    if d:
        biggest = max(d, key=lambda t: int(t[0].replace(",", "")))
        biggest = f"{biggest[0]} {biggest[1]}"
    return sum(parts.values()), parts, biggest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--require-data", action="store_true",
                    help="only items naming a feed, dump, archive or API")
    ap.add_argument("--min-len", type=int, default=400)
    args = ap.parse_args()

    con = db.connect()
    read = {r["post_id"] for r in con.execute("SELECT post_id FROM sc_readings")}
    rows = con.execute("""
        SELECT p.post_id, p.platform, p.subreddit, p.title, p.selftext,
               p.score, p.num_comments, p.permalink
        FROM rd_posts p JOIN rd_scores s ON s.post_id = p.post_id
        WHERE p.gate_status = 'PASS'""").fetchall()

    cand = []
    for r in rows:
        if r["post_id"] in read:
            continue
        body = f"{r['title']}\n{r['selftext'] or ''}"
        if len(body) < args.min_len:
            continue
        sc, parts, biggest = score(body)
        if args.require_data and not parts["data_source"]:
            continue
        if sc <= 0:
            continue
        cand.append((sc, parts, biggest, r))
    cand.sort(key=lambda t: (-t[0], -(t[3]["num_comments"] or 0)))

    print(f"{len(rows)} scored posts, {len(read)} already read, "
          f"{len(cand)} candidates\n")
    out = os.path.join(db.REPORTS, "HUNT_NEW.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Hunting for what we have never tried\n\n")
        fh.write("Ranked by **denominator + cost side + new venue + data "
                 "source**, minus selling language. Not by 'contradicts "
                 "something we hold' — a queue that hunts for disagreement "
                 "finds it whether or not it is there.\n\n")
        fh.write(f"{len(cand)} candidates from {len(rows)} scored posts, "
                 f"excluding {len(read)} already read.\n\n")
        fh.write("| # | score | biggest denominator | why it ranked | title |\n")
        fh.write("|---|---|---|---|---|\n")
        for i, (sc, parts, big, r) in enumerate(cand[:args.top], 1):
            why = " ".join(k for k, v in parts.items() if v > 0)
            link = (f"https://reddit.com{r['permalink']}"
                    if (r["platform"] or "reddit") == "reddit"
                    else (r["permalink"] or ""))
            fh.write(f"| {i} | {sc} | {big or '—'} | {why} | "
                     f"[{(r['title'] or '')[:66]}]({link}) |\n")
            print(f"{i:>3}. [{sc:>2}] {big or '—':<22} {(r['title'] or '')[:74]}")
            print(f"      {r['post_id']}  r/{r['subreddit']}  "
                  f"{r['num_comments']} replies  ({why})")
    print(f"\n  wrote {out}")
    db.log(con, "hunt_new", f"candidates={len(cand)} read={len(read)}")
    con.close()


if __name__ == "__main__":
    main()
