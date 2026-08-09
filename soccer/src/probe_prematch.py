"""TASK 3: what is knowable BEFORE kickoff, and what is live-only?

The knowability question is the whole point. A lineup read off a finished
match's summary tells you who played; it does not tell you what was KNOWN an
hour before kickoff, and a feature that silently uses post-kickoff information
is a look-ahead leak of exactly the kind LEDGER T010 is.

So: take fixtures that have NOT started, and see which blocks are already
populated. Whatever is populated pre-match and later overwritten is live-only
and must be recorded now.
"""
import json
import os
from datetime import datetime, timezone

import requests

# ESPN (Akamai) began returning 403 to any Mozilla/... or unknown custom
# User-Agent on 2026-08-08. Measured: "Mozilla/5.0 (soccer-research/1.0)"
# -> 403, "soccer-research/1.0" -> 403, curl/8.4.0 -> 200, requests' own
# default -> 200. Sending no override is what works; do not "fix" this by
# adding a browser string back.
UA = {}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
NOW = datetime.now(timezone.utc)

out = {}
for lg in ["mex.1", "arg.1", "col.1", "bra.1", "usa.1"]:
    r = requests.get(f"{SITE}/{lg}/scoreboard",
                     params={"dates": f"{NOW:%Y%m%d}-"
                                      f"{(NOW.replace(day=NOW.day)):%Y%m%d}",
                             "limit": 200}, headers=UA, timeout=45)
    evs = r.json().get("events", []) if r.status_code == 200 else []
    # also look a few days ahead
    r2 = requests.get(f"{SITE}/{lg}/scoreboard",
                      params={"dates": f"{NOW:%Y%m%d}-20260810", "limit": 200},
                      headers=UA, timeout=45)
    if r2.status_code == 200:
        evs += r2.json().get("events", [])
    seen, uniq = set(), []
    for e in evs:
        if e["id"] not in seen:
            seen.add(e["id"])
            uniq.append(e)
    pending = [e for e in uniq
               if not ((e.get("status") or {}).get("type") or {}).get("completed")]
    print(f"\n=== {lg}: {len(uniq)} events, {len(pending)} not yet completed ===")
    for e in pending[:3]:
        st = ((e.get("status") or {}).get("type") or {})
        try:
            ko = datetime.fromisoformat((e["date"]).replace("Z", "+00:00"))
            hrs = (ko - NOW).total_seconds() / 3600
        except Exception:  # noqa: BLE001
            hrs = None
        s = requests.get(f"{SITE}/{lg}/summary", params={"event": e["id"]},
                         headers=UA, timeout=45)
        d = s.json() if s.status_code == 200 else {}
        ros = d.get("rosters") or []
        n_players = sum(len(x.get("roster") or []) for x in ros)
        forms = [x.get("formation") for x in ros]
        starters = sum(1 for x in ros for p in (x.get("roster") or [])
                       if p.get("starter"))
        odds = d.get("odds") or []
        gi = d.get("gameInfo") or {}
        offs = [o.get("displayName") for o in (gi.get("officials") or [])]
        print(f"  {e.get('name')[:46]:46s} T-{hrs:6.1f}h  status={st.get('name')}")
        print(f"     rosters={len(ros)} players={n_players} starters={starters} "
              f"formations={forms}")
        print(f"     odds_blocks={len(odds)} officials={offs} "
              f"keyEvents={len(d.get('keyEvents') or [])}")
        if odds:
            o = odds[0]
            print(f"     odds: provider={(o.get('provider') or {}).get('name')} "
                  f"home={(o.get('homeTeamOdds') or {}).get('moneyLine')} "
                  f"draw={o.get('drawOdds')} "
                  f"away={(o.get('awayTeamOdds') or {}).get('moneyLine')}")
        out[f"{lg}:{e['id']}"] = {
            "hours_to_kickoff": hrs, "status": st.get("name"),
            "n_rosters": len(ros), "n_players": n_players,
            "starters": starters, "formations": forms,
            "odds_blocks": len(odds), "officials": offs,
            "n_keyEvents": len(d.get("keyEvents") or [])}

with open(os.path.join(REP, "prematch_availability.json"), "w",
          encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/prematch_availability.json")
