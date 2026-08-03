"""Kalshi favourite-longshot test, corrected: cluster by match, split in-play from pre-match.

## Why v1 was wrong

v1 reported edges of -20.9pp to +19.5pp with CIs of ~1pp. Those CIs were nonsense:
490,464 fills came from only 762 markets (644 fills per market), and a match settles
ONCE, so fills within a market are not independent observations. The same
pseudo-replication error caught in the Polymarket analysis.

The aggregate was always sane and should have been the tell:
    YES takers paid 0.4704, won 0.4508  ->  -1.96pp
    NO  takers paid 0.4123, won 0.4254  ->  +1.31pp
    overall -0.67pp, with a 2.72% overround
That is a near-efficient market, consistent with Kalshi tennis tracking Betfair at
r = 0.9878.

## The fix

- one observation per (match, price bucket): size-weighted average price paid and the
  single realised outcome
- confidence intervals from the spread ACROSS MATCHES, not across fills
- in-play and pre-match reported separately. `close_time` on a sports market is when
  the event finished, so a fill "30 minutes before close" is mid-match, not pre-match.
  In-play prices are informative by construction, which is not a bias.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
BUCKETS = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]
TENNIS_ROUND_TRIP_C = 2.4


def cluster_table(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Aggregate to one row per (match, bucket), then compute CIs across matches."""
    d = df.copy()
    d["bucket"] = pd.cut(d.price, BUCKETS)
    per = (
        d.groupby(["match", "bucket"], observed=True)
        .apply(lambda x: pd.Series({
            "price": np.average(x.price, weights=np.maximum(x["count"], 1e-9)),
            "won": x.won.iloc[0] if x.won.nunique() == 1 else x.won.mean(),
            "fills": len(x),
        }), include_groups=False)
        .reset_index()
    )
    per["pnl"] = per.won - per.price
    rows = []
    for b, g in per.groupby("bucket", observed=True):
        n = len(g)
        if n < 5:
            continue
        m = g.pnl.mean()
        se = g.pnl.std(ddof=1) / np.sqrt(n)
        rows.append({
            "bucket": str(b), "n_matches": n, "n_fills": int(g.fills.sum()),
            "mean_price": g.price.mean(), "win_rate": g.won.mean(),
            "edge_pp": m * 100, "ci95_pp": 1.96 * se * 100,
            "signif": abs(m) > 1.96 * se,
        })
    t = pd.DataFrame(rows)
    print(f"\n--- {label} ---")
    if t.empty:
        print("  too few matches")
        return t
    print(t.round(3).to_string(index=False))
    return t


def main() -> None:
    p = REPORTS / "kalshi_longshot_trades.parquet"
    if not p.exists():
        print("run longshot_bias_kalshi.py first")
        return
    df = pd.read_parquet(p)
    df["match"] = df.ticker.str.rsplit("-", n=1).str[0]
    print(f"{len(df):,} fills, {df.ticker.nunique():,} markets, "
          f"{df['match'].nunique():,} matches")
    print(f"fills per market: {len(df)/df.ticker.nunique():.0f}  "
          "<- why fill-level CIs were meaningless")

    print("\n" + "=" * 80)
    print("AGGREGATE (the sanity check v1 should have led with)")
    print("=" * 80)
    for side, g in df.groupby("side"):
        print(f"  {side:>3} takers: paid {g.price.mean():.4f}  won {g.won.mean():.4f}"
              f"  edge {(g.won.mean()-g.price.mean())*100:+.2f}pp  n={len(g):,}")
    print(f"  overall edge: {(df.won-df.price).mean()*100:+.2f}pp "
          f"(size-weighted {np.average(df.won-df.price, weights=df['count'])*100:+.2f}pp)")
    s = df.groupby(["ticker", "side"]).price.mean().unstack().dropna()
    print(f"  overround: {(s.yes + s['no']).mean():.4f} -> "
          f"{100*((s.yes + s['no']).mean()-1):.2f}% -- this IS the house edge")

    tables = {}
    tables["all"] = cluster_table(df, "ALL fills, clustered by match")
    inplay = df[df.mins_to_close < 60]
    pre = df[df.mins_to_close >= 120]
    if len(inplay):
        tables["inplay"] = cluster_table(
            inplay, f"IN-PLAY (<60 min to event end), n={len(inplay):,} fills")
    if len(pre) > 200:
        tables["pre"] = cluster_table(
            pre, f"EARLY (>=120 min to event end), n={len(pre):,} fills")

    print("\n" + "=" * 80)
    print("VERDICT vs POLYMARKET")
    print("=" * 80)
    poly = {"(0.1, 0.2]": -6.39, "(0.2, 0.3]": -8.03, "(0.5, 0.6]": 5.09,
            "(0.6, 0.7]": 8.57, "(0.7, 0.8]": 9.63}
    t = tables.get("pre") if "pre" in tables and not tables["pre"].empty else tables["all"]
    which = "EARLY" if ("pre" in tables and not tables["pre"].empty) else "ALL"
    print(f"using the {which} table (in-play prices are informative by construction, "
          "so they cannot test a pricing bias)\n")
    print(f"{'bucket':>12} {'Kalshi':>10} {'+/-95%':>9} {'Polymarket':>11} "
          f"{'net of 2.4c':>12}")
    any_trade = False
    for _, r in t.iterrows():
        pv = poly.get(r.bucket)
        ps = f"{pv:+.2f}pp" if pv is not None else "   --  "
        net = r.edge_pp - TENNIS_ROUND_TRIP_C
        ok = (r.edge_pp - r.ci95_pp) > TENNIS_ROUND_TRIP_C
        any_trade |= bool(ok)
        print(f"{r.bucket:>12} {r.edge_pp:>+9.2f}pp {r.ci95_pp:>8.2f} {ps:>11} "
              f"{net:>+11.2f}pp {'TRADEABLE' if ok else ''}")

    print("\n" + "=" * 80)
    if not any_trade:
        print("CONCLUSION: no bucket clears the 2.4c round trip with a CI excluding it.")
        print("The favourite-longshot bias found on Polymarket does NOT transfer to")
        print("Kalshi at a magnitude that survives fees and honest clustering.")
    else:
        print("CONCLUSION: at least one bucket clears the cost bar -- inspect closely,")
        print("and check it is not driven by a handful of matches.")
    print("=" * 80)

    out = {k: v.to_dict("records") for k, v in tables.items() if not v.empty}
    (REPORTS / "kalshi_longshot_bias_v2.json").write_text(
        json.dumps({"tables": out,
                    "aggregate_edge_pp": float((df.won - df.price).mean() * 100),
                    "n_fills": int(len(df)), "n_matches": int(df["match"].nunique())},
                   indent=1, default=str))
    print(f"\nwrote {REPORTS/'kalshi_longshot_bias_v2.json'}")


if __name__ == "__main__":
    main()
