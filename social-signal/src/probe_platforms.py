"""What does each platform actually hand a keyless client? Measured, per endpoint.

This exists because this project has twice built on a shallow check and been
wrong: a directory listing that "verified" an archive nobody had opened, and a
26-row sample that said the opposite of a 312-file census. Every row below is a
status code and a byte count from a real request, and the interesting column is
not "does it respond" but **"does it return the text a rubric can score"**.

The rubric needs, per item: words (transcript / caption / body), an author, a
date, and ideally engagement. A title and a thumbnail score nothing.

    python src/probe_platforms.py
    python src/probe_platforms.py --json      # machine-readable, for adapters
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
BOT = "social-signal/0.1 (research; +https://github.com/vinexcleaning/trading)"

# A real public post on each platform, used as the concrete target. Chosen to be
# stable, public and uncontroversial.
TARGETS = {
    "tiktok_video": "https://www.tiktok.com/@tiktok/video/6718335390845095173",
    "instagram_post": "https://www.instagram.com/p/CXqNzGmpBcW/",
    "x_post": "https://x.com/kalshi/status/1750000000000000000",
    "facebook_post": "https://www.facebook.com/facebook/posts/10160000000000000",
}

PROBES = [
    # (platform, label, url, what a PASS would mean)
    ("tiktok", "robots.txt", "https://www.tiktok.com/robots.txt",
     "what a crawler is permitted to fetch"),
    ("tiktok", "oEmbed (documented, keyless)",
     "https://www.tiktok.com/oembed?url=" + urllib.parse.quote(TARGETS["tiktok_video"]),
     "TITLE + author only, or more?"),

    ("instagram", "robots.txt", "https://www.instagram.com/robots.txt", ""),
    ("instagram", "oEmbed (legacy, keyless)",
     "https://api.instagram.com/oembed?url=" + urllib.parse.quote(TARGETS["instagram_post"]),
     "retired in 2020?"),
    ("instagram", "graph oEmbed (app-gated)",
     "https://graph.facebook.com/v20.0/instagram_oembed?url="
     + urllib.parse.quote(TARGETS["instagram_post"]),
     "needs a Meta app token?"),

    ("facebook", "robots.txt", "https://www.facebook.com/robots.txt",
     "NEVER TESTED BEFORE THIS RUN"),
    ("facebook", "oEmbed post (app-gated?)",
     "https://graph.facebook.com/v20.0/oembed_post?url="
     + urllib.parse.quote(TARGETS["facebook_post"]),
     "does any keyless oEmbed survive?"),
    ("facebook", "public page HTML", "https://www.facebook.com/facebook",
     "login wall?"),
    ("facebook", "mbasic (no-JS mirror)", "https://mbasic.facebook.com/facebook",
     "the low-bandwidth front end"),

    ("x", "robots.txt", "https://x.com/robots.txt", ""),
    ("x", "oEmbed (publish.twitter.com, keyless)",
     "https://publish.twitter.com/oembed?url=" + urllib.parse.quote(TARGETS["x_post"]),
     "the ONE documented keyless X endpoint"),
    ("x", "api v2 without a key",
     "https://api.x.com/2/tweets/search/recent?query=kalshi",
     "401 means paid, not broken"),

    ("reddit", "robots.txt", "https://www.reddit.com/robots.txt", ""),
    ("reddit", "arctic-shift archive (in use)",
     "https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=Kalshi&limit=1",
     "the transport this project actually uses"),

    # Cross-platform: the only documented, keyless, transcript-bearing endpoint
    # any of these platforms has ever had.
    ("youtube", "oEmbed (control)",
     "https://www.youtube.com/oembed?format=json&url="
     + urllib.parse.quote("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
     "control: a platform this programme already extracts from"),
]

# Words whose presence in a response means the rubric has something to score.
TEXT_KEYS = ("transcript", "caption", "subtitle", "description", "selftext",
             "body", "text", "content", "message")


def fetch(url: str, ua: str = BROWSER, timeout: int = 30):
    req = urllib.request.Request(url, headers={
        "User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-GB,en;q=0.9"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(300_000), time.time() - t, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:8000], time.time() - t, ""
    except Exception as e:  # noqa: BLE001
        return 0, b"", time.time() - t, f"{type(e).__name__}: {e}"


def star_block(body: str) -> str:
    """The `User-agent: *` rules only — the sole part that binds a general client."""
    star, rules = False, []
    for ln in body.splitlines():
        low = ln.strip().lower()
        if low.startswith("user-agent:"):
            star = low.split(":", 1)[1].strip() == "*"
        elif star and (low.startswith("disallow:") or low.startswith("allow:")):
            rules.append(ln.strip())
    return " | ".join(rules[:6]) or "(no * block)"


def analyse(url: str, status: int, blob: bytes):
    """Does the payload contain scoreable TEXT, or only metadata?"""
    body = blob.decode("utf-8", "replace")
    out = {"bytes": len(blob), "note": "", "scoreable_text": False}
    if url.endswith("robots.txt") and status == 200:
        out["note"] = star_block(body)
        return out
    try:
        d = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        out["note"] = f"{len(blob):,} bytes of non-JSON"
        low = body.lower()
        if "login" in low and status == 200 and len(blob) > 50_000:
            out["note"] += " — looks like a login wall"
        return out
    if not isinstance(d, dict):
        out["note"] = "JSON, not an object"
        return out
    keys = sorted(d.keys())
    out["note"] = "keys " + ", ".join(keys[:9])
    for k in ("error", "detail", "message", "title"):
        if k in d and status >= 400:
            out["note"] += f" | {k}={str(d[k])[:90]}"
            break
    # the decisive test: is there prose long enough for a rubric to grade?
    for k, v in d.items():
        if k.lower() in TEXT_KEYS and isinstance(v, str) and len(v) > 40:
            out["scoreable_text"] = True
            out["note"] += f" | TEXT in '{k}' ({len(v)} chars)"
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for platform, label, url, why in PROBES:
        status, blob, secs, err = fetch(url)
        a = analyse(url, status, blob)
        rows.append({"platform": platform, "label": label, "url": url,
                     "status": status, "seconds": round(secs, 2),
                     "err": err, "why": why, **a})
        flag = "TEXT" if a["scoreable_text"] else ""
        print(f"  {platform:<10} {label:<34} {status:<4} "
              f"{a['bytes']:>7}B {flag:<5} {(err or a['note'])[:78]}")
        time.sleep(1.2)

    if args.json:
        print(json.dumps(rows, indent=1))

    out = os.path.join(db.REPORTS, "T4c_platform_probe.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# What each platform hands a keyless client\n\n")
        fh.write("Every row is a real request. The decisive column is **TEXT** "
                 "— whether the payload contains prose a rubric can grade. A "
                 "title and a thumbnail score nothing.\n\n")
        fh.write("| platform | probe | status | bytes | scoreable text | what came back |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['platform']} | {r['label']} | **{r['status']}** | "
                     f"{r['bytes']:,} | {'**YES**' if r['scoreable_text'] else 'no'} "
                     f"| {(r['err'] or r['note'])[:150]} |\n")
    print(f"\n  wrote {out}")
    con = db.connect()
    db.log(con, "probe_platforms",
           " ".join(f"{r['platform']}:{r['label'][:12]}={r['status']}" for r in rows))
    con.close()
    return rows


if __name__ == "__main__":
    main()
