"""Run environment by ballpark, computed from this season's finished games.

This is NOT the published park factor. A real one adjusts for the fact that
each team plays half its games at home against a non-random schedule. What is
computed here is the plainer thing, stated plainly:

    park index = (mean total runs in games AT this venue)
               / (mean total runs in all games)

and alongside it the same quantity computed as a HOME/ROAD ratio per club,
which removes most of the schedule bias:

    ratio = (runs per game in that club's home games)
          / (runs per game in that club's road games)

Both are reported. Neither is a published number and neither is called one.
The `n` is attached to every row because with ~55 home games so far a park
index of 1.10 is well inside noise, and the decision rule in `mentalities.py`
uses the ratio only where n clears a pre-registered floor.

Free, from `statsapi.mlb.com`, which passes the robots gate.
"""
from __future__ import annotations

import json
import statistics
from datetime import date, datetime, timezone
from pathlib import Path

import statsapi as S

OUT = Path(__file__).resolve().parent.parent / "data" / "park_factors.json"
MIN_GAMES = 30            # pre-registered floor; below this the row is unusable


def season_games(season, through: date):
    start = date(season, 3, 1)
    js = S.get("/v1/schedule", ttl_s=3600, sportId=1,
               startDate=start.isoformat(), endDate=through.isoformat(),
               hydrate="linescore,venue,team", gameType="R")
    out = []
    for dd in js.get("dates", []):
        for g in dd.get("games", []):
            if (g.get("status") or {}).get("abstractGameState") != "Final":
                continue
            # REGULAR SEASON ONLY. Spring training is played in Arizona and
            # Florida heat with minor-league pitching and runs ~14 runs a
            # game; leaving it in pulled the league mean up and every real
            # ballpark's index down. gameType 'R' regular, 'S' spring,
            # 'E' exhibition, 'A' all-star, 'P/D/L/W' postseason.
            if g.get("gameType") != "R":
                continue
            ls = g.get("linescore") or {}
            t = ls.get("teams") or {}
            a = (t.get("away") or {}).get("runs")
            h = (t.get("home") or {}).get("runs")
            if a is None or h is None:
                continue
            out.append({
                "venue_id": (g.get("venue") or {}).get("id"),
                "venue": (g.get("venue") or {}).get("name"),
                "home_id": g["teams"]["home"]["team"]["id"],
                "away_id": g["teams"]["away"]["team"]["id"],
                "total": int(a) + int(h),
            })
    return out


def build(season=None, through=None):
    season = season or datetime.now(timezone.utc).year
    through = through or datetime.now(timezone.utc).date()
    games = season_games(season, through)
    if not games:
        return {"season": season, "games": 0, "venues": {}, "clubs": {}}
    league_mean = statistics.mean(g["total"] for g in games)

    by_venue, home_by_club, road_by_club = {}, {}, {}
    for g in games:
        by_venue.setdefault(g["venue_id"], {"name": g["venue"], "t": []})
        by_venue[g["venue_id"]]["t"].append(g["total"])
        home_by_club.setdefault(g["home_id"], []).append(g["total"])
        road_by_club.setdefault(g["away_id"], []).append(g["total"])

    venues = {}
    for vid, v in by_venue.items():
        n = len(v["t"])
        venues[str(vid)] = {
            "name": v["name"], "n": n,
            "runs_per_game": round(statistics.mean(v["t"]), 3),
            "park_index": round(statistics.mean(v["t"]) / league_mean, 4),
            "usable": n >= MIN_GAMES,
        }
    clubs = {}
    for cid, home in home_by_club.items():
        road = road_by_club.get(cid, [])
        if not road:
            continue
        hm, rm = statistics.mean(home), statistics.mean(road)
        clubs[str(cid)] = {
            "home_n": len(home), "road_n": len(road),
            "home_rpg": round(hm, 3), "road_rpg": round(rm, 3),
            "home_road_ratio": round(hm / rm, 4) if rm else None,
            "usable": len(home) >= MIN_GAMES and len(road) >= MIN_GAMES,
        }
    return {
        "season": season,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "through": through.isoformat(),
        "games": len(games),
        "league_runs_per_game": round(league_mean, 3),
        "min_games_floor": MIN_GAMES,
        "venues": venues, "clubs": clubs,
    }


def load(max_age_h=24):
    """Cached park factors, rebuilt if stale."""
    if OUT.exists():
        try:
            d = json.loads(OUT.read_text())
            t = datetime.fromisoformat(d["computed_at_utc"])
            age = (datetime.now(timezone.utc) - t).total_seconds() / 3600
            if age < max_age_h:
                return d
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    d = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, indent=2))
    return d


if __name__ == "__main__":
    d = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, indent=2))
    print(f"season {d['season']}, {d['games']} finished games, "
          f"league {d['league_runs_per_game']} runs/game")
    rows = sorted(d["venues"].items(), key=lambda kv: -kv[1]["park_index"])
    print(f"\n{'venue':<28} {'n':>4} {'rpg':>6} {'index':>7}  usable")
    for _, v in rows:
        print(f"{v['name'][:28]:<28} {v['n']:>4} {v['runs_per_game']:>6} "
              f"{v['park_index']:>7}  {'yes' if v['usable'] else 'NO'}")
    print(f"\nwrote {OUT}")
