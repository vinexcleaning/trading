"""Capture Kalshi's OWN settled MLB tape before the ~69-day window deletes it.

⚠ THIS IS THE URGENT HALF AND IT IS URGENT ON A DAILY CLOCK.

Measured 2026-08-14: Kalshi's earliest settled `KXMLBGAME` market starts
**2026-06-07**, which is 68 days back. It is a ROLLING window, not the fixed
calendar wall at 2026-05-25 that BH009 recorded — that measurement has since
rolled.

The outside archive (`archive.pmxt.dev`) spans 2026-05-14 → 2026-06-11. So:

    2026-05-14 → 06-07   24 days   ARCHIVE ONLY, Kalshi has already deleted it
    2026-06-07 → 06-11    5 days   BOTH EXIST  <- the calibration window

**That 5-day overlap is the only place the archive can ever be scored against
the truth, and it shrinks by one day per day. On 2026-08-19 it is zero and the
calibration becomes impossible forever.**

So this script grabs Kalshi's side first and stores it raw. The archive is not
on a daily clock; Kalshi is.

    python src/capture_truth.py            # capture, then report
    python src/capture_truth.py --report   # just report what is stored

Public read-only endpoints. No credentials, no order path.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kalshi as K                     # noqa: E402

OUT = HERE.parent / "data" / "kalshi_truth.db"
SERIES = ("KXMLBGAME", "KXMLBTOTAL")
# Everything Kalshi still has. Capture the lot, not just the overlap: the
# window rolls, so what is spare today is the calibration window tomorrow.
CAPTURE_FROM = date(2026, 6, 1)
CAPTURE_TO = date(2026, 8, 14)
PACE_S = 0.35


SCHEMA = """
CREATE TABLE IF NOT EXISTS market (
  ticker TEXT PRIMARY KEY, series TEXT, event_ticker TEXT,
  game_date TEXT, starts_utc TEXT, away TEXT, home TEXT, suffix TEXT,
  floor_strike REAL, result TEXT, status TEXT,
  captured_utc TEXT, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS candle (
  ticker TEXT, end_ts INTEGER,
  yes_bid_close_c REAL, yes_ask_close_c REAL, price_close_c REAL,
  volume REAL, open_interest REAL,
  PRIMARY KEY (ticker, end_ts)
);
CREATE TABLE IF NOT EXISTS capture_log (
  ts_utc TEXT, note TEXT
);
CREATE INDEX IF NOT EXISTS ix_m_date ON market(game_date);
"""


def db():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(OUT, timeout=60)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _c(v):
    """A *_dollars decimal string -> cents. GUARD #23: never the legacy name."""
    try:
        return round(float(v) * 100, 2)
    except (TypeError, ValueError):
        return None


def capture(con):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen = 0
    for series in SERIES:
        # Valid statuses, measured 2026-08-14: settled, closed, open.
        # `finalized`, `determined` and `active` all return HTTP 400 -- they
        # read like plausible Kalshi vocabulary and are not accepted, and the
        # first run died on one because the catch below was RuntimeError only.
        for status in ("settled", "closed"):
            try:
                mkts = K.markets(series, status=status)
            except Exception as e:                      # noqa: BLE001
                # Broad on purpose: an HTTPError here is a bad status value,
                # not a transient failure, and it must not abort the capture of
                # the OTHER statuses. The window is closing daily.
                print(f"  ! {series}/{status}: {type(e).__name__} {e}")
                continue
            for m in mkts:
                p = K.ticker_parts(m["ticker"])
                if not p:
                    continue
                gd = p["starts"].date()
                if not (CAPTURE_FROM <= gd <= CAPTURE_TO):
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO market (ticker, series, "
                    "event_ticker, game_date, starts_utc, away, home, suffix, "
                    "floor_strike, result, status, captured_utc, raw_json) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (m["ticker"], series, m.get("event_ticker"),
                     gd.isoformat(), p["starts"].isoformat(), p["away"],
                     p["home"], p["suffix"], m.get("floor_strike"),
                     m.get("result"), status, now, json.dumps(m)))
                seen += 1
            con.commit()
            print(f"  {series}/{status}: {len(mkts)} listed, {seen} kept so far")
            time.sleep(PACE_S)
    return seen


def capture_candles(con, limit=None):
    """1-minute candles per market. THE PRICE HISTORY -- the part that dies.

    Candlesticks use a DIFFERENT schema from markets: `yes_bid` and `yes_ask`
    are live CONTAINERS whose leaves are `*_dollars`, while `volume` and
    `open_interest` ARE renamed to `*_fp` on the same object. GUARD #23.
    """
    _CAPTURE_BUGS = """
    ⚠ TWO CAPTURE BUGS FIXED 2026-08-17, and the first one voided a claim I had
    already put in front of the user.

    BUG A -- RESOLUTION. `period_interval=60` is SIXTY MINUTES, not sixty
    seconds. Kalshi's parameter is in minutes. So the first capture stored
    HOURLY bars while I described them in BRIEF.md as "minute-by-minute". The
    accepted values are 1 and 60; **5 is rejected with HTTP 400**, so there is
    no middle setting to compromise on. Measured on one market: interval 1 ->
    1,790 rows, interval 60 -> 66 rows. Same span.

    BUG B -- WINDOW. The window was first pitch ±6h, which is the part of the
    tape these bots never trade in. `starter` and `early` enter roughly a DAY
    before first pitch. So the capture missed the only hours that matter and a
    price lookup at entry time landed 23 hours before the earliest stored row.

    The tape actually reaches ~72h before first pitch, which covers every entry
    either bot has ever made. Both are fixed below. Re-pulled markets are
    detected by row count, not by presence, or the old 10-row stubs would be
    treated as done.
    """
    rows = con.execute(
        "SELECT m.ticker, m.series, m.starts_utc FROM market m LEFT JOIN "
        "(SELECT ticker, COUNT(*) n FROM candle GROUP BY ticker) c "
        "ON c.ticker=m.ticker WHERE COALESCE(c.n,0) < 100 "
        "ORDER BY m.game_date DESC").fetchall()
    if limit:
        rows = rows[:limit]
    print(f"  {len(rows)} markets still need candles")
    got = fail = 0
    for i, r in enumerate(rows, 1):
        st = datetime.fromisoformat(r["starts_utc"])
        s = int(st.timestamp()) - 72 * 3600     # BUG B: bots enter ~1 day out
        e = int(st.timestamp()) + 6 * 3600
        try:
            d = K.get(f"/series/{r['series']}/markets/{r['ticker']}"
                      f"/candlesticks", start_ts=s, end_ts=e,
                      period_interval=1)   # BUG A: minutes
        except Exception:                              # noqa: BLE001
            fail += 1
            time.sleep(PACE_S)
            continue
        cs = d.get("candlesticks") or []
        for c in cs:
            yb = (c.get("yes_bid") or {}).get("close_dollars")
            ya = (c.get("yes_ask") or {}).get("close_dollars")
            pr = (c.get("price") or {}).get("close_dollars")
            con.execute(
                "INSERT OR REPLACE INTO candle (ticker, end_ts, "
                "yes_bid_close_c, yes_ask_close_c, price_close_c, volume, "
                "open_interest) VALUES (?,?,?,?,?,?,?)",
                (r["ticker"], c.get("end_period_ts"), _c(yb), _c(ya), _c(pr),
                 c.get("volume_fp"), c.get("open_interest_fp")))
        if cs:
            got += 1
        if i % 25 == 0:
            con.commit()
            print(f"    {i}/{len(rows)}  markets with candles {got}, failed {fail}")
        time.sleep(PACE_S)
    con.commit()
    return got, fail


def report(con):
    m = con.execute(
        "SELECT COUNT(*) n, COUNT(DISTINCT game_date) d, MIN(game_date) a, "
        "MAX(game_date) b FROM market").fetchone()
    c = con.execute(
        "SELECT COUNT(*) n, COUNT(DISTINCT ticker) t FROM candle").fetchone()
    print(f"\n  markets stored : {m['n']} over {m['d']} game dates "
          f"({m['a']} -> {m['b']})")
    print(f"  candles stored : {c['n']} rows across {c['t']} markets")
    ov = con.execute(
        "SELECT COUNT(DISTINCT game_date) d, COUNT(*) n FROM market "
        "WHERE game_date <= '2026-06-11'").fetchone()
    print(f"  ** in the ARCHIVE OVERLAP (<= 2026-06-11): {ov['n']} markets "
          f"over {ov['d']} dates **")
    print("     that overlap is the ONLY place the archive can be scored")
    print("     against the truth, and it shrinks by one day per day.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    con = db()
    if not a.report:
        print("capturing Kalshi's own settled MLB tape "
              f"({CAPTURE_FROM} -> {CAPTURE_TO})")
        n = capture(con)
        con.execute("INSERT INTO capture_log (ts_utc, note) VALUES (?,?)",
                    (datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     f"markets pass: {n}"))
        con.commit()
        print("\ncapturing candles (the price history -- the part that dies)")
        got, fail = capture_candles(con, limit=a.limit)
        print(f"  candles captured for {got} markets, {fail} failed")
    report(con)
    con.close()
    print(f"\nstored in {OUT}")
