"""The crypto maker test, on many days. Placebo-first.

MM_RESULTS_MAKER.md ran this on ONE day: all four series looked positive
(+0.70 to +1.93c) and then the placebo -- shuffling WHICH SIDE WAS THE AGGRESSOR
within each event -- returned +1.351c against the real +0.873c on KXBTC15M,
p=0.995. "Always buy YES" returned +3.874c on the same data, naming the apparent
edge as a one-day directional move rather than a maker edge.

This re-runs it on ~37 days from `data/trade_tape.db`. KXBTC15M is ONE market per
event, so the event count is the ticker count and there is no ladder
pseudo-replication to correct for (contrast K003, where a ten-strike ladder was
counted as ten markets and the intervals came out ~3x too tight).

THE TEST STATISTIC IS `real - placebo`, NOT `real`. That is the whole lesson of
the one-day run: `real` was positive and meaningless. A maker edge must be
something the aggressor label carries, and the placebo destroys exactly that
label while preserving prices, outcomes, sizes and clustering.

Reported alongside, because each kills a different way of being wrong:
  D1  always-long-yes / always-short-yes -- the directional artifact
  D2  a per-day breakdown -- is any single day carrying it (GUARDS #19)
  D3  a stability curve over increasing event counts -- a statistic that
      wanders was never a measurement
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402
from common.kalshi_fees import SeriesFees, maker_fee_order_cents  # noqa: E402

DB = ROOT / "data" / "trade_tape.db"
REP = ROOT / "reports"
N_BOOT = 4000
N_PERM = 300
SEED = 20260807


def fee_for(series: str):
    r = V.k_get(f"/series/{series}")
    if r is None or r.status_code != 200:
        return None
    try:
        obj = (r.json() or {}).get("series") or {}
    except ValueError:
        return None
    return SeriesFees.from_api(obj) if "fee_type" in obj else None


def make_grouper(ev):
    """Contract-weighted per-event mean via bincount.

    A pandas groupby-apply over 3.5 M rows, 300 times for the permutation null,
    is minutes of wall clock. bincount is the same arithmetic in one pass and
    makes the placebo affordable -- which matters, because the placebo is the
    test statistic here, not a nicety.
    """
    codes, uniq = pd.factorize(ev)
    return codes, len(uniq)


def event_means(codes, n_ev, pnl, w):
    w = np.maximum(w, 1e-9)
    num = np.bincount(codes, weights=pnl * w, minlength=n_ev)
    den = np.bincount(codes, weights=w, minlength=n_ev)
    return num / den


def boot_ci(v, rng):
    if len(v) < 2:
        return (np.nan, np.nan)
    idx = rng.integers(0, len(v), size=(N_BOOT, len(v)))
    m = v[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    if not DB.exists():
        print("no trade_tape.db - run pull_trade_tape.py first")
        return
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=300)
    # Drop rows the arithmetic cannot use, and COUNT them rather than letting
    # them coerce. A null yes_price silently becoming 0 would price a fill at
    # 0c and hand the maker a free 100c winner -- exactly the shape of defect
    # that manufactures an edge. The first run crashed on it, which is the
    # lucky outcome.
    n_all = pd.read_sql(
        "select count(*) n from trades t join markets m on m.ticker=t.ticker "
        "where m.result in ('yes','no')", con).n[0]
    t = pd.read_sql(
        "select t.ticker, t.series, t.count, t.yes_price, t.taker_outcome_side, "
        "m.result, m.close_time from trades t join markets m on m.ticker=t.ticker "
        "where m.result in ('yes','no') and t.yes_price is not null "
        "and t.count is not null and t.taker_outcome_side in ('yes','no')", con)
    con.close()
    print(f"dropped {n_all - len(t):,} of {n_all:,} rows for a null price, "
          f"null size or missing aggressor side "
          f"({100*(n_all-len(t))/max(n_all,1):.3f}%)")
    if t.empty:
        print("no joined trades")
        return
    t["day"] = t.close_time.str[:10]
    print(f"trades {len(t):,}   events {t.ticker.nunique():,}   "
          f"days {t.day.nunique()}   {t.day.min()} .. {t.day.max()}")

    rng = np.random.default_rng(SEED)
    out = {}
    for s in sorted(t.series.unique()):
        sub = t[t.series == s]
        sf = fee_for(s)
        if sf is None:
            print(f"\n{s}: no fee schedule retrieved - refusing to price it")
            continue
        mk = float(maker_fee_order_cents(50, 1, sf))
        y = (sub.result.values == "yes").astype(float)
        yp = sub.yes_price.values * 100.0
        ty = (sub.taker_outcome_side.astype(str).values == "yes")
        ev = sub.ticker.values
        w = sub["count"].values

        def pnl_of(taker_yes):
            # the maker is always the opposite side of the taker
            return np.where(taker_yes, yp - 100.0 * y, 100.0 * y - yp) - mk

        codes, n_ev = make_grouper(ev)
        real_g = event_means(codes, n_ev, pnl_of(ty), w)
        real = float(real_g.mean())
        lo, hi = boot_ci(real_g, rng)

        print(f"\n{'='*72}\n{s}   events={len(real_g):,}  trades={len(sub):,}  "
              f"maker fee={mk:.2f}c (charges_maker={sf.charges_maker})\n{'='*72}")
        print(f"   REAL maker P&L      {real:+.4f}c   95% CI [{lo:+.4f},{hi:+.4f}]")

        # ---------------- THE PLACEBO: destroy the aggressor label only
        order = np.argsort(codes, kind="stable")
        bounds = np.searchsorted(codes[order], np.arange(n_ev + 1))
        groups = [order[bounds[k]:bounds[k + 1]] for k in range(n_ev)]
        perm = []
        for _ in range(N_PERM):
            sh = ty.copy()
            for arr in groups:
                v = sh[arr]
                rng.shuffle(v)
                sh[arr] = v
            perm.append(float(event_means(codes, n_ev, pnl_of(sh), w).mean()))
        perm = np.array(perm)
        diff = real - perm.mean()
        p = float((np.abs(perm - perm.mean()) >= abs(diff)).mean())
        print(f"   PLACEBO (aggressor shuffled within event)")
        print(f"      mean {perm.mean():+.4f}c   sd {perm.std():.4f}c   "
              f"p2.5 {np.percentile(perm,2.5):+.4f}  p97.5 {np.percentile(perm,97.5):+.4f}")
        print(f"   >>> REAL - PLACEBO = {diff:+.4f}c      permutation p = {p:.4f}")

        # ---------------- D1 directional controls
        dl = float(event_means(codes, n_ev, 100.0 * y - yp, w).mean())
        ds = float(event_means(codes, n_ev, yp - 100.0 * y, w).mean())
        print(f"   D1 always-long-yes {dl:+.4f}c   always-short-yes {ds:+.4f}c")

        # ---------------- D2 per day
        dd = pd.DataFrame({"day": sub.day.values, "ev": ev,
                           "p": pnl_of(ty), "w": w})
        per = dd.groupby("day").apply(
            lambda x: np.average(x.p, weights=np.maximum(x.w, 1e-9)),
            include_groups=False)
        print(f"   D2 per-day maker P&L: n_days={len(per)}  "
              f"mean {per.mean():+.3f}c  sd {per.std():.3f}c  "
              f"positive on {100*(per>0).mean():.0f}% of days")

        # ---------------- D3 stability curve
        order = np.argsort(sub.close_time.values)
        uniq = pd.unique(ev[order])
        pts = []
        for frac in (0.25, 0.5, 0.75, 1.0):
            keep = set(uniq[: max(2, int(len(uniq) * frac))])
            m = np.isin(ev, list(keep))
            c2, n2 = make_grouper(ev[m])
            pts.append((frac, float(event_means(c2, n2, pnl_of(ty)[m], w[m]).mean())))
        print("   D3 stability: " + "  ".join(
            f"{int(f*100)}%={v:+.3f}c" for f, v in pts))

        out[s] = {"events": int(n_ev), "trades": int(len(sub)),
                  "maker_fee_c": mk, "real_c": round(real, 4),
                  "ci": [round(lo, 4), round(hi, 4)],
                  "placebo_mean_c": round(float(perm.mean()), 4),
                  "placebo_sd_c": round(float(perm.std()), 4),
                  "real_minus_placebo_c": round(float(diff), 4),
                  "perm_p": round(p, 5),
                  "always_long_yes_c": round(dl, 4),
                  "always_short_yes_c": round(ds, 4),
                  "days": int(len(per)),
                  "day_positive_frac": round(float((per > 0).mean()), 4),
                  "stability": [[f, round(v, 4)] for f, v in pts]}

    (REP / "maker_multiday.json").write_text(json.dumps(out, indent=1),
                                             encoding="utf-8")
    print("\nwrote reports/maker_multiday.json")


if __name__ == "__main__":
    main()
