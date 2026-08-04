"""T2 — collect the Reddit corpus.

Reddit matters for one reason the other platforms cannot supply: **it is where
tools get criticised.** A YouTube comment section is emoji; a Reddit thread
contains specific technical objections, which the credibility rubric treats as
the strongest available honesty signal, and it is where scams get named.

Two passes, in this order:

  sweep    every post in each target subreddit back to a date floor, plus the
           comment threads on the posts that matter. Pulled whole and searched
           offline, because the archive has no global text search (see
           `reddit.py`) and because a local corpus can be re-queried for a new
           tool name at zero cost.

  probe    a scoped title/selftext/body search per subreddit for the venue
           terms, to catch posts a date-floored sweep missed.

Subreddit choice, and why each one is here:

  algotrading, quantfinance    where a bot claim gets picked apart
  predictionmarkets, Kalshi,   the venues themselves; also where the tools this
  Polymarket, sportsbook,      programme's YouTube corpus promotes get named
  sportsbetting
  webscraping                  where the data-source questions get answered

    python src/reddit_fetch.py --dry-run       # one page per sub, report shape
    python src/reddit_fetch.py --since 2024-01-01
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import reddit  # noqa: E402

SUBS = [
    # (name, why it is here)
    ("algotrading", "where a bot claim gets picked apart"),
    ("Kalshi", "venue"),
    ("Polymarket", "venue"),
    ("predictionmarkets", "venue-adjacent, cross-venue comparisons"),
    ("sportsbook", "where scam tout services get named"),
    ("sportsbetting", "same, larger"),
    ("quant", "method criticism"),
    ("quantfinance", "method criticism"),
    ("webscraping", "the data-source questions"),
    ("options", "adjacent cost-side discipline"),
]

# Scoped text probes. The archive refuses an unscoped text search, so every
# term is run per subreddit.
VENUE_TERMS = ["kalshi", "polymarket", "prediction market"]

# Where a prediction-market tool is plausibly named. r/options and r/quant get
# the sweep and the venue probe but not 40 product names each.
TOOL_SUBS = {"kalshi", "polymarket", "predictionmarkets", "algotrading",
             "sportsbook", "sportsbetting"}

# Tool names are read out of the entity table rather than hardcoded, so the
# probe list is whatever T1 could not corroborate. That is the point of running
# T1 first: it produces the shortlist of things worth asking a room of critics
# about.
MIN_TERM_LEN = 5
GENERIC_TERMS = {
    "kalshi", "polymarket", "discord", "python", "claude", "vercel", "grok",
    "metamask", "streamlit", "duckdb", "pydantic", "openrouter", "binance",
    "alpaca", "jupyter", "homebrew", "tradingview", "hyperliquid", "fanduel",
    "prizepicks", "quantconnect", "numpy", "chainlink", "goldsky", "polygon",
}


def probe_terms_from_entities(con, max_terms=40):
    """Every entity a promoter pushed that no independent source corroborated,
    plus anything the join marked as contradicted. These are exactly the names
    where a room of critics is the only remaining evidence."""
    rows = con.execute("""
        SELECT e.display, e.compact_key, v.verdict
        FROM entities e JOIN verdicts v ON v.entity_id = e.entity_id
        WHERE v.verdict IN ('UNDISCLOSED', 'CONTRADICTION', 'SINGLE_SOURCE')
        ORDER BY CASE v.verdict WHEN 'UNDISCLOSED' THEN 0
                                WHEN 'CONTRADICTION' THEN 1 ELSE 2 END""").fetchall()
    terms, seen = [], set()
    for r in rows:
        import norm as _n
        name = _n.strip_descriptor(r["display"]).strip().lower()
        # A multi-word gloss is not a search term; the first token of a product
        # name is. Anything under MIN_TERM_LEN characters returns noise.
        cand = name if " " not in name else name.split()[0]
        cand = cand.strip("'\"“”‘’.,")
        if (len(cand) < MIN_TERM_LEN or cand in GENERIC_TERMS or cand in seen
                or not any(c.isalpha() for c in cand)):
            continue
        seen.add(cand)
        terms.append((cand, r["verdict"]))
        if len(terms) >= max_terms:
            break
    return terms


def store_posts(con, rows, query: str):
    n = 0
    for r in rows:
        con.execute("""
            INSERT OR IGNORE INTO rd_posts
              (post_id, subreddit, title, selftext, author, created_utc, score,
               upvote_ratio, num_comments, permalink, is_self, url, link_flair,
               over_18, query, fetched_utc)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r.get("id"), r.get("subreddit"), r.get("title"),
             r.get("selftext") or "", r.get("author"),
             float(r.get("created_utc") or 0), r.get("score"),
             r.get("upvote_ratio"), r.get("num_comments"), r.get("permalink"),
             1 if r.get("is_self") else 0, r.get("url"),
             r.get("link_flair_text"), 1 if r.get("over_18") else 0,
             query, db.now()))
        n += 1
    con.commit()
    return n


def store_comments(con, rows):
    n = 0
    for r in rows:
        con.execute("""
            INSERT OR IGNORE INTO rd_comments
              (comment_id, post_id, parent_id, author, body, created_utc,
               score, depth, permalink, fetched_utc)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (r.get("id"), (r.get("link_id") or "").replace("t3_", ""),
             r.get("parent_id"), r.get("author"), r.get("body") or "",
             float(r.get("created_utc") or 0), r.get("score"), r.get("depth"),
             r.get("permalink"), db.now()))
        n += 1
    con.commit()
    return n


def logrun(con, kind, target, n, seconds, ok=1, error=""):
    con.execute("""INSERT INTO rd_log (ts_utc, kind, target, n, seconds, ok, error)
                   VALUES (?,?,?,?,?,?,?)""",
                (db.now(), kind, target, n, seconds, ok, error))
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2024-01-01",
                    help="date floor for the sweep (UTC)")
    ap.add_argument("--dry-run", action="store_true",
                    help="one page per subreddit; report shape and stop")
    ap.add_argument("--cap", type=int, default=6000,
                    help="hard cap on posts per subreddit")
    ap.add_argument("--comments-for", type=int, default=250,
                    help="pull comment threads for the N most-commented posts "
                         "that mention a venue term")
    ap.add_argument("--subs", default="",
                    help="comma-separated override of the subreddit list")
    args = ap.parse_args()

    floor = datetime.datetime.strptime(args.since, "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc).timestamp()
    subs = [(s.strip(), "") for s in args.subs.split(",") if s.strip()] or SUBS

    con = db.connect()
    t_start = time.time()

    print(f"SWEEP — {len(subs)} subreddits back to {args.since}")
    for name, why in subs:
        t0 = time.time()
        try:
            if args.dry_run:
                rows = reddit.posts(subreddit=name, limit=100, sort="desc")
            else:
                rows = reddit.paginate(reddit.posts, floor, hard_cap=args.cap,
                                       subreddit=name, limit=100, sort="desc")
        except Exception as e:  # noqa: BLE001
            print(f"  r/{name:<20} FAILED {e}")
            logrun(con, "sweep", name, 0, time.time() - t0, 0, str(e)[:300])
            continue
        n = store_posts(con, rows, f"sweep:{name}")
        oldest = min((float(r.get("created_utc") or 0) for r in rows),
                     default=0)
        age = (datetime.datetime.fromtimestamp(oldest, datetime.timezone.utc)
               if oldest else None)
        oldest = f"oldest {age:%Y-%m-%d}" if age else "no posts"
        # Say so on the line itself. A sweep that stopped at the cap covers a
        # shorter window than one that reached the floor, and a table of counts
        # that does not distinguish them invites comparing different periods.
        capped = "  ← CAPPED, not exhausted" if n >= args.cap else ""
        print(f"  r/{name:<20} {n:>6} posts  {oldest}  "
              f"{time.time()-t0:.0f}s{capped}", flush=True)
        logrun(con, "sweep", name, n, time.time() - t0)

    if args.dry_run:
        report_shape(con, t_start)
        con.close()
        return

    tool_terms = probe_terms_from_entities(con)
    print(f"\nPROBE — {len(VENUE_TERMS)} venue terms x {len(subs)} subreddits")
    for name, _ in subs:
        for term in VENUE_TERMS:
            t0 = time.time()
            got = 0
            for field in ("title", "selftext"):
                try:
                    rows = reddit.posts(subreddit=name, limit=100, sort="desc",
                                        **{field: term})
                except Exception as e:  # noqa: BLE001
                    logrun(con, "probe", f"{name}/{term}/{field}", 0,
                           time.time() - t0, 0, str(e)[:300])
                    continue
                got += store_posts(con, rows, f"probe:{name}:{field}:{term}")
            logrun(con, "probe", f"{name}/{term}", got, time.time() - t0)
        print(f"  r/{name} probed", flush=True)

    # The tool probe, and the reason it searches COMMENTS as well as posts:
    # a tool gets its own thread rarely and gets named in someone else's
    # comments constantly, and the comment is where the specific technical
    # objection lives.
    # Restricted to the rooms where these products are actually discussed.
    # Running 40 tool names across all ten subreddits is 1,200 requests to a
    # volunteer-run archive for the sake of asking r/options about a Polymarket
    # copy-trading bot.
    tool_subs = [(n, w) for n, w in subs if n.lower() in TOOL_SUBS]
    print(f"\nTOOL PROBE — {len(tool_terms)} names from T1 x "
          f"{len(tool_subs)} subreddits")
    for term, verdict in tool_terms:
        hits = 0
        t0 = time.time()
        for name, _ in tool_subs:
            for kind, fn, field in (("post", reddit.posts, "title"),
                                    ("post", reddit.posts, "selftext"),
                                    ("comment", reddit.comments, "body")):
                try:
                    rows = fn(subreddit=name, limit=100, sort="desc",
                              **{field: term})
                except Exception as e:  # noqa: BLE001
                    logrun(con, "tool_probe", f"{name}/{term}/{field}", 0,
                           time.time() - t0, 0, str(e)[:300])
                    continue
                if kind == "post":
                    hits += store_posts(con, rows, f"tool:{term}:{field}")
                else:
                    hits += store_comments(con, rows)
        logrun(con, "tool_probe", term, hits, time.time() - t0)
        print(f"  {term:<24} {verdict:<14} {hits:>5} rows "
              f"{time.time()-t0:.0f}s", flush=True)

    # Comments are the point. Pull threads for the most-discussed posts that
    # mention a venue, because that is where the specific technical objection
    # lives — the strongest single signal in the rubric.
    print(f"\nCOMMENTS — top {args.comments_for} discussed venue posts")
    targets = con.execute("""
        SELECT post_id, subreddit, num_comments FROM rd_posts
        WHERE num_comments > 2
          AND (lower(title) LIKE '%kalshi%' OR lower(selftext) LIKE '%kalshi%'
               OR lower(title) LIKE '%polymarket%' OR lower(selftext) LIKE '%polymarket%'
               OR lower(title) LIKE '%prediction market%'
               OR lower(selftext) LIKE '%prediction market%')
          AND post_id NOT IN (SELECT DISTINCT post_id FROM rd_comments)
        ORDER BY num_comments DESC LIMIT ?""", (args.comments_for,)).fetchall()
    total = 0
    for i, t in enumerate(targets, 1):
        t0 = time.time()
        try:
            rows = reddit.comments(link_id=t["post_id"], limit=100, sort="desc")
        except Exception as e:  # noqa: BLE001
            logrun(con, "comments", t["post_id"], 0, time.time() - t0, 0,
                   str(e)[:300])
            continue
        total += store_comments(con, rows)
        if i % 25 == 0:
            print(f"    {i}/{len(targets)} threads, {total} comments", flush=True)
    logrun(con, "comments", "venue_posts", total, time.time() - t_start)

    report_shape(con, t_start)
    db.log(con, "reddit_fetch",
           f"posts={con.execute('SELECT COUNT(*) c FROM rd_posts').fetchone()['c']} "
           f"comments={con.execute('SELECT COUNT(*) c FROM rd_comments').fetchone()['c']} "
           f"calls={reddit.STATS['calls']} 429s={reddit.STATS['429s']}")
    con.close()


def report_shape(con, t_start):
    print("\n--- corpus ---")
    for r in con.execute("""SELECT subreddit, COUNT(*) n,
                                   MIN(created_utc) lo, MAX(created_utc) hi
                            FROM rd_posts GROUP BY subreddit ORDER BY n DESC"""):
        lo = datetime.datetime.fromtimestamp(r["lo"], datetime.timezone.utc)
        hi = datetime.datetime.fromtimestamp(r["hi"], datetime.timezone.utc)
        print(f"  r/{r['subreddit']:<22}{r['n']:>7}  {lo:%Y-%m-%d} .. {hi:%Y-%m-%d}")
    # No silent caps. A subreddit whose sweep stopped short of the floor is
    # truncated, and a coverage table that does not say so reads as complete.
    print("  (a sweep whose oldest post is later than --since was capped, "
          "not exhausted)")
    nc = con.execute("SELECT COUNT(*) c FROM rd_comments").fetchone()["c"]
    np_ = con.execute("SELECT COUNT(*) c FROM rd_posts").fetchone()["c"]
    print(f"  {np_} posts, {nc} comments")
    print(f"  transport: {json.dumps(reddit.STATS)}")
    print(f"  wall clock: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
