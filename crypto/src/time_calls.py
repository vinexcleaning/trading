"""Measure candlestick call latency under current machine load."""
import datetime as dt
import json
import time

import requests

UA = {"User-Agent": "research-readonly/0.1"}
B = "https://api.elections.kalshi.com/trade-api/v2"

m = json.loads(open(r"C:\Users\gianf\crypto\data\kalshi_settled\KXBTCD.jsonl",
                    encoding="utf-8").readline())
ct = dt.datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
e = int(ct.timestamp())

lat, codes = [], []
for _ in range(8):
    t0 = time.perf_counter()
    r = requests.get(f"{B}/series/KXBTCD/markets/{m['ticker']}/candlesticks",
                     params={"start_ts": e - 3600, "end_ts": e,
                             "period_interval": 1},
                     headers=UA, timeout=45)
    lat.append(time.perf_counter() - t0)
    codes.append(r.status_code)
lat.sort()
print("codes:", codes)
print(f"candlestick latency ms: min={lat[0]*1000:.0f} "
      f"med={lat[len(lat)//2]*1000:.0f} max={lat[-1]*1000:.0f}")
print(f"=> per-event (8 strikes): {8*lat[len(lat)//2]:.1f}s")
print(f"=> 250 events: {250*8*lat[len(lat)//2]/60:.0f} min")
