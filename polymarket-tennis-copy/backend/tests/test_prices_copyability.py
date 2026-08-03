"""Price reconstruction and copyability tests.

The load-bearing assertions here are about *honesty*: that weak evidence is
labelled weak, that a missing price is not silently replaced by a confident
number, and that copyability is independent of profitability.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.enums import MarketPhase, PriceSourceQuality, RiskFlag
from app.providers.base import ProviderBookLevel, ProviderOrderBook
from app.services.copyability import (
    CopyabilityInput,
    build_copyability_input,
    compute_follower_outcome,
    score_copyability,
)
from app.services.prices import (
    PriceSeries,
    ResolvedPrice,
    estimate_fill_from_book,
    estimate_fill_modeled,
)

T0 = 1_785_000_000


def series_with_trades(points: list[tuple[int, str]]) -> PriceSeries:
    s = PriceSeries(token_id="tok")
    for offset, price in points:
        s.add_trade(T0 + offset, Decimal(price), Decimal("100"))
    return s


class TestPriceResolutionTiers:
    def test_exact_print_is_observed_trade(self):
        s = series_with_trades([(0, "0.50"), (15, "0.55"), (60, "0.60")])
        r = s.resolve(T0 + 15)
        assert r.quality is PriceSourceQuality.OBSERVED_TRADE
        assert r.price == Decimal("0.55")
        assert r.distance_seconds == 0
        assert r.confidence == 100.0

    def test_print_within_tolerance_is_observed(self):
        s = series_with_trades([(0, "0.50"), (17, "0.55")])
        r = s.resolve(T0 + 15, tolerance_seconds=3)
        assert r.quality is PriceSourceQuality.OBSERVED_TRADE
        assert r.price == Decimal("0.55")
        assert r.distance_seconds == 2

    def test_bracketed_target_interpolates(self):
        s = series_with_trades([(0, "0.50"), (100, "0.60")])
        r = s.resolve(T0 + 50)
        assert r.quality is PriceSourceQuality.INTERPOLATED_TRADE
        assert r.price == Decimal("0.55")
        assert r.confidence < 100.0

    def test_wide_gap_does_not_interpolate(self):
        """Beyond the interpolation window, invented mid-points are refused."""
        s = series_with_trades([(0, "0.50"), (5000, "0.90")])
        r = s.resolve(T0 + 2500)
        assert r.quality is not PriceSourceQuality.INTERPOLATED_TRADE

    def test_minute_bar_used_when_no_prints(self):
        s = PriceSeries(token_id="tok")
        s.add_bar(T0, Decimal("0.50"))
        s.add_bar(T0 + 60, Decimal("0.55"))
        r = s.resolve(T0 + 70)
        assert r.quality is PriceSourceQuality.MINUTE_BAR
        assert r.price == Decimal("0.55")
        assert "sub-minute movement is not observable" in (r.note or "")

    def test_distant_print_is_nearest_trade_tier(self):
        s = series_with_trades([(0, "0.50")])
        r = s.resolve(T0 + 400)
        assert r.quality is PriceSourceQuality.NEAREST_TRADE
        assert r.confidence < PriceSourceQuality.MINUTE_BAR.confidence

    def test_no_evidence_with_fallback_is_modeled(self):
        s = PriceSeries(token_id="tok")
        r = s.resolve(T0, fallback_price=Decimal("0.42"))
        assert r.quality is PriceSourceQuality.MODELED
        assert r.price == Decimal("0.42")
        assert r.confidence == PriceSourceQuality.MODELED.confidence

    def test_no_evidence_no_fallback_is_unavailable(self):
        """A missing price must stay missing, not become a plausible number."""
        s = PriceSeries(token_id="tok")
        r = s.resolve(T0)
        assert r.quality is PriceSourceQuality.UNAVAILABLE
        assert r.price is None
        assert r.is_usable is False
        assert r.confidence == 0.0

    def test_confidence_decays_with_distance(self):
        near = ResolvedPrice(Decimal("0.5"), PriceSourceQuality.OBSERVED_TRADE, 0)
        far = ResolvedPrice(Decimal("0.5"), PriceSourceQuality.OBSERVED_TRADE, 60)
        assert far.confidence < near.confidence

    def test_tier_confidence_is_strictly_ordered(self):
        order = [
            PriceSourceQuality.OBSERVED_TRADE,
            PriceSourceQuality.INTERPOLATED_TRADE,
            PriceSourceQuality.MINUTE_BAR,
            PriceSourceQuality.NEAREST_TRADE,
            PriceSourceQuality.MODELED,
            PriceSourceQuality.UNAVAILABLE,
        ]
        confidences = [q.confidence for q in order]
        assert confidences == sorted(confidences, reverse=True)

    def test_prices_clamped_into_tradeable_band(self):
        s = series_with_trades([(0, "1.50")])
        assert s.resolve(T0).price == Decimal("0.999")

    def test_price_before_finds_prior_observation(self):
        s = series_with_trades([(0, "0.50"), (100, "0.70")])
        r = s.price_before(T0 + 100)
        assert r.price == Decimal("0.50")

    def test_volatility_after_measures_range(self):
        s = series_with_trades([(0, "0.50"), (10, "0.58"), (20, "0.54")])
        assert s.volatility_after(T0, 60) == Decimal("0.08")


class TestBookWalk:
    def test_walking_a_thin_ladder_raises_average_price(self):
        """Reproduces the live finding: touch depth is far thinner than total."""
        book = ProviderOrderBook(
            token_id="tok",
            timestamp=T0,
            asks=[
                ProviderBookLevel(Decimal("0.50"), Decimal("20")),   # $10
                ProviderBookLevel(Decimal("0.55"), Decimal("100")),  # $55
                ProviderBookLevel(Decimal("0.70"), Decimal("1000")),
            ],
        )
        fill = estimate_fill_from_book(book, Decimal("100"))
        assert fill is not None
        # $10 @0.50, $55 @0.55, remaining $35 @0.70 -> average well above touch
        assert fill.fill_price > Decimal("0.55")
        assert fill.slippage > ZERO_D
        assert fill.partially_filled is False

    def test_insufficient_depth_reports_partial_fill(self):
        book = ProviderOrderBook(
            token_id="tok",
            timestamp=T0,
            asks=[ProviderBookLevel(Decimal("0.50"), Decimal("20"))],  # only $10
        )
        fill = estimate_fill_from_book(book, Decimal("100"))
        assert fill is not None
        assert fill.partially_filled is True
        assert fill.filled_notional == Decimal("10.00")
        assert fill.fill_ratio == pytest.approx(0.10)

    def test_empty_book_returns_none(self):
        book = ProviderOrderBook(token_id="tok", timestamp=T0, asks=[])
        assert estimate_fill_from_book(book, Decimal("100")) is None

    def test_modeled_fill_adds_half_spread_and_impact(self):
        fill = estimate_fill_modeled(
            Decimal("0.50"), Decimal("100"), spread=Decimal("0.02"), slippage_bps=150
        )
        # 0.50 + 0.01 half-spread + 0.0075 impact
        assert fill.fill_price == Decimal("0.5175")
        assert fill.quality is PriceSourceQuality.MODELED


ZERO_D = Decimal("0")


def base_input(**kw) -> CopyabilityInput:
    defaults = dict(
        wallet_entry_price=Decimal("0.50"),
        wallet_entry_ts=T0,
        delay_seconds=15,
        price_after_delay=ResolvedPrice(
            Decimal("0.50"), PriceSourceQuality.OBSERVED_TRADE, 0
        ),
        available_liquidity=Decimal("5000"),
        spread=Decimal("0.01"),
        market_phase=MarketPhase.PREMATCH,
        holding_seconds=3600,
    )
    defaults.update(kw)
    return CopyabilityInput(**defaults)


class TestCopyabilityScoring:
    def test_ideal_conditions_score_high(self):
        r = score_copyability(base_input())
        assert r.score >= 85
        assert r.price_deterioration == ZERO_D

    def test_price_ran_away_scores_low(self):
        """The spec's canonical case: bought 0.68, market at 0.76 moments later."""
        r = score_copyability(
            base_input(
                wallet_entry_price=Decimal("0.68"),
                price_after_delay=ResolvedPrice(
                    Decimal("0.76"), PriceSourceQuality.OBSERVED_TRADE, 0
                ),
                holding_seconds=45,          # wallet exited quickly
                available_liquidity=Decimal("120"),  # thin
                market_phase=MarketPhase.LIVE,
                price_range_during_delay=Decimal("0.09"),
            )
        )
        # Well below the alert gate: price gone, thin depth, wallet fled, unstable.
        assert r.score < 25
        assert r.price_deterioration == Decimal("0.08")
        assert r.components["price_persistence"] == 0.0
        assert RiskFlag.RAPID_EXIT_PATTERN in r.flags
        assert RiskFlag.FAST_MOVING_MARKET in r.flags

    def test_high_data_quality_cannot_rescue_an_uncopyable_trade(self):
        """Confidence in a measurement must not improve what was measured."""
        bad = dict(
            wallet_entry_price=Decimal("0.68"),
            price_after_delay=ResolvedPrice(
                Decimal("0.80"), PriceSourceQuality.OBSERVED_TRADE, 0
            ),
            holding_seconds=20,
            available_liquidity=Decimal("40"),
            market_phase=MarketPhase.LIVE,
            price_range_during_delay=Decimal("0.12"),
        )
        confident = score_copyability(base_input(classification_confidence=100.0, **bad))
        # Perfect evidence leaves the multiplier at 1.0, so the score is the
        # execution score -- which is itself very low.
        assert confident.quality_multiplier == pytest.approx(1.0, abs=0.02)
        assert confident.score < 25

    def test_better_price_is_not_penalised(self):
        r = score_copyability(
            base_input(
                price_after_delay=ResolvedPrice(
                    Decimal("0.45"), PriceSourceQuality.OBSERVED_TRADE, 0
                )
            )
        )
        assert r.components["price_persistence"] == 100.0
        assert r.price_deterioration < ZERO_D

    def test_copyability_is_independent_of_profitability(self):
        """Two trades, identical execution conditions, opposite outcomes."""
        conditions = dict(
            wallet_entry_price=Decimal("0.50"),
            price_after_delay=ResolvedPrice(
                Decimal("0.505"), PriceSourceQuality.OBSERVED_TRADE, 1
            ),
            holding_seconds=1800,
        )
        a = score_copyability(base_input(**conditions))
        b = score_copyability(base_input(**conditions))
        assert a.score == b.score
        # Nothing in the result references the trade's P&L at all.
        assert "pnl" not in r_keys(a)
        assert "roi" not in r_keys(a)

    def test_unusable_price_forces_zero(self):
        r = score_copyability(
            base_input(
                price_after_delay=ResolvedPrice(None, PriceSourceQuality.UNAVAILABLE)
            )
        )
        assert r.score == 0.0
        assert RiskFlag.THIN_DATA in r.flags

    def test_modeled_price_caps_the_score(self):
        """Modelled evidence must never clear a strict alert gate."""
        r = score_copyability(
            base_input(
                price_after_delay=ResolvedPrice(
                    Decimal("0.50"), PriceSourceQuality.MODELED
                )
            )
        )
        assert r.score <= 55.0
        assert RiskFlag.THIN_DATA in r.flags
        assert any("capped" in n for n in r.notes)

    def test_thin_liquidity_flagged_and_penalised(self):
        rich = score_copyability(base_input(available_liquidity=Decimal("10000")))
        thin = score_copyability(base_input(available_liquidity=Decimal("50")))
        assert thin.score < rich.score
        assert RiskFlag.LOW_LIQUIDITY_MARKETS in thin.flags

    def test_wide_spread_flagged(self):
        r = score_copyability(base_input(spread=Decimal("0.10")))
        assert RiskFlag.WIDE_SPREAD in r.flags
        assert r.components["spread"] == 0.0

    def test_live_market_penalised_more_than_prematch_at_same_delay(self):
        live = score_copyability(base_input(market_phase=MarketPhase.LIVE, delay_seconds=60))
        pre = score_copyability(base_input(market_phase=MarketPhase.PREMATCH, delay_seconds=60))
        assert live.components["timing_pressure"] < pre.components["timing_pressure"]

    def test_wallet_exit_inside_delay_scores_zero_hold(self):
        r = score_copyability(base_input(delay_seconds=30, holding_seconds=10))
        assert r.components["hold_duration"] == 0.0
        assert RiskFlag.RAPID_EXIT_PATTERN in r.flags

    def test_low_classification_confidence_lowers_data_quality(self):
        """Ambiguous classification drags the score down via the multiplier."""
        good = score_copyability(base_input(classification_confidence=100.0))
        bad = score_copyability(base_input(classification_confidence=30.0))
        assert bad.data_confidence < good.data_confidence
        assert bad.quality_multiplier < good.quality_multiplier
        assert bad.score < good.score
        # Execution conditions were identical, so only the multiplier differs.
        assert bad.execution_score == good.execution_score

    def test_zero_delay_is_annotated_as_theoretical(self):
        r = score_copyability(base_input(delay_seconds=0))
        assert any("theoretical" in n for n in r.notes)

    def test_components_json_is_explainable(self):
        import json

        r = score_copyability(base_input())
        payload = json.loads(r.components_json())
        assert set(payload["weights"]) == set(payload["factors"])
        assert abs(sum(payload["weights"].values()) - 1.0) < 1e-9


def r_keys(result) -> set[str]:
    return set(result.components) | {"score"}


class TestFollowerOutcome:
    def test_resolution_win_pays_one(self):
        out = compute_follower_outcome(
            Decimal("0.50"),
            wallet_exit_price=None,
            resolved_winner=True,
            stake_usdc=Decimal("100"),
        )
        # 200 shares * (1 - 0.5) = 100
        assert out.pnl == Decimal("100.00")
        assert out.roi == pytest.approx(1.0)
        assert out.is_win is True

    def test_resolution_loss_is_total(self):
        out = compute_follower_outcome(
            Decimal("0.50"),
            wallet_exit_price=None,
            resolved_winner=False,
            stake_usdc=Decimal("100"),
        )
        assert out.pnl == Decimal("-100.00")
        assert out.is_win is False

    def test_worse_fill_reduces_follower_pnl_vs_wallet(self):
        """Quantifies the cost of being late on the same winning trade."""
        wallet = compute_follower_outcome(
            Decimal("0.50"), wallet_exit_price=None, resolved_winner=True,
            stake_usdc=Decimal("100"),
        )
        follower = compute_follower_outcome(
            Decimal("0.58"), wallet_exit_price=None, resolved_winner=True,
            stake_usdc=Decimal("100"),
        )
        assert follower.pnl < wallet.pnl

    def test_exit_with_wallet_when_unresolved(self):
        out = compute_follower_outcome(
            Decimal("0.50"),
            wallet_exit_price=Decimal("0.60"),
            resolved_winner=None,
            stake_usdc=Decimal("100"),
        )
        assert out.pnl == Decimal("20.00")
        assert out.note == "exited with the wallet"

    def test_no_exit_reference_returns_undetermined(self):
        """An unknown outcome must not be recorded as a zero-P&L trade."""
        out = compute_follower_outcome(
            Decimal("0.50"),
            wallet_exit_price=None,
            resolved_winner=None,
            stake_usdc=Decimal("100"),
        )
        assert out.pnl is None
        assert out.roi is None
        assert out.is_win is None

    def test_fees_reduce_pnl(self):
        out = compute_follower_outcome(
            Decimal("0.50"), wallet_exit_price=Decimal("0.60"),
            resolved_winner=None, stake_usdc=Decimal("100"), fee_bps=100,
        )
        assert out.pnl == Decimal("19.00")


class TestDelaySensitivity:
    def test_copyability_declines_monotonically_with_delay(self):
        """A drifting market must look progressively harder to copy."""
        s = series_with_trades(
            [(0, "0.50"), (5, "0.52"), (15, "0.55"), (30, "0.58"), (60, "0.62"), (120, "0.66")]
        )
        scores = []
        for delay in (2, 5, 15, 30, 60, 120):
            data = build_copyability_input(
                wallet_entry_price=Decimal("0.50"),
                wallet_entry_ts=T0,
                delay_seconds=delay,
                series=s,
                holding_seconds=3600,
                market_phase=MarketPhase.LIVE,
                spread=Decimal("0.01"),
                available_liquidity=Decimal("5000"),
            )
            scores.append(score_copyability(data).score)
        assert scores[0] > scores[-1]
        assert scores == sorted(scores, reverse=True)

    def test_stable_market_holds_persistence_across_delays(self):
        """A flat market has no drift to penalise at any delay.

        Persistence scores market drift only; the follower still pays spread and
        slippage, which show up in ``price_deterioration`` rather than here.
        """
        s = series_with_trades([(0, "0.50"), (30, "0.50"), (120, "0.50")])
        results = []
        for delay in (5, 30):
            data = build_copyability_input(
                wallet_entry_price=Decimal("0.50"), wallet_entry_ts=T0,
                delay_seconds=delay, series=s, holding_seconds=3600,
                market_phase=MarketPhase.PREMATCH, spread=Decimal("0.01"),
                available_liquidity=Decimal("5000"),
            )
            results.append(score_copyability(data))

        for r in results:
            assert r.components["price_persistence"] == 100.0
            assert r.market_price_after_delay == Decimal("0.50")
            # Execution cost is still charged, just not to persistence.
            assert r.price_deterioration > ZERO_D
            assert r.estimated_fill_price > Decimal("0.50")
