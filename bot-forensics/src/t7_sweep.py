r"""
t7_sweep.py - the parameter sweep the user asked for, with the corrections
that make a sweep mean anything.

Design fixed in advance: ../PREREGISTRATION_T6.md.

WHAT IT DOES
    Hundreds of (feature x threshold x price band x tier x round) cells. For
    each cell, on TRAIN only:
        * mean calibration residual (outcome - implied) and its t
        * a fee-exact buy-at-open, hold-to-settlement P&L using
          common/kalshi_fees.py (ONE implementation, GUARDS #6)
    Then:
        * BH-FDR at 5% over the WHOLE family, one denominator (GUARDS #11)
        * every BH survivor re-tested on the untouched HOLDOUT
        * a permutation null: outcome shuffled within tier, whole sweep re-run,
          to measure how many "discoveries" this machinery invents from noise

WHY THE RESIDUAL AND NOT THE WIN RATE
    A rule that selects favourites raises the win rate for free. Only the
    residual is an edge. GUARDS #1, filter form.

WHY BUY-AND-HOLD
    Four independent files in this repo now agree the stop loss is the single
    most expensive component (ledger B012). Buy-at-open-hold-to-settlement is
    both the cheapest execution and the one the 480-config sweep found least
    bad (S2, -2.29c).

THE BAR
    edge_cents = residual * 100. Cost bar is spread + entry fee + exit fee;
    hold-to-settlement pays no exit fee, so the bar is roughly
    spread + entry fee ~ 3-4c. A 2pp residual is 2c and DOES NOT CLEAR.
"""
from __future__ import annotations
import os, sys, math, itertools, json

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.abspath(os.path.join(HERE, "..", "out"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.kalshi_fees import (fee_order_cents,        # the ONLY fee impl
                                fee_rate_cents)

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 500)

RNG = np.random.default_rng(20260806)


# ----------------------------------------------------------------------
def net_cents_buy_hold(mid_c: np.ndarray, won: np.ndarray,
                       spread_c: np.ndarray | None = None) -> np.ndarray:
    """Net cents per contract: buy 1, hold to settlement.

    YOU CANNOT BUY AT THE MID. A taker lifts the ask, which is mid + spread/2.
    The first version of this function priced entries at the mid and thereby
    handed every strategy half a spread of free money - on the wide ITF books
    that is 2-4c per contract, which is the entire size of anything found here.
    `spread_c=None` reproduces the old, wrong behaviour and is kept only so the
    difference can be shown.

    Entry pays a taker fee on the price actually paid. Settlement pays no
    additional trading fee - the forensics established that a settlement row's
    `fee_cost` is the cumulative trading fee, not an extra charge.
    """
    px = mid_c if spread_c is None else mid_c + spread_c / 2.0
    px = np.clip(px, 1.0, 99.0)
    # **fee_rate_cents, NOT fee_order_cents. Corrected 2026-09-01.**
    # This is expectancy arithmetic, and `common/kalshi_fees.py` says so in
    # as many words: the per-ORDER round-up is "an artefact of order size
    # rather than an economic cost". Charging it to orders of ONE contract
    # billed a whole cent on a 0.63c fee at ~90c entries.
    #
    # Measured on the cited holdout cell (open_price>=80, n=261):
    #   as coded, fee_order_cents(px, 1) : -0.770c   <- the published number
    #   corrected, fee_rate_cents(px)    : -0.374c
    # So +0.396c of the published -0.77c was the rounding assumption.
    # **B024 STANDS**: still negative, and the 6.06c mean spread in that
    # cell is the killer, not the fee. Found by the `reopen` audit.
    fees = np.array([float(fee_rate_cents(float(p))) for p in px])
    return won * 100.0 - px - fees


# ----------------------------------------------------------------------
# the cells
# ----------------------------------------------------------------------
FEATURES = {
    # name            column        directions
    "form_last3_diff": ("last3_diff", (">=", "<=")),
    "form_last5_diff": ("last5_diff", (">=", "<=")),
    "winrate_diff":    ("wr_diff",    (">=", "<=")),
    "rest_diff_days":  ("rest_diff",  (">=", "<=")),
    "workload_diff":   ("load_diff",  (">=", "<=")),
    "experience_diff": ("exp_diff",   (">=", "<=")),
    "own_rest_days":   ("a_rest",     (">=", "<=")),
    "own_matches_7d":  ("a_in7",      (">=", "<=")),
    "round_ordinal":   ("round_ord",  (">=", "<=")),
    "open_price":      ("open_mid",   (">=", "<=")),
}

THRESH = {
    "last3_diff":  [-0.67, -0.34, 0.0, 0.34, 0.67],
    "last5_diff":  [-0.6, -0.3, 0.0, 0.3, 0.6],
    "wr_diff":     [-0.5, -0.25, 0.0, 0.25, 0.5],
    "rest_diff":   [-3.0, -1.0, 0.0, 1.0, 3.0],
    "load_diff":   [-2.0, -1.0, 0.0, 1.0, 2.0],
    "exp_diff":    [-3.0, -1.0, 0.0, 1.0, 3.0],
    "a_rest":      [1.0, 2.0, 3.0, 5.0, 7.0],
    "a_in7":       [1.0, 2.0, 3.0, 4.0],
    "round_ord":   [2.0, 4.0, 5.0, 6.0],
    "open_mid":    [20.0, 35.0, 50.0, 65.0, 80.0],
}

BANDS = {"any": (0, 100), "cheap": (5, 35), "mid": (35, 65), "dear": (65, 95)}
TIERS = ["any", "ATP", "Challenger", "WTA", "ITF-M", "ITF-W", "ITF-any"]

MIN_N = 40          # fixed in advance; a cell below this is not tested


def cells(df):
    """Yield (label, mask) for every pre-declared cell."""
    for tier in TIERS:
        if tier == "any":
            tmask = np.ones(len(df), bool)
        elif tier == "ITF-any":
            tmask = df.tier.isin(["ITF-M", "ITF-W"]).values
        else:
            tmask = (df.tier == tier).values
        for bname, (lo, hi) in BANDS.items():
            bmask = ((df.open_mid >= lo) & (df.open_mid < hi)).values
            for fname, (col, dirs) in FEATURES.items():
                vals = df[col].values
                ok = ~np.isnan(vals)
                for d in dirs:
                    for th in THRESH[col]:
                        m = tmask & bmask & ok
                        m = m & ((vals >= th) if d == ">=" else (vals <= th))
                        if m.sum() >= MIN_N:
                            yield (f"{tier}|{bname}|{fname}{d}{th}", m)


def evaluate(df, mask):
    sub = df[mask]
    n = len(sub)
    r = sub.residual.values
    mean = r.mean()
    se = r.std(ddof=1) / math.sqrt(n)
    t = mean / se if se > 0 else 0.0
    # two-sided p, normal approximation (n >= 40 everywhere)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    net_mid = net_cents_buy_hold(sub.open_mid.values, sub.outcome.values)
    net_ask = net_cents_buy_hold(sub.open_mid.values, sub.outcome.values,
                                 sub.open_spread.values)
    return dict(n=n, resid=mean, se=se, t=t, p=p,
                edge_c=mean * 100.0,
                net_c=net_ask.mean(),                    # the tradeable one
                net_se=net_ask.std(ddof=1) / math.sqrt(n),
                net_mid_c=net_mid.mean(),                # the flattering one
                spread=sub.open_spread.mean(),
                # same correction as above -- this is a reported
                # expectancy, not a bill
                fee_c=np.mean([float(fee_rate_cents(float(x)))
                               for x in sub.open_mid.values]))


def run_sweep(df, label=""):
    rows = []
    for name, mask in cells(df):
        r = evaluate(df, mask)
        r["cell"] = name
        rows.append(r)
    out = pd.DataFrame(rows)
    if label:
        print(f"{label}: {len(out)} cells tested")
    return out


def bh(pv, q=0.05):
    """Benjamini-Hochberg. Returns boolean array of discoveries."""
    m = len(pv)
    order = np.argsort(pv)
    crit = (np.arange(1, m + 1) / m) * q
    passed = pv[order] <= crit
    k = np.max(np.flatnonzero(passed)) + 1 if passed.any() else 0
    keep = np.zeros(m, bool)
    if k:
        keep[order[:k]] = True
    return keep


# ----------------------------------------------------------------------
def main():
    df = pd.read_csv(os.path.join(OUT, "t6_features.csv"))
    train = df[df.split == "train"].reset_index(drop=True)
    hold = df[df.split == "holdout"].reset_index(drop=True)
    print(f"train {len(train)}   holdout {len(hold)}\n")

    # ---------- 1. the real sweep, TRAIN only -------------------------
    S = run_sweep(train, "TRAIN sweep")
    S["bh_pass"] = bh(S.p.values, 0.05)
    n_disc = int(S.bh_pass.sum())
    print(f"BH-FDR 5% over the whole family of {len(S)} cells: "
          f"**{n_disc} discoveries**\n")

    print("--- 12 most extreme cells by |t| on TRAIN (BH column is the test)")
    top = S.reindex(S.t.abs().sort_values(ascending=False).index).head(12)
    print(top[["cell", "n", "resid", "t", "p", "bh_pass", "edge_c",
               "net_mid_c", "net_c", "spread"]].to_string(index=False,
                                            float_format=lambda x: f"{x:.4f}"))

    # ---------- 2. the permutation null -------------------------------
    # Shuffle the outcome within (tier x 5-cent price bin).
    #
    # THE FIRST VERSION SHUFFLED WITHIN TIER ONLY AND WAS WRONG. Favourites
    # really do win ~92% of the time; handing them the tier average (~50%)
    # manufactured a -38pp residual in every high-price cell that had nothing
    # to do with any feature. That null produced ~1,010 "discoveries" out of
    # 2,008 cells and max|t| = 22 - i.e. it was a worse null than the real
    # data, which is the tell. Stratifying by price bin preserves the
    # calibration structure and destroys only the feature link, which is the
    # hypothesis actually under test.
    print("\n" + "=" * 74)
    print("PERMUTATION NULL - outcome shuffled within (tier x 5c price bin),")
    print("so calibration survives and only the FEATURE link is destroyed")
    print("=" * 74)
    train = train.copy()
    train["_stratum"] = (train.tier.astype(str) + "|" +
                         (train.open_mid // 5).astype(int).astype(str))
    null_counts, null_max_t = [], []
    for it in range(10):
        t2 = train.copy()
        shuffled = t2.outcome.values.copy()
        for _s, idx in t2.groupby("_stratum").groups.items():
            idx = np.array(list(idx))
            if len(idx) > 1:
                shuffled[idx] = t2.outcome.values[RNG.permutation(idx)]
        t2["outcome"] = shuffled
        t2["residual"] = t2.outcome - t2.implied
        Sn = run_sweep(t2)
        k = int(bh(Sn.p.values, 0.05).sum())
        null_counts.append(k)
        null_max_t.append(float(Sn.t.abs().max()))
        print(f"  shuffle {it+1:2d}: {k:3d} BH discoveries, "
              f"max |t| = {null_max_t[-1]:.2f}")
    print(f"\n  null BH discoveries: mean {np.mean(null_counts):.1f}, "
          f"max {max(null_counts)}")
    print(f"  observed on real data: {n_disc}")
    print(f"  null max|t|: mean {np.mean(null_max_t):.2f}, "
          f"max {max(null_max_t):.2f}   observed max|t|: {S.t.abs().max():.2f}")

    # ---------- 3. holdout for BH survivors ---------------------------
    print("\n" + "=" * 74)
    print("HOLDOUT - the only number that counts")
    print("=" * 74)
    surv = S[S.bh_pass]
    if len(surv) == 0:
        print("No cell survived BH on train, so there is nothing to confirm.")
        print("Reporting the strongest train cells on holdout anyway, as a")
        print("courtesy check that they are not merely underpowered:")
        surv = top.head(6)

    hrows = []
    cellmap = dict(cells(hold))
    for _, row in surv.iterrows():
        m = cellmap.get(row.cell)
        if m is None or m.sum() < MIN_N:
            hrows.append(dict(cell=row.cell, n=0, note="cell empty on holdout"))
            continue
        r = evaluate(hold, m)
        hrows.append(dict(cell=row.cell, train_resid=row.resid, train_t=row.t,
                          n=r["n"], hold_resid=r["resid"], hold_t=r["t"],
                          hold_edge_c=r["edge_c"], hold_net_c=r["net_c"], hold_net_mid_c=r["net_mid_c"],
                          spread=r["spread"],
                          same_sign=bool(np.sign(row.resid) == np.sign(r["resid"]))))
    H = pd.DataFrame(hrows)
    print(H.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    S.to_csv(os.path.join(OUT, "t7_sweep_train.csv"), index=False)
    H.to_csv(os.path.join(OUT, "t7_sweep_holdout.csv"), index=False)

    # ---------- 4. the naive benchmarks -------------------------------
    print("\n" + "=" * 74)
    print("NAIVE BENCHMARKS - every result above must be read against these")
    print("=" * 74)
    for name, sub in [("ALL events", df),
                      ("favourites (>=50c)", df[df.open_mid >= 50]),
                      ("longshots (<50c)", df[df.open_mid < 50])]:
        nm = net_cents_buy_hold(sub.open_mid.values, sub.outcome.values)
        na = net_cents_buy_hold(sub.open_mid.values, sub.outcome.values,
                                sub.open_spread.values)
        se = na.std(ddof=1) / math.sqrt(len(na))
        print(f"  {name:22s} n={len(sub):5d}   at MID {nm.mean():+7.3f}c   "
              f"AT ASK {na.mean():+7.3f}c  se {se:.3f}")
    print("\n  Kalshi's own mid at the open is the benchmark to beat, and the")
    print("  calibration table in t6 says it is unbiased to within noise.")


if __name__ == "__main__":
    main()
