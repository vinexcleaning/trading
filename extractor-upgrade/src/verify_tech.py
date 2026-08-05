"""Build the currency table by CHECKING, not by remembering.

The `T` (currency) axis added in `rubric_v2.py` is only as good as its list of
identifiers, and a hand-written list goes stale exactly as fast as the content
it is supposed to police. This script re-derives the list from live sources:

  GitHub API   archived flag + last push, which is the venue's own statement
  PyPI JSON    latest release date and yanked status
  HTTP HEAD    whether a named site still resolves at all

`signal-github/.env` supplies a token if one is present (5,000/hr instead of
60), but every call here works unauthenticated too.

    python src/verify_tech.py

Writes `data/tech_currency.json`, which `rubric_v2.py` loads. If the file is
missing, rubric_v2 falls back to the frozen snapshot in `TECH_FALLBACK` and
says so in its output, because silently scoring currency off a list you cannot
date is worse than not scoring it.
"""
from __future__ import annotations

import json
import re
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "data" / "tech_currency.json"

UA = "extractor-upgrade/1.0 (+trading repo; currency check)"
TIMEOUT = 25

# What to check, and the aliases a transcript or README might use for it.
GH_REPOS = {
    "Polymarket/py-clob-client": ["py-clob-client", "py clob client",
                                  "pyclobclient"],
    "Polymarket/clob-client": ["@polymarket/clob-client", "clob-client"],
    "Polymarket/py-sdk": ["polymarket py-sdk", "polymarket python sdk"],
    "Polymarket/agents": ["polymarket/agents", "polymarket agents"],
    "Kalshi/kalshi-python": ["kalshi-python", "kalshi python sdk"],
    "ArshKA/pykalshi": ["pykalshi"],
}
PYPI = ["py-clob-client", "kalshi-python", "kalshi-python-sync",
        "polymarket-py-sdk", "pykalshi"]
SITES = {
    "api.pushshift.io": "https://api.pushshift.io/reddit/search/submission/?limit=1",
    "arctic-shift.photon-reddit.com": "https://arctic-shift.photon-reddit.com/api/subreddits/search?subreddit=algotrading&limit=1",
    "oracleselixir.com": "https://oracleselixir.com/",
    "thebetterers.com": "https://thebetterers.com/",
    "guest.api.arcadia.pinnacle.com": "https://guest.api.arcadia.pinnacle.com/0.1/sports",
}


def _token():
    p = ROOT / "signal-github" / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+)", line)
        if m and "TOKEN" in m.group(1).upper():
            return m.group(2).strip().strip("\"'")
    return None


def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()


def main():
    tok = _token()
    now = datetime.now(timezone.utc)
    out = {"checked_utc": now.isoformat(timespec="seconds"),
           "token_used": bool(tok), "github": {}, "pypi": {}, "sites": {}}

    gh_hdr = {"Accept": "application/vnd.github+json"}
    if tok:
        gh_hdr["Authorization"] = "Bearer " + tok
    for repo, aliases in GH_REPOS.items():
        try:
            _, body = _get("https://api.github.com/repos/" + repo, gh_hdr)
            d = json.loads(body)
            pushed = d.get("pushed_at") or ""
            age_d = None
            if pushed:
                age_d = (now - datetime.fromisoformat(
                    pushed.replace("Z", "+00:00"))).days
            out["github"][repo] = {
                "archived": bool(d.get("archived")),
                "pushed_at": pushed, "days_since_push": age_d,
                "stars": d.get("stargazers_count"),
                "license": (d.get("license") or {}).get("spdx_id"),
                "aliases": aliases,
                "dead": bool(d.get("archived")),
            }
        except Exception as e:
            out["github"][repo] = {"error": f"{type(e).__name__}: {e}",
                                   "aliases": aliases, "dead": None}
        print(f"  gh {repo:34s} {out['github'][repo].get('dead')}")

    for pkg in PYPI:
        try:
            _, body = _get(f"https://pypi.org/pypi/{pkg}/json")
            d = json.loads(body)
            ver = d["info"]["version"]
            rel = d["releases"].get(ver) or []
            up = rel[0]["upload_time_iso_8601"] if rel else None
            age_d = None
            if up:
                age_d = (now - datetime.fromisoformat(
                    up.replace("Z", "+00:00"))).days
            out["pypi"][pkg] = {"version": ver, "last_upload": up,
                                "days_since_release": age_d,
                                "yanked": bool(rel and rel[0].get("yanked"))}
        except urllib.error.HTTPError as e:
            out["pypi"][pkg] = {"http": e.code, "exists": False}
        except Exception as e:
            out["pypi"][pkg] = {"error": f"{type(e).__name__}: {e}"}
        print(f"  pypi {pkg:28s} {out['pypi'][pkg]}")

    for name, url in SITES.items():
        try:
            st, body = _get(url)
            out["sites"][name] = {"status": st, "bytes": len(body),
                                  "dead": st >= 400}
        except urllib.error.HTTPError as e:
            out["sites"][name] = {"status": e.code, "dead": e.code >= 400}
        except (urllib.error.URLError, socket.timeout, socket.gaierror) as e:
            out["sites"][name] = {"status": None, "dead": True,
                                  "error": f"{type(e).__name__}: {e}"}
        print(f"  site {name:36s} {out['sites'][name]}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
