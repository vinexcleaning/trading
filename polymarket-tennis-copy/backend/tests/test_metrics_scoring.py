"""Metrics, statistics and scoring tests.

The headline assertion is the spec's core requirement: a wallet with 8 lucky
winning trades must not outrank a wallet with 300 consistently profitable and
copyable trades, however flattering its raw ROI looks.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import MarketPhase, PositionStatus, RiskFlag, TennisMarketType
from app.services import statistics as stats
from app.services.metrics import (
    MetricsCalculator,
    PositionRecord,
    compute_scope_metrics,
    population_mean_copyable_roi,
)
from app.services.scoring import WalletScorer

NOW = datetime(2026, 7, 29, tzinfo=timezone.utc)
BENCH = 15


def pos(
    idx: int,
    *,
    pnl: str,
    stake: str = "100",
    entry: str = "0.50",
    days_ago: float = 5.0,
    copyable_roi: float | None = None,
    copyability: float = 85.0,
    data_conf: float = 95.0,
    market_type: str = TennisMarketType.MATCH_WINNER,
    phase: str = MarketPhase.PREMATCH,
    hold: int = 3600,
    behaviour: str = "directional",
    recon: float = 100.0,
    tournament: str = "Wimbledon",
    player: str = "Player A",
    liquidity: str = "20000",
    status: str = PositionStatus.SETTLED,
) -> PositionRecord:
    opened = int((NOW - timedelta(days=days_ago)).timestamp())
    pnl_d = Decimal(pnl)
    stake_d = Decimal(stake)
    roi = float(pnl_d / stake_d)
    if copyable_roi is None:
        # Default: follower captures slightly less than the wallet.
        copyable_roi = roi * 0.7
    return PositionRecord(
        position_id=idx,
        opened_ts=opened,
        closed_ts=opened + hold,
        status=status,
        is_tennis=True,
        tennis_market_type=market_type,
        entry_phase=phase,
        avg_entry_price=Decimal(entry),
        capital_committed=stake_d,
        net_pnl=pnl_d,
        roi=roi,
        is_win=pnl_d > 0,
        holding_seconds=hold,
        behaviour=behaviour,
        market_liquidity=Decimal(liquidity),
        tournament=tournament,
        player=player,
        reconstruction_confidence=recon,
        copyable={
            BENCH: (
                copyable_roi,
                stake_d * Decimal(str(copyable_roi)),
                copyable_roi > 0,
                copyability,
                data_conf,
            )
        },
    )


def lucky_wallet() -> list[PositionRecord]:
    """8 trades, all winners, huge ROI. Almost certainly luck."""
    return [pos(i, pnl="60", stake="100", days_ago=3 + i) for i in range(8)]


def grinder_wallet() -> list[PositionRecord]:
    """300 trades, modest and consistent edge, spread over a year."""
    rng = random.Random(42)
    out = []
    for i in range(300):
        win = rng.random() < 0.56
        pnl = "18" if win else "-14"
        out.append(
            pos(
                i,
                pnl=pnl,
                stake="100",
                days_ago=rng.uniform(1, 300),
                market_type=(
                    TennisMarketType.MATCH_WINNER if i % 3 else TennisMarketType.SET_WINNER
                ),
            )
        )
    return out


class TestStatistics:
    def test_bayesian_shrinkage_hits_small_samples_hardest(self):
        small = stats.bayesian_shrink(0.60, n=5, prior_mean=0.02, strength=30)
        large = stats.bayesian_shrink(0.60, n=300, prior_mean=0.02, strength=30)
        assert small < large
        # 5/(5+30) = 1/7 of the observed edge survives.
        assert small == pytest.approx(0.02 + (0.60 - 0.02) * (5 / 35), abs=1e-6)
        assert large > 0.5

    def test_shrinkage_with_no_trades_returns_prior(self):
        assert stats.bayesian_shrink(0.9, 0, 0.03) == 0.03

    def test_sample_confidence_is_concave_and_capped(self):
        assert stats.sample_confidence(0) == 0.0
        assert stats.sample_confidence(100, 100) == 100.0
        assert stats.sample_confidence(500, 100) == 100.0
        # Concave: doubling a small sample adds more than doubling a large one.
        assert (
            stats.sample_confidence(20) - stats.sample_confidence(10)
            > stats.sample_confidence(100) - stats.sample_confidence(90)
        )

    def test_bootstrap_is_deterministic(self):
        values = [0.1, -0.05, 0.2, 0.03, -0.1, 0.15]
        a = stats.bootstrap_mean(values, iterations=500)
        b = stats.bootstrap_mean(values, iterations=500)
        assert a is not None and b is not None
        assert a.ci_low == b.ci_low and a.ci_high == b.ci_high

    def test_bootstrap_ci_widens_with_smaller_samples(self):
        rng = random.Random(1)
        small = [rng.gauss(0.1, 0.3) for _ in range(8)]
        large = [rng.gauss(0.1, 0.3) for _ in range(400)]
        s = stats.bootstrap_mean(small, iterations=800)
        l = stats.bootstrap_mean(large, iterations=800)
        assert (s.ci_high - s.ci_low) > (l.ci_high - l.ci_low)

    def test_single_observation_reports_no_dispersion(self):
        r = stats.bootstrap_mean([0.25])
        assert r is not None and r.n == 1 and r.iterations == 0

    def test_profit_factor_none_when_no_losses(self):
        """An 'infinite' profit factor must not be rankable."""
        assert stats.profit_factor([Decimal("10"), Decimal("5")]) is None
        assert stats.profit_factor([Decimal("10"), Decimal("-5")]) == 2.0

    def test_expected_value_catches_the_high_win_rate_trap(self):
        """90% win rate buying at $0.95 is still a losing strategy."""
        # 9 wins of +$0.05/share, 1 loss of -$0.95/share on $100 stakes.
        pnls = [Decimal("5.26")] * 9 + [Decimal("-100")]
        stakes = [Decimal("100")] * 10
        ev = stats.expected_value_per_dollar(pnls, stakes)
        assert ev is not None and ev < 0

    def test_profit_concentration_measures_gross_profit_share(self):
        pnls = [Decimal("900"), Decimal("50"), Decimal("50"), Decimal("-200")]
        assert stats.profit_concentration(pnls, 1) == pytest.approx(0.9)
        assert stats.profit_concentration(pnls, 5) == pytest.approx(1.0)

    def test_drawdown_finds_peak_to_trough(self):
        seq = [Decimal("100"), Decimal("-30"), Decimal("-40"), Decimal("80")]
        dd = stats.compute_drawdown(seq, starting_capital=Decimal("100"))
        assert dd.max_drawdown_pct > 0
        assert dd.max_drawdown_abs == Decimal("70")
        assert len(dd.equity_curve) == 4

    def test_streaks(self):
        outcomes = [True, True, True, False, False, True]
        assert stats.longest_streak(outcomes, winning=True) == 3
        assert stats.longest_streak(outcomes, winning=False) == 2

    def test_stability_penalises_one_lucky_period(self):
        steady = stats.compute_stability([0.10, 0.12, 0.09, 0.11])
        lumpy = stats.compute_stability([0.80, -0.20, -0.15, -0.10])
        assert steady.stability_score > lumpy.stability_score

    def test_stability_neutral_when_too_few_slices(self):
        assert stats.compute_stability([0.1]).stability_score == 50.0


class TestMetrics:
    def test_basic_metrics_are_exact(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        positions = [
            pos(1, pnl="50", stake="100"),
            pos(2, pnl="-30", stake="100"),
            pos(3, pnl="20", stake="100"),
        ]
        m = calc.compute("tennis", positions)
        assert m.completed_positions == 3
        assert m.net_profit == Decimal("40")
        assert m.gross_profit == Decimal("70")
        assert m.gross_loss == Decimal("30")
        assert m.win_rate == pytest.approx(2 / 3, abs=1e-4)
        assert m.profit_factor == pytest.approx(70 / 30, abs=1e-3)
        assert m.roi == pytest.approx(40 / 300, abs=1e-6)

    def test_copyable_metrics_lag_raw_metrics(self):
        """The gap between raw and copyable is the product's core number."""
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        m = calc.compute("tennis", [pos(i, pnl="30", copyable_roi=0.10) for i in range(30)])
        assert m.roi == pytest.approx(0.30, abs=1e-6)
        assert m.copyable_roi == pytest.approx(0.10, abs=1e-6)
        assert m.copyable_roi < m.roi

    def test_positions_without_price_evidence_excluded_not_zeroed(self):
        """Unmeasurable trades must not dilute the copyable average with zeros."""
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        good = [pos(i, pnl="20", copyable_roi=0.15) for i in range(10)]
        blind = [pos(100 + i, pnl="20") for i in range(10)]
        for p in blind:
            p.copyable = {}  # no evidence at any delay
        m = calc.compute("tennis", good + blind)
        assert m.completed_positions == 20
        # Average reflects only the 10 measurable trades.
        assert m.copyable_roi == pytest.approx(0.15, abs=1e-6)
        assert m.roi_by_delay[BENCH]["n"] == 10

    def test_all_open_wallet_makes_no_performance_claim(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        open_pos = pos(1, pnl="0", status=PositionStatus.OPEN)
        open_pos.net_pnl = None
        m = calc.compute("tennis", [open_pos])
        assert m.completed_positions == 0
        assert m.roi is None
        assert m.win_rate is None

    def test_negative_copyable_roi_is_flagged(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        m = calc.compute(
            "tennis", [pos(i, pnl="10", copyable_roi=-0.05) for i in range(30)]
        )
        assert m.copyable_roi < 0
        assert RiskFlag.NEGATIVE_COPYABLE_ROI in m.risk_flags

    def test_concentration_flag_on_one_dominant_trade(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        positions = [pos(1, pnl="5000", stake="100")] + [
            pos(i, pnl="10", stake="100") for i in range(2, 25)
        ]
        m = calc.compute("tennis", positions)
        assert m.pct_profit_from_largest_trade > 0.9
        assert RiskFlag.PROFIT_CONCENTRATION in m.risk_flags

    def test_breakdowns_populate(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        positions = [
            pos(1, pnl="20", market_type=TennisMarketType.MATCH_WINNER, phase=MarketPhase.LIVE),
            pos(2, pnl="-10", market_type=TennisMarketType.SET_WINNER, phase=MarketPhase.PREMATCH),
            pos(3, pnl="30", market_type=TennisMarketType.MATCH_WINNER, entry="0.80"),
        ]
        m = calc.compute("tennis", positions)
        assert TennisMarketType.MATCH_WINNER in m.performance_by_market_type
        assert "Wimbledon" in m.performance_by_tournament
        assert m.performance_by_entry_bucket
        assert "last_30d" in m.performance_by_period
        assert MarketPhase.LIVE in m.performance_by_period

    def test_delay_curve_covers_every_delay(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        positions = []
        for i in range(20):
            p = pos(i, pnl="20")
            p.copyable = {
                0: (0.20, Decimal("20"), True, 95.0, 100.0),
                5: (0.16, Decimal("16"), True, 90.0, 100.0),
                BENCH: (0.12, Decimal("12"), True, 85.0, 100.0),
                60: (0.04, Decimal("4"), True, 70.0, 100.0),
            }
            positions.append(p)
        m = calc.compute("tennis", positions)
        assert set(m.roi_by_delay) == {0, 5, BENCH, 60}
        # Edge decays as delay grows.
        assert m.roi_by_delay[0]["roi"] > m.roi_by_delay[60]["roi"]

    def test_scope_split_by_phase_and_type(self):
        positions = [
            pos(1, pnl="20", phase=MarketPhase.LIVE),
            pos(2, pnl="20", phase=MarketPhase.PREMATCH),
            pos(3, pnl="20", market_type=TennisMarketType.SET_WINNER),
        ]
        scopes = compute_scope_metrics(positions, benchmark_delay_seconds=BENCH, now=NOW)
        assert "tennis" in scopes and "overall" in scopes
        assert scopes["tennis:live"].completed_positions == 1
        assert scopes["tennis:set_winner"].completed_positions == 1

    def test_population_mean_is_sample_weighted(self):
        calc = MetricsCalculator(benchmark_delay_seconds=BENCH, now=NOW)
        big = calc.compute("tennis", [pos(i, pnl="10", copyable_roi=0.05) for i in range(200)])
        tiny = calc.compute("tennis", [pos(i, pnl="90", copyable_roi=0.90) for i in range(2)])
        mean = population_mean_copyable_roi([big, tiny])
        # Dominated by the large sample, not the extreme tiny one.
        assert mean < 0.10


class TestScoringLuckVersusSkill:
    def _score(self, positions, population_mean=0.05):
        m = compute_scope_metrics(
            positions, benchmark_delay_seconds=BENCH,
            population_mean_copyable_roi=population_mean, now=NOW,
        )["tennis"]
        return m, WalletScorer(now=NOW).score(m)

    def test_grinder_outranks_lucky_small_sample(self):
        """The spec's central requirement."""
        lucky_m, lucky_s = self._score(lucky_wallet())
        grind_m, grind_s = self._score(grinder_wallet())

        # The lucky wallet genuinely has the better raw AND copyable point estimate.
        assert lucky_m.copyable_roi > grind_m.copyable_roi
        # But it must not outrank the grinder.
        assert grind_s.skill_score > lucky_s.skill_score
        # And it must not be alertable.
        assert lucky_s.qualified is False
        assert any("completed tennis trades" in r for r in lucky_s.disqualification_reasons)

    def test_shrinkage_collapses_the_lucky_edge(self):
        lucky_m, _ = self._score(lucky_wallet())
        assert lucky_m.copyable_roi > 0.3
        # Shrunk toward a 5% population mean on 8 trades.
        assert lucky_m.shrunk_copyable_roi < lucky_m.copyable_roi / 2

    def test_small_sample_penalty_and_flag_applied(self):
        _, s = self._score(lucky_wallet())
        assert "below_min_trades" in s.penalties
        assert RiskFlag.SMALL_SAMPLE in s.risk_flags
        assert s.confidence_level in ("insufficient", "low")

    def test_grinder_reaches_meaningful_confidence(self):
        m, s = self._score(grinder_wallet())
        assert m.completed_positions == 300
        assert s.confidence_level in ("medium", "high")
        assert "below_min_trades" not in s.penalties


class TestScoringBehaviour:
    def _score(self, positions):
        m = compute_scope_metrics(
            positions, benchmark_delay_seconds=BENCH, now=NOW
        )["tennis"]
        return m, WalletScorer(now=NOW).score(m)

    def test_negative_copyable_roi_disqualifies_despite_raw_profit(self):
        """A profitable wallet nobody can copy must not qualify."""
        positions = [
            pos(i, pnl="40", stake="100", copyable_roi=-0.03) for i in range(60)
        ]
        m, s = self._score(positions)
        assert m.roi > 0                      # wallet made money
        assert m.copyable_roi < 0             # follower would not have
        assert s.qualified is False
        assert "negative_copyable_roi" in s.penalties

    def test_market_making_behaviour_disqualifies(self):
        positions = [
            pos(i, pnl="5", behaviour="likely_market_making") for i in range(60)
        ]
        _, s = self._score(positions)
        assert "market_making" in s.penalties
        assert s.qualified is False

    def test_severe_drawdown_penalised(self):
        positions = (
            [pos(i, pnl="100", stake="100", days_ago=200 - i) for i in range(10)]
            + [pos(50 + i, pnl="-95", stake="100", days_ago=100 - i) for i in range(20)]
            + [pos(80 + i, pnl="20", stake="100", days_ago=50 - i) for i in range(30)]
        )
        m, s = self._score(positions)
        assert m.max_drawdown > 0
        assert s.skill_score < 75

    def test_score_components_are_all_present_and_bounded(self):
        _, s = self._score(grinder_wallet())
        expected = {
            "copyable_roi", "profit_factor", "sample_confidence", "consistency",
            "drawdown", "recency", "liquidity_fit", "concentration", "data_quality",
        }
        assert set(s.components) == expected
        assert all(0.0 <= v <= 100.0 for v in s.components.values())
        assert 0.0 <= s.skill_score <= 100.0

    def test_explanation_is_human_readable_and_specific(self):
        _, s = self._score(grinder_wallet())
        assert "Copyable ROI" in s.explanation
        assert "delay" in s.explanation
        assert str(len(grinder_wallet())) in s.explanation or "300" in s.explanation

    def test_weights_sum_to_one(self):
        from app.config import get_settings

        assert abs(sum(get_settings().score_weights.values()) - 1.0) < 1e-9

    def test_penalties_compound_multiplicatively(self):
        positions = [
            pos(i, pnl="5", copyable_roi=-0.02, behaviour="likely_market_making")
            for i in range(10)
        ]
        _, s = self._score(positions)
        assert len(s.penalties) >= 2
        expected = 1.0
        for v in s.penalties.values():
            expected *= v
        # Stored rounded to 4dp.
        assert s.total_penalty_multiplier == pytest.approx(expected, abs=5e-5)
        assert s.skill_score < s.base_score

    def test_no_copyable_evidence_cannot_qualify(self):
        positions = [pos(i, pnl="30") for i in range(60)]
        for p in positions:
            p.copyable = {}
        m, s = self._score(positions)
        assert m.copyable_roi is None
        assert s.qualified is False
        assert any("copyable ROI" in r for r in s.disqualification_reasons)


def test_drawdown_percentage_never_exceeds_one():
    """A modelled bankroll can be exceeded; the reported ratio should not be.

    The capital base is an assumption, so a wallet that loses more than it shows
    a raw ratio above 1.0. Reporting "190% drawdown" reads as losing more than
    everything; the absolute figure carries the real magnitude instead.
    """
    from decimal import Decimal

    from app.services import statistics as stats

    # Base of 100 against cumulative losses far exceeding it.
    result = stats.compute_drawdown(
        [Decimal("-50"), Decimal("-100"), Decimal("-150")],
        starting_capital=Decimal("100"),
    )
    assert result.max_drawdown_pct == 1.0
    assert all(d <= 1.0 for d in result.drawdown_curve)
    # The uncapped magnitude is still available.
    assert result.max_drawdown_abs == Decimal("300")


def test_normal_drawdown_is_unaffected_by_the_cap():
    from decimal import Decimal

    from app.services import statistics as stats

    result = stats.compute_drawdown(
        [Decimal("50"), Decimal("-30"), Decimal("20")], starting_capital=Decimal("100")
    )
    # Peak 150, trough 120 -> 20%.
    assert 0.0 < result.max_drawdown_pct < 1.0


# ------------------------------------------------------------- activity gate

NOW_TS = 1_785_000_000
WEEK = 7 * 86_400


def test_stray_early_trades_do_not_buy_a_long_track_record():
    """The real pattern that fooled the span gate: a couple of trades months ago
    plus a recent burst reads as a long history, and is not one."""
    stale = [NOW_TS - 190 * 86_400, NOW_TS - 160 * 86_400]
    recent = [NOW_TS - 3 * 86_400, NOW_TS - 5 * 86_400]
    span_days = (max(stale + recent) - min(stale + recent)) / 86_400

    assert span_days > 180  # what the old gate saw
    assert stats.active_periods(stale + recent, now_ts=NOW_TS) == 1  # what it did


def test_consistent_trader_fills_its_recent_weeks():
    weekly = [NOW_TS - int((i + 0.5) * WEEK) for i in range(8)]
    assert stats.active_periods(weekly, now_ts=NOW_TS, lookback_periods=8) == 8


def test_gaps_inside_the_window_are_counted_as_gaps():
    # Weeks 0, 1 and 5 only.
    ts = [NOW_TS - 86_400, NOW_TS - 8 * 86_400, NOW_TS - 36 * 86_400]
    assert stats.active_periods(ts, now_ts=NOW_TS, lookback_periods=8) == 3


def test_activity_older_than_the_window_is_ignored():
    assert stats.active_periods([NOW_TS - 400 * 86_400], now_ts=NOW_TS) == 0


def test_many_trades_in_one_week_count_once():
    burst = [NOW_TS - 86_400 - i * 3600 for i in range(20)]
    assert stats.active_periods(burst, now_ts=NOW_TS) == 1


def test_activity_gate_edge_cases():
    assert stats.active_periods([], now_ts=NOW_TS) == 0
    assert stats.active_periods([NOW_TS], now_ts=NOW_TS, lookback_periods=0) == 0
    # Future timestamps are data errors, not activity.
    assert stats.active_periods([NOW_TS + 86_400], now_ts=NOW_TS) == 0


# --------------------------------------------------- favourite-longshot risk


def _longshot_metrics(**overrides):
    """A wallet buying ~$0.95 favourites: wins tiny and often, loses huge."""
    from decimal import Decimal

    from app.services.metrics import MetricSet

    base = dict(
        scope="tennis",
        completed_positions=181,
        total_positions=181,
        win_rate=0.989,
        gross_profit=Decimal("1290.62"),
        gross_loss=Decimal("201.13"),
        net_profit=Decimal("1089.49"),
        roi=0.048,
        copyable_roi=0.031,
        shrunk_copyable_roi=0.018,
        profit_factor=6.42,
        max_drawdown=0.068,
        avg_entry_price=Decimal("0.945"),
        benchmark_delay_seconds=15,
    )
    base.update(overrides)
    return MetricSet(**base)


def test_favourite_longshot_shape_is_flagged_and_penalised():
    """The spec's trap, found in real data and now caught.

    Two losses in 181 trades cannot establish a loss rate, and this strategy's
    sign depends entirely on that unmeasured number. A 98.9% win rate with a
    6.4 profit factor otherwise looks outstanding.
    """
    from app.enums import RiskFlag
    from app.services.scoring import WalletScorer

    result = WalletScorer().score(_longshot_metrics())

    assert RiskFlag.TAIL_RISK_ASYMMETRY in result.risk_flags
    assert "tail_risk_asymmetry" in result.penalties
    assert result.penalties["tail_risk_asymmetry"] < 1.0


def test_balanced_wallet_is_not_flagged_for_tail_risk():
    """A normal win/loss profile must not trip the detector."""
    from decimal import Decimal

    from app.enums import RiskFlag
    from app.services.scoring import WalletScorer

    result = WalletScorer().score(
        _longshot_metrics(
            win_rate=0.58,
            gross_profit=Decimal("2000"),
            gross_loss=Decimal("1200"),
            profit_factor=1.67,
        )
    )
    assert RiskFlag.TAIL_RISK_ASYMMETRY not in result.risk_flags


def test_high_win_rate_with_symmetric_sizing_is_not_flagged():
    """High win rate alone is not the problem -- the asymmetry is."""
    from decimal import Decimal

    from app.enums import RiskFlag
    from app.services.scoring import WalletScorer

    # 90% win rate, but average loss is only ~1.5x the average win.
    result = WalletScorer().score(
        _longshot_metrics(
            completed_positions=100,
            win_rate=0.90,
            gross_profit=Decimal("900"),   # 90 wins x $10
            gross_loss=Decimal("150"),     # 10 losses x $15
        )
    )
    assert RiskFlag.TAIL_RISK_ASYMMETRY not in result.risk_flags


def test_copyable_roi_exposes_outlier_dependence():
    """Mean-of-ROI is convex on binary outcomes and must not stand alone.

    A loss floors at -100% whatever price you paid; a win at a cheap fill is
    unbounded. So a few lucky cheap fills on winners can manufacture an edge.
    Observed live: a 481-trade wallet reporting 11.3% copyable ROI that fell to
    0.5% once its ten best trades were removed.
    """
    from decimal import Decimal

    from app.services.metrics import PositionRecord, compute_scope_metrics

    positions = []
    # 30 losers and 65 barely-positive winners -> flat on its own, plus 5 huge
    # convex outliers that drag the mean positive.
    rois = [-1.0] * 30 + [0.02] * 65 + [9.0, 7.5, 5.8, 5.4, 4.3]
    for i, roi in enumerate(rois):
        pnl = Decimal(str(round(100 * roi, 2)))
        positions.append(
            PositionRecord(
                position_id=i,
                opened_ts=1_700_000_000 + i * 3600,
                closed_ts=1_700_000_000 + i * 3600 + 1800,
                status="settled",
                is_tennis=True,
                tennis_market_type="match_winner",
                entry_phase="prematch",
                avg_entry_price=Decimal("0.5"),
                capital_committed=Decimal("100"),
                net_pnl=pnl,
                roi=roi,
                is_win=roi > 0,
                holding_seconds=1800,
                behaviour="directional",
                copyable={15: (roi, pnl, roi > 0, 90.0, 100.0)},
            )
        )

    metrics = compute_scope_metrics(positions, benchmark_delay_seconds=15)["tennis"]

    assert metrics.copyable_roi is not None
    # The trimmed figure strips the top 5% and must be materially lower.
    assert metrics.copyable_roi_trimmed < metrics.copyable_roi
    # And the dependence measure should show most of the edge is outliers.
    assert metrics.copyable_outlier_dependence > 0.5
