"""Pull 1-second klines from data.binance.vision for the lead-lag test.

WHY: cross-asset lead-lag is the ONLY hypothesis left in this project with zero
evidence against it. Every prior measurement of BTC/ETH relatedness in this
project (corr 0.891) was CONTEMPORANEOUS and sampled HOURLY -- structurally
incapable of detecting a lead. Lead-lag in crypto lives at milliseconds to
seconds, so hourly data cannot see it either way.

api.binance.com is geo-blocked from this machine (HTTP 451) but
data.binance.vision is NOT -- verified in Phase 0. It serves free daily zips of
1-second klines going back years, no auth.

Single-threaded and paced: two other Claude sessions share this machine's
connection to Kalshi. This host is different but courtesy costs nothing.
"""
import argparse
import datetime as dt
import io
import os
import sys
import time
import zipfile

import requests

UA = {"User-Agent": "research-readonly/0.1"}
BASE = "https://data.binance.vision/data/spot/daily/klines"
OUT = r"C:\Users\gianf\crypto\data\binance_1s"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]


def fetch_day(sym, day):
    """-> list of (open_time_ms, close_price) or None."""
    url = f"{BASE}/{sym}/1s/{sym}-1s-{day}.zip"
    for a in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=120)
        except Exception:
            time.sleep(1.5 * (a + 1))
            continue
        if r.status_code == 404:
            return None, 404
        if r.status_code != 200:
            time.sleep(1.2 * (a + 1))
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(r.content))
        except zipfile.BadZipFile:
            return None, "badzip"
        name = zf.namelist()[0]
        rows = []
        with zf.open(name) as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8"):
                p = line.rstrip("\n").split(",")
                if len(p) < 5:
                    continue
                try:
                    # Binance kline: openTime,open,high,low,close,volume,...
                    rows.append((int(p[0]), float(p[4]), float(p[5])))
                except ValueError:
                    continue
        return rows, 200
    return None, "retries"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--end", default="2026-07-30")
    ap.add_argument("--symbols", nargs="*", default=SYMBOLS)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    end = dt.date.fromisoformat(args.end)
    days = [(end - dt.timedelta(days=i)).isoformat()
            for i in range(args.days)][::-1]
    print(f"pulling {len(args.symbols)} symbols x {len(days)} days "
          f"({days[0]} -> {days[-1]})", flush=True)

    t0 = time.time()
    for sym in args.symbols:
        path = os.path.join(OUT, f"{sym}_1s.csv")
        have = set()
        if os.path.exists(path):
            # resume: record which days already present
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("d,"):
                        continue
                    have.add(line.split(",", 1)[0][:10])
        mode = "a" if os.path.exists(path) else "w"
        with open(path, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write("day,ms,close,volume\n")
            for day in days:
                if day in have:
                    continue
                rows, code = fetch_day(sym, day)
                if not rows:
                    print(f"  {sym} {day} -> {code}", flush=True)
                    continue
                for ms, c, v in rows:
                    f.write(f"{day},{ms},{c},{v}\n")
                f.flush()
                print(f"  {sym} {day} -> {len(rows)} rows "
                      f"[{time.time()-t0:.0f}s]", flush=True)
                time.sleep(0.25)
    print(f"done in {time.time()-t0:.0f}s", flush=True)
    for sym in args.symbols:
        p = os.path.join(OUT, f"{sym}_1s.csv")
        if os.path.exists(p):
            print(f"  {sym}: {os.path.getsize(p)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
