"""TASK 1 — roll the 3,074-series Kalshi universe up to categories and fee types.

fee_type is read from the /series endpoint per series, never from documentation.
Documentation has been wrong twice in this project (LEDGER C015 Polymarket fee,
S010 Kalshi maker fee), and both times only the venue's own data revealed it.
"""
import json
import os
from collections import Counter, defaultdict

REP = os.path.join(os.path.dirname(__file__), "..", "reports")
rows = json.load(open(os.path.join(REP, "kalshi_universe.json"), encoding="utf-8"))

print(f"KALSHI: {len(rows)} series, {sum(r['n_markets'] for r in rows):,} open "
      f"markets, {sum(r['n_events'] for r in rows):,} events\n")

print("=== fee_type, from the API ===")
ft = Counter(str(r["fee_type"]) for r in rows)
ftm = defaultdict(int)
ftv = defaultdict(float)
for r in rows:
    ftm[str(r["fee_type"])] += r["n_markets"]
    ftv[str(r["fee_type"])] += r["volume_24h"]
print(f"{'fee_type':34s} {'series':>7s} {'markets':>9s} {'vol24h':>12s}")
for k, n in ft.most_common():
    print(f"{k:34s} {n:7d} {ftm[k]:9,d} {ftv[k]:12,.0f}")

print("\n=== fee_multiplier ===")
print(Counter(str(r.get("fee_multiplier")) for r in rows).most_common())

print("\n=== by category ===")
cat = defaultdict(lambda: {"series": 0, "markets": 0, "events": 0, "vol": 0.0,
                           "two": [], "maker": 0})
for r in rows:
    c = r["category"] or "(none)"
    a = cat[c]
    a["series"] += 1
    a["markets"] += r["n_markets"]
    a["events"] += r["n_events"]
    a["vol"] += r["volume_24h"]
    a["two"].append(r["pct_two_sided"])
    a["maker"] += (r["fee_type"] == "quadratic_with_maker_fees")
print(f"{'category':22s} {'series':>7s} {'markets':>9s} {'events':>7s} "
      f"{'vol24h':>12s} {'2sided%':>8s} {'makerfee':>8s}")
for c, a in sorted(cat.items(), key=lambda x: -x[1]["vol"]):
    tw = sorted(a["two"])
    med = tw[len(tw) // 2] if tw else 0
    print(f"{c[:22]:22s} {a['series']:7d} {a['markets']:9,d} {a['events']:7,d} "
          f"{a['vol']:12,.0f} {med:8.1f} {a['maker']:8d}")

print("\n=== tick sizes across the exchange ===")
ts = Counter()
for r in rows:
    for t in r["tick_sizes"] or ["(none)"]:
        ts[t] += r["n_markets"]
print(ts.most_common(10))

print("\n=== settlement sources actually declared ===")
ss = Counter()
for r in rows:
    for s in (r["settlement_sources"] or []):
        ss[s] += 1
    if not r["settlement_sources"]:
        ss["(none declared)"] += 1
for k, v in ss.most_common(25):
    print(f"  {v:5d}  {k[:90]}")

print("\n=== how concentrated is the market count? ===")
tot = sum(r["n_markets"] for r in rows)
run = 0
for i, r in enumerate(sorted(rows, key=lambda r: -r["n_markets"])[:8], 1):
    run += r["n_markets"]
    print(f"  {i}. {r['series']:32s} {r['n_markets']:8,d} "
          f"({100*r['n_markets']/tot:5.1f}%)  cum {100*run/tot:5.1f}%")

poly = json.load(open(os.path.join(REP, "poly_universe.json"), encoding="utf-8"))
print(f"\n\nPOLYMARKET: {len(poly)} tags")
print(f"{'tag':26s} {'mkts':>6s} {'evts':>5s} {'live':>6s} {'vol24h':>12s} "
      f"{'2sid%':>6s} {'med':>5s} {'p75':>5s} {'p90':>6s}")
for r in poly[:22]:
    print(f"{str(r['tag'])[:26]:26s} {r['n_markets']:6d} {r['n_events']:5d} "
          f"{r['n_live']:6d} {r['volume_24h']:12,.0f} {r['pct_two_sided']:6.1f} "
          f"{str(r['median_spread_c']):>5s} {str(r['p75_spread_c']):>5s} "
          f"{str(r['p90_spread_c']):>6s}")
