"""THE BROAD PASS — every category on the exchange, and what it costs to trade.

Mailbox 014 §1: *"enumerate candidates across EVERY category, not the ones you
like. The census is the denominator - if a category is absent, say why."*
Mailbox 015 §6, twice: *"the biggest problem that Claude has is that it will
find something, narrow in on it, and then forget everything else."*

So this file refuses to be about baseball. It walks the WHOLE exchange from the
census and reports, per category and per family:

  * how many markets, and how many are quoted on both sides at all
  * the COST BAR - half the real spread plus the fee at that family's own rate
  * the size actually resting at the offer
  * whether anything in this project has ever touched it

**The cost bar is the screen, and it comes first, before any view about
anything.** Mailbox 014: *"screen on cost bar, quotability and available size
FIRST, before any edge estimate. Most things die here and they die cheaply."*
A family that costs 8 cents to enter cannot be rescued by a good idea, so
there is no point having ideas about it.

⚠ BOTH SIDES OF THE REAL TOUCH, NEVER THE MIDDLE PRICE.
⚠ THE FEE COMES FROM EACH SERIES' OWN MULTIPLIER, looked up in the census.
  Carrying one rate across families is the mistake that has now been made twice
  in this repo in opposite directions - baseball read as all-half-fee on
  2026-09-01, and combo legs read as all-full-fee on 2026-09-14.

    py -3 strategy-factory/src/broad.py
    py -3 strategy-factory/src/broad.py --by family --max-bar 2.0
"""
from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

BASE = 0.07
MIN_P, MAX_P = 5.0, 95.0

# Families this project has actually pointed a strategy at, so "untouched" is
# a fact rather than a feeling. Read off specs/ on 2026-09-18.
TOUCHED = set()


def load_touched():
    import json
    for p in (ROOT / "specs").glob("SF*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for f in d.get("families") or []:
            TOUCHED.add(f)


def census():
    """series -> (category, taker rate). Never inferred from the name."""
    c = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "census.db"),
                        uri=True)
    out = {}
    for tk, cat, mult in c.execute(
            "select ticker, category, fee_multiplier from series"):
        out[tk] = (cat or "(none)",
                   BASE * (1.0 if mult is None else float(mult)))
    c.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by", choices=["category", "family"], default="category")
    ap.add_argument("--max-bar", type=float, default=0.0,
                    help="family mode: only show families at or under this bar")
    ap.add_argument("--min-touch", type=int, default=400,
                    help="family mode: only families with this many touches")
    args = ap.parse_args()

    load_touched()
    cen = census()
    top = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"),
                          uri=True)

    fam = defaultdict(lambda: {"n": 0, "two": 0, "sp": [], "bar": [],
                               "ask": [], "mk": set()})
    for series, ticker, yb, ya, asz in top.execute(
            "select series, ticker, yes_bid_c, yes_ask_c, ask_size from w_top"):
        f = fam[series]
        f["n"] += 1
        if yb is None or ya is None or ya <= yb:
            continue
        if not (MIN_P <= ya <= MAX_P):
            continue
        rate = cen.get(series, ("?", BASE))[1]
        f["two"] += 1
        f["sp"].append(ya - yb)
        f["bar"].append((ya - yb) / 2.0 + float(fee_rate_cents(ya, rate)))
        f["ask"].append(asz or 0.0)
        f["mk"].add(ticker)

    if args.by == "family":
        rows = []
        for s, f in fam.items():
            if f["two"] < args.min_touch:
                continue
            bar = statistics.median(f["bar"])
            if args.max_bar and bar > args.max_bar:
                continue
            rows.append((bar, s, cen.get(s, ("?", BASE))[0], f["two"],
                         len(f["mk"]), statistics.median(f["ask"]),
                         s in TOUCHED))
        rows.sort()
        print("%-26s %-22s %8s %7s %8s %8s %s"
              % ("family", "category", "touches", "mkts", "COSTBAR", "at ask",
                 "ours?"))
        for bar, s, cat, two, nmk, ask, touched in rows:
            print("%-26s %-22s %8d %7d %7.2fc %8.0f %s"
                  % (s[:26], cat[:22], two, nmk, bar, ask,
                     "yes" if touched else "-"))
        print()
        print("%d families at or under %.2fc, of which %d have ever been "
              "pointed at by a strategy here."
              % (len(rows), args.max_bar or 99,
                 sum(1 for r in rows if r[6])))
        return

    cat = defaultdict(lambda: {"fams": set(), "two": 0, "bar": [], "ask": [],
                               "mk": set(), "touched": set(), "n": 0})
    for s, f in fam.items():
        c = cat[cen.get(s, ("(not in census)", BASE))[0]]
        c["fams"].add(s)
        c["two"] += f["two"]
        c["bar"] += f["bar"]
        c["ask"] += f["ask"]
        c["mk"] |= f["mk"]
        c["n"] += f["n"]
        if s in TOUCHED:
            c["touched"].add(s)

    print("EVERY CATEGORY ON THE EXCHANGE - the denominator, not a selection")
    print("Recorded 2026-08-18 to 09-18. Cost bar = half the real spread plus "
          "the fee at that")
    print("family's own rate. Both sides of the real touch, never the middle "
          "price.")
    print()
    print("%-24s %7s %8s %9s %8s %8s %7s"
          % ("category", "families", "markets", "touches", "COSTBAR", "at ask",
             "ours"))
    rows = []
    for name, c in cat.items():
        if not c["bar"]:
            rows.append((99.0, name, len(c["fams"]), len(c["mk"]), c["two"],
                         None, None, len(c["touched"])))
            continue
        rows.append((statistics.median(c["bar"]), name, len(c["fams"]),
                     len(c["mk"]), c["two"], statistics.median(c["bar"]),
                     statistics.median(c["ask"]), len(c["touched"])))
    for bar, name, nf, nmk, two, b, ask, nt in sorted(rows):
        print("%-24s %7d %8d %9d %7s %8s %4d/%d"
              % (name[:24], nf, nmk, two,
                 ("%.2fc" % b) if b is not None else "  none",
                 ("%.0f" % ask) if ask is not None else "  none", nt, nf))
    print()
    print("'ours' = families in this category that any strategy here has ever "
          "named, out of the")
    print("  families recorded. That column is the honest measure of how broad "
          "this project")
    print("  has actually been, as opposed to how broad it says it is.")


if __name__ == "__main__":
    main()
