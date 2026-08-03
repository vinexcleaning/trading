"""
venue_compare.py — would these strategies do better on Polymarket?

⚠ RETRACTED 2026-08-03 — THIS COMPARISON'S FEE INPUTS WERE BOTH WRONG.
    Do not quote any number this file produces. It is kept, corrected, so the
    error is not re-derived. Two independent defects:

    1. The Polymarket taker rate was written as `0.05 * C * p * (1-p)`, taken
       from documentation. Polymarket's real fee is a DIFFERENT SHAPE and a
       HIGHER rate: `0.10 * min(p, 1-p)`, established on 4,310 on-chain fills
       at median relative error 0.000000 (LEDGER C004) and independently
       reproduced on 5,362 fills (W015). The documented quadratic form matched
       0.0% of real fills. At 50c the truth is 5.00c/share against Kalshi's
       1.75c — Polymarket is 2.86x MORE expensive, not cheaper. LEDGER C015,
       "Polymarket taker cost is identical to Kalshi", is itself RETRACTED for
       the same reason: it trusted docs over the venue's own API.

    2. The Kalshi maker rate 0.0175 was applied unconditionally. Maker fees
       apply only where the series' `fee_type` is `quadratic_with_maker_fees`
       — 130 of 12,396 series, verified against the live API 2026-08-03. On
       plain `quadratic` series the maker fee is ZERO. This file never read
       `fee_type`, so every "maker" number it produced was wrong on ~99% of
       series and, for tennis, wrong in the direction that flattered Kalshi's
       maker side on ITF/Challenger (where the fee is zero) while charging it.

    The conclusion this file was written to support — "would these strategies
    do better on Polymarket?" — reversed sign once (1) was corrected. It is
    now answered by the shared cost bar in common/costbar.py, which uses the
    empirically-resolved formula for both venues.

WHAT THIS CAN AND CANNOT TELL YOU
    The PRICES are Kalshi's, reused as a stand-in for Polymarket's. That is an
    assumption, not a measurement. It is defensible for the same match at the
    same moment, but Polymarket tennis volume is thin (median event volume
    ~$450) so real fills could differ.
"""

from __future__ import annotations

import math
import os
import sys
import pickle

import numpy as np
import pandas as pd

SLIP = 1.0


_COMMON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from kalshi_fees import (  # noqa: E402
    SeriesFees, fee_order_dollars, maker_fee_order_cents,
)


def fee(venue: str, side: str, contracts: int, price_c: float,
        series: SeriesFees | None = None) -> float:
    """Fee in dollars for one leg.

    `series` is REQUIRED for the Kalshi maker side, because whether a maker
    fee exists at all is a per-series fact (`fee_type`). Passing None on the
    maker side raises rather than silently assuming 0.0175 — that assumption
    is the defect recorded at the top of this file.
    """
    if venue == "kalshi":
        if side == "taker":
            return fee_order_dollars(price_c, contracts)
        if series is None:
            raise ValueError(
                "Kalshi maker fee depends on the series' fee_type "
                "(quadratic_with_maker_fees on 130 of 12,396 series). "
                "Pass a SeriesFees read from the API; do not assume 0.0175.")
        return float(maker_fee_order_cents(price_c, contracts, series)) / 100.0

    # Polymarket: 0.10 * min(p, 1-p) per share, verified on-chain (C004/W015).
    # Makers are exempt. NOT the documented quadratic — see the header.
    p = price_c / 100.0
    if side != "taker":
        return 0.0
    return 0.10 * min(p, 1 - p) * contracts


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
