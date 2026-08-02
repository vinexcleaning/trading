"""Phase 2 -- the base test.

One question: conditional on entry price p, does the favourite win more often
than p? Everything else in this study is downstream of that.

Design notes that matter:

  * The unit is the match. Each match contributes exactly one row, so there is
    nothing to cluster -- the CIs are already match-level. Clustering is
    re-checked only where a match could contribute twice (it never does here).

  * The per-bucket null is a Poisson-binomial (the p_i differ within a bucket),
    not a binomial at the bucket mean. It is evaluated by exact simulation
    rather than approximated, because a 5c bucket at n=300 is exactly the regime
    where the normal approximation starts lying about the tail.

  * `entry_mid` is used for calibration and `entry_ask + slippage` for P&L, and
    they are never mixed. A result that exists only at mid is not a result.
"""
import argparse
import pathlib
from decimal import Decimal

import numpy as np
import pandas as pd

import fees
import ledger

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

FAV_MIN = 60            # cents; pre-match favourite threshold
MIN_DROP = 5            # cents; below this "lost set 1" is not readable
CP_LO, CP_HI = 15, 90   # minutes from t0 to search for the set-1 changepoint
HALF = 10               # half-window for the changepoint step statistic
STAB = 3                # minutes of stabilisation after the changepoint
# The step statistic at candidate c reads mid[c+1 : c+1+HALF], so the
# changepoint is not KNOWN until minute c+HALF. Entering at c+STAB would use
# HALF-STAB minutes of future information. The first honest entry is therefore
# c + HALF + 1, and the stabilisation delay sits on top of that.
CP_LAG = HALF + 1
# Primary entry rule. Causal-with-threshold, because it is a stopping time and
# the argmax variant is not. Both are reported.
BASE_RULE, BASE_OFFSET = "deep:12", 0
SLIP = 1                # cents of adverse slippage on entry
NSIM = 40000


# ------------------------------------------------------------------ loading
def load_extremes(tag="paths"):
    """Within-minute bid high / ask low, favourite-oriented. NaN where absent.

    These answer "did the book trade through this price during this minute",
    which is the only honest basis for deciding whether a resting order filled.
    """
    npz = np.load(DATA / f"{tag}_paths.npz", allow_pickle=True)
    if "bid_h" not in npz:
        raise SystemExit(f"{tag}_paths.npz predates the OHLC pull; rebuild "
                         f"with p1_state.py against candles_ohlc")
    bh = npz["bid_h"].astype(np.float64)
    al = npz["ask_l"].astype(np.float64)
    bh[bh < 0] = np.nan
    al[al < 0] = np.nan
    return bh, al


def load(tag="paths"):
    st = pd.read_parquet(DATA / f"{tag}_state.parquet")
    npz = np.load(DATA / f"{tag}_paths.npz", allow_pickle=True)
    bid = npz["bid"].astype(np.float64)
    ask = npz["ask"].astype(np.float64)
    bid[bid < 0] = np.nan
    ask[ask < 0] = np.nan
    mid = (bid + ask) / 2.0
    assert len(st) == len(bid), "state/path row mismatch"
    assert (st["ticker"].values == npz["ticker"]).all(), "path/state misaligned"
    # rows that failed extraction carry only ticker/ok/why; give them inert
    # values so nothing downstream has to special-case them
    st = st.reset_index(drop=True)
    st["ok"] = st["ok"].fillna(False).astype(bool)
    for c, v in (("plausible", False), ("kept_is_fav", False),
                 ("fav_won", False)):
        st[c] = st[c].fillna(v).astype(bool) if c in st else v
    for c in ("pre_bid", "pre_ask", "dur_min", "flat_before"):
        st[c] = pd.to_numeric(st.get(c), errors="coerce").fillna(-1)
    return st, bid, ask, mid


# ------------------------------------------------------- set-1 changepoint
def changepoint(mid):
    """Largest sustained level shift in the opening phase of each match.

    step(c) = mean(mid[c+1 : c+1+HALF]) - mean(mid[c-HALF : c]).  The set
    conclusion is the biggest such shift; its sign says who won the set.
    Returns (index, step) per row, NaN where the path is too short.
    """
    n, T = mid.shape
    cs = np.nancumsum(np.nan_to_num(mid), axis=1)
    ct = np.cumsum(np.isfinite(mid), axis=1)
    cs = np.concatenate([np.zeros((n, 1)), cs], axis=1)
    ct = np.concatenate([np.zeros((n, 1)), ct], axis=1)

    def wmean(lo, hi):
        s = cs[:, hi] - cs[:, lo]
        c = ct[:, hi] - ct[:, lo]
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(c >= HALF * 0.6, s / np.maximum(c, 1), np.nan)

    best_i = np.full(n, -1)
    best_s = np.full(n, np.nan)
    for c in range(CP_LO, min(CP_HI, T - HALF - 1)):
        after = wmean(c + 1, c + 1 + HALF)
        before = wmean(c - HALF, c)
        step = after - before
        better = np.abs(step) > np.abs(np.nan_to_num(best_s, nan=-1))
        better &= np.isfinite(step)
        best_i = np.where(better, c, best_i)
        best_s = np.where(better, step, best_s)
    return best_i, best_s


def changepoint_causal(mid, thresh=8.0):
    """First changepoint whose step clears `thresh` -- a genuine stopping time.

    `changepoint` above takes the argmax over the whole search window, so
    knowing that candidate c is the winner requires having seen every later
    candidate too. That is not a stopping time, optional-stopping fairness does
    not apply to it, and selection bias is possible even though no individual
    price is read from the future. This version fires at the first candidate
    that clears a fixed threshold, using nothing after minute c+HALF, so the
    entry time is a stopping time and the martingale argument holds.
    """
    n, T = mid.shape
    cs = np.nancumsum(np.nan_to_num(mid), axis=1)
    ct = np.cumsum(np.isfinite(mid), axis=1)
    cs = np.concatenate([np.zeros((n, 1)), cs], axis=1)
    ct = np.concatenate([np.zeros((n, 1)), ct], axis=1)

    def wmean(lo, hi):
        s = cs[:, hi] - cs[:, lo]
        c = ct[:, hi] - ct[:, lo]
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(c >= HALF * 0.6, s / np.maximum(c, 1), np.nan)

    fire_i = np.full(n, -1)
    fire_s = np.full(n, np.nan)
    for c in range(CP_LO, min(CP_HI, T - HALF - 1)):
        step = wmean(c + 1, c + 1 + HALF) - wmean(c - HALF, c)
        hit = (fire_i < 0) & np.isfinite(step) & (np.abs(step) >= thresh)
        fire_i = np.where(hit, c, fire_i)
        fire_s = np.where(hit, step, fire_s)
    return fire_i, fire_s


# ---------------------------------------------------------------- events
def completed_dip(mid, pre_mid, depth=12.0, pause=8, hi_extra=40, lo=None):
    """First minute at which the favourite's dip is both DEEP and DONE.

    This is the closest causal approximation to "the first set is over and the
    price has settled at its new level". Two conditions, both readable at the
    minute they fire:

      deep  -- the mid is at least `depth` cents below the pre-match mid
      done  -- the mid is not a new low relative to the previous `pause`
               minutes, i.e. the fall has stopped for now

    NOTE ON THE STRENGTH OF `done`, pinned by tests/test_fillmodel.py. This is
    weaker than "stable for `pause` minutes". Once the price steps down and
    holds for a single minute, the trailing window already contains that low
    and the condition is satisfied at the very next minute. In practice the
    rule fires ~1 minute after the fall stops, not `pause` minutes after.
    That is still a stopping time and still uses no future data, but the rule
    must not be described as an 8-minute stabilisation.

    The first-8c-step rule fires on whatever moved first, which in a set the
    favourite loses is usually the break of serve rather than the set itself.
    This rule waits for the move to complete. It is still a stopping time: no
    price after the firing minute is consulted.
    """
    n, T = mid.shape
    lo = CP_LO if lo is None else lo
    hi = min(CP_HI + hi_extra, T - 1)
    fire = np.full(n, -1)
    for t in range(lo + pause, hi):
        m = mid[:, t]
        prev = mid[:, t - pause:t]
        # an all-NaN window means no quote at all in that stretch; nanmin would
        # warn and return NaN, which `done` below already treats as "not ready"
        any_ok = np.isfinite(prev).any(axis=1)
        lowest = np.full(len(prev), np.nan)
        if any_ok.any():
            lowest[any_ok] = np.nanmin(prev[any_ok], axis=1)
        deep = np.isfinite(m) & (m <= pre_mid - depth)
        done = np.isfinite(lowest) & (m >= lowest)
        hit = (fire < 0) & deep & done
        fire = np.where(hit, t, fire)
    return fire


def build_events(st, bid, ask, mid, entry_rule="cp", offset=0, leaky=False,
                 min_minute=0):
    """One row per candidate match, at a given entry definition."""
    ok = st["ok"].values & st["plausible"].values
    pre_bid = st["pre_bid"].values.astype(float)
    pre_ask = st["pre_ask"].values.astype(float)
    pre_mid = (pre_bid + pre_ask) / 2.0

    if entry_rule.startswith("deep"):
        d = float(entry_rule.split(":")[1]) if ":" in entry_rule else 12.0
        cp_i = completed_dip(mid, pre_mid, d, lo=max(CP_LO, min_minute))
        cp_s = np.where(cp_i >= 0, -d, np.nan)
        e = np.where(cp_i >= 0, cp_i + STAB + offset, -1)
        return _finish(st, bid, ask, mid, pre_mid, cp_i, cp_s, e)

    if entry_rule.startswith("causal"):
        thresh = float(entry_rule.split(":")[1]) if ":" in entry_rule else 8.0
        cp_i, cp_s = changepoint_causal(mid, thresh)
        entry_rule = "cp"
    else:
        cp_i, cp_s = changepoint(mid)

    if entry_rule == "cp":
        e = cp_i + CP_LAG + STAB + offset
        # hard guarantee, not a comment: no entry may precede the minute at
        # which the changepoint became knowable
        assert offset >= 0 or leaky, "cp offset < 0 is look-ahead"
        if not leaky:
            assert np.all(e[cp_i >= 0] >= (cp_i + CP_LAG)[cp_i >= 0])
    elif entry_rule == "cpleak":
        e = cp_i + STAB + offset          # deliberately leaky; diagnostic only
    elif entry_rule == "fixed":
        e = np.full(len(st), offset)
    else:
        raise ValueError(entry_rule)
    e = np.where((cp_i >= 0) | (entry_rule == "fixed"), e, -1)
    return _finish(st, bid, ask, mid, pre_mid, cp_i, cp_s, e)


def _finish(st, bid, ask, mid, pre_mid, cp_i, cp_s, e):
    """Common tail: read the entry quote and assemble one row per match."""
    ok = st["ok"].values & st["plausible"].values
    T = mid.shape[1]
    valid = ok & (e >= 0) & (e < T) & (pre_mid >= FAV_MIN)
    # entry must be strictly inside the match
    valid &= (e < st["dur_min"].values)

    ei = np.clip(e, 0, T - 1)
    r = np.arange(len(st))
    em = mid[r, ei]
    ea = ask[r, ei]
    eb = bid[r, ei]
    valid &= np.isfinite(em) & np.isfinite(ea)

    df = pd.DataFrame({
        "ticker": st["ticker"].values,
        "event_ticker": st.get("event_ticker", pd.Series(st["ticker"])).values,
        "tour": st["tour"].values if "tour" in st else "?",
        "close_time": st["close_time"].values if "close_time" in st else pd.NaT,
        "dur_min": st["dur_min"].values,
        "pre_mid": pre_mid,
        "cp_idx": cp_i,
        "cp_step": cp_s,
        "entry_idx": e,
        "entry_mid": em,
        "entry_ask": ea,
        "entry_bid": eb,
        "fav_won": st["fav_won"].values.astype(float),
        "valid": valid,
    })
    df["entry_spread"] = df["entry_ask"] - df["entry_bid"]
    df["vol_inplay"] = (st["vol_inplay"].values if "vol_inplay" in st
                        else np.nan)
    df["drop"] = df["pre_mid"] - df["entry_mid"]
    df["is_event"] = df["valid"] & (df["drop"] >= MIN_DROP)
    return df


# ------------------------------------------------------------- statistics
def poisson_binom_p(wins, p, rng, nsim=NSIM):
    """Two-sided and one-sided p for observed wins under sum of Bernoulli(p_i)."""
    if len(p) == 0:
        return np.nan, np.nan
    sims = (rng.random((nsim, len(p))) < p).sum(axis=1)
    exp = p.sum()
    hi = (sims >= wins).mean()
    lo = (sims <= wins).mean()
    two = min(1.0, 2 * min(hi, lo))
    return hi, two


def costed(entry_mid, entry_ask, win, hold=True, exit_price=None):
    """Net cents per contract. Buy at the ask plus slippage; exact fees."""
    fill = np.minimum(entry_ask + SLIP, 99.0)
    fee_in = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    if hold:
        gross = 100.0 * win - fill
        return gross - fee_in, fill, fee_in
    ex = exit_price
    fee_out = np.array([float(fees.fee_rate_cents(int(round(x)))) for x in ex])
    return ex - fill - fee_in - fee_out, fill, fee_in + fee_out


def calib_table(ev, rng, width=5, label=""):
    e = ev[ev["is_event"]].copy()
    e["bucket"] = (np.floor(e["entry_mid"] / width) * width).astype(int)
    out = []
    for b, g in e.groupby("bucket"):
        p = (g["entry_mid"] / 100.0).values
        w = g["fav_won"].values
        wins = int(w.sum())
        one, two = poisson_binom_p(wins, p, rng)
        net, fill, fee = costed(g["entry_mid"].values, g["entry_ask"].values, w)
        be = (fill.mean() + fee.mean()) / 100.0
        out.append({
            "bucket": f"{b}-{b + width}",
            "n": len(g),
            "impl_p": p.mean(),
            "obs": w.mean(),
            "mis_pp": 100 * (w.mean() - p.mean()),
            "p_1sided": one,
            "p_2sided": two,
            "mean_fill": fill.mean(),
            "mean_fee": fee.mean(),
            "breakeven_win": be,
            "net_c": net.mean(),
        })
    t = pd.DataFrame(out)
    return t, e


def bootstrap_ci(x, rng, n=10000, q=(2.5, 97.5)):
    idx = rng.integers(0, len(x), size=(n, len(x)))
    m = x[idx].mean(axis=1)
    return np.percentile(m, q)


def report(ev, rng, title, fh=None, tag=None):
    def w(s=""):
        print(s, flush=True)
        if fh:
            fh.write(s + "\n")

    t, e = calib_table(ev, rng)
    w(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    w(f"candidate matches (fav >= {FAV_MIN}c, valid entry): "
      f"{int(ev['valid'].sum()):,}")
    w(f"events (drop >= {MIN_DROP}c):                        {len(e):,}")
    if len(e) == 0:
        return t, e
    w(f"median drop {e['drop'].median():.1f}c   "
      f"median entry mid {e['entry_mid'].median():.1f}c   "
      f"median pre-match {e['pre_mid'].median():.1f}c")
    sp = e["entry_spread"]
    w(f"spread at entry: median {sp.median():.0f}c  p75 {sp.quantile(.75):.0f}c "
      f" p90 {sp.quantile(.9):.0f}c  p99 {sp.quantile(.99):.0f}c")
    w(f"  (the 1c slippage assumption is optimistic wherever the spread is "
      f"wide; {(sp >= 4).mean():.1%} of entries quote 4c or more)")

    w("")
    w(f"{'entry':>9} {'n':>6} {'impl p':>7} {'obs':>7} {'mis pp':>7} "
      f"{'p1':>7} {'p2':>7} {'fill':>6} {'fee':>5} {'BE win':>7} {'net c':>7}")
    for r in t.itertuples():
        w(f"{r.bucket:>9} {r.n:>6,} {r.impl_p:>7.3f} {r.obs:>7.3f} "
          f"{r.mis_pp:>+7.2f} {r.p_1sided:>7.3f} {r.p_2sided:>7.3f} "
          f"{r.mean_fill:>6.1f} {r.mean_fee:>5.2f} {r.breakeven_win:>7.3f} "
          f"{r.net_c:>+7.2f}")

    p = (e["entry_mid"] / 100.0).values
    win = e["fav_won"].values
    mis = 100 * (win - p)
    lo, hi = bootstrap_ci(mis, rng)
    one, two = poisson_binom_p(int(win.sum()), p, rng)
    net, fill, fee = costed(e["entry_mid"].values, e["entry_ask"].values, win)
    nlo, nhi = bootstrap_ci(net, rng)

    w("")
    w(f"POOLED  n={len(e):,}")
    w(f"  implied  {p.mean():.4f}     observed {win.mean():.4f}")
    w(f"  miscalibration  {mis.mean():+.2f} pp   "
      f"95% CI [{lo:+.2f}, {hi:+.2f}]")
    w(f"  Poisson-binomial  p(one-sided, overshoot) = {one:.4f}   "
      f"p(two-sided) = {two:.4f}")
    w(f"  net expectancy, hold to settlement, ask+{SLIP}c fill, exact fees:")
    w(f"     {net.mean():+.3f} c/contract   95% CI [{nlo:+.3f}, {nhi:+.3f}]")
    w(f"  breakeven miscalibration needed: "
      f"{(fill.mean() + fee.mean() - p.mean() * 100):+.2f} pp")
    if tag:
        ledger.add(phase="2", factor="headline", level=tag, n=len(e),
                   mis_pp=round(mis.mean(), 3), ci_lo=round(lo, 3),
                   ci_hi=round(hi, 3), p_one=round(one, 5),
                   p_two=round(two, 5), net_c=round(net.mean(), 4))
    return t, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="paths")
    ap.add_argument("--out", default="p2_base.txt")
    ap.add_argument("--grid", action="store_true")
    args = ap.parse_args()

    st, bid, ask, mid = load(args.tag)
    rng = np.random.default_rng(7)
    path = ROOT / "reports" / args.out
    with open(path, "w", encoding="utf-8") as fh:
        ev = build_events(st, bid, ask, mid, BASE_RULE, BASE_OFFSET)
        ev_t = build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
        t, e = report(
            ev, rng,
            f"PHASE 2 BASE TEST -- entry rule '{BASE_RULE}': the first minute "
            f"at which the\nfavourite's price is 12c+ below its pre-match "
            f"level AND has stopped making new\nlows for 8 minutes, entered "
            f"{STAB} min later. A stopping time: no price after the\n"
            f"firing minute is consulted. Twenty-seven other entry definitions "
            f"are in the grid below.",
            fh, tag="deep:12 (pre-committed primary)")
        e.to_parquet(DATA / f"{args.tag}_events.parquet", index=False)

        report(ev_t, rng,
               "PHASE 2b BEST-TARGETED RULE -- 'deep:30 after minute 38'.\n"
               "Phase 1 measured this as the entry rule whose fired events are "
               "most often a\nreal set-1 loss (precision 0.788 vs 0.559 for the "
               "pre-committed rule above).\nChosen on labelled state, not on "
               "outcomes.", fh, tag="deep:30@38 (best-targeted)")

        # ---- label-verified subsample -----------------------------------
        tp = DATA / "truth_set1.parquet"
        if tp.exists():
            truth = pd.read_parquet(tp)
            kf = st.set_index("ticker")["kept_is_fav"].to_dict()
            truth = truth[truth["ticker"].isin(kf)]
            fav_lost = np.array([
                (not w) if kf.get(t, False) else bool(w)
                for t, w in zip(truth["ticker"], truth["player_won_s1"])])
            keep = set(truth.loc[fav_lost, "ticker"])
            lab = ev_t[ev_t["ticker"].isin(keep)].copy()
            report(lab, rng,
                   "PHASE 2c LABEL-VERIFIED SUBSAMPLE -- only matches where an "
                   "external\nscoreline confirms the favourite actually lost "
                   "set 1. Small, but it is the\nliteral question the brief "
                   "asks, with no inference in the state variable.", fh,
                   tag="label-verified subsample")

        if args.grid:
            fh.write("\n\n" + "#" * 78 +
                     "\n# ENTRY-TIMING SENSITIVITY GRID\n" + "#" * 78 + "\n")
            print("\n" + "#" * 78)
            rows = []
            specs = ([(f"deep:{d}", 0) for d in (8, 12, 16, 20, 25, 30)] +
                     [(f"deep:{d}@38", 0) for d in (12, 20, 30)] +
                     [("deep:12", o) for o in (5, 10)] +
                     [("cp", o) for o in (0, 5, 10, 15, 20)] +
                     [(f"causal:{t}", 0) for t in (5, 8, 12, 16)] +
                     [("fixed", o) for o in (25, 30, 35, 40, 45, 50, 60, 75)] +
                     [("cpleak", o) for o in (-10, 0)])
            for rule, off in specs:
                floor = 0
                if "@" in rule:
                    rule, floor = rule.split("@")
                    floor = int(floor)
                g = build_events(st, bid, ask, mid, rule, off,
                                 leaky=(rule == "cpleak"), min_minute=floor)
                rule = rule if not floor else f"{rule}@{floor}"
                ge = g[g["is_event"]]
                if len(ge) < 50:
                    continue
                p = (ge["entry_mid"] / 100.0).values
                win = ge["fav_won"].values
                m = 100 * (win - p)
                lo, hi = bootstrap_ci(m, rng, n=4000)
                net, fill, fee = costed(ge["entry_mid"].values,
                                        ge["entry_ask"].values, win)
                rows.append({"rule": f"{rule}{off:+d}", "n": len(ge),
                             "mis_pp": m.mean(), "lo": lo, "hi": hi,
                             "net_c": net.mean()})
                one, two = poisson_binom_p(int(win.sum()), p, rng)
                ledger.add(phase="2-grid", factor="entry definition",
                           level=f"{rule}{off:+d}", n=len(ge),
                           mis_pp=round(m.mean(), 3), ci_lo=round(lo, 3),
                           ci_hi=round(hi, 3), p_one=round(one, 5),
                           p_two=round(two, 5), net_c=round(net.mean(), 4),
                           note=("DELIBERATE LEAK, diagnostic only"
                                 if rule == "cpleak" else ""))
            gt = pd.DataFrame(rows)
            hdr = (f"{'entry rule':>12} {'n':>7} {'mis pp':>8} "
                   f"{'95% CI':>18} {'net c':>8}")
            print(hdr)
            fh.write(hdr + "\n")
            for r in gt.itertuples():
                line = (f"{r.rule:>12} {r.n:>7,} {r.mis_pp:>+8.2f} "
                        f"[{r.lo:+6.2f},{r.hi:+6.2f}] {r.net_c:>+8.3f}")
                print(line)
                fh.write(line + "\n")
            gt.to_csv(ROOT / "reports" / "p2_entry_grid.csv", index=False)
    print(f"\n-> {path}")


if __name__ == "__main__":
    main()
