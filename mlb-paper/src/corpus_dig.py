"""Read-only dig through the three extractor corpora for BASEBALL-specific
trading behaviour.

Nothing here fetches. It reads:
  social-signal/data/social.db      Reddit posts + comments, scored
  signal-github/data/github.db      4,017 repos, classified
  youtube-signal/data/*.db          read videos, claims

The question is narrow and deliberately not "is there an edge": it is
*what do people who actually trade baseball markets say they look at.*
That is an input to hypothesis selection, not evidence for a hypothesis.

    python src/corpus_dig.py            # everything
    python src/corpus_dig.py --posts    # full text of the MLB threads
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import textwrap
from pathlib import Path

TRADING = Path(r"C:\Users\vinig\trading")
DBS = {
    "reddit": TRADING / "social-signal" / "data" / "social.db",
    "github": TRADING / "signal-github" / "data" / "github.db",
    "yt": TRADING / "youtube-signal" / "data" / "signal.db",
    "yt_kalshi": TRADING / "youtube-signal" / "data" / "signal_kalshi_edge.db",
}

# Baseball vocabulary. Deliberately wide: the point is recall, and every hit is
# read by a human (me) rather than counted.
TERMS = [
    "mlb", "baseball", "pitcher", "starter", "bullpen", "reliever", "lineup",
    "nrfi", "yrfi", "first inning", "run line", "over/under", "totals",
    "park factor", "coors", "wrigley", "umpire", "statcast", "era", "whip",
    "innings", "yankees", "dodgers", "opener", "rotation", "day game",
    "doubleheader", "bat", "hitter", "batting order",
]

W = 100


def _p(s=""):
    print(s)


def _wrap(s, indent=6):
    return textwrap.fill(" ".join(str(s).split()), width=W,
                         initial_indent=" " * indent,
                         subsequent_indent=" " * indent)


def ro(key):
    p = DBS[key]
    if not p.exists():
        return None
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def safe(con, sql, args=()):
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error as e:
        print(f"  ! {e}", file=sys.stderr)
        return []


def _clean(s):
    if not s:
        return ""
    return re.sub(r"[^\x20-\x7e\n]", "", str(s))


# --------------------------------------------------------------------- reddit

def reddit_threads(full=False):
    con = ro("reddit")
    if con is None:
        _p("  social.db missing")
        return
    like = " OR ".join(["lower(p.title) LIKE ?"] * len(TERMS))
    like2 = " OR ".join(["lower(p.selftext) LIKE ?"] * len(TERMS))
    args = [f"%{t}%" for t in TERMS] * 2
    rows = safe(con,
                "SELECT p.post_id, p.subreddit, p.title, p.selftext, p.score, "
                "       p.num_comments, p.permalink, s.s_total, s.b_total, "
                "       s.h_total, s.verdict "
                "FROM rd_posts p LEFT JOIN rd_scores s ON s.post_id = p.post_id "
                f"WHERE ({like}) OR ({like2}) "
                "ORDER BY COALESCE(s.s_total,-99) DESC, p.num_comments DESC",
                tuple(args))
    _p(f"\n=== REDDIT: {len(rows)} posts mention baseball vocabulary ===\n")
    for r in rows[:40 if not full else 25]:
        _p(f"[{r['subreddit']}] S={r['s_total']} B={r['b_total']} H={r['h_total']} "
           f"{r['verdict']} · {r['score']}pts {r['num_comments']}c")
        _p(f"  {_clean(r['title'])[:110]}")
        _p(f"  reddit.com{r['permalink']}")
        if full:
            body = _clean(r["selftext"])[:2400]
            if body.strip():
                _p(_wrap(body, 4))
            cm = safe(con,
                      "SELECT body, score FROM rd_comments WHERE post_id = ? "
                      "ORDER BY score DESC LIMIT 12", (r["post_id"],))
            for c in cm:
                b = _clean(c["body"])
                if len(b) < 60:
                    continue
                _p(_wrap(f"[{c['score']}pts] {b[:900]}", 6))
        _p()
    con.close()


def reddit_comment_grep():
    """Comments are where the actual reasoning lives; titles are advertising."""
    con = ro("reddit")
    if con is None:
        return
    _p("\n=== REDDIT COMMENTS containing baseball reasoning ===\n")
    seen = set()
    for t in ["pitcher", "bullpen", "nrfi", "run line", "park factor",
              "umpire", "lineup", "starter", "mlb", "baseball", "innings"]:
        rows = safe(con,
                    "SELECT c.body, c.score, p.title, p.subreddit, p.permalink "
                    "FROM rd_comments c JOIN rd_posts p ON p.post_id = c.post_id "
                    "WHERE lower(c.body) LIKE ? AND length(c.body) > 200 "
                    "ORDER BY c.score DESC LIMIT 8", (f"%{t}%",))
        for r in rows:
            k = r["body"][:120]
            if k in seen:
                continue
            seen.add(k)
            _p(f"-- [{t}] r/{r['subreddit']} {r['score']}pts · "
               f"{_clean(r['title'])[:70]}")
            _p(_wrap(_clean(r["body"])[:1400], 4))
            _p()
    con.close()


# --------------------------------------------------------------------- github

def github_repos():
    con = ro("github")
    if con is None:
        _p("  github.db missing")
        return
    cols = {r[1] for r in safe(con, "PRAGMA table_info(repos)")}
    want = [c for c in ("full_name", "stars", "commits", "is_archived",
                        "pushed_at", "s_adj", "kind", "venue_detected",
                        "submits_orders", "trust_me_bro", "description",
                        "what_it_does", "readme") if c in cols]
    sel = ", ".join(want)
    like = " OR ".join(
        ["lower(full_name) LIKE ?", "lower(description) LIKE ?"]
        + (["lower(what_it_does) LIKE ?"] if "what_it_does" in cols else []))
    per = 2 + (1 if "what_it_does" in cols else 0)
    terms = ["mlb", "baseball", "nrfi", "yrfi", "first inning", "run line",
             "statcast", "pitcher", "sabermetric", "pybaseball", "retrosheet"]
    args = []
    for t in terms:
        args += [f"%{t}%"] * per
    where = " OR ".join([f"({like})"] * len(terms))
    rows = safe(con, f"SELECT {sel} FROM repos WHERE {where} "
                     "ORDER BY COALESCE(s_adj,-99) DESC", tuple(args))
    _p(f"\n=== GITHUB: {len(rows)} repos mention baseball ===\n")
    for r in rows[:40]:
        k = r.keys()
        _p(f"s_adj={r['s_adj'] if 's_adj' in k else '?'} "
           f"{'ARCHIVED' if ('is_archived' in k and r['is_archived']) else 'alive'} "
           f"{r['commits'] if 'commits' in k else '?'}c "
           f"{r['stars'] if 'stars' in k else '?'}* "
           f"{'ORDERS ' if ('submits_orders' in k and r['submits_orders']) else ''}"
           f"{'TRUST-ME-BRO ' if ('trust_me_bro' in k and r['trust_me_bro']) else ''}"
           f"{r['full_name']}")
        for f in ("description", "what_it_does"):
            if f in k and r[f]:
                _p(_wrap(_clean(r[f])[:400], 4))
    con.close()


# ------------------------------------------------------------------- youtube

def yt_claims():
    for key in ("yt", "yt_kalshi"):
        con = ro(key)
        if con is None:
            continue
        terms = ["mlb", "baseball", "pitcher", "nrfi", "inning", "sports book",
                 "sportsbook", "closing line", "clv", "de-vig", "devig",
                 "pinnacle", "sharp"]
        like = " OR ".join(["lower(c.claim_text) LIKE ?"] * len(terms))
        rows = safe(con,
                    "SELECT c.video_id, c.claim_type, c.claim_text, c.stated_n, "
                    "       v.title, v.channel_name, s.s_total, s.h_total "
                    "FROM claims c JOIN videos v ON v.video_id=c.video_id "
                    "LEFT JOIN scores s ON s.video_id=c.video_id "
                    f"WHERE {like} ORDER BY (c.claim_type='result') DESC",
                    tuple(f"%{t}%" for t in terms))
        _p(f"\n=== YOUTUBE [{key}]: {len(rows)} claims ===\n")
        for r in rows[:30]:
            _p(f"[{r['claim_type']} n={r['stated_n']}] {r['channel_name']} "
               f"S={r['s_total']} H={r['h_total']}")
            _p(_wrap(_clean(r["claim_text"])[:600], 4))
            _p()
        con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", action="store_true")
    ap.add_argument("--comments", action="store_true")
    ap.add_argument("--github", action="store_true")
    ap.add_argument("--yt", action="store_true")
    a = ap.parse_args()
    any_ = a.posts or a.comments or a.github or a.yt
    if a.posts or not any_:
        reddit_threads(full=a.posts)
    if a.comments or not any_:
        reddit_comment_grep()
    if a.github or not any_:
        github_repos()
    if a.yt or not any_:
        yt_claims()


if __name__ == "__main__":
    main()
