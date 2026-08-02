"""What exactly is in ESPN's keyEvents, and is there a WALL CLOCK?

The clock problem the tasking flags is real: ESPN stamps match minutes, Kalshi
stamps wall clock, and stoppage time makes the mapping non-linear. But the
summary payload advertises `wallclockAvailable`, which would make the mapping
exact rather than estimated. Worth knowing before building any alignment.
"""
import json
import os

import requests

UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SUM = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary"

r = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard",
                 params={"dates": "20260720-20260802"}, headers=UA, timeout=45)
evs = [e for e in r.json().get("events", [])
       if (e.get("status") or {}).get("type", {}).get("completed")]
print(f"completed mex.1 matches in the window: {len(evs)}")
eid = evs[0]["id"]
print(f"using event {eid}: {evs[0].get('name')}  date={evs[0].get('date')}")

d = requests.get(SUM, params={"event": eid}, headers=UA, timeout=45).json()
print(f"\nwallclockAvailable = {d.get('wallclockAvailable')}")

ke = d.get("keyEvents") or []
print(f"\n=== keyEvents: {len(ke)} ===")
print(json.dumps(ke[0], indent=2)[:1200])

print("\n=== every event type present, with clock and wallclock ===")
for e in ke:
    t = (e.get("type") or {})
    clk = (e.get("clock") or {}).get("displayValue")
    per = (e.get("period") or {}).get("number")
    wc = e.get("wallclock")
    team = ((e.get("team") or {}).get("displayName")
            or (e.get("team") or {}).get("abbreviation"))
    sc = e.get("scoringPlay")
    print(f"  P{per} {str(clk):>7s} wc={str(wc):>22s} "
          f"{str(t.get('text'))[:22]:22s} scoring={sc} team={str(team)[:18]}")

print("\n=== commentary: does it carry wallclock? ===")
cm = d.get("commentary") or []
print(f"  {len(cm)} entries")
if cm:
    print(json.dumps(cm[0], indent=2)[:700])
    have_wc = sum(1 for c in cm if c.get("time", {}).get("displayValue"))
    print(f"  entries with a clock: {have_wc}/{len(cm)}")

print("\n=== other domain-relevant blocks in this one payload ===")
for k in ("rosters", "odds", "pickcenter", "standings", "lastFiveGames",
          "seasonseries", "gameInfo", "boxscore"):
    v = d.get(k)
    if v is None:
        print(f"  {k:14s} absent")
        continue
    if isinstance(v, list):
        print(f"  {k:14s} list n={len(v)}  keys={sorted(v[0])[:10] if v and isinstance(v[0],dict) else ''}")
    else:
        print(f"  {k:14s} dict keys={sorted(v)[:12]}")

gi = d.get("gameInfo") or {}
print(f"\n  gameInfo: venue={((gi.get('venue') or {}).get('fullName'))!r} "
      f"attendance={gi.get('attendance')} "
      f"officials={[o.get('displayName') for o in (gi.get('officials') or [])]}")

ros = d.get("rosters") or []
if ros:
    r0 = ros[0]
    print(f"\n  rosters[0]: team={((r0.get('team') or {}).get('displayName'))!r} "
          f"formation={r0.get('formation')} n_players={len(r0.get('roster') or [])}")
    pl = (r0.get("roster") or [])
    if pl:
        p = pl[0]
        print(f"    player keys: {sorted(p)[:14]}")
        print(f"    starter={p.get('starter')} pos="
              f"{((p.get('position') or {}).get('abbreviation'))} "
              f"name={((p.get('athlete') or {}).get('displayName'))!r}")

with open(os.path.join(REP, "espn_keyevents_shape.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"wallclockAvailable": d.get("wallclockAvailable"),
               "n_keyEvents": len(ke), "sample": ke[:3],
               "summary_keys": sorted(d)}, fh, indent=1, default=str)
