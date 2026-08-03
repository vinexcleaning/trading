import math

import pytest

from kalshi_research.fees import (
    MAKER_RATE,
    TAKER_RATE,
    SeriesFeeSpec,
    breakeven_edge_cents,
    maker_fee_dollars,
    round_trip_taker_cents,
    taker_fee_dollars,
)


def test_known_reference_fee():
    """100 contracts at 50c -> $1.75. This is the anchor the units were fixed against."""
    assert taker_fee_dollars(100, 0.50) == pytest.approx(1.75)


def test_ceiling_is_to_the_cent_not_the_dollar():
    # raw = 0.07 * 1 * 0.5 * 0.5 = 0.0175 -> ceil to 0.02
    assert taker_fee_dollars(1, 0.50) == pytest.approx(0.02)
    # raw = 0.07 * 10 * 0.5 * 0.5 = 0.175 -> ceil to 0.18
    assert taker_fee_dollars(10, 0.50) == pytest.approx(0.18)


def test_fee_is_symmetric_about_50c():
    for p in (0.01, 0.1, 0.25, 0.4):
        assert taker_fee_dollars(100, p) == pytest.approx(taker_fee_dollars(100, 1 - p))


def test_fee_is_maximised_at_50c():
    fees = {p: taker_fee_dollars(1000, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)}
    assert max(fees, key=fees.get) == 0.5


def test_tails_are_about_one_fifth_the_cost_of_the_middle():
    """The prompt's claim: 10c/90c costs ~1/5 of 50c. p(1-p): 0.09 vs 0.25 -> 0.36."""
    ratio = taker_fee_dollars(10_000, 0.10) / taker_fee_dollars(10_000, 0.50)
    assert 0.30 < ratio < 0.40


def test_zero_fee_at_boundaries():
    assert taker_fee_dollars(100, 0.0) == 0.0
    assert taker_fee_dollars(100, 1.0) == 0.0


def test_zero_contracts_is_free():
    assert taker_fee_dollars(0, 0.5) == 0.0


def test_round_trip_at_50c_is_350_bps_per_contract():
    """The headline cost bar: 3.5c round trip per contract at the money."""
    rt = round_trip_taker_cents(100, 0.50) / 100
    assert rt == pytest.approx(3.50, abs=0.01)


def test_round_trip_table_matches_contract_spec():
    expected = {0.10: 1.26, 0.25: 2.63, 0.50: 3.50, 0.75: 2.63, 0.90: 1.26}
    for p, want in expected.items():
        got = round_trip_taker_cents(100, p) / 100
        assert got == pytest.approx(want, abs=0.02), f"P={p}"


def test_maker_is_one_quarter_of_taker_when_charged():
    t = taker_fee_dollars(10_000, 0.5)
    m = maker_fee_dollars(10_000, 0.5, charges_maker=True)
    assert m == pytest.approx(t / 4, rel=1e-6)
    assert MAKER_RATE == pytest.approx(TAKER_RATE / 4)


def test_maker_is_free_when_series_does_not_charge():
    assert maker_fee_dollars(10_000, 0.5, charges_maker=False) == 0.0


def test_multiplier_scales_linearly():
    full = taker_fee_dollars(10_000, 0.5, multiplier=1.0)
    half = taker_fee_dollars(10_000, 0.5, multiplier=0.5)
    assert half == pytest.approx(full / 2, rel=1e-6)


def test_zero_multiplier_is_free():
    assert taker_fee_dollars(10_000, 0.5, multiplier=0.0) == 0.0


def test_breakeven_includes_spread_and_slippage():
    b = breakeven_edge_cents(0.5, spread_cents=2.0, slippage_cents=0.5)
    assert b == pytest.approx(3.50 + 2.0 + 0.5, abs=0.02)


def test_breakeven_at_tails_is_cheaper_than_middle():
    assert breakeven_edge_cents(0.10, 1.0) < breakeven_edge_cents(0.50, 1.0)


def test_invalid_price_rejected():
    for bad in (-0.01, 1.01, 50):
        with pytest.raises(ValueError):
            taker_fee_dollars(100, bad)


def test_negative_contracts_rejected():
    with pytest.raises(ValueError):
        taker_fee_dollars(-1, 0.5)


class TestSeriesFeeSpec:
    def test_maker_flag_from_fee_type(self):
        assert SeriesFeeSpec("KXPGA", "quadratic_with_maker_fees", 1).charges_maker
        assert not SeriesFeeSpec("KXBTC15M", "quadratic", 1).charges_maker

    def test_zero_multiplier_series(self):
        s = SeriesFeeSpec("KXBTCY", "quadratic", 0)
        assert s.effective_multiplier == 0.0
        assert taker_fee_dollars(10_000, 0.5, s.effective_multiplier) == 0.0

    def test_observed_index_series_are_not_halved(self):
        """D-002: live API reports multiplier 1 for KXINX/KXNASDAQ100."""
        for t in ("KXINX", "KXNASDAQ100"):
            assert SeriesFeeSpec(t, "quadratic", 1).effective_multiplier == 1.0


def test_fee_never_exceeds_notional():
    """Sanity: a fee larger than the position would be a formula error."""
    for c in (1, 10, 100, 1000):
        for p in (0.01, 0.5, 0.99):
            assert taker_fee_dollars(c, p) <= c * 1.0 + 0.01


def test_monotone_in_contracts():
    prev = -1.0
    for c in range(0, 500, 25):
        f = taker_fee_dollars(c, 0.5)
        assert f >= prev
        prev = f


def test_ceil_behaviour_explicit():
    """Guard the exact rounding rule: ceil(rate*C*p*(1-p)*100)/100."""
    c, p = 37, 0.31
    raw = TAKER_RATE * c * p * (1 - p)
    assert taker_fee_dollars(c, p) == pytest.approx(math.ceil(raw * 100) / 100)
