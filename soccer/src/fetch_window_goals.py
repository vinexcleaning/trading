"""Goal wallclocks for soccer matches inside the tape window (2026-05-25..06-11).

Needed for the in-play study. ESPN publishes an absolute UTC `wallclock` on
every keyEvent, which is what makes a second-resolution join possible at all.

IMPORTANT CAVEAT THIS DATA CANNOT ESCAPE. `wallclock` is when ESPN RECORDED
the event, not when the ball crossed the line. There is a reporting lag of
unknown size. The event study measures that lag indirectly -- by comparing
ESPN's stamp to the moment Kalshi's price actually starts moving -- and if the
market moves first, ESPN is too slow to trade on and the idea is dead.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
LO, HI = "2026-05-24", "2026-06-12"


def get(u, p=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(u, params=p, headers=UA, timeout=45)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3 * (i + 1))
            continue
        time.sleep(0.15)
        return r
    return None


def main():
    matches = []
    with open(os.path.join(DATA, "espn_history", "matches.jsonl"),
              encoding="utf-8") as fh:
        for line in fh:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            d = (m.get("date") or "")[:10]
            if LO <= d <= HI and m.get("completed"):
                matches.append(m)
    print(f"{len(matches)} completed ESPN matches in the tape window")
    print(f"  by league: {dict(Counter(m['league'] for m in matches))}")

    out, n_ev = [], 0
    for i, m in enumerate(matches):
        s = get(f"{SITE}/{m['league']}/summary", {"event": m["espn_id"]})
        if s is None or s.status_code != 200:
            continue
        try:
            d = s.json()
        except ValueError:
            continue
        ke = d.get("keyEvents") or []
        kick = None
        for e in ke:
            if (e.get("type") or {}).get("type") == "kickoff" and e.get("wallclock"):
                kick = e["wallclock"]
                break
        evs = []
        for e in ke:
            typ = (e.get("type") or {})
            txt = (typ.get("text") or "").lower()
            is_goal = bool(e.get("scoringPlay"))
            is_red = "red card" in txt
            if not (is_goal or is_red) or not e.get("wallclock"):
                continue
            evs.append({
                "kind": "red_card" if is_red else "goal",
                "detail": typ.get("text"),
                "wallclock": e["wallclock"],
                "minute": (e.get("clock") or {}).get("displayValue"),
                "team": ((e.get("team") or {}).get("displayName")),
            })
        n_ev += len(evs)
        out.append({"espn_id": m["espn_id"], "league": m["league"],
                    "date": m["date"], "home": m["home"], "away": m["away"],
                    "kickoff_wallclock": kick, "events": evs})
        if (i + 1) % 40 == 0:
            print(f"  {i+1}/{len(matches)} matches, {n_ev} events", flush=True)

    with open(os.path.join(DATA, "window_goals.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n{len(out)} matches, {n_ev} goal/red events with a wallclock")
    print(f"  goals: {sum(1 for m in out for e in m['events'] if e['kind']=='goal')}")
    print(f"  reds:  {sum(1 for m in out for e in m['events'] if e['kind']=='red_card')}")
    print("wrote data/window_goals.json")


if __name__ == "__main__":
    main()
