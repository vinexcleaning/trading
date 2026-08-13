"""Find baseball strategy candidates across ALL THREE corpora at once.

**The concrete customer:** the `mlb` chat is adding mentalities and has been told
to ask this session for candidates. This is the first job that reads Reddit,
YouTube and GitHub together rather than one at a time.

**Why all three, and why it is not just tidiness.** Each corpus fails in a
different direction, so agreement across them is worth far more than volume in
any one:

  REDDIT/MASTODON   opinions and results, mostly undated, easy to fake
  YOUTUBE           methods explained step by step, but sellers dominate
  GITHUB            code that either runs or does not, and cannot lie about
                    what it implements — but says nothing about whether it won

**A candidate named by two of the three is the shape worth an afternoon.** One
corpus alone is a lead, not evidence.

Everything is offline over local databases, so it costs nothing and works with
the network down.

    python src/hunt_baseball.py
    python src/hunt_baseball.py --top 40
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

YT = r"C:\Users\vinig\trading\youtube-signal\data\signal.db"
YT2 = r"C:\Users\vinig\trading\youtube-signal\data\signal_kalshi_edge.db"
GH = r"C:\Users\vinig\trading\signal-github\data\github.db"

# Baseball, tightly. "MLB" alone catches too much; require a baseball word.
BALL = re.compile(
    r"\b(mlb|baseball|statcast|retrosheet|pybaseball|savant|"
    r"first[- ]inning|nrfi|yrfi|run[- ]line|strikeout prop|"
    r"starting pitcher|bullpen|park factor|lineup card|"
    r"first 5 innings|f5\b|moneyline)\b", re.I)
# The mechanism words that make a mention a candidate rather than chatter.
MECH = re.compile(
    r"\b(edge|model|backtest|closing line|clv|fair value|de[- ]?vig|"
    r"arbitrage|market maker|hold|overround|kelly|prop|"
    r"weather|wind|umpire|travel|rest days|bullpen fatigue|"
    r"lineup|handedness|platoon|park factor|regress)\b", re.I)
DENOM = re.compile(
    r"\b(\d{2,3}(?:,\d{3})+|\d{2,7})\s*"
    r"(games?|bets?|trades?|matches|seasons?|markets?|samples?|"
    r"observations?|innings?|starts?|plate appearances?|pitches)\b", re.I)
SELLING = re.compile(r"\b(dm me|link in bio|my (picks|discord|course)|"
                     r"subscribe|promo|\$\d+/mo|per month)\b", re.I)
# **Tipster daily-pick posts, which flooded the first run and are worthless.**
# "POTD: 7.6.2026", "LOCKED IN DAY 29 OF BECOMING THE MOST PROFITABLE...",
# "Day 31: Flat four-trade day..." -- one account posting the same format every
# day. They carry numbers, so a denominator filter cannot see them; they have to
# be named. They are a record of one person's bets, not a testable claim.
TIPSTER = re.compile(
    r"(^|\n)\s*(potd|pod|play of the day|lock of the day)\b"
    r"|^\s*day\s*\d+\s*[:\-]"
    r"|\b(locked in|heater|\d+-\d+ run|today'?s (picks|plays|card))\b"
    r"|\b(picks|parlays)\b.{0,20}\bwriteup\b"
    r"|[\U0001F300-\U0001FAFF]{2,}", re.I)


def ro(path):
    if not os.path.exists(path):
        return None
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=120)
    c.row_factory = sqlite3.Row
    return c


def cols(con, table):
    try:
        return {r["name"] for r in con.execute(f"PRAGMA table_info('{table}')")}
    except Exception:  # noqa: BLE001
        return set()


def score(text):
    if TIPSTER.search(text[:400]):
        return -99, ""          # a daily-pick post is not a candidate
    d = DENOM.findall(text)
    s = 0
    s += min(len(d), 3) * 3
    s += 3 if MECH.search(text) else 0
    s -= 5 if SELLING.search(text) else 0
    big = ""
    if d:
        b = max(d, key=lambda t: int(t[0].replace(",", "")))
        big = f"{b[0]} {b[1]}"
    return s, big


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    hits = []          # (source, ident, score, denominator, snippet)
    per_source = defaultdict(int)

    # ---------- 1. Reddit + Mastodon ----------
    con = db.connect()
    for r in con.execute(
            "SELECT post_id, platform, subreddit, title, "
            "COALESCE(selftext,'') AS body, num_comments, permalink "
            "FROM rd_posts"):
        text = f"{r['title']}\n{r['body']}"
        if not BALL.search(text) or len(text) < 300:
            continue
        s, big = score(text)
        if s <= 0:
            continue
        per_source["reddit/mastodon"] += 1
        hits.append(("reddit", r["post_id"], s, big,
                     (r["title"] or "")[:96], r["subreddit"],
                     r["num_comments"] or 0))
    for r in con.execute("SELECT comment_id, post_id, body FROM rd_comments"):
        text = r["body"] or ""
        if not BALL.search(text) or len(text) < 300:
            continue
        s, big = score(text)
        if s <= 2:
            continue
        per_source["reddit comments"] += 1
        hits.append(("rd-comment", r["comment_id"], s, big,
                     " ".join(text.split())[:96], r["post_id"], 0))
    con.close()

    # ---------- 2. YouTube transcripts, both databases ----------
    # **There is no text column.** Transcripts are stored as `snippets_json`,
    # a list of {"start","duration","text"} from the timed-caption API. The
    # first run of this script reported "no text column" and skipped 1,135
    # transcripts already sitting on disk — a corpus is not untouched just
    # because the obvious column name is missing.
    for tag, path in (("youtube", YT), ("yt-kalshi", YT2)):
        c = ro(path)
        if not c:
            continue
        titles = {r["video_id"]: r["title"]
                  for r in c.execute("SELECT video_id, title FROM videos")}
        for r in c.execute("SELECT video_id, snippets_json FROM transcripts"):
            try:
                snips = json.loads(r["snippets_json"] or "[]")
            except Exception:  # noqa: BLE001
                continue
            text = " ".join(s.get("text", "") for s in snips)
            if not BALL.search(text):
                continue
            s_, big = score(text)
            if s_ <= 0:
                continue
            per_source[tag] += 1
            # keep the sentence around the first baseball word, not the opening
            m = BALL.search(text)
            lo = max(0, m.start() - 90)
            hits.append((tag, r["video_id"], s_, big,
                         (titles.get(r["video_id"]) or
                          " ".join(text[lo:m.end() + 90].split()))[:96], "", 0))
        c.close()

    # ---------- 3. GitHub repos ----------
    # This corpus was collected with prediction-market queries, so it holds
    # almost no baseball MODELLING. What it does hold is baseball repos that
    # trade a prediction market, which is the more useful thing anyway — and
    # unlike a Reddit post, `submits_orders` and `has_backtest` are properties
    # of the code, not claims about it.
    c = ro(GH)
    if c:
        for r in c.execute(
                "SELECT full_name, description, topics, stars, language, "
                "pushed_at, submits_orders, has_backtest, has_live_trading, "
                "s_total, gate, venue_detected, kind FROM repos"):
            text = " ".join(str(r[k] or "") for k in
                            ("full_name", "description", "topics"))
            if not BALL.search(text):
                continue
            s = 0
            s += 4 if r["submits_orders"] else 0
            s += 3 if r["has_backtest"] else 0
            s += min(int(r["s_total"] or 0), 6)
            s += 2 if (r["stars"] or 0) >= 3 else 0
            s += 2 if r["gate"] == "PASS" else 0
            per_source["github"] += 1
            flags = "".join(("O" if r["submits_orders"] else "-",
                             "B" if r["has_backtest"] else "-",
                             "L" if r["has_live_trading"] else "-"))
            hits.append(("github", r["full_name"], s,
                         f"{r['stars'] or 0}* {flags}",
                         " ".join(str(r["description"] or "").split())[:96],
                         str(r["pushed_at"] or "")[:10], r["stars"] or 0))
        c.close()

    hits.sort(key=lambda t: (-t[2], -t[6]))
    print(f"\nbaseball-and-mechanism hits per corpus:")
    for k, v in sorted(per_source.items(), key=lambda t: -t[1]):
        print(f"  {k:<18} {v:>6}")
    print(f"  {'TOTAL':<18} {len(hits):>6}\n")

    out = os.path.join(db.REPORTS, "HUNT_BASEBALL.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Baseball strategy candidates, across all three corpora\n\n")
        fh.write("Each corpus fails in a different direction — Reddit carries "
                 "opinion, YouTube carries method but is full of sellers, "
                 "GitHub carries code that cannot lie about what it implements "
                 "but says nothing about whether it won. **A candidate named "
                 "by two of the three is worth an afternoon; one alone is a "
                 "lead.**\n\n")
        for k, v in sorted(per_source.items(), key=lambda t: -t[1]):
            fh.write(f"- `{k}` — {v} hits\n")
        fh.write("\n| # | corpus | score | biggest count | what |\n")
        fh.write("|---|---|---|---|---|\n")
        for i, (src, ident, s, big, snip, extra, _n) in enumerate(
                hits[:args.top], 1):
            fh.write(f"| {i} | {src} | {s} | {big or '—'} | "
                     f"`{ident}` {snip} |\n")
    for i, (src, ident, s, big, snip, extra, n) in enumerate(hits[:args.top], 1):
        print(f"{i:>3}. [{s:>2}] {src:<11} {big or '—':<18} {snip[:70]}")
        print(f"      {ident}  {extra}")
    print(f"\n  wrote {out}")
    db.log(db.connect(), "hunt_baseball", f"hits={len(hits)}")


if __name__ == "__main__":
    main()
