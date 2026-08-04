"""Does a working social-media extractor already exist? Ask GitHub, don't guess.

`signal-github`'s corpus is Kalshi/Polymarket trading code and contains **zero**
social-media extractors — checked, 8 hits and all of them market scrapers. Its
own rule is then to run retrieval with new terms. That project belongs to
another session and one is running in it, so this asks the same question from
here instead of editing their queries.

The question is NOT "does a scraper exist" — of course one does, for everything.
It is three specific things, because those are what decide the kills recorded in
`reports/T4_feasibility.md`:

  1. TikTok / Instagram: can anything get a **transcript or caption text**
     without a paid API? The kill was on substance — a title, an author and a
     thumbnail cannot carry a cost side or a sample size. A tool that returns
     *transcripts* would reopen it.
  2. X: is there a free extractor, and **what is its terms position**? The kill
     was on terms, not capability. A tool that works does not change a rule that
     says do not.
  3. Reddit: what do people use now that robots.txt is `Disallow: /` and the
     `.json` endpoints 403?

Unauthenticated repo search: 10 requests/minute, no token, no account. Results
are recorded with stars, last push, archived flag and licence so a dead project
is visible as dead.

    python src/find_extractors.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
NOW = datetime.datetime.now(datetime.timezone.utc)
PACE = 7.0  # unauthenticated search is 10/min; stay under it

# (bucket, query). Ordered so the decisive ones run first.
QUERIES = [
    ("tiktok_transcript", "tiktok transcript in:name,description,readme"),
    ("tiktok_subtitle", "tiktok subtitles OR captions scraper in:name,description"),
    ("tiktok_general", "tiktok scraper in:name,description stars:>200"),
    ("instagram_caption", "instagram caption scraper in:name,description"),
    ("instagram_general", "instagram scraper in:name,description stars:>500"),
    ("x_free", "twitter OR x scraper no api in:name,description stars:>500"),
    ("x_general", "twitter scraper in:name,description stars:>1000"),
    ("reddit_current", "reddit scraper OR api wrapper in:name,description stars:>300"),
]


def search(q: str, per_page: int = 20):
    url = ("https://api.github.com/search/repositories?"
           + urllib.parse.urlencode({"q": q, "per_page": per_page,
                                     "sort": "stars", "order": "desc"}))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read()).get("items") or []
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}: {e.read()[:160].decode('utf-8','replace')}")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"    {type(e).__name__}: {e}")
        return []
    finally:
        time.sleep(PACE)


def age_days(iso: str):
    if not iso:
        return None
    try:
        return (NOW - datetime.datetime.fromisoformat(
            iso.replace("Z", "+00:00"))).days
    except ValueError:
        return None


def main():
    rows = []
    for bucket, q in QUERIES:
        print(f"  {bucket}: {q}", flush=True)
        for it in search(q):
            d = age_days(it.get("pushed_at"))
            rows.append({
                "bucket": bucket,
                "full_name": it["full_name"],
                "stars": it.get("stargazers_count"),
                "pushed_days": d,
                "archived": bool(it.get("archived")),
                "license": ((it.get("license") or {}) or {}).get("spdx_id") or "",
                "desc": (it.get("description") or "")[:200],
                "lang": it.get("language") or "",
            })
        print(f"    {len([r for r in rows if r['bucket']==bucket])} repos",
              flush=True)

    out = os.path.join(db.REPORTS, "T4b_existing_extractors.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Do social-media extractors already exist?\n\n")
        fh.write(f"GitHub repo search, unauthenticated, {NOW:%Y-%m-%d} UTC. "
                 "Stars are recorded because search ranks by them, **not because "
                 "they mean anything** — `signal-github` measured "
                 "`rho(stars, substance) = -0.007, p = 0.73` at n = 2,260.\n\n")
        fh.write("**Existence is not the question.** Scrapers exist for "
                 "everything. The kills in `T4_feasibility.md` rest on two "
                 "separate grounds and a tool only reopens one of them:\n\n"
                 "- **X was killed on TERMS** (`robots.txt` `Disallow: /`, API "
                 "401 without a paid key). A working scraper does not change a "
                 "rule that says do not.\n"
                 "- **TikTok and Instagram were killed on SUBSTANCE** — measured, "
                 "not assumed: sub-minute video clears `youtube-signal`'s "
                 "substance gate at 31.6% [19.1, 47.5] against 66.3% "
                 "[61.9, 70.3] at 10–30 minutes. A tool that returns "
                 "**transcripts** would reopen that; one that returns a title "
                 "and a thumbnail would not.\n\n")
        for bucket, _q in QUERIES:
            sel = [r for r in rows if r["bucket"] == bucket]
            if not sel:
                continue
            fh.write(f"## {bucket}\n\n")
            fh.write("| repo | ★ | last push | archived | licence | lang | what it says |\n")
            fh.write("|---|---|---|---|---|---|---|\n")
            for r in sel[:12]:
                pd = f"{r['pushed_days']}d" if r["pushed_days"] is not None else "?"
                fh.write(f"| [{r['full_name']}](https://github.com/{r['full_name']}) "
                         f"| {r['stars']} | {pd} | "
                         f"{'YES' if r['archived'] else ''} | {r['license']} | "
                         f"{r['lang']} | {r['desc']} |\n")
            fh.write("\n")
    print(f"\n  {len(rows)} repos across {len(QUERIES)} queries")
    print(f"  wrote {out}")
    con = db.connect()
    db.log(con, "find_extractors", f"queries={len(QUERIES)} repos={len(rows)}")
    con.close()
    return rows


if __name__ == "__main__":
    main()
