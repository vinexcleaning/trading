"""The headline comparison, clustered by market: our probability vs Kalshi's mid.

`score_vs_mid.py` reported a paired difference over 2,543 snapshots from 25 markets.
Snapshots within a market share ONE settlement, so that CI is far too tight -- the same
pseudo-replication trap caught twice already. Effective n is the number of markets.

This version:
  - scores at fixed decision offsets, one observation per (market, offset)
  - clusters the CI by market via a market-level bootstrap
  - reports the microstructure profile from the full multi-hour tape, which corrects an
    earlier claim made from a single market over three minutes
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402
from kalshi_research.evaluate import brier  # noqa: E402
from kalshi_research.fees import taker_fee_dollars  # noqa: E402
from kalshi_research.models import settlement_aware_prob_above  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
OFFSETS = [720, 600, 480, 300, 180, 120, 60]


def top_of_book(df: pd.DataFrame) -> pd.DataFrame:
    yes = (df[df.side == "yes"].groupby(["ticker", "recv_ns"])
           .apply(lambda g: pd.Series({"yes_bid": g.price.max(),
                                       "yes_bid_size": g.loc[g.price.idxmax(), "size"]}),
                  include_groups=False))
    no = (df[df.side == "no"].groupby(["ticker", "recv_ns"])
          .apply(lambda g: pd.Series({"no_bid": g.price.max(),
                                      "no_bid_size": g.loc[g.price.idxmax(), "size"]}),
                 include_groups=False))
    t = yes.join(no, how="inner").reset_index()
    t["yes_ask"] = 1.0 - t.no_bid
    t["mid"] = (t.yes_bid + t.yes_ask) / 2
    t["spread_c"] = (t.yes_ask - t.yes_bid) * 100
    t["touch_depth"] = t[["yes_bid_size", "no_bid_size"]].min(axis=1)
    return t


def main() -> None:
    fs = sorted(glob.glob(str(RAW / "source=kalshi_book_tier*" / "**" / "*.parquet"),
                          recursive=True))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df = df[df.side.isin(["yes", "no"]) & df.ticker.str.startswith("KXBTC15M")]
    tob = top_of_book(df)
    print(f"snapshots: {len(tob):,} across {tob.ticker.nunique()} markets")

    c = KalshiPublicClient(rps=2.0)
    meta = {}
    for tk in tob.ticker.unique():
        try:
            m = (c.get("/markets", {"tickers": tk, "limit": 1}).get("markets") or [{}])[0]
            if m.get("result") in ("yes", "no"):
                meta[tk] = {"close": pd.Timestamp(m["close_time"]),
                            "strike": float(m["floor_strike"]),
                            "y": int(m["result"] == "yes")}
        except Exception:  # noqa: BLE001,S112
            continue
    print(f"settled with a usable strike: {len(meta)}")
    tob = tob[tob.ticker.isin(meta)].copy()
    tob["close_ns"] = tob.ticker.map(lambda t: meta[t]["close"]).astype(
        "datetime64[ns, UTC]").astype("int64")
    tob["secs"] = (tob.close_ns - tob.recv_ns) / 1e9
    tob["y"] = tob.ticker.map(lambda t: meta[t]["y"])
    tob["strike"] = tob.ticker.map(lambda t: meta[t]["strike"])
    live = tob[(tob.secs > 0) & (tob.secs <= 900)].copy()

    # ---------------- microstructure, from the full tape -------------------
    live["bucket"] = pd.cut(live.secs, [0, 60, 120, 300, 600, 900],
                            labels=["0-60s", "60-120s", "2-5m", "5-10m", "10-15m"])
    prof = live.groupby("bucket", observed=True).agg(
        n_snaps=("mid", "size"), n_markets=("ticker", "nunique"),
        median_spread_c=("spread_c", "median"),
        median_touch_depth=("touch_depth", "median"),
        median_mid=("mid", "median"))
    prof["fee_c"] = prof.median_mid.map(
        lambda p: 2 * taker_fee_dollars(10_000, float(np.clip(p, .01, .99))) * 100 / 10_000)
    prof["breakeven_c"] = prof.fee_c + prof.median_spread_c
    print("\n=== MICROSTRUCTURE (full tape) ===")
    print(prof.round(2).to_string())
    prof.to_csv(REPORTS / "btc15m_microstructure_full.csv")

    # ---------------- spot for the model -----------------------------------
    sfs = sorted(glob.glob(str(RAW / "source=ext_spot" / "**" / "*.parquet"),
                           recursive=True))
    spot = pd.concat([pd.read_parquet(f) for f in sfs], ignore_index=True)
    spot = spot[(spot.symbol == "BTCUSD") & (spot.venue == "coinbase")].sort_values("recv_ns")
    spot = spot.dropna(subset=["last"])
    lr = np.log(spot.last.values)
    sigma_step = float(np.nanstd(np.diff(lr)))
    dt_s = float(np.median(np.diff(spot.recv_ns.values)) / 1e9)
    print(f"\nspot: {len(spot):,} samples, {dt_s:.1f}s apart, "
          f"per-sample sigma {sigma_step:.6f}")

    # ---------------- one observation per (market, offset) -----------------
    rows = []
    for tk, g in live.groupby("ticker"):
        g = g.sort_values("secs")
        for off in OFFSETS:
            i = (g.secs - off).abs().idxmin()
            r = g.loc[i]
            if abs(r.secs - off) > 25:
                continue
            j = np.searchsorted(spot.recv_ns.values, r.recv_ns) - 1
            if j < 0:
                continue
            S = float(spot.last.values[j])
            n_steps = max(r.secs / dt_s, 1e-9)
            sig = sigma_step * np.sqrt(n_steps)
            p_model = float(settlement_aware_prob_above(
                np.array([S]), np.array([r.strike]), np.array([sig]),
                np.array([r.secs]), 60.0)[0])
            rows.append({"ticker": tk, "offset": off, "secs": r.secs,
                         "mid": r["mid"], "p_model": p_model, "y": int(r.y),
                         "spread_c": r.spread_c, "depth": r.touch_depth})
    panel = pd.DataFrame(rows)
    panel.to_parquet(REPORTS / "vs_mid_clustered_panel.parquet", index=False)
    print(f"\npanel: {len(panel)} observations, {panel.ticker.nunique()} markets")

    # ---------------- market-clustered bootstrap ---------------------------
    print("\n" + "=" * 84)
    print("OUR MODEL vs KALSHI'S MID  (CI bootstrapped over MARKETS, not snapshots)")
    print("=" * 84)
    print(f"{'offset':>8} {'markets':>8} {'ourBrier':>10} {'midBrier':>10} "
          f"{'diff':>10} {'95% CI (clustered)':>26}  verdict")
    out = []
    rng = np.random.default_rng(0)
    for off, g in panel.groupby("offset"):
        tks = g.ticker.unique()
        n = len(tks)
        if n < 8:
            continue
        bm, bd = brier(g.p_model.values, g.y.values), brier(g["mid"].values, g.y.values)
        # bootstrap whole markets
        by = {t: gg for t, gg in g.groupby("ticker")}
        boot = []
        for _ in range(4000):
            pick = rng.choice(tks, n, replace=True)
            d = pd.concat([by[t] for t in pick])
            boot.append(brier(d["mid"].values, d.y.values)
                        - brier(d.p_model.values, d.y.values))
        lo, hi = np.percentile(boot, [2.5, 97.5])
        diff = bd - bm
        v = ("WE BEAT MID" if lo > 0 else
             "MID BEATS US" if hi < 0 else "no difference")
        print(f"{off:>7}s {n:>8} {bm:>10.5f} {bd:>10.5f} {diff:>+10.5f} "
              f"[{lo:>+9.5f},{hi:>+9.5f}]  {v}")
        out.append({"offset_s": off, "n_markets": int(n), "brier_model": bm,
                    "brier_mid": bd, "diff": diff, "ci_lo": lo, "ci_hi": hi,
                    "verdict": v})

    res = pd.DataFrame(out)
    res.to_csv(REPORTS / "vs_mid_clustered.csv", index=False)
    n_win = int((res.ci_lo > 0).sum())
    n_lose = int((res.ci_hi < 0).sum())
    print(f"\n  offsets where we beat the mid: {n_win}/{len(res)}")
    print(f"  offsets where the mid beats us: {n_lose}/{len(res)}")
    print("\n  VERDICT: " + (
        "no evidence of edge -- the market's mid is at least as good as our model"
        if n_win == 0 else "we beat the mid at some offsets; investigate"))
    (REPORTS / "vs_mid_clustered.json").write_text(json.dumps({
        "n_markets": int(panel.ticker.nunique()),
        "results": out, "offsets_beating_mid": n_win,
        "offsets_losing_to_mid": n_lose,
    }, indent=1, default=str))


if __name__ == "__main__":
    main()
