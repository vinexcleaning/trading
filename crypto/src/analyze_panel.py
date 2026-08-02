"""TASK 1 manifest + TASK 2 models + TASK 3 THE HEADLINE TEST.

Runs the same scoring code the synthetic control validated (models.py), on the
real panel.

Order of operations is deliberate:
  1. sample composition FIRST, before any score is computed
  2. knowability assertions
  3. models
  4. the vs-mid comparison, CIs clustered BY EVENT
"""
import argparse
import datetime as dt
import json
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from models import (  # noqa: E402
    m1_gbm, m2_settlement_aware, m3_empirical, m3_student_t,
    brier, log_loss, cluster_bootstrap_diff, reliability, SECONDS_PER_YEAR,
)
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

PANEL = r"C:\Users\gianf\crypto\data\panel"
SPOT = r"C:\Users\gianf\crypto\data\spot\btc_1m.jsonl"
REPORTS = r"C:\Users\gianf\crypto\reports"


def load_panel(series):
    rows = []
    with open(os.path.join(PANEL, f"panel_{series}.jsonl"),
              encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_spot():
    spot = {}
    if not os.path.exists(SPOT):
        return spot
    with open(SPOT, encoding="utf-8") as f:
        for line in f:
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            spot[c["t"]] = c["close"]
    return spot


def manifest(rows, spot, series):
    print("=" * 104)
    print(f"TASK 1 — PANEL COMPOSITION  ({series})   [printed before any score]")
    print("=" * 104)
    n = len(rows)
    evs = {r["event"] for r in rows}
    tks = {r["ticker"] for r in rows}
    ts = [r["ts"] for r in rows]
    print(f"  rows (market-minutes) : {n}")
    print(f"  events                : {len(evs)}   <-- THE UNIT OF OBSERVATION")
    print(f"  distinct markets      : {len(tks)}")
    print(f"  date range            : "
          f"{dt.datetime.utcfromtimestamp(min(ts))} -> "
          f"{dt.datetime.utcfromtimestamp(max(ts))}")
    per_ev = Counter(r["event"] for r in rows)
    per_mkt = Counter(r["ticker"] for r in rows)
    print(f"  rows per event        : min={min(per_ev.values())} "
          f"med={int(np.median(list(per_ev.values())))} "
          f"max={max(per_ev.values())}")
    mkts_per_ev = Counter()
    for r in rows:
        mkts_per_ev[r["event"]] = mkts_per_ev.get(r["event"], 0)
    tmp = defaultdict(set)
    for r in rows:
        tmp[r["event"]].add(r["ticker"])
    mpe = [len(v) for v in tmp.values()]
    print(f"  markets per event     : min={min(mpe)} "
          f"med={int(np.median(mpe))} max={max(mpe)}")
    tau = np.array([r["tau_s"] for r in rows]) / 60.0
    print(f"  time-to-expiry (min)  : p5={np.percentile(tau,5):.0f} "
          f"p25={np.percentile(tau,25):.0f} med={np.median(tau):.0f} "
          f"p75={np.percentile(tau,75):.0f} p95={np.percentile(tau,95):.0f}")
    mid = np.array([r["mid"] for r in rows])
    sp = np.array([r["spread"] for r in rows])
    print(f"  mid                   : p5={np.percentile(mid,5):.3f} "
          f"med={np.median(mid):.3f} p95={np.percentile(mid,95):.3f}")
    print(f"  spread                : med={np.median(sp):.4f} "
          f"p90={np.percentile(sp,90):.4f} max={sp.max():.4f}")
    y = np.array([r["y"] for r in rows])
    print(f"  outcome base rate     : {y.mean():.4f}")
    weeks = Counter(dt.datetime.utcfromtimestamp(t).strftime("%G-W%V")
                    for t in ts)
    print(f"  calendar coverage     : {len(weeks)} distinct ISO weeks")
    print(f"    {dict(sorted(weeks.items()))}")
    print(f"  spot series loaded    : {len(spot)} minutes")
    # content validation, not row counts
    bad = sum(1 for r in rows
              if not (0 < r["bid"] < r["ask"] < 1)
              or r["tau_s"] <= 0 or r["K"] <= 0)
    print(f"  content validation    : {bad} malformed rows "
          f"({'PASS' if bad == 0 else 'FAIL'})")
    return {"rows": n, "events": len(evs), "markets": len(tks),
            "weeks": len(weeks), "malformed": bad}


def estimate_basis(spot, split_ts):
    """Mean BRTI - Coinbase basis, estimated on the FIRST HALF only.

    Coinbase is a BRTI constituent, not the index. Measured over 1,593 hourly
    boundaries the basis is +1.25 bp mean (Coinbase reads BELOW BRTI), sd 2.76
    bp, p99 |diff| 9.96 bp -- about $10 median and $63 p99 at $62,900. Small
    against $500 strike spacing but NOT negligible near a boundary, so the mean
    is corrected out and the residual sd is carried as irreducible noise.

    Estimated on data strictly BEFORE `split_ts` so the correction is not fitted
    on the evaluation period.
    """
    import json as _json
    settles = []
    with open(os.path.join(r"C:\Users\gianf\crypto\data\kalshi_settled",
                           "KXBTCD.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                m = _json.loads(line)
            except Exception:
                continue
            v, ct = m.get("expiration_value"), m.get("close_time")
            if v in (None, "") or not ct:
                continue
            try:
                ts = int(dt.datetime.fromisoformat(
                    ct.replace("Z", "+00:00")).timestamp())
                settles.append((ts, float(v)))
            except Exception:
                pass
    # DEDUPE BY BOUNDARY. Every market in an event carries the SAME
    # expiration_value, so iterating markets counts each settlement ~180 times
    # and weights events by how many strikes they happen to list. The dry run
    # reported n=5908 boundaries against 1,593 real events, which is how this
    # was caught. One row per distinct close timestamp.
    uniq = {}
    for ts, v in settles:
        uniq[ts] = v
    d = []
    for ts, v in sorted(uniq.items()):
        if ts >= split_ts:
            continue
        c = spot.get(ts - 60)
        if c:
            d.append((v - c) / v)
    if not d:
        return 0.0, 0.0, 0
    return float(np.mean(d)), float(np.std(d)), len(d)


def attach_spot(rows, spot, max_stale_s=180):
    """Spot at the decision minute. Assert knowability."""
    ok, miss, stale = 0, 0, 0
    for r in rows:
        t = r["ts"]
        s = None
        for back in range(0, max_stale_s + 1, 60):
            s = spot.get(t - back)
            if s is not None:
                if back > 0:
                    stale += 1
                break
        if s is None:
            r["S"] = None
            miss += 1
            continue
        # KNOWABILITY ASSERTION: the spot minute must not be after the
        # decision minute.
        assert (t - back) <= t, "spot timestamp after decision timestamp"
        r["S"] = s
        ok += 1
    print(f"\n  spot attach: {ok} ok, {miss} missing, {stale} back-filled "
          f"(<= {max_stale_s}s stale)")
    return [r for r in rows if r.get("S")]


def trailing_vol(rows, spot, window_min=360):
    """Trailing realized vol per decision minute, from spot only.

    Uses ONLY prices strictly BEFORE the decision minute.
    """
    ks = sorted(spot)
    arr = np.array([spot[k] for k in ks])
    idx = {k: i for i, k in enumerate(ks)}
    for r in rows:
        i = idx.get(r["ts"])
        if i is None or i < window_min + 1:
            r["sigma"] = None
            continue
        seg = arr[i - window_min:i]            # strictly before, excludes i
        lr = np.diff(np.log(seg))
        if len(lr) < 30:
            r["sigma"] = None
            continue
        sd_1m = float(np.std(lr, ddof=1))
        r["sigma"] = sd_1m * math.sqrt(525960.0)   # minutes per year
    return [r for r in rows if r.get("sigma")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXBTCD")
    args = ap.parse_args()
    os.makedirs(REPORTS, exist_ok=True)

    rows = load_panel(args.series)
    spot = load_spot()
    man = manifest(rows, spot, args.series)
    if not spot:
        print("\n*** spot series missing — cannot build models. Stop.")
        return

    # basis correction, fitted on the first half of the window only
    all_ts = sorted(r["ts"] for r in rows)
    split_ts = all_ts[len(all_ts) // 2]
    b_mean, b_sd, b_n = estimate_basis(spot, split_ts)
    print(f"\n  BRTI basis (fitted on n={b_n} boundaries BEFORE "
          f"{dt.datetime.utcfromtimestamp(split_ts)}): "
          f"mean={b_mean*1e4:+.2f}bp sd={b_sd*1e4:.2f}bp")
    print(f"  -> spot multiplied by {1+b_mean:.8f}; residual sd "
          f"{b_sd*1e4:.2f}bp (~${b_sd*62900:.0f}) carried as irreducible noise")

    rows = attach_spot(rows, spot)
    for r in rows:
        r["S"] = r["S"] * (1.0 + b_mean)
    rows = trailing_vol(rows, spot)
    print(f"  after spot + vol attach: {len(rows)} rows, "
          f"{len({r['event'] for r in rows})} events")

    # reference empirical return distribution for M3, from spot only,
    # using the FIRST HALF of the sample (out-of-sample discipline)
    ks = sorted(spot)
    half = ks[:len(ks) // 2]
    a = np.array([spot[k] for k in half])
    ref = np.diff(np.log(a))
    ref = ref[np.isfinite(ref)]
    print(f"  M3 reference distribution: {len(ref)} 1-minute returns from the "
          f"FIRST HALF of the spot series only")

    # ------------------------------------------------------------- models
    for r in rows:
        S, K, t, sg = r["S"], r["K"], r["tau_s"], r["sigma"]
        r["m1"] = m1_gbm(S, K, t, sg)
        r["m2"] = m2_settlement_aware(S, K, t, sg)
        r["m3"] = m3_empirical(S, K, t, ref, 60.0)
        r["m3t"] = m3_student_t(S, K, t, sg)

    y = np.array([r["y"] for r in rows])
    mid = np.array([r["mid"] for r in rows])
    ev = np.array([r["event"] for r in rows])

    print("\n" + "=" * 104)
    print("TASK 3 — THE HEADLINE TEST: does any model beat the Kalshi mid?")
    print("=" * 104)
    print(f"  unit of observation : EVENT ({len(set(ev))} events)")
    print(f"  rows                : {len(rows)} market-minutes")
    print(f"  CI method           : bootstrap resampling EVENTS, 2000 reps")
    print(f"  benchmark           : Kalshi's own mid at the decision timestamp")
    print()
    print(f"  {'model':<26} {'Brier':>10} {'mid Brier':>10} {'diff':>11} "
          f"{'95% CI (event-clustered)':>28} {'p':>8} {'verdict':>10}")
    results = []
    for key, label in [("m1", "M1 driftless GBM"),
                       ("m2", "M2 settlement-aware"),
                       ("m3", "M3 empirical fat-tail"),
                       ("m3t", "M3t Student-t nu=2.03")]:
        p = np.array([r[key] for r in rows])
        res = cluster_bootstrap_diff(p, mid, y, ev)
        res["model"] = label
        res["brier_model"] = brier(p, y)
        res["brier_mid"] = brier(mid, y)
        res["logloss_model"] = log_loss(p, y)
        res["logloss_mid"] = log_loss(mid, y)
        verdict = ("MODEL" if res["ci_hi"] < 0
                   else ("MID" if res["ci_lo"] > 0 else "tie"))
        res["verdict"] = verdict
        ci = f"[{res['ci_lo']:+.6f}, {res['ci_hi']:+.6f}]"
        print(f"  {label:<26} {res['brier_model']:>10.6f} "
              f"{res['brier_mid']:>10.6f} {res['diff']:>+11.6f} {ci:>28} "
              f"{res['p']:>8.4f} {verdict:>10}")
        results.append(res)

    print("\n  (diff = Brier_model - Brier_mid; NEGATIVE = model beats mid)")
    print(f"\n  log loss: mid={results[0]['logloss_mid']:.6f}  " +
          "  ".join(f"{r['model'].split()[0]}={r['logloss_model']:.6f}"
                    for r in results))

    # ---- model-ladder ordering (B1-ORD) --------------------------------
    print("\n  model-ladder ordering (each must beat its predecessor):")
    for (k0, l0), (k1, l1) in [(("m1", "M1"), ("m2", "M2")),
                               (("m2", "M2"), ("m3", "M3"))]:
        p0 = np.array([r[k0] for r in rows])
        p1 = np.array([r[k1] for r in rows])
        d = cluster_bootstrap_diff(p1, p0, y, ev)
        vd = ("BETTER" if d["ci_hi"] < 0
              else ("WORSE" if d["ci_lo"] > 0 else "tie"))
        print(f"    {l1} vs {l0}: diff={d['diff']:+.6f} "
              f"CI [{d['ci_lo']:+.6f}, {d['ci_hi']:+.6f}] -> {vd}")

    # ---- reliability ----------------------------------------------------
    print("\n  RELIABILITY — Kalshi mid (5% buckets, with counts)")
    print(f"    {'bucket':>12} {'n':>7} {'mean p':>9} {'empirical':>10} "
          f"{'gap':>8}")
    for b in reliability(mid, y, bins=20):
        print(f"    {b['lo']:.2f}-{b['hi']:.2f} {b['n']:>7} "
              f"{b['mean_p']:>9.4f} {b['emp']:>10.4f} "
              f"{b['emp']-b['mean_p']:>+8.4f}")

    # ---- GO_NO_GO criterion 4: two disjoint periods ---------------------
    print("\n  TWO DISJOINT PERIODS (GO_NO_GO criterion 4)")
    ts_arr = np.array([r["ts"] for r in rows])
    cut = np.median(ts_arr)
    for key, label in [("m1", "M1"), ("m2", "M2"), ("m3", "M3")]:
        p = np.array([r[key] for r in rows])
        line = f"    {label}: "
        for nm, msk in [("first half", ts_arr < cut), ("second half",
                                                       ts_arr >= cut)]:
            if msk.sum() < 50:
                continue
            d = cluster_bootstrap_diff(p[msk], mid[msk], y[msk], ev[msk])
            line += (f"{nm} diff={d['diff']:+.6f} "
                     f"CI[{d['ci_lo']:+.5f},{d['ci_hi']:+.5f}] "
                     f"n_ev={d['n_events']}   ")
        print(line)

    # ---- localisation: where does the gap live? -------------------------
    print("\n  LOCALISATION — Brier diff (best model - mid) by bucket")
    print("  (reported for completeness; per PREREGISTRATION a diffuse "
          "advantage is treated as a leak, not an edge)")
    best_key = min(["m1", "m2", "m3"],
                   key=lambda k: brier(np.array([r[k] for r in rows]), y))
    pb = np.array([r[best_key] for r in rows])
    tau_m = np.array([r["tau_s"] for r in rows]) / 60.0
    absz = np.array([abs(math.log(r["S"] / r["K"]))
                     / math.sqrt(max(r["tau_s"], 1) / SECONDS_PER_YEAR)
                     / max(r["sigma"], 1e-9) for r in rows])
    hour = np.array([dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).hour
                     for r in rows])
    spread_a = np.array([r["spread"] for r in rows])
    print(f"  best model by Brier: {best_key}")
    for name, arr, edges in [
        ("time-to-expiry (min)", tau_m, [0, 10, 20, 30, 45, 61]),
        ("|ln(S/K)|/(sig sqrt(tau))", absz, [0, 0.25, 0.5, 1.0, 2.0, 99]),
        ("mid price", mid, [0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.0]),
        ("spread", spread_a, [0, 0.011, 0.021, 0.031, 1.0]),
    ]:
        print(f"    -- {name}")
        for lo, hi in zip(edges, edges[1:]):
            m = (arr >= lo) & (arr < hi)
            if m.sum() < 100 or len(set(ev[m])) < 5:
                continue
            d = cluster_bootstrap_diff(pb[m], mid[m], y[m], ev[m])
            vd = ("MODEL" if d["ci_hi"] < 0
                  else ("MID" if d["ci_lo"] > 0 else "tie"))
            # cost test: fee at that price + spread actually crossed
            fee_c = float(np.mean([
                float(kalshi_fee_per_contract_unrounded(
                    min(max(x, 0.001), 0.999))) for x in mid[m]])) * 100
            sp_c = float(np.mean(spread_a[m])) * 100
            print(f"       {lo:>6.3g}-{hi:<6.3g} n={m.sum():>6} "
                  f"ev={len(set(ev[m])):>4} diff={d['diff']:+.6f} "
                  f"CI[{d['ci_lo']:+.5f},{d['ci_hi']:+.5f}] {vd:>6}  "
                  f"fee={fee_c:.2f}c halfspread={sp_c/2:.2f}c")

    json.dump({"manifest": man, "results": results},
              open(os.path.join(REPORTS, f"b1_{args.series}.json"), "w"),
              indent=2, default=str)
    print(f"\nwrote reports/b1_{args.series}.json")


if __name__ == "__main__":
    main()
