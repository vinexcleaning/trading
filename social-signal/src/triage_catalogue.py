"""Cross-check a stranger's strategy catalogue against everything we have tried.

**The find.** `sueun-dev/polymarket-alpha-lab` (read 2026-08-14) carries
`research/EN-polymarket-top-100-strategies.md` — 100 prediction-market
strategies, tiered S/A/B/C, *"curated from 600+ internet sources"*. The author
deliberately stripped the execution layer out of the repo (no `place_order`, no
wallet handling, no live loop), which is an honesty marker, not a limitation.

**Why this needs a tool rather than a read-through.** A list of 100 strategies is
worth nothing if 80 of them are things this repo already killed — and it is
actively harmful, because re-deriving a dead idea under a new name is how the
same work gets paid for twice. But the opposite failure is worse and this repo
has a rule against it: **"we tried that" is banned**, and a sweep over price
features was once used to close a question about individual players that it
never tested.

So this does the boring middle thing: for each of the 100, ask
`coordinator/idea.py` what we hold, and sort into

    OVERLAP    something in the 640 claims matches strongly -- read the row
    ADJACENT   partial match, and the difference has to be stated by a human
    NOT FOUND  nothing matched -- a candidate, not a discovery

**NOT FOUND means "not found", never "never tried".** `idea.py` matches words,
not meaning, and 7 of the 23 project folders carry no ledger rows at all.

    python src/triage_catalogue.py <catalogue.md>
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

REPO = r"C:\Users\vinig\trading"
HEAD = re.compile(r"^##\s+(\d{1,3})\.\s+(.+?)\s*$", re.M)
# idea.py prints a block per related claim; these pull out what we need.
CLAIM = re.compile(r"^\s*\[(\d+)\]\s+(\S+).*?STATUS:\s*(\S+)", re.M)
MATCHED_ON = re.compile(r"MATCHED ON\s*:\s*(.+)")


def ask(idea: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return [(claim_id, status)], [matched words] from idea.py."""
    try:
        out = subprocess.run(
            ["py", "-3", r"coordinator\idea.py", "check", "--idea", idea],
            cwd=REPO, capture_output=True, text=True, timeout=180,
            encoding="utf-8", errors="replace").stdout or ""
    except Exception as e:  # noqa: BLE001
        return [], [f"ERROR {type(e).__name__}"]
    claims = [(m.group(2), m.group(3)) for m in CLAIM.finditer(out)]
    words = []
    m = re.search(r"Words matched on:\s*(.+?)\n\n", out, re.S)
    if m:
        words = [w.strip() for w in m.group(1).replace("\n", " ").split(",")
                 if w.strip()]
    return claims, words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("catalogue")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()

    text = open(args.catalogue, encoding="utf-8").read()
    items = [(int(m.group(1)), m.group(2)) for m in HEAD.finditer(text)]
    # keep the first occurrence of each number, in order
    seen, ordered = set(), []
    for n, title in items:
        if n not in seen:
            seen.add(n)
            ordered.append((n, title))
    ordered.sort()
    print(f"{len(ordered)} numbered strategies found in {args.catalogue}\n")

    rows = []
    for n, title in ordered[:args.limit]:
        claims, words = ask(title)
        strong = [c for c in claims if len(words) >= 4]
        bucket = ("OVERLAP" if len(claims) >= 8 and len(words) >= 5
                  else "ADJACENT" if claims else "NOT FOUND")
        rows.append((n, title, bucket, claims[:3], len(words)))
        print(f"  {n:>3}. [{bucket:<9}] {title[:66]}")
        if claims[:2]:
            print(f"        nearest: " + ", ".join(
                f"{cid}({st})" for cid, st in claims[:2]))

    out = os.path.join(db.REPORTS, "CATALOGUE_TRIAGE.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# A stranger's 100 strategies, against our 640 claims\n\n")
        fh.write("Source: `sueun-dev/polymarket-alpha-lab`, "
                 "`research/EN-polymarket-top-100-strategies.md`, read "
                 "2026-08-14.\n\n**NOT FOUND means not found.** `idea.py` "
                 "matches words, not meaning, and 7 of 23 project folders "
                 "carry no ledger rows at all.\n\n")
        for bucket in ("NOT FOUND", "ADJACENT", "OVERLAP"):
            sel = [r for r in rows if r[2] == bucket]
            fh.write(f"\n## {bucket} — {len(sel)}\n\n")
            fh.write("| # | strategy | nearest claims |\n|---|---|---|\n")
            for n, title, _b, claims, _w in sel:
                near = ", ".join(f"`{c}` {s}" for c, s in claims) or "—"
                fh.write(f"| {n} | {title} | {near} |\n")
    counts = {b: sum(1 for r in rows if r[2] == b)
              for b in ("NOT FOUND", "ADJACENT", "OVERLAP")}
    print(f"\n  {counts}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
