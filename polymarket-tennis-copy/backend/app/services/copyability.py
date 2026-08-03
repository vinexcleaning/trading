"""Copyability scoring: could a realistic follower have taken this trade?

Design principle
----------------
Copyability is scored from **execution realism only** -- price persistence,
depth, spread, timing pressure, data quality. Whether the trade *won* is
deliberately excluded. Scoring copyability from profitability would collapse it
into "was this a good trade", and the whole point is to separate two independent
questions:

1. Did the wallet have an edge?          (wallet metrics / skill score)
2. Could a follower have captured it?    (this module)

A trade can be highly profitable and completely uncopyable -- the canonical case
from the spec: wallet buys at $0.68, the market is $0.76 seconds later, the
wallet exits shortly after, and depth is thin. That trade should score *low*
here even though it made money.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal

from ..enums import MarketPhase, PriceSourceQuality, RiskFlag
from ..logging_setup import get_logger
from .prices import FillEstimate, PriceSeries, ResolvedPrice, clamp_price

log = get_logger(__name__)

ZERO = Decimal("0")
ONE = Decimal("1")

# --- execution factor weights (sum to 1.0) ----------------------------------
# These describe the *trade*: could it have been executed. Price persistence
# dominates, because if the price is gone nothing else rescues the copy.
#
# Data quality is deliberately NOT in here. It describes our *measurement*, not
# the trade, so it is applied as a multiplier below. Adding it as a positive
# factor would let high measurement confidence inflate the score of a plainly
# uncopyable trade -- being certain a trade was bad must not make it look better.
WEIGHTS: dict[str, float] = {
    "price_persistence": 0.34,
    "liquidity": 0.22,
    "spread": 0.12,
    "timing_pressure": 0.12,
    "hold_duration": 0.14,
    "market_stability": 0.06,
}

# Data quality scales the execution score into this range. Perfect evidence
# leaves the score untouched; worthless evidence halves it before the separate
# hard caps below also apply.
DATA_QUALITY_FLOOR = 0.5

# A follower's assumed stake when judging whether depth was sufficient.
DEFAULT_FOLLOWER_STAKE = Decimal("100")
# Price deterioration at which the persistence factor reaches zero.
MAX_TOLERABLE_DETERIORATION = Decimal("0.08")
# Holding at least this long gives a follower room to act.
COMFORTABLE_HOLD_SECONDS = 900
# Below this, the wallet was gone before a follower could realistically react.
RAPID_EXIT_SECONDS = 60
# Spread beyond this makes crossing prohibitively expensive.
MAX_TOLERABLE_SPREAD = Decimal("0.06")
# Price range during the delay window that counts as "rapidly repricing".
UNSTABLE_RANGE = Decimal("0.05")


@dataclass(slots=True)
class CopyabilityInput:
    """Everything needed to judge one wallet entry at one follower delay."""

    wallet_entry_price: Decimal
    wallet_entry_ts: int
    delay_seconds: int

    price_after_delay: ResolvedPrice
    price_before: ResolvedPrice | None = None
    fill: FillEstimate | None = None

    available_liquidity: Decimal | None = None
    spread: Decimal | None = None
    market_phase: str = MarketPhase.UNKNOWN
    holding_seconds: int | None = None
    wallet_exited_within_delay: bool = False
    wallet_position_usdc: Decimal | None = None
    price_range_during_delay: Decimal | None = None
    follower_stake: Decimal = DEFAULT_FOLLOWER_STAKE
    classification_confidence: float = 100.0


@dataclass
class CopyabilityResult:
    """Score plus the per-factor breakdown that explains it."""

    score: float
    components: dict[str, float] = field(default_factory=dict)
    # Execution-only score, before the data-quality multiplier is applied.
    execution_score: float = 0.0
    quality_multiplier: float = 1.0
    estimated_fill_price: Decimal | None = None
    # Market price after the delay, before spread/slippage.
    market_price_after_delay: Decimal | None = None
    price_deterioration: Decimal | None = None
    price_deterioration_pct: float | None = None
    slippage: Decimal | None = None
    data_confidence: float = 0.0
    price_source_quality: PriceSourceQuality = PriceSourceQuality.UNAVAILABLE
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def components_json(self) -> str:
        """Full derivation of the score, for the UI tooltip."""
        return json.dumps(
            {
                "weights": WEIGHTS,
                "factors": {k: round(v, 2) for k, v in self.components.items()},
                "weighted": {
                    k: round(v * WEIGHTS.get(k, 0.0), 2)
                    for k, v in self.components.items()
                },
                "execution_score": self.execution_score,
                "data_confidence": self.data_confidence,
                "quality_multiplier": self.quality_multiplier,
                "final_score": self.score,
            },
            sort_keys=True,
        )

    def notes_text(self) -> str | None:
        return "; ".join(self.notes) if self.notes else None


def _score_price_persistence(
    wallet_price: Decimal, market_price_after_delay: Decimal | None
) -> float:
    """How much of the wallet's price survived in the *market*.

    Measured against the market price after the delay, not the follower's fill.
    Market drift and execution cost are separate problems -- drift is scored here,
    spread and slippage are scored by their own factors -- so that a stable market
    is not penalised twice for the same cent.

    Directional: a follower able to buy *cheaper* than the wallet is not
    penalised, since that only improves the copy.
    """
    if market_price_after_delay is None:
        return 0.0
    drift = market_price_after_delay - wallet_price
    if drift <= ZERO:
        return 100.0
    return max(0.0, 100.0 * (1.0 - float(drift / MAX_TOLERABLE_DETERIORATION)))


def _score_liquidity(
    available: Decimal | None, stake: Decimal, fill: FillEstimate | None
) -> tuple[float, list[str]]:
    """Whether the follower's stake was actually fillable.

    A partial fill from a real book walk is the strongest evidence of a depth
    problem and overrides the quoted-liquidity view.
    """
    flags: list[str] = []

    if fill is not None and fill.partially_filled:
        flags.append(RiskFlag.LOW_LIQUIDITY_MARKETS)
        return max(0.0, 60.0 * fill.fill_ratio), flags

    if available is None:
        # Unknown depth is not treated as good depth.
        return 40.0, flags

    if available <= ZERO:
        flags.append(RiskFlag.LOW_LIQUIDITY_MARKETS)
        return 0.0, flags

    # Full marks at 20x the stake: enough that the follower is not the market.
    coverage = float(available / stake) if stake > ZERO else 0.0
    if coverage >= 20:
        return 100.0, flags
    if coverage < 1:
        flags.append(RiskFlag.LOW_LIQUIDITY_MARKETS)
    return max(0.0, min(100.0, (coverage / 20.0) * 100.0)), flags


def _score_spread(spread: Decimal | None) -> tuple[float, list[str]]:
    flags: list[str] = []
    if spread is None:
        return 50.0, flags
    if spread <= ZERO:
        return 100.0, flags
    if spread >= MAX_TOLERABLE_SPREAD:
        flags.append(RiskFlag.WIDE_SPREAD)
        return 0.0, flags
    return float(100 * (1 - spread / MAX_TOLERABLE_SPREAD)), flags


def _score_timing_pressure(delay_seconds: int, phase: str) -> float:
    """Penalise long delays, and penalise them harder in live markets.

    A live tennis market reprices on every point, so 60 seconds of delay is a far
    bigger handicap in-play than it is pre-match.
    """
    if phase == MarketPhase.LIVE:
        # Effectively unusable beyond ~2 minutes in-play.
        horizon = 120.0
    elif phase == MarketPhase.PREMATCH:
        horizon = 1800.0
    else:
        horizon = 600.0
    return max(0.0, 100.0 * (1.0 - min(1.0, delay_seconds / horizon)))


def _score_hold_duration(
    holding_seconds: int | None, exited_within_delay: bool, delay_seconds: int
) -> tuple[float, list[str]]:
    """A wallet that vanishes immediately leaves nothing to copy.

    The "already gone" condition is derived here rather than trusted from the
    caller, so a directly-constructed input cannot understate it.
    """
    flags: list[str] = []
    already_gone = exited_within_delay or (
        holding_seconds is not None and holding_seconds <= delay_seconds
    )
    if already_gone:
        flags.append(RiskFlag.RAPID_EXIT_PATTERN)
        return 0.0, flags
    if holding_seconds is None:
        # Still open: the follower has time, which is favourable.
        return 85.0, flags
    if holding_seconds <= RAPID_EXIT_SECONDS:
        flags.append(RiskFlag.RAPID_EXIT_PATTERN)
        return max(0.0, 25.0 * (holding_seconds / RAPID_EXIT_SECONDS)), flags
    if holding_seconds >= COMFORTABLE_HOLD_SECONDS:
        return 100.0, flags
    span = COMFORTABLE_HOLD_SECONDS - RAPID_EXIT_SECONDS
    return 25.0 + 75.0 * ((holding_seconds - RAPID_EXIT_SECONDS) / span), flags


def _score_market_stability(
    price_range: Decimal | None, phase: str
) -> tuple[float, list[str]]:
    flags: list[str] = []
    if price_range is None:
        return 60.0 if phase == MarketPhase.LIVE else 80.0, flags
    if price_range >= UNSTABLE_RANGE:
        flags.append(RiskFlag.FAST_MOVING_MARKET)
        return 0.0, flags
    return float(100 * (1 - price_range / UNSTABLE_RANGE)), flags


def score_copyability(data: CopyabilityInput) -> CopyabilityResult:
    """Score one wallet entry at one follower delay."""
    market_price = data.price_after_delay.price
    # The follower's realistic cost: their fill if we could model one, else the
    # bare market price.
    follower_price = data.fill.fill_price if data.fill is not None else market_price

    # Headline deterioration is measured to the *fill*, because that is what the
    # follower actually pays, even though the persistence factor scores drift only.
    deterioration: Decimal | None = None
    deterioration_pct: float | None = None
    if follower_price is not None:
        deterioration = follower_price - data.wallet_entry_price
        if data.wallet_entry_price > ZERO:
            deterioration_pct = float(deterioration / data.wallet_entry_price)

    persistence = _score_price_persistence(data.wallet_entry_price, market_price)
    liquidity, liq_flags = _score_liquidity(
        data.available_liquidity, data.follower_stake, data.fill
    )
    spread_score, spread_flags = _score_spread(data.spread)
    timing = _score_timing_pressure(data.delay_seconds, data.market_phase)
    hold, hold_flags = _score_hold_duration(
        data.holding_seconds, data.wallet_exited_within_delay, data.delay_seconds
    )
    stability, stability_flags = _score_market_stability(
        data.price_range_during_delay, data.market_phase
    )

    components = {
        "price_persistence": persistence,
        "liquidity": liquidity,
        "spread": spread_score,
        "timing_pressure": timing,
        "hold_duration": hold,
        "market_stability": stability,
    }

    # Execution score: purely "could this have been executed".
    execution_score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)

    # Data quality blends price-evidence confidence with classification
    # confidence: a perfectly-priced trade in a market we cannot classify is
    # still not something to act on.
    data_quality = (data.price_after_delay.confidence * 0.7) + (
        data.classification_confidence * 0.3
    )
    # Applied as a multiplier, never as a bonus, so weak evidence can only ever
    # reduce the score.
    quality_multiplier = DATA_QUALITY_FLOOR + (1.0 - DATA_QUALITY_FLOOR) * (
        data_quality / 100.0
    )
    score = execution_score * quality_multiplier

    flags = list(dict.fromkeys(liq_flags + spread_flags + hold_flags + stability_flags))
    notes: list[str] = []

    if not data.price_after_delay.is_usable:
        # Without a price there is no copyability claim to make at all.
        score = 0.0
        flags.append(RiskFlag.THIN_DATA)
        notes.append("no usable price at the follower's decision time")
    elif data.price_after_delay.quality in (
        PriceSourceQuality.MODELED,
        PriceSourceQuality.NEAREST_TRADE,
    ):
        # Hard cap so modelled evidence can never clear a strict alert gate,
        # regardless of how favourable the execution factors look.
        capped = min(score, 55.0)
        if capped < score:
            notes.append(
                f"score capped at 55 because price evidence is "
                f"{data.price_after_delay.quality.value}"
            )
        score = capped
        flags.append(RiskFlag.THIN_DATA)

    if data.price_after_delay.note:
        notes.append(data.price_after_delay.note)
    if data.fill is not None and data.fill.note:
        notes.append(data.fill.note)
    if data.delay_seconds == 0:
        notes.append(
            "0s delay is a theoretical reference only; no follower can achieve it"
        )

    return CopyabilityResult(
        score=round(max(0.0, min(100.0, score)), 1),
        components=components,
        execution_score=round(execution_score, 1),
        quality_multiplier=round(quality_multiplier, 3),
        estimated_fill_price=follower_price,
        market_price_after_delay=market_price,
        price_deterioration=deterioration,
        price_deterioration_pct=deterioration_pct,
        slippage=data.fill.slippage if data.fill is not None else None,
        data_confidence=round(data_quality, 1),
        price_source_quality=data.price_after_delay.quality,
        flags=flags,
        notes=notes,
    )


@dataclass(slots=True)
class FollowerOutcome:
    """What a delayed follower would have actually made on a trade."""

    entry_price: Decimal
    exit_price: Decimal | None
    pnl: Decimal | None
    roi: float | None
    is_win: bool | None
    note: str | None = None


def compute_follower_outcome(
    fill_price: Decimal,
    *,
    wallet_exit_price: Decimal | None,
    resolved_winner: bool | None,
    stake_usdc: Decimal,
    fee_bps: int = 0,
) -> FollowerOutcome:
    """P&L for a follower who entered at ``fill_price``.

    Exit priority: the market's resolution if known (unambiguous), otherwise the
    wallet's own exit price. If neither exists the outcome is undetermined and
    returns ``None`` rather than a zero that would dilute averages.
    """
    if fill_price <= ZERO:
        return FollowerOutcome(fill_price, None, None, None, None, "invalid fill price")

    shares = stake_usdc / fill_price

    if resolved_winner is not None:
        exit_price = ONE if resolved_winner else ZERO
        note = "held to resolution"
    elif wallet_exit_price is not None:
        exit_price = clamp_price(wallet_exit_price)
        note = "exited with the wallet"
    else:
        return FollowerOutcome(
            fill_price, None, None, None, None, "no exit reference available"
        )

    gross = shares * (exit_price - fill_price)
    fees = (stake_usdc * Decimal(fee_bps) / Decimal("10000")) if fee_bps else ZERO
    pnl = gross - fees
    roi = float(pnl / stake_usdc) if stake_usdc > ZERO else None

    return FollowerOutcome(
        entry_price=fill_price,
        exit_price=exit_price,
        pnl=pnl,
        roi=roi,
        is_win=pnl > ZERO,
        note=note,
    )


def build_copyability_input(
    *,
    wallet_entry_price: Decimal,
    wallet_entry_ts: int,
    delay_seconds: int,
    series: PriceSeries,
    holding_seconds: int | None,
    market_phase: str,
    spread: Decimal | None = None,
    available_liquidity: Decimal | None = None,
    follower_stake: Decimal = DEFAULT_FOLLOWER_STAKE,
    classification_confidence: float = 100.0,
    book=None,
    slippage_bps: int = 150,
) -> CopyabilityInput:
    """Assemble a :class:`CopyabilityInput` from a price series.

    Kept as a helper so the metrics pipeline and the backtester construct their
    inputs identically -- a divergence there would make backtest results
    incomparable to live scoring.
    """
    from .prices import estimate_follower_fill

    target_ts = wallet_entry_ts + delay_seconds
    resolved = series.resolve(target_ts, fallback_price=wallet_entry_price)
    before = series.price_before(wallet_entry_ts)

    fill = None
    if resolved.price is not None:
        fill = estimate_follower_fill(
            resolved.price,
            follower_stake,
            book=book,
            spread=spread,
            slippage_bps=slippage_bps,
            price_quality=resolved.quality,
        )

    exited_within_delay = (
        holding_seconds is not None and holding_seconds <= delay_seconds
    )

    return CopyabilityInput(
        wallet_entry_price=wallet_entry_price,
        wallet_entry_ts=wallet_entry_ts,
        delay_seconds=delay_seconds,
        price_after_delay=resolved,
        price_before=before,
        fill=fill,
        available_liquidity=available_liquidity,
        spread=spread,
        market_phase=market_phase,
        holding_seconds=holding_seconds,
        wallet_exited_within_delay=exited_within_delay,
        price_range_during_delay=series.volatility_after(
            wallet_entry_ts, max(delay_seconds, 30)
        ),
        follower_stake=follower_stake,
        classification_confidence=classification_confidence,
    )
