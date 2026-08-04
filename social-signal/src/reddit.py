"""Reddit transport.

**Read this before changing the endpoint.** The brief for this project said
"free JSON API, no key: add .json to any URL, ~60/min unauthenticated". Measured
2026-08-04, that is **no longer true**:

    https://www.reddit.com/robots.txt   ->  User-agent: *   Disallow: /
    https://old.reddit.com/robots.txt   ->  User-agent: *   Disallow: /
    https://oauth.reddit.com/robots.txt ->  User-agent: *   Disallow: /
    /r/<sub>/hot.json                   ->  HTTP 403 (bot UA and browser UA alike)
    /r/<sub>/.rss                       ->  HTTP 403
    api.pushshift.io                    ->  403 "Not authenticated" (moderators only)

So the documented route is both **disallowed by robots and blocked in
practice**, and this project does not work around either. Scraping reddit.com
here would be a terms violation, not a clever transport.

What IS available, and why it is legitimate:

    https://arctic-shift.photon-reddit.com/robots.txt  ->  User-agent: *  Disallow:
                                                           (empty = everything allowed)

Arctic Shift is the public Reddit research archive that replaced Pushshift for
non-moderators. Its robots.txt permits crawling, it publishes a documented JSON
API for exactly this purpose, and it returns `X-RateLimit-Reset` headers which
this module obeys. We query the archive; we do not touch reddit.com.

Two shape constraints decide the collection design.

**1. Text search requires a scope.** `?title=`, `?selftext=`, `?body=` and
`?query=` all 400 with *"requires one of: author, subreddit"*. There is no
global text search.

**2. Full-text search over COMMENTS is expensive enough to time out.**
`?subreddit=X&body=Y` is a valid combination — it returns 400 with a different
message when it is not — but in practice it returns

    422 {"data":null,"error":"Timeout. Maybe slow down a bit"}

Post search over the same subreddit returns 200 immediately. So the comment
text search is the one query this archive cannot serve cheaply, and it is
exactly the one a tool-reputation project wants most.

Both constraints point the same way: **pull whole subreddits into local storage
and search offline.** That is faster, reproducible, and costs the archive one
pass instead of one expensive request per tool name.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://arctic-shift.photon-reddit.com"
UA = ("social-signal/0.1 (research; personal, non-commercial; "
      "+https://github.com/vinexcleaning/trading)")
MAX_LIMIT = 100

# Paced conservatively. The archive is a volunteer-run research service; the
# rule here is the same one signal-github runs under — back off, never hammer,
# and treat a 429 as an instruction rather than an obstacle.
MIN_GAP = 1.1
_last = 0.0

STATS = {"calls": 0, "429s": 0, "errors": 0, "rows": 0, "sleep_s": 0.0}


class RateLimited(Exception):
    pass


def _sleep_for(seconds: float, why: str):
    if seconds <= 0:
        return
    STATS["sleep_s"] += seconds
    print(f"    [reddit] sleeping {seconds:.0f}s ({why})", flush=True)
    time.sleep(seconds)


def call(path: str, params: dict, retries: int = 4):
    """One archive request. Obeys X-RateLimit-Reset; retries on 429 and on
    transient network failure, and gives up loudly rather than silently
    returning an empty list — an empty list is indistinguishable from
    "subreddit has no posts", which is how a collection run reports success
    while having collected nothing."""
    global _last
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{BASE}{path}?{qs}"
    for attempt in range(retries + 1):
        gap = MIN_GAP - (time.time() - _last)
        if gap > 0:
            time.sleep(gap)
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read().decode("utf-8", "replace")
                _last = time.time()
                STATS["calls"] += 1
                doc = json.loads(body)
                rows = doc.get("data") or []
                STATS["rows"] += len(rows)
                return rows
        except urllib.error.HTTPError as e:
            _last = time.time()
            STATS["calls"] += 1
            body = e.read()[:400].decode("utf-8", "replace")
            if e.code == 429:
                STATS["429s"] += 1
                reset = e.headers.get("X-RateLimit-Reset")
                try:
                    wait = float(reset) + 2
                except (TypeError, ValueError):
                    wait = 30.0
                _sleep_for(min(wait, 120), "HTTP 429")
                continue
            if e.code == 400:
                raise ValueError(f"400 from archive: {body} ({url})")
            if e.code == 422:
                # Measured 2026-08-04: the archive returns
                #   422 {"data":null,"error":"Timeout. Maybe slow down a bit"}
                # This is NOT a malformed request — `body=` plus `subreddit=` is
                # a valid combination and returns 400 with a different message
                # when it is not. 422 means the server timed out running an
                # expensive full-text scan and is asking, in words, to be given
                # room. The original 5/10/15/20s backoff treated it as a generic
                # transient failure and kept pushing, which is how a volunteer
                # research service gets hammered by something claiming to be
                # polite. Back off in minutes, not seconds.
                STATS["422s"] = STATS.get("422s", 0) + 1
                _sleep_for(60 * (attempt + 1), "HTTP 422 — the server asked to "
                                               "slow down, in those words")
                continue
            if attempt < retries:
                _sleep_for(5 * (attempt + 1), f"HTTP {e.code}")
                continue
            STATS["errors"] += 1
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except Exception as e:  # noqa: BLE001 — network is allowed to fail
            _last = time.time()
            if attempt < retries:
                _sleep_for(5 * (attempt + 1), f"{type(e).__name__}")
                continue
            STATS["errors"] += 1
            raise RuntimeError(f"{type(e).__name__}: {e}")
    STATS["errors"] += 1
    raise RuntimeError(f"gave up after {retries} retries: {url}")


def posts(subreddit=None, author=None, before=None, after=None, limit=MAX_LIMIT,
          sort="desc", title=None, selftext=None, query=None):
    return call("/api/posts/search", {
        "subreddit": subreddit, "author": author, "before": before,
        "after": after, "limit": min(limit, MAX_LIMIT), "sort": sort,
        "title": title, "selftext": selftext, "query": query})


def comments(subreddit=None, author=None, link_id=None, before=None, after=None,
             limit=MAX_LIMIT, sort="desc", body=None, query=None):
    return call("/api/comments/search", {
        "subreddit": subreddit, "author": author, "link_id": link_id,
        "before": before, "after": after, "limit": min(limit, MAX_LIMIT),
        "sort": sort, "body": body, "query": query})


def paginate(fn, floor_utc: float, hard_cap: int = 100_000, **kw):
    """Walk backwards in time until the floor or exhaustion.

    Pages on `before` = the oldest `created_utc` seen. Two traps handled:
    a page that returns nothing new (identical timestamps at a boundary) would
    loop forever, and a page shorter than the limit is the end of the archive,
    not a transient short read.
    """
    seen: set[str] = set()
    before = None
    out = []
    while len(out) < hard_cap:
        rows = fn(before=before, **kw)
        if not rows:
            break
        fresh = [r for r in rows if r.get("id") not in seen]
        for r in fresh:
            seen.add(r.get("id"))
        out.extend(fresh)
        oldest = min(float(r.get("created_utc") or 0) for r in rows)
        if oldest <= floor_utc:
            out = [r for r in out if float(r.get("created_utc") or 0) > floor_utc]
            break
        nxt = int(oldest)
        if before is not None and nxt >= before:
            nxt = before - 1          # boundary tie: step past it explicitly
        before = nxt
        if len(rows) < MAX_LIMIT:
            break
        if not fresh:
            break
    return out
