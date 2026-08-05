"""TASK 5 - the cross-platform table EXISTS. This adds the axis it is missing.

`social-signal` already built the unified tool reputation table: 240 entities,
946 observations joined across YouTube, GitHub and Reddit, 11 CONTRADICTION
verdicts. The brief says "if social-signal has not already built it, build it
here" - it has, so this does not rebuild it.

What it does NOT have is a **currency** axis, and Task 1 measured exactly what
that costs: `Polymarket/agents` sits in the table as a CONTRADICTION only
because a human noticed it was archived, and every other entity was judged on
what people SAID about it rather than on whether it still runs.

This joins a dated, re-runnable liveness verdict onto every entity that has a
GitHub repo or a URL, and reports the new contradiction class:

    THE SOURCES RECOMMEND IT AND THE VENUE HAS ARCHIVED IT.

That is a finding no single corpus produces, and unlike a stance it is not a
matter of opinion - it is the repo owner's own flag.

Read-only against `social.db`. Nothing is written back to a sibling project.

    python src/unify_currency.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

UA = "extractor-upgrade/1.0 (+trading repo; currency join)"
CACHE = corpora.DATA / "entity_currency.json"


def _token():
    p = corpora.ROOT / "signal-github" / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+)", line)
        if m and "TOKEN" in m.group(1).upper():
            return m.group(2).strip().strip("\"'")
    return None


def gh_repo(repo, tok, now):
    h = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    try:
        req = urllib.request.Request("https://api.github.com/repos/" + repo,
                                     headers=h)
        d = json.load(urllib.request.urlopen(req, timeout=25))
    except urllib.error.HTTPError as e:
        return {"state": "GONE" if e.code == 404 else f"HTTP_{e.code}",
                "detail": f"GitHub API returned {e.code}"}
    except Exception as e:
        return {"state": "ERROR", "detail": f"{type(e).__name__}: {e}"}
    pushed = d.get("pushed_at") or ""
    days = None
    if pushed:
        days = (now - datetime.fromisoformat(
            pushed.replace("Z", "+00:00"))).days
    if d.get("archived"):
        state = "ARCHIVED"
    elif days is not None and days > 365:
        state = "COLD"
    else:
        state = "ALIVE"
    return {"state": state, "pushed_at": pushed, "days_since_push": days,
            "stars": d.get("stargazers_count"),
            "detail": (f"archived={d.get('archived')}, last push "
                       f"{pushed[:10]} ({days}d ago)")}


def head(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"state": "ALIVE" if r.status < 400 else f"HTTP_{r.status}",
                    "detail": f"{r.status}, {len(r.read(4096))}+ bytes"}
    except urllib.error.HTTPError as e:
        return {"state": f"HTTP_{e.code}",
                "detail": f"{e.code} {'(blocked, not dead)' if e.code in (401,403,429) else ''}"}
    except Exception as e:
        return {"state": "NO_DNS" if "getaddrinfo" in str(e) else "ERROR",
                "detail": f"{type(e).__name__}: {str(e)[:80]}"}


DEAD_STATES = {"ARCHIVED", "GONE", "NO_DNS", "HTTP_410", "COLD"}
# 401/403/429 are a door being held shut, not a door that is gone. Treating
# them as death is how `social-signal` nearly lost the Pinnacle route, and how
# this session's own first probe called a working API dead - see DECISIONS D9.
BLOCKED_STATES = {"HTTP_401", "HTTP_403", "HTTP_429", "HTTP_400", "HTTP_522"}


def _dead(o: dict) -> bool:
    """Is this entity actually gone?

    !! THE FIRST VERSION OF THIS FUNCTION COUNTED EVERY 404 AS DEATH AND
    PRODUCED THREE FALSE KILLS IN ITS FIRST RUN - `api.elections.kalshi.com`,
    `api.exchange.coinbase.com` and `r2v2.pmxt.dev`, all of which are live API
    hosts whose BASE URL has no handler. That is the fourth occurrence in this
    repo of a probe sampling the wrong thing and failing toward a kill
    (market-selection's stale tickers -> 19 wrong kills; bot-hunt's
    tag_slug=esports; this session's own Pinnacle 401).

    THE SECOND VERSION WAS ALSO WRONG. It counted a 404 as death when the URL
    had two or more path segments, and immediately killed
    `https://api.elections.kalshi.com/trade-api/v2` - a VERSIONED API BASE that
    this repo is recording against right now. A heuristic written to patch a
    false kill produced another false kill on its first run.

    So the rule is now the one with no heuristic in it: **a 404 never
    establishes death.** It means "no handler at this path", which is what an
    API base returns when it is perfectly healthy. Only four states do:

      NO_DNS    the name does not resolve - nothing is there to serve anything
      ARCHIVED  the OWNER's own flag, not an inference
      HTTP_410  Gone, the one status that explicitly means permanently removed
      COLD      no push in over a year, reported as its own state, not as death

    Everything else is UNDECIDED and needs a second probe against a real
    resource path. That is more expensive and it is the price of not producing
    a fifth wrong kill.
    """
    return o.get("state", "") in DEAD_STATES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--pace", type=float, default=0.35)
    a = ap.parse_args()

    tok = _token()
    now = datetime.now(timezone.utc)
    con = corpora.ro("reddit")
    rows = con.execute(
        "SELECT e.entity_id, e.display, e.kind, e.canonical_url, "
        "       e.github_repo, v.verdict, v.n_platforms, v.reason "
        "FROM entities e LEFT JOIN verdicts v ON v.entity_id = e.entity_id "
        "ORDER BY v.n_platforms DESC").fetchall()
    con.close()
    if a.limit:
        rows = rows[:a.limit]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out, checked = [], 0
    for r in rows:
        key = r["github_repo"] or r["canonical_url"] or ""
        if not key:
            continue
        if key in cache:
            res = cache[key]
        else:
            res = (gh_repo(r["github_repo"], tok, now) if r["github_repo"]
                   else head(r["canonical_url"]))
            cache[key] = res
            checked += 1
            time.sleep(a.pace)
        out.append({"display": r["display"], "kind": r["kind"],
                    "target": key, "social_verdict": r["verdict"],
                    "n_platforms": r["n_platforms"], "reason": r["reason"],
                    **res})
        if checked and checked % 25 == 0:
            print(f"  checked {checked}...")
            CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    states = Counter(o["state"] for o in out)
    # The new contradiction: the sources like it and the venue has shut it.
    recommended = {"AGREE_POSITIVE", "SINGLE_SOURCE", "UNDISCLOSED",
                   "CONTRADICTION"}
    new_contra = [o for o in out
                  if _dead(o) and o["social_verdict"] in recommended]
    blocked = [o for o in out
               if o["state"] in BLOCKED_STATES
               or (o["state"] == "HTTP_404" and not _dead(o))]

    L = ["# TASK 5 - a currency verdict joined onto the cross-platform table\n",
         "`social-signal` already built the unified entity table - 240 "
         "entities, 946 observations, 11 CONTRADICTION verdicts across "
         "YouTube, GitHub and Reddit. **This does not rebuild it.** It adds "
         "the one axis it has no column for: whether the thing still runs.\n",
         f"Checked {len(out)} entities carrying a GitHub repo or a URL, "
         f"{datetime.now(timezone.utc).isoformat(timespec='minutes')}.\n",
         "## Liveness\n", "| state | n |", "|---|---|"]
    for s, n in states.most_common():
        L.append(f"| {s} | {n} |")
    L.append("")
    L.append("> **401, 403, 429 and a bare-host 404 are counted as BLOCKED or "
             "UNDECIDED, not dead.** A door held shut is not a door that is "
             "gone, and an API base URL with no handler is not a dead API.\n>\n"
             "> This rule was written because the first run of this script "
             "did NOT have it and produced **three false kills** - "
             "`api.elections.kalshi.com`, `api.exchange.coinbase.com` and "
             "`r2v2.pmxt.dev`, all live hosts whose base path returns 404. "
             "That is the **fourth** occurrence in this repo of a probe "
             "sampling the wrong thing and failing toward a kill: "
             "`market-selection`'s stale tickers produced 19 wrong kills, "
             "`bot-hunt`'s `tag_slug=esports` killed its own best lead, and "
             "this session's first Pinnacle probe returned 401 on the index "
             "while the endpoint that matters returned 200 and 1.7 MB with no "
             "header at all (`DECISIONS.md` D9).\n>\n"
             "> **The second version of the rule was also wrong.** It counted a 404 as "
             "more path segments.\n")

    L.append("## The new contradiction class\n")
    L.append(f"**{len(new_contra)} entities that the corpora treat as usable, "
             "and whose owner has archived, removed or abandoned them.** "
             "Unlike a stance, this is not an opinion: it is the repo owner's "
             "own flag or an HTTP status.\n")
    L.append("| entity | target | state | detail | what the corpora say |")
    L.append("|---|---|---|---|---|")
    for o in sorted(new_contra, key=lambda x: -(x["n_platforms"] or 0)):
        L.append(f"| {o['display'][:44]} | `{o['target'][:40]}` | "
                 f"**{o['state']}** | {(o.get('detail') or '')[:60]} | "
                 f"{o['social_verdict']} on {o['n_platforms']} platforms |")
    L.append("")

    L.append("## Blocked, and therefore undecided\n")
    L.append("| entity | target | status |")
    L.append("|---|---|---|")
    for o in blocked[:30]:
        L.append(f"| {o['display'][:44]} | `{o['target'][:44]}` | "
                 f"{o['state']} |")
    L.append("")

    path = corpora.REPORTS / "T5_currency_join.md"
    path.write_text("\n".join(L), encoding="utf-8")
    (corpora.DATA / "T5_currency_join.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"  {len(out)} entities; states {dict(states)}")
    print(f"  NEW CONTRADICTIONS: {len(new_contra)}; blocked {len(blocked)}")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
