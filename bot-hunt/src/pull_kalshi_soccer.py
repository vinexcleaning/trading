"""STEP 3 — pull the Kalshi side of the backfillable pair.

For every settled market in the South American / Mexican soccer families inside
Kalshi's ~71-day tape window, fetch:

  * the market record (result, strikes, close time, the event it belongs to)
  * hourly candlesticks, which are the only re-pullable price history Kalshi
    publishes

Candlesticks use a DIFFERENT schema from the market object. On a market,
`yes_bid` is dead and you must read `yes_bid_dollars`. On a candlestick,
`yes_bid` is a live NESTED DICT carrying `open_dollars`/`close_dollars` etc.
`STATUS.md` names four files that read candles correctly and says explicitly:
do not "fix" them. This follows the candle convention.

Read-only, public, paced. Writes data/kalshi_soccer.db.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
DB = DATA / "kalshi_soccer.db"

SERIES = ["KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXCOPADOBRASILGAME",
          "KXMLSGAME", "KXBRASILEIRAOGAME", "KXDIMAYORGAME"]

SCHEMA = """
create table if not exists markets (
  ticker text primary key, series text, event_ticker text, title text,
  yes_sub_title text, no_sub_title text, status text, result text,
  open_time text, close_time text, expiration_time text,
  volume real, open_interest real, raw text, pulled_utc text);
create table if not exists candles (
  ticker text, series text, end_period_ts integer,
  yes_bid_open real, yes_bid_close real, yes_bid_high real, yes_bid_low real,
  yes_ask_open real, yes_ask_close real, yes_ask_high real, yes_ask_low real,
  price_open real, price_close real, price_high real, price_low real,
  volume real, open_interest real,
  primary key (ticker, end_period_ts));
create index if not exists ix_c on candles(series, end_period_ts);
create table if not exists pull_log (
  ts_utc text, series text, n_markets integer, n_candles integer, note text);
"""


def con():
    DATA.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=120.0)
    c.execute("pragma journal_mode=WAL")
    c.execute("pragma busy_timeout=120000")
    c.executescript(SCHEMA)
    return c


def d(v):
    """Candlestick nested-dict field -> cents, or None."""
    return None if v is None else V.fnum(v) * 100.0 if isinstance(v, str) \
        else (float(v) * 100.0 if isinstance(v, (int, float)) else None)


def nested(cd: dict, key: str, sub: str):
    """Candle sides are nested dicts: yes_bid.open_dollars etc.

    Returns cents. Falls back to the legacy integer-cent key ONLY if the
    dollars key is absent, and records nothing silently: a candle with neither
    returns None, which the caller counts.
    """
    blk = cd.get(key)
    if isinstance(blk, dict):
        v = blk.get(f"{sub}_dollars")
        if v is not None:
            f = V.fnum(v)
            return None if f is None else f * 100.0
        v = blk.get(sub)
        if v is not None:
            f = V.fnum(v)
            return None if f is None else float(f)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=75)
    ap.add_argument("--series", default="")
    ap.add_argument("--skip-candles", action="store_true")
    a = ap.parse_args()
    series_list = [s for s in (a.series.split(",") if a.series else SERIES) if s]

    c = con()
    now_ts = int(time.time())
    start_ts = now_ts - a.days * 86400

    for s in series_list:
        n_m = 0
        seen = set()
        for status in ("settled", "closed", "open"):
            for m in V.k_paginate("/markets",
                                  {"series_ticker": s, "status": status,
                                   "limit": 200}, "markets", max_pages=60):
                tk = m.get("ticker")
                if not tk or tk in seen:
                    continue
                seen.add(tk)
                c.execute(
                    "insert or replace into markets values "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (tk, s, m.get("event_ticker"), m.get("title"),
                     m.get("yes_sub_title"), m.get("no_sub_title"),
                     m.get("status"), m.get("result"), m.get("open_time"),
                     m.get("close_time"), m.get("expiration_time"),
                     V.fnum(m.get("volume_fp")), V.fnum(m.get("open_interest_fp")),
                     json.dumps(m, default=str)[:6000],
                     datetime.now(timezone.utc).isoformat()))
                n_m += 1
        c.commit()
        print(f"{s}: {n_m} markets", flush=True)

        n_c = 0
        if not a.skip_candles:
            rows = c.execute(
                "select ticker, close_time from markets where series=? "
                "and status in ('settled','closed','finalized')", (s,)).fetchall()
            for i, (tk, close_time) in enumerate(rows):
                if c.execute("select 1 from candles where ticker=? limit 1",
                             (tk,)).fetchone():
                    continue
                # Kalshi wants the SERIES ticker in the candlestick path.
                r = V.k_get(f"/series/{s}/markets/{tk}/candlesticks",
                            {"start_ts": start_ts, "end_ts": now_ts,
                             "period_interval": 60})
                if r is None or r.status_code != 200:
                    continue
                cds = (r.json() or {}).get("candlesticks") or []
                recs = []
                for cd in cds:
                    recs.append((
                        tk, s, cd.get("end_period_ts"),
                        nested(cd, "yes_bid", "open"), nested(cd, "yes_bid", "close"),
                        nested(cd, "yes_bid", "high"), nested(cd, "yes_bid", "low"),
                        nested(cd, "yes_ask", "open"), nested(cd, "yes_ask", "close"),
                        nested(cd, "yes_ask", "high"), nested(cd, "yes_ask", "low"),
                        nested(cd, "price", "open"), nested(cd, "price", "close"),
                        nested(cd, "price", "high"), nested(cd, "price", "low"),
                        V.fnum(cd.get("volume")), V.fnum(cd.get("open_interest"))))
                if recs:
                    c.executemany("insert or replace into candles values "
                                  "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", recs)
                    n_c += len(recs)
                if i % 50 == 0:
                    c.commit()
                    print(f"   candles {i}/{len(rows)}  {n_c} rows", flush=True)
            c.commit()
        c.execute("insert into pull_log values (?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(), s, n_m, n_c, None))
        c.commit()
        print(f"{s}: {n_c} candle rows", flush=True)

    print("\n== summary")
    for r in c.execute(
            "select m.series, count(distinct m.ticker), "
            " sum(case when m.result in ('yes','no') then 1 else 0 end), "
            " (select count(*) from candles cc where cc.series=m.series), "
            " min(m.close_time), max(m.close_time) "
            "from markets m group by m.series"):
        print(f"  {r[0]:24} markets={r[1]:>5} settled={r[2]:>5} "
              f"candles={r[3]:>7}  {str(r[4])[:10]} -> {str(r[5])[:10]}")
    c.close()


if __name__ == "__main__":
    main()
