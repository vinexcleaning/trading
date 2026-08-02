"""Exact-decimal fee arithmetic for Kalshi and Polymarket.

Failure mode #4 in this project (independently rediscovered in 3 codebases):
    0.07*100*0.5*0.5*100 == 175.00000000000003
Never use binary floats for money here. Everything below is `decimal.Decimal`.

Reference points the prompt fixes for the quadratic schedule:
    1.75c at 50c,  0.63c at 90c,  0.63c at 10c   (per contract)

Both venues use the SAME functional form for crypto taker fees:
    fee_per_contract = rate * p * (1 - p)
with rate = 0.07. They differ in (a) rounding and (b) the maker side.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

# ---------------------------------------------------------------- constants
KALSHI_TAKER_RATE = Decimal("0.07")

# --- Kalshi MAKER fee, RESOLVED 2026-08-01 from the API + docs ---
# Kalshi has TWO fee types, exposed per series as `fee_type`:
#   `quadratic`                  -> TAKER FEES ONLY. No maker fee.
#   `quadratic_with_maker_fees`  -> makers also pay, at 25% of taker.
# Across ALL 12,368 Kalshi series: 12,224 are `quadratic`, 130 are
# `quadratic_with_maker_fees`, 14 are `quadratic` with fee_multiplier 0.
# The 130 maker-fee series are Sports / Entertainment / Economics /
# Financials -- championships, awards, unemployment prints. **ZERO are
# crypto.** Kalshi's own docs corroborate: maker fees apply to "some markets
# ... often due to special events".
#
# => On every crypto series in this project the MAKER FEE IS ZERO.
#
# This corrects venue_spec.md, which recorded ~0.25x taker at confidence B
# from documentation alone. The documentation describes the rate that applies
# WHERE a maker fee exists; it does not apply to crypto.
KALSHI_MAKER_RATE_WHERE_CHARGED = Decimal("0.0175")   # 0.25 x taker
KALSHI_MAKER_RATE_CRYPTO = Decimal("0")               # verified: no maker fee

# Back-compat name used by earlier code paths. Now correctly zero for crypto.
KALSHI_MAKER_RATE = KALSHI_MAKER_RATE_CRYPTO

MAKER_FEE_SERIES_COUNT = 130          # of 12,368, none crypto
TOTAL_SERIES_COUNT = 12368

# --- Polymarket, RESOLVED EMPIRICALLY from on-chain fills (2026-08-01) ---
# The published schedule implies 0.07 * p * (1-p). On-chain reality is a
# DIFFERENT SHAPE and a HIGHER rate. Verified against 4,310 fee-bearing fills
# (2026-04-20..27): median relative error 0.000000, 100% within 1%, both sides.
#
#   economic fee per share, dollars = (feeRateBps/10000) * min(p, 1-p)
#
# with feeRateBps = 1000 observed uniformly. The raw on-chain amount is
# side-dependent because the fee is taken in whichever asset the taker
# receives:
#   BUY  fee_tokens = rate * min(p,1-p) * shares / p   (tokens, worth p each)
#   SELL fee_usdc   = rate * min(p,1-p) * shares       (collateral)
# Both reduce to the same ECONOMIC cost above.
#
# At 50c this is 5.00c/share vs Kalshi's 1.75c -- 2.86x, not parity.
POLY_FEE_RATE_BPS = Decimal("1000")
POLY_TAKER_RATE = POLY_FEE_RATE_BPS / Decimal("10000")   # 0.10

# The published (documentation) figure, retained ONLY to reproduce the claim
# in venue docs. Do not use it for cost modelling.
POLY_PUBLISHED_CRYPTO_RATE = Decimal("0.07")

# Maker exemption is UNVERIFIED. `maker_base_fee` reads 1000 on live markets
# (the market MAXIMUM, not necessarily the signed rate). The on-chain data
# that could settle it ends 2026-04-28. Treat any maker-side advantage as
# provisional.
POLY_MAKER_RATE_VERIFIED = None

CENT = Decimal("0.01")
FIVE_DP = Decimal("0.00001")


def _d(x) -> Decimal:
    """Coerce to Decimal without going through binary float where possible."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


# ------------------------------------------------------------------ Kalshi
def kalshi_fee(price, contracts, rate=KALSHI_TAKER_RATE) -> Decimal:
    """Kalshi trading fee in DOLLARS for `contracts` at `price` dollars/contract.

    Kalshi: fee = ceil_to_cent(rate * C * P * (1 - P)).
    The round-UP is per order and is punitive on small orders.
    """
    p = _d(price)
    c = _d(contracts)
    raw = _d(rate) * c * p * (Decimal(1) - p)
    return raw.quantize(CENT, rounding=ROUND_CEILING)


def kalshi_fee_per_contract_unrounded(price, rate=KALSHI_TAKER_RATE) -> Decimal:
    """Un-rounded per-contract fee in dollars — the shape of the curve."""
    p = _d(price)
    return _d(rate) * p * (Decimal(1) - p)


# -------------------------------------------------------------- Polymarket
def polymarket_fee(price, shares, rate=POLY_TAKER_RATE) -> Decimal:
    """Polymarket ECONOMIC taker fee in dollars — the empirically verified form.

        fee = shares * rate * min(p, 1 - p)

    Verified to machine precision against 4,310 on-chain fills.
    """
    p = _d(price)
    c = _d(shares)
    raw = _d(rate) * c * min(p, Decimal(1) - p)
    if raw == 0:
        return Decimal("0")
    return raw.quantize(FIVE_DP, rounding=ROUND_HALF_UP)


def polymarket_fee_raw_onchain(price, shares, side,
                               rate=POLY_TAKER_RATE) -> Decimal:
    """The RAW on-chain amount, in whichever asset the taker receives.

    side='BUY'  -> returned in outcome TOKENS  (each worth `price`)
    side='SELL' -> returned in USDC
    """
    p = _d(price)
    c = _d(shares)
    m = min(p, Decimal(1) - p)
    if side == "BUY":
        return _d(rate) * m * c / p
    return _d(rate) * m * c


def polymarket_published_fee(price, shares,
                             rate=POLY_PUBLISHED_CRYPTO_RATE) -> Decimal:
    """The DOCUMENTED formula, 0.07*p*(1-p). Does NOT match observed fills.

    Kept only to quantify the gap between documentation and reality.
    """
    p = _d(price)
    c = _d(shares)
    return (_d(rate) * c * p * (Decimal(1) - p)).quantize(
        FIVE_DP, rounding=ROUND_HALF_UP)


# ------------------------------------------------------------ round trips
def kalshi_round_trip(entry_price, exit_price, contracts,
                      entry_rate=KALSHI_TAKER_RATE,
                      exit_rate=KALSHI_TAKER_RATE) -> Decimal:
    """Two fees: one in, one out."""
    return (kalshi_fee(entry_price, contracts, entry_rate)
            + kalshi_fee(exit_price, contracts, exit_rate))


def kalshi_hold_to_settlement(entry_price, contracts,
                              rate=KALSHI_TAKER_RATE) -> Decimal:
    """One fee only. Settlement itself is not charged on Kalshi."""
    return kalshi_fee(entry_price, contracts, rate)


if __name__ == "__main__":
    print("Kalshi per-contract fee curve (unrounded, cents):")
    for pc in range(5, 100, 5):
        p = Decimal(pc) / 100
        f = kalshi_fee_per_contract_unrounded(p) * 100
        print(f"  p={pc:>3}c   fee={f:.4f}c")
