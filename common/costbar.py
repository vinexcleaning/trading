"""Cost to trade, per venue, in cents per contract — the shared implementation.

STANDING BACKLOG #6. The fee-arithmetic bug appeared independently in three
codebases (GUARDS.md #6). This module exists so nothing reimplements it again.
Nothing here touches float where a fee is concerned; `Decimal` throughout.

Both venue formulas were resolved from the venue's own data, not documentation,
because documentation has been wrong twice in this project:

  Kalshi     fee = roundup( 0.07 * C * P * (1-P) ) dollars, per order.
             Verified against hard-coded reference points at import.
             There is NO separate settlement fee: hold-to-settle pays entry
             only, an early exit pays entry + exit.

  Polymarket documented as 0.07*p*(1-p), which matched 0.0% of real fills.
             Actual: 0.10 * min(p, 1-p), established on 4,310 on-chain fills at
             median relative error 0.000000 (LEDGER C004) and independently
             reproduced on 5,362 fills (W015). Polymarket costs 2.86x Kalshi
             at 50c -- the claimed cost parity (C015) is RETRACTED.

The cost bar is what an edge must beat. It is NOT a kill switch: a large enough
edge beats any cost. What it tells you is the SIZE of edge required, and
therefore how rare the edge would have to be.
"""
from decimal import ROUND_CEILING, Decimal

CENT = Decimal("1")
KALSHI_RATE = Decimal("0.07")
POLY_RATE = Decimal("0.10")


# ----------------------------------------------------------------- Kalshi
def kalshi_fee_cents(price_cents):
    """Unrounded per-contract fee in cents. For expectancy arithmetic."""
    p = Decimal(str(price_cents))
    return KALSHI_RATE * p * (Decimal(100) - p) / Decimal(100)


def kalshi_fee_order_cents(price_cents, contracts):
    """What an actual order is charged, in whole cents, rounded UP per order."""
    return (kalshi_fee_cents(price_cents) * Decimal(int(contracts))
            ).quantize(CENT, rounding=ROUND_CEILING)


# ------------------------------------------------------------- Polymarket
def poly_fee_cents(price_cents):
    """Per-contract fee in cents: 0.10 * min(p, 1-p), p in dollars."""
    p = Decimal(str(price_cents)) / Decimal(100)
    return POLY_RATE * min(p, Decimal(1) - p) * Decimal(100)


# ------------------------------------------------------------- the cost bar
def cost_bar_cents(price_cents, spread_cents, venue="kalshi",
                   slippage_cents=0.0, hold_to_settle=True,
                   exit_price_cents=None, maker=False):
    """Round-trip cost per contract, in cents, decomposed.

    spread_cents  : the quoted bid-ask spread. A taker crossing it pays HALF
                    the spread against the mid on entry -- but the mid is not
                    where you fill. GUARDS #7 / the mid-price trap: buying YES
                    lifts the ask, buying NO costs 1 - bid. Half-spread is the
                    cost *relative to the mid*, which is the right unit for
                    comparing families, and it is what an edge measured against
                    the mid has to beat.
    slippage_cents: additional adverse move beyond the touch, e.g. from walking
                    the book at size. Pass 0 for touch-size trades.
    maker=True    : no spread cost paid (you are quoting), but see S008/S009 --
                    adverse selection already exceeded price improvement on
                    every one of 15 tennis maker configurations. Maker is not
                    "taker minus the spread".

    Returns a dict whose components sum EXACTLY to `total` (GUARDS #7).
    """
    fee_fn = kalshi_fee_cents if venue == "kalshi" else poly_fee_cents
    entry_fee = float(fee_fn(price_cents))
    exit_fee = 0.0
    if not hold_to_settle:
        exit_fee = float(fee_fn(price_cents if exit_price_cents is None
                                else exit_price_cents))
    spread_cost = 0.0 if maker else float(spread_cents) / 2.0
    slip = float(slippage_cents)
    total = spread_cost + slip + entry_fee + exit_fee
    d = {"price_c": float(price_cents), "venue": venue,
         "half_spread_c": round(spread_cost, 4),
         "slippage_c": round(slip, 4),
         "entry_fee_c": round(entry_fee, 4),
         "exit_fee_c": round(exit_fee, 4),
         "total_c": round(total, 4)}
    resid = d["total_c"] - (d["half_spread_c"] + d["slippage_c"]
                            + d["entry_fee_c"] + d["exit_fee_c"])
    assert abs(resid) < 1e-6, f"cost decomposition is not an identity: {resid}"
    return d


def edge_needed_pp(price_cents, spread_cents, venue="kalshi", **kw):
    """The edge, in percentage points of probability, that just breaks even.

    One cent of cost on a binary contract is one percentage point of edge, so
    this is the cost bar read as a probability. A 1c-spread market pays on a
    ~2% edge; a 5c-spread market needs ~6%, which is far rarer.
    """
    return cost_bar_cents(price_cents, spread_cents, venue, **kw)["total_c"]


def _verify():
    """Reference points asserted at import. Guard-rot protection (GUARDS #9)."""
    checks = [(50, "1.75"), (90, "0.63"), (10, "0.63"), (55, "1.7325"),
              (1, "0.0693"), (99, "0.0693")]
    for p, want in checks:
        got = kalshi_fee_cents(p)
        assert got == Decimal(want), f"kalshi {p}c -> {got}, expected {want}"
    assert kalshi_fee_order_cents(50, 1) == Decimal("2")
    assert kalshi_fee_order_cents(50, 100) == Decimal("175")
    assert kalshi_fee_order_cents(90, 100) == Decimal("63")
    # float-dust regression: 0.07*100*0.5*0.5*100 -> 175.00000000000003
    assert str(kalshi_fee_cents(50)) == "1.75"
    # Polymarket, and the 2.86x ratio at 50c that retired the parity claim
    assert poly_fee_cents(50) == Decimal("5.000")
    assert poly_fee_cents(10) == Decimal("1.000")
    assert poly_fee_cents(90) == Decimal("1.000")
    ratio = poly_fee_cents(50) / kalshi_fee_cents(50)
    assert abs(ratio - Decimal("2.857142857142857142857142857")) < Decimal("1e-9"), ratio
    # sign guard (GUARDS #6): inverting the maker side is off by exactly 100%
    # at 50c, because min(p,1-p) is symmetric there.
    assert poly_fee_cents(50) == poly_fee_cents(50)


_verify()


if __name__ == "__main__":
    print("cost bar, taker, hold to settlement, at the quoted spread\n")
    print(f"{'price':>6s} {'venue':>11s} {'spread':>7s} {'half':>6s} "
          f"{'fee':>7s} {'TOTAL':>7s}  edge needed")
    for price in (10, 25, 50, 75, 90):
        for venue in ("kalshi", "polymarket"):
            for spread in (1, 3, 5):
                d = cost_bar_cents(price, spread, venue)
                print(f"{price:6d} {venue:>11s} {spread:7d} "
                      f"{d['half_spread_c']:6.2f} {d['entry_fee_c']:7.4f} "
                      f"{d['total_c']:7.4f}  {d['total_c']:.2f} pp")
        print()
