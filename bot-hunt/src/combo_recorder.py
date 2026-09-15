"""Mailbox 032: capture Kalshi COMBOS before they age out of the 69-day window.

Kalshi's parlays are "combos" -- multivariate event collections. They are public
and need no authentication, and **settled ones disappear with the rest of the
~69-day window, so whatever is not captured now cannot be captured later.** That
is the whole reason this exists today rather than in a queue.

Read-only. No orders, no Request For Quote creation, no account, no credential.

WHAT ONE ROW IS
---------------
    combos       one row per combo market per READ DAY -- the quote moves, so a
                 settled combo captured twice on different days is two rows.
    combo_legs   one row per LEG, written once per combo ticker. The analysis is
                 a join from combo to leg, so legs are rows and never a string.

THREE THINGS THE INSTRUCTION GOT RIGHT AND I HAVE HONOURED
-----------------------------------------------------------
1. **Explicit connect AND read timeout on every request**, as a tuple, plus a
   sweep deadline -- because `requests`' timeout is per socket operation and not
   a total, which is exactly how the cross-venue recorder lost nine hours
   (mailboxes 029-031). See `_kget` and `Deadline`.
2. **Registered in BOTH registries**, per CLAUDE.md section 10.
3. **`bid 0.00 / ask 1.00` is the NORMAL state for a combo and is NOT filtered.**
   Combos are priced by Request For Quote: nothing rests on the book until
   somebody asks. Every other recorder here sensibly drops rows with no
   two-sided quote; doing that here would store nothing at all.

⚠ TWO CORRECTIONS TO THE INSTRUCTION, both the renamed-field trap (GUARDS #12)
------------------------------------------------------------------------------
* It asks to store "volume, open interest". **`volume` and `open_interest` are
  BOTH `null` on every combo market.** The live fields are `volume_fp`,
  `volume_24h_fp` and `open_interest_fp`. Reading the names as given would have
  stored a column of nulls and nobody would have noticed until the analysis.
* It describes the legs as `custom_strike."Associated Events"`, a comma string.
  **There is a structured field -- `mve_selected_legs` -- carrying
  `event_ticker`, `market_ticker` and `side` per leg as objects.** The comma
  strings exist too, in THREE parallel lists that have to stay aligned by index;
  using them would have been a misalignment bug waiting to happen. The
  structured field is used, and the comma strings are used only as a
  cross-check that the leg count agrees.

⚠ AND ONE ON THE ENDPOINT: the collections listing returns its rows under
`multivariate_contracts`, not `multivariate_event_collections`. Reading the
obvious key returns **zero collections** and looks exactly like "there are
none".
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

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

DB = ROOT / "data" / "combos.db"
UA = {"User-Agent": "bot-hunt-research/1.0"}
SESSION = requests.Session()

# (connect, read). A connect-only timeout is the usual mistake and a single
# scalar hides which half failed. Short connect: a venue that will not answer
# should fail in seconds, not half a minute.
TIMEOUT = (5, 25)
SWEEP_BUDGET_S = 900.0          # 15 minutes for the whole sweep, checked between calls

SERIES = [
    "KXMVESPORTSMULTIGAMEEXTENDED",   # cross-game parlays -- the ones he means
    "KXMVECROSSCATEGORY",
    "KXMVECROSSCATEGORY-SHARD1",
    "KXMVENFLSINGLEGAME",
    "KXMVENBASINGLEGAME",
]

SCHEMA = """
create table if not exists sweeps (
  sweep_id integer primary key autoincrement,
  started_utc text, finished_utc text, seconds real,
  n_combos integer, n_legs integer, truncated integer, note text);

create table if not exists combos (
  read_date text, read_utc text, sweep_id integer,
  ticker text, event_ticker text, series_ticker text, collection_ticker text,
  status text, result text, close_utc text, open_utc text, settlement_utc text,
  n_legs integer,
  last_price_c real, yes_bid_c real, yes_ask_c real,
  no_bid_c real, no_ask_c real,
  yes_bid_size real, volume real, volume_24h real, open_interest real,
  liquidity_dollars real, title text,
  primary key (ticker, read_date));

create table if not exists combo_legs (
  ticker text, leg_index integer,
  leg_event_ticker text, leg_market_ticker text, leg_side text,
  first_seen_utc text,
  primary key (ticker, leg_index));
create index if not exists ix_leg on combo_legs(leg_market_ticker);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_alive(pid: int) -> bool:
    """⚠ Never os.kill(pid, 0) on Windows -- CPython maps it to TerminateProcess."""
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
    h = k32.OpenProcess(0x00100000, False, pid)
    if not h:
        return False
    alive = k32.WaitForSingleObject(h, 0) == 0x00000102
    k32.CloseHandle(h)
    return bool(alive)


def claim_lock() -> None:
    lock = DB.with_suffix(DB.suffix + ".lock")
    DB.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            held = json.loads(lock.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            held = {}
        pid = held.get("pid")
        if isinstance(pid, int) and pid != os.getpid() and _pid_alive(pid):
            print(f"already running: pid {pid} owns {DB.name} -- exiting", flush=True)
            raise SystemExit(0)
        if pid:
            print(f"stale lock from pid {pid}; taking over", flush=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "started": now()}),
                    encoding="utf-8")
    import atexit
    atexit.register(lambda: lock.unlink(missing_ok=True))


class Deadline:
    """A wall-clock budget, checked BETWEEN requests and never inside one."""

    def __init__(self, budget_s: float):
        self.until = time.time() + budget_s
        self.tripped = False

    def expired(self) -> bool:
        if time.time() >= self.until:
            self.tripped = True
        return self.tripped


def _kget(path: str, params: dict, tries: int = 3):
    """Kalshi GET with an explicit (connect, read) timeout and bounded retries."""
    url = V.KALSHI + path
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, headers=UA, timeout=TIMEOUT)
        except requests.RequestException:
            time.sleep(1.0 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(1.5 * (i + 1))
            continue
        return r
    return None


def c(v):
    """Dollars -> cents, or None. Never coerce a missing price to zero."""
    f = V.fnum(v)
    return None if f is None else f * 100.0


def sweep(con, dl: Deadline) -> tuple[int, int, bool]:
    """One pass over every combo series, open and settled. Returns counts."""
    cur = con.execute("insert into sweeps (started_utc) values (?)", (now(),))
    sid = cur.lastrowid
    con.commit()
    read_utc = now()
    read_date = read_utc[:10]
    n_combos = n_legs = 0

    for series in SERIES:
        for status in ("open", "settled"):
            if dl.expired():
                print(f"   ⚠ sweep budget exhausted before {series}/{status}",
                      flush=True)
                con.execute("update sweeps set truncated=1 where sweep_id=?", (sid,))
                con.commit()
                return n_combos, n_legs, True
            # ⚠ NO ARBITRARY PAGE CAP. The first run of this recorder capped at
            # 40 pages and three series came back on EXACTLY 8,000 -- which is
            # 40 x 200, i.e. the cap, not the data. That is the same failure as
            # BH014 (the recorder probed mkts[:60] in an undocumented order and
            # starved 40 markets a cycle) and as the blind-spot census that
            # returned zero baseball. **A round number equal to your own limit is
            # never a measurement.** The cursor is now followed until it runs
            # out; the sweep DEADLINE is what bounds this, not a page count,
            # because a deadline cannot silently truncate without saying so.
            cursor, page, got, stalls = None, 0, 0, 0
            while True:
                if dl.expired():
                    con.execute("update sweeps set truncated=1 where sweep_id=?",
                                (sid,))
                    con.commit()
                    return n_combos, n_legs, True
                q = {"series_ticker": series, "status": status, "limit": 200}
                if cursor:
                    q["cursor"] = cursor
                r = _kget("/markets", q)
                if r is None or r.status_code != 200:
                    # ⚠ A DROPPED PAGE MUST NOT ABANDON THE SERIES. The first
                    # full run printed "HTTP None" three times and each one
                    # silently ended that series' sweep wherever it happened to
                    # be -- so the cross-game family stopped at 142,400 not
                    # because it was exhausted but because one request timed
                    # out. A sweep that truncates at a random point every run,
                    # and says only "HTTP None", is worse than one that fails:
                    # the count looks like data.
                    #
                    # So the SAME cursor is retried with a longer back-off, and
                    # only a repeated failure ends the series -- loudly, and
                    # flagged on the sweep row.
                    stalls += 1
                    if stalls <= 3:
                        print(f"   {series:32} {status:8} page failed "
                              f"(attempt {stalls}) -- retrying the same cursor",
                              flush=True)
                        time.sleep(3.0 * stalls)
                        continue
                    print(f"   ⚠ {series:30} {status:8} GAVE UP after {stalls} "
                          f"failures at {got:,} rows -- this series is "
                          f"TRUNCATED, not exhausted", flush=True)
                    con.execute("update sweeps set truncated=1, note=? "
                                "where sweep_id=?",
                                (f"{series}/{status} truncated at {got} rows "
                                 f"after {stalls} page failures", sid))
                    con.commit()
                    break
                js = r.json() or {}
                mkts = js.get("markets") or []
                if not mkts:
                    break
                rows, legrows = [], []
                for m in mkts:
                    tk = m.get("ticker")
                    if not tk:
                        continue
                    legs = m.get("mve_selected_legs") or []
                    # cross-check against the comma strings the instruction named
                    cs = m.get("custom_strike") or {}
                    ev_str = (cs.get("Associated Events") or "").strip()
                    n_from_string = len([x for x in ev_str.split(",") if x])
                    if legs and n_from_string and len(legs) != n_from_string:
                        print(f"   ⚠ LEG COUNT DISAGREES on {tk}: structured "
                              f"{len(legs)} vs comma-string {n_from_string}. "
                              f"Storing the structured one.", flush=True)
                    rows.append((
                        read_date, read_utc, sid, tk, m.get("event_ticker"),
                        series, m.get("mve_collection_ticker"),
                        m.get("status"), m.get("result"), m.get("close_time"),
                        m.get("open_time"), m.get("settlement_ts"),
                        len(legs) or n_from_string or None,
                        # ⚠ *_dollars / *_fp only. `volume` and `open_interest`
                        # are null on every combo market (see module docstring).
                        c(m.get("last_price_dollars")),
                        c(m.get("yes_bid_dollars")), c(m.get("yes_ask_dollars")),
                        c(m.get("no_bid_dollars")), c(m.get("no_ask_dollars")),
                        V.fnum(m.get("yes_bid_size_fp")),
                        V.fnum(m.get("volume_fp")),
                        V.fnum(m.get("volume_24h_fp")),
                        V.fnum(m.get("open_interest_fp")),
                        V.fnum(m.get("liquidity_dollars")),
                        (m.get("title") or "")[:200]))
                    for i, leg in enumerate(legs):
                        legrows.append((tk, i, leg.get("event_ticker"),
                                        leg.get("market_ticker"),
                                        leg.get("side"), read_utc))
                con.executemany(
                    "insert or replace into combos values ("
                    + ",".join(["?"] * 24) + ")", rows)
                con.executemany(
                    "insert or ignore into combo_legs values (?,?,?,?,?,?)",
                    legrows)
                con.commit()
                n_combos += len(rows)
                n_legs += len(legrows)
                got += len(rows)
                cursor = js.get("cursor")
                page += 1
                if not cursor:
                    break
                time.sleep(0.15)
            print(f"   {series:32} {status:8} {got:>6} combos", flush=True)

    con.execute("update sweeps set finished_utc=?, n_combos=?, n_legs=?, "
                "truncated=0 where sweep_id=?", (now(), n_combos, n_legs, sid))
    con.commit()
    return n_combos, n_legs, False


def report(con) -> None:
    print("=" * 78)
    print("COMBO TAPE — what is captured")
    print("=" * 78)
    ns, = con.execute("select count(*) from sweeps").fetchone()
    nc, nt = con.execute(
        "select count(*), count(distinct ticker) from combos").fetchone()
    nl, = con.execute("select count(*) from combo_legs").fetchone()
    print(f"   sweeps: {ns}   combo snapshots: {nc:,}   distinct combos: {nt:,}")
    print(f"   legs stored: {nl:,}")
    print("\n   by series and status (distinct combos):")
    for s, st, n in con.execute(
            "select series_ticker, status, count(distinct ticker) from combos "
            "group by 1,2 order by 3 desc"):
        print(f"      {s:32} {st:10} {n:>6}")
    print("\n   settled combos with a result, by result:")
    for res, n in con.execute(
            "select result, count(distinct ticker) from combos "
            "where result is not null and result != '' group by 1 order by 2 desc"):
        print(f"      {str(res):10} {n:>6}")
    row = con.execute("select min(close_utc), max(close_utc) from combos "
                      "where close_utc is not null").fetchone()
    print(f"\n   close times span: {row[0]} -> {row[1]}")
    print("\n   legs per combo:")
    for n, cnt in con.execute(
            "select n_legs, count(distinct ticker) from combos "
            "where n_legs is not null group by 1 order by 1"):
        print(f"      {n} legs: {cnt:,} combos")
    print("\n   ⚠ quote state -- the reason nothing is filtered:")
    tot, wide = con.execute(
        "select count(*), sum(case when yes_bid_c<=0 and yes_ask_c>=100 "
        "then 1 else 0 end) from combos").fetchone()
    print(f"      snapshots with bid 0 / ask 100: {wide:,} of {tot:,} "
          f"({100.0*(wide or 0)/max(1,tot):.0f} out of 100)")
    print("      Combos are priced by Request For Quote. If this recorder")
    print("      dropped rows with no two-sided quote, as the others do, it")
    print("      would have stored almost nothing.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--every", type=float, default=21600.0)   # 6 h
    args = ap.parse_args()

    DB.parent.mkdir(parents=True, exist_ok=True)
    if args.report:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        report(con)
        return

    claim_lock()
    con = sqlite3.connect(DB, timeout=60.0)
    con.execute("pragma journal_mode=WAL")
    con.executescript(SCHEMA)
    print("=" * 78)
    print("COMBO RECORDER — Kalshi parlays, read-only, before they age out")
    print("=" * 78)
    print(f"db={DB}  timeout={TIMEOUT} (connect, read)  budget={SWEEP_BUDGET_S:.0f}s")
    while True:
        t0 = time.time()
        dl = Deadline(SWEEP_BUDGET_S)
        print(f"\nsweep {now()}")
        try:
            nc, nl, trunc = sweep(con, dl)
            print(f"   -> {nc:,} combo snapshots, {nl:,} legs, "
                  f"{time.time()-t0:.0f}s{'  (TRUNCATED)' if trunc else ''}",
                  flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"   sweep failed: {type(e).__name__}: {e}", flush=True)
        if args.once:
            break
        time.sleep(max(60.0, args.every - (time.time() - t0)))
    con.close()


if __name__ == "__main__":
    main()
