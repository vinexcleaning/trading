"""Does Bluesky's AppView answer an honest client, or only a browser string?

This is the whole Bluesky decision and it is one measurement.

`social-signal/PLATFORMS.md` says of the 403: *"403 to a research User-Agent and
403 to a browser User-Agent alike, so it is not UA filtering."* That was
measured on `public.api.bsky.app`. `api.bsky.app` is a different host and has to
be asked separately.

The standard this repo already applies, from its own Reddit and TikTok rows:
**a User-Agent string is not consent.** If the only way in is to claim to be
Chrome, the route is shut whatever the status code says.

Each UA is tried twice with a gap, because one 403 can be a rate limit wearing a
different number.

    py -3 extractor-apify\\src\\ua_test.py
"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

AGENTS = [
    ("browser string", BROWSER),
    ("honest research UA", "trading-research/1.0 (+github; obeys 429)"),
    ("bare project name", "extractor-apify"),
    ("python default", None),
    ("empty", ""),
    ("curl", "curl/8.4.0"),
    ("browser string, no Accept", BROWSER),
]

HOSTS = ["api.bsky.app", "public.api.bsky.app"]


def call(host: str, ua, send_accept: bool = True):
    url = (f"https://{host}/xrpc/app.bsky.feed.searchPosts?"
           + urllib.parse.urlencode({"q": "kalshi", "limit": "3"}))
    headers = {}
    if ua is not None:
        headers["User-Agent"] = ua
    if send_accept:
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, len(e.read())
    except Exception as e:                       # noqa: BLE001
        return 0, str(e)[:40]


def main() -> int:
    print(f"  {'host':<20} {'user-agent':<26} try1   try2")
    results = {}
    for host in HOSTS:
        for name, ua in AGENTS:
            accept = "no Accept" not in name
            a = call(host, ua, accept)
            time.sleep(2.0)
            b = call(host, ua, accept)
            results[(host, name)] = (a[0], b[0])
            print(f"  {host:<20} {name:<26} {a[0]:>4}   {b[0]:>4}")
            time.sleep(1.5)

    print()
    ok = {k for k, v in results.items() if v[0] == 200 and v[1] == 200}
    browser_only = [h for h in HOSTS
                    if (h, "browser string") in ok
                    and (h, "honest research UA") not in ok]
    if browser_only:
        print("  VERDICT: on " + ", ".join(browser_only) + " the endpoint "
              "answers a browser string and refuses an honest one.")
        print("  That is User-Agent filtering. By this repo's own standard "
              "-- the one that closed Reddit's .json route and TikTok's /tag "
              "-- getting in requires not identifying as what we are, so the "
              "route is SHUT regardless of the 200.")
    elif ok:
        print("  VERDICT: an honest client is served. The route is OPEN.")
    else:
        print("  VERDICT: nothing answers. Closed to everyone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
