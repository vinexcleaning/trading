"""Does StatsBomb open data really cover MLS?

My first filter matched country_name against lowercase "united states" and
missed "United States of America", so I reported StatsBomb as covering only
Argentina. The competition list actually names "Major League Soccer" and
"NWSL". Checking whether those are real datasets or, like Argentina, two
historical showcase matches.
"""
import json
import os
from collections import Counter

import requests

UA = {"User-Agent": "soccer-research/1.0"}
SB = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

comps = requests.get(f"{SB}/competitions.json", headers=UA, timeout=60).json()
targets = [c for c in comps
           if c.get("competition_name") in ("Major League Soccer", "NWSL",
                                            "North American League",
                                            "Liga Profesional")]
out = []
for c in targets:
    line = {"competition_id": c["competition_id"], "season_id": c["season_id"],
            "name": c["competition_name"], "season": c["season_name"],
            "country": c.get("country_name")}
    print(f"\n{c['competition_name']} {c['season_name']} "
          f"(country={c.get('country_name')}, comp={c['competition_id']}, "
          f"season={c['season_id']})")
    r = requests.get(f"{SB}/matches/{c['competition_id']}/{c['season_id']}.json",
                     headers=UA, timeout=60)
    if r.status_code != 200:
        print(f"  matches http {r.status_code}")
        line["matches"] = None
        out.append(line)
        continue
    ms = r.json()
    ds = sorted(m.get("match_date", "") for m in ms)
    teams = sorted({m["home_team"]["home_team_name"] for m in ms}
                   | {m["away_team"]["away_team_name"] for m in ms})
    line.update({"matches": len(ms), "first": ds[0] if ds else None,
                 "last": ds[-1] if ds else None, "n_teams": len(teams)})
    print(f"  -> {len(ms)} matches, {ds[0] if ds else '?'} .. "
          f"{ds[-1] if ds else '?'}, {len(teams)} teams")
    print(f"     teams: {teams[:8]}")
    if ms:
        mid = ms[0]["match_id"]
        ev = requests.get(f"{SB}/events/{mid}.json", headers=UA, timeout=60)
        if ev.status_code == 200:
            e = ev.json()
            xg = sum(1 for x in e if (x.get("shot") or {}).get("statsbomb_xg"))
            line["sample_events"] = len(e)
            line["sample_shots_with_xg"] = xg
            print(f"     sample match {mid}: {len(e)} events, {xg} shots with xG")
    out.append(line)

print("\n=== verdict ===")
for l in out:
    n = l.get("matches")
    print(f"  {l['name']:24s} {l['season']:10s} n={n}")

with open(os.path.join(REP, "statsbomb_mls.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
