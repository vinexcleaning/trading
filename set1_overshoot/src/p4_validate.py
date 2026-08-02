"""Phase 4 -- validation.

Holdout, purged walk-forward, bootstrap, deflated Sharpe. Run once, at the end.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

import ledger
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def deflated_sharpe(sr, n, n_trials, skew=0.0, kurt=3.0):
    """Bailey & Lopez de Prado. sr is per-observation, n observations.

    The expected maximum Sharpe from n_trials independent noise draws is
    subtracted before asking whether what is left is real.
    """
    if n_trials < 2 or n < 10:
        return np.nan, np.nan
    e = 0.5772156649
    z1 = stats.norm.ppf(1 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    sr0 = (1 - e) * z1 + e * z2
    denom = np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)
    if denom <= 0:
        return sr0, np.nan
    dsr = stats.norm.cdf((sr - sr0) * np.sqrt(n - 1) / denom)
    return sr0, dsr


def block(e, rng, label, w):
    p = (e["entry_mid"] / 100.0).values
    win = e["fav_won"].values
    mis = 100 * (win - p)
    lo, hi = p2.bootstrap_ci(mis, rng, n=10000)
    one, two = p2.poisson_binom_p(int(win.sum()), p, rng)
    net, fill, fee = p2.costed(e["entry_mid"].values, e["entry_ask"].values, win)
    nlo, nhi = p2.bootstrap_ci(net, rng, n=10000)
    w(f"| {label} | {len(e):,} | {p.mean():.4f} | {win.mean():.4f} | "
      f"{mis.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {one:.4f} | "
      f"{net.mean():+.3f} | [{nlo:+.3f}, {nhi:+.3f}] |")
    return {"n": len(e), "mis": mis.mean(), "lo": lo, "hi": hi,
            "p_one": one, "net": net.mean(), "net_lo": nlo, "net_hi": nhi,
            "net_arr": net}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="paths")
    ap.add_argument("--trials", type=int, default=0,
                    help="variant count for the deflated Sharpe; "
                         "0 = read it from the ledger")
    args = ap.parse_args()

    st, bid, ask, mid = p2.load(args.tag)
    rng = np.random.default_rng(23)
    ev = p2.build_events(st, bid, ask, mid, p2.BASE_RULE, p2.BASE_OFFSET)
    e = ev[ev["is_event"]].copy()
    e["close_time"] = pd.to_datetime(e["close_time"], utc=True)
    e = e.sort_values("close_time")

    lines = []

    def w(s=""):
        print(s, flush=True)
        lines.append(s)

    w("# Phase 4 -- validation")
    w("")
    cut = e["close_time"].quantile(0.60)
    tr = e[e["close_time"] <= cut]
    ho = e[e["close_time"] > cut]

    w("## Temporal split")
    w("")
    w(f"Split at **{cut:%Y-%m-%d %H:%M} UTC** (oldest 60% / newest 40%).")
    w("")
    w(f"- train: {len(tr):,} events, "
      f"{tr['close_time'].min():%Y-%m-%d} to {tr['close_time'].max():%Y-%m-%d}")
    w(f"- holdout: {len(ho):,} events, "
      f"{ho['close_time'].min():%Y-%m-%d} to {ho['close_time'].max():%Y-%m-%d}")
    w("")
    w("**Confound to note explicitly:** the split falls inside the "
      "clay-to-grass-to-hard")
    w("run of the calendar. A temporal holdout in tennis is therefore also a "
      "surface and")
    w("tournament-mix change, and a configuration failing on holdout may be "
      "failing on")
    w("surface rather than on time. The composition of both halves is printed "
      "below so")
    w("that is visible rather than buried.")
    w("")
    w("| tour | train | holdout |")
    w("|---|---|---|")
    a = tr.groupby("tour").size()
    b = ho.groupby("tour").size()
    for t in sorted(set(a.index) | set(b.index)):
        w(f"| {t} | {a.get(t, 0):,} | {b.get(t, 0):,} |")
    w("")

    w("## Headline, train vs holdout")
    w("")
    w("| sample | n | implied | observed | mis pp | 95% CI | p(1s) | "
      "net c | net 95% CI |")
    w("|---|---|---|---|---|---|---|---|---|")
    r_all = block(e, rng, "all", w)
    r_tr = block(tr, rng, "train (oldest 60%)", w)
    r_ho = block(ho, rng, "holdout (newest 40%)", w)
    w("")

    # --- top configurations, run once on holdout -------------------------
    w("## Top configurations on the holdout, run once")
    w("")
    cfgs = []
    tr2 = tr.copy()
    tr2["f_strength"] = pd.cut(tr2["pre_mid"], [59.9, 70, 80, 90, 101],
                               labels=["60-70", "70-80", "80-90", "90+"])
    tr2["f_drop"] = pd.cut(tr2["drop"], [4.9, 10, 20, 30, 200],
                           labels=["5-10c", "10-20c", "20-30c", "30c+"])
    for col in ("f_strength", "f_drop", "tour"):
        for lvl, g in tr2.groupby(col, observed=True):
            if len(g) < 80:
                continue
            p = (g["entry_mid"] / 100.0).values
            cfgs.append((col, lvl, 100 * (g["fav_won"].values - p).mean(),
                         len(g)))
    cfgs.sort(key=lambda x: -x[2])
    top = cfgs[:3]
    w("Selected on **train only**, by train miscalibration, then evaluated "
      "once here.")
    w("")
    w("| config | train mis pp | train n | holdout n | holdout mis pp | "
      "95% CI | p(1s) | holdout net c |")
    w("|---|---|---|---|---|---|---|---|")
    ho2 = ho.copy()
    ho2["f_strength"] = pd.cut(ho2["pre_mid"], [59.9, 70, 80, 90, 101],
                               labels=["60-70", "70-80", "80-90", "90+"])
    ho2["f_drop"] = pd.cut(ho2["drop"], [4.9, 10, 20, 30, 200],
                           labels=["5-10c", "10-20c", "20-30c", "30c+"])
    for col, lvl, tm, tn in top:
        g = ho2[ho2[col] == lvl]
        if len(g) < 20:
            w(f"| {col}={lvl} | {tm:+.2f} | {tn:,} | {len(g):,} | "
              f"*too few* | - | - | - |")
            continue
        p = (g["entry_mid"] / 100.0).values
        win = g["fav_won"].values
        mis = 100 * (win - p)
        lo, hi = p2.bootstrap_ci(mis, rng, n=10000)
        one, _ = p2.poisson_binom_p(int(win.sum()), p, rng)
        net, _, _ = p2.costed(g["entry_mid"].values, g["entry_ask"].values, win)
        w(f"| {col}={lvl} | {tm:+.2f} | {tn:,} | {len(g):,} | "
          f"{mis.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {one:.4f} | "
          f"{net.mean():+.3f} |")
        ledger.add(phase="4-holdout", factor="top config", level=f"{col}={lvl}",
                   n=len(g), mis_pp=round(mis.mean(), 3), ci_lo=round(lo, 3),
                   ci_hi=round(hi, 3), p_one=round(one, 5),
                   net_c=round(net.mean(), 4), note="holdout, run once")
    w("")

    # --- purged walk-forward ---------------------------------------------
    w("## Purged walk-forward")
    w("")
    w("Five sequential folds, each evaluated on data strictly after its "
      "training")
    w("window, with a **48-hour embargo** between them. Tennis matches settle "
      "within")
    w("hours, so 48h is comfortably longer than any single observation's life "
      "and no")
    w("information can straddle the boundary.")
    w("")
    w("| fold | train n | test n | test window | test mis pp | 95% CI | "
      "test net c |")
    w("|---|---|---|---|---|---|---|")
    # Timestamps, not integers. Parquet hands back datetime64[us] here, so an
    # int64 cast is microseconds while np.timedelta64(48,"h") in ns is 1000x
    # larger -- an embargo of 5.5 years, which silently empties every fold.
    ti = pd.to_datetime(e["close_time"], utc=True)
    qs = [ti.quantile(q) for q in np.linspace(0, 1, 7)]
    emb = pd.Timedelta(hours=48)
    fold_mis = []
    for k in range(1, 6):
        tr_m = ti <= qs[k]
        te_m = (ti > qs[k] + emb) & (ti <= qs[k + 1])
        g = e[te_m]
        if len(g) < 40:
            continue
        p = (g["entry_mid"] / 100.0).values
        win = g["fav_won"].values
        mis = 100 * (win - p)
        lo, hi = p2.bootstrap_ci(mis, rng, n=4000)
        net, _, _ = p2.costed(g["entry_mid"].values, g["entry_ask"].values, win)
        fold_mis.append(mis.mean())
        w(f"| {k} | {tr_m.sum():,} | {len(g):,} | "
          f"{g['close_time'].min():%m-%d} to {g['close_time'].max():%m-%d} | "
          f"{mis.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {net.mean():+.3f} |")
    if fold_mis:
        w("")
        w(f"Fold-to-fold miscalibration: mean {np.mean(fold_mis):+.2f} pp, "
          f"sd {np.std(fold_mis):.2f} pp, "
          f"{sum(m > 0 for m in fold_mis)}/{len(fold_mis)} positive.")
    w("")

    # --- the fade side, on the holdout ------------------------------------
    w("## The undershoot on the holdout, and the fade it implies")
    w("")
    w("Phase 2 found the market undershoots, so the direction with any edge "
      "in it is")
    w("buying the **underdog** at `100 - favourite_bid`. Phase 2 also showed "
      "that trade")
    w("losing money in every configuration. The question left for the holdout "
      "is narrow:")
    w("is the undershoot itself stable over time, or was it a property of the "
      "first half")
    w("of the sample?")
    w("")
    import fees as _f
    evt = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    et = evt[evt["is_event"]].copy()
    et["close_time"] = pd.to_datetime(et["close_time"], utc=True)
    cut_t = et["close_time"].quantile(0.60)
    w("| sample | n | fav implied | fav observed | mis pp | 95% CI | p(1s "
      "undershoot) | fade net c | fade net 95% CI |")
    w("|---|---|---|---|---|---|---|---|---|")
    for lbl, g in (("all", et),
                   ("train (oldest 60%)", et[et["close_time"] <= cut_t]),
                   ("holdout (newest 40%)", et[et["close_time"] > cut_t])):
        pf = (g["entry_mid"] / 100.0).values
        wf = g["fav_won"].values
        m = 100 * (wf - pf)
        lo2, hi2 = p2.bootstrap_ci(m, rng, n=10000)
        _, two_u = p2.poisson_binom_p(int(wf.sum()), pf, rng)
        one_u = 1.0 - p2.poisson_binom_p(int(wf.sum()), pf, rng)[0]
        fill = np.minimum(100.0 - g["entry_bid"].values + p2.SLIP, 99.0)
        fee = np.array([float(_f.fee_rate_cents(int(round(x)))) for x in fill])
        netf = 100.0 * (1 - wf) - fill - fee
        flo, fhi = p2.bootstrap_ci(netf, rng, n=10000)
        w(f"| {lbl} | {len(g):,} | {pf.mean():.4f} | {wf.mean():.4f} | "
          f"{m.mean():+.2f} | [{lo2:+.2f}, {hi2:+.2f}] | {one_u:.4f} | "
          f"{netf.mean():+.3f} | [{flo:+.3f}, {fhi:+.3f}] |")
        ledger.add(phase="4-holdout", factor="undershoot, deep:30@38",
                   level=lbl, n=len(g), mis_pp=round(m.mean(), 3),
                   ci_lo=round(lo2, 3), ci_hi=round(hi2, 3),
                   p_one=round(one_u, 5), net_c=round(netf.mean(), 4),
                   note="fade side; p is one-sided for UNDERSHOOT")
    w("")

    # --- day-clustered bootstrap ------------------------------------------
    w("## Day-clustered bootstrap")
    w("")
    w("Each row is already one match, so the ordinary bootstrap is "
      "match-clustered by")
    w("construction. But matches on the same day at the same tournament share "
      "weather,")
    w("court, balls and draw quality, so the effective sample is smaller than "
      "the match")
    w("count. Resampling whole days instead of individual matches prices that "
      "in.")
    w("")
    day = pd.to_datetime(e["close_time"]).dt.strftime("%Y-%m-%d").values
    keys = np.unique(day)
    groups = {k: np.where(day == k)[0] for k in keys}
    p = (e["entry_mid"] / 100.0).values
    win = e["fav_won"].values
    mis = 100 * (win - p)
    net_all = r_all["net_arr"]
    bm, bn = [], []
    for _ in range(4000):
        pick = rng.choice(len(keys), size=len(keys))
        idx = np.concatenate([groups[keys[i]] for i in pick])
        bm.append(mis[idx].mean())
        bn.append(net_all[idx].mean())
    lo_d, hi_d = np.percentile(bm, [2.5, 97.5])
    nlo_d, nhi_d = np.percentile(bn, [2.5, 97.5])
    w(f"- distinct days: **{len(keys)}**, median "
      f"{np.median([len(v) for v in groups.values()]):.0f} events per day")
    w(f"- miscalibration, day-clustered 95% CI: "
      f"**[{lo_d:+.2f}, {hi_d:+.2f}] pp** "
      f"(match-clustered was [{r_all['lo']:+.2f}, {r_all['hi']:+.2f}])")
    w(f"- net expectancy, day-clustered 95% CI: "
      f"**[{nlo_d:+.3f}, {nhi_d:+.3f}] c** "
      f"(match-clustered was [{r_all['net_lo']:+.3f}, "
      f"{r_all['net_hi']:+.3f}])")
    w("")

    # --- deflated Sharpe ---------------------------------------------------
    n_trials = args.trials
    if not n_trials:
        try:
            n_trials = len(pd.read_csv(ledger.CSV))
        except Exception:  # noqa: BLE001
            n_trials = 50
    net = r_all["net_arr"]
    sr = net.mean() / net.std() if net.std() > 0 else 0.0
    sk = stats.skew(net)
    ku = stats.kurtosis(net, fisher=False)
    sr0, dsr = deflated_sharpe(sr, len(net), max(n_trials, 2), sk, ku)
    w("## Deflated Sharpe")
    w("")
    w(f"- variants evaluated (ledger rows): **{n_trials}**")
    w(f"- per-trade Sharpe of the base configuration: **{sr:+.4f}** "
      f"(skew {sk:+.2f}, kurtosis {ku:.2f})")
    w(f"- expected maximum Sharpe from {n_trials} pure-noise variants: "
      f"**{sr0:+.4f}**")
    w(f"- **deflated Sharpe probability: {dsr:.4f}** "
      f"(probability the true Sharpe exceeds zero once selection is "
      f"accounted for)")
    w("")
    if np.isfinite(dsr) and dsr < 0.95:
        w("The observed Sharpe does not exceed what this many variants would "
          "produce from noise alone.")

    (ROOT / "reports" / "p4_validation.md").write_text("\n".join(lines),
                                                       encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p4_validation.md'}")


if __name__ == "__main__":
    main()
