"""GUARD #23 — repo-wide: no code reads a Kalshi field name that no longer exists.

Modelled on `test_no_fee_reimplementation.py`, for the same reason. The fee
formula went from 3 copies to 17 while the rule was only a convention, and
stopped at 17 the day it became a failing test. The renamed-field trap has now
caught three sessions with the warning already written down in prose.

An offending line must either be fixed or added to `ALLOWLIST` **with a written
reason**. There is deliberately no way to silence it without leaving a sentence
behind.

    py -3 -m pytest common/tests/test_no_legacy_kalshi_fields.py -q
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.kalshi_fields import DEAD, LIVE_CONTAINERS  # noqa: E402

# Names that are dead on a Kalshi object but are also ordinary words used all
# over normal code (`count`, `volume` of anything else). Matching those on
# sight would make the guard noise, and a noisy guard gets ignored -- which is
# how a guard rots. So the check is narrowed to reads that look like they are
# indexing a Kalshi-shaped object.
AMBIGUOUS = {"count", "volume", "price", "yes", "no"}

# Every dead name, minus the ambiguous ones. These are unmistakable.
UNAMBIGUOUS = sorted(
    {d for kind in DEAD.values() for d in kind} - AMBIGUOUS)

# file -> reason. A path here is exempt and the reason is the point.
ALLOWLIST = {
    "common/kalshi_fields.py":
        "the field map itself; it must name the dead fields to forbid them",
    "common/tests/test_no_legacy_kalshi_fields.py":
        "this test; it names the dead fields to search for them",
    "mlb-paper/src/kalshi.py":
        "names the dead fields only inside the module docstring that documents "
        "the trap; the code reads *_dollars / *_fp exclusively",
    "coordinator/scan.py":
        "coordinator is filesystem-and-git only and makes no venue call at all",
}

SKIP_DIRS = {".venv", "site-packages", "__pycache__", "node_modules",
             "_archive", ".git"}

# The WIRE bucket, adjudicated file by file on 2026-08-07. Each verdict was
# reached by READING the code, not by trusting the classifier.
WIRE_ADJUDICATED = {
    "market-selection/src/probe_orderbook.py":
        "*** REAL BUG *** reads r.json().get('orderbook') -- the response nests "
        "under 'orderbook_fp' with keys 'yes_dollars'/'no_dollars', so "
        "yes_levels and no_levels are 0 for EVERY market. Not mine to fix; "
        "flagged in STATUS.md per CLAUDE.md section 5.",
    "crypto/src/mm_capability_probe.py":
        "*** REAL BUG *** same as above: r2.json().get('orderbook', {}) then "
        "ob.get('yes'). It prints 'keys: []' and finds no levels, i.e. it "
        "reports the orderbook endpoint as returning nothing. Not mine to fix; "
        "flagged in STATUS.md.",
    "crypto/src/record_15m_opens.py":
        "FALSE POSITIVE -- valid() reads its OWN local dict, built after "
        "reading the *_dollars names. Superseded by _v2 anyway.",
    "crypto/src/record_15m_opens_v2.py":
        "FALSE POSITIVE -- same pattern, and STATUS.md already adjudicated it: "
        "reads the new names at :174-185 and stores under local keys.",
    "signal-github/src/kalshi_liquidity_survey.py":
        "CORRECT -- m.get('volume_fp') or m.get('volume') or 0. New name "
        "first, legacy as a harmless fallback.",
    "kalshi-market-scan/src/kalshi_research/api.py":
        "CORRECT -- d.get('orderbook_fp') or d.get('orderbook'), with a "
        "docstring that warns about exactly this trap.",
    "common/measure_tennis_maker_liquidity.py":
        "CORRECT, and the model to copy -- it ASSERTS volume_fp is present and "
        "raises if the schema moved, then reads r['volume'] off its own "
        "accumulator.",
}


def _tracked_py():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT,
                         capture_output=True, text=True, timeout=120).stdout
    files = []
    for line in out.splitlines():
        p = (ROOT / line)
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.exists():
            files.append((line.replace("\\", "/"), p))
    return files


def _string_reads(text):
    """Every `x["name"]` and `x.get("name")` in the file, as (name, lineno).

    Parsed with `ast`, not regex, so a dead name mentioned in a comment or a
    docstring does not fire. That distinction matters: several files in this
    repo legitimately DESCRIBE the trap, and a guard that cannot tell a warning
    from a violation punishes the people documenting it.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                hits.append((sl.value, sl.lineno))
        elif isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr == "get"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                hits.append((node.args[0].value, node.args[0].lineno))
    return hits


def scan_text(text):
    """Dead-name reads in one source text, as a list of (name, lineno)."""
    dead = set(UNAMBIGUOUS)
    return [(n, ln) for n, ln in _string_reads(text) if n in dead]


def test_no_new_WIRE_hit_appears():
    """Fails when a NEW file starts reading a dead name off the Kalshi wire.

    Deliberately NOT "no file anywhere reads a dead name". That version fired on
    25 files across 10 projects and the first four sampled were all correct
    code -- two reading candlesticks, where the names are live containers, and
    two reading their own stored JSON. A guard that fires on correct code in ten
    projects gets wholesale-allowlisted and then deleted. That is guard rot
    arriving on day one.

    So the frozen list below is the WIRE bucket as adjudicated ONE BY ONE on
    2026-08-07. Growing it requires a human to look and write a verdict; the
    test only defends the boundary.
    """
    import subprocess
    r = subprocess.run(
        [sys.executable, str(ROOT / "common" / "scan_legacy_kalshi_fields.py")],
        capture_output=True, text=True, timeout=300, cwd=ROOT)
    found = {ln.split("`")[1] for ln in r.stdout.splitlines()
             if ln.startswith("- `") and "`" in ln[3:]}
    wire = set()
    seen_wire = False
    for ln in r.stdout.splitlines():
        if ln.startswith("## WIRE"):
            seen_wire = True
            continue
        if ln.startswith("## ") and seen_wire:
            break
        if seen_wire and ln.startswith("- `"):
            wire.add(ln.split("`")[1])
    new = wire - set(WIRE_ADJUDICATED)
    assert not new, (
        "GUARD #23 -- new file(s) read a dead Kalshi field name off the wire: "
        f"{sorted(new)}. Look at each, then add it to WIRE_ADJUDICATED with a "
        "verdict. The live names end in _dollars or _fp; the legacy names are "
        "ABSENT and read None, which flows into arithmetic as a silent zero.")


def test_the_detector_still_detects():
    """GUARDS #9 — guard rot. A guard never tested against a real violation is
    a guard nobody knows still works."""
    planted = [
        'v = m["yes_bid_size"]\n',
        'v = m.get("open_interest")\n' if "open_interest" in UNAMBIGUOUS
        else 'v = m.get("last_price")\n',
        'p = trade["yes_price"]\n',
    ]
    for src in planted:
        assert scan_text(src), f"detector missed a planted violation: {src!r}"


def test_the_detector_does_not_fire_on_prose():
    """A file that WARNS about the trap must not be flagged for warning."""
    doc = ('"""Do not read yes_bid or last_price; they are gone."""\n'
           '# volume -> volume_fp, open_interest -> open_interest_fp\n'
           'v = m["yes_bid_dollars"]\n')
    assert not scan_text(doc), "the guard fires on prose, so it will be ignored"


def test_the_detector_does_not_fire_on_the_live_names():
    ok = ('a = m["yes_ask_dollars"]\nb = m.get("volume_fp")\n'
          'c = ob["orderbook_fp"]["yes_dollars"]\n')
    assert not scan_text(ok)


def test_candlestick_containers_are_not_treated_as_dead():
    """The half-truth this guard exists to correct.

    On a candlestick `yes_bid` is LIVE and is a container; on a market it is
    DEAD. Meanwhile `volume` is dead on BOTH. STATUS.md currently says only the
    first half, which would let somebody read `candle["volume"]` believing
    candlesticks are exempt.
    """
    assert "yes_bid" in LIVE_CONTAINERS["candlestick"]
    assert "yes_bid" in DEAD["market"]
    assert "volume" in DEAD["candlestick"]
    assert "volume" in DEAD["market"]


def test_every_allowlist_entry_has_a_reason_and_a_real_file():
    for rel, reason in ALLOWLIST.items():
        assert reason and len(reason) > 20, f"{rel}: reason too thin"
        assert (ROOT / rel).exists(), f"{rel}: allowlisted but does not exist"
