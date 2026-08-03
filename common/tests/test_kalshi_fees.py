"""Tests for the consolidated Kalshi fee module.

The float-dust regression is the reason this module exists. Nine of the
fifteen pre-consolidation implementations failed it, two of them in the
live-money path.

    C:\\Users\\vinig\\trading\\kalshi-market-scan\\.venv\\Scripts\\python.exe -m pytest common/tests -q
"""
import math
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kalshi_fees import (  # noqa: E402
    CENSUS_CRYPTO_MAKER_SERIES,
    CENSUS_MAKER_FEE_SERIES,
    FEE_TYPE_TAKER_ONLY,
    FEE_TYPE_WITH_MAKER,
    MAKER_RATE_WHERE_CHARGED,
    TAKER_ONLY,
    TAKER_RATE,
    SeriesFees,
    fee_order_cents,
    fee_order_dollars,
    fee_order_from_price,
    fee_rate_cents,
    fee_rate_from_price,
    maker_fee_order_cents,
    roundtrip_cost_cents,
)


# ------------------------------------------------- the reference points
@pytest.mark.parametrize("price_cents,want", [
    (50, "1.75"),      # the headline: 1.75c at 50c
    (90, "0.63"),      # 0.63c at 90c
    (10, "0.63"),      # 0.63c at 10c — symmetric with 90c
])
def test_reference_points(price_cents, want):
    """The three numbers the whole project quotes. Exact, not approximate."""
    assert fee_rate_cents(price_cents) == Decimal(want)


def test_reference_points_are_exact_decimals_not_floats():
    """str() would expose any float contamination immediately."""
    assert str(fee_rate_cents(50)) == "1.75"
    assert str(fee_rate_cents(90)) == "0.63"
    assert str(fee_rate_cents(10)) == "0.63"


# ------------------------------------------------- the float-dust regression
def test_float_dust_regression():
    """0.07*100*0.5*0.5*100 == 175.00000000000003; a naive ceil charges 176.

    This is the bug. It is not hypothetical: it was live in nine call sites,
    two of which placed real orders.
    """
    naive = math.ceil(0.07 * 100 * 0.5 * 0.5 * 100)
    assert naive == 176, "the float dust itself has changed; re-derive the test"
    assert fee_order_cents(50, 100) == Decimal("175")
    assert fee_order_cents(50, 100) != naive


def test_float_dust_across_the_whole_grid():
    """No price/size cell may disagree with the exact quadratic.

    The unguarded float form overcharges on 115 of these 1,881 cells.
    """
    sizes = [1, 2, 3, 5, 8, 10, 12, 15, 20, 25, 32, 50, 64, 100, 137, 200,
             500, 1000, 10000]
    disagreements = []
    for c in sizes:
        for pc in range(1, 100):
            exact = fee_order_cents(pc, c)
            naive = math.ceil(0.07 * c * (pc / 100) * (1 - pc / 100) * 100)
            if Decimal(naive) != exact:
                disagreements.append((pc, c, int(exact), naive))
    # every disagreement must be the naive form OVERcharging, never under
    assert all(n > e for _, _, e, n in disagreements)
    # and the exact form is the one we ship
    assert fee_order_cents(50, 8) == Decimal("14")     # naive says 15
    assert fee_order_cents(50, 12) == Decimal("21")    # naive says 22
    assert fee_order_cents(25, 32) == Decimal("42")    # naive says 43


@pytest.mark.parametrize("price_cents,contracts,want", [
    (49, 12, "21"),     # the 28 Jul martingale, leg 1
    (31, 20, "30"),     # leg 2
    (19, 32, "35"),     # leg 3
    (50, 8, "14"),      # a routine size, at the peak of the fee curve
    (50, 12, "21"),
    (25, 32, "42"),
])
def test_live_bot_order_sizes(price_cents, contracts, want):
    """Order sizes the live bot actually placed. Exact values, pinned."""
    assert fee_order_cents(price_cents, contracts) == Decimal(want)


@pytest.mark.parametrize("price_cents,contracts", [
    (50, 8), (50, 12), (25, 32),
])
def test_live_bot_sizes_that_the_naive_form_overcharges(price_cents, contracts):
    """These specific cells were being overcharged by the live bot.

    Note the three legs of the 28 Jul martingale (12@49c, 20@31c, 32@19c) do
    NOT hit the dust bug — the overcharge clusters near the 50c peak of the
    fee curve, not at the prices that sequence actually traded at. The bug is
    real and was live, but it is not what made that day expensive.
    """
    naive = math.ceil(0.07 * contracts * (price_cents / 100)
                      * (1 - price_cents / 100) * 100)
    assert Decimal(naive) == fee_order_cents(price_cents, contracts) + 1


# ------------------------------------------------- shape of the curve
def test_symmetric_about_fifty():
    for pc in range(1, 50):
        assert fee_rate_cents(pc) == fee_rate_cents(100 - pc)


def test_peaks_at_fifty():
    peak = fee_rate_cents(50)
    for pc in range(1, 100):
        assert fee_rate_cents(pc) <= peak


def test_zero_at_the_boundaries():
    assert fee_rate_cents(0) == Decimal(0)
    assert fee_rate_cents(100) == Decimal(0)


def test_never_negative():
    for pc in range(0, 101):
        assert fee_rate_cents(pc) >= 0


def test_scales_linearly_in_contracts_before_rounding():
    one = fee_rate_cents(50) * 1000
    assert one == fee_rate_cents(50) * Decimal(1000)
    assert fee_order_cents(50, 1000) == Decimal("1750")


def test_order_fee_rounds_up_not_down():
    """1 contract at 50c is 1.75c raw and is billed 2c, not 1c."""
    assert fee_rate_cents(50) == Decimal("1.75")
    assert fee_order_cents(50, 1) == Decimal("2")


def test_fee_never_exceeds_notional():
    for pc in range(1, 100):
        for c in (1, 10, 100):
            assert fee_order_cents(pc, c) <= Decimal(pc * c)


# ------------------------------------------------- fractional cents
def test_fractional_cents_are_not_truncated():
    """The pre-consolidation module did Decimal(int(price)), silently
    truncating 49.7c to 49c. Mid prices are fractional; this must be exact."""
    assert fee_rate_cents(Decimal("49.5")) == fee_rate_cents(Decimal("50.5"))
    assert fee_rate_cents(49.5) != fee_rate_cents(49)


# ------------------------------------------------- unit conversions agree
def test_dollar_and_cent_entry_points_agree():
    for pc in range(1, 100):
        assert fee_rate_from_price(Decimal(pc) / 100) == fee_rate_cents(pc)
        assert fee_order_from_price(Decimal(pc) / 100, 37) == \
            fee_order_cents(pc, 37)


def test_fee_order_dollars_matches_cents():
    assert fee_order_dollars(50, 100) == 1.75
    assert fee_order_dollars(50, 1) == 0.02
    assert fee_order_dollars(90, 100) == 0.63


# ------------------------------------------------- round trips
def test_hold_to_settlement_pays_one_fee():
    assert roundtrip_cost_cents(55) == fee_rate_cents(55)


def test_early_exit_pays_two():
    assert roundtrip_cost_cents(55, 70) == \
        fee_rate_cents(55) + fee_rate_cents(70)


# ------------------------------------------------- the maker side
def test_maker_fee_is_zero_on_taker_only_series():
    assert maker_fee_order_cents(50, 10_000, TAKER_ONLY) == Decimal(0)


def test_maker_fee_applies_only_where_fee_type_says_so():
    s = SeriesFees("KXATPMATCH", FEE_TYPE_WITH_MAKER)
    assert s.charges_maker
    assert s.maker_rate == MAKER_RATE_WHERE_CHARGED
    assert maker_fee_order_cents(50, 100, s) == Decimal("44")


def test_maker_rate_is_a_quarter_of_taker():
    assert MAKER_RATE_WHERE_CHARGED == TAKER_RATE / 4


def test_maker_fee_refuses_to_guess():
    """No default argument, and no duck-typing. If you do not know the
    series' fee_type you do not know its maker fee."""
    with pytest.raises(TypeError):
        maker_fee_order_cents(50, 100, None)
    with pytest.raises(TypeError):
        maker_fee_order_cents(50, 100, "quadratic_with_maker_fees")


def test_series_from_api_requires_fee_type():
    with pytest.raises(KeyError):
        SeriesFees.from_api({"ticker": "KXFOO"})


def test_series_from_api_reads_both_fields():
    s = SeriesFees.from_api({"ticker": "KXBTCMAX150",
                             "fee_type": FEE_TYPE_WITH_MAKER,
                             "fee_multiplier": 1})
    assert s.charges_maker
    assert s.taker_rate == TAKER_RATE
    assert s.maker_rate == MAKER_RATE_WHERE_CHARGED


def test_fee_multiplier_zero_means_free():
    """14 of 12,396 series carry fee_multiplier 0 — genuinely no fee."""
    s = SeriesFees.from_api({"ticker": "KXBTCY",
                             "fee_type": FEE_TYPE_TAKER_ONLY,
                             "fee_multiplier": 0})
    assert s.taker_rate == Decimal(0)
    assert s.maker_rate == Decimal(0)
    assert fee_order_cents(50, 100, s.taker_rate) == Decimal(0)


def test_crypto_series_do_carry_maker_fees():
    """Refutes the 'ZERO are crypto' claim that justified a hardcoded zero.

    KXBTCMAX150 and KXBTCMAX125 are category Crypto and fee_type
    quadratic_with_maker_fees, verified against the live API 2026-08-03.
    """
    assert len(CENSUS_CRYPTO_MAKER_SERIES) == 2
    for ticker in CENSUS_CRYPTO_MAKER_SERIES:
        s = SeriesFees(ticker, FEE_TYPE_WITH_MAKER)
        assert s.charges_maker
        assert s.maker_rate > 0


def test_census_maker_count_is_the_verified_130():
    assert CENSUS_MAKER_FEE_SERIES == 130


# ------------------------------------------------- vectorised path agrees
def test_vectorised_matches_scalar():
    np = pytest.importorskip("numpy")
    from kalshi_fees import fee_order_from_price_vec, fee_rate_from_price_vec
    prices = np.arange(1, 100) / 100.0
    got = fee_rate_from_price_vec(prices)
    want = np.array([float(fee_rate_cents(pc)) for pc in range(1, 100)])
    assert np.allclose(got, want)
    got_o = fee_order_from_price_vec(prices, 100)
    want_o = np.array([float(fee_order_cents(pc, 100)) for pc in range(1, 100)])
    assert np.allclose(got_o, want_o)


def test_vectorised_beats_the_naive_numpy_form():
    """np.ceil on the float product has the same dust bug."""
    np = pytest.importorskip("numpy")
    from kalshi_fees import fee_dollars_from_price_vec
    p = np.array([0.50])
    naive = np.ceil(0.07 * 100 * p * (1 - p) * 100) / 100
    assert naive[0] == 1.76
    assert fee_dollars_from_price_vec(p, 100)[0] == 1.75


def test_vectorised_handles_scalars():
    pytest.importorskip("numpy")
    from kalshi_fees import fee_dollars_from_price_vec
    assert fee_dollars_from_price_vec(0.5, 100) == 1.75


@pytest.mark.parametrize("pc", [7, 14, 28, 29, 55, 56, 57, 58])
def test_vectorised_does_not_reintroduce_dust_via_times_100(pc):
    """Converting a dollar price back to cents in float is lossy.

    For these eight prices (pc/100)*100 != pc, e.g. 0.07*100 is
    7.000000000000001. Routing through that changes the billed fee on 8
    price/size cells. The dollar-native path coerces with Decimal(str(x))
    and never performs the multiplication in float.
    """
    np = pytest.importorskip("numpy")
    from kalshi_fees import fee_order_from_price_vec
    assert (pc / 100) * 100 != float(pc)      # the trap being avoided
    got = fee_order_from_price_vec(np.array([pc / 100]), 100)
    assert got[0] == float(fee_order_cents(pc, 100))
