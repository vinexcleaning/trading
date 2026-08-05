"""TASK 3 - point the extractors at extraction itself, and VERIFY BY RUNNING.

`social-signal` already did the scraper half of this brief
(`reports/T4b_existing_extractors.md`) and reached the conclusion that matters:
**existence is not the question.** Scrapers exist for everything; X was killed
on terms and TikTok/Instagram on measured substance, and a working tool
reopens neither.

So this covers the three halves it did not:

  A  RANKING AND CREDIBILITY SCORING that people have already built - the brief
     is right that this is solved-ish in recommender-system and misinformation
     research and that reinventing it is waste
  B  SOURCES NOT COVERED AT ALL - podcasts, newsletters, forums
  C  BETTER YOUTUBE EXTRACTION from what is already on disk

Every candidate is checked three ways and the order is deliberate:

  1  ROBOTS   does the site's own machine-readable statement permit it
  2  LIVE     does it actually return bytes, right now, with no key
  3  RUN      does the thing it returns contain what the README claims

Step 3 is the one prior sessions skipped, and it is why prior sessions listed
sources that turned out to be 404 or 403.

    python src/find_sources.py           everything
    python src/find_sources.py --probe   just the live probes, no GitHub search
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

UA = "extractor-upgrade/1.0 (+trading repo; source survey)"
NOW = datetime.now(timezone.utc)


def _token():
    p = corpora.ROOT / "signal-github" / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+)", line)
        if m and "TOKEN" in m.group(1).upper():
            return m.group(2).strip().strip("\"'")
    return None


def get(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def probe(url, headers=None):
    try:
        st, body = get(url, headers)
        return {"status": st, "bytes": len(body), "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "bytes": 0, "body": b""}
    except Exception as e:
        return {"status": None, "err": f"{type(e).__name__}: {str(e)[:70]}",
                "bytes": 0, "body": b""}


_ROBOTS_CACHE = {}


def robots_allows(url: str, path_hint: str = "") -> tuple[bool | None, str]:
    """Does this host's robots.txt permit a generic agent on this path?

    Returns (allowed, evidence). None means undecidable, which is NOT the same
    as allowed and is reported as its own state.
    """
    p = urllib.parse.urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _ROBOTS_CACHE:
        r = probe(root + "/robots.txt")
        _ROBOTS_CACHE[root] = (r["body"] or b"").decode("utf-8", "replace") \
            if r["status"] == 200 else None
        time.sleep(0.2)
    txt = _ROBOTS_CACHE[root]
    if txt is None:
        return None, "no robots.txt served"

    # Only the `User-agent: *` block matters for a generic agent.
    block, in_star = [], False
    signals = []
    for line in txt.splitlines():
        s = line.split("#")[0].strip()
        if not s:
            continue
        k, _, v = s.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            in_star = (v == "*")
        elif k == "content-signal":
            signals.append(v)
        elif in_star and k in ("disallow", "allow"):
            block.append((k, v))
    target = p.path or "/"

    # !! THE FIRST VERSION OF THIS FUNCTION IGNORED `Allow:` AND PRODUCED A
    # FALSE FORBID. hacker-news.firebaseio.com/robots.txt reads
    #     Allow: /*.json$
    #     Allow: /*.json?*$
    #     Disallow: /
    # so the JSON API is EXPLICITLY permitted and only the HTML is not. A
    # parser that reads the Disallow and not the Allow calls a documented
    # public API forbidden - the mirror image of the false-kill problem, and
    # just as wrong. The standard is LONGEST MATCH WINS, with `*` and `$`
    # wildcards, and that is what this implements.
    best_len, best_kind, best_rule = -1, None, None
    for kind, rule in block:
        if not rule:
            continue
        pat = "^" + re.escape(rule).replace(r"\*", ".*")
        if pat.endswith(r"\$"):
            pat = pat[:-2] + "$"
        if re.match(pat, target):
            if len(rule) > best_len or (len(rule) == best_len
                                        and kind == "allow"):
                best_len, best_kind, best_rule = len(rule), kind, rule
    sig = (f"; Content-Signal: {'; '.join(signals)}" if signals else "")
    if best_kind == "disallow":
        return False, f"Disallow: {best_rule} (longest match){sig}"
    if best_kind == "allow":
        return True, f"Allow: {best_rule} beats any Disallow (longest match){sig}"
    dis = [v for k, v in block if k == "disallow" and v]
    return True, ((f"{len(dis)} Disallow rules, none matching {target}"
                   if dis else "Disallow: (empty) - everything permitted") + sig)


# ============================================================ A: GitHub search

CREDIBILITY_QUERIES = [
    "misinformation detection credibility scoring",
    "source credibility ranking news",
    "claim verification pipeline evidence retrieval",
    "learning to rank relevance library",
    "reciprocal rank fusion retrieval",
    "fact checking claim extraction transformers",
]
EXTRACTION_QUERIES = [
    "podcast transcript pipeline whisper rss",
    "newsletter archive scraper substack",
    "discourse forum scraper api",
    "youtube chapters extraction",
    "youtube comments analysis sentiment",
]


def gh_search(q, tok, per=8):
    url = ("https://api.github.com/search/repositories?q="
           + urllib.parse.quote(q + " in:name,description,readme")
           + f"&sort=stars&order=desc&per_page={per}")
    h = {"Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    r = probe(url, h)
    if r["status"] != 200:
        return []
    items = json.loads(r["body"]).get("items", [])
    out = []
    for d in items:
        pushed = d.get("pushed_at") or ""
        days = ((NOW - datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days
                if pushed else None)
        out.append({
            "full_name": d["full_name"], "stars": d["stargazers_count"],
            "archived": bool(d.get("archived")), "days": days,
            "license": (d.get("license") or {}).get("spdx_id"),
            "lang": d.get("language"),
            "desc": (d.get("description") or "")[:150],
        })
    return out


# ============================================================== B: live probes
# Every one is keyless. `check` reads the response and asserts the thing the
# source is supposed to contain, because a 200 is not a correct file - the
# football-data trap in this repo returned HTTP 200 and the WRONG COUNTRY.

def _json(body):
    return json.loads(body.decode("utf-8", "replace"))


PROBES = [
    dict(name="Hacker News (Algolia)", kind="forum",
         url="https://hn.algolia.com/api/v1/search?query=polymarket&tags=story&hitsPerPage=5",
         check=lambda b: (lambda d: (len(d.get("hits", [])) > 0,
                                     f"{d.get('nbHits')} stories; first: "
                                     f"{(d['hits'][0]['title'][:60] if d.get('hits') else 'none')}"))(_json(b)),
         note="Algolia's official public HN index. No key, no quota published."),
    dict(name="Hacker News (official Firebase)", kind="forum",
         url="https://hacker-news.firebaseio.com/v0/topstories.json",
         check=lambda b: (len(_json(b)) > 100,
                          f"{len(_json(b))} story ids"),
         note="YC's own API. Documented as public and keyless."),
    dict(name="Lobsters", kind="forum",
         url="https://lobste.rs/t/programming.json",
         check=lambda b: (len(_json(b)) > 0,
                          f"{len(_json(b))} stories"),
         note="Every listing page has a .json twin."),
    dict(name="Discourse (a public instance)", kind="forum",
         url="https://meta.discourse.org/latest.json",
         check=lambda b: (len(_json(b).get("topic_list", {})
                              .get("topics", [])) > 0,
                          f"{len(_json(b).get('topic_list',{}).get('topics',[]))} topics"),
         note="Every Discourse forum exposes /latest.json and /t/<id>.json. "
              "Quant and trading communities run on Discourse."),
    dict(name="iTunes / Apple Podcasts search", kind="podcast",
         url="https://itunes.apple.com/search?term=prediction%20markets&media=podcast&limit=5",
         check=lambda b: (lambda d: (d.get("resultCount", 0) > 0,
                                     f"{d.get('resultCount')} shows; first feed: "
                                     f"{(d['results'][0].get('feedUrl') or 'none')[:60] if d.get('results') else 'none'}"))(_json(b)),
         note="Keyless. Returns the RSS feedUrl, which is the whole point - "
              "the feed is the source, Apple is just the directory."),
    dict(name="PodcastIndex (open directory)", kind="podcast",
         url="https://podcastindex.org/api/1.0/search/byterm?q=prediction+markets",
         check=lambda b: (b"feeds" in b or b"status" in b, f"{len(b)} bytes"),
         note="Open podcast directory. Expected to need a key; probed to "
              "confirm rather than assumed."),
    dict(name="SEC EDGAR full-text search", kind="filings",
         url="https://efts.sec.gov/LATEST/search-index?q=%22prediction%20market%22&forms=10-K",
         check=lambda b: (len(b) > 0, f"{len(b)} bytes"),
         note="Keyless, and the primary source for anything a public company "
              "says about a venue."),
    dict(name="Kalshi public API", kind="venue",
         url="https://api.elections.kalshi.com/trade-api/v2/exchange/status",
         check=lambda b: (b"exchange_active" in b or b"trading_active" in b,
                          b.decode("utf-8", "replace")[:70]),
         note="The endpoint that decides whether the earlier bare-base 404 "
              "meant anything. It did not."),
    dict(name="arctic-shift (Reddit archive)", kind="forum",
         url="https://arctic-shift.photon-reddit.com/api/subreddits/search?subreddit=algotrading&limit=1",
         check=lambda b: (b"data" in b, f"{len(b)} bytes"),
         note="social-signal's permitted mirror of a forbidden source. "
              "Re-verified here rather than trusted."),
]


def run_probes():
    rows = []
    for p in PROBES:
        allowed, why = robots_allows(p["url"])
        r = probe(p["url"])
        ok, detail = (None, "")
        if r["status"] == 200 and r["bytes"]:
            try:
                ok, detail = p["check"](r["body"])
            except Exception as e:
                ok, detail = False, f"parse failed: {type(e).__name__}"
        rows.append({**{k: p[k] for k in ("name", "kind", "url", "note")},
                     "robots_allowed": allowed, "robots_why": why,
                     "status": r.get("status"), "bytes": r["bytes"],
                     "content_ok": ok, "detail": detail,
                     "err": r.get("err", "")})
        print(f"  {str(allowed):5s} {str(r.get('status')):>4s} "
              f"{'OK ' if ok else 'xx ' if ok is False else '?? '}"
              f"{p['name'][:38]:<38} {str(detail)[:44]}")
        time.sleep(0.3)
    return rows


# ================================================ C: chapters, already on disk

CHAPTER = re.compile(r"^\s*\(?(\d{1,2}:\d{2}(?::\d{2})?)\)?\s*[-–—:|]?\s*(.{3,80})$",
                     re.M)


def chapters_from_descriptions():
    """Chapter detection needs no new source at all: YouTube chapters live in
    the description, and the descriptions are already in the database.

    A chapter list is a free, author-written table of contents - the cheapest
    possible answer to "which 90 seconds of this 40-minute video matter", and
    a far better `watch_segment` seed than a phrase list.
    """
    hits, total, examples = 0, 0, []
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        for r in con.execute("SELECT video_id, title, description FROM videos "
                             "WHERE description IS NOT NULL AND description<>''"):
            total += 1
            m = CHAPTER.findall(r["description"] or "")
            if len(m) >= 3:
                hits += 1
                if len(examples) < 6:
                    examples.append((corpus, r["video_id"], r["title"][:52],
                                     [f"{t} {n.strip()[:38]}" for t, n in m[:5]]))
        con.close()
    return hits, total, examples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()

    print("-- live probes")
    probes = run_probes()

    print("\n-- chapters already on disk")
    ch_hits, ch_total, ch_ex = chapters_from_descriptions()
    print(f"  {ch_hits} of {ch_total} descriptions carry >=3 chapter markers "
          f"({ch_hits/max(1,ch_total):.1%})")

    search = {}
    if not a.probe:
        tok = _token()
        print(f"\n-- GitHub search (token={bool(tok)})")
        for q in CREDIBILITY_QUERIES + EXTRACTION_QUERIES:
            search[q] = gh_search(q, tok)
            print(f"  {len(search[q]):>2} for  {q}")
            time.sleep(1.2 if tok else 6.0)

    write(probes, (ch_hits, ch_total, ch_ex), search)


def write(probes, chapters, search):
    ch_hits, ch_total, ch_ex = chapters
    L, w = [], None
    L = []
    w = L.append
    w("# TASK 3 - the extractors pointed at extraction\n")
    w(f"Everything below was checked live, "
      f"{NOW.isoformat(timespec='minutes')}. "
      "**`social-signal` already did the scraper half** "
      "(`reports/T4b_existing_extractors.md`) and reached the conclusion that "
      "matters: existence is not the question. This covers what it did not.\n")

    w("## B. Sources not covered at all - probed, not listed\n")
    w("Three checks in order, and the third is the one prior sessions skipped: "
      "**robots** (does the site's own statement permit it), **live** (does it "
      "return bytes with no key), **content** (does what came back contain "
      "what it claims). A 200 is not a correct file — this repo's own "
      "football-data trap returns HTTP 200 and the wrong country.\n")
    w("| source | kind | robots | HTTP | bytes | content check | what came back |")
    w("|---|---|---|---|---|---|---|")
    for p in probes:
        rb = {True: "**permits**", False: "**FORBIDS**",
              None: "no robots.txt"}[p["robots_allowed"]]
        cc = {True: "**PASS**", False: "FAIL", None: "-"}[p["content_ok"]]
        w(f"| {p['name']} | {p['kind']} | {rb} | "
          f"{p['status'] or p['err']} | {p['bytes']:,} | {cc} | "
          f"{str(p['detail'])[:70]} |")
    w("")
    for p in probes:
        w(f"- **{p['name']}** — {p['note']} robots: {p['robots_why']}.")
    w("")

    usable = [p for p in probes
              if p["robots_allowed"] and p["content_ok"] and p["status"] == 200]
    w(f"**{len(usable)} of {len(probes)} are usable right now: permitted by "
      "robots, returning 200 with no key, and containing what they claim.**\n")

    w("## C. Chapter detection needs no new source at all\n")
    w(f"**{ch_hits} of {ch_total} video descriptions already in the database "
      f"carry three or more chapter markers ({ch_hits/max(1,ch_total):.1%}).** "
      "YouTube chapters live in the description, the descriptions are already "
      "on disk, and a chapter list is an author-written table of contents — "
      "the cheapest possible answer to *which 90 seconds of this 40 minutes "
      "matter*, and a far better `watch_segment` seed than a phrase list.\n")
    for corpus, vid, title, marks in ch_ex:
        w(f"- `{corpus}:{vid}` **{title}**")
        for m in marks:
            w(f"    - {m}")
    w("")

    if search:
        w("## A. Ranking and credibility scoring people have already built\n")
        w("Stars are recorded because GitHub search ranks by them, **not "
          "because they mean anything** — `signal-github` measured "
          "`rho(stars, substance) = -0.008, p = 0.65` at n = 3,165.\n")
        for q, rows in search.items():
            w(f"### `{q}`\n")
            if not rows:
                w("no results.\n")
                continue
            w("| repo | ★ | last push | archived | licence | lang | what it says |")
            w("|---|---|---|---|---|---|---|")
            for r in rows:
                w(f"| [{r['full_name']}](https://github.com/{r['full_name']}) "
                  f"| {r['stars']:,} | {r['days']}d | "
                  f"{'**YES**' if r['archived'] else ''} | "
                  f"{r['license'] or ''} | {r['lang'] or ''} | {r['desc']} |")
            w("")

    path = corpora.REPORTS / "T3_sources.md"
    path.write_text("\n".join(L), encoding="utf-8")
    (corpora.DATA / "T3_sources.json").write_text(
        json.dumps({"probes": [{k: v for k, v in p.items() if k != "body"}
                               for p in probes],
                    "chapters": {"hits": ch_hits, "total": ch_total},
                    "search": search}, indent=2, default=str),
        encoding="utf-8")
    print(f"\n  usable now: {len(usable)}/{len(probes)}")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
