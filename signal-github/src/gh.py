"""HTTP layer for signal-github.

Four transports, three of them free:

  core        api.github.com REST      60 req/hour unauthenticated. SCARCE.
  search      api.github.com/search    10 req/minute unauthenticated. Plentiful.
  raw         raw.githubusercontent    no documented API limit. Free.
  sourcegraph sourcegraph.com/.api     free, unauthenticated, public code only.

Everything is cached on disk by URL hash so a re-run costs nothing. The core
budget is the binding constraint on the whole project: spend it only on the
tree/commits/contributors calls that have no free substitute.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)

UA = "signal-github/0.1 (research; unauthenticated)"

# A token is used if the environment happens to provide one. We never create an
# account and never prompt for one.
TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("GITHUB_API_TOKEN")
    or ""
).strip()

_last_search = 0.0
_core_remaining = None
_core_reset = 0.0

STATS = {"core_calls": 0, "search_calls": 0, "raw_calls": 0, "sg_calls": 0, "cache_hits": 0}


def _key(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:20]


def _cache_path(url: str, ext: str) -> str:
    return os.path.join(CACHE, f"{_key(url)}.{ext}")


def _read_cache(path: str):
    if os.path.exists(path):
        STATS["cache_hits"] += 1
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


def _fetch(url: str, accept: str = "application/vnd.github+json", timeout: int = 45):
    """Raw HTTP. Returns (status, headers, body_text)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    if TOKEN and url.startswith("https://api.github.com"):
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - network is allowed to fail; caller records it
        return 0, {}, f"{type(e).__name__}: {e}"


def _note_core_headers(headers: dict):
    global _core_remaining, _core_reset
    rem = headers.get("X-RateLimit-Remaining")
    res = headers.get("X-RateLimit-Reset")
    if rem is not None:
        try:
            _core_remaining = int(rem)
        except ValueError:
            pass
    if res is not None:
        try:
            _core_reset = float(res)
        except ValueError:
            pass


def core(path: str, allow_404: bool = True, cache_only: bool = False):
    """One call against the 60/hour core budget. Cached. Blocks when exhausted.

    cache_only=True never touches the network — for read-back passes that must
    not compete with a fetch running in another process."""
    url = path if path.startswith("http") else "https://api.github.com" + path
    cp = _cache_path(url, "json")
    hit = _read_cache(cp)
    if hit is not None:
        try:
            return json.loads(hit)
        except json.JSONDecodeError:
            return None
    if cache_only:
        return None

    global _core_remaining
    if _core_remaining is not None and _core_remaining <= 1:
        wait = max(0.0, _core_reset - time.time()) + 5
        if wait > 0:
            print(f"[core] budget exhausted, sleeping {wait:.0f}s until reset", flush=True)
            time.sleep(wait)
            _core_remaining = None

    status, headers, body = _fetch(url)
    STATS["core_calls"] += 1
    _note_core_headers(headers)

    if status == 403 and "rate limit" in body.lower():
        wait = max(0.0, _core_reset - time.time()) + 5
        print(f"[core] 403 rate limit, sleeping {wait:.0f}s", flush=True)
        time.sleep(max(wait, 60))
        status, headers, body = _fetch(url)
        STATS["core_calls"] += 1
        _note_core_headers(headers)

    payload = {"_status": status, "_url": url, "_link": headers.get("Link", "")}
    if status == 200:
        try:
            payload["data"] = json.loads(body)
        except json.JSONDecodeError:
            payload["data"] = None
    else:
        payload["data"] = None
        payload["_body"] = body[:500]

    # 404s are cached (a repo really is gone); transient failures are not.
    if status == 200 or (status == 404 and allow_404):
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    return payload


def core_remaining():
    return _core_remaining


def search(kind: str, query: str, per_page: int = 100, page: int = 1, sort: str = ""):
    """kind is 'repositories' or 'users'. 10 req/minute unauthenticated."""
    global _last_search
    params = {"q": query, "per_page": per_page, "page": page}
    if sort:
        params["sort"] = sort
    url = f"https://api.github.com/search/{kind}?" + urllib.parse.urlencode(params)
    cp = _cache_path(url, "json")
    hit = _read_cache(cp)
    if hit is not None:
        try:
            return json.loads(hit)
        except json.JSONDecodeError:
            return {"_status": 0, "items": []}

    gap = 6.5 - (time.time() - _last_search)  # 10/min -> one every 6s, +margin
    if gap > 0:
        time.sleep(gap)
    status, headers, body = _fetch(url)
    _last_search = time.time()
    STATS["search_calls"] += 1

    if status == 403:
        time.sleep(65)
        status, headers, body = _fetch(url)
        _last_search = time.time()
        STATS["search_calls"] += 1

    out = {"_status": status, "_url": url}
    if status == 200:
        try:
            out.update(json.loads(body))
        except json.JSONDecodeError:
            out["items"] = []
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(out, fh)
    else:
        out["items"] = []
        out["_body"] = body[:400]
    return out


def raw(full_name: str, path: str, branches=("main", "master")):
    """Fetch a file from raw.githubusercontent. Free. Returns (text, url) or (None, None)."""
    for br in branches:
        url = f"https://raw.githubusercontent.com/{full_name}/{br}/{path}"
        cp = _cache_path(url, "txt")
        hit = _read_cache(cp)
        if hit is not None:
            if hit == "\x00MISSING":
                continue
            return hit, url
        status, _h, body = _fetch(url, accept="text/plain", timeout=30)
        STATS["raw_calls"] += 1
        if status == 200:
            with open(cp, "w", encoding="utf-8") as fh:
                fh.write(body)
            return body, url
        if status == 404:
            with open(cp, "w", encoding="utf-8") as fh:
                fh.write("\x00MISSING")
    return None, None


def sourcegraph(query: str, count: int = 30, timeout: int = 60):
    """Free public code search. Substitute for GitHub code search, which 401s
    without a token. Returns the parsed 'content' match events."""
    params = {"q": f"{query} count:{count}", "v": "V3", "t": "literal"}
    url = "https://sourcegraph.com/.api/search/stream?" + urllib.parse.urlencode(params)
    cp = _cache_path(url, "txt")
    body = _read_cache(cp)
    if body is None:
        status, _h, body = _fetch(url, accept="text/event-stream", timeout=timeout)
        STATS["sg_calls"] += 1
        if status != 200:
            return []
        with open(cp, "w", encoding="utf-8") as fh:
            fh.write(body)
        time.sleep(1.0)

    matches = []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("type") in ("content", "path", "repo"):
                    matches.append(item)
    return matches
