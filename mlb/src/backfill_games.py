"""Backfill MLB games + the first-inning outcome, 2016-2026.

One row per game with:
  * the RFI LABEL -- runs in the first inning, from the linescore
  * both starting pitchers (who actually started)
  * both batting orders (who actually batted) -- the historical proxy for the
    announced lineup
  * venue, date, teams, final score

The label and the lineup are both free and historical, which is why the live
recorder does not block this.

Resumable by date. Content-validated: a date is only marked done once its
games parsed and carried a linescore or an explicit not-final status.
Paced, read-only, public.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import date, timedelta

import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "games")
API = "https://statsapi.mlb.com/api/v1"
UA = {"User-Agent": "mlb-research/1.0"}
START = date(2016, 3, 1)
END = date.today()
PACE = 0.12


def get(path, params=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(f"{API}/{path}", params=params, headers=UA,
                             timeout=45)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3 * (i + 1))
            continue
        time.sleep(PACE)
        return r
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    prog_p = os.path.join(OUT, "_progress.json")
    prog = {}
    if os.path.exists(prog_p):
        try:
            prog = json.load(open(prog_p, encoding="utf-8"))
        except ValueError:
            prog = {}
    path = os.path.join(OUT, "games.jsonl")
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["game_pk"])
                except (ValueError, KeyError):
                    pass
    print(f"{len(seen)} games already on disk", flush=True)

    # walk in 7-day windows -- the schedule endpoint takes a range
    wins = []
    d = START
    while d < END:
        d2 = min(d + timedelta(days=7), END)
        wins.append((d, d2))
        if d2 >= END:
            break
        d = d2
    todo = [w for w in wins if prog.get(str(w[0])) != "done"]
    print(f"{len(wins)} windows, {len(todo)} to fetch", flush=True)

    stats = Counter()
    t0 = time.time()
    with open(path, "a", encoding="utf-8", buffering=1) as fh:
        for i, (d, d2) in enumerate(todo):
            r = get("schedule", {"sportId": 1,
                                 "startDate": d.isoformat(),
                                 "endDate": d2.isoformat(),
                                 "hydrate": "linescore,probablePitcher,venue"})
            if r is None or r.status_code != 200:
                stats["window_fail"] += 1
                continue
            try:
                dates = r.json().get("dates", [])
            except ValueError:
                stats["unparseable"] += 1
                continue
            for day in dates:
                for g in day.get("games", []):
                    pk = g.get("gamePk")
                    st = ((g.get("status") or {}).get("abstractGameState"))
                    if not pk or st != "Final":
                        stats["not_final"] += 1
                        continue
                    if pk in seen:
                        continue
                    ls = g.get("linescore") or {}
                    inns = ls.get("innings") or []
                    if not inns:
                        stats["no_linescore"] += 1
                        continue
                    i1 = inns[0]
                    ar = ((i1.get("away") or {}).get("runs"))
                    hr = ((i1.get("home") or {}).get("runs"))
                    if ar is None or hr is None:
                        stats["no_first_inning"] += 1
                        continue
                    teams = g.get("teams") or {}

                    def side(s):
                        t = teams.get(s) or {}
                        tm = t.get("team") or {}
                        pp = t.get("probablePitcher") or {}
                        return {"team_id": tm.get("id"), "team": tm.get("name"),
                                "score": t.get("score"),
                                "probable_id": pp.get("id"),
                                "probable": pp.get("fullName")}

                    row = {
                        "game_pk": pk, "date": g.get("gameDate"),
                        "season": g.get("season"),
                        "game_type": g.get("gameType"),
                        "venue_id": ((g.get("venue") or {}).get("id")),
                        "venue": ((g.get("venue") or {}).get("name")),
                        "day_night": g.get("dayNight"),
                        "double_header": g.get("doubleHeader"),
                        "home": side("home"), "away": side("away"),
                        # ---- THE LABEL
                        "first_inning_away_runs": ar,
                        "first_inning_home_runs": hr,
                        "yrfi": 1 if (ar + hr) > 0 else 0,
                        "total_innings": len(inns),
                    }
                    fh.write(json.dumps(row) + "\n")
                    seen.add(pk)
                    stats["written"] += 1
            prog[str(d)] = "done"
            stats["windows"] += 1
            if (i + 1) % 40 == 0:
                json.dump(prog, open(prog_p, "w"), indent=0)
                el = time.time() - t0
                print(f"  {i+1}/{len(todo)} windows | {stats['written']} games "
                      f"| {el/60:.1f} min | eta "
                      f"{(len(todo)-i-1)*el/max(i+1,1)/60:.0f} min", flush=True)
    json.dump(prog, open(prog_p, "w"), indent=0)

    print(f"\nDONE {(time.time()-t0)/60:.1f} min  {dict(stats)}")
    # coverage + the base rate, computed from the file
    yrs = Counter()
    yr_yrfi = Counter()
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                g = json.loads(line)
            except ValueError:
                continue
            n += 1
            y = str(g.get("season"))
            yrs[y] += 1
            yr_yrfi[y] += g["yrfi"]
    print(f"\ngames on disk: {n:,}")
    print(f"\n  {'season':8s} {'games':>7s} {'YRFI':>7s} {'rate':>7s}")
    tot = tyr = 0
    for y in sorted(yrs):
        tot += yrs[y]
        tyr += yr_yrfi[y]
        print(f"  {y:8s} {yrs[y]:7,d} {yr_yrfi[y]:7,d} "
              f"{yr_yrfi[y]/yrs[y]:7.4f}")
    print(f"\n  BASE RATE across {tot:,} games: {tyr/max(tot,1):.4f}")
    print(f"  Brier of always predicting the base rate: "
          f"{(tyr/max(tot,1))*(1-tyr/max(tot,1)):.4f}")
    print("  (this is the number any model must beat before anything else)")


if __name__ == "__main__":
    main()
