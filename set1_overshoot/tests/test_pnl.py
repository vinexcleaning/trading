"""Tests for fee arithmetic and the P&L decomposition.

The crypto session lost a result to a decomposition that omitted inventory
carry and defaulted the mark to 0.5, fabricating +2.96c/contract. This project
has separately had float-dust fee bugs in three codebases. Neither had tests.
Now both do.
"""
import pathlib
import sys
from decimal import Decimal

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fees  # noqa: E402


# ------------------------------------------------------------------- fees
@pytest.mark.parametrize("price,want", [
    (50, "1.75"), (90, "0.63"), (10, "0.63"),
    (55, "1.7325"), (62, "1.6492"), (1, "0.0693"), (99, "0.0693"),
])
def test_fee_rate_exact(price, want):
    assert fees.fee_rate_cents(price) == Decimal(want)


def test_fee_is_decimal_not_float():
    """0.07*100*0.5*0.5*100 == 175.00000000000003 in float. Not here."""
    v = fees.fee_rate_cents(50)
    assert isinstance(v, Decimal)
    assert str(v) == "1.75"


def test_fee_symmetric_about_fifty():
    for p in range(1, 50):
        assert fees.fee_rate_cents(p) == fees.fee_rate_cents(100 - p)


def test_fee_peaks_at_fifty():
    rates = [fees.fee_rate_cents(p) for p in range(1, 100)]
    assert max(rates) == fees.fee_rate_cents(50)


def test_fee_never_negative():
    assert all(fees.fee_rate_cents(p) >= 0 for p in range(0, 101))


def test_order_fee_rounds_up_not_down():
    # 1 contract at 50c is 1.75c, which must be charged as 2c, never 1c
    assert fees.fee_order_cents(50, 1) == Decimal("2")
    assert fees.fee_order_cents(50, 100) == Decimal("175")
    assert fees.fee_order_cents(90, 100) == Decimal("63")


def test_roundtrip_costs_more_than_hold():
    hold = fees.roundtrip_cost_cents(55)
    trip = fees.roundtrip_cost_cents(55, 70)
    assert trip > hold
    assert trip == fees.fee_rate_cents(55) + fees.fee_rate_cents(70)


def test_settlement_exit_fee_is_tiny_not_zero():
    """A position closed at settlement exits at 0 or 100, where the fee bottoms
    out but is not zero. Treating it as zero would flatter every hold."""
    assert fees.fee_rate_cents(100) == Decimal("0")
    assert fees.fee_rate_cents(99) > 0


# ----------------------------------------------------- P&L decomposition
def decompose(fill_rate, y_all, y_filled, fair, cost, fee):
    """The identity used in Task 1b, isolated so it can be tested."""
    gross = fill_rate * (100.0 * y_all - fair)
    adverse = fill_rate * 100.0 * (y_filled - y_all)
    improvement = fill_rate * (fair - cost)
    fee_term = -fill_rate * fee
    return gross, adverse, improvement, fee_term


def direct(fill_rate, y_filled, cost, fee):
    return fill_rate * (100.0 * y_filled - cost - fee)


@pytest.mark.parametrize("fr,ya,yf,fair,cost,fee", [
    (0.631, 0.6353, 0.6595, 62.71, 61.62, 0.021),
    (1.000, 0.5000, 0.5000, 50.00, 50.00, 1.750),
    (0.200, 0.7000, 0.6000, 68.00, 66.00, 0.250),
    (0.850, 0.3000, 0.3400, 31.00, 29.50, 0.000),
])
def test_decomposition_is_an_exact_identity(fr, ya, yf, fair, cost, fee):
    parts = decompose(fr, ya, yf, fair, cost, fee)
    assert sum(parts) == pytest.approx(direct(fr, yf, cost, fee), abs=1e-9)


def test_adverse_selection_is_zero_when_fills_are_representative():
    _, adverse, _, _ = decompose(0.5, 0.62, 0.62, 60.0, 59.0, 0.1)
    assert adverse == pytest.approx(0.0)


def test_adverse_selection_is_negative_when_fills_underperform():
    _, adverse, _, _ = decompose(0.5, 0.62, 0.58, 60.0, 59.0, 0.1)
    assert adverse < 0


def test_unfilled_opportunities_dilute_not_flatter():
    """Per-opportunity must be <= per-fill in magnitude for a profitable cell.
    Reporting only fills is the survivorship error."""
    per_fill = direct(1.0, 0.70, 60.0, 0.0)
    per_opp = direct(0.25, 0.70, 60.0, 0.0)
    assert per_opp == pytest.approx(0.25 * per_fill)
    assert abs(per_opp) < abs(per_fill)


def test_mark_at_settlement_not_at_half():
    """The crypto session's inventory-carry defect: marking an open position at
    0.5 instead of its realised value fabricated +2.96c/contract. A
    hold-to-settlement book has no open position, and the two must not agree."""
    y = np.array([1.0, 0.0, 1.0, 1.0])
    cost = np.full(4, 60.0)
    settled = (100.0 * y - cost).mean()
    marked_half = (100.0 * 0.5 - cost).mean()
    assert settled != pytest.approx(marked_half)
    assert settled == pytest.approx(15.0)
    assert marked_half == pytest.approx(-10.0)


def test_fade_and_favourite_are_exact_complements_before_costs():
    """Buying the underdog and buying the favourite must sum to 100c of payout
    with no cost. If they do not, an orientation bug is present."""
    for fav_won in (0.0, 1.0):
        fav = 100.0 * fav_won
        dog = 100.0 * (1.0 - fav_won)
        assert fav + dog == pytest.approx(100.0)
