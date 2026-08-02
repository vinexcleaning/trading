"""TASK 1: exchange-wide census + counterparty fingerprint.

The question this session exists to answer: is -2.16c of adverse selection a
property of MARKET MAKING or a property of CRYPTO?

Cheapest high-information move: page the GLOBAL trade tape (`/markets/trades`
with no ticker filter). One call returns 1,000 real trades from anywhere on the
exchange, each carrying ticker, size, timestamp and aggressor side. From that
we get, per series and per category:

  - share of exchange-wide flow
  - trade size distribution (round vs odd lots)
  - inter-trade timing regularity
  - hour-of-day profile

COUNTERPARTY FINGERPRINT — the variable the session tests against:
  retail-like  = bursty timing, ROUND sizes (1,5,10,25,100), waking-hours skew
  algo-like    = flat 24h profile, regular timing, odd/fractional sizes
We score each series 0..1 where 1 = most algorithmic, and rank.

fee_type is read per series from /series so the 130 maker-fee series are
flagged, never assumed.
"""
import datetime as dt
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\mm"


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


def series_of(ticker):
    return str(ticker).split("-")[0]


def load_series_meta():
    """ticker -> (category, fee_type, frequency, title)."""
    meta, cursor = {}, None
    for _ in range(30):
        p = {"limit": 1000}
        if cursor:
            p["cursor"] = cursor
        r = get("/series", **p)
        if r is None or r.status_code != 200:
            break
        j = r.json()
        for s in j.get("series", []) or []:
            meta[s.get("ticker")] = {
                "category": s.get("category"),
                "fee_type": s.get("fee_type"),
                "fee_multiplier": s.get("fee_multiplier"),
                "frequency": s.get("frequency"),
                "title": str(s.get("title"))[:60],
            }
        cursor = j.get("cursor")
        if not cursor:
            break
    return meta


def page_global_trades(n_pages=40):
    """Page the exchange-wide tape. Returns list of trades."""
    out, cursor = [], None
    for i in range(n_pages):
        p = {"limit": 1000}
        if cursor:
            p["cursor"] = cursor
        r = get("/markets/trades", **p)
        if r is None or r.status_code != 200:
            break
        j = r.json()
        tr = j.get("trades", []) or []
        out.extend(tr)
        cursor = j.get("cursor")
        if not cursor or not tr:
            break
        if (i + 1) % 10 == 0:
            print(f"    paged {i+1}, {len(out)} trades", flush=True)
        time.sleep(0.03)
    return out


ROUND_LOTS = {1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000}


def fingerprint(trades):
    """-> dict of counterparty features. Higher algo_score = more algorithmic."""
    if len(trades) < 20:
        return None
    sizes, ts, hours = [], [], Counter()
    for t in trades:
        try:
            sizes.append(float(t["count_fp"]))
            ts.append(dt.datetime.fromisoformat(
                t["created_time"].replace("Z", "+00:00")).timestamp())
        except (KeyError, ValueError, TypeError):
            continue
        hours[t["created_time"][11:13]] += 1
    if len(sizes) < 20:
        return None
    sizes = np.array(sizes)
    ts = np.array(sorted(ts))

    # 1. round-lot fraction: retail trades round numbers
    round_frac = float(np.mean([
        (abs(s - round(s)) < 1e-9) and (int(round(s)) in ROUND_LOTS)
        for s in sizes]))
    # 2. fractional-size fraction: algos produce odd/fractional sizes
    frac_frac = float(np.mean([abs(s - round(s)) > 1e-9 for s in sizes]))
    # 3. hour-of-day flatness: entropy of the hour distribution, normalised.
    #    algos trade flat across 24h; retail follows waking hours
    h = np.array([hours.get(f"{i:02d}", 0) for i in range(24)], dtype=float)
    p = h / h.sum() if h.sum() else np.ones(24) / 24
    ent = float(-(p[p > 0] * np.log(p[p > 0])).sum() / np.log(24))
    # 4. timing regularity: CV of inter-trade gaps. bursty retail -> high CV
    gaps = np.diff(ts)
    gaps = gaps[gaps > 0]
    cv = float(np.std(gaps) / np.mean(gaps)) if len(gaps) > 5 and \
        np.mean(gaps) > 0 else np.nan

    algo = np.nanmean([
        1.0 - round_frac,                       # fewer round lots -> algo
        frac_frac,                              # fractional sizes -> algo
        ent,                                    # flat 24h -> algo
        1.0 / (1.0 + (cv if np.isfinite(cv) else 3.0)),  # regular -> algo
    ])
    return {"n_trades": len(sizes), "size_med": float(np.median(sizes)),
            "size_mean": float(np.mean(sizes)),
            "round_lot_frac": round_frac, "fractional_frac": frac_frac,
            "hour_entropy": ent, "gap_cv": cv,
            "algo_score": float(algo)}


def main():
    os.makedirs(OUT, exist_ok=True)
    print("loading series metadata ...", flush=True)
    meta = load_series_meta()
    print(f"  {len(meta)} series")
    cats = Counter(v["category"] for v in meta.values())
    print(f"  categories: {dict(cats.most_common())}")
    fee_types = Counter(v["fee_type"] for v in meta.values())
    print(f"  fee_types: {dict(fee_types)}")

    print("\npaging the GLOBAL trade tape ...", flush=True)
    trades = page_global_trades(n_pages=40)
    print(f"  {len(trades)} trades pulled")
    if trades:
        tt = sorted(t["created_time"] for t in trades)
        print(f"  window: {tt[0][:19]} -> {tt[-1][:19]}")

    by_series = defaultdict(list)
    for t in trades:
        by_series[series_of(t.get("ticker"))].append(t)
    print(f"  {len(by_series)} distinct series traded in that window")

    rows = []
    for s, tr in by_series.items():
        m = meta.get(s, {})
        fp = fingerprint(tr)
        if fp is None:
            continue
        rows.append({"series": s, "category": m.get("category", "?"),
                     "fee_type": m.get("fee_type", "?"),
                     "frequency": m.get("frequency", "?"),
                     "title": m.get("title", ""),
                     "flow_share": len(tr) / max(1, len(trades)),
                     **fp})
    rows.sort(key=lambda r: -r["n_trades"])

    print(f"\n{len(rows)} series with >=20 trades in the window\n")
    print(f"  {'series':<22} {'category':<14} {'trades':>7} {'sz_med':>8} "
          f"{'round%':>7} {'frac%':>7} {'hrEnt':>6} {'gapCV':>7} "
          f"{'ALGO':>6} {'fee_type':<26}")
    for r in rows[:45]:
        print(f"  {r['series'][:22]:<22} {str(r['category'])[:14]:<14} "
              f"{r['n_trades']:>7} {r['size_med']:>8.1f} "
              f"{r['round_lot_frac']*100:>6.1f}% {r['fractional_frac']*100:>6.1f}% "
              f"{r['hour_entropy']:>6.3f} "
              f"{(r['gap_cv'] if np.isfinite(r['gap_cv']) else -1):>7.2f} "
              f"{r['algo_score']:>6.3f} {str(r['fee_type']):<26}")

    # category-level aggregate
    print("\n  === CATEGORY AGGREGATE (flow-weighted) ===")
    bycat = defaultdict(list)
    for r in rows:
        bycat[r["category"]].append(r)
    print(f"  {'category':<16} {'series':>7} {'trades':>8} {'sz_med':>8} "
          f"{'round%':>7} {'ALGO(mean)':>11}")
    catrows = []
    for c, rs in sorted(bycat.items(), key=lambda kv: -sum(
            x["n_trades"] for x in kv[1])):
        n = sum(x["n_trades"] for x in rs)
        algo = float(np.mean([x["algo_score"] for x in rs]))
        rl = float(np.mean([x["round_lot_frac"] for x in rs]))
        szm = float(np.median([x["size_med"] for x in rs]))
        print(f"  {str(c)[:16]:<16} {len(rs):>7} {n:>8} {szm:>8.1f} "
              f"{rl*100:>6.1f}% {algo:>11.3f}")
        catrows.append({"category": c, "n_series": len(rs), "n_trades": n,
                        "size_med": szm, "round_lot_frac": rl,
                        "algo_score": algo})

    json.dump({"series": rows, "categories": catrows,
               "n_trades_sampled": len(trades),
               "window": [tt[0], tt[-1]] if trades else None},
              open(os.path.join(OUT, "exch_census.json"), "w"), indent=2,
              default=str)
    print(f"\nwrote {os.path.join(OUT, 'exch_census.json')}")


if __name__ == "__main__":
    main()
