"""Adjusted Tennis Skill Score.

Formula (v1)
------------
Nine components, each normalised to 0-100, combined with the weights in
``Settings.score_weights``::

    base = 25% copyable ROI        (shrunk toward the population mean)
         + 15% profit factor
         + 15% sample confidence
         + 10% consistency         (stability across periods and market types)
         + 10% max drawdown
         + 10% recency
         +  5% liquidity compatibility
         +  5% profit concentration
         +  5% data quality

    skill_score = base x (product of penalty multipliers)

The score is built on **copyable** ROI, not raw ROI. A wallet whose edge
evaporates once a follower's delay is applied scores poorly here by construction,
which is the entire point.

Penalties are multiplicative and compound. Any single severe problem -- a negative
copyable edge, market-making behaviour, a tiny sample -- can move a wallet from
the top of the board to unqualified on its own. Every applied penalty is stored
so the UI can show precisely why a wallet scores what it does.

Qualification (``qualified``) is a separate hard gate, not a score threshold: a
wallet must clear every configured minimum to be alertable, regardless of how
attractive its weighted score looks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..config import Settings, get_settings
from ..enums import RiskFlag
from ..logging_setup import get_logger
from . import statistics as stats
from .metrics import MetricSet

log = get_logger(__name__)

FORMULA_VERSION = "v1"

# --- component normalisation ranges -----------------------------------------
# Copyable ROI: -20% scores 0, +30% scores 100. Deliberately demanding -- a
# copyable edge above 30% after delay and slippage would be exceptional.
COPYABLE_ROI_WORST = -0.20
COPYABLE_ROI_BEST = 0.30
# Profit factor: 1.0 is break-even, 3.0 is excellent.
PROFIT_FACTOR_WORST = 0.5
PROFIT_FACTOR_BEST = 3.0
# Drawdown: 0% scores 100, 60% scores 0.
DRAWDOWN_WORST = 0.60
# Liquidity: full marks once typical market liquidity comfortably exceeds what a
# follower needs.
LIQUIDITY_BEST_USDC = 25_000.0
# Concentration: a wallet whose single best trade is most of its profit is fragile.
CONCENTRATION_WORST = 0.60

# Favourite-longshot detection. A wallet winning this often whose average
# loss erases this many average wins is carrying tail risk its sample cannot
# measure.
HIGH_WIN_RATE_THRESHOLD = 0.85
LOSS_TO_WIN_RATIO_THRESHOLD = 5.0


@dataclass
class ScoreResult:
    """A wallet's score with its full derivation."""

    skill_score: float
    base_score: float
    components: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)
    total_penalty_multiplier: float = 1.0
    risk_flags: list[str] = field(default_factory=list)
    qualified: bool = False
    disqualification_reasons: list[str] = field(default_factory=list)
    confidence_level: str = "low"
    explanation: str = ""
    formula_version: str = FORMULA_VERSION

    def penalties_json(self) -> str | None:
        return json.dumps(self.penalties, sort_keys=True) if self.penalties else None

    def risk_flags_json(self) -> str | None:
        return json.dumps(self.risk_flags) if self.risk_flags else None

    def reasons_json(self) -> str | None:
        return (
            json.dumps(self.disqualification_reasons)
            if self.disqualification_reasons
            else None
        )


def _recency_score(metrics: MetricSet, now: datetime) -> float:
    """Reward wallets whose edge is present *recently*.

    A wallet that was excellent a year ago and mediocre since is not a wallet to
    follow now, so the recent window is weighted far above the older one.
    """
    periods = metrics.performance_by_period or {}
    recent = periods.get("last_30d", {})
    medium = periods.get("last_90d", {})

    recent_roi = recent.get("copyable_roi")
    if recent_roi is None:
        recent_roi = recent.get("roi")
    medium_roi = medium.get("copyable_roi")
    if medium_roi is None:
        medium_roi = medium.get("roi")

    if recent_roi is None and medium_roi is None:
        # No recent activity at all is not evidence of skill.
        return 25.0

    scores: list[tuple[float, float]] = []
    if recent_roi is not None:
        scores.append((
            stats.normalise_to_score(
                recent_roi, worst=COPYABLE_ROI_WORST, best=COPYABLE_ROI_BEST
            ),
            0.7,
        ))
    if medium_roi is not None:
        scores.append((
            stats.normalise_to_score(
                medium_roi, worst=COPYABLE_ROI_WORST, best=COPYABLE_ROI_BEST
            ),
            0.3,
        ))

    total_w = sum(w for _, w in scores)
    return round(sum(s * w for s, w in scores) / total_w, 1) if total_w else 25.0


def _consistency_score(metrics: MetricSet) -> float:
    """Stability of the copyable edge across independent slices."""
    slice_values: list[float] = []

    for key in ("last_30d", "last_90d", "last_365d"):
        row = (metrics.performance_by_period or {}).get(key, {})
        value = row.get("copyable_roi")
        if value is None:
            value = row.get("roi")
        if value is not None:
            slice_values.append(float(value))

    for row in (metrics.performance_by_market_type or {}).values():
        if row.get("completed", 0) >= 3:
            value = row.get("copyable_roi")
            if value is None:
                value = row.get("roi")
            if value is not None:
                slice_values.append(float(value))

    return stats.compute_stability(slice_values).stability_score


def _liquidity_score(metrics: MetricSet) -> float:
    """How well the wallet's markets accommodate a follower.

    Approximated from average copyability, which already folds in depth and
    partial-fill evidence, so this does not double-count the same signal.
    """
    if metrics.avg_copyability_score is not None:
        return round(metrics.avg_copyability_score, 1)
    return 40.0


class WalletScorer:
    """Turns a metric set into an explainable score and a qualification verdict."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.now = now or datetime.now(timezone.utc)

    def score(self, metrics: MetricSet) -> ScoreResult:
        s = self.settings
        weights = s.score_weights

        # ------------------------------------------------------- components
        # Shrunk ROI is preferred: it is the small-sample-safe version.
        copyable_roi = (
            metrics.shrunk_copyable_roi
            if metrics.shrunk_copyable_roi is not None
            else metrics.copyable_roi
        )
        components = {
            "copyable_roi": stats.normalise_to_score(
                copyable_roi, worst=COPYABLE_ROI_WORST, best=COPYABLE_ROI_BEST
            ),
            "profit_factor": stats.normalise_to_score(
                metrics.copyable_profit_factor
                if metrics.copyable_profit_factor is not None
                else metrics.profit_factor,
                worst=PROFIT_FACTOR_WORST,
                best=PROFIT_FACTOR_BEST,
                # An undefined profit factor (no losses) is treated neutrally
                # rather than as perfection.
                default=50.0 if metrics.completed_positions else 0.0,
            ),
            "sample_confidence": metrics.sample_confidence or 0.0,
            "consistency": _consistency_score(metrics),
            "drawdown": stats.normalise_to_score(
                -(metrics.max_drawdown if metrics.max_drawdown is not None else DRAWDOWN_WORST),
                worst=-DRAWDOWN_WORST,
                best=0.0,
            ),
            "recency": _recency_score(metrics, self.now),
            "liquidity_fit": _liquidity_score(metrics),
            "concentration": stats.normalise_to_score(
                -(
                    metrics.pct_profit_from_largest_trade
                    if metrics.pct_profit_from_largest_trade is not None
                    else CONCENTRATION_WORST
                ),
                worst=-CONCENTRATION_WORST,
                best=0.0,
            ),
            "data_quality": metrics.data_quality_score or 0.0,
        }

        base = sum(components[k] * weights[k] for k in weights)

        # --------------------------------------------------------- penalties
        penalties, flags = self._penalties(metrics)
        multiplier = 1.0
        for value in penalties.values():
            multiplier *= value

        final = round(max(0.0, min(100.0, base * multiplier)), 1)

        qualified, reasons = self._qualify(metrics, final, flags)

        return ScoreResult(
            skill_score=final,
            base_score=round(base, 1),
            components={k: round(v, 1) for k, v in components.items()},
            penalties=penalties,
            total_penalty_multiplier=round(multiplier, 4),
            risk_flags=flags,
            qualified=qualified,
            disqualification_reasons=reasons,
            confidence_level=self._confidence_level(metrics),
            explanation=self._explain(metrics, components, penalties, final, qualified, reasons),
        )

    # -------------------------------------------------------------- tail risk
    @staticmethod
    def _tail_risk(metrics: MetricSet) -> tuple[bool, float | None]:
        """Detect the favourite-longshot shape: win small often, lose big rarely.

        Returns ``(flagged, wins_erased_per_loss)``.

        The spec's warning made concrete: a wallet winning 90% of the time buying
        at $0.95 can still be unprofitable. The observed record of such a wallet
        looks superb -- high win rate, high profit factor, shallow drawdown --
        precisely because the losses that define its risk have barely occurred
        yet. With two losses in 181 trades you cannot estimate the loss rate, and
        the strategy's sign depends entirely on that unmeasured number.
        """
        completed = metrics.completed_positions or 0
        win_rate = metrics.win_rate
        if not completed or win_rate is None:
            return False, None

        wins = round(win_rate * completed)
        losses = completed - wins
        if wins <= 0 or losses <= 0:
            return False, None

        gross_profit = float(metrics.gross_profit or 0)
        gross_loss = float(metrics.gross_loss or 0)
        if gross_profit <= 0 or gross_loss <= 0:
            return False, None

        avg_win = gross_profit / wins
        avg_loss = gross_loss / losses
        if avg_win <= 0:
            return False, None

        ratio = avg_loss / avg_win
        flagged = win_rate >= HIGH_WIN_RATE_THRESHOLD and ratio >= LOSS_TO_WIN_RATIO_THRESHOLD
        return flagged, round(ratio, 2)

    # --------------------------------------------------------------- penalties
    def _penalties(self, metrics: MetricSet) -> tuple[dict[str, float], list[str]]:
        s = self.settings
        penalties: dict[str, float] = {}
        flags = list(metrics.risk_flags)

        if metrics.completed_positions < s.min_trades_soft_floor:
            penalties["below_min_trades"] = s.penalty_below_min_trades
            if RiskFlag.SMALL_SAMPLE not in flags:
                flags.append(RiskFlag.SMALL_SAMPLE)

        if (metrics.pct_profit_from_largest_trade or 0) > 0.5:
            penalties["profit_concentration"] = s.penalty_high_concentration
            if RiskFlag.PROFIT_CONCENTRATION not in flags:
                flags.append(RiskFlag.PROFIT_CONCENTRATION)

        if (metrics.max_drawdown or 0) > s.alert_max_drawdown:
            penalties["severe_drawdown"] = s.penalty_severe_drawdown

        recent = (metrics.performance_by_period or {}).get("last_30d", {})
        recent_roi = recent.get("copyable_roi", recent.get("roi"))
        if recent_roi is not None and recent_roi < 0 and recent.get("completed", 0) >= 3:
            penalties["negative_30d"] = s.penalty_negative_30d

        # The decisive one: no copyable edge at the benchmark delay.
        if metrics.copyable_roi is not None and metrics.copyable_roi <= 0:
            penalties["negative_copyable_roi"] = s.penalty_negative_copyable

        if RiskFlag.LIKELY_MARKET_MAKING in flags:
            penalties["market_making"] = s.penalty_market_making

        if RiskFlag.LOW_LIQUIDITY_MARKETS in flags:
            penalties["low_liquidity"] = s.penalty_low_liquidity

        if RiskFlag.AMBIGUOUS_RECONSTRUCTION in flags:
            penalties["ambiguous_reconstruction"] = s.penalty_ambiguous_reconstruction

        tail_flagged, _ratio = self._tail_risk(metrics)
        if tail_flagged:
            penalties["tail_risk_asymmetry"] = s.penalty_tail_risk_asymmetry
            if RiskFlag.TAIL_RISK_ASYMMETRY not in flags:
                flags.append(RiskFlag.TAIL_RISK_ASYMMETRY)

        return penalties, flags

    # ------------------------------------------------------------ qualification
    def _qualify(
        self, metrics: MetricSet, score: float, flags: list[str]
    ) -> tuple[bool, list[str]]:
        """Hard gate for alerting. Every minimum must pass."""
        s = self.settings
        reasons: list[str] = []

        if metrics.completed_positions < s.alert_min_tennis_trades:
            reasons.append(
                f"only {metrics.completed_positions} completed tennis trades "
                f"(need {s.alert_min_tennis_trades})"
            )
        if score < s.alert_min_skill_score:
            reasons.append(
                f"skill score {score:.1f} below minimum {s.alert_min_skill_score:.0f}"
            )
        if metrics.copyable_roi is None:
            reasons.append("no copyable ROI could be measured at the benchmark delay")
        elif metrics.copyable_roi <= s.alert_min_copyable_roi:
            reasons.append(
                f"copyable ROI {metrics.copyable_roi:.2%} at "
                f"{s.benchmark_delay_seconds}s delay is not above "
                f"{s.alert_min_copyable_roi:.2%}"
            )
        if (metrics.data_quality_score or 0) < s.alert_min_data_confidence:
            reasons.append(
                f"data confidence {metrics.data_quality_score or 0:.0f} below "
                f"{s.alert_min_data_confidence:.0f}"
            )
        if (metrics.max_drawdown or 0) > s.alert_max_drawdown:
            reasons.append(
                f"max drawdown {metrics.max_drawdown:.1%} exceeds "
                f"{s.alert_max_drawdown:.1%}"
            )

        # Behaviours that make a wallet structurally unsuitable to copy.
        for flag, why in (
            (RiskFlag.LIKELY_MARKET_MAKING, "behaviour looks like market making"),
            (RiskFlag.NEGATIVE_COPYABLE_ROI, "copyable ROI is negative"),
        ):
            if flag in flags:
                reasons.append(why)

        return (not reasons), reasons

    def _confidence_level(self, metrics: MetricSet) -> str:
        n = metrics.completed_positions
        quality = metrics.data_quality_score or 0
        prob = metrics.prob_positive_edge

        if n >= 100 and quality >= 80 and prob is not None and prob >= 0.95:
            return "high"
        if n >= 50 and quality >= 70 and prob is not None and prob >= 0.85:
            return "medium"
        if n >= self.settings.min_trades_soft_floor and quality >= 60:
            return "low"
        return "insufficient"

    # ------------------------------------------------------------- explanation
    def _explain(
        self,
        metrics: MetricSet,
        components: dict[str, float],
        penalties: dict[str, float],
        score: float,
        qualified: bool,
        reasons: list[str],
    ) -> str:
        """Plain-language derivation shown next to the score in the UI."""
        parts: list[str] = []

        if metrics.copyable_roi is not None:
            gap = ""
            if metrics.roi is not None:
                delta = metrics.roi - metrics.copyable_roi
                gap = (
                    f" Raw ROI is {metrics.roi:.1%}, so a "
                    f"{self.settings.benchmark_delay_seconds}s delay costs "
                    f"{delta:.1%}."
                )
            coverage = ""
            if metrics.copyable_coverage is not None and metrics.copyable_coverage < 1.0:
                coverage = (
                    f" Only {metrics.copyable_coverage:.0%} of completed positions had "
                    "price evidence strong enough to assess, so this figure describes "
                    "part of the record, not all of it."
                )
            parts.append(
                f"Copyable ROI at {self.settings.benchmark_delay_seconds}s delay is "
                f"{metrics.copyable_roi:.1%} across {metrics.completed_positions} "
                f"completed tennis positions.{gap}{coverage}"
            )
        else:
            parts.append(
                "No copyable ROI could be measured: no position had price evidence "
                "at the benchmark delay strong enough to assess. Modelled-price "
                "estimates are deliberately excluded from this figure."
            )

        if metrics.shrunk_copyable_roi is not None and metrics.copyable_roi is not None:
            if abs(metrics.shrunk_copyable_roi - metrics.copyable_roi) > 0.005:
                parts.append(
                    f"Shrunk toward the population mean for sample size: "
                    f"{metrics.copyable_roi:.1%} -> {metrics.shrunk_copyable_roi:.1%}."
                )

        if metrics.prob_positive_edge is not None:
            parts.append(
                f"Bootstrap puts the probability of a genuine positive edge at "
                f"{metrics.prob_positive_edge:.0%}."
            )

        strongest = sorted(components.items(), key=lambda kv: kv[1], reverse=True)[:2]
        weakest = sorted(components.items(), key=lambda kv: kv[1])[:2]
        parts.append(
            "Strongest components: "
            + ", ".join(f"{k} {v:.0f}" for k, v in strongest)
            + ". Weakest: "
            + ", ".join(f"{k} {v:.0f}" for k, v in weakest)
            + "."
        )

        if penalties:
            parts.append(
                "Penalties applied: "
                + ", ".join(f"{k} (x{v:.2f})" for k, v in sorted(penalties.items()))
                + "."
            )

        parts.append(
            f"Final score {score:.1f}/100. "
            + (
                "Qualified for alerting."
                if qualified
                else "Not qualified: " + "; ".join(reasons) + "."
            )
        )
        return " ".join(parts)


# ---------------------------------------------------------------- ranking

RANKING_DEFINITIONS: dict[str, dict[str, str]] = {
    "best_overall": {
        "scope": "tennis",
        "sort": "skill_score",
        "label": "Best overall tennis wallets",
        "description": "Highest Adjusted Tennis Skill Score.",
    },
    "best_copyable": {
        "scope": "tennis",
        "sort": "copyable_roi",
        "label": "Best copyable tennis wallets",
        "description": "Highest ROI actually achievable after the benchmark delay.",
    },
    "best_live": {
        "scope": "tennis:live",
        "sort": "copyable_roi",
        "label": "Best live-tennis wallets",
        "description": "Copyable edge on in-play markets.",
    },
    "best_prematch": {
        "scope": "tennis:prematch",
        "sort": "copyable_roi",
        "label": "Best prematch tennis wallets",
        "description": "Copyable edge before the match starts.",
    },
    "best_match_winner": {
        "scope": "tennis:match_winner",
        "sort": "copyable_roi",
        "label": "Best match-winner wallets",
        "description": "Copyable edge on moneyline markets.",
    },
    "best_set_market": {
        "scope": "tennis:set_winner",
        "sort": "copyable_roi",
        "label": "Best set-market wallets",
        "description": "Copyable edge on set-winner markets.",
    },
    "best_recent": {
        "scope": "tennis:30d",
        "sort": "copyable_roi",
        "label": "Best recent wallets",
        "description": "Copyable edge over the last 30 days.",
    },
    "most_consistent": {
        "scope": "tennis",
        "sort": "consistency",
        "label": "Most consistent wallets",
        "description": "Steadiest edge across periods and market types.",
    },
    "highest_confidence": {
        "scope": "tennis",
        "sort": "prob_positive_edge",
        "label": "Highest-confidence wallets",
        "description": "Strongest statistical evidence of a real edge.",
    },
    "highest_raw_profit": {
        "scope": "tennis",
        "sort": "net_profit",
        "label": "Highest raw profit",
        "description": "Largest tennis P&L. Not a measure of copyability.",
    },
    "highest_adjusted_roi": {
        "scope": "tennis",
        "sort": "shrunk_copyable_roi",
        "label": "Highest adjusted ROI",
        "description": "Copyable ROI after small-sample shrinkage.",
    },
    "lowest_drawdown": {
        "scope": "tennis",
        "sort": "-max_drawdown",
        "label": "Lowest drawdown",
        "description": "Smallest peak-to-trough decline.",
    },
    "emerging": {
        "scope": "tennis",
        "sort": "emerging",
        "label": "Emerging wallets",
        "description": (
            "Promising but below the sample threshold. Explicitly unproven."
        ),
    },
}
