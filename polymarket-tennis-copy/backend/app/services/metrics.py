"""Wallet performance metrics, raw and delay-adjusted.

Two parallel views are computed for every wallet:

* **Raw** -- what the wallet itself achieved.
* **Copyable** -- what a follower entering at the benchmark delay would have
  achieved, after price deterioration, spread and slippage.

The gap between them is the product's central number. A wallet can post a strong
raw ROI and a negative copyable ROI, and that wallet is worthless to follow.

Positions whose copyability could not be established (no price evidence) are
excluded from copyable statistics rather than counted as zero -- diluting an
average with fabricated zeros would understate a good wallet and flatter a bad one.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable, Sequence

from ..config import get_settings
from ..enums import MarketPhase, PositionStatus, RiskFlag, TennisMarketType
from ..logging_setup import get_logger
from . import statistics as stats

log = get_logger(__name__)

ZERO = Decimal("0")

# Entry-price buckets: skill at long odds is a different skill from skill at
# short odds, and aggregating them hides both.
ENTRY_BUCKETS: tuple[tuple[str, Decimal, Decimal], ...] = (
    ("0.00-0.10", Decimal("0.00"), Decimal("0.10")),
    ("0.10-0.25", Decimal("0.10"), Decimal("0.25")),
    ("0.25-0.40", Decimal("0.25"), Decimal("0.40")),
    ("0.40-0.60", Decimal("0.40"), Decimal("0.60")),
    ("0.60-0.75", Decimal("0.60"), Decimal("0.75")),
    ("0.75-0.90", Decimal("0.75"), Decimal("0.90")),
    ("0.90-1.00", Decimal("0.90"), Decimal("1.01")),
)

SIZE_BUCKETS: tuple[tuple[str, Decimal, Decimal], ...] = (
    ("<$50", Decimal("0"), Decimal("50")),
    ("$50-250", Decimal("50"), Decimal("250")),
    ("$250-1k", Decimal("250"), Decimal("1000")),
    ("$1k-5k", Decimal("1000"), Decimal("5000")),
    ("$5k-25k", Decimal("5000"), Decimal("25000")),
    (">$25k", Decimal("25000"), Decimal("1e12")),
)

LOOKBACK_WINDOWS = (7, 30, 90, 365)


@dataclass(slots=True)
class PositionRecord:
    """Flattened position used by the metrics engine.

    Decoupled from the ORM so metrics can be computed from fixtures in tests and
    from the database in production with identical code.
    """

    position_id: int
    opened_ts: int
    closed_ts: int | None
    status: str
    is_tennis: bool
    tennis_market_type: str
    entry_phase: str
    avg_entry_price: Decimal
    capital_committed: Decimal
    net_pnl: Decimal | None
    roi: float | None
    is_win: bool | None
    holding_seconds: int | None
    behaviour: str
    max_shares: Decimal = ZERO
    market_liquidity: Decimal | None = None
    tournament: str | None = None
    player: str | None = None
    reconstruction_confidence: float = 100.0
    flags: list[str] = field(default_factory=list)

    # Per-delay follower results: {delay_seconds: (roi, pnl, is_win, copyability,
    # data_confidence)}
    copyable: dict[int, tuple[float | None, Decimal | None, bool | None, float, float]] = field(
        default_factory=dict
    )

    @property
    def is_complete(self) -> bool:
        return self.status in (PositionStatus.CLOSED, PositionStatus.SETTLED)

    @property
    def occurred_at(self) -> datetime:
        return datetime.fromtimestamp(self.opened_ts, tz=timezone.utc)


@dataclass
class MetricSet:
    """Computed metrics for one wallet under one scope."""

    scope: str
    total_positions: int = 0
    completed_positions: int = 0
    open_positions: int = 0
    total_trades: int = 0
    volume_usdc: Decimal = ZERO
    capital_deployed: Decimal = ZERO

    gross_profit: Decimal = ZERO
    gross_loss: Decimal = ZERO
    net_profit: Decimal = ZERO
    fees_paid: Decimal = ZERO

    roi: float | None = None
    # Mean per-trade ROI, ignoring position size. This is the only raw figure
    # comparable to copyable ROI: a follower stakes a flat amount per signal, so
    # its copyable counterpart is equal-weighted by construction. Subtracting the
    # capital-weighted `roi` from it instead conflates the cost of delay with the
    # wallet's position sizing, and can make being late look profitable.
    roi_equal_weighted: float | None = None
    return_on_capital: float | None = None
    win_rate: float | None = None
    profit_factor: float | None = None
    avg_profit_per_trade: Decimal | None = None
    median_profit_per_trade: Decimal | None = None
    expected_value_per_dollar: float | None = None

    avg_entry_price: Decimal | None = None
    avg_holding_seconds: int | None = None
    median_holding_seconds: int | None = None

    max_drawdown: float | None = None
    max_drawdown_usdc: Decimal | None = None
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    pct_profit_from_largest_trade: float | None = None
    pct_profit_from_top5_trades: float | None = None
    pnl_std_dev: float | None = None
    sharpe_like: float | None = None

    benchmark_delay_seconds: int | None = None
    copyable_roi: float | None = None
    # Robust companions to copyable_roi. Mean-of-ROI is convex on binary
    # outcomes, so these expose how much of the headline rests on a few trades.
    copyable_roi_median: float | None = None
    copyable_roi_trimmed: float | None = None
    copyable_outlier_dependence: float | None = None
    copyable_win_rate: float | None = None
    copyable_net_profit: Decimal | None = None
    copyable_profit_factor: float | None = None
    avg_copyability_score: float | None = None
    # Fraction of completed positions with price evidence strong enough to assess.
    # Low coverage means the copyable figures describe a small slice of the record.
    copyable_coverage: float | None = None
    roi_by_delay: dict[int, dict[str, float | int | None]] = field(default_factory=dict)

    roi_ci_low: float | None = None
    roi_ci_high: float | None = None
    copyable_roi_ci_low: float | None = None
    copyable_roi_ci_high: float | None = None
    shrunk_copyable_roi: float | None = None
    prob_positive_edge: float | None = None
    sample_confidence: float | None = None

    performance_by_market_type: dict = field(default_factory=dict)
    performance_by_tournament: dict = field(default_factory=dict)
    performance_by_player: dict = field(default_factory=dict)
    performance_by_entry_bucket: dict = field(default_factory=dict)
    performance_by_size_bucket: dict = field(default_factory=dict)
    performance_by_period: dict = field(default_factory=dict)

    data_quality_score: float | None = None
    equity_curve: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)

    def json_field(self, name: str) -> str | None:
        value = getattr(self, name, None)
        return json.dumps(value, default=str) if value else None


def _breakdown(positions: Sequence[PositionRecord], benchmark_delay: int) -> dict:
    """Summarise a group of positions for a breakdown table."""
    complete = [p for p in positions if p.is_complete and p.net_pnl is not None]
    if not complete:
        return {
            "n": len(positions),
            "completed": 0,
            "net_pnl": "0",
            "roi": None,
            "win_rate": None,
            "copyable_roi": None,
        }

    pnls = [p.net_pnl for p in complete if p.net_pnl is not None]
    capital = sum((p.capital_committed for p in complete), ZERO)
    wins = sum(1 for p in complete if p.is_win)

    copyable_rois = [
        p.copyable[benchmark_delay][0]
        for p in complete
        if benchmark_delay in p.copyable and p.copyable[benchmark_delay][0] is not None
    ]

    return {
        "n": len(positions),
        "completed": len(complete),
        "net_pnl": str(sum(pnls, ZERO)),
        "roi": round(float(sum(pnls, ZERO) / capital), 4) if capital > 0 else None,
        "win_rate": round(wins / len(complete), 4),
        "copyable_roi": (
            round(sum(copyable_rois) / len(copyable_rois), 4) if copyable_rois else None
        ),
        "copyable_n": len(copyable_rois),
    }


class MetricsCalculator:
    """Computes every metric scope for one wallet."""

    def __init__(
        self,
        *,
        benchmark_delay_seconds: int | None = None,
        population_mean_copyable_roi: float = 0.0,
        now: datetime | None = None,
    ) -> None:
        settings = get_settings()
        self.settings = settings
        self.benchmark_delay = (
            benchmark_delay_seconds
            if benchmark_delay_seconds is not None
            else settings.benchmark_delay_seconds
        )
        # Prior for shrinkage. Defaults to zero edge, which is the correct
        # skeptical prior: absent evidence, assume no edge.
        self.population_mean = population_mean_copyable_roi
        self.now = now or datetime.now(timezone.utc)

    # ------------------------------------------------------------------ core
    def compute(self, scope: str, positions: Sequence[PositionRecord]) -> MetricSet:
        m = MetricSet(scope=scope, benchmark_delay_seconds=self.benchmark_delay)

        ordered = sorted(positions, key=lambda p: p.opened_ts)
        m.total_positions = len(ordered)

        complete = [p for p in ordered if p.is_complete and p.net_pnl is not None]
        m.completed_positions = len(complete)
        m.open_positions = m.total_positions - m.completed_positions
        m.capital_deployed = sum((p.capital_committed for p in ordered), ZERO)
        m.volume_usdc = sum(
            (p.capital_committed for p in ordered), ZERO
        )

        if not complete:
            # An all-open wallet still reports counts, but no performance claim.
            m.sample_confidence = stats.sample_confidence(0)
            m.data_quality_score = self._data_quality(ordered)
            m.risk_flags = self._risk_flags(m, ordered)
            return m

        pnls = [p.net_pnl for p in complete if p.net_pnl is not None]
        stakes = [p.capital_committed for p in complete]
        outcomes = [bool(p.is_win) for p in complete]

        m.gross_profit = sum((p for p in pnls if p > 0), ZERO)
        m.gross_loss = -sum((p for p in pnls if p < 0), ZERO)
        m.net_profit = sum(pnls, ZERO)

        total_capital = sum(stakes, ZERO)
        if total_capital > 0:
            m.roi = round(float(m.net_profit / total_capital), 6)
            m.return_on_capital = m.roi

        per_trade_rois = [p.roi for p in complete if p.roi is not None]
        if per_trade_rois:
            m.roi_equal_weighted = round(sum(per_trade_rois) / len(per_trade_rois), 6)
        m.win_rate = round(sum(outcomes) / len(outcomes), 4)
        m.profit_factor = stats.profit_factor(pnls)
        m.avg_profit_per_trade = m.net_profit / Decimal(len(pnls))
        m.median_profit_per_trade = _median_decimal(pnls)
        m.expected_value_per_dollar = stats.expected_value_per_dollar(pnls, stakes)

        entry_capital = sum(
            (p.avg_entry_price * p.capital_committed for p in complete), ZERO
        )
        if total_capital > 0:
            # Capital-weighted, so a $10k entry counts more than a $10 one.
            m.avg_entry_price = entry_capital / total_capital

        holds = [p.holding_seconds for p in complete if p.holding_seconds is not None]
        if holds:
            m.avg_holding_seconds = int(sum(holds) / len(holds))
            m.median_holding_seconds = int(sorted(holds)[len(holds) // 2])

        dd = stats.compute_drawdown(pnls, starting_capital=_drawdown_base(stakes))
        m.max_drawdown = dd.max_drawdown_pct
        m.max_drawdown_usdc = dd.max_drawdown_abs
        m.equity_curve = dd.equity_curve
        m.drawdown_curve = dd.drawdown_curve

        m.longest_win_streak = stats.longest_streak(outcomes, winning=True)
        m.longest_loss_streak = stats.longest_streak(outcomes, winning=False)
        m.pct_profit_from_largest_trade = stats.profit_concentration(pnls, 1)
        m.pct_profit_from_top5_trades = stats.profit_concentration(pnls, 5)
        m.sharpe_like = stats.sharpe_like(pnls, stakes)

        roi_series = [
            float(p / s) for p, s in zip(pnls, stakes) if s and s > 0
        ]
        if len(roi_series) >= 2:
            import numpy as np

            m.pnl_std_dev = round(float(np.std(np.asarray(roi_series), ddof=1)), 6)

        boot = stats.bootstrap_mean(
            roi_series, iterations=self.settings.bootstrap_iterations
        )
        if boot is not None:
            m.roi_ci_low = round(boot.ci_low, 6)
            m.roi_ci_high = round(boot.ci_high, 6)

        m.sample_confidence = stats.sample_confidence(
            len(complete), self.settings.min_trades_for_full_confidence
        )

        # ------------------------------------------------------- copyable view
        self._compute_copyable(m, complete)

        # ---------------------------------------------------------- breakdowns
        m.performance_by_market_type = self._group_by(
            complete, lambda p: p.tennis_market_type
        )
        m.performance_by_tournament = self._group_by(
            complete, lambda p: p.tournament, limit=25
        )
        m.performance_by_player = self._group_by(complete, lambda p: p.player, limit=25)
        m.performance_by_entry_bucket = self._group_by_bucket(
            complete, ENTRY_BUCKETS, lambda p: p.avg_entry_price
        )
        m.performance_by_size_bucket = self._group_by_bucket(
            complete, SIZE_BUCKETS, lambda p: p.capital_committed
        )
        m.performance_by_period = self._by_period(complete)

        m.data_quality_score = self._data_quality(ordered)
        m.risk_flags = self._risk_flags(m, complete)
        return m

    # -------------------------------------------------------------- copyable
    def _measured_rows(self, complete: list[PositionRecord], delay: int) -> list[tuple]:
        """Copyability rows at ``delay`` that rest on real price evidence.

        Rows priced from a modelled fallback are excluded. They exist so the UI can
        show *why* a trade could not be assessed, but averaging an assumption into
        copyable ROI would fabricate an edge -- and did, in testing: modelled rows
        made a 15s delay appear to *improve* returns by 6%, which is impossible.
        A wallet with no real evidence gets a null copyable ROI and therefore
        cannot qualify, which is the correct sceptical outcome.
        """
        floor = self.settings.min_copyable_data_confidence
        return [
            p.copyable[delay]
            for p in complete
            if delay in p.copyable
            and p.copyable[delay][0] is not None
            and p.copyable[delay][4] >= floor
        ]

    def _compute_copyable(self, m: MetricSet, complete: list[PositionRecord]) -> None:
        """Delay-adjusted performance, and the full delay curve."""
        delays = sorted(
            {d for p in complete for d in p.copyable}
            or set(self.settings.follower_delays_seconds)
        )

        for delay in delays:
            rows = self._measured_rows(complete, delay)
            # Count how many rows existed but were too weakly evidenced to use,
            # so thin coverage is visible rather than silent.
            attempted = sum(
                1
                for p in complete
                if delay in p.copyable and p.copyable[delay][0] is not None
            )
            if not rows:
                m.roi_by_delay[delay] = {
                    "roi": None,
                    "win_rate": None,
                    "net_profit": None,
                    "n": 0,
                    "excluded_weak_evidence": attempted,
                }
                continue

            rois = [r[0] for r in rows if r[0] is not None]
            pnls = [r[1] for r in rows if r[1] is not None]
            wins = [r[2] for r in rows if r[2] is not None]
            m.roi_by_delay[delay] = {
                "roi": round(sum(rois) / len(rois), 6) if rois else None,
                "win_rate": round(sum(1 for w in wins if w) / len(wins), 4) if wins else None,
                "net_profit": float(sum(pnls, ZERO)) if pnls else None,
                "n": len(rows),
                "excluded_weak_evidence": attempted - len(rows),
                "avg_copyability": round(sum(r[3] for r in rows) / len(rows), 1),
            }

        bench = self.benchmark_delay
        bench_rows = self._measured_rows(complete, bench)
        m.copyable_coverage = (
            round(len(bench_rows) / len(complete), 4) if complete else None
        )
        if not bench_rows:
            # No copyable evidence at the benchmark: leave the copyable metrics
            # null rather than implying a measured zero.
            return

        bench_rois = [r[0] for r in bench_rows if r[0] is not None]
        bench_pnls = [r[1] for r in bench_rows if r[1] is not None]
        bench_wins = [r[2] for r in bench_rows if r[2] is not None]

        m.copyable_roi = round(sum(bench_rois) / len(bench_rois), 6)

        # Mean-of-ROI is convex on binary outcomes: a loss floors at -100% no
        # matter what price you paid, while a win at a cheap fill is unbounded.
        # Any noise in fill prices therefore biases the mean upward, and a
        # handful of lucky cheap fills on winners can manufacture an edge out of
        # nothing. Observed live: a 481-trade wallet reporting 11.3% copyable ROI
        # that fell to 0.5% once its ten best trades were removed.
        ordered_rois = sorted(bench_rois, reverse=True)
        m.copyable_roi_median = round(_median_float(bench_rois), 6)
        trim = max(1, len(ordered_rois) // 20)  # drop the top 5%
        remaining = ordered_rois[trim:]
        if remaining:
            m.copyable_roi_trimmed = round(sum(remaining) / len(remaining), 6)
            if m.copyable_roi > 0:
                # How much of the edge rests on the very best few trades.
                m.copyable_outlier_dependence = round(
                    1.0 - (max(m.copyable_roi_trimmed, 0.0) / m.copyable_roi), 4
                )
        m.copyable_net_profit = sum(bench_pnls, ZERO)
        m.copyable_win_rate = (
            round(sum(1 for w in bench_wins if w) / len(bench_wins), 4)
            if bench_wins
            else None
        )
        m.copyable_profit_factor = stats.profit_factor(bench_pnls)
        m.avg_copyability_score = round(
            sum(r[3] for r in bench_rows) / len(bench_rows), 1
        )

        boot = stats.bootstrap_mean(
            bench_rois, iterations=self.settings.bootstrap_iterations
        )
        if boot is not None:
            m.copyable_roi_ci_low = round(boot.ci_low, 6)
            m.copyable_roi_ci_high = round(boot.ci_high, 6)
            # Below the soft floor a bootstrap cannot separate edge from luck --
            # resampling 8 similar wins yields "100% probability of an edge",
            # which is precisely the false confidence this system must not emit.
            # Withholding the number is more honest than qualifying it in a
            # footnote the reader may not see.
            if len(bench_rois) >= self.settings.min_trades_soft_floor:
                m.prob_positive_edge = round(boot.prob_positive, 4)

        m.shrunk_copyable_roi = round(
            stats.bayesian_shrink(
                m.copyable_roi,
                len(bench_rois),
                self.population_mean,
                strength=self.settings.bayesian_shrinkage_strength,
            ),
            6,
        )

    # ------------------------------------------------------------ breakdowns
    def _group_by(
        self,
        positions: list[PositionRecord],
        key_fn,
        *,
        limit: int | None = None,
    ) -> dict:
        groups: dict[str, list[PositionRecord]] = defaultdict(list)
        for p in positions:
            key = key_fn(p)
            if key:
                groups[str(key)].append(p)
        result = {k: _breakdown(v, self.benchmark_delay) for k, v in groups.items()}
        if limit is not None and len(result) > limit:
            # Keep the most-traded groups; the long tail is noise.
            top = sorted(result.items(), key=lambda kv: kv[1]["n"], reverse=True)[:limit]
            result = dict(top)
        return result

    def _group_by_bucket(
        self,
        positions: list[PositionRecord],
        buckets: tuple[tuple[str, Decimal, Decimal], ...],
        value_fn,
    ) -> dict:
        groups: dict[str, list[PositionRecord]] = {name: [] for name, _, _ in buckets}
        for p in positions:
            value = value_fn(p)
            if value is None:
                continue
            for name, low, high in buckets:
                if low <= value < high:
                    groups[name].append(p)
                    break
        return {
            k: _breakdown(v, self.benchmark_delay) for k, v in groups.items() if v
        }

    def _by_period(self, positions: list[PositionRecord]) -> dict:
        """Rolling-window performance, plus phase and type splits."""
        out: dict[str, dict] = {}
        for days in LOOKBACK_WINDOWS:
            cutoff = self.now - timedelta(days=days)
            subset = [p for p in positions if p.occurred_at >= cutoff]
            out[f"last_{days}d"] = _breakdown(subset, self.benchmark_delay)

        for phase in (MarketPhase.PREMATCH, MarketPhase.LIVE):
            subset = [p for p in positions if p.entry_phase == phase]
            if subset:
                out[phase.value] = _breakdown(subset, self.benchmark_delay)

        for mtype in (TennisMarketType.MATCH_WINNER, TennisMarketType.SET_WINNER):
            subset = [p for p in positions if p.tennis_market_type == mtype]
            if subset:
                out[mtype.value] = _breakdown(subset, self.benchmark_delay)
        return out

    # ----------------------------------------------------------- data quality
    def _data_quality(self, positions: Sequence[PositionRecord]) -> float:
        """0-100 confidence in the underlying data for this wallet."""
        if not positions:
            return 0.0

        recon = sum(p.reconstruction_confidence for p in positions) / len(positions)

        bench = self.benchmark_delay
        graded = [
            p.copyable[bench][4] for p in positions if bench in p.copyable
        ]
        price_conf = sum(graded) / len(graded) if graded else 0.0
        coverage = len(graded) / len(positions) if positions else 0.0

        # Reconstruction quality, price-evidence quality, and how much of the
        # book we could actually price all matter.
        score = (recon * 0.4) + (price_conf * 0.4) + (coverage * 100.0 * 0.2)
        return round(max(0.0, min(100.0, score)), 1)

    def _risk_flags(self, m: MetricSet, positions: Sequence[PositionRecord]) -> list[str]:
        flags: list[str] = []
        s = self.settings

        if m.completed_positions < s.min_trades_soft_floor:
            flags.append(RiskFlag.SMALL_SAMPLE)
        if (m.pct_profit_from_largest_trade or 0) > 0.5:
            flags.append(RiskFlag.PROFIT_CONCENTRATION)
        if (m.max_drawdown or 0) > s.alert_max_drawdown:
            flags.append(RiskFlag.SEVERE_DRAWDOWN)
        if m.copyable_roi is not None and m.copyable_roi < 0:
            flags.append(RiskFlag.NEGATIVE_COPYABLE_ROI)

        recent = m.performance_by_period.get("last_30d", {})
        if recent.get("roi") is not None and recent["roi"] < 0:
            flags.append(RiskFlag.NEGATIVE_RECENT_TREND)

        mm = sum(1 for p in positions if p.behaviour == "likely_market_making")
        if positions and mm / len(positions) > 0.3:
            flags.append(RiskFlag.LIKELY_MARKET_MAKING)

        hedged = sum(1 for p in positions if RiskFlag.HEDGING_BEHAVIOUR in p.flags)
        if positions and hedged / len(positions) > 0.3:
            flags.append(RiskFlag.HEDGING_BEHAVIOUR)

        if (m.data_quality_score or 0) < 60:
            flags.append(RiskFlag.THIN_DATA)
        if m.copyable_coverage is not None and m.copyable_coverage < 0.5:
            # Most of the record could not be assessed for copyability at all.
            flags.append(RiskFlag.THIN_DATA)

        ambiguous = sum(1 for p in positions if p.reconstruction_confidence < 80)
        if positions and ambiguous / len(positions) > 0.2:
            flags.append(RiskFlag.AMBIGUOUS_RECONSTRUCTION)

        liq = [p.market_liquidity for p in positions if p.market_liquidity is not None]
        if liq and (sum(liq, ZERO) / Decimal(len(liq))) < s.alert_min_liquidity_usdc:
            flags.append(RiskFlag.LOW_LIQUIDITY_MARKETS)

        if positions:
            latest = max(p.opened_ts for p in positions)
            age_days = (self.now.timestamp() - latest) / 86400
            if age_days > 30:
                flags.append(RiskFlag.STALE_ACTIVITY)

        return list(dict.fromkeys(flags))


def _median_float(values: list[float]) -> float:
    """Median of a non-empty float list."""
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _median_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")


# Assumed bankroll as a multiple of typical stake. A trader betting $100 a time
# is not operating on $100 of capital, and measuring hundreds of trades' swings
# against a single bet's size makes every real strategy look catastrophic.
ASSUMED_BANKROLL_MULTIPLE = Decimal("10")


def _drawdown_base(stakes: list[Decimal]) -> Decimal:
    """Capital base for expressing drawdown as a percentage.

    Set to the larger of the biggest single stake and a bankroll of
    ``ASSUMED_BANKROLL_MULTIPLE`` x the median stake. Rationale:

    * Using the largest single stake alone understates the capital base, so a
      long P&L sequence shows an implausible drawdown (a 300-trade wallet betting
      $100 a time measured against $100 of capital).
    * Using cumulative volume overstates it, flattering a high-turnover wallet by
      making any decline look trivial against lifetime throughput.

    This is an explicit modelling assumption, not an observation: true wallet
    bankroll is not visible on-chain. It is documented in docs/SCORING.md and
    applied identically to every wallet, so comparisons stay fair.
    """
    if not stakes:
        return ZERO
    median = _median_decimal(stakes) or ZERO
    return max(max(stakes), median * ASSUMED_BANKROLL_MULTIPLE)


def compute_scope_metrics(
    positions: Sequence[PositionRecord],
    *,
    benchmark_delay_seconds: int | None = None,
    population_mean_copyable_roi: float = 0.0,
    now: datetime | None = None,
) -> dict[str, MetricSet]:
    """Compute every standard scope for one wallet."""
    calc = MetricsCalculator(
        benchmark_delay_seconds=benchmark_delay_seconds,
        population_mean_copyable_roi=population_mean_copyable_roi,
        now=now,
    )
    tennis = [p for p in positions if p.is_tennis]

    scopes: dict[str, Sequence[PositionRecord]] = {
        "overall": positions,
        "tennis": tennis,
        "tennis:prematch": [p for p in tennis if p.entry_phase == MarketPhase.PREMATCH],
        "tennis:live": [p for p in tennis if p.entry_phase == MarketPhase.LIVE],
        "tennis:match_winner": [
            p for p in tennis if p.tennis_market_type == TennisMarketType.MATCH_WINNER
        ],
        "tennis:set_winner": [
            p for p in tennis if p.tennis_market_type == TennisMarketType.SET_WINNER
        ],
    }

    now_dt = now or datetime.now(timezone.utc)
    for days in LOOKBACK_WINDOWS:
        cutoff = now_dt - timedelta(days=days)
        scopes[f"tennis:{days}d"] = [p for p in tennis if p.occurred_at >= cutoff]

    return {
        scope: calc.compute(scope, list(items))
        for scope, items in scopes.items()
        if items or scope in ("overall", "tennis")
    }


def population_mean_copyable_roi(all_metrics: Iterable[MetricSet]) -> float:
    """Sample-weighted population mean, used as the shrinkage prior.

    Weighting by sample size stops a handful of tiny, extreme wallets from
    dragging the prior around.
    """
    total_weight = 0
    total = 0.0
    for m in all_metrics:
        if m.copyable_roi is None or m.completed_positions <= 0:
            continue
        total += m.copyable_roi * m.completed_positions
        total_weight += m.completed_positions
    if total_weight == 0:
        # No evidence anywhere: assume no edge.
        return 0.0
    return round(total / total_weight, 6)
