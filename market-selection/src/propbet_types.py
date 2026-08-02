"""Which MLB prop markets does the FREE DraftKings feed cover?

Established: ESPN's free propBets endpoint returns fully priced entries --
type name, line, current American odds and the opening price -- 555-677 per
game with no key. So SHORTLIST #1's mechanism ("no free public reference price
exists for props") is false.

The remaining question is coverage: does the free feed cover the SAME props
Kalshi lists (strikeouts, hits, total bases, HR, hits+runs+RBI), or only a
subset? Whatever it does not cover is the only place the original mechanism
could survive.
"""
import json
import os
from collections import Counter

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

KALSHI = {
    "KXMLBKS": "strikeouts", "KXMLBHIT": "hits", "KXMLBTB": "total bases",
    "KXMLBHR": "home runs", "KXMLBHRR": "hits + runs + RBIs",
    "KXMLBRFI": "run in the first inning",
    "KXMLBTEAMTOTAL": "team total runs", "KXMLBF5TOTAL": "first 5 innings runs",
    "KXMLBTOTAL": "game total runs", "KXMLBSPREAD": "run line",
    "KXMLBEXTRAS": "extra innings",
}

items = requests.get(f"{CORE}/events", headers=UA, timeout=45).json()["items"]
types = Counter()
priced = 0
total_seen = 0
lines_by_type = {}

for it0 in items[:6]:
    ref = it0["$ref"].split("?")[0]
    eid = ref.rstrip("/").split("/")[-1]
    url = f"{ref}/competitions/{eid}/odds/100/propBets"
    page = 1
    got = 0
    while page <= 8:
        try:
            d = requests.get(url, params={"limit": 100, "page": page},
                             headers=UA, timeout=45).json()
        except Exception:  # noqa: BLE001
            break
        its = d.get("items", [])
        if not its:
            break
        for x in its:
            t = (x.get("type") or {}).get("name")
            types[t] += 1
            total_seen += 1
            o = x.get("odds") or {}
            if (o.get("american") or {}).get("value") is not None:
                priced += 1
            tot = (o.get("total") or {}).get("value")
            if t and tot is not None and t not in lines_by_type:
                lines_by_type[t] = tot
        got += len(its)
        if got >= (d.get("count") or 0):
            break
        page += 1

print(f"scanned {total_seen} prop entries across 6 games")
print(f"entries carrying an American price: {priced} "
      f"({100*priced/max(total_seen,1):.1f}%)\n")
print(f"{'prop type':40s} {'entries':>8s}  example line")
for t, n in types.most_common(40):
    print(f"{str(t)[:40]:40s} {n:8d}  {lines_by_type.get(t)}")

print("\n=== does the free feed cover Kalshi's prop families? ===")
low = {str(t).lower(): t for t in types}
for series, want in KALSHI.items():
    hit = [orig for l, orig in low.items()
           if any(w in l for w in want.split()[:2])]
    print(f"  {series:16s} ({want:26s}) -> "
          f"{'COVERED: ' + str(hit[:3]) if hit else 'not found in the free feed'}")

with open(os.path.join(REP, "propbet_types.json"), "w", encoding="utf-8") as fh:
    json.dump({"types": dict(types), "priced": priced, "total": total_seen,
               "example_lines": lines_by_type}, fh, indent=1, default=str)
print("\nwrote reports/propbet_types.json")
