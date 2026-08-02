"""Do ESPN's free propBets carry actual PRICES, and which markets?

SHORTLIST #1 claimed "no free public reference price exists for MLB player
props". The propBets reference resolves with 555-677 entries per game. Before
retracting the mechanism I have to confirm those entries are priced markets and
not, say, a list of participating athletes.
"""
import json
import os
from collections import Counter

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

items = requests.get(f"{CORE}/events", headers=UA, timeout=45).json()["items"]
ref = items[0]["$ref"].split("?")[0]
eid = ref.rstrip("/").split("/")[-1]
url = f"{ref}/competitions/{eid}/odds/100/propBets"

d = requests.get(url, params={"limit": 25}, headers=UA, timeout=45).json()
print(f"propBets on event {eid}: count={d.get('count')}")
print("\n=== one entry, fully expanded ===")
x = d["items"][0]
print(json.dumps(x, indent=1)[:1400])

# resolve the sub-references so we can see what the market actually is
print("\n=== resolving sub-refs on 6 entries ===")
kinds = Counter()
priced = 0
rows = []
for x in d["items"][:6]:
    rec = {}
    for k, v in x.items():
        if isinstance(v, dict) and "$ref" in v:
            try:
                sub = requests.get(v["$ref"], headers=UA, timeout=30).json()
            except Exception:  # noqa: BLE001
                continue
            if k == "athlete":
                rec["athlete"] = sub.get("displayName")
            elif k == "propBetType":
                rec["type"] = sub.get("displayName") or sub.get("name")
            else:
                rec[k] = list(sub)[:6] if isinstance(sub, dict) else str(sub)[:40]
        else:
            rec[k] = v
    kinds[rec.get("type")] += 1
    if any(kk in rec for kk in ("value", "current", "total", "line")):
        priced += 1
    rows.append(rec)
    print(f"  {json.dumps(rec, default=str)[:300]}")

print(f"\nprop types seen: {dict(kinds)}")
print(f"entries carrying a numeric line/price field: {priced}/6")

# how many distinct prop TYPES exist across a full page sweep
print("\n=== sweeping all pages for prop types ===")
types = Counter()
page = 1
seen = 0
while page <= 6:
    dd = requests.get(url, params={"limit": 100, "page": page},
                      headers=UA, timeout=45).json()
    its = dd.get("items", [])
    if not its:
        break
    seen += len(its)
    for x in its:
        pt = x.get("propBetType") or {}
        r = pt.get("$ref")
        if r:
            types[r.rstrip("?lang=en&region=us").split("/")[-1].split("?")[0]] += 1
    if seen >= (dd.get("count") or 0):
        break
    page += 1
print(f"  scanned {seen} entries; distinct propBetType ids: {len(types)}")
print(f"  {dict(list(types.most_common(20)))}")

with open(os.path.join(REP, "propbets_expanded.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"sample": rows, "type_ids": dict(types), "count": d.get("count")},
              fh, indent=1, default=str)
print("\nwrote reports/propbets_expanded.json")
