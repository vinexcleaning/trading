"""Kalshi fee arithmetic — THE implementation. Exact Decimal, no float.

STANDING BACKLOG #6 / GUARDS #6. Before this module was made canonical the
Kalshi fee formula existed **fifteen times** across five codebases. Nine of
those fifteen carried the float-dust bug:

    0.07 * 100 * 0.5 * 0.5 * 100  ==  175.00000000000003

A naive `ceil()` on that turns the correct 175c fee into 176c. Measured over
the integer-cent x order-size grid, each unguarded copy overcharges on 115 of
1,881 cells (~6%) — including 8, 12, 25 and 32 contracts at 50c, which are
real live-bot order sizes. Two of the nine were in the live-money path
(`tennis_engine.py`, `paper_bot.py`).

Nothing in this module touches binary float where a fee is concerned.

THE FORMULA
    fee = roundup_to_cent( rate * C * P * (1 - P) )   per order

with P the price in dollars, C the contract count, rounded UP per order (not
per contract — the round-up is punitive on small orders and that is the point).
There is no separate settlement fee: holding to settlement pays the entry fee
only; an early exit pays entry + exit.

THE RATE IS NOT A CONSTANT — READ IT PER SERIES
    Kalshi exposes `fee_type` and `fee_multiplier` on each series object.

      fee_type = "quadratic"                  -> taker fees only, no maker fee
      fee_type = "quadratic_with_maker_fees"  -> makers also pay, at 25% of taker
      fee_multiplier = 0                      -> the series is fee-free entirely

    Verified against the live API on 2026-08-03 (`/trade-api/v2/series`,
    full pagination, 12,396 series):

      quadratic                    12,266   (of which 14 have fee_multiplier 0)
      quadratic_with_maker_fees       130
      fee_multiplier == 0              14

    The 130 is exact and unchanged since the 2026-08-01 census; the total grew
    12,368 -> 12,396, and the taker-only count grew 12,224 -> 12,252 by the
    same 28. The maker-fee series are Sports 107, Economics 10, Entertainment
    7, Financials 3, **Crypto 2**, Science and Technology 1.

    ** The two crypto series are KXBTCMAX150 and KXBTCMAX125. ** This refutes
    the "ZERO are crypto" comment that `crypto/src/fees.py` used to justify
    `KALSHI_MAKER_RATE = 0`. Do not hardcode a maker rate. Pass a `SeriesFees`
    read from the API and let it answer.

Reference points, per contract, unrounded:
    1.75c at 50c   ·   0.63c at 90c   ·   0.63c at 10c
Asserted at import time (guard-rot protection, GUARDS #9).
"""
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

# ------------------------------------------------------------------ rates
TAKER_RATE = Decimal("0.07")

# Applies ONLY on fee_type == "quadratic_with_maker_fees". Never apply it
# without checking fee_type first.
#
# ⚠ THE MAKER *RATE* IS NOT API-VERIFIABLE. The series object exposes exactly
# two fee fields — `fee_type` and `fee_multiplier` — and no maker rate
# (confirmed against /series/{ticker} for KXATPMATCH, KXNBA, KXBTCMAX150 on
# 2026-08-03; full key list has no maker field). WHICH series charge makers is
# a hard API fact. HOW MUCH is taken from Kalshi's published schedule.
#
# Two incompatible readings of that schedule exist in this repo and they are
# not reconcilable from data:
#
#   (a) 25% of taker, same quadratic shape  -> 0.0175 * C * P * (1-P)
#       used by crypto/, kalshi-market-scan/, kalshi-inplay-bot/
#   (b) a FLAT 0.25c per contract           -> 0.25 * C
#       used by set1_overshoot/ (p5_task1b.py), which flags it as
#       "NOT verifiable from the read-only API" and tests both arms
#
# They cross: at 95c, (a) is 0.083c/contract while (b) is 0.25c; at 50c (a) is
# 0.4375c while (b) is 0.25c. Neither dominates, so the choice changes results
# in a price-dependent direction. (a) is the default here because it matches
# the `quadratic_with_maker_fees` name and three of the four codebases, but it
# is a CONVENTION, not a measurement. If a maker result ever matters, run both
# arms — see set1_overshoot/src/p5_task1b.py for the pattern.
MAKER_RATE_WHERE_CHARGED = Decimal("0.0175")
MAKER_RATE_IS_VERIFIED = False

#: The competing flat-rate reading, in cents per contract. Not used by default.
MAKER_FLAT_CENTS_ALTERNATIVE = Decimal("0.25")

FEE_TYPE_TAKER_ONLY = "quadratic"
FEE_TYPE_WITH_MAKER = "quadratic_with_maker_fees"

CENT = Decimal("1")
HUNDRED = Decimal(100)

# Back-compat: the pre-consolidation name for the taker rate.
RATE = TAKER_RATE

# The census as measured, for documentation and tests. NOT used in any
# calculation — series counts drift, `fee_type` does not.
CENSUS_DATE = "2026-08-03"
CENSUS_TOTAL_SERIES = 12396
CENSUS_MAKER_FEE_SERIES = 130
CENSUS_ZERO_MULTIPLIER_SERIES = 14
CENSUS_CRYPTO_MAKER_SERIES = ("KXBTCMAX150", "KXBTCMAX125")


def _d(x):
    """Coerce to Decimal without routing through binary float."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


# ------------------------------------------------- per-series fee schedule
@dataclass(frozen=True)
class SeriesFees:
    """The fee schedule for one series, as read from the Kalshi API.

    Build it with `SeriesFees.from_api(series_object)`. The whole point of
    this type is that maker fees are a per-series fact, not a constant.
    """
    ticker: str
    fee_type: str
    fee_multiplier: Decimal = Decimal(1)

    @classmethod
    def from_api(cls, obj):
        """From a `/trade-api/v2/series` (or `/series/{t}`) series object."""
        if "fee_type" not in obj:
            raise KeyError(
                f"series object for {obj.get('ticker', '?')} has no 'fee_type'; "
                "refusing to guess a fee schedule")
        return cls(ticker=obj.get("ticker", "?"),
                   fee_type=obj["fee_type"],
                   fee_multiplier=_d(obj.get("fee_multiplier", 1)))

    @property
    def charges_maker(self) -> bool:
        return self.fee_type == FEE_TYPE_WITH_MAKER

    @property
    def taker_rate(self) -> Decimal:
        return TAKER_RATE * self.fee_multiplier

    @property
    def maker_rate(self) -> Decimal:
        if not self.charges_maker:
            return Decimal(0)
        return MAKER_RATE_WHERE_CHARGED * self.fee_multiplier


#: The schedule that applies to all but 144 of 12,396 series. Use it only when
#: you have confirmed the series is plain `quadratic`.
TAKER_ONLY = SeriesFees("<taker-only>", FEE_TYPE_TAKER_ONLY, Decimal(1))


# --------------------------------------------------- core, price in CENTS
def fee_rate_cents(price_cents, rate=TAKER_RATE) -> Decimal:
    """Unrounded per-contract fee, in cents, exact.

    For expectancy arithmetic, where the per-order round-up is an artefact of
    order size rather than an economic cost.
    """
    p = _d(price_cents)
    return _d(rate) * p * (HUNDRED - p) / HUNDRED


def fee_order_cents(price_cents, contracts=1, rate=TAKER_RATE) -> Decimal:
    """What an order of `contracts` is actually charged, in whole cents.

    Rounded UP per order, which is how Kalshi bills it.
    """
    return (fee_rate_cents(price_cents, rate) * _d(contracts)
            ).quantize(CENT, rounding=ROUND_CEILING)


def fee_order_dollars(price_cents, contracts=1, rate=TAKER_RATE) -> float:
    """`fee_order_cents` as float dollars, for dollar-native callers.

    The only float in the module, and it is applied to a value that is already
    a whole number of cents, so it cannot reintroduce the dust bug.
    """
    return float(fee_order_cents(price_cents, contracts, rate)) / 100.0


# ------------------------------------------------- price in DOLLARS (0..1)
def fee_rate_from_price(price_dollars, rate=TAKER_RATE) -> Decimal:
    """Unrounded per-contract fee in cents, from a price in dollars."""
    return fee_rate_cents(_d(price_dollars) * HUNDRED, rate)


def fee_order_from_price(price_dollars, contracts=1, rate=TAKER_RATE) -> Decimal:
    """Order fee in whole cents, from a price in dollars."""
    return fee_order_cents(_d(price_dollars) * HUNDRED, contracts, rate)


# ------------------------------------------------------------- maker side
def maker_fee_order_cents(price_cents, contracts, series: SeriesFees) -> Decimal:
    """Maker fee in whole cents. Requires a `SeriesFees` — never guesses.

    Returns exactly 0 on the 12,266 `quadratic` series. There is no default
    argument here on purpose: a caller that does not know the series' fee_type
    does not know its maker fee.
    """
    if not isinstance(series, SeriesFees):
        raise TypeError(
            "maker_fee_order_cents needs a SeriesFees read from the API "
            "(fee_type is per-series); got "
            f"{type(series).__name__}. Build one with SeriesFees.from_api().")
    if not series.charges_maker:
        return Decimal(0)
    return fee_order_cents(price_cents, contracts, series.maker_rate)


# ---------------------------------------------------------- round trips
def roundtrip_cost_cents(entry_cents, exit_cents=None, rate=TAKER_RATE) -> Decimal:
    """Total unrounded fee cost per contract, in cents.

    `exit_cents=None` means held to settlement, which pays the entry fee only.
    """
    c = fee_rate_cents(entry_cents, rate)
    if exit_cents is not None:
        c += fee_rate_cents(exit_cents, rate)
    return c


# -------------------------------------------------------------- vectorised
# These take the price in DOLLARS, because that is the form the analysis code
# holds it in. Do NOT ask the caller to multiply by 100 first: 0.49 * 100 is
# 49.000000000000007 in float, which is exactly the class of dust this module
# exists to keep out. Each element is coerced with Decimal(str(x)) instead.
#
# numpy is imported lazily so the live bot never needs it. Every element goes
# through Decimal, so this is exact but not fast — it is for analysis code
# over thousands of rows, not a hot loop.
def _vec(fn, prices_dollars, *args):
    import numpy as np
    arr = np.asarray(prices_dollars)
    if arr.ndim == 0:
        return float(fn(_d(arr.item()), *args))
    out = np.array([float(fn(_d(x), *args)) for x in arr.ravel()],
                   dtype=float)
    return out.reshape(arr.shape)


def fee_rate_from_price_vec(prices_dollars, rate=TAKER_RATE):
    """Unrounded per-contract fee in CENTS, for an array of dollar prices."""
    return _vec(fee_rate_from_price, prices_dollars, rate)


def fee_order_from_price_vec(prices_dollars, contracts=1, rate=TAKER_RATE):
    """Per-order fee in CENTS (ceil), for an array of dollar prices."""
    return _vec(fee_order_from_price, prices_dollars, contracts, rate)


def fee_dollars_from_price_vec(prices_dollars, contracts=1, rate=TAKER_RATE):
    """Per-order fee in DOLLARS (ceil to the cent), for dollar prices.

    This is the exact replacement for the `np.ceil(0.07*p*(1-p)*100)/100`
    idiom that appeared in three analysis scripts.
    """
    return fee_order_from_price_vec(prices_dollars, contracts, rate) / 100.0


# ------------------------------------------------------------------ guard
def _verify():
    """Reference points asserted at import. If this fails, do not trade."""
    for p, want in [(50, "1.75"), (90, "0.63"), (10, "0.63"),
                    (55, "1.7325"), (62, "1.6492"),
                    (1, "0.0693"), (99, "0.0693")]:
        got = fee_rate_cents(p)
        assert got == Decimal(want), f"{p}c -> {got}, expected {want}"

    # the float-dust regression, in the exact form that bit nine call sites
    assert fee_order_cents(50, 100) == Decimal("175")
    assert str(fee_rate_cents(50)) == "1.75"

    # per-order round-UP, not round-half
    assert fee_order_cents(50, 1) == Decimal("2")
    assert fee_order_cents(90, 100) == Decimal("63")

    # symmetric about 50c, zero at the boundaries, never negative
    assert fee_rate_cents(10) == fee_rate_cents(90)
    assert fee_rate_cents(0) == Decimal(0)
    assert fee_rate_cents(100) == Decimal(0)

    # maker side is gated on fee_type and defaults to nothing
    assert maker_fee_order_cents(50, 100, TAKER_ONLY) == Decimal(0)
    with_maker = SeriesFees("KXATPMATCH", FEE_TYPE_WITH_MAKER, Decimal(1))
    assert with_maker.maker_rate == Decimal("0.0175")
    assert maker_fee_order_cents(50, 100, with_maker) == Decimal("44")
    # fee_multiplier 0 means genuinely free
    free = SeriesFees("KXBTCY", FEE_TYPE_TAKER_ONLY, Decimal(0))
    assert free.taker_rate == Decimal(0)
    assert fee_order_cents(50, 100, free.taker_rate) == Decimal(0)


_verify()


if __name__ == "__main__":
    print(f"Kalshi fee arithmetic — verified. Census {CENSUS_DATE}: "
          f"{CENSUS_TOTAL_SERIES} series, {CENSUS_MAKER_FEE_SERIES} with "
          f"maker fees, {CENSUS_ZERO_MULTIPLIER_SERIES} fee-free.\n")
    print(f"{'price':>6}  {'per contract':>14}  {'order of 100':>14}")
    for pc in range(5, 100, 5):
        print(f"{pc:5d}c  {fee_rate_cents(pc):>13}c  "
              f"{fee_order_cents(pc, 100):>13}c")
