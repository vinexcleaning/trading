"""Phase 6: the four tests, applied to the live tennis copy-trading source.

Data: /c/Users/vinig/tennis copy trade/data/tape_scan.db -> tape_bets
      (wallet, condition_id, ts, price, size, won), 1.77M rows of Polymarket
      wallet activity with realised outcomes.

Edge definition for a prediction market: buying at price p and winning w% of the
time earns w - p per unit staked before fees. So `edge = mean(won) - mean(price)`,
in probability points. This is the correct measure -- raw win rate is meaningless
without the price paid.

Test 1 PERSISTENCE     rank on period 1, evaluate on a strictly later period 2
Test 2 SKILL VS LUCK   Bayesian shrinkage of edge against sample size
Test 3 EDGE DECAY      price path after the whale print (needs market_prices)
Test 4 ADVERSE SELECT  do our fills cluster just before adverse moves
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NB = ROOT / "notebooks"
REPORTS.mkdir(exist_ok=True)
NB.mkdir(exist_ok=True)

TAPE_DB = Path(r"C:\Users\vinig\tennis copy trade\data\tape_scan.db")
BEST_DB = Path(r"C:\Users\vinig\tennis copy trade\data\best.db")

MIN_BETS_PER_PERIOD = 20


def _bh(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg q-values."""
    p = np.asarray(p, float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    q = np.minimum.accumulate((p[order] * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(q, 0, 1)
    return out
KALSHI_ROUND_TRIP_C = 3.5  # at-the-money; tennis mid-book is ~2.4c per the user


def load_tape() -> pd.DataFrame:
    con = sqlite3.connect(f"file:{TAPE_DB}?mode=ro", uri=True)
    df = pd.read_sql_query(
        "SELECT wallet, condition_id, ts, price, size, won FROM tape_bets "
        "WHERE won IS NOT NULL AND price IS NOT NULL",
        con,
    )
    con.close()
    df["price"] = pd.to_numeric(df.price, errors="coerce")
    df["won"] = pd.to_numeric(df.won, errors="coerce")
    df["size"] = pd.to_numeric(df["size"], errors="coerce").fillna(0)
    df["ts"] = pd.to_numeric(df.ts, errors="coerce")
    df = df.dropna(subset=["price", "won", "ts"])
    df = df[(df.price > 0.005) & (df.price < 0.995)]
    return df.sort_values("ts").reset_index(drop=True)


def wallet_stats(g: pd.DataFrame) -> pd.Series:
    n = len(g)
    edge = g.won.mean() - g.price.mean()
    # per-bet PnL in probability points, for a variance estimate
    pnl = g.won - g.price
    return pd.Series(
        {
            "n": n,
            "avg_price": g.price.mean(),
            "win_rate": g.won.mean(),
            "edge": edge,
            "edge_se": pnl.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan,
            "staked": g["size"].sum(),
        }
    )


def test1_persistence(df: pd.DataFrame) -> dict:
    """Rank on period 1, evaluate on period 2. Both halves by time, never shuffled."""
    cut = df.ts.quantile(0.5)
    p1 = df[df.ts < cut]
    p2 = df[df.ts >= cut]
    s1 = p1.groupby("wallet").apply(wallet_stats, include_groups=False)
    s2 = p2.groupby("wallet").apply(wallet_stats, include_groups=False)
    both = s1.join(s2, lsuffix="_p1", rsuffix="_p2", how="inner")
    both = both[(both.n_p1 >= MIN_BETS_PER_PERIOD) & (both.n_p2 >= MIN_BETS_PER_PERIOD)]

    out: dict = {
        "period_split_ts": float(cut),
        "n_wallets_both_periods": int(len(both)),
        "min_bets_per_period": MIN_BETS_PER_PERIOD,
    }
    if len(both) < 8:
        out["verdict"] = "INSUFFICIENT DATA"
        return out

    sp = stats.spearmanr(both.edge_p1, both.edge_p2)
    pe = stats.pearsonr(both.edge_p1, both.edge_p2)
    out.update(
        spearman_rho=float(sp.statistic), spearman_p=float(sp.pvalue),
        pearson_r=float(pe.statistic), pearson_p=float(pe.pvalue),
    )

    # the decision-relevant framing: pick the top decile on p1, what do they do on p2?
    k = max(1, len(both) // 10)
    top = both.nlargest(k, "edge_p1")
    bot = both.nsmallest(k, "edge_p1")
    out.update(
        top_decile_n=int(k),
        top_decile_edge_p1=float(top.edge_p1.mean()),
        top_decile_edge_p2=float(top.edge_p2.mean()),
        bottom_decile_edge_p1=float(bot.edge_p1.mean()),
        bottom_decile_edge_p2=float(bot.edge_p2.mean()),
        all_wallets_edge_p2=float(both.edge_p2.mean()),
    )
    # is the top decile's period-2 edge distinguishable from everyone else's?
    t = stats.ttest_ind(top.edge_p2, both.edge_p2, equal_var=False)
    out["top_vs_all_p2_tstat"] = float(t.statistic)
    out["top_vs_all_p2_p"] = float(t.pvalue)
    out["top_decile_beats_cost_bar_p2"] = bool(
        top.edge_p2.mean() * 100 > KALSHI_ROUND_TRIP_C
    )
    out["verdict"] = (
        "PERSISTENT" if (sp.pvalue < 0.05 and sp.statistic > 0.2) else "NOT PERSISTENT"
    )
    both.to_csv(REPORTS / "copytrade_persistence.csv")
    return out


def test2_skill_vs_luck(df: pd.DataFrame) -> dict:
    """Empirical-Bayes shrinkage of each wallet's edge toward the population mean.

    A wallet with a large edge over 20 bets is mostly noise. Shrinkage weights the
    observed edge by its precision relative to the spread of true skill.
    """
    s = df.groupby("wallet").apply(wallet_stats, include_groups=False)
    s = s[s.n >= MIN_BETS_PER_PERIOD].copy()
    if len(s) < 8:
        return {"verdict": "INSUFFICIENT DATA", "n_wallets": int(len(s))}

    grand = float((df.won - df.price).mean())
    total_var = float(s.edge.var(ddof=1))
    mean_sampling_var = float((s.edge_se**2).mean())
    # observed spread = true skill spread + sampling noise
    tau2 = max(total_var - mean_sampling_var, 0.0)

    s["shrink_weight"] = tau2 / (tau2 + s.edge_se**2)
    s["edge_shrunk"] = grand + s.shrink_weight * (s.edge - grand)
    s["t_stat"] = s.edge / s.edge_se
    s["p_value"] = 2 * (1 - stats.norm.cdf(np.abs(s.t_stat)))

    q = _bh(s.p_value.values)
    s["q_value"] = q
    s["significant_fdr"] = q < 0.05
    s.sort_values("edge_shrunk", ascending=False).to_csv(
        REPORTS / "copytrade_skill.csv"
    )

    # how many bets to distinguish a genuinely 55%-at-50c wallet from a 50% one?
    # per-bet PnL sd for a binary at price p is sqrt(p(1-p)); at p=0.5 that is 0.5
    sd = 0.5
    delta = 0.05
    n_needed = int(np.ceil(((1.96 + 0.84) * sd / delta) ** 2))  # 80% power, alpha 5%

    return {
        "n_wallets": int(len(s)),
        "grand_mean_edge": grand,
        "observed_edge_variance": total_var,
        "mean_sampling_variance": mean_sampling_var,
        "true_skill_variance_tau2": tau2,
        "skill_variance_share": float(tau2 / total_var) if total_var > 0 else 0.0,
        "median_shrink_weight": float(s.shrink_weight.median()),
        "n_significant_raw_p05": int((s.p_value < 0.05).sum()),
        "n_significant_after_fdr": int(s.significant_fdr.sum()),
        "best_raw_edge": float(s.edge.max()),
        "best_shrunk_edge": float(s.edge_shrunk.max()),
        "median_n_bets": float(s.n.median()),
        "n_bets_to_detect_55_vs_50_at_80pct_power": n_needed,
        "median_wallet_has_enough_bets": bool(s.n.median() >= n_needed),
        "verdict": (
            "SKILL PRESENT" if tau2 > 0 and int(s.significant_fdr.sum()) > 0
            else "INDISTINGUISHABLE FROM LUCK"
        ),
    }


def test3_edge_decay() -> dict:
    """Does price move away before a follower could fill?

    The existing project already computed this into `trade_copyability`, which
    stores price_before, price_after_delay and the deterioration per delay. Reuse
    it rather than recomputing from raw prices.
    """
    if not BEST_DB.exists():
        return {"verdict": "NO DATA"}
    con = sqlite3.connect(f"file:{BEST_DB}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query(
            "SELECT delay_seconds, wallet_entry_price, price_before, "
            "price_after_delay, estimated_fill_price, price_deterioration, "
            "price_deterioration_pct, slippage, spread_at_entry, follower_pnl "
            "FROM trade_copyability",
            con,
        )
    except Exception as e:  # noqa: BLE001
        con.close()
        return {"verdict": f"QUERY FAILED: {e}"}
    con.close()
    if df.empty:
        return {"verdict": "NO ROWS"}

    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    rows = []
    for d, g in df.groupby("delay_seconds"):
        det = g.price_deterioration.dropna()
        rows.append(
            {
                "delay_seconds": float(d),
                "n": int(len(g)),
                "median_deterioration_c": float(det.median() * 100)
                if len(det) else np.nan,
                "mean_deterioration_c": float(det.mean() * 100) if len(det) else np.nan,
                "pct_moved_against": float((det > 0).mean() * 100) if len(det) else np.nan,
                "median_spread_c": float(g.spread_at_entry.dropna().median() * 100)
                if g.spread_at_entry.notna().any() else np.nan,
                "median_follower_pnl": float(g.follower_pnl.dropna().median())
                if g.follower_pnl.notna().any() else np.nan,
            }
        )
    dec = pd.DataFrame(rows).sort_values("delay_seconds")
    dec.to_csv(REPORTS / "copytrade_edge_decay.csv", index=False)
    return {"n_rows": int(len(df)), "by_delay": dec.to_dict("records")}


def test4_adverse_selection(df: pd.DataFrame) -> dict:
    """Are followed entries systematically on the wrong side?

    Proxy available from the tape: compare the edge on bets placed at prices that
    later proved wrong vs right, split by whether the wallet was buying into a
    crowded side. Without an order book we test the weaker but still meaningful
    version: does edge deteriorate as the followed size grows (crowding)?
    """
    s = df.groupby("wallet").apply(wallet_stats, include_groups=False)
    s = s[s.n >= MIN_BETS_PER_PERIOD]
    if len(s) < 8:
        return {"verdict": "INSUFFICIENT DATA"}
    q = pd.qcut(df["size"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    g = df.assign(size_q=q).groupby("size_q", observed=True).apply(
        lambda x: pd.Series(
            {"n": len(x), "edge": x.won.mean() - x.price.mean(),
             "avg_price": x.price.mean(), "avg_size": x["size"].mean()}
        ),
        include_groups=False,
    )
    g.to_csv(REPORTS / "copytrade_adverse_selection.csv")
    big, small = g.loc[5, "edge"], g.loc[1, "edge"]
    return {
        "edge_by_size_quintile": g.edge.round(5).to_dict(),
        "largest_quintile_edge": float(big),
        "smallest_quintile_edge": float(small),
        "large_trades_worse": bool(big < small),
        "verdict": (
            "ADVERSE SELECTION SUSPECTED" if big < small - 0.01
            else "NO CLEAR ADVERSE SELECTION"
        ),
    }


def main() -> None:
    if not TAPE_DB.exists():
        print(f"tape db not found at {TAPE_DB}")
        return
    df = load_tape()
    print(f"tape_bets loaded: {len(df):,} bets, {df.wallet.nunique():,} wallets")
    print(f"time span: {pd.Timestamp(df.ts.min(), unit='s')} -> "
          f"{pd.Timestamp(df.ts.max(), unit='s')}")
    print(f"population edge: {(df.won - df.price).mean()*100:+.3f}pp "
          f"(win rate {df.won.mean():.4f} vs avg price {df.price.mean():.4f})")

    res: dict = {
        "n_bets": int(len(df)),
        "n_wallets": int(df.wallet.nunique()),
        "population_edge_pp": float((df.won - df.price).mean() * 100),
    }

    print("\n" + "=" * 74)
    print("TEST 1 - PERSISTENCE")
    print("=" * 74)
    res["test1_persistence"] = t1 = test1_persistence(df)
    for k, v in t1.items():
        print(f"  {k:38s} {v}")

    print("\n" + "=" * 74)
    print("TEST 2 - SKILL VS LUCK")
    print("=" * 74)
    res["test2_skill_vs_luck"] = t2 = test2_skill_vs_luck(df)
    for k, v in t2.items():
        print(f"  {k:38s} {v}")

    print("\n" + "=" * 74)
    print("TEST 3 - EDGE DECAY AND CAPACITY")
    print("=" * 74)
    res["test3_edge_decay"] = t3 = test3_edge_decay()
    if "by_delay" in t3:
        print(pd.DataFrame(t3["by_delay"]).to_string(index=False))
    else:
        print(f"  {t3}")

    print("\n" + "=" * 74)
    print("TEST 4 - ADVERSE SELECTION")
    print("=" * 74)
    res["test4_adverse_selection"] = t4 = test4_adverse_selection(df)
    for k, v in t4.items():
        print(f"  {k:38s} {v}")

    (REPORTS / "copytrade_tests.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {REPORTS/'copytrade_tests.json'}")


if __name__ == "__main__":
    main()
