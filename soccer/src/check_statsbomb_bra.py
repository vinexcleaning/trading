"""How much StatsBomb Argentina is there, and is ESPN Brazil actually empty?

Two loose ends:
  1. StatsBomb open-data lists "Argentina / Liga Profesional". If that carries
     event-level data with xG it is the single most predictive public football
     source for one of our exact leagues.
  2. My ESPN history probe returned 0 Brazilian matches for every sampled year
     -- but it sampled the first week of MARCH, and Brazilian Serie A runs
     April to December. That is a defect in my probe, not in the source.
"""
import csv
import io
import json
import os
from collections import Counter

import requests

UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SB = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"


def get(u, p=None):
    try:
        return requests.get(u, params=p, headers=UA, timeout=60)
    except requests.RequestException as e:
        print("  ERR", type(e).__name__, str(e)[:60])
        return None


print("=== StatsBomb: Argentina Liga Profesional ===")
comps = get(f"{SB}/competitions.json").json()
arg = [c for c in comps if c.get("country_name") == "Argentina"]
for c in arg:
    print(f"  competition_id={c['competition_id']} season_id={c['season_id']} "
          f"{c['competition_name']} {c['season_name']} "
          f"gender={c.get('competition_gender')} "
          f"360={c.get('match_available_360') is not None}")
tot = 0
for c in arg:
    r = get(f"{SB}/matches/{c['competition_id']}/{c['season_id']}.json")
    if r is None or r.status_code != 200:
        print(f"  matches {c['competition_id']}/{c['season_id']}: "
              f"http={getattr(r,'status_code','ERR')}")
        continue
    ms = r.json()
    tot += len(ms)
    dates = sorted(m.get("match_date", "") for m in ms)
    teams = sorted({m["home_team"]["home_team_name"] for m in ms})
    print(f"  -> {len(ms)} matches, {dates[0]}..{dates[-1]}, {len(teams)} teams")
    print(f"     sample teams: {teams[:6]}")
    if ms:
        mid = ms[0]["match_id"]
        ev = get(f"{SB}/events/{mid}.json")
        if ev is not None and ev.status_code == 200:
            e = ev.json()
            kinds = Counter(x.get("type", {}).get("name") for x in e)
            has_xg = sum(1 for x in e if (x.get("shot") or {}).get("statsbomb_xg"))
            print(f"     event file for match {mid}: {len(e)} events, "
                  f"{has_xg} shots with statsbomb_xg")
            print(f"     top event types: {kinds.most_common(6)}")
print(f"\n  TOTAL StatsBomb Argentina matches: {tot}")

print("\n=== ESPN Brazil, sampled IN SEASON (August, not March) ===")
for yr in (2026, 2024, 2022, 2019, 2015):
    r = get(f"{SITE}/bra.1/scoreboard",
            {"dates": f"{yr}0801-{yr}0808", "limit": 400})
    n = len(r.json().get("events", [])) if r is not None and r.status_code == 200 else None
    print(f"  bra.1 {yr} first week of August: {n} matches")

print("\n=== the brasileirao-dataset repo ===")
r = get("https://api.github.com/repos/leeofernandes1980/brasileirao-dataset")
if r is not None and r.status_code == 200:
    d = r.json()
    print(f"  pushed={d['pushed_at']} size={d['size']}KB "
          f"stars={d['stargazers_count']} licence={(d.get('license') or {}).get('spdx_id')}")
    tr = get("https://api.github.com/repos/leeofernandes1980/brasileirao-dataset/git/trees/HEAD?recursive=1")
    if tr is not None and tr.status_code == 200:
        files = [x["path"] for x in tr.json().get("tree", [])
                 if x["type"] == "blob"]
        print(f"  {len(files)} files; csv/json: "
              f"{[f for f in files if f.endswith(('.csv','.json'))][:10]}")
