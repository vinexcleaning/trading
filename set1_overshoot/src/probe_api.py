"""Quick probe: confirm market + candlestick shapes before building the puller."""
import json
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"

r = requests.get(f"{BASE}/markets",
                 params={"series_ticker": "KXATPMATCH", "limit": 5,
                         "status": "settled"}, timeout=60)
r.raise_for_status()
mk = r.json()["markets"]
print("=== settled market keys ===")
print(sorted(mk[0].keys()))
print("\n=== sample market ===")
print(json.dumps(mk[0], indent=2)[:2500])

m = mk[0]
open_ts = m["open_time"]
close_ts = m["close_time"]
print("\nopen", open_ts, "close", close_ts)

import datetime as dt
o = int(dt.datetime.fromisoformat(open_ts.replace("Z", "+00:00")).timestamp())
c = int(dt.datetime.fromisoformat(close_ts.replace("Z", "+00:00")).timestamp())
url = f"{BASE}/series/{m['series_ticker'] if 'series_ticker' in m else 'KXATPMATCH'}/markets/{m['ticker']}/candlesticks"
r2 = requests.get(url, params={"start_ts": o, "end_ts": c,
                               "period_interval": 1}, timeout=90)
print("\ncandles status", r2.status_code)
if r2.ok:
    cs = r2.json().get("candlesticks", [])
    print("n candles", len(cs))
    if cs:
        print(json.dumps(cs[len(cs) // 2], indent=2))
else:
    print(r2.text[:800])
