"""Exact fee arithmetic in Decimal cents.

This project has had float-dust bugs in three separate codebases
(`0.07*100*0.5*0.5*100` -> 175.00000000000003). Nothing here touches float.

Kalshi's trading fee is  fee = roundup( 0.07 * C * P * (1 - P) )  in dollars,
with P the price in dollars and C the contract count, rounded UP to the next
cent per order. There is no separate settlement fee: holding to settlement pays
the entry fee only, an early exit pays entry + exit.
"""
from decimal import Decimal, ROUND_CEILING

RATE = Decimal("0.07")
CENT = Decimal("1")


def fee_rate_cents(price_cents):
    """Unrounded per-contract fee, in cents, as an exact Decimal.

    Used for expectancy arithmetic, where per-order round-up is a rounding
    artefact of order size rather than an economic cost.
    """
    p = Decimal(int(price_cents))
    return RATE * p * (Decimal(100) - p) / Decimal(100)


def fee_order_cents(price_cents, contracts):
    """What an actual order of `contracts` is charged, in whole cents."""
    return (fee_rate_cents(price_cents) * Decimal(int(contracts))
            ).quantize(CENT, rounding=ROUND_CEILING)


def roundtrip_cost_cents(entry_cents, exit_cents=None):
    """Total fee cost per contract, in cents.

    exit_cents=None means held to settlement (entry fee only).
    """
    c = fee_rate_cents(entry_cents)
    if exit_cents is not None:
        c += fee_rate_cents(exit_cents)
    return c


def _verify():
    checks = [
        (50, Decimal("1.75")),
        (90, Decimal("0.63")),
        (10, Decimal("0.63")),
        (55, Decimal("1.7325")),
        (62, Decimal("1.6492")),
        (1, Decimal("0.0693")),
        (99, Decimal("0.0693")),
    ]
    for p, want in checks:
        got = fee_rate_cents(p)
        assert got == want, f"{p}c -> {got} expected {want}"
    # order-level round-up
    assert fee_order_cents(50, 1) == Decimal("2")
    assert fee_order_cents(50, 100) == Decimal("175")
    assert fee_order_cents(90, 100) == Decimal("63")
    # no float can leak in
    assert str(fee_rate_cents(50)) == "1.75"
    print("fee arithmetic verified:")
    for p, want in checks:
        print(f"  {p:3d}c -> {fee_rate_cents(p)} cents / contract")
    print(f"  order 100 @ 50c -> {fee_order_cents(50, 100)} cents")
    print(f"  round trip 55c in / 70c out -> "
          f"{roundtrip_cost_cents(55, 70)} cents")
    print(f"  hold to settle from 55c      -> "
          f"{roundtrip_cost_cents(55)} cents")


if __name__ == "__main__":
    _verify()
