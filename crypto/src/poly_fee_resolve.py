"""TASK 1: resolve the Polymarket fee discrepancy EMPIRICALLY.

The CLOB API reports `taker_base_fee: 1000` on live crypto markets. The published
schedule implies `fee = 0.07 * p * (1-p)` per share. Those are incompatible, not
a rounding difference, and every number in venue_comparison.md rests on it.

Resolve from on-chain `orderFilledEvent.fee`, which is populated on ~96% of
fills. Strategy:

  1. Decode each fill into (price, size, fee) in human units. One leg of every
     fill is USDC (assetId "0"); the other is the outcome token. Both have 6
     decimals on Polygon.
  2. For each CANDIDATE fee shape f(p), compute the implied rate r = fee/(size*f(p)).
     If the shape is correct, r collapses onto a few DISCRETE values (the
     per-category rates 0.04 / 0.05 / 0.07). If the shape is wrong, r smears.
     This identifies the shape without needing to know each market's category.
  3. Bucket by date to detect schedule changes (the crypto rate reportedly moved
     0.072 -> 0.07 in July 2026, and sports 0.03 -> 0.05).

SAMPLE HYGIENE (failure mode #1 — badly-drawn samples, 4 prior instances):
the date range, composition and selection rule of every sample is printed
BEFORE any conclusion is drawn. The subgraph indexes 2022-11-21 -> 2026-04-28,
so a naive "first 1000" would be a 2022 sample and a naive "last 1000" a single
2026-04-28 minute. Both are drawn deliberately and reported.

Read-only. No wallet, no orders.
"""
import json
import os
import time
from collections import Counter, defaultdict
from decimal import Decimal

import numpy as np
import requests

UA = {"User-Agent": "research-readonly/0.1"}
GOLDSKY = ("https://api.goldsky.com/api/public/"
           "project_cl6mb8i9h0003e201j6li0diw/subgraphs/"
           "orderbook-subgraph/prod/gn")
OUT = r"C:\Users\gianf\crypto\reports"

USDC_DEC = Decimal(10) ** 6
TOKEN_DEC = Decimal(10) ** 6

FIELDS = ("id timestamp maker taker makerAssetId takerAssetId "
          "makerAmountFilled takerAmountFilled fee")


def gql(query):
    for attempt in range(5):
        try:
            r = requests.post(GOLDSKY, json={"query": query}, headers=UA,
                              timeout=60)
        except Exception:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        try:
            j = r.json()
        except Exception:
            time.sleep(1.5)
            continue
        if "errors" in j:
            return None
        return j.get("data")
    return None


def fetch_window(ts_gt, ts_lt, n=1000):
    q = ('{ orderFilledEvents(first:%d, orderBy:timestamp, orderDirection:asc, '
         'where:{timestamp_gt:"%d", timestamp_lt:"%d"}) { %s } }'
         % (n, ts_gt, ts_lt, FIELDS))
    d = gql(q)
    return (d or {}).get("orderFilledEvents", []) or []


def decode(ev):
    """-> dict(price, size, fee_tokens, side) in human units, or None.

    Convention: assetId "0" is the collateral (USDC). The other leg is the
    outcome token. `maker` is the resting order's owner.
      - makerAssetId == 0  -> maker paid USDC, received tokens (maker BUYS)
      - takerAssetId == 0  -> maker gave tokens, received USDC (maker SELLS)
    """
    mid, tid = ev["makerAssetId"], ev["takerAssetId"]
    ma = Decimal(ev["makerAmountFilled"])
    ta = Decimal(ev["takerAmountFilled"])
    fee = Decimal(ev["fee"])
    if mid == "0" and tid != "0":
        usdc, tokens, side = ma, ta, "maker_buy"
    elif tid == "0" and mid != "0":
        usdc, tokens, side = ta, ma, "maker_sell"
    else:
        return None
    if tokens <= 0 or usdc <= 0:
        return None
    price = (usdc / USDC_DEC) / (tokens / TOKEN_DEC)
    if not (Decimal("0.001") < price < Decimal("0.999")):
        return None
    return {"ts": int(ev["timestamp"]), "side": side,
            "price": float(price),
            "size": float(tokens / TOKEN_DEC),
            "fee": float(fee / TOKEN_DEC),
            "maker": ev["maker"], "taker": ev["taker"]}


# ---------------------------------------------------------- candidate shapes
def shape_quadratic(p):
    """0.07 * p * (1-p)  -- the published/Kalshi-identical form."""
    return p * (1 - p)


def shape_min(p):
    """baseRate * min(p, 1-p) -- the CTF exchange contract form."""
    return min(p, 1 - p)


def shape_flat(p):
    return 1.0


SHAPES = [("quadratic  p*(1-p)", shape_quadratic),
          ("min(p,1-p)        ", shape_min),
          ("flat              ", shape_flat)]


def analyse(rows, label):
    print(f"\n{'='*100}")
    print(f"SAMPLE: {label}")
    print(f"{'='*100}")
    if not rows:
        print("  empty")
        return None
    ts = [r["ts"] for r in rows]
    print(f"  n = {len(rows)}")
    print(f"  date range: "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(min(ts)))} -> "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(max(ts)))}")
    print(f"  sides: {dict(Counter(r['side'] for r in rows))}")
    ps = np.array([r["price"] for r in rows])
    print(f"  price:  min={ps.min():.4f} p25={np.percentile(ps,25):.4f} "
          f"med={np.median(ps):.4f} p75={np.percentile(ps,75):.4f} "
          f"max={ps.max():.4f}")
    szs = np.array([r["size"] for r in rows])
    print(f"  size:   med={np.median(szs):.2f} max={szs.max():.2f}")
    nz = [r for r in rows if r["fee"] > 0]
    print(f"  fills with non-zero fee: {len(nz)}/{len(rows)} "
          f"({100*len(nz)/len(rows):.1f}%)")
    if not nz:
        print("  -> no fee-bearing fills in this sample")
        return None

    # fee per share
    print(f"\n  {'shape':<22} {'implied rate r = fee/(size*f(p))':<46} "
          f"{'discreteness'}")
    best = None
    for name, f in SHAPES:
        rs = []
        for r in nz:
            den = r["size"] * f(r["price"])
            if den > 1e-12:
                rs.append(r["fee"] / den)
        if not rs:
            continue
        rs = np.array(rs)
        rs = rs[(rs > 0) & (rs < 5)]
        if len(rs) < 10:
            continue
        # discreteness: fraction of mass within 1% of the modal value
        mode = np.median(rs)
        conc = float(np.mean(np.abs(rs / mode - 1) < 0.01))
        cv = float(np.std(rs) / np.mean(rs))
        print(f"  {name:<22} med={np.median(rs):8.5f} "
              f"p10={np.percentile(rs,10):8.5f} "
              f"p90={np.percentile(rs,90):8.5f}  CV={cv:6.3f}  "
              f"within1%ofmode={conc*100:5.1f}%")
        if best is None or conc > best[1]:
            best = (name, conc, float(np.median(rs)), cv)

    if best:
        print(f"\n  -> most DISCRETE shape: {best[0].strip()} "
              f"(median rate {best[2]:.5f}, {best[1]*100:.1f}% within 1% of mode)")

    # is the fee charged to the maker leg, the taker leg, or both?
    mk = [r for r in nz if r["side"] == "maker_buy"]
    ms = [r for r in nz if r["side"] == "maker_sell"]
    print(f"\n  fee-bearing by side: maker_buy={len(mk)} maker_sell={len(ms)}")
    return {"n": len(rows), "n_fee": len(nz),
            "date_min": min(ts), "date_max": max(ts),
            "best_shape": best[0].strip() if best else None,
            "median_rate": best[2] if best else None}


def main():
    os.makedirs(OUT, exist_ok=True)
    # subgraph coverage established in Phase 0
    T0, T1 = 1669060209, 1777374040          # 2022-11-21 .. 2026-04-28
    results = {}

    # Deliberate stratified sample across the whole indexed period, so no
    # conclusion rests on a single day (failure mode #1).
    marks = [("2023-06", 1685577600), ("2024-06", 1717200000),
             ("2025-06", 1748736000), ("2026-01", 1767225600),
             ("2026-03", 1772409600), ("2026-04-late", 1777200000)]
    allrows = []
    for label, ts in marks:
        if not (T0 < ts < T1):
            continue
        raw = fetch_window(ts, ts + 6 * 3600, n=1000)
        rows = [d for d in (decode(e) for e in raw) if d]
        results[label] = analyse(rows, f"{label} (6h window from {ts})")
        allrows.extend(rows)
        time.sleep(0.3)

    results["pooled"] = analyse(allrows, "POOLED across all windows")

    # --------------------------------------------------- the decisive fit
    print(f"\n{'='*100}")
    print("DECISIVE TEST — fee/share vs price, against both candidate curves")
    print(f"{'='*100}")
    nz = [r for r in allrows if r["fee"] > 0]
    if nz:
        bins = np.linspace(0.02, 0.98, 25)
        print(f"  {'price bin':>12} {'n':>6} {'obs fee/share':>15} "
              f"{'0.07*p*(1-p)':>14} {'0.10*min(p,1-p)':>17} {'ratio_quad':>11}")
        for lo, hi in zip(bins, bins[1:]):
            sel = [r for r in nz if lo <= r["price"] < hi]
            if len(sel) < 5:
                continue
            obs = np.median([r["fee"] / r["size"] for r in sel])
            pm = (lo + hi) / 2
            q = 0.07 * pm * (1 - pm)
            mn = 0.10 * min(pm, 1 - pm)
            print(f"  {lo:.2f}-{hi:.2f}   {len(sel):>6} {obs:>15.6f} "
                  f"{q:>14.6f} {mn:>17.6f} {obs/q if q else 0:>11.3f}")

    with open(os.path.join(OUT, "poly_fee_resolution.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
