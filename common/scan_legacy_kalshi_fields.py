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
import re
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

# ⚠ CORRECTED 2026-08-08. v1 decided "did this come off the wire?" by looking
# for the Kalshi URL literal in the file. That fails for every project with a
# SHARED HTTP CLIENT, which is the normal shape of mature code:
#
#     market-selection/src/resolve_orderbook.py
#         import kalshi_api as K
#         r = K.get(f"/markets/{t}/orderbook", ...)
#         ob = (r.json() or {}).get("orderbook") or {}      <- the same bug
#
# It contains no URL, so v1 filed it as OWN ("the dict is its own") and the
# scan reported 2 of 3 real bugs. The devig session found the third by plain
# grep. Two extra signals, both stronger than a URL literal:
#   * `.json(` anywhere -- an HTTP response is being parsed
#   * an import whose module name names a venue or a client
CLIENT_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+[\w.]*(kalshi|polymarket|arcadia|pinnacle|venue)",
    re.I | re.M)
RESPONSE_PARSE = re.compile(r"\.json\s*\(")
SKIP_DIRS = {".venv", "site-packages", "__pycache__", "node_modules",
             "_archive", ".git"}

# WIRE entries already looked at BY A HUMAN, with the verdict. Living here and
# not in the pytest file on purpose: mailbox 004 pointed out that
# `py -3 -m pytest` returns "No module named pytest" on the base interpreter, so
# the test naming two of these bugs was PRESENT, CORRECT AND RUN BY NOTHING.
# A guard nobody runs is a comment. `python common/scan_legacy_kalshi_fields.py`
# now exits non-zero on any UNADJUDICATED wire hit and needs no test runner.
WIRE_ADJUDICATED = {
    # --- the three real bugs. All FIXED by the devig session on 2026-08-08.
    "market-selection/src/probe_orderbook.py":
        "WAS A REAL BUG, fixed 2026-08-08 in 8f68e7e -- now reads orderbook_fp",
    "market-selection/src/resolve_orderbook.py":
        "WAS A REAL BUG (the third site, which v1 of this scan MISSED), fixed "
        "2026-08-08 -- now reads orderbook_fp",
    "crypto/src/mm_capability_probe.py":
        "WAS A REAL BUG, fixed 2026-08-08. The owning session confirmed this "
        "file is where CLAUDE.md section 5's 'does the orderbook endpoint "
        "return data' contradiction came from. Depth IS public: 20 levels a "
        "side, free. LEDGER M001.",
    # --- correct code that this scan cannot distinguish statically
    "crypto/src/record_15m_opens.py": "own local dict; superseded by _v2",
    "crypto/src/record_15m_opens_v2.py":
        "own local dict, already adjudicated in STATUS.md Task 1",
    "signal-github/src/kalshi_liquidity_survey.py":
        "volume_fp first, legacy as a harmless fallback",
    "kalshi-market-scan/src/kalshi_research/api.py":
        "orderbook_fp first, with a docstring warning about the trap",
    "common/measure_tennis_maker_liquidity.py":
        "ASSERTS volume_fp is present, then reads its own accumulator -- the "
        "model to copy",
    "kalshi-market-scan/scripts/record_kalshi.py":
        "orderbook_fp first, reads yes_dollars/no_dollars",
    "kalshi-market-scan/scripts/record_external.py":
        "reads its own recorded rows, not a venue response",
    "kalshi-market-scan/scripts/score_vs_mid.py":
        "reads its own recorded rows",
    "kalshi-market-scan/scripts/vs_mid_clustered.py":
        "reads its own recorded rows",
    "market-selection/src/check_fees_and_ticks.py":
        "reads kalshi_universe.json, a file this project wrote itself",
    "market-selection/src/pull_kalshi_universe.py":
        "reads the accumulator row it just built, under its own key names",
    "market-selection/src/pull_poly_universe.py":
        "POLYMARKET, not Kalshi -- volume_24h is a live Polymarket field and "
        "the Kalshi rename does not apply",
    "crypto/src/deribit_chain.py":
        "DERIBIT, not Kalshi -- open_interest is a live Deribit field",
    "crypto/src/deribit_pricer.py":
        "DERIBIT, not Kalshi -- open_interest is a live Deribit field",
    "kalshi-market-scan/scripts/soccer_census.py":
        "FALSE POSITIVE, checked 2026-08-12 -- line 70 sums the LIVE name "
        "`m.get('volume_fp')`; the flagged reads at 84/91/97 are its own "
        "accumulator row built at line 78. Correct code.",
    "bot-hunt/src/pull_kalshi_soccer.py":
        "reads candle dicts it built itself from *_fp names",
}


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
    calls_kalshi = bool(
        KALSHI_URL in text
        or CLIENT_IMPORT.search(text)
        or RESPONSE_PARSE.search(text))
    candle_ctx = ("candle" in text.lower() or "candlestick" in text.lower())
    only_containers = all(n in CANDLE_CONTAINERS for n, _ in hits)
    if not calls_kalshi:
        return "OWN", ("no venue call, no client import and no .json() parse "
                       "in this file; the dict is its own")
    if candle_ctx and only_containers:
        return "CANDLE", ("works with candlesticks, where these names are live "
                          "containers whose leaves are *_dollars")
    if candle_ctx:
        return "WIRE", ("candlestick file, but reads a name that is dead on "
                        "candlesticks too (volume / open_interest are renamed "
                        "there as well)")
    how = ("URL literal" if KALSHI_URL in text
           else "imports a venue client" if CLIENT_IMPORT.search(text)
           else "parses an HTTP response with .json()")
    return "WIRE", f"reaches the venue ({how}) and reads a dead name"


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
    wire = {r["file"] for r in rows if r["bucket"] == "WIRE"}
    new = sorted(wire - set(WIRE_ADJUDICATED))
    if new:
        print()
        print("*** GUARD #23 FAILS: unadjudicated wire hit(s) ***")
        for f in new:
            print("  " + f)
        print()
        print("Read each one, then add it to WIRE_ADJUDICATED with a "
              "verdict. The live names end in _dollars or _fp; the legacy "
              "names are ABSENT and read None, which becomes a silent zero.")
        sys.exit(1)
    stale = sorted(set(WIRE_ADJUDICATED) - wire)
    if stale:
        print()
        print("note: %d adjudicated file(s) no longer hit -- fixed or "
              "moved:" % len(stale))
        for f in stale:
            print("  " + f)
    print()
    print("GUARD #23 OK -- all %d wire hit(s) are adjudicated." % len(wire))
    sys.exit(0)
