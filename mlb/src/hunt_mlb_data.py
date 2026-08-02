"""Deep hunt for free MLB data, and for work others have already done.

Verified by pulling. Three layers:
  A. the official/primary free feeds, tested for what they actually contain
  B. first-inning specifics -- lineups, batting order, starter splits
  C. what the community has already built: GitHub repos and Reddit threads on
     YRFI/NRFI, first-inning modelling, and Statcast pipelines. If someone has
     solved a piece of this, read their code rather than rewrite it.
"""
import csv
import io
import json
import os
import time
from collections import Counter

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
out = {}


def get(u, p=None, tries=3, timeout=60):
    for i in range(tries):
        try:
            r = requests.get(u, params=p, headers=UA, timeout=timeout)
        except requests.RequestException as e:
            if i == tries - 1:
                return None
            time.sleep(2 * (i + 1))
            continue
        if r.status_code >= 500 or r.status_code == 429:
            time.sleep(3 * (i + 1))
            continue
        return r
    return None


print("=" * 72)
print("A. PRIMARY FREE FEEDS")
print("=" * 72)

# --- MLB StatsAPI: how deep does it go, and what does a game carry?
r = get("https://statsapi.mlb.com/api/v1/schedule",
        {"sportId": 1, "startDate": "2015-04-06", "endDate": "2015-04-12"})
n2015 = sum(len(d.get("games", [])) for d in r.json().get("dates", [])) if r and r.ok else None
r = get("https://statsapi.mlb.com/api/v1/schedule",
        {"sportId": 1, "startDate": "2026-07-26", "endDate": "2026-08-01"})
n2026 = sum(len(d.get("games", [])) for d in r.json().get("dates", [])) if r and r.ok else None
print(f"  StatsAPI schedule: 2015 sample week {n2015} games, "
      f"2026 sample week {n2026} games")
out["statsapi_schedule"] = {"2015_week": n2015, "2026_week": n2026}

# --- linescore: does it give per-inning runs (the RFI label)?
r = get("https://statsapi.mlb.com/api/v1/schedule",
        {"sportId": 1, "date": "2026-08-01"})
gid = None
if r and r.ok:
    for d in r.json().get("dates", []):
        for g in d.get("games", []):
            if (g.get("status") or {}).get("abstractGameState") == "Final":
                gid = g["gamePk"]
                break
print(f"  sample final gamePk: {gid}")
if gid:
    rl = get(f"https://statsapi.mlb.com/api/v1/game/{gid}/linescore")
    if rl and rl.ok:
        ls = rl.json()
        inns = ls.get("innings") or []
        print(f"  linescore: {len(inns)} innings")
        if inns:
            i1 = inns[0]
            print(f"    inning 1: away runs={((i1.get('away') or {}).get('runs'))} "
                  f"home runs={((i1.get('home') or {}).get('runs'))}")
            print("    -> THE RFI LABEL IS DIRECTLY AVAILABLE, free, per game")
            out["rfi_label_available"] = True
    # boxscore -> probable pitchers, batting order
    rb = get(f"https://statsapi.mlb.com/api/v1/game/{gid}/boxscore")
    if rb and rb.ok:
        bx = rb.json()
        tm = (bx.get("teams") or {}).get("home") or {}
        print(f"  boxscore home: battingOrder n={len(tm.get('battingOrder') or [])} "
              f"pitchers n={len(tm.get('pitchers') or [])}")
        out["boxscore_batting_order"] = len(tm.get("battingOrder") or [])

# --- probable pitchers ahead of time (knowability!)
r = get("https://statsapi.mlb.com/api/v1/schedule",
        {"sportId": 1, "date": "2026-08-03", "hydrate": "probablePitcher,lineups"})
if r and r.ok:
    gs = [g for d in r.json().get("dates", []) for g in d.get("games", [])]
    withpp = sum(1 for g in gs
                 if ((g.get("teams") or {}).get("home") or {}).get("probablePitcher"))
    withlu = sum(1 for g in gs if g.get("lineups"))
    print(f"  TOMORROW: {len(gs)} games, {withpp} with a probable pitcher, "
          f"{withlu} with lineups")
    out["tomorrow"] = {"games": len(gs), "probable_pitcher": withpp,
                       "lineups": withlu}

# --- Statcast
r = get("https://baseballsavant.mlb.com/statcast_search/csv",
        {"all": "true", "game_date_gt": "2026-07-30",
         "game_date_lt": "2026-07-30", "type": "details"}, timeout=120)
if r and r.ok:
    rows = list(csv.reader(io.StringIO(r.text)))
    print(f"  Statcast one day: {len(rows)-1} pitches x {len(rows[0])} cols")
    hdr = rows[0]
    keep = [c for c in hdr if c in ("inning", "pitcher", "batter", "events",
                                    "estimated_woba_using_speedangle",
                                    "launch_speed", "release_speed",
                                    "at_bat_number", "pitch_number",
                                    "home_team", "away_team", "game_pk")]
    print(f"    RFI-relevant columns present: {keep}")
    out["statcast"] = {"pitches_one_day": len(rows) - 1, "cols": len(hdr)}

print("\n" + "=" * 72)
print("B. FIRST-INNING SPECIFICS")
print("=" * 72)
for name, u, p in [
    ("Savant pitcher 1st-inning split",
     "https://baseballsavant.mlb.com/statcast_search/csv",
     {"all": "true", "game_date_gt": "2026-07-01", "game_date_lt": "2026-07-02",
      "type": "details"}),
    ("FanGraphs leaders (free page)",
     "https://www.fangraphs.com/leaders/major-league", None),
    ("Baseball-Reference", "https://www.baseball-reference.com/leagues/MLB/2026.shtml", None),
    ("Retrosheet event files", "https://www.retrosheet.org/game.htm", None),
    ("pybaseball repo", "https://api.github.com/repos/jldbc/pybaseball", None),
]:
    r = get(u, p)
    print(f"  {name:38s} http={getattr(r,'status_code','ERR')} "
          f"bytes={len(r.content) if r is not None else 0}")
    out[name] = getattr(r, "status_code", None)

print("\n" + "=" * 72)
print("C. WHAT THE COMMUNITY HAS ALREADY BUILT")
print("=" * 72)
queries = ["YRFI NRFI", "first inning run prediction", "NRFI model baseball",
           "mlb first inning betting", "statcast first inning",
           "kalshi mlb", "mlb prop model statcast", "baseball betting model"]
repos = {}
for q in queries:
    r = get("https://api.github.com/search/repositories",
            {"q": q, "sort": "updated", "per_page": 8})
    if r is None or r.status_code != 200:
        print(f"  {q!r}: http {getattr(r,'status_code','ERR')}")
        continue
    d = r.json()
    print(f"\n  {q!r}: {d.get('total_count')} repos")
    for x in d.get("items", [])[:8]:
        key = x["full_name"]
        repos[key] = {"pushed": x["pushed_at"][:10],
                      "stars": x["stargazers_count"], "size_kb": x["size"],
                      "desc": (x.get("description") or "")[:80]}
        print(f"    {key[:46]:46s} {x['pushed_at'][:10]} "
              f"*{x['stargazers_count']:<4d} {x['size']:>7d}KB  "
              f"{(x.get('description') or '')[:52]}")
    time.sleep(1.5)
out["repos"] = repos

print("\n  --- Reddit: what are people saying about YRFI/NRFI edges? ---")
for sub, q in [("sportsbook", "NRFI"), ("algobetting", "first inning"),
               ("Sabermetrics", "first inning"), ("dfsports", "NRFI")]:
    r = get(f"https://www.reddit.com/r/{sub}/search.json",
            {"q": q, "restrict_sr": "on", "sort": "top", "t": "year",
             "limit": 8})
    if r is None or r.status_code != 200:
        print(f"    r/{sub} {q!r}: http {getattr(r,'status_code','ERR')}")
        continue
    try:
        ch = r.json().get("data", {}).get("children", [])
    except ValueError:
        print(f"    r/{sub}: non-json")
        continue
    print(f"    r/{sub} {q!r}: {len(ch)} posts")
    for c in ch[:5]:
        dd = c["data"]
        print(f"       [{dd.get('score'):>4}] {dd.get('title')[:80]}")
    out[f"reddit_{sub}_{q}"] = [c["data"].get("title") for c in ch[:8]]
    time.sleep(2)

with open(os.path.join(REP, "hunt_mlb.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/hunt_mlb.json")
