"""Phase 5: BTC deep dive.

Volatility work, direction work, and a fair-value model scored against the 6,271
real settled KXBTC15M outcomes.

Leak discipline: the decision anchor is always the close of a 1-minute candle that
had already closed at or before the decision timestamp, and the strike is the
previous window's settlement, which is knowable at window open. No field that
postdates the decision is ever read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.evaluate import (  # noqa: E402
    benjamini_hochberg,
    brier,
    compare_to_mid,
    log_loss,
    reliability,
)
from kalshi_research.fees import breakeven_edge_cents  # noqa: E402
from kalshi_research.models import (  # noqa: E402
    bipower_variation,
    ewma_vol,
    garman_klass_vol,
    gbm_prob_above,
    har_rv_design,
    parkinson_vol,
    rogers_satchell_vol,
    settlement_aware_prob_above,
    student_t_prob_above,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NB = ROOT / "notebooks"
REPORTS.mkdir(exist_ok=True)
NB.mkdir(exist_ok=True)

WINDOW_S = 900.0
AVG_WINDOW_S = 60.0
DECISION_OFFSETS_S = [780, 600, 300, 120, 60]  # seconds before close

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def to_unix_s(s: pd.Series) -> np.ndarray:
    """Datetime series -> int64 unix seconds, independent of pandas time resolution.

    `.astype("int64") // 10**9` is wrong whenever the dtype is datetime64[us]
    rather than [ns] -- pandas 2.x preserves microsecond resolution when parsing
    ISO strings, which silently produced 1785393 instead of 1785393600 and made
    every price lookup miss.
    """
    return ((s - EPOCH).dt.total_seconds()).to_numpy(dtype="int64")


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    btc = pd.read_parquet(ROOT / "data" / "external" / "BTCUSD_1m.parquet")
    eth = pd.read_parquet(ROOT / "data" / "external" / "ETHUSD_1m.parquet")
    mk = pd.read_parquet(ROOT / "data" / "settled" / "KXBTC15M.parquet")
    for d in (btc, eth):
        d.sort_values("timestamp", inplace=True)
        d.reset_index(drop=True, inplace=True)
    mk["ev"] = pd.to_numeric(mk.expiration_value, errors="coerce")
    mk["fs"] = pd.to_numeric(mk.floor_strike, errors="coerce")
    mk["close_ts"] = pd.to_datetime(mk.close_time, utc=True, errors="coerce")
    mk = mk.dropna(subset=["ev", "fs", "close_ts"]).sort_values("close_ts")
    mk["y"] = (mk.result == "yes").astype(int)
    return btc, eth, mk.reset_index(drop=True)


# ------------------------------------------------------------------ vol work


def vol_section(btc: pd.DataFrame) -> dict:
    out: dict = {}
    b = btc.copy()
    b["logret"] = np.log(b.close).diff()
    b = b.dropna(subset=["logret"])
    r = b.logret.values

    # realized vol at several horizons, annualisation-free (per-horizon sigma)
    per_min = float(np.std(r, ddof=1))
    out["sigma_per_1m"] = per_min
    for h, name in ((5, "5m"), (15, "15m"), (60, "1h"), (1440, "1d")):
        agg = b.logret.rolling(h).sum().dropna()
        out[f"sigma_per_{name}"] = float(agg.std(ddof=1))
    out["sigma_15m_implied_from_1m_sqrt_rule"] = per_min * np.sqrt(15)
    out["variance_ratio_15m_vs_1m"] = (
        out["sigma_per_15m"] / out["sigma_15m_implied_from_1m_sqrt_rule"]
    )

    # range-based estimators on 15-minute bars
    b["bucket"] = b.timestamp // 900
    bars = b.groupby("bucket").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"),
        ts=("ts", "first"), n=("close", "size"),
    )
    bars = bars[bars.n >= 10]
    out["n_15m_bars"] = int(len(bars))
    out["parkinson_15m"] = float(np.nanmean(parkinson_vol(bars.high, bars.low)))
    out["garman_klass_15m"] = float(
        np.nanmean(garman_klass_vol(bars.open, bars.high, bars.low, bars.close))
    )
    out["rogers_satchell_15m"] = float(
        np.nanmean(rogers_satchell_vol(bars.open, bars.high, bars.low, bars.close))
    )
    out["close_to_close_15m"] = float(out["sigma_per_15m"])

    # jumps: realized variance vs jump-robust bipower variation, per 15m bar
    jump_flags, rv_bp = [], []
    for _, g in b.groupby("bucket"):
        rr = g.logret.values
        if len(rr) < 10:
            continue
        rv = float(np.sum(rr**2))
        bp = bipower_variation(rr)
        rv_bp.append((rv, bp))
        jump_flags.append(bool(np.isfinite(bp) and rv > 1.5 * bp))
    out["n_bars_jump_tested"] = len(jump_flags)
    out["p_jump_in_15m_window"] = float(np.mean(jump_flags)) if jump_flags else np.nan

    # return distribution and tail behaviour
    fifteen = b.logret.rolling(15).sum().dropna().values
    out["kurtosis_15m_excess"] = float(pd.Series(fifteen).kurtosis())
    out["skew_15m"] = float(pd.Series(fifteen).skew())
    from scipy.stats import t as tdist

    dof, loc, scale = tdist.fit(fifteen)
    out["student_t_dof"] = float(dof)
    z = (fifteen - np.mean(fifteen)) / np.std(fifteen, ddof=1)
    for q in (0.001, 0.01, 0.05):
        from scipy.stats import norm

        out[f"tail_ratio_q{q}"] = float(np.mean(z < norm.ppf(q)) / q)
    return out


def vol_seasonality(btc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    b = btc.copy()
    b["logret"] = np.log(b.close).diff()
    b = b.dropna(subset=["logret"])
    b["minute_of_day"] = b.ts.dt.hour * 60 + b.ts.dt.minute
    b["dow"] = b.ts.dt.dayofweek
    b["min_in_quarter"] = b.ts.dt.minute % 15

    def agg(key: str) -> pd.DataFrame:
        g = b.groupby(key).logret
        d = pd.DataFrame({"n": g.size(), "rms_logret": g.apply(lambda s: np.sqrt(np.mean(s**2)))})
        # bootstrap-free CI on the RMS via the chi-square approximation
        d["se"] = d.rms_logret / np.sqrt(2 * d.n)
        d["ci_lo"] = d.rms_logret - 1.96 * d.se
        d["ci_hi"] = d.rms_logret + 1.96 * d.se
        d["vol_ratio_to_mean"] = d.rms_logret / d.rms_logret.mean()
        return d.reset_index()

    return agg("minute_of_day"), agg("dow"), agg("min_in_quarter")


def direction_section(btc: pd.DataFrame, eth: pd.DataFrame) -> dict:
    out: dict = {}
    b = btc.copy()
    b["logret"] = np.log(b.close).diff()
    r = b.logret.dropna().values

    # autocorrelation of returns and of signs
    acf_r, acf_s = [], []
    s = np.sign(r)
    for lag in range(1, 21):
        acf_r.append(float(np.corrcoef(r[:-lag], r[lag:])[0, 1]))
        acf_s.append(float(np.corrcoef(s[:-lag], s[lag:])[0, 1]))
    out["acf_returns_lag1_20"] = [round(x, 5) for x in acf_r]
    out["acf_signs_lag1_20"] = [round(x, 5) for x in acf_s]
    out["max_abs_acf_returns"] = float(np.max(np.abs(acf_r)))
    out["acf_95pct_band"] = float(1.96 / np.sqrt(len(r)))
    out["n_acf_lags_outside_band"] = int(
        np.sum(np.abs(acf_r) > 1.96 / np.sqrt(len(r)))
    )

    # sign persistence at several horizons
    persist = {}
    for h in (1, 5, 15):
        agg = b.logret.rolling(h).sum().dropna().values
        sg = np.sign(agg[::h])
        sg = sg[sg != 0]
        if len(sg) > 10:
            persist[f"{h}m"] = float(np.mean(sg[1:] == sg[:-1]))
    out["sign_persistence"] = persist

    # ETH -> BTC lead-lag cross-correlation on 1-minute returns
    m = pd.merge(
        b[["timestamp", "logret"]].rename(columns={"logret": "btc"}),
        eth.assign(logret=np.log(eth.close).diff())[["timestamp", "logret"]].rename(
            columns={"logret": "eth"}
        ),
        on="timestamp", how="inner",
    ).dropna()
    xc = {}
    for lag in range(-10, 11):
        if lag < 0:
            a, c = m.btc.values[-lag:], m.eth.values[: len(m) + lag]
        elif lag > 0:
            a, c = m.btc.values[: len(m) - lag], m.eth.values[lag:]
        else:
            a, c = m.btc.values, m.eth.values
        xc[lag] = float(np.corrcoef(a, c)[0, 1])
    out["eth_btc_xcorr_by_lag_min"] = {k: round(v, 5) for k, v in xc.items()}
    out["eth_btc_xcorr_at_lag0"] = xc[0]
    best_lead = max((k for k in xc if k > 0), key=lambda k: abs(xc[k]))
    out["eth_leads_btc_best_lag_min"] = best_lead
    out["eth_leads_btc_best_corr"] = xc[best_lead]
    out["eth_btc_lead_beats_contemporaneous"] = bool(abs(xc[best_lead]) > abs(xc[0]))
    out["n_minutes_matched"] = int(len(m))
    return out


# ------------------------------------------------ fair value on real outcomes


def build_decision_panel(btc: pd.DataFrame, mk: pd.DataFrame) -> pd.DataFrame:
    """One row per (settled market x decision offset), leak-audited by construction."""
    px = btc.set_index("timestamp")[["close", "high", "low", "open"]]
    ts_index = px.index.values

    b = btc.copy()
    b["logret"] = np.log(b.close).diff()
    b["ewma"] = ewma_vol(b.logret.values, lam=0.94)
    ewma_map = dict(zip(b.timestamp.values, b.ewma.values))
    # trailing realized sigma over the previous 60 minutes, strictly backward-looking
    b["rv60"] = b.logret.rolling(60).apply(lambda s: np.sqrt(np.mean(s**2)), raw=True)
    rv60_map = dict(zip(b.timestamp.values, b.rv60.values))

    rows = []
    close_s = to_unix_s(mk.close_ts)
    if not ((close_s >= ts_index.min()) & (close_s <= ts_index.max())).any():
        raise RuntimeError(
            f"no temporal overlap: markets {close_s.min()}..{close_s.max()} vs "
            f"candles {ts_index.min()}..{ts_index.max()}"
        )
    for i, (_, m) in enumerate(mk.iterrows()):
        c = close_s[i]
        for off in DECISION_OFFSETS_S:
            dt = c - off
            # the candle that has ALREADY closed at the decision instant
            anchor = dt - (dt % 60) - 60
            j = np.searchsorted(ts_index, anchor)
            if j >= len(ts_index) or ts_index[j] != anchor:
                continue
            spot = float(px.close.values[j])
            sig1 = ewma_map.get(anchor, np.nan)
            rv = rv60_map.get(anchor, np.nan)
            rows.append(
                {
                    "ticker": m.ticker,
                    "close_s": c,
                    "decision_s": dt,
                    "anchor_s": anchor,
                    "offset_s": off,
                    "spot": spot,
                    "strike": float(m.fs),
                    "settle": float(m.ev),
                    "y": int(m.y),
                    "sigma_1m_ewma": float(sig1) if np.isfinite(sig1) else np.nan,
                    "sigma_1m_rv60": float(rv) if np.isfinite(rv) else np.nan,
                    "volume": pd.to_numeric(m.volume_fp, errors="coerce"),
                    "hour_utc": pd.Timestamp(c, unit="s", tz="UTC").hour,
                    "dow": pd.Timestamp(c, unit="s", tz="UTC").dayofweek,
                }
            )
    p = pd.DataFrame(rows)
    # leak assertion: the price anchor must strictly precede the decision, and the
    # decision must strictly precede settlement.
    assert (p.anchor_s < p.decision_s).all(), "price anchor not strictly pre-decision"
    assert (p.decision_s < p.close_s).all(), "decision not strictly pre-settlement"
    return p


def fair_value_section(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, rel_rows = [], []
    for off, g in panel.groupby("offset_s"):
        g = g.dropna(subset=["sigma_1m_ewma", "sigma_1m_rv60"]).copy()
        if len(g) < 200:
            continue
        tau_min = off / 60.0
        S, K, y = g.spot.values, g.strike.values, g.y.values

        models = {
            "always_50": np.full(len(g), 0.5),
            "gbm_ewma": gbm_prob_above(S, K, g.sigma_1m_ewma.values * np.sqrt(tau_min)),
            "gbm_rv60": gbm_prob_above(S, K, g.sigma_1m_rv60.values * np.sqrt(tau_min)),
            "settlement_aware_ewma": settlement_aware_prob_above(
                S, K, g.sigma_1m_ewma.values * np.sqrt(tau_min),
                np.full(len(g), float(off)), AVG_WINDOW_S,
            ),
            "student_t_ewma": student_t_prob_above(
                S, K, g.sigma_1m_ewma.values * np.sqrt(tau_min), dof=4
            ),
            "momentum": np.clip(0.5 + 50.0 * (S / K - 1.0), 0.01, 0.99),
            "reversal": np.clip(0.5 - 50.0 * (S / K - 1.0), 0.01, 0.99),
        }
        base = models["always_50"]
        for name, p in models.items():
            c = compare_to_mid(p, base, y, n_boot=2000, seed=7)
            r = c.as_row(f"KXBTC15M@{off}s::{name}")
            r.update(offset_s=off, model=name, n_rows=len(g),
                     base_rate=float(y.mean()))
            rows.append(r)
            if name in ("gbm_ewma", "settlement_aware_ewma"):
                rr = reliability(p, y, n_bins=10)
                rr["offset_s"] = off
                rr["model"] = name
                rel_rows.append(rr)
    return pd.DataFrame(rows), (
        pd.concat(rel_rows, ignore_index=True) if rel_rows else pd.DataFrame()
    )


def main() -> None:
    btc, eth, mk = load()
    print(f"BTC candles: {len(btc)}  ETH: {len(eth)}  settled KXBTC15M: {len(mk)}")
    print(f"market window: {mk.close_ts.min()} -> {mk.close_ts.max()}")

    res: dict = {"n_btc_candles": len(btc), "n_settled_markets": len(mk)}

    print("\n[1/5] volatility estimators and distribution")
    res["vol"] = vol_section(btc)
    for k, v in res["vol"].items():
        if isinstance(v, float):
            print(f"    {k:42s} {v:.6g}")

    print("\n[2/5] volatility seasonality")
    mod, dow, miq = vol_seasonality(btc)
    mod.to_csv(REPORTS / "btc_vol_by_minute_of_day.csv", index=False)
    dow.to_csv(REPORTS / "btc_vol_by_dow.csv", index=False)
    miq.to_csv(REPORTS / "btc_vol_by_minute_in_quarter.csv", index=False)
    hr = mod.copy()
    hr["hour"] = hr.minute_of_day // 60
    byhr = hr.groupby("hour").rms_logret.mean()
    print("    vol ratio by UTC hour (1.0 = daily mean):")
    for h, v in (byhr / byhr.mean()).items():
        bar = "#" * int(round(v * 30))
        print(f"      {h:02d}:00  {v:5.3f}  {bar}")
    res["vol_seasonality"] = {
        "peak_hour_utc": int((byhr / byhr.mean()).idxmax()),
        "trough_hour_utc": int((byhr / byhr.mean()).idxmin()),
        "peak_to_trough_ratio": float(byhr.max() / byhr.min()),
        "dow_peak": int(dow.loc[dow.rms_logret.idxmax(), "dow"]),
        "dow_peak_to_trough_ratio": float(dow.rms_logret.max() / dow.rms_logret.min()),
        "minute_in_quarter_spread_pct": float(
            100 * (miq.rms_logret.max() / miq.rms_logret.min() - 1)
        ),
    }
    print(f"    minute-within-quarter-hour spread: "
          f"{res['vol_seasonality']['minute_in_quarter_spread_pct']:.2f}% "
          f"(boundary effect at :00/:15/:30/:45)")
    print(f"    day-of-week peak/trough ratio: "
          f"{res['vol_seasonality']['dow_peak_to_trough_ratio']:.3f}")

    print("\n[3/5] direction tests (expect null)")
    res["direction"] = direction_section(btc, eth)
    d = res["direction"]
    print(f"    max |ACF| of 1m returns over lags 1-20: {d['max_abs_acf_returns']:.5f} "
          f"(95% band {d['acf_95pct_band']:.5f})")
    print(f"    lags outside band: {d['n_acf_lags_outside_band']}/20")
    print(f"    sign persistence: {d['sign_persistence']}")
    print(f"    ETH/BTC contemporaneous corr: {d['eth_btc_xcorr_at_lag0']:.4f}")
    print(f"    best ETH lead lag {d['eth_leads_btc_best_lag_min']}m "
          f"corr {d['eth_leads_btc_best_corr']:.4f}  "
          f"beats contemporaneous: {d['eth_btc_lead_beats_contemporaneous']}")

    print("\n[4/5] fair-value panel on real settled outcomes")
    panel = build_decision_panel(btc, mk)
    panel.to_parquet(REPORTS / "btc15m_decision_panel.parquet", index=False)
    print(f"    panel rows: {len(panel)} "
          f"({panel.ticker.nunique()} markets x {panel.offset_s.nunique()} offsets)")
    print("    leak assertions passed: anchor < decision < settlement")

    fv, rel = fair_value_section(panel)
    if not fv.empty:
        bh = benjamini_hochberg(fv.p_value.tolist(), alpha=0.05)
        fv["q_value"] = bh.q_value.values
        fv["survives_fdr"] = bh.reject_at_alpha.values
        fv["beats_coinflip_after_fdr"] = fv.beats_mid & fv.survives_fdr
        fv.to_csv(REPORTS / "btc15m_fair_value.csv", index=False)
        if not rel.empty:
            rel.to_csv(REPORTS / "btc15m_reliability.csv", index=False)
        cols = ["offset_s", "model", "n_rows", "brier_model", "brier_mid",
                "paired_diff_mean", "ci_lo", "ci_hi", "q_value",
                "beats_coinflip_after_fdr"]
        print("\n    model vs coinflip baseline (brier_mid column = always_50):")
        print(fv[cols].to_string(index=False))
        res["n_models_beating_coinflip"] = int(fv.beats_coinflip_after_fdr.sum())

    print("\n[5/5] the cost bar for this contract")
    # KXBTC15M is struck at-the-money, so entry sits where the fee is maximised
    bar = {
        "breakeven_at_50c_zero_spread": breakeven_edge_cents(0.50, 0.0),
        "breakeven_at_50c_1c_spread": breakeven_edge_cents(0.50, 1.0),
        "breakeven_at_50c_2c_spread": breakeven_edge_cents(0.50, 2.0),
    }
    res["cost_bar"] = bar
    for k, v in bar.items():
        print(f"    {k:36s} {v:.2f}c  => need {v:.2f} pp of edge")

    (REPORTS / "btc_analysis.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {REPORTS/'btc_analysis.json'}")


if __name__ == "__main__":
    main()
