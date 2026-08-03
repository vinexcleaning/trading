"""Phase 6 (corrected): the four tests at the correct unit of observation.

## Why v1 was wrong, and it mattered

v1 treated each row of `tape_bets` as an independent observation. It is not. A
wallet routinely places dozens of fills on the SAME match, and if that match wins
they all win together. v1's top-ranked "skilled" wallet had:

    edge = +95.0 pp over 21 bets ... all 21 on ONE market, avg price 0.05, won

That is a single coin flip counted 21 times. Across the tape, 12.3% of wallets
with >=20 bets traded fewer than 5 distinct markets. Pseudo-replication of this
kind understates every standard error and manufactured 1,684 "significant"
wallets after FDR, which is why v1 reported SKILL PRESENT while the persistence
test reported NOT PERSISTENT. The two tests disagreed because one of them was
counting wrong.

## The fix

One observation per (wallet, market): the wallet's size-weighted average entry
price in that market and the single binary outcome. Skill is then measured across
markets, requiring MIN_MARKETS distinct settlements per wallet per period.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NB = ROOT / "notebooks"
REPORTS.mkdir(exist_ok=True)

TAPE_DB = Path(r"C:\Users\vinig\tennis copy trade\data\tape_scan.db")
MIN_MARKETS = 20  # distinct settled markets, per period
TENNIS_ROUND_TRIP_C = 2.4  # user's measured Kalshi tennis round trip


def _bh(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    if n == 0:
        return p
    o = np.argsort(p)
    q = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.clip(q, 0, 1)
    return out


def load_positions() -> pd.DataFrame:
    """Collapse fills to one row per (wallet, market): the unit that settles once."""
    con = sqlite3.connect(f"file:{TAPE_DB}?mode=ro", uri=True)
    df = pd.read_sql_query(
        "SELECT wallet, condition_id, ts, price, size, won FROM tape_bets "
        "WHERE won IS NOT NULL AND price IS NOT NULL",
        con,
    )
    con.close()
    for c in ("price", "won", "size", "ts"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["price", "won", "ts"])
    df = df[(df.price > 0.005) & (df.price < 0.995)]
    df["size"] = df["size"].fillna(0.0)
    df["notional"] = df["size"] * df.price

    def agg(g: pd.DataFrame) -> pd.Series:
        w = g["size"].sum()
        vwap = (g.price * g["size"]).sum() / w if w > 0 else g.price.mean()
        return pd.Series(
            {
                "entry": float(vwap),
                "won": float(g.won.iloc[0]),
                "size": float(w),
                "notional": float(g.notional.sum()),
                "n_fills": int(len(g)),
                "ts": float(g.ts.min()),
            }
        )

    pos = df.groupby(["wallet", "condition_id"]).apply(agg, include_groups=False)
    pos = pos.reset_index()
    # a market resolves once, so `won` must be constant within the group
    return pos.sort_values("ts").reset_index(drop=True)


def wallet_edge(g: pd.DataFrame) -> pd.Series:
    """Edge per market, so n = number of independent settlements."""
    pnl = g.won - g.entry
    n = len(g)
    return pd.Series(
        {
            "n_markets": n,
            "n_fills": int(g.n_fills.sum()),
            "avg_entry": float(g.entry.mean()),
            "win_rate": float(g.won.mean()),
            "edge": float(pnl.mean()),
            "edge_se": float(pnl.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan,
            "notional": float(g.notional.sum()),
        }
    )


def test1_persistence(pos: pd.DataFrame) -> dict:
    cut = pos.ts.quantile(0.5)
    s1 = pos[pos.ts < cut].groupby("wallet").apply(wallet_edge, include_groups=False)
    s2 = pos[pos.ts >= cut].groupby("wallet").apply(wallet_edge, include_groups=False)
    both = s1.join(s2, lsuffix="_p1", rsuffix="_p2", how="inner")
    both = both[
        (both.n_markets_p1 >= MIN_MARKETS) & (both.n_markets_p2 >= MIN_MARKETS)
    ]
    out = {
        "split_date": str(pd.Timestamp(cut, unit="s")),
        "n_wallets_qualifying": int(len(both)),
        "min_markets_per_period": MIN_MARKETS,
    }
    if len(both) < 8:
        out["verdict"] = "INSUFFICIENT DATA"
        return out
    sp = stats.spearmanr(both.edge_p1, both.edge_p2)
    pe = stats.pearsonr(both.edge_p1, both.edge_p2)
    k = max(1, len(both) // 10)
    top = both.nlargest(k, "edge_p1")
    out.update(
        spearman_rho=float(sp.statistic), spearman_p=float(sp.pvalue),
        pearson_r=float(pe.statistic), pearson_p=float(pe.pvalue),
        top_decile_n=int(k),
        top_decile_edge_p1_pp=float(top.edge_p1.mean() * 100),
        top_decile_edge_p2_pp=float(top.edge_p2.mean() * 100),
        all_wallets_edge_p2_pp=float(both.edge_p2.mean() * 100),
        shrinkage_of_top_decile=float(
            1 - top.edge_p2.mean() / top.edge_p1.mean()
        ) if top.edge_p1.mean() != 0 else np.nan,
        top_decile_beats_cost_bar_p2=bool(
            top.edge_p2.mean() * 100 > TENNIS_ROUND_TRIP_C
        ),
    )
    t = stats.ttest_ind(top.edge_p2, both.edge_p2, equal_var=False)
    out["top_vs_rest_p2_p"] = float(t.pvalue)
    out["verdict"] = (
        "PERSISTENT" if (sp.pvalue < 0.05 and sp.statistic > 0.2) else "NOT PERSISTENT"
    )
    both.to_csv(REPORTS / "copytrade_persistence_v2.csv")
    return out


def test2_skill_vs_luck(pos: pd.DataFrame) -> dict:
    s = pos.groupby("wallet").apply(wallet_edge, include_groups=False)
    s = s[s.n_markets >= MIN_MARKETS].copy()
    if len(s) < 8:
        return {"verdict": "INSUFFICIENT DATA", "n_wallets": int(len(s))}

    grand = float((pos.won - pos.entry).mean())
    total_var = float(s.edge.var(ddof=1))
    mean_samp = float((s.edge_se**2).mean())
    tau2 = max(total_var - mean_samp, 0.0)

    s["shrink_w"] = tau2 / (tau2 + s.edge_se**2)
    s["edge_shrunk"] = grand + s.shrink_w * (s.edge - grand)
    s["t_stat"] = s.edge / s.edge_se
    s["p_value"] = 2 * (1 - stats.norm.cdf(np.abs(s.t_stat)))
    s["q_value"] = _bh(s.p_value.values)
    s["significant_fdr"] = s.q_value < 0.05
    s.sort_values("edge_shrunk", ascending=False).to_csv(
        REPORTS / "copytrade_skill_v2.csv"
    )

    # markets needed to distinguish a true +5pp edge from zero, 80% power
    sd = float((pos.won - pos.entry).std(ddof=1))
    n_needed = int(np.ceil(((1.96 + 0.84) * sd / 0.05) ** 2))
    # and to clear the actual cost bar rather than merely zero
    n_needed_cost = int(np.ceil(((1.96 + 0.84) * sd / (TENNIS_ROUND_TRIP_C / 100)) ** 2))

    return {
        "n_wallets": int(len(s)),
        "grand_mean_edge_pp": grand * 100,
        "observed_edge_variance": total_var,
        "mean_sampling_variance": mean_samp,
        "true_skill_variance_tau2": tau2,
        "skill_variance_share": float(tau2 / total_var) if total_var > 0 else 0.0,
        "median_shrink_weight": float(s.shrink_w.median()),
        "best_raw_edge_pp": float(s.edge.max() * 100),
        "best_shrunk_edge_pp": float(s.edge_shrunk.max() * 100),
        "n_significant_raw_p05": int((s.p_value < 0.05).sum()),
        "n_significant_after_fdr": int(s.significant_fdr.sum()),
        "expected_false_positives_at_p05": float(0.05 * len(s)),
        "median_n_markets": float(s.n_markets.median()),
        "per_market_pnl_sd": sd,
        "markets_needed_to_detect_5pp_edge": n_needed,
        "markets_needed_to_clear_cost_bar": n_needed_cost,
        "median_wallet_has_enough_markets": bool(s.n_markets.median() >= n_needed),
        "n_wallets_with_enough_markets": int((s.n_markets >= n_needed).sum()),
        "verdict": (
            "SKILL PRESENT"
            if (tau2 > 0 and int(s.significant_fdr.sum()) > 0)
            else "INDISTINGUISHABLE FROM LUCK"
        ),
    }


def main() -> None:
    pos = load_positions()
    print(f"positions (wallet x market): {len(pos):,}")
    print(f"  from {pos.n_fills.sum():,} fills, {pos.wallet.nunique():,} wallets, "
          f"{pos.condition_id.nunique():,} markets")
    print(f"  span {pd.Timestamp(pos.ts.min(), unit='s')} -> "
          f"{pd.Timestamp(pos.ts.max(), unit='s')}")
    print(f"  population edge: {(pos.won - pos.entry).mean()*100:+.3f} pp")

    res = {
        "n_positions": int(len(pos)),
        "n_fills": int(pos.n_fills.sum()),
        "n_wallets": int(pos.wallet.nunique()),
        "n_markets": int(pos.condition_id.nunique()),
        "population_edge_pp": float((pos.won - pos.entry).mean() * 100),
        "unit_of_observation": "one row per (wallet, market); fills collapsed to VWAP",
    }

    print("\n" + "=" * 74)
    print("TEST 1 - PERSISTENCE (market-level)")
    print("=" * 74)
    res["test1"] = t1 = test1_persistence(pos)
    for k, v in t1.items():
        print(f"  {k:36s} {v}")

    print("\n" + "=" * 74)
    print("TEST 2 - SKILL VS LUCK (market-level)")
    print("=" * 74)
    res["test2"] = t2 = test2_skill_vs_luck(pos)
    for k, v in t2.items():
        print(f"  {k:36s} {v}")

    (REPORTS / "copytrade_tests_v2.json").write_text(
        json.dumps(res, indent=1, default=str)
    )
    print(f"\nwrote {REPORTS/'copytrade_tests_v2.json'}")


if __name__ == "__main__":
    main()
