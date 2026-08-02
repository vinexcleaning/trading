"""Measure the CEILING: what the free public Kalshi API will actually give.

No auth. Read-only. Answers, with live requests rather than assumption:
  1. How many series/categories exist, and how big is the whole market universe?
  2. How far back does market history really go? (plan assumes July 2021)
  3. Are trades public, and how far back?
  4. Are candlesticks public, at what interval, and how far back?
  5. Do the price/volume fields still carry data, or are they now None?

Everything is bounded so this finishes in a couple of minutes.
"""
import datetime as dt
import json
import pathlib
import sys
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
S = requests.Session()
S.headers["User-Agent"] = "kalshi-audit/1.0"
OUT = pathlib.Path(__file__).resolve().parent


def get(path, **params):
    for attempt in range(6):
        try:
            r = S.get(f"{BASE}{path}", params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            return r
        except Exception:  # noqa: BLE001
            if attempt == 5:
                raise
            time.sleep(1.5 * (attempt + 1))
    return r


def hdr(s):
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}", flush=True)


def q1_series():
    hdr("1. SERIES AND CATEGORIES")
    out, cursor, pages = [], None, 0
    while True:
        p = {"limit": 200}
        if cursor:
            p["cursor"] = cursor
        r = get("/series/", **p)
        if not r.ok:
            print(f"  /series/ -> {r.status_code} {r.text[:200]}")
            break
        b = r.json()
        batch = b.get("series", [])
        out.extend(batch)
        pages += 1
        cursor = b.get("cursor")
        if not cursor or not batch or pages > 60:
            break
        time.sleep(0.1)
    print(f"series returned    {len(out):,}  ({pages} pages)")
    cats = {}
    for s in out:
        c = s.get("category") or "(none)"
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"   {c:34s} {n:5d} series")
    (OUT / "series_raw.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def q2_universe_size():
    hdr("2. UNIVERSE SIZE AND DATE FLOOR (paginating /markets to exhaustion)")
    cursor, pages, n = None, 0, 0
    by_status, by_year, by_cat = {}, {}, {}
    oldest, newest = None, None
    t0 = time.time()
    while True:
        p = {"limit": 1000}
        if cursor:
            p["cursor"] = cursor
        r = get("/markets", **p)
        if not r.ok:
            print(f"  stopped: {r.status_code} {r.text[:200]}")
            break
        b = r.json()
        batch = b.get("markets", [])
        for m in batch:
            n += 1
            st = m.get("status", "?")
            by_status[st] = by_status.get(st, 0) + 1
            ct = m.get("close_time") or ""
            if len(ct) >= 4:
                by_year[ct[:4]] = by_year.get(ct[:4], 0) + 1
                if oldest is None or ct < oldest:
                    oldest = ct
                if newest is None or ct > newest:
                    newest = ct
            tk = m.get("ticker", "")
            root = tk.split("-")[0]
            by_cat[root] = by_cat.get(root, 0) + 1
        pages += 1
        cursor = b.get("cursor")
        if pages % 25 == 0:
            print(f"   ...{n:,} markets, {pages} pages, "
                  f"{time.time() - t0:.0f}s", flush=True)
        if not cursor or not batch:
            break
        time.sleep(0.05)
    print(f"\nTOTAL markets      {n:,}   ({pages} pages, "
          f"{time.time() - t0:.0f}s)")
    print(f"close_time range   {oldest} -> {newest}")
    print("by status          " + ", ".join(f"{k}={v:,}" for k, v in
                                            sorted(by_status.items())))
    print("by close year      " + ", ".join(f"{k}={v:,}" for k, v in
                                            sorted(by_year.items())))
    print(f"distinct series roots  {len(by_cat):,}")
    top = sorted(by_cat.items(), key=lambda kv: -kv[1])[:25]
    for k, v in top:
        print(f"   {k:32s} {v:7,}")
    return n, by_year, by_status


def q3_trades():
    hdr("3. TRADE HISTORY -- public? how far back?")
    r = get("/markets/trades", limit=1)
    print(f"/markets/trades unauth -> {r.status_code}")
    if not r.ok:
        return
    t = r.json().get("trades", [])
    if t:
        print("sample trade fields: " + ", ".join(sorted(t[0])))
        print(json.dumps(t[0], indent=2)[:600])
    # how far back does the global feed go: binary-ish probe by year
    for y in (2022, 2023, 2024, 2025, 2026):
        cut = int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp())
        rr = get("/markets/trades", limit=100, max_ts=cut)
        tt = rr.json().get("trades", []) if rr.ok else []
        oldest = min((x.get("created_time", "") for x in tt), default="-")
        print(f"  trades with ts < {y}-01-01: n={len(tt):4d} oldest={oldest}")
        time.sleep(0.1)


def q4_candles(sample_tickers):
    hdr("4. CANDLESTICKS -- public? intervals? how far back?")
    if not sample_tickers:
        print("  no sample ticker available")
        return
    for tk in sample_tickers[:3]:
        series = tk.split("-")[0]
        end = int(time.time())
        start = end - 60 * 60 * 24 * 365
        for interval in (1, 60, 1440):
            r = get(f"/series/{series}/markets/{tk}/candlesticks",
                    start_ts=start, end_ts=end, period_interval=interval)
            if not r.ok:
                print(f"  {tk[:44]:44s} int={interval:5d} -> "
                      f"{r.status_code} {r.text[:90]}")
                continue
            c = r.json().get("candlesticks", [])
            if c:
                ts = [x.get("end_period_ts") for x in c if x.get("end_period_ts")]
                span = (f"{dt.datetime.utcfromtimestamp(min(ts)):%Y-%m-%d %H:%M}"
                        f" -> {dt.datetime.utcfromtimestamp(max(ts)):%Y-%m-%d %H:%M}"
                        if ts else "-")
                print(f"  {tk[:44]:44s} int={interval:5d} n={len(c):5d} {span}")
                if interval == 60:
                    print("     candle fields: "
                          + ", ".join(sorted(c[0])))
                    print("     sample: " + json.dumps(c[-1])[:400])
            else:
                print(f"  {tk[:44]:44s} int={interval:5d} n=0")
            time.sleep(0.1)


def q5_field_liveness():
    hdr("5. ARE PRICE / VOLUME FIELDS STILL POPULATED?")
    r = get("/markets", limit=200, status="settled")
    ms = r.json().get("markets", []) if r.ok else []
    if not ms:
        print("  no settled markets returned")
        return
    keys = sorted({k for m in ms for k in m})
    print(f"n={len(ms)} settled markets; {len(keys)} distinct fields\n")
    print(f"{'field':34s} {'non-null%':>9s}  sample")
    for k in keys:
        vals = [m.get(k) for m in ms]
        nn = sum(v is not None and v != "" for v in vals) / len(vals) * 100
        samp = next((repr(v)[:38] for v in vals if v not in (None, "")), "-")
        print(f"  {k:32s} {nn:8.1f}%  {samp}")
    return ms


def main():
    q1_series()
    n, by_year, _ = q2_universe_size()
    q3_trades()
    ms = q5_field_liveness()
    tickers = [m.get("ticker") for m in (ms or []) if m.get("ticker")]
    q4_candles(tickers)
    print("\nDONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
