"""FEASIBILITY ONLY. Can the weather model be compared to the MARKET's price?

`docs/GO_NO_GO.md` says of the deciding gate: **"Edge vs the mid: still
unmeasured."** The 2026-08-06 audit ranked that as the single largest open
question in the programme -- KXTEMPDCH is the only family on the exchange that
clears both the power bar (512 settlements vs the 481 needed) and the capacity
bar. The model beats climatology. Nobody ever asked whether it beats the price.

The recorded books cannot answer it: `data/raw/source=kalshi_book_tier2` covers
ONE DAY (2026-07-30) and carries 10 KXTEMPDCH rows. But Kalshi's hourly
candlesticks ARE re-pullable for these markets -- they settled 2026-07-08 ->
07-30, inside the retention window -- and they carry `yes_bid`/`yes_ask` as
nested dollar fields.

THIS SCRIPT COMPUTES NO EDGE AND NO BRIER SCORE. It measures only whether a
tradeable price exists at a pre-settlement anchor, because the first probe
returned a market quoted 0 bid / 1 ask, and a strike with no bid cannot be sold
and has no meaningful mid. If most strikes look like that, the gate is answered
structurally rather than statistically -- which is the same shape as C016
("the cheap wings have an ask but no bid") and would be a finding in itself.

Reads candles with `*_dollars` (the legacy integer fields return None -- C024).
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402

SETTLED = ROOT / "data" / "settled"
OUT = ROOT / "data" / "weather_candles.db"
REPORTS = ROOT / "reports"

SCHEMA = """
create table if not exists wcandles (
  ticker text, series text, event_ticker text, close_ts integer,
  end_period_ts integer,
  yes_bid_close real, yes_ask_close real,
  yes_bid_open real, yes_ask_open real,
  volume_fp real, open_interest_fp real,
  primary key (ticker, end_period_ts));
create index if not exists ix_wc on wcandles(series, close_ts);
create table if not exists wpull (ticker text primary key, series text,
  n_candles integer, http integer);
"""


def fnum(d, k):
    try:
        return float(d[k])
    except (TypeError, KeyError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXTEMPDCH")
    ap.add_argument("--sample", type=int, default=250,
                    help="0 = pull every settled market in the series")
    ap.add_argument("--pace", type=float, default=0.18,
                    help="seconds between calls; the bot-hunt recorder is live")
    a = ap.parse_args()

    d = pd.read_parquet(SETTLED / f"{a.series}.parquet")
    d["ct"] = pd.to_datetime(d.close_time, utc=True, errors="coerce")
    d = d.dropna(subset=["ct"])
    tickers = list(d[["ticker", "event_ticker", "ct"]].itertuples(index=False))
    if a.sample and a.sample < len(tickers):
        # deterministic sample -- a fixed seed, so a re-run pulls the same set
        random.Random(20260806).shuffle(tickers)
        tickers = tickers[: a.sample]
    print(f"{a.series}: {len(d)} settled markets, pulling {len(tickers)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(OUT, timeout=120)
    con.executescript(SCHEMA)

    done = {r[0] for r in con.execute("select ticker from wpull")}
    n_new = 0
    for i, (tk, ev, ct) in enumerate(tickers, 1):
        if tk in done:
            continue
        close_ts = int(ct.timestamp())
        r = V.k_get(f"/series/{a.series}/markets/{tk}/candlesticks",
                    {"start_ts": close_ts - 24 * 3600, "end_ts": close_ts + 3600,
                     "period_interval": 60}, pace=a.pace)
        http = None if r is None else r.status_code
        cds = []
        if r is not None and r.status_code == 200:
            try:
                cds = (r.json() or {}).get("candlesticks") or []
            except ValueError:
                cds = []
        rows = []
        for c in cds:
            yb, ya = c.get("yes_bid") or {}, c.get("yes_ask") or {}
            rows.append((tk, a.series, ev, close_ts, c.get("end_period_ts"),
                         fnum(yb, "close_dollars"), fnum(ya, "close_dollars"),
                         fnum(yb, "open_dollars"), fnum(ya, "open_dollars"),
                         fnum(c, "volume_fp"), fnum(c, "open_interest_fp")))
        if rows:
            con.executemany("insert or replace into wcandles values "
                            "(?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("insert or replace into wpull values (?,?,?,?)",
                    (tk, a.series, len(rows), http))
        n_new += 1
        if i % 50 == 0:
            con.commit()
            print(f"   {i}/{len(tickers)}  candles so far="
                  f"{con.execute('select count(*) from wcandles').fetchone()[0]:,}",
                  flush=True)
    con.commit()

    # ------------------------------------------------------------- report
    print(f"\n== PULL  new={n_new}")
    for r in con.execute("select http, count(*) from wpull group by http"):
        print(f"   http {r[0]}: {r[1]}")
    tot, zero = con.execute(
        "select count(*), sum(n_candles=0) from wpull where series=?",
        (a.series,)).fetchone()
    print(f"   markets with ZERO candles: {zero} of {tot} "
          f"({100*zero/max(tot,1):.1f}%)")

    print("\n== IS THERE A TRADEABLE PRICE AT A PRE-SETTLEMENT ANCHOR?")
    rep = {"series": a.series, "markets_pulled": tot, "zero_candle": zero}
    for lead_h in (1, 2, 3, 6):
        q = """
        with anchored as (
          select ticker, close_ts, yes_bid_close b, yes_ask_close a,
                 row_number() over (partition by ticker
                   order by end_period_ts desc) rn
          from wcandles
          where series=? and end_period_ts <= close_ts - ?*3600)
        select count(*) n,
               sum(b is not null and a is not null) both,
               sum(b > 0) has_bid,
               sum(b > 0 and a is not null and a < 1.0) two_sided,
               avg(case when b>0 and a is not null then (a-b)*100 end) sp_mean
        from anchored where rn=1"""
        n, both, has_bid, two, sp = con.execute(q, (a.series, lead_h)).fetchone()
        print(f"   -{lead_h}h  markets with a candle {n:>5}   "
              f"quoted both sides {both or 0:>5}   "
              f"BID > 0 {has_bid or 0:>5} ({100*(has_bid or 0)/max(n,1):5.1f}%)   "
              f"genuinely two-sided {two or 0:>5}   "
              f"mean spread {0 if sp is None else sp:6.2f}c")
        rep[f"lead_{lead_h}h"] = {"markets": n, "bid_gt_0": has_bid or 0,
                                 "two_sided": two or 0,
                                 "mean_spread_c": None if sp is None else round(sp, 3)}

    print("\n== WHERE THE BID EXISTS, WHAT DOES THE BOOK LOOK LIKE (-1h)")
    q = """
    with anchored as (
      select ticker, yes_bid_close b, yes_ask_close a,
             row_number() over (partition by ticker order by end_period_ts desc) rn
      from wcandles where series=? and end_period_ts <= close_ts - 3600)
    select b, a from anchored where rn=1 and b > 0 and a is not null"""
    rows = con.execute(q, (a.series,)).fetchall()
    if rows:
        sp = sorted((a_ - b) * 100 for b, a_ in rows)
        mid = sorted((a_ + b) * 50 for b, a_ in rows)
        print(f"   n={len(sp)}  spread median {sp[len(sp)//2]:.2f}c  "
              f"p90 {sp[int(.9*len(sp))]:.2f}c")
        print(f"   mid price median {mid[len(mid)//2]:.1f}c  "
              f"p10 {mid[int(.1*len(mid))]:.1f}c  p90 {mid[int(.9*len(mid))]:.1f}c")
        rep["two_sided_spread_median_c"] = round(sp[len(sp) // 2], 3)
        rep["two_sided_spread_p90_c"] = round(sp[int(.9 * len(sp))], 3)
    else:
        print("   NONE. No settled market in the sample has a bid above zero "
              "one hour before it settles.")

    con.close()
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"weather_vs_mid_scope_{a.series}.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"\nwrote reports/weather_vs_mid_scope_{a.series}.json")


if __name__ == "__main__":
    main()
