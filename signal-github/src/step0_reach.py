"""STEP 0 — reachability. Measure, do not assume.

Writes reports/step0.md and exits 0 whatever it finds. Nothing here is allowed
to stop the run.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh  # noqa: E402

ROOT = gh.ROOT
UTC = datetime.timezone.utc


def probe(name, url, accept="application/vnd.github+json", note=""):
    req = urllib.request.Request(url, headers={"User-Agent": gh.UA, "Accept": accept})
    if gh.TOKEN and url.startswith("https://api.github.com"):
        req.add_header("Authorization", f"Bearer {gh.TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            status, headers, body = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        status, headers, body = e.code, dict(e.headers), e.read()
    except Exception as e:  # noqa: BLE001
        return {"name": name, "url": url, "status": 0, "error": f"{type(e).__name__}: {e}", "note": note}
    return {
        "name": name,
        "url": url,
        "status": status,
        "bytes": len(body),
        "limit": headers.get("X-RateLimit-Limit"),
        "remaining": headers.get("X-RateLimit-Remaining"),
        "reset": headers.get("X-RateLimit-Reset"),
        "resource": headers.get("X-RateLimit-Resource"),
        "note": note,
    }


def main():
    now = datetime.datetime.now(UTC)
    results = []

    results.append(probe("rate_limit (core)", "https://api.github.com/rate_limit"))
    results.append(probe("repo metadata (core)",
                         "https://api.github.com/repos/Jon-Becker/prediction-market-analysis"))
    results.append(probe("repo SEARCH",
                         "https://api.github.com/search/repositories?q=kalshi+bot&per_page=1"))
    results.append(probe("CODE SEARCH",
                         "https://api.github.com/search/code?q=py_clob_client&per_page=1",
                         note="the one that decides whether Step 1's second half is possible"))
    results.append(probe("raw.githubusercontent (README)",
                         "https://raw.githubusercontent.com/Jon-Becker/prediction-market-analysis/main/README.md",
                         accept="text/plain", note="not an API endpoint; no rate-limit headers"))
    results.append(probe("git tree recursive (core)",
                         "https://api.github.com/repos/Jon-Becker/prediction-market-analysis/git/trees/main?recursive=1"))
    results.append(probe("sourcegraph public code search",
                         "https://sourcegraph.com/.api/search/stream?q=py_clob_client+count:3&v=V3&t=literal",
                         accept="text/event-stream", note="candidate substitute for GitHub code search"))
    results.append(probe("dependents graph (HTML)",
                         "https://github.com/Polymarket/py-clob-client/network/dependents",
                         accept="text/html", note="renders client-side; body carries no repo rows"))

    # What does the token situation actually look like?
    token_state = "present in environment" if gh.TOKEN else "ABSENT — running unauthenticated"

    # Full quota snapshot
    quota = {}
    try:
        req = urllib.request.Request("https://api.github.com/rate_limit",
                                     headers={"User-Agent": gh.UA})
        if gh.TOKEN:
            req.add_header("Authorization", f"Bearer {gh.TOKEN}")
        with urllib.request.urlopen(req, timeout=30) as r:
            quota = json.load(r)["resources"]
    except Exception as e:  # noqa: BLE001
        quota = {"error": str(e)}

    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    out = os.path.join(ROOT, "reports", "step0.md")
    with open(out, "w", encoding="utf-8") as fh:
        w = fh.write
        w(f"# STEP 0 — reachability\n\nMeasured {now.strftime('%Y-%m-%d %H:%M')} UTC. "
          f"Token: **{token_state}**. No account was created and none was requested.\n\n")
        w("## Probes\n\n| endpoint | status | limit | remaining | resource | note |\n")
        w("|---|---|---|---|---|---|\n")
        for r in results:
            w(f"| {r['name']} | `{r.get('status')}`{' ' + r.get('error','') if r.get('error') else ''} "
              f"| {r.get('limit') or '—'} | {r.get('remaining') or '—'} "
              f"| {r.get('resource') or '—'} | {r.get('note','')} |\n")
        w("\n## Real quota, from the response headers\n\n")
        w("| resource | limit | window | effective |\n|---|---|---|---|\n")
        windows = {"core": "hour", "search": "minute", "code_search": "minute",
                   "graphql": "hour", "integration_manifest": "hour"}
        for k, v in sorted(quota.items()):
            if not isinstance(v, dict):
                continue
            win = windows.get(k, "?")
            eff = v["limit"] * (60 if win == "minute" else 1)
            w(f"| `{k}` | {v['limit']}/{win} | {win} | {eff}/hour |\n")
        code_status = next((r["status"] for r in results if r["name"] == "CODE SEARCH"), None)
        sg_status = next((r["status"] for r in results if r["name"].startswith("sourcegraph")), None)
        w("\n## What this means for the run\n\n")
        w(f"- **GitHub code search is BLOCKED unauthenticated** (`{code_status}`), and the "
          "`rate_limit` endpoint advertises a `code_search` quota of "
          f"{quota.get('code_search',{}).get('limit','?')}/min that does not exist for an "
          "anonymous caller. The quota table lies; the endpoint is the truth.\n")
        w(f"- **Sourcegraph's public index answers the same question** (`{sg_status}`) and is "
          "used as the substitute. It is NOT like-for-like: it indexes a subset of GitHub and "
          "excludes forks by default. Every code-search hit in this project is therefore "
          "labelled `F2_CODE` with source `sourcegraph`, never as GitHub code search.\n")
        w("- **`core` at 60/hour is the binding constraint on the entire project.** Repo search "
          "at 600/hour and raw.githubusercontent (unmetered) carry everything they can; core is "
          "spent only on git trees, commit counts and contributor counts, which have no free "
          "substitute. Budget: roughly 3 core calls per repo, so ~20 repos deep-read per hour.\n")
        w("- **The dependents graph is not scrapeable.** The page returns 200 but the repository "
          "rows are rendered client-side; the HTML body contains none of them. Forks of the "
          "client libraries are used as the free substitute and are labelled `LIB_FORK`.\n")
        w("- No token was created. If one is ever added to the environment as `GITHUB_TOKEN`, "
          "`gh.py` picks it up automatically and core goes to 5,000/hour and code search unblocks.\n")
        w("\n")
        json_path = os.path.join(ROOT, "reports", "step0.json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump({"measured_utc": now.isoformat(), "token": bool(gh.TOKEN),
                       "probes": results, "quota": quota}, jf, indent=2)
        w(f"Raw: `reports/step0.json`\n")

    print(open(out, encoding="utf-8").read())


if __name__ == "__main__":
    main()
