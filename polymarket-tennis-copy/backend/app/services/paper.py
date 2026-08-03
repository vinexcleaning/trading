"""Paper-trading engine. Simulation only -- never places a real order.

Risk controls are enforced *before* a simulated entry, not reported after, so the
simulation cannot quietly exceed limits a real deployment would enforce. The
defaults are deliberately small ($5 stake, $50 total exposure) and are simulation
parameters, not position-sizing advice.

Fill realism
------------
Every entry is priced at the market *after* a configured execution delay, walked
through real order-book depth where available, and reduced when depth cannot
absorb the stake. A paper trade that could not have been filled is recorded as
rejected rather than silently filled at an unavailable price.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from ..config import Settings, get_settings
from ..enums import ExitStrategy, PaperEventType, PaperTradeStatus, PriceSourceQuality
from ..logging_setup import get_logger
from .prices import PriceSeries, estimate_follower_fill

log = get_logger(__name__)

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(slots=True)
class RiskState:
    """Live exposure snapshot used to gate new entries."""

    open_positions: int = 0
    total_exposure: Decimal = ZERO
    exposure_by_market: dict[str, Decimal] = field(default_factory=dict)
    realized_pnl_today: Decimal = ZERO
    entries_today: int = 0

    def market_exposure(self, key: str) -> Decimal:
        return self.exposure_by_market.get(key, ZERO)


@dataclass(slots=True)
class RiskDecision:
    allowed: bool
    stake: Decimal
    reason: str | None = None
    reduced: bool = False


@dataclass(slots=True)
class PaperEntry:
    """A simulated entry, or a documented refusal to enter."""

    accepted: bool
    stake_usdc: Decimal
    reference_price: Decimal | None = None
    fill_price: Decimal | None = None
    shares: Decimal | None = None
    slippage: Decimal | None = None
    fees: Decimal = ZERO
    entered_at: datetime | None = None
    price_source_quality: PriceSourceQuality = PriceSourceQuality.UNAVAILABLE
    data_confidence: float = 0.0
    stake_reduced_for_liquidity: bool = False
    rejection_reason: str | None = None
    note: str | None = None


@dataclass(slots=True)
class PaperExit:
    exited: bool
    exit_price: Decimal | None = None
    exited_at: datetime | None = None
    reason: str | None = None
    realized_pnl: Decimal | None = None
    roi: float | None = None
    settled_by_resolution: bool = False


class RiskManager:
    """Enforces the configured paper-trading limits."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(
        self,
        state: RiskState,
        market_key: str,
        *,
        requested_stake: Decimal | None = None,
        modeled_fillable: Decimal | None = None,
    ) -> RiskDecision:
        s = self.settings
        stake = requested_stake if requested_stake is not None else s.paper_stake_usdc

        if not s.paper_trading_enabled:
            return RiskDecision(False, ZERO, "paper trading is disabled")

        if state.open_positions >= s.paper_max_open_positions:
            return RiskDecision(
                False, ZERO,
                f"max open positions reached ({s.paper_max_open_positions})",
            )

        # Daily loss cap: compared against a negative realized total.
        if state.realized_pnl_today <= -s.paper_daily_loss_cap_usdc:
            return RiskDecision(
                False, ZERO,
                f"daily loss cap reached (${s.paper_daily_loss_cap_usdc})",
            )

        remaining_total = s.paper_max_total_exposure_usdc - state.total_exposure
        if remaining_total <= ZERO:
            return RiskDecision(
                False, ZERO,
                f"total exposure cap reached (${s.paper_max_total_exposure_usdc})",
            )

        remaining_market = (
            s.paper_max_exposure_per_market_usdc - state.market_exposure(market_key)
        )
        if remaining_market <= ZERO:
            return RiskDecision(
                False, ZERO,
                f"per-market exposure cap reached "
                f"(${s.paper_max_exposure_per_market_usdc})",
            )

        allowed = min(stake, remaining_total, remaining_market)
        reduced = allowed < stake

        # Never simulate more size than modelled depth could absorb.
        if modeled_fillable is not None and modeled_fillable < allowed:
            allowed = modeled_fillable
            reduced = True

        if allowed < s.min_order_size_usdc:
            return RiskDecision(
                False, ZERO,
                f"remaining allowance ${allowed} is below the minimum order size "
                f"${s.min_order_size_usdc}",
            )

        return RiskDecision(True, allowed, None, reduced)


class PaperTradingEngine:
    """Simulates follower entries and exits."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.risk = RiskManager(self.settings)

    # ----------------------------------------------------------------- entry
    def simulate_entry(
        self,
        *,
        signal_detected_at: datetime,
        series: PriceSeries,
        wallet_entry_price: Decimal | None,
        risk_state: RiskState,
        market_key: str,
        book=None,
        spread: Decimal | None = None,
        execution_delay_seconds: int | None = None,
        requested_stake: Decimal | None = None,
    ) -> PaperEntry:
        """Simulate an entry at the price available after the execution delay."""
        s = self.settings
        delay = (
            execution_delay_seconds
            if execution_delay_seconds is not None
            else s.paper_execution_delay_seconds
        )
        entry_time = signal_detected_at + timedelta(seconds=delay)
        target_ts = int(entry_time.timestamp())

        resolved = series.resolve(target_ts, fallback_price=wallet_entry_price)
        if not resolved.is_usable or resolved.price is None:
            return PaperEntry(
                accepted=False,
                stake_usdc=ZERO,
                rejection_reason="no_price_available",
                price_source_quality=resolved.quality,
                note=(
                    "no usable price at the simulated execution time; entry "
                    "refused rather than filled at a guessed price"
                ),
            )

        # Probe depth first so the risk manager can cap the stake to what is
        # actually fillable.
        probe_stake = requested_stake if requested_stake is not None else s.paper_stake_usdc
        probe = estimate_follower_fill(
            resolved.price, probe_stake, book=book, spread=spread,
            slippage_bps=s.modeled_slippage_bps, price_quality=resolved.quality,
        )
        fillable = probe.filled_notional if probe.partially_filled else None

        decision = self.risk.evaluate(
            risk_state, market_key,
            requested_stake=requested_stake, modeled_fillable=fillable,
        )
        if not decision.allowed:
            return PaperEntry(
                accepted=False,
                stake_usdc=ZERO,
                rejection_reason="risk_limit",
                price_source_quality=resolved.quality,
                note=decision.reason,
            )

        fill = estimate_follower_fill(
            resolved.price, decision.stake, book=book, spread=spread,
            slippage_bps=s.modeled_slippage_bps, price_quality=resolved.quality,
        )
        if fill.fill_price <= ZERO:
            return PaperEntry(
                accepted=False, stake_usdc=ZERO,
                rejection_reason="invalid_fill_price",
                price_source_quality=resolved.quality,
            )

        stake = fill.filled_notional
        shares = stake / fill.fill_price
        fees = stake * Decimal(s.taker_fee_bps) / Decimal("10000")

        return PaperEntry(
            accepted=True,
            stake_usdc=stake,
            reference_price=resolved.price,
            fill_price=fill.fill_price,
            shares=shares,
            slippage=fill.slippage,
            fees=fees,
            entered_at=entry_time,
            price_source_quality=resolved.quality,
            data_confidence=resolved.confidence,
            stake_reduced_for_liquidity=decision.reduced or fill.partially_filled,
            note="; ".join(x for x in (resolved.note, fill.note, decision.reason) if x),
        )

    # ------------------------------------------------------------------ exit
    def evaluate_exit(
        self,
        *,
        strategy: ExitStrategy,
        entered_at: datetime,
        fill_price: Decimal,
        shares: Decimal,
        stake_usdc: Decimal,
        now: datetime,
        current_price: Decimal | None = None,
        peak_price: Decimal | None = None,
        market_resolved: bool = False,
        won: bool | None = None,
        wallet_has_exited: bool = False,
        wallet_reduced: bool = False,
        consensus_still_present: bool = True,
        profit_target: Decimal | None = None,
        stop_loss: Decimal | None = None,
        max_hold_seconds: int | None = None,
        trailing_pct: Decimal | None = None,
    ) -> PaperExit:
        """Decide whether a simulated position exits now, and at what price.

        Resolution is checked first and unconditionally: once a market settles,
        every strategy is closed out at $1 or $0 regardless of its rule.
        """
        s = self.settings

        if market_resolved and won is not None:
            exit_price = ONE if won else ZERO
            return self._close(
                fill_price, shares, stake_usdc, exit_price, now,
                "market_resolved", settled=True,
            )

        if current_price is None:
            return PaperExit(exited=False)

        held = (now - entered_at).total_seconds()

        if strategy is ExitStrategy.HOLD_TO_RESOLUTION:
            return PaperExit(exited=False)

        if strategy is ExitStrategy.FOLLOW_WALLET_EXIT and wallet_has_exited:
            return self._close(
                fill_price, shares, stake_usdc, current_price, now, "wallet_exited"
            )

        if strategy is ExitStrategy.WALLET_REDUCES and (wallet_reduced or wallet_has_exited):
            return self._close(
                fill_price, shares, stake_usdc, current_price, now, "wallet_reduced"
            )

        if strategy is ExitStrategy.CONSENSUS_GONE and not consensus_still_present:
            return self._close(
                fill_price, shares, stake_usdc, current_price, now, "consensus_gone"
            )

        if strategy is ExitStrategy.PROFIT_TARGET:
            target = profit_target if profit_target is not None else s.paper_profit_target
            if fill_price > ZERO and (current_price - fill_price) / fill_price >= target:
                return self._close(
                    fill_price, shares, stake_usdc, current_price, now, "profit_target"
                )

        if strategy is ExitStrategy.STOP_LOSS:
            stop = stop_loss if stop_loss is not None else s.paper_stop_loss
            if fill_price > ZERO and (fill_price - current_price) / fill_price >= stop:
                return self._close(
                    fill_price, shares, stake_usdc, current_price, now, "stop_loss"
                )

        if strategy is ExitStrategy.FIXED_HOLD:
            limit = max_hold_seconds if max_hold_seconds is not None else s.paper_max_hold_seconds
            if held >= limit:
                return self._close(
                    fill_price, shares, stake_usdc, current_price, now, "max_hold_reached"
                )

        if strategy is ExitStrategy.TRAILING_STOP and peak_price is not None:
            pct = trailing_pct if trailing_pct is not None else Decimal("0.20")
            if peak_price > ZERO and (peak_price - current_price) / peak_price >= pct:
                return self._close(
                    fill_price, shares, stake_usdc, current_price, now, "trailing_stop"
                )

        return PaperExit(exited=False)

    @staticmethod
    def _close(
        fill_price: Decimal,
        shares: Decimal,
        stake_usdc: Decimal,
        exit_price: Decimal,
        now: datetime,
        reason: str,
        *,
        settled: bool = False,
    ) -> PaperExit:
        pnl = shares * (exit_price - fill_price)
        roi = float(pnl / stake_usdc) if stake_usdc > ZERO else None
        return PaperExit(
            exited=True,
            exit_price=exit_price,
            exited_at=now,
            reason=reason,
            realized_pnl=pnl,
            roi=roi,
            settled_by_resolution=settled,
        )

    def mark_to_market(
        self, fill_price: Decimal, shares: Decimal, current_price: Decimal
    ) -> Decimal:
        return shares * (current_price - fill_price)


@dataclass(slots=True)
class PaperSummary:
    """Aggregate paper-trading performance, including the wallet comparison."""

    trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_staked: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    unrealized_pnl: Decimal = ZERO
    roi: float | None = None
    win_rate: float | None = None
    rejected: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    # Mean gap between follower and source-wallet ROI: the measured cost of delay.
    avg_roi_gap_vs_wallet: float | None = None

    @property
    def net_pnl(self) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl


def summarise_paper_trades(rows: list[dict]) -> PaperSummary:
    """Roll up paper-trade rows into a summary.

    Each row needs ``status``, ``stake_usdc``, ``realized_pnl``,
    ``unrealized_pnl``, ``is_win``, ``roi_gap_vs_wallet``, ``rejection_reason``.
    """
    summary = PaperSummary(trades=len(rows))

    gaps: list[float] = []
    for row in rows:
        status = row.get("status")
        if status == PaperTradeStatus.REJECTED:
            summary.rejected += 1
            reason = row.get("rejection_reason") or "unknown"
            summary.rejection_reasons[reason] = (
                summary.rejection_reasons.get(reason, 0) + 1
            )
            continue

        summary.total_staked += Decimal(str(row.get("stake_usdc") or 0))

        if status in (PaperTradeStatus.CLOSED, PaperTradeStatus.SETTLED):
            summary.closed_trades += 1
            summary.realized_pnl += Decimal(str(row.get("realized_pnl") or 0))
            if row.get("is_win") is True:
                summary.wins += 1
            elif row.get("is_win") is False:
                summary.losses += 1
            gap = row.get("roi_gap_vs_wallet")
            if gap is not None:
                gaps.append(float(gap))
        elif status == PaperTradeStatus.OPEN:
            summary.open_trades += 1
            summary.unrealized_pnl += Decimal(str(row.get("unrealized_pnl") or 0))

    if summary.total_staked > ZERO:
        summary.roi = round(float(summary.net_pnl / summary.total_staked), 6)
    decided = summary.wins + summary.losses
    if decided:
        summary.win_rate = round(summary.wins / decided, 4)
    if gaps:
        summary.avg_roi_gap_vs_wallet = round(sum(gaps) / len(gaps), 6)
    return summary


def today_utc() -> date:
    return datetime.now(timezone.utc).date()
