"""Phase 4: weather ground-truth model, scored on real settled outcomes.

The settled markets encode their own ground truth: `expiration_value` on a settled
`KXTEMPDCH-...-Txx.xx` market IS the observed temperature at that hour. So 512
hourly settlements per city reconstruct the temperature series without needing any
external archive (NWS historical observation queries return empty over these dates).

Leak discipline: to price the settlement at hour T we use only temperatures observed
at hours strictly < T, plus the strike (known at market open). Nothing from hour T
itself is read. Asserted in code.

Models, each producing P(temp_T >= strike):
  climatology   -- hour-of-day mean and sd from a strictly earlier training window
  persistence   -- last observed temperature as the mean, empirical error sd
  persist_hod   -- persistence plus the hour-of-day change profile (the real model)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.evaluate import (  # noqa: E402
    benjamini_hochberg,
    compare_to_mid,
    reliability,
)
from kalshi_research.fees import breakeven_edge_cents  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SETTLED = ROOT / "data" / "settled"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

CITIES = ["KXTEMPDCH", "KXTEMPLAXH", "KXTEMPCHIH", "KXTEMPAUSH"]
TRAIN_FRAC = 0.6


def load_city(series: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = SETTLED / f"{series}.parquet"
    if not p.exists():
        return pd.DataFrame(), pd.DataFrame()
    d = pd.read_parquet(p)
    d["ct"] = pd.to_datetime(d.close_time, utc=True, errors="coerce")
    d["temp"] = pd.to_numeric(d.expiration_value, errors="coerce")
    d["strike"] = pd.to_numeric(d.floor_strike, errors="coerce")
    d["y"] = (d.result == "yes").astype(int)
    d["vol"] = pd.to_numeric(d.volume_fp, errors="coerce").fillna(0)
    d = d.dropna(subset=["ct", "temp", "strike"])
    d = d[d.strike_type.isin(["greater", "greater_or_equal"])]
    # the observation series: one temperature per settlement hour
    obs = (
        d.groupby("ct").temp.first().reset_index().sort_values("ct").reset_index(drop=True)
    )
    obs["hour"] = obs.ct.dt.hour
    return d.sort_values("ct").reset_index(drop=True), obs


def build_panel(markets: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    """One row per market, with features knowable strictly before its close."""
    obs = obs.reset_index(drop=True)
    # keep tz-awareness: obs.ct.values drops it and makes the subtraction below fail
    ts = obs.ct.to_numpy(dtype="datetime64[ns]")
    temps = obs.temp.values
    rows = []
    for ct, g in markets.groupby("ct"):
        j = int(np.searchsorted(ts, ct.tz_localize(None).to_datetime64()))
        if j < 3:
            continue  # need some history
        prev_temp = float(temps[j - 1])
        prev_ct = pd.Timestamp(ts[j - 1], tz="UTC")
        lag_h = (ct - prev_ct).total_seconds() / 3600.0
        hist = temps[:j]  # strictly earlier
        for _, m in g.iterrows():
            rows.append(
                {
                    "ticker": m.ticker,
                    "ct": ct,
                    "hour": ct.hour,
                    "strike": float(m.strike),
                    "y": int(m.y),
                    "temp_actual": float(m.temp),
                    "prev_temp": prev_temp,
                    "prev_ct": prev_ct,
                    "lag_hours": lag_h,
                    "n_hist": j,
                    "hist_mean": float(np.mean(hist)),
                    "hist_sd": float(np.std(hist, ddof=1)) if j > 1 else np.nan,
                    "volume": float(m.vol),
                }
            )
    p = pd.DataFrame(rows)
    if p.empty:
        return p
    # leak assertion: every feature timestamp must strictly precede the settlement
    assert (p.prev_ct < p.ct).all(), "feature observation not strictly pre-settlement"
    return p


def fit_and_score(panel: pd.DataFrame, obs: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    panel = panel.sort_values("ct").reset_index(drop=True)
    cut = panel.ct.quantile(TRAIN_FRAC)
    train, test = panel[panel.ct < cut], panel[panel.ct >= cut].copy()
    if len(test) < 200 or len(train) < 200:
        return pd.DataFrame(), {"status": "insufficient data"}

    # --- parameters fit on TRAIN only -----------------------------------
    tr_obs = obs[obs.ct < cut]
    hod = tr_obs.groupby("hour").temp.agg(["mean", "std", "size"])
    hod_mean = hod["mean"].to_dict()
    hod_sd = hod["std"].to_dict()
    global_mean = float(tr_obs.temp.mean())
    global_sd = float(tr_obs.temp.std(ddof=1))

    # persistence error sd as a function of lag, from TRAIN
    t2 = tr_obs.copy()
    t2["prev"] = t2.temp.shift(1)
    t2["lag_h"] = t2.ct.diff().dt.total_seconds() / 3600
    t2["err"] = t2.temp - t2.prev
    t2 = t2.dropna(subset=["err", "lag_h"])
    persist_sd = float(t2.err.std(ddof=1)) if len(t2) > 2 else global_sd
    # hour-of-day mean change, so persistence can follow the diurnal cycle
    hod_delta = t2.groupby(t2.ct.dt.hour).err.mean().to_dict()

    def p_above(mu: np.ndarray, sd: np.ndarray, k: np.ndarray) -> np.ndarray:
        sd = np.maximum(sd, 0.25)
        return np.clip(1.0 - norm.cdf((k - mu) / sd), 1e-6, 1 - 1e-6)

    hours = test.hour.values
    k = test.strike.values
    mu_clim = np.array([hod_mean.get(h, global_mean) for h in hours])
    sd_clim = np.array([hod_sd.get(h, global_sd) or global_sd for h in hours])
    mu_pers = test.prev_temp.values
    mu_pers_hod = mu_pers + np.array([hod_delta.get(h, 0.0) for h in hours])

    models = {
        "climatology": p_above(mu_clim, sd_clim, k),
        "persistence": p_above(mu_pers, np.full(len(test), persist_sd), k),
        "persist_hod": p_above(mu_pers_hod, np.full(len(test), persist_sd), k),
        "always_50": np.full(len(test), 0.5),
    }
    y = test.y.values

    rows, rel_frames = [], []
    base = models["climatology"]
    for name, p in models.items():
        c = compare_to_mid(p, base, y, n_boot=2000, seed=3)
        r = c.as_row(name)
        r.update(model=name, n=len(test))
        rows.append(r)
        rr = reliability(p, y, n_bins=10)
        rr["model"] = name
        rel_frames.append(rr)
    res = pd.DataFrame(rows)
    meta = {
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "split": str(cut),
        "persistence_error_sd_F": persist_sd,
        "climatology_sd_F": global_sd,
        "base_rate": float(y.mean()),
    }
    return res, meta, pd.concat(rel_frames, ignore_index=True)


def main() -> None:
    all_rows, metas = [], {}
    rel_all = []
    for city in CITIES:
        markets, obs = load_city(city)
        if markets.empty:
            print(f"{city}: no data")
            continue
        panel = build_panel(markets, obs)
        if panel.empty:
            print(f"{city}: empty panel")
            continue
        out = fit_and_score(panel, obs)
        if len(out) == 2:
            print(f"{city}: {out[1]}")
            continue
        res, meta, rel = out
        res["city"] = city
        rel["city"] = city
        all_rows.append(res)
        rel_all.append(rel)
        metas[city] = meta
        print(f"\n=== {city} ===")
        print(f"  obs hours={len(obs)}  markets={len(markets)}  panel={len(panel)}  "
              f"test={meta['n_test']}  base_rate={meta['base_rate']:.4f}")
        print(f"  persistence error sd = {meta['persistence_error_sd_F']:.2f} F, "
              f"climatology sd = {meta['climatology_sd_F']:.2f} F")
        print(res[["model", "n", "brier_model", "brier_mid", "paired_diff_mean",
                   "ci_lo", "ci_hi"]].round(5).to_string(index=False))

    if not all_rows:
        print("no results")
        return
    res = pd.concat(all_rows, ignore_index=True)
    bh = benjamini_hochberg(res.p_value.tolist(), alpha=0.05)
    res["q_value"] = bh.q_value.values
    res["survives_fdr"] = bh.reject_at_alpha.values
    res["beats_climatology"] = res.beats_mid & res.survives_fdr
    res.to_csv(REPORTS / "weather_model.csv", index=False)
    pd.concat(rel_all, ignore_index=True).to_csv(
        REPORTS / "weather_reliability.csv", index=False
    )

    print("\n" + "=" * 78)
    print("SUMMARY: persistence vs climatology, out-of-sample, all cities")
    print("=" * 78)
    piv = res.pivot_table(index="city", columns="model", values="brier_model")
    print(piv.round(5).to_string())
    print("\nmodels beating climatology after FDR:")
    w = res[res.beats_climatology]
    print(w[["city", "model", "brier_model", "brier_mid", "ci_lo", "ci_hi", "q_value"]]
          .round(5).to_string(index=False) if len(w) else "  none")

    # liquidity reality check -- the question that actually decides this family
    print("\n" + "=" * 78)
    print("LIQUIDITY: can any of this be traded?")
    print("=" * 78)
    for city in CITIES:
        markets, _ = load_city(city)
        if markets.empty:
            continue
        v = markets["vol"]
        print(f"  {city}: median volume={v.median():.0f} p90={v.quantile(.9):.0f} "
              f"max={v.max():.0f} | markets with 0 volume: {100*(v==0).mean():.1f}%")
    print(f"\n  breakeven at 10c with a 1c spread: "
          f"{breakeven_edge_cents(0.10, 1.0):.2f}c")
    print(f"  breakeven at 50c with a 1c spread: "
          f"{breakeven_edge_cents(0.50, 1.0):.2f}c")

    (REPORTS / "weather_model.json").write_text(
        json.dumps({"per_city": metas}, indent=1, default=str)
    )
    print(f"\nwrote {REPORTS/'weather_model.csv'}")


if __name__ == "__main__":
    main()
