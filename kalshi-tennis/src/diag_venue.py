"""Why is surface unresolved for a quarter of markets?"""
import pathlib
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ev = td.load_kalshi_events()
matches = td.load_matches()
smap = td.build_surface_map(matches)
ev["surface"] = ev["venue"].map(lambda v: td.surface_for(v, smap))

print(f"total markets            {len(ev)}")
print(f"tourney_raw parsed       {ev['tourney_raw'].notna().sum()} "
      f"({ev['tourney_raw'].notna().mean() * 100:.1f}%)")
print(f"venue parsed             {ev['venue'].notna().sum()}")
print(f"surface resolved         {ev['surface'].notna().sum()} "
      f"({ev['surface'].notna().mean() * 100:.1f}%)")

print("\n--- markets where tourney_raw failed to parse: sample rules ---")
bad = ev[ev["tourney_raw"].isna()]
print(f"{len(bad)} rows")
seen = set()
for _, r in bad.iterrows():
    t = r["event_ticker"].split("-")[0]
    if t in seen:
        continue
    seen.add(t)
    print(f"\n  [{t}] {r['event_ticker']}")

import json  # noqa: E402
raw = json.loads((td.KALSHI / "tennis_markets.json").read_text(encoding="utf-8"))
lookup = {}
for series, rows in raw.items():
    for m in rows:
        lookup.setdefault(m["event_ticker"], m)

shown = 0
for _, r in bad.iterrows():
    m = lookup.get(r["event_ticker"])
    if not m:
        continue
    print(f"\n  {r['event_ticker']}")
    print(f"    {(m.get('rules_primary') or '')[:260]}")
    shown += 1
    if shown >= 8:
        break

print("\n--- which venues map to Carpet? (suspicious for 2026) ---")
carp = ev[ev["surface"] == "Carpet"]
print(Counter(carp["tourney_raw"].dropna()).most_common(20))

print("\n--- venue -> surface for the 25 most common venues ---")
top = ev["venue"].value_counts().head(25)
for v, n in top.items():
    print(f"  {v:<28} n={n:<5} -> {smap.get(v) or td.surface_for(v, smap)}")
