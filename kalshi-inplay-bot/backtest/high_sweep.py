"""
high_sweep.py — sweep the "buy high and hold" idea across every dimension the
price-only dataset actually supports.

MAKER MODELLING
    Taker  : cross the spread, pay ask + slippage, always fills.
    Maker  : rest a limit at bid+1 and wait. It only fills if the market
             actually trades down to you, so we require a later candle whose
             low reaches our price within `patience` minutes. If it never
             does, there is NO TRADE — you watched it go up without you.

             This matters: modelling maker fills as "always get bid+1" is the
             single easiest way to fake a profitable backtest, because in
             reality you fill exactly when the price is coming toward you,
             which is disproportionately when it's about to keep going.

NOT TESTABLE HERE
    Anything score-based — won the first set, up N games, who is serving.
    The candle history has no score in it. That is what record_data.py is
    collecting live, and it is the only way those questions get answered.
"""

from __future__ import annotations

import math
import os
import sys
import pickle

import numpy as np
import pandas as pd

SLIP = 1.0
CONTRACTS = 8


_COMMON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from kalshi_fees import fee_order_dollars as _fee_order_dollars  # noqa: E402


def fee_d(contracts: int, price_c: float) -> float:
    """Kalshi taker fee in dollars. Exact Decimal — see common/kalshi_fees.py."""
    return _fee_order_dollars(price_c, contracts)


# Which tennis series actually charge makers, read from GET /series/{ticker}
# .fee_type (verified 2026-08-01, re-verified 2026-08-03):
#   KXATPMATCH, KXWTAMATCH        -> quadratic_with_maker_fees
#   KXATPCHALLENGERMATCH, KXITF*  -> quadratic  (maker fee ZERO)
# In this dataset that is 1,362 ATP/WTA markets against 12,800 ITF/Challenger,
# so the maker fee is zero on 90.4% of it.
#
# The RATE where it applies (0.25x taker) is Kalshi's published schedule and
# is NOT verifiable from the read-only API — the series object carries no
# maker-rate field. See common/kalshi_fees.py for the competing flat-0.25c
# reading. Treat any maker number this produces as convention-dependent.
_MAKER_MULTIPLIER_BY_TOUR = {
    "ATP": 0.25, "WTA": 0.25,
    "Challenger": 0.0, "ITF-M": 0.0, "ITF-W": 0.0,
}


def _maker_multiplier(tournament: str) -> float:
    """Fraction of the taker fee a maker pays on this series.

    Unknown tournaments default to 0.25 — the conservative side, since
    assuming a fee you do not pay understates the strategy rather than
    flattering it.
    """
    return _MAKER_MULTIPLIER_BY_TOUR.get(tournament, 0.25)


def simulate(views, lo, hi, *, maker=False, strict=False, patience=5, fav_min=None,
             fav_max=None, climb_min=None, phase=None, elapsed_min=None,
             elapsed_max=None, min_vol=None,
             max_spread=3, label=""):
    wins = losses = missed = 0
    net = 0.0
    entries = []

    for v in views:
        if np.isnan(v.settlement) or v.live.sum() < 10:
            continue
        op = v.mid[0]
        if fav_min is not None and op < fav_min:
            continue
        if fav_max is not None and op >= fav_max:
            continue

        ok = (v.mid >= lo) & (v.mid <= hi) & v.live & (v.spread <= max_spread)
        if climb_min is not None:
            ok &= (v.mid - op) >= climb_min
        # Minutes since the first live candle. Unlike `phase`, this is known
        # AT THE TIME OF TRADING — `phase` divides by the match's total length,
        # which you only learn once it has finished. That is look-ahead, and it
        # is why the "final third" result below is not tradeable.
        if elapsed_min is not None or elapsed_max is not None:
            live_idx = np.flatnonzero(v.live)
            t0 = v.ts[live_idx[0]]
            mins = (v.ts - t0) / 60.0
            if elapsed_min is not None:
                ok &= mins >= elapsed_min
            if elapsed_max is not None:
                ok &= mins < elapsed_max
        if phase is not None:
            live_idx = np.flatnonzero(v.live)
            first, last = live_idx[0], live_idx[-1]
            frac = (np.arange(v.n) - first) / max(1, last - first)
            ok &= (frac >= phase[0]) & (frac < phase[1])
        idx = np.flatnonzero(ok)
        if not len(idx):
            continue
        i0 = idx[0]

        if maker:
            want = v.bid_close[i0] + 1.0          # rest 1c inside the bid
            fill_i = None
            # Start at i0+1, NOT i0. Inside the entry candle the low is below
            # our limit by construction, so including it fills every order
            # instantly and manufactures a profit that does not exist. We only
            # get filled if the market comes back to us on a LATER candle; if
            # it runs away upward we miss the trade entirely, which is the
            # real cost of resting instead of crossing.
            for j in range(i0 + 1, min(v.n, i0 + patience + 1)):
                if not v.live[j]:
                    continue
                if strict:
                    # Someone must actually be willing to SELL at our price:
                    # the ask has to come down to us. This is the pessimistic
                    # bound, and it captures adverse selection — we fill when
                    # sellers are pressing, which is not when we'd like to buy.
                    hit = v.ask_close[j] <= want
                else:
                    hit = v.bid_low[j] <= want
                if hit:
                    fill_i = j
                    break
            if fill_i is None:
                missed += 1
                continue
            entry = want
            # Maker fee is a PER-SERIES fact, not a constant. This line used
            # to be an unconditional `fee_mult = 0.25`, which charged a maker
            # fee on ITF and Challenger — verified `quadratic` (taker-only,
            # maker fee ZERO) and ~91% of the tennis book (LEDGER S010).
            # Only KXATPMATCH and KXWTAMATCH are
            # `quadratic_with_maker_fees`. Charging 0.25x taker on the other
            # 91% overstated maker cost and understated the maker case.
            fee_mult = _maker_multiplier(v.tournament)
        else:
            entry = v.ask_close[i0] + SLIP
            fee_mult = 1.0

        if not (1 <= entry < 100):
            continue
        cost = CONTRACTS * entry / 100.0 + fee_d(CONTRACTS, entry) * fee_mult
        entries.append(entry)

        payout = CONTRACTS * (1.0 if v.settlement >= 99.5 else 0.0)
        if v.settlement >= 99.5:
            wins += 1
        else:
            losses += 1
        net += payout - cost

    n = wins + losses
    mode = ("maker-strict" if strict else "maker") if maker else "taker"
    return {"filter": label, "band": f"{lo}-{hi}", "mode": mode,
            "trades": n, "missed": missed,
            "avg_entry": np.mean(entries) if entries else 0,
            "win%": wins / n * 100 if n else 0,
            "net_$": net,
            "c/contract": net / (n * CONTRACTS) * 100 if n else 0}


def show(rows, title):
    print(f"\n=== {title} ===")
    df = pd.DataFrame(rows).sort_values("c/contract", ascending=False)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


def main():
    views, _ = pickle.load(open("data/views.pkl", "rb"))
    pd.set_option("display.width", 220)

    bands = [(85, 89), (90, 92), (93, 95), (96, 97)]

    rows = []
    for lo, hi in bands:
        rows.append(simulate(views, lo, hi, label="all markets"))
        rows.append(simulate(views, lo, hi, maker=True, label="all markets"))
        rows.append(simulate(views, lo, hi, maker=True, strict=True,
                             patience=10, label="all markets"))
    show(rows, "1. TAKER vs MAKER (optimistic) vs MAKER (strict fill)")

    show([simulate(views, 93, 95, maker=True, patience=p,
                   label=f"wait {p}min for a fill")
          for p in (1, 3, 5, 10, 20)],
         "2. HOW LONG TO WAIT FOR A MAKER FILL (93-95c)")

    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for f0, f1, name in [(None, 40, "opened <40c (underdog)"),
                             (40, 60, "opened 40-60c (even)"),
                             (60, 80, "opened 60-80c (favourite)"),
                             (80, None, "opened 80c+ (heavy fav)")]:
            rows.append(simulate(views, lo, hi, maker=True,
                                 fav_min=f0, fav_max=f1, label=name))
    show(rows, "3. BY PRE-MATCH FAVOURITE (maker)")

    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for c in [None, 10, 25, 40, 60]:
            rows.append(simulate(views, lo, hi, maker=True, climb_min=c,
                                 label=f"climbed >={c}c from open" if c else "any climb"))
    show(rows, "4. BY HOW FAR IT CLIMBED FROM THE OPENING LINE (maker)")

    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for a, b, name in [(0.0, 0.33, "first third of match"),
                           (0.33, 0.66, "middle third"),
                           (0.66, 1.01, "final third")]:
            rows.append(simulate(views, lo, hi, maker=True, phase=(a, b), label=name))
    show(rows, "5. BY WHEN IN THE MATCH (maker)")

    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for s in (1, 2, 3):
            rows.append(simulate(views, lo, hi, maker=True, max_spread=s,
                                 label=f"spread <={s}c"))
    show(rows, "6. BY SPREAD (maker)")

    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for lo_m, hi_m, name in [(0, 45, "0-45 min in"), (45, 90, "45-90 min in"),
                                 (90, 150, "90-150 min in"), (150, None, "150+ min in")]:
            rows.append(simulate(views, lo, hi, maker=True, elapsed_min=lo_m,
                                 elapsed_max=hi_m, label=name))
    show(rows, "7. BY MINUTES ELAPSED - tradeable, no look-ahead (maker)")

    rows = []
    for lo, hi in [(90, 92), (93, 95)]:
        for e in (60, 90, 120):
            rows.append(simulate(views, lo, hi, maker=True, elapsed_min=e,
                                 label=f">={e} min in (optimistic fill)"))
            rows.append(simulate(views, lo, hi, maker=True, strict=True, patience=10,
                                 elapsed_min=e, label=f">={e} min in (STRICT fill)"))
            rows.append(simulate(views, lo, hi, elapsed_min=e,
                                 label=f">={e} min in (taker)"))
    show(rows, "8. THE SURVIVOR, UNDER ALL THREE FILL MODELS")


if __name__ == "__main__":
    main()
