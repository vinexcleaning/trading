"""Trade reconstruction: raw activity -> round-trip positions with P&L.

Accounting model
----------------
Exposure in one outcome token is tracked as an ordered list of *lots*. A
position opens when exposure leaves zero and closes when it returns to zero, so
a scaled-in entry produces one position with several lots -- not several
positions. That is the property that prevents a wallet which accumulates in five
clips from looking like five independent winning trades.

Two accounting methods are supported and produce different realized P&L on
partial exits:

* ``fifo`` (default) -- oldest lots are consumed first. Matches how most
  jurisdictions and most traders reason about disposals.
* ``weighted_average`` -- every exit realizes against the blended cost of all
  open lots.

Both leave *total* P&L over a completed round trip identical; they differ only in
how it is attributed across partial exits. The method is recorded on every
position so a stored result is always interpretable.

Settlement
----------
Polymarket positions frequently end in ``REDEEM`` rather than a SELL. A winning
share redeems at $1.00 and a losing share at $0.00, so settlement is priced from
the market's resolved outcome rather than from a trade price. When a market is
resolved but no REDEEM has been observed yet, the position is still settled
analytically -- otherwise winning trades would sit "open" forever and be excluded
from performance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from ..enums import (
    ActivityType,
    MarketPhase,
    PositionBehaviour,
    PositionStatus,
    RiskFlag,
    TennisMarketType,
    TradeSide,
)
from ..logging_setup import get_logger

log = get_logger(__name__)

AccountingMethod = Literal["fifo", "weighted_average"]

ZERO = Decimal("0")
ONE = Decimal("1")
# Share quantities below this are treated as flat: venue rounding leaves dust
# that would otherwise keep positions open forever.
DUST = Decimal("0.000001")

# --- behavioural thresholds (heuristics, surfaced as flags not verdicts) ----
# A round trip shorter than this looks like a scalp rather than a view on the match.
SCALP_SECONDS = 120
# Buying and selling repeatedly on both sides of a market this often suggests
# market-making rather than a directional opinion.
MARKET_MAKING_MIN_FLIPS = 4
# Holding both outcomes simultaneously beyond this fraction of the position is a
# hedge (or an arbitrage), not a directional bet.
HEDGE_OVERLAP_FRACTION = Decimal("0.25")


@dataclass(slots=True)
class TxInput:
    """A normalized transaction, decoupled from the ORM for testability."""

    id: int | None
    timestamp: int
    activity_type: str
    size: Decimal
    side: str | None = None
    price: Decimal | None = None
    usdc_size: Decimal | None = None
    fee_usdc: Decimal | None = None
    token_id: str = ""
    condition_id: str | None = None
    outcome_index: int | None = None
    market_phase: str = MarketPhase.UNKNOWN
    transaction_hash: str | None = None

    @property
    def occurred_at(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    @property
    def is_trade(self) -> bool:
        return self.activity_type == ActivityType.TRADE

    @property
    def signed_size(self) -> Decimal:
        """Positive acquires exposure, negative disposes of it."""
        if self.activity_type == ActivityType.TRADE:
            return self.size if self.side == TradeSide.BUY else -self.size
        if self.activity_type in (ActivityType.REDEEM, ActivityType.MERGE):
            return -self.size
        if self.activity_type == ActivityType.SPLIT:
            return self.size
        # Rebates and rewards move cash, never exposure.
        return ZERO

    def effective_price(self) -> Decimal | None:
        """Price per share, derived from notional when not stated directly."""
        if self.price is not None:
            return self.price
        if self.usdc_size is not None and self.size > ZERO:
            return self.usdc_size / self.size
        return None


@dataclass
class Lot:
    """An open acquisition tranche."""

    lot_index: int
    acquired_ts: int
    shares: Decimal
    entry_price: Decimal
    transaction_id: int | None = None
    shares_remaining: Decimal = ZERO
    realized_pnl: Decimal = ZERO

    def __post_init__(self) -> None:
        if self.shares_remaining == ZERO:
            self.shares_remaining = self.shares

    @property
    def cost_basis(self) -> Decimal:
        return self.shares * self.entry_price

    @property
    def fully_consumed(self) -> bool:
        return self.shares_remaining <= DUST


@dataclass
class ReconstructedPositionData:
    """In-memory result of reconstructing one round trip."""

    token_id: str
    sequence: int
    condition_id: str | None
    outcome_index: int | None
    accounting_method: AccountingMethod

    opened_ts: int
    first_entry_price: Decimal
    entry_phase: str

    lots: list[Lot] = field(default_factory=list)
    transaction_ids: list[int] = field(default_factory=list)

    total_shares_bought: Decimal = ZERO
    total_shares_sold: Decimal = ZERO
    current_shares: Decimal = ZERO
    max_shares: Decimal = ZERO
    capital_committed: Decimal = ZERO
    max_capital_at_risk: Decimal = ZERO

    entry_tx_count: int = 0
    exit_tx_count: int = 0
    partial_exit_count: int = 0

    realized_pnl: Decimal = ZERO
    fees_paid: Decimal = ZERO
    proceeds: Decimal = ZERO

    closed_ts: int | None = None
    avg_exit_price: Decimal | None = None
    status: str = PositionStatus.OPEN
    settled_by_redemption: bool = False

    scaled_in_at_worse_prices: bool = False
    held_both_outcomes: bool = False
    behaviour: str = PositionBehaviour.DIRECTIONAL
    flags: list[str] = field(default_factory=list)
    reconstruction_confidence: float = 100.0
    notes: list[str] = field(default_factory=list)

    # Running sums used to derive weighted averages.
    _entry_notional: Decimal = ZERO
    _exit_notional: Decimal = ZERO

    # ------------------------------------------------------------- accessors
    @property
    def avg_entry_price(self) -> Decimal:
        if self.total_shares_bought <= ZERO:
            return self.first_entry_price
        return self._entry_notional / self.total_shares_bought

    @property
    def accumulated(self) -> bool:
        return self.entry_tx_count > 1

    @property
    def holding_seconds(self) -> int | None:
        if self.closed_ts is None:
            return None
        return max(0, self.closed_ts - self.opened_ts)

    @property
    def net_pnl(self) -> Decimal:
        return self.realized_pnl - self.fees_paid

    @property
    def roi(self) -> float | None:
        """Return on capital actually committed."""
        if self.capital_committed <= ZERO:
            return None
        return float(self.net_pnl / self.capital_committed)

    @property
    def is_win(self) -> bool | None:
        if self.status not in (PositionStatus.CLOSED, PositionStatus.SETTLED):
            return None
        return self.net_pnl > ZERO

    def flags_json(self) -> str | None:
        return json.dumps(sorted(set(self.flags))) if self.flags else None

    def notes_text(self) -> str | None:
        return "; ".join(self.notes) if self.notes else None

    # --------------------------------------------------------------- mutation
    def add_lot(self, tx: TxInput, price: Decimal) -> None:
        lot = Lot(
            lot_index=len(self.lots),
            acquired_ts=tx.timestamp,
            shares=tx.size,
            entry_price=price,
            transaction_id=tx.id,
        )
        self.lots.append(lot)
        self.total_shares_bought += tx.size
        self.current_shares += tx.size
        self._entry_notional += tx.size * price
        self.entry_tx_count += 1
        self.capital_committed += tx.size * price
        self.max_shares = max(self.max_shares, self.current_shares)
        self.max_capital_at_risk = max(
            self.max_capital_at_risk, self.current_shares * self.avg_entry_price
        )
        if price > self.first_entry_price:
            # Adding at a worse price than the first entry: relevant because a
            # follower who copied the first entry gets a different average.
            self.scaled_in_at_worse_prices = True
        if tx.fee_usdc:
            self.fees_paid += tx.fee_usdc
        if tx.id is not None:
            self.transaction_ids.append(tx.id)

    def reduce(
        self, tx: TxInput, price: Decimal, *, is_settlement: bool = False
    ) -> Decimal:
        """Consume lots against a disposal. Returns realized P&L for this exit."""
        shares_to_close = min(tx.size, self.current_shares)
        if shares_to_close <= ZERO:
            return ZERO

        realized = ZERO
        if self.accounting_method == "weighted_average":
            basis = self.avg_open_cost()
            realized = (price - basis) * shares_to_close
            self._consume_proportionally(shares_to_close, realized)
        else:
            remaining = shares_to_close
            for lot in self.lots:
                if remaining <= DUST:
                    break
                if lot.fully_consumed:
                    continue
                take = min(lot.shares_remaining, remaining)
                lot_pnl = (price - lot.entry_price) * take
                lot.realized_pnl += lot_pnl
                lot.shares_remaining -= take
                realized += lot_pnl
                remaining -= take

        self.current_shares -= shares_to_close
        self.total_shares_sold += shares_to_close
        self.realized_pnl += realized
        self.proceeds += shares_to_close * price
        self._exit_notional += shares_to_close * price
        self.exit_tx_count += 1
        if tx.fee_usdc:
            self.fees_paid += tx.fee_usdc
        if tx.id is not None:
            self.transaction_ids.append(tx.id)

        if self.current_shares > DUST:
            self.partial_exit_count += 1
            self.status = PositionStatus.PARTIALLY_CLOSED
        else:
            self.current_shares = ZERO
            self.closed_ts = tx.timestamp
            self.status = PositionStatus.SETTLED if is_settlement else PositionStatus.CLOSED
            self.settled_by_redemption = self.settled_by_redemption or is_settlement
            if self.total_shares_sold > ZERO:
                self.avg_exit_price = self._exit_notional / self.total_shares_sold
        return realized

    def avg_open_cost(self) -> Decimal:
        """Weighted-average cost of currently open lots."""
        open_shares = sum((lot.shares_remaining for lot in self.lots), ZERO)
        if open_shares <= ZERO:
            return self.avg_entry_price
        notional = sum(
            (lot.shares_remaining * lot.entry_price for lot in self.lots), ZERO
        )
        return notional / open_shares

    def _consume_proportionally(self, shares: Decimal, realized: Decimal) -> None:
        """Reduce every open lot pro rata (weighted-average accounting)."""
        open_shares = sum((lot.shares_remaining for lot in self.lots), ZERO)
        if open_shares <= ZERO:
            return
        ratio = shares / open_shares
        for lot in self.lots:
            if lot.fully_consumed:
                continue
            take = lot.shares_remaining * ratio
            lot.shares_remaining -= take
            if open_shares > ZERO:
                lot.realized_pnl += realized * (take / shares) if shares > ZERO else ZERO


@dataclass(slots=True)
class MarketContext:
    """Resolution and classification facts needed to settle a position."""

    condition_id: str
    resolved: bool = False
    winning_outcome_index: int | None = None
    resolved_at: datetime | None = None
    game_start_time: datetime | None = None
    is_tennis: bool = False
    tennis_market_type: str = TennisMarketType.UNKNOWN
    closed: bool = False


class TradeReconstructor:
    """Rebuilds positions for one wallet from its normalized transactions."""

    def __init__(
        self,
        accounting_method: AccountingMethod = "fifo",
        *,
        settle_resolved_markets: bool = True,
    ) -> None:
        if accounting_method not in ("fifo", "weighted_average"):
            raise ValueError(f"Unsupported accounting method: {accounting_method!r}")
        self.accounting_method = accounting_method
        self.settle_resolved_markets = settle_resolved_markets

    def reconstruct(
        self,
        transactions: list[TxInput],
        market_contexts: dict[str, MarketContext] | None = None,
        *,
        token_to_condition: dict[str, str] | None = None,
        token_outcome_index: dict[str, int] | None = None,
        wallet_portfolio_value: Decimal | None = None,
    ) -> list[ReconstructedPositionData]:
        """Reconstruct every round trip across all tokens for one wallet.

        ``transactions`` need not be sorted; they are ordered chronologically
        here because out-of-order processing would mis-assign lots.
        """
        contexts = market_contexts or {}
        token_condition = token_to_condition or {}

        ordered = sorted(
            transactions,
            # Ties broken by id so repeated runs produce identical output.
            key=lambda t: (t.timestamp, t.id if t.id is not None else 0),
        )

        by_token: dict[str, list[TxInput]] = {}
        for tx in ordered:
            if not tx.token_id:
                continue
            by_token.setdefault(tx.token_id, []).append(tx)

        positions: list[ReconstructedPositionData] = []
        for token_id, txs in by_token.items():
            condition_id = (
                txs[0].condition_id or token_condition.get(token_id) or None
            )
            ctx = contexts.get(condition_id) if condition_id else None
            outcome_index = txs[0].outcome_index
            if outcome_index is None and token_outcome_index:
                outcome_index = token_outcome_index.get(token_id)
            positions.extend(
                self._reconstruct_token(token_id, txs, ctx, condition_id, outcome_index)
            )

        self._annotate_cross_token_behaviour(positions, contexts)

        if wallet_portfolio_value and wallet_portfolio_value > ZERO:
            for pos in positions:
                pos_pct = float(pos.max_capital_at_risk / wallet_portfolio_value)
                # Stored on the ORM row by the caller; kept here for reporting.
                pos.notes.append(f"pct_of_observed_capital={pos_pct:.4f}")

        return positions

    # ------------------------------------------------------------- internals
    def _reconstruct_token(
        self,
        token_id: str,
        txs: list[TxInput],
        ctx: MarketContext | None,
        condition_id: str | None,
        outcome_index: int | None,
    ) -> list[ReconstructedPositionData]:
        positions: list[ReconstructedPositionData] = []
        current: ReconstructedPositionData | None = None
        sequence = 0
        flip_count = 0
        last_direction: str | None = None
        unpriced_exits = 0

        for tx in txs:
            signed = tx.signed_size
            if signed == ZERO:
                # Rebates/rewards: cash only. Attributed as a fee credit so the
                # wallet's economics stay honest without inventing exposure.
                if current is not None and tx.activity_type in (
                    ActivityType.TAKER_REBATE,
                    ActivityType.MAKER_REBATE,
                    ActivityType.REWARD,
                ):
                    credit = tx.usdc_size or ZERO
                    current.fees_paid -= credit
                    if credit > ZERO:
                        current.notes.append(f"{tx.activity_type.lower()}_credit={credit}")
                continue

            direction = "buy" if signed > ZERO else "sell"
            if last_direction is not None and direction != last_direction:
                flip_count += 1
            last_direction = direction

            if signed > ZERO:
                price = tx.effective_price()
                if price is None:
                    # SPLIT mints both outcomes for $1 total; each side costs
                    # $0.50 in the absence of a stated price.
                    price = (
                        Decimal("0.5")
                        if tx.activity_type == ActivityType.SPLIT
                        else ZERO
                    )
                    if current is not None:
                        current.reconstruction_confidence = min(
                            current.reconstruction_confidence, 70.0
                        )

                if current is None:
                    sequence += 1
                    current = ReconstructedPositionData(
                        token_id=token_id,
                        sequence=sequence,
                        condition_id=condition_id,
                        outcome_index=outcome_index,
                        accounting_method=self.accounting_method,
                        opened_ts=tx.timestamp,
                        first_entry_price=price,
                        entry_phase=tx.market_phase,
                    )
                    if tx.activity_type == ActivityType.SPLIT:
                        current.notes.append("opened via SPLIT (price modelled at 0.5)")
                current.add_lot(tx, price)
            else:
                if current is None:
                    # Selling with no tracked entry: the wallet acquired shares
                    # before our ingestion window, or via an unobserved path.
                    # Fabricating a synthetic entry would invent a P&L number, so
                    # the disposal is skipped and the gap recorded instead.
                    log.debug(
                        "reconstruction.exit_without_entry",
                        token_id=token_id,
                        ts=tx.timestamp,
                    )
                    continue

                is_settlement = tx.activity_type in (
                    ActivityType.REDEEM,
                    ActivityType.MERGE,
                )
                price = self._settlement_price(tx, ctx, outcome_index)
                if price is None:
                    price = tx.effective_price()
                if price is None:
                    unpriced_exits += 1
                    price = current.avg_open_cost()
                    current.reconstruction_confidence = min(
                        current.reconstruction_confidence, 60.0
                    )
                    current.notes.append("exit price unavailable; assumed break-even")
                    current.flags.append(RiskFlag.AMBIGUOUS_RECONSTRUCTION)

                current.reduce(tx, price, is_settlement=is_settlement)
                if current.status in (PositionStatus.CLOSED, PositionStatus.SETTLED):
                    self._finalise(current, ctx, flip_count)
                    positions.append(current)
                    current = None
                    last_direction = None

        if current is not None:
            # Still open at the end of the tape. If the market has resolved we
            # settle analytically so winners are not stranded as "open".
            if (
                self.settle_resolved_markets
                and ctx is not None
                and ctx.resolved
                and ctx.winning_outcome_index is not None
                and outcome_index is not None
            ):
                self._settle_open_position(current, ctx, outcome_index)
            self._finalise(current, ctx, flip_count)
            positions.append(current)

        if unpriced_exits:
            log.debug(
                "reconstruction.unpriced_exits", token_id=token_id, count=unpriced_exits
            )
        return positions

    @staticmethod
    def _settlement_price(
        tx: TxInput, ctx: MarketContext | None, outcome_index: int | None
    ) -> Decimal | None:
        """Price a REDEEM from the resolved outcome, not from a trade price.

        A redemption's ``price`` field is unreliable, but the economics are not
        ambiguous: a winning share pays exactly $1 and a losing share $0.
        """
        if tx.activity_type != ActivityType.REDEEM:
            return None
        if ctx is None or not ctx.resolved or ctx.winning_outcome_index is None:
            return None
        if outcome_index is None:
            return None
        return ONE if outcome_index == ctx.winning_outcome_index else ZERO

    def _settle_open_position(
        self, pos: ReconstructedPositionData, ctx: MarketContext, outcome_index: int
    ) -> None:
        """Close a still-open position at its resolved value."""
        won = outcome_index == ctx.winning_outcome_index
        price = ONE if won else ZERO
        settle_ts = int(
            (ctx.resolved_at or datetime.now(timezone.utc)).timestamp()
        )
        synthetic = TxInput(
            id=None,
            timestamp=max(settle_ts, pos.opened_ts),
            activity_type=ActivityType.REDEEM,
            size=pos.current_shares,
            side=None,
            price=price,
        )
        pos.reduce(synthetic, price, is_settlement=True)
        pos.notes.append(
            f"settled analytically at resolution (outcome "
            f"{'won' if won else 'lost'}; no REDEEM observed)"
        )

    def _finalise(
        self,
        pos: ReconstructedPositionData,
        ctx: MarketContext | None,
        flip_count: int,
    ) -> None:
        """Attach behavioural flags and confidence to a completed position."""
        if ctx is not None:
            if ctx.game_start_time is not None:
                opened = datetime.fromtimestamp(pos.opened_ts, tz=timezone.utc)
                pos.entry_phase = (
                    MarketPhase.PREMATCH
                    if opened < ctx.game_start_time
                    else MarketPhase.LIVE
                )

        holding = pos.holding_seconds

        # --- behaviour classification (flags, never asserted as fact) -------
        if flip_count >= MARKET_MAKING_MIN_FLIPS and pos.partial_exit_count >= 2:
            pos.behaviour = PositionBehaviour.LIKELY_MARKET_MAKING
            pos.flags.append(RiskFlag.LIKELY_MARKET_MAKING)
            pos.notes.append(f"direction flips={flip_count}")
        elif holding is not None and holding <= SCALP_SECONDS and pos.total_shares_sold > ZERO:
            pos.behaviour = PositionBehaviour.SCALP
            pos.flags.append(RiskFlag.RAPID_EXIT_PATTERN)
        elif pos.status == PositionStatus.OPEN and pos.total_shares_sold == ZERO:
            pos.behaviour = PositionBehaviour.DIRECTIONAL

        if pos.reconstruction_confidence < 80.0:
            pos.flags.append(RiskFlag.AMBIGUOUS_RECONSTRUCTION)

        # A position opened by SPLIT is structurally not a directional view.
        if any("SPLIT" in n for n in pos.notes):
            pos.behaviour = PositionBehaviour.LIQUIDITY_PROVISION

    def _annotate_cross_token_behaviour(
        self,
        positions: list[ReconstructedPositionData],
        contexts: dict[str, MarketContext],
    ) -> None:
        """Detect hedging/arbitrage by comparing sibling outcomes of one market.

        Holding both sides of a binary market at the same time is not a
        directional bet, and counting it as one would credit a wallet with
        "wins" that were structurally guaranteed. Overlap is measured in time,
        so sequential trades on both sides are not mistaken for a hedge.
        """
        by_condition: dict[str, list[ReconstructedPositionData]] = {}
        for pos in positions:
            if pos.condition_id:
                by_condition.setdefault(pos.condition_id, []).append(pos)

        for condition_id, group in by_condition.items():
            tokens = {p.token_id for p in group}
            if len(tokens) < 2:
                continue

            for pos in group:
                for other in group:
                    if other.token_id == pos.token_id:
                        continue
                    if self._overlaps_in_time(pos, other):
                        pos.held_both_outcomes = True
                        smaller = min(pos.max_shares, other.max_shares)
                        larger = max(pos.max_shares, other.max_shares, DUST)
                        overlap_fraction = smaller / larger
                        if overlap_fraction >= HEDGE_OVERLAP_FRACTION:
                            # Near-equal size on both sides looks like arbitrage;
                            # a smaller offsetting leg looks like a hedge.
                            pos.behaviour = (
                                PositionBehaviour.POSSIBLE_ARBITRAGE
                                if overlap_fraction >= Decimal("0.9")
                                else PositionBehaviour.POSSIBLE_HEDGE
                            )
                            pos.flags.append(RiskFlag.HEDGING_BEHAVIOUR)
                            pos.notes.append(
                                f"held both outcomes of {condition_id[:12]}... "
                                f"(size ratio {float(overlap_fraction):.2f})"
                            )
                        break

    @staticmethod
    def _overlaps_in_time(
        a: ReconstructedPositionData, b: ReconstructedPositionData
    ) -> bool:
        """True when two positions were open simultaneously."""
        a_end = a.closed_ts if a.closed_ts is not None else 2**62
        b_end = b.closed_ts if b.closed_ts is not None else 2**62
        return a.opened_ts < b_end and b.opened_ts < a_end


def summarise_positions(positions: list[ReconstructedPositionData]) -> dict[str, object]:
    """Compact roll-up used in logs and reconstruction tests."""
    complete = [p for p in positions if p.status in (PositionStatus.CLOSED, PositionStatus.SETTLED)]
    return {
        "positions": len(positions),
        "complete": len(complete),
        "open": len(positions) - len(complete),
        "net_pnl": str(sum((p.net_pnl for p in complete), ZERO)),
        "wins": sum(1 for p in complete if p.is_win),
        "losses": sum(1 for p in complete if p.is_win is False),
        "behaviours": {
            b: sum(1 for p in positions if p.behaviour == b)
            for b in {p.behaviour for p in positions}
        },
    }
