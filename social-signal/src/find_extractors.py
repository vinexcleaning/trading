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


class SearchRefused(RuntimeError):
    """The search did not happen. NOT the same as finding nothing."""


def search(q: str, per_page: int = 20, retries: int = 1):
    """Return the hit list, or raise `SearchRefused`.

    **This used to return `[]` on a genuine empty result, on an HTTP error and
    on a network error — three different worlds, one return value.** This
    function's whole job is answering *"does an extractor for X already
    exist?"*, which is an absence question, so a GitHub **403 rate-limit
    refusal was indistinguishable from "no such tool exists"** and would have
    been written up as one.

    That is `GUARDS.md` #25, and the `reopen` audit aimed it at this folder
    specifically: *"if any extractor records 'no results' without recording the
    status code and a second attempt, it can manufacture exactly this."* It
    could, and it did neither.

    **Printing the error was not a fix.** Every count in every report is built
    from the return value; a human reading a log later is not a data structure.
    So the refusal now raises, and the caller has to decide what to write down.

    Also: **one retry**, because the measurement behind #25 is that ATP
    returned 200 and then 403 to the identical request a minute apart.
    """
    url = ("https://api.github.com/search/repositories?"
           + urllib.parse.urlencode({"q": q, "per_page": per_page,
                                     "sort": "stars", "order": "desc"}))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/vnd.github+json"})
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                payload = json.loads(r.read())
                # An empty `items` here IS a real zero: the server answered.
                return payload.get("items") or []
        except urllib.error.HTTPError as e:
            body = e.read()[:160].decode("utf-8", "replace")
            last = f"HTTP {e.code}: {body}"
            print(f"    {last}")
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            print(f"    {last}")
        finally:
            time.sleep(PACE)
        if attempt < retries:
            print(f"    retrying once — a refusal and a real zero look "
                  f"identical, so one attempt is not evidence")
            time.sleep(PACE * 4)
    raise SearchRefused(f"{q!r} was refused, not answered ({last})")


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
    refused = []          # queries that were NOT answered — never counted as 0
    for bucket, q in QUERIES:
        print(f"  {bucket}: {q}", flush=True)
        try:
            hits = search(q)
        except SearchRefused as e:
            # **Recorded, not swallowed, and never merged into the results.**
            # A refused query with 0 rows and an answered query with 0 rows are
            # different facts, and only one of them supports "nothing exists".
            print(f"    REFUSED — this query contributes NO evidence: {e}")
            refused.append((bucket, q, str(e)))
            continue
        for it in hits:
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
        # **The refused queries go at the TOP, not in a footnote.** A reader
        # who sees "0 results" for a bucket has to know whether the question
        # was asked and answered, or never asked at all. GUARDS #25.
        if refused:
            fh.write(f"## ⚠ {len(refused)} of {len(QUERIES)} queries were "
                     f"REFUSED, not answered\n\n")
            fh.write("**These contribute no evidence in either direction.** A "
                     "refused query returning nothing and an answered query "
                     "returning nothing are different facts, and only the "
                     "second one supports an absence claim.\n\n")
            for bucket, q, err in refused:
                fh.write(f"- **{bucket}** — `{q}` — {err}\n")
            fh.write("\n")
        else:
            fh.write(f"**All {len(QUERIES)} queries were answered** (no "
                     "refusals), so a bucket with no rows below means the "
                     "search really did come back empty.\n\n")

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
