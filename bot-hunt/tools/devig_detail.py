"""Read only the de-vig IMPLEMENTATION LINES from selected repos.

github-signal's cost model: reading N repos in one context costs ~N^2/2. This
extracts the ~40 lines that answer the question and never puts a repo's source
in context. It is the cheap middle ground between a score and a full read.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

GH = Path(r"C:\Users\vinig\trading\signal-github")
CACHE, DB = GH / "cache", GH / "data" / "github.db"
REP = Path(__file__).resolve().parent.parent / "reports"

PAT = re.compile(
    r"de[-_ ]?vig|devig|overround|\bshin\b|no[-_ ]?vig|remove_vig|"
    r"arcadia\.pinnacle|guest\.api|fair_prob|fair_odds|closing[_ ]line|"
    r"maxRiskStake|power_method|worst_case", re.I)


def load(fn, br):
    for b in [br, "main", "master"]:
        if not b:
            continue
        u = f"https://codeload.github.com/{fn}/tar.gz/{b}"
        p = CACHE / f"{hashlib.sha1(u.encode()).hexdigest()[:20]}.arch.json"
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if d.get("status") == 200 and d.get("files"):
                return d
    return None


def main() -> None:
    names = sys.argv[1:]
    if not names:
        scan = json.loads((REP / "devig_scan.json").read_text(encoding="utf-8"))
        names = [h["repo"] for h in scan["hits"]
                 if "pinnacle_guest_api" in h["signals"]
                 or any(k.startswith("m_") for k in h["signals"])][:12]
        print(f"(auto-selected {len(names)} repos: guest-API users + any repo "
              f"that NAMES a de-vig method)\n")
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    for fn in names:
        row = con.execute(
            "select default_branch, stars, s_adj, kind, venue_detected, "
            "submits_orders, has_backtest, trust_me_bro, pushed_at, description "
            "from repos where full_name=?", (fn,)).fetchone()
        if not row:
            print(f"!! {fn}: not in corpus")
            continue
        br, stars, s_adj, kind, ven, ord_, bt, tmb, pushed, desc = row
        arch = load(fn, br)
        print("=" * 76)
        print(f"{fn}  stars={stars} s_adj={s_adj} kind={kind} venue={ven} "
              f"orders={bool(ord_)} backtest={bool(bt)} tmb={bool(tmb)} "
              f"pushed={pushed}")
        print(f"  {(desc or '')[:150]}")
        if not arch:
            print("  (no cached archive)")
            continue
        n = 0
        for path, text in sorted(arch["files"].items()):
            if not isinstance(text, str):
                continue
            for i, ln in enumerate(text.splitlines(), 1):
                if PAT.search(ln):
                    s = ln.strip()[:150]
                    if len(s) < 8:
                        continue
                    print(f"    {path}:{i}: {s}")
                    n += 1
                    if n >= 22:
                        break
            if n >= 22:
                break
        if n == 0:
            print("    (pattern matched at corpus level but not line level)")
    con.close()


if __name__ == "__main__":
    main()
