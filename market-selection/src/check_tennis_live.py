"""Is there a free LIVE data source covering the tennis tiers Kalshi trades?

The tennis problem in one line: LEDGER T001/T018 -- ITF is ~76% of Kalshi's
tennis book, and even when Sackmann existed it carried serve stats on only 4.6%
of futures rows. The tier that trades has no features; the tier with features
barely trades. Sackmann is now deleted outright (M015).

So the only remaining route for tennis is live/in-play state, which is
LIVE-ONLY and cannot be backfilled. If a free source covers ITF and Challenger,
a recorder has to start tonight. If it covers only ATP/WTA main tour, tennis
loses its last dimension-D argument.
"""
import json
import os

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SITE = "https://site.api.espn.com/apis/site/v2/sports/tennis"

out = {}
for league in ["atp", "wta"]:
    try:
        r = requests.get(f"{SITE}/{league}/scoreboard", headers=UA, timeout=45)
    except requests.RequestException as e:
        print(f"{league}: ERR {e}")
        continue
    print(f"\n=== ESPN tennis/{league} scoreboard: http {r.status_code}, "
          f"{len(r.content)} bytes ===")
    if r.status_code != 200:
        continue
    d = r.json()
    evs = d.get("events", [])
    print(f"  events (tournaments): {len(evs)}")
    tours = []
    for e in evs:
        comps = e.get("competitions", [])
        # tournament-level grouping
        names = set()
        n_matches = 0
        for c in comps:
            n_matches += 1
            g = c.get("grouping") or {}
            if g.get("shortName"):
                names.add(g["shortName"])
        print(f"    {str(e.get('name'))[:60]:60s} matches={n_matches} "
              f"groupings={sorted(names)[:4]}")
        tours.append({"name": e.get("name"), "matches": n_matches})
        if comps:
            c = comps[0]
            print(f"      sample competition keys: {sorted(c.keys())[:14]}")
            cs = c.get("competitors") or []
            if cs:
                print(f"      competitor keys: {sorted(cs[0].keys())[:14]}")
                print(f"      linescores present: "
                      f"{'linescores' in cs[0]} ; status: "
                      f"{(c.get('status') or {}).get('type', {}).get('name')}")
    out[league] = tours

print("\n=== does anything free cover ITF / Challenger? ===")
checks = [
    ("ESPN tennis all leagues", f"{SITE}/scoreboard"),
    ("ITF official", "https://www.itftennis.com/en/"),
    ("ITF api", "https://www.itftennis.com/tennis/api/TournamentApi/GetCalendar?circuitCode=MT&searchString=&skip=0&take=5"),
    ("ATP challenger tour page", "https://www.atptour.com/en/scores/results-archive"),
    ("Tennis Live Data (rapidapi probe)", "https://tennis-live-data.p.rapidapi.com/matches-by-date/2026-08-02"),
    ("flashscore-ish: sofascore api", "https://api.sofascore.com/api/v1/sport/tennis/events/live"),
]
for name, url in checks:
    try:
        r = requests.get(url, headers=UA, timeout=40)
        body = r.content
        detail = ""
        if r.status_code == 200 and "json" in (r.headers.get("content-type") or ""):
            try:
                d = r.json()
                if isinstance(d, dict):
                    ev = d.get("events") or d.get("Items") or []
                    detail = f"keys={sorted(d)[:8]} n_events={len(ev)}"
                    if ev and isinstance(ev, list) and isinstance(ev[0], dict):
                        t = ev[0].get("tournament") or {}
                        detail += (f" first={str(t.get('name'))[:40]!r} "
                                   f"cat={str((t.get('category') or {}).get('name'))[:22]!r}")
                elif isinstance(d, list):
                    detail = f"list n={len(d)}"
            except ValueError:
                detail = "(unparseable json)"
        print(f"  {name:36s} http={r.status_code} bytes={len(body)} {detail}")
        out[name] = {"http": r.status_code, "bytes": len(body), "detail": detail}
    except Exception as e:  # noqa: BLE001
        print(f"  {name:36s} ERR {type(e).__name__}: {str(e)[:70]}")
        out[name] = {"status": "ERROR", "err": str(e)[:100]}

with open(os.path.join(REP, "tennis_live_sources.json"), "w",
          encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/tennis_live_sources.json")
