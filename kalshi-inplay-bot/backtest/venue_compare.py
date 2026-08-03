"""
venue_compare.py — would these strategies do better on Polymarket?

FEE FACTS (from each venue's own docs)
    Kalshi      taker  ceil(0.07 * C * p * (1-p))      maker 0.0175 (25% of taker)
    Polymarket  taker       0.05 * C * p * (1-p)       maker 0.00  (+0.2% US rebate)

    Same formula shape. Two differences that matter: Polymarket's taker rate is
    lower, and Polymarket's MAKER FEE IS ZERO where Kalshi still charges a
    quarter of taker.

WHAT THIS CAN AND CANNOT TELL YOU
    The fee arithmetic is exact — both formulas are published.
    The PRICES are Kalshi's, reused as a stand-in for Polymarket's. That is an
    assumption, not a measurement. It is defensible for the same match at the
    same moment, but Polymarket tennis volume is thin (median event volume
    ~$450) so real fills could differ. Treat the fee delta as solid and the
    rest as indicative.
"""

from __future__ import annotations

import math
import pickle

import numpy as np
import pandas as pd

SLIP = 1.0


def fee(venue: str, side: str, contracts: int, price_c: float) -> float:
    p = price_c / 100.0
    base = contracts * p * (1 - p)
    if venue == "kalshi":
        rate = 0.07 if side == "taker" else 0.0175
        return math.ceil(rate * base * 100) / 100.0
    rate = 0.05 if side == "taker" else 0.0
    return rate * base


def run(views, lo, hi, venue, side, stake=None, contracts_fixed=8,
        take=None, max_spread=3):
    wins = losses = took = 0
    net = 0.0
    for v in views:
        if np.isnan(v.settlement) or v.live.sum() < 10:
            continue
        idx = np.flatnonzero((v.mid >= lo) & (v.mid <= hi) & v.live
                             & (v.spread <= max_spread))
        if not len(idx):
            continue
        i0 = idx[0]
        # taker crosses the spread; maker rests at bid+1 and we assume the
        # optimistic fill, which flatters maker — noted in the writeup
        entry = (v.ask_close[i0] + SLIP) if side == "taker" else (v.bid_close[i0] + 1.0)
        if not (1 <= entry < 100):
            continue
        c = max(1, int(stake / (entry / 100.0))) if stake else contracts_fixed
        cost = c * entry / 100.0 + fee(venue, side, c, entry)

        out = None
        if take:
            tgt = entry + take
            for j in range(i0 + 1, v.n):
                if v.live[j] and v.bid_high[j] >= tgt:
                    px = tgt - SLIP
                    out = c * px / 100.0 - fee(venue, side, c, px)
                    took += 1
                    break
        if out is None:
            won = v.settlement >= 99.5
            out = c * (1.0 if won else 0.0)
            wins += won
            losses += (not won)
        net += out - cost

    n = wins + losses + took
    per_c = net / (n * contracts_fixed) * 100 if (n and not stake) else None
    return {"venue": venue, "side": side, "band": f"{lo}-{hi}c",
            "trades": n, "net_$": net,
            "c/contract": per_c if per_c is not None else float("nan"),
            "roi_%": net / (stake * n) * 100 if (stake and n) else float("nan")}


def main():
    views, _ = pickle.load(open("data/views.pkl", "rb"))
    pd.set_option("display.width", 200)

    print("=== BUY HIGH AND HOLD (8 contracts, ~$6) ===")
    rows = [run(views, lo, hi, ven, sd)
            for lo, hi in [(90, 92), (93, 95)]
            for ven in ("kalshi", "polymarket")
            for sd in ("taker", "maker")]
    df = pd.DataFrame(rows).sort_values("c/contract", ascending=False)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print("\n\n=== LONGSHOTS, $1 a go, sell into a +10c bounce ===")
    rows = [run(views, lo, hi, ven, sd, stake=1.0, take=10)
            for lo, hi in [(8, 12), (13, 18)]
            for ven in ("kalshi", "polymarket")
            for sd in ("taker", "maker")]
    df = pd.DataFrame(rows).sort_values("roi_%", ascending=False)
    print(df[["venue", "side", "band", "trades", "net_$", "roi_%"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print("\n\n=== FEE PER CONTRACT, SIDE BY SIDE (cents) ===")
    rows = []
    for p in (10, 25, 50, 75, 90, 95):
        rows.append({"price": f"{p}c",
                     "kalshi_taker": fee("kalshi", "taker", 100, p) / 100 * 100,
                     "kalshi_maker": fee("kalshi", "maker", 100, p) / 100 * 100,
                     "poly_taker": fee("polymarket", "taker", 100, p) / 100 * 100,
                     "poly_maker": fee("polymarket", "maker", 100, p) / 100 * 100})
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
