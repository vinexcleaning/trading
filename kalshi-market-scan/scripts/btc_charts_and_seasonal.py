"""Phase 5b: test whether the intra-window vol decay explains the model's
calibration bias, and produce the chart deliverables.

The three facts from btc_analysis.py fit together into one hypothesis:
  - vol is systematically 35% higher at minute 0 of each quarter-hour than at
    minute 14 (monotone decay, n=6,847 per bucket)
  - a trailing EWMA sigma therefore OVER-states the vol remaining in the window
  - and the model is correspondingly under-confident: at 5 minutes to expiry the
    0.7-0.8 bucket realises 0.85

So: scale sigma by the integral of the seasonal over the remaining window and the
calibration bias should shrink. That is a falsifiable prediction, tested here
out-of-sample on a strict time split.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.evaluate import brier, compare_to_mid, reliability  # noqa: E402
from kalshi_research.models import settlement_aware_prob_above  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NB = ROOT / "notebooks"
NB.mkdir(exist_ok=True)

plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3})


def fit_intra_window_seasonal(btc: pd.DataFrame, train_end_s: int) -> np.ndarray:
    """Relative vol multiplier for each minute-within-quarter-hour, TRAIN ONLY."""
    b = btc[btc.timestamp < train_end_s].copy()
    b["logret"] = np.log(b.close).diff()
    b = b.dropna(subset=["logret"])
    b["miq"] = ((b.timestamp // 60) % 15).astype(int)
    g = b.groupby("miq").logret.apply(lambda s: np.sqrt(np.mean(s**2)))
    return (g / g.mean()).reindex(range(15)).ffill().values


def seasonal_sigma_scale(offset_s: int, seasonal: np.ndarray) -> float:
    """RMS seasonal multiplier over the final `offset_s` seconds of a window.

    Variance adds, so we average the squared multipliers over the minutes that
    remain and take the root.
    """
    n_min = max(1, int(round(offset_s / 60)))
    mins = list(range(15 - n_min, 15))
    return float(np.sqrt(np.mean(seasonal[mins] ** 2)))


def main() -> None:
    btc = pd.read_parquet(ROOT / "data" / "external" / "BTCUSD_1m.parquet").sort_values(
        "timestamp"
    )
    panel = pd.read_parquet(REPORTS / "btc15m_decision_panel.parquet")
    panel = panel.dropna(subset=["sigma_1m_ewma"]).sort_values("close_s")

    # strict time split: fit the seasonal on the first 60%, evaluate on the last 40%
    cut = int(panel.close_s.quantile(0.60))
    seasonal = fit_intra_window_seasonal(btc, cut)
    test = panel[panel.close_s >= cut].copy()
    print(f"train ends {pd.Timestamp(cut, unit='s', tz='UTC')}  "
          f"test rows {len(test)} of {len(panel)}")
    print("intra-window seasonal multipliers (fit on train only):")
    print("  " + "  ".join(f"m{i}:{seasonal[i]:.3f}" for i in range(15)))

    rows, rel_frames = [], []
    for off, g in test.groupby("offset_s"):
        tau_min = off / 60.0
        S, K, y = g.spot.values, g.strike.values, g.y.values
        sig_flat = g.sigma_1m_ewma.values * np.sqrt(tau_min)
        scale = seasonal_sigma_scale(int(off), seasonal)
        sig_seas = sig_flat * scale

        p_flat = settlement_aware_prob_above(
            S, K, sig_flat, np.full(len(g), float(off)), 60.0
        )
        p_seas = settlement_aware_prob_above(
            S, K, sig_seas, np.full(len(g), float(off)), 60.0
        )
        c = compare_to_mid(p_seas, p_flat, y, n_boot=2000, seed=5)

        for nm, p in (("flat_sigma", p_flat), ("seasonal_sigma", p_seas)):
            r = reliability(p, y, n_bins=10)
            r["offset_s"], r["model"] = off, nm
            rel_frames.append(r)
            rows.append(
                {
                    "offset_s": off, "model": nm, "n": len(g),
                    "sigma_scale": scale if nm == "seasonal_sigma" else 1.0,
                    "brier": brier(p, y),
                    "cal_mae": float(np.average(np.abs(r.gap), weights=r.n)),
                }
            )
        rows[-1]["paired_diff_vs_flat"] = c.paired_diff_mean
        rows[-1]["ci_lo"] = c.paired_diff_ci[0]
        rows[-1]["ci_hi"] = c.paired_diff_ci[1]
        rows[-1]["improves"] = bool(c.paired_diff_ci[0] > 0)

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "btc15m_seasonal_sigma.csv", index=False)
    rel = pd.concat(rel_frames, ignore_index=True)
    rel.to_csv(REPORTS / "btc15m_seasonal_reliability.csv", index=False)

    print("\nout-of-sample: flat vs seasonal sigma")
    print(out[["offset_s", "model", "n", "sigma_scale", "brier", "cal_mae"]]
          .to_string(index=False))
    imp = out[out.model == "seasonal_sigma"]
    print("\nseasonal-sigma improvement over flat (paired, CI excludes 0 = real):")
    print(imp[["offset_s", "paired_diff_vs_flat", "ci_lo", "ci_hi", "improves"]]
          .to_string(index=False))

    # ---------------------------------------------------------------- charts
    mod = pd.read_csv(REPORTS / "btc_vol_by_minute_of_day.csv")
    dow = pd.read_csv(REPORTS / "btc_vol_by_dow.csv")
    miq = pd.read_csv(REPORTS / "btc_vol_by_minute_in_quarter.csv")

    fig, ax = plt.subplots(figsize=(11, 4))
    x = mod.minute_of_day / 60
    # per-minute is too noisy to read; a 15-min centred rolling mean shows the shape
    sm = mod.rms_logret.rolling(15, center=True, min_periods=5).mean()
    lo = mod.ci_lo.rolling(15, center=True, min_periods=5).mean()
    hi = mod.ci_hi.rolling(15, center=True, min_periods=5).mean()
    ax.plot(x, mod.rms_logret * 1e4, lw=0.4, color="#a0aec0", alpha=0.7,
            label="per-minute (raw)")
    ax.plot(x, sm * 1e4, lw=2.0, color="#2b6cb0", label="15-min rolling mean")
    ax.fill_between(x, lo * 1e4, hi * 1e4, alpha=0.25, color="#2b6cb0")
    ax.axvspan(13.5, 15.5, alpha=0.12, color="red", label="US equity open (13:30-15:30 UTC)")
    ax.set_xlabel("hour of day (UTC)")
    ax.set_ylabel("RMS 1-min log return (bp)")
    ax.set_title("BTC intraday volatility seasonality, 1-min returns, 2026-05-20 to 2026-07-30\n"
                 "peak 14:00 UTC, trough 10:00 UTC, ratio 2.10x")
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(NB / "btc_vol_seasonality_minute_of_day.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    a = axes[0]
    a.bar(miq.min_in_quarter, miq.rms_logret / miq.rms_logret.mean(), color="#805ad5")
    a.axhline(1.0, color="k", lw=0.8, ls="--")
    a.set_xlabel("minute within the quarter-hour")
    a.set_ylabel("vol relative to mean")
    a.set_title("Vol decays monotonically inside each 15-min window\n"
                "minute 0 = 1.17x, minute 14 = 0.87x (35% spread)")
    a.set_xticks(range(15))
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    b = axes[1]
    b.bar([names[int(i)] for i in dow.dow], dow.rms_logret * 1e4,
          color=["#2b6cb0"] * 5 + ["#a0aec0"] * 2)
    b.set_ylabel("RMS 1-min log return (bp)")
    b.set_title("Weekday vs weekend volatility\nThu 1.18x vs Sat 0.70x (1.69x ratio)")
    fig.tight_layout()
    fig.savefig(NB / "btc_vol_seasonality_intraweek.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, off in zip(axes, [120, 300, 600]):
        for nm, col in (("flat_sigma", "#e53e3e"), ("seasonal_sigma", "#2b6cb0")):
            s = rel[(rel.offset_s == off) & (rel.model == nm)]
            ax.plot(s.mean_pred, s.observed_freq, "o-", ms=3.5, lw=1.2, color=col,
                    label=nm.replace("_", " "))
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_title(f"{off}s to settlement")
        ax.set_xlabel("predicted probability")
        if ax is axes[0]:
            ax.set_ylabel("observed frequency")
        ax.legend(fontsize=7)
    fig.suptitle("KXBTC15M fair-value calibration, out-of-sample on real settled outcomes "
                 "(points above the diagonal = model under-confident)", fontsize=9)
    fig.tight_layout()
    fig.savefig(NB / "btc15m_calibration.png")
    plt.close(fig)

    with open(REPORTS / "btc_analysis.json") as f:
        res = json.load(f)
    d = res["direction"]
    lags = sorted(int(k) for k in d["eth_btc_xcorr_by_lag_min"])
    vals = [d["eth_btc_xcorr_by_lag_min"][str(k)] for k in lags]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    axes[0].bar(lags, vals, color=["#a0aec0" if k else "#2b6cb0" for k in lags])
    axes[0].set_xlabel("lag (minutes); positive = ETH leads BTC")
    axes[0].set_ylabel("correlation of 1-min returns")
    axes[0].set_title(f"ETH does NOT lead BTC\ncontemporaneous {vals[lags.index(0)]:.3f} "
                      f"vs best lead {d['eth_leads_btc_best_corr']:.3f}")
    acf = d["acf_returns_lag1_20"]
    band = d["acf_95pct_band"]
    axes[1].bar(range(1, 21), acf, color="#2b6cb0")
    axes[1].axhline(band, color="r", ls="--", lw=0.8, label="95% band")
    axes[1].axhline(-band, color="r", ls="--", lw=0.8)
    axes[1].set_xlabel("lag (minutes)")
    axes[1].set_ylabel("autocorrelation")
    axes[1].set_title("1-min return autocorrelation\nmax |ACF| 0.014: real but far below the cost bar")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(NB / "btc_direction_tests.png")
    plt.close(fig)

    # cost bar chart -- the central economic obstacle
    from kalshi_research.fees import breakeven_edge_cents

    ps = np.linspace(0.02, 0.98, 200)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for sp, lbl in ((0.0, "zero spread"), (1.0, "1c spread"), (2.0, "2c spread")):
        ax.plot(ps * 100, [breakeven_edge_cents(p, sp) for p in ps], label=lbl)
    ax.axvline(50, color="r", ls="--", lw=1.2,
               label="KXBTC15M entry (struck at-the-money)")
    ax.set_xlabel("contract price (cents)")
    ax.set_ylabel("breakeven edge required (pp)")
    ax.set_title("Round-trip cost bar. KXBTC15M is struck at the previous settle,\n"
                 "so entry is pinned to 50c where the quadratic fee is maximised")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(NB / "cost_bar.png")
    plt.close(fig)

    print(f"\ncharts written to {NB}")
    for p in sorted(NB.glob("*.png")):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
