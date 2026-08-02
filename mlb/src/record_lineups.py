"""Live lineup scanner: poll until teams post their batting order.

NOTE ON PRIORITY. This does NOT block backtesting. Historical batting orders
are available for every past game from `/game/{pk}/boxscore`, so the model can
be built and tested today. This recorder exists for two narrower reasons:

  1. live trading later needs the lineup at decision time, not after
  2. a past boxscore reports who BATTED, which can include substitutes. For
     the first inning that is almost always the announced starters, but
     "almost always" is an assumption and this recorder is what lets it be
     measured -- capture the announced lineup live, compare it later to the
     boxscore, and quantify the disagreement.

Measured 2026-08-02: 0 of 8 games had a lineup a day ahead; 7 of 8 had a
probable pitcher. So lineups land inside a few hours of first pitch.

Content-validated per row. Paced, read-only, public. No credentials.
"""
import datetime as dt
import json
import pathlib
import sys
import time
from collections import Counter

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lineups"
API = "https://statsapi.mlb.com/api/v1"
UA = {"User-Agent": "mlb-research/1.0"}
CYCLE = 300          # 5 minutes
PACE = 0.3


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(m):
    print(f"[{now():%Y-%m-%d %H:%M:%S}] {m}", flush=True)


def get(path, params=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(f"{API}/{path}", params=params, headers=UA,
                             timeout=40)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3 * (i + 1))
            continue
        time.sleep(PACE)
        return r
    return None


def todays_games():
    t = now()
    out = []
    for off in (0, 1):
        d = (t + dt.timedelta(days=off)).strftime("%Y-%m-%d")
        r = get("schedule", {"sportId": 1, "date": d,
                             "hydrate": "probablePitcher,lineups,venue"})
        if r is None or r.status_code != 200:
            continue
        for day in r.json().get("dates", []):
            for g in day.get("games", []):
                st = ((g.get("status") or {}).get("abstractGameState"))
                if st == "Final":
                    continue
                out.append(g)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cycle, tot = 0, Counter()
    log("MLB lineup scanner starting -- polls until batting orders appear")
    while True:
        cycle += 1
        t0 = time.time()
        try:
            games = todays_games()
        except Exception as e:  # noqa: BLE001
            log(f"schedule failed: {type(e).__name__}: {e}")
            time.sleep(120)
            continue
        t = now()
        d = OUT / f"{t:%Y-%m-%d}"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "lineups.jsonl"
        cyc = Counter()
        with open(path, "a", encoding="utf-8", buffering=1) as fh:
            for g in games:
                fetched = now()          # stamped AT FETCH (CH031)
                pk = g.get("gamePk")
                if not pk:
                    cyc["missing_key_field"] += 1
                    continue
                try:
                    ko = dt.datetime.fromisoformat(
                        g["gameDate"].replace("Z", "+00:00"))
                    hrs = (ko - fetched).total_seconds() / 3600.0
                except Exception:  # noqa: BLE001
                    ko, hrs = None, None
                lu = g.get("lineups") or {}
                home_lu = [p.get("id") for p in (lu.get("homePlayers") or [])]
                away_lu = [p.get("id") for p in (lu.get("awayPlayers") or [])]
                teams = g.get("teams") or {}

                def pp(side):
                    p = ((teams.get(side) or {}).get("probablePitcher") or {})
                    return {"id": p.get("id"), "name": p.get("fullName")}

                row = {
                    "fetched_at": fetched.isoformat(),
                    "game_pk": pk, "game_date": g.get("gameDate"),
                    "hours_to_first_pitch": round(hrs, 3) if hrs is not None else None,
                    "status": ((g.get("status") or {}).get("abstractGameState")),
                    "venue": ((g.get("venue") or {}).get("name")),
                    "home_team": (((teams.get("home") or {}).get("team") or {})
                                  .get("name")),
                    "away_team": (((teams.get("away") or {}).get("team") or {})
                                  .get("name")),
                    "home_probable": pp("home"), "away_probable": pp("away"),
                    "home_lineup_ids": home_lu, "away_lineup_ids": away_lu,
                    "n_home_lineup": len(home_lu), "n_away_lineup": len(away_lu),
                    "lineups_posted": len(home_lu) >= 9 and len(away_lu) >= 9,
                }
                if not row["game_pk"] or not row["fetched_at"]:
                    cyc["missing_key_field"] += 1
                    continue
                fh.write(json.dumps(row) + "\n")
                cyc["rows"] += 1
                if row["lineups_posted"]:
                    cyc["with_lineup"] += 1
                if row["home_probable"]["id"]:
                    cyc["with_probable"] += 1
        for k, v in cyc.items():
            tot[k] += v
        log(f"cycle {cycle}: {cyc['rows']} games in {time.time()-t0:.0f}s | "
            f"lineups {cyc['with_lineup']} | probables {cyc['with_probable']} "
            f"| bad {cyc['missing_key_field']}")
        if cycle % 12 == 0:
            log(f"HEALTH {cycle} cycles: {dict(tot)}")
            if tot["rows"] > 100 and tot["with_lineup"] == 0:
                log("WARNING: no lineup captured yet. Either no game has come "
                    "within a few hours of first pitch, or the `lineups` "
                    "hydrate is not populating. Check before trusting.")
        time.sleep(max(30, CYCLE - (time.time() - t0)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
