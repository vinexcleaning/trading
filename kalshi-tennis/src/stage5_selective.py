"""Stage 5 -- where (not whether) the model beats the market.

The published result worth imitating: a model that loses money applied to
everything can make money restricted to a narrow subset. So this segments the
holdout and asks where the edge is positive AND survives correction for how
many segments were examined.

Everything here is fee-inclusive on both legs. Kalshi's taker fee is
    ceil(0.07 * C * P * (1-P))  cents
charged on entry; winning contracts settle at $1 with no settlement fee. A
model edge of one or two cents is inside the fee, which is exactly why
"bet everything with a positive edge" loses.

Multiple comparisons are corrected with Benjamini-Hochberg, and the number of
segments tested is reported, because testing 30 segments at p<0.05 finds 1.5
"edges" in pure noise by construction.
"""
import itertools
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
REPORT = ROOT / "reports"

FEE_RATE = 0.07
EDGE_GRID = (0.02, 0.05, 0.10)
MIN_SEGMENT = 40


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "common"))
from kalshi_fees import fee_dollars_from_price_vec  # noqa: E402


def fee(price, contracts=1.0):
    """Kalshi taker fee in dollars, rounded up to the cent. price in dollars.

    Exact Decimal — see common/kalshi_fees.py. The previous float form
    overcharged a cent on ~6% of price/size cells.
    """
    return fee_dollars_from_price_vec(price, contracts)


def entry_price(side_yes, bid, ask, mid, executable=True):
    """What you actually pay per contract.

    Buying YES lifts the ASK. Buying NO costs 1 - BID. Filling at the mid is
    not a trade: 39% of these markets quote 1c/99c, where the "mid" of 50c is
    an average of two prices nobody will trade at.
    """
    if not executable:
        return np.where(side_yes, mid, 1.0 - mid)
    return np.where(side_yes, ask, 1.0 - bid)


def pnl(side_yes, entry, won):
    """Profit per 1 contract, fee-inclusive. Winners settle at $1."""
    hit = np.where(side_yes, won, 1 - won)
    gross = np.where(hit == 1, 1.0 - entry, -entry)
    return gross - fee(entry)


def bootstrap_ci(x, n_boot=4000, seed=11):
    rng = np.random.default_rng(seed)
    n = len(x)
    if n < 5:
        return np.nan, np.nan
    means = [x[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def bh(pvals, alpha=0.05):
    """Benjamini-Hochberg: returns a boolean mask of survivors."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    thresh = alpha * (np.arange(1, n + 1) / n)
    passed = p[order] <= thresh
    keep = np.zeros(n, dtype=bool)
    if passed.any():
        cutoff = np.max(np.where(passed)[0])
        keep[order[:cutoff + 1]] = True
    return keep


def enrich(j):
    """Pull ranking-gap and data-density axes off the Stage 4 prediction frame."""
    pred_path = CACHE / "stage4_predictions.parquet"
    if not pred_path.exists():
        return j
    cols = ["date", "p1", "p2", "d_elo", "d_log_rank",
            "min_all_serve_pts_won_n", "min_elo_n"]
    have = pd.read_parquet(pred_path).columns
    cols = [c for c in cols if c in have]
    p = pd.read_parquet(pred_path, columns=cols)
    p["date"] = pd.to_datetime(p["date"])
    # The same two players can meet twice on one date (different events), so
    # this key is not unique -- dedupe or the merge silently inflates the row
    # count and double-counts bets.
    # LEDGER T022, fixed 2026-08-06. `keep="first"` on its own is ORDER-
    # DEPENDENT: which of two same-day meetings survives was decided by whatever
    # order the parquet happened to return, so two runs on the same data could
    # keep different rows and neither was reproducible.
    #
    # The fix is an explicit sort on the columns already loaded, all of which are
    # pre-match features or identifiers -- date, player names, elo and rank gaps,
    # sample-size counts. NONE is outcome-derived, which is the condition
    # GUARDS #1 actually cares about: S011 voided four phases of set1_overshoot
    # by deduping on `volume_fp`, which scored P(kept side wins) = 0.5356,
    # z = +10.0. A fixed arbitrary rule is not ideal; a non-deterministic one is
    # strictly worse, because it cannot even be reproduced to be audited.
    p = p.sort_values(list(p.columns), kind="mergesort")
    p = p.drop_duplicates(subset=["date", "p1", "p2"], keep="first")
    j = j.copy()
    j["date"] = pd.to_datetime(j["date"])

    # attach the executable quotes
    # ==================================================================
    # WARNING: THIS IS THE LEAKED ANCHOR. Re-running this script reproduces
    # a benchmark built on it, and nothing on screen would say so.
    #
    # `kalshi_prematch_prices.parquet` is, in this project's own words,
    # "really the settled price... that is leakage". Its sibling docstring
    # says exactly that.
    #
    # No live conclusion rests on it: T007, T008 and T010 were RETRACTED and
    # T012 re-did the direction on the clean anchor. The numbers this script
    # prints are therefore of historical interest ONLY and must not be
    # quoted as a result.
    #
    # The real fix is to re-anchor to -6h. Flagged by the repo-wide audit,
    # 2026-09-01 (`tennis` mailbox 022); the header is the cheap half.
    # ==================================================================
    price_path = ROOT / "data" / "kalshi" / "kalshi_prematch_prices.parquet"
    if price_path.exists():
        q = pd.read_parquet(price_path,
                            columns=["event_ticker", "pre_bid", "pre_ask"])
        j = j.merge(q, on="event_ticker", how="left", suffixes=("", "_q"))
    out = j.merge(p, on=["date", "p1", "p2"], how="left")
    assert len(out) == len(j), f"merge duplicated rows: {len(j)} -> {len(out)}"
    return out


def segment_frame(j):
    """Attach the segmentation axes the spec asks for."""
    d = enrich(j)
    d["edge"] = d["p_model"] - d["p_market"]
    d["price_band"] = pd.cut(d["p_market"],
                             [0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0],
                             labels=["<20c", "20-35c", "35-50c", "50-65c",
                                     "65-80c", ">80c"])
    if "d_elo" in d.columns:
        d["gap_band"] = pd.cut(d["d_elo"].abs(), [0, 50, 100, 200, 1e9],
                               labels=["elo<50", "50-100", "100-200", "200+"])
    if "min_all_serve_pts_won_n" in d.columns:
        d["density"] = pd.cut(d["min_all_serve_pts_won_n"],
                              [-1, 500, 2000, 5000, 1e12],
                              labels=["thin", "medium", "thick", "very thick"])
    if "pre_bid" in d.columns and "pre_ask" in d.columns:
        d["spread"] = d["pre_ask"] - d["pre_bid"]
        d["liquidity"] = pd.cut(d["spread"], [-1, 0.02, 0.05, 0.10, 1.01],
                                labels=["tight <=2c", "3-5c", "6-10c",
                                        "wide >10c"])
    return d


def evaluate(d, thresh, executable=True):
    """Bet only where |edge| exceeds thresh; return per-bet fee-inclusive P&L."""
    take = d[d["edge"].abs() >= thresh].copy()
    if executable:
        take = take[take["pre_bid"].notna() & take["pre_ask"].notna()]
    if take.empty:
        return take
    take["side_yes"] = take["edge"] > 0
    take["entry"] = entry_price(take["side_yes"].to_numpy(),
                                take["pre_bid"].to_numpy(),
                                take["pre_ask"].to_numpy(),
                                take["p_market"].to_numpy(),
                                executable=executable)
    take = take[take["entry"].between(0.01, 0.99)]
    if take.empty:
        return take
    take["pnl"] = pnl(take["side_yes"].to_numpy(),
                      take["entry"].to_numpy(),
                      take["y"].to_numpy())
    return take


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    path = CACHE / "stage4_kalshi_join.parquet"
    if not path.exists():
        print("no Kalshi join available -- run Stage 4 first")
        return
    j = pd.read_parquet(path)
    d = segment_frame(j)

    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    emit("=" * 90)
    emit("STAGE 5 -- SELECTIVE BETTING (fee-inclusive, both legs)")
    emit("=" * 90)
    emit(f"held-out Kalshi matches with a pre-match price: {len(d):,}")
    emit(f"fee model: ceil(0.07 * P * (1-P)) per contract, charged on entry")
    emit(f"mean |edge| vs market: {d['edge'].abs().mean():.4f}")
    emit(f"mean fee at 50c: ${fee(0.5):.4f}  -- an edge below this cannot pay")
    emit()

    if "spread" in d.columns:
        emit("-" * 90)
        emit("LIQUIDITY -- can these prices actually be traded?")
        emit("-" * 90)
        emit(d["liquidity"].value_counts().sort_index().to_string())
        emit(f"  median spread {d['spread'].median():.3f}   "
             f"share wider than 10c: {(d['spread'] > 0.10).mean() * 100:.1f}%")
        emit("  A 1c/99c quote has a 50c 'mid' that no one will trade at.")
        emit()

    emit("-" * 90)
    emit("BET EVERYTHING -- fantasy fill (at the mid) vs real fill (ask/bid)")
    emit("-" * 90)
    emit(f"{'min edge':<10}{'fill':<10}{'bets':>7}{'mean P&L':>11}"
         f"{'95% CI':>24}{'ROI':>9}")
    for t in EDGE_GRID:
        for label, execu in (("mid", False), ("ask/bid", True)):
            take = evaluate(d, t, executable=execu)
            if take.empty:
                emit(f"{t:<10.2f}{label:<10}{'0':>7}")
                continue
            x = take["pnl"].to_numpy()
            lo, hi = bootstrap_ci(x)
            stake = take["entry"].mean()
            emit(f"{t:<10.2f}{label:<10}{len(x):>7,}{x.mean():>+11.4f}"
                 f"{f'[{lo:+.4f}, {hi:+.4f}]':>24}"
                 f"{x.mean() / stake * 100:>+8.1f}%")
    emit()
    emit("Only the ask/bid rows are real. Everything below uses executable fills.")
    emit()

    # ---- segmented search -------------------------------------------------
    axes = ["k_tier", "surface", "price_band"]
    for extra in ("gap_band", "density", "liquidity"):
        if extra in d.columns:
            axes.append(extra)

    emit("-" * 90)
    emit("SEGMENTED SEARCH")
    emit("-" * 90)
    rows = []
    for t in EDGE_GRID:
        take = evaluate(d, t)
        if take.empty:
            continue
        for ax in axes:
            if ax not in take.columns:
                continue
            for val, g in take.groupby(ax, observed=True):
                if len(g) < MIN_SEGMENT:
                    continue
                x = g["pnl"].to_numpy()
                tstat, p = stats.ttest_1samp(x, 0.0)
                rows.append({
                    "min_edge": t, "axis": ax, "segment": str(val),
                    "bets": len(x), "mean_pnl": x.mean(), "p": p,
                })
        # two-way: tier x surface
        for (a, b), g in take.groupby(["k_tier", "surface"], observed=True):
            if len(g) < MIN_SEGMENT:
                continue
            x = g["pnl"].to_numpy()
            tstat, p = stats.ttest_1samp(x, 0.0)
            rows.append({"min_edge": t, "axis": "tier x surface",
                         "segment": f"{a} / {b}", "bets": len(x),
                         "mean_pnl": x.mean(), "p": p})

    if not rows:
        emit("  no segment reached the minimum size")
    else:
        res = pd.DataFrame(rows)
        res["survives_bh"] = bh(res["p"].to_numpy())
        # LEDGER T021, re-read 2026-08-06 and its severity CORRECTED DOWN.
        # The row is worded "sorts variants on mean_pnl over the full sample
        # with no holdout", which reads like a selection step. It is not: this
        # sort only decides the ORDER OF THE PRINTED TABLE, and the
        # Benjamini-Hochberg correction below is applied across EVERY segment,
        # not across the 25 shown. Nothing downstream consumes the ordering.
        #
        # The hazard that remains is a reading hazard: printing the 25 best
        # realised P&Ls invites a reader to quote one. `res.head(25)` below is
        # therefore the thing to be careful with, and `n_sig` -- computed over
        # all segments -- is the number that means anything.
        res = res.sort_values("mean_pnl", ascending=False)
        emit(f"segments tested: {len(res)}  "
             f"(Benjamini-Hochberg at alpha=0.05 applied across all of them)")
        emit()
        emit(f"{'edge':<6}{'axis':<16}{'segment':<26}{'bets':>7}"
             f"{'mean P&L':>11}{'p':>9}{'BH':>5}")
        for _, r in res.head(25).iterrows():
            emit(f"{r['min_edge']:<6.2f}{r['axis']:<16}{r['segment']:<26}"
                 f"{r['bets']:>7,}{r['mean_pnl']:>+11.4f}{r['p']:>9.3f}"
                 f"{'  YES' if r['survives_bh'] else '   no'}")
        emit()
        n_sig = int(res["survives_bh"].sum())
        emit(f"segments surviving correction: {n_sig} of {len(res)}")
        if n_sig == 0:
            emit("Nothing survives. The positive segments above are what you")
            emit("would expect from searching this many slices of noise.")
        res.to_csv(CACHE / "stage5_segments.csv", index=False)

    (REPORT / "stage5_selective.txt").write_text("\n".join(lines), encoding="utf-8")
    emit()
    emit(f"report -> {REPORT / 'stage5_selective.txt'}")


if __name__ == "__main__":
    main()
