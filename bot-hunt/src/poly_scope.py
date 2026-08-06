"""What is in the recorded Polymarket esports data, and can it be joined?

Polymarket is the venue that matters most and is still untested here. It is
where the only reconciled live P&L in any corpus came from (+$8,293 arb /
-$3,184 residual / +$4,973 net, 3,858 fills), and it is structurally different
from Kalshi in the one way that could change the answer: **makers are paid
rebates rather than charged**.

Kalshi's join failed on abbreviations. Polymarket uses slugs like
`dota2-1win-bb4-2026-08-05`, which carry team text and a date, so the failure
mode should be different — but the corpora warn that markets on one event
multiply into handicaps, game-1 markets and prop questions, and pairing a
moneyline to a handicap is the classic phantom.

This measures the shape before any edge is computed.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "data" / "record.db"

con = sqlite3.connect(f"file:{REC.as_posix()}?mode=ro", uri=True, timeout=180)

print("== Polymarket rows by tag")
for tag, n, slugs, toks in con.execute(
        "select tag, count(1), count(distinct slug), count(distinct token_id) "
        "from p_book group by tag order by 2 desc"):
    print(f"   {tag:12} rows={n:>7,} slugs={slugs:>5} tokens={toks:>5}")

es = ("cs2", "dota-2", "valorant")
rows = con.execute(
    "select slug, outcome, count(1), min(ts_utc), max(ts_utc), "
    " avg(bid_c), avg(ask_c), avg(bid_size), avg(depth5) "
    "from p_book where tag in (?,?,?) group by slug, outcome",
    es).fetchall()
print(f"\n== esports: {len(rows)} (slug, outcome) pairs")

# What KIND of market is each slug? The phantom risk is pairing a moneyline to
# a handicap or a prop, so classify before joining anything.
KIND = [
    ("handicap", r"handicap"),
    ("map/game-n", r"-game\d|-map\d|game-\d"),
    ("prop", r"rampage|clutch|ace|first-|will-|total-|over-|under-|kills"),
    ("outright/futures", r"winner$|champion|to-win-the"),
]


def kind_of(slug):
    s = (slug or "").lower()
    for k, rx in KIND:
        if re.search(rx, s):
            return k
    return "moneyline?"


kinds = Counter(kind_of(r[0]) for r in rows)
print(f"   market kinds: {dict(kinds)}")

ml = [r for r in rows if kind_of(r[0]) == "moneyline?"]
print(f"\n== the {len(ml)} plausible MONEYLINE (slug, outcome) pairs")
print(f"   {'slug':56} {'outcome':16} {'snaps':>6} {'bid':>6} {'ask':>6} {'depth5':>9}")
for r in sorted(ml, key=lambda x: -x[2])[:16]:
    print(f"   {str(r[0])[:56]:56} {str(r[1])[:16]:16} {r[2]:>6} "
          f"{(r[5] or 0):>6.1f} {(r[6] or 0):>6.1f} {(r[8] or 0):>9.0f}")

# Do the two outcomes of one slug both appear? A one-sided record cannot be
# joined to a two-way sportsbook line.
per_slug = defaultdict(set)
for r in rows:
    per_slug[r[0]].add(r[1])
two = [s for s, o in per_slug.items() if len(o) >= 2]
print(f"\n   slugs with >=2 recorded outcomes: {len(two)} of {len(per_slug)}")
print(f"   (a slug recorded on only one side cannot be de-vigged against a "
      f"two-way line)")

print("\n== a slug's outcome vocabulary — is it TEAM names or Yes/No?")
oc = Counter(r[1] for r in rows)
print(f"   {oc.most_common(12)}")
con.close()
