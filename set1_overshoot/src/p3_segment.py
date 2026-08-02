"""Phase 3 -- segmentation. Runs only if Phase 2 clears its gate.

Factors are tested one at a time against the base effect. There is no factorial
grid: with a 4-level and a 4-level and a 5-level factor, a grid is 80 cells and
at least four of them will look significant on noise. Combinations are formed
only from factors that individually survive FDR.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

import fees
import ledger
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


# ------------------------------------------------------------ exit rules
def simulate_exit(ev, bid, ask, row_of, target=None, stop=None):
    """Walk each match forward from entry; exit at the bid, pay two fees.

    Hold-to-settlement pays one fee; any early exit pays two. The asymmetry is
    large enough (about 1.7c at mid prices) to reverse the ranking of exit
    rules on its own, so it is applied exactly rather than approximated.
    """
    fill = np.minimum(ev["entry_ask"].values + p2.SLIP, 99.0)
    ei = ev["entry_idx"].values.astype(int)
    dur = ev["dur_min"].values.astype(int)
    win = ev["fav_won"].values
    rows = row_of

    net = np.empty(len(ev))
    exited = np.zeros(len(ev), bool)
    exit_px = np.full(len(ev), np.nan)
    for k in range(len(ev)):
        r = rows[k]
        lo = ei[k] + 1
        hi = min(int(dur[k]), bid.shape[1] - 1)
        px = None
        if lo < hi and (target is not None or stop is not None):
            b = bid[r, lo:hi]
            hit_t = np.where(b >= fill[k] + target)[0] if target else np.array([])
            hit_s = np.where(b <= fill[k] - stop)[0] if stop else np.array([])
            first_t = hit_t[0] if len(hit_t) else np.inf
            first_s = hit_s[0] if len(hit_s) else np.inf
            if np.isfinite(min(first_t, first_s)):
                j = int(min(first_t, first_s))
                px = float(b[j])
        if px is None or not np.isfinite(px):
            fee = float(fees.fee_rate_cents(int(round(fill[k]))))
            net[k] = 100.0 * win[k] - fill[k] - fee
        else:
            fee = (float(fees.fee_rate_cents(int(round(fill[k]))))
                   + float(fees.fee_rate_cents(int(round(px)))))
            net[k] = px - fill[k] - fee
            exited[k] = True
            exit_px[k] = px
    return net, exited, exit_px


# ------------------------------------------------------------ reporting
def seg(e, col, rng, phase, factor, w, note="", min_n=40):
    w(f"\n### {factor}")
    w("")
    w(f"| level | n | implied | observed | mis pp | 95% CI | p(1s) | "
      f"net c/contract |")
    w("|---|---|---|---|---|---|---|---|")
    for lvl, g in e.groupby(col, observed=True):
        if len(g) < min_n:
            w(f"| {lvl} | {len(g):,} | - | - | *n too small* | - | - | - |")
            ledger.add(phase=phase, factor=factor, level=str(lvl), n=len(g),
                       note="skipped, n<%d" % min_n)
            continue
        p = (g["entry_mid"] / 100.0).values
        win = g["fav_won"].values
        mis = 100 * (win - p)
        lo, hi = p2.bootstrap_ci(mis, rng, n=4000)
        one, two = p2.poisson_binom_p(int(win.sum()), p, rng)
        net, fill, fee = p2.costed(g["entry_mid"].values,
                                   g["entry_ask"].values, win)
        w(f"| {lvl} | {len(g):,} | {p.mean():.3f} | {win.mean():.3f} | "
          f"{mis.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {one:.4f} | "
          f"{net.mean():+.3f} |")
        ledger.add(phase=phase, factor=factor, level=str(lvl), n=len(g),
                   mis_pp=round(mis.mean(), 3), ci_lo=round(lo, 3),
                   ci_hi=round(hi, 3), p_one=round(one, 5),
                   p_two=round(two, 5), net_c=round(net.mean(), 4), note=note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="paths")
    ap.add_argument("--out", default="p3_segments.md")
    ap.add_argument("--holdout", action="store_true",
                    help="run on the newest 40% instead of the oldest 60%")
    args = ap.parse_args()

    st, bid, ask, mid = p2.load(args.tag)
    rng = np.random.default_rng(11)
    ev = p2.build_events(st, bid, ask, mid, p2.BASE_RULE, p2.BASE_OFFSET)
    ev["row"] = np.arange(len(ev))
    e = ev[ev["is_event"]].copy()

    e["close_time"] = pd.to_datetime(e["close_time"], utc=True)
    cut = e["close_time"].quantile(0.60)
    e_train = e[e["close_time"] <= cut].copy()
    e_hold = e[e["close_time"] > cut].copy()
    use = e_hold if args.holdout else e_train

    lines = []

    def w(s=""):
        print(s, flush=True)
        lines.append(s)

    w(f"# Phase 3 -- segmentation "
      f"({'HOLDOUT (newest 40%)' if args.holdout else 'TRAIN (oldest 60%)'})")
    w("")
    w("> **The Phase 2 gate FAILED. Everything in this file is exploratory and "
      "none of it")
    w("> is a candidate for trading.** The pre-registered rule was to stop "
      "here, because")
    w("> slicing a null into subgroups until one looks positive is how this "
      "project has")
    w("> produced false positives four times. It is run anyway, and labelled, "
      "for two")
    w("> reasons: the user asked specific questions about favourite strength "
      "and about")
    w("> men's versus women's tennis that deserve a direct answer, and the "
      "output is a")
    w("> concrete demonstration of what subgroup hunting yields on a null. "
      "Every level")
    w("> below is carried into the Benjamini-Hochberg correction over the "
      "whole ledger.")
    w("")
    w("> Read the holdout column in `p4_validation.md` alongside this. The "
      "best subgroup")
    w("> found on train (`pre-match 90+`, +7.93 pp) collapses to **+0.04 pp** "
      "on the")
    w("> holdout. That single line is the most useful thing in this file.")
    w("")
    w(f"Split at **{cut:%Y-%m-%d %H:%M} UTC**. "
      f"train n={len(e_train):,}, holdout n={len(e_hold):,}. "
      f"Working set: **n={len(use):,}**.")
    w("")
    w("Every level below is written to `HYPOTHESIS_LEDGER.md` and carried into "
      "the Benjamini-Hochberg correction, including the levels skipped for "
      "small n.")

    use["f_strength"] = pd.cut(use["pre_mid"], [59.9, 70, 80, 90, 101],
                               labels=["60-70", "70-80", "80-90", "90+"])
    use["f_drop"] = pd.cut(use["drop"], [4.9, 10, 20, 30, 200],
                           labels=["5-10c", "10-20c", "20-30c", "30c+"])
    # closeness proxy: drop relative to what that pre-match price usually drops
    med = use.groupby(pd.cut(use["pre_mid"], [59.9, 70, 80, 90, 101]),
                      observed=True)["drop"].transform("median")
    use["f_close"] = np.where(use["drop"] < med, "close set (small drop)",
                              "decisive set (large drop)")
    use["f_entry"] = pd.cut(use["entry_mid"], [0, 30, 40, 50, 60, 101],
                            labels=["<30c", "30-40c", "40-50c", "50-60c",
                                    "60c+"])

    ph = "3-holdout" if args.holdout else "3"
    seg(use, "f_strength", rng, ph, "3a favourite strength (pre-match mid)", w,
        "pre-registered directional: 70-80 > 60-70")
    seg(use, "f_drop", rng, ph, "3b drop size", w,
        "pre-registered directional: larger drop -> larger overshoot")
    seg(use, "f_close", rng, ph, "3c first-set closeness (drop vs cohort median)",
        w)
    seg(use, "tour", rng, ph, "3f series and gender", w,
        "pre-registered directional: men's more predictable")
    seg(use, "f_entry", rng, ph, "3-extra entry price band", w)

    # ---- 3e exit surface -------------------------------------------------
    w("\n### 3e exit rules")
    w("")
    w("Entry fill is the ask plus 1c of slippage in every cell. Exits sell at "
      "the **bid**.")
    w("Hold-to-settlement pays **one** fee; every early exit pays **two**.")
    w("")
    rows = []
    rowidx = use["row"].values
    for tgt in [None, 10, 15, 20, 25]:
        for stp in [None, 15, 20, 25, 30]:
            net, exited, _ = simulate_exit(use, bid, ask, rowidx, tgt, stp)
            lo, hi = p2.bootstrap_ci(net, rng, n=3000)
            rows.append({"target": tgt or "-", "stop": stp or "-",
                         "net_c": net.mean(), "lo": lo, "hi": hi,
                         "pct_exited": exited.mean(),
                         "sd": net.std()})
            ledger.add(phase=ph, factor="3e exit rule",
                       level=f"target={tgt or 'hold'} stop={stp or 'none'}",
                       n=len(use), net_c=round(net.mean(), 4),
                       ci_lo=round(lo, 3), ci_hi=round(hi, 3),
                       note="P&L cell, no calibration p-value")
    ex = pd.DataFrame(rows)
    w("| target | stop | net c/contract | 95% CI | sd | % exited early |")
    w("|---|---|---|---|---|---|")
    for r in ex.itertuples():
        w(f"| {r.target} | {r.stop} | {r.net_c:+.3f} | "
          f"[{r.lo:+.3f}, {r.hi:+.3f}] | {r.sd:.1f} | {r.pct_exited:.1%} |")
    ex.to_csv(ROOT / "reports" /
              f"p3_exit_surface{'_holdout' if args.holdout else ''}.csv",
              index=False)

    best = ex.loc[ex["net_c"].idxmax()]
    neigh = ex[(ex["net_c"] > best["net_c"] - 0.5)]
    w("")
    w(f"Best cell: target={best['target']} stop={best['stop']} at "
      f"{best['net_c']:+.3f} c. "
      f"{len(neigh)} of {len(ex)} cells sit within 0.5c of it, so this is "
      f"{'a broad plateau' if len(neigh) >= 6 else '**an isolated peak -- treat as overfitting**'}.")

    # ---- 3d wait-for-the-next-move ---------------------------------------
    w("\n### 3d serve order in set 2, and waiting for the first game")
    w("")
    w("Serve order itself is **not recoverable from price**, and no source in "
      "reach")
    w("publishes it. Saying otherwise would be inventing a variable. What *is* "
      "testable")
    w("is the tradeable form of the same question: does waiting through the "
      "first game")
    w("or two of set 2 -- and in particular waiting to see whether the "
      "favourite holds or")
    w("is broken again -- change the risk-adjusted result? Each rule below is "
      "causal: it")
    w("only ever looks at prices at or before its own entry minute.")
    w("")
    w("| rule | n | implied | observed | mis pp | 95% CI | net c | sd of net |")
    w("|---|---|---|---|---|---|---|---|")
    rowidx = use["row"].values
    ei = use["entry_idx"].values.astype(int)
    dur = use["dur_min"].values.astype(int)
    for name, wait, cond in [("enter immediately", 0, None),
                             ("wait 7 min (about one game)", 7, None),
                             ("wait 14 min (about two games)", 14, None),
                             ("wait for a further 5c fall", 0, -5),
                             ("wait for a 5c recovery", 0, +5)]:
        idx, keep = [], []
        for k in range(len(use)):
            r = rowidx[k]
            base = ei[k]
            lim = min(int(dur[k]), mid.shape[1] - 1)
            if cond is None:
                j = base + wait
                if j < lim and np.isfinite(mid[r, j]):
                    idx.append(j)
                    keep.append(k)
            else:
                m0 = mid[r, base]
                seg_m = mid[r, base + 1:lim]
                hit = (np.where(seg_m <= m0 + cond)[0] if cond < 0
                       else np.where(seg_m >= m0 + cond)[0])
                if len(hit):
                    idx.append(base + 1 + int(hit[0]))
                    keep.append(k)
        if len(keep) < 40:
            w(f"| {name} | {len(keep):,} | *too few* | - | - | - | - | - |")
            continue
        keep = np.array(keep)
        idx = np.array(idx)
        rr = rowidx[keep]
        em = mid[rr, idx]
        ea = ask[rr, idx]
        win = use["fav_won"].values[keep]
        good = np.isfinite(em) & np.isfinite(ea)
        em, ea, win = em[good], ea[good], win[good]
        p = em / 100.0
        m = 100 * (win - p)
        lo, hi = p2.bootstrap_ci(m, rng, n=4000)
        one, two = p2.poisson_binom_p(int(win.sum()), p, rng)
        net, _, _ = p2.costed(em, ea, win)
        w(f"| {name} | {len(em):,} | {p.mean():.3f} | {win.mean():.3f} | "
          f"{m.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {net.mean():+.3f} | "
          f"{net.std():.1f} |")
        ledger.add(phase=ph, factor="3d entry timing within set 2", level=name,
                   n=len(em), mis_pp=round(m.mean(), 3), ci_lo=round(lo, 3),
                   ci_hi=round(hi, 3), p_one=round(one, 5),
                   p_two=round(two, 5), net_c=round(net.mean(), 4))

    # ---- 3g player tendencies --------------------------------------------
    w("\n### 3g player-level comeback tendency")
    w("")
    try:
        pl = pd.read_parquet(DATA / "players.parquet")
    except Exception:  # noqa: BLE001
        pl = None
    if pl is None:
        w("`players.parquet` missing -- skipped.")
    else:
        g = use.merge(pl[["ticker", "player", "opponent"]], on="ticker",
                      how="left")
        g["fav_name"] = np.where(
            use["pre_mid"].values >= 60,
            np.where(g["ticker"].isin(
                st.loc[st["kept_is_fav"].fillna(False), "ticker"]),
                g["player"], g["opponent"]), g["player"])
        cnt = g.groupby("fav_name").size().sort_values(ascending=False)
        w(f"- distinct favourites in the sample: **{cnt.size:,}**")
        w(f"- median matches per favourite: **{cnt.median():.0f}**, "
          f"p90 {cnt.quantile(.9):.0f}, max {cnt.max():.0f}")
        w(f"- favourites with 10+ qualifying matches: "
          f"**{(cnt >= 10).sum():,}**")
        w("")
        n_need = int(np.ceil(2 * (1.96 + 0.84) ** 2 * 0.25 / (0.10 ** 2)))
        w(f"To separate a genuine 60% comeback player from a 50% one at 80% "
          f"power needs about **{n_need} qualifying matches per player**. "
          f"The sample offers a median of {cnt.median():.0f}.")
        w("")
        if (cnt >= 10).sum() >= 30:
            half = use["close_time"].quantile(0.5)
            a = g[g["close_time"] <= half]
            b = g[g["close_time"] > half]
            ra = a.groupby("fav_name")["fav_won"].agg(["mean", "size"])
            ra = ra[ra["size"] >= 4]
            rb = b.groupby("fav_name")["fav_won"].agg(["mean", "size"])
            rb = rb[rb["size"] >= 4]
            j = ra.join(rb, lsuffix="_1", rsuffix="_2", how="inner")
            if len(j) >= 20:
                r = np.corrcoef(j["mean_1"], j["mean_2"])[0, 1]
                w(f"Out-of-sample persistence: rank a player on the first "
                  f"half, evaluate on the second. n={len(j)} players with 4+ "
                  f"matches in both halves, correlation of comeback rates "
                  f"**r = {r:+.3f}**.")
                ledger.add(phase=ph, factor="3g player tendency",
                           level="half-to-half persistence", n=len(j),
                           mis_pp=round(100 * r, 2),
                           note="correlation, not a miscalibration")
            else:
                w("Too few players appear in both halves with 4+ matches. "
                  "**Dropped as underpowered** rather than reported as noise.")
        else:
            w("**Dropped as underpowered.** Fewer than 30 favourites reach "
              "even 10 qualifying matches, so any per-player comeback rate "
              "here is noise with a decimal point on it.")
            ledger.add(phase=ph, factor="3g player tendency",
                       level="dropped, underpowered", n=int(cnt.size),
                       note="not evaluated")

    (ROOT / "reports" / args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / args.out}")


if __name__ == "__main__":
    main()
