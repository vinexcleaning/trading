"""Adaptive wallet rotation: follow while hot, drop when it turns.

The static gates elsewhere in this system ask "has this wallet been good over its
whole history". In a market that adapts, that question systematically selects for
edges that have already died -- by the time an edge is provable over months, the
market has usually priced it away.

This module asks a different question: **is this wallet good right now, and is it
still trading?** It scores a rolling window of the most recent trades rather than
the lifetime record, and it emits explicit FOLLOW / HOLD / DROP decisions so the
follow-list can rotate as form changes.

Two failure modes it is built to avoid:

* **Whipsaw.** Dropping on a short losing run sells the dip on a wallet that is
  merely experiencing variance. Dropping therefore requires the *rolling* edge to
  go negative, not merely a few losses, and a separate (larger) minimum sample.
* **Chasing noise.** A hot streak over 8 trades is not evidence. Following
  requires a minimum number of outcomes in the window, so a burst of luck cannot
  promote a wallet on its own.

Nothing here is calendar-based except the staleness check. Sample size is counted
in *trades*, because that is what statistics respond to -- 400 trades in two days
is a stronger sample than 40 trades over six months, and far more current.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from ..logging_setup import get_logger

log = get_logger(__name__)


class RotationAction(StrEnum):
    FOLLOW = "follow"      # not currently followed, form justifies starting
    HOLD = "hold"          # already followed, form still acceptable
    DROP = "drop"          # followed, but form has deteriorated
    IGNORE = "ignore"      # not followed and not worth starting
    WATCH = "watch"        # promising but not yet enough trades in the window


@dataclass(slots=True)
class RotationConfig:
    """Thresholds for the rotation decision.

    Defaults are deliberately looser than the static alert gates: this mechanism
    is meant to catch a wallet *while* it is working, accepting that some of what
    it catches will be luck, because the drop rule limits the cost of being wrong.
    """

    # Trades in the rolling window used to judge current form.
    window_trades: int = 40
    # Minimum outcomes in the window before any positive decision.
    min_window_trades: int = 20
    # Edge (realised win rate minus price-implied) required to start following.
    follow_edge: float = 0.03
    # Edge below which a followed wallet is dropped. Deliberately below zero so
    # ordinary variance does not trigger a sale.
    drop_edge: float = -0.01
    # A wallet silent for longer than this is not tradeable regardless of record.
    max_quiet_days: int = 10
    # Minimum trades per active day, so the window refreshes at a usable rate.
    min_trades_per_day: float = 0.25
    # Require the recent half of the window to not be collapsing.
    max_form_decay: float = 0.10


@dataclass(slots=True)
class TradeOutcome:
    """One completed trade, reduced to what rotation needs."""

    opened_ts: int
    entry_price: float
    is_win: bool
    roi: float | None = None


@dataclass
class RotationDecision:
    address: str
    action: RotationAction
    window_trades: int = 0
    window_edge: float | None = None
    lifetime_edge: float | None = None
    recent_half_edge: float | None = None
    older_half_edge: float | None = None
    trades_per_day: float | None = None
    quiet_days: int | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def is_followable(self) -> bool:
        return self.action in (RotationAction.FOLLOW, RotationAction.HOLD)


def _edge(trades: list[TradeOutcome]) -> float | None:
    """Realised win rate minus the probability the entry prices implied.

    Works identically for favourites and longshots: a price *is* a probability,
    so paying $0.35 requires winning 35% of the time to break even.
    """
    if not trades:
        return None
    wins = sum(1 for t in trades if t.is_win)
    implied = sum(t.entry_price for t in trades) / len(trades)
    return wins / len(trades) - implied


class WalletRotationEngine:
    """Decides which wallets to follow right now."""

    def __init__(self, config: RotationConfig | None = None, *, now: datetime | None = None) -> None:
        self.config = config or RotationConfig()
        self.now = now or datetime.now(timezone.utc)

    def evaluate(
        self,
        address: str,
        trades: list[TradeOutcome],
        *,
        currently_followed: bool = False,
    ) -> RotationDecision:
        c = self.config
        decision = RotationDecision(address=address, action=RotationAction.IGNORE)

        if not trades:
            decision.reasons.append("no completed tennis trades")
            return decision

        ordered = sorted(trades, key=lambda t: t.opened_ts)
        window = ordered[-c.window_trades :]
        decision.window_trades = len(window)
        decision.lifetime_edge = _edge(ordered)
        decision.window_edge = _edge(window)

        # --- is it still trading? ------------------------------------------
        last = datetime.fromtimestamp(ordered[-1].opened_ts, tz=timezone.utc)
        quiet = (self.now - last).days
        decision.quiet_days = quiet

        span_days = max(
            1.0, (ordered[-1].opened_ts - ordered[0].opened_ts) / 86400
        )
        decision.trades_per_day = round(len(ordered) / span_days, 2)

        if quiet > c.max_quiet_days:
            decision.action = RotationAction.DROP if currently_followed else RotationAction.IGNORE
            decision.reasons.append(
                f"silent for {quiet} days (limit {c.max_quiet_days}); a dormant wallet "
                "cannot be followed no matter how good its record looks"
            )
            return decision

        # --- form trend within the window ----------------------------------
        mid = len(window) // 2
        if mid:
            decision.older_half_edge = _edge(window[:mid])
            decision.recent_half_edge = _edge(window[mid:])

        # --- enough outcomes to judge? -------------------------------------
        if len(window) < c.min_window_trades:
            decision.action = (
                RotationAction.HOLD if currently_followed else RotationAction.WATCH
            )
            decision.reasons.append(
                f"only {len(window)} trades in the window; {c.min_window_trades} needed "
                "before form means anything"
            )
            return decision

        edge = decision.window_edge or 0.0

        # --- drop rules (applied first: exiting beats entering) -------------
        if currently_followed:
            if edge < c.drop_edge:
                decision.action = RotationAction.DROP
                decision.reasons.append(
                    f"rolling edge {edge * 100:+.1f}pp has fallen below "
                    f"{c.drop_edge * 100:+.1f}pp over the last {len(window)} trades"
                )
                return decision

            decay = None
            if decision.older_half_edge is not None and decision.recent_half_edge is not None:
                decay = decision.older_half_edge - decision.recent_half_edge
            if decay is not None and decay > c.max_form_decay and (decision.recent_half_edge or 0) < 0:
                decision.action = RotationAction.DROP
                decision.reasons.append(
                    f"form is collapsing inside the window: {decision.older_half_edge * 100:+.1f}pp "
                    f"then {decision.recent_half_edge * 100:+.1f}pp"
                )
                return decision

            decision.action = RotationAction.HOLD
            decision.reasons.append(
                f"rolling edge {edge * 100:+.1f}pp still above the drop line"
            )
            return decision

        # --- follow rules ---------------------------------------------------
        if edge < c.follow_edge:
            decision.action = RotationAction.IGNORE
            decision.reasons.append(
                f"rolling edge {edge * 100:+.1f}pp is below the {c.follow_edge * 100:+.1f}pp "
                "required to start following"
            )
            return decision

        if (decision.trades_per_day or 0) < c.min_trades_per_day:
            decision.action = RotationAction.WATCH
            decision.reasons.append(
                f"trades too infrequently ({decision.trades_per_day}/day) for the window to "
                "refresh at a usable rate"
            )
            return decision

        decision.action = RotationAction.FOLLOW
        decision.reasons.append(
            f"rolling edge {edge * 100:+.1f}pp over {len(window)} recent trades, "
            f"still active ({quiet}d quiet, {decision.trades_per_day}/day)"
        )
        if decision.lifetime_edge is not None and edge > decision.lifetime_edge + 0.02:
            decision.reasons.append(
                f"improving: lifetime edge is only {decision.lifetime_edge * 100:+.1f}pp"
            )
        return decision


def rank_candidates(decisions: list[RotationDecision]) -> list[RotationDecision]:
    """Followable wallets first, strongest current form at the top."""
    return sorted(
        decisions,
        key=lambda d: (
            d.is_followable,
            d.window_edge if d.window_edge is not None else -99,
        ),
        reverse=True,
    )
