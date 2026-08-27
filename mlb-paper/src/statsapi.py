"""MLB Stats API -- the whole free baseball side of the pre-match brief.

`statsapi.mlb.com` passes the robots gate (`reports/robots_policy.json`) and
needs no key. Everything the brief calls "baseball" comes from here:

    schedule + probable pitchers ....... a day ahead, verified 15 games
    pitcher game logs .................. every start, with PITCH COUNT
    boxscore ........................... battingOrder (9 ids) + bullpen roster
    standings .......................... W/L, and home/away split records
    venue .............................. lat/lon, ELEVATION, and azimuthAngle
    linescore .......................... per-inning runs -- the settlement label

Two things that were checked rather than assumed:

  * `gameData.weather` is `{}` before first pitch. It is populated at or after
    the game starts, so it is USELESS for a pre-match brief and the weather
    comes from `wx.py` instead. Verified on a live game 22 h out.
  * `venue.azimuthAngle` is published (PNC Park = 116.0). That is what turns a
    wind bearing into "blowing out to left" -- without it, wind speed alone is
    nearly meaningless for a total.

Nothing here writes. There is no order path in this package.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://statsapi.mlb.com/api"
UA = {"User-Agent": "trading-research/1.0 (personal research)"}
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"


def _get(url, tries=4, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:                       # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(1.5 * (2 ** i))
    raise RuntimeError(f"statsapi failed after {tries}: {url}: {last}")


def get(path, ttl_s=0, **params):
    """GET with an optional on-disk cache.

    ttl_s = 0 means never cache. Used for anything that changes inside a game
    day; a pitcher's career game log from three weeks ago is cached, today's
    boxscore never is.
    """
    q = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = f"{BASE}{path}" + (f"?{q}" if q else "")
    if ttl_s <= 0:
        return _get(url)
    CACHE.mkdir(parents=True, exist_ok=True)
    # NOTE: `hash()` on a str is SALTED PER PROCESS (PYTHONHASHSEED), so a
    # cache keyed on it never hits across runs -- it silently degrades to no
    # cache at all while looking like one. The first version of this did
    # exactly that and a second brief build cost the same 6 minutes as the
    # first. hashlib is stable across processes and machines.
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:20]
    f = CACHE / f"{key}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) < ttl_s:
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            pass
    d = _get(url)
    f.write_text(json.dumps(d))
    return d


# ------------------------------------------------------------------ schedule

SCHEDULE_HYDRATE = ("probablePitcher,linescore,team,venue(location,timezone),"
                    "game(content(summary)),seriesStatus")


def schedule(day: date | str):
    d = day if isinstance(day, str) else day.isoformat()
    js = get("/v1/schedule", sportId=1, date=d, hydrate=SCHEDULE_HYDRATE)
    out = []
    for dd in js.get("dates", []):
        for g in dd.get("games", []):
            out.append(g)
    return out


def games_between(start: date, end: date):
    js = get("/v1/schedule", sportId=1, startDate=start.isoformat(),
             endDate=end.isoformat(), hydrate=SCHEDULE_HYDRATE)
    out = []
    for dd in js.get("dates", []):
        out += dd.get("games", [])
    return out


# ------------------------------------------------------------------- pitcher

def pitcher_game_log(person_id, season):
    js = get(f"/v1/people/{person_id}/stats", ttl_s=3600,
             stats="gameLog", group="pitching", season=season)
    for s in js.get("stats", []):
        if s.get("type", {}).get("displayName") == "gameLog":
            return s.get("splits", [])
    return []


def pitcher_season(person_id, season):
    js = get(f"/v1/people/{person_id}/stats", ttl_s=3600,
             stats="season", group="pitching", season=season)
    for s in js.get("stats", []):
        sp = s.get("splits") or []
        if sp:
            return sp[0].get("stat", {})
    return {}


def _ip(x):
    """'5.2' innings pitched -> 5.667. Baseball's decimal is thirds."""
    try:
        whole, _, frac = str(x).partition(".")
        return int(whole) + (int(frac or 0) / 3.0)
    except (TypeError, ValueError):
        return 0.0


def starter_profile(person_id, season, as_of: datetime, last_n=3):
    """The last N STARTS and rest days strictly before `as_of` -- and season
    aggregates that are NOT, which is a trap. Read the warning.

    ⚠ `season_era`, `season_ip`, `season_starts` and `season_whip` come from
    `pitcher_season()`, which returns the WHOLE season. They are **not**
    filtered by `as_of`, despite what this docstring said until 2026-08-26.

    **Live that is harmless and correct** -- when the bot runs on the day of the
    game, "the season so far" IS the point-in-time value.

    **In a REPLAY it is a look-ahead leak, and a big one.** Measured on games of
    2026-06-10: pitcher 453286 is handed **7.02** when his real ERA that day was
    **9.64**; pitcher 592662 is handed **3.21** against a real **4.12**. A
    backtest using these is being told how the rest of the summer went.

    `season_era_asof` and `season_ip_asof` are computed from the game log with
    the same date cut as everything else and are the ones a replay must use.
    The unfiltered fields are left in place deliberately so that the live
    forward test's behaviour does not change in the middle of the experiment.

    The date filter is the whole point. `phatcobra/nrfi-predictor`'s own
    docstring is the rule worth stealing: *"Per-game windows use only rows
    strictly before game_date. Missing observations remain missing; they are
    never converted into zero-valued outcomes."* This function returns None for
    an absent quantity and never 0.0.
    """
    if not person_id:
        return None
    log = pitcher_game_log(person_id, season)
    cut = as_of.date()
    prior = []
    for s in log:
        try:
            gd = date.fromisoformat(s["date"])
        except (KeyError, ValueError):
            continue
        if gd < cut:
            prior.append((gd, s))
    prior.sort(key=lambda x: x[0])
    starts = [(d, s) for d, s in prior
              if int(s.get("stat", {}).get("gamesStarted", 0) or 0) > 0]
    season_stat = pitcher_season(person_id, season)

    recent = starts[-last_n:] if starts else []
    rec_ip = sum(_ip(s["stat"].get("inningsPitched")) for _, s in recent)
    rec_er = sum(int(s["stat"].get("earnedRuns", 0) or 0) for _, s in recent)
    rec_k = sum(int(s["stat"].get("strikeOuts", 0) or 0) for _, s in recent)
    rec_bb = sum(int(s["stat"].get("baseOnBalls", 0) or 0) for _, s in recent)

    # season to date, computed from the log with the SAME cut -- see the
    # warning above. `prior` already excludes anything on or after `as_of`.
    a_er = sum(int(s["stat"].get("earnedRuns", 0) or 0) for _, s in prior)
    a_ip = sum(_ip(s["stat"].get("inningsPitched")) for _, s in prior)

    return {
        "person_id": person_id,
        "season_era_asof": round(9.0 * a_er / a_ip, 2) if a_ip > 0 else None,
        "season_ip_asof": round(a_ip, 2) if a_ip > 0 else None,
        "season_era": _f(season_stat.get("era")),
        "season_ip": _ip(season_stat.get("inningsPitched")) or None,
        "season_starts": _i(season_stat.get("gamesStarted")),
        "season_whip": _f(season_stat.get("whip")),
        "career_starts_prior": len(starts),
        "is_debut_or_near": len(starts) < 3,
        "last_start_date": starts[-1][0].isoformat() if starts else None,
        "rest_days": (cut - starts[-1][0]).days if starts else None,
        "last_start_pitches": _i(starts[-1][1]["stat"].get("numberOfPitches"))
                              if starts else None,
        "recent_n": len(recent),
        "recent_ip": round(rec_ip, 2) if recent else None,
        "recent_era": round(9.0 * rec_er / rec_ip, 2) if rec_ip > 0 else None,
        "recent_k9": round(9.0 * rec_k / rec_ip, 2) if rec_ip > 0 else None,
        "recent_bb9": round(9.0 * rec_bb / rec_ip, 2) if rec_ip > 0 else None,
    }


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _i(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------- bullpen

def boxscore(game_pk, ttl_s=0):
    """ttl_s > 0 only for FINAL games -- a finished boxscore never changes.

    Without this, one call to bullpen_load() costs ~11 boxscores per team, and
    building 15 briefs costs ~900 requests against a public API that is being
    used politely. With it, the second build of the day costs almost nothing.
    A LIVE game must always pass ttl_s=0.
    """
    return get(f"/v1/game/{game_pk}/boxscore", ttl_s=ttl_s)


def linescore(game_pk, ttl_s=0):
    return get(f"/v1/game/{game_pk}/linescore", ttl_s=ttl_s)


def bullpen_load(team_id, season, as_of: datetime, days=3, lookback_days=10):
    """Days of rest and rolling pitch load for a team's relievers.

    Computed from prior boxscores only. A team with no prior game in the window
    returns `games_seen = 0` and every load field None -- NOT zero. Zero would
    read as "fully rested" and is the exact substitution
    `phatcobra/nrfi-predictor` refuses to make.
    """
    end = as_of.date() - timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    try:
        js = get("/v1/schedule", sportId=1, teamId=team_id,
                 startDate=start.isoformat(), endDate=end.isoformat(),
                 ttl_s=1800)
    except RuntimeError:
        return {"games_seen": 0}
    pks = []
    for dd in js.get("dates", []):
        for g in dd.get("games", []):
            if (g.get("status", {}).get("abstractGameState")) == "Final":
                pks.append((dd["date"], g["gamePk"]))
    if not pks:
        return {"games_seen": 0}

    last_app, pitches = {}, {}
    innings_by_pen = 0.0
    extra_inning_games = 0
    for day_s, pk in pks:
        try:
            bs = boxscore(pk, ttl_s=86400 * 14)
        except RuntimeError:
            continue
        try:
            gd = date.fromisoformat(day_s)
        except ValueError:
            continue
        for side in ("home", "away"):
            t = bs["teams"][side]
            if t["team"]["id"] != team_id:
                continue
            pen = set(t.get("bullpen") or [])
            # `pitchers` is in APPEARANCE ORDER, so index 0 is the starter.
            # Anyone after the first, or anyone on the bullpen roster, is a
            # reliever. Using the bullpen roster alone misses an opener.
            order = list(t.get("pitchers") or [])
            for idx, pid in enumerate(order):
                pl = (t.get("players") or {}).get(f"ID{pid}", {})
                st = (pl.get("stats") or {}).get("pitching") or {}
                np_ = _i(st.get("pitchesThrown")) or _i(st.get("numberOfPitches"))
                is_reliever = idx > 0 or pid in pen
                if not is_reliever:
                    continue
                last_app[pid] = max(last_app.get(pid, gd), gd)
                if gd >= end - timedelta(days=days - 1) and np_:
                    pitches[pid] = pitches.get(pid, 0) + np_
                if np_:
                    innings_by_pen += _ip(st.get("inningsPitched"))
    # extra innings: cheap, one linescore per prior game
    for day_s, pk in pks[-4:]:
        try:
            ls = linescore(pk, ttl_s=86400 * 14)
        except RuntimeError:
            continue
        if _i(ls.get("currentInning")) and _i(ls.get("currentInning")) > 9:
            extra_inning_games += 1

    cut = as_of.date()
    rest = {pid: (cut - d).days for pid, d in last_app.items()}
    used_yesterday = sum(1 for v in rest.values() if v <= 1)
    used_2of3 = sum(1 for pid, v in rest.items() if v <= 3 and
                    pitches.get(pid, 0) >= 25)
    total_recent_pitches = sum(pitches.values()) or None
    return {
        "games_seen": len(pks),
        "relievers_seen": len(rest),
        "relievers_used_yesterday": used_yesterday,
        "relievers_heavy_last3": used_2of3,
        "bullpen_pitches_last3": total_recent_pitches,
        "bullpen_innings_lookback": round(innings_by_pen, 1) or None,
        "extra_inning_games_last4": extra_inning_games,
    }


# ------------------------------------------------------------------ standings

def standings(season):
    js = get("/v1/standings", ttl_s=3600, leagueId="103,104", season=season,
             standingsTypes="byDivision", hydrate="team")
    out = {}
    for rec in js.get("records", []):
        for tr in rec.get("teamRecords", []):
            tid = tr["team"]["id"]
            splits = {}
            for sr in ((tr.get("records") or {}).get("splitRecords") or []):
                splits[sr.get("type")] = (sr.get("wins"), sr.get("losses"))
            last10 = None
            for sr in ((tr.get("records") or {}).get("splitRecords") or []):
                if sr.get("type") == "lastTen":
                    last10 = (sr.get("wins"), sr.get("losses"))
            out[tid] = {
                "name": tr["team"]["name"],
                "wins": tr.get("wins"), "losses": tr.get("losses"),
                "pct": _f(tr.get("winningPercentage")),
                "run_diff": _i(tr.get("runDifferential")),
                "runs_scored": _i(tr.get("runsScored")),
                "runs_allowed": _i(tr.get("runsAllowed")),
                "home": splits.get("home"), "away": splits.get("away"),
                "last_ten": last10,
                "streak": (tr.get("streak") or {}).get("streakCode"),
            }
    return out


# --------------------------------------------------------------------- venue

def venue(venue_id):
    js = get(f"/v1/venues/{venue_id}", ttl_s=86400 * 30,
             hydrate="location,fieldInfo,timezone")
    v = (js.get("venues") or [{}])[0]
    loc = v.get("location") or {}
    coords = loc.get("defaultCoordinates") or {}
    fi = v.get("fieldInfo") or {}
    return {
        "id": venue_id, "name": v.get("name"),
        "lat": coords.get("latitude"), "lon": coords.get("longitude"),
        "elevation_ft": loc.get("elevation"),
        "azimuth_deg": loc.get("azimuthAngle"),
        "roof": fi.get("roofType"),
        "lf": fi.get("leftLine"), "cf": fi.get("center"),
        "rf": fi.get("rightLine"),
        "city": loc.get("city"), "state": loc.get("stateAbbrev"),
    }


# ------------------------------------------------------------------ lineups

def lineup(game_pk):
    """battingOrder for both sides, or None where the card is not posted yet.

    Lineups are LIVE-ONLY -- 0 of 8 games had one a day ahead when
    mlb/PROGRESS.md measured it, and they cannot be backfilled. An empty list
    here means "not posted", which is information, not a failure.
    """
    bs = boxscore(game_pk)
    out = {}
    for side in ("home", "away"):
        t = bs["teams"][side]
        order = [int(x) for x in (t.get("battingOrder") or [])]
        names = []
        for pid in order:
            pl = (t.get("players") or {}).get(f"ID{pid}", {})
            names.append((pid, (pl.get("person") or {}).get("fullName")))
        out[side] = {"posted": bool(order), "order": names,
                     "team_id": t["team"]["id"]}
    return out


def team_roster_ops(team_id, season, top_n=5):
    """The team's top-N regulars by season OPS -- the yardstick for 'who is
    missing from tonight's card'."""
    js = get(f"/v1/teams/{team_id}/roster", ttl_s=86400,
             rosterType="active",
             hydrate=f"person(stats(type=season,season={season},group=hitting))")
    rows = []
    for r in js.get("roster", []):
        p = r.get("person") or {}
        for s in (p.get("stats") or []):
            for sp in (s.get("splits") or []):
                st = sp.get("stat") or {}
                pa = _i(st.get("plateAppearances")) or 0
                ops = _f(st.get("ops"))
                if ops is not None and pa >= 100:
                    rows.append({"id": p.get("id"), "name": p.get("fullName"),
                                 "ops": ops, "pa": pa})
    rows.sort(key=lambda x: -x["ops"])
    return rows[:top_n]


# --------------------------------------------------------------- settlement

def final_score(game_pk):
    """(away_runs, home_runs, first_inning_runs_total) or None if not final."""
    ls = linescore(game_pk)
    t = ls.get("teams") or {}
    away, home = (t.get("away") or {}), (t.get("home") or {})
    ar, hr = _i(away.get("runs")), _i(home.get("runs"))
    if ar is None or hr is None:
        return None
    innings = ls.get("innings") or []
    fi = None
    if innings:
        i1 = innings[0]
        fi = (_i((i1.get("away") or {}).get("runs")) or 0) + \
             (_i((i1.get("home") or {}).get("runs")) or 0)
    return {"away_runs": ar, "home_runs": hr, "total_runs": ar + hr,
            "first_inning_runs": fi,
            "is_final": (ls.get("currentInningOrdinal") is not None
                         and _i(ls.get("currentInning") or 0) >= 9)}


if __name__ == "__main__":
    today = datetime.now(timezone.utc).date()
    gs = schedule(today + timedelta(days=1))
    print(f"tomorrow: {len(gs)} games")
    g = gs[0]
    print(g["gamePk"], g["gameDate"],
          g["teams"]["away"]["team"]["name"], "@",
          g["teams"]["home"]["team"]["name"])
    v = venue(g["venue"]["id"])
    print("venue:", v)
    pp = (g["teams"]["home"].get("probablePitcher") or {})
    print("home probable:", pp.get("fullName"))
    if pp.get("id"):
        import pprint
        pprint.pprint(starter_profile(
            pp["id"], 2026,
            datetime.fromisoformat(g["gameDate"].replace("Z", "+00:00"))))
    print("bullpen:", bullpen_load(g["teams"]["home"]["team"]["id"], 2026,
                                   datetime.now(timezone.utc)))
