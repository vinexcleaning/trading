"""Hypothesis C8: does BTC pin near large round numbers more than chance?

Uses `expiration_value` from the settled Kalshi hourly ladders — the realised
CF Benchmarks BRTI 60-second average at each hourly boundary. That is a clean,
free, high-quality spot series sampled at exactly the settlement timestamps,
with no candle reconstruction required.

Unit of observation: the EVENT (one hourly settlement). One settlement value per
event, deduplicated across the ladder's strikes -- a 188-strike ladder is ONE
observation of the settlement, not 188. See PREREGISTRATION.md section 1.

Null: the last digits of the settlement are uniform, i.e. no round-number
attraction. Tested with a chi-square on the distance-to-nearest-round-number
distribution, plus a direct comparison of observed vs expected mass in a window
around round levels.
"""
import glob
import json
import os
from collections import Counter, defaultdict

import numpy as np
from scipy import stats

ROOT = r"C:\Users\gianf\crypto\data\kalshi_settled"


def load_settlements(series):
    """One (event, close_time, settlement) per event."""
    path = os.path.join(ROOT, f"{series}.jsonl")
    if not os.path.exists(path):
        return []
    by_ev = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev = m.get("event_ticker")
            v = m.get("expiration_value")
            if not ev or v in (None, ""):
                continue
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            if x <= 0:
                continue
            prev = by_ev.get(ev)
            if prev is None:
                by_ev[ev] = (m.get("close_time"), x)
            elif prev[1] != x:
                # two different settlement values for one event => data problem
                by_ev[ev] = (prev[0], None)
    return [(ev, c, v) for ev, (c, v) in by_ev.items() if v is not None]


def test_round(vals, level, label):
    """Are settlements attracted to multiples of `level`?"""
    v = np.asarray(vals, dtype=float)
    # signed distance to nearest multiple, scaled to [-0.5, 0.5]
    frac = (v / level) - np.round(v / level)
    n = len(v)

    # 1. chi-square on 10 uniform bins of the fractional position
    bins = np.linspace(-0.5, 0.5, 11)
    obs, _ = np.histogram(frac, bins=bins)
    exp = np.full(10, n / 10.0)
    chi2, p_chi = stats.chisquare(obs, exp)

    # 2. direct: mass within +/-10% of a round level vs the 20% expected
    near = float(np.mean(np.abs(frac) < 0.10))
    # binomial test against the exact null 0.20
    p_bin = stats.binomtest(int(round(near * n)), n, 0.20).pvalue

    # 3. Rayleigh test for circular concentration (the right test here:
    #    fractional position is a circular variable)
    ang = 2 * np.pi * frac
    R = np.hypot(np.mean(np.cos(ang)), np.mean(np.sin(ang)))
    z = n * R * R
    p_ray = np.exp(-z) * (1 + (2 * z - z * z) / (4 * n))

    print(f"  {label:<22} n={n:<6} "
          f"near±10%={near*100:5.2f}% (exp 20.00%)  "
          f"chi2={chi2:7.2f} p={p_chi:.4f}  "
          f"Rayleigh R={R:.4f} p={p_ray:.4f}")
    return {"level": level, "n": n, "near_frac": near, "chi2": float(chi2),
            "p_chi": float(p_chi), "rayleigh_R": float(R),
            "p_rayleigh": float(p_ray),
            "hist": [int(x) for x in obs]}


def main():
    out = {}
    for series, asset in [("KXBTC", "BTC"), ("KXBTCD", "BTC"),
                          ("KXETH", "ETH"), ("KXETHD", "ETH")]:
        rows = load_settlements(series)
        if len(rows) < 100:
            print(f"{series}: only {len(rows)} events, skipping")
            continue
        vals = [r[2] for r in rows]
        print(f"\n{series} ({asset}) — {len(rows)} EVENTS "
              f"(unit = one hourly settlement)")
        print(f"  settlement range {min(vals):.2f} .. {max(vals):.2f}")
        res = []
        levels = ([100, 250, 500, 1000, 5000] if asset == "BTC"
                  else [5, 10, 25, 50, 100])
        for lv in levels:
            res.append(test_round(vals, lv, f"multiples of {lv}"))
        out[series] = {"n_events": len(rows), "tests": res}

    # Benjamini-Hochberg across every test run here, as pre-registered
    ps = []
    for s, d in out.items():
        for t in d["tests"]:
            ps.append((s, t["level"], t["p_rayleigh"]))
    if ps:
        ps.sort(key=lambda x: x[2])
        m = len(ps)
        print(f"\nBenjamini-Hochberg over {m} pinning tests (alpha=0.05):")
        crit = None
        for i, (s, lv, p) in enumerate(ps, 1):
            thr = 0.05 * i / m
            flag = "SURVIVES" if p <= thr else ""
            if p <= thr:
                crit = i
            print(f"  {i:>2}. {s:<8} level={lv:<6} p={p:.5f} "
                  f"thr={thr:.5f} {flag}")
        print(f"\n  {crit or 0} of {m} tests survive BH-FDR")
        out["bh"] = {"n_tests": m, "n_surviving": crit or 0}

    with open(r"C:\Users\gianf\crypto\reports\pinning_test.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
