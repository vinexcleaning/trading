"""TASK 1 (Kalshi half) — enumerate every open market and every series.

Writes:
  data/kalshi_markets_open.jsonl   one row per open market (raw)
  data/kalshi_series.json          one row per series incl. fee_type FROM THE API
  reports/kalshi_universe.json     per-series aggregates

Read-only, paced, public endpoints.
"""
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(OUT, "data")
REP = os.path.join(OUT, "reports")


def main():
    t0 = time.time()
    path = os.path.join(DATA, "kalshi_markets_open.jsonl")
    n = 0
    series_tickers = set()
    with open(path, "w", encoding="utf-8") as fh:
        for m in K.paginate("/markets", {"limit": 1000, "status": "open"}, "markets"):
            fh.write(json.dumps(m) + "\n")
            n += 1
            series_tickers.add(K.series_of(m["ticker"]))
            if n % 5000 == 0:
                print(f"  {n} markets, {len(series_tickers)} series, "
                      f"{time.time()-t0:.0f}s", flush=True)
    print(f"open markets: {n}  distinct series: {len(series_tickers)}  "
          f"({time.time()-t0:.0f}s)")

    # Series metadata -- fee_type comes from here, not from documentation.
    # LEDGER S010: docs said maker fee is "25% of taker"; the series field says
    # zero on Challenger/ITF. Documentation has been wrong twice in this project.
    series = {}
    for i, s in enumerate(sorted(series_tickers)):
        r = K.get(f"/series/{s}")
        if r is not None and r.status_code == 200:
            series[s] = r.json().get("series", {})
        else:
            series[s] = {"_http": None if r is None else r.status_code}
        if (i + 1) % 50 == 0:
            print(f"  series {i+1}/{len(series_tickers)}", flush=True)
    with open(os.path.join(DATA, "kalshi_series.json"), "w", encoding="utf-8") as fh:
        json.dump(series, fh, indent=1)
    print(f"series metadata: {len(series)}  ({time.time()-t0:.0f}s)")

    # Aggregate
    agg = defaultdict(lambda: {"n_markets": 0, "n_events": set(), "vol24": 0.0,
                               "oi": 0.0, "two_sided": 0, "any_quote": 0,
                               "tick_sizes": set(), "spreads": []})
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            s = K.series_of(m["ticker"])
            a = agg[s]
            a["n_markets"] += 1
            a["n_events"].add(m.get("event_ticker"))
            a["vol24"] += K.f(m.get("volume_24h_fp")) or 0.0
            a["oi"] += K.f(m.get("open_interest_fp")) or 0.0
            yb = K.cents(m.get("yes_bid_dollars"))
            ya = K.cents(m.get("yes_ask_dollars"))
            # Kalshi reports a "bid" of 0 and an "ask" of 100 when a side is empty.
            has_b = yb is not None and yb > 0
            has_a = ya is not None and ya < 100
            if has_b or has_a:
                a["any_quote"] += 1
            if has_b and has_a:
                a["two_sided"] += 1
                a["spreads"].append(ya - yb)
            ts = m.get("tick_size") or m.get("tick_size_dollars")
            if ts is not None:
                a["tick_sizes"].add(str(ts))

    rows = []
    for s, a in agg.items():
        meta = series.get(s, {})
        sp = sorted(a["spreads"])
        rows.append({
            "series": s,
            "title": meta.get("title", ""),
            "category": meta.get("category", ""),
            "frequency": meta.get("frequency", ""),
            "fee_type": meta.get("fee_type"),
            "fee_multiplier": meta.get("fee_multiplier"),
            "settlement_sources": [x.get("name") or x.get("url", "")
                                   for x in (meta.get("settlement_sources") or [])],
            "n_markets": a["n_markets"],
            "n_events": len(a["n_events"]),
            "volume_24h": round(a["vol24"], 1),
            "open_interest": round(a["oi"], 1),
            "pct_two_sided": round(100.0 * a["two_sided"] / a["n_markets"], 1),
            "pct_any_quote": round(100.0 * a["any_quote"] / a["n_markets"], 1),
            "median_spread_c": round(sp[len(sp) // 2], 2) if sp else None,
            "tick_sizes": sorted(a["tick_sizes"]),
        })
    rows.sort(key=lambda r: -r["volume_24h"])
    with open(os.path.join(REP, "kalshi_universe.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)

    print(f"\n{'series':30s} {'cat':14s} {'mkts':>6s} {'evts':>5s} {'vol24h':>10s} "
          f"{'2sided%':>7s} {'medspr':>6s} fee_type")
    for r in rows[:40]:
        print(f"{r['series'][:30]:30s} {str(r['category'])[:14]:14s} "
              f"{r['n_markets']:6d} {r['n_events']:5d} {r['volume_24h']:10.0f} "
              f"{r['pct_two_sided']:7.1f} {str(r['median_spread_c']):>6s} "
              f"{r['fee_type']}")
    print(f"\ntotal series {len(rows)}  total open markets {n}  "
          f"elapsed {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
