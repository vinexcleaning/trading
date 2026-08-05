"""
t2b_nightday.py - TASK 2 proper. Is the night/day split real, or is it the
shape every random walk has?

THREE THINGS ARE TESTED, IN THIS ORDER:

1. THE ARGMAX NULL. The "it worked, then it stopped working" split was found
   by cutting the record at the maximum of its own cumulative curve. That is
   the single most selection-biased cut available: the argmax is DEFINED as
   the point that maximises (sum before) - and therefore tends to maximise
   (mean before) - (mean after). A pure random walk with zero drift produces
   a rising-then-falling equity curve every single time. So the observed gap
   is compared against the distribution of the same statistic computed on the
   SAME 108 numbers in random order. If the real gap is not extreme against
   that null, the split carries no information at all.

2. PRE-SPECIFIED CLOCK BUCKETS. Splitting on the clock rather than on the
   argmax. Four-hour UTC blocks, and a night/day dichotomy fixed before
   looking (night = 20:00-07:59 UTC, when Kalshi tennis is overwhelmingly
   ITF; day = 08:00-19:59). Reported with n, the cost bar per bucket, the
   minimum detectable effect, and a BH-FDR correction over the whole family.

3. THE CONFOUND. Tier mix differs by hour, and tier mix is what drives the
   spread. The night/day comparison is reported both raw and within tier.

The prior tennis study this repo already ran found 0 of 25 time/tier buckets
clearing a 3.61pp cost bar, with 7 positive where 12.5 would be expected by
chance. That is the benchmark this has to beat.
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import load

rng = np.random.default_rng(20260805)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

B = pd.read_csv(os.path.join(OUT, "bot_matches.csv"), parse_dates=["t_entry"])
B = B.sort_values("t_entry").reset_index(drop=True)
x = B.pnl.values
n = len(x)
print(f"{n} bot matches, total ${x.sum():+.2f}, mean ${x.mean():+.4f}, "
      f"sd ${x.std(ddof=1):.4f}")

# ----------------------------------------------------------------------
# 1. THE ARGMAX NULL
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("1. THE ARGMAX NULL")
print("=" * 78)


def argmax_stat(v):
    c = np.cumsum(v)
    k = int(np.argmax(c)) + 1          # matches up to and including the peak
    if k < 2 or k > len(v) - 2:
        return np.nan, np.nan, k
    return v[:k].mean(), v[k:].mean(), k


pre, post, k = argmax_stat(x)
obs_gap = pre - post
obs_peak = np.cumsum(x).max()
print(f"observed: peak ${obs_peak:+.2f} after {k} of {n} matches")
print(f"          mean before ${pre:+.4f}   mean after ${post:+.4f}   "
      f"gap ${obs_gap:+.4f}")

NSIM = 200_000
gaps = np.empty(NSIM)
peaks = np.empty(NSIM)
ks = np.empty(NSIM)
for i in range(NSIM):
    v = rng.permutation(x)
    a, b, kk = argmax_stat(v)
    gaps[i] = a - b if a == a else np.nan
    peaks[i] = np.cumsum(v).max()
    ks[i] = kk
ok = ~np.isnan(gaps)
print(f"\n{NSIM:,} random reorderings of the SAME 108 P&Ls "
      f"({(~ok).sum()} discarded: peak at an end)")
print(f"  gap under the null : mean ${np.nanmean(gaps):+.4f}   "
      f"median ${np.nanmedian(gaps):+.4f}   "
      f"95th pct ${np.nanpercentile(gaps, 95):+.4f}")
p_gap = (gaps[ok] >= obs_gap).mean()
print(f"  P(null gap >= observed ${obs_gap:.4f}) = {p_gap:.4f}")
print(f"  peak under the null: mean ${peaks.mean():+.2f}   "
      f"median ${np.median(peaks):+.2f}   95th pct ${np.percentile(peaks, 95):+.2f}")
p_peak = (peaks >= obs_peak).mean()
print(f"  P(null peak >= observed ${obs_peak:.2f}) = {p_peak:.4f}")
print()
print("READ THIS: the null here already contains the true total (-$6.92) and")
print("the true dispersion. It only destroys the ORDER. If p is large, the")
print("only thing the night/day story rests on is the order the matches")
print("happened to arrive in.")

# a second null: same n, same sd, but zero-mean gaussian - checks the
# statistic itself rather than this particular sample
g2 = np.empty(20000)
for i in range(20000):
    v = rng.normal(0, x.std(ddof=1), n)
    a, b, _ = argmax_stat(v)
    g2[i] = a - b
print(f"\n  same test on zero-drift gaussian noise (sd ${x.std(ddof=1):.2f}): "
      f"median gap ${np.median(g2):+.4f}, 95th ${np.percentile(g2, 95):+.4f}")
print(f"  a zero-edge process shows a positive argmax gap "
      f"{(g2 > 0).mean():.1%} of the time.")

# ----------------------------------------------------------------------
# 2. PRE-SPECIFIED CLOCK BUCKETS
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("2. CLOCK BUCKETS (split on the clock, not on the curve)")
print("=" * 78)
B["utc_hour"] = B.t_entry.dt.hour
B["night"] = np.where((B.utc_hour >= 20) | (B.utc_hour < 8), "night", "day")
B["block"] = pd.cut(B.utc_hour, [-1, 3, 7, 11, 15, 19, 23],
                    labels=["00-03", "04-07", "08-11", "12-15", "16-19", "20-23"])


def cell(g):
    v = g.pnl.values
    m = v.mean()
    se = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan
    return pd.Series({
        "n": len(v), "total": v.sum(), "mean": m, "se": se,
        "t": m / se if se and se == se else np.nan,
        "win": (v > 0).mean(),
        "contracts": g.contracts.sum(),
        "c_per_ct": v.sum() / g.contracts.sum() * 100 if g.contracts.sum() else np.nan,
        "mde_$": 2.8 * se if se == se else np.nan,
    })


from scipy import stats as st


def report(df, by, label):
    t = df.groupby(by, observed=True).apply(cell, include_groups=False)
    t["p"] = 2 * (1 - st.norm.cdf(np.abs(t["t"].fillna(0))))
    print(f"\n--- {label}")
    print(t.round(4).to_string())
    return t


t_night = report(B, "night", "NIGHT (20:00-07:59 UTC) vs DAY (08:00-19:59 UTC)")
nn = B[B.night == "night"].pnl.values
dd = B[B.night == "day"].pnl.values
w = st.ttest_ind(nn, dd, equal_var=False)
print(f"\nnight - day difference in mean per-match P&L: "
      f"${nn.mean() - dd.mean():+.4f}   Welch t={w.statistic:+.3f}  p={w.pvalue:.4f}")
print(f"  (n_night={len(nn)}, n_day={len(dd)})")

t_block = report(B, "block", "4-hour UTC block")
t_tier = report(B, "tier", "tour tier")

# tier x night
B["cellkey"] = B.tier + " | " + B.night
t_cell = report(B[B.groupby("cellkey").pnl.transform("size") >= 3],
                "cellkey", "tier x night, cells with n>=3")

# ----------------------------------------------------------------------
# BH-FDR over the whole family of bucket tests
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("BH-FDR over every bucket tested above")
print("=" * 78)
fam = pd.concat([
    t_night.assign(family="night/day"),
    t_block.assign(family="4h block"),
    t_tier.assign(family="tier"),
    t_cell.assign(family="tier x night"),
])
fam = fam[fam.n >= 3].copy()
fam = fam.sort_values("p")
m = len(fam)
fam["rank"] = np.arange(1, m + 1)
fam["bh_crit"] = fam["rank"] / m * 0.05
fam["bh_pass"] = fam.p <= fam.bh_crit
print(fam[["family", "n", "total", "mean", "se", "t", "p", "bh_crit",
           "bh_pass"]].round(4).to_string())
print(f"\nbuckets tested: {m}   BH discoveries at FDR 5%: {int(fam.bh_pass.sum())}")
pos = (fam["mean"] > 0).sum()
print(f"buckets with a positive mean: {pos} of {m}  "
      f"(chance expectation {m/2:.1f})")
p_bin = st.binomtest(int(pos), m, 0.5).pvalue
print(f"binomial p against 50/50: {p_bin:.4f}")
print("\nThe prior tennis study: 0 of 25 buckets cleared, 7 positive where 12.5")
print("were expected. Compare like with like.")

fam.to_csv(os.path.join(OUT, "buckets.csv"))
json.dump({"p_argmax_gap": float(p_gap), "p_argmax_peak": float(p_peak),
           "obs_gap": float(obs_gap), "obs_peak": float(obs_peak),
           "n_matches": int(n), "total": float(x.sum()),
           "buckets_tested": int(m), "bh_discoveries": int(fam.bh_pass.sum()),
           "buckets_positive": int(pos)},
          open(os.path.join(OUT, "t2b_summary.json"), "w"), indent=1)
