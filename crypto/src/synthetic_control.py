"""TASK 4: the SYNTHETIC CONTROL — the gate on every Phase 2 result.

Generate price paths from a KNOWN distribution, price fake ladders from that
SAME distribution, add quote noise, then run the identical scoring code used on
the real panel. By construction there is no edge: the "market" and the "model"
draw from the same generating process. If the pipeline reports one anyway, the
pipeline is broken and every Phase 2 result is void.

Three arms, because a control with only the null arm cannot distinguish "no
edge" from "no power":

  A  NULL      market prices = true probability + symmetric noise
                 -> expect NO significant difference
  B  POSITIVE  market prices deliberately biased (mispriced wings)
                 -> expect the pipeline to DETECT it (power check)
  C  LEAK      model is given the realised outcome through a feature
                 -> expect the pipeline to scream (leak detector check)

Arm B and C matter as much as A. A pipeline that finds nothing on everything is
just as broken as one that finds something on noise.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from models import (  # noqa: E402
    m1_gbm, m2_settlement_aware, brier, log_loss,
    cluster_bootstrap_diff, reliability, SECONDS_PER_YEAR,
)

OUT = r"C:\Users\gianf\crypto\reports"


def simulate(n_events=1500, strikes_per_event=9, sigma_ann=0.435,
             horizon_s=3600.0, quote_noise=0.01, arm="NULL",
             wing_bias=0.05, seed=7):
    """Build a fake panel with the same shape as the real one.

    Returns dict of arrays, one row per (event, strike), plus event ids.
    """
    rng = np.random.default_rng(seed)
    tau = horizon_s / SECONDS_PER_YEAR
    sd = sigma_ann * math.sqrt(tau)

    ev, S0s, Ks, taus, ys, mids, truths = [], [], [], [], [], [], []
    for e in range(n_events):
        S0 = 60000.0 * math.exp(rng.normal(0, 0.05))
        # realised terminal price from the KNOWN distribution
        z = rng.normal()
        ST = S0 * math.exp(-0.5 * sd * sd + sd * z)
        # ladder centred on S0, spaced in sd units
        for j in range(strikes_per_event):
            offs = (j - (strikes_per_event - 1) / 2) * 0.6 * sd
            K = S0 * math.exp(offs)
            true_p = m1_gbm(S0, K, horizon_s, sigma_ann)
            y = 1.0 if ST > K else 0.0
            if arm == "POSITIVE":
                # market misprices the WINGS: pushes tail probs toward 0.5
                d = abs(true_p - 0.5)
                mid = true_p + wing_bias * (0.5 - true_p) * (2 * d)
            else:
                mid = true_p
            mid = mid + rng.normal(0, quote_noise)
            mid = min(max(mid, 0.005), 0.995)
            ev.append(e)
            S0s.append(S0)
            Ks.append(K)
            taus.append(horizon_s)
            ys.append(y)
            mids.append(mid)
            truths.append(true_p)
    return {"event": np.array(ev), "S": np.array(S0s), "K": np.array(Ks),
            "tau_s": np.array(taus), "y": np.array(ys),
            "mid": np.array(mids), "true_p": np.array(truths),
            "sigma_ann": sigma_ann}


def score_arm(panel, arm, leak=False):
    S, K, t = panel["S"], panel["K"], panel["tau_s"]
    sig = panel["sigma_ann"]
    y, mid, ev = panel["y"], panel["mid"], panel["event"]

    if leak:
        # deliberately leak the outcome into the "model"
        p_model = 0.02 + 0.96 * y
    else:
        p_model = np.array([m1_gbm(S[i], K[i], t[i], sig)
                            for i in range(len(S))])

    res = cluster_bootstrap_diff(p_model, mid, y, ev)
    res.update({
        "arm": arm,
        "brier_model": brier(p_model, y),
        "brier_mid": brier(mid, y),
        "logloss_model": log_loss(p_model, y),
        "logloss_mid": log_loss(mid, y),
    })
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=" * 100)
    print("SYNTHETIC CONTROL — three arms")
    print("=" * 100)
    print("  generating process : driftless GBM, sigma_ann=0.435 (the measured")
    print("                       BTC hourly figure), 1h horizon")
    print("  panel shape        : 1,500 events x 9 strikes = 13,500 rows")
    print("  unit of observation: EVENT (bootstrap resamples events, not rows)")
    print()

    results = []

    # ---- ARM A: null -------------------------------------------------------
    p = simulate(arm="NULL", seed=7)
    r = score_arm(p, "A_NULL")
    results.append(r)

    # ---- ARM B: real mispricing -------------------------------------------
    p2 = simulate(arm="POSITIVE", wing_bias=0.05, seed=7)
    r2 = score_arm(p2, "B_POSITIVE_5pct_wing_bias")
    results.append(r2)

    p3 = simulate(arm="POSITIVE", wing_bias=0.15, seed=7)
    r3 = score_arm(p3, "B_POSITIVE_15pct_wing_bias")
    results.append(r3)

    # ---- ARM C: leak -------------------------------------------------------
    r4 = score_arm(p, "C_LEAK_outcome_in_model", leak=True)
    results.append(r4)

    print(f"  {'arm':<30} {'Brier model':>12} {'Brier mid':>11} "
          f"{'diff':>10} {'95% CI':>22} {'p':>8} {'n_ev':>6}")
    for r in results:
        ci = f"[{r['ci_lo']:+.5f}, {r['ci_hi']:+.5f}]"
        print(f"  {r['arm']:<30} {r['brier_model']:>12.6f} "
              f"{r['brier_mid']:>11.6f} {r['diff']:>+10.6f} {ci:>22} "
              f"{r['p']:>8.4f} {r['n_events']:>6}")

    print("\n  (diff = Brier_model - Brier_mid; NEGATIVE means model beats mid)")

    # ---- verdicts ----------------------------------------------------------
    print("\n" + "=" * 100)
    print("GATE VERDICTS")
    print("=" * 100)
    a = results[0]
    ok_a = a["ci_lo"] <= 0 <= a["ci_hi"]
    print(f"  A NULL     : CI {'CONTAINS' if ok_a else 'EXCLUDES'} zero  "
          f"-> {'PASS' if ok_a else '*** FAIL — pipeline finds edge on noise'}")

    ok_b = results[2]["ci_hi"] < 0
    print(f"  B POSITIVE : 15% wing bias detected = {ok_b}  "
          f"-> {'PASS' if ok_b else '*** FAIL — pipeline is blind to real edge'}")
    ok_b5 = results[1]["ci_hi"] < 0
    print(f"               5% wing bias detected = {ok_b5} "
          f"(sensitivity floor)")

    ok_c = results[3]["ci_hi"] < 0 and results[3]["brier_model"] < 0.01
    print(f"  C LEAK     : outcome-in-feature detected = {ok_c}  "
          f"-> {'PASS' if ok_c else '*** FAIL — leak detector is blind'}")

    gate = ok_a and ok_b and ok_c
    print(f"\n  OVERALL GATE: {'PASS — Phase 2 results may be trusted' if gate else '*** FAIL — Phase 2 results are VOID'}")

    with open(os.path.join(OUT, "synthetic_control.json"), "w") as f:
        json.dump({"results": results,
                   "gate": {"null_ok": bool(ok_a), "power_ok": bool(ok_b),
                            "power_5pct": bool(ok_b5), "leak_ok": bool(ok_c),
                            "overall": bool(gate)}}, f, indent=2)


if __name__ == "__main__":
    main()
