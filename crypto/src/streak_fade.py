"""The streak result, framed as the TRADE: buy the DOWN side after a run of ups.

The handoff reported up-rates. The tradeable version is the fade, so every
number here is the DOWN rate, tested against the REAL BAR (51.75%) rather than
a coinflip. Testing against 50% answers "is there an effect"; testing against
51.75% answers "is there a trade". Only the second one matters.

BAR: KXBTC15M is struck at the previous window's settlement, so it opens near
50c. Hold-to-settlement pays ONE taker fee: 0.07*0.5*0.5 = 1.75c. Break-even
win rate = 51.75%.

Splits: two disjoint periods, hour-of-day, and volatility regime, for EVERY
conditional state -- all listed as not-yet-run in the previous handoff.

LOOK-AHEAD: streak state at window i uses only windows < i, all of which had
already settled when window i opened.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

S15 = r"C:\Users\gianf\crypto\data\kalshi_settled\KXBTC15M.jsonl"
OUT = r"C:\Users\gianf\crypto\reports"

BAR = 0.5175          # break-even down-rate at a 50c entry, one fee


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def load():
    ev = {}
    with open(S15, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            e, ct, res = (m.get("event_ticker"), m.get("close_time"),
                          str(m.get("result")))
            v = m.get("expiration_value")
            if not e or not ct or res not in ("yes", "no"):
                continue
            try:
                sv = float(v) if v not in (None, "") else None
            except ValueError:
                sv = None
            ev[e] = (ct, 1 if res == "yes" else 0, sv)
    rows = sorted(ev.values())
    return rows


def conditions(ups):
    """-> {label: index array}. Index i means 'decide window i'."""
    out = {}
    n = len(ups)
    for N in (3, 5, 10, 20):
        for k in range(N + 1):
            idx = np.array([i for i in range(N, n) if ups[i - N:i].sum() == k])
            if len(idx) >= 100:
                out[f"{k}/{N} ups"] = idx
    for k in range(2, 9):
        for d, lab in ((1, "ups"), (0, "downs")):
            idx = np.array([i for i in range(k, n)
                            if all(ups[i - j - 1] == d for j in range(k))])
            if len(idx) >= 100:
                out[f"{k} consec {lab}"] = idx
    return out


def fade_row(ups, idx):
    """DOWN rate on the next window, tested against the 51.75% bar."""
    nxt = ups[idx]
    n = len(nxt)
    downs = int((nxt == 0).sum())
    rate = downs / n
    p_bar = stats.binomtest(downs, n, BAR, alternative="greater").pvalue
    lo, hi = wilson(downs, n)
    se = np.sqrt(BAR * (1 - BAR) / n)
    z = (rate - BAR) / se if se > 0 else 0.0
    edge_pp = (rate - BAR) * 100
    return {"n": n, "down_rate": rate, "ci_lo": lo, "ci_hi": hi,
            "p_vs_bar": p_bar, "z_vs_bar": z, "edge_pp": edge_pp}


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = load()
    ups = np.array([r[1] for r in rows])
    times = [r[0] for r in rows]
    sv = [r[2] for r in rows]
    n = len(ups)
    print("=" * 108)
    print("THE FADE — buy the DOWN side. Tested against the REAL bar "
          f"({BAR*100:.2f}%), not a coinflip.")
    print("=" * 108)
    print(f"  n = {n} settled KXBTC15M windows, "
          f"{times[0][:16]} -> {times[-1][:16]}")
    print(f"  unconditional DOWN rate = {(1-ups.mean())*100:.2f}%")
    print(f"  BAR = {BAR*100:.2f}% (50c entry, hold-to-settlement, one 1.75c "
          f"fee)")
    print(f"\n  NOTE: the bar assumes entry at exactly 50c. The real entry is "
          f"the NO ASK,\n  which is not in settled records and is now being "
          f"recorded live.\n")

    conds = conditions(ups)
    print(f"  {'condition':<20} {'n':>6} {'DOWN%':>7} {'95% CI':>16} "
          f"{'edge vs bar':>12} {'z':>7} {'p(>bar)':>9} {'verdict':>10}")
    res = {}
    for lab, idx in conds.items():
        r = fade_row(ups, idx)
        res[lab] = r
        vd = ("CLEARS" if r["ci_lo"] > BAR else
              ("above" if r["down_rate"] > BAR else "below"))
        print(f"  {lab:<20} {r['n']:>6} {r['down_rate']*100:>6.2f}% "
              f"[{r['ci_lo']*100:>5.2f},{r['ci_hi']*100:>5.2f}] "
              f"{r['edge_pp']:>+11.2f}pp {r['z_vs_bar']:>+7.2f} "
              f"{r['p_vs_bar']:>9.4f} {vd:>10}")

    # ---- BH-FDR across all fade tests ----
    labs = sorted(res, key=lambda k: res[k]["p_vs_bar"])
    m = len(labs)
    print(f"\n  Benjamini-Hochberg across all {m} fade tests (alpha=0.05):")
    surv = 0
    for i, lab in enumerate(labs[:8], 1):
        thr = 0.05 * i / m
        ok = res[lab]["p_vs_bar"] <= thr
        if ok:
            surv = i
        print(f"    {i:>2}. {lab:<20} p={res[lab]['p_vs_bar']:.4f} "
              f"thr={thr:.4f} {'SURVIVES' if ok else ''}")
    print(f"    -> {surv} of {m} survive")

    # ---- two disjoint periods ----
    half = n // 2
    print(f"\n  TWO DISJOINT PERIODS (first {half} vs last {n-half} windows)")
    print(f"  {'condition':<20} {'n1':>5} {'DOWN%1':>8} {'n2':>5} "
          f"{'DOWN%2':>8} {'gap pp':>8} {'both>bar?':>10}")
    for lab, idx in conds.items():
        i1 = idx[idx < half]
        i2 = idx[idx >= half]
        if len(i1) < 40 or len(i2) < 40:
            continue
        r1, r2 = fade_row(ups, i1), fade_row(ups, i2)
        both = "YES" if (r1["down_rate"] > BAR and r2["down_rate"] > BAR) \
            else "no"
        print(f"  {lab:<20} {r1['n']:>5} {r1['down_rate']*100:>7.2f}% "
              f"{r2['n']:>5} {r2['down_rate']*100:>7.2f}% "
              f"{(r1['down_rate']-r2['down_rate'])*100:>+7.2f} {both:>10}")

    # ---- hour-of-day, for the headline conditions ----
    hours = np.array([int(t[11:13]) for t in times])
    print(f"\n  HOUR-OF-DAY (UTC) for the strongest conditions")
    for lab in ["2 consec ups", "2/3 ups", "10/20 ups"]:
        if lab not in conds:
            continue
        idx = conds[lab]
        print(f"    {lab}:")
        buckets = [(0, 6), (6, 12), (12, 18), (18, 24)]
        for lo, hi in buckets:
            sel = idx[(hours[idx] >= lo) & (hours[idx] < hi)]
            if len(sel) < 40:
                continue
            r = fade_row(ups, sel)
            print(f"      {lo:02d}-{hi:02d}h n={r['n']:>5} "
                  f"DOWN={r['down_rate']*100:>6.2f}% "
                  f"edge={r['edge_pp']:>+6.2f}pp "
                  f"{'>bar' if r['down_rate'] > BAR else ''}")

    # ---- volatility regime, from |prev return| of the settlement series ----
    volr = np.full(n, np.nan)
    for i in range(2, n):
        a, b = sv[i - 2], sv[i - 1]
        if a and b and a > 0:
            volr[i] = abs(np.log(b / a))
    ok = ~np.isnan(volr)
    if ok.sum() > 500:
        terc = np.nanpercentile(volr[ok], [33.3, 66.7])
        print(f"\n  VOLATILITY REGIME (|prev 15m log return| terciles: "
              f"<{terc[0]*100:.3f}% / {terc[1]*100:.3f}%+)")
        for lab in ["2 consec ups", "2/3 ups", "10/20 ups"]:
            if lab not in conds:
                continue
            idx = conds[lab]
            print(f"    {lab}:")
            for nm, sel in (
                    ("low ", idx[(volr[idx] <= terc[0]) & ~np.isnan(volr[idx])]),
                    ("mid ", idx[(volr[idx] > terc[0]) & (volr[idx] <= terc[1])]),
                    ("high", idx[volr[idx] > terc[1]])):
                if len(sel) < 40:
                    continue
                r = fade_row(ups, sel)
                print(f"      {nm} n={r['n']:>5} "
                      f"DOWN={r['down_rate']*100:>6.2f}% "
                      f"edge={r['edge_pp']:>+6.2f}pp "
                      f"{'>bar' if r['down_rate'] > BAR else ''}")

    json.dump({k: {kk: float(vv) for kk, vv in v.items()}
               for k, v in res.items()},
              open(os.path.join(OUT, "streak_fade.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
