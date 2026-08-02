"""Fee arithmetic tests — failure mode #4 guard.

Anchored on the reference points fixed in the master prompt:
    1.75c at 50c,  0.63c at 90c,  0.63c at 10c  (per contract)
"""
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fees import (  # noqa: E402
    kalshi_fee,
    kalshi_fee_per_contract_unrounded,
    kalshi_round_trip,
    kalshi_hold_to_settlement,
    polymarket_fee,
    polymarket_fee_raw_onchain,
    polymarket_published_fee,
    POLY_TAKER_RATE,
)


# ---------------------------------------------------- the three reference pts
def test_kalshi_reference_50c():
    """1.75c per contract at 50c."""
    f = kalshi_fee_per_contract_unrounded("0.50") * 100
    assert f == Decimal("1.75"), f


def test_kalshi_reference_90c():
    f = kalshi_fee_per_contract_unrounded("0.90") * 100
    assert f == Decimal("0.63"), f


def test_kalshi_reference_10c():
    f = kalshi_fee_per_contract_unrounded("0.10") * 100
    assert f == Decimal("0.63"), f


def test_curve_is_symmetric():
    for pc in range(1, 50):
        lo = kalshi_fee_per_contract_unrounded(Decimal(pc) / 100)
        hi = kalshi_fee_per_contract_unrounded(Decimal(100 - pc) / 100)
        assert lo == hi, (pc, lo, hi)


def test_no_float_dust():
    """The exact expression from the prompt that produces 175.00000000000003."""
    bad = 0.07 * 100 * 0.5 * 0.5 * 100
    assert bad != 175.0  # documents the float bug
    good = kalshi_fee_per_contract_unrounded("0.5") * 100 * 100
    assert good == Decimal("175"), good


# ---------------------------------------------------------------- rounding
def test_kalshi_rounds_up_to_cent():
    """100 contracts at 50c = $1.75 exactly, no rounding needed."""
    assert kalshi_fee("0.50", 100) == Decimal("1.75")


def test_kalshi_roundup_punishes_small_orders():
    """Round-UP means small orders pay MORE than the headline rate.

    1 contract @50c: raw 0.0175 -> ceilings to 0.02, i.e. 2.00c not 1.75c
    (+14%). 2 contracts: raw 0.035 -> 0.04, i.e. 2.00c/contract (+14%).
    The penalty vanishes as size grows.
    """
    assert kalshi_fee("0.50", 1) == Decimal("0.02")
    assert kalshi_fee("0.50", 2) == Decimal("0.04")
    assert kalshi_fee("0.50", 100) == Decimal("1.75")  # no penalty at size


def test_kalshi_roundup_penalty_is_worst_in_the_tails():
    """A 1-lot at 5c pays 1.00c on a raw 0.33c fee — 3x the headline rate.

    This partly offsets the Family D 'tails are cheap' argument for small
    orders, and does NOT offset it for large ones.
    """
    raw_tail = kalshi_fee_per_contract_unrounded("0.05") * 100
    assert raw_tail == Decimal("0.3325")
    assert kalshi_fee("0.05", 1) == Decimal("0.01")      # 1.00c charged
    assert kalshi_fee("0.05", 1000) == Decimal("3.33")   # 0.333c/contract


def test_kalshi_tail_is_cheaper_than_mid():
    mid = kalshi_fee_per_contract_unrounded("0.50")
    tail = kalshi_fee_per_contract_unrounded("0.10")
    assert tail < mid
    # tail fee is 36% of the mid fee
    assert (tail / mid) == Decimal("0.36")


# -------------------------------------------------------------- Polymarket
def test_kalshi_crypto_maker_fee_is_zero():
    """Verified from the API: crypto series are fee_type `quadratic`, which is
    taker-only. `quadratic_with_maker_fees` exists but covers 130 non-crypto
    series. This CORRECTS the earlier 0.25x-taker assumption."""
    from fees import (KALSHI_MAKER_RATE_CRYPTO,
                      KALSHI_MAKER_RATE_WHERE_CHARGED)
    assert KALSHI_MAKER_RATE_CRYPTO == Decimal("0")
    assert kalshi_fee_per_contract_unrounded(
        "0.50", KALSHI_MAKER_RATE_CRYPTO) == Decimal("0")
    # where it IS charged it is a quarter of taker
    taker = kalshi_fee_per_contract_unrounded("0.50")
    maker = kalshi_fee_per_contract_unrounded(
        "0.50", KALSHI_MAKER_RATE_WHERE_CHARGED)
    assert maker == taker / 4


def test_maker_round_trip_margin_at_one_cent_tick():
    """The market-making arithmetic that matters.

    Minimum tick on the crypto hourly ladders is 1c, so a maker capturing the
    touch earns 1.00c gross. With a zero maker fee the full 1.00c survives to
    meet adverse selection. Under the old (wrong) 0.25x assumption only 0.125c
    would have survived -- an 8x difference in the margin available.
    """
    from fees import (KALSHI_MAKER_RATE_CRYPTO,
                      KALSHI_MAKER_RATE_WHERE_CHARGED)
    tick = Decimal("0.01")
    rt_zero = 2 * kalshi_fee_per_contract_unrounded(
        "0.50", KALSHI_MAKER_RATE_CRYPTO)
    rt_charged = 2 * kalshi_fee_per_contract_unrounded(
        "0.50", KALSHI_MAKER_RATE_WHERE_CHARGED)
    assert rt_zero == Decimal("0")
    assert (tick - rt_zero) == Decimal("0.01")            # 1.00c margin
    assert rt_charged == Decimal("0.00875")               # 0.875c
    assert (tick - rt_charged) == Decimal("0.00125")      # 0.125c


def test_polymarket_rate_is_1000bps():
    assert POLY_TAKER_RATE == Decimal("0.1")


def test_polymarket_is_NOT_the_same_as_kalshi():
    """RETRACTED CLAIM. The venues were reported as having identical taker
    costs. On-chain fills disprove it: Polymarket is 2.86x Kalshi at 50c."""
    k = kalshi_fee_per_contract_unrounded("0.50")     # 0.0175
    p = polymarket_fee("0.50", 1)                     # 0.05
    assert p > k
    assert (p / k).quantize(Decimal("0.01")) == Decimal("2.86")


def test_polymarket_economic_fee_curve():
    """rate * min(p, 1-p) -- verified to machine precision on 4,310 fills."""
    cases = {"0.05": "0.005", "0.10": "0.010", "0.25": "0.025",
             "0.50": "0.050", "0.75": "0.025", "0.90": "0.010",
             "0.95": "0.005"}
    for p, want in cases.items():
        assert polymarket_fee(p, 1) == Decimal(want).quantize(
            Decimal("0.00001")), p


def test_polymarket_onchain_buy_branch_is_flat_below_50c():
    """The BUY branch divides by p, so below 50c it collapses to rate*shares
    -- exactly the flat 0.100000 tokens/share observed on-chain."""
    for p in ["0.05", "0.20", "0.40", "0.49"]:
        raw = polymarket_fee_raw_onchain(p, 1, "BUY")
        assert abs(raw - Decimal("0.1")) < Decimal("1e-9"), (p, raw)


def test_polymarket_onchain_buy_branch_declines_above_50c():
    """At 80c: 0.10*0.20/0.80 = 0.025 tokens/share -- matches observation."""
    assert abs(polymarket_fee_raw_onchain("0.80", 1, "BUY")
               - Decimal("0.025")) < Decimal("1e-9")


def test_polymarket_sell_branch_is_the_economic_fee():
    for p in ["0.10", "0.50", "0.90"]:
        assert (polymarket_fee_raw_onchain(p, 1, "SELL")
                == polymarket_fee(p, 1))


def test_published_formula_does_not_match_reality():
    """Documentation says $1.75/100sh at 50c; on-chain says $5.00."""
    assert polymarket_published_fee("0.50", 100) == Decimal("1.75000")
    assert polymarket_fee("0.50", 100) == Decimal("5.00000")


# ------------------------------------------------------------- round trips
def test_round_trip_is_two_fees():
    rt = kalshi_round_trip("0.50", "0.50", 100)
    assert rt == Decimal("3.50")


def test_hold_to_settlement_is_one_fee():
    """Family B: half the cost bar of a taker round trip."""
    one = kalshi_hold_to_settlement("0.50", 100)
    two = kalshi_round_trip("0.50", "0.50", 100)
    assert one == Decimal("1.75")
    assert two == one * 2


def test_tail_round_trip_vs_mid_round_trip():
    """Family D rationale: tail round trips cost ~a third of mid ones."""
    mid = kalshi_round_trip("0.50", "0.50", 100)
    tail = kalshi_round_trip("0.10", "0.10", 100)
    assert tail == Decimal("1.26")
    assert mid == Decimal("3.50")
