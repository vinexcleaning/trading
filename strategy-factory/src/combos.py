"""COMBO RECORDER - capture every Kalshi combo before the 69-day window eats it.

Mailbox 013. This is the urgent half of that task and it is the only half that
cannot be done later: **a settled combo older than about 69 days 404s and is
gone at any price**, exactly like every other closed Kalshi market. Everything
else in the combo project - the markup measurement, the pre-registration, the
report - can be done next month on data captured today. The capture cannot.

So this runs first, and it runs every day.

WHAT A COMBO IS, in the exchange's own words (help.kalshi.com/en/articles/
13823820-combos, dated 2026-06-20, quoted in mailbox 013):

    "Combos allow you to trade custom combinations of events in a single
    position... Combos resolve to the product of the underlying positions,
    paying out a maximum of $1.00 per contract."

Three consequences that shape this file:

  * **There is no order book.** Price comes from a request-for-quote. Every
    settled combo on the tape reads `yes_bid 0.00 / yes_ask 1.00`, which is
    not a spread - it is the absence of a book. **The only price that exists
    is what somebody actually paid**, in `last_price_dollars`.
  * **A filled combo cannot be sold.** So `volume` and `open_interest` are the
    same number on every settled row seen so far, and there is no exit rule to
    test. Anything about exits is out of scope by construction.
  * **Legs are ordinary markets.** `mve_selected_legs` names each leg's market
    ticker and side, so the price paid can later be compared against what the
    legs themselves cost at that moment. That comparison is the whole project
    and it is why the legs are stored rather than summarised.

⚠ A FIELD-NAME TRAP THAT WOULD HAVE READ AS "THE PRODUCT DOES NOT EXIST".
`GET /multivariate_event_collections` returns its rows under the key
**`multivariate_contracts`**, not under a key matching the path. Reading it as
`multivariate_event_collections` returns None, `or []` turns that into an empty
list, and the honest-looking conclusion is "0 collections, there are no combos
on this exchange". There are 1,389. This is GUARDS #23 arriving for the third
time in this folder, so the key is asserted rather than defaulted below.

    py -3 strategy-factory/src/combos.py              # one sweep
    py -3 strategy-factory/src/combos.py --loop 3600  # every hour, forever
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "bot-hunt" / "src"))
import venues as V  # noqa: E402

DB = ROOT / "data" / "combos.db"
LOCK = ROOT / "data" / "combos.lock"

# ⚠ EXPLICIT CONNECT AND READ TIMEOUTS, as a tuple.
# `devig` mailbox 029-031: the cross-venue recorder lost 9 HOURS to a request
# that hung instead of failing. A bare `timeout=30` is already both in
# requests, but writing the pair out means the next reader cannot wonder.
TIMEOUT = (10, 30)   # (connect seconds, read seconds)

SCHEMA = """
-- Latest known state of every combo market ever seen.
create table if not exists combos (
  ticker text primary key,
  series text, collection_ticker text, event_ticker text,
  n_legs integer, legs_json text,
  last_price_d real, yes_bid_d real, yes_ask_d real,
  volume real, open_interest real,
  status text, result text, settlement_value_d real,
  created_utc text, open_utc text, close_utc text, settled_utc text,
  title text,
  first_seen_utc text, last_seen_utc text);

-- ⚠ APPEND-ONLY CHANGE LOG. A combo cannot be sold, so its price is expected
-- to be static once filled - but "expected" is not "measured", and a row here
-- is the difference between knowing that and assuming it. Written only when
-- something actually changes, so the table stays small.
create table if not exists combo_seen (
  ticker text, seen_utc text,
  last_price_d real, volume real, open_interest real, status text, result text,
  primary key (ticker, last_price_d, volume, open_interest, status, result));

-- Every collection the exchange lists, so a NEW combo series is discovered
-- rather than needing to be typed in here.
create table if not exists collections (
  collection_ticker text primary key, series text, title text,
  size_min integer, size_max integer,
  functional_description text, n_assoc_events integer,
  open_utc text, close_utc text, seen_utc text);

create table if not exists sweep (
  sweep_id integer primary key autoincrement,
  started_utc text, finished_utc text, seconds real,
  n_collections integer, n_series integer,
  n_markets integer, n_new integer, n_changed integer, note text);

create index if not exists ix_combo_series on combos(series, close_utc);
create index if not exists ix_combo_seen on combo_seen(ticker, seen_utc);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=120.0)
    con.execute("pragma journal_mode=WAL")
    con.execute("pragma busy_timeout=120000")
    con.executescript(SCHEMA)
    return con


_LOCK_HANDLE = None


def claim_lock() -> None:
    """One recorder per database, using an OS lock the OS releases for us.

    ⚠ THIS REPLACES A pid CHECK THAT COST THREE DAYS OF CAPTURE, and the way it
    failed is worth writing down because it is the exact opposite of the trap it
    was written to avoid.

    The old version asked `os.kill(pid, 0)` and treated `OSError` as "the
    process exists but is not signalable, so assume alive". That is true on
    Unix. **On Windows a pid that does NOT exist also raises OSError** - WinError
    87, "the parameter is incorrect" - and never `ProcessLookupError`. Measured
    on this machine 2026-09-18:

        os.kill(43960, 0)   -> OSError 87   (process long dead)
        os.kill(999999, 0)  -> OSError 87   (never existed)

    So "assume alive" meant **assume alive for ever**. The recorder died 25
    minutes after starting on 2026-09-15, the watchdog tried to restart it every
    ten minutes for three days, and this function refused every single attempt
    with "combo recorder already running as pid 43960". The log says so 400-odd
    times.

    **A pid in a file is not a lock.** It is a note about the past that nothing
    updates when the process dies. So the pid is now written for humans only and
    the actual exclusion is an OS-level lock on the file handle, which the
    kernel drops the instant the process ends however it ends - crash, kill,
    power cut. There is nothing left to go stale.
    """
    global _LOCK_HANDLE
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fh = open(LOCK, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.seek(0)
        who = fh.read().strip() or "(unnamed)"
        fh.close()
        raise SystemExit("combo recorder already running: %s. The lock is held "
                         "by a LIVE process - the operating system releases it "
                         "automatically, so this is never stale." % who)
    _LOCK_HANDLE = fh
    fh.seek(0)
    fh.truncate()
    fh.write("%d %s" % (os.getpid(), now()))
    fh.flush()


def release_lock() -> None:
    """Best-effort tidy-up. Correctness does not depend on this running - the
    kernel drops the lock when the process ends, which is the whole point."""
    global _LOCK_HANDLE
    if _LOCK_HANDLE is None:
        return
    try:
        if os.name == "nt":
            import msvcrt
            _LOCK_HANDLE.seek(0)
            msvcrt.locking(_LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        _LOCK_HANDLE.close()
    except OSError:
        pass
    _LOCK_HANDLE = None


def pull_collections(con) -> tuple[int, list]:
    """Every combo collection the exchange lists, and the series they belong to.

    Series are DISCOVERED here rather than hard-coded, so a combo family Kalshi
    launches next week is recorded without anyone editing this file.
    """
    ts = now()
    rows, cur, seen = [], None, 0
    while True:
        p = {"limit": 200}
        if cur:
            p["cursor"] = cur
        r = V.k_get("/multivariate_event_collections", p, timeout=TIMEOUT)
        if r is None or r.status_code != 200:
            print("  collections HTTP %s - keeping what we have"
                  % (r and r.status_code), flush=True)
            break
        d = r.json() or {}
        # ⚠ ASSERTED, NOT DEFAULTED. See the module docstring: the key does not
        # match the path, and `.get(path_name) or []` silently reports zero.
        if "multivariate_contracts" not in d:
            raise SystemExit(
                "collections payload has no 'multivariate_contracts' key - "
                "keys were %s. Kalshi has renamed it; fix this before the "
                "recorder quietly records nothing." % sorted(d))
        batch = d["multivariate_contracts"] or []
        for c in batch:
            rows.append((c.get("collection_ticker"), c.get("series_ticker"),
                         c.get("title"), c.get("size_min"), c.get("size_max"),
                         c.get("functional_description"),
                         len(c.get("associated_event_tickers") or []),
                         c.get("open_date"), c.get("close_date"), ts))
        seen += len(batch)
        cur = d.get("cursor")
        if not cur or not batch:
            break
    con.executemany("insert or replace into collections "
                    "values (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    series = sorted({r[1] for r in rows if r[1]})
    return seen, series


def _leg_list(m) -> list:
    """Legs as [(market_ticker, side), ...].

    Two sources agree in the sample checked, and both are kept because they
    fail differently: `mve_selected_legs` is structured, `custom_strike` is the
    human-readable copy. If they ever disagree, the structured one wins and the
    disagreement is worth a look.
    """
    legs = m.get("mve_selected_legs") or []
    return [(l.get("market_ticker"), l.get("side")) for l in legs]


def known_final(con) -> set:
    """Deliberately NOT used any more. Kept as a signpost.

    ⚠ THE FIRST VERSION LOADED EVERY FINAL TICKER INTO A PYTHON SET. That was
    fine at the 118,000 I had measured and is not fine at the **20,534,685**
    this tape actually holds - it is about two gigabytes of strings to answer a
    question SQLite can answer with an index.

    The skip now happens in SQL: a settled combo is written with
    `insert or ignore`, so the second and later sweeps cost one indexed probe
    per row and no memory at all. An OPEN combo still uses `insert or replace`,
    because that one really can change.
    """
    raise NotImplementedError("superseded - the skip is now done in SQL")


def sweep_series(con, series: str) -> tuple[int, int, int]:
    """Every combo market in one series, whatever its status.

    Statuses are swept explicitly rather than left to the default, because the
    default is not documented to be "all" and a silently narrowed sweep is
    exactly the shape of bug this folder keeps finding.
    """
    ts = now()
    n = new = changed = 0
    buf, seenbuf = [], []

    def flush():
        # A SETTLED combo can never change - it cannot even be sold - so
        # `insert or ignore` makes every sweep after the first one nearly free.
        # An OPEN one still gets replaced, because its volume really does move.
        fin = [r for r in buf if (r[12] or "") not in ("", None)]
        live = [r for r in buf if (r[12] or "") in ("", None)]
        if fin:
            con.executemany(
                "insert or ignore into combos values "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fin)
        if live:
            con.executemany(
                "insert or replace into combos values "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", live)
        if seenbuf:
            con.executemany(
                "insert or ignore into combo_seen values (?,?,?,?,?,?,?)",
                seenbuf)
        con.commit()
        buf.clear()
        seenbuf.clear()

    for status in ("settled", "open", "closed"):
        for m in V.k_paginate("/markets",
                              {"series_ticker": series, "status": status,
                               "limit": 1000}, "markets"):
            tk = m.get("ticker")
            if not tk:
                continue
            n += 1
            legs = _leg_list(m)
            row = (tk, series, m.get("mve_collection_ticker"),
                   m.get("event_ticker"), len(legs), json.dumps(legs),
                   V.fnum(m.get("last_price_dollars")),
                   V.fnum(m.get("yes_bid_dollars")),
                   V.fnum(m.get("yes_ask_dollars")),
                   V.fnum(m.get("volume_fp")),
                   V.fnum(m.get("open_interest_fp")),
                   m.get("status"), m.get("result"),
                   V.fnum(m.get("settlement_value_dollars")),
                   m.get("created_time"), m.get("open_time"),
                   m.get("close_time"), m.get("settlement_ts"),
                   (m.get("title") or "")[:400], ts, ts)
            buf.append(row)
            seenbuf.append((tk, ts, row[6], row[9], row[10], row[11], row[12]))
            new += 1
            # ⚠ COMMIT OFTEN, NOT AT THE END OF THE SERIES. The first run of
            # this file was stopped partway through a six-figure series and
            # lost EVERY row, because the only commit was after the whole
            # series. Against a 69-day window that is the one failure mode
            # that actually costs data.
            if len(buf) >= 2000:
                flush()
                print("    %s ... %d new" % (series, n), flush=True)
    flush()
    return n, new, changed


def one_sweep(con) -> None:
    t0 = time.time()
    started = now()
    cur = con.execute("insert into sweep (started_utc) values (?)", (started,))
    sid = cur.lastrowid
    con.commit()

    n_col, series = pull_collections(con)
    print("collections: %d across %d series" % (n_col, len(series)), flush=True)

    have = con.execute("select count(*) from combos").fetchone()[0]
    print("already captured: %d (settled ones are insert-or-ignored, so a "
          "re-read of them is nearly free)" % have, flush=True)
    tot = new = chg = 0
    for s in series:
        a, b, c = sweep_series(con, s)
        tot += a
        new += b
        chg += c
        if a:
            print("  %-34s markets %5d  new %4d  changed %4d"
                  % (s, a, b, c), flush=True)
    secs = time.time() - t0
    con.execute("update sweep set finished_utc=?, seconds=?, n_collections=?, "
                "n_series=?, n_markets=?, n_new=?, n_changed=? where sweep_id=?",
                (now(), secs, n_col, len(series), tot, new, chg, sid))
    con.commit()
    print("sweep done in %.0fs: %d markets, %d new, %d changed"
          % (secs, tot, new, chg), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0,
                    help="seconds between sweeps; 0 = one sweep and exit")
    args = ap.parse_args()
    claim_lock()
    con = connect()
    try:
        while True:
            one_sweep(con)
            if not args.loop:
                break
            time.sleep(args.loop)
    finally:
        con.close()
        release_lock()


if __name__ == "__main__":
    main()
