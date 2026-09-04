"""Point-in-time fatigue/context features per team-game, from the cached schedule.

Mailbox 028: fill the 10 duplicate slots with ENTRY ideas that are genuinely
different from the current five (pitcher form, bullpen, park air, crude prior,
lineup absence). Nothing here touches pitching or price -- that is the point.

⚠ EVERY FEATURE IS BUILT FROM GAMES STRICTLY BEFORE THE ONE BEING SCORED.
The whole file walks the schedule forward and never looks at the current game's
result. That is the same discipline `records_before` needed, and the reason the
first replay was wrong.

Built from `replay_cache.db`, which already holds 2,241 games with venue
coordinates -- no new API calls, no new source, nothing to pay for.
"""
from __future__ import annotations

import collections
import json
import math
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import replay as R                                     # noqa: E402


def _haversine(a, b):
    """Great-circle miles between two (lat, lon) pairs."""
    if not a or not b:
        return None
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def build(con):
    """{game_pk: {side: {rest_days, travel_miles, ...}}}, no look-ahead."""
    games = []
    for r in con.execute(
            "SELECT game_pk, game_date, starts_utc, away_id, home_id, raw "
            "FROM game WHERE json_extract(raw,'$.gameType')='R' "
            "ORDER BY starts_utc"):
        try:
            d = json.loads(r["raw"])
        except Exception:                               # noqa: BLE001
            continue
        v = (d.get("venue") or {}).get("location", {}).get(
            "defaultCoordinates") or {}
        games.append({
            "pk": r["game_pk"], "date": r["game_date"],
            "starts": r["starts_utc"],
            "away": r["away_id"], "home": r["home_id"],
            "coord": ((v.get("latitude"), v.get("longitude"))
                      if v.get("latitude") is not None else None),
            "venue_id": (d.get("venue") or {}).get("id"),
            "day_night": d.get("dayNight"),
            "dh": d.get("doubleHeader"),
            "series_game": d.get("seriesGameNumber"),
            "series_len": d.get("gamesInSeries"),
        })

    # A stale cache does not error -- it just returns {} per game and every
    # schedule-reading strategy declines forever. Say so out loud instead.
    if games:
        newest = max(g["date"] for g in games)
        from datetime import date as _date
        try:
            gap = (_date.today() - _date.fromisoformat(newest)).days
            if gap > 2:
                print(f"  ! schedule cache is {gap} days stale (newest "
                      f"{newest}). `rested` and `travel` will decline every "
                      f"game until `python src/replay.py --build` is re-run.",
                      file=__import__("sys").stderr)
        except (TypeError, ValueError):
            pass

    last = {}                       # team -> the previous game it played
    out = {}
    for g in games:
        f = {}
        for side, tid in (("away", g["away"]), ("home", g["home"])):
            prev = last.get(tid)
            rest = travel = None
            prev_night_to_day = False
            if prev:
                try:
                    d0 = datetime.fromisoformat(prev["date"])
                    d1 = datetime.fromisoformat(g["date"])
                    rest = (d1 - d0).days
                except (TypeError, ValueError):
                    rest = None
                travel = _haversine(prev["coord"], g["coord"])
                prev_night_to_day = (prev["day_night"] == "night"
                                     and g["day_night"] == "day"
                                     and rest == 1)
            f[side] = {
                "rest_days": rest,
                "travel_miles": round(travel, 1) if travel is not None else None,
                "night_to_day": prev_night_to_day,
                "series_game": g["series_game"],
                "doubleheader": g["dh"] not in (None, "N"),
                "day_night": g["day_night"],
            }
        out[g["pk"]] = f
        for side, tid in (("away", g["away"]), ("home", g["home"])):
            last[tid] = g
    return out


if __name__ == "__main__":
    con = R.cache()
    f = build(con)
    print(f"features built for {len(f)} regular-season games\n")
    import statistics
    rest = [v[s]["rest_days"] for v in f.values() for s in ("away", "home")
            if v[s]["rest_days"] is not None]
    trav = [v[s]["travel_miles"] for v in f.values() for s in ("away", "home")
            if v[s]["travel_miles"]]
    print(f"rest days   : median {statistics.median(rest)}, "
          f"{sum(1 for x in rest if x == 1)} of {len(rest)} are back-to-back")
    print(f"travel miles: median {statistics.median(trav):.0f}, "
          f"max {max(trav):.0f}, "
          f"{sum(1 for x in trav if x > 1500)} trips over 1,500")
    nd = sum(1 for v in f.values() for s in ("away", "home")
             if v[s]["night_to_day"])
    print(f"night-then-day-next-day team-games: {nd}")
    con.close()
