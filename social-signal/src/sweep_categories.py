"""Sweep all three corpora for each Kalshi CATEGORY the factory listed.

**Mailbox 013:** *"You are looking for ideas per category, not ideas in general.
Somebody has traded each of these somewhere and written about it."*

**The constraint this tool is built around, measured 2026-08-20 and not
assumed.** My own ranking scorer is a keyword counter. `src/placebo_scorer.py`
shuffled every word in all 7,411 gated posts — keeping the exact vocabulary,
destroying every sentence — and **86.6% of the posts that scored above zero
still scored above zero.** A scorer reading meaning would collapse; this one
barely moved.

**So this tool RANKS, it does not CONCLUDE.** Its output is a reading queue per
category. Nothing here becomes a strategy spec until a human has read the
source, and every spec records which of the two it was.

Also measured, and it matters for anything shaped "they had a real sample":
**43.4% of denominator matches are time windows, not observations** — *"30
days"* is how long someone watched, not how many things they saw. **38.8% of
posts carrying any denominator have only a time window.**

    python src/sweep_categories.py
    python src/sweep_categories.py --category crypto --top 25
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
import db          # noqa: E402
import hunt_new    # noqa: E402

YT = r"C:\Users\vinig\trading\youtube-signal\data\signal.db"
YT2 = r"C:\Users\vinig\trading\youtube-signal\data\signal_kalshi_edge.db"
GH = r"C:\Users\vinig\trading\signal-github\data\github.db"

# One entry per Kalshi category the factory marked testable. Terms are
# deliberately narrow: a broad term matches everything and ranks nothing.
CATEGORIES = {
    "weather": r"\b(weather|temperature|rainfall|snowfall|noaa|forecast|"
               r"hurricane|heat index|degree days|nws|ecmwf)\b",
    "economics": r"\b(cpi|inflation|nonfarm|payroll|unemployment|fed funds|"
                 r"fomc|interest rate|gdp|jobless claims|rate cut|rate hike)\b",
    "politics": r"\b(election|primary|midterm|senate|congress|parliament|"
                r"approval rating|pollster|polling|nominee|electoral)\b",
    "crypto": r"\b(bitcoin|btc|ethereum|solana|altcoin|on-chain|stablecoin|"
              r"halving|funding rate|perpetual)\b",
    "entertainment": r"\b(box office|rotten tomatoes|oscar|grammy|emmy|"
                     r"billboard|spotify|netflix|award show)\b",
    "financials": r"\b(s&p|spx|nasdaq|dow jones|djia|vix|earnings|"
                  r"treasury yield|0dte)\b",
    "commodities": r"\b(crude|wti|brent|natural gas|gold price|silver price|"
                   r"wheat|corn|soybean|opec)\b",
    "mentions": r"\b(mention market|word count|press conference|"
                r"transcript market)\b",
    "companies": r"\b(ipo|earnings call|guidance|layoff|merger|acquisition|"
                 r"bankruptcy)\b",
    "sports": r"\b(nfl|nba|mlb|soccer|tennis|game total|moneyline|"
              r"spread bet|parlay|first inning)\b",
    "science_tech": r"\b(spacex|rocket launch|ai model|benchmark|"
                    r"clinical trial|fda approval)\b",
}
# A category hit only counts if the text also talks about TRADING it.
TRADING = re.compile(
    r"\b(market|kalshi|polymarket|contract|odds|price|traded|trading|"
    r"bet|position|edge|arbitrage|hedge|settle|resolve)\b", re.I)


def ro(path):
    if not os.path.exists(path):
        return None
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=120)
    c.row_factory = sqlite3.Row
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    pats = {k: re.compile(v, re.I) for k, v in CATEGORIES.items()
            if not args.category or k == args.category}
    hits = defaultdict(list)
    seen_src = defaultdict(lambda: defaultdict(int))

    def consider(cat, src, ident, text, title, extra=""):
        if not TRADING.search(text):
            return
        # **SPECIFICITY, not mention.** The first run of this sweep put "Learn
        # How Polymarket Works While Sleeping" at the top of weather, economics,
        # politics AND crypto -- one passing word each. That is the keyword
        # counter the placebo test exposed, showing up in its own output.
        # A source is about a category if the category is in its TITLE, or if
        # it comes back to it repeatedly. Once in passing is not aboutness.
        pat = pats[cat]
        in_title = bool(pat.search(title or ""))
        mentions = len(pat.findall(text))
        if not in_title and mentions < 3:
            return
        s, _parts, big = hunt_new.score(text)
        s += 4 if in_title else 0
        s += min(mentions, 6)
        if s <= 0:
            return
        hits[cat].append({"src": src, "id": ident, "score": s,
                          "denom": big, "title": title[:110],
                          "extra": extra + (" TITLE" if in_title else "")
                                   + f" x{mentions}"})
        seen_src[cat][src] += 1

    con = db.connect()
    for r in con.execute("SELECT post_id, platform, subreddit, title, "
                         "COALESCE(selftext,'') b FROM rd_posts "
                         "WHERE gate_status='PASS'"):
        text = f"{r['title']}\n{r['b']}"
        if len(text) < 300:
            continue
        for cat, pat in pats.items():
            if pat.search(text):
                consider(cat, r["platform"] or "reddit", r["post_id"], text,
                         r["title"] or "", "r/" + str(r["subreddit"]))
    con.close()

    for tag, path in (("youtube", YT), ("yt2", YT2)):
        c = ro(path)
        if not c:
            continue
        titles = {r["video_id"]: r["title"]
                  for r in c.execute("SELECT video_id,title FROM videos")}
        for r in c.execute("SELECT video_id, snippets_json FROM transcripts"):
            try:
                sn = json.loads(r["snippets_json"] or "[]")
            except Exception:  # noqa: BLE001
                continue
            text = " ".join(x.get("text", "") for x in sn)
            for cat, pat in pats.items():
                if pat.search(text):
                    consider(cat, tag, r["video_id"], text,
                             titles.get(r["video_id"], "") or "")
        c.close()

    c = ro(GH)
    if c:
        for r in c.execute("SELECT full_name, description, topics, stars, "
                           "submits_orders, has_backtest, s_total, gate "
                           "FROM repos"):
            text = " ".join(str(r[k] or "") for k in
                            ("full_name", "description", "topics"))
            for cat, pat in pats.items():
                if pat.search(text) and TRADING.search(text):
                    # a repo's whole description IS its title, so one mention
                    # there is aboutness in a way a passing word in an hour of
                    # transcript is not
                    s = ((4 if r["submits_orders"] else 0)
                         + (3 if r["has_backtest"] else 0)
                         + min(int(r["s_total"] or 0), 6)
                         + (2 if (r["stars"] or 0) >= 3 else 0)
                         + (2 if r["gate"] == "PASS" else 0))
                    flags = ("O" if r["submits_orders"] else "-") + \
                            ("B" if r["has_backtest"] else "-")
                    hits[cat].append({
                        "src": "github", "id": r["full_name"], "score": s,
                        "denom": str(r["stars"] or 0) + "*" + flags,
                        "title": (r["description"] or "")[:110], "extra": ""})
                    seen_src[cat]["github"] += 1
        c.close()

    out = os.path.join(db.REPORTS, "SWEEP_CATEGORIES.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# What the corpora hold, per Kalshi category\n\n")
        fh.write("**This is a READING QUEUE, not evidence.** The ranking "
                 "scorer was placebo-tested on 2026-08-20: shuffling every "
                 "word in all 7,411 gated posts left **86.6% of the "
                 "above-zero scores still above zero**. It counts keywords. "
                 "Nothing here becomes a spec until a human reads it.\n\n")
        fh.write("| category | total | reddit/mastodon | youtube | github |\n")
        fh.write("|---|---:|---:|---:|---:|\n")
        for cat in CATEGORIES:
            if cat not in hits:
                continue
            s = seen_src[cat]
            fh.write("| **" + cat + "** | " + str(len(hits[cat])) + " | "
                     + str(s.get("reddit", 0) + s.get("mastodon", 0)) + " | "
                     + str(s.get("youtube", 0) + s.get("yt2", 0)) + " | "
                     + str(s.get("github", 0)) + " |\n")
        for cat in CATEGORIES:
            if cat not in hits:
                continue
            fh.write("\n## " + cat + " — " + str(len(hits[cat])) + "\n\n")
            for h in sorted(hits[cat], key=lambda x: -x["score"])[:args.top]:
                fh.write("- `" + h["src"] + "` **" + str(h["score"]) + "** ["
                         + (h["denom"] or "—") + "] `" + str(h["id"]) + "` "
                         + h["extra"] + " — " + h["title"] + "\n")

    print(f"{'category':<16}{'total':>7}{'reddit':>9}{'youtube':>9}{'github':>8}")
    for cat in CATEGORIES:
        if cat not in hits:
            continue
        s = seen_src[cat]
        print(f"{cat:<16}{len(hits[cat]):>7}"
              f"{s.get('reddit',0)+s.get('mastodon',0):>9}"
              f"{s.get('youtube',0)+s.get('yt2',0):>9}{s.get('github',0):>8}")
    print("\n  wrote " + out)


if __name__ == "__main__":
    main()
