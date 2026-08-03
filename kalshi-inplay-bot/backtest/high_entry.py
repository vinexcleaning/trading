"""
high_entry.py — test the "buy at 90c+, it's basically guaranteed" idea.

The appeal is obvious: a 95c favourite wins nearly always. The problem is
equally arithmetic: you risk 95c to make 5c, so you need to be right ~95% of
the time BEFORE costs just to break even. This measures whether the real hit
rate clears that bar once spread and fees are paid.

Entry  : real ask + slippage, first time mid enters the band
Exit   : settlement, or the stop if price trades down to it first
Costs  : fee = ceil(0.07 * C * P * (1-P)) each side; settlement pays no exit fee
"""

from __future__ import annotations

import math
import pickle

import numpy as np
import pandas as pd

SLIP = 1.0          # cents against us on entry and on any sold exit
CONTRACTS = 8       # ~$6 notional at these prices


def fee_dollars(contracts: int, price_c: float) -> float:
    p = price_c / 100.0
    return math.ceil(0.07 * contracts * p * (1 - p) * 100) / 100.0


def run(views, lo: int, hi: int, stop: int | None,
        fav_min: int | None = None) -> dict:
    wins = losses = stopped = 0
    net = 0.0
    entries = []
    for v in views:
        if np.isnan(v.settlement):
            continue
        live = v.live
        if live.sum() < 10:
            continue
        if fav_min is not None:
            op = v.mid[0]
            if not (op >= fav_min):
                continue
        idx = np.flatnonzero((v.mid >= lo) & (v.mid <= hi) & live
                             & (v.spread <= 3))
        if not len(idx):
            continue
        i0 = idx[0]
        entry = v.ask_close[i0] + SLIP
        if entry >= 100:
            continue
        cost = CONTRACTS * entry / 100.0 + fee_dollars(CONTRACTS, entry)
        entries.append(entry)

        exit_val = None
        if stop is not None:
            for j in range(i0 + 1, v.n):
                if not live[j]:
                    continue
                if v.bid_low[j] <= stop:
                    px = max(1.0, min(v.bid_close[j], stop) - SLIP)
                    exit_val = (CONTRACTS * px / 100.0
                                - fee_dollars(CONTRACTS, px))
                    stopped += 1
                    break
        if exit_val is None:
            exit_val = CONTRACTS * (1.0 if v.settlement >= 99.5 else 0.0)
            if v.settlement >= 99.5:
                wins += 1
            else:
                losses += 1
        net += exit_val - cost

    n = wins + losses + stopped
    return {"band": f"{lo}-{hi}c", "stop": stop if stop else "none",
            "trades": n, "avg_entry": np.mean(entries) if entries else 0,
            "settled_win": wins, "settled_loss": losses, "stopped": stopped,
            "win_rate": wins / n * 100 if n else 0,
            "net_$": net, "net_c_per_contract": net / (n * CONTRACTS) * 100 if n else 0}


def main() -> None:
    views, markets = pickle.load(open("data/views.pkl", "rb"))
    pd.set_option("display.width", 200)

    print("=== BUY HIGH, HOLD TO SETTLEMENT ===")
    print("(entry = real ask +1c slip, spread <=3c, 8 contracts)\n")
    rows = [run(views, lo, hi, None)
            for lo, hi in [(85, 89), (90, 92), (93, 95), (96, 97), (98, 98)]]
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print("\n\n=== SAME, WITH A STOP LOSS ===\n")
    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for stop in [None, 85, 80, 70, 60, 50]:
            rows.append(run(views, lo, hi, stop))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print("\n\n=== ONLY WHERE THE MARKET OPENED THEM FAVOURITE (>=60c) ===\n")
    rows = []
    for lo, hi in [(90, 92), (93, 95), (96, 97)]:
        for stop in [None, 80]:
            rows.append({**run(views, lo, hi, stop, fav_min=60),
                         "filter": "opened >=60c"})
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print("\n\n=== THE BREAKEVEN BAR ===")
    print("Buying at X and holding needs this hit rate just to cover costs:\n")
    for x in [85, 90, 92, 95, 97]:
        entry = x + SLIP
        cost = CONTRACTS * entry / 100 + fee_dollars(CONTRACTS, entry)
        need = cost / CONTRACTS * 100
        print(f"  buy at {x}c (pay {entry:.0f}c + fee) -> need to win "
              f"{need:.1f}% of the time to break even")


if __name__ == "__main__":
    main()
