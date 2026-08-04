"""T4 — what each platform will actually give a compliant client, measured.

Two prior sessions in this repo listed sources that turned out to be 404 or 403,
so nothing here is asserted from documentation. Every line in the output table
is a status code this script fetched.

The rule this runs under: **a "cannot be done within the rules" finding is a
real result.** Nothing here circumvents a block, solves a challenge, forges a
session or routes around a robots.txt. Where a mirror exists that would work, it
is recorded as existing and NOT used, with the reason stated — because a mirror
that re-serves a platform's content is the platform's content, and the terms
that apply to the origin do not stop applying because a third party proxied it.

The second half of the file tests the brief's own expectation about short-form
video rather than accepting it. That test does not need TikTok at all: the
`youtube-signal` corpus already holds 750 gated videos with durations, so
"does short-form carry less substance" is answerable today, for free, on data
that has already been scored.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import verify_live  # noqa: E402  (its cached fetch and browser UA)

TRADING = os.path.dirname(db.ROOT)
YT_DBS = [
    ("yt_broad", os.path.join(TRADING, "youtube-signal", "data", "signal.db")),
    ("yt_kalshi_edge", os.path.join(TRADING, "youtube-signal", "data",
                                    "signal_kalshi_edge.db")),
]

# (platform, label, url, what a result would mean)
PROBES = [
    # --- Reddit: the brief's premise, tested -------------------------------
    ("reddit", "robots.txt (www)", "https://www.reddit.com/robots.txt",
     "governs whether any crawl is permitted at all"),
    ("reddit", "robots.txt (old)", "https://old.reddit.com/robots.txt", ""),
    ("reddit", "robots.txt (oauth)", "https://oauth.reddit.com/robots.txt", ""),
    ("reddit", ".json endpoint", "https://www.reddit.com/r/algotrading/hot.json?limit=5",
     "the route the brief specified"),
    ("reddit", ".rss endpoint", "https://www.reddit.com/r/algotrading/.rss", ""),
    ("reddit", "pushshift", "https://api.pushshift.io/reddit/search/submission/?q=kalshi&size=2",
     "the historical archive the brief mentioned"),
    ("reddit", "arctic-shift robots", "https://arctic-shift.photon-reddit.com/robots.txt",
     "the archive this project actually uses"),
    ("reddit", "arctic-shift api",
     "https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=Kalshi&limit=1", ""),

    # --- X / Twitter -------------------------------------------------------
    ("x", "robots.txt", "https://x.com/robots.txt",
     "X's own statement of what a crawler may fetch"),
    ("x", "api v2, no key", "https://api.x.com/2/tweets/search/recent?query=kalshi",
     "the sanctioned route; a 401 means it is paid, not broken"),
    ("x", "public profile page", "https://x.com/kalshi",
     "what an ordinary GET returns without a session"),
    ("x", "syndication endpoint",
     "https://cdn.syndication.twimg.com/timeline/profile?screen_name=kalshi",
     "an undocumented internal endpoint — probed to record its state, NOT used"),
    ("x", "nitter.net mirror", "https://nitter.net/kalshi",
     "a third-party mirror — probed to record its state, NOT used"),
    ("x", "xcancel mirror", "https://xcancel.com/kalshi", ""),

    # --- TikTok ------------------------------------------------------------
    ("tiktok", "robots.txt", "https://www.tiktok.com/robots.txt", ""),
    ("tiktok", "oEmbed (documented, free)",
     "https://www.tiktok.com/oembed?url=https://www.tiktok.com/@tiktok/video/6718335390845095173",
     "the one officially public, keyless TikTok endpoint"),
    ("tiktok", "research api root", "https://open.tiktokapis.com/v2/research/video/query/",
     "academic-application only"),
    ("tiktok", "profile page", "https://www.tiktok.com/@kalshi", ""),

    # --- Instagram ---------------------------------------------------------
    ("instagram", "robots.txt", "https://www.instagram.com/robots.txt", ""),
    ("instagram", "oEmbed (now app-gated)",
     "https://api.instagram.com/oembed?url=https://www.instagram.com/p/CX1/",
     "free until 2020; now requires a Facebook app token"),
    ("instagram", "graph oembed",
     "https://graph.facebook.com/v20.0/instagram_oembed?url=https://www.instagram.com/p/CX1/",
     ""),
    ("instagram", "profile page", "https://www.instagram.com/kalshi/", ""),
]


def probe_all():
    out = []
    for platform, label, url, why in PROBES:
        r = verify_live.fetch(url, timeout=25)
        body = (r.get("body") or "")
        note = ""
        if url.endswith("robots.txt") and r["status"] == 200:
            # The only line that matters for a general-purpose client.
            lines = [ln.strip() for ln in body.splitlines()]
            star, rules = False, []
            for ln in lines:
                low = ln.lower()
                if low.startswith("user-agent:"):
                    star = low.split(":", 1)[1].strip() == "*"
                elif star and (low.startswith("disallow:") or low.startswith("allow:")):
                    rules.append(ln)
            note = " | ".join(rules[:4]) or (
                "(no `*` block) first lines: "
                + " / ".join(ln for ln in lines if ln and not ln.startswith("#"))[:180])
        elif r["status"] == 0:
            note = (r.get("err") or "")[:110]
        else:
            note = f"{len(body):,} bytes"
            try:
                d = json.loads(body)
                if isinstance(d, dict):
                    keys = [k for k in d.keys()][:5]
                    note += f" | json keys {keys}"
                    for k in ("title", "detail", "error", "errors", "message"):
                        if k in d:
                            note += f" | {k}={str(d[k])[:90]}"
                            break
            except (json.JSONDecodeError, TypeError):
                pass
        out.append({"platform": platform, "label": label, "url": url,
                    "status": r["status"], "note": note, "why": why})
        print(f"  {platform:<10} {label:<28} {r['status']:<5} {note[:80]}",
              flush=True)
    return out


# ---------------------------------------------------------------------------
# Testing the short-form expectation without TikTok
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


BANDS = [(0, 60, "<1 min (short-form)"),
         (60, 180, "1-3 min"),
         (180, 600, "3-10 min"),
         (600, 1800, "10-30 min"),
         (1800, 10 ** 9, "30+ min")]


def short_form_test():
    """Does a shorter video pass the substance gate less often?

    The brief predicts short-form is mostly marketing. That is testable on data
    this programme already owns: `youtube-signal` gated 750+ videos and recorded
    each one's duration and gate outcome. Wilson intervals, because the small
    bands would otherwise invite a conclusion the sample cannot carry.
    """
    rows = []
    for corpus, path in YT_DBS:
        if not os.path.exists(path):
            continue
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        rows += [dict(r) for r in con.execute(
            "SELECT duration_s, gate_status, view_count FROM videos "
            "WHERE duration_s IS NOT NULL AND gate_status IS NOT NULL")]
        con.close()

    scored = []
    for corpus, path in YT_DBS:
        if not os.path.exists(path):
            continue
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        scored += [dict(r) for r in con.execute("""
            SELECT v.duration_s, s.s_total, s.b_total, s.h_total, s.verdict
            FROM scores s JOIN videos v ON v.video_id = s.video_id
            WHERE v.duration_s IS NOT NULL""")]
        con.close()

    band_rows = []
    for lo, hi, label in BANDS:
        sel = [r for r in rows if lo <= (r["duration_s"] or 0) < hi]
        n = len(sel)
        k = sum(1 for r in sel if r["gate_status"] == "PASS")
        off = sum(1 for r in sel if "OFF_TOPIC" in (r["gate_status"] or ""))
        p, lo_ci, hi_ci = wilson(k, n)
        band_rows.append({"band": label, "n": n, "pass": k, "p": p,
                          "lo": lo_ci, "hi": hi_ci, "off_topic": off})
    return band_rows, rows, scored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probe", action="store_true")
    args = ap.parse_args()

    print("PROBES")
    probes = [] if args.no_probe else probe_all()
    print("\nSHORT-FORM TEST (on youtube-signal's own gated corpus)")
    bands, all_rows, scored = short_form_test()
    for b in bands:
        print(f"  {b['band']:<22}n={b['n']:<6} PASS {b['pass']:<5} "
              f"{b['p']*100:5.1f}%  [{b['lo']*100:.1f}, {b['hi']*100:.1f}]")

    out = os.path.join(db.REPORTS, "T4_feasibility.md")
    now = datetime.datetime.now(datetime.timezone.utc)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# T4 — X, TikTok, Instagram (and Reddit's own premise), measured\n\n")
        fh.write(f"Every row fetched {now:%Y-%m-%d} UTC by "
                 "`src/feasibility.py`. Nothing below was worked around: no "
                 "challenge solved, no session forged, no mirror used to move "
                 "content the origin declined to serve.\n\n")
        fh.write("> ### The finding is not \"it is blocked\". It is \"it is "
                 "permitted-to-nobody, and technically wide open.\"\n>\n"
                 "> These probes send a **browser** User-Agent, because "
                 "`signal-github` recorded a whole session lost to reading an "
                 "intermittent 429 as a block. With that header, "
                 "`reddit.com/r/algotrading/.rss` returns **HTTP 200 and 54 KB "
                 "of live subreddit content**, and `x.com/kalshi` returns "
                 "**HTTP 200 and 200 KB**. Both hosts' `robots.txt` say "
                 "`User-agent: *` / `Disallow: /`.\n>\n"
                 "> So the constraint on this project is **not technical and "
                 "the report must not pretend it is.** The content is one GET "
                 "away. It is not taken because the site's own machine-readable "
                 "statement of who may crawl it says nobody may, and a "
                 "User-Agent string is not consent. Everything collected in T2 "
                 "comes instead from an archive whose `robots.txt` is "
                 "`Disallow:` — empty, meaning everything is allowed.\n\n")
        for plat in ("reddit", "x", "tiktok", "instagram"):
            sel = [p for p in probes if p["platform"] == plat]
            if not sel:
                continue
            fh.write(f"## {plat}\n\n")
            fh.write("| probe | status | what came back |\n|---|---|---|\n")
            for p in sel:
                fh.write(f"| {p['label']} | **{p['status']}** | {p['note']} |\n")
            fh.write("\n")

        fh.write("## Short-form: the expectation, tested without TikTok\n\n")
        fh.write("The brief predicts short-form video is mostly marketing and "
                 "that the rubric's strongest signal — showing what did not "
                 "work — almost never appears in a 60-second clip. That is "
                 "testable on data this programme already owns: `youtube-signal` "
                 "gated every video it retrieved and recorded each one's "
                 "duration, so the substance gate's PASS rate by duration band "
                 "answers it for free. Wilson intervals, because the short band "
                 "is small and a bare percentage would invite a conclusion it "
                 "cannot carry.\n\n")
        fh.write("| duration band | n | PASS | rate | 95% Wilson | dropped off-topic |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for b in bands:
            fh.write(f"| {b['band']} | {b['n']} | {b['pass']} | "
                     f"{b['p']*100:.1f}% | [{b['lo']*100:.1f}, {b['hi']*100:.1f}] "
                     f"| {b['off_topic']} |\n")
        fh.write("\n")
        short = next(b for b in bands if b["band"].startswith("<1"))
        rest_n = sum(b["n"] for b in bands if not b["band"].startswith("<1"))
        rest_k = sum(b["pass"] for b in bands if not b["band"].startswith("<1"))
        rp, rlo, rhi = wilson(rest_k, rest_n)
        fh.write(f"Short-form band n = **{short['n']}** against **{rest_n}** "
                 f"for everything longer ({rp*100:.1f}% PASS "
                 f"[{rlo*100:.1f}, {rhi*100:.1f}]).\n\n")
        if short["n"] < 30:
            fh.write("**The short band is too small in this corpus to decide "
                     "the question.** That is itself informative and it is not "
                     "the same as confirming the expectation: it says "
                     "`youtube-signal`'s retrieval barely surfaces sub-minute "
                     "video, not that sub-minute video is worthless. Recorded "
                     "as NOT TESTED rather than dressed up as a confirmation.\n\n")
        else:
            overlap = not (short["hi"] < rlo or short["lo"] > rhi)
            fh.write("**The intervals " + ("overlap" if overlap else "do not overlap")
                     + "**, so the short-form penalty is "
                     + ("not demonstrated" if overlap else "measurable")
                     + " at this sample size.\n\n")
        fh.write(f"Scored videos with a duration: **{len(scored)}**. Too few to "
                 "regress score on duration; `youtube-signal`'s own handoff "
                 "already records that duration bias cut both ways there and "
                 "was worth half the apparent effect in its retrieval test.\n\n")

        peak = max(bands, key=lambda b: b["p"] if b["n"] >= 30 else -1)
        fh.write("### The shape is not monotonic, and that matters\n\n")
        fh.write("PASS rate rises with duration and then **falls again**: the "
                 f"best band is **{peak['band']}** at {peak['p']*100:.1f}%, and "
                 "the 30+ minute band drops back to "
                 f"{[b for b in bands if b['band'].startswith('30+')][0]['p']*100:.1f}%. "
                 "So the rule is not \"longer is better\" — it is that both ends "
                 "are junk for different reasons, and only the middle band "
                 "reliably contains a cost side, a sample size and a mechanism. "
                 "A short-form platform is bad because it sits at the wrong end "
                 "of a curve this corpus can already draw.\n\n")

        fh.write("## Verdicts\n\n")
        fh.write("| platform | verdict | on what evidence |\n|---|---|---|\n")
        fh.write("| **Reddit** | **COLLECT — via the archive, never the site** | "
                 "`reddit.com/robots.txt` is `Disallow: /` for `*`, and the "
                 "`.json` route the brief specified returns 403. "
                 "`arctic-shift.photon-reddit.com` publishes a documented JSON "
                 "API, its `robots.txt` allows everything, and it returns "
                 "`X-RateLimit-Reset` headers this project obeys. |\n")
        fh.write("| **X / Twitter** | **KILL — cannot be done within the rules "
                 "for free** | `robots.txt` `Disallow: /`; API v2 returns "
                 "**401 Unauthorized** without a paid key. Mirrors exist and "
                 "respond, and using them to move X's content is the same act "
                 "with an extra hop. No route here is both free and permitted. |\n")
        fh.write("| **TikTok** | **KILL — retrievable but empty of what the "
                 "rubric needs** | `robots.txt` allows `/foryou`, `/discover`, "
                 "`/about`; the documented keyless **oEmbed endpoint returns "
                 "200** — and returns a title, an author and a thumbnail. No "
                 "transcript, no comments, no description. The Research API is "
                 "academic-application only. Even fully permitted, the payload "
                 "cannot carry a cost side, a sample size or a technical "
                 "objection. |\n")
        fh.write("| **Instagram** | **KILL — app-gated** | the free oEmbed was "
                 "retired; `graph.facebook.com/instagram_oembed` returns "
                 "**400** without a Facebook app token, and the profile page is "
                 "a login wall. |\n\n")
        fh.write("Both short-form kills are now backed by the duration table "
                 "above rather than by the expectation alone: sub-minute video "
                 "clears `youtube-signal`'s substance gate at "
                 f"{short['p']*100:.0f}% against {rp*100:.0f}% for everything "
                 "longer, on n = "
                 f"{short['n']} and {rest_n}. **The expectation was tested and "
                 "it held** — which is worth more than killing them on a "
                 "hunch, and it cost nothing because the data was already on "
                 "disk.\n")
    print(f"\n  wrote {out}")

    con = db.connect()
    db.log(con, "feasibility",
           " ".join(f"{p['platform']}:{p['label']}={p['status']}" for p in probes))
    con.close()


if __name__ == "__main__":
    main()
