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
import os
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

# Set by --raw. Off by default; see _market_row.
KEEP_RAW = False

# Families excluded by default because they are machine-generated combinatorial
# ladders rather than markets anyone trades. KXMVECROSSCATEGORY alone was
# 124,851 of the first 126,000 settled markets walked - 99% of the archive would
# have been one auto-generated family. --all overrides this.
EXCLUDE_DEFAULT = {"KXMVECROSSCATEGORY"}
EXCLUDE: set[str] = set()

# Measured by retention_rebisect.py on 2026-09-06: the tape is present at 68
# days and empty at 69, and the boundary rolls. Asking for more than this
# returns nothing and costs a request.
RETENTION_DAYS = 68

# 0.15 s earned a 429 partway through a 300-request smoke test, so the
# unauthenticated limit is real and lower than it looks from a short burst.
# Half a second is roughly 2 requests a second, which walks the whole 68-day
# backfill in about five hours and every later pass in minutes. A slower
# backfill is cheap; a rate-limited one that dies overnight is not.
PAUSE = 0.5
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

-- How far each series has been covered, so a pass asks only for what is new.
-- Per series rather than per page: interrupt the run and the finished series
-- stay finished, and the one in flight is redone from its own last close time.
create table if not exists progress (
  series_ticker text primary key, last_close_ts integer, updated_utc text);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Lifted verbatim from record.py rather than rewritten. Two writers on one
# SQLite file is this repo's most expensive recurring mistake - a second
# recorder on record.db died in 19 minutes in August - and the Windows
# pid check inside it is load-bearing: os.kill(pid, 0) TERMINATES the
# process on Windows rather than asking about it.
def _pid_alive(pid: int) -> bool:
    """Is this pid still running? ⚠ NEVER use os.kill(pid, 0) to ask on Windows.

    CPython maps os.kill on Windows to TerminateProcess for any signal that is
    not CTRL_C_EVENT/CTRL_BREAK_EVENT. The POSIX idiom for "does this process
    exist" would therefore KILL THE RECORDER -- the exact process whose data
    cannot be re-pulled at any price. So on Windows this asks the kernel.
    """
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x00100000, False, pid)   # SYNCHRONIZE
    if not h:
        return False
    still_running = k32.WaitForSingleObject(h, 0) == 0x00000102   # WAIT_TIMEOUT
    k32.CloseHandle(h)
    return bool(still_running)


def claim_single_instance() -> None:
    """Exit quietly if another recorder already owns this database file."""
    lock = DB.with_suffix(DB.suffix + ".lock")
    DATA.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            held = json.loads(lock.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            held = {}
        pid = held.get("pid")
        if isinstance(pid, int) and pid != os.getpid() and _pid_alive(pid):
            print(f"already running: pid {pid} owns {DB.name} since "
                  f"{held.get('started')} -- exiting without touching it",
                  flush=True)
            raise SystemExit(0)
        # A stale lock is normal after a crash or a reboot and is NOT an error.
        # Say so out loud though: a lock that silently reappears every restart
        # would hide a recorder that is crash-looping.
        if pid:
            print(f"stale lock from pid {pid} ({held.get('started')}) - "
                  f"that process is gone, taking over", flush=True)
    lock.write_text(json.dumps(
        {"pid": os.getpid(), "db": str(DB), "started": now(),
         "argv": sys.argv[1:]}), encoding="utf-8")
    import atexit
    atexit.register(lambda: lock.unlink(missing_ok=True))


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

# The exact keys this archive depends on. Kalshi renames fields - `volume`
# became `volume_fp`, `liquidity` became `liquidity_dollars` - and a script that
# reads a key that no longer exists gets None and stores a zero, which looks
# like a market that never traded. GUARDS.md has a field-renaming guard because
# three sessions hit this independently; this run hit it a fourth time and wrote
# 126,000 rows of zero volume before anyone looked.
#
# So the names are declared, and a pass that cannot find them stops instead of
# quietly recording nothing.
REQUIRED_FIELDS = ("ticker", "event_ticker", "status", "close_time",
                   "volume_fp", "open_interest_fp", "result")


def assert_fields(m: dict, where: str) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in m]
    if missing:
        raise RuntimeError(
            f"SCHEMA MOVED at {where}: {missing} absent from a market payload. "
            f"Keys present: {sorted(m.keys())}. Fix the mapping before running "
            f"again - a missing field is stored as a zero and reads as a market "
            f"that never traded.")


def series_of(m: dict) -> str | None:
    """The family, which the markets endpoint does not return.

    `event_ticker` is `KXMLBGAME-26SEP05DETNYY` and the family is everything
    before the first dash. Derived rather than guessed at from the market
    ticker, which carries a strike suffix as well.
    """
    ev = m.get("event_ticker") or ""
    return ev.split("-", 1)[0] or None


def _market_row(m: dict, stamp: str) -> tuple:
    def num(*names):
        for n in names:
            v = m.get(n)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return v
        return None
    return (
        m.get("ticker"), m.get("event_ticker"), series_of(m),
        m.get("title"), m.get("yes_sub_title") or m.get("subtitle"),
        m.get("status"),
        m.get("open_time"), m.get("close_time"), m.get("expiration_time"),
        m.get("result"), 1 if m.get("can_close_early") else 0,
        num("volume_fp"), num("volume_24h_fp"),
        num("liquidity_dollars"),
        num("open_interest_fp"),
        num("last_price_dollars"),
        num("previous_price_dollars"),
        num("yes_bid_dollars"), num("yes_ask_dollars"),
        m.get("strike_type"), num("floor_strike"), num("cap_strike"),
        # The raw payload is 4.3 KB a market and 90% of the file. At the
        # observed density - 126,000 settled markets in six hours - keeping it
        # would put the 68-day archive past 150 GB, on a disk already carrying a
        # 193 GB recorder. The typed columns are what anything reads; --raw
        # keeps the blob for a run that genuinely needs it.
        json.dumps(m, separators=(",", ":")) if KEEP_RAW else None,
        stamp,
    )


def sweep_markets(con: sqlite3.Connection, status: str, max_pages: int = 0) -> tuple[int, int]:
    """Walk the exchange by close time, forwards, resuming where it stopped.

    ## Third design, because the first two were wrong and both failures are
    ## worth keeping written down

    1. **Cursor walk of everything.** Kalshi settles roughly 500,000 markets a
       day and 99% of them are one machine-generated family, so the 68-day
       window is about 34,000 pages. Fine as a one-time backfill; useless as
       something that runs twice a day, because it can never be incremental.

    2. **One request per series.** `series_ticker` plus a close-time window
       works and answers in 0.2 s, but there are 13,839 series and asking for
       all of them every pass earned a `429 Too Many Requests` partway through
       a 300-series smoke test. The limit is the constraint, not the query.

    3. **This.** `min_close_ts` on the exchange-wide walk. The first pass covers
       the whole retention window and takes hours; every pass after it asks only
       for what has closed since, which is a few hundred pages. One request per
       1,000 markets either way, and the request count falls to what has
       actually happened rather than what exists.

    The combinatorial families are dropped client-side. They still cost a page
    each, which cannot be helped - the endpoint has no family filter - but they
    cost no disk.
    """
    horizon = int(time.time()) - RETENTION_DAYS * 86400

    # The endpoint answers NEWEST FIRST. That matters more than it sounds:
    # checkpointing the highest close time seen and feeding it back as
    # min_close_ts would move the floor straight to now on the first page, and
    # a resumed backfill would silently skip the 68 days it exists to collect.
    # Found by running it and reading the close range.
    #
    # So two markers, not one:
    #   __floor__   the OLDEST close time reached. Backfill continues below it
    #               with max_close_ts, walking further into the past.
    #   __newest__  the HIGHEST close time archived. Once the floor reaches the
    #               retention horizon there is no more past to collect, and
    #               every later pass asks only for what has closed since this.
    def marker(key: str, default: int) -> int:
        row = con.execute(
            "select last_close_ts from progress where series_ticker=?", (key,)).fetchone()
        return row[0] if row else default

    floor = marker("__floor__", 0)
    newest = marker("__newest__", 0)
    backfilling = floor == 0 or floor > horizon

    if backfilling:
        ceiling = floor if floor else 0
        where = (f"back from {datetime.fromtimestamp(ceiling, timezone.utc):%Y-%m-%d %H:%M}Z"
                 if ceiling else "back from now")
        print(f"  backfill: {where} to the {RETENTION_DAYS}-day horizon", flush=True)
    else:
        print(f"  incremental: since "
              f"{datetime.fromtimestamp(newest, timezone.utc):%Y-%m-%d %H:%M}Z", flush=True)

    sweep = con.execute(
        "insert into sweeps (kind,started_utc,pages,rows) values (?,?,0,0)",
        (f"markets:{status}", now())).lastrowid
    con.commit()

    cursor = ""
    pages = rows = 0
    lowest = floor if floor else 0
    while True:
        path = f"/markets?limit=1000&status={status}&min_close_ts={horizon}"
        if backfilling and lowest:
            path += f"&max_close_ts={lowest}"
        if not backfilling:
            path = f"/markets?limit=1000&status={status}&min_close_ts={newest}"
        if cursor:
            path += f"&cursor={cursor}"
        payload = get(path)
        batch = payload.get("markets") or []
        pages += 1
        if batch:
            assert_fields(batch[0], f"markets/{status} page {pages}")
            for m in batch:
                ts = _epoch(m.get("close_time"))
                if not ts:
                    continue
                if ts > newest:
                    newest = ts
                if not lowest or ts < lowest:
                    lowest = ts
            keep = [m for m in batch if series_of(m) not in EXCLUDE]
            if keep:
                stamp = now()
                con.executemany(
                    "insert or replace into markets values (" + ",".join("?" * 24) + ")",
                    [_market_row(m, stamp) for m in keep])
                rows += len(keep)
        cursor = payload.get("cursor") or ""
        con.execute("insert or replace into progress values ('__floor__',?,?)",
                    (lowest, now()))
        con.execute("insert or replace into progress values ('__newest__',?,?)",
                    (newest, now()))
        con.execute("update sweeps set pages=?, rows=? where id=?", (pages, rows, sweep))
        con.commit()
        if pages % 200 == 0:
            print(f"  {pages:,} pages, {rows:,} kept, floor at "
                  f"{datetime.fromtimestamp(lowest, timezone.utc):%Y-%m-%d %H:%M}Z",
                  flush=True)
        if not cursor or not batch:
            break
        if max_pages and pages >= max_pages:
            print("  page limit - floor kept, run again to continue", flush=True)
            return pages, rows
        time.sleep(PAUSE)

    con.execute("update sweeps set finished_utc=?, cursor=null where id=?", (now(), sweep))
    con.commit()
    return pages, rows


def _epoch(iso: str | None) -> int:
    if not iso:
        return 0
    try:
        return int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
                   .replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# trades
# ---------------------------------------------------------------------------

def recorded_families() -> list[str]:
    """The families `record.py` is recording depth for, read from that file.

    Imported rather than copied. A second hand-maintained list would drift, and
    the whole reason to pull the tape for exactly these families is that their
    order books are being recorded too - tape and depth on the same markets is
    what makes a backtest possible, and a copy that fell out of step would
    quietly break that alignment.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import record  # noqa: PLC0415 - deliberately late, and it has no import side effects
    return list(record.KALSHI_SERIES)


def sweep_trades(con: sqlite3.Connection, top: int, min_volume: int) -> tuple[int, int]:
    """Pull the tape for settled markets in the recorded families, busiest first.

    ## Why these families and not everything

    Measured on a 2.3-hour sample and scaled across the 68-day window:

      the 18 recorded families      ~70,000 markets
      every sports family, vol>=1k  ~1,300,000

    The second is not a slower version of the first, it is a different project.
    The 18 are the set this programme already decided matters, they are where
    the live money was, and their depth is being recorded - so the tape lines up
    with a book rather than sitting on its own.

    ## Oldest first, and the cost is per page rather than per market

    ⚠ An earlier version of this docstring said ~10 hours for those 70,000
    markets. That was wrong, and wrong in the way sizing usually is: it counted
    markets and the cost is pages. Measured, the six busiest settled markets
    carried 72,295 trades between them and took 194 seconds - about 32 seconds
    each, not the fraction of a second a per-market estimate implies.

    So this cannot finish the window in one night, and the ordering matters more
    than the throughput. It pulls OLDEST first, because the run is racing a
    deletion clock and the oldest markets are the ones about to fall off the
    end. Busiest-first was the intuitive order and is exactly backwards: the
    newest markets are the ones that will still be there tomorrow.

    `trade_done` makes it resumable and stops a second run re-walking what is
    already held.
    """
    families = recorded_families()
    slots = ",".join("?" * len(families))
    targets = con.execute(
        f"""select m.ticker, m.volume from markets m
           left join trade_done d on d.ticker = m.ticker
           where m.status in ('settled','finalized') and d.ticker is null
             and m.series_ticker in ({slots})
             and coalesce(m.volume,0) >= ?
           order by m.close_time asc
           limit ?""", (*families, min_volume, top)).fetchall()
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
    ap.add_argument("--pages", type=int, default=0,
                    help="stop after N pages; progress is kept, so re-running resumes")
    # Daemon mode, so this can live in runners/runners.json beside the recorders
    # rather than needing its own scheduled task. The registry's watchdog already
    # restarts a dead process after a reboot or a power cut, which is the failure
    # this job cannot survive: a day not archived is a day deleted.
    ap.add_argument("--every", type=float, default=0.0,
                    help="hours between passes. 0 = run once and exit")
    ap.add_argument("--raw", action="store_true",
                    help="also store each market's full payload (about 10x the disk)")
    ap.add_argument("--all", action="store_true",
                    help="include the combinatorial families excluded by default")
    args = ap.parse_args()
    global KEEP_RAW, EXCLUDE
    KEEP_RAW = args.raw
    EXCLUDE = set() if args.all else set(EXCLUDE_DEFAULT)

    if not (args.series or args.markets or args.trades):
        ap.error("nothing asked for - use --series, --markets or --trades")

    claim_single_instance()
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
