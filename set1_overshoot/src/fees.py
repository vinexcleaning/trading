"""Kalshi fee arithmetic for set1_overshoot — re-exported from common/.

This file was a byte-identical copy of `common/kalshi_fees.py`. It is now a
thin re-export so there is exactly one implementation in the repo. Every name
this module used to define is still available, unchanged:

    RATE, CENT, fee_rate_cents, fee_order_cents, roundtrip_cost_cents

so `import fees` keeps working everywhere in this project.

The shared module also carries the per-series maker schedule (`SeriesFees`,
`maker_fee_order_cents`), which this project needs: KXATPMATCH/KXWTAMATCH are
`quadratic_with_maker_fees` while Challenger and ITF — ~91% of the tennis book
— are plain `quadratic` with NO maker fee. See LEDGER S010 and
`p5_task1b.py`, which tests both readings of the maker rate because the rate
itself is not API-verifiable.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "common"))

from kalshi_fees import (  # noqa: F401,E402
    CENT,
    MAKER_FLAT_CENTS_ALTERNATIVE,
    MAKER_RATE_IS_VERIFIED,
    MAKER_RATE_WHERE_CHARGED,
    RATE,
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

if __name__ == "__main__":
    import kalshi_fees
    print(f"re-exported from {kalshi_fees.__file__}")
    for p in (50, 90, 10):
        print(f"  {p:3d}c -> {fee_rate_cents(p)} cents / contract")
