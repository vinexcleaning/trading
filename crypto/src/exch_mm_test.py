"""TASK 2: is -2.16c adverse selection a property of MARKET MAKING or of CRYPTO?

Runs the identical fill model + P&L decomposition on non-crypto series spanning
the counterparty spectrum, and plots adverse selection against how algorithmic
the counterparty looks.

Discipline carried forward, asserted in code:
  - decompose PER MARKET, residual inventory marked at that market's ACTUAL
    settlement, never pooled, never defaulted to 0.5 (that bug fabricated
    +2.96c/contract earlier today)
  - per-opportunity accounting; fill rate reported alongside per-fill economics
  - CI bootstrapped over MARKETS (the unit), stated explicitly
  - fee_type read per series from the API; the 130 maker-fee series flagged
"""
import datetime as dt
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(__file__))
from mm_fill_model import simulate, decompose, fetch_market  # noqa: E402
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\mm"

# spanning the counterparty spectrum measured in exch_census.json.
# algo_score: lower = more retail-like.
TARGETS = [
    ("KXBTCD",     "Crypto",     0.380),
    ("KXNPBGAME",  "Sports",     0.431),
    ("KXATPSETWINNER", "Sports", 0.389),
    ("KXHIGHLAX",  "Weather",    0.418),
    ("KXRAIN",     "Weather",    0.409),
    ("KXPRESNOMD", "Elections",  0.245),
    ("KXUFCFIGHT", "Sports",     0.505),
]


def get(path, **params):
    for a in range(6):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(0.7 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.4 * (a + 1))
            continue
        if r.status_code >= 500:
            time.sleep(0.7 * (a + 1))
            continue
        return r
    return None


def settled_markets(series, limit=400):
    j = get("/markets", series_ticker=series, status="settled", limit=limit)
    if j is None or j.status_code != 200:
        return []
    return j.json().get("markets", []) or []


def fee_type_of(series):
    j = get("/series/" + series)
    if j is not None and j.status_code == 200:
        s = j.json().get("series", {})
        return s.get("fee_type"), s.get("fee_multiplier")
    return "?", "?"


def run_series(series, n_markets=14, minutes=60):
    ft, fm = fee_type_of(series)
    mkts = settled_markets(series)
    if not mkts:
        return {"series": series, "kill": "no settled markets", "fee_type": ft}
    # keep only markets that traded, sort by volume, take a spread of them
    scored = []
    for m in mkts:
        try:
            v = float(m.get("volume_fp") or 0)
        except (TypeError, ValueError):
            v = 0.0
        if v > 0 and m.get("close_time") and m.get("result") in ("yes", "no"):
            scored.append((v, m))
    if len(scored) < 3:
        return {"series": series, "kill": f"only {len(scored)} traded settled "
                                          f"markets", "fee_type": ft}
    scored.sort(key=lambda x: -x[0])
    # stride through the volume-ranked list so we are not only taking the
    # single most active market
    stride = max(1, len(scored) // n_markets)
    pick = [m for _, m in scored[::stride][:n_markets]]

    per_market, opps_all = [], []
    got = 0
    for m in pick:
        close_ts = int(dt.datetime.fromisoformat(
            m["close_time"].replace("Z", "+00:00")).timestamp())
        start_ts = close_ts - minutes * 60
        q, tr = fetch_market(series, m["ticker"], start_ts, close_ts)
        if not q or not tr:
            continue
        got += 1
        settle_y = 1.0 if str(m.get("result")) == "yes" else 0.0
        o, f = simulate(q, tr, settle_y, close_ts, latency_s=0.373,
                        queue_ahead=0.0, half_spread=0.005)
        opps_all.extend(o)
        d = decompose(f, terminal_mark=settle_y)   # ACTUAL settlement
        if d:
            per_market.append(d)
        time.sleep(0.02)

    if not per_market:
        return {"series": series, "kill": f"no fills ({got} markets fetched)",
                "fee_type": ft}
    w = np.array([x["contracts"] for x in per_market])
    agg = {k: float(np.average([x[k] for x in per_market], weights=w))
           for k in ("spread_per_contract", "adverse_per_contract",
                     "inventory_per_contract", "net_per_contract")}
    nb = np.array([x["net_per_contract"] for x in per_market])
    rng = np.random.default_rng(5)
    bs = np.array([nb[rng.integers(0, len(nb), len(nb))].mean()
                   for _ in range(2000)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    nf = sum(1 for o in opps_all if o["filled_bid"] > 0 or o["filled_ask"] > 0)
    return {"series": series, "fee_type": ft, "fee_multiplier": fm,
            "n_markets": len(per_market), "contracts": float(w.sum()),
            "opportunities": len(opps_all),
            "fill_rate": nf / max(1, len(opps_all)),
            "ci_lo": float(lo), "ci_hi": float(hi),
            "inv_max": float(np.max([abs(x["residual_inventory"])
                                     for x in per_market])),
            "inv_mean": float(np.mean([abs(x["residual_inventory"])
                                       for x in per_market])), **agg}


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=" * 112)
    print("TASK 2 — adverse selection vs counterparty, ACROSS CATEGORIES")
    print("=" * 112)
    print("  latency 373ms, half-spread 0.5c, queue_ahead 0, inventory cap 50")
    print("  unit of observation = MARKET; CI bootstraps markets\n")
    hdr = (f"  {'series':<18} {'cat':<10} {'algo':>5} {'mkts':>5} {'fill%':>7} "
           f"{'contracts':>10} {'spread':>8} {'ADVERSE':>9} {'NET':>9} "
           f"{'95% CI':>18} {'fee_type':<26}")
    print(hdr)
    rows = []
    for s, cat, algo in TARGETS:
        r = run_series(s)
        r["category"] = cat
        r["algo_score"] = algo
        rows.append(r)
        if r.get("kill"):
            print(f"  {s:<18} {cat:<10} {algo:>5.3f}  KILLED: {r['kill']}")
        else:
            ci = f"[{r['ci_lo']:+.2f},{r['ci_hi']:+.2f}]"
            print(f"  {s:<18} {cat:<10} {algo:>5.3f} {r['n_markets']:>5} "
                  f"{r['fill_rate']*100:>6.2f}% {r['contracts']:>10.0f} "
                  f"{r['spread_per_contract']:>+8.3f} "
                  f"{r['adverse_per_contract']:>+9.3f} "
                  f"{r['net_per_contract']:>+9.3f} {ci:>18} "
                  f"{str(r['fee_type']):<26}")
        sys.stdout.flush()

    ok = [r for r in rows if not r.get("kill")]
    if len(ok) >= 3:
        a = np.array([r["algo_score"] for r in ok])
        adv = np.array([r["adverse_per_contract"] for r in ok])
        net = np.array([r["net_per_contract"] for r in ok])
        print(f"\n  HEADLINE RELATIONSHIP (n={len(ok)} series):")
        print(f"    corr(algo_score, adverse selection) = "
              f"{np.corrcoef(a, adv)[0,1]:+.3f}")
        print(f"    corr(algo_score, net)               = "
              f"{np.corrcoef(a, net)[0,1]:+.3f}")
        print(f"    adverse range: {adv.min():+.3f} .. {adv.max():+.3f} c")
        print(f"    net range:     {net.min():+.3f} .. {net.max():+.3f} c")
        nprof = sum(1 for r in ok if r["ci_lo"] > 0)
        print(f"    series with CI strictly > 0: {nprof} / {len(ok)}")

    json.dump(rows, open(os.path.join(OUT, "exch_mm_test.json"), "w"),
              indent=2, default=str)
    print(f"\nwrote {os.path.join(OUT, 'exch_mm_test.json')}")


if __name__ == "__main__":
    main()
