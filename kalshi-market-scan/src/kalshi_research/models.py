"""Fair-value probability models for threshold contracts.

Every model answers the same question: P(settle >= K | spot, vol, time remaining).
`gbm_prob_above` is the benchmark everything else must beat.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, t as student_t


def gbm_prob_above(
    spot: np.ndarray, strike: np.ndarray, sigma_to_expiry: np.ndarray
) -> np.ndarray:
    """Driftless GBM: P(S_T >= K) = Phi( ln(S/K) / sigma ).

    `sigma_to_expiry` is the total log-return standard deviation over the
    remaining life, i.e. sigma_per_period * sqrt(tau) already applied.
    """
    spot = np.asarray(spot, float)
    strike = np.asarray(strike, float)
    sig = np.maximum(np.asarray(sigma_to_expiry, float), 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(spot / strike) / sig
    return np.clip(norm.cdf(z), 1e-9, 1 - 1e-9)


def settlement_aware_prob_above(
    spot: np.ndarray,
    strike: np.ndarray,
    sigma_to_expiry: np.ndarray,
    seconds_remaining: np.ndarray,
    avg_window_s: float = 60.0,
) -> np.ndarray:
    """P(mean of the final `avg_window_s` seconds >= K).

    Kalshi settles KXBTC15M on the arithmetic mean of 60 one-second samples of the
    CF Benchmarks RTI, not on a point sample. For a driftless random walk the mean
    of the terminal window has strictly lower variance than its endpoint:

        Var(mean over final w) = sigma^2 * (T - w + w/3)   (continuous limit)

    so the effective sigma is scaled by sqrt((tau - w + w/3)/tau). Lower variance
    pushes probabilities away from 0.5, which is why a correct model prices
    late-window contracts *further* from 50c than point-sample GBM does.
    """
    spot = np.asarray(spot, float)
    strike = np.asarray(strike, float)
    sig = np.maximum(np.asarray(sigma_to_expiry, float), 1e-12)
    tau_s = np.maximum(np.asarray(seconds_remaining, float), 1e-9)
    w = np.minimum(avg_window_s, tau_s)
    # variance of the average of the final w seconds, relative to a point sample
    eff = np.sqrt(np.maximum((tau_s - w + w / 3.0) / tau_s, 1e-12))
    return gbm_prob_above(spot, strike, sig * eff)


def student_t_prob_above(
    spot: np.ndarray, strike: np.ndarray, sigma_to_expiry: np.ndarray, dof: float = 4.0
) -> np.ndarray:
    """Fat-tailed variant. Scaled so the t has the same variance as the Gaussian."""
    spot = np.asarray(spot, float)
    strike = np.asarray(strike, float)
    sig = np.maximum(np.asarray(sigma_to_expiry, float), 1e-12)
    if dof <= 2:
        raise ValueError("dof must exceed 2 for finite variance")
    scale = sig / np.sqrt(dof / (dof - 2.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(spot / strike) / scale
    return np.clip(student_t.cdf(z, df=dof), 1e-9, 1 - 1e-9)


def implied_sigma_from_price(
    price: np.ndarray, spot: np.ndarray, strike: np.ndarray
) -> np.ndarray:
    """Invert driftless GBM for the sigma the market is quoting."""
    price = np.clip(np.asarray(price, float), 1e-6, 1 - 1e-6)
    z = norm.ppf(price)
    lr = np.log(np.asarray(spot, float) / np.asarray(strike, float))
    with np.errstate(divide="ignore", invalid="ignore"):
        sig = np.where(np.abs(z) > 1e-9, lr / z, np.nan)
    return np.where(sig > 0, sig, np.nan)


# ------------------------------------------------------------ vol estimators


def realized_vol_close_to_close(logret: np.ndarray, window: int) -> np.ndarray:
    s = np.asarray(logret, float)
    out = np.full(len(s), np.nan)
    if len(s) < window:
        return out
    c = np.cumsum(np.insert(s**2, 0, 0.0))
    sums = c[window:] - c[:-window]
    out[window - 1 :] = np.sqrt(sums / window)
    return out


def parkinson_vol(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """Range estimator; ~5x more efficient than close-to-close per observation."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.sqrt(np.log(h / l) ** 2 / (4.0 * np.log(2.0)))


def garman_klass_vol(
    open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray
) -> np.ndarray:
    o, h, l, c = (np.asarray(x, float) for x in (open_, high, low, close))
    with np.errstate(divide="ignore", invalid="ignore"):
        v = 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    return np.sqrt(np.maximum(v, 0.0))


def rogers_satchell_vol(
    open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray
) -> np.ndarray:
    o, h, l, c = (np.asarray(x, float) for x in (open_, high, low, close))
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    return np.sqrt(np.maximum(v, 0.0))


def bipower_variation(logret: np.ndarray) -> float:
    """Jump-robust variance estimate. Compare with realized variance to detect jumps."""
    r = np.abs(np.asarray(logret, float))
    if len(r) < 2:
        return float("nan")
    mu1 = np.sqrt(2.0 / np.pi)
    return float((mu1**-2) * np.sum(r[1:] * r[:-1]))


def ewma_vol(logret: np.ndarray, lam: float = 0.94) -> np.ndarray:
    r = np.asarray(logret, float)
    var = np.empty(len(r))
    var[:] = np.nan
    seed = np.nanvar(r[: min(50, len(r))])
    if not np.isfinite(seed) or seed <= 0:
        seed = np.nanvar(r) or 1e-8
    v = seed
    for i, x in enumerate(r):
        if np.isfinite(x):
            v = lam * v + (1 - lam) * x * x
        var[i] = v
    return np.sqrt(var)


def har_rv_design(rv: np.ndarray, d: int = 1, w: int = 5, m: int = 22):
    """HAR-RV regressors: daily, weekly, monthly averages of realized variance.

    Returns (X, y, valid_mask) with strictly backward-looking features only.
    """
    rv = np.asarray(rv, float)
    n = len(rv)

    def trailing(k: int) -> np.ndarray:
        out = np.full(n, np.nan)
        cs = np.nancumsum(np.insert(rv, 0, 0.0))
        for i in range(k, n):
            out[i] = (cs[i] - cs[i - k]) / k
        return out

    Xd, Xw, Xm = trailing(d), trailing(w), trailing(m)
    X = np.column_stack([Xd, Xw, Xm])[:-1]
    y = rv[1:]
    valid = np.isfinite(X).all(axis=1) & np.isfinite(y)
    return X, y, valid
