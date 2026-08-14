"""Read a GitHub repo properly — README, tree, and the files that decide things.

**Why this exists.** `signal-github` holds 4,017 repos and 4 have been read. The
lesson this programme keeps re-learning is that **reading beats scoring**: its
own GitHub pass found 5 real defects in repos that scored well on every computed
measure. A score tells you a repo *looks* like it trades. Only reading tells you
what it actually does when the number is wrong.

**What it fetches, and nothing else.** Public unauthenticated GitHub API:
metadata, the file tree, the README, and up to `--files` source files chosen for
being where the answer usually is — order placement, fee arithmetic, backtest
loops, and anything naming a sport.

**Unauthenticated GitHub allows 60 requests an hour.** That is the real
constraint on this job and it is why reading is paced and selective rather than
bulk. The limit is printed after every call so a run that dies of throttling
says so instead of looking like an empty repo.

    python src/read_repo.py mbordash/DRADIS
    python src/read_repo.py owner/name --files 8
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
UA = {"User-Agent": "Mozilla/5.0 (research reader)",
      "Accept": "application/vnd.github+json"}

# Where the answer usually is, in priority order.
INTERESTING = (
    (r"(order|exec|trade|submit|place)", "ORDER PATH"),
    (r"(fee|cost|slippage|commission)", "COST"),
    (r"(backtest|simulat|replay)", "BACKTEST"),
    (r"(strategy|signal|alpha|edge|model)", "STRATEGY"),
    (r"(latency|websocket|stream|live|realtime|real_time)", "LIVE/LATENCY"),
    (r"(mlb|baseball|sport|nfl|nba)", "SPORT"),
    (r"(risk|kelly|size|position)", "SIZING"),
)
SKIP = re.compile(r"(node_modules|\.lock$|package-lock|\.min\.|dist/|build/|"
                  r"\.png$|\.jpg$|\.svg$|\.ico$|\.woff|test_fixtures)", re.I)
CODE = re.compile(r"\.(py|ts|js|rs|go|java|rb|sol)$", re.I)


def get(path, raw=False):
    url = path if path.startswith("http") else API + path
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=45) as r:
            rem = r.headers.get("x-ratelimit-remaining")
            body = r.read()
            return (body if raw else json.loads(body)), rem
    except urllib.error.HTTPError as e:
        rem = e.headers.get("x-ratelimit-remaining") if e.headers else "?"
        print(f"   HTTP {e.code} on {url}  (rate limit remaining: {rem})")
        if e.code == 403:
            print("   -> 403 here almost always means the 60/hour "
                  "unauthenticated limit, NOT that the repo is private.")
        return (None, rem)
    except Exception as e:  # noqa: BLE001
        print(f"   {type(e).__name__} on {url}")
        return (None, "?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="owner/name")
    ap.add_argument("--files", type=int, default=6)
    ap.add_argument("--bytes", type=int, default=6000)
    args = ap.parse_args()

    print("=" * 88)
    print(f"  {args.repo}")
    print("=" * 88)

    meta, rem = get(f"/repos/{args.repo}")
    if not meta:
        print("  cannot read metadata -- stopping")
        return
    print(f"  {meta.get('stargazers_count')}* forks={meta.get('forks_count')} "
          f"lang={meta.get('language')} archived={meta.get('archived')}")
    print(f"  created {str(meta.get('created_at'))[:10]}  "
          f"pushed {str(meta.get('pushed_at'))[:10]}  "
          f"size {meta.get('size')}kb  issues={meta.get('open_issues_count')}")
    print(f"  {meta.get('description') or '(no description)'}")
    print(f"  [rate limit remaining: {rem}]")

    branch = meta.get("default_branch", "main")
    tree, rem = get(f"/repos/{args.repo}/git/trees/{branch}?recursive=1")
    files = []
    if tree:
        files = [t["path"] for t in tree.get("tree", [])
                 if t.get("type") == "blob" and not SKIP.search(t["path"])]
        print(f"\n  {len(files)} files (truncated={tree.get('truncated')})")
        buckets = {}
        for f in files:
            for pat, label in INTERESTING:
                if re.search(pat, f, re.I):
                    buckets.setdefault(label, []).append(f)
                    break
        for label, fs in buckets.items():
            print(f"    {label:<14} {len(fs):>3}  e.g. {', '.join(fs[:3])[:78]}")

    rd, rem = get(f"/repos/{args.repo}/readme")
    if rd and rd.get("content"):
        txt = base64.b64decode(rd["content"]).decode("utf-8", "replace")
        print(f"\n  --- README ({len(txt):,} chars) ---")
        print("  " + "\n  ".join(
            " ".join(txt.split("\n")[i].split())
            for i in range(min(60, len(txt.split("\n")))))[:4000])

    # read the code files most likely to settle something
    picks, seen = [], set()
    for pat, label in INTERESTING:
        for f in files:
            if f in seen or not CODE.search(f):
                continue
            if re.search(pat, f, re.I):
                picks.append((label, f))
                seen.add(f)
                break
        if len(picks) >= args.files:
            break

    for label, f in picks[:args.files]:
        body, rem = get(f"https://raw.githubusercontent.com/{args.repo}/"
                        f"{branch}/{f}", raw=True)
        if not body:
            continue
        txt = body.decode("utf-8", "replace")
        print(f"\n  {'=' * 84}")
        print(f"  [{label}] {f}  ({len(txt):,} chars)  "
              f"[rate limit remaining: {rem}]")
        print(f"  {'=' * 84}")
        print(txt[:args.bytes])


if __name__ == "__main__":
    main()
