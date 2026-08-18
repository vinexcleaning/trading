"""THE WIDE RECORDER - stage 1 of the factory, and the only irreversible one.

`bot-hunt/data/record.db` covers 19 Kalshi series. The exchange lists 13,133.
Kalshi's history window is roughly 69 days and rolling and a closed market 404s
forever, so **every day a family is not recorded is a day of its history that no
amount of money will ever buy back.** This is the script that fixes that.

WHAT IT IS NOT. It is not a replacement for `bot-hunt/src/record.py` and it does
not touch it, restart it, compete with it, or write its database file. That
recorder keeps its 19 families, its Pinnacle feed and its Polymarket feed
exactly as they are. This one ADDS, in its own file, in this folder. The rule
from `STRATEGY_FACTORY.md` stage 1 is "Add, never replace", and the 62 GB tape
is the best asset in this repo.

---

THE MEASUREMENT THAT MAKES THIS POSSIBLE (see `reports/RESULT_LIST_QUOTES.md`).

`bot-hunt/src/venues.py` says in its docstring, as an inherited trap:

    "Kalshi list endpoints null out bid/ask; quotes only come off the
     per-market orderbook endpoint."

**That is no longer true, and it was checked rather than assumed.** The list
endpoint returns `yes_bid_dollars` / `yes_ask_dollars` / `yes_bid_size_fp` /
`yes_ask_size_fp`, and on 168 markets across 23 series those agreed with the
per-market orderbook on 100% of bids and 94% of asks - every disagreement being
one tick on a market that moved between the two requests, plus the two Exotics
parlay families where the list quote is stale against an empty book.

The consequence is the whole design. Top-of-book for a thousand markets costs
ONE request. The per-market orderbook route would be 0.35 s per market, which
on 835,422 open markets is 81 hours for a single pass. So:

    TIER A   full orderbook ladder, every cycle.     Expensive, narrow.
    TIER B   top-of-book from the list endpoint.     Cheap, very wide.

TIER A is where a strategy is live and where the capacity question - "what
would it cost to put $500 into this thin market" - has to be answerable by
walking a real ladder. TIER B is the long tail, and it exists so that when a
strategy for weather or crypto or an economic release is written next month,
the tape to test it on already exists.

---

THE CHANGE-ONLY RULE, and why it is lossless.

Most Kalshi markets do not move for hours. Writing an identical row every five
minutes for 80,000 markets is how a disk dies. So a TIER B row is written only
when the quote CHANGED from the last one recorded for that ticker.

That is lossless for reconstruction - the tape is a change log - but it has one
failure mode that must not be silent: **"nothing changed" and "the recorder was
down" look identical.** Two things stop that:

  1. every cycle writes a `w_cycle` row whether or not anything changed, so the
     gaps in the tape are explicit and countable;
  2. every `--heartbeat` cycles, ALL rows are written regardless of change, so
     the tape has a full snapshot at a known cadence.

GUARDS #12 is the reason both are here: a crypto parse bug wrote real row
counts with empty content for 1h45m and was caught by accident.

---

    py -3 strategy-factory/src/wide.py --dry-run        one cycle, writes nothing
    py -3 strategy-factory/src/wide.py --once
    py -3 strategy-factory/src/wide.py                  runs forever
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402

DATA = ROOT / "data"
DB = DATA / "wide.db"
TIERS = DATA / "tiers.json"

SCHEMA = """
create table if not exists w_cycle (
  cycle_id integer primary key autoincrement,
  started_utc text, finished_utc text, seconds real,
  n_series_a integer, n_series_b integer,
  n_seen integer, n_changed integer, n_written integer,
  n_depth integer, heartbeat integer, note text);

-- TIER B: top of book, written only when it changed. `src` records which
-- endpoint the row came from, so a later analysis can never confuse a list
-- quote with a walked ladder.
create table if not exists w_top (
  cycle_id integer, ts_utc text, series text, ticker text,
  yes_bid_c real, yes_ask_c real, bid_size real, ask_size real,
  last_c real, volume real, open_interest real, status text, close_utc text,
  src text);
create index if not exists ix_wtop on w_top(series, ticker, ts_utc);
create index if not exists ix_wtop_ts on w_top(ts_utc);

-- TIER A: the whole ladder, both sides, as recorded. Stored as JSON because
-- the capacity question -- "what does $500 actually cost here" -- needs the
-- levels, not a summary of them. depth5_* are kept alongside so the cheap
-- query stays cheap.
create table if not exists w_depth (
  cycle_id integer, ts_utc text, series text, ticker text,
  yes_bid_c real, yes_ask_c real, bid_size real, ask_size real,
  n_yes_levels integer, n_no_levels integer,
  depth5_yes real, depth5_no real,
  yes_ladder text, no_ladder text, close_utc text);
create index if not exists ix_wdepth on w_depth(series, ticker, ts_utc);

-- Written once per ticker. The name never changes, so repeating it on every
-- snapshot would be pure duplication. This table is why a cross-venue join is
-- possible later: Kalshi outcome codes are 2-4 letters (REDA, ODK, WAVE) and
-- every other venue uses full names, which matched 3 of 218 events until
-- `yes_sub_title` was stored.
create table if not exists w_names (
  ticker text primary key, series text, event_ticker text, title text,
  yes_sub_title text, no_sub_title text, close_utc text, open_utc text,
  market_type text, strike_type text, rules_primary text, first_seen_utc text);

create table if not exists w_health (
  cycle_id integer, ts_utc text, tier text, series text,
  n_listed integer, n_quoted integer, n_two_sided integer,
  n_written integer, http_ok integer, detail text);
create index if not exists ix_wh on w_health(cycle_id, series);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------- single-instance lock ----
# Copied in shape from `bot-hunt/src/record.py`, deliberately, including the
# Windows note. That note is not style - it is a correctness trap:
#
#   CPython maps os.kill on Windows to TerminateProcess for any signal that is
#   not CTRL_C_EVENT/CTRL_BREAK_EVENT. The POSIX idiom for "does this process
#   exist" would therefore KILL THE RECORDER.
#
# It is reimplemented rather than imported because `record.py`'s version closes
# over that module's own global DB path and is not parameterised. Ten lines
# duplicated is the right trade against importing a script for one function.

def _pid_alive(pid: int) -> bool:
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
    h = k32.OpenProcess(0x00100000, False, pid)      # SYNCHRONIZE
    if not h:
        return False
    alive = k32.WaitForSingleObject(h, 0) == 0x00000102   # WAIT_TIMEOUT
    k32.CloseHandle(h)
    return bool(alive)


def claim_single_instance(db: Path) -> None:
    lock = db.with_suffix(db.suffix + ".lock")
    db.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            held = json.loads(lock.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            held = {}
        pid = held.get("pid")
        if isinstance(pid, int) and pid != os.getpid() and _pid_alive(pid):
            print("already running: pid %s owns %s since %s -- exiting "
                  "without touching it" % (pid, db.name, held.get("started")),
                  flush=True)
            raise SystemExit(0)
        if pid:
            print("stale lock from pid %s (%s) - that process is gone, "
                  "taking over" % (pid, held.get("started")), flush=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "db": str(db),
                                "started": now(), "argv": sys.argv[1:]}),
                    encoding="utf-8")
    import atexit
    atexit.register(lambda: lock.unlink(missing_ok=True))


def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, timeout=120.0)
    con.execute("pragma journal_mode=WAL")
    con.execute("pragma busy_timeout=120000")
    con.executescript(SCHEMA)
    return con


# ------------------------------------------------------------- quoting ----

def quote_of(m):
    """(yes_bid_c, yes_ask_c, bid_size, ask_size) from a LIST row.

    Kalshi encodes "no bid" as 0.0000 and "no ask" as 1.0000 on the list side,
    where the orderbook endpoint has no level at all. Normalising both to None
    is not cosmetic: scoring an absent bid as a 0-cent bid would make every
    dead market read as quoted, and the whole tier split is decided on that
    number. GUARDS #23 - a missing field must not become a silent zero.

    Cents are rounded to 2 dp because Kalshi returns dollar strings that float
    to 55.00000000000001, and unrounded dust would make the change-only rule
    fire on every cycle for markets that never moved.
    """
    yb = V.fnum(m.get("yes_bid_dollars"))
    ya = V.fnum(m.get("yes_ask_dollars"))
    yb = None if yb in (None, 0.0) else round(yb * 100.0, 2)
    ya = None if ya in (None, 1.0) else round(ya * 100.0, 2)
    bs = V.fnum(m.get("yes_bid_size_fp"))
    asz = V.fnum(m.get("yes_ask_size_fp"))
    return yb, ya, bs, asz


def name_row(m, ts):
    return (m.get("ticker"), V.series_of(m.get("ticker") or ""),
            m.get("event_ticker"), m.get("title"), m.get("yes_sub_title"),
            m.get("no_sub_title"), m.get("close_time"), m.get("open_time"),
            m.get("market_type"), m.get("strike_type"),
            (m.get("rules_primary") or "")[:1200], ts)


# ------------------------------------------------------------- the tiers ----

def load_tiers():
    if not TIERS.exists():
        raise SystemExit(
            "no %s -- run `py -3 strategy-factory/src/tiers.py` first. The "
            "tier list is built from a measurement, never hand-written."
            % TIERS)
    d = json.loads(TIERS.read_text(encoding="utf-8"))
    return d["tier_a"], d["tier_b"], d


# -------------------------------------------------------------- one cycle ----

def list_series(series: str):
    """Every open market in one series, with its list quote. TIER A only."""
    out = []
    for m in V.k_paginate("/markets",
                          {"series_ticker": series, "status": "open",
                           "limit": 1000}, "markets", max_pages=6):
        if m.get("ticker"):
            out.append(m)
    return out


def sweep_exchange():
    """Every open market on the exchange, in ~785 requests. TIER B.

    ⚠ THIS REPLACED A PER-SERIES LOOP, AND THE ARITHMETIC IS WHY.

    v1 fetched tier B one series at a time, on the reasoning that asking for
    the families we want beats downloading 700,000 parlay markets we do not.
    That reasoning was right about bandwidth and **wrong about the thing that
    actually costs**, which is requests:

        tier B, one request per SERIES     3,357 requests
        tier B, one exchange-wide sweep      785 requests

    Four times cheaper, because a sweep returns 1,000 markets of ANY series per
    request while a per-series call returns one family's worth however small
    that family is - and the median tier B series has 3 open markets. The
    parlay payload is wasted bytes, not wasted requests, and bytes are not the
    constraint. Measured, not estimated: `reports/SHAPE.md` section 1.

    It also fixes something the per-series loop could not: a series that did
    not exist when `tiers.json` was built is invisible to a per-series loop
    forever, and arrives on its own in a sweep.
    """
    for m in V.k_paginate("/markets", {"status": "open", "limit": 1000},
                          "markets", max_pages=4000):
        if m.get("ticker"):
            yield m


def _flush(con, names, tops, dry):
    if dry:
        return
    if names:
        con.executemany("insert or ignore into w_names values "
                        "(?,?,?,?,?,?,?,?,?,?,?,?)", names)
    if tops:
        con.executemany("insert into w_top values "
                        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tops)


def cycle_b(con, tier_b, drop, cid, heartbeat, last, dry):
    """TIER B: one exchange-wide sweep, filtered on write.

    The filter is applied to what is WRITTEN, not to what is fetched, because
    the sweep returns everything anyway. `drop` holds the parlay families,
    excluded by name as well as by measurement (DECISIONS.md D5) - a single
    quoted leg would otherwise drag 614,573 markets onto the tape.

    A series that is in neither `tier_b` nor `drop` is NEW since the tier list
    was built. It is recorded, and counted separately, because a family
    appearing for the first time is exactly the thing a rolling 69-day window
    makes expensive to notice late.
    """
    ts = now()
    n_seen = n_changed = n_new_series = 0
    names, tops = [], []
    per_series = {}
    for m in sweep_exchange():
        tk = m["ticker"]
        series = V.series_of(tk)
        if series in drop:
            continue
        known = series in tier_b
        if not known:
            n_new_series += 1
        yb, ya, bs, asz = quote_of(m)
        if yb is None and ya is None and not known:
            continue          # unknown AND unquoted: not worth a row
        n_seen += 1
        st = per_series.setdefault(series, [0, 0, 0])
        st[0] += 1
        st[1] += int(yb is not None or ya is not None)
        st[2] += int(yb is not None and ya is not None)
        key = (yb, ya, bs, asz, m.get("status"))
        prev = last.get(tk)
        if prev != key:
            n_changed += 1
        if prev != key or heartbeat:
            last[tk] = key
            tops.append((cid, ts, series, tk, yb, ya, bs, asz,
                         V.fnum(m.get("last_price_dollars")),
                         V.fnum(m.get("volume_fp")),
                         V.fnum(m.get("open_interest_fp")),
                         m.get("status"), m.get("close_time"), "list"))
        names.append(name_row(m, ts))
        # Flush in batches. A whole sweep held in memory is ~800,000 rows and
        # the process that dies is the one holding tape nobody can re-pull.
        if len(names) >= 5000:
            _flush(con, names, tops, dry)
            names, tops = [], []
    _flush(con, names, tops, dry)
    if not dry:
        con.executemany("insert into w_health values (?,?,?,?,?,?,?,?,?,?)",
                        [(cid, ts, "B", s, v[0], v[1], v[2], 0, 1, None)
                         for s, v in per_series.items()])
        con.commit()
    return n_seen, n_changed, n_new_series, len(per_series)


def cycle_a(con, tier_a, cid, dry, depth_cap, depth_levels):
    """TIER A: walk the real ladder, per series, on the soonest-closing markets.

    Soonest-closing rather than largest-volume, for the reason `record.py`
    fixed on 2026-08-06 (BH014): an unspecified server-side ordering starved
    ~40 of KXMLBGAME's markets on every cycle and nothing said so. A pre-match
    strategy trades the market about to settle, so close_time ascending is the
    ordering that matters, and markets with no close_time sort LAST - an absent
    field must never win a priority contest.
    """
    ts = now()
    n_depth = 0
    for series in tier_a:
        try:
            mkts = list_series(series)
        except Exception:                                      # noqa: BLE001
            if not dry:
                con.execute(
                    "insert into w_health values (?,?,?,?,?,?,?,?,?,?)",
                    (cid, ts, "A", series, 0, 0, 0, 0, 0,
                     traceback.format_exc()[-300:]))
            continue
        mkts.sort(key=lambda m: (m.get("close_time") is None,
                                 m.get("close_time") or "",
                                 m.get("ticker") or ""))
        drows = []
        for m in mkts[:depth_cap]:
            ylv, nlv = V.k_orderbook(m["ticker"], depth=depth_levels)
            if ylv is None and nlv is None:
                continue
            yb, ya, bs, asz = V.k_touch(ylv, nlv)
            d5y = sum(sz for p, sz in (ylv or [])
                      if yb is not None and p >= yb - 5)
            nb = nlv[-1][0] if nlv else None
            d5n = sum(sz for p, sz in (nlv or [])
                      if nb is not None and p >= nb - 5)
            drows.append((cid, ts, series, m["ticker"], yb, ya, bs, asz,
                          len(ylv or []), len(nlv or []), d5y, d5n,
                          json.dumps([[round(p, 2), s] for p, s in (ylv or [])]),
                          json.dumps([[round(p, 2), s] for p, s in (nlv or [])]),
                          m.get("close_time")))
        if drows and not dry:
            con.executemany("insert into w_depth values "
                            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", drows)
            con.executemany("insert or ignore into w_names values "
                            "(?,?,?,?,?,?,?,?,?,?,?,?)",
                            [name_row(m, ts) for m in mkts[:depth_cap]])
            con.execute("insert into w_health values (?,?,?,?,?,?,?,?,?,?)",
                        (cid, ts, "A", series, len(mkts), len(drows),
                         sum(1 for r in drows if r[4] is not None
                             and r[5] is not None), len(drows), 1, None))
            con.commit()
        n_depth += len(drows)
    return n_depth


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["a", "b"], required=True,
                    help="which tier this process runs. They are SEPARATE "
                         "processes with SEPARATE database files because two "
                         "writers on one SQLite file died with 'database is "
                         "locked' inside 19 minutes here on 2026-08-09, and "
                         "because the two tiers want different cadences.")
    ap.add_argument("--interval", type=float, default=600.0)
    ap.add_argument("--minutes", type=float, default=0.0, help="0 = forever")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="one cycle, no writes, print what it would cost")
    ap.add_argument("--heartbeat", type=int, default=12,
                    help="tier B: every Nth cycle writes every row, changed "
                         "or not, so 'quiet' and 'dead' stay distinguishable")
    ap.add_argument("--depth-cap", type=int, default=25,
                    help="tier A: markets per series to walk the ladder on")
    ap.add_argument("--depth-levels", type=int, default=20)
    ap.add_argument("--db", default="")
    args = ap.parse_args()

    db = Path(args.db) if args.db else (
        DATA / ("wide_depth.db" if args.tier == "a" else "wide_top.db"))
    tier_a, tier_b, meta = load_tiers()
    drop = set(meta.get("dropped", {}).get("exotic_parlay", []))
    tier_b_set = set(tier_b)
    print("wide recorder  tier=%s  db=%s" % (args.tier.upper(), db), flush=True)
    print("  tier A (full ladder) : %d series, %d markets each"
          % (len(tier_a), args.depth_cap), flush=True)
    print("  tier B (top of book) : %d series, %d parlay families dropped"
          % (len(tier_b), len(drop)), flush=True)
    print("  tier list built %s from %s"
          % (meta.get("built_utc"), meta.get("source")), flush=True)

    if args.dry_run:
        con = sqlite3.connect(":memory:")
        con.executescript(SCHEMA)
        t0 = time.time()
        if args.tier == "a":
            dep = cycle_a(con, tier_a, 1, True, args.depth_cap,
                          args.depth_levels)
            print("\nDRY RUN tier A - nothing written")
            print("  ladders that would be walked : %d" % dep)
        else:
            seen, chg, newser, nser = cycle_b(con, tier_b_set, drop, 1, True,
                                              {}, True)
            print("\nDRY RUN tier B - nothing written")
            print("  markets kept in one sweep    : %d" % seen)
            print("  series seen                  : %d" % nser)
            print("  markets in series NOT in the tier list (new since it "
                  "was built) : %d" % newser)
        dt = time.time() - t0
        print("  seconds for one cycle        : %.0f" % dt)
        print("  at --interval %.0f s that is %.2f cycles an hour"
              % (args.interval, 3600.0 / max(args.interval, dt)))
        return

    claim_single_instance(db)
    con = connect(db)
    # Seed the change detector from the tape, so a restart does not rewrite
    # every row it already has. Without this, a recorder that the watchdog
    # restarts every ten minutes would write a full snapshot every ten minutes
    # and the change-only rule would quietly stop saving anything -- a saving
    # that silently stops is worse than one that was never claimed.
    last = {}
    if args.tier == "b":
        for tk, yb, ya, bs, asz, st in con.execute(
                "select ticker, yes_bid_c, yes_ask_c, bid_size, ask_size, "
                "status from w_top where rowid in "
                "(select max(rowid) from w_top group by ticker)"):
            last[tk] = (yb, ya, bs, asz, st)
        print("  change detector seeded from %d tickers already on tape"
              % len(last), flush=True)

    n_done = con.execute("select count(*) from w_cycle").fetchone()[0]
    t_end = time.time() + args.minutes * 60 if args.minutes else None
    while True:
        t0 = time.time()
        cur = con.execute("insert into w_cycle (started_utc) values (?)",
                          (now(),))
        cid = cur.lastrowid
        con.commit()
        hb = args.tier == "b" and (n_done % max(args.heartbeat, 1)) == 0
        seen = chg = dep = newser = 0
        note = None
        try:
            if args.tier == "a":
                dep = cycle_a(con, tier_a, cid, False, args.depth_cap,
                              args.depth_levels)
                seen = dep
            else:
                seen, chg, newser, _ = cycle_b(con, tier_b_set, drop, cid, hb,
                                               last, False)
        except Exception:                                      # noqa: BLE001
            note = traceback.format_exc()[-1500:]
        dt = time.time() - t0
        # Count the rows THIS tier writes. Reading w_top for tier A printed
        # `wrote=0` on a cycle that had just written 900 ladders, which is the
        # shape of a health number that quietly lies.
        wrote = con.execute(
            "select count(*) from %s where cycle_id=?"
            % ("w_depth" if args.tier == "a" else "w_top"),
            (cid,)).fetchone()[0]
        con.execute("update w_cycle set finished_utc=?, seconds=?, "
                    "n_series_a=?, n_series_b=?, n_seen=?, n_changed=?, "
                    "n_written=?, n_depth=?, heartbeat=?, note=? "
                    "where cycle_id=?",
                    (now(), round(dt, 1), len(tier_a), len(tier_b), seen, chg,
                     wrote, dep, int(hb),
                     note if note else
                     ("new-series markets=%d" % newser if newser else None),
                     cid))
        con.commit()
        print("cycle %d %s %.0fs tier=%s seen=%d changed=%d wrote=%d depth=%d"
              "%s%s" % (cid, now(), dt, args.tier.upper(), seen, chg, wrote,
                        dep, " HEARTBEAT" if hb else "",
                        (" ERR " + note[:120]) if note else ""), flush=True)
        n_done += 1
        if args.once:
            break
        if t_end and time.time() > t_end:
            break
        time.sleep(max(5.0, args.interval - (time.time() - t0)))
    con.close()


if __name__ == "__main__":
    main()
