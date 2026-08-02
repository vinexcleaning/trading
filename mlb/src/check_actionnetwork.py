"""Does Action Network's free API actually carry a first-inning line?

Its MLB scoreboard returned HTTP 200 and the body contains "rfi". If that is a
real priced YRFI/NRFI market then KXMLBRFI has a free reference and dies the
way the game-winner did. A substring match is not evidence -- find the actual
field and the actual price, or rule it out.
"""
import json
import os
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

r = requests.get("https://api.actionnetwork.com/web/v2/scoreboard/mlb",
                 headers=UA, timeout=45)
print(f"http={r.status_code} bytes={len(r.content)}")
txt = r.text

# where does 'rfi' actually appear?
print("\n=== every occurrence of 'rfi' in context ===")
seen = set()
for m in re.finditer(r"rfi", txt, re.I):
    s = txt[max(0, m.start() - 90):m.start() + 90].replace("\n", " ")
    if s[:60] in seen:
        continue
    seen.add(s[:60])
    print(f"  ...{s}...")
    if len(seen) > 12:
        break

d = r.json()
print(f"\ntop-level keys: {sorted(d)}")
games = d.get("games") or []
print(f"games: {len(games)}")
if games:
    g = games[0]
    print(f"game keys: {sorted(g)}")
    odds = g.get("odds") or []
    print(f"\nodds blocks on game 0: {len(odds)}")
    if odds:
        print(f"  odds[0] keys: {sorted(odds[0])}")
        print(f"  sample: {json.dumps(odds[0])[:700]}")
    # markets / options that might be RFI
    for k in ("markets", "props", "period", "type"):
        if k in g:
            print(f"  g[{k!r}] = {json.dumps(g[k])[:300]}")

# Action Network exposes period-scoped odds; check for a first-inning period
print("\n=== period values present across all odds blocks ===")
periods = {}
for g in games:
    for o in (g.get("odds") or []):
        p = o.get("type") or o.get("period")
        periods[p] = periods.get(p, 0) + 1
print(f"  {periods}")

hit = any(p and ("first" in str(p).lower() or "1st" in str(p).lower()
                 or "inning" in str(p).lower()) for p in periods)
print("\nVERDICT:")
if hit:
    print("  *** A first-inning period EXISTS in Action Network's free feed.")
    print("      KXMLBRFI likely has a free reference -- investigate before")
    print("      building anything on it. ***")
else:
    print("  No first-inning period in the free scoreboard feed. The 'rfi'")
    print("  substring is not a priced first-inning market here.")
    print(f"  periods offered: {sorted(str(p) for p in periods)}")

json.dump({"periods": {str(k): v for k, v in periods.items()},
           "first_inning_present": hit},
          open(os.path.join(REP, "actionnetwork.json"), "w"), indent=1)
