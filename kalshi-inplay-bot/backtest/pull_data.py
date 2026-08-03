"""
pull_data.py - one-time historical pull of Kalshi tennis candlesticks.

READ-ONLY. Uses only public market-data endpoints; no credentials are loaded,
so this process cannot place, cancel, or modify an order even by accident.

Writes two parquet files into ./data:
    markets.parquet   one row per settled market (metadata + settlement)
    candles.parquet   one row per market-minute (bid/ask OHLC, volume)

Resumable: candle shards are written per series, and completed markets are
skipped on re-run.
"""

from __future__ import annotations

import datetime as dt
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"

SERIES = {
    "KXATPMATCH": "ATP",
    "KXWTAMATCH": "WTA",
    "KXATPCHALLENGERMATCH": "Challenger",
    "KXITFMATCH": "ITF-M",
    "KXITFWMATCH": "ITF-W",
}

LOOKBACK_DAYS = 28
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

_session = requests.Session()


def ts_of(s: str) -> int:
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def get(path: str, params: dict, tries: int = 5) -> dict:
    """GET with backoff. 429/5xx are retried; anything else raises."""
    delay = 0.5
    last = None
    for _ in range(tries):
        try:
            r = _session.get(BASE + path, params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                last = requests.HTTPError(f"{r.status_code}")
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last = e
            time.sleep(delay)
            delay = min(delay * 2, 8.0)
    raise last


def enumerate_markets() -> pd.DataFrame:
    """Every settled tennis market that closed inside the lookback window."""
    cutoff = int(time.time()) - LOOKBACK_DAYS * 86400
    rows = []
    for series, label in SERIES.items():
        cursor, seen, kept = None, 0, 0
        while True:
            p = {"series_ticker": series, "status": "settled", "limit": 1000}
            if cursor:
                p["cursor"] = cursor
            d = get("/markets", p)
            ms = d.get("markets", [])
            if not ms:
                break
            stop = False
            for m in ms:
                seen += 1
                ct = m.get("close_time")
                ot = m.get("open_time")
                if not ct or not ot:
                    continue
                close_ts = ts_of(ct)
                if close_ts < cutoff:
                    stop = True          # list is newest-first; nothing older matters
                    continue
                sv = m.get("settlement_value_dollars")
                rows.append({
                    "ticker": m["ticker"],
                    "event_ticker": m["event_ticker"],
                    "series": series,
                    "tournament": label,
                    "player": m.get("yes_sub_title", ""),
                    "title": m.get("title", ""),
                    "open_ts": ts_of(ot),
                    "close_ts": close_ts,
                    "result": m.get("result", ""),
                    "settlement": float(sv) if sv is not None else float("nan"),
                    "volume": float(m.get("volume_fp", 0) or 0),
                    "volume_24h": float(m.get("volume_24h_fp", 0) or 0),
                })
                kept += 1
            cursor = d.get("cursor")
            if not cursor or stop:
                break
        print(f"  {label:11s} scanned {seen:6d}  kept {kept:6d}")
    return pd.DataFrame(rows)


def fetch_candles(mkt: dict) -> list[dict]:
    """1-minute candles for one market, windowed under the 5000-candle cap."""
    series, ticker = mkt["series"], mkt["ticker"]
    start = max(mkt["open_ts"], mkt["close_ts"] - 3 * 86400)
    end = mkt["close_ts"]
    out = []
    span = 4000 * 60                      # stay clear of the 5000 ceiling
    a = start
    while a < end:
        b = min(a + span, end)
        try:
            d = get(f"/series/{series}/markets/{ticker}/candlesticks",
                    {"start_ts": a, "end_ts": b, "period_interval": 1})
        except Exception:
            break
        for c in d.get("candlesticks", []):
            bid = c.get("yes_bid") or {}
            ask = c.get("yes_ask") or {}
            px = c.get("price") or {}

            def f(v):
                return float(v) * 100 if v is not None else None

            out.append({
                "ticker": ticker,
                "ts": c["end_period_ts"],
                "bid_open": f(bid.get("open_dollars")), "bid_high": f(bid.get("high_dollars")),
                "bid_low": f(bid.get("low_dollars")), "bid_close": f(bid.get("close_dollars")),
                "ask_open": f(ask.get("open_dollars")), "ask_high": f(ask.get("high_dollars")),
                "ask_low": f(ask.get("low_dollars")), "ask_close": f(ask.get("close_dollars")),
                "trade_open": f(px.get("open_dollars")), "trade_high": f(px.get("high_dollars")),
                "trade_low": f(px.get("low_dollars")), "trade_close": f(px.get("close_dollars")),
                "trade_prev": f(px.get("previous_dollars")),
                "volume": float(c.get("volume_fp", 0) or 0),
                "open_interest": float(c.get("open_interest_fp", 0) or 0),
            })
        a = b
    return out


def main() -> None:
    mpath = os.path.join(DATA, "markets.parquet")
    if os.path.exists(mpath):
        markets = pd.read_parquet(mpath)
        print(f"markets.parquet exists: {len(markets)} markets")
    else:
        print(f"Enumerating settled tennis markets, last {LOOKBACK_DAYS} days...")
        markets = enumerate_markets()
        markets.to_parquet(mpath, index=False)
        print(f"-> {len(markets)} markets, {markets.event_ticker.nunique()} distinct matches")

    for series, label in SERIES.items():
        shard = os.path.join(DATA, f"candles_{label}.parquet")
        if os.path.exists(shard):
            print(f"  {label}: shard exists, skipping")
            continue
        sub = markets[markets.series == series]
        recs = sub.to_dict("records")
        print(f"  {label}: pulling {len(recs)} markets...")
        rows, done, t0 = [], 0, time.time()
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(fetch_candles, m): m for m in recs}
            for fu in as_completed(futs):
                try:
                    rows.extend(fu.result())
                except Exception:
                    pass
                done += 1
                if done % 250 == 0:
                    el = time.time() - t0
                    print(f"    {done}/{len(recs)}  {len(rows)} rows  "
                          f"{el:.0f}s  eta {el/done*(len(recs)-done):.0f}s", flush=True)
        df = pd.DataFrame(rows)
        df.to_parquet(shard, index=False)
        print(f"  {label}: {len(df)} candle rows -> {shard}")

    shards = [os.path.join(DATA, f"candles_{l}.parquet") for l in SERIES.values()]
    shards = [s for s in shards if os.path.exists(s)]
    allc = pd.concat([pd.read_parquet(s) for s in shards], ignore_index=True)
    allc.to_parquet(os.path.join(DATA, "candles.parquet"), index=False)
    print(f"\nTOTAL: {len(markets)} markets, {len(allc)} candle rows")


if __name__ == "__main__":
    main()
