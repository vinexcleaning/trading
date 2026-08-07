"""The execution model. Every one of these asserts a way this repo has
previously produced a fake profit."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from common.kalshi_fees import TAKER_RATE, fee_order_cents, fee_rate_cents  # noqa: E402
from src.engine import (MAX_DEPTH_FRACTION, Ledger, PaperEngine, PendingOrder,  # noqa: E402
                        Position, hold_cost_cents, round_trip_cost_cents)
from src.kalshi_read import MatchView, Quote  # noqa: E402
from src.sizing import choose_stake  # noqa: E402


def q(ticker, bid, ask, bidsz=1000.0, asksz=1000.0, event="E1", player="P"):
    return Quote(ticker=ticker, event_ticker=event, series="KXATPMATCH",
                 player=player, yes_bid=bid, yes_ask=ask,
                 yes_bid_size=bidsz, yes_ask_size=asksz, last=ask,
                 volume=100.0, open_interest=100.0, status="active",
                 open_time=None, expected_expiration=None, result="",
                 fetched_at="2026-08-06T00:00:00Z")


def mv(bid=50, ask=52, bidsz=1000.0, asksz=1000.0):
    a = q("E1-A", bid, ask, bidsz, asksz, player="A")
    b = q("E1-B", 100 - ask, 100 - bid, 1000.0, 1000.0, player="B")
    return MatchView(event_ticker="E1", series="KXATPMATCH", tier="ATP",
                     tour="atp", primary=a, mirror=b,
                     fetched_at="2026-08-06T00:00:00Z")


# --------------------------------------------------------------------------
# GUARDS #7 — fill at the ask, never the mid
# --------------------------------------------------------------------------

def test_a_buy_lifts_the_ask_and_never_touches_the_mid():
    e = PaperEngine(["bot"])
    m = mv(bid=50, ask=56)          # mid is 53 and nobody trades there
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=10)
    e.execute_pending({"E1": m})
    pos = e.ledgers["bot"].positions[0]
    assert pos.entry_price == 56, "filled somewhere other than the ask"
    assert pos.entry_price != 53


def test_a_sell_hits_the_bid_and_never_the_mid():
    e = PaperEngine(["bot"])
    m = mv(bid=50, ask=56)
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=10)
    e.execute_pending({"E1": m})
    pos = e.ledgers["bot"].positions[0]
    e.queue_sell("bot", pos, m, "d2")
    e.execute_pending({"E1": m})
    assert pos.exit_price == 50, "sold above the bid"


# --------------------------------------------------------------------------
# The latency model: a decision cannot fill at the price that triggered it
# --------------------------------------------------------------------------

def test_the_fill_uses_the_next_ticks_book_and_records_the_slippage():
    e = PaperEngine(["bot"])
    t1 = mv(bid=50, ask=52)
    e.queue_buy("bot", t1, "E1-A", "A", "d1", qty=10)
    t2 = mv(bid=52, ask=54)          # the market moved against us
    e.execute_pending({"E1": t2})
    fill = e.ledgers["bot"].fills[0]
    assert fill.price_cents == 54
    assert fill.decided_price_cents == 52
    assert fill.slippage_cents == 2


def test_a_runaway_market_refuses_the_fill_rather_than_chasing():
    e = PaperEngine(["bot"])
    t1 = mv(bid=50, ask=52)
    e.queue_buy("bot", t1, "E1-A", "A", "d1", qty=10, max_price=55)
    e.execute_pending({"E1": mv(bid=68, ask=70)})
    assert not e.ledgers["bot"].positions
    assert "ran to 70c" in e.ledgers["bot"].rejected[0]["reason"]


# --------------------------------------------------------------------------
# Depth
# --------------------------------------------------------------------------

def test_an_order_cannot_consume_size_the_book_never_showed():
    e = PaperEngine(["bot"])
    m = mv(bid=50, ask=52, asksz=40.0)     # 25% of 40 is 10
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=100)
    e.execute_pending({"E1": m})
    pos = e.ledgers["bot"].positions[0]
    assert pos.qty == 10
    assert e.ledgers["bot"].fills[0].depth_shortfall == 90


def test_no_shown_depth_means_no_fill():
    e = PaperEngine(["bot"])
    m = mv(bid=50, ask=52, asksz=0.0)
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=10)
    e.execute_pending({"E1": m})
    assert not e.ledgers["bot"].positions
    assert "depth" in e.ledgers["bot"].rejected[0]["reason"]


# --------------------------------------------------------------------------
# GUARDS #6 — fees come from the one implementation, and settlement is free
# --------------------------------------------------------------------------

def test_holding_to_settlement_pays_the_entry_fee_only():
    """Getting this wrong doubles the cost bar on every hold-to-settle bot."""
    e = PaperEngine(["bot"])
    m = mv(bid=50, ask=52)
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=10)
    e.execute_pending({"E1": m})
    pos = e.ledgers["bot"].positions[0]
    e.settle("E1", "E1-A")
    assert pos.exit_fee_cents == 0.0
    expected = (100 - 52) * 10 - float(fee_order_cents(52, 10, TAKER_RATE))
    assert pos.pnl_cents == pytest.approx(expected)


def test_an_early_exit_pays_two_fees():
    e = PaperEngine(["bot"])
    m = mv(bid=50, ask=52)
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=10)
    e.execute_pending({"E1": m})
    pos = e.ledgers["bot"].positions[0]
    e.queue_sell("bot", pos, m, "d2")
    e.execute_pending({"E1": m})
    assert pos.entry_fee_cents > 0 and pos.exit_fee_cents > 0
    expected = ((50 - 52) * 10
                - float(fee_order_cents(52, 10, TAKER_RATE))
                - float(fee_order_cents(50, 10, TAKER_RATE)))
    assert pos.pnl_cents == pytest.approx(expected)


def test_the_reference_fee_points_still_hold():
    assert float(fee_rate_cents(50)) == pytest.approx(1.75)
    assert float(fee_rate_cents(90)) == pytest.approx(0.63, abs=0.005)
    assert float(fee_order_cents(50, 1)) == 2
    assert float(fee_order_cents(50, 100)) == 175


def test_the_cost_bars_are_what_a_bot_must_beat():
    assert hold_cost_cents(50, 2) == pytest.approx(1.75 + 2)
    assert round_trip_cost_cents(50, 2) == pytest.approx(1.75 + 1.75 + 2)


# --------------------------------------------------------------------------
# A void is its own state
# --------------------------------------------------------------------------

def test_a_void_is_not_folded_into_a_loss():
    e = PaperEngine(["bot"])
    m = mv()
    e.queue_buy("bot", m, "E1-A", "A", "d1", qty=10)
    e.execute_pending({"E1": m})
    e.settle("E1", None, voided=True)
    pos = e.ledgers["bot"].positions[0]
    assert pos.exit_kind == "voided"
    assert pos.pnl_cents is None, "a void counted as a number is a selection effect"
    assert e.ledgers["bot"].realised_cents() == 0.0


# --------------------------------------------------------------------------
# THE MARTINGALE. The single most important test in this file.
# --------------------------------------------------------------------------

def test_a_re_entry_can_never_be_larger_than_the_first_entry():
    """The live bot went 12 -> 20 -> 32 contracts into a falling market.

    Every individual size was arithmetically correct: a fixed dollar stake
    buys more contracts as the price falls. Reproduce the price path and
    assert the sizer refuses it.
    """
    first = choose_stake(conviction=4.0, enter_at=2.0, fair=0.60,
                         ask_cents=49, open_exposure_cents=0)
    assert first.contracts > 0
    # price collapses; the same confidence would buy far more contracts
    unguarded = choose_stake(conviction=4.0, enter_at=2.0, fair=0.60,
                             ask_cents=19, open_exposure_cents=0)
    guarded = choose_stake(conviction=4.0, enter_at=2.0, fair=0.60,
                           ask_cents=19, open_exposure_cents=0,
                           first_entry_contracts=first.contracts)
    assert unguarded.contracts > first.contracts, (
        "the martingale mechanism is not even present, so this test proves nothing")
    assert guarded.contracts <= first.contracts
    assert "no_larger_than_first_entry" in guarded.capped_by


def test_a_bot_cannot_stake_more_than_its_bankroll():
    s = choose_stake(conviction=10.0, enter_at=2.0, fair=0.99, ask_cents=50,
                     bankroll_cents=50_000, open_exposure_cents=50_000)
    assert s.contracts == 0


def test_sizing_varies_with_confidence_or_it_measures_nothing():
    """A constant stake cannot correlate with anything, so a constant stake
    makes 'sizing skill' unmeasurable by construction."""
    lo = choose_stake(conviction=2.1, enter_at=2.0, fair=0.55, ask_cents=52)
    hi = choose_stake(conviction=6.0, enter_at=2.0, fair=0.75, ask_cents=52)
    assert hi.fraction > lo.fraction
    assert hi.contracts > lo.contracts


def test_the_fee_is_inside_the_kelly_payoff():
    """Using ask and 100-ask instead of ask+fee and 100-ask-fee overstates the
    odds by the whole fee, which is the largest term at these prices."""
    s = choose_stake(conviction=3.0, enter_at=2.0, fair=0.50, ask_cents=50)
    # a fair coin at 50c is a LOSS once the fee is paid, so Kelly must be <= 0
    assert s.kelly_full is not None and s.kelly_full <= 0
    assert s.basis == "floor"


def test_open_exposure_counts_the_fee_too():
    lg = Ledger(bot="b")
    lg.positions.append(Position(bot="b", event_ticker="E1", ticker="E1-A",
                                 player="A", qty=10, entry_price=50,
                                 entry_fee_cents=18.0, entry_ts="t", decision_id="d"))
    assert lg.open_exposure_cents() == 518
