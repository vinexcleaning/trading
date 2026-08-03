"""
longshot.py — the opposite bet: buy cheap, hope for a comeback.

$1 a go on a 10c underdog buys ~9 contracts. If he climbs to 20c you've
doubled; if he wins outright it's 10x. The catch is that the fee is a
percentage of a much smaller number: at 10c the taker fee is ~0.63c per
contract, which is over 6% of the position before anything happens. That is
the thing this measures.

Two exit styles, because they are completely different bets:
  * HOLD    - ride to settlement, betting the comeback completes
  * TAKE +X - sell into any bounce, never mind who wins the match

Costs: real ask + 1c slip in, real bid - 1c slip out, fee both sides.
"""

from __future__ import annotations

import math
import os
import sys
import pickle

import numpy as np
import pandas as pd

SLIP = 1.0
STAKE = 1.00          # dollars per trade


_COMMON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from kalshi_fees import fee_order_dollars as _fee_order_dollars  # noqa: E402


def fee_d(contracts: int, price_c: float) -> float:
    """Kalshi taker fee in dollars. Exact Decimal — see common/kalshi_fees.py."""
    return _fee_order_dollars(price_c, contracts)


def run(views, lo, hi, *, take=None, stop=None, max_spread=3,
        fell_min=None, label=""):
    """take: sell at entry+take cents. None = hold to settlement."""
    wins = losses = took = stopped = 0
    net = 0.0
    entries, sizes = [], []

    for v in views:
        if np.isnan(v.settlement) or v.live.sum() < 10:
            continue
        op = v.mid[0]
        ok = (v.mid >= lo) & (v.mid <= hi) & v.live & (v.spread <= max_spread)
        if fell_min is not None:
            ok &= (op - v.mid) >= fell_min      # how far it has COLLAPSED
        idx = np.flatnonzero(ok)
        if not len(idx):
            continue
        i0 = idx[0]
        entry = v.ask_close[i0] + SLIP
        if not (1 <= entry < 100):
            continue
        contracts = max(1, int(STAKE / (entry / 100.0)))
        cost = contracts * entry / 100.0 + fee_d(contracts, entry)
        entries.append(entry)
        sizes.append(contracts)

        exit_val = None
        target = entry + take if take else None
        for j in range(i0 + 1, v.n):
            if not v.live[j]:
                continue
            # stop first: same-candle ties always resolve against us
            if stop is not None and v.bid_low[j] <= stop:
                px = max(1.0, min(v.bid_close[j], stop) - SLIP)
                exit_val = contracts * px / 100.0 - fee_d(contracts, px)
                stopped += 1
                break
            if target is not None and v.bid_high[j] >= target:
                px = target - SLIP
                exit_val = contracts * px / 100.0 - fee_d(contracts, px)
                took += 1
                break
        if exit_val is None:
            won = v.settlement >= 99.5
            exit_val = contracts * (1.0 if won else 0.0)
            if won:
                wins += 1
            else:
                losses += 1
        net += exit_val - cost

    n = wins + losses + took + stopped
    return {"filter": label, "band": f"{lo}-{hi}c",
            "take": f"+{take}c" if take else "hold",
            "stop": stop if stop else "none",
            "trades": n, "avg_entry": np.mean(entries) if entries else 0,
            "avg_size": np.mean(sizes) if sizes else 0,
            "settled_win": wins, "hit_take": took, "stopped": stopped,
            "net_$": net,
            "$/trade": net / n if n else 0,
            "roi_%": net / (STAKE * n) * 100 if n else 0}


def show(rows, title):
    print(f"\n=== {title} ===")
    df = pd.DataFrame(rows).sort_values("$/trade", ascending=False)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


def main():
    views, _ = pickle.load(open("data/views.pkl", "rb"))
    pd.set_option("display.width", 240)

    bands = [(4, 7), (8, 12), (13, 18), (19, 25), (26, 32)]

    show([run(views, lo, hi, label="hold to settlement") for lo, hi in bands],
         "1. BUY CHEAP AND HOLD - betting the comeback completes")

    rows = []
    for lo, hi in [(8, 12), (13, 18), (19, 25)]:
        for t in (3, 5, 10, 15, 25):
            rows.append(run(views, lo, hi, take=t, label="sell into a bounce"))
    show(rows, "2. BUY CHEAP AND SELL INTO ANY BOUNCE")

    rows = []
    for lo, hi in [(8, 12), (13, 18)]:
        for t in (5, 10, 20):
            for s in (None, 3, 5):
                rows.append(run(views, lo, hi, take=t, stop=s, label="with a stop"))
    show(rows, "3. DOES A STOP HELP THE BOUNCE TRADE?")

    rows = []
    for lo, hi in [(8, 12), (13, 18), (19, 25)]:
        for f in (None, 20, 40, 60):
            rows.append(run(views, lo, hi, take=10, fell_min=f,
                            label=f"collapsed >={f}c from open" if f else "any"))
    show(rows, "4. ONLY BUY PLAYERS WHO HAVE COLLAPSED (take +10c)")

    print("\n\n=== THE BREAKEVEN BAR ===")
    for x in (5, 10, 15, 20, 30):
        entry = x + SLIP
        c = max(1, int(STAKE / (entry / 100.0)))
        cost = c * entry / 100 + fee_d(c, entry)
        print(f"  buy at {x}c ({c} contracts, ${cost:.2f} all-in) -> "
              f"need to win {cost / c * 100:.1f}% of the time, "
              f"or a {cost / c * 100 - entry + SLIP:.1f}c bounce to break even")


if __name__ == "__main__":
    main()
