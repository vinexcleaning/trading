"""GUARD #23, enforced locally, because the repo-wide version did not see this
folder.

WHY THIS FILE EXISTS, and it is not a hypothetical.

`census.py` v1 read `volume_dollars` with `volume` as a fallback. Both names
are absent from Kalshi's response, so every volume and every open interest in
the first exchange census came back null, and the summary printed `oi 0` for
all sixteen categories. That reads as a finding about the exchange. It was a
finding about my own field names.

`common/tests/test_no_legacy_kalshi_fields.py` is the repo-wide guard for
exactly this and it did NOT catch it. Its scanner classifies a file as
venue-reaching if it has a URL literal, calls `.json()`, or imports a known
venue client - and this folder reaches Kalshi by putting `bot-hunt/src` on
`sys.path` and doing `import venues`, which matches none of those. So the file
was scored as not touching the wire and its dead names were never looked at.

That is a real gap in the repo-wide guard and it has been reported. Meanwhile
this folder defends its own boundary rather than waiting.

    py -3 -m pytest strategy-factory/tests -q
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

#: Names Kalshi no longer returns. Reading one gets None on every market, which
#: flows into arithmetic as a silent zero. The live names end in `_fp` (counts)
#: or `_dollars` (money), and the two are not interchangeable.
DEAD = ["yes_bid", "yes_ask", "no_bid", "no_ask", "last_price", "volume",
        "volume_24h", "open_interest", "liquidity", "orderbook", "yes_price",
        "no_price", "previous_price", "yes_bid_size", "yes_ask_size",
        "notional_value", "volume_dollars", "open_interest_dollars"]

#: A dead name is only dead as a KEY read off a Kalshi response. The same word
#: is a perfectly good column name in our own SQLite schema, a variable, or
#: prose. So the check is deliberately narrow: `.get("<dead>")` and
#: `["<dead>"]` and nothing else.
PATTERNS = [re.compile(r"""\.get\(\s*['"](%s)['"]""" % n) for n in DEAD] + \
           [re.compile(r"""\[\s*['"](%s)['"]\s*\]""" % n) for n in DEAD]


def _sources():
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in str(p))


def scan(text):
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for pat in PATTERNS:
            m = pat.search(line)
            if m:
                hits.append("line %d reads dead field %r" % (line_no, m.group(1)))
    return hits


def test_no_source_reads_a_dead_kalshi_field_name():
    problems = {}
    for p in _sources():
        bad = scan(p.read_text(encoding="utf-8", errors="replace"))
        if bad:
            problems[p.name] = bad
    assert not problems, (
        "GUARD #23 - dead Kalshi field name read off the wire: %s. The live "
        "names end in _fp or _dollars; these read None and become a silent "
        "zero." % problems)


def test_the_detector_still_detects():
    """GUARDS #9 - guard rot. The planted violation is the exact line that was
    in `census.py` v1, so this test would have failed on the real bug."""
    planted = [
        'V.fnum(m.get("volume_dollars"), V.fnum(m.get("volume")))',
        'yb = m["yes_bid"]',
        "ob = (r.json() or {}).get('orderbook') or {}",
    ]
    for src in planted:
        assert scan(src), "detector missed a planted violation: %s" % src


def test_it_does_not_fire_on_our_own_column_names():
    """It must not fire on ordinary code, or it gets allowlisted and deleted -
    which is how the repo-wide version reasons about the same trade-off."""
    assert not scan(
        'con.execute("select volume, open_interest from open_markets")\n'
        'volume = row[7]\n'
        '# the legacy name volume is dead; read volume_fp\n'
        'V.fnum(m.get("volume_fp"))\n')
