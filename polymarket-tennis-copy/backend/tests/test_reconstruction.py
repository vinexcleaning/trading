"""Trade reconstruction tests.

These assert exact Decimal arithmetic. Reconstruction feeds every downstream
metric, so an off-by-a-lot error here would silently corrupt wallet scores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.enums import ActivityType, MarketPhase, PositionBehaviour, PositionStatus, TradeSide
from app.services.reconstruction import (
    MarketContext,
    TradeReconstructor,
    TxInput,
)

TOKEN_A = "1000000000000000000000000000000000000000000000000000000000000000000000000001"
TOKEN_B = "1000000000000000000000000000000000000000000000000000000000000000000000000002"
COND = "0xcondition"

BASE_TS = 1_785_000_000


def tx(
    ts_offset: int,
    side: str | None,
    size: str,
    price: str | None,
    *,
    activity: str = ActivityType.TRADE,
    token: str = TOKEN_A,
    outcome_index: int = 0,
    tx_id: int | None = None,
    usdc: str | None = None,
    fee: str | None = None,
) -> TxInput:
    return TxInput(
        id=tx_id if tx_id is not None else ts_offset,
        timestamp=BASE_TS + ts_offset,
        activity_type=activity,
        size=Decimal(size),
        side=side,
        price=Decimal(price) if price is not None else None,
        usdc_size=Decimal(usdc) if usdc is not None else None,
        fee_usdc=Decimal(fee) if fee is not None else None,
        token_id=token,
        condition_id=COND,
        outcome_index=outcome_index,
    )


def ctx(
    *, resolved: bool = False, winner: int | None = None, start_offset: int | None = None
) -> MarketContext:
    return MarketContext(
        condition_id=COND,
        resolved=resolved,
        winning_outcome_index=winner,
        resolved_at=datetime.fromtimestamp(BASE_TS + 10_000, tz=timezone.utc),
        game_start_time=(
            datetime.fromtimestamp(BASE_TS + start_offset, tz=timezone.utc)
            if start_offset is not None
            else None
        ),
        is_tennis=True,
    )


class TestSimpleRoundTrip:
    def test_buy_then_full_sell_realizes_exact_pnl(self):
        r = TradeReconstructor()
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.40"),
                tx(600, TradeSide.SELL, "100", "0.55"),
            ]
        )
        assert len(positions) == 1
        p = positions[0]
        assert p.status == PositionStatus.CLOSED
        # 100 shares * (0.55 - 0.40) = 15.00 exactly
        assert p.realized_pnl == Decimal("15.00")
        assert p.net_pnl == Decimal("15.00")
        assert p.capital_committed == Decimal("40.00")
        assert p.avg_entry_price == Decimal("0.40")
        assert p.avg_exit_price == Decimal("0.55")
        assert p.roi == pytest.approx(0.375)
        assert p.is_win is True
        assert p.holding_seconds == 600
        assert p.accumulated is False

    def test_losing_trade(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [tx(0, TradeSide.BUY, "50", "0.70"), tx(300, TradeSide.SELL, "50", "0.60")]
        )[0]
        assert p.realized_pnl == Decimal("-5.00")
        assert p.is_win is False

    def test_fees_reduce_net_but_not_gross(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.40", fee="0.50"),
                tx(60, TradeSide.SELL, "100", "0.45", fee="0.50"),
            ]
        )[0]
        assert p.realized_pnl == Decimal("5.00")
        assert p.fees_paid == Decimal("1.00")
        assert p.net_pnl == Decimal("4.00")


class TestAccumulation:
    def test_scaled_entry_is_one_position_not_three(self):
        """The core anti-double-counting guarantee."""
        r = TradeReconstructor()
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.50"),
                tx(30, TradeSide.BUY, "100", "0.60"),
                tx(60, TradeSide.BUY, "200", "0.55"),
                tx(900, TradeSide.SELL, "400", "0.70"),
            ]
        )
        assert len(positions) == 1
        p = positions[0]
        assert p.entry_tx_count == 3
        assert p.accumulated is True
        assert p.total_shares_bought == Decimal("400")
        # Weighted average: (100*.5 + 100*.6 + 200*.55) / 400 = 220/400 = 0.55
        assert p.avg_entry_price == Decimal("0.55")
        assert p.capital_committed == Decimal("220.00")
        # 400 * (0.70 - 0.55) = 60
        assert p.realized_pnl == Decimal("60.00")
        assert p.scaled_in_at_worse_prices is True
        assert p.max_shares == Decimal("400")

    def test_successive_round_trips_are_separate_sequences(self):
        r = TradeReconstructor()
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.40"),
                tx(100, TradeSide.SELL, "100", "0.50"),
                tx(200, TradeSide.BUY, "100", "0.45"),
                tx(300, TradeSide.SELL, "100", "0.55"),
            ]
        )
        assert len(positions) == 2
        assert [p.sequence for p in positions] == [1, 2]
        assert all(p.status == PositionStatus.CLOSED for p in positions)
        assert positions[0].realized_pnl == Decimal("10.00")
        assert positions[1].realized_pnl == Decimal("10.00")


class TestPartialExits:
    def test_fifo_consumes_oldest_lots_first(self):
        r = TradeReconstructor("fifo")
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.30"),
                tx(10, TradeSide.BUY, "100", "0.50"),
                tx(20, TradeSide.SELL, "100", "0.60"),  # closes the 0.30 lot
            ]
        )
        p = positions[0]
        assert p.status == PositionStatus.PARTIALLY_CLOSED
        assert p.partial_exit_count == 1
        # FIFO: 100 * (0.60 - 0.30) = 30
        assert p.realized_pnl == Decimal("30.00")
        assert p.current_shares == Decimal("100")

    def test_weighted_average_uses_blended_basis(self):
        r = TradeReconstructor("weighted_average")
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.30"),
                tx(10, TradeSide.BUY, "100", "0.50"),
                tx(20, TradeSide.SELL, "100", "0.60"),
            ]
        )
        p = positions[0]
        # Blended basis 0.40 -> 100 * (0.60 - 0.40) = 20
        assert p.realized_pnl == Decimal("20.00")

    def test_both_methods_agree_on_completed_round_trip_total(self):
        """Methods differ per-exit but must reconcile over the full round trip."""
        txs = [
            tx(0, TradeSide.BUY, "100", "0.30"),
            tx(10, TradeSide.BUY, "100", "0.50"),
            tx(20, TradeSide.SELL, "100", "0.60"),
            tx(30, TradeSide.SELL, "100", "0.45"),
        ]
        fifo = TradeReconstructor("fifo").reconstruct(list(txs))[0]
        wavg = TradeReconstructor("weighted_average").reconstruct(list(txs))[0]
        assert fifo.status == PositionStatus.CLOSED
        assert wavg.status == PositionStatus.CLOSED
        # Total: proceeds 60+45=105, cost 30+50=80 -> +25 either way.
        assert fifo.realized_pnl == Decimal("25.00")
        assert wavg.realized_pnl == Decimal("25.00")

    def test_multiple_partial_exits_counted(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "300", "0.40"),
                tx(10, TradeSide.SELL, "100", "0.50"),
                tx(20, TradeSide.SELL, "100", "0.55"),
                tx(30, TradeSide.SELL, "100", "0.60"),
            ]
        )[0]
        assert p.partial_exit_count == 2  # third exit closes it
        assert p.exit_tx_count == 3
        assert p.status == PositionStatus.CLOSED
        # 100*.1 + 100*.15 + 100*.2 = 45
        assert p.realized_pnl == Decimal("45.00")
        # Weighted average exit = (50+55+60)/300 = 0.55
        assert p.avg_exit_price == Decimal("0.55")


class TestSettlement:
    def test_redeem_on_winning_outcome_prices_at_one(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.60"),
                tx(5000, None, "100", None, activity=ActivityType.REDEEM),
            ],
            {COND: ctx(resolved=True, winner=0)},
        )[0]
        assert p.status == PositionStatus.SETTLED
        assert p.settled_by_redemption is True
        # Winner redeems at $1: 100 * (1.00 - 0.60) = 40
        assert p.realized_pnl == Decimal("40.00")
        assert p.is_win is True

    def test_redeem_on_losing_outcome_prices_at_zero(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.60", outcome_index=1),
                tx(5000, None, "100", None, activity=ActivityType.REDEEM, outcome_index=1),
            ],
            {COND: ctx(resolved=True, winner=0)},
        )[0]
        # Loser is worthless: 100 * (0 - 0.60) = -60
        assert p.realized_pnl == Decimal("-60.00")
        assert p.is_win is False

    def test_open_position_in_resolved_market_is_settled_analytically(self):
        """A winner with no observed REDEEM must not be stranded as 'open'."""
        r = TradeReconstructor()
        p = r.reconstruct(
            [tx(0, TradeSide.BUY, "100", "0.25")],
            {COND: ctx(resolved=True, winner=0)},
        )[0]
        assert p.status == PositionStatus.SETTLED
        assert p.realized_pnl == Decimal("75.00")
        assert p.is_win is True
        assert any("settled analytically" in n for n in p.notes)

    def test_open_position_in_unresolved_market_stays_open(self):
        r = TradeReconstructor()
        p = r.reconstruct([tx(0, TradeSide.BUY, "100", "0.25")], {COND: ctx()})[0]
        assert p.status == PositionStatus.OPEN
        assert p.is_win is None
        assert p.roi is not None  # capital committed is known

    def test_settlement_disabled_leaves_position_open(self):
        r = TradeReconstructor(settle_resolved_markets=False)
        p = r.reconstruct(
            [tx(0, TradeSide.BUY, "100", "0.25")], {COND: ctx(resolved=True, winner=0)}
        )[0]
        assert p.status == PositionStatus.OPEN


class TestEdgeCases:
    def test_exit_without_entry_is_skipped_not_invented(self):
        """Shares acquired before our window must not produce a fabricated P&L."""
        r = TradeReconstructor()
        positions = r.reconstruct([tx(0, TradeSide.SELL, "100", "0.50")])
        assert positions == []

    def test_oversized_exit_clamps_to_held_shares(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [tx(0, TradeSide.BUY, "50", "0.40"), tx(10, TradeSide.SELL, "500", "0.60")]
        )[0]
        assert p.total_shares_sold == Decimal("50")
        assert p.realized_pnl == Decimal("10.00")
        assert p.current_shares == Decimal("0")

    def test_price_derived_from_usdc_when_absent(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", None, usdc="42.50"),
                tx(10, TradeSide.SELL, "100", "0.50"),
            ]
        )[0]
        assert p.avg_entry_price == Decimal("0.425")
        assert p.realized_pnl == Decimal("7.50")

    def test_unpriced_exit_flags_low_confidence(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [tx(0, TradeSide.BUY, "100", "0.40"), tx(10, TradeSide.SELL, "100", None)]
        )[0]
        assert p.reconstruction_confidence < 80.0
        assert p.realized_pnl == Decimal("0")  # assumed break-even, not invented
        assert any("break-even" in n for n in p.notes)

    def test_transactions_are_sorted_before_processing(self):
        """Out-of-order input must not mis-assign lots."""
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(900, TradeSide.SELL, "400", "0.70"),
                tx(60, TradeSide.BUY, "200", "0.55"),
                tx(0, TradeSide.BUY, "100", "0.50"),
                tx(30, TradeSide.BUY, "100", "0.60"),
            ]
        )[0]
        assert p.avg_entry_price == Decimal("0.55")
        assert p.realized_pnl == Decimal("60.00")

    def test_rebates_credited_without_creating_exposure(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.40"),
                tx(5, None, "0", None, activity=ActivityType.MAKER_REBATE, usdc="0.25"),
                tx(10, TradeSide.SELL, "100", "0.45"),
            ]
        )[0]
        assert p.total_shares_bought == Decimal("100")
        assert p.fees_paid == Decimal("-0.25")  # a credit
        assert p.net_pnl == Decimal("5.25")

    def test_dust_remainder_closes_position(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.40"),
                tx(10, TradeSide.SELL, "99.9999999", "0.50"),
            ]
        )[0]
        assert p.status == PositionStatus.CLOSED


class TestPhaseAndBehaviour:
    def test_prematch_vs_live_from_game_start(self):
        r = TradeReconstructor()
        pre = r.reconstruct(
            [tx(0, TradeSide.BUY, "100", "0.40"), tx(50, TradeSide.SELL, "100", "0.45")],
            {COND: ctx(start_offset=1000)},
        )[0]
        assert pre.entry_phase == MarketPhase.PREMATCH

        live = r.reconstruct(
            [tx(2000, TradeSide.BUY, "100", "0.40"), tx(2050, TradeSide.SELL, "100", "0.45")],
            {COND: ctx(start_offset=1000)},
        )[0]
        assert live.entry_phase == MarketPhase.LIVE

    def test_fast_round_trip_flagged_as_scalp(self):
        r = TradeReconstructor()
        p = r.reconstruct(
            [tx(0, TradeSide.BUY, "100", "0.40"), tx(30, TradeSide.SELL, "100", "0.42")]
        )[0]
        assert p.behaviour == PositionBehaviour.SCALP

    def test_holding_both_outcomes_flagged_as_hedge_or_arb(self):
        """Simultaneous both-sides exposure is not a directional bet."""
        r = TradeReconstructor()
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.45", token=TOKEN_A, outcome_index=0),
                tx(10, TradeSide.BUY, "100", "0.50", token=TOKEN_B, outcome_index=1),
                tx(500, TradeSide.SELL, "100", "0.55", token=TOKEN_A, outcome_index=0),
                tx(510, TradeSide.SELL, "100", "0.48", token=TOKEN_B, outcome_index=1),
            ]
        )
        assert len(positions) == 2
        assert all(p.held_both_outcomes for p in positions)
        assert all(
            p.behaviour
            in (PositionBehaviour.POSSIBLE_ARBITRAGE, PositionBehaviour.POSSIBLE_HEDGE)
            for p in positions
        )

    def test_sequential_both_sides_is_not_a_hedge(self):
        """Non-overlapping trades on both outcomes are two directional views."""
        r = TradeReconstructor()
        positions = r.reconstruct(
            [
                tx(0, TradeSide.BUY, "100", "0.45", token=TOKEN_A, outcome_index=0),
                tx(100, TradeSide.SELL, "100", "0.50", token=TOKEN_A, outcome_index=0),
                tx(200, TradeSide.BUY, "100", "0.40", token=TOKEN_B, outcome_index=1),
                tx(300, TradeSide.SELL, "100", "0.44", token=TOKEN_B, outcome_index=1),
            ]
        )
        assert len(positions) == 2
        assert not any(p.held_both_outcomes for p in positions)

    def test_repeated_flipping_flagged_as_market_making(self):
        r = TradeReconstructor()
        txs = [
            tx(0, TradeSide.BUY, "100", "0.50"),
            tx(10, TradeSide.SELL, "50", "0.51"),
            tx(20, TradeSide.BUY, "50", "0.50"),
            tx(30, TradeSide.SELL, "50", "0.51"),
            tx(40, TradeSide.BUY, "50", "0.50"),
            tx(50, TradeSide.SELL, "100", "0.51"),
        ]
        p = r.reconstruct(txs)[0]
        assert p.behaviour == PositionBehaviour.LIKELY_MARKET_MAKING


class TestDeterminism:
    def test_repeated_runs_produce_identical_results(self):
        txs = [
            tx(0, TradeSide.BUY, "100", "0.50", tx_id=1),
            tx(0, TradeSide.BUY, "100", "0.60", tx_id=2),
            tx(100, TradeSide.SELL, "200", "0.65", tx_id=3),
        ]
        a = TradeReconstructor().reconstruct(list(txs))[0]
        b = TradeReconstructor().reconstruct(list(reversed(txs)))[0]
        assert a.realized_pnl == b.realized_pnl
        assert a.avg_entry_price == b.avg_entry_price

    def test_no_float_contamination(self):
        """Every monetary output must remain Decimal."""
        p = TradeReconstructor().reconstruct(
            [tx(0, TradeSide.BUY, "33", "0.37"), tx(10, TradeSide.SELL, "33", "0.61")]
        )[0]
        for value in (
            p.realized_pnl,
            p.net_pnl,
            p.capital_committed,
            p.avg_entry_price,
            p.fees_paid,
        ):
            assert isinstance(value, Decimal)
        # 33 * 0.24 = 7.92 exactly -- a float would give 7.920000000000001
        assert p.realized_pnl == Decimal("7.92")
