"""W1 -- does the weather model beat the MARKET's price? The gate GO_NO_GO left empty.

Design fixed in advance: docs/PREREGISTRATION_WEATHER_VS_MID.md, committed at
9db1a5a before any model score, edge or settled outcome touched a price.

Everything here follows that file:
  * anchor = the market's OPEN (it lives exactly one hour)
  * features use ONLY temperatures observed at hours strictly BEFORE the open,
    which is one observation stricter than weather_model.py's rule
  * price = yes_ask_open of the candle whose end_period_ts == close_ts.
    Never a mid -- there is no bid to average with (0 of 248 two-sided at open),
    and inventing one is T008, the retraction that turned +24.6% into -30.9%
  * cost = fee(ask) + slippage, fee from common/kalshi_fees.py and nowhere else
  * UNIT OF OBSERVATION IS THE SETTLEMENT HOUR, never the market -- K003 called
    a ten-strike ladder ten markets and its intervals were ~3x too tight
  * one trade per hour, at the largest qualifying edge
  * controls N1 climatology / N2 shuffled outcomes / N3 always-50 gate the run
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

SETTLED = ROOT / "data" / "settled"
CANDLES = ROOT / "data" / "weather_candles.db"
REPORTS = ROOT / "reports"

SERIES = "KXTEMPDCH"
TRAIN_FRAC = 0.60          # identical to weather_model.py / K002
HOLDOUT_FRAC = 0.30        # newest 30% of settlement hours, SEALED
SLIPPAGES = [0.0, 0.5, 1.0, 2.0]
N_BOOT = 4000
N_PERM = 200
SEED = 20260806


# ----------------------------------------------------------------- panel ----

def load(series: str):
    d = pd.read_parquet(SETTLED / f"{series}.parquet")
    d["ct"] = pd.to_datetime(d.close_time, utc=True, errors="coerce")
    d["ot"] = pd.to_datetime(d.open_time, utc=True, errors="coerce")
    d["temp"] = pd.to_numeric(d.expiration_value, errors="coerce")
    d["strike"] = pd.to_numeric(d.floor_strike, errors="coerce")
    d["y"] = (d.result == "yes").astype(int)
    d = d.dropna(subset=["ct", "ot", "temp", "strike"])
    d = d[d.strike_type.isin(["greater", "greater_or_equal"])]
    obs = (d.groupby("ct").temp.first().reset_index()
             .sort_values("ct").reset_index(drop=True))
    obs["hour"] = obs.ct.dt.hour
    return d.sort_values("ct").reset_index(drop=True), obs


def load_asks(series: str) -> pd.DataFrame:
    con = sqlite3.connect(f"file:{CANDLES.as_posix()}?mode=ro", uri=True)
    # PROVENANCE CANARY (preregistration 2.3): the ask must come from the candle
    # whose period ENDS at close. Every market also has a post-settlement candle
    # reading 0 bid / 100 ask; taking it would be reading the answer.
    a = pd.read_sql(
        "select ticker, yes_ask_open, yes_bid_open, yes_ask_close, volume_fp "
        "from wcandles where series=? and end_period_ts = close_ts", con,
        params=(series,))
    n_post = con.execute(
        "select count(*) from wcandles where series=? and end_period_ts > close_ts",
        (series,)).fetchone()[0]
    con.close()
    a["ask_c"] = a.yes_ask_open * 100.0
    a["bid_c"] = a.yes_bid_open * 100.0
    # BOTH tables carry `volume_fp` and a merge would silently suffix them _x/_y.
    # That is C024's renamed-field trap in a new costume: the first version of
    # this script read the WRONG one and crashed, which is the lucky outcome --
    # had the names differed by suffix only in one direction it would have read
    # the settled parquet's lifetime volume as if it were the entry-hour volume.
    a = a.rename(columns={"volume_fp": "hour_volume_fp"})
    print(f"   ask candles at end_period_ts == close_ts : {len(a):,}")
    print(f"   post-settlement candles EXCLUDED         : {n_post:,}")
    return a


def build(series: str):
    mk, obs = load(series)
    asks = load_asks(series)
    mk = mk.merge(asks[["ticker", "ask_c", "bid_c", "hour_volume_fp"]],
                  on="ticker", how="inner")

    ts = obs.ct.to_numpy(dtype="datetime64[ns]")
    temps = obs.temp.values
    rows = []
    for ct, g in mk.groupby("ct"):
        # LEAK RULE, stricter than K002's: strictly before the market's OPEN,
        # and the market opens one hour before it closes. So the newest usable
        # observation is two hours before settlement, not one.
        j = int(np.searchsorted(ts, ct.tz_localize(None).to_datetime64()))
        if j < 4:
            continue
        prev_temp = float(temps[j - 2])          # <-- j-2, not j-1
        prev_ct = pd.Timestamp(ts[j - 2], tz="UTC")
        open_t = g.ot.iloc[0]
        assert prev_ct < open_t, "feature observation not strictly pre-OPEN"
        hist = temps[: j - 1]
        for _, m in g.iterrows():
            rows.append({"ticker": m.ticker, "ct": ct, "hour": int(ct.hour),
                         "strike": float(m.strike), "y": int(m.y),
                         "ask_c": float(m.ask_c), "bid_c": float(m.bid_c),
                         "prev_temp": prev_temp, "n_hist": j,
                         "hist_mean": float(np.mean(hist)),
                         "vol": float(m.hour_volume_fp or 0)})
    p = pd.DataFrame(rows)
    return p, obs


def fit_models(panel: pd.DataFrame, obs: pd.DataFrame):
    """Parameters from the TRAIN window only; never refit."""
    cut = panel.ct.quantile(TRAIN_FRAC)
    tr = obs[obs.ct < cut]
    hod = tr.groupby("hour").temp.agg(["mean", "std"])
    hod_mean, hod_sd = hod["mean"].to_dict(), hod["std"].to_dict()
    gmean = float(tr.temp.mean())
    gsd = float(tr.temp.std(ddof=1))

    # TWO-HOUR persistence error, because the anchor is two observations back.
    # weather_model.py fits a ONE-hour error sd; using it here would understate
    # the model's own uncertainty and manufacture confident wrong probabilities.
    t2 = tr.copy()
    t2["prev2"] = t2.temp.shift(2)
    t2["err"] = t2.temp - t2.prev2
    t2 = t2.dropna(subset=["err"])
    persist_sd = float(t2.err.std(ddof=1)) if len(t2) > 2 else gsd
    hod_delta = t2.groupby(t2.ct.dt.hour).err.mean().to_dict()
    return {"cut": cut, "hod_mean": hod_mean, "hod_sd": hod_sd, "gmean": gmean,
            "gsd": gsd, "persist_sd": persist_sd, "hod_delta": hod_delta}


def probs(panel: pd.DataFrame, f: dict) -> dict:
    def p_above(mu, sd, k):
        sd = np.maximum(sd, 0.25)
        return np.clip(1.0 - norm.cdf((k - mu) / sd), 1e-6, 1 - 1e-6)

    h, k = panel.hour.values, panel.strike.values
    mu_c = np.array([f["hod_mean"].get(x, f["gmean"]) for x in h])
    sd_c = np.array([f["hod_sd"].get(x) or f["gsd"] for x in h])
    mu_p = panel.prev_temp.values + np.array(
        [f["hod_delta"].get(x, 0.0) for x in h])
    return {
        "persist_hod": p_above(mu_p, np.full(len(panel), f["persist_sd"]), k),
        "climatology": p_above(mu_c, sd_c, k),          # N1
        "always_50": np.full(len(panel), 0.5),          # N3
    }


# ------------------------------------------------------------- the trade ----

def run_cell(panel, p, slip, y_override=None):
    """One trade per settlement hour, at the largest qualifying edge."""
    y = panel.y.values if y_override is None else y_override
    ask = panel.ask_c.values
    fee = np.array([float(fee_rate_cents(round(a))) for a in ask])
    edge = 100.0 * p - ask
    net = edge - fee - slip
    d = pd.DataFrame({"ct": panel.ct.values, "net": net, "ask": ask,
                      "fee": fee, "y": y})
    d = d[d.net > 0]
    if d.empty:
        return None
    best = d.sort_values("net", ascending=False).groupby("ct", as_index=False).first()
    pnl = np.where(best.y.values == 1, 100.0 - best.ask.values, -best.ask.values) \
        - best.fee.values - slip
    return {"hours": len(best), "pnl": pnl, "ct": best.ct.values,
            "ask_median": float(np.median(best.ask.values))}


def boot(pnl, rng):
    n = len(pnl)
    if n < 2:
        return (np.nan, np.nan)
    idx = rng.integers(0, n, size=(N_BOOT, n))
    m = pnl[idx].mean(axis=1)
    return (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


def main():
    rng = np.random.default_rng(SEED)
    REPORTS.mkdir(exist_ok=True)
    print(f"== BUILD  {SERIES}")
    panel, obs = build(SERIES)
    if panel.empty:
        print("   empty panel — stop")
        return
    quotable = panel[(panel.ask_c > 0) & (panel.ask_c < 100)].copy()
    print(f"   markets with a usable ask at OPEN : {len(quotable):,} of {len(panel):,}")
    print(f"   settlement hours represented      : {quotable.ct.nunique():,}")
    print(f"   two-sided at open (bid>0)         : {int((quotable.bid_c>0).sum()):,}")

    # ---- holdout seal, before anything is scored
    hours = np.sort(quotable.ct.unique())
    n_hold = int(len(hours) * HOLDOUT_FRAC)
    hold_hours = set(hours[len(hours) - n_hold:])
    train = quotable[~quotable.ct.isin(hold_hours)].copy()
    hold = quotable[quotable.ct.isin(hold_hours)].copy()
    hp = REPORTS / "weather_holdout_hours.json"
    if not hp.exists():
        hp.write_text(json.dumps(
            {"sealed_utc": "2026-08-06", "series": SERIES,
             "n_hours": n_hold,
             "hours": [str(pd.Timestamp(h)) for h in sorted(hold_hours)]},
            indent=1), encoding="utf-8")
        print(f"   holdout SEALED: {n_hold} hours -> {hp.name}")
    print(f"   train hours {train.ct.nunique()} / holdout hours {hold.ct.nunique()}")

    f = fit_models(train, obs)
    print(f"   two-hour persistence error sd = {f['persist_sd']:.2f} F  "
          f"(climatology sd {f['gsd']:.2f} F)")

    # ---- leak canary
    ex = train[(train.ask_c <= 2) | (train.ask_c >= 98)]
    frac = len(ex) / max(len(train), 1)
    corr = float((ex.y.values == (ex.ask_c.values >= 98)).mean()) if len(ex) else 0.0
    verdict = "VOID" if (frac > 0.01 and corr >= 0.99) else "PASS"
    print(f"\n== LEAK CANARY  extreme asks {100*frac:.2f}% of entries, "
          f"{100*corr:.1f}% correct -> {verdict}")
    if verdict == "VOID":
        print("   the gate refuses to print a result. Stop.")
        return

    # ---- the grid
    P = probs(train, f)
    print(f"\n== TRAIN GRID  (unit = settlement hour; CIs bootstrap hours)")
    print(f"   {'model':13} {'slip':>5} {'hours':>6} {'mean net':>10} "
          f"{'95% CI':>22} {'med ask':>8}")
    results = {}
    for name, p in P.items():
        for slip in SLIPPAGES:
            r = run_cell(train, p, slip)
            if r is None:
                print(f"   {name:13} {slip:>5} {'0':>6}   no qualifying trade")
                results[f"{name}|{slip}"] = {"hours": 0}
                continue
            lo, hi = boot(r["pnl"], rng)
            mu = float(r["pnl"].mean())
            print(f"   {name:13} {slip:>5} {r['hours']:>6} {mu:>+9.2f}c  "
                  f"[{lo:>+7.2f},{hi:>+7.2f}] {r['ask_median']:>7.1f}c")
            results[f"{name}|{slip}"] = {
                "hours": r["hours"], "mean_net_c": round(mu, 4),
                "ci": [round(lo, 4), round(hi, 4)],
                "median_ask_c": r["ask_median"]}

    # ---- naive benchmarks
    print(f"\n== NAIVE BENCHMARKS  (no model at all)")
    for label, sub in (("B0-ALLASK", train),
                       ("B0-CHEAP<20c", train[train.ask_c < 20])):
        if sub.empty:
            continue
        fee = np.array([float(fee_rate_cents(round(a))) for a in sub.ask_c.values])
        pnl = np.where(sub.y.values == 1, 100.0 - sub.ask_c.values,
                       -sub.ask_c.values) - fee - 1.0
        g = pd.DataFrame({"ct": sub.ct.values, "pnl": pnl}).groupby("ct").pnl.mean()
        lo, hi = boot(g.values, rng)
        print(f"   {label:13} hours {len(g):>5}  {g.mean():>+8.2f}c  "
              f"[{lo:>+7.2f},{hi:>+7.2f}]")
        results[label] = {"hours": len(g), "mean_net_c": round(float(g.mean()), 4),
                          "ci": [round(lo, 4), round(hi, 4)]}

    # ---- N2 permutation null
    print(f"\n== N2  PERMUTATION NULL  ({N_PERM} draws, outcomes shuffled within "
          f"hour-of-day x 5c ask bucket)")
    base = run_cell(train, P["persist_hod"], 1.0)
    if base is not None:
        t2 = train.copy()
        t2["bucket"] = list(zip(t2.hour, (t2.ask_c // 5).astype(int)))
        null_means = []
        for _ in range(N_PERM):
            ys = t2.groupby("bucket").y.transform(
                lambda s: s.sample(frac=1.0, random_state=int(rng.integers(1e9))).values)
            r = run_cell(t2, P["persist_hod"], 1.0, y_override=ys.values)
            if r is not None:
                null_means.append(float(r["pnl"].mean()))
        nm = np.array(null_means)
        real = float(base["pnl"].mean())
        pval = float((np.abs(nm) >= abs(real)).mean()) if len(nm) else np.nan
        print(f"   real {real:+.2f}c   null mean {nm.mean():+.2f}c  "
              f"sd {nm.std():.2f}c  p90 {np.percentile(nm,90):+.2f}c")
        print(f"   two-sided permutation p = {pval:.4f}")
        results["N2_permutation"] = {"real_c": round(real, 4),
                                     "null_mean_c": round(float(nm.mean()), 4),
                                     "null_sd_c": round(float(nm.std()), 4),
                                     "p": round(pval, 5), "draws": len(nm)}

    (REPORTS / "weather_vs_ask.json").write_text(
        json.dumps(results, indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/weather_vs_ask.json")
    print("HOLDOUT NOT TOUCHED — it is opened only if a train cell survives "
          "everything, per the pre-registration.")


if __name__ == "__main__":
    main()
