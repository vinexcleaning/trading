"""Expand the `propBets` reference on ESPN's free odds object.

SHORTLIST entry #1's entire mechanism is "no free public reference price exists
for MLB player props". The odds object has a `propBets` key. If it resolves to
real free prop prices, that mechanism is dead and entry #1 has to be demoted.
"""
import json
import os

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

items = requests.get(f"{CORE}/events", headers=UA, timeout=45).json()["items"]
found = {}
for it0 in items[:4]:
    ref = it0["$ref"].split("?")[0]
    eid = ref.rstrip("/").split("/")[-1]
    od = requests.get(f"{ref}/competitions/{eid}/odds", headers=UA,
                      timeout=45).json()
    for item in od.get("items", []):
        prov = (item.get("provider") or {}).get("name")
        pb = item.get("propBets")
        print(f"\nevent {eid} provider {prov}")
        print(f"  propBets = {json.dumps(pb)[:220]}")
        url = None
        if isinstance(pb, dict):
            url = pb.get("$ref")
        elif isinstance(pb, list) and pb and isinstance(pb[0], dict):
            url = pb[0].get("$ref")
        if not url:
            print("  -> no $ref to follow")
            continue
        r = requests.get(url, headers=UA, timeout=45)
        print(f"  -> {url.split('?')[0][-60:]}  http={r.status_code} "
              f"bytes={len(r.content)}")
        if r.status_code != 200:
            continue
        try:
            d = r.json()
        except ValueError:
            print("  -> non-json")
            continue
        if isinstance(d, dict):
            print(f"     keys={sorted(d)[:12]} count={d.get('count')} "
                  f"items={len(d.get('items', []))}")
            for x in (d.get("items") or [])[:6]:
                print(f"       {json.dumps(x)[:200]}")
            found[eid] = {"count": d.get("count"),
                          "n_items": len(d.get("items", []))}

print("\nVERDICT")
total = sum(v.get("count") or 0 for v in found.values())
if total:
    print(f"  ESPN's free feed DOES expose {total} prop entries -- "
          f"SHORTLIST #1's mechanism is weakened or dead.")
else:
    print("  propBets resolves but is EMPTY on every event checked.")
    print("  ESPN's free feed carries moneyline, spread and game over/under only.")
    print("  No player-prop prices. SHORTLIST #1's mechanism survives this test.")

with open(os.path.join(REP, "propbets.json"), "w", encoding="utf-8") as fh:
    json.dump(found, fh, indent=1, default=str)
