"""EXCHANGE CENSUS - every Kalshi series, and whether a strategy could ever
trade it.

This is stage 1 of the factory and it is the only irreversible one. Kalshi's
history window is roughly 69 days and rolling; a closed market 404s and is gone
at any price. So the question this script answers is not "what is interesting"
but "what must be on tape by tonight".

Three passes, cheapest first, and each one narrows the next:

  A. LIST every series.               1 request.  ~13,000 rows.
  B. LIST every OPEN market.          ~40 requests at limit=1000.
     Group by series. A series with no open market cannot be recorded today,
     so it drops out here and costs nothing.
  C. PROBE ONE ORDERBOOK per surviving series, on the soonest-closing open
     market. This is the only expensive pass and it is the only one that can
     answer "is there a counterparty". ~1 request per live series.

WARNING. Pass C probes ONE market per series, not the series. A one-sided read
on one market is evidence about that market. GUARDS #15: a 404 never
establishes that something is dead, and by the same argument one empty book
never establishes that a family is untradeable. The output therefore records
what was probed and when, and `tier` is a RECORDING PRIORITY, never a verdict.

Read-only. Public endpoints only. No credentials exist on this path - the
client is bot-hunt's `venues.py`, which has no authenticated code in it by
construction.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
# Reuse bot-hunt's read-only client rather than writing a second one. It
# encodes four traps that each cost a prior session real time (the *_dollars
# field names, `orderbook_fp`, both Kalshi sides quoted as bids, list endpoints
# nulling bid/ask). A copy of it would drift away from those. This is a READ of
# another chat's folder, never a write - see DECISIONS.md D2.
sys.path.insert(0, str(REPO / "bot-hunt" / "src"))
import venues as V  # noqa: E402

DB = ROOT / "data" / "census.db"

SCHEMA = """
create table if not exists series (
  ticker text primary key, title text, category text, frequency text,
  fee_type text, fee_multiplier real, n_settlement_sources integer,
  settlement_sources text, seen_utc text);

create table if not exists open_markets (
  ticker text primary key, series text, event_ticker text, title text,
  close_utc text, open_utc text, status text, volume real, open_interest real,
  liquidity real, seen_utc text);

create table if not exists probe (
  series text primary key, ticker text, probed_utc text,
  yes_bid_c real, yes_ask_c real, bid_size real, ask_size real,
  n_yes_levels integer, n_no_levels integer,
  depth5_yes real, depth5_no real, spread_c real, http_ok integer);
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


def pass_a(con: sqlite3.Connection) -> int:
    """Every series the exchange lists. One request; the endpoint ignores
    `limit` and returns the lot."""
    r = V.k_get("/series")
    if r is None or r.status_code != 200:
        raise SystemExit("series listing failed: %s" % (r and r.status_code))
    rows = (r.json() or {}).get("series") or []
    ts = now()
    con.executemany(
        "insert or replace into series values (?,?,?,?,?,?,?,?,?)",
        [(s.get("ticker"), s.get("title"), s.get("category"),
          s.get("frequency"), s.get("fee_type"),
          V.fnum(s.get("fee_multiplier")),
          len(s.get("settlement_sources") or []),
          json.dumps([x.get("name") for x in
                      (s.get("settlement_sources") or [])])[:2000],
          ts) for s in rows if s.get("ticker")])
    con.commit()
    return len(rows)


def pass_b(con: sqlite3.Connection) -> int:
    """Every OPEN market on the exchange, grouped later by series.

    ⚠ THE LIVE FIELD NAMES, WRITTEN OUT, BECAUSE I GOT THEM WRONG ON THE FIRST
    RUN. GUARDS #23 exactly: a missing key reads None and becomes a silent
    zero. v1 of this function read `volume_dollars` with `volume` as a
    fallback, and BOTH are absent - so every volume and every open interest in
    the first census came back null and the summary printed `oi 0` for all
    16 categories. It looked like a finding about the exchange. It was a
    finding about my own field names.

    Verified against a real response on 2026-08-18. The names are:

        volume            -> volume_fp          (also volume_24h_fp)
        open_interest     -> open_interest_fp
        liquidity         -> liquidity_dollars
        last_price        -> last_price_dollars

    Note the two suffixes are NOT interchangeable: `_fp` on the count fields,
    `_dollars` on the money fields, and guessing wrong reads None again.
    """
    ts = now()
    n = 0
    buf = []
    for m in V.k_paginate("/markets", {"status": "open", "limit": 1000},
                          "markets"):
        tk = m.get("ticker")
        if not tk:
            continue
        buf.append((tk, V.series_of(tk), m.get("event_ticker"), m.get("title"),
                    m.get("close_time"), m.get("open_time"), m.get("status"),
                    V.fnum(m.get("volume_fp")),
                    V.fnum(m.get("open_interest_fp")),
                    V.fnum(m.get("liquidity_dollars")),
                    ts))
        if len(buf) >= 2000:
            con.executemany("insert or replace into open_markets "
                            "values (?,?,?,?,?,?,?,?,?,?,?)", buf)
            con.commit()
            n += len(buf)
            buf = []
            print("  ...%d open markets" % n, flush=True)
    if buf:
        con.executemany("insert or replace into open_markets "
                        "values (?,?,?,?,?,?,?,?,?,?,?)", buf)
        con.commit()
        n += len(buf)
    return n


def pass_c(con: sqlite3.Connection, limit: int = 0, redo: bool = False) -> int:
    """One orderbook per live series, on its soonest-closing open market.

    Soonest-closing rather than largest-volume on purpose: the same argument
    the recorder uses. A pre-match strategy trades the market about to settle,
    and picking by volume would systematically probe the family's showpiece
    market and report the family as more liquid than it is.
    """
    done = set()
    if not redo:
        done = {r[0] for r in con.execute("select series from probe")}
    rows = con.execute("""
        select series, ticker from (
          select series, ticker,
                 row_number() over (
                   partition by series
                   order by (close_utc is null), close_utc, ticker) rn
          from open_markets)
        where rn = 1 order by series""").fetchall()
    todo = [r for r in rows if r[0] not in done]
    if limit:
        todo = todo[:limit]
    print("pass C: %d series to probe (%d already done)"
          % (len(todo), len(done)), flush=True)
    n = 0
    t0 = time.time()
    for series, ticker in todo:
        ylv, nlv = V.k_orderbook(ticker)
        ts = now()
        if ylv is None and nlv is None:
            con.execute("insert or replace into probe values "
                        "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (series, ticker, ts, None, None, None, None,
                         None, None, None, None, None, 0))
        else:
            yb, ya, bs, asz = V.k_touch(ylv, nlv)
            d5y = sum(sz for p, sz in (ylv or [])
                      if yb is not None and p >= yb - 5)
            nb = nlv[-1][0] if nlv else None
            d5n = sum(sz for p, sz in (nlv or [])
                      if nb is not None and p >= nb - 5)
            spread = (ya - yb) if (yb is not None and ya is not None) else None
            con.execute("insert or replace into probe values "
                        "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (series, ticker, ts, yb, ya, bs, asz,
                         len(ylv or []), len(nlv or []), d5y, d5n, spread, 1))
        n += 1
        if n % 200 == 0:
            con.commit()
            rate = n / max(1e-9, time.time() - t0)
            print("  probed %d/%d  %.1f/s  eta %.0f min"
                  % (n, len(todo), rate, (len(todo) - n) / max(rate, 1e-9) / 60),
                  flush=True)
    con.commit()
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", default="abc")
    ap.add_argument("--limit", type=int, default=0,
                    help="pass C only: probe at most this many series")
    ap.add_argument("--redo", action="store_true",
                    help="pass C only: re-probe series already probed")
    args = ap.parse_args()
    con = connect()
    if "a" in args.passes:
        print("pass A: series listed = %d" % pass_a(con), flush=True)
    if "b" in args.passes:
        print("pass B: open markets = %d" % pass_b(con), flush=True)
        n_ser = con.execute(
            "select count(distinct series) from open_markets").fetchone()[0]
        print("        series with an open market = %d" % n_ser, flush=True)
    if "c" in args.passes:
        print("pass C: probed = %d" % pass_c(con, args.limit, args.redo),
              flush=True)
    con.close()


if __name__ == "__main__":
    main()
