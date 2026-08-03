"""No-arbitrage violation detection, net of fees and the spread actually crossed.

Three checkable constraints that require zero forecasting skill:
  1. bucket_sum      — mutually exclusive & exhaustive buckets must price to 100c
  2. monotone_ladder — nested thresholds must be monotone in strike
  3. combo_vs_legs   — a parlay must not exceed the product of its legs

Everything is reported net of round-trip taker fees on every leg. A 1c violation is
not an arb when each leg costs ~3.5c to round-trip, so the fee subtraction is the
whole point, not a refinement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal

from .fees import taker_fee_dollars


@dataclass(frozen=True)
class Quote:
    """Top of book for one market. Prices in dollars (0..1). None = no quote."""

    ticker: str
    yes_bid: float | None
    yes_ask: float | None
    yes_bid_size: float = 0.0
    yes_ask_size: float = 0.0
    floor_strike: float | None = None
    cap_strike: float | None = None
    strike_type: str | None = None

    @property
    def mid(self) -> float | None:
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return (self.yes_bid + self.yes_ask) / 2

    @property
    def spread(self) -> float | None:
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return self.yes_ask - self.yes_bid


@dataclass(frozen=True)
class Violation:
    kind: Literal["bucket_sum_low", "bucket_sum_high", "monotone_ladder", "combo_vs_legs"]
    family: str
    tickers: tuple[str, ...]
    gross_edge_cents: float
    fee_cents: float
    net_edge_cents: float
    size_available: float
    detail: str = ""
    legs: tuple[dict, ...] = field(default_factory=tuple)

    @property
    def is_arb(self) -> bool:
        return self.net_edge_cents > 0 and self.size_available > 0


def classify_family(quotes: Iterable[Quote]) -> Literal["bucket", "ladder", "unknown"]:
    """Decide which no-arbitrage constraint an event's markets actually satisfy.

    This must be derived from `strike_type`, never assumed per series. Getting it
    wrong manufactures enormous false positives: summing 60 nested
    `greater_or_equal` thresholds as if they were exhaustive buckets yields an
    apparent 1,300c "arb" on a 100c contract.

      bucket — contains `between` markets; the union of {less, between..., greater}
               tiles the outcome line, so YES prices must sum to 100c.
      ladder — only threshold markets (`greater*` / `less`); these are nested and
               monotone in strike, and must NOT be summed.
    """
    types = {q.strike_type for q in quotes if q.strike_type}
    if not types:
        return "unknown"
    if any(t == "between" for t in types):
        return "bucket"
    if all(t in ("greater", "greater_or_equal", "less", "less_or_equal") for t in types):
        return "ladder"
    return "unknown"


def _round_trip_fee_cents_per_contract(price: float, multiplier: float = 1.0) -> float:
    """Both legs of a taker round trip, per contract, in cents.

    For a locked arb the position is held to settlement, so strictly only the entry
    fee is paid. We charge the round trip anyway: it is the conservative choice and
    covers the case where we must unwind before expiry.
    """
    c = 10_000  # large C so the per-fill ceiling doesn't dominate the per-contract rate
    return 2 * taker_fee_dollars(c, price, multiplier) * 100.0 / c


def verify_bucket_coverage(quotes: Iterable[Quote], tol: float = 0.02) -> tuple[bool, str]:
    """Check that a bucket family really tiles the outcome line exactly once.

    The bucket-sum constraint only holds for a mutually exclusive AND exhaustive
    set. A missing tail or a gap between buckets breaks exhaustiveness; an extra
    overlapping threshold market breaks exclusivity. Either way the sum is not
    required to be 100c and any "violation" is an artifact.
    """
    qs = list(quotes)
    betweens = sorted(
        (q for q in qs if q.strike_type == "between"),
        key=lambda q: q.floor_strike if q.floor_strike is not None else float("-inf"),
    )
    if not betweens:
        return False, "no between buckets"
    if any(q.floor_strike is None or q.cap_strike is None for q in betweens):
        return False, "between bucket missing floor or cap"

    lows = [q for q in qs if q.strike_type in ("less", "less_or_equal")]
    highs = [q for q in qs if q.strike_type in ("greater", "greater_or_equal")]
    if len(lows) != 1 or len(highs) != 1:
        return False, f"expected exactly one low and one high tail, got {len(lows)}/{len(highs)}"
    if len(lows) + len(highs) + len(betweens) != len(qs):
        return False, "unexpected extra markets in family"

    # buckets must be contiguous: next floor picks up where previous cap left off
    for a, b in zip(betweens, betweens[1:]):
        if b.floor_strike - a.cap_strike > tol + 1e-9:  # type: ignore[operator]
            return False, f"gap between {a.cap_strike} and {b.floor_strike}"
        if b.floor_strike < a.cap_strike - tol:  # type: ignore[operator]
            return False, f"overlap between {a.cap_strike} and {b.floor_strike}"
    # tails must abut the bucket range
    if lows[0].cap_strike is None or highs[0].floor_strike is None:
        return False, "tail missing its strike"
    if abs(lows[0].cap_strike - betweens[0].floor_strike) > tol + 1e-9:  # type: ignore[operator]
        return False, "low tail does not abut first bucket"
    if abs(highs[0].floor_strike - (betweens[-1].cap_strike + 0.01)) > tol + 1e-9:  # type: ignore[operator]
        return False, "high tail does not abut last bucket"
    return True, f"{len(qs)} markets tile the line ({len(betweens)} buckets + 2 tails)"


def check_bucket_sum(
    family: str,
    quotes: Iterable[Quote],
    multiplier: float = 1.0,
    require_coverage: bool = False,
) -> list[Violation]:
    """Buckets are mutually exclusive and exhaustive, so they must price to 100c.

    - sum(asks) < 100c  -> buy every bucket, guaranteed 100c payout
    - sum(bids) > 100c  -> sell every bucket, guaranteed 100c liability

    With `require_coverage=True` the family must first pass
    `verify_bucket_coverage`. Live scanning should always set this; the unit tests
    exercise the arithmetic on synthetic families without strike metadata.
    """
    qs = [q for q in quotes]
    out: list[Violation] = []
    if require_coverage:
        ok, why = verify_bucket_coverage(qs)
        if not ok:
            return []

    buyable = [q for q in qs if q.yes_ask is not None and q.yes_ask_size > 0]
    if len(buyable) == len(qs) and len(qs) >= 2:
        cost = sum(q.yes_ask for q in buyable) * 100.0
        gross = 100.0 - cost
        fee = sum(_round_trip_fee_cents_per_contract(q.yes_ask, multiplier) for q in buyable)
        size = min(q.yes_ask_size for q in buyable)
        if gross > 0:
            out.append(
                Violation(
                    "bucket_sum_low",
                    family,
                    tuple(q.ticker for q in buyable),
                    gross,
                    fee,
                    gross - fee,
                    size,
                    f"sum(asks)={cost:.2f}c over {len(buyable)} buckets",
                    tuple({"ticker": q.ticker, "ask": q.yes_ask, "size": q.yes_ask_size}
                          for q in buyable),
                )
            )

    sellable = [q for q in qs if q.yes_bid is not None and q.yes_bid_size > 0]
    if len(sellable) == len(qs) and len(qs) >= 2:
        proceeds = sum(q.yes_bid for q in sellable) * 100.0
        gross = proceeds - 100.0
        fee = sum(_round_trip_fee_cents_per_contract(q.yes_bid, multiplier) for q in sellable)
        size = min(q.yes_bid_size for q in sellable)
        if gross > 0:
            out.append(
                Violation(
                    "bucket_sum_high",
                    family,
                    tuple(q.ticker for q in sellable),
                    gross,
                    fee,
                    gross - fee,
                    size,
                    f"sum(bids)={proceeds:.2f}c over {len(sellable)} buckets",
                    tuple({"ticker": q.ticker, "bid": q.yes_bid, "size": q.yes_bid_size}
                          for q in sellable),
                )
            )
    return out


def check_monotone_ladder(
    family: str, quotes: Iterable[Quote], multiplier: float = 1.0
) -> list[Violation]:
    """P(X > k) must be non-increasing in k.

    So for strikes k_lo < k_hi, the low-strike market must not be cheaper than the
    high-strike one. If ask(k_lo) < bid(k_hi) we buy the low and sell the high for a
    position that can never lose: the low strike pays whenever the high one does.
    """
    qs = sorted(
        (q for q in quotes if q.floor_strike is not None),
        key=lambda q: q.floor_strike,  # type: ignore[arg-type,return-value]
    )
    out: list[Violation] = []
    for i in range(len(qs) - 1):
        lo, hi = qs[i], qs[i + 1]
        if lo.floor_strike == hi.floor_strike:
            continue
        if lo.yes_ask is None or hi.yes_bid is None:
            continue
        if lo.yes_ask_size <= 0 or hi.yes_bid_size <= 0:
            continue
        gross = (hi.yes_bid - lo.yes_ask) * 100.0
        if gross <= 0:
            continue
        fee = _round_trip_fee_cents_per_contract(
            lo.yes_ask, multiplier
        ) + _round_trip_fee_cents_per_contract(hi.yes_bid, multiplier)
        out.append(
            Violation(
                "monotone_ladder",
                family,
                (lo.ticker, hi.ticker),
                gross,
                fee,
                gross - fee,
                min(lo.yes_ask_size, hi.yes_bid_size),
                f"ask(k={lo.floor_strike})={lo.yes_ask:.4f} < "
                f"bid(k={hi.floor_strike})={hi.yes_bid:.4f}",
                (
                    {"ticker": lo.ticker, "side": "buy", "price": lo.yes_ask},
                    {"ticker": hi.ticker, "side": "sell", "price": hi.yes_bid},
                ),
            )
        )
    return out


def check_combo_vs_legs(
    family: str,
    combo: Quote,
    legs: Iterable[Quote],
    correlation: float = 0.0,
    multiplier: float = 1.0,
) -> list[Violation]:
    """A parlay must not be worth more than its legs jointly can deliver.

    Under independence, P(all) = prod(P(leg)). Positive correlation raises the joint
    probability, so the independence product is a *lower* bound when legs are
    positively correlated. We therefore only flag the direction that survives either
    assumption: combo bid materially above the comonotone upper bound min(P(leg)),
    which no correlation structure can justify.
    """
    ls = [q for q in legs if q.mid is not None]
    if not ls or combo.yes_bid is None or combo.yes_bid_size <= 0:
        return []
    indep = 1.0
    for q in ls:
        indep *= q.mid  # type: ignore[operator]
    upper = min(q.mid for q in ls)  # type: ignore[type-var]
    gross = (combo.yes_bid - upper) * 100.0
    if gross <= 0:
        return []
    fee = _round_trip_fee_cents_per_contract(combo.yes_bid, multiplier)
    return [
        Violation(
            "combo_vs_legs",
            family,
            (combo.ticker,) + tuple(q.ticker for q in ls),
            gross,
            fee,
            gross - fee,
            combo.yes_bid_size,
            f"combo bid={combo.yes_bid:.4f} > comonotone upper bound "
            f"min(legs)={upper:.4f} (independence product={indep:.4f}, "
            f"assumed rho={correlation})",
        )
    ]
