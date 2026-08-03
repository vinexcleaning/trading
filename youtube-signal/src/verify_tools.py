"""STEP 4 -- do the claimed tools actually exist?

Free. No LLM, no API key. Just HTTP.

H2 (+3, "points to a verifiable artifact") is the single most gameable component
in the whole scoring scheme: saying "the code is on my GitHub" costs nothing. This
is the check that makes the claim mean something. Only `resolved` awards H2.

For GitHub repos specifically, existing is not enough -- a README-only repo is not
a working artifact. The public API reports pushed_at and size, so an empty or
never-pushed repo is detectable without cloning it.

Results are cached in the tools table; a tool is not re-checked within 30 days.
"""

import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db as _db  # noqa: E402
import db_phase2  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
RECHECK_DAYS = 30
PAUSE_S = 1.5
GH = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)", re.I)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(200_000)


def check_github(owner, repo):
    """Existing != working. Check it has been pushed to and has real size."""
    repo = repo.removesuffix(".git")
    try:
        status, body = fetch(f"https://api.github.com/repos/{owner}/{repo}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "dead", f"github api 404 for {owner}/{repo}"
        return "unreachable", f"github api HTTP {e.code}"
    except Exception as exc:  # noqa: BLE001
        return "unreachable", f"{type(exc).__name__}"
    d = json.loads(body)
    size = d.get("size", 0)
    pushed = d.get("pushed_at")
    if d.get("archived"):
        return "resolved", f"ARCHIVED, {size}KB, last push {pushed}"
    if size == 0:
        return "dead", f"repo exists but is EMPTY (0KB), last push {pushed}"
    return "resolved", (f"{size}KB, {d.get('stargazers_count',0)} stars, "
                        f"last push {pushed}")


def check_url(url):
    if not url:
        return "not_checked", "no url given"
    if not url.startswith("http"):
        url = "https://" + url
    m = GH.search(url)
    if m:
        return check_github(m.group(1), m.group(2))
    try:
        status, body = fetch(url)
    except urllib.error.HTTPError as e:
        return ("dead" if e.code in (404, 410) else "unreachable",
                f"HTTP {e.code}")
    except Exception as exc:  # noqa: BLE001
        return "unreachable", f"{type(exc).__name__}"
    if status == 200 and len(body) < 500:
        return "unreachable", f"HTTP 200 but only {len(body)} bytes (parked?)"
    return "resolved", f"HTTP {status}, {len(body):,} bytes"


def main():
    con = db_phase2.connect()
    rows = con.execute("SELECT * FROM tools ORDER BY tool_id").fetchall()
    cutoff = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(days=RECHECK_DAYS)).isoformat()

    print(f"{len(rows)} tools in the table\n")
    counts = {}
    for t in rows:
        if t["resolved_utc"] and t["resolved_utc"] > cutoff:
            print(f"  {t['name'][:42]:<44} cached: {t['resolution']}")
            counts[t["resolution"]] = counts.get(t["resolution"], 0) + 1
            continue
        res, detail = check_url(t["url"])
        con.execute(
            "UPDATE tools SET resolution=?, resolution_detail=?, resolved_utc=?"
            " WHERE tool_id=?", (res, detail, _db.now(), t["tool_id"]))
        con.commit()
        counts[res] = counts.get(res, 0) + 1
        mark = {"resolved": "OK  ", "dead": "DEAD", "unreachable": "????",
                "not_checked": "--  "}[res]
        print(f"  {mark} {t['name'][:42]:<44} {detail}")
        if t["url"]:
            time.sleep(PAUSE_S)

    print("\n" + "=" * 68)
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<14} {v}")
    dead = counts.get("dead", 0)
    print(f"\n  {dead} claimed artifact(s) turned out to be dead or empty.")
    print("  Only 'resolved' awards H2 (+3). Everything else scores zero for it.")
    con.close()


if __name__ == "__main__":
    main()
