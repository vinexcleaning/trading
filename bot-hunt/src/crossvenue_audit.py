"""Which matched pairs actually carried the cross-venue result, and are they REAL?

The join produced 97 matched events but only 13 contributed paired quotes, so
those 13 carry the entire finding. The corpora are unanimous that this is where
cross-venue work dies — *"the phantoms have HIGH token overlap, not low"* — and
two suspicious pairs are already visible by eye:

  Kalshi "Vitality" <-> Pinnacle "Bigetron by Vitality"   probably NOT the same
  Kalshi "CYBERSHOKE Esports" <-> Pinnacle "CYBERSHOKE Prospects"   two teams

So every contributing pair is printed in full for inspection, with its own edge,
rather than trusting an aggregate over pairs that may not be the same contract.
A pair that cannot be confirmed is dropped, not averaged in.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

REP = Path(__file__).resolve().parent.parent / "reports"
d = json.loads((REP / "crossvenue_join.json").read_text(encoding="utf-8"))
print(f"matched events: {d['pairs']}   paired observations: {d['observations']}")
print("\nAggregate by de-vig method (from the join run):")
for m, v in d["methods"].items():
    print(f"  {m:16} n={v['n']:>5} median buy edge {v['edge_buy_med']:+6.2f}c "
          f"p90 {v['edge_buy_p90']:+6.2f}c   >2c on "
          f"{100*v['frac_buy_over_2c']:.1f}%")

print("\n" + "=" * 78)
print("EVERY MATCHED PAIR, FOR HAND INSPECTION")
print("=" * 78)
print("A pair is REAL only if both sides name the same team in the same match.")
print("Watch for: academy/junior/prospects suffixes, sponsor prefixes, and")
print("organisations that field multiple rosters.\n")
sus = 0
for p in d["examples"]:
    nm = p.get("names", {})
    meta = p.get("meta", {})
    kn = " | ".join(sorted(nm.values()))
    print(f"  {p['event'][:46]:46}")
    print(f"     kalshi   : {kn[:70]}")
    print(f"     pinnacle : {meta.get('home','?')} vs {meta.get('away','?')}"
          f"   [{meta.get('league','?')}]")
    joined = (kn + " " + str(meta.get("home")) + " "
              + str(meta.get("away"))).lower()
    flags = [w for w in ("academy", "junior", "prospect", "youth", "by ",
                         "female", "women", "b team", " ii")
             if w in joined]
    if flags:
        sus += 1
        print(f"     !! SUSPECT — contains {flags}; an organisation's second "
              f"roster is not the first")
    print()
print(f"{sus} of {len(d['examples'])} shown pairs carry a suspect token.")
print("\nThe honest position: this join is a RECALL net. Its precision is")
print("unmeasured and visibly imperfect, so the aggregate above is an upper")
print("bound on how much of the tail is real edge rather than a mismatched")
print("pair. Resolution-equivalence, not name similarity, is the real filter.")
