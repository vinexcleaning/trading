r"""
t8_calibration.py - the full calibration curve of Kalshi's OPENING price, and
the resolution of the B026 tension with K009.

WHY THIS EXISTS
    t7 found "buy the heavy favourite" worth +4.31pp at the open, while K009
    (kalshi-market-scan, 762 settled matches) says the favourite-longshot bias
    does NOT exist on Kalshi. Both cannot be right as stated.

    t7's spread-stratified table already pointed at the answer: the residual is
    monotonic in the width of the opening book. This script makes that the
    primary measurement rather than a footnote, across the WHOLE price range.

THE TEST
    Bucket every event by opening price. In each bucket report the realised win
    rate against the implied probability, with a binomial CI, split by whether
    the opening book was tradeable (spread <= 2c) or not.

    If Kalshi is well calibrated where it is liquid, the tight-book curve should
    hug the diagonal and the wide-book curve should not.
"""
from __future__ import annotations
import os, sys, math

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "out"))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

pd.set_option("display.width", 260)

BUCKETS = [(1, 10), (10, 20), (20, 30), (30, 40), (40, 50),
           (50, 60), (60, 70), (70, 80), (80, 90), (90, 99)]


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def curve(df, label):
    print(f"\n--- {label}   n={len(df)}")
    print(f"{'band':>9} {'n':>5} {'implied':>8} {'actual':>8} "
          f"{'resid pp':>9} {'95% CI (pp)':>20} {'spread':>7}")
    rows = []
    for lo, hi in BUCKETS:
        s = df[(df.open_mid >= lo) & (df.open_mid < hi)]
        if len(s) < 25:
            continue
        n = len(s)
        k = int(s.outcome.sum())
        imp = s.implied.mean()
        act = k / n
        lo_ci, hi_ci = wilson(k, n)
        rows.append(dict(band=f"{lo}-{hi}", n=n, implied=imp, actual=act,
                         resid_pp=(act - imp) * 100,
                         ci_lo_pp=(lo_ci - imp) * 100,
                         ci_hi_pp=(hi_ci - imp) * 100,
                         spread=s.open_spread.mean(), label=label))
        star = "" if (lo_ci - imp) * (hi_ci - imp) < 0 else "  <-- CI excludes 0"
        print(f"{lo:3d}-{hi:<5d} {n:5d} {imp*100:8.1f} {act*100:8.1f} "
              f"{(act-imp)*100:+9.2f} "
              f"[{(lo_ci-imp)*100:+7.2f},{(hi_ci-imp)*100:+7.2f}] "
              f"{s.open_spread.mean():7.2f}{star}")
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(os.path.join(OUT, "t6_features.csv"))
    tight = df[df.open_spread <= 2]
    wide = df[df.open_spread > 4]

    print("=" * 92)
    print("CALIBRATION OF THE KALSHI OPENING PRICE")
    print("A well-calibrated market sits on the diagonal: actual == implied.")
    print("=" * 92)

    a = curve(df, "ALL books")
    t = curve(tight, "TRADEABLE books only (opening spread <= 2c)")
    w = curve(wide, "WIDE books (opening spread > 4c)")

    out = pd.concat([a, t, w])
    out.to_csv(os.path.join(OUT, "t8_calibration.csv"), index=False)

    # --- the summary statistic -----------------------------------------
    print("\n" + "=" * 92)
    print("THE ANSWER TO B026")
    print("=" * 92)
    for name, sub in [("ALL books", df), ("tight (<=2c)", tight),
                      ("wide (>4c)", wide)]:
        r = sub.residual
        se = r.std(ddof=1) / math.sqrt(len(r))
        print(f"  {name:14s} n={len(sub):5d}  mean residual {r.mean()*100:+6.2f}pp"
              f"  se {se*100:.2f}pp  t={r.mean()/se:+6.2f}")

    n_excl_t = int(((t.ci_lo_pp > 0) | (t.ci_hi_pp < 0)).sum()) if len(t) else 0
    n_excl_w = int(((w.ci_lo_pp > 0) | (w.ci_hi_pp < 0)).sum()) if len(w) else 0
    print(f"\n  price bands whose CI excludes zero:")
    print(f"    tradeable books: {n_excl_t} of {len(t)}")
    print(f"    wide books:      {n_excl_w} of {len(w)}")
    print("\n  K009 (kalshi-market-scan, 762 settled matches) reports the")
    print("  favourite-longshot bias does NOT exist on Kalshi, measured on")
    print("  TRADED prices. If the tradeable-book row above is flat, the two")
    print("  results agree and t7's +4.31pp was a wide-book quoting artifact.")


if __name__ == "__main__":
    main()
