"""TASK 3: record the pre-match state that cannot be backfilled.

WHY THIS EXISTS. Measured 2026-08-02 against live fixtures:

    T-145h, T-7.3h, T-5.3h, T-3.0h : rosters present but EMPTY
                                     (players=0, starters=0, formation=None),
                                     no officials, odds present (1 block)
    T-0.2h                         : players=46, starters=22,
                                     formations ['3-4-2-1','4-2-3-1'],
                                     officials ['Luis Medina'], odds 3 blocks

So the announced XI, the formation and the referee all appear roughly an hour
before kickoff. After the match the same endpoint shows who ACTUALLY PLAYED,
substitutes included -- which is a different fact, and using it as if it were
the pre-match lineup is a look-ahead leak of the same family as LEDGER T010.

There is no historical endpoint for "what was announced at T-60min". It exists
only in wall-clock time. Hence this recorder.

Also captures odds drift, which is live-only in the same sense: the archived
summary keeps a closing value, not the path.

CONTENT VALIDATION PER ROW, not row counts (GUARDS #12). Every snapshot is
checked for a parseable event id, a fetch timestamp, and at least one populated
block before it is written; counters distinguish "fetched but still empty"
(expected far from kickoff) from "fetch failed".

`fetched_at` is stamped THE MOMENT THE RESPONSE RETURNS, never at cache read.
CH031 is the bug where a staleness guard never fired because the timestamp was
applied at the wrong point.

Read-only, paced, public. No credentials.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import time
from collections import Counter

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "prematch"
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
# ESPN (Akamai) began returning 403 to any Mozilla/... or unknown custom
# User-Agent on 2026-08-08. Measured: "Mozilla/5.0 (soccer-research/1.0)"
# -> 403, "soccer-research/1.0" -> 403, curl/8.4.0 -> 200, requests' own
# default -> 200. Sending no override is what works; do not "fix" this by
# adding a browser string back.
UA = {}
LEAGUES = ["mex.1", "arg.1", "col.1", "bra.1", "usa.1"]

CYCLE_SEC = 600          # every 10 minutes
LOOKAHEAD_H = 8          # fixtures kicking off within this many hours
PACE = 0.35


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(m):
    print(f"[{now():%Y-%m-%d %H:%M:%S}] {m}", flush=True)


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=40)
        except requests.RequestException:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2.5 * (i + 1))
            continue
        time.sleep(PACE)
        return r
    return None


def upcoming():
    """Fixtures kicking off within LOOKAHEAD_H, plus any in progress."""
    t = now()
    out = []
    for lg in LEAGUES:
        r = get(f"{SITE}/{lg}/scoreboard",
                {"dates": f"{t:%Y%m%d}-{(t + dt.timedelta(days=2)):%Y%m%d}",
                 "limit": 300})
        if r is None or r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            st = ((e.get("status") or {}).get("type") or {})
            if st.get("completed"):
                continue
            try:
                ko = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                continue
            hrs = (ko - t).total_seconds() / 3600.0
            if -3.5 <= hrs <= LOOKAHEAD_H:
                out.append((lg, e["id"], e.get("name"), ko, hrs))
    return out


def snapshot(lg, eid, name, ko, hrs):
    r = get(f"{SITE}/{lg}/summary", {"event": eid})
    fetched = now()                       # stamped AT FETCH, not at parse
    if r is None or r.status_code != 200:
        return None, "http_fail"
    try:
        d = r.json()
    except ValueError:
        return None, "unparseable"

    ros = d.get("rosters") or []
    rosters = []
    for x in ros:
        players = []
        for p in (x.get("roster") or []):
            ath = p.get("athlete") or {}
            players.append({
                "id": ath.get("id"), "name": ath.get("displayName"),
                "starter": p.get("starter"),
                "pos": ((p.get("position") or {}).get("abbreviation")),
                "jersey": p.get("jersey"),
            })
        rosters.append({
            "team": ((x.get("team") or {}).get("displayName")),
            "homeAway": x.get("homeAway"),
            "formation": x.get("formation"),
            "n_players": len(players),
            "n_starters": sum(1 for p in players if p.get("starter")),
            "players": players,
        })

    odds = []
    for o in (d.get("odds") or []):
        odds.append({
            "provider": ((o.get("provider") or {}).get("name")),
            "details": o.get("details"),
            "overUnder": o.get("overUnder"),
            "home_ml": ((o.get("homeTeamOdds") or {}).get("moneyLine")),
            "away_ml": ((o.get("awayTeamOdds") or {}).get("moneyLine")),
            "draw_ml": ((o.get("drawOdds") or {}).get("moneyLine")
                        if isinstance(o.get("drawOdds"), dict)
                        else o.get("drawOdds")),
        })

    gi = d.get("gameInfo") or {}
    row = {
        "fetched_at": fetched.isoformat(),
        "league": lg, "event_id": eid, "event_name": name,
        "kickoff": ko.isoformat(), "hours_to_kickoff": round(hrs, 3),
        "status": (((d.get("header") or {}).get("competitions") or [{}])[0]
                   .get("status", {}).get("type", {}).get("name")),
        "rosters": rosters,
        "n_starters_total": sum(r["n_starters"] for r in rosters),
        "formations": [r["formation"] for r in rosters],
        "officials": [o.get("displayName") for o in (gi.get("officials") or [])],
        "venue": ((gi.get("venue") or {}).get("fullName")),
        "odds": odds,
        "n_key_events": len(d.get("keyEvents") or []),
    }
    # ---- content validation, per row
    if not row["event_id"] or not row["fetched_at"]:
        return None, "missing_key_field"
    if not (row["rosters"] or row["odds"]):
        return row, "empty_but_valid"
    return row, "ok"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cycle = 0
    tot = Counter()
    log(f"pre-match recorder starting -- {len(LEAGUES)} leagues, "
        f"lookahead {LOOKAHEAD_H}h, cycle {CYCLE_SEC}s, read-only")
    while True:
        cycle += 1
        t0 = time.time()
        try:
            fx = upcoming()
        except Exception as e:  # noqa: BLE001
            log(f"fixture list failed: {type(e).__name__}: {e}")
            time.sleep(120)
            continue
        cyc = Counter()
        t = now()
        d = OUT / f"{t:%Y-%m-%d}"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "prematch.jsonl"
        with open(path, "a", encoding="utf-8", buffering=1) as fh:
            for lg, eid, name, ko, hrs in fx:
                row, verdict = snapshot(lg, eid, name, ko, hrs)
                cyc[verdict] += 1
                if row is not None:
                    fh.write(json.dumps(row) + "\n")
                    if row["n_starters_total"] >= 20:
                        cyc["with_lineup"] += 1
                    if row["officials"]:
                        cyc["with_referee"] += 1
        for k, v in cyc.items():
            tot[k] += v
        log(f"cycle {cycle}: {len(fx)} fixtures in {time.time()-t0:.0f}s | "
            f"ok={cyc['ok']} empty={cyc['empty_but_valid']} "
            f"lineups={cyc['with_lineup']} refs={cyc['with_referee']} "
            f"fail={cyc['http_fail']+cyc['unparseable']+cyc['missing_key_field']}"
            f" -> {path.parent.name}")
        if cycle % 6 == 0:
            log(f"HEALTH after {cycle} cycles: {dict(tot)}")
            if tot["ok"] + tot["empty_but_valid"] > 50 and tot["with_lineup"] == 0:
                log("WARNING: no lineup has EVER been captured. Either no "
                    "fixture has come within ~1h of kickoff yet, or the roster "
                    "parse is broken. Check before trusting this data.")
        time.sleep(max(30, CYCLE_SEC - (time.time() - t0)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
