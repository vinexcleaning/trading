"""TASK 1 probe: do Kalshi candlesticks and ESPN timelines actually exist,
and what are the real field names?

Verifying by fetching. Two things this project has been burned by:
  - legacy Kalshi price fields are null on 100% of markets; the values live in
    `*_dollars` / `*_fp`. The candlestick payload has its own schema and must
    be checked separately rather than assumed to match.
  - a source described as available that was 404.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "market-selection", "src"))
import kalshi_api as K  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
SERIES = ["KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXLIGAMXTOTAL",
          "KXDIMAYORGAME", "KXCOPADOBRASILGAME", "KXMLSGAME"]

print("=== how many SETTLED soccer markets are reachable? ===")
for s in SERIES:
    counts = {}
    for status in ("settled", "finalized", "closed", "open"):
        r = K.get("/markets", {"series_ticker": s, "status": status,
                               "limit": 1000})
        n = len(r.json().get("markets", [])) if r and r.status_code == 200 else None
        counts[status] = n
    print(f"  {s:22s} {counts}")

print("\n=== a settled market, and its candlesticks ===")
r = K.get("/markets", {"series_ticker": "KXLIGAMXGAME", "status": "settled",
                       "limit": 20})
ms = r.json().get("markets", []) if r and r.status_code == 200 else []
if not ms:
    r = K.get("/markets", {"series_ticker": "KXLIGAMXGAME",
                           "status": "finalized", "limit": 20})
    ms = r.json().get("markets", []) if r and r.status_code == 200 else []
print(f"  got {len(ms)} settled/finalized markets")
if ms:
    m = ms[0]
    print(f"  ticker={m['ticker']}  title={m.get('title')!r}")
    print(f"  yes_sub={m.get('yes_sub_title')!r}  result={m.get('result')!r}")
    print(f"  open={m.get('open_time')}  close={m.get('close_time')}")
    ev = m.get("event_ticker")
    series = m["ticker"].split("-")[0]
    # candlesticks: series/markets/ticker/candlesticks
    try:
        ot = datetime.fromisoformat(m["open_time"].replace("Z", "+00:00"))
        ct = datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        ot, ct = None, None
    if ot and ct:
        for interval in (1, 60):
            rr = K.get(f"/series/{series}/markets/{m['ticker']}/candlesticks",
                       {"start_ts": int(ot.timestamp()),
                        "end_ts": int(ct.timestamp()),
                        "period_interval": interval})
            print(f"\n  candlesticks period_interval={interval}: "
                  f"http={getattr(rr,'status_code','ERR')}")
            if rr is not None and rr.status_code == 200:
                d = rr.json()
                cs = d.get("candlesticks") or []
                print(f"    top-level keys: {sorted(d)}")
                print(f"    n candles: {len(cs)}")
                if cs:
                    print(f"    FIRST CANDLE:\n{json.dumps(cs[0], indent=6)[:900]}")
            else:
                print(f"    body: {getattr(rr,'text','')[:200]}")

print("\n\n=== ESPN: play-by-play / timeline for a soccer match ===")
for league in ("mex.1", "arg.1", "bra.1", "usa.1", "col.1"):
    u = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
    try:
        rr = requests.get(u, headers=UA, timeout=40)
    except Exception as e:  # noqa: BLE001
        print(f"  {league}: ERR {e}")
        continue
    n = len(rr.json().get("events", [])) if rr.status_code == 200 else None
    print(f"  {league:8s} scoreboard http={rr.status_code} events={n}")

print("\n=== ESPN summary with timeline (a finished match) ===")
u = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"
rr = requests.get(u, params={"dates": "20260726-20260802"}, headers=UA, timeout=45)
evs = rr.json().get("events", []) if rr.status_code == 200 else []
print(f"  events in the last week: {len(evs)}")
for e in evs[:3]:
    print(f"    {e.get('date')}  {e.get('name')}  "
          f"status={(e.get('status') or {}).get('type', {}).get('name')}")
if evs:
    eid = evs[0]["id"]
    su = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary"
    rs = requests.get(su, params={"event": eid}, headers=UA, timeout=45)
    print(f"\n  summary event={eid} http={rs.status_code} bytes={len(rs.content)}")
    if rs.status_code == 200:
        d = rs.json()
        print(f"  summary keys: {sorted(d)}")
        for k in ("keyEvents", "commentary", "plays"):
            v = d.get(k)
            if v:
                print(f"\n  --- {k}: {len(v)} entries ---")
                print(json.dumps(v[0], indent=4)[:900])
