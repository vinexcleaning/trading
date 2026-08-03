"""Historical price reconstruction and follower fill simulation.

The central problem
-------------------
To know whether a follower could have copied a trade we must answer: *what price
was actually available N seconds after the wallet traded?* Polymarket's public
history cannot answer that directly. Verified against the live API:

* ``GET /prices-history`` bottoms out at ``fidelity=1`` -- one minute. Observed
  gaps between consecutive points were 60s+. There is no sub-minute series.
* ``GET /trades`` returns executed prints with **second-level** timestamps
  (489 distinct seconds across 3235s in a busy market), but only where trades
  actually happened. An illiquid market returns nothing at all.

So for the short delays that matter most (2s-30s) the only genuine evidence is
the trade tape, and that evidence is *sparse*. Rather than interpolate silently
and present a confident-looking number, every resolved price carries the tier of
evidence behind it, and confidence flows through to copyability, wallet scores
and alert gating.

Tiers, strongest first:

=====================  ==========================================================
OBSERVED_TRADE         A real print within ``tolerance`` of the target second.
INTERPOLATED_TRADE     Bracketed by two real prints close enough to interpolate.
MINUTE_BAR             A ``prices-history`` point -- correct to the minute only.
NEAREST_TRADE          The closest print, further away than ``tolerance``.
MODELED                No usable observation; a documented assumption is used.
UNAVAILABLE            Nothing at all; the trade is excluded from copyable stats.
=====================  ==========================================================
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from ..enums import PriceSourceQuality
from ..logging_setup import get_logger
from ..providers.base import ProviderOrderBook, ProviderPricePoint, ProviderTrade

log = get_logger(__name__)

ZERO = Decimal("0")
ONE = Decimal("1")

# A print this close to the target second is treated as the price itself.
DEFAULT_TOLERANCE_SECONDS = 3
# Beyond this, two prints are too far apart to interpolate between honestly.
MAX_INTERPOLATION_GAP_SECONDS = 600
# Beyond this, even a nearest-print fallback is meaningless.
MAX_NEAREST_DISTANCE_SECONDS = 1800
# A minute bar is only usable within half a bar of the target.
MAX_MINUTE_BAR_DISTANCE_SECONDS = 90

# Polymarket prices are probabilities and must stay strictly inside (0, 1).
MIN_PRICE = Decimal("0.001")
MAX_PRICE = Decimal("0.999")


def clamp_price(price: Decimal) -> Decimal:
    """Keep a price inside the tradeable band."""
    return max(MIN_PRICE, min(MAX_PRICE, price))


@dataclass(slots=True)
class ResolvedPrice:
    """A price with the evidence behind it."""

    price: Decimal | None
    quality: PriceSourceQuality
    # Seconds between the requested time and the evidence used.
    distance_seconds: int | None = None
    note: str | None = None

    @property
    def confidence(self) -> float:
        """0-100, degraded by how far the evidence sits from the target."""
        base = self.quality.confidence
        if self.price is None:
            return 0.0
        if self.distance_seconds is None or self.distance_seconds <= 0:
            return base
        # Linear decay: a full minute of distance costs a fifth of the tier's
        # confidence, so stale evidence cannot masquerade as fresh.
        decay = min(0.4, (self.distance_seconds / 60.0) * 0.2)
        return round(base * (1.0 - decay), 1)

    @property
    def is_usable(self) -> bool:
        return self.price is not None and self.quality is not PriceSourceQuality.UNAVAILABLE


@dataclass
class PriceSeries:
    """Time-indexed price evidence for one outcome token.

    Trade prints and minute bars are kept separate on purpose: merging them would
    destroy the distinction between second-level observation and minute-level
    approximation, which is the whole basis of the confidence model.
    """

    token_id: str
    # Sorted (timestamp, price) of executed prints.
    trade_ts: list[int] = field(default_factory=list)
    trade_px: list[Decimal] = field(default_factory=list)
    trade_size: list[Decimal] = field(default_factory=list)
    # Sorted (timestamp, price) of minute bars.
    bar_ts: list[int] = field(default_factory=list)
    bar_px: list[Decimal] = field(default_factory=list)

    # -------------------------------------------------------------- builders
    @classmethod
    def from_sources(
        cls,
        token_id: str,
        trades: Sequence[ProviderTrade] | None = None,
        bars: Sequence[ProviderPricePoint] | None = None,
    ) -> PriceSeries:
        series = cls(token_id=token_id)
        if trades:
            rows = sorted(
                ((t.timestamp, t.price, t.size) for t in trades if t.token_id == token_id),
                key=lambda r: r[0],
            )
            for ts, px, size in rows:
                series.trade_ts.append(ts)
                series.trade_px.append(px)
                series.trade_size.append(size)
        if bars:
            rows2 = sorted(
                ((b.timestamp, b.price) for b in bars if b.token_id == token_id),
                key=lambda r: r[0],
            )
            for ts, px in rows2:
                series.bar_ts.append(ts)
                series.bar_px.append(px)
        return series

    def add_trade(self, timestamp: int, price: Decimal, size: Decimal = ZERO) -> None:
        idx = bisect.bisect_left(self.trade_ts, timestamp)
        self.trade_ts.insert(idx, timestamp)
        self.trade_px.insert(idx, price)
        self.trade_size.insert(idx, size)

    def add_bar(self, timestamp: int, price: Decimal) -> None:
        idx = bisect.bisect_left(self.bar_ts, timestamp)
        self.bar_ts.insert(idx, timestamp)
        self.bar_px.insert(idx, price)

    @property
    def has_evidence(self) -> bool:
        return bool(self.trade_ts or self.bar_ts)

    # ------------------------------------------------------------- resolution
    def resolve(
        self,
        target_ts: int,
        *,
        tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
        fallback_price: Decimal | None = None,
    ) -> ResolvedPrice:
        """Best available price at ``target_ts`` with its evidence tier.

        ``fallback_price`` (typically the wallet's own execution price) is used
        only for the MODELED tier, and is labelled as such -- never presented as
        an observation.
        """
        if not self.has_evidence:
            if fallback_price is not None:
                return ResolvedPrice(
                    price=clamp_price(fallback_price),
                    quality=PriceSourceQuality.MODELED,
                    note="no price observations for this token; used fallback",
                )
            return ResolvedPrice(
                price=None,
                quality=PriceSourceQuality.UNAVAILABLE,
                note="no price observations available",
            )

        # --- tier 1: an actual print at (or beside) the target second --------
        if self.trade_ts:
            idx = bisect.bisect_left(self.trade_ts, target_ts)
            best_i: int | None = None
            best_dist = None
            for cand in (idx - 1, idx, idx + 1):
                if 0 <= cand < len(self.trade_ts):
                    dist = abs(self.trade_ts[cand] - target_ts)
                    if best_dist is None or dist < best_dist:
                        best_dist, best_i = dist, cand
            if best_i is not None and best_dist is not None and best_dist <= tolerance_seconds:
                return ResolvedPrice(
                    price=clamp_price(self.trade_px[best_i]),
                    quality=PriceSourceQuality.OBSERVED_TRADE,
                    distance_seconds=best_dist,
                    note=f"executed print {best_dist}s from target",
                )

            # --- tier 2: interpolate between two bracketing prints ----------
            lo = idx - 1
            hi = idx
            if 0 <= lo < len(self.trade_ts) and 0 <= hi < len(self.trade_ts):
                gap = self.trade_ts[hi] - self.trade_ts[lo]
                if 0 < gap <= MAX_INTERPOLATION_GAP_SECONDS:
                    weight = Decimal(target_ts - self.trade_ts[lo]) / Decimal(gap)
                    interpolated = self.trade_px[lo] + (
                        self.trade_px[hi] - self.trade_px[lo]
                    ) * weight
                    return ResolvedPrice(
                        price=clamp_price(interpolated),
                        quality=PriceSourceQuality.INTERPOLATED_TRADE,
                        distance_seconds=min(
                            target_ts - self.trade_ts[lo], self.trade_ts[hi] - target_ts
                        ),
                        note=f"interpolated across a {gap}s gap between prints",
                    )

        # --- tier 3: minute bar ---------------------------------------------
        if self.bar_ts:
            bar = self._nearest(self.bar_ts, self.bar_px, target_ts)
            if bar is not None:
                price, dist = bar
                if dist <= MAX_MINUTE_BAR_DISTANCE_SECONDS:
                    return ResolvedPrice(
                        price=clamp_price(price),
                        quality=PriceSourceQuality.MINUTE_BAR,
                        distance_seconds=dist,
                        note=(
                            f"minute-resolution bar {dist}s from target; "
                            "sub-minute movement is not observable"
                        ),
                    )

        # --- tier 4: nearest print, however far ------------------------------
        if self.trade_ts:
            nearest = self._nearest(self.trade_ts, self.trade_px, target_ts)
            if nearest is not None:
                price, dist = nearest
                if dist <= MAX_NEAREST_DISTANCE_SECONDS:
                    return ResolvedPrice(
                        price=clamp_price(price),
                        quality=PriceSourceQuality.NEAREST_TRADE,
                        distance_seconds=dist,
                        note=f"nearest print is {dist}s away; weak evidence",
                    )

        # --- tier 5: modeled / unavailable -----------------------------------
        if fallback_price is not None:
            return ResolvedPrice(
                price=clamp_price(fallback_price),
                quality=PriceSourceQuality.MODELED,
                note="no observation near target; used fallback price",
            )
        return ResolvedPrice(
            price=None,
            quality=PriceSourceQuality.UNAVAILABLE,
            note="no observation within acceptable distance",
        )

    @staticmethod
    def _nearest(
        timestamps: list[int], prices: list[Decimal], target_ts: int
    ) -> tuple[Decimal, int] | None:
        if not timestamps:
            return None
        idx = bisect.bisect_left(timestamps, target_ts)
        best: tuple[Decimal, int] | None = None
        for cand in (idx - 1, idx):
            if 0 <= cand < len(timestamps):
                dist = abs(timestamps[cand] - target_ts)
                if best is None or dist < best[1]:
                    best = (prices[cand], dist)
        return best

    # ----------------------------------------------------------- diagnostics
    def price_before(self, target_ts: int, lookback: int = 300) -> ResolvedPrice:
        """Last observation strictly before ``target_ts``.

        Used to measure how far the market moved *because of or after* the
        wallet's own trade, as distinct from where it already was.
        """
        if self.trade_ts:
            idx = bisect.bisect_left(self.trade_ts, target_ts) - 1
            if idx >= 0:
                dist = target_ts - self.trade_ts[idx]
                if dist <= lookback:
                    return ResolvedPrice(
                        price=clamp_price(self.trade_px[idx]),
                        quality=PriceSourceQuality.OBSERVED_TRADE,
                        distance_seconds=dist,
                        note="last print before wallet trade",
                    )
        if self.bar_ts:
            idx = bisect.bisect_left(self.bar_ts, target_ts) - 1
            if idx >= 0:
                dist = target_ts - self.bar_ts[idx]
                if dist <= max(lookback, MAX_MINUTE_BAR_DISTANCE_SECONDS):
                    return ResolvedPrice(
                        price=clamp_price(self.bar_px[idx]),
                        quality=PriceSourceQuality.MINUTE_BAR,
                        distance_seconds=dist,
                        note="last minute bar before wallet trade",
                    )
        return ResolvedPrice(
            price=None, quality=PriceSourceQuality.UNAVAILABLE, note="no prior observation"
        )

    def volatility_after(self, from_ts: int, window_seconds: int = 60) -> Decimal | None:
        """Price range over a window -- a proxy for "is this market repricing fast?".

        A wide range during the follower's delay window means the copy price is
        materially uncertain regardless of which tier resolved it.
        """
        if not self.trade_ts:
            return None
        lo = bisect.bisect_left(self.trade_ts, from_ts)
        hi = bisect.bisect_right(self.trade_ts, from_ts + window_seconds)
        window = self.trade_px[lo:hi]
        if len(window) < 2:
            return None
        return max(window) - min(window)

    def traded_notional(self, from_ts: int, to_ts: int) -> Decimal:
        """Executed notional in a window -- observed (not quoted) liquidity."""
        if not self.trade_ts:
            return ZERO
        lo = bisect.bisect_left(self.trade_ts, from_ts)
        hi = bisect.bisect_right(self.trade_ts, to_ts)
        return sum(
            (self.trade_px[i] * self.trade_size[i] for i in range(lo, hi)), ZERO
        )


@dataclass(slots=True)
class FillEstimate:
    """Simulated outcome of a follower's buy order."""

    fill_price: Decimal
    filled_notional: Decimal
    requested_notional: Decimal
    slippage: Decimal
    quality: PriceSourceQuality
    partially_filled: bool = False
    note: str | None = None

    @property
    def fill_ratio(self) -> float:
        if self.requested_notional <= ZERO:
            return 0.0
        return float(self.filled_notional / self.requested_notional)


def estimate_fill_from_book(
    book: ProviderOrderBook, notional_usdc: Decimal
) -> FillEstimate | None:
    """Walk the ask ladder to fill ``notional_usdc``.

    This is why quoted "liquidity" is not the right input: on a live market we
    measured $2,178 of total ask depth but only **$14.55** within a cent of touch.
    A follower placing a market order eats the ladder, so the achievable average
    price is what matters, not the headline number.
    """
    if not book.asks or notional_usdc <= ZERO:
        return None

    ladder = sorted(book.asks, key=lambda lvl: lvl.price)
    remaining = notional_usdc
    spent = ZERO
    shares = ZERO

    for level in ladder:
        level_notional = level.price * level.size
        if level_notional <= ZERO:
            continue
        take_notional = min(remaining, level_notional)
        take_shares = take_notional / level.price
        spent += take_notional
        shares += take_shares
        remaining -= take_notional
        if remaining <= ZERO:
            break

    if shares <= ZERO:
        return None

    avg_price = spent / shares
    best_ask = ladder[0].price
    return FillEstimate(
        fill_price=clamp_price(avg_price),
        filled_notional=spent,
        requested_notional=notional_usdc,
        slippage=avg_price - best_ask,
        quality=PriceSourceQuality.OBSERVED_TRADE,
        partially_filled=remaining > ZERO,
        note=(
            f"walked {len(ladder)} ask levels"
            + (f"; only ${spent:.2f} of ${notional_usdc:.2f} fillable" if remaining > ZERO else "")
        ),
    )


def estimate_fill_modeled(
    reference_price: Decimal,
    notional_usdc: Decimal,
    *,
    spread: Decimal | None = None,
    slippage_bps: int = 150,
    quality: PriceSourceQuality = PriceSourceQuality.MODELED,
) -> FillEstimate:
    """Fill estimate without book depth.

    A follower crossing the spread pays roughly the mid plus half the spread,
    plus impact. With no ladder we cannot know impact, so a configured slippage
    assumption stands in and the estimate is labelled as modelled.
    """
    half_spread = (spread / Decimal("2")) if spread and spread > ZERO else ZERO
    impact = reference_price * (Decimal(slippage_bps) / Decimal("10000"))
    fill = clamp_price(reference_price + half_spread + impact)
    return FillEstimate(
        fill_price=fill,
        filled_notional=notional_usdc,
        requested_notional=notional_usdc,
        slippage=fill - reference_price,
        quality=quality,
        note=(
            f"modelled: +half-spread {half_spread} +{slippage_bps}bps impact "
            "(no order-book depth available)"
        ),
    )


def estimate_follower_fill(
    reference_price: Decimal,
    notional_usdc: Decimal,
    *,
    book: ProviderOrderBook | None = None,
    spread: Decimal | None = None,
    slippage_bps: int = 150,
    price_quality: PriceSourceQuality = PriceSourceQuality.MODELED,
) -> FillEstimate:
    """Best available fill estimate, preferring real depth over assumptions."""
    if book is not None:
        from_book = estimate_fill_from_book(book, notional_usdc)
        if from_book is not None:
            # The fill is only as trustworthy as the price that located it.
            from_book.quality = (
                price_quality
                if price_quality.confidence < from_book.quality.confidence
                else from_book.quality
            )
            return from_book
    return estimate_fill_modeled(
        reference_price,
        notional_usdc,
        spread=spread,
        slippage_bps=slippage_bps,
        quality=price_quality,
    )
