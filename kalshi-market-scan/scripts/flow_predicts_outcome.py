"""Phase 6 (Kalshi): does one-sided flow predict the outcome BEYOND the price?

The brief's flow-following hypothesis: large accumulating one-sided positions in single
markets are a signal. Kalshi's feed is anonymous, so this is the only version of copy
trading available there.

The test that matters is not "does the flow side win" -- of course it does, flow pushes
price and price predicts outcome. It is whether flow adds information **over and above
the price it has already moved to**. So:

    outcome ~ price_at_cutoff   vs   outcome ~ price_at_cutoff + flow_imbalance

If flow carries no information beyond price, the market has already absorbed it and
there is nothing to follow.

One observation per market. Flow measured strictly before the cutoff; outcome strictly
after. Nothing else is used.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
CUTOFF_S = 120  # measure flow up to 2 minutes before close


def main() -> None:
    fs = sorted(glob.glob(str(RAW / "source=kalshi_trades" / "**" / "*.parquet"),
                          recursive=True))
    tr = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    tr = tr.drop_duplicates(subset=["trade_id"])
    print(f"trades: {len(tr):,}")

    uni = pd.read_parquet(ROOT / "data" / "markets_open.parquet",
                          columns=["ticker", "mve_collection_ticker"])
    combo = set(uni[uni.mve_collection_ticker.notna()].ticker)
    tr = tr[~tr.ticker.isin(combo)]
    tr = tr.dropna(subset=["event_ns", "yes_price", "count"])
    print(f"organic trades: {len(tr):,} across {tr.ticker.nunique():,} markets")

    # only markets with enough flow to constitute a "signal"
    counts = tr.groupby("ticker").size()
    cand = counts[counts >= 30].index
    tr = tr[tr.ticker.isin(cand)]
    print(f"markets with >=30 trades: {tr.ticker.nunique():,}")

    # settlement outcomes
    c = KalshiPublicClient(rps=6.0)
    meta = {}
    tks = list(tr.ticker.unique())
    for i in range(0, len(tks), 20):
        batch = tks[i:i + 20]
        try:
            d = c.get("/markets", {"tickers": ",".join(batch), "limit": 200})
        except Exception:  # noqa: BLE001
            continue
        for m in d.get("markets") or []:
            if m.get("result") in ("yes", "no") and m.get("close_time"):
                meta[m["ticker"]] = {
                    "y": int(m["result"] == "yes"),
                    "close_ns": int(pd.Timestamp(m["close_time"]).value),
                }
        if i and i % 400 == 0:
            print(f"  resolved {len(meta)} of {i} checked", flush=True)
    print(f"settled markets with flow: {len(meta):,}")
    if len(meta) < 50:
        print("too few settled markets yet")
        return

    tr = tr[tr.ticker.isin(meta)].copy()
    tr["close_ns"] = tr.ticker.map(lambda t: meta[t]["close_ns"])
    tr["y"] = tr.ticker.map(lambda t: meta[t]["y"])
    tr["secs_to_close"] = (tr.close_ns - tr.event_ns) / 1e9
    pre = tr[tr.secs_to_close >= CUTOFF_S].copy()
    print(f"trades at least {CUTOFF_S}s before close: {len(pre):,}")

    pre["notional"] = pre["count"] * pre.yes_price
    pre["signed"] = np.where(pre.taker_outcome_side.eq("yes"),
                             pre.notional, -pre.notional)

    rows = []
    for tk, g in pre.groupby("ticker"):
        g = g.sort_values("event_ns")
        if len(g) < 20:
            continue
        notional = g.notional.sum()
        if notional <= 0:
            continue
        last_px = float(g.yes_price.iloc[-1])
        rows.append({
            "ticker": tk,
            "y": int(g.y.iloc[0]),
            "price": last_px,
            "flow_imbalance": float(g.signed.sum() / notional),  # -1..+1
            "notional": float(notional),
            "n_trades": int(len(g)),
        })
    p = pd.DataFrame(rows)
    if len(p) < 50:
        print(f"only {len(p)} usable markets")
        return
    p.to_parquet(REPORTS / "flow_predicts_panel.parquet", index=False)
    print(f"\npanel: {len(p):,} settled markets")

    print("\n" + "=" * 80)
    print("1. Does the flow side win? (expected yes -- flow moves price)")
    print("=" * 80)
    p["flow_side_won"] = np.where(p.flow_imbalance > 0, p.y, 1 - p.y)
    strong = p[p.flow_imbalance.abs() > 0.5]
    print(f"  all markets:            flow side won {p.flow_side_won.mean():.4f} "
          f"(n={len(p)})")
    print(f"  |imbalance| > 0.5:      flow side won {strong.flow_side_won.mean():.4f} "
          f"(n={len(strong)})")

    print("\n" + "=" * 80)
    print("2. THE REAL TEST: does flow add information OVER the price?")
    print("=" * 80)
    # residual: outcome minus what the price already implies
    p["resid"] = p.y - p.price
    for lo, hi, lbl in [(-1.01, -0.5, "strong NO flow"), (-0.5, -0.1, "mild NO"),
                        (-0.1, 0.1, "balanced"), (0.1, 0.5, "mild YES"),
                        (0.5, 1.01, "strong YES flow")]:
        g = p[(p.flow_imbalance > lo) & (p.flow_imbalance <= hi)]
        if len(g) < 10:
            continue
        m = g.resid.mean() * 100
        se = g.resid.std(ddof=1) / np.sqrt(len(g)) * 100
        sig = "SIGNIF" if abs(m) > 1.96 * se else ""
        print(f"  {lbl:16s} n={len(g):5d}  mean price {g.price.mean():.3f}  "
              f"win rate {g.y.mean():.3f}  residual {m:+6.2f}pp +/-{1.96*se:5.2f}  {sig}")

    # correlation of flow with the residual: the cleanest single number
    r, pv = stats.pearsonr(p.flow_imbalance, p.resid)
    print(f"\n  corr(flow_imbalance, outcome - price) = {r:+.4f}  p={pv:.4f}  n={len(p)}")
    print("  -> if ~0, flow carries no information the price has not already absorbed")

    print("\n" + "=" * 80)
    print("3. Whale prints specifically")
    print("=" * 80)
    big = p[p.notional > p.notional.quantile(0.9)]
    r2, pv2 = stats.pearsonr(big.flow_imbalance, big.resid)
    print(f"  top-decile notional markets (n={len(big)}): "
          f"corr={r2:+.4f} p={pv2:.4f}")
    print(f"  mean residual: {big.resid.mean()*100:+.2f}pp "
          f"+/-{196*big.resid.std(ddof=1)/np.sqrt(len(big)):.2f}")

    verdict = ("NO SIGNAL — flow adds nothing over price"
               if pv > 0.05 else "flow correlates with the residual; investigate")
    print("\n" + "=" * 80)
    print(f"VERDICT: {verdict}")
    print("=" * 80)
    (REPORTS / "flow_predicts_outcome.json").write_text(json.dumps({
        "n_markets": int(len(p)), "cutoff_s": CUTOFF_S,
        "flow_side_win_rate": float(p.flow_side_won.mean()),
        "corr_flow_residual": float(r), "p_value": float(pv),
        "corr_whales": float(r2), "p_value_whales": float(pv2),
        "verdict": verdict,
    }, indent=1))


if __name__ == "__main__":
    main()
