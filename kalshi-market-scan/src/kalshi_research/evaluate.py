"""Scoring, calibration and leak-audit machinery, identical for every family.

Every number this module produces is out-of-sample by construction: splits are
strictly time-ordered and there is no shuffled cross-validation anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def brier(p: np.ndarray, y: np.ndarray) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    return float(np.mean((p - y) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray, eps: float = 1e-12) -> float:
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def reliability(p: np.ndarray, y: np.ndarray, n_bins: int = 20) -> pd.DataFrame:
    """Reliability curve in equal-width buckets, with counts."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        rows.append(
            {
                "bin_lo": edges[b],
                "bin_hi": edges[b + 1],
                "n": int(m.sum()),
                "mean_pred": float(p[m].mean()),
                "observed_freq": float(y[m].mean()),
                "gap": float(p[m].mean() - y[m].mean()),
            }
        )
    return pd.DataFrame(rows)


@dataclass
class Comparison:
    """The decisive comparison: our probability vs Kalshi's mid, same outcomes."""

    n: int
    brier_model: float
    brier_mid: float
    logloss_model: float
    logloss_mid: float
    brier_skill_score: float  # >0 means we beat the mid
    paired_diff_mean: float  # mean(mid_se - model_se); >0 favours us
    paired_diff_ci: tuple[float, float]
    p_value: float

    def as_row(self, family: str) -> dict:
        return {
            "family": family,
            "n": self.n,
            "brier_model": round(self.brier_model, 6),
            "brier_mid": round(self.brier_mid, 6),
            "brier_skill_score": round(self.brier_skill_score, 6),
            "logloss_model": round(self.logloss_model, 6),
            "logloss_mid": round(self.logloss_mid, 6),
            "paired_diff_mean": round(self.paired_diff_mean, 8),
            "ci_lo": round(self.paired_diff_ci[0], 8),
            "ci_hi": round(self.paired_diff_ci[1], 8),
            "p_value": self.p_value,
            "beats_mid": bool(self.paired_diff_ci[0] > 0),
        }


def compare_to_mid(
    p_model: np.ndarray, p_mid: np.ndarray, y: np.ndarray, n_boot: int = 5000, seed: int = 0
) -> Comparison:
    """Paired comparison of squared errors, bootstrapped.

    Paired rather than independent because both forecasts see the same events;
    the paired difference removes event difficulty as a nuisance term.
    """
    p_model = np.asarray(p_model, float)
    p_mid = np.asarray(p_mid, float)
    y = np.asarray(y, float)
    ok = np.isfinite(p_model) & np.isfinite(p_mid) & np.isfinite(y)
    p_model, p_mid, y = p_model[ok], p_mid[ok], y[ok]
    n = len(y)
    if n == 0:
        return Comparison(0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, (np.nan, np.nan), np.nan)

    se_model = (p_model - y) ** 2
    se_mid = (p_mid - y) ** 2
    d = se_mid - se_model  # positive => we are closer than the mid

    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        boot[i] = d[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    # two-sided bootstrap p-value for H0: mean(d) == 0
    p_val = float(2 * min((boot <= 0).mean(), (boot >= 0).mean()))

    b_model, b_mid = brier(p_model, y), brier(p_mid, y)
    return Comparison(
        n=n,
        brier_model=b_model,
        brier_mid=b_mid,
        logloss_model=log_loss(p_model, y),
        logloss_mid=log_loss(p_mid, y),
        brier_skill_score=float(1 - b_model / b_mid) if b_mid > 0 else np.nan,
        paired_diff_mean=float(d.mean()),
        paired_diff_ci=(float(lo), float(hi)),
        p_value=p_val,
    )


# ---------------------------------------------------------------- leak audit


@dataclass
class LeakAuditResult:
    name: str
    passed: bool
    detail: str
    value: float | None = None


def assert_knowability(
    features: pd.DataFrame, knowable_ns: pd.Series, decision_ns: pd.Series
) -> LeakAuditResult:
    """Every feature's knowability timestamp must precede the decision timestamp."""
    bad = int((pd.Series(knowable_ns).values > pd.Series(decision_ns).values).sum())
    return LeakAuditResult(
        "knowability",
        bad == 0,
        f"{bad}/{len(features)} rows have a feature knowable at or after the decision",
        float(bad),
    )


def shift_forward_test(
    fit_predict, X: pd.DataFrame, y: np.ndarray, p_mid: np.ndarray, threshold: float = 0.0
) -> LeakAuditResult:
    """Shift features forward one period. A real edge must degrade; a leak survives.

    If the shifted model still beats the mid, the "edge" was reading the future.
    """
    Xs = X.shift(1).iloc[1:]
    ys, mids = y[1:], p_mid[1:]
    ok = Xs.notna().all(axis=1).values
    if ok.sum() < 50:
        return LeakAuditResult("shift_forward", False, "insufficient rows after shift")
    p = fit_predict(Xs[ok], ys[ok])
    c = compare_to_mid(p, mids[ok], ys[ok], n_boot=1000)
    passed = not (c.paired_diff_ci[0] > threshold)
    return LeakAuditResult(
        "shift_forward",
        passed,
        f"shifted model vs mid: paired diff {c.paired_diff_mean:.2e} "
        f"CI ({c.paired_diff_ci[0]:.2e}, {c.paired_diff_ci[1]:.2e}); "
        f"{'no edge survives shift (good)' if passed else 'EDGE SURVIVES SHIFT - LEAK'}",
        c.paired_diff_mean,
    )


def shuffle_label_test(
    fit_predict, X: pd.DataFrame, y: np.ndarray, p_mid: np.ndarray, seed: int = 0
) -> LeakAuditResult:
    """Shuffled labels must destroy any edge. If not, the pipeline is broken."""
    rng = np.random.default_rng(seed)
    ys = rng.permutation(y)
    p = fit_predict(X, ys)
    c = compare_to_mid(p, p_mid, ys, n_boot=1000)
    passed = not (c.paired_diff_ci[0] > 0)
    return LeakAuditResult(
        "shuffle_labels",
        passed,
        f"shuffled-label model vs mid: paired diff {c.paired_diff_mean:.2e} "
        f"CI ({c.paired_diff_ci[0]:.2e}, {c.paired_diff_ci[1]:.2e}); "
        f"{'edge destroyed (good)' if passed else 'EDGE SURVIVES SHUFFLE - BROKEN'}",
        c.paired_diff_mean,
    )


# ---------------------------------------------------------- multiple testing


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> pd.DataFrame:
    """BH FDR control. Applied across the WHOLE hypothesis ledger, never per family."""
    p = np.asarray(p_values, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    crit = alpha * (np.arange(1, n + 1) / n)
    below = ranked <= crit
    k = int(np.max(np.where(below)[0]) + 1) if below.any() else 0
    reject = np.zeros(n, bool)
    if k:
        reject[order[:k]] = True
    q = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    qv = np.empty(n)
    qv[order] = np.clip(q, 0, 1)
    return pd.DataFrame(
        {"p_value": p, "q_value": qv, "reject_at_alpha": reject, "n_tests": n, "alpha": alpha}
    )


def deflated_sharpe_ratio(
    observed_sr: float, n_trials: int, n_obs: int, skew: float = 0.0, kurt: float = 3.0
) -> float:
    """Probability the observed Sharpe is real given how many trials were run.

    Bailey & Lopez de Prado. The expected maximum Sharpe from n_trials of pure
    noise is subtracted before testing, which is exactly the correction a wide
    parameter sweep requires.
    """
    from scipy.stats import norm

    if n_trials < 1 or n_obs < 2:
        return float("nan")
    e = 0.5772156649015329  # Euler-Mascheroni
    if n_trials == 1:
        sr0 = 0.0
    else:
        sr0 = (1 - e) * norm.ppf(1 - 1 / n_trials) + e * norm.ppf(1 - 1 / (n_trials * np.e))
    denom = np.sqrt(
        max(1e-12, 1 - skew * observed_sr + (kurt - 1) / 4 * observed_sr**2)
    )
    z = (observed_sr - sr0) * np.sqrt(n_obs - 1) / denom
    return float(norm.cdf(z))
