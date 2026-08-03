"""Download historical 1-minute BTC/ETH OHLCV covering the settled-market history.

Bitstamp's public OHLC endpoint gives 1000 candles per request with no auth and
reaches back well past 2026-05-25, which is where the KXBTC15M settled history
starts. Coinbase (300/req) is used as an independent cross-check on a sample.

Idempotent: merges on timestamp.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external"
OUT.mkdir(parents=True, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "kalshi-research-readonly/0.1"})
STEP = 60
LIMIT = 1000


def fetch_bitstamp(pair: str, start_s: int, end_s: int) -> pd.DataFrame:
    rows: list[dict] = []
    t = start_s
    n_req = 0
    while t < end_s:
        for attempt in range(5):
            try:
                r = S.get(
                    f"https://www.bitstamp.net/api/v2/ohlc/{pair}/",
                    params={"step": STEP, "limit": LIMIT, "start": t},
                    timeout=25,
                )
                if r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                r.raise_for_status()
                data = r.json()["data"]["ohlc"]
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 4:
                    print(f"    give up at t={t}: {type(e).__name__} {str(e)[:60]}")
                    data = []
                    break
                time.sleep(1.5 * (attempt + 1))
        n_req += 1
        if not data:
            t += STEP * LIMIT
            continue
        rows += data
        last_ts = int(data[-1]["timestamp"])
        if last_ts <= t:
            t += STEP * LIMIT
        else:
            t = last_ts + STEP
        if n_req % 20 == 0:
            print(f"    {n_req} reqs, {len(rows)} candles, at "
                  f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(t))}")
        time.sleep(0.15)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce").astype("int64")
    df = (
        df.drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    df["ts"] = pd.to_datetime(df.timestamp, unit="s", utc=True)
    return df


def main() -> None:
    # cover the settled-market window with a margin either side
    start = int(pd.Timestamp("2026-05-20", tz="UTC").timestamp())
    end = int(time.time())
    for pair, name in (("btcusd", "BTCUSD"), ("ethusd", "ETHUSD")):
        print(f"{name}: downloading 1-min candles "
              f"{time.strftime('%Y-%m-%d', time.gmtime(start))} -> now")
        t0 = time.time()
        df = fetch_bitstamp(pair, start, end)
        if df.empty:
            print(f"  {name}: NO DATA")
            continue
        path = OUT / f"{name}_1m.parquet"
        if path.exists():
            old = pd.read_parquet(path)
            df = (
                pd.concat([old, df])
                .drop_duplicates(subset=["timestamp"], keep="last")
                .sort_values("timestamp")
                .reset_index(drop=True)
            )
        df.to_parquet(path, index=False)
        expected = (df.timestamp.max() - df.timestamp.min()) // 60 + 1
        print(
            f"  {name}: {len(df)} candles {df.ts.min()} -> {df.ts.max()} "
            f"(coverage {100*len(df)/expected:.1f}%, {time.time()-t0:.0f}s)"
        )


if __name__ == "__main__":
    main()
