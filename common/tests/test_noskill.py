"""Guards on the shared no-skill module.

The test that matters most is the POSITIVE CONTROL. A null-only suite is passed
by a function that always returns a band from -100% to +100% and calls
everything noise. GUARDS #4: the pipeline must detect an effect you put there.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from common.noskill import (Bets, band, best_of, binomial_tail,  # noqa: E402
                            p_at_least, verdict)


def _flat(n, price=70, qty=10, fee=0.0):
    return Bets(prices=[price] * n, qtys=[qty] * n, fees=[fee] * n)


# --------------------------------------------------------------------------
# THE POSITIVE CONTROL — a planted edge must escape the band
# --------------------------------------------------------------------------

def test_a_real_edge_lands_outside_the_band():
    """Plant a strategy that genuinely wins more than the price implies and
    assert the band calls it out. Without this, a band of -100..+100 passes
    every other test in this file."""
    n, price = 400, 50
    b = _flat(n, price=price)
    lo, hi = band(b)
    # a strategy winning 65 times in 100 at a 50c price
    true_p = 0.65
    ret = 100.0 * (true_p * (100 - price) - (1 - true_p) * price) / price
    assert ret > hi, (
        f"a genuine {true_p:.0%} win rate at {price}c returns {ret:.1f}% and the "
        f"band tops out at {hi:.1f}% — the band cannot see a real edge")
    assert verdict(ret, lo, hi).startswith("OUTSIDE, better")


def test_no_edge_lands_inside_the_band_about_90_percent_of_the_time():
    """The null half. Ten independent no-skill runs should mostly sit inside."""
    b = _flat(300)
    lo, hi = band(b)
    rng = np.random.default_rng(7)
    inside = 0
    for _ in range(40):
        wins = rng.random(300) < 0.70
        pnl = np.where(wins, 30.0 * 10, -70.0 * 10).sum()
        r = 100.0 * pnl / (70 * 10 * 300)
        inside += int(lo <= r <= hi)
    assert inside >= 32, f"only {inside}/40 no-skill runs fell inside a 90% band"


# --------------------------------------------------------------------------
# The fee correction that this module exists to stop being forgotten
# --------------------------------------------------------------------------

def test_fees_shift_the_band_downwards():
    """Six of sixteen tennis bots once looked worse than luck purely because the
    null paid no fees and they did."""
    free = band(_flat(300, fee=0.0))
    paid = band(_flat(300, fee=1.4))
    assert paid[0] < free[0] and paid[1] < free[1], (
        "adding fees to the null did not move the band down; the comparison is "
        "gross-against-net and will manufacture findings")


def test_fees_are_optional_but_default_to_none():
    b = Bets(prices=[50, 60], qtys=[1, 1])
    assert b.n == 2
    band(b)          # must not raise


# --------------------------------------------------------------------------
# best_of — the number that is always missing
# --------------------------------------------------------------------------

def test_best_of_many_is_far_more_forgiving_than_one():
    """Judging the best of 200 is a different question from judging one, and the
    factory plans to generate thousands."""
    one = _flat(100, price=50)
    p_single = p_at_least(one, 15.0)
    p_best = best_of([one] * 200, 15.0)
    assert p_best > p_single * 5, (
        f"best-of-200 ({p_best:.3f}) is barely different from a single strategy "
        f"({p_single:.3f}); the multiple-comparison correction is not working")


def test_best_of_empty_is_not_a_number():
    assert np.isnan(best_of([], 10.0))


# --------------------------------------------------------------------------
# Shape, and the exact form
# --------------------------------------------------------------------------

def test_binomial_tail_matches_known_values():
    assert binomial_tail(0, 10, 0.5) == pytest.approx(1.0)
    assert binomial_tail(11, 10, 0.5) == pytest.approx(0.0, abs=1e-12)
    assert binomial_tail(5, 10, 0.5) == pytest.approx(0.623046875)


def test_a_price_outside_the_book_is_refused():
    for bad in (0, 100, -5, 101):
        with pytest.raises(ValueError):
            Bets(prices=[bad], qtys=[1])


def test_mismatched_lengths_are_refused():
    with pytest.raises(ValueError):
        Bets(prices=[50, 60], qtys=[1])
    with pytest.raises(ValueError):
        Bets(prices=[50], qtys=[1], fees=[1, 2])


def test_verdict_has_three_outcomes_not_two():
    assert verdict(50.0, -10, 10).startswith("OUTSIDE, better")
    assert verdict(-50.0, -10, 10).startswith("OUTSIDE, worse")
    assert verdict(0.0, -10, 10).startswith("INSIDE")


def test_the_same_seed_gives_the_same_band():
    """Reproducible. Note the band does NOT have to differ between seeds: with
    flat prices and stakes the return takes discrete values, so two seeds
    routinely land on the same percentile. An earlier version of this test
    asserted they differed and was simply wrong about the arithmetic."""
    b = _flat(200)
    assert band(b, seed=1) == band(b, seed=1)
    mixed = Bets(prices=[20, 45, 70, 90] * 60, qtys=[3, 7, 11, 2] * 60)
    assert band(mixed, seed=1) != band(mixed, seed=999)
