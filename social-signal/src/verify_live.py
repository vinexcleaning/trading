"""Verify by fetching, not by finding a link.

Two prior sessions in this repo listed sources that turned out to be 404 or 403,
so nothing in this project treats "a URL was written down" as evidence that
anything is there. Every URL an entity carries gets fetched once, cached, and
recorded with its status code.

Three checks, cheapest first:

  site    a plain GET. 200 means something answers; it does not mean the
          product exists, and that distinction is kept in the stance names.
  github  api.github.com/repos/<owner>/<repo> — archived, pushed_at, stars.
          Unauthenticated is 60/hour, which is far more than this needs.
  pypi    pypi.org/pypi/<name>/json — is the package real, and when was it
          last released.

`NO_URL_RECORDED` is a verdict about the *upstream corpus*, not about the tool.
It is reported separately and loudly, because a reputation table cannot check
what it was never told the address of.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import norm  # noqa: E402

CACHE = os.path.join(db.ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)

# A real browser UA. signal-github recorded that kalshi.com returns an
# intermittent 429 to a bot UA and serves the same document to a browser one;
# the 429 was mistaken for a block for a whole session.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
NOW = datetime.datetime.now(datetime.timezone.utc)

PACE = 1.2  # seconds between live requests; back off, never hammer


def _cache_path(url: str) -> str:
    return os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest()[:20] + ".json")


def fetch(url: str, timeout: int = 25, accept: str = "*/*", retries: int = 1):
    cp = _cache_path(url)
    if os.path.exists(cp):
        try:
            with open(cp, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    out = {"url": url, "status": 0, "body": "", "final_url": url, "err": ""}
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": accept,
                          "Accept-Language": "en-GB,en;q=0.9"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(400_000)
                out.update(status=r.status, final_url=r.geturl(),
                           body=body.decode("utf-8", "replace"))
            break
        except urllib.error.HTTPError as e:
            out.update(status=e.code,
                       body=e.read(20_000).decode("utf-8", "replace"))
            if e.code == 429 and attempt < retries:
                time.sleep(8)
                continue
            break
        except Exception as e:  # noqa: BLE001 — a dead host is a real answer
            out.update(status=0, err=f"{type(e).__name__}: {e}")
            if attempt < retries:
                time.sleep(3)
                continue
            break
    time.sleep(PACE)
    with open(cp, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    return out


def check_github(full_name: str):
    r = fetch(f"https://api.github.com/repos/{full_name}",
              accept="application/vnd.github+json")
    if r["status"] == 404:
        return "GONE", "GitHub returns 404 for the repo the tool was named with"
    if r["status"] != 200:
        return "UNKNOWN", f"GitHub API returned {r['status']}"
    try:
        d = json.loads(r["body"])
    except json.JSONDecodeError:
        return "UNKNOWN", "unparseable GitHub response"
    pushed = d.get("pushed_at") or ""
    days = None
    if pushed:
        try:
            days = (NOW - datetime.datetime.fromisoformat(
                pushed.replace("Z", "+00:00"))).days
        except ValueError:
            pass
    stars = d.get("stargazers_count")
    if d.get("archived"):
        return "ARCHIVED", (f"archived by its maintainer; {stars}*, last push "
                            f"{days}d ago")
    if days is not None and days > 730:
        return "STALE", f"last push {days}d ago (>24 months); {stars}*"
    if days is not None and days > 365:
        return "QUIET", f"last push {days}d ago; {stars}*"
    return "ALIVE", f"last push {days}d ago; {stars}*"


def check_pypi(pkg: str):
    r = fetch(f"https://pypi.org/pypi/{pkg}/json", accept="application/json")
    if r["status"] == 404:
        return "GONE", "no such package on PyPI"
    if r["status"] != 200:
        return "UNKNOWN", f"PyPI returned {r['status']}"
    try:
        d = json.loads(r["body"])
    except json.JSONDecodeError:
        return "UNKNOWN", "unparseable PyPI response"
    rels = d.get("releases") or {}
    dates = []
    for files in rels.values():
        for f in files:
            if f.get("upload_time_iso_8601"):
                dates.append(f["upload_time_iso_8601"])
    last = max(dates) if dates else ""
    ver = (d.get("info") or {}).get("version", "?")
    if last:
        try:
            days = (NOW - datetime.datetime.fromisoformat(
                last.replace("Z", "+00:00"))).days
        except ValueError:
            days = None
        if days is not None and days > 730:
            return "STALE", f"v{ver}, last release {days}d ago"
        return "ALIVE", f"v{ver}, last release {days}d ago, {len(rels)} versions"
    return "ALIVE", f"v{ver}, {len(rels)} versions, no release date"


# Parked / for-sale pages return 200 and are not a product. Cheap giveaways
# only; anything subtler is left to a human, not guessed at.
PARKED = re.compile(
    r"(domain (is )?(for sale|may be for sale)|buy this domain|"
    r"parked (free )?(at|by)|godaddy\.com/domainsearch|sedoparking|"
    r"this domain is (available|parked))", re.I)


def check_site(url: str):
    if not url.startswith("http"):
        url = "https://" + url
    host = norm.domain(url) or ""
    # An API *root* is supposed to 404. `api.exchange.coinbase.com/` has no
    # document at `/` and never did; recording that as GONE would be a fact
    # about REST conventions, not about the data source. Kept as its own stance
    # so it can never be read as a death.
    api_root = host.startswith("api.") or host.startswith("r2")

    r = fetch(url, accept="text/html,application/xhtml+xml")
    s = r["status"]
    err = r["err"] or ""
    if s == 0:
        # DNS failure is the strongest death signal available: the domain does
        # not resolve at all.
        if "getaddrinfo" in err:
            return "GONE", f"domain does not resolve ({err[:80]})"
        # A TLS failure needs splitting, because the two halves are facts about
        # different machines. "unable to get local issuer certificate" is this
        # box's trust store; reporting cnn.com as GONE on that basis would be a
        # measurement of our own CA bundle. "certificate has expired" is the
        # site's own certificate and is a real signal about the site.
        if "CERTIFICATE_VERIFY_FAILED" in err:
            if "expired" in err:
                return "BROKEN", "the site's TLS certificate has expired"
            return "TLS_UNVERIFIED", (
                "TLS verification failed for a reason that is about THIS "
                "machine's certificate store, not the site — not evidence of "
                "anything about the tool")
        return "GONE", f"no response: {err[:120]}"
    if s in (404, 410):
        if api_root:
            return "API_ROOT_404", (f"HTTP {s} at the API root — normal for a "
                                    "REST base URL, NOT evidence the API is dead")
        return "GONE", f"HTTP {s}"
    if s == 451:
        return "BLOCKED", "HTTP 451 — unavailable for legal reasons in this region"
    if s == 429:
        return "BLOCKED", "HTTP 429 — rate limited, retried once"
    if 400 <= s < 500:
        return "BLOCKED", f"HTTP {s} — present but refuses this client"
    if s >= 500:
        return "BROKEN", f"HTTP {s}"
    body = r["body"] or ""
    if PARKED.search(body[:20000]):
        return "PARKED", f"HTTP {s} but the page is a domain-parking placeholder"
    if len(body.strip()) < 512:
        return "THIN", (f"HTTP {s} with only {len(body)} bytes of body — "
                        "answers, but serves no document")
    return "LIVE", f"HTTP {s}, {len(body):,} bytes"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    con = db.connect()
    # Live stances are a classification of a cached response, and the
    # classifier changes. Old rows are dropped rather than merged, or a URL
    # reclassified from GONE to API_ROOT_404 keeps both and reads as a
    # contradiction with itself. The HTTP cache is untouched, so this costs
    # nothing.
    con.execute("DELETE FROM observations WHERE platform='live'")
    con.commit()
    ents = con.execute("SELECT * FROM entities ORDER BY display").fetchall()
    if args.limit:
        ents = ents[:args.limit]

    counts = collections.Counter()
    no_url = []
    rows = []
    for e in ents:
        url = (e["canonical_url"] or "").strip()
        repo = e["github_repo"]
        if not url and not repo:
            no_url.append(e["display"])
            counts["NO_URL_RECORDED"] += 1
            continue

        stance = note = kind = None
        if repo:
            stance, note = check_github(repo)
            kind = "github"
            target = f"github:{repo}"
        elif "pypi.org/project/" in url:
            pkg = url.rstrip("/").split("/")[-1]
            stance, note = check_pypi(pkg)
            kind = "pypi"
            target = f"pypi:{pkg}"
        elif norm.domain(url) == "github.com":
            owner = norm.github_owner(url)
            if owner:
                r = fetch(f"https://api.github.com/users/{owner}",
                          accept="application/vnd.github+json")
                if r["status"] == 200:
                    d = json.loads(r["body"])
                    stance, note = "ALIVE", (
                        f"GitHub account: {d.get('public_repos')} public repos, "
                        f"{d.get('followers')} followers")
                elif r["status"] == 404:
                    stance, note = "GONE", "GitHub account 404s"
                else:
                    stance, note = "UNKNOWN", f"GitHub API {r['status']}"
                kind, target = "github_user", f"github_user:{owner}"
            else:
                stance, note = "UNKNOWN", "bare github.com with no account or repo"
                kind, target = "site", url
        else:
            stance, note = check_site(url)
            kind, target = "site", url

        counts[stance] += 1
        db.add_observation(con, e["entity_id"], "live", kind, target, stance,
                           detail=note, evidence="")
        con.execute("""UPDATE observations SET detail=?
                       WHERE entity_id=? AND platform='live' AND source_id=?
                         AND stance=?""",
                    (note, e["entity_id"], target, stance))
        rows.append((e["display"], target, stance, note))
        print(f"  {stance:<8} {e['display'][:44]:<46} {note[:70]}", flush=True)
    con.commit()

    out = os.path.join(db.REPORTS, "T1b_live_verification.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Live verification of every URL the corpora recorded\n\n")
        fh.write(f"Fetched {NOW:%Y-%m-%d} UTC, one request per target, cached, "
                 f"{PACE}s apart, browser User-Agent.\n\n")
        fh.write("| stance | n |\n|---|---|\n")
        for k, n in counts.most_common():
            fh.write(f"| {k} | {n} |\n")
        fh.write("\n| entity | target | stance | note |\n|---|---|---|---|\n")
        for d, t, s, n in sorted(rows, key=lambda r: r[2]):
            fh.write(f"| {d} | `{t}` | **{s}** | {n} |\n")
        fh.write(f"\n## {len(no_url)} entities carry no URL at all\n\n")
        fh.write("This is a gap in the **upstream corpora**, not a judgement "
                 "about the tools. youtube-signal's extraction records a URL "
                 "only when one is spoken or shown on screen, and most creators "
                 "name a product without ever showing its address. Nothing "
                 "below can be verified by fetching, which is why the Reddit "
                 "pass (T2) matters: a name is searchable even when an address "
                 "was never given.\n\n")
        for d in sorted(no_url):
            fh.write(f"- {d}\n")
    print(f"\n  wrote {out}")
    for k, n in counts.most_common():
        print(f"    {k:<16} {n}")
    db.log(con, "verify_live",
           " ".join(f"{k}={v}" for k, v in counts.most_common()))
    con.close()


if __name__ == "__main__":
    main()
