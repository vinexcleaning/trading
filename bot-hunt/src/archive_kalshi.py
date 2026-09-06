"""Save Kalshi's settled history before the exchange deletes it.

## Why this exists

`retention_rebisect.py` was run again on 2026-09-06 and it settles the
disagreement HANDOFF.md §2c has been carrying since August. The two projects
predicted different things and only one of them can be right today:

  M009 (market-selection): the trade tape retains ~69 days and ROLLS daily.
  BH009 (bot-hunt):        the listing boundary is a FIXED calendar date,
                           2026-05-25, and the window is simply growing.

On 2026-08-04 the earliest listed settled market was 2026-05-25. Today it is
2026-06-30, and the tape goes empty between age 68 d and 69 d. The boundary
moved 36 days forward in 33 calendar days.

**BH009 is wrong. The window rolls.** Every day that passes, one more day of
Kalshi's history is deleted and cannot be bought back at any price. Everything
before 2026-06-30 is already gone.

## What it saves, and what it deliberately does not

The live recorder (`record.py`) snapshots order books for 19 series and has
already written 193 GB. That is depth, and depth cannot be backfilled — which
is exactly why it must not be widened to chase this. This is the other half:
the *settled* record for the WHOLE exchange, which is small, and which is the
thing actually expiring.

  series   13,839 rows, one call.  Includes fee_multiplier, which is how the
           19 half-fee and 14 zero-fee families were found.
  markets  every settled market on the exchange, walked by cursor. Title,
           open/close, result, volume, liquidity, and the event it belonged to.
  trades   the tape for a market: price, count, side, timestamp. Optional and
           prioritised by volume, because it is the expensive one.

Depth is not attempted. It was never retained and nothing here can invent it.

## Its own database file, on purpose

`record.db` is a 193 GB file with a live writer holding one transaction across
all 18 series for up to 1,400 seconds. A second writer on it died in 19 minutes
in August. WAL lets readers run beside a writer; it does not let two writers
overlap. Analysis joins the two with ATTACH, which costs nothing.

## Resumable

The market walk checkpoints its cursor after every page, so a network drop
costs one page rather than the run. Re-running continues from where it stopped;
re-running after completion is a cheap no-op that picks up whatever is new.

Read-only against Kalshi. Unauthenticated. No keys, no orders.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.elections.kalshi.com/trade-api/v2"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "kalshi_archive.db"

# Kalshi's unauthenticated limit is generous for reads and this walk is one
# request per 1,000 markets. The pause is politeness, not necessity - but a
# 429 mid-walk would cost the run, and the run is racing a deletion clock.
PAUSE = 0.15
TIMEOUT = 45

SCHEMA = """
create table if not exists series (
  ticker text primary key,
  title text, category text, frequency text,
  fee_type text, fee_multiplier real,
  tags text, contract_url text, last_updated_ts text,
  seen_utc text);

create table if not exists markets (
  ticker text primary key,
  event_ticker text, series_ticker text,
  title text, subtitle text, status text,
  open_time text, close_time text, expiration_time text,
  result text, can_close_early integer,
  volume integer, volume_24h integer, liquidity real,
  open_interest integer,
  last_price real, previous_price real,
  yes_bid real, yes_ask real,
  strike_type text, floor_strike real, cap_strike real,
  raw text,
  seen_utc text);
create index if not exists ix_m_series on markets(series_ticker, close_time);
create index if not exists ix_m_close on markets(close_time);

create table if not exists trades (
  trade_id text primary key,
  ticker text, created_time text,
  yes_price real, no_price real, count integer, taker_side text,
  seen_utc text);
create index if not exists ix_t_ticker on trades(ticker, created_time);

-- One row per walk, so a partial run is visible rather than looking finished.
create table if not exists sweeps (
  id integer primary key autoincrement,
  kind text, started_utc text, finished_utc text,
  cursor text, pages integer, rows integer, note text);

-- Which markets have had their tape pulled, so the trade pass is resumable
-- and does not re-walk a market whose tape is already saved.
create table if not exists trade_done (
  ticker text primary key, trades integer, done_utc text);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=120)
    con.execute("pragma journal_mode=WAL")
    con.executescript(SCHEMA)
    con.commit()
    return con


def get(path: str, tries: int = 5) -> dict:
    """One GET, with backoff. Raises only after every retry is spent."""
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(BASE + path, timeout=TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            last = exc
            # 429 means slow down rather than stop; anything else in the 4xx
            # range is a bad request and retrying it will not help.
            if exc.code == 429:
                time.sleep(2 + attempt * 3)
                continue
            if 400 <= exc.code < 500:
                raise
            time.sleep(1 + attempt)
        except Exception as exc:  # noqa: BLE001 - network, timeouts, JSON
            last = exc
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"GET {path} failed after {tries} tries: {last}")


# ---------------------------------------------------------------------------
# series
# ---------------------------------------------------------------------------

def sweep_series(con: sqlite3.Connection) -> int:
    payload = get("/series/")
    rows = payload.get("series") or []
    stamp = now()
    con.executemany(
        """insert into series (ticker,title,category,frequency,fee_type,
                               fee_multiplier,tags,contract_url,last_updated_ts,seen_utc)
           values (?,?,?,?,?,?,?,?,?,?)
           on conflict(ticker) do update set
             title=excluded.title, category=excluded.category,
             frequency=excluded.frequency, fee_type=excluded.fee_type,
             fee_multiplier=excluded.fee_multiplier, tags=excluded.tags,
             contract_url=excluded.contract_url,
             last_updated_ts=excluded.last_updated_ts, seen_utc=excluded.seen_utc""",
        [(s.get("ticker"), s.get("title"), s.get("category"), s.get("frequency"),
          s.get("fee_type"), s.get("fee_multiplier"),
          json.dumps(s.get("tags") or []), s.get("contract_url"),
          str(s.get("last_updated_ts")), stamp) for s in rows])
    con.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# markets
# ---------------------------------------------------------------------------

def _market_row(m: dict, stamp: str) -> tuple:
    def num(*names):
        for n in names:
            v = m.get(n)
            if v is not None:
                return v
        return None
    return (
        m.get("ticker"), m.get("event_ticker"), m.get("series_ticker"),
        m.get("title"), m.get("subtitle") or m.get("yes_sub_title"),
        m.get("status"),
        m.get("open_time"), m.get("close_time"), m.get("expiration_time"),
        m.get("result"), 1 if m.get("can_close_early") else 0,
        num("volume"), num("volume_24h"),
        num("liquidity_dollars", "liquidity"),
        num("open_interest"),
        num("last_price_dollars", "last_price"),
        num("previous_price_dollars", "previous_price"),
        num("yes_bid_dollars", "yes_bid"), num("yes_ask_dollars", "yes_ask"),
        m.get("strike_type"), num("floor_strike"), num("cap_strike"),
        json.dumps(m, separators=(",", ":")),
        stamp,
    )


def sweep_markets(con: sqlite3.Connection, status: str, limit_pages: int = 0) -> tuple[int, int]:
    """Walk every market of one status, checkpointing the cursor per page.

    `status=settled` is the one racing the clock. `status=closed` and `open`
    are cheap and worth having so a market's whole life is in one place.
    """
    cur = con.execute(
        "select cursor from sweeps where kind=? and finished_utc is null "
        "order by id desc limit 1", (f"markets:{status}",)).fetchone()
    cursor = cur[0] if cur and cur[0] else ""
    if cursor:
        print(f"  resuming {status} from saved cursor", flush=True)
        con.execute("update sweeps set note='resumed' where kind=? and finished_utc is null",
                    (f"markets:{status}",))
    sweep = con.execute(
        "insert into sweeps (kind,started_utc,pages,rows) values (?,?,0,0)",
        (f"markets:{status}", now())).lastrowid
    con.commit()

    pages = rows = 0
    while True:
        path = f"/markets?limit=1000&status={status}"
        if cursor:
            path += f"&cursor={cursor}"
        payload = get(path)
        batch = payload.get("markets") or []
        if batch:
            stamp = now()
            con.executemany(
                "insert or replace into markets values (" + ",".join("?" * 24) + ")",
                [_market_row(m, stamp) for m in batch])
            rows += len(batch)
        pages += 1
        cursor = payload.get("cursor") or ""
        # Checkpoint before the next request, so a drop costs one page.
        con.execute("update sweeps set cursor=?, pages=?, rows=? where id=?",
                    (cursor, pages, rows, sweep))
        con.commit()
        if pages % 25 == 0:
            print(f"  {status}: {pages} pages, {rows:,} markets", flush=True)
        exhausted = not cursor or not batch
        if exhausted:
            break
        if limit_pages and pages >= limit_pages:
            # Deliberately NOT marked finished, and the cursor is left in place.
            # An early stop that looks complete is worse than no checkpoint at
            # all: the next run silently starts from page one and the operator
            # has no way to tell. Found by running it.
            print("  stopping early at page limit - cursor kept, run again to resume",
                  flush=True)
            return pages, rows
        time.sleep(PAUSE)

    con.execute("update sweeps set finished_utc=?, cursor=null where id=?", (now(), sweep))
    con.commit()
    return pages, rows


# ---------------------------------------------------------------------------
# trades
# ---------------------------------------------------------------------------

def sweep_trades(con: sqlite3.Connection, top: int, min_volume: int) -> tuple[int, int]:
    """Pull the tape for settled markets, busiest first.

    Busiest first because the run is racing a deletion clock and a market with
    no volume has no tape worth saving. `trade_done` makes it resumable and
    stops a second run re-walking what is already held.
    """
    targets = con.execute(
        """select m.ticker, m.volume from markets m
           left join trade_done d on d.ticker = m.ticker
           where m.status='settled' and d.ticker is null
             and coalesce(m.volume,0) >= ?
           order by coalesce(m.volume,0) desc
           limit ?""", (min_volume, top)).fetchall()
    print(f"  {len(targets):,} settled markets to pull", flush=True)

    done = total = 0
    for ticker, volume in targets:
        cursor = ""
        got = 0
        while True:
            path = f"/markets/trades?ticker={ticker}&limit=1000"
            if cursor:
                path += f"&cursor={cursor}"
            try:
                payload = get(path)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {ticker}: {exc}", flush=True)
                break
            batch = payload.get("trades") or []
            if batch:
                stamp = now()
                con.executemany(
                    "insert or replace into trades values (?,?,?,?,?,?,?,?)",
                    [(t.get("trade_id"), t.get("ticker"), t.get("created_time"),
                      t.get("yes_price_dollars", t.get("yes_price")),
                      t.get("no_price_dollars", t.get("no_price")),
                      t.get("count"), t.get("taker_side"), stamp) for t in batch])
                got += len(batch)
            cursor = payload.get("cursor") or ""
            if not cursor or not batch:
                break
            time.sleep(PAUSE)
        con.execute("insert or replace into trade_done values (?,?,?)", (ticker, got, now()))
        con.commit()
        done += 1
        total += got
        if done % 50 == 0:
            print(f"  {done:,}/{len(targets):,} markets, {total:,} trades", flush=True)
        time.sleep(PAUSE)
    return done, total


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--series", action="store_true", help="refresh the series list")
    ap.add_argument("--markets", default="", help="comma list of statuses: settled,closed,open")
    ap.add_argument("--trades", type=int, default=0, help="pull the tape for N settled markets")
    ap.add_argument("--min-volume", type=int, default=1, help="skip markets below this volume")
    ap.add_argument("--pages", type=int, default=0, help="stop a market walk after N pages")
    # Daemon mode, so this can live in runners/runners.json beside the recorders
    # rather than needing its own scheduled task. The registry's watchdog already
    # restarts a dead process after a reboot or a power cut, which is the failure
    # this job cannot survive: a day not archived is a day deleted.
    ap.add_argument("--every", type=float, default=0.0,
                    help="hours between passes. 0 = run once and exit")
    args = ap.parse_args()

    if not (args.series or args.markets or args.trades):
        ap.error("nothing asked for - use --series, --markets or --trades")

    con = connect()
    print(f"archive {now()}  db={DB}", flush=True)
    while True:
        one_pass(con, args)
        if not args.every:
            return
        print(f"sleeping {args.every}h", flush=True)
        time.sleep(args.every * 3600)


def one_pass(con: sqlite3.Connection, args) -> None:
    if args.series:
        n = sweep_series(con)
        print(f"series: {n:,}", flush=True)

    for status in [s.strip() for s in args.markets.split(",") if s.strip()]:
        t0 = time.time()
        pages, rows = sweep_markets(con, status, args.pages)
        print(f"markets/{status}: {rows:,} in {pages} pages, {time.time()-t0:.0f}s", flush=True)

    if args.trades:
        t0 = time.time()
        done, total = sweep_trades(con, args.trades, args.min_volume)
        print(f"trades: {total:,} across {done:,} markets, {time.time()-t0:.0f}s", flush=True)

    size = DB.stat().st_size / 1e9 if DB.exists() else 0
    print(f"pass done {now()}. archive is {size:.2f} GB", flush=True)


if __name__ == "__main__":
    sys.exit(main())
