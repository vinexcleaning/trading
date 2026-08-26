"""Guards on the free-roll overlay.

The overlay is EV-negative by construction, so the danger is not that it looks
bad — it is that a bug makes it look good. Every test here is a way an exit
rule flatters itself: selling at the mid, forgetting the exit fee, quietly
dropping the positions that never fired, or seeing the trigger before it
happened.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "..", "..")))

from common import freeroll as FR          # noqa: E402
from common import kalshi_fees as KF       # noqa: E402


def pos(entry=10, n=10, tape=None, won=True, pid="p"):
    return FR.Position(pid=pid, entry_ask_c=entry, contracts=n,
                       tape=tape or [], won=won)


# ------------------------------------------------------------ his own example
def test_his_example_recovers_the_stake_and_leaves_a_runner():
    """Buy 10 at 10c for $1; at 20c sell enough to get $1 back; 5 ride on."""
    tape = [(20, 21)] * 5
    o = FR.apply(pos(entry=10, n=10, tape=tape, won=False), FR.Rule("multiple", 2.0))
    assert o.activated
    assert o.sold == 5, f"sold {o.sold}, his arithmetic says 5"
    assert o.runner == 5
    assert o.sold_at_c == 20


def test_the_free_roll_still_loses_money_when_the_runner_loses():
    """'The principal was already recovered' is not the same as breaking even —
    the fees are real and they are why this cannot be free."""
    tape = [(20, 21)] * 5
    o = FR.apply(pos(entry=10, n=10, tape=tape, won=False), FR.Rule("multiple", 2.0))
    assert o.net_c < 0, "recovering the stake somehow came out non-negative"
    assert o.net_c > -20, "it should lose the fees, not the whole stake"


# ---------------------------------------------------------------- execution
def test_the_exit_is_at_the_bid_and_never_the_mid():
    """GUARDS #7. Selling at the mid is the single most common way an exit
    backtest invents money that was never on the screen."""
    tape = [(20, 30)] * 5              # mid is 25, bid is 20
    o = FR.apply(pos(entry=10, n=10, tape=tape), FR.Rule("multiple", 2.0))
    assert o.sold_at_c == 20, "the overlay sold above the bid"


def test_the_exit_fee_is_charged():
    tape = [(20, 21)] * 5
    o = FR.apply(pos(entry=10, n=10, tape=tape), FR.Rule("multiple", 2.0))
    gross = o.sold * o.sold_at_c
    assert o.recovered_c < gross, "the sale paid no exit fee"


def test_holding_pays_no_exit_fee_which_is_why_the_overlay_costs_money():
    """Kalshi charges nothing at settlement. The asymmetry IS the cost."""
    assert FR.settle_c(10, True) == 1000.0
    assert FR.settle_c(10, False) == 0.0


def test_one_whole_minute_of_latency_is_applied():
    """Seeing the trigger at minute i, you execute at i+1 — and if the price
    fell back in between, that is what you get. Executing at the trigger price
    is a look-ahead."""
    tape = [(20, 21), (12, 13), (12, 13)]
    o = FR.apply(pos(entry=10, n=10, tape=tape), FR.Rule("multiple", 2.0))
    assert o.sold_at_min == 1
    assert o.sold_at_c == 12, "executed at the trigger price, not one bar later"


def test_a_trigger_on_the_last_bar_cannot_be_executed():
    tape = [(12, 13), (20, 21)]
    o = FR.apply(pos(entry=10, n=10, tape=tape), FR.Rule("multiple", 2.0))
    assert not o.activated
    assert "too late" in o.reason


def test_whole_contracts_only():
    """A 3-contract position cannot sell 1.5. He named this case specifically."""
    tape = [(20, 21)] * 5
    o = FR.apply(pos(entry=10, n=3, tape=tape), FR.Rule("multiple", 2.0))
    assert o.sold == int(o.sold), "sold a fractional contract"
    assert o.sold == 1                       # 30c of stake / 20c = 1.5 -> 1


def test_a_position_too_small_to_recover_is_REPORTED_not_dropped():
    tape = [(20, 21)] * 5
    o = FR.apply(pos(entry=10, n=1, tape=tape), FR.Rule("multiple", 2.0))
    assert not o.activated
    assert "too small" in o.reason
    # and it still carries its real hold-to-settlement result
    assert o.net_c == pytest.approx(FR.settle_c(1, True) - o.cost_c)


def test_never_reaching_the_trigger_is_reported_not_dropped():
    tape = [(11, 12)] * 20
    o = FR.apply(pos(entry=10, n=10, tape=tape), FR.Rule("multiple", 2.0))
    assert not o.activated and "never reached" in o.reason


# ------------------------------------------- the ceiling he could not have hit
def test_a_multiple_rule_cannot_fire_on_an_expensive_entry():
    """His example is a 10c ticket doubling. Our tennis entries are 60-70c,
    where doubling is arithmetically impossible — 100c is the ceiling. This is
    a fact about the ceiling, not a finding, and it is why the activation rate
    is a headline number."""
    tape = [(99, 99)] * 10
    o = FR.apply(pos(entry=60, n=10, tape=tape), FR.Rule("multiple", 2.0))
    assert not o.activated
    assert "unreachable" in o.reason
    assert FR.Rule("multiple", 2.0).reachable_below == 50.0
    assert FR.Rule("multiple", 3.0).reachable_below == pytest.approx(33.33, abs=0.01)


def test_absolute_rules_have_no_such_ceiling():
    tape = [(70, 71)] * 5
    o = FR.apply(pos(entry=60, n=10, tape=tape), FR.Rule("profit", 10))
    assert o.activated and o.sold_at_c == 70


# ---------------------------------------------------------------- the fee shape
def test_taking_principal_off_the_table_is_dearest_at_LOW_prices():
    """Counterintuitive and it is the heart of Job 0: the Kalshi fee is
    proportional to price x (1-price), so in cents it peaks at 50c — but as a
    FRACTION of the sale it is far worse when the price is low. His own example
    sells at 20c, which is close to the worst place to do it."""
    def cost_per_dollar(price):
        n = 100.0 / price
        return n * (float(KF.fee_order_cents(price, 100)) / 100 + 0.5)
    cheap = cost_per_dollar(20)
    dear = cost_per_dollar(90)
    assert cheap > 3 * dear, (
        f"selling at 20c cost {cheap:.1f}c per $1 and at 90c {dear:.1f}c; "
        "the low-price penalty has gone")
    assert 7 < cheap < 10


# ---------------------------------------------------------------- portfolio
def test_the_baseline_is_hold_and_it_activates_nothing():
    ps = [pos(pid=str(i), entry=10, n=10, tape=[(20, 21)] * 5, won=i % 2 == 0)
          for i in range(10)]
    r = FR.simulate(ps, FR.HOLD)
    assert r.n == 10 and r.activated == 0


def test_the_overlay_lowers_return_against_holding_when_the_edge_is_the_same():
    """The core claim, asserted rather than assumed: on identical positions the
    overlay must not make MORE money. If it does, something is wrong."""
    ps = [pos(pid=str(i), entry=10, n=10, tape=[(20, 21)] * 5, won=i % 3 == 0)
          for i in range(30)]
    hold = FR.simulate(ps, FR.HOLD)
    over = FR.simulate(ps, FR.Rule("multiple", 2.0))
    assert over.net_c < hold.net_c, "the free-roll beat holding — check the fees"


def test_the_overlay_reduces_the_worst_run_of_losses():
    """The thing his framing actually turns on. Lower return with a much
    smaller worst run is a SUCCESS, so the measure has to work."""
    ps = [pos(pid=str(i), entry=10, n=10, tape=[(20, 21)] * 5, won=False)
          for i in range(20)]
    hold = FR.simulate(ps, FR.HOLD)
    over = FR.simulate(ps, FR.Rule("multiple", 2.0))
    assert over.max_drawdown_c < hold.max_drawdown_c


def test_a_bankroll_skips_signals_and_says_how_many():
    """The one mechanism by which the overlay can genuinely win: freeing cash
    sooner means more shots. If skipped signals are not counted, that mechanism
    is invisible."""
    ps = [pos(pid=str(i), entry=50, n=10, tape=[(60, 61)] * 5, won=False)
          for i in range(20)]
    r = FR.simulate(ps, FR.HOLD, bankroll_c=1500.0)
    assert r.skipped_for_cash > 0
    assert r.n + r.skipped_for_cash == len(ps)


def test_activation_rate_counts_every_position_not_just_the_ones_that_fired():
    ps = ([pos(pid=f"a{i}", entry=10, n=10, tape=[(20, 21)] * 5) for i in range(2)]
          + [pos(pid=f"b{i}", entry=10, n=10, tape=[(11, 12)] * 5) for i in range(8)])
    r = FR.simulate(ps, FR.Rule("multiple", 2.0))
    assert r.n == 10
    assert r.activation_rate == pytest.approx(0.2)
    assert r.never_triggered == 8
