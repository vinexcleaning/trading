"""THE RECORDER. Starts the day the sources are identified, because none of the
three can be backfilled.

  Pinnacle guest API  live-only. No historical endpoint exists at any price.
  Kalshi orderbook    live-only. Kalshi publishes no historical book endpoint
                      and closed markets 404 after ~69 days.
  Polymarket CLOB     live-only for the touch; pmxt archives the book but only
                      from its own start date forward.

This is the only asset in the project that accrues in wall-clock time and
cannot be recovered by working harder later. Everything else can wait.

Design decisions, each one paid for by a prior failure in this repo:

  * RE-LIST EVERY CYCLE. `market-selection`'s recorder picked tickers from a
    static dump and never re-listed, so short-lived markets accumulated as
    settled books — and a settled book reads as "no counterparty". It reported
    NPB two-sided uptime at 27.9% when a fresh probe read 100%. More than half
    that recorder's kills were wrong.
  * CONTENT-LEVEL HEALTH CHECK, not a row count. GUARDS #12: a crypto parse bug
    wrote real row counts with empty content for 1h45m and was caught by
    accident. Every cycle writes a `_health` record with non-empty fraction,
    level counts and staleness.
  * READ THE `*_dollars` / `*_fp` NAMES. The legacy integer-cent fields return
    None on every Kalshi market; a recorder reading them writes silent nulls.
  * NEVER MARK AT THE MID. Both touch sides are stored raw; no mid is computed
    or stored anywhere in this file.
  * SQLITE WITH A 120s BUSY TIMEOUT AND WAL. A sibling session's analysis pass
    held a write lock and killed social-signal's collector after 45 minutes on
    SQLite's 5-second default.

Usage:
    record.py --minutes 0        run forever
    record.py --minutes 30       run for 30 minutes then exit
    record.py --once             one cycle, for testing
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import venues as V  # noqa: E402
from common import kalshi_fields as KF  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "record.db"

PIN_SPORTS = {12: "esports", 29: "soccer", 33: "tennis", 3: "baseball",
              4: "basketball", 15: "amfootball"}

# Kalshi families to record. Chosen from `market-selection`'s measured
# scorecard (which had the 24h exchange-wide tape) intersected with the
# families for which a FREE SHARP REFERENCE PRICE now provably exists on
# Pinnacle. That intersection is the whole point — see PRIOR_ART.md.
KALSHI_SERIES = [
    # South American / Mexican soccer — prior shortlist #1, Pinnacle live+hist
    "KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXDIMAYORGAME", "KXCOPADOBRASILGAME",
    "KXLIGAMXTOTAL", "KXBRASILGAME",
    # tennis — the largest sports counterparty on the exchange, and Pinnacle
    # live tennis turns out to be free (3,728 priced markets)
    "KXATPMATCH", "KXWTAMATCH", "KXITFMATCH", "KXITFWMATCH",
    # esports — killed by market-selection on domain data, revived here because
    # the mechanism needs a reference PRICE, not domain data
    "KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME",
    # MLB derivatives — prior shortlist #2; RFI has no free prop reference
    "KXMLBRFI", "KXMLBGAME", "KXMLBTOTAL",
    # a deliberate NEGATIVE CONTROL: weather is known one-sided (0% two-sided
    # on 11 of 11 city families). If the recorder ever reports it two-sided,
    # the recorder is wrong, not the market.
    "KXHIGHNY", "KXHIGHCHI",
]

# Polymarket tag slugs, PER GAME rather than per category.
#
# CORRECTION, cycle 1: the recorder first queried `tag_slug=esports` and read
# 11 quoted tokens of 95 with 0% two-sided, which would have killed the family
# on dimension A. It was the probe, not the market. `esports` and
# `league-of-legends` ordered by volume24hr return mostly `acceptingOrders=
# false` events (96 of 156), i.e. historic high-volume markets that are closed.
# Queried by the specific game slug at the same minute:
#     dota-2   51 two-sided of 60, top $51,029/24h at a 1.0c spread, 2,458/4,068
#     valorant 54 of 60, top $8,807 at 1.0c, 18,060/41,270 at the touch
#     cs2      23 of 27
# Same shape as `market-selection`'s stale-ticker bug, which produced 19 wrong
# kills. A false kill on dimension A is the most expensive error available here.
POLY_TAGS = ["cs2", "dota-2", "valorant", "tennis", "soccer", "weather",
             "baseball", "mlb"]

SCHEMA = """
create table if not exists cycles (
  cycle_id integer primary key autoincrement,
  started_utc text, finished_utc text, seconds real, note text);

create table if not exists pin_market (
  cycle_id integer, ts_utc text, sport text, matchup_id integer,
  market_key text, market_type text, period integer, cutoff_utc text,
  designation text, participant_id integer, points real, price_american real,
  max_risk real, status text);
create index if not exists ix_pin_m on pin_market(sport, matchup_id, ts_utc);

create table if not exists pin_matchup (
  cycle_id integer, ts_utc text, sport text, matchup_id integer,
  league text, starts_utc text, home text, away text, live integer,
  parent_id integer, raw text);
create index if not exists ix_pin_mu on pin_matchup(sport, matchup_id, ts_utc);

create table if not exists k_book (
  cycle_id integer, ts_utc text, series text, ticker text,
  yes_bid_c real, yes_ask_c real, bid_size real, ask_size real,
  n_yes_levels integer, n_no_levels integer,
  depth5_yes real, depth5_no real, status text, close_utc text);
create index if not exists ix_kb on k_book(series, ticker, ts_utc);

-- Ticker -> the human-readable outcome name, written once per ticker.
--
-- ADDED 2026-08-05 after the cross-venue join failed. Matching Pinnacle to
-- Kalshi on the TICKER matched 3 of 218 events, because Kalshi's outcome codes
-- are 2-4 letter abbreviations (REDA, ODK, WAVE) and every other venue uses
-- full team names. `yes_sub_title` carries the full name and nothing was
-- storing it, so the join had to be reconstructed from a separately-pulled
-- market universe. One table, and the join becomes a first-class operation.
-- Kept separate from k_book rather than added as columns: the name never
-- changes, so repeating it on every snapshot would be pure duplication.
create table if not exists k_names (
  ticker text primary key, series text, event_ticker text,
  title text, yes_sub_title text, no_sub_title text,
  close_utc text, first_seen_utc text);

create table if not exists p_book (
  cycle_id integer, ts_utc text, tag text, slug text, token_id text,
  outcome text, bid_c real, ask_c real, bid_size real, ask_size real,
  n_bid_levels integer, n_ask_levels integer, depth5 real, tick real);
create index if not exists ix_pb on p_book(tag, token_id, ts_utc);

create table if not exists health (
  cycle_id integer, ts_utc text, source text, n_attempted integer,
  n_ok integer, n_nonempty integer, n_two_sided integer, detail text);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------- single-instance lock ----
# ADDED 2026-08-14, and it is a PRECONDITION rather than a nicety.
#
# This recorder is being registered with `runners/`, the shared watchdog that
# restarts anything that is not running -- at startup and every ten minutes.
# That is the fix for the outage that cost 19 hours of tape: the machine
# rebooted at 06:03 on 2026-08-12 and nothing brought the recorders back.
#
# ⚠ But `runners/README.md` states the watchdog's ENTIRE safety argument as a
# precondition on the runner, not on the watchdog:
#
#     "Every test already holds its own single-instance lock and refuses to
#      start twice. So the worst case if the watchdog is wrong about liveness
#      is a process that starts, sees the lock, says 'already running' and
#      exits."
#
# **This recorder did not hold one.** Registering it without this would have
# broken the argument the watchdog rests on, and the failure it invites is one
# that has ALREADY happened here: two writers on one SQLite file died with
# `database is locked` inside 19 minutes (see --db below). The watchdog is
# allowed to be stupid about liveness precisely because the runner is not.
#
# The lock is per DATABASE, not per process: the two recorders write different
# files and both should run. Locking on the process name would forbid that.

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
    con = sqlite3.connect(DB, timeout=120.0)
    con.execute("pragma journal_mode=WAL")
    con.execute("pragma busy_timeout=120000")
    con.executescript(SCHEMA)
    return con


# ------------------------------------------------------------- Pinnacle ----

def pin_cycle(con: sqlite3.Connection, cid: int) -> None:
    ts = now()
    for sid, name in PIN_SPORTS.items():
        mus = V.get(f"https://guest.api.arcadia.pinnacle.com/0.1/sports/{sid}/matchups",
                    pace=0.3)
        mk = V.get(f"https://guest.api.arcadia.pinnacle.com/0.1/sports/{sid}/markets/straight",
                   pace=0.3)
        n_mu = n_mk = 0
        if mus is not None and mus.status_code == 200:
            try:
                rows = mus.json()
            except ValueError:
                rows = []
            recs = []
            for m in rows:
                parts = m.get("participants") or []
                home = away = None
                for p in parts:
                    if p.get("alignment") == "home":
                        home = p.get("name")
                    elif p.get("alignment") == "away":
                        away = p.get("name")
                league = ((m.get("league") or {}).get("name")) if isinstance(
                    m.get("league"), dict) else None
                recs.append((cid, ts, name, m.get("id"), league,
                             m.get("startTime"), home, away,
                             1 if m.get("isLive") else 0, m.get("parentId"),
                             json.dumps(m, default=str)[:4000]))
            con.executemany(
                "insert into pin_matchup values (?,?,?,?,?,?,?,?,?,?,?)", recs)
            n_mu = len(recs)
        if mk is not None and mk.status_code == 200:
            try:
                rows = mk.json()
            except ValueError:
                rows = []
            recs = []
            for m in rows:
                lim = m.get("limits") or []
                maxrisk = None
                for l in lim:
                    if l.get("type") == "maxRiskStake":
                        maxrisk = l.get("amount")
                for pr in (m.get("prices") or []):
                    recs.append((cid, ts, name, m.get("matchupId"),
                                 m.get("key"), m.get("type"), m.get("period"),
                                 m.get("cutoffAt"), pr.get("designation"),
                                 pr.get("participantId"), pr.get("points"),
                                 pr.get("price"), maxrisk, m.get("status")))
            con.executemany(
                "insert into pin_market values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", recs)
            n_mk = len(recs)
        con.execute("insert into health values (?,?,?,?,?,?,?,?)",
                    (cid, ts, f"pinnacle:{name}", 2,
                     int(mus is not None and mus.status_code == 200)
                     + int(mk is not None and mk.status_code == 200),
                     n_mk, None, json.dumps({"matchups": n_mu, "prices": n_mk})))
    con.commit()


# --------------------------------------------------------------- Kalshi ----

def kalshi_cycle(con: sqlite3.Connection, cid: int) -> None:
    ts = now()
    for series in KALSHI_SERIES:
        # RE-LIST LIVE every cycle. This is the fix for the stale-ticker bug
        # that made a prior recorder report 27.9% two-sided where a fresh
        # probe read 100%.
        mkts = list(V.k_paginate("/markets",
                                 {"series_ticker": series, "status": "open",
                                  "limit": 200}, "markets", max_pages=3))
        recs = []
        n_ok = n_two = 0
        # ⚠ SCHEMA ASSERT, added 2026-08-12 during the machinery audit.
        #
        # GUARDS #13: a 200 and a row count are not a result. `assert_priced`
        # has existed in `common/kalshi_fields.py` the whole time and **nothing
        # in this repo called it** — I checked the entire tree. A guard nobody
        # imports is documentation, not a guard.
        #
        # It is the ten-second version of the check that would have caught
        # 3,979,927 null-priced trade rows before the SECOND fifty-minute pull,
        # and the `orderbook` vs `orderbook_fp` bug that reported every book as
        # empty for six days across three scripts.
        #
        # Once per series per cycle, on the FIRST market only — it is a schema
        # assertion, not a row filter. Individually unpriced rows are still
        # skipped and counted below, because "how many were unpriced" is itself
        # a health number.
        if mkts:
            try:
                KF.assert_priced(mkts[0], "market", where=f"{series} listing")
            except KF.KalshiSchemaError as exc:
                print(f"  ⚠ SCHEMA MOVED on {series}: {exc}", flush=True)
        # Names first, for every LISTED market — not only the 60 whose books
        # get probed — because a name is free once the listing is in hand and
        # the join needs the whole universe.
        con.executemany(
            "insert or ignore into k_names values (?,?,?,?,?,?,?,?)",
            [(m.get("ticker"), series, m.get("event_ticker"), m.get("title"),
              m.get("yes_sub_title"), m.get("no_sub_title"),
              m.get("close_time"), ts) for m in mkts if m.get("ticker")])
        # PROBE THE SOONEST-CLOSING MARKETS FIRST.
        #
        # FIXED 2026-08-06. v1 was `mkts[:60]` in whatever order Kalshi's
        # /markets endpoint happened to return, and that order is undocumented.
        # KXMLBGAME lists 85-104 markets against a cap of 60, so ~40 of them got
        # no orderbook probe on any given cycle and WHICH 40 was decided by an
        # unspecified server-side ordering. Measured effect: snapshots per MLB
        # ticker ran min=1, p25=25, median=94 over 214 cycles. Some markets were
        # nearly starved and nothing said so.
        #
        # close_time ascending is the right key rather than an arbitrary one: a
        # pre-match strategy trades the games about to start, so the markets
        # that matter are exactly the ones this ordering guarantees. For live
        # MLB markets close_time is the game start plus a fixed 72 h (see
        # PREREGISTRATION_DEVIG.md section 2.5), so ordering by it is ordering
        # by first pitch. Markets with no close_time sort last rather than
        # first -- an absent field must never win a priority contest.
        mkts.sort(key=lambda m: (m.get("close_time") is None,
                                 m.get("close_time") or "",
                                 m.get("ticker") or ""))
        for m in mkts[:60]:
            tk = m.get("ticker")
            if not tk:
                continue
            ylv, nlv = V.k_orderbook(tk)
            if ylv is None and nlv is None:
                continue
            n_ok += 1
            yb, ya, bs, asz = V.k_touch(ylv, nlv)
            two = yb is not None and ya is not None
            n_two += int(two)
            d5y = sum(sz for p, sz in (ylv or []) if yb is not None and p >= yb - 5)
            nb = nlv[-1][0] if nlv else None
            d5n = sum(sz for p, sz in (nlv or []) if nb is not None and p >= nb - 5)
            recs.append((cid, ts, series, tk, yb, ya, bs, asz,
                         len(ylv or []), len(nlv or []), d5y, d5n,
                         m.get("status"), m.get("close_time")))
        if recs:
            con.executemany(
                "insert into k_book values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", recs)
        con.execute("insert into health values (?,?,?,?,?,?,?,?)",
                    (cid, ts, f"kalshi:{series}", len(mkts), n_ok, len(recs),
                     n_two, json.dumps({"listed": len(mkts)})))
    con.commit()


# ----------------------------------------------------------- Polymarket ----

def poly_cycle(con: sqlite3.Connection, cid: int) -> None:
    ts = now()
    for tag in POLY_TAGS:
        # `active=true` as well as `closed=false`: without it, a volume-ordered
        # query surfaces settled blockbusters ahead of live thin markets and
        # the sample reads as bookless. See the CORRECTION note on POLY_TAGS.
        r = V.p_gamma("/events", {"tag_slug": tag, "closed": "false",
                                  "active": "true", "limit": 60,
                                  "order": "volume24hr", "ascending": "false"})
        if r is None or r.status_code != 200:
            con.execute("insert into health values (?,?,?,?,?,?,?,?)",
                        (cid, ts, f"poly:{tag}", 0, 0, 0, 0,
                         json.dumps({"http": None if r is None else r.status_code})))
            continue
        try:
            events = r.json() or []
        except ValueError:
            events = []
        recs = []
        n_two = 0
        seen = set()
        for e in events:
            for m in (e.get("markets") or []):
                if not m.get("acceptingOrders"):
                    continue
                try:
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                    outs = json.loads(m.get("outcomes") or "[]")
                except (json.JSONDecodeError, TypeError):
                    continue
                if not toks:
                    continue
                # BOTH OUTCOME TOKENS, not just the first.
                #
                # FIXED 2026-08-06. v1 probed `toks[0]` only, so `p_book` held
                # one side of every market and a census found "slugs with >=2
                # recorded outcomes: 0 of 436". A single token's bid/ask does
                # carry both directions (buying the complement is selling this
                # one), but recording one side alone makes it impossible to see
                # the real two-sided book, to detect a crossed market, or to
                # compare the two books' independent spreads. Same class of gap
                # as the missing `k_names`: cheap to record, expensive to
                # reconstruct later, and not recoverable at all after the fact.
                if toks[0] in seen:
                    continue
                if len(seen) > 40:
                    break
                for ti, tok in enumerate(toks[:2]):
                    seen.add(tok)
                    bk = V.p_book(tok)
                    bid, ask, bs, asz, nb, na = V.p_touch(bk)
                    if bid is None and ask is None:
                        continue
                    n_two += int(bid is not None and ask is not None)
                    recs.append((cid, ts, tag, m.get("slug"), tok,
                                 outs[ti] if outs and ti < len(outs) else None,
                                 bid, ask, bs, asz, nb, na, V.p_depth_5c(bk),
                                 V.fnum(m.get("orderPriceMinTickSize"))))
        if recs:
            con.executemany(
                "insert into p_book values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", recs)
        con.execute("insert into health values (?,?,?,?,?,?,?,?)",
                    (cid, ts, f"poly:{tag}", len(seen), len(recs), len(recs),
                     n_two, json.dumps({"events": len(events)})))
    con.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=0.0,
                    help="0 = run forever")
    ap.add_argument("--interval", type=float, default=300.0,
                    help="seconds between cycles")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--skip", default="", help="comma list: pin,kalshi,poly")
    # ADDED 2026-08-09 (mailbox 009). Lets a SECOND recorder process cover extra
    # Kalshi series without touching the main loop's timing. The instruction was
    # explicit: do not lengthen the cycle for the other four threads. A recorder
    # going quiet is this repo's most expensive recurring failure -- three silent
    # deaths so far, and that data cannot be bought back at any price.
    #
    # Both processes write the same SQLite file, which is safe here and by
    # design: WAL plus a 120 s busy timeout, chosen after a sibling session's
    # analysis pass killed a collector on SQLite's 5-second default.
    ap.add_argument("--series", default="",
                    help="comma list overriding KALSHI_SERIES for this process")
    # ⚠ --db ADDED 2026-08-09 AFTER THE SECOND RECORDER DIED IN 19 MINUTES.
    #
    # I claimed in STATUS.md that two processes sharing record.db was "safe by
    # design: WAL plus a 120 s busy timeout". IT IS NOT, and it failed with
    # `sqlite3.OperationalError: database is locked` before the first cycle
    # completed. WAL lets readers run beside a writer; it does NOT let two
    # writers overlap. And `kalshi_cycle` holds ONE write transaction across all
    # 18 series -- 340 to 1,400 seconds -- which dwarfs any busy timeout worth
    # setting.
    #
    # The fix is a separate file, not a longer timeout: a timeout only has to be
    # wrong once, and the thing it kills is the process whose data cannot be
    # re-pulled at any price. Analysis joins the two with ATTACH, which costs
    # nothing.
    ap.add_argument("--db", default="",
                    help="write to this sqlite file instead of data/record.db")
    args = ap.parse_args()
    global KALSHI_SERIES, DB
    if args.series:
        KALSHI_SERIES = [s.strip() for s in args.series.split(",") if s.strip()]
        print(f"series overridden: {KALSHI_SERIES}", flush=True)
    if args.db:
        DB = Path(args.db)
        print(f"db overridden: {DB}", flush=True)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    # AFTER the --db override is applied, because the lock is per database file.
    claim_single_instance()
    con = connect()
    t_end = time.time() + args.minutes * 60 if args.minutes else None
    print(f"recorder start {now()}  db={DB}  interval={args.interval}s "
          f"skip={sorted(skip) or 'none'}", flush=True)
    while True:
        t0 = time.time()
        cur = con.execute("insert into cycles (started_utc) values (?)", (now(),))
        cid = cur.lastrowid
        con.commit()
        errs = []
        for name, fn in (("pin", pin_cycle), ("kalshi", kalshi_cycle),
                         ("poly", poly_cycle)):
            if name in skip:
                continue
            try:
                fn(con, cid)
            except Exception:  # noqa: BLE001
                errs.append(f"{name}: {traceback.format_exc()[-400:]}")
        dt = time.time() - t0
        con.execute("update cycles set finished_utc=?, seconds=?, note=? "
                    "where cycle_id=?",
                    (now(), round(dt, 1), "; ".join(errs)[:2000] or None, cid))
        con.commit()
        rows = con.execute(
            "select source, n_ok, n_nonempty, n_two_sided from health "
            "where cycle_id=?", (cid,)).fetchall()
        tot = sum(r[2] or 0 for r in rows)
        print(f"cycle {cid} {now()} {dt:.0f}s rows={tot} "
              f"{'ERR ' + errs[0][:100] if errs else ''}", flush=True)
        if args.once:
            break
        if t_end and time.time() > t_end:
            break
        time.sleep(max(5.0, args.interval - (time.time() - t0)))
    con.close()


if __name__ == "__main__":
    main()
