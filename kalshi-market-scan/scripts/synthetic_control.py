"""Phase 4: the synthetic-noise control.

Runs the ENTIRE modelling and evaluation pipeline on data containing no
exploitable signal. If it reports an edge, the pipeline is broken and every other
number in this project is void.

## Design note — a mistake worth recording

The first version of this control set the synthetic "market mid" to the true
probability *plus* unbiased noise. Every near-optimal model then beat it, and the
control reported FAIL. That was not leakage: adding zero-mean noise to a
probability forecast strictly raises its Brier score, so a model closer to the
truth beats it by arithmetic. The control was mis-specified, not the pipeline.

The corrected design pins the mid to the **exact true probability**, which is the
best forecast obtainable. Nothing can then beat it except by chance, so a
detected "edge" is unambiguously a defect.

## Negative controls (must all report NO edge)

  A. driftless GBM walk, strikes set the way KXBTC15M sets them (strike = the
     previous window's 60s-average settle), outcomes computed from the walk.
     Mid = true GBM probability.
  B. same walk, outcomes replaced by an independent coin. True probability is
     0.5, so the mid is 0.5.
  C. pure random features, random binary outcomes, mid = 0.5.

## Positive control (MUST report an edge, or the suite is vacuous)

  D. mid is deliberately biased away from the truth. A pipeline that reports "no
     edge" on everything would pass A-C trivially, so we require it to *find* an
     edge that genuinely exists. A suite with only negative controls cannot
     distinguish a correct pipeline from a broken-and-silent one.
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
    reliability,
)
from kalshi_research.models import (  # noqa: E402
    gbm_prob_above,
    settlement_aware_prob_above,
    student_t_prob_above,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

WINDOW_S = 900.0
AVG_WINDOW_S = 60.0
SIGMA_15M = 0.0035
DECISION_S = 300.0  # decide 5 minutes into the window
N_SIM = 4000


def gen_walk_markets(n: int, sigma_15m: float, seed: int, sever_outcome: bool = False):
    """Simulate KXBTC15M exactly: strike = previous window's 60s-average settle."""
    rng = np.random.default_rng(seed)
    steps = 900
    sigma_step = sigma_15m / np.sqrt(steps)
    path = np.exp(np.cumsum(rng.normal(0, sigma_step, (n + 2) * steps)) + np.log(60_000.0))

    rows, prev = [], None
    for i in range(n + 1):
        win = path[i * steps : (i + 1) * steps]
        settle = float(win[-60:].mean())
        if prev is not None:
            k = int(steps * (DECISION_S / WINDOW_S))
            rows.append(
                {
                    "i": i,
                    "strike": prev,
                    "spot_decision": float(win[k]),
                    "settle": settle,
                    "seconds_remaining": WINDOW_S - DECISION_S,
                    "outcome": int(settle >= prev),
                }
            )
        prev = settle
    df = pd.DataFrame(rows)
    if sever_outcome:
        df["outcome"] = rng.integers(0, 2, len(df))
    return df


def sigma_to_expiry(df: pd.DataFrame, sigma: float) -> np.ndarray:
    tau = df.seconds_remaining.values / WINDOW_S
    return sigma * np.sqrt(np.maximum(tau, 1e-9))


def candidate_models(df: pd.DataFrame, sigma: float) -> dict[str, np.ndarray]:
    sig = sigma_to_expiry(df, sigma)
    S, K = df.spot_decision.values, df.strike.values
    return {
        "gbm": gbm_prob_above(S, K, sig),
        "settlement_aware": settlement_aware_prob_above(
            S, K, sig, df.seconds_remaining.values, AVG_WINDOW_S
        ),
        "student_t": student_t_prob_above(S, K, sig, dof=4),
        "always_50": np.full(len(df), 0.5),
        "momentum": np.clip(0.5 + 3.0 * (S / K - 1.0), 0.01, 0.99),
        "reversal": np.clip(0.5 - 3.0 * (S / K - 1.0), 0.01, 0.99),
    }


def run_case(name: str, df: pd.DataFrame, p_mid: np.ndarray, sigma: float) -> list[dict]:
    y = df.outcome.values
    out = []
    for model, p in candidate_models(df, sigma).items():
        c = compare_to_mid(p, p_mid, y, n_boot=2000, seed=1)
        row = c.as_row(f"{name}::{model}")
        row.update(case=name, model=model)
        out.append(row)
    return out


def main() -> None:
    rows: list[dict] = []

    # --- A: real walk outcomes, mid = the exact true probability ------------
    df_a = gen_walk_markets(N_SIM, SIGMA_15M, seed=11)
    mid_a = gbm_prob_above(
        df_a.spot_decision.values, df_a.strike.values, sigma_to_expiry(df_a, SIGMA_15M)
    )
    rows += run_case("A_walk_true_mid", df_a, mid_a, SIGMA_15M)

    # --- B: outcomes severed from prices, so the truth is a coin -----------
    df_b = gen_walk_markets(N_SIM, SIGMA_15M, seed=22, sever_outcome=True)
    rows += run_case("B_severed_outcomes", df_b, np.full(len(df_b), 0.5), SIGMA_15M)

    # --- C: pure noise features, coin outcomes, mid = 0.5 ------------------
    rng = np.random.default_rng(33)
    df_c = pd.DataFrame(
        {
            "spot_decision": rng.normal(60_000, 500, N_SIM),
            "strike": rng.normal(60_000, 500, N_SIM),
            "seconds_remaining": np.full(N_SIM, WINDOW_S - DECISION_S),
            "outcome": rng.integers(0, 2, N_SIM),
        }
    )
    rows += run_case("C_pure_noise", df_c, np.full(N_SIM, 0.5), SIGMA_15M)

    neg = pd.DataFrame(rows)
    neg["control_type"] = "negative"

    # --- D: POSITIVE control. Mid is biased; the truth is findable. --------
    # Without this, a pipeline that reports "no edge" on everything passes A-C.
    df_d = gen_walk_markets(N_SIM, SIGMA_15M, seed=44)
    true_d = gbm_prob_above(
        df_d.spot_decision.values, df_d.strike.values, sigma_to_expiry(df_d, SIGMA_15M)
    )
    mid_d = np.clip(true_d - 0.06 * np.sign(true_d - 0.5), 0.01, 0.99)
    pos = pd.DataFrame(run_case("D_biased_mid", df_d, mid_d, SIGMA_15M))
    pos["control_type"] = "positive"

    res = pd.concat([neg, pos], ignore_index=True)
    bh = benjamini_hochberg(res.p_value.tolist(), alpha=0.05)
    res["q_value"] = bh.q_value.values
    res["survives_fdr"] = bh.reject_at_alpha.values
    res["detected_edge"] = res.beats_mid & res.survives_fdr

    # A negative control must detect nothing. The positive control must detect
    # the GBM model specifically -- that is the model that knows the truth.
    neg_fail = res[(res.control_type == "negative") & res.detected_edge]
    pos_hit = res[
        (res.control_type == "positive")
        & res.detected_edge
        & res.model.isin(["gbm", "settlement_aware"])
    ]

    res.to_csv(REPORTS / "synthetic_control.csv", index=False)
    verdict = "PASS" if (len(neg_fail) == 0 and len(pos_hit) > 0) else "FAIL"
    summary = {
        "verdict": verdict,
        "n_hypotheses": len(res),
        "negative_control_false_positives": len(neg_fail),
        "positive_control_detections": len(pos_hit),
        "requirement": (
            "PASS requires zero detected edges across all negative controls AND at "
            "least one detection in the positive control. Negative controls alone "
            "would be passed trivially by a pipeline that never detects anything."
        ),
        "design_note": (
            "An earlier version set the synthetic mid to truth+noise and reported "
            "FAIL. That was a mis-specified control, not leakage: unbiased noise "
            "raises a forecast's Brier score, so near-optimal models beat it by "
            "arithmetic. The mid is now pinned to the exact true probability."
        ),
    }
    (REPORTS / "synthetic_control_verdict.json").write_text(json.dumps(summary, indent=1))

    cols = ["control_type", "case", "model", "n", "brier_model", "brier_mid",
            "paired_diff_mean", "ci_lo", "ci_hi", "q_value", "detected_edge"]
    print("=" * 100)
    print(f"SYNTHETIC-NOISE CONTROL: {verdict}")
    print("=" * 100)
    print(res[cols].to_string(index=False))
    print()
    print(f"hypotheses: {len(res)}   "
          f"negative-control false positives: {len(neg_fail)} (must be 0)   "
          f"positive-control detections: {len(pos_hit)} (must be >0)")
    if len(neg_fail):
        print("\n*** PIPELINE IS BROKEN - findings a signal in signal-free data ***")
        print(neg_fail[cols].to_string(index=False))
    if len(pos_hit) == 0:
        print("\n*** PIPELINE IS BLIND - cannot detect a real 6c mispricing ***")

    rel = reliability(mid_a, df_a.outcome.values, n_bins=10)
    rel.to_csv(REPORTS / "synthetic_reliability.csv", index=False)
    print(f"\ncase A: true-model Brier={brier(mid_a, df_a.outcome.values):.5f} "
          f"base rate={df_a.outcome.mean():.4f}")
    print("reliability of the true model on case A (should hug the diagonal):")
    print(rel.to_string(index=False))


if __name__ == "__main__":
    main()
