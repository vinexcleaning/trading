"""Is the cost bar in SHORTLIST.md measured at a time you could not trade?

Every dimension-C number in this project - and in `market-selection` before it -
comes from probing the book AT THE TOUCH, on markets sampled while they are
live or close to it. `market-selection` recorded 1.0c median spreads and 21,236
contracts at the touch on KXCS2GAME, and this session's recorder reproduces
100% two-sided uptime on the same series.

But the grid's own naive benchmarks at a -24h anchor come back at **-6.8c
(random side) and -8.7c (buy the kept side)** - three to four times the ~2.2c
cost bar those touch measurements imply. Either the benchmark is wrong or the
cost bar is being read at a moment a pre-match strategy cannot use.

This measures the spread as a function of LEAD TIME, from the same candle panel
the grid uses. If the spread widens sharply with lead, then a strategy that must
decide a day ahead pays a completely different cost from the one dimension C
reports, and every entry in the shortlist is costed at the wrong point.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "kalshi_soccer.db"
REP = ROOT / "reports"
SERIES = ["KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME", "KXMLBGAME"]
LEADS = [15, 30, 60, 120, 180, 360, 720, 1440, 2880]


def ts(s):
    if not s:
        return None
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(s, f).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def q(a, p):
    return float(np.percentile(a, p)) if len(a) else float("nan")


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=120)
    out = {}
    for s in SERIES:
        rows = []
        for ev, tk, ct in con.execute(
                "select event_ticker, ticker, close_time from markets "
                "where series=? and result in ('yes','no')", (s,)):
            c = ts(ct)
            if c is None:
                continue
            cds = con.execute(
                "select end_period_ts, yes_bid_close, yes_ask_close from candles "
                "where ticker=? and yes_bid_close is not null "
                "and yes_ask_close is not null order by end_period_ts",
                (tk,)).fetchall()
            if cds:
                rows.append((c, cds))
        print(f"\n== {s}  ({len(rows)} markets with a quoted panel)")
        print(f"   {'lead':>7} {'n':>6} {'spread med':>11} {'p90':>7} "
              f"{'mean':>7}   round-trip cost implied")
        ser = {}
        for lead in LEADS:
            sp = []
            for close, cds in rows:
                cut = close - lead * 60
                best = None
                for t, b, a in cds:
                    if t < cut:
                        best = (b, a)
                if best and best[1] is not None and best[0] is not None:
                    d = best[1] - best[0]
                    if 0 <= d <= 100:
                        sp.append(d)
            if not sp:
                continue
            sp = np.asarray(sp, dtype=float)
            med, p90, mean = q(sp, 50), q(sp, 90), float(sp.mean())
            # A taker who enters and exits pays the full spread once each way;
            # a hold-to-settlement strategy pays it ONCE on entry (there is no
            # settlement fee - GUARDS #6), so half-spread is the entry cost.
            print(f"   {lead:>6}m {len(sp):>6} {med:>11.2f} {p90:>7.2f} "
                  f"{mean:>7.2f}   entry half-spread {med/2:>5.2f}c")
            ser[lead] = {"n": len(sp), "median": med, "p90": p90,
                         "mean": mean}
        out[s] = ser

    print("\n== THE COMPARISON THAT MATTERS")
    print("   dimension C in SHORTLIST.md / market-selection was measured AT "
          "THE TOUCH on live markets.")
    print(f"   {'series':16} {'spread @touch-ish (15m)':>24} "
          f"{'spread @-24h':>14} {'ratio':>7}")
    for s, ser in out.items():
        near = ser.get(15) or ser.get(30) or ser.get(60)
        far = ser.get(1440)
        if not near or not far:
            continue
        r = far["median"] / near["median"] if near["median"] else float("nan")
        print(f"   {s:16} {near['median']:>24.2f} {far['median']:>14.2f} "
              f"{r:>6.1f}x")
    (REP / "spread_vs_lead.json").write_text(json.dumps(out, indent=1),
                                             encoding="utf-8")
    print("\nwrote reports/spread_vs_lead.json")
    con.close()


if __name__ == "__main__":
    main()
