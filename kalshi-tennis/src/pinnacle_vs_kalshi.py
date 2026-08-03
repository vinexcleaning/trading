"""Pinnacle closing line vs Kalshi pre-match price, on the same matches.

This is a market-vs-market test. No model is involved and nothing is fitted, so
there is no overfitting risk and no train/test split is needed -- but every
sample size is reported, results are broken out by period, and every estimate
carries a bootstrap CI.

The question: does Kalshi price tennis the way the sharpest public book does?
If it does, there is no pricing edge to find here and the sensible move is to
stop. That is a valid and expected outcome.

Cost model (Kalshi, hold to settlement):
    crossing the spread  = spread / 2   (you lift the ask, not the mid)
    taker fee            = ceil(0.07 * P * (1-P)) per contract, on entry
    settlement           = free
A disagreement only matters if it exceeds what it costs to act on it.
"""
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
REPORT = ROOT / "reports"

MAX_SPREAD = 0.10          # wider than this is not a tradeable quote

# `occurrence_datetime` is at or after the match END for a large minority of
# markets, so a quote anchored there is post-settlement. anchor_leak_test.py
# shows the leak is gone by -6h: extreme quotes fall from 4.1% (100% correct)
# to 0.1%, and correlation with two independent books rises to 0.978.
ANCHOR = "h6"


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "common"))
from kalshi_fees import fee_dollars_from_price_vec  # noqa: E402


def fee(p):
    """Kalshi taker fee in dollars per contract, p in dollars.

    Exact Decimal — see common/kalshi_fees.py. The previous
    `np.ceil(0.07*p*(1-p)*100)/100` overcharged a cent wherever the float
    product landed just above an exact cent.
    """
    return fee_dollars_from_price_vec(p, 1)


def devig(o1, o2):
    i1, i2 = 1.0 / o1, 1.0 / o2
    s = i1 + i2
    return i1 / s


def td_key(name):
    """'Van Assche L.' -> ('van assche', 'l')"""
    toks = td.norm_name(name).split()
    if len(toks) < 2:
        return None
    return " ".join(toks[:-1]), toks[-1][0]


def full_keys(name):
    """'Luca Van Assche' -> {('van assche','l'), ('assche','l')}"""
    toks = td.norm_name(name).split()
    if len(toks) < 2:
        return set()
    ini = toks[0][0]
    return {(" ".join(toks[1:]), ini), (toks[-1], ini)}


def bootstrap_diff(y, pa, pb, n_boot=4000, seed=5):
    """Bootstrap CI on Brier(a) - Brier(b)."""
    rng = np.random.default_rng(seed)
    n = len(y)
    d = [np.mean((pa[s] - y[s]) ** 2) - np.mean((pb[s] - y[s]) ** 2)
         for s in (rng.integers(0, n, n) for _ in range(n_boot))]
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def build():
    # ---- Kalshi main-tour events with a pre-match quote -------------------
    ev = td.load_kalshi_events()
    ev = ev[ev["tier"] == "main"]
    prices = pd.read_parquet(ROOT / "data" / "kalshi" /
                             "kalshi_prices_multianchor.parquet")
    prices = prices.rename(columns={f"mid_{ANCHOR}": "pre_mid",
                                    f"bid_{ANCHOR}": "pre_bid",
                                    f"ask_{ANCHOR}": "pre_ask",
                                    f"lag_{ANCHOR}": "hours_before"})
    prices["volume_pre"] = np.nan
    ev = ev.merge(prices, on="event_ticker", how="inner")
    ev = ev[ev["pre_mid"].notna() & ev["result_a"].isin(["yes", "no"])].copy()
    ev["spread"] = ev["pre_ask"] - ev["pre_bid"]
    ev["day"] = pd.to_datetime(ev["date"], utc=True, errors="coerce") \
        .dt.tz_localize(None).dt.normalize()
    ev = ev[ev["day"].notna()]
    print(f"Kalshi main-tour events with settled result + pre-match quote: {len(ev):,}")

    # ---- tennis-data.co.uk main tour with Pinnacle prices -----------------
    b = pd.read_parquet(ROOT / "data" / "tennisdata" / "tennisdata_all.parquet")
    b["Date"] = pd.to_datetime(b["Date"])
    b = b[b["Comment"].astype(str).str.contains("Completed", na=False)]
    b = b[b["Date"] >= ev["day"].min() - pd.Timedelta(days=2)]
    print(f"tennis-data completed main-tour matches in window: {len(b):,}")
    b["kw"] = b["Winner"].astype(str).map(td_key)
    b["kl"] = b["Loser"].astype(str).map(td_key)
    b = b[b["kw"].notna() & b["kl"].notna()].copy()
    b["day"] = b["Date"].dt.normalize()

    idx = {}
    for r in b.itertuples(index=False):
        for dd in (r.day, r.day - pd.Timedelta(days=1),
                   r.day + pd.Timedelta(days=1)):
            idx.setdefault((dd, frozenset([r.kw, r.kl])), r)

    # ---- join --------------------------------------------------------------
    recs = []
    for r in ev.itertuples(index=False):
        ka, kb = full_keys(r.player_a), full_keys(r.player_b)
        hit = None
        for k1 in ka:
            for k2 in kb:
                hit = idx.get((r.day, frozenset([k1, k2])))
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is None:
            continue
        psw, psl = getattr(hit, "BFEW", np.nan), getattr(hit, "BFEL", np.nan)
        avw, avl = getattr(hit, "AvgW", np.nan), getattr(hit, "AvgL", np.nan)
        pinw, pinl = getattr(hit, "PSW", np.nan), getattr(hit, "PSL", np.nan)
        a_won = hit.kw in ka                       # did Kalshi's player_a win?
        p_k = float(r.pre_mid)                     # P(player_a) per Kalshi
        rec = {
            "date": r.day, "tour": r.tour,
            "player_a": r.player_a, "player_b": r.player_b,
            "y": int(a_won), "p_kalshi": p_k,
            "bid": r.pre_bid, "ask": r.pre_ask, "spread": r.spread,
            "hours_before": r.hours_before, "volume": r.volume_pre,
            "surface": getattr(hit, "Surface", None),
            "series": getattr(hit, "Series", None),
            "round": getattr(hit, "Round", None),
        }
        if psw and psl and psw > 1 and psl > 1:
            pw = devig(float(psw), float(psl))
            rec["p_pinn"] = pw if a_won else 1.0 - pw
        else:
            rec["p_pinn"] = np.nan
        if avw and avl and avw > 1 and avl > 1:
            pw = devig(float(avw), float(avl))
            rec["p_avg"] = pw if a_won else 1.0 - pw
        else:
            rec["p_avg"] = np.nan
        if pinw and pinl and pinw > 1 and pinl > 1:
            pw = devig(float(pinw), float(pinl))
            rec["p_pinnacle_raw"] = pw if a_won else 1.0 - pw
        else:
            rec["p_pinnacle_raw"] = np.nan
        recs.append(rec)

    d = pd.DataFrame(recs)
    print(f"joined Kalshi<->tennis-data: {len(d):,}")
    return d


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    d = build()
    d.to_parquet(CACHE / "pinnacle_vs_kalshi.parquet", index=False)

    emit("=" * 92)
    emit("SHARP BOOK vs KALSHI PRE-MATCH PRICE")
    emit("=" * 92)
    emit(f"Kalshi quote anchored {ANCHOR[1:]}h before `occurrence_datetime`.")
    emit("That field is at or after the match END for many markets; anchoring")
    emit("on it directly leaks the result (4.1% of quotes sat outside 2c-98c")
    emit("and were 100% correct). At -6h that signature is gone.")
    emit()
    emit("NOTE: tennis-data.co.uk carries Pinnacle for only 5.1% of 2026 rows --")
    emit("they stopped publishing it. The sharp benchmark used here is the")
    emit("BETFAIR EXCHANGE closing price (93.6% coverage in 2026), which for")
    emit("tennis is at least as sharp as Pinnacle. Book average is the control.")
    emit()
    emit("No model, nothing fitted, no parameters tuned -> no holdout required.")
    emit("Every figure below reports its own n. CIs are 4,000-sample bootstraps.")
    emit()
    emit(f"joined matches                     {len(d):,}")
    emit(f"  with a Betfair price             {d['p_pinn'].notna().sum():,}")
    emit(f"  with an average-book price       {d['p_avg'].notna().sum():,}")
    emit(f"  with a real Pinnacle price       {d['p_pinnacle_raw'].notna().sum():,}"
         f"   (why Pinnacle is not the benchmark)")
    emit(f"  with a tradeable Kalshi quote    "
         f"{(d['spread'] <= MAX_SPREAD).sum():,} (spread <= {MAX_SPREAD:.2f})")

    core = d[d["p_pinn"].notna() & (d["spread"] <= MAX_SPREAD)].copy()
    emit(f"  BOTH (the analysis set)          {len(core):,}")
    emit()
    if len(core) < 50:
        emit("Too few joined matches to say anything. Stopping.")
        (REPORT / "pinnacle_vs_kalshi.txt").write_text("\n".join(lines),
                                                       encoding="utf-8")
        return

    core["diff"] = core["p_kalshi"] - core["p_pinn"]
    core["abs_diff"] = core["diff"].abs()
    core["cost"] = core["spread"] / 2.0 + fee(core["p_kalshi"].to_numpy())

    y = core["y"].to_numpy()
    pk = np.clip(core["p_kalshi"].to_numpy(), 1e-6, 1 - 1e-6)
    pp = np.clip(core["p_pinn"].to_numpy(), 1e-6, 1 - 1e-6)

    emit("-" * 92)
    emit("1. AGREEMENT")
    emit("-" * 92)
    r, pval = stats.pearsonr(pk, pp)
    rs, _ = stats.spearmanr(pk, pp)
    emit(f"  n                                {len(core):,}")
    emit(f"  Pearson r                        {r:.4f}   (p={pval:.2e})")
    emit(f"  Spearman rho                     {rs:.4f}")
    emit(f"  mean absolute difference         {core['abs_diff'].mean():.4f}")
    emit(f"  median absolute difference       {core['abs_diff'].median():.4f}")
    emit(f"  90th pct absolute difference     {core['abs_diff'].quantile(0.9):.4f}")
    emit(f"  mean signed diff (Kalshi-Pinn)   {core['diff'].mean():+.4f}")
    emit(f"  mean round-trip-ish cost         {core['cost'].mean():.4f}"
         f"   (half-spread + entry fee)")
    emit()

    emit("-" * 92)
    emit("2. ACCURACY vs OUTCOMES")
    emit("-" * 92)
    bk = float(np.mean((pk - y) ** 2))
    bp = float(np.mean((pp - y) ** 2))
    lo, hi = bootstrap_diff(y, pk, pp)
    emit(f"  n                                {len(core):,}")
    emit(f"  Kalshi   Brier                   {bk:.5f}")
    emit(f"  Pinnacle Brier                   {bp:.5f}")
    emit(f"  Kalshi - Pinnacle                {bk - bp:+.5f}  95% CI [{lo:+.5f}, {hi:+.5f}]")
    verdict = ("Pinnacle is sharper" if lo > 0 else
               "Kalshi is sharper" if hi < 0 else
               "indistinguishable")
    emit(f"  VERDICT                          {verdict}")
    emit()

    emit("-" * 92)
    emit("3. WHERE THEY DISAGREE BY MORE THAN IT COSTS TO ACT")
    emit("-" * 92)
    dis = core[core["abs_diff"] > core["cost"]].copy()
    emit(f"  disagreements beyond cost        {len(dis):,} of {len(core):,} "
         f"({len(dis) / len(core) * 100:.1f}%)")
    if len(dis) >= 30:
        yy = dis["y"].to_numpy()
        a = np.clip(dis["p_kalshi"].to_numpy(), 1e-6, 1 - 1e-6)
        c = np.clip(dis["p_pinn"].to_numpy(), 1e-6, 1 - 1e-6)
        bka, bpa = np.mean((a - yy) ** 2), np.mean((c - yy) ** 2)
        l2, h2 = bootstrap_diff(yy, a, c)
        emit(f"  mean |disagreement|              {dis['abs_diff'].mean():.4f}")
        emit(f"  Kalshi   Brier (disagreements)   {bka:.5f}")
        emit(f"  Pinnacle Brier (disagreements)   {bpa:.5f}")
        emit(f"  Kalshi - Pinnacle                {bka - bpa:+.5f}  "
             f"95% CI [{l2:+.5f}, {h2:+.5f}]")
        closer = np.mean(np.abs(a - yy) < np.abs(c - yy))
        se = np.sqrt(closer * (1 - closer) / len(dis))
        emit(f"  Kalshi closer to the truth       {closer * 100:.1f}% "
             f"95% CI [{(closer - 1.96 * se) * 100:.1f}%, "
             f"{(closer + 1.96 * se) * 100:.1f}%]  (50% = coin flip)")
        emit(f"  WHO WAS RIGHT                    "
             f"{'Pinnacle' if l2 > 0 else 'Kalshi' if h2 < 0 else 'neither -- noise'}")
    else:
        emit("  too few to test")
    emit()

    emit("-" * 92)
    emit("4. SEGMENTS  (Kalshi Brier - Pinnacle Brier; positive = Pinnacle better)")
    emit("-" * 92)
    core["fav_band"] = pd.cut(np.maximum(pk, 1 - pk),
                              [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                              labels=["50-60c", "60-70c", "70-80c",
                                      "80-90c", "90c+"])
    core["tts"] = pd.cut(core["hours_before"], [-0.01, 0.25, 1, 6, 24, 1e6],
                         labels=["<15min", "15-60min", "1-6h", "6-24h", ">24h"])
    core["period"] = core["date"].dt.to_period("Q").astype(str)

    emit(f"{'axis':<12}{'segment':<16}{'n':>7}{'Kalshi':>10}{'Pinnacle':>10}"
         f"{'diff':>10}  {'95% CI':<22}")
    for axis in ("tour", "surface", "fav_band", "tts", "period"):
        for val, g in core.groupby(axis, observed=True):
            if len(g) < 40:
                continue
            yy = g["y"].to_numpy()
            a = np.clip(g["p_kalshi"].to_numpy(), 1e-6, 1 - 1e-6)
            c = np.clip(g["p_pinn"].to_numpy(), 1e-6, 1 - 1e-6)
            ba, bb = np.mean((a - yy) ** 2), np.mean((c - yy) ** 2)
            l3, h3 = bootstrap_diff(yy, a, c, n_boot=2000)
            emit(f"{axis:<12}{str(val):<16}{len(g):>7,}{ba:>10.5f}{bb:>10.5f}"
                 f"{ba - bb:>+10.5f}  [{l3:+.4f},{h3:+.4f}]")
    emit()

    emit("-" * 92)
    emit("5. SENSITIVITY TO THE LIQUIDITY FILTER")
    emit("-" * 92)
    emit(f"{'max spread':<12}{'n':>7}{'Kalshi':>10}{'Pinnacle':>10}{'diff':>10}")
    for s in (0.02, 0.05, 0.10, 1.01):
        g = d[d["p_pinn"].notna() & (d["spread"] <= s)]
        if len(g) < 40:
            continue
        yy = g["y"].to_numpy()
        a = np.clip(g["p_kalshi"].to_numpy(), 1e-6, 1 - 1e-6)
        c = np.clip(g["p_pinn"].to_numpy(), 1e-6, 1 - 1e-6)
        emit(f"{s:<12.2f}{len(g):>7,}{np.mean((a - yy) ** 2):>10.5f}"
             f"{np.mean((c - yy) ** 2):>10.5f}"
             f"{np.mean((a - yy) ** 2) - np.mean((c - yy) ** 2):>+10.5f}")

    (REPORT / "pinnacle_vs_kalshi.txt").write_text("\n".join(lines),
                                                   encoding="utf-8")
    emit()
    emit(f"report -> {REPORT / 'pinnacle_vs_kalshi.txt'}")


if __name__ == "__main__":
    main()
