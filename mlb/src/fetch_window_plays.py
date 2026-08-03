"""MLB scoring plays with UTC timestamps, inside the tape window.

The in-play test needs discrete events stamped in absolute time. MLB's
play-by-play carries `about.startTime` / `endTime` in UTC for every play, and
`about.isScoringPlay`, so a run crossing the plate has a real timestamp.

Why MLB rather than soccer: the tape window (2026-05-25..06-11) is the Liga MX
and Argentine OFF-SEASON, leaving only 31 ESPN soccer matches. MLB plays every
day and the tape is full of it.

THE CAVEAT THAT DECIDES EVERYTHING. `startTime` is when MLB's own system
recorded the play, not when the ball was hit. Every data feed has a
publication lag. The study measures it indirectly: if Kalshi's price starts
moving BEFORE this timestamp, the feed is too slow to trade on.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta

import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
API = "https://statsapi.mlb.com/api/v1"
UA = {"User-Agent": "mlb-research/1.0"}
LO, HI = date(2026, 5, 25), date(2026, 6, 11)


def get(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3 * (i + 1))
            continue
        time.sleep(0.12)
        return r
    return None


def main():
    # games in the window
    games = []
    d = LO
    while d <= HI:
        d2 = min(d + timedelta(days=6), HI)
        r = get(f"{API}/schedule", {"sportId": 1, "startDate": d.isoformat(),
                                    "endDate": d2.isoformat()})
        if r is not None and r.status_code == 200:
            for day in r.json().get("dates", []):
                for g in day.get("games", []):
                    if ((g.get("status") or {}).get("abstractGameState")) == "Final":
                        games.append({"pk": g["gamePk"], "date": g["gameDate"],
                                      "home": ((g.get("teams") or {}).get("home") or {}).get("team", {}).get("name"),
                                      "away": ((g.get("teams") or {}).get("away") or {}).get("team", {}).get("name")})
        d = d2 + timedelta(days=1)
    print(f"{len(games)} final MLB games in {LO}..{HI}")

    out, n_sc, n_1st = 0, 0, 0
    path = os.path.join(DATA, "window_plays.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for i, g in enumerate(games):
            r = get(f"https://statsapi.mlb.com/api/v1.1/game/{g['pk']}/feed/live")
            if r is None or r.status_code != 200:
                continue
            try:
                d_ = r.json()
            except ValueError:
                continue
            plays = (((d_.get("liveData") or {}).get("plays") or {})
                     .get("allPlays") or [])
            evs = []
            for p in plays:
                ab = p.get("about") or {}
                res = p.get("result") or {}
                if not ab.get("startTime"):
                    continue
                rbi = res.get("rbi") or 0
                scoring = bool(ab.get("isScoringPlay"))
                if not scoring:
                    continue
                evs.append({
                    "inning": ab.get("inning"),
                    "half": ab.get("halfInning"),
                    "start": ab.get("startTime"),
                    "end": ab.get("endTime"),
                    "event": res.get("event"),
                    "desc": (res.get("description") or "")[:120],
                    "rbi": rbi,
                    "away_score": res.get("awayScore"),
                    "home_score": res.get("homeScore"),
                })
            n_sc += len(evs)
            n_1st += sum(1 for e in evs if e["inning"] == 1)
            fh.write(json.dumps({**g, "scoring_plays": evs}) + "\n")
            out += 1
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(games)} games, {n_sc} scoring plays "
                      f"({n_1st} in the 1st)", flush=True)

    print(f"\n{out} games written")
    print(f"  scoring plays: {n_sc}")
    print(f"  first-inning scoring plays: {n_1st}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
