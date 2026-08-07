"""Narrow pass: only unambiguous baseball vocabulary, and read the bodies.

corpus_dig.py's wide net matched 9,005 Reddit posts because "era", "bat" and
"opener" are substrings of ordinary English. That is recall without precision.
This pass uses word-boundary regex in Python rather than SQL LIKE, and prints
the post body and its top comments, because the reasoning lives in the bodies.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import textwrap
from pathlib import Path

TRADING = Path(__file__).resolve().parents[2]
SOCIAL = TRADING / "social-signal" / "data" / "social.db"
GITHUB = TRADING / "signal-github" / "data" / "github.db"

# word-boundary patterns, unambiguous in a betting context
RX = re.compile(
    r"\b(mlb|baseball|nrfi|yrfi|first[- ]inning|run ?line|starting pitcher|"
    r"starter'?s?\b|bullpen|reliever|batting order|lineup card|park factor|"
    r"coors|wrigley|umpire|statcast|pybaseball|retrosheet|"
    r"yankees|dodgers|astros|mets|braves|phillies|orioles|guardians|"
    r"innings? (pitched|total)|f5\b|first five)\b", re.I)

W = 100


def clean(s):
    return re.sub(r"[^\x20-\x7e\n]", "", str(s or ""))


def wrap(s, i=4):
    return textwrap.fill(" ".join(clean(s).split()), width=W,
                         initial_indent=" " * i, subsequent_indent=" " * i)


def ro(p):
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def posts(limit, min_hits):
    con = ro(SOCIAL)
    rows = con.execute(
        "SELECT p.post_id, p.subreddit, p.title, p.selftext, p.score, "
        "       p.num_comments, p.permalink, s.s_total, s.b_total, s.h_total, "
        "       s.verdict "
        "FROM rd_posts p LEFT JOIN rd_scores s ON s.post_id=p.post_id"
    ).fetchall()
    scored = []
    for r in rows:
        blob = f"{r['title']}\n{r['selftext'] or ''}"
        hits = len(RX.findall(blob))
        if hits >= min_hits:
            scored.append((hits, r))
    scored.sort(key=lambda x: (-(x[1]["s_total"] or -99), -x[0]))
    print(f"\n=== {len(scored)} posts with >= {min_hits} baseball terms "
          f"(word-boundary) ===\n")
    for hits, r in scored[:limit]:
        print(f"[r/{r['subreddit']}] S={r['s_total']} B={r['b_total']} "
              f"H={r['h_total']} {r['verdict']} · {r['score']}pts "
              f"{r['num_comments']}c · {hits} bb-terms")
        print(f"  {clean(r['title'])[:110]}")
        print(f"  reddit.com{r['permalink']}")
        body = clean(r["selftext"]).strip()
        if body:
            print(wrap(body[:3000], 4))
        cm = con.execute(
            "SELECT body, score FROM rd_comments WHERE post_id=? "
            "ORDER BY score DESC LIMIT 15", (r["post_id"],)).fetchall()
        for c in cm:
            b = clean(c["body"]).strip()
            if len(b) < 120:
                continue
            if not RX.search(b) and c["score"] < 3:
                continue
            print(wrap(f"> [{c['score']}pts] {b[:1200]}", 6))
        print()
    con.close()


def repo_readme(name):
    con = ro(GITHUB)
    cols = {r[1] for r in con.execute("PRAGMA table_info(repos)")}
    text_cols = [c for c in ("readme", "readme_text", "what_it_does",
                             "description", "evidence", "notes")
                 if c in cols]
    row = con.execute(
        f"SELECT full_name, {', '.join(text_cols)} FROM repos "
        "WHERE full_name LIKE ?", (f"%{name}%",)).fetchone()
    if not row:
        print(f"  no repo matching {name}")
        return
    print(f"\n=== {row['full_name']} ===")
    for c in text_cols:
        if row[c]:
            print(f"\n-- {c}")
            print(wrap(str(row[c])[:6000], 2))
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--min-hits", type=int, default=3)
    ap.add_argument("--repo")
    a = ap.parse_args()
    if a.repo:
        repo_readme(a.repo)
    else:
        posts(a.limit, a.min_hits)
