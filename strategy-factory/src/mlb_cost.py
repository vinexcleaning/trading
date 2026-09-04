"""THE COST BAR OF EVERY BASEBALL FAMILY, MEASURED OFF MY OWN TAPE.

Mailbox 012 asks for entry specs and says to say WHICH FAMILY each one trades.
That question is only answerable with a number: a family whose round trip costs
more than the edge on offer is not a market, it is a fee.

So this measures, per family, from real recorded touches:

  * the two-sided quote rate            - is there anything to trade at all
  * the median spread in cents          - half of it is what a taker pays
  * the median size at the ask          - can $25 even land
  * the FEE at the family's own rate    - KXMLBGAME is HALF fee, KXMLBWINS is
                                          FULL, and using one for the other is
                                          the mistake mailbox 011 caught
  * COST BAR = half spread + entry fee  - the edge a spec must beat to break
                                          even, in cents per contract

⚠ NOT the mid. Both sides of the real touch, per GUARDS and the session brief.
⚠ Fee is the UNROUNDED per-contract rate, because this is an expectancy bar,
  not a bill for one specific order. `fee_order_cents` at one contract would
  overstate it by up to 4.9x at 97c - the error corrected on 2026-09-01.
"""
from __future__ import annotations

import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

BASE_TAKER = 0.07
MIN_P, MAX_P = 5.0, 95.0


def fee_map():
    """series -> taker rate, from the census. Never inferred from the sport."""
    c = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "census.db"),
                        uri=True)
    out = {}
    for tk, mult in c.execute("select ticker, fee_multiplier from series "
                              "where ticker like 'KXMLB%'"):
        out[tk] = BASE_TAKER * (1.0 if mult is None else float(mult))
    c.close()
    return out


def main():
    fees = fee_map()
    c = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"),
                        uri=True)
    fams = [r[0] for r in c.execute(
        "select distinct series from w_names where series like 'KXMLB%'")]
    rows = []
    for f in sorted(fams):
        n = nq = 0
        spreads, asks, bars = [], [], []
        rate = fees.get(f, BASE_TAKER)
        for yb, ya, asz in c.execute(
                "select yes_bid_c, yes_ask_c, ask_size from w_top "
                "where series = ?", (f,)):
            n += 1
            if yb is None or ya is None or ya <= yb:
                continue
            if not (MIN_P <= ya <= MAX_P):
                continue
            nq += 1
            sp = ya - yb
            spreads.append(sp)
            asks.append(asz or 0.0)
            bars.append(sp / 2.0 + float(fee_rate_cents(ya, rate)))
        if nq < 200:
            continue
        rows.append((f, n, nq, 100.0 * nq / max(n, 1),
                     statistics.median(spreads), statistics.median(bars),
                     statistics.median(asks), rate))
    rows.sort(key=lambda r: r[5])
    print("%-18s %9s %8s %6s %7s %8s %7s %6s"
          % ("family", "instants", "2-sided", "%2s", "spread", "COSTBAR",
             "asksz", "rate"))
    for f, n, nq, pct, sp, bar, asz, rate in rows:
        print("%-18s %9d %8d %5.0f%% %6.1fc %7.2fc %7.0f %5.3f"
              % (f, n, nq, pct, sp, bar, asz, rate))


if __name__ == "__main__":
    main()
