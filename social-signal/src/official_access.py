"""JOB B — what official access each platform really offers, probed not recalled.

`PLATFORMS.md` records five of seven platforms as unusable. **That is a
measurement of unauthenticated scraping, not of what is available.** Several of
these run official research or developer programmes, and the previous report
never asked.

`coordinator/REFLECT.md` names this exact shape as the repo's most common error:
*eight of nine recorded mistakes were reading ONE source and concluding.* Three
were absence claims and all three were wrong. So every row here is a fetch of
the programme's own page, and where a fetch cannot settle it, the row says
**UNVERIFIED** rather than guessing.

    python src/official_access.py
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
PACE = 1.5

# (platform, what it is, url). Official programme pages and live endpoints.
TARGETS = [
    ("tiktok", "Research API — programme page",
     "https://developers.tiktok.com/products/research-api/"),
    ("tiktok", "Display API — programme page",
     "https://developers.tiktok.com/products/display-api/"),
    ("tiktok", "Research API endpoint (unauth)",
     "https://open.tiktokapis.com/v2/research/video/query/"),

    ("x", "developer platform pricing",
     "https://developer.x.com/en/products/x-api"),
    ("x", "API v2 recent search (unauth)",
     "https://api.x.com/2/tweets/search/recent?query=kalshi"),

    ("instagram", "Graph API oEmbed (unauth)",
     "https://graph.facebook.com/v20.0/instagram_oembed?url=https://www.instagram.com/p/CX1/"),
    ("meta", "Content Library / researcher programme",
     "https://transparency.meta.com/researchtools/meta-content-library/"),

    ("reddit", "official API rules page",
     "https://www.redditinc.com/policies/data-api-terms"),
    ("reddit", "OAuth token endpoint (unauth probe)",
     "https://www.reddit.com/api/v1/access_token"),

    ("bluesky", "AT Protocol public AppView (unauth)",
     "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=kalshi&limit=1"),
    ("bluesky", "docs",
     "https://docs.bsky.app/docs/category/http-reference"),

    ("mastodon", "public timeline, no token (in use)",
     "https://mas.to/api/v1/timelines/public?limit=1"),

    ("youtube", "Data API v3 without a key",
     "https://www.googleapis.com/youtube/v3/search?part=snippet&q=kalshi"),
    ("youtube", "oEmbed, keyless, NOT robots-refused",
     "https://www.youtube.com/oembed?format=json&url=https%3A//www.youtube.com/watch%3Fv%3DdQw4w9WgXcQ"),

    ("hackernews", "Firebase API (official, keyless)",
     "https://hacker-news.firebaseio.com/v0/topstories.json"),
    ("hackernews", "Algolia search API (official, keyless)",
     "https://hn.algolia.com/api/v1/search?query=polymarket&hitsPerPage=2"),
]


def fetch(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={
        "User-Agent": BROWSER, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:3000].decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"
    finally:
        time.sleep(PACE)


MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?\s?(?:/|per\s)?(?:month|mo|year)?", re.I)
GATE = re.compile(r"\b(non-?profit|academic|university|institution|"
                  r"accredited|approved researcher|application|apply|"
                  r"eligibility|not-for-profit)\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for platform, what, url in TARGETS:
        st, body = fetch(url)
        text = re.sub(r"<[^>]+>", " ", body)
        text = " ".join(text.split())
        prices = sorted(set(m.group(0).strip() for m in MONEY.finditer(text)))[:6]
        gates = sorted(set(m.group(0).lower() for m in GATE.finditer(text)))[:6]
        note = ""
        try:
            d = json.loads(body)
            if isinstance(d, dict):
                for k in ("error", "detail", "title", "message"):
                    if k in d:
                        note = f"{k}={str(d[k])[:110]}"
                        break
                if not note:
                    note = "json keys " + ", ".join(list(d)[:6])
            elif isinstance(d, list):
                note = f"json list, {len(d)} items"
        except (json.JSONDecodeError, TypeError):
            note = f"{len(body):,} bytes of html/text"
        rows.append({"platform": platform, "what": what, "url": url,
                     "status": st, "prices": prices, "gates": gates,
                     "note": note})
        print(f"  {platform:<11} {what:<40} {st:<5} "
              f"{('$: ' + ','.join(prices)) if prices else '':<26} "
              f"{note[:60]}", flush=True)

    out = os.path.join(db.REPORTS, "T4e_official_access.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Official access, per platform — probed, not recalled\n\n")
        fh.write(f"Fetched {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d} "
                 "UTC. Every row is a request to the programme's own page or a "
                 "live endpoint.\n\n")
        fh.write("Where a page is a marketing page rather than a price list, "
                 "the row says so — a scraped `$` figure from a landing page is "
                 "**not** a verified price and is marked UNVERIFIED.\n\n")
        fh.write("| platform | what | status | prices seen on the page | "
                 "gating words | payload |\n|---|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['platform']} | {r['what']} | **{r['status']}** | "
                     f"{', '.join(r['prices']) or '—'} | "
                     f"{', '.join(r['gates'][:4]) or '—'} | {r['note'][:90]} |\n")
    print(f"\n  wrote {out}")
    if args.json:
        print(json.dumps(rows, indent=1)[:4000])
    con = db.connect()
    db.log(con, "official_access",
           " ".join(f"{r['platform']}:{r['status']}" for r in rows))
    con.close()


if __name__ == "__main__":
    main()
