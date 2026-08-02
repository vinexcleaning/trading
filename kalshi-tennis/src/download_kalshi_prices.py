"""Pull Kalshi pre-match prices for every settled tennis match.

The /markets snapshot only carries the FINAL price of a settled market, which
is useless as a pre-match benchmark. Candlesticks give the price path, so we
can take the last quote strictly before the match started -- which is what the
model has to beat.

One market per event is enough: the two sides are complements.
"""
import concurrent.futures as cf
import datetime as dt
import json
import pathlib
import sys
import threading
import time

import pandas as pd
import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "kalshi"
BASE = "https://api.elections.kalshi.com/trade-api/v2"

_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch(row):
    series, ticker, occ = row["series"], row["ticker_a"], row["occurrence"]
    if not occ:
        return None
    t = dt.datetime.fromisoformat(str(occ).replace("Z", "+00:00"))
    start = int((t - dt.timedelta(days=7)).timestamp())
    end = int(t.timestamp())
    url = f"{BASE}/series/{series}/markets/{ticker}/candlesticks"
    params = {"start_ts": start, "end_ts": end, "period_interval": 60}

    for attempt in range(4):
        try:
            r = session().get(url, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            body = r.json()
            break
        except Exception:  # noqa: BLE001
            if attempt == 3:
                return {"event_ticker": row["event_ticker"], "error": 1}
            time.sleep(0.8 * (attempt + 1))
    else:
        return {"event_ticker": row["event_ticker"], "error": 1}

    candles = body.get("candlesticks") or []
    # last bar that closed at or before the scheduled start
    usable = [c for c in candles if c.get("end_period_ts", 0) <= end]
    if not usable:
        return {"event_ticker": row["event_ticker"], "n_candles": len(candles)}
    last = usable[-1]
    bid = f((last.get("yes_bid") or {}).get("close_dollars"))
    ask = f((last.get("yes_ask") or {}).get("close_dollars"))
    px = f((last.get("price") or {}).get("close_dollars"))
    mid = None
    if bid is not None and ask is not None and ask >= bid:
        mid = (bid + ask) / 2.0
    return {
        "event_ticker": row["event_ticker"],
        "pre_bid": bid, "pre_ask": ask, "pre_last": px, "pre_mid": mid,
        "pre_ts": last.get("end_period_ts"),
        "hours_before": (end - last.get("end_period_ts", end)) / 3600.0,
        "n_candles": len(candles),
        "volume_pre": f(last.get("volume_fp")),
        "oi_pre": f(last.get("open_interest_fp")),
    }


def main():
    ev = td.load_kalshi_events()
    ev = ev[ev["occurrence"].notna() & ev["ticker_a"].notna()]
    rows = ev[["event_ticker", "series", "ticker_a", "occurrence"]].to_dict("records")
    print(f"fetching pre-match prices for {len(rows):,} matches ...", flush=True)

    out, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(fetch, rows):
            done += 1
            if res:
                out.append(res)
            if done % 250 == 0:
                print(f"  {done:,}/{len(rows):,}", flush=True)

    df = pd.DataFrame(out)
    path = OUT / "kalshi_prematch_prices.parquet"
    df.to_parquet(path, index=False)
    got = df["pre_mid"].notna().sum() if "pre_mid" in df else 0
    print(f"\n{len(df):,} rows, {got:,} with a usable pre-match mid -> {path}")
    if "hours_before" in df:
        print(df["hours_before"].describe().to_string())


if __name__ == "__main__":
    main()
