"""Fair-value models M1-M6 and the scoring harness.

Shared by the real panel and the synthetic control, so the control tests the
SAME code path that produces real results. A control that exercises a different
code path proves nothing.

Every model returns P(settle > strike). Unit of observation is the EVENT
throughout; nothing here aggregates across strikes.
"""
import math

import numpy as np
from scipy import stats

SECONDS_PER_YEAR = 365.25 * 86400.0


def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# --------------------------------------------------------------------- M1
def m1_gbm(S, K, tau_s, sigma_ann):
    """Driftless GBM. Phi( ln(S/K) / (sigma*sqrt(tau)) ).

    The baseline everything must beat.
    """
    if S <= 0 or K <= 0 or tau_s <= 0 or sigma_ann <= 0:
        return 1.0 if S > K else 0.0
    tau = tau_s / SECONDS_PER_YEAR
    v = sigma_ann * math.sqrt(tau)
    if v <= 0:
        return 1.0 if S > K else 0.0
    return _ncdf(math.log(S / K) / v)


# --------------------------------------------------------------------- M2
def averaging_factor(tau_s, avg_window_s=60.0):
    """Variance of the MEAN over the final `avg_window_s`, relative to a point
    sample, for driftless BM:   1 - a + a^2/3,   a = window / horizon.

    Always <= 1. Kalshi settles on a 60-second average, so the terminal
    variable is less variable than a point sample and the correct price sits
    FURTHER from 50c than M1 implies. A correctness fix, not a refinement.
    """
    if tau_s <= 0:
        return 1.0
    a = min(avg_window_s, tau_s) / tau_s
    return max(1e-9, 1.0 - a + (a * a) / 3.0)


def m2_settlement_aware(S, K, tau_s, sigma_ann, avg_window_s=60.0):
    if S <= 0 or K <= 0 or tau_s <= 0 or sigma_ann <= 0:
        return 1.0 if S > K else 0.0
    tau = tau_s / SECONDS_PER_YEAR
    v = sigma_ann * math.sqrt(tau * averaging_factor(tau_s, avg_window_s))
    if v <= 0:
        return 1.0 if S > K else 0.0
    return _ncdf(math.log(S / K) / v)


# --------------------------------------------------------------------- M3
def m3_empirical(S, K, tau_s, ref_returns, ref_horizon_s, avg_window_s=60.0):
    """Fat-tailed via the EMPIRICAL return distribution, scaled to horizon.

    Preferred over a fitted Student-t: the fit gave nu ~ 2.03, which sits on
    the infinite-variance boundary, so any sigma-scaled quantity from it is
    unstable. The empirical distribution needs no such parameter.

    Scaling uses sqrt-time on the ORDER STATISTICS, which is crude but avoids
    inventing a parametric tail. Reported as such.
    """
    if S <= 0 or K <= 0 or tau_s <= 0 or len(ref_returns) < 50:
        return 1.0 if S > K else 0.0
    scale = math.sqrt(max(tau_s, 1.0) / ref_horizon_s
                      * averaging_factor(tau_s, avg_window_s))
    thr = math.log(K / S)
    r = np.asarray(ref_returns) * scale
    return float(np.mean(r > thr))


def m3_student_t(S, K, tau_s, sigma_ann, nu=2.03, avg_window_s=60.0):
    """Student-t alternative. Kept for comparison; see the nu caveat above."""
    if S <= 0 or K <= 0 or tau_s <= 0 or sigma_ann <= 0 or nu <= 2:
        return 1.0 if S > K else 0.0
    tau = tau_s / SECONDS_PER_YEAR
    v = sigma_ann * math.sqrt(tau * averaging_factor(tau_s, avg_window_s))
    # scale so the t has variance v^2
    s = v / math.sqrt(nu / (nu - 2.0))
    return float(1.0 - stats.t.cdf(math.log(K / S) / s, nu))


# ------------------------------------------------------------------ scoring
def brier(p, y):
    p = np.asarray(p, float)
    y = np.asarray(y, float)
    return float(np.mean((p - y) ** 2))


def log_loss(p, y, eps=1e-6):
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def cluster_bootstrap_diff(p_model, p_mid, y, events, n_boot=2000, seed=0):
    """Paired Brier difference (model - mid), CI clustered BY EVENT.

    Negative difference = model is BETTER (lower Brier).

    Resampling EVENTS, not rows: the ~180 legs of one hourly ladder settle on
    one BTC price, so they are one observation. Resampling rows would shrink
    the CI by roughly sqrt(180) and manufacture significance. This is failure
    mode #3 and it has fired 4 times in this project.
    """
    p_model = np.asarray(p_model, float)
    p_mid = np.asarray(p_mid, float)
    y = np.asarray(y, float)
    events = np.asarray(events)

    d_row = (p_model - y) ** 2 - (p_mid - y) ** 2
    uniq = np.unique(events)
    idx_of = {e: np.flatnonzero(events == e) for e in uniq}
    # per-event mean, then bootstrap over events
    per_ev = np.array([d_row[idx_of[e]].mean() for e in uniq])
    point = float(per_ev.mean())

    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    n = len(uniq)
    for b in range(n_boot):
        take = rng.integers(0, n, n)
        boots[b] = per_ev[take].mean()
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # two-sided p for H0: difference = 0
    p_val = 2.0 * min(float(np.mean(boots >= 0)), float(np.mean(boots <= 0)))
    return {"diff": point, "ci_lo": float(lo), "ci_hi": float(hi),
            "p": min(1.0, p_val), "n_events": int(n), "n_rows": int(len(d_row))}


def reliability(p, y, bins=20):
    """Reliability curve in equal-width buckets, WITH COUNTS."""
    p = np.asarray(p, float)
    y = np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for lo, hi in zip(edges, edges[1:]):
        m = (p >= lo) & (p < hi)
        if not m.any():
            continue
        out.append({"lo": float(lo), "hi": float(hi), "n": int(m.sum()),
                    "mean_p": float(p[m].mean()),
                    "emp": float(y[m].mean())})
    return out
