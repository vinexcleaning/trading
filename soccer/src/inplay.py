"""TASK 1: what the Kalshi price does around goals and red cards.

DESCRIPTIVE ONLY. No entry rules, no strategy, no edge claims.

Method
------
For every matched, completed fixture:
  * pull the ESPN summary -> keyEvents, each carrying a WALLCLOCK timestamp
  * pull Kalshi 1-minute candlesticks for all three 3-way markets over
    [kickoff-60min, kickoff+200min]
  * for each goal / red card, read the price of the SCORING (or offending)
    team's own contract at T-5, T-1, T, T+1, T+3, T+5, T+10 minutes

THE CLOCK PROBLEM, MEASURED RATHER THAN ASSUMED
The tasking warns that ESPN match minutes and Kalshi wall clock are different
clocks and that stoppage time makes the mapping non-linear. That is true of the
DISPLAYED MINUTE -- but ESPN also publishes `wallclock`, an absolute UTC
instant, on every keyEvent, and `wallclockAvailable` is true. So no mapping is
needed and no alignment error is introduced. This script measures the
minute-vs-wallclock divergence anyway, to document how wrong a minute-based
join would have been.

PRICE CONVENTION
Candles carry `yes_bid` and `yes_ask` OHLC in `*_dollars`. The event study
reports the MID for describing movement, and reports the spread alongside so
the executable move is never overstated (GUARDS #7: fill at the ask, never the
mid). No P&L is computed anywhere in this file.
"""
import json
import os
import statistics as st
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "market-selection", "src"))
import kalshi_api as K  # noqa: E402
import teammatch as TM  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

OFFSETS = [-5, -1, 0, 1, 3, 5, 10]
GOAL_TYPES = {"goal", "penalty-goal", "own-goal"}


def espn_summary(league, eid, tries=3):
    for i in range(tries):
        try:
            r = requests.get(f"{SITE}/{league}/summary", params={"event": eid},
                             headers=UA, timeout=45)
        except requests.RequestException:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2.5 * (i + 1))
            continue
        time.sleep(0.15)
        return r.json() if r.status_code == 200 else None
    return None


def candles(series, ticker, t0, t1):
    """1-minute candles -> {minute_ts: {'bid':c,'ask':c,'mid':c,'vol':v}}."""
    r = K.get(f"/series/{series}/markets/{ticker}/candlesticks",
              {"start_ts": int(t0.timestamp()), "end_ts": int(t1.timestamp()),
               "period_interval": 1})
    if r is None or r.status_code != 200:
        return {}
    out = {}
    for c in r.json().get("candlesticks", []):
        ts = c.get("end_period_ts")
        yb = ((c.get("yes_bid") or {}).get("close_dollars"))
        ya = ((c.get("yes_ask") or {}).get("close_dollars"))
        b = None if yb is None else float(yb) * 100
        a = None if ya is None else float(ya) * 100
        if b is None and a is None:
            continue
        # Kalshi reports an empty side as bid 0 / ask 100
        bb = b if (b is not None and b > 0) else None
        aa = a if (a is not None and a < 100) else None
        mid = ((bb + aa) / 2 if bb is not None and aa is not None
               else (bb if bb is not None else aa))
        out[ts] = {"bid": bb, "ask": aa, "mid": mid,
                   "spread": (aa - bb) if (bb is not None and aa is not None) else None,
                   "vol": float(c.get("volume_fp") or 0)}
    return out


def at(series_map, ts, tol=90):
    """Price at (or nearest within tol seconds before) a wall-clock instant."""
    best, bestd = None, None
    for k, v in series_map.items():
        d = ts - k
        if -60 <= d <= tol:
            ad = abs(d)
            if bestd is None or ad < bestd:
                best, bestd = v, ad
    return best


def main():
    join = json.load(open(os.path.join(DATA, "join.json"), encoding="utf-8"))
    fx = [f for f in join["matched"] if f.get("espn_completed")]
    print(f"completed matched fixtures: {len(fx)}")

    rows = []          # one row per (event, market-side)
    clock_err = []     # minute-implied vs wallclock divergence
    per_fixture = []
    n_no_candle = n_no_summary = 0

    for i, f in enumerate(fx):
        s = espn_summary(f["espn_league"], f["espn_id"])
        if not s:
            n_no_summary += 1
            continue
        ke = s.get("keyEvents") or []
        kick = None
        for e in ke:
            if (e.get("type") or {}).get("type") == "kickoff" and e.get("wallclock"):
                kick = datetime.fromisoformat(e["wallclock"].replace("Z", "+00:00"))
                break
        if kick is None:
            continue

        # candles for all three legs
        t0, t1 = kick - timedelta(minutes=60), kick + timedelta(minutes=200)
        legs = {}
        for m in f["markets"]:
            c = candles(f["series"], m["ticker"], t0, t1)
            if c:
                legs[m["yes_sub"]] = {"ticker": m["ticker"], "candles": c,
                                      "result": m.get("result")}
        if not legs:
            n_no_candle += 1
            continue

        # pre-match favourite: highest mid at kickoff-5min among non-Tie legs
        pre = {}
        for sub, L in legs.items():
            p = at(L["candles"], int((kick - timedelta(minutes=5)).timestamp()))
            pre[sub] = p["mid"] if p else None
        team_legs = {k: v for k, v in pre.items()
                     if k and k.lower() not in ("tie", "draw") and v is not None}
        fav = max(team_legs, key=team_legs.get) if team_legs else None

        n_ev = 0
        for e in ke:
            typ = (e.get("type") or {})
            tt = (typ.get("type") or "").lower()
            txt = (typ.get("text") or "").lower()
            is_goal = bool(e.get("scoringPlay")) or tt in GOAL_TYPES
            is_red = "red card" in txt
            if not (is_goal or is_red):
                continue
            wc = e.get("wallclock")
            if not wc:
                continue
            ts = int(datetime.fromisoformat(wc.replace("Z", "+00:00")).timestamp())

            # clock divergence: what the displayed minute would have implied
            disp = (e.get("clock") or {}).get("displayValue") or ""
            mins = None
            if disp:
                base = disp.split("'")[0]
                try:
                    mins = int(base)
                    if "+" in disp:
                        mins += int(disp.split("+")[1].strip("' "))
                except ValueError:
                    mins = None
            if mins is not None:
                implied = int((kick + timedelta(minutes=mins)).timestamp())
                clock_err.append((implied - ts) / 60.0)

            team = ((e.get("team") or {}).get("displayName")
                    or (e.get("team") or {}).get("abbreviation"))
            # which Kalshi leg belongs to that team?
            leg_sub = None
            if team:
                for sub in legs:
                    if sub and sub.lower() not in ("tie", "draw") and \
                            TM.canon(sub) == TM.canon(team):
                        leg_sub = sub
                        break
            if leg_sub is None:
                continue
            L = legs[leg_sub]
            px = {}
            for off in OFFSETS:
                p = at(L["candles"], ts + off * 60)
                px[off] = p
            if px.get(0) is None or px.get(-1) is None:
                continue
            n_ev += 1
            rows.append({
                "series": f["series"], "league": f["espn_league"],
                "espn_id": f["espn_id"], "date": f["espn_date"],
                "event_type": "red_card" if is_red else "goal",
                "detail": typ.get("text"),
                "team": team, "leg": leg_sub,
                "is_favourite": (leg_sub == fav) if fav else None,
                "pre_price_c": pre.get(leg_sub),
                "minute": disp, "wallclock": wc,
                "prices": {str(k): (v["mid"] if v else None) for k, v in px.items()},
                "spreads": {str(k): (v["spread"] if v else None) for k, v in px.items()},
                "result": L["result"],
            })
        per_fixture.append({"espn_id": f["espn_id"], "n_events": n_ev,
                            "legs": len(legs), "fav": fav})
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(fx)} fixtures, {len(rows)} events", flush=True)

    with open(os.path.join(DATA, "inplay_events.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"rows": rows, "clock_err_min": clock_err,
                   "per_fixture": per_fixture,
                   "n_no_summary": n_no_summary,
                   "n_no_candle": n_no_candle}, fh, indent=1)
    print(f"\nfixtures with no ESPN summary: {n_no_summary}")
    print(f"fixtures with no candles:      {n_no_candle}")
    print(f"events captured:               {len(rows)}")
    print(f"  goals     {sum(1 for r in rows if r['event_type']=='goal')}")
    print(f"  red cards {sum(1 for r in rows if r['event_type']=='red_card')}")
    if clock_err:
        ce = sorted(clock_err)
        print(f"\nCLOCK DIVERGENCE (minute-implied minus true wallclock), n={len(ce)}")
        print(f"  median {ce[len(ce)//2]:+.2f} min   p10 {ce[int(len(ce)*.1)]:+.2f}"
              f"   p90 {ce[int(len(ce)*.9)]:+.2f}   min {ce[0]:+.2f}   max {ce[-1]:+.2f}")
        print(f"  |error| > 2 min on {100*sum(1 for x in ce if abs(x)>2)/len(ce):.1f}% of events")


if __name__ == "__main__":
    main()
