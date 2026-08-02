"""Stage 4 -- win-probability model, and the only test that matters.

Logistic regression first, deliberately: a baseline that can be read and
debugged beats a black box that can't be trusted.

Rows are built with an OUTCOME-INDEPENDENT ordering (players sorted by name,
never by who won), so the target is ~50/50 and the model cannot learn "the
first player usually wins". Features are p1-minus-p2 differences.

Then the model is scored against the market on the same held-out matches:
  * Kalshi pre-match mid -- the actual thing we would be betting into
  * Pinnacle / Bet365 closing odds, de-vigged -- a much larger sample and the
    sharpest public line in tennis. Losing to Pinnacle means losing to Kalshi.

Splits are chronological. Train < 2023, validate 2023-24, test 2025 onward.
The test split is touched once.
"""
import pathlib
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
REPORT = ROOT / "reports"

TRAIN_END = pd.Timestamp("2023-01-01")
VAL_END = pd.Timestamp("2025-01-01")

RATES = ["serve_pts_won", "first_in", "first_won", "ace", "df", "hold",
         "rtn_pts_won", "break"]


def build_frame(f):
    """Symmetric p1/p2 rows with an outcome-independent ordering."""
    w = f["winner_name"].astype(str).to_numpy()
    l = f["loser_name"].astype(str).to_numpy()
    swap = w > l                     # p1 is alphabetically first
    y = (~swap).astype(int)          # p1 won?

    out = pd.DataFrame({
        "date": f["date"].to_numpy(), "surface": f["surface"].to_numpy(),
        "tier": f["tier"].to_numpy(), "tour": f["tour"].to_numpy(),
        "round": f["round"].to_numpy(), "best_of": f["best_of"].to_numpy(),
        "p1": np.where(swap, l, w), "p2": np.where(swap, w, l),
        "y": y, "has_serve": f["has_serve"].to_numpy(),
    })

    def pair(col):
        a = f[f"w_{col}"].to_numpy(dtype=float)
        b = f[f"l_{col}"].to_numpy(dtype=float)
        return np.where(swap, b, a), np.where(swap, a, b)

    feats = {}
    for col in ["elo", "elo_surf"]:
        p1, p2 = pair(col)
        feats[f"d_{col}"] = p1 - p2
        n1, n2 = pair(f"{col}_n")
        feats[f"min_{col}_n"] = np.minimum(n1, n2)

    for bucket in ("all", "surf"):
        for r in RATES:
            p1, p2 = pair(f"{bucket}_{r}")
            feats[f"d_{bucket}_{r}"] = p1 - p2
            n1, n2 = pair(f"{bucket}_{r}_n")
            feats[f"min_{bucket}_{r}_n"] = np.log1p(np.minimum(n1, n2))

    for col in ["matches_7d", "matches_14d", "minutes_14d", "days_since",
                "back_to_back", "qualifier", "age", "ht"]:
        p1, p2 = pair(col)
        feats[f"d_{col}"] = p1 - p2

    r1, r2 = pair("rank")
    feats["d_log_rank"] = np.log1p(np.nan_to_num(r2, nan=500.0)) - \
        np.log1p(np.nan_to_num(r1, nan=500.0))

    hw = f["h2h_w_wins"].to_numpy(dtype=float)
    hl = f["h2h_l_wins"].to_numpy(dtype=float)
    h1 = np.where(swap, hl, hw)
    h2 = np.where(swap, hw, hl)
    feats["d_h2h"] = h1 - h2
    feats["h2h_played"] = f["h2h_played"].to_numpy(dtype=float)
    hws = f["h2h_w_wins_surf"].to_numpy(dtype=float)
    hls = f["h2h_l_wins_surf"].to_numpy(dtype=float)
    feats["d_h2h_surf"] = np.where(swap, hls, hws) - np.where(swap, hws, hls)
    feats["h2h_days_since"] = np.nan_to_num(
        f["h2h_days_since"].to_numpy(dtype=float), nan=9999.0)

    lh1 = (f["w_hand"].to_numpy() == "L").astype(float)
    lh2 = (f["l_hand"].to_numpy() == "L").astype(float)
    feats["d_lefty"] = np.where(swap, lh2, lh1) - np.where(swap, lh1, lh2)

    for k, v in feats.items():
        out[k] = v
    return out, [k for k in feats]


def calibration_table(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        if m.sum() < 10:
            continue
        rows.append((f"{edges[b]:.1f}-{edges[b + 1]:.1f}", int(m.sum()),
                     float(p[m].mean()), float(y[m].mean()),
                     float(y[m].mean() - p[m].mean())))
    return pd.DataFrame(rows, columns=["bucket", "n", "predicted",
                                       "actual", "gap"])


def devig(o1, o2):
    """Two-way odds -> normalised probabilities (proportional de-vigging)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        i1, i2 = 1.0 / o1, 1.0 / o2
    s = i1 + i2
    return i1 / s, i2 / s


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    f = pd.read_parquet(CACHE / "stage2_features.parquet")
    f["date"] = pd.to_datetime(f["date"])
    print(f"loaded {len(f):,} matches")

    df, featcols = build_frame(f)

    # Restrict to matches where serve features are meaningful at all.
    df = df[df["date"] >= "1991-01-01"]
    X = df[featcols].to_numpy(dtype=float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = df["y"].to_numpy()

    train = (df["date"] < TRAIN_END).to_numpy()
    val = ((df["date"] >= TRAIN_END) & (df["date"] < VAL_END)).to_numpy()
    test = (df["date"] >= VAL_END).to_numpy()

    emit("=" * 84)
    emit("STAGE 4 -- MODEL vs MARKET")
    emit("=" * 84)
    emit(f"rows: {len(df):,}   features: {len(featcols)}")
    emit(f"train {train.sum():,} (<2023) | val {val.sum():,} (2023-24) | "
         f"test {test.sum():,} (2025+)")
    emit(f"base rate (p1 wins): train {y[train].mean():.4f}  test {y[test].mean():.4f}")
    emit()

    # ---- fit, choosing regularisation on validation only -----------------
    emit("-" * 84)
    emit("MODEL SELECTION (validation)")
    emit("-" * 84)
    variants = []
    for C in (0.003, 0.01, 0.03, 0.1, 0.3, 1.0):
        pipe = Pipeline([("sc", StandardScaler()),
                         ("lr", LogisticRegression(C=C, max_iter=3000))])
        pipe.fit(X[train], y[train])
        pv = pipe.predict_proba(X[val])[:, 1]
        b = brier_score_loss(y[val], pv)
        variants.append((C, b, pipe))
        emit(f"  C={C:<7} val Brier {b:.5f}  logloss {log_loss(y[val], pv):.5f}")
    C, _, model = min(variants, key=lambda t: t[1])
    emit(f"  -> chose C={C}. Variants tested: {len(variants)} "
         f"(reported for multiple-comparisons honesty)")
    emit()

    pt = model.predict_proba(X[test])[:, 1]
    emit("-" * 84)
    emit("HELD-OUT PERFORMANCE (test split, all tiers, model alone)")
    emit("-" * 84)
    emit(f"  Brier    {brier_score_loss(y[test], pt):.5f}")
    emit(f"  LogLoss  {log_loss(y[test], pt):.5f}")
    emit(f"  AUC      {roc_auc_score(y[test], pt):.5f}")
    emit(f"  Accuracy {((pt > 0.5) == y[test]).mean():.5f}")
    emit()
    emit("  calibration by bucket:")
    ct = calibration_table(y[test], pt)
    for _, r in ct.iterrows():
        emit(f"    {r['bucket']:<10} n={r['n']:>7,}  pred {r['predicted']:.3f}"
             f"  actual {r['actual']:.3f}  gap {r['gap']:+.3f}")
    emit()

    df = df.copy()
    df["p_model"] = np.nan
    df.loc[test, "p_model"] = pt
    df.to_parquet(CACHE / "stage4_predictions.parquet", index=False)

    # ---- benchmark 1: bookmaker closing odds -----------------------------
    emit("=" * 84)
    emit("BENCHMARK 1 -- vs BOOKMAKER CLOSING ODDS (ATP/WTA main tour)")
    emit("=" * 84)
    joined = join_bookmakers(df[test])
    if joined is None or joined.empty:
        emit("  no bookmaker matches joined")
    else:
        emit(f"  joined {len(joined):,} test matches to bookmaker lines")
        report_market(joined, "AvgW_p", "average closing", emit)
        report_market(joined, "PSW_p", "Pinnacle closing", emit)
        joined.to_parquet(CACHE / "stage4_bookmaker_join.parquet", index=False)

    # ---- benchmark 2: Kalshi pre-match mid -------------------------------
    emit()
    emit("=" * 84)
    emit("BENCHMARK 2 -- vs KALSHI PRE-MATCH MID (the thing we'd bet into)")
    emit("=" * 84)
    kj = join_kalshi(df[test])
    if kj is None or kj.empty:
        emit("  no Kalshi matches joined")
    else:
        emit(f"  joined {len(kj):,} test matches to Kalshi pre-match prices")
        for tier, g in kj.groupby("k_tier", observed=True):
            emit(f"    {tier}: {len(g):,}")
        report_market(kj, "p_market", "Kalshi pre-match mid", emit)
        kj.to_parquet(CACHE / "stage4_kalshi_join.parquet", index=False)

    (REPORT / "stage4_model.txt").write_text("\n".join(lines), encoding="utf-8")
    emit()
    emit(f"report -> {REPORT / 'stage4_model.txt'}")
    return df, model, featcols


def _td_key(name):
    """'Van Assche L.' -> ('van assche', 'l')"""
    n = td.norm_name(name)
    toks = n.split()
    if len(toks) < 2:
        return None
    return " ".join(toks[:-1]), toks[-1][0]


def _sack_keys(name):
    """'Luca Van Assche' -> {('van assche','l'), ('assche','l')}"""
    toks = td.norm_name(name).split()
    if len(toks) < 2:
        return set()
    ini = toks[0][0]
    return {(" ".join(toks[1:]), ini), (toks[-1], ini)}


def join_bookmakers(test_df):
    path = ROOT / "data" / "tennisdata" / "tennisdata_all.parquet"
    if not path.exists():
        return None
    b = pd.read_parquet(path)
    b["Date"] = pd.to_datetime(b["Date"])
    b = b[b["Date"] >= test_df["date"].min()]
    b = b[b["Comment"].astype(str).str.contains("Completed", na=False)]

    bw = b["Winner"].astype(str).map(_td_key)
    bl = b["Loser"].astype(str).map(_td_key)
    ok = bw.notna() & bl.notna()
    b = b[ok].copy()
    b["kw"], b["kl"] = bw[ok], bl[ok]
    b["day"] = b["Date"].dt.normalize()

    idx = {}
    for _, r in b.iterrows():
        for dd in (r["day"], r["day"] - pd.Timedelta(days=1),
                   r["day"] + pd.Timedelta(days=1)):
            idx.setdefault((dd, frozenset([r["kw"], r["kl"]])), []).append(r)

    recs = []
    for _, r in test_df.iterrows():
        k1s, k2s = _sack_keys(r["p1"]), _sack_keys(r["p2"])
        day = pd.Timestamp(r["date"]).normalize()
        hit = None
        for k1 in k1s:
            for k2 in k2s:
                cand = idx.get((day, frozenset([k1, k2])))
                if cand:
                    hit = cand[0]
                    break
            if hit is not None:
                break
        if hit is None:
            continue
        p1_won_book = hit["kw"] in k1s
        rec = {"y": int(p1_won_book), "p_model": r["p_model"],
               "surface": r["surface"], "tier": r["tier"], "tour": r["tour"],
               "date": r["date"]}
        for src, cw, cl in (("AvgW_p", "AvgW", "AvgL"), ("PSW_p", "PSW", "PSL")):
            ow, ol = hit.get(cw), hit.get(cl)
            if ow and ol and ow > 1 and ol > 1:
                pw, _pl = devig(float(ow), float(ol))
                rec[src] = pw if p1_won_book else 1.0 - pw
            else:
                rec[src] = np.nan
        recs.append(rec)
    return pd.DataFrame(recs)


def join_kalshi(test_df):
    """Join held-out predictions to Kalshi events + their pre-match mid."""
    price_path = ROOT / "data" / "kalshi" / "kalshi_prematch_prices.parquet"
    if not price_path.exists():
        return None
    prices = pd.read_parquet(price_path)
    ev = td.load_kalshi_events()
    ev = ev.merge(prices, on="event_ticker", how="inner")
    ev = ev[ev["pre_mid"].notna() & ev["result_a"].isin(["yes", "no"])]
    if ev.empty:
        return None

    # Kalshi names -> canonical Sackmann names. Stage 0 already resolved every
    # Kalshi player; reuse that rather than reloading 1.75M matches and
    # rebuilding a 3.5M-row index just to look up ~1,500 names.
    canon = {}
    cached = CACHE / "stage0_player_market.parquet"
    if cached.exists():
        pm = pd.read_parquet(cached, columns=["kalshi_name", "canon"])
        pm = pm[pm["canon"].notna()].drop_duplicates("kalshi_name")
        canon = dict(zip(pm["kalshi_name"], pm["canon"]))
    else:
        idx = td.build_player_index(td.to_long(td.load_matches()))
        for nm in pd.unique(pd.concat([ev["player_a"], ev["player_b"]]).dropna()):
            canon[nm], _ = td.resolve(nm, idx)
    ev["canon_a"] = ev["player_a"].map(canon)
    ev["canon_b"] = ev["player_b"].map(canon)
    ev = ev[ev["canon_a"].notna() & ev["canon_b"].notna()]

    lookup = {}
    for _, r in ev.iterrows():
        day = pd.Timestamp(r["date"]).tz_localize(None).normalize() \
            if pd.notna(r["date"]) else None
        if day is None:
            continue
        pair = frozenset([r["canon_a"], r["canon_b"]])
        for dd in (day, day - pd.Timedelta(days=1), day + pd.Timedelta(days=1)):
            lookup.setdefault((dd, pair), r)

    recs = []
    for _, r in test_df.iterrows():
        day = pd.Timestamp(r["date"]).normalize()
        pair = frozenset([r["p1"], r["p2"]])
        hit = lookup.get((day, pair))
        if hit is None:
            continue
        # pre_mid is P(player_a wins); translate to P(p1 wins)
        p_a = float(hit["pre_mid"])
        p1_is_a = r["p1"] == hit["canon_a"]
        recs.append({
            "date": r["date"], "p1": r["p1"], "p2": r["p2"], "y": int(r["y"]),
            "p_model": r["p_model"],
            "p_market": p_a if p1_is_a else 1.0 - p_a,
            "surface": r["surface"], "tier": r["tier"], "tour": r["tour"],
            "k_tier": f"{hit['tour']} {hit['tier']}",
            "event_ticker": hit["event_ticker"],
            "hours_before": hit.get("hours_before"),
            "volume_pre": hit.get("volume_pre"),
            "spread": (float(hit["pre_ask"]) - float(hit["pre_bid"]))
            if pd.notna(hit.get("pre_ask")) and pd.notna(hit.get("pre_bid")) else np.nan,
        })
    out = pd.DataFrame(recs)
    if not out.empty:
        out = out[out["p_market"].between(0.01, 0.99)]
    return out


def report_market(j, col, label, emit):
    m = j[j[col].notna() & j["p_model"].notna()]
    if len(m) < 50:
        emit(f"  {label}: too few joined matches ({len(m)})")
        return
    y = m["y"].to_numpy()
    pm = m["p_model"].to_numpy()
    pk = m[col].to_numpy()
    bm, bk = brier_score_loss(y, pm), brier_score_loss(y, pk)
    emit(f"\n  {label}: {len(m):,} matches")
    emit(f"    model  Brier {bm:.5f}   logloss {log_loss(y, pm):.5f}")
    emit(f"    market Brier {bk:.5f}   logloss {log_loss(y, pk):.5f}")
    diff = bm - bk
    # paired bootstrap CI on the Brier difference
    rng = np.random.default_rng(7)
    boots = []
    n = len(m)
    for _ in range(2000):
        s = rng.integers(0, n, n)
        boots.append(brier_score_loss(y[s], pm[s]) - brier_score_loss(y[s], pk[s]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    emit(f"    model - market = {diff:+.5f}  95% CI [{lo:+.5f}, {hi:+.5f}]")
    emit(f"    VERDICT: {'model beats market' if hi < 0 else ('market beats model' if lo > 0 else 'indistinguishable')}")


if __name__ == "__main__":
    main()
