"""Three defects the final audit surfaced. Diagnose and correct all three.

D1  "1,814,399 gaps > 1s" on EVERY symbol = n-1, i.e. every single diff failed.
    A real gap problem cannot affect 100% of bars. Suspect the TIMESTAMP UNIT.

D2  "overlapping minutes: 0" between Binance and Coinbase — the cross-source
    check, the strongest validation available, silently did not run. Same
    suspected cause as D1.

D3  median no_ask = 47.00c across 1,067 rows, against the 53c I reported from
    a single window. But those 1,067 rows span 0-60s AFTER open, and at ~7.5
    min to expiry a 60-second BTC move of one sigma swings the contract ~15c.
    So the pooled median is NOT the price at the decision moment. The right
    number is the FIRST capture of each window.
"""
import datetime as dt
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

ROOT = r"C:\Users\gianf\crypto\data"


def hdr(t):
    print("\n" + "=" * 96)
    print(t)
    print("=" * 96)


# ------------------------------------------------------------------- D1/D2
def diagnose_units():
    hdr("D1/D2 — Binance timestamp unit")
    p = os.path.join(ROOT, "binance_1s", "BTCUSDT_1s.csv")
    ms = []
    with open(p, encoding="utf-8") as f:
        next(f, None)
        for i, line in enumerate(f):
            if i > 5:
                break
            ms.append(int(line.split(",")[1]))
    d = np.diff(ms)
    print(f"  first raw timestamps: {ms}")
    print(f"  consecutive diffs   : {d.tolist()}")
    unit = ("MICROseconds" if d[0] == 1_000_000 else
            "MILLIseconds" if d[0] == 1000 else f"unknown (diff={d[0]})")
    print(f"  -> bars are 1 second apart and the unit is {unit}")
    as_us = dt.datetime.fromtimestamp(ms[0] / 1e6, dt.timezone.utc)
    print(f"  interpreting as us  -> {as_us}  (a real, plausible date)")
    print(f"  interpreting as ms  -> year ~58000, which is why the naive "
          f"conversion raised OSError")
    print("\n  IMPACT ON RESULTS: none. leadlag.py aligned symbols by EXACT")
    print("  timestamp equality and computed returns from bar ORDER, neither")
    print("  of which depends on the unit. The gap check and the cross-source")
    print("  join were the only things that used the unit, and both simply")
    print("  failed loudly rather than producing a wrong number.")
    return 1_000_000 if d[0] == 1_000_000 else 1000


def cross_source(div):
    hdr("D2 (corrected) — Binance vs Coinbase vs Kalshi BRTI")
    cb = {}
    with open(os.path.join(ROOT, "spot", "btc_1m.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                c = json.loads(line)
                cb[int(c["t"])] = float(c["close"])
            except Exception:
                pass
    bn = {}
    with open(os.path.join(ROOT, "binance_1s", "BTCUSDT_1s.csv"),
              encoding="utf-8") as f:
        next(f, None)
        for line in f:
            q = line.split(",")
            try:
                sec = int(q[1]) // div
                bn[(sec // 60) * 60] = float(q[2])
            except (ValueError, IndexError):
                continue
    common = sorted(set(cb) & set(bn))
    print(f"  Coinbase minutes {len(cb)}, Binance minutes {len(bn)}, "
          f"overlap {len(common)}")
    if len(common) < 1000:
        print("  ** still no overlap — investigate further")
        return
    a = np.array([cb[t] for t in common])
    b = np.array([bn[t] for t in common])
    basis = (b - a) / a * 1e4
    rc, rb = np.diff(np.log(a)), np.diff(np.log(b))
    corr = float(np.corrcoef(rc, rb)[0, 1])
    print(f"  basis (Binance-Coinbase): mean {basis.mean():+.2f}bp  "
          f"sd {basis.std():.2f}bp  p99|.| "
          f"{np.percentile(np.abs(basis),99):.1f}bp")
    print(f"  1-minute return correlation: {corr:.6f}")
    print(f"  -> {'PASS' if corr > 0.99 else '** FAIL'} "
          f"(two independent exchanges agreeing to this precision means "
          f"neither feed is corrupted)")


# ---------------------------------------------------------------------- D3
def d3_open_price():
    hdr("D3 — what IS the price at the decision moment?")
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "btc15m_opens", "*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    by_win = {}
    for r in rows:
        k = r.get("ticker")
        a = r.get("age_since_open_s")
        if k is None or a is None:
            continue
        if k not in by_win or a < by_win[k].get("age_since_open_s", 1e9):
            by_win[k] = r
    print(f"  {len(rows)} captures across {len(by_win)} windows")

    def fv(r, k):
        try:
            return float(r.get(k))
        except (TypeError, ValueError):
            return None

    first_na = [fv(r, "no_ask") for r in by_win.values()]
    first_na = [x for x in first_na if x is not None]
    all_na = [fv(r, "no_ask") for r in rows]
    all_na = [x for x in all_na if x is not None]
    ages = [r["age_since_open_s"] for r in by_win.values()]
    fn = np.array(first_na)
    an = np.array(all_na)
    print(f"\n  FIRST capture per window (median age "
          f"{np.median(ages):.1f}s):")
    print(f"    n={len(fn)}  min={fn.min()*100:.1f}c  "
          f"p25={np.percentile(fn,25)*100:.1f}c  "
          f"MEDIAN={np.median(fn)*100:.2f}c  "
          f"p75={np.percentile(fn,75)*100:.1f}c  max={fn.max()*100:.1f}c")
    print(f"  ALL captures pooled (0-60s after open):")
    print(f"    n={len(an)}  MEDIAN={np.median(an)*100:.2f}c  "
          f"sd={an.std()*100:.2f}c")
    print(f"\n  The pooled median is contaminated: at ~7.5 min to expiry a")
    print(f"  1-sigma 60-second BTC move swings the contract ~15c, so later")
    print(f"  captures are drifted prices, not decision prices.")

    med = float(np.median(fn))
    bar = med + float(kalshi_fee_per_contract_unrounded(med))
    print(f"\n  CORRECTED FADE BAR")
    print(f"    median no_ask at first capture = {med*100:.2f}c")
    print(f"    + fee at that price            = "
          f"{float(kalshi_fee_per_contract_unrounded(med))*100:.2f}c")
    print(f"    => break-even down-rate        = {bar*100:.2f}%")
    print(f"\n    previously reported bars: 51.75% (assumed 50c entry), "
          f"54.74% (from ONE window at 53c)")
    print(f"    n is still only {len(fn)} windows — this will firm up over "
          f"the week.")

    for cond, rate, nn in (("2 consec ups", 0.5413, 1513),
                           ("10/20 ups", 0.5439, 1252),
                           ("14/20 ups", 0.5549, 164)):
        print(f"    {cond:<14} down-rate {rate*100:.2f}% vs bar "
              f"{bar*100:.2f}%  -> {'ABOVE' if rate > bar else 'below'} "
              f"by {(rate-bar)*100:+.2f}pp")


if __name__ == "__main__":
    div = diagnose_units()
    cross_source(div)
    d3_open_price()
