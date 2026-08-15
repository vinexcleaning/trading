"""Collect Bluesky posts and their reply threads. Free, keyless, permitted.

`social-signal/PLATFORMS.md` records Bluesky as CLOSED on one 403. That 403 is
real and it is on **`public.api.bsky.app`**. The AppView also answers on
**`api.bsky.app`**, which returns 200 to the identical logged-out request, and
its `robots.txt` says in words: *"Crawling the public parts of the API is
allowed."* No account, no token, no key.

Rate limiting is by the platform's own instruction: it asks for a handful of
concurrent requests at most and uses HTTP 429 to say slow down. This client is
single-threaded, sleeps between calls, and backs off on 429.

    py -3 extractor-apify\\src\\bluesky_fetch.py
    py -3 extractor-apify\\src\\bluesky_fetch.py --per-term 200 --threads 100
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HOST = "api.bsky.app"
UA = "trading-research/1.0 (+contact via github; single-threaded, obeys 429)"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
DB = os.path.join(DATA, "bluesky.db")

# Fixed in PREREGISTRATION_BLUESKY.md before any post was scored. Narrow on
# purpose: this repo has recorded three retrieval failures in a row, all of
# them from widening the net.
TERMS = ["kalshi", "polymarket", "prediction market", "prediction markets",
         "event contract", "manifold markets", "kalshi bot", "polymarket bot",
         "predictit", "betfair exchange"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS bs_posts (
    uri TEXT PRIMARY KEY, cid TEXT, handle TEXT, did TEXT,
    created_utc TEXT, indexed_utc TEXT, text TEXT, langs TEXT,
    like_count INTEGER, reply_count INTEGER, repost_count INTEGER,
    quote_count INTEGER, is_reply INTEGER, term TEXT, fetched_utc TEXT);
CREATE TABLE IF NOT EXISTS bs_replies (
    uri TEXT PRIMARY KEY, root_uri TEXT, handle TEXT, depth INTEGER,
    created_utc TEXT, text TEXT, like_count INTEGER);
CREATE INDEX IF NOT EXISTS ix_replies_root ON bs_replies(root_uri);
CREATE TABLE IF NOT EXISTS bs_log (
    ts TEXT, event TEXT, detail TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def xrpc(method: str, params: dict, tries: int = 7):
    """One logged-out GET. Backs off on 429 the way the robots file asks."""
    url = f"https://{HOST}/xrpc/{method}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # 403 here is transient edge behaviour, not a refusal, and
            # `src/ua_test.py` is the evidence: this host answers 200 to a
            # browser string, an honest research string, curl and an empty
            # User-Agent alike, twice each. Nothing is being talked round --
            # the same honest client gets in on a retry.
            if e.code in (429, 403):
                wait = int(e.headers.get("Retry-After") or (5 * (attempt + 1)))
                time.sleep(min(wait, 60))
                continue
            if e.code in (400, 404):          # a dead post, not a dead client
                return None
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
        except Exception:                     # noqa: BLE001
            # Bare TCP timeouts happen on this host. Measured 2026-08-14: a run
            # died on WinError 10060 at the first call and the identical call
            # succeeded three times in a row a minute later. Retry patiently
            # rather than recording a platform as closed because of a blip --
            # that is how `PLATFORMS.md` came to say Bluesky was shut.
            if attempt == tries - 1:
                return None
            time.sleep(3 * (attempt + 1))
    return None


def search(term: str, want: int, pause: float, days: int = 400):
    """Yield posts for one term by walking BACKWARDS IN TIME, not by cursor.

    ⚠ THE CURSOR DOES NOT WORK, and this is measured rather than assumed.
    `searchPosts` returns 100 posts and a cursor; feeding that cursor back
    returns **403**, immediately and after waiting 20 and 60 seconds, while the
    identical request without a cursor returns 200 every time. So the search
    hands out the first 100 results of a query and nothing beyond them.

    What DOES work is `since`/`until`. A query bounded to a time window returns
    the newest 100 posts **inside that window**, so narrow windows walk the
    whole history. The window halves whenever it comes back full, because a
    full window means posts were dropped off the bottom of it.

    Cost of the workaround: one call per window instead of one per 100 posts.
    That is the price of the platform not paginating, and it is still free.
    """
    got = 0
    end = datetime.now(timezone.utc)
    floor = end - timedelta(days=days)
    span = timedelta(days=7)
    while got < want and end > floor:
        start = max(end - span, floor)
        j = xrpc("app.bsky.feed.searchPosts",
                 {"q": term, "limit": "100",
                  "since": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "until": end.strftime("%Y-%m-%dT%H:%M:%SZ")})
        time.sleep(pause)
        if j is None:                       # a dead window, not a dead term
            end = start
            span = timedelta(days=7)
            continue
        posts = j.get("posts") or []
        if len(posts) >= 100 and span > timedelta(hours=2):
            span = span / 2                 # full window: posts were dropped
            continue
        for p in posts:
            yield p
        got += len(posts)
        end = start
        # Widen again when a window comes back thin, so quiet stretches of
        # history are not walked an hour at a time.
        if len(posts) < 30:
            span = min(span * 2, timedelta(days=14))


def store_post(con, p: dict, term: str) -> None:
    rec = p.get("record") or {}
    con.execute(
        """INSERT OR IGNORE INTO bs_posts
           (uri, cid, handle, did, created_utc, indexed_utc, text, langs,
            like_count, reply_count, repost_count, quote_count, is_reply,
            term, fetched_utc)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (p.get("uri"), p.get("cid"), (p.get("author") or {}).get("handle"),
         (p.get("author") or {}).get("did"), rec.get("createdAt"),
         p.get("indexedAt"), rec.get("text") or "",
         ",".join(rec.get("langs") or []), p.get("likeCount") or 0,
         p.get("replyCount") or 0, p.get("repostCount") or 0,
         p.get("quoteCount") or 0, 1 if rec.get("reply") else 0,
         term, now()))


def walk_thread(node, root_uri: str, depth: int, out: list) -> None:
    post = node.get("post") if isinstance(node, dict) else None
    if post and depth > 0:                     # depth 0 is the root itself
        rec = post.get("record") or {}
        out.append((post.get("uri"), root_uri,
                    (post.get("author") or {}).get("handle"), depth,
                    rec.get("createdAt"), rec.get("text") or "",
                    post.get("likeCount") or 0))
    for r in (node.get("replies") or []):
        walk_thread(r, root_uri, depth + 1, out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-term", type=int, default=1000)
    ap.add_argument("--cap", type=int, default=6000)
    ap.add_argument("--threads", type=int, default=800,
                    help="how many posts with replies to expand")
    ap.add_argument("--pause", type=float, default=0.35)
    ap.add_argument("--no-search", action="store_true",
                    help="skip collection and only expand threads already held")
    ap.add_argument("--only-search", action="store_true",
                    help="collect and do not expand threads")
    args = ap.parse_args()

    con = connect()
    t0 = time.time()
    total = 0
    for term in ([] if args.no_search else TERMS):
        if total >= args.cap:
            break
        before = con.execute("SELECT COUNT(*) FROM bs_posts").fetchone()[0]
        n = 0
        # One term failing must not take the other nine with it. A partial
        # corpus with the shortfall recorded is worth more than no corpus.
        try:
            for p in search(term, min(args.per_term, args.cap - total),
                            args.pause):
                store_post(con, p, term)
                n += 1
        except Exception as e:                 # noqa: BLE001
            con.execute("INSERT INTO bs_log VALUES (?,?,?)",
                        (now(), "term_failed", f"{term}: {type(e).__name__}"))
            print(f"  {term:<22} FAILED after {n}: {type(e).__name__}",
                  flush=True)
        con.commit()
        after = con.execute("SELECT COUNT(*) FROM bs_posts").fetchone()[0]
        total += n
        print(f"  {term:<22} {n:>5} returned, {after - before:>5} new "
              f"(corpus {after})", flush=True)
        con.execute("INSERT INTO bs_log VALUES (?,?,?)",
                    (now(), "search", f"{term}: {n} returned"))
        con.commit()

    todo = [] if args.only_search else con.execute(
        """SELECT uri FROM bs_posts
           WHERE reply_count > 0
             AND uri NOT IN (SELECT DISTINCT root_uri FROM bs_replies)
           ORDER BY reply_count DESC LIMIT ?""", (args.threads,)).fetchall()
    print(f"  expanding {len(todo)} threads", flush=True)
    expanded = replies = 0
    for i, row in enumerate(todo):
        j = xrpc("app.bsky.feed.getPostThread",
                 {"uri": row["uri"], "depth": "6", "parentHeight": "0"})
        if not j or not j.get("thread"):
            continue
        out = []
        walk_thread(j["thread"], row["uri"], 0, out)
        if out:
            con.executemany(
                "INSERT OR IGNORE INTO bs_replies VALUES (?,?,?,?,?,?,?)", out)
            replies += len(out)
        expanded += 1
        if i % 50 == 0:
            con.commit()
            print(f"    {i}/{len(todo)} threads, {replies} replies",
                  flush=True)
        time.sleep(args.pause)
    con.commit()

    posts = con.execute("SELECT COUNT(*) FROM bs_posts").fetchone()[0]
    rng = con.execute("SELECT MIN(created_utc), MAX(created_utc) "
                      "FROM bs_posts").fetchone()
    print(f"\n  {posts} posts, {replies} replies in {expanded} threads, "
          f"{time.time() - t0:.0f}s")
    print(f"  date range {rng[0]} .. {rng[1]}")
    con.execute("INSERT INTO bs_log VALUES (?,?,?)",
                (now(), "done", f"{posts} posts, {replies} replies"))
    con.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
