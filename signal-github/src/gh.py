"""HTTP layer for signal-github.

Six transports, five of them free:

  core        api.github.com REST      60 req/hour unauthenticated. SCARCE.
  search      api.github.com/search    10 req/minute unauthenticated. Plentiful.
  raw         raw.githubusercontent    no documented API limit. Free.
  archive     codeload.github.com      NOT metered against core. Free. See below.
  atom        github.com/*/commits.atom  free; last 20 commits with dates.
  sourcegraph sourcegraph.com/.api     free, unauthenticated, public code only.

Everything is cached on disk by URL hash so a re-run costs nothing.

**`archive` is the transport that changes the economics of this project.**
Measured 2026-08-03: `codeload.github.com/<repo>/tar.gz/<branch>` returns the
complete file tree AND the contents of every file in one request, carries no
`X-RateLimit-*` headers, and spends **zero** of the 60/hour core budget (checked
by reading /rate_limit either side of a download). One request replaces the
git-tree core call and makes file *contents* available, which path-name
heuristics never had. Use `archive` for depth; spend `core` only on what has no
free substitute.

Note the URL form: the documented `/tar.gz/refs/heads/<branch>` path times out
from this network (WinError 10060), while the legacy `/tar.gz/<branch>` form
returns in ~0.3s. Do not "modernise" it.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)

UA = "signal-github/0.2 (research)"


def _load_dotenv():
    """Read signal-github/.env into the environment if present.

    A GitHub token is worth 60/hour -> 5,000/hour on `core` and unblocks code
    search. Shell environment variables do not survive between tool calls on
    Windows, so a gitignored `.env` beside the project is the durable place to
    put one. Never overrides a variable already set in the real environment.
    """
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


_load_dotenv()

# A token is used if the environment (or .env) happens to provide one. We never
# create an account and never prompt for one.
TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("GITHUB_API_TOKEN")
    or ""
).strip()

_last_search = 0.0
_core_remaining = None
_core_reset = 0.0

STATS = {"core_calls": 0, "search_calls": 0, "raw_calls": 0, "sg_calls": 0,
         "archive_calls": 0, "atom_calls": 0, "cache_hits": 0}


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
        wait = _core_reset - time.time() + 5
        if wait <= 0:
            # The recorded reset has already passed — the window rolled over
            # while we were doing free work. Do not sleep on a stale timestamp;
            # just try again and let the response headers correct us.
            _core_remaining = None
        else:
            print(f"[core] budget exhausted, sleeping {wait:.0f}s until reset", flush=True)
            time.sleep(min(wait, 3900))
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


# --- archive: the whole repo, free ------------------------------------------
# Extensions worth keeping as text. Everything else (images, wheels, model
# weights, vendored binaries) is counted in the file list but not stored.
TEXT_EXT = {
    ".py", ".ipynb", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".kt",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".rb", ".php", ".sh", ".ps1", ".bat",
    ".sql", ".md", ".rst", ".txt", ".toml", ".yaml", ".yml", ".json", ".cfg",
    ".ini", ".env", ".example", ".lock", ".csv", ".tsv", ".html", ".css",
}
MAX_FILE_BYTES = 512 * 1024        # one file
MAX_TEXT_BYTES = 8 * 1024 * 1024   # all text kept for one repo
MAX_DOWNLOAD = 80 * 1024 * 1024    # refuse to pull a monster


def _fetch_bytes(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()[:2000]
    except Exception as e:  # noqa: BLE001
        return 0, {}, f"{type(e).__name__}: {e}".encode()


def archive(full_name: str, branches=("main", "master"), timeout: int = 120):
    """The whole repository — every path, and the text of every text file — in
    one request that costs **nothing** from the core budget.

    Returns a dict:
        {"status": 200, "branch": "main", "paths": [...all paths...],
         "files": {path: text}, "n_paths": int, "bytes": int, "truncated": bool}
    or {"status": <code>, ...} on failure. Cached as one JSON per repo, so a
    re-run and every later analysis pass are free.

    Why this exists: the git-tree REST call costs 1 of 60 core calls/hour and
    returns *paths only*. This returns paths **and contents** for free. Every
    scoring component that had to guess from a filename can now read the code.
    """
    for br in branches:
        url = f"https://codeload.github.com/{full_name}/tar.gz/{br}"
        cp = _cache_path(url, "arch.json")
        hit = _read_cache(cp)
        if hit is not None:
            try:
                out = json.loads(hit)
            except json.JSONDecodeError:
                continue
            if out.get("status") == 200:
                return out
            continue

        status, headers, body = _fetch_bytes(url, timeout=timeout)
        STATS["archive_calls"] += 1
        if status != 200 or not isinstance(body, bytes):
            # A missing branch is a real answer and worth caching; a network
            # blip is not.
            if status == 404:
                with open(cp, "w", encoding="utf-8") as fh:
                    json.dump({"status": 404, "_url": url}, fh)
            continue
        if len(body) > MAX_DOWNLOAD:
            out = {"status": 200, "branch": br, "paths": [], "files": {},
                   "n_paths": 0, "bytes": len(body), "truncated": True,
                   "skipped": "archive larger than MAX_DOWNLOAD"}
            with open(cp, "w", encoding="utf-8") as fh:
                json.dump(out, fh)
            return out

        paths, files, kept = [], {}, 0
        truncated = False
        try:
            tf = tarfile.open(fileobj=io.BytesIO(body), mode="r:gz")
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                # strip the "<repo>-<sha>/" prefix codeload adds
                rel = m.name.split("/", 1)[1] if "/" in m.name else m.name
                paths.append(rel)
                ext = os.path.splitext(rel)[1].lower()
                if ext not in TEXT_EXT or m.size > MAX_FILE_BYTES:
                    continue
                if kept + m.size > MAX_TEXT_BYTES:
                    truncated = True
                    continue
                fh = tf.extractfile(m)
                if fh is None:
                    continue
                files[rel] = fh.read().decode("utf-8", "replace")
                kept += m.size
        except Exception as e:  # noqa: BLE001 - a corrupt tarball is a real answer
            return {"status": -1, "error": f"{type(e).__name__}: {e}", "_url": url}

        out = {"status": 200, "branch": br, "paths": paths, "files": files,
               "n_paths": len(paths), "bytes": len(body), "truncated": truncated}
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(out, fh)
        return out
    return {"status": 404, "paths": [], "files": {}, "n_paths": 0}


def commits_atom(full_name: str, branches=("main", "master")):
    """Last ~20 commits with dates and messages, free, no core spend.

    A partial substitute for the /commits credibility call: it cannot give a
    total commit count, but it gives recency, cadence and whether the most
    recent commit was substantive — which is what the credibility axis actually
    used the call for.
    """
    for br in branches:
        url = f"https://github.com/{full_name}/commits/{br}.atom"
        cp = _cache_path(url, "xml")
        body = _read_cache(cp)
        if body is None:
            status, _h, body = _fetch(url, accept="application/atom+xml", timeout=30)
            STATS["atom_calls"] += 1
            if status != 200:
                continue
            with open(cp, "w", encoding="utf-8") as fh:
                fh.write(body)
        import re
        dates = re.findall(r"<updated>([^<]+)</updated>", body)
        titles = re.findall(r"<title>([^<]*)</title>", body)
        return {"status": 200, "branch": br, "dates": dates[1:], "titles": titles[1:]}
    return {"status": 404, "dates": [], "titles": []}


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
