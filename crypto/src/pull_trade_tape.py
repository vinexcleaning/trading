"""Pull the Kalshi trade tape for the crypto maker test -- LISTING-DRIVEN.

MM_RESULTS_MAKER.md ran the maker test on ONE day and it did not survive its
placebo: shuffling which side was the aggressor returned +1.351c against the real
+0.873c on KXBTC15M (p=0.995), and "always buy YES" returned +3.874c on the same
data, naming the apparent edge as a one-day directional move. The constraint is
EVENTS, not method: 29 correlated windows on a single day.

FOUR API FACTS, EACH MEASURED RATHER THAN ASSUMED, AND EACH CHANGED THE DESIGN:

  1. `/markets/trades` SILENTLY IGNORES `series_ticker`. Passing
     series_ticker=KXBTC15M returns KXABNB, KXALIENS, KXASEANGAME... A filter
     that is accepted and ignored is worse than one that errors.
  2. So v1 of this file paginated the whole exchange by hour. Measured: ONE HOUR
     is >200,000 trades and did not exhaust at a 200-page cap -- 128 s per hour,
     i.e. **7+ hours for a week**. Abandoned.
  3. `/markets/trades?ticker=X` DOES work, per market, with a cursor.
  4. **KXBTC15M is ONE market per event, not a strike ladder** -- 97 settled
     tickers in a day across 97 distinct windows. So the whole series is ~97
     requests a day, not 200,000 trades an hour. That is a ~50x saving and it is
     the difference between this being feasible and not.

The market LISTING also carries `result`, so settlement arrives with the ticker
list and needs no second pass. That is why this pulls both into one database.

Resumable per ticker. Paced: C018 puts the unauthenticated ceiling at 15 req/s
and the recorder is the irreplaceable process.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402

DB = ROOT / "data" / "trade_tape.db"

SCHEMA = """
create table if not exists markets (
  ticker text primary key, series text, event_ticker text,
  result text, close_time text, volume_fp real);
create table if not exists trades (
  trade_id text primary key, ticker text, series text, event_ticker text,
  count real, yes_price real, no_price real,
  taker_outcome_side text, taker_book_side text, created_time text);
create index if not exists ix_tr on trades(series, ticker);
create table if not exists pulled (ticker text primary key, n integer,
  pages integer, done_utc text);
"""


def fnum(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXBTC15M,KXETH15M")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--pace", type=float, default=0.25)
    # 20, not 8. MEASURED: one 15-minute market holds 12,462 trades over 13
    # pages, and THE CURSOR IS NEWEST-FIRST -- page 1 is the last 1,000 trades
    # before settlement. So a page cap does not sample a market, it keeps the
    # window nearest the answer and throws away the early price discovery. That
    # is the worst possible direction to truncate in, and an 8-page cap would
    # have silently done it to most markets. `pulled.pages` records the depth
    # used so truncation is detectable downstream rather than invisible.
    ap.add_argument("--max-pages", type=int, default=20)
    a = ap.parse_args()

    lo = int(datetime.strptime(a.start, "%Y-%m-%d")
             .replace(tzinfo=timezone.utc).timestamp())
    hi = int(datetime.strptime(a.end, "%Y-%m-%d")
             .replace(tzinfo=timezone.utc).timestamp())

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=180)
    con.execute("pragma journal_mode=WAL")
    con.executescript(SCHEMA)

    # ---- 1. the listing. It carries `result`, so settlement is free here.
    for s in a.series.split(","):
        s = s.strip()
        n = 0
        for m in V.k_paginate("/markets",
                              {"series_ticker": s, "status": "settled",
                               "limit": 200, "min_close_ts": lo,
                               "max_close_ts": hi}, "markets", max_pages=200):
            con.execute("insert or replace into markets values (?,?,?,?,?,?)",
                        (m.get("ticker"), s, (m.get("ticker") or "").rsplit("-", 1)[0],
                         m.get("result"), m.get("close_time"),
                         fnum(m.get("volume_fp"), 0.0)))
            n += 1
        con.commit()
        got = con.execute("select count(*) from markets where series=? and "
                          "result in ('yes','no')", (s,)).fetchone()[0]
        print(f"listing {s:11} {n:,} markets, {got:,} with a settled result",
              flush=True)

    # ---- 2. trades, per ticker
    todo = [r[0] for r in con.execute(
        "select m.ticker from markets m left join pulled p on p.ticker=m.ticker "
        "where m.result in ('yes','no') and p.ticker is null "
        "and m.series in (%s) order by m.close_time"
        % ",".join("?" * len(a.series.split(","))),
        [x.strip() for x in a.series.split(",")])]
    print(f"tickers to pull: {len(todo):,}", flush=True)

    started = time.time()
    for i, tk in enumerate(todo, 1):
        s = tk.split("-")[0]
        cursor, pages, kept = None, 0, 0
        while pages < a.max_pages:
            p = {"ticker": tk, "limit": 1000}
            if cursor:
                p["cursor"] = cursor
            r = V.k_get("/markets/trades", p, pace=a.pace)
            if r is None or r.status_code != 200:
                break
            try:
                j = r.json() or {}
            except ValueError:
                break
            tr = j.get("trades") or []
            pages += 1
            rows = []
            for t in tr:
                # ASSERT the ticker rather than trusting the filter -- fact (1)
                # above is exactly this endpoint ignoring a filter it accepted.
                if str(t.get("ticker") or "") != tk:
                    continue
                rows.append((t.get("trade_id"), tk, s, tk.rsplit("-", 1)[0],
                             fnum(t.get("count")), fnum(t.get("yes_price")),
                             fnum(t.get("no_price")),
                             t.get("taker_outcome_side"),
                             t.get("taker_book_side"), t.get("created_time")))
            if rows:
                con.executemany(
                    "insert or ignore into trades values (?,?,?,?,?,?,?,?,?,?)",
                    rows)
                kept += len(rows)
            cursor = j.get("cursor")
            if not cursor or not tr:
                break
        con.execute("insert or replace into pulled values (?,?,?,?)",
                    (tk, kept, pages,
                     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
        if i % 100 == 0 or i == len(todo):
            con.commit()
            el = time.time() - started
            tot = con.execute("select count(*) from trades").fetchone()[0]
            print(f"   {i}/{len(todo)}  db={tot:,} trades  "
                  f"ETA {el/i*(len(todo)-i)/60:.0f} min", flush=True)
    con.commit()

    print("\n== DONE")
    for r in con.execute(
            "select t.series, count(*), count(distinct t.ticker), "
            "min(m.close_time), max(m.close_time) from trades t "
            "join markets m on m.ticker=t.ticker group by t.series order by 2 desc"):
        print(f"   {r[0]:11} trades={r[1]:>10,}  events={r[2]:>6,}  "
              f"{str(r[3])[:10]} .. {str(r[4])[:10]}")
    con.close()


if __name__ == "__main__":
    main()
