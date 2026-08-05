"""How do the few repos that model QUEUE POSITION actually do it?

Only 5.2% of 3,201 cached archives mention queue position and 3.0% mention
trade-through — the two things that decide whether a maker backtest is honest.
I wrote `h10_passive.py`'s fill model from first principles, so this checks it
against the handful of people who have written one, without putting a byte of
repo source into context beyond the matching lines.
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

PAT = re.compile(
    r"queue[_ ]?(position|ahead|prio|rank|depth)|position[_ ]in[_ ]queue|"
    r"time[_ ]priority|price[_ ]time|trade[_ ]?through|traded[_ ]through|"
    r"ahead[_ ]of[_ ]us|in[_ ]front[_ ]of|fill[_ ]prob|probability[_ ]of[_ ]fill|"
    r"partial[_ ]fill|queue_size|resting[_ ]size", re.I)
SKIP = re.compile(r"^\s*(#|//|\*|/\*)")


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


def main():
    names = sys.argv[1:]
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    for fn in names:
        row = con.execute("select default_branch, stars, s_adj, description "
                          "from repos where full_name=?", (fn,)).fetchone()
        if not row:
            print(f"!! {fn} not in corpus")
            continue
        br, stars, s_adj, desc = row
        arch = load(fn, br)
        print("=" * 76)
        print(f"{fn}  *{stars}  s_adj={s_adj}")
        print(f"  {(desc or '')[:170]}")
        if not arch:
            print("  (no cached archive)")
            continue
        n = 0
        for path, text in sorted(arch["files"].items()):
            if not isinstance(text, str):
                continue
            if not any(path.endswith(e) for e in
                       (".py", ".md", ".ts", ".js", ".rs", ".go")):
                continue
            for i, ln in enumerate(text.splitlines(), 1):
                if PAT.search(ln) and len(ln.strip()) > 12:
                    print(f"    {path}:{i}: {ln.strip()[:155]}")
                    n += 1
                    if n >= 18:
                        break
            if n >= 18:
                break
        if n == 0:
            print("    (no line-level queue logic)")
    con.close()


if __name__ == "__main__":
    main()
