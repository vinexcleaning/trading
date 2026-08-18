"""Bright Data Web Scraper API client. Free-allowance only, preflight first.

⚠ THREE RULES THIS FILE EXISTS TO ENFORCE, not to document.

**1. The token never enters this repo.** It is read at runtime from
`C:\\Users\\vinig\\keys\\brightdata.txt` -- outside the repo, which is public --
or from the `BRIGHTDATA_TOKEN` environment variable. It is never printed, never
logged, never put in an error message, and never written to `data/`.
`tests/test_no_secrets.py` fails the build if a token shape appears anywhere in
this folder.

**2. It cannot spend past the free allowance.** `HARD_CAP` records, total,
across every call in a run. A request that would take the running total past it
is refused before it is sent, not after.

**3. Dataset ids are DISCOVERED, not hardcoded.** Bright Data's public docs do
not publish the ids for X, TikTok and Instagram discovery -- four documentation
pages were read on 2026-08-14 and none carries them. `CLAUDE.md` §3 is explicit
that instructions written from unverified memory have already cost this project
an afternoon. So the client asks the account which scrapers it has and prints
what it matched and why. If two scrapers match a platform, or none does, **it
stops and asks rather than guessing and spending.**

    py -3 extractor-apify\\src\\brightdata.py preflight     # spends nothing
    py -3 extractor-apify\\src\\brightdata.py run           # spends allowance
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.brightdata.com"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
DB = os.path.join(DATA, "paid_trial.db")

# Outside the repo. The repo is public.
TOKEN_PATH = r"C:\Users\vinig\keys\brightdata.txt"
TOKEN_ENV = "BRIGHTDATA_TOKEN"

# The free monthly allowance, and the whole budget. Fixed in
# PREREGISTRATION_PAIDTRIAL.md before anything was pulled.
HARD_CAP = 5000
PLAN = [("x", 3500), ("tiktok", 1000), ("instagram", 500)]

TERMS = ["kalshi", "polymarket", "prediction market", "prediction markets",
         "event contract", "predictit"]

# How to recognise the right scraper in the account's library. Deliberately
# loose on the name and strict on the platform, because vendor naming drifts
# and this must fail loudly rather than pick the wrong one.
PLATFORM_HINTS = {
    "x":         (("twitter", "x.com"), ("post", "tweet")),
    "tiktok":    (("tiktok",), ("post", "video")),
    "instagram": (("instagram",), ("post",)),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS pt_posts (
    id TEXT PRIMARY KEY, platform TEXT, term TEXT, url TEXT, author TEXT,
    created_utc TEXT, text TEXT, likes INTEGER, comments INTEGER,
    shares INTEGER, raw TEXT, fetched_utc TEXT);
CREATE TABLE IF NOT EXISTS pt_spend (
    ts TEXT, platform TEXT, term TEXT, requested INTEGER, returned INTEGER,
    snapshot_id TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS pt_log (ts TEXT, event TEXT, detail TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def load_token() -> str:
    """Read the token from OUTSIDE the repo. Never returns it to a log."""
    env = os.environ.get(TOKEN_ENV, "").strip()
    if env:
        return env
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, encoding="utf-8") as fh:
            t = fh.read().strip()
        if t:
            return t
    raise SystemExit(
        "No Bright Data token.\n"
        f"  Put it in {TOKEN_PATH} (one line, nothing else),\n"
        f"  or set the {TOKEN_ENV} environment variable.\n"
        "  It must NOT be placed anywhere inside this repo -- the repo is "
        "public and a test fails the build if it is.")


def call(token: str, method: str, path: str, params=None, body=None,
         tries: int = 4):
    """One request. Returns (status, parsed). Errors carry the vendor's
    message and never anything that could contain the token."""
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
                try:
                    return r.status, json.loads(raw)
                except Exception:               # noqa: BLE001
                    return r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf-8", "replace")
            if e.code in (429, 502, 503, 504) and attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return e.code, msg
        except Exception as e:                  # noqa: BLE001
            if attempt == tries - 1:
                return 0, type(e).__name__
            time.sleep(3 * (attempt + 1))
    return 0, "exhausted"


# --------------------------------------------------------------------------
# Discovery of what the account actually has

def list_scrapers(token: str):
    """Ask the account which scrapers exist. Tries the documented paths in
    order and returns the first that answers, with the path it used."""
    tried = []
    for path in ("/datasets/v3/scrapers", "/datasets/list",
                 "/datasets/v3/list", "/datasets"):
        status, body = call(token, "GET", path)
        tried.append((path, status))
        if status == 200 and body:
            return path, body, tried
    return None, None, tried


def _fields(entry) -> str:
    """Every string in one library entry, lowercased, for matching."""
    if isinstance(entry, str):
        return entry.lower()
    out = []
    for v in (entry or {}).values():
        if isinstance(v, str):
            out.append(v.lower())
    return " | ".join(out)


def pick(entries, platform: str):
    """Return (chosen, candidates). Chosen is None unless exactly one
    candidate survives -- ambiguity is reported, never resolved silently."""
    names, kinds = PLATFORM_HINTS[platform]
    cands = []
    for e in entries:
        blob = _fields(e)
        if not any(n in blob for n in names):
            continue
        if not any(k in blob for k in kinds):
            continue
        # Discovery, not collect-by-url: we have keywords, not post URLs.
        if "discover" not in blob and "keyword" not in blob:
            continue
        cands.append(e)
    return (cands[0] if len(cands) == 1 else None), cands


def dataset_id_of(entry):
    if isinstance(entry, str):
        return entry
    for k in ("id", "dataset_id", "datasetId", "collector"):
        v = (entry or {}).get(k)
        if isinstance(v, str) and v:
            return v
    return None


def name_of(entry) -> str:
    if isinstance(entry, str):
        return entry
    for k in ("name", "title", "description", "dataset_name"):
        v = (entry or {}).get(k)
        if isinstance(v, str) and v:
            return v
    return "?"


# --------------------------------------------------------------------------

def spent(con) -> int:
    r = con.execute("SELECT COALESCE(SUM(returned),0) FROM pt_spend").fetchone()
    return int(r[0] or 0)


def trigger(token: str, dataset_id: str, keyword: str, limit: int):
    """Start one discover-by-keyword collection."""
    return call(token, "POST", "/datasets/v3/trigger",
                params={"dataset_id": dataset_id, "type": "discover_new",
                        "discover_by": "keyword", "format": "json",
                        "limit_multiple_results": str(limit)},
                body=[{"keyword": keyword, "num_of_posts": limit}])


def wait(token: str, snapshot_id: str, budget_s: int = 1800):
    """Poll until the snapshot is ready. Returns (state, rows_or_message)."""
    t0 = time.time()
    while time.time() - t0 < budget_s:
        status, body = call(token, "GET",
                            f"/datasets/v3/progress/{snapshot_id}")
        state = body.get("status") if isinstance(body, dict) else None
        if state == "ready":
            s2, rows = call(token, "GET",
                            f"/datasets/v3/snapshot/{snapshot_id}",
                            params={"format": "json"})
            return "ready", rows
        if state in ("failed", "canceled"):
            return str(state), body
        time.sleep(15)
    return "timeout", f"still running after {budget_s}s"


def normalise(row: dict, platform: str, term: str):
    """Flatten one vendor record into the shape the rubric needs. Vendors
    rename fields; every plausible key is tried and the raw row is kept so a
    wrong guess here is recoverable without paying again."""
    def first(*keys):
        for k in keys:
            v = row.get(k)
            if isinstance(v, (str, int, float)) and str(v).strip():
                return v
        return None
    text = first("description", "caption", "text", "content", "post_text",
                 "title", "tweet_text") or ""
    ident = first("id", "post_id", "pk", "url", "post_url")
    return (
        str(ident if ident is not None
            else f"{platform}:{abs(hash(json.dumps(row, sort_keys=True)))}"),
        platform, term,
        str(first("url", "post_url", "link") or ""),
        str(first("user_posted", "username", "author", "owner",
                  "profile_name") or ""),
        str(first("date_posted", "timestamp", "created_at", "taken_at") or ""),
        str(text),
        int(first("likes", "like_count", "digg_count", "favorites") or 0),
        int(first("num_comments", "comment_count", "replies", "comments") or 0),
        int(first("shares", "share_count", "reposts", "retweets") or 0),
        json.dumps(row)[:20000], now())


def cmd_preflight(token: str) -> int:
    """Spends nothing. Says exactly what a run would do."""
    print("  PREFLIGHT -- nothing is triggered, nothing is spent.\n")
    path, body, tried = list_scrapers(token)
    if not path:
        print("  Could not list the account's scrapers. Paths tried:")
        for p, s in tried:
            print(f"    {s:>4}  {p}")
        print("\n  Nothing was triggered. This is where it stops -- guessing "
              "a dataset id and spending on it is the one thing this client "
              "will not do.")
        return 1
    entries = body if isinstance(body, list) else (
        body.get("datasets") or body.get("data") or body.get("results") or [])
    print(f"  scraper library read from {path}: {len(entries)} entries\n")

    con = connect()
    already = spent(con)
    ok = True
    for platform, want in PLAN:
        chosen, cands = pick(entries, platform)
        print(f"  {platform.upper():<10} want {want} records")
        if not cands:
            print("     NO scraper in this account matches "
                  f"{PLATFORM_HINTS[platform][0]} + discovery-by-keyword.")
            print("     STOP. Nothing will be triggered for this platform.")
            ok = False
            continue
        for c in cands[:8]:
            mark = "->" if c is chosen else "  "
            print(f"     {mark} {dataset_id_of(c)}  {name_of(c)[:70]}")
        if not chosen:
            print(f"     {len(cands)} candidates matched and none is "
                  "unambiguous. STOP -- ambiguity is not resolved silently.")
            ok = False
            continue
        did = dataset_id_of(chosen)
        print(f"     would POST /datasets/v3/trigger dataset_id={did} "
              f"type=discover_new discover_by=keyword")
        print(f"     terms: {', '.join(TERMS)}")
        print(f"     per term: {want // len(TERMS)} records")
    print(f"\n  budget: {HARD_CAP} records free, {already} already spent, "
          f"{HARD_CAP - already} left")
    print("  " + ("READY -- run `brightdata.py run` to spend the allowance."
                  if ok else
                  "NOT READY -- see the STOPs above. Nothing was spent."))
    return 0 if ok else 1


def cmd_run(token: str) -> int:
    con = connect()
    path, body, tried = list_scrapers(token)
    if not path:
        print("  cannot read the scraper library; refusing to guess. "
              "Nothing spent.")
        return 1
    entries = body if isinstance(body, list) else (
        body.get("datasets") or body.get("data") or body.get("results") or [])

    for platform, want in PLAN:
        chosen, cands = pick(entries, platform)
        if not chosen:
            print(f"  {platform}: {len(cands)} candidates, not unambiguous. "
                  "SKIPPED, nothing spent.")
            con.execute("INSERT INTO pt_log VALUES (?,?,?)",
                        (now(), "skipped", f"{platform}: ambiguous"))
            con.commit()
            continue
        did = dataset_id_of(chosen)
        per = max(1, want // len(TERMS))
        for term in TERMS:
            used = spent(con)
            if used + per > HARD_CAP:
                print(f"  BUDGET STOP: {used} spent, {per} more would pass "
                      f"{HARD_CAP}. Nothing further is requested.")
                con.execute("INSERT INTO pt_log VALUES (?,?,?)",
                            (now(), "budget_stop", f"{used}/{HARD_CAP}"))
                con.commit()
                return 0
            st, resp = trigger(token, did, term, per)
            snap = resp.get("snapshot_id") if isinstance(resp, dict) else None
            if not snap:
                print(f"  {platform}/{term}: trigger returned {st} -- "
                      f"{str(resp)[:140]}")
                con.execute("INSERT INTO pt_spend VALUES (?,?,?,?,?,?,?)",
                            (now(), platform, term, per, 0, "",
                             f"trigger {st}"))
                con.commit()
                continue
            state, rows = wait(token, snap)
            got = len(rows) if isinstance(rows, list) else 0
            if isinstance(rows, list):
                con.executemany(
                    "INSERT OR IGNORE INTO pt_posts VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?)",
                    [normalise(r, platform, term) for r in rows
                     if isinstance(r, dict)])
            con.execute("INSERT INTO pt_spend VALUES (?,?,?,?,?,?,?)",
                        (now(), platform, term, per, got, snap, state))
            con.commit()
            print(f"  {platform:<10} {term:<20} requested {per:>4} "
                  f"got {got:>4}  ({state})", flush=True)

    tot = con.execute("SELECT COUNT(*) FROM pt_posts").fetchone()[0]
    print(f"\n  {tot} records stored, {spent(con)} of {HARD_CAP} allowance "
          f"used")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["preflight", "run", "balance"])
    args = ap.parse_args()
    token = load_token()
    if args.command == "balance":
        st, body = call(token, "GET", "/customer/balance")
        print(f"  {st}  {str(body)[:300]}")
        return 0
    return cmd_preflight(token) if args.command == "preflight" \
        else cmd_run(token)


if __name__ == "__main__":
    sys.exit(main())
