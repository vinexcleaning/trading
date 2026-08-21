"""Phase 6a -- re-pull the tennis tape from the public API, for the MAKER test.

WHY THIS EXISTS, AND WHY IT IS URGENT
-------------------------------------
The maker question (mailbox tennis/017) needs two things joined that this repo
was believed not to have: a per-minute price path, and who the aggressor was on
each trade. Both were reported absent on 2026-08-20. **That report was wrong.**

  * `bot-hunt/data/record.db` really does hold quotes only, at ~731 s.
  * `kalshi-market-scan`'s trades tape really is one day, 2026-07-30.
  * BUT the exchange still serves BOTH, per market, for anything not yet aged
    out -- and nobody had asked it.

MEASURED 2026-08-20, not assumed:

  * `/markets?status=settled` returns tennis back to **2026-06-14 and no
    further** -- the ~69-day window. 2026-06-12 returns zero. **27,730 settled
    tennis markets** are inside it across the six series below.
  * `/markets/trades?ticker=X` returns `taker_book_side` and
    `taker_outcome_side` for those settled markets, 1,000 to a page, cursored.
  * `/series/{s}/markets/{t}/candlesticks?period_interval=1` returns
    **one-minute bars carrying `yes_bid` and `yes_ask` separately**, for every
    tier including ITF. That is strictly better than the mid-only tape the
    original study built: the maker price and the taker price are then both
    observed rather than modelled, which is the single easiest thing to fake in
    a maker backtest.

**Every day of delay permanently destroys one day of the window.** A closed
Kalshi market 404s forever once it ages out. That is why this pulls first and
asks questions afterwards -- pulling is free, reversible and read-only; waiting
is not.

ORDERING IS DELIBERATE. Main tour and Challenger first (7,066 markets), because
that is where the original study's universe lived and where set-1 outcomes are
obtainable free. ITF (20,664) second: it is 75% of the markets, and by S025 a
much smaller share of the actual contract volume.

NO CREDENTIALS. Read-only GETs against the public endpoint, exactly as
`p0_candles.py` and `crypto/src/pull_trade_tape.py` already do. Paced below the
unauthenticated ceiling C018 measured (15 req/s) and deliberately well below it,
because the two forward recorders share this machine's quota and they are the
irreplaceable processes.

Usage:
    p6_maker_pull.py --start 2026-06-14 --end 2026-08-02
    p6_maker_pull.py --status
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import queue
import sqlite3
import sys
import threading
import time
from decimal import Decimal

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB = DATA / "maker.db"
BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Tier order is the pull order. Main tour and Challenger before ITF.
SERIES = [
    "KXATPMATCH",
    "KXWTAMATCH",
    "KXATPCHALLENGERMATCH",
    "KXWTACHALLENGERMATCH",
    "KXITFMATCH",
    "KXITFWMATCH",
]

MAX_PERIODS = 4800          # the API caps a candlestick request at 5000
RATE_PER_SEC = 6.0          # C018 ceiling is 15; the recorders share the quota
WORKERS = 6

SCHEMA = """
create table if not exists markets (
  ticker text primary key, series text, event_ticker text,
  result text, status text, open_time text, close_time text,
  volume_fp real, tier text);
create table if not exists candles (
  ticker text, ts integer,
  bid_c integer, ask_c integer, close_c integer, mean_c integer,
  volume_fp real, oi_fp real,
  primary key (ticker, ts));
create table if not exists trades (
  trade_id text primary key, ticker text, series text,
  count real, yes_price_c integer, no_price_c integer,
  taker_outcome_side text, taker_book_side text, created_time text,
  is_block integer);
create index if not exists ix_tr_tk on trades(ticker);
create table if not exists pulled (
  ticker text primary key, n_candles integer, n_trades integer,
  trade_pages integer, done_utc text, note text);
create table if not exists fees (
  series text primary key, fee_type text, fee_multiplier real, seen_utc text);
"""


# ------------------------------------------------------------------ helpers
class Limiter:
    """One global token bucket. Threads share it, so WORKERS does not multiply
    the request rate -- a mistake that would show up as 429s and, worse, as
    pressure on the two recorders."""

    def __init__(self, per_sec):
        self._gap = 1.0 / per_sec
        self._lock = threading.Lock()
        self._next = time.monotonic()

    def take(self):
        with self._lock:
            now = time.monotonic()
            if self._next < now:
                self._next = now
            wait = self._next - now
            self._next += self._gap
        if wait > 0:
            time.sleep(wait)


LIM = Limiter(RATE_PER_SEC)
_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers["User-Agent"] = "trading-repo/set1_overshoot p6 (read-only)"
        s.mount("https://", requests.adapters.HTTPAdapter(
            pool_connections=WORKERS * 2, pool_maxsize=WORKERS * 2))
        _local.s = s
    return _local.s


def get(path, **params):
    """GET with backoff. Returns None only after the retries are exhausted, so
    a caller can record the ticker as attempted-and-failed rather than silently
    treating it as empty -- GUARDS #15: absent is not zero."""
    url = BASE + path
    for attempt in range(6):
        LIM.take()
        try:
            r = session().get(url, params=params, timeout=90)
        except requests.RequestException:
            time.sleep(1.0 + 1.5 * attempt)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(1.5 + 2.0 * attempt)
            continue
        if r.status_code == 404:
            return None
        time.sleep(1.0 + attempt)
    return None


def cents(x):
    """Dollar string -> integer cents, exactly. None if absent or not a whole
    cent. Tennis is `linear_cent`, so a fraction here means something changed
    and it must not be rounded away quietly."""
    if x is None or x == "":
        return None
    d = Decimal(str(x)) * 100
    i = int(d.to_integral_value())
    return i if Decimal(i) == d else None


def ts_of(day):
    return int(dt.datetime.strptime(day, "%Y-%m-%d")
               .replace(tzinfo=dt.timezone.utc).timestamp())


def tier_of(series):
    if "ITF" in series:
        return "itf"
    if "CHALLENGER" in series:
        return "challenger"
    return "main"


# ------------------------------------------------------------------ stage 1
def pull_universe(con, start, end):
    """Every settled market per series in the window, plus the fee schedule.

    The listing carries `result`, so settlement needs no second pass -- the
    same saving `crypto/src/pull_trade_tape.py` found."""
    lo, hi = ts_of(start), ts_of(end)
    for s in SERIES:
        meta = get(f"/series/{s}")
        if meta and meta.get("series"):
            o = meta["series"]
            con.execute(
                "insert or replace into fees values (?,?,?,?)",
                (s, o.get("fee_type"), float(o.get("fee_multiplier") or 1),
                 dt.datetime.now(dt.timezone.utc).isoformat()))

        cur, n = None, 0
        while True:
            q = dict(series_ticker=s, status="settled",
                     min_close_ts=lo, max_close_ts=hi, limit=1000)
            if cur:
                q["cursor"] = cur
            d = get("/markets", **q)
            if not d:
                break
            ms = d.get("markets") or []
            con.executemany(
                "insert or replace into markets values (?,?,?,?,?,?,?,?,?)",
                [(m["ticker"], s, m.get("event_ticker"), m.get("result"),
                  m.get("status"), m.get("open_time"), m.get("close_time"),
                  float(m.get("volume_fp") or 0), tier_of(s)) for m in ms])
            n += len(ms)
            cur = d.get("cursor")
            if not cur or not ms:
                break
        con.commit()
        print(f"  {s:<26} {n:>6,} settled markets", flush=True)


# ------------------------------------------------------------------ stage 2
def pull_one(row, want_trades=True):
    """Candles and/or every trade page for one market. Returns rows to write.

    The trade cursor is NEWEST-FIRST, so a page cap does not sample a market --
    it keeps the window nearest the answer and discards the early price
    discovery, which is the worst possible direction to truncate a fade study
    in. There is therefore no page cap here; `trade_pages` records the depth so
    a truncation could be detected if one is ever added."""
    ticker, series, open_time, close_time = row
    out = {"ticker": ticker, "candles": [], "trades": [], "pages": 0,
           "note": ""}

    try:
        end = int(dt.datetime.fromisoformat(
            close_time.replace("Z", "+00:00")).timestamp())
        start = end - MAX_PERIODS * 60
        if open_time:
            o = int(dt.datetime.fromisoformat(
                open_time.replace("Z", "+00:00")).timestamp())
            start = max(start, o - 3600)
    except (TypeError, ValueError, AttributeError):
        out["note"] = "unparseable close_time"
        return out

    c = get(f"/series/{series}/markets/{ticker}/candlesticks",
            start_ts=start, end_ts=end, period_interval=1)
    if c is None:
        out["note"] = "candles failed"
    else:
        for k in (c.get("candlesticks") or []):
            p = k.get("price") or {}
            out["candles"].append((
                ticker, int(k["end_period_ts"]),
                cents((k.get("yes_bid") or {}).get("close_dollars")),
                cents((k.get("yes_ask") or {}).get("close_dollars")),
                cents(p.get("close_dollars")),
                cents(p.get("mean_dollars")),
                float(k.get("volume_fp") or 0),
                float(k.get("open_interest_fp") or 0)))

    if not want_trades:
        return out

    cur = None
    while True:
        q = dict(ticker=ticker, limit=1000)
        if cur:
            q["cursor"] = cur
        d = get("/markets/trades", **q)
        if not d:
            if out["pages"] == 0:
                out["note"] = (out["note"] + "; trades failed").strip("; ")
            break
        tr = d.get("trades") or []
        for t in tr:
            # `count_fp`, not `count`. MEASURED: the trade object has no
            # `count` key at all, so `t.get("count")` would have written 0.0
            # for every trade -- the exact silent-zero shape that
            # common/tests/test_no_legacy_kalshi_fields.py exists to catch.
            out["trades"].append((
                t["trade_id"], ticker, series, float(t.get("count_fp") or 0),
                cents(t.get("yes_price_dollars")),
                cents(t.get("no_price_dollars")),
                t.get("taker_outcome_side"), t.get("taker_book_side"),
                t.get("created_time"),
                1 if t.get("is_block_trade") else 0))
        out["pages"] += 1
        cur = d.get("cursor")
        if not cur or not tr:
            break
    return out


def pull_bodies(con, want_trades=True, only=None):
    """`only` is an explicit ticker list -- pass 2, the markets that fired.

    Two passes, and the reason is arithmetic rather than taste. MEASURED on
    the 2026-07-16 smoke run: 616 candle rows and 4,011 trade rows per
    market. Over 27,730 markets that is 17M candles (~1 GB) against 111M
    trades (~28 GB) -- and the overwhelming majority of those trades belong
    to markets where the entry rule never fires, so they can never affect
    any result. Candles first for everything, trades only where the signal
    actually triggers."""
    if only is not None:
        marks = ",".join("?" * len(only))
        todo = con.execute(
            "select ticker, series, open_time, close_time from markets "
            f"where ticker in ({marks}) order by close_time", only).fetchall()
        have = {r[0] for r in con.execute(
            "select distinct ticker from trades")}
        todo = [r for r in todo if r[0] not in have]
    else:
        todo = con.execute(
            "select m.ticker, m.series, m.open_time, m.close_time "
            "from markets m left join pulled p on p.ticker = m.ticker "
            "where p.ticker is null "
            "order by case m.tier when 'main' then 0 "
            "when 'challenger' then 1 else 2 end, m.close_time").fetchall()
    total = len(todo)
    what = "candles + trades" if want_trades else "CANDLES ONLY"
    print(f"\n  {total:,} markets to pull -- {what} "
          f"(main tour and Challenger first)\n", flush=True)
    if not total:
        return

    q_in = queue.Queue()
    q_out = queue.Queue(maxsize=256)
    for r in todo:
        q_in.put(r)

    def worker():
        while True:
            try:
                r = q_in.get_nowait()
            except queue.Empty:
                return
            try:
                q_out.put(pull_one(r, want_trades))
            except Exception as e:                    # noqa: BLE001
                q_out.put({"ticker": r[0], "candles": [], "trades": [],
                           "pages": 0, "note": f"error {type(e).__name__}"})

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(WORKERS)]
    for t in threads:
        t.start()

    done = t0 = 0
    t0 = time.monotonic()
    while done < total:
        o = q_out.get()
        if o["candles"]:
            con.executemany(
                "insert or replace into candles values (?,?,?,?,?,?,?,?)",
                o["candles"])
        if o["trades"]:
            con.executemany(
                "insert or replace into trades values (?,?,?,?,?,?,?,?,?,?)",
                o["trades"])
        prev = con.execute("select n_candles from pulled where ticker=?",
                           (o["ticker"],)).fetchone()
        n_c = len(o["candles"]) if o["candles"] else (prev[0] if prev else 0)
        con.execute("insert or replace into pulled values (?,?,?,?,?,?)",
                    (o["ticker"], n_c, len(o["trades"]),
                     o["pages"], dt.datetime.now(dt.timezone.utc).isoformat(),
                     o["note"]))
        done += 1
        if done % 100 == 0:
            con.commit()
            el = time.monotonic() - t0
            rate = done / el if el else 0
            left = (total - done) / rate / 3600 if rate else 0
            print(f"  {done:>6,}/{total:,}  {rate:5.2f} mkt/s  "
                  f"~{left:4.1f} h left", flush=True)
    con.commit()


# ------------------------------------------------------------------ status
def status(con):
    def one(q, *a):
        return con.execute(q, a).fetchone()[0]

    print(f"database: {DB}")
    print(f"  markets listed : {one('select count(*) from markets'):>10,}")
    print(f"  markets pulled : {one('select count(*) from pulled'):>10,}")
    print(f"  candle rows    : {one('select count(*) from candles'):>10,}")
    print(f"  trade rows     : {one('select count(*) from trades'):>10,}")
    bad = one("select count(*) from pulled where note <> ''")
    print(f"  markets with a problem: {bad:,}")
    print("\n  by tier:")
    for r in con.execute(
            "select m.tier, count(distinct m.ticker), "
            "  sum(case when p.ticker is not null then 1 else 0 end) "
            "from markets m left join pulled p on p.ticker=m.ticker "
            "group by m.tier order by 1"):
        print(f"    {r[0]:<12} {r[2]:>6,} / {r[1]:,} pulled")
    print("\n  fee schedule as the API reports it:")
    for r in con.execute("select series, fee_type from fees order by 1"):
        charged = "MAKER CHARGED" if "maker" in (r[1] or "") else "maker free"
        print(f"    {r[0]:<26} {r[1]:<28} {charged}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-06-14",
                    help="measured cliff: nothing before 2026-06-14 exists")
    ap.add_argument("--end", default="2026-08-02")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--universe-only", action="store_true")
    ap.add_argument("--candles-only", action="store_true",
                    help="pass 1: ~1 GB. Trades for everything is ~28 GB")
    ap.add_argument("--trades-for", metavar="FILE",
                    help="pass 2: a file of tickers, one per line")
    a = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=60)
    con.executescript(SCHEMA)
    con.execute("pragma journal_mode=wal")

    if a.status:
        status(con)
        return

    if a.trades_for:
        only = [ln.strip() for ln in open(a.trades_for) if ln.strip()]
        print(f"pass 2: trades for {len(only):,} markets that fired",
              flush=True)
        pull_bodies(con, want_trades=True, only=only)
        print()
        status(con)
        return

    print(f"universe: settled tennis markets {a.start} -> {a.end}", flush=True)
    pull_universe(con, a.start, a.end)
    if a.universe_only:
        status(con)
        return
    pull_bodies(con, want_trades=not a.candles_only)
    print()
    status(con)


if __name__ == "__main__":
    sys.exit(main())
