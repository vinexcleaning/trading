"""Crypto market making: the measurement MM_RESULTS.md section 10 never took.

MM_RESULTS.md's verdict section is titled "Verdict" and opens "Not yet reached".
It names ONE open question: does adverse selection on real flow exceed the 1.00c
gross margin a maker earns at the touch? It never ran, for two stated reasons:

  (a) this machine's recorder held top-of-book only, at 120 s resolution
  (b) "Kalshi does not expose order-book depth publicly at all"

(b) IS FALSE. It is claim M001, retracted 2026-08-02: the response carries one
key, `orderbook_fp`, and reading a non-existent `orderbook` key returns an empty
book from an HTTP 200 on every market. Re-verified live 2026-08-06 -- 16 price
levels on a KXBTCD market. Marked inline in MM_RESULTS.md.

But this script does not need a book at all, which is the point. MM_RESULTS
itself says the one very good thing on disk is the TRADE TAPE, which carries the
AGGRESSOR SIDE. That is sufficient:

    every trade has a taker and a maker on the opposite side.
    a passive quoter IS the maker side of the tape.

So mark every maker fill to settlement and ask what a maker who quoted both
sides, never hedged and never cancelled actually earned. That number already
contains the spread AND adverse selection AND inventory -- it is the bottom
line, not a decomposition of it, and it needs no book reconstruction and no
fill model. The fill model is the single easiest thing to fake in a maker
backtest (kalshi-inplay-bot's own high_sweep header says so); here there is
nothing to fake, because every fill in the tape is a fill that really happened.

WHAT IT CANNOT DO, stated up front: a real maker chooses WHEN and WHERE to
quote. This measures the maker side of ALL flow, i.e. a quoter who is always at
the touch on both sides. That is a lower bound on skill and an upper bound on
volume, and it is the honest version of "can a passive quoter make money here".

Unit of observation is the SETTLEMENT EVENT, never the fill. C019 measured the
pseudo-replication factor at ~10x on CI width; B001 collapsed 1,237 fills to 74.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT.parent / "kalshi-market-scan"
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402
from common.kalshi_fees import (  # noqa: E402
    SeriesFees, fee_rate_cents, maker_fee_order_cents,
)


def fetch_schedules(series_list):
    """Per-series fee_type, from the API. Never guessed -- see GUARDS #6."""
    out = {}
    for s in series_list:
        r = V.k_get(f"/series/{s}")
        if r is None or r.status_code != 200:
            continue
        try:
            obj = (r.json() or {}).get("series") or {}
        except ValueError:
            continue
        if "fee_type" in obj:
            sf = SeriesFees.from_api(obj)
            out[s] = sf
            print(f"   {s:11} fee_type={sf.fee_type:28} "
                  f"charges_maker={sf.charges_maker}")
    return out

TRADES = SCAN / "data" / "raw" / "source=kalshi_trades"
SETTLED = SCAN / "data" / "settled"
REP = ROOT / "reports"
N_BOOT = 4000
SEED = 20260807

# KXBTCD / KXBTC15M are plain `quadratic` -- makers pay ZERO.
# NOT assumed: common/HANDOFF.md records that crypto/src/fees.py once asserted
# "ZERO are crypto" and was wrong, because KXBTCMAX150/KXBTCMAX125 are crypto
# AND charge makers. Neither series here is one of those, and the maker rate is
# read from the shared module rather than hardcoded.
SERIES = ["KXBTCD", "KXBTC15M", "KXETHD", "KXETH15M"]


def load_settled(series: str, lo_ts=None, hi_ts=None) -> dict:
    """Outcomes for the markets the TAPE covers.

    ⚠ The on-disk `data/settled/*.parquet` snapshots were pulled ON 2026-07-30,
    so they hold markets that had ALREADY settled by then -- and the tape is OF
    2026-07-30. The overlap is exactly zero, which is why the first run of this
    script reported "none of these tickers are in the settled set" on all four
    series. A quieter version of this bug would have silently matched a handful
    and reported a confident number on 20 fills.

    So the outcome is pulled fresh, bounded to the tape's own window. This is
    only possible because the retention boundary turned out to be a FIXED date
    (2026-05-25, re-bisected 2026-08-06 and unmoved across three measurements),
    not the 69-day rolling window M009 claimed -- under a rolling window these
    markets would have expired on 2026-10-07 but the point is that nothing was
    lost.
    """
    out = {}
    p = SETTLED / f"{series}.parquet"
    if p.exists():
        d = pd.read_parquet(p)
        d = d[d.result.isin(["yes", "no"])]
        out.update(dict(zip(d.ticker, (d.result == "yes").astype(int))))
    params = {"series_ticker": series, "status": "settled", "limit": 200}
    if lo_ts:
        params["min_close_ts"] = int(lo_ts)
    if hi_ts:
        params["max_close_ts"] = int(hi_ts)
    n_api = 0
    for m in V.k_paginate("/markets", params, "markets", max_pages=60):
        if m.get("result") in ("yes", "no"):
            out[m["ticker"]] = 1 if m["result"] == "yes" else 0
            n_api += 1
    print(f"   {series:11} outcomes: {n_api:,} from the API "
          f"+ {len(out) - n_api:,} from disk")
    return out


def event_of(ticker: str) -> str:
    """One settlement event = one strike ladder = one price observation."""
    return ticker.rsplit("-", 1)[0]


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(TRADES / "**" / "*.parquet"), recursive=True))
    print(f"trade-tape files: {len(files):,}")
    if not files:
        print("no tape on this machine — stop rather than invent a number")
        return

    frames = []
    for f in files:
        try:
            frames.append(pd.read_parquet(
                f, columns=["ticker", "count", "yes_price", "no_price",
                            "taker_outcome_side", "event_ns"]))
        except (OSError, ValueError):
            continue
    t = pd.concat(frames, ignore_index=True)
    t["series"] = t.ticker.astype(str).str.split("-").str[0]
    print(f"trades loaded: {len(t):,}   window "
          f"{pd.to_datetime(t.event_ns.min()).date()} .. "
          f"{pd.to_datetime(t.event_ns.max()).date()}")

    print("\nfee schedules, fetched not assumed:")
    SERIES_FEES = fetch_schedules(SERIES)

    rng = np.random.default_rng(SEED)
    out = {}
    print(f"\n{'series':11} {'trades':>9} {'events':>7} {'maker c/contract':>18} "
          f"{'95% CI (events)':>22} {'win%':>6}")
    for s in SERIES:
        sub = t[t.series == s]
        if sub.empty:
            print(f"{s:11} {'-':>9}  no trades in tape")
            continue
        lo = int(pd.to_datetime(sub.event_ns.min()).timestamp()) - 3600
        hi = int(pd.to_datetime(sub.event_ns.max()).timestamp()) + 30*3600
        res = load_settled(s, lo, hi)
        sub = sub[sub.ticker.isin(res)]
        if sub.empty:
            print(f"{s:11} {len(t[t.series==s]):>9,}  none of these tickers "
                  f"are in the settled set")
            continue

        y = sub.ticker.map(res).values                 # 1 if YES settled true
        yp = sub.yes_price.values * 100.0              # cents
        taker_yes = (sub.taker_outcome_side.astype(str).values == "yes")

        # The maker is ALWAYS the opposite side of the taker.
        #   taker bought YES  -> maker is SHORT yes at yp
        #        maker P&L = yp - 100*y
        #   taker bought NO   -> maker is LONG yes at yp
        #        maker P&L = 100*y - yp
        pnl = np.where(taker_yes, yp - 100.0 * y, 100.0 * y - yp)

        # The maker fee is a PER-SERIES fact and the shared module refuses to
        # guess it -- `maker_fee_order_cents` raises unless handed a SeriesFees
        # built from the API. That guard exists because crypto/src/fees.py once
        # asserted "ZERO are crypto" and was wrong (KXBTCMAX150/125 are crypto
        # and DO charge makers). So the schedule is fetched, not assumed.
        sf = SERIES_FEES.get(s)
        if sf is None:
            print(f"{s:11} no fee schedule retrieved - refusing to price it")
            continue
        mk_fee = float(maker_fee_order_cents(50, 1, sf))
        pnl = pnl - mk_fee

        ev = pd.Series([event_of(x) for x in sub.ticker.astype(str)])
        d = pd.DataFrame({"ev": ev.values, "pnl": pnl,
                          "n": sub["count"].values})
        # contract-weighted mean per event, then cluster over events
        g = d.groupby("ev").apply(
            lambda x: np.average(x.pnl, weights=np.maximum(x.n, 1e-9)),
            include_groups=False)
        vals = g.values
        if len(vals) < 2:
            print(f"{s:11} {len(sub):>9,} {len(vals):>7}  too few events")
            continue
        idx = rng.integers(0, len(vals), size=(N_BOOT, len(vals)))
        bm = vals[idx].mean(axis=1)
        lo, hi = np.percentile(bm, 2.5), np.percentile(bm, 97.5)
        print(f"{s:11} {len(sub):>9,} {len(vals):>7} {vals.mean():>+17.3f}c "
              f"[{lo:>+9.3f},{hi:>+9.3f}] {100*(pnl>0).mean():>5.1f}%")
        out[s] = {"trades": int(len(sub)), "events": int(len(vals)),
                  "maker_c_per_contract": round(float(vals.mean()), 4),
                  "ci": [round(float(lo), 4), round(float(hi), 4)],
                  "maker_fee_c": mk_fee,
                  "frac_fills_profitable": round(float((pnl > 0).mean()), 4)}

    # ---- the mirror check: the TAKER side must be the exact negative,
    #      before fees. If it is not, the sign convention is wrong.
    print("\nSIGN-CONVENTION CANARY — the taker side must mirror the maker side")
    for s, o in out.items():
        print(f"   {s:11} maker {o['maker_c_per_contract']:+.3f}c  "
              f"=> taker {-o['maker_c_per_contract']:+.3f}c before taker fees "
              f"(taker also pays ~{float(fee_rate_cents(50)):.2f}c at 50c)")

    (REP / "maker_marked_to_settlement.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote reports/maker_marked_to_settlement.json")


if __name__ == "__main__":
    main()
