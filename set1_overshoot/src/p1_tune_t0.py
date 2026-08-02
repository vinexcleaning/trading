"""Tune and validate the match-start detector against real match durations.

Sackmann records `minutes` (actual playing time) for main-tour matches. Kalshi's
inferred play window can therefore be checked against ground truth rather than
eyeballed. The tuning target is the median signed error and the spread of the
error, not correlation -- a detector that is 40 minutes early on every match
correlates perfectly and is still wrong.

Kalshi's clock runs on wall time, so the inferred window legitimately exceeds
Sackmann's playing minutes by the changeovers, medical timeouts and rain delays
that Sackmann does not count. A small positive bias is expected; a large or
erratic one is not.
"""
import itertools
import pathlib

import numpy as np
import pandas as pd

import p1_state as ps

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main():
    subdir = "candles" if (DATA / "candles").exists() else "candles_dev"
    cd = ps.load_candles(subdir)
    uni = pd.read_parquet(DATA / "universe.parquet")
    truth = pd.read_parquet(DATA / "truth_set1.parquet")
    truth = truth[truth["minutes"].notna() & (truth["minutes"] > 20)]
    want = set(truth["ticker"])
    cd = cd[cd["ticker"].isin(want)]
    print(f"{cd['ticker'].nunique():,} markets with a true duration")
    if cd["ticker"].nunique() < 30:
        print("not enough overlap yet -- rerun after the full candle pull")
        return

    tmin = truth.set_index("ticker")["minutes"].to_dict()
    t_arr = cd["ticker"].values
    ts = cd["ts"].values
    bid = cd["bid"].values.astype(np.int32)
    ask = cd["ask"].values.astype(np.int32)
    bounds = np.r_[0, np.where(t_arr[1:] != t_arr[:-1])[0] + 1, len(t_arr)]

    cleaned = {}
    for k in range(len(bounds) - 1):
        s, e = bounds[k], bounds[k + 1]
        res = ps.clean_one(ts[s:e], bid[s:e], ask[s:e])
        if res is not None:
            cleaned[t_arr[s]] = res[3]

    rows = []
    grid = list(itertools.product([12, 18, 25, 35], [0, 30, 60], [0, 4, 8]))
    for gap, dw, dm in grid:
        if (dw == 0) != (dm == 0):
            continue
        errs, n = [], 0
        for tick, mid2 in cleaned.items():
            w = ps.find_play_window(mid2, gap, dw, dm)
            if w is None:
                continue
            errs.append((w[1] - w[0]) - tmin[tick])
            n += 1
        errs = np.array(errs, float)
        rows.append({
            "gap": gap, "dens_win": dw, "dens_min": dm, "n": n,
            "median_err": np.median(errs),
            "mad": np.median(np.abs(errs - np.median(errs))),
            "p10": np.percentile(errs, 10),
            "p90": np.percentile(errs, 90),
            "frac_over_60": (errs > 60).mean(),
            "frac_neg": (errs < -10).mean(),
        })
    t = pd.DataFrame(rows).sort_values("mad")
    print("\ninferred window length minus true playing minutes:")
    print(t.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
    t.to_csv(ROOT / "reports" / "p1_t0_tuning.csv", index=False)
    b = t.iloc[0]
    print(f"\nbest by MAD: gap={b.gap:.0f} dens_win={b.dens_win:.0f} "
          f"dens_min={b.dens_min:.0f}  median err {b.median_err:+.0f} min, "
          f"MAD {b.mad:.0f} min")


if __name__ == "__main__":
    main()
