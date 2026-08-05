"""TASK 4 - one command that answers a question from every corpus at once.

The extractors currently run as separate sessions doing undirected search. That
is the expensive way to use them and it is the wrong shape for the question a
trading session actually has, which is always some form of

    "has anyone already done this, and what happened?"

asked in the middle of something else. This is that lookup. It is READ-ONLY,
OFFLINE, and finishes in seconds, because the corpora are already on disk:

    38 read videos - 484 claims, 112 tools, 36 methods
    4,017 repos - 3,165 scored, 2,882 live, classified by venue and kind
    39,629 Reddit posts, 12,846 comments, 4,432 scored
    240 entities with cross-platform reputation verdicts

    python src/ask.py "kalshi market maker"
    python src/ask.py --tested "5 minute bitcoin"
    python src/ask.py --backtester kalshi
    python src/ask.py --datasources
    python src/ask.py --tool py-clob-client
    python src/ask.py --chapters "results|p&l|live account"

Nothing here fetches. If the corpora do not contain the answer, it says so -
which is itself the answer, and is the point at which running a full skill
session is justified.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

W = 100


def _p(s=""):
    print(s)


def _wrap(s, indent=6, width=W):
    return textwrap.fill(" ".join(str(s).split()), width=width,
                         initial_indent=" " * indent,
                         subsequent_indent=" " * indent)


def _head(t):
    _p()
    _p("=" * W)
    _p(t)
    _p("=" * W)


def _like(term):
    return f"%{term}%"


def _safe(con, sql, args=()):
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error:
        return []


# --------------------------------------------------------------- the corpora

def yt_claims(term, limit=12):
    out = []
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        rows = _safe(con,
                     "SELECT c.video_id, c.claim_type, c.claim_text, c.stated_n, "
                     "       c.stated_period, c.stated_capital, c.stated_win_rate, "
                     "       c.n_check_verdict, v.title, v.channel_name, "
                     "       s.s_total, s.h_total, s.verdict "
                     "FROM claims c JOIN videos v ON v.video_id = c.video_id "
                     "LEFT JOIN scores s ON s.video_id = c.video_id "
                     "WHERE c.claim_text LIKE ? OR v.title LIKE ? "
                     "ORDER BY (c.claim_type='result') DESC",
                     (_like(term), _like(term)))
        con.close()
        out += [(corpus, r) for r in rows]
    return out[:limit]


def gh_repos(term=None, venue=None, kind=None, limit=12):
    con = corpora.ro("github")
    sql = ("SELECT full_name, stars, commits, is_archived, pushed_at, s_adj, "
           "       s_strict, kind, venue_detected, submits_orders, pm_client, "
           "       trust_me_bro, description, verdict "
           "FROM repos WHERE s_adj IS NOT NULL")
    args = []
    if term:
        sql += " AND (full_name LIKE ? OR description LIKE ? OR what_it_does LIKE ?)"
        args += [_like(term)] * 3
    if venue:
        sql += " AND venue_detected LIKE ?"
        args.append(_like(venue))
    if kind:
        sql += " AND kind LIKE ?"
        args.append(_like(kind))
    sql += " ORDER BY s_adj DESC LIMIT ?"
    args.append(limit)
    rows = _safe(con, sql, tuple(args))
    con.close()
    return rows


def reddit_posts(term, limit=10):
    con = corpora.ro("reddit")
    rows = _safe(con,
                 "SELECT p.post_id, p.subreddit, p.title, p.score, "
                 "       p.num_comments, p.permalink, s.s_total, s.b_total, "
                 "       s.h_total, s.verdict "
                 "FROM rd_posts p JOIN rd_scores s ON s.post_id = p.post_id "
                 "WHERE (p.title LIKE ? OR p.selftext LIKE ?) "
                 "  AND s.verdict <> 'SKIP' "
                 "ORDER BY s.s_total DESC, p.score DESC LIMIT ?",
                 (_like(term), _like(term), limit))
    con.close()
    return rows


def entity_reputation(term, limit=10):
    con = corpora.ro("reddit")
    rows = _safe(con,
                 "SELECT e.display, e.kind, e.canonical_url, e.github_repo, "
                 "       v.verdict, v.n_platforms, v.promo_score, "
                 "       v.critic_score, v.reason "
                 "FROM entities e LEFT JOIN verdicts v "
                 "  ON v.entity_id = e.entity_id "
                 "WHERE e.display LIKE ? OR e.key LIKE ? "
                 "ORDER BY v.n_platforms DESC LIMIT ?",
                 (_like(term), _like(term), limit))
    obs = {}
    for r in rows:
        obs[r["display"]] = _safe(
            con,
            "SELECT o.platform, o.stance, o.strength, o.detail, o.evidence "
            "FROM observations o JOIN entities e ON e.entity_id = o.entity_id "
            "WHERE e.display = ? LIMIT 8", (r["display"],))
    con.close()
    return rows, obs


# ------------------------------------------------------------- the questions

def q_tested(term):
    """"Has anyone already tested X, and what happened?" """
    _head(f'HAS ANYONE TESTED "{term}" - and what happened?')
    hits = yt_claims(term, limit=14)
    results = [(c, r) for c, r in hits if r["claim_type"] == "result"]
    _p(f"\n-- VIDEO CLAIMS ({len(hits)} matched, {len(results)} are RESULTS)")
    if not hits:
        _p("     nothing in the read set. 38 videos are read of ~1,200 gated - "
           "absence here is weak evidence.")
    for c, r in hits:
        n = r["stated_n"]
        flag = "RESULT" if r["claim_type"] == "result" else r["claim_type"]
        den = (f"n={n}" if n else "NO DENOMINATOR")
        _p(f"\n  [{flag} · {den}] {r['channel_name']} — {r['title'][:60]}")
        _p(f"     video={r['video_id']}  S={r['s_total']} H={r['h_total']} "
           f"{r['verdict']}"
           + (f"  n-check={r['n_check_verdict']}" if r["n_check_verdict"] else ""))
        _p(_wrap(r["claim_text"][:340]))

    rows = reddit_posts(term)
    _p(f"\n-- REDDIT ({len(rows)} scored, non-SKIP)")
    for r in rows:
        _p(f"  S={r['s_total']:>2} B={r['b_total']:>2} H={r['h_total']:>3} "
           f"{r['verdict']:<24} {r['score']:>4}pts {r['num_comments']:>3}c  "
           f"{r['title'][:64]}")
        _p(f"     reddit.com{r['permalink']}")

    repos = gh_repos(term, limit=8)
    _p(f"\n-- GITHUB ({len(repos)} scored repos matching)")
    for r in repos:
        _p(f"  s_adj={r['s_adj']:>5.2f} {'ARCHIVED' if r['is_archived'] else 'alive   '} "
           f"{r['commits'] or 0:>5}c {r['stars']:>6}* "
           f"{'TRUST-ME-BRO ' if r['trust_me_bro'] else ''}{r['full_name']}")

    _p("\n-- HOW TO READ THIS")
    _p(_wrap("A RESULT claim with NO DENOMINATOR is not a test, it is an "
             "advertisement. A result whose n IS stated still needs its "
             "break-even: this repo's own tally is 45 retractions and every "
             "one shrank the edge. If nothing above states an n, the honest "
             "answer to 'has anyone tested this' is NO.", 2))


def q_backtester(venue):
    _head(f"DOES A WORKING BACKTESTER EXIST FOR {venue.upper()}?")
    rows = gh_repos(venue=venue, kind="backtester", limit=15)
    _p(f"\n-- classified `kind=backtester`, venue detected FROM IMPORTS "
       f"(never the README): {len(rows)}\n")
    for r in rows:
        stale = ""
        if (r["pm_client"] or "").startswith("v1"):
            stale = "  << imports the ARCHIVED v1 Polymarket client"
        _p(f"  s_adj={r['s_adj']:>5.2f} {'ARCHIVED' if r['is_archived'] else 'alive'} "
           f"{r['commits'] or 0:>5}c {r['stars']:>6}*  {r['full_name']}{stale}")
        if r["description"]:
            _p(_wrap(r["description"][:150], 8))
    _p("\n-- WHAT TO CHECK BEFORE TRUSTING ANY OF THEM")
    for line in [
        "Does it model the fee IN THE ENGINE, or apply it afterwards? "
        "Afterwards is wrong at the sizing decision.",
        "Does the backtest import the SAME fair-value function as the live "
        "engine? The best repo in this corpus does it explicitly 'so they can "
        "never drift apart'.",
        "Does it add LATENCY? An independent source measured that without it, "
        "most strategies are profitable - and this repo's own leak canary "
        "recovers +0.32c, half the quoted spread, by marking at the mid.",
        "Does it use scipy `filtfilt`? That is zero-phase - it runs the filter "
        "forwards AND backwards, so today's indicator uses FUTURE prices. "
        "Silent look-ahead. Demand `lfilter`.",
        "Kalshi's maker fee is PER SERIES - 130 of 12,396 charge makers and "
        "they are the liquid ones. Two of the most rigorous repos here get "
        "this wrong in the other direction. Use common/kalshi_fees.py.",
    ]:
        _p(_wrap("- " + line, 2))


def q_datasources():
    _head("WHAT FREE DATA SOURCES DO PEOPLE WHO PUBLISH REAL RESULTS USE?")
    con = corpora.ro("github")
    rows = _safe(con, "SELECT * FROM data_sources")
    con.close()
    if rows:
        _p("\n-- signal-github's data_sources table")
        for r in rows:
            _p("  " + " · ".join(f"{k}={r[k]}" for k in r.keys()
                                 if r[k] not in (None, "")))
    _p("\n-- verified by fetching, in this repo, with the date of the check")
    for line in [
        "guest.api.arcadia.pinnacle.com/0.1/sports/<id>/matchups — 200 and "
        "1.7 MB with NO header at all (2026-08-04). The de-vigged sharp "
        "reference price, free. NOTE the /0.1/sports INDEX returns 401 - "
        "probing that first makes a live API look dead.",
        "archive.pmxt.dev — free hourly-batched Parquet order books, CC BY 4.0. "
        "Polymarket v2 21 Apr - 4 Aug 2026. Kalshi 15 May - 11 Jun 2026 only. "
        "One hour = 20.7M rows at microsecond resolution, NOT hourly snapshots.",
        "arctic-shift.photon-reddit.com — the public Reddit research archive "
        "that replaced Pushshift for non-moderators. robots.txt `Disallow:` "
        "(empty = everything permitted). api.pushshift.io is 403, moderators "
        "only.",
        "sports.core.api.espn.com v2 — 200. site.api.espn.com scoreboard is "
        "403 on 7 of 7 leagues as of 2026-08-04; a finding that rested on it "
        "needs re-establishing.",
        "api.binance.com — HTTP 451, GEO-BLOCKED from this machine. `crypto/` "
        "treats it as a data source and will fail here for a reason that looks "
        "like a network error and is not one.",
        "football-data.co.uk — HTTP 200 and WRONG FILE. COL.csv is byte-"
        "identical to POL.csv (its own League column reads Ekstraklasa) and "
        "KOR.csv to NOR.csv. Hash it and check its own content column.",
    ]:
        _p(_wrap("- " + line, 2))
    _p("\n-- COSTS MONEY, so it is not on this list")
    _p(_wrap("the-odds-api (129 repos use it, keyed), Apify (at a monthly hard "
             "limit), tennisexplorer/crawlstone (~$20). See PAID_OPTIONS.md in "
             "social-signal and extractor-upgrade.", 2))


def q_tool(term):
    _head(f'WHAT IS SAID ABOUT "{term}" OUTSIDE ITS OWN MARKETING?')
    rows, obs = entity_reputation(term)
    if not rows:
        _p("\n  no entity by that name in the 240-entity cross-platform table.")
    for r in rows:
        _p(f"\n  {r['display']}")
        _p(f"     verdict={r['verdict']}  platforms={r['n_platforms']}  "
           f"promo={r['promo_score']}  critic={r['critic_score']}")
        if r["reason"]:
            _p(_wrap(r["reason"], 8))
        for o in obs.get(r["display"], []):
            _p(f"     [{o['platform']:<8} {o['stance']:<24}] "
               f"{(o['detail'] or '')[:66]}")
            if o["evidence"]:
                _p(_wrap('"' + str(o["evidence"])[:150] + '"', 10))

    posts = reddit_posts(term, limit=8)
    if posts:
        _p(f"\n-- Reddit threads mentioning it ({len(posts)})")
        for p in posts:
            _p(f"  S={p['s_total']:>2} H={p['h_total']:>3} {p['score']:>4}pts  "
               f"{p['title'][:62]}")
            _p(f"     reddit.com{p['permalink']}")

    repos = gh_repos(term, limit=6)
    if repos:
        _p(f"\n-- GitHub")
        for r in repos:
            _p(f"  {'ARCHIVED ' if r['is_archived'] else ''}"
               f"{r['full_name']} · {r['stars']}* · {r['commits'] or 0} commits "
               f"· pushed {(r['pushed_at'] or '')[:10]}")

    _p("\n-- HOW TO READ THIS")
    _p(_wrap("ADVOCACY is kept separate from CORROBORATION on purpose: a stale "
             "repo somebody mentioned in passing is a stale repo, not a "
             "contradiction. TRUST_ME_BRO discounts a tool's CLAIMS without "
             "condemning the tool - the flag is weakly POSITIVELY correlated "
             "with substance (rho +0.064, p 0.0009, n=2,717), because making a "
             "results claim at all requires having built something.", 2))


def q_chapters(term, limit=25):
    """Videos whose AUTHOR indexed the thing you are asking about.

    The cheapest lookup in the whole system: chapter titles are written by the
    creator, sit in a description field that was fetched long ago, and are
    searchable without reading one word of transcript. 367 of 1,197 videos have
    them.
    """
    import chapters as CH
    rx = re.compile(term, re.I)
    rows = CH.scan()
    have = [r for r in rows if r["chapters"]]
    _head(f'CHAPTER TITLES MATCHING "{term}" - no transcript read')
    _p(f"\n{len(have)} of {len(rows)} videos publish a real chapter list "
       f"(YouTube's own rule: first stamp 0:00, >=3, >=10s apart).\n")
    n = 0
    for r in have:
        m = [(t, ti) for t, ti in r["chapters"] if rx.search(ti)]
        if not m:
            continue
        n += 1
        _p(f"  {r['video_id']} {'[ALREADY READ]' if r['is_read'] else '              '} "
           f"{(r['title'] or '')[:56]}")
        for t, ti in m[:5]:
            _p(f"      {t//60:>3}m{t%60:02d}s  {ti[:72]}")
        if n >= limit:
            break
    _p(f"\n  {n} videos matched.")
    _p("\n-- HOW TO READ THIS")
    _p(_wrap("A chapter titled 'Results' or '3-hour results: $13 profit' is the "
             "author telling you where the claim is AND, sometimes, what its "
             "denominator is - for free, before anybody reads anything. A "
             "video marked [ALREADY READ] has an extraction; the rest are "
             "candidates, and the chapter title is the cheapest evidence there "
             "is for picking which.", 2))
    _p(_wrap("It is NOT a screen detector. Measured: only 2 of 19 recorded "
             "watch_segments fall inside a chapter whose title names screen "
             "content. Chapters index topics; watch_segments index moments.", 2))


def q_free(term):
    _head(f'"{term}" ACROSS EVERY CORPUS')
    q_tested(term)
    q_chapters(term)
    q_tool(term)


def main():
    ap = argparse.ArgumentParser(
        description="One read-only lookup across every extractor corpus.")
    ap.add_argument("term", nargs="?", default=None)
    ap.add_argument("--tested", metavar="X",
                    help="has anyone already tested X, and what happened")
    ap.add_argument("--backtester", metavar="VENUE",
                    help="does a working backtester exist for VENUE")
    ap.add_argument("--datasources", action="store_true",
                    help="what free data do people with real results use")
    ap.add_argument("--tool", metavar="NAME",
                    help="what is said about NAME outside its own marketing")
    ap.add_argument("--chapters", metavar="REGEX",
                    help="videos whose AUTHOR indexed this, no transcript read")
    a = ap.parse_args()

    ran = False
    if a.tested:
        q_tested(a.tested); ran = True
    if a.backtester:
        q_backtester(a.backtester); ran = True
    if a.datasources:
        q_datasources(); ran = True
    if a.tool:
        q_tool(a.tool); ran = True
    if a.chapters:
        q_chapters(a.chapters); ran = True
    if a.term and not ran:
        q_free(a.term); ran = True
    if not ran:
        ap.print_help()
        return
    _p()
    _p("-" * W)
    _p("Corpora are OFFLINE snapshots. Absence is weak evidence: 38 of ~1,200 "
       "gated videos are read.")
    _p("If the answer is not here, THAT is the trigger for a full "
       "/youtube-signal or /github-signal session.")


if __name__ == "__main__":
    main()
