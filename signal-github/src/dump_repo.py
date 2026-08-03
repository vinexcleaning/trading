"""Print one repo for reading. The only expensive step is the model reading this.

Reads from the cache, so it costs nothing and can be re-run freely.

    python src/dump_repo.py owner/name [--chars 60000]

One repo per turn. Reading many in a single session is quadratic in tokens:
the YouTube project processed ~2.7M tokens against 244k of actual text by
batching 15 transcripts into one context.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

INTERESTING = re.compile(
    r"(backtest|strateg|signal|trade|order|execut|fee|cost|slippage|risk|size|sizing|"
    r"market_?mak|quote|spread|arb|main|bot|engine|model)", re.I)


def cache_read(fn, branch, path):
    url = f"https://raw.githubusercontent.com/{fn}/{branch}/{path}"
    cp = os.path.join(gh.CACHE, hashlib.sha1(url.encode()).hexdigest()[:20] + ".txt")
    if not os.path.exists(cp):
        return None
    t = open(cp, encoding="utf-8", errors="replace").read()
    return None if t.startswith("\x00MISSING") else t


def main():
    fn = sys.argv[1]
    budget = 60000
    if "--chars" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--chars") + 1])

    con = db.connect()
    r = con.execute("SELECT * FROM repos WHERE full_name=?", (fn,)).fetchone()
    if not r:
        print(f"{fn} not in db")
        return
    ev = json.loads(r["evidence"] or "{}")
    evs = json.loads(r["evidence_strict"] or "{}")
    branch = (ev.get("branch") or ["main"])[0]

    print(f"=== {fn} ===")
    print(f"url={r['url']}  stars={r['stars']}  language={r['language']}  license={r['license']}")
    print(f"created={r['created_at'][:10]}  pushed={r['pushed_at'][:10]}  size={r['size_kb']}KB "
          f"files={r['tree_files']}  forks={r['forks']}")
    print(f"commits={r['commits']}  contributors={r['contributors']}  span={r['span_days']}d "
          f"open_issues={r['open_issues']}  closed={r['closed_issues']}")
    print(f"families={r['families']}  gate={r['gate']} {r['drop_reason']}")
    print(f"S_literal={r['s_total']}  S_strict={r['s_strict']}")
    print(f"evidence_strict={json.dumps(evs, indent=1)[:2000]}")
    print(f"description: {r['description']}\n")

    tr = gh.core(f"/repos/{fn}/git/trees/{branch}?recursive=1", cache_only=True)
    paths = [t["path"] for t in (tr or {}).get("data", {}).get("tree", [])
             if t.get("type") == "blob"] if tr else []
    print(f"--- FILE TREE ({len(paths)} files) ---")
    for p in sorted(paths)[:200]:
        print(" ", p)
    print()

    readme = None
    for nm in ("README.md", "readme.md", "README.rst"):
        readme = cache_read(fn, branch, nm)
        if readme:
            break
    if readme:
        print(f"--- README.md ({len(readme)} chars) ---")
        print(readme[:20000])
        budget -= min(len(readme), 20000)
        print()

    src = [p for p in paths if p.lower().endswith((".py", ".ts", ".js", ".rs", ".go"))
           and not re.search(r"(^|/)(node_modules|dist|vendor|\.venv)/", p)]
    src.sort(key=lambda p: (0 if INTERESTING.search(p) else 1, len(p)))
    for p in src:
        if budget <= 0:
            break
        t = cache_read(fn, branch, p)
        if not t:
            continue
        take = min(len(t), max(2000, budget // 3))
        print(f"--- {p} ({len(t)} chars, showing {take}) ---")
        print(t[:take])
        print()
        budget -= take

    for nm in ("requirements.txt", "pyproject.toml", "package.json", "Cargo.toml", "Makefile"):
        t = cache_read(fn, branch, nm)
        if t:
            print(f"--- {nm} ---")
            print(t[:3000])
            print()


if __name__ == "__main__":
    main()
