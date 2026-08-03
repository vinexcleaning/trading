"""Statistical safeguards against small samples and lucky streaks.

The failure mode this module exists to prevent: a wallet with 8 winning trades
showing a 40% ROI outranking a wallet with 300 consistently profitable, copyable
trades at 12%. Raw point estimates make that mistake; shrinkage, confidence
intervals and concentration penalties do not.

Everything here is deterministic. Bootstrap resampling uses a seeded generator so
that re-running the pipeline over unchanged data produces identical scores --
otherwise wallet rankings would jitter between runs for no reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from ..logging_setup import get_logger

log = get_logger(__name__)

# Fixed seed: reproducibility matters more than fresh randomness here.
BOOTSTRAP_SEED = 20260729


def _to_array(values: list[Decimal] | list[float]) -> np.ndarray:
    """Convert to float64 for statistics.

    Money stays Decimal for accounting; statistics are inherently approximate, so
    float is appropriate here and the conversion happens at exactly one boundary.
    """
    if not values:
        return np.array([], dtype=np.float64)
    return np.asarray([float(v) for v in values], dtype=np.float64)


@dataclass(slots=True)
class BootstrapResult:
    """Bootstrap distribution summary for a per-trade statistic."""

    point_estimate: float
    ci_low: float
    ci_high: float
    prob_positive: float
    iterations: int
    n: int

    @property
    def is_significant(self) -> bool:
        """True when the whole interval sits above zero."""
        return self.ci_low > 0.0


def bootstrap_mean(
    values: list[Decimal] | list[float],
    *,
    iterations: int = 2000,
    confidence: float = 0.95,
    seed: int = BOOTSTRAP_SEED,
) -> BootstrapResult | None:
    """Percentile bootstrap for the mean of ``values``.

    Reports the probability that the true mean exceeds zero, which is the
    question that actually matters for "does this wallet have an edge".
    """
    arr = _to_array(values)
    n = arr.size
    if n == 0:
        return None
    if n == 1:
        # A single observation carries no information about dispersion; saying so
        # is better than reporting a zero-width interval.
        v = float(arr[0])
        return BootstrapResult(v, v, v, 1.0 if v > 0 else 0.0, 0, 1)

    rng = np.random.default_rng(seed)
    samples = rng.choice(arr, size=(iterations, n), replace=True)
    means = samples.mean(axis=1)

    alpha = (1.0 - confidence) / 2.0
    return BootstrapResult(
        point_estimate=float(arr.mean()),
        ci_low=float(np.quantile(means, alpha)),
        ci_high=float(np.quantile(means, 1.0 - alpha)),
        prob_positive=float((means > 0).mean()),
        iterations=iterations,
        n=n,
    )


def bayesian_shrink(
    observed: float,
    n: int,
    prior_mean: float,
    *,
    strength: float = 30.0,
) -> float:
    """Shrink an observed mean toward a population prior.

    ``strength`` is expressed in trades: it is the sample size at which the
    observation and the prior carry equal weight. With ``strength=30``, a wallet
    with 5 trades keeps only 5/35 of its observed edge, while one with 300 keeps
    300/330. This is the mechanism that stops a tiny sample from topping the
    leaderboard on a point estimate alone.
    """
    if n <= 0:
        return prior_mean
    if strength <= 0:
        return observed
    weight = n / (n + strength)
    return weight * observed + (1.0 - weight) * prior_mean


def sample_confidence(n: int, target: int = 100) -> float:
    """0-100 confidence from sample size alone.

    Concave (square-root) rather than linear: the information gained going from
    10 to 20 trades far exceeds that from 200 to 210.
    """
    if n <= 0:
        return 0.0
    return round(100.0 * min(1.0, (n / target) ** 0.5), 1)


@dataclass(slots=True)
class DrawdownResult:
    max_drawdown_pct: float
    max_drawdown_abs: Decimal
    peak_index: int
    trough_index: int
    # Cumulative P&L after each trade, for charting.
    equity_curve: list[float]
    drawdown_curve: list[float]


def compute_drawdown(
    pnl_sequence: list[Decimal], starting_capital: Decimal | None = None
) -> DrawdownResult:
    """Peak-to-trough decline over a chronological P&L sequence.

    Drawdown is expressed against the running peak of cumulative P&L plus any
    starting capital. Without a capital base, a wallet whose first trade loses
    would otherwise show an undefined or infinite drawdown.
    """
    if not pnl_sequence:
        return DrawdownResult(0.0, Decimal("0"), 0, 0, [], [])

    base = float(starting_capital) if starting_capital and starting_capital > 0 else 0.0
    cumulative = 0.0
    equity: list[float] = []
    for pnl in pnl_sequence:
        cumulative += float(pnl)
        equity.append(cumulative)

    # Reference for percentage terms: capital base, or the largest peak reached.
    if base <= 0:
        base = max(max(equity), abs(min(equity)), 1.0)

    peak = base
    peak_idx = 0
    max_dd = 0.0
    max_dd_abs = 0.0
    trough_idx = 0
    best_peak_idx = 0
    dd_curve: list[float] = []

    for i, value in enumerate(equity):
        level = base + value
        if level > peak:
            peak = level
            peak_idx = i
        decline = peak - level
        dd_pct = (decline / peak) if peak > 0 else 0.0
        dd_curve.append(dd_pct)
        if dd_pct > max_dd:
            max_dd = dd_pct
            max_dd_abs = decline
            trough_idx = i
            best_peak_idx = peak_idx

    # Capped at 100%. The capital base is a modelled bankroll, not an observed
    # one, so a wallet losing more than it can produce a ratio above 1.0 --
    # which reads as "lost more than everything" and invites misreading. The
    # absolute figure below is uncapped and carries the full magnitude, and
    # scoring already treats anything past 60% as the worst case, so nothing is
    # lost by reporting a full wipe-out as 100%.
    return DrawdownResult(
        max_drawdown_pct=round(min(max_dd, 1.0), 4),
        max_drawdown_abs=Decimal(str(round(max_dd_abs, 6))),
        peak_index=best_peak_idx,
        trough_index=trough_idx,
        equity_curve=equity,
        drawdown_curve=[min(d, 1.0) for d in dd_curve],
    )


def longest_streak(outcomes: list[bool], *, winning: bool) -> int:
    """Longest run of wins (or losses) in chronological order."""
    best = current = 0
    for won in outcomes:
        if won == winning:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def profit_concentration(pnls: list[Decimal], top_n: int = 1) -> float:
    """Share of gross profit contributed by the ``top_n`` best trades.

    Measured against gross *profit* (winners only), not net P&L: if losses were
    netted off, a wallet with one huge win and many small losses could report a
    concentration above 100% or a negative denominator.
    """
    winners = sorted((p for p in pnls if p > 0), reverse=True)
    if not winners:
        return 0.0
    total = sum(winners, Decimal("0"))
    if total <= 0:
        return 0.0
    top = sum(winners[:top_n], Decimal("0"))
    return round(float(top / total), 4)


def profit_factor(pnls: list[Decimal]) -> float | None:
    """Gross profit / gross loss.

    ``None`` when there are no losses at all: an "infinite" profit factor is not
    a meaningful number to rank on, and reporting a huge float would let a
    3-trade wallet with no losers dominate the leaderboard.
    """
    gross_profit = sum((p for p in pnls if p > 0), Decimal("0"))
    gross_loss = -sum((p for p in pnls if p < 0), Decimal("0"))
    if gross_loss <= 0:
        return None
    return round(float(gross_profit / gross_loss), 4)


def expected_value_per_dollar(pnls: list[Decimal], stakes: list[Decimal]) -> float | None:
    """Mean P&L per dollar staked.

    This is the metric that defuses the spec's trap: a wallet winning 90% of the
    time buying at $0.95 has a high win rate and a *negative* value here.
    """
    if not pnls or len(pnls) != len(stakes):
        return None
    total_stake = sum(stakes, Decimal("0"))
    if total_stake <= 0:
        return None
    return round(float(sum(pnls, Decimal("0")) / total_stake), 6)


def active_periods(
    timestamps: list[int],
    *,
    now_ts: int,
    period_days: float = 7.0,
    lookback_periods: int = 8,
) -> int:
    """How many of the last ``lookback_periods`` weeks contain at least one trade.

    Replaces first-to-last span as an activity gate, because span is trivially
    inflated by a couple of stray early trades. Observed live: the leading
    candidate showed a 198-day span from monthly tennis counts of 1, 3, 3, 0, 18,
    11, 25 — April empty, and the whole record really only three months old. A
    span gate waved that through; this counts the weeks it actually turned up.

    Buckets are counted backwards from ``now_ts``, so the most recent partial week
    is bucket 0 and a wallet must have traded recently to fill it.
    """
    if not timestamps or lookback_periods <= 0 or period_days <= 0:
        return 0
    window = int(period_days * 86_400)
    buckets: set[int] = set()
    for ts in timestamps:
        age = now_ts - ts
        if age < 0 or age >= window * lookback_periods:
            continue
        buckets.add(age // window)
    return len(buckets)


def recency_weight(age_days: float, halflife_days: float = 90.0) -> float:
    """Exponential decay weight for a trade's age."""
    if halflife_days <= 0:
        return 1.0
    return float(0.5 ** (max(0.0, age_days) / halflife_days))


def weighted_mean(values: list[float], weights: list[float]) -> float | None:
    if not values or len(values) != len(weights):
        return None
    total_w = sum(weights)
    if total_w <= 0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / total_w


@dataclass(slots=True)
class StabilityResult:
    """Consistency of a statistic across independent slices."""

    slices_evaluated: int
    positive_slices: int
    mean: float
    std_dev: float
    # 0-100: high when the statistic is both positive and steady.
    stability_score: float

    @property
    def positive_fraction(self) -> float:
        if self.slices_evaluated == 0:
            return 0.0
        return self.positive_slices / self.slices_evaluated


def compute_stability(slice_values: list[float], *, min_slices: int = 2) -> StabilityResult:
    """Score how consistently a statistic holds up across slices.

    Slices are time periods or market types. A wallet profitable in one slice and
    deeply negative in three is not consistent, even if the aggregate is positive
    -- that pattern usually means one lucky period is carrying the record.
    """
    values = [v for v in slice_values if v is not None]
    n = len(values)
    if n < min_slices:
        # Too few slices to say anything; a neutral score avoids both rewarding
        # and punishing absent evidence.
        return StabilityResult(n, sum(1 for v in values if v > 0),
                               float(np.mean(values)) if values else 0.0, 0.0, 50.0)

    arr = _to_array(values)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if n > 1 else 0.0
    positive = int((arr > 0).sum())

    consistency = positive / n
    # Penalise dispersion relative to the mean's magnitude.
    if abs(mean) > 1e-9:
        cv = std / abs(mean)
        dispersion_score = 1.0 / (1.0 + cv)
    else:
        dispersion_score = 0.0

    score = 100.0 * (0.6 * consistency + 0.4 * dispersion_score)
    if mean <= 0:
        # A negative average cannot be "stable" in a useful sense.
        score *= 0.4

    return StabilityResult(
        slices_evaluated=n,
        positive_slices=positive,
        mean=round(mean, 6),
        std_dev=round(std, 6),
        stability_score=round(max(0.0, min(100.0, score)), 1),
    )


def sharpe_like(pnls: list[Decimal], stakes: list[Decimal]) -> float | None:
    """Mean ROI over its standard deviation across trades.

    Not an annualised Sharpe ratio -- these are discrete event bets with no
    holding-period return -- so it is named to avoid implying otherwise.
    """
    if not pnls or len(pnls) != len(stakes):
        return None
    rois = [
        float(p / s) for p, s in zip(pnls, stakes) if s and s > 0
    ]
    if len(rois) < 2:
        return None
    arr = np.asarray(rois, dtype=np.float64)
    std = float(arr.std(ddof=1))
    if std <= 1e-12:
        return None
    return round(float(arr.mean()) / std, 4)


def normalise_to_score(
    value: float | None,
    *,
    worst: float,
    best: float,
    default: float = 0.0,
) -> float:
    """Map a raw value onto 0-100, clamped, tolerating an inverted range."""
    if value is None:
        return default
    if best == worst:
        return default
    ratio = (value - worst) / (best - worst)
    return round(100.0 * max(0.0, min(1.0, ratio)), 1)
