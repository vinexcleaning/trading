"""Dimension C detail: which series are fee-free, and what is the real tick?

Two things the universe roll-up surfaced that documentation would not have:

1. `fee_multiplier` is 0 on 11 of 3,074 series. If that means what it says,
   those series are FEE-FREE, which changes their cost bar to spread alone.
2. `tick_size` is ABSENT from the market object on all 419,828 markets -- the
   key simply is not there. Yet observed median spreads include 0.1c and 0.3c,
   so a 1c tick is not universal. The tick therefore has to be measured off
   real quoted prices rather than read from a field.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
REP, DATA = os.path.join(ROOT, "reports"), os.path.join(ROOT, "data")

series = json.load(open(os.path.join(DATA, "kalshi_series.json"), encoding="utf-8"))
uni = {r["series"]: r for r in
       json.load(open(os.path.join(REP, "kalshi_universe.json"), encoding="utf-8"))}

print("=== series with fee_multiplier == 0 ===")
zero = [(s, d) for s, d in series.items() if str(d.get("fee_multiplier")) == "0"]
for s, d in zero:
    u = uni.get(s, {})
    print(f"  {s:26s} fee_type={str(d.get('fee_type')):26s} "
          f"cat={str(d.get('category'))[:14]:14s} mkts={u.get('n_markets')} "
          f"vol24h={u.get('volume_24h')}")
    print(f"      title: {str(d.get('title'))[:88]}")
print(f"  ({len(zero)} series)")

print("\n=== is `tick_size` really absent from the market object? ===")
keys = Counter()
n = 0
with open(os.path.join(DATA, "kalshi_markets_open.jsonl"), encoding="utf-8") as fh:
    for line in fh:
        m = json.loads(line)
        n += 1
        for k in m:
            keys[k] += 1
        if n >= 20000:
            break
print(f"  scanned {n} market objects")
for k in ("tick_size", "tick_size_dollars", "min_tick", "notional_value_dollars",
          "strike_type", "market_type", "response_price_units"):
    print(f"    {k:26s} present on {keys.get(k,0):6d}")
print(f"  full key list: {sorted(keys)}")

print("\n=== empirical tick, measured off quoted prices in the depth recorder ===")
import glob  # noqa: E402
gran = defaultdict(Counter)
files = glob.glob(os.path.join(DATA, "depth_broad", "*", "*", "depth.jsonl"))
rows = 0
for f in files:
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows += 1
            s = d.get("series", "?")
            for side in ("yes", "no"):
                for p, _sz in (d.get(side) or []):
                    # how many decimal places does this price really use?
                    q = Decimal(str(round(p, 4))).normalize()
                    exp = -q.as_tuple().exponent
                    gran[s][max(exp, 0)] += 1
print(f"  {rows} snapshots, {len(files)} hour-files")
print(f"  {'series':28s} {'levels':>8s}  decimal places in price (cents)")
out = {}
for s, c in sorted(gran.items(), key=lambda x: -sum(x[1].values()))[:40]:
    tot = sum(c.values())
    frac = {k: round(v / tot, 3) for k, v in sorted(c.items())}
    # smallest observed increment implied by the finest place used
    finest = max(c)
    tick = 10 ** (-finest) if finest else 1.0
    out[s] = {"levels": tot, "places": frac, "implied_tick_c": tick}
    print(f"  {s[:28]:28s} {tot:8d}  {frac}  -> tick ~{tick}c")

with open(os.path.join(REP, "fees_and_ticks.json"), "w", encoding="utf-8") as fh:
    json.dump({"zero_fee_multiplier": [s for s, _ in zero],
               "tick_by_series": out}, fh, indent=1)
print("\nwrote reports/fees_and_ticks.json")
