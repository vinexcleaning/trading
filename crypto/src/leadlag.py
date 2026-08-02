"""CROSS-ASSET LEAD-LAG at 1-second resolution.

The last hypothesis in this project with zero evidence against it. Every prior
measurement of BTC/ETH relatedness here was CONTEMPORANEOUS and HOURLY
(corr 0.891) — structurally blind to a lead.

THE TRAP THIS TEST MUST AVOID (and it is the reason naive lead-lag studies are
almost always wrong): **stale prices manufacture fake lead-lag.**

If BTC trades every second and DOGE trades every 5 seconds, DOGE's 1-second
"close" is often just its last trade from several seconds ago. A stale series
mechanically appears to LAG a fresh one, with no information flow whatsoever.
This is the Epps effect / Lo-MacKinlay non-synchronous trading bias. It produces
textbook-looking lead-lag curves out of pure illiquidity.

Controls run here:
  C1  staleness census — fraction of 1s bars with ZERO volume, per asset
  C2  lead-lag computed on ALL bars vs only bars where BOTH assets traded
  C3  synthetic control — two INDEPENDENT random walks, same length, must show
      zero cross-correlation at every lag
  C4  a stale-price simulation — take one real series, create a deliberately
      staled copy, and confirm the pipeline reports the fake lead. If it does
      NOT, the pipeline cannot detect the bias it is supposed to control for.
  C5  two disjoint periods

Only a lead that survives C2 and is absent in C3 is worth anything.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

DATA = r"C:\Users\gianf\crypto\data\binance_1s"
OUT = r"C:\Users\gianf\crypto\reports"


def load(sym):
    """-> (ms array, close array, volume array), sorted, deduped."""
    p = os.path.join(DATA, f"{sym}_1s.csv")
    if not os.path.exists(p):
        return None
    ms, px, vol = [], [], []
    with open(p, encoding="utf-8") as f:
        next(f, None)
        for line in f:
            q = line.rstrip("\n").split(",")
            if len(q) < 4:
                continue
            try:
                ms.append(int(q[1]))
                px.append(float(q[2]))
                vol.append(float(q[3]))
            except ValueError:
                continue
    ms = np.array(ms, dtype=np.int64)
    px = np.array(px)
    vol = np.array(vol)
    o = np.argsort(ms)
    ms, px, vol = ms[o], px[o], vol[o]
    keep = np.concatenate(([True], np.diff(ms) > 0))
    return ms[keep], px[keep], vol[keep]


def align(series):
    """Intersect timestamps across all symbols."""
    common = None
    for _, (ms, _, _) in series.items():
        s = set(ms.tolist())
        common = s if common is None else (common & s)
    common = np.array(sorted(common), dtype=np.int64)
    out = {}
    for sym, (ms, px, vol) in series.items():
        idx = np.searchsorted(ms, common)
        out[sym] = (px[idx], vol[idx])
    return common, out


def xcorr(ra, rb, max_lag):
    """corr(ra[t], rb[t+lag]) for lag in [-max_lag, max_lag].

    lag > 0 and a positive value means A LEADS B (A's move today predicts B's
    move `lag` seconds later).
    """
    out = []
    n = len(ra)
    a = ra - ra.mean()
    b = rb - rb.mean()
    sa, sb = a.std(), b.std()
    if sa == 0 or sb == 0:
        return [(l, 0.0) for l in range(-max_lag, max_lag + 1)]
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            x, y = a[:-lag], b[lag:]
        elif lag < 0:
            x, y = a[-lag:], b[:lag]
        else:
            x, y = a, b
        out.append((lag, float((x * y).mean() / (sa * sb))))
    return out


def report_pair(name, ra, rb, max_lag, se):
    xs = xcorr(ra, rb, max_lag)
    lag0 = dict(xs)[0]
    pos = [(l, c) for l, c in xs if l > 0]
    neg = [(l, c) for l, c in xs if l < 0]
    bl, bc = max(pos, key=lambda t: abs(t[1]))
    bl2, bc2 = max(neg, key=lambda t: abs(t[1]))
    sig = "YES" if abs(bc) > 3 * se else "no"
    print(f"  {name:<18} lag0={lag0:+.4f}  "
          f"best_lead(+)={bl:>+3}s {bc:+.4f}  "
          f"best_lag(-)={bl2:>+3}s {bc2:+.4f}  "
          f"3SE={3*se:.4f}  leads={sig}")
    return {"pair": name, "lag0": lag0, "best_lead_s": bl, "best_lead_c": bc,
            "best_neg_s": bl2, "best_neg_c": bc2, "se": se,
            "curve": xs[:0] or [(l, c) for l, c in xs if abs(l) <= 10]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-lag", type=int, default=30)
    ap.add_argument("--symbols", nargs="*",
                    default=["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
                             "DOGEUSDT"])
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    series = {}
    for s in args.symbols:
        r = load(s)
        if r is None or len(r[0]) < 100000:
            print(f"  {s}: missing or too short, skipping")
            continue
        series[s] = r
    if len(series) < 2:
        print("need at least 2 symbols")
        return

    print("=" * 104)
    print("C1 — STALENESS CENSUS (the bias that manufactures fake lead-lag)")
    print("=" * 104)
    for s, (ms, px, vol) in series.items():
        zero_vol = float((vol == 0).mean())
        zero_ret = float((np.diff(px) == 0).mean())
        print(f"  {s:<10} bars={len(ms):>9}  zero-volume={zero_vol*100:6.2f}%  "
              f"zero-return={zero_ret*100:6.2f}%")

    common, al = align(series)
    print(f"\n  aligned on {len(common)} common 1-second bars "
          f"({len(common)/86400:.1f} days)")

    rets, vols = {}, {}
    for s, (px, vol) in al.items():
        rets[s] = np.diff(np.log(px))
        vols[s] = vol[1:]
    n = len(next(iter(rets.values())))
    se = 1.0 / np.sqrt(n)

    print("\n" + "=" * 104)
    print("C3 — SYNTHETIC CONTROL: two INDEPENDENT random walks (expect ~0 "
          "at every lag)")
    print("=" * 104)
    rng = np.random.default_rng(5)
    fa = rng.normal(0, 1, n)
    fb = rng.normal(0, 1, n)
    report_pair("SYNTH indep", fa, fb, args.max_lag, se)

    print("\n" + "=" * 104)
    print("C4 — STALE-PRICE CONTROL: real BTC vs a deliberately STALED copy")
    print("=" * 104)
    print("  (if the pipeline cannot see this fake lead, it cannot control "
          "for it)")
    base = rets[args.symbols[0]] if args.symbols[0] in rets \
        else next(iter(rets.values()))
    px0 = al[args.symbols[0]][0] if args.symbols[0] in al \
        else next(iter(al.values()))[0]
    for hold in (2, 5):
        stale_px = px0.copy()
        for i in range(1, len(stale_px)):
            if i % hold != 0:
                stale_px[i] = stale_px[i - 1]
        sr = np.diff(np.log(stale_px))
        report_pair(f"BTC vs stale/{hold}", base, sr, args.max_lag, se)

    print("\n" + "=" * 104)
    print("REAL PAIRS — ALL BARS (contaminated by staleness)")
    print("=" * 104)
    print("  lag>0 positive => first asset LEADS second")
    res_all = []
    syms = list(rets)
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            res_all.append(report_pair(f"{a[:3]} -> {b[:3]}", rets[a],
                                       rets[b], args.max_lag, se))

    print("\n" + "=" * 104)
    print("C2 — REAL PAIRS, ONLY BARS WHERE **BOTH** ASSETS TRADED")
    print("=" * 104)
    print("  this removes the stale-price bias; a lead that vanishes here "
          "was never real")
    res_both = []
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            m = (vols[a] > 0) & (vols[b] > 0)
            if m.sum() < 50000:
                print(f"  {a[:3]} -> {b[:3]}: only {m.sum()} joint-trade bars, "
                      f"skipping")
                continue
            se2 = 1.0 / np.sqrt(int(m.sum()))
            r = report_pair(f"{a[:3]} -> {b[:3]} [{m.sum()}]", rets[a][m],
                            rets[b][m], args.max_lag, se2)
            res_both.append(r)

    print("\n" + "=" * 104)
    print("C5 — TWO DISJOINT PERIODS (BTC -> each, joint-trade bars only)")
    print("=" * 104)
    half = n // 2
    a = syms[0]
    for b in syms[1:]:
        m = (vols[a] > 0) & (vols[b] > 0)
        for nm, sl in (("first", slice(0, half)), ("second", slice(half, n))):
            mm = m[sl]
            if mm.sum() < 20000:
                continue
            se3 = 1.0 / np.sqrt(int(mm.sum()))
            report_pair(f"{a[:3]}->{b[:3]} {nm}", rets[a][sl][mm],
                        rets[b][sl][mm], 10, se3)

    json.dump({"all_bars": res_all, "joint_bars": res_both,
               "n_bars": int(n)},
              open(os.path.join(OUT, "leadlag.json"), "w"),
              indent=2, default=str)
    print(f"\nwrote {os.path.join(OUT, 'leadlag.json')}")


if __name__ == "__main__":
    main()
