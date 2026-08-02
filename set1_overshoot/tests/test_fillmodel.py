"""Tests for the maker fill simulator and the entry-rule detector.

Both produce headline numbers and neither was tested. `simulate()` decides the
-0.205 c/opportunity maker result; `completed_dip()` decides which 3,436 matches
are events at all.
"""
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import p2_calib as p2          # noqa: E402
import p5_task1b as t1         # noqa: E402


def mk(entry_idx, dur, bid=50, ask=52, n=1):
    return pd.DataFrame({
        "entry_idx": [entry_idx] * n,
        "entry_bid": [bid] * n,
        "entry_ask": [ask] * n,
        "dur_min": [dur] * n,
        "tour": ["ITF-M"] * n,
    })


# ------------------------------------------------------------ fill model
def test_no_fill_when_book_only_touches_the_level():
    """Last in queue: touching the resting price must NOT fill."""
    e = mk(10, 60)
    bh = np.full((1, 300), 40.0)
    bh[0, 11:20] = 52.0                      # exactly at the join_ask level
    f, at, L = t1.simulate(e, np.array([0]), bh, "join_ask", 30,
                           e["dur_min"].values)
    assert L[0] == 52
    assert not f[0], "touching the level must not count as a fill"


def test_fill_when_book_trades_through():
    e = mk(10, 60)
    bh = np.full((1, 300), 40.0)
    bh[0, 15] = 53.0                          # strictly through 52
    f, at, _ = t1.simulate(e, np.array([0]), bh, "join_ask", 30,
                           e["dur_min"].values)
    assert f[0] and at[0] == 15


def test_fill_takes_the_first_crossing_not_the_best():
    e = mk(10, 60)
    bh = np.full((1, 300), 40.0)
    bh[0, 14] = 53.0
    bh[0, 25] = 99.0
    f, at, _ = t1.simulate(e, np.array([0]), bh, "join_ask", 60,
                           e["dur_min"].values)
    assert at[0] == 14, "must fill at the first crossing, not the deepest"


def test_window_is_respected():
    e = mk(10, 200)
    bh = np.full((1, 300), 40.0)
    bh[0, 40] = 60.0                          # crossing at +30 min
    f5, _, _ = t1.simulate(e, np.array([0]), bh, "join_ask", 5,
                           e["dur_min"].values)
    f60, _, _ = t1.simulate(e, np.array([0]), bh, "join_ask", 60,
                            e["dur_min"].values)
    assert not f5[0] and f60[0]


def test_no_fill_after_match_end():
    e = mk(10, 20)                            # match ends at minute 20
    bh = np.full((1, 300), 40.0)
    bh[0, 50] = 99.0                          # crossing long after the end
    f, _, _ = t1.simulate(e, np.array([0]), bh, "join_ask", 300,
                          e["dur_min"].values)
    assert not f[0], "cannot fill after the match has finished"


def test_resting_styles_are_ordered_by_price():
    """More passive = better price for a fade = higher favourite sell level."""
    e = mk(10, 60, bid=50, ask=54)
    imp = t1.rest_levels(e, "improve")[0]
    join = t1.rest_levels(e, "join_ask")[0]
    pas = t1.rest_levels(e, "passive")[0]
    assert imp < join < pas
    assert imp == 51 and join == 54 and pas == 55


def test_improve_collapses_to_ask_when_spread_is_one():
    e = mk(10, 60, bid=50, ask=51)
    assert t1.rest_levels(e, "improve")[0] == 51


def test_more_passive_fills_less_often():
    rng = np.random.default_rng(0)
    n = 400
    e = mk(10, 120, bid=50, ask=54, n=n)
    bh = 40 + rng.random((n, 300)) * 30
    dur = e["dur_min"].values
    rates = []
    for style in ("improve", "join_ask", "passive"):
        f, _, _ = t1.simulate(e, np.arange(n), bh, style, 60, dur)
        rates.append(f.mean())
    assert rates[0] >= rates[1] >= rates[2]


# --------------------------------------------------------- maker fee table
def test_maker_fee_zero_on_itf_and_challenger():
    px = np.array([60.0, 60.0, 60.0])
    tours = np.array(["ITF-M", "ITF-W", "CHALL"])
    assert (t1.maker_fee_verified(tours, px) == 0).all()


def test_maker_fee_applies_on_atp_wta():
    px = np.array([60.0, 60.0])
    tours = np.array(["ATP", "WTA"])
    assert (t1.maker_fee_verified(tours, px) == 0.25).all()


def test_the_two_fee_arms_cross_and_neither_dominates():
    """Documents a real subtlety the name 'pessimistic' obscures.

    The quarter-of-taker arm is harsher than the verified schedule on ITF and
    Challenger (where the verified fee is zero) and at mid prices on ATP/WTA.
    But the taker fee collapses toward the tails, so at 95c a quarter of it is
    0.083c -- CHEAPER than the flat 0.25c the verified ATP/WTA schedule charges.
    The arms cross; the headline uses whichever is harsher at each price, which
    happens to be the verified one at the extremes.
    """
    quarter_95 = t1.maker_fee_pessimistic(np.array(["WTA"]), np.array([95.0]))[0]
    verified_95 = t1.maker_fee_verified(np.array(["WTA"]), np.array([95.0]))[0]
    assert quarter_95 < verified_95, "arms must cross at the tails"
    assert quarter_95 == pytest.approx(0.25 * 0.07 * 95 * 5 / 100)

    # on the zero-fee series the quarter arm is always the harsher one
    itf = np.array(["ITF-M"] * 4)
    px = np.array([20.0, 50.0, 80.0, 95.0])
    assert (t1.maker_fee_pessimistic(itf, px)
            >= t1.maker_fee_verified(itf, px)).all()


# ------------------------------------------------------------- entry rule
def test_completed_dip_fires_one_minute_after_the_fall_stops():
    """Pins the ACTUAL semantics, which are weaker than 'stable for 8 minutes'.

    The `done` condition is "not a new low relative to the previous `pause`
    minutes". Once the price steps down and holds for a single minute, the
    previous window already contains that low, so the condition is met at the
    next minute -- not 8 minutes later. That is still a stopping time and uses
    no future data, but the reports must not describe it as an 8-minute
    stabilisation, because it is not.
    """
    pre = np.array([80.0])
    mid = np.full((1, 300), 80.0)
    mid[0, 30:] = 60.0                        # 20c drop at t=30, then flat
    fire = p2.completed_dip(mid, pre, depth=12.0, pause=8)
    assert fire[0] == 31, "fires the minute after the fall stops, not +8"
    assert mid[0, fire[0]] <= 80.0 - 12.0


def test_completed_dip_does_not_fire_on_a_shallow_dip():
    pre = np.array([80.0])
    mid = np.full((1, 300), 80.0)
    mid[0, 30:] = 74.0                        # only 6c
    assert p2.completed_dip(mid, pre, depth=12.0)[0] == -1


def test_completed_dip_does_not_fire_while_still_falling():
    pre = np.array([80.0])
    mid = np.full((1, 300), 80.0)
    for i in range(20, 200):                  # monotone decline, never pauses
        mid[0, i] = 80.0 - (i - 19) * 0.5
    fire = p2.completed_dip(mid, pre, depth=12.0, pause=8)
    # a strictly falling series makes every point a new low, so no pause exists
    assert fire[0] == -1


def test_completed_dip_respects_the_minimum_minute():
    pre = np.array([80.0])
    mid = np.full((1, 300), 80.0)
    mid[0, 25:] = 60.0
    early = p2.completed_dip(mid, pre, depth=12.0, lo=p2.CP_LO)
    late = p2.completed_dip(mid, pre, depth=12.0, lo=38)
    assert late[0] > early[0]
    assert late[0] >= 38 + 8
