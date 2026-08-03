"""Kalshi favourite-longshot test, properly powered.

v2 concluded "no bias" but on only 19-52 matches per price bucket, which rules out a
large bias and not a small one. The binding constraint was that the trades endpoint
returns newest-first, so reaching pre-match fills needed deep pagination.

`max_ts` solves it: one request per market returns the fills immediately preceding a
chosen cutoff. So a clean pre-match snapshot costs ONE request per market per horizon
instead of ~20, and n can be raised by an order of magnitude.

Design:
  - one observation per (market, horizon): the size-weighted price actually paid by
    takers just before the cutoff, and the single realised outcome. Clustering is
    structural rather than a correction applied afterwards.
  - several horizons, so we can see whether calibration degrades further from the event
  - binomial test per price bucket, n = markets. Binary outcomes get a binomial test,
    not a normal approximation on P&L, which is what produced v2's degenerate-variance
    false positives when every match in a bucket resolved the same way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402
from kalshi_research.fees import taker_fee_dollars  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

SERIES = [
    "KXATPMATCH", "KXWTAMATCH", "KXITFMATCH", "KXITFWMATCH",
    "KXMLBGAME", "KXNBAGAME", "KXNHLGAME", "KXWNBAGAME",
    "KXEPLGAME", "KXUCLGAME", "KXNFLGAME", "KXMLSGAME",
]
MARKETS_PER_SERIES = 400
HORIZONS_MIN = [60, 240, 1440]  # 1h, 4h, 24h before the event ends
BUCKETS = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]
ROUND_TRIP_C = 2.4


def fetch_settled(c: KalshiPublicClient, series: str, n: int) -> list[dict]:
    out, cur = [], None
    while len(out) < n:
        p = {"series_ticker": series, "status": "settled", "limit": 200}
        if cur:
            p["cursor"] = cur
        try:
            d = c.get("/markets", p)
        except Exception:  # noqa: BLE001
            break
        mk = d.get("markets") or []
        if not mk:
            break
        out += [
            m for m in mk
            if m.get("result") in ("yes", "no") and m.get("close_time")
        ]
        cur = d.get("cursor")
        if not cur:
            break
    return out[:n]


def snapshot(c: KalshiPublicClient, ticker: str, cutoff_unix: int) -> list[dict]:
    try:
        d = c.get("/markets/trades",
                  {"ticker": ticker, "limit": 100, "max_ts": cutoff_unix})
    except Exception:  # noqa: BLE001
        return []
    return d.get("trades") or []


def main() -> None:
    c = KalshiPublicClient(rps=3.5)
    rows = []
    for ser in SERIES:
        mkts = fetch_settled(c, ser, MARKETS_PER_SERIES)
        if not mkts:
            print(f"{ser}: none")
            continue
        got = 0
        for m in mkts:
            tk, res = m["ticker"], m["result"]
            close = pd.Timestamp(m["close_time"])
            for H in HORIZONS_MIN:
                cutoff = int((close - pd.Timedelta(minutes=H)).timestamp())
                tr = snapshot(c, tk, cutoff)
                if not tr:
                    continue
                px, wt, n_used = [], [], 0
                for t in tr:
                    side = t.get("taker_outcome_side")
                    if side not in ("yes", "no"):
                        continue
                    try:
                        p = float(t["yes_price_dollars"]) if side == "yes" \
                            else float(t["no_price_dollars"])
                        cnt = max(float(t["count_fp"]), 1e-9)
                    except (TypeError, ValueError, KeyError):
                        continue
                    if not 0.005 < p < 0.995:
                        continue
                    won = int((res == "yes") if side == "yes" else (res == "no"))
                    px.append(p * won if False else p)
                    wt.append(cnt)
                    n_used += 1
                    rows.append({
                        "series": ser, "ticker": tk, "horizon_min": H,
                        "price": p, "won": won, "count": cnt,
                    })
                got += 1 if n_used else 0
        print(f"{ser}: {len(mkts)} markets, snapshots for {got} "
              f"(req={c.n_req} 429={c.n_429})", flush=True)

    if not rows:
        print("nothing collected")
        return
    fills = pd.DataFrame(rows)
    fills.to_parquet(REPORTS / "kalshi_longshot_v3_fills.parquet", index=False)

    # ---- collapse to ONE observation per (market, horizon) -----------------
    def collapse(g: pd.DataFrame) -> pd.Series:
        w = np.maximum(g["count"].values, 1e-9)
        return pd.Series({
            "price": float(np.average(g.price.values, weights=w)),
            "won": float(g.won.iloc[0]) if g.won.nunique() == 1 else float(g.won.mean()),
            "n_fills": int(len(g)),
        })

    obs = (fills.groupby(["ticker", "horizon_min"])
           .apply(collapse, include_groups=False).reset_index())
    obs = obs[obs.won.isin([0.0, 1.0])]
    obs.to_parquet(REPORTS / "kalshi_longshot_v3_obs.parquet", index=False)

    print("\n" + "=" * 88)
    print(f"KALSHI FAVOURITE-LONGSHOT, PROPERLY POWERED")
    print(f"{len(fills):,} fills -> {len(obs):,} market-horizon observations, "
          f"{obs.ticker.nunique():,} distinct markets")
    print("=" * 88)

    summary = {}
    for H in HORIZONS_MIN:
        d = obs[obs.horizon_min == H]
        if len(d) < 50:
            print(f"\n--- {H} min before event end: only {len(d)} obs, skipping ---")
            continue
        d = d.copy()
        d["bucket"] = pd.cut(d.price, BUCKETS)
        print(f"\n--- {H} min before event end  (n={len(d):,} markets) ---")
        print(f"{'bucket':>12} {'markets':>8} {'wins':>6} {'fair':>7} {'obs':>7} "
              f"{'edge_pp':>9} {'binom_p':>9}  {'net of fee':>11}")
        recs = []
        for b, g in d.groupby("bucket", observed=True):
            n = len(g)
            if n < 15:
                continue
            k = int(g.won.sum())
            p0 = float(np.clip(g.price.mean(), 1e-6, 1 - 1e-6))
            bt = stats.binomtest(k, n, p0)
            edge = (k / n - p0) * 100
            fee_c = 2 * taker_fee_dollars(10_000, p0) * 100 / 10_000
            net = edge - fee_c
            flag = "SIGNIF" if bt.pvalue < 0.05 else ""
            print(f"{str(b):>12} {n:>8} {k:>6} {p0:>7.3f} {k/n:>7.3f} "
                  f"{edge:>+8.2f}pp {bt.pvalue:>9.3f}  {net:>+10.2f}pp {flag}")
            recs.append({"bucket": str(b), "n_markets": n, "wins": k,
                         "fair": p0, "observed": k / n, "edge_pp": edge,
                         "binom_p": bt.pvalue, "net_of_fee_pp": net})
        summary[str(H)] = recs
        # overall calibration at this horizon
        k, n = int(d.won.sum()), len(d)
        p0 = float(d.price.mean())
        bt = stats.binomtest(k, n, p0)
        print(f"  OVERALL: {k}/{n} = {k/n:.4f} vs fair {p0:.4f}  "
              f"edge {(k/n-p0)*100:+.2f}pp  binomial p={bt.pvalue:.4f}")

    # ---- the decisive comparison ------------------------------------------
    poly = {"(0.1, 0.2]": -6.39, "(0.2, 0.3]": -8.03, "(0.4, 0.5]": -2.34,
            "(0.5, 0.6]": 5.09, "(0.6, 0.7]": 8.57, "(0.7, 0.8]": 9.63,
            "(0.9, 1.0]": 2.16}
    best_H = max((h for h in HORIZONS_MIN if str(h) in summary),
                 key=lambda h: sum(r["n_markets"] for r in summary[str(h)]),
                 default=None)
    if best_H is None:
        return
    print("\n" + "=" * 88)
    print(f"KALSHI (at {best_H} min pre-event) vs POLYMARKET — can we now exclude it?")
    print("=" * 88)
    print(f"{'bucket':>12} {'Kalshi':>10} {'95% CI':>18} {'Polymarket':>11}  verdict")
    n_excl = n_tot = 0
    for r in summary[str(best_H)]:
        k, n, p0 = r["wins"], r["n_markets"], r["fair"]
        lo, hi = stats.binomtest(k, n, p0).proportion_ci(confidence_level=0.95)
        lo_pp, hi_pp = (lo - p0) * 100, (hi - p0) * 100
        pv = poly.get(r["bucket"])
        if pv is None:
            ps, verdict = "   --   ", ""
        else:
            n_tot += 1
            excluded = pv < lo_pp or pv > hi_pp
            n_excl += excluded
            ps = f"{pv:+.2f}pp"
            verdict = "POLYMARKET VALUE EXCLUDED" if excluded else "cannot exclude"
        print(f"{r['bucket']:>12} {r['edge_pp']:>+9.2f}pp "
              f"[{lo_pp:>+6.2f},{hi_pp:>+6.2f}]pp {ps:>11}  {verdict}")
    print(f"\n  Polymarket values excluded in {n_excl}/{n_tot} comparable buckets")

    (REPORTS / "kalshi_longshot_v3.json").write_text(json.dumps({
        "n_fills": int(len(fills)), "n_obs": int(len(obs)),
        "n_markets": int(obs.ticker.nunique()),
        "by_horizon": summary,
        "polymarket_excluded": f"{n_excl}/{n_tot}",
    }, indent=1, default=str))
    print(f"\nwrote {REPORTS/'kalshi_longshot_v3.json'}")


if __name__ == "__main__":
    main()
