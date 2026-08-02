"""Phase 0c -- pull 1-minute candles for every kept market.

Prices are stored as integer cents. Kalshi's tennis markets are
`price_level_structure: linear_cent`, so every quote is a whole cent and the
integer representation is exact -- no float dust can enter from here.

Usage:
    p0_candles.py [--limit N] [--workers N] [--mirror N] [--out NAME]
"""
import argparse
import concurrent.futures as cf
import pathlib
import sys
import threading
import time
from decimal import Decimal

import numpy as np
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://api.elections.kalshi.com/trade-api/v2"

MAX_PERIODS = 4800          # API caps a candlestick request at 5000 periods
_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.mount("https://", requests.adapters.HTTPAdapter(
            pool_connections=32, pool_maxsize=32))
        _local.s = s
    return _local.s


def cents(x):
    """Dollar string -> integer cents, exactly. -1 means absent."""
    if x is None:
        return -1
    d = Decimal(str(x)) * 100
    i = int(d.to_integral_value())
    if Decimal(i) != d:            # not a whole cent -- should not happen
        return -1
    return i


def get(url, params):
    for attempt in range(6):
        try:
            r = session().get(url, params=params, timeout=90)
            if r.status_code == 429:
                time.sleep(1.0 + 1.5 * attempt)
                continue
            if r.status_code >= 500:
                time.sleep(0.5 + attempt)
                continue
            r.raise_for_status()
            return r.json()
        except Exception:  # noqa: BLE001
            if attempt == 5:
                return None
            time.sleep(0.5 * (attempt + 1))
    return None


def fetch_one(job):
    ticker, series, start, end = job
    url = f"{BASE}/series/{series}/markets/{ticker}/candlesticks"
    candles = []
    s = start
    while s < end:
        e = min(s + MAX_PERIODS * 60, end)
        body = get(url, {"start_ts": s, "end_ts": e, "period_interval": 1})
        if body is None:
            return ticker, None
        candles.extend(body.get("candlesticks") or [])
        s = e
    if not candles:
        return ticker, np.zeros((0, 12), dtype=np.int32)

    seen, rows = set(), []
    for c in candles:
        t = c.get("end_period_ts")
        if t is None or t in seen:
            continue
        seen.add(t)
        b = c.get("yes_bid") or {}
        a = c.get("yes_ask") or {}
        p = c.get("price") or {}
        # a period with no trade carries only previous_dollars
        pc = p.get("close_dollars", p.get("previous_dollars"))
        try:
            vol = int(float(c.get("volume_fp") or 0))
        except (TypeError, ValueError):
            vol = 0
        rows.append((
            t,
            cents(b.get("open_dollars")), cents(b.get("high_dollars")),
            cents(b.get("low_dollars")), cents(b.get("close_dollars")),
            # ask OHLC, not just close. Modelling a resting order needs to know
            # whether the book TRADED THROUGH a price during the minute, and
            # for the ~62% of matches where the favourite is the NO side that
            # question is answered by ask_low, not by any close.
            cents(a.get("open_dollars")), cents(a.get("high_dollars")),
            cents(a.get("low_dollars")), cents(a.get("close_dollars")),
            cents(pc),
            vol,
            int(float(c.get("open_interest_fp") or 0)),
        ))
    rows.sort()
    return ticker, np.array(rows, dtype=np.int64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--mirror", type=int, default=0,
                    help="also fetch N random opposite sides, for the "
                         "mirror-relationship check")
    ap.add_argument("--out", default="candles")
    ap.add_argument("--uni", default="universe.parquet")
    args = ap.parse_args()

    uni = pd.read_parquet(DATA / args.uni)
    uni = uni.sort_values("ticker").reset_index(drop=True)
    if args.limit:
        uni = uni.head(args.limit)

    jobs = [(r.ticker, r.series,
             int(r.open_time.timestamp()) - 60,
             int(r.close_time.timestamp()) + 300)
            for r in uni.itertuples()]

    if args.mirror:
        sides = pd.read_parquet(DATA / "sides.parquet")
        kept = set(uni["ticker"])
        others = sides[~sides["ticker"].isin(kept)]
        others = others[others["event_ticker"].isin(set(uni["event_ticker"]))]
        rng = np.random.default_rng(20260731)
        pick = others.iloc[rng.choice(len(others),
                                      size=min(args.mirror, len(others)),
                                      replace=False)]
        jobs += [(r.ticker, r.series,
                  int(r.open_time.timestamp()) - 60,
                  int(r.close_time.timestamp()) + 300)
                 for r in pick.itertuples()]
        print(f"+{len(pick):,} mirror sides")

    print(f"fetching {len(jobs):,} markets with {args.workers} workers ...",
          flush=True)
    t0 = time.time()

    parts, done, failed, chunk = [], 0, [], 0
    outdir = DATA / args.out
    outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob("*.parquet"):
        f.unlink()

    def flush():
        nonlocal parts, chunk
        if not parts:
            return
        df = pd.concat(parts, ignore_index=True)
        df.to_parquet(outdir / f"part_{chunk:04d}.parquet", index=False)
        chunk += 1
        parts = []

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for ticker, arr in ex.map(fetch_one, jobs):
            done += 1
            if arr is None:
                failed.append(ticker)
            elif len(arr):
                parts.append(pd.DataFrame({
                    "ticker": ticker,
                    "ts": arr[:, 0].astype("int64"),
                    "bid_o": arr[:, 1].astype("int16"),
                    "bid_h": arr[:, 2].astype("int16"),
                    "bid_l": arr[:, 3].astype("int16"),
                    "bid": arr[:, 4].astype("int16"),
                    "ask_o": arr[:, 5].astype("int16"),
                    "ask_h": arr[:, 6].astype("int16"),
                    "ask_l": arr[:, 7].astype("int16"),
                    "ask": arr[:, 8].astype("int16"),
                    "last": arr[:, 9].astype("int16"),
                    "vol": arr[:, 10].astype("int32"),
                    "oi": arr[:, 11].astype("int64"),
                }))
            if done % 500 == 0:
                el = time.time() - t0
                print(f"  {done:,}/{len(jobs):,}  {el:6.0f}s  "
                      f"{done / el:5.1f}/s  fail={len(failed)}", flush=True)
            if len(parts) >= 1500:
                flush()
    flush()

    print(f"\ndone in {(time.time() - t0) / 60:.1f} min, "
          f"{len(failed)} failures", flush=True)
    if failed:
        (DATA / f"{args.out}_failed.txt").write_text("\n".join(failed))
    tot = sum(pd.read_parquet(p, columns=["ts"]).shape[0]
              for p in sorted(outdir.glob("*.parquet")))
    print(f"{tot:,} candle rows in {len(list(outdir.glob('*.parquet')))} parts")


if __name__ == "__main__":
    sys.exit(main())
