"""Probe every Bluesky route, logged out, and say exactly which ones answer.

`social-signal/PLATFORMS.md` records Bluesky as CLOSED on the strength of one
endpoint returning 403 to two different User-Agents. One endpoint is not a
platform. This asks the whole AppView the same question and prints a row per
route, so "closed" can be replaced with a list of what is open and what is not.

No credentials. Everything here is a logged-out GET.

    py -3 extractor-apify\\src\\probe_bluesky.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# host, path, params, what a 200 would mean for us
ROUTES = [
    ("public.api.bsky.app", "app.bsky.feed.searchPosts",
     {"q": "kalshi", "limit": "5"},
     "keyword search — the one thing that matters for discovery"),
    ("public.api.bsky.app", "app.bsky.feed.searchPosts",
     {"q": "polymarket", "limit": "5"}, "same, different term"),
    ("api.bsky.app", "app.bsky.feed.searchPosts",
     {"q": "kalshi", "limit": "5"}, "the non-public AppView host"),
    ("bsky.social", "app.bsky.feed.searchPosts",
     {"q": "kalshi", "limit": "5"}, "the PDS host"),
    ("public.api.bsky.app", "app.bsky.actor.searchActors",
     {"q": "prediction market", "limit": "5"},
     "find accounts — a discovery route that is not post search"),
    ("public.api.bsky.app", "app.bsky.actor.getProfile",
     {"actor": "bsky.app"}, "read one profile"),
    ("public.api.bsky.app", "app.bsky.feed.getAuthorFeed",
     {"actor": "bsky.app", "limit": "5"},
     "read one account's posts — the fallback if search is shut"),
    ("public.api.bsky.app", "app.bsky.feed.getPostThread",
     {"uri": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/"
             "3kkzc3swzy22c"},
     "read a thread — where substance would live"),
    ("public.api.bsky.app", "app.bsky.unspecced.getPopularFeedGenerators",
     {"limit": "5"}, "custom feeds, i.e. other people's topic filters"),
    ("public.api.bsky.app", "com.atproto.repo.describeRepo",
     {"repo": "bsky.app"}, "raw repo description"),
    ("public.api.bsky.app", "com.atproto.identity.resolveHandle",
     {"handle": "bsky.app"}, "handle -> DID"),
]


def get(host: str, method: str, params: dict):
    url = (f"https://{host}/xrpc/{method}?"
           + urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
            return r.status, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.time() - t0
    except Exception as e:                       # noqa: BLE001
        return 0, str(e).encode(), time.time() - t0


def summarise(status: int, body: bytes) -> str:
    if status != 200:
        try:
            j = json.loads(body)
            return f"{j.get('error', '')}: {j.get('message', '')}"[:90]
        except Exception:                        # noqa: BLE001
            return body[:90].decode("utf-8", "replace").replace("\n", " ")
    try:
        j = json.loads(body)
    except Exception:                            # noqa: BLE001
        return f"{len(body)} bytes, not JSON"
    for key in ("posts", "actors", "feeds", "feed"):
        if isinstance(j.get(key), list):
            return f"{len(j[key])} {key}"
    if isinstance(j, dict) and "thread" in j:
        return "1 thread"
    return ", ".join(list(j)[:5])[:90]


def main() -> int:
    rows = []
    for host, method, params, why in ROUTES:
        status, body, secs = get(host, method, params)
        rows.append((host, method, status, summarise(status, body), secs, why))
        print(f"{status:>4}  {host:<20} {method:<42} "
              f"{summarise(status, body)[:50]:<50} {secs:5.2f}s")
        time.sleep(0.4)

    print()
    open_routes = [r for r in rows if r[2] == 200]
    print(f"{len(open_routes)} of {len(rows)} routes answer logged out.")
    for r in open_routes:
        print(f"  OPEN  {r[1]:<45} {r[5]}")
    for r in rows:
        if r[2] != 200:
            print(f"  SHUT  {r[1]:<45} {r[2]} {r[3][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
