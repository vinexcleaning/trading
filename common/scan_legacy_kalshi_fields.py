"""Find reads of dead Kalshi field names, and CLASSIFY them before accusing.

## Why this is a report and not a failing test

The first version of this was a failing test asserting repo-wide that no dead
name is read anywhere. It fired on **25 files across 10 projects**, and the
first four sampled were all **correct code**:

  * `set1_overshoot/src/p0_candles.py` and `soccer/src/inplay.py` read
    CANDLESTICKS, where `yes_bid` / `yes_ask` are live *containers* whose
    leaves are `*_dollars`.
  * `market-selection/src/summarise_universe.py` reads `volume_24h` out of
    `kalshi_universe.json` — **a file it wrote itself**, with its own key
    names, which the venue has no say over.
  * `tennis-paper-forward/src/analyse.py` reads `yes_ask` out of its own
    stored brief.

A static checker cannot see whether a dict came off the wire or out of your own
storage. A guard that fires on correct code in ten projects gets wholesale-
allowlisted and then deleted, which is worse than no guard — that is guard rot
arriving on day one. So the enforcement lives in
`common.kalshi_fields.assert_priced()`, which runs against the actual object and
cannot be fooled, and this file produces a triage list for a human.

    py -3 common/scan_legacy_kalshi_fields.py            # print
    py -3 common/scan_legacy_kalshi_fields.py --md out.md

## The three buckets

  WIRE       the file fetches a Kalshi API URL and reads a dead name that is
             not a candlestick container. **Look at these.**
  CANDLE     the file works with candlesticks, where some of those names are
             live containers. Almost certainly fine.
  OWN        the file makes no Kalshi call at all — the dict came from its own
             database or JSON. Not the venue's business.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.kalshi_fields import DEAD, LIVE_CONTAINERS  # noqa: E402

AMBIGUOUS = {"count", "price", "yes", "no"}
DEAD_NAMES = {d for kind in DEAD.values() for d in kind} - AMBIGUOUS
CANDLE_CONTAINERS = set(LIVE_CONTAINERS["candlestick"])
KALSHI_URL = "api.elections.kalshi.com"
SKIP_DIRS = {".venv", "site-packages", "__pycache__", "node_modules",
             "_archive", ".git"}


def _tracked_py():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT,
                         capture_output=True, text=True, timeout=180).stdout
    for line in out.splitlines():
        p = ROOT / line
        if any(part in SKIP_DIRS for part in p.parts) or not p.exists():
            continue
        yield line.replace("\\", "/"), p


def reads(text):
    """(name, lineno) for every x["name"] and x.get("name"), via ast.

    Parsed, not grepped, so a dead name in a comment or docstring does not
    fire. Several files here legitimately DESCRIBE the trap, and a guard that
    cannot tell a warning from a violation punishes the people documenting it.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and isinstance(n.slice.value, str):
            out.append((n.slice.value, n.slice.lineno))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "get" and n.args \
                and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            out.append((n.args[0].value, n.args[0].lineno))
    return out


def classify(rel, text, hits):
    calls_kalshi = KALSHI_URL in text
    candle_ctx = ("candle" in text.lower() or "candlestick" in text.lower())
    only_containers = all(n in CANDLE_CONTAINERS for n, _ in hits)
    if not calls_kalshi:
        return "OWN", "no Kalshi API call in this file; the dict is its own"
    if candle_ctx and only_containers:
        return "CANDLE", ("works with candlesticks, where these names are live "
                          "containers whose leaves are *_dollars")
    if candle_ctx:
        return "WIRE", ("candlestick file, but reads a name that is dead on "
                        "candlesticks too (volume / open_interest are renamed "
                        "there as well)")
    return "WIRE", "fetches the Kalshi API and reads a dead name"


def scan():
    rows = []
    for rel, path in _tracked_py():
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = [(n, ln) for n, ln in reads(text) if n in DEAD_NAMES]
        if not hits:
            continue
        bucket, why = classify(rel, text, hits)
        rows.append({"file": rel, "bucket": bucket, "why": why,
                     "hits": sorted(set(hits))})
    order = {"WIRE": 0, "CANDLE": 1, "OWN": 2}
    rows.sort(key=lambda r: (order[r["bucket"]], r["file"]))
    return rows


def render(rows):
    out = []
    n = {"WIRE": 0, "CANDLE": 0, "OWN": 0}
    for r in rows:
        n[r["bucket"]] += 1
    out.append(f"{len(rows)} files read a dead Kalshi field name: "
               f"**{n['WIRE']} WIRE**, {n['CANDLE']} CANDLE, {n['OWN']} OWN.\n")
    for b in ("WIRE", "CANDLE", "OWN"):
        sel = [r for r in rows if r["bucket"] == b]
        if not sel:
            continue
        out.append(f"\n## {b} — {len(sel)} file(s)\n")
        for r in sel:
            names = ", ".join(sorted({f"`{x}`" for x, _ in r["hits"]}))
            lines = ", ".join(str(ln) for _, ln in r["hits"])
            out.append(f"- `{r['file']}` — {names} (line {lines}) — {r['why']}")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    a = ap.parse_args()
    rows = scan()
    body = render(rows)
    print(body)
    if a.md:
        Path(a.md).write_text(
            "# Dead Kalshi field names — triage (GUARD #23)\n\n"
            "Generated by `common/scan_legacy_kalshi_fields.py`. "
            "**Only WIRE needs a human.**\n\n" + body + "\n",
            encoding="utf-8")
        print(f"\nwrote {a.md}")
    sys.exit(1 if any(r["bucket"] == "WIRE" for r in rows) else 0)
