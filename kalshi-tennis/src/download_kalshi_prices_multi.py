"""Re-pull Kalshi prices at SEVERAL anchors before the scheduled time.

The first version anchored on `occurrence_datetime` and took the last candle at
or before it. For a large minority of markets that timestamp is the expiry, not
the start, so the "pre-match" price was really the settled price -- prices of
0.995/0.005 that are always exactly right. That is leakage, and it inflated
Kalshi's apparent accuracy everywhere it was used.

Fix: capture the last quote at occurrence minus 0/1/2/6/24 hours, so the
leakage can be measured rather than assumed away, and a safe anchor chosen on
evidence.
"""
import concurrent.futures as cf
import datetime as dt
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

ANCHORS_H = (0.0, 1.0, 2.0, 6.0, 24.0)
TIERS = ("main",)          # what the bookmaker comparison needs

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
    t = dt.datetime.fromisoformat(str(occ).replace("Z", "+00:00"))
    end = int(t.timestamp())
    start = int((t - dt.timedelta(days=10)).timestamp())
    url = f"{BASE}/series/{series}/markets/{ticker}/candlesticks"
    params = {"start_ts": start, "end_ts": end, "period_interval": 60}

    body = None
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
    if body is None:
        return {"event_ticker": row["event_ticker"], "error": 1}

    candles = sorted(body.get("candlesticks") or [],
                     key=lambda c: c.get("end_period_ts", 0))
    out = {"event_ticker": row["event_ticker"], "n_candles": len(candles)}
    for h in ANCHORS_H:
        cutoff = end - int(h * 3600)
        usable = [c for c in candles if c.get("end_period_ts", 0) <= cutoff]
        tag = f"h{h:g}"
        if not usable:
            out[f"bid_{tag}"] = out[f"ask_{tag}"] = out[f"mid_{tag}"] = None
            continue
        last = usable[-1]
        bid = f((last.get("yes_bid") or {}).get("close_dollars"))
        ask = f((last.get("yes_ask") or {}).get("close_dollars"))
        out[f"bid_{tag}"] = bid
        out[f"ask_{tag}"] = ask
        out[f"mid_{tag}"] = ((bid + ask) / 2.0
                             if bid is not None and ask is not None
                             and ask >= bid else None)
        out[f"lag_{tag}"] = (cutoff - last.get("end_period_ts", cutoff)) / 3600.0
    return out


def main():
    ev = td.load_kalshi_events()
    ev = ev[ev["tier"].isin(TIERS)]
    ev = ev[ev["occurrence"].notna() & ev["ticker_a"].notna()]
    rows = ev[["event_ticker", "series", "ticker_a", "occurrence"]].to_dict("records")
    print(f"fetching multi-anchor prices for {len(rows):,} main-tour matches ...",
          flush=True)

    out, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(fetch, rows):
            done += 1
            if res:
                out.append(res)
            if done % 250 == 0:
                print(f"  {done:,}/{len(rows):,}", flush=True)

    df = pd.DataFrame(out)
    path = OUT / "kalshi_prices_multianchor.parquet"
    df.to_parquet(path, index=False)
    print(f"\n{len(df):,} rows -> {path}")
    for h in ANCHORS_H:
        c = f"mid_h{h:g}"
        if c in df:
            print(f"  anchor -{h:g}h: {df[c].notna().sum():,} with a mid")


if __name__ == "__main__":
    main()
