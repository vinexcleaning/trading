"""Adaptive wallet allocation: follow what is working now, drop what stops.

The static scoring in :mod:`scoring` answers "is this wallet's whole record good
enough to trust". That turned out to be the wrong question for a live tool. It
ranked a wallet that had not traded in 57 days as the best candidate, because a
lifetime average has no opinion about whether the trader is still there.

This module answers the operational question instead: **who should I be
following this week, and who should I stop following?** Three departures from the
static score, each one a correction to a real failure:

1. **Liveness is a gate, not a weight.** A wallet that has stopped trading is
   not a candidate at any score. Recency at 10% of a blended score cannot
   express that.

2. **Rolling windows beat lifetime averages.** Form is measured over the recent
   window and compared against the prior one, so a decaying edge shows up as a
   trend rather than being averaged away by good history.

3. **Profit concentration is not penalised.** A longshot strategy earns from
   rare large winners by design; docking it for that shape punishes the strategy
   for working as intended. Concentration is reported so it stays visible, and
   it feeds the *sizing* recommendation rather than the ranking.

What has NOT changed: this ranks candidates to watch and paper-trade. Nothing
here is a recommendation to bet, and a high rank on a short record still means
"promising and unproven", which is why :class:`AllocationState` carries an
explicit confidence tier and a suggested stake fraction rather than a verdict.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..logging_setup import get_logger
from ..models import ReconstructedPosition, Wallet

log = get_logger(__name__)

ZERO = Decimal("0")

# A wallet silent for longer than this is not followable, whatever its record.
MAX_SILENCE_DAYS = 14
# Recent window used for current form.
FORM_WINDOW_DAYS = 30
# Prior window, compared against the recent one to detect decay.
PRIOR_WINDOW_DAYS = 90
# Minimum trades in the form window before form is treated as measured at all.
MIN_FORM_TRADES = 8
# Trades below which a wallet is watch-only regardless of returns.
MIN_TRADES_FOR_SIZING = 25


class Stance(StrEnum):
    """What to do about a wallet right now."""

    FOLLOW = "follow"          # active, positive form, enough sample to size
    PROBATION = "probation"    # active and positive but thin or deteriorating
    WATCH = "watch"            # promising, not yet enough evidence to stake
    PAUSE = "pause"            # was followable, form has turned negative
    DROP = "drop"              # gone quiet, or persistently negative


@dataclass(slots=True)
class WindowStats:
    """Performance over one time window, flat-staked per trade."""

    trades: int = 0
    wins: int = 0
    mean_pct: float = 0.0      # mean per-trade return, %
    median_pct: float = 0.0
    total_pct: float = 0.0     # sum of per-trade returns, % (flat-stake profit)
    win_rate: float = 0.0
    implied_win_rate: float = 0.0   # mean entry price = market's own probability
    edge_pp: float = 0.0            # win_rate - implied, in percentage points

    @property
    def measured(self) -> bool:
        return self.trades >= MIN_FORM_TRADES


@dataclass
class AllocationState:
    """A wallet's current standing and the reasoning behind it."""

    wallet_id: int
    address: str
    stance: Stance
    # 0-100. Ranks *current followability*, not lifetime quality.
    form_score: float = 0.0
    days_since_last_trade: int = 0
    active_span_days: int = 0
    trades_per_day: float = 0.0

    lifetime: WindowStats = field(default_factory=WindowStats)
    form: WindowStats = field(default_factory=WindowStats)
    prior: WindowStats = field(default_factory=WindowStats)

    # form.mean_pct - prior.mean_pct: positive means improving.
    trend_pp: float | None = None
    # Share of profit from the single best trade. Reported, never penalised.
    concentration: float | None = None
    median_position_usdc: float = 0.0

    # Fraction of the configured stake to risk, given sample size and volatility.
    suggested_stake_fraction: float = 0.0
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "wallet_id": self.wallet_id,
            "address": self.address,
            "stance": self.stance.value,
            "form_score": round(self.form_score, 1),
            "days_since_last_trade": self.days_since_last_trade,
            "active_span_days": self.active_span_days,
            "trades_per_day": round(self.trades_per_day, 2),
            "lifetime_trades": self.lifetime.trades,
            "lifetime_per_trade_pct": round(self.lifetime.mean_pct, 2),
            "form_trades": self.form.trades,
            "form_per_trade_pct": round(self.form.mean_pct, 2),
            "form_edge_pp": round(self.form.edge_pp, 2),
            "trend_pp": None if self.trend_pp is None else round(self.trend_pp, 2),
            "concentration": None if self.concentration is None else round(self.concentration, 3),
            "median_position_usdc": round(self.median_position_usdc, 2),
            "suggested_stake_fraction": round(self.suggested_stake_fraction, 3),
            "reasons": self.reasons,
            "warnings": self.warnings,
        }


def _window(rows: list[tuple]) -> WindowStats:
    """Summarise (opened_at, net_pnl, capital, is_win, entry_price) rows."""
    stats = WindowStats()
    per: list[float] = []
    entries: list[float] = []
    for _opened, pnl, capital, is_win, entry in rows:
        if capital is None or float(capital) <= 0 or pnl is None:
            continue
        per.append(100.0 * float(pnl) / float(capital))
        if entry is not None:
            entries.append(float(entry))
        if is_win:
            stats.wins += 1
    if not per:
        return stats

    stats.trades = len(per)
    stats.mean_pct = sum(per) / len(per)
    stats.median_pct = statistics.median(per)
    stats.total_pct = sum(per)
    stats.win_rate = stats.wins / len(per)
    if entries:
        # The market's own probability estimate: what the wallet paid on average.
        stats.implied_win_rate = sum(entries) / len(entries)
        stats.edge_pp = (stats.win_rate - stats.implied_win_rate) * 100.0
    return stats


class AllocationEngine:
    """Decides which wallets to follow now, and how much to risk on each."""

    def __init__(self, session: Session, settings: Settings | None = None,
                 *, now: datetime | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.now = now or datetime.now(timezone.utc)

    def evaluate_all(self, *, min_lifetime_trades: int = 10) -> list[AllocationState]:
        """Rank every wallet by current followability, best first."""
        states: list[AllocationState] = []
        for wallet in self.session.scalars(select(Wallet)):
            state = self.evaluate(wallet, min_lifetime_trades=min_lifetime_trades)
            if state is not None:
                states.append(state)

        # Followable stances first, then by form score.
        order = {
            Stance.FOLLOW: 0, Stance.PROBATION: 1, Stance.WATCH: 2,
            Stance.PAUSE: 3, Stance.DROP: 4,
        }
        states.sort(key=lambda s: (order[s.stance], -s.form_score))
        return states

    def evaluate(
        self, wallet: Wallet, *, min_lifetime_trades: int = 10
    ) -> AllocationState | None:
        rows = self.session.execute(
            select(
                ReconstructedPosition.opened_at,
                ReconstructedPosition.net_pnl,
                ReconstructedPosition.capital_committed,
                ReconstructedPosition.is_win,
                ReconstructedPosition.avg_entry_price,
            )
            .where(
                ReconstructedPosition.wallet_id == wallet.id,
                ReconstructedPosition.is_tennis.is_(True),
                ReconstructedPosition.status.in_(("closed", "settled")),
                ReconstructedPosition.is_win.is_not(None),
            )
            .order_by(ReconstructedPosition.opened_at)
        ).all()
        if len(rows) < min_lifetime_trades:
            return None

        first_at, last_at = rows[0][0], rows[-1][0]
        days_since = max((self.now - last_at).days, 0)
        span = max((last_at - first_at).days, 1)

        state = AllocationState(
            wallet_id=wallet.id,
            address=wallet.address,
            stance=Stance.WATCH,
            days_since_last_trade=days_since,
            active_span_days=span,
            trades_per_day=len(rows) / span,
        )

        state.lifetime = _window(rows)
        state.form = _window(
            [r for r in rows if (self.now - r[0]).days <= FORM_WINDOW_DAYS]
        )
        state.prior = _window(
            [
                r for r in rows
                if FORM_WINDOW_DAYS < (self.now - r[0]).days <= PRIOR_WINDOW_DAYS
            ]
        )
        if state.form.measured and state.prior.measured:
            state.trend_pp = state.form.mean_pct - state.prior.mean_pct

        sizes = [float(r[2]) for r in rows if r[2] and float(r[2]) > 0]
        state.median_position_usdc = statistics.median(sizes) if sizes else 0.0

        pnls = [float(r[1]) for r in rows if r[1] is not None]
        gains = [p for p in pnls if p > 0]
        if gains and sum(gains) > 0:
            state.concentration = max(gains) / sum(gains)

        self._assign_stance(state)
        self._score_form(state)
        self._suggest_size(state)
        return state

    # ---------------------------------------------------------------- stance
    def _assign_stance(self, state: AllocationState) -> None:
        """Liveness first, then form. Silence overrides every other signal."""
        if state.days_since_last_trade > MAX_SILENCE_DAYS:
            state.stance = Stance.DROP
            state.reasons.append(
                f"no tennis trade for {state.days_since_last_trade} days -- "
                "not followable regardless of past record"
            )
            return

        # Prefer the recent window; fall back to lifetime when it is too thin.
        current = state.form if state.form.measured else state.lifetime
        basis = "last 30d" if state.form.measured else "lifetime"

        if current.mean_pct <= 0:
            state.stance = Stance.PAUSE
            state.reasons.append(
                f"active, but {basis} return is {current.mean_pct:+.2f}% per trade"
            )
            return

        state.reasons.append(
            f"active ({state.days_since_last_trade}d ago), {basis} "
            f"{current.mean_pct:+.2f}% per trade over {current.trades} trades"
        )

        deteriorating = state.trend_pp is not None and state.trend_pp < -5.0
        thin = state.lifetime.trades < MIN_TRADES_FOR_SIZING

        if thin:
            state.stance = Stance.WATCH
            state.reasons.append(
                f"only {state.lifetime.trades} completed trades -- watch and paper-trade "
                f"before sizing (floor is {MIN_TRADES_FOR_SIZING})"
            )
        elif deteriorating:
            state.stance = Stance.PROBATION
            state.warnings.append(
                f"form is deteriorating: {state.trend_pp:+.2f}pp versus the prior window"
            )
        elif not state.form.measured:
            state.stance = Stance.PROBATION
            state.reasons.append(
                f"fewer than {MIN_FORM_TRADES} trades in the last {FORM_WINDOW_DAYS} days; "
                "ranked on lifetime record until recent activity accumulates"
            )
        else:
            state.stance = Stance.FOLLOW

        if state.trend_pp is not None and state.trend_pp > 5.0:
            state.reasons.append(f"improving: {state.trend_pp:+.2f}pp versus prior window")

    # ----------------------------------------------------------- form score
    def _score_form(self, state: AllocationState) -> None:
        """0-100 ranking of current followability.

        Deliberately simple and readable. Every term is something an operator can
        check by hand, because a score nobody can audit is a score nobody should
        act on.
        """
        if state.stance is Stance.DROP:
            state.form_score = 0.0
            return

        current = state.form if state.form.measured else state.lifetime

        # Return per trade, mapped so +20% per trade reaches full marks.
        ret = max(0.0, min(100.0, (current.mean_pct / 20.0) * 100.0))
        # Edge over the market's own price: the price-independent skill measure.
        edge = max(0.0, min(100.0, (current.edge_pp / 15.0) * 100.0))
        # Sample: 100 trades for full confidence.
        sample = max(0.0, min(100.0, (state.lifetime.trades / 100.0) * 100.0))
        # Longevity: a 180-day active span earns full marks. This is what
        # separates a durable edge from a ten-day run.
        longevity = max(0.0, min(100.0, (state.active_span_days / 180.0) * 100.0))
        # Freshness: full marks for trading today, decaying to zero at the gate.
        freshness = max(
            0.0, 100.0 * (1.0 - state.days_since_last_trade / MAX_SILENCE_DAYS)
        )
        # Trend, centred: flat scores 50, +10pp scores 100.
        trend = 50.0 if state.trend_pp is None else max(
            0.0, min(100.0, 50.0 + state.trend_pp * 5.0)
        )

        state.form_score = (
            0.30 * ret
            + 0.20 * edge
            + 0.15 * sample
            + 0.15 * longevity
            + 0.10 * freshness
            + 0.10 * trend
        )

    # ------------------------------------------------------------- sizing
    def _suggest_size(self, state: AllocationState) -> None:
        """Fraction of the configured paper stake to risk.

        Sample size and volatility scale the stake down rather than excluding the
        wallet. This is where thin evidence belongs: a promising 27-trade wallet
        gets a small position, not a rejection.
        """
        if state.stance in (Stance.DROP, Stance.PAUSE):
            state.suggested_stake_fraction = 0.0
            return
        if state.stance is Stance.WATCH:
            state.suggested_stake_fraction = 0.0
            state.reasons.append("paper only: no stake until the sample grows")
            return

        fraction = min(1.0, state.lifetime.trades / 100.0)
        if state.stance is Stance.PROBATION:
            fraction *= 0.5

        # A strategy whose profit rides on one trade needs a smaller position,
        # not a lower rank -- the shape is legitimate, the variance is still real.
        if state.concentration is not None and state.concentration > 0.4:
            fraction *= 0.6
            state.warnings.append(
                f"{state.concentration:.0%} of profit came from one trade; "
                "sized down for variance, not penalised in the ranking"
            )

        # A very high win rate at high prices means rare, large losses. Size for
        # the loss that has not happened yet.
        if state.lifetime.win_rate > 0.9 and state.lifetime.implied_win_rate > 0.85:
            fraction *= 0.5
            state.warnings.append(
                f"buys at ~${state.lifetime.implied_win_rate:.2f} with a "
                f"{state.lifetime.win_rate:.0%} win rate -- rare large losses are "
                "under-sampled; sized down"
            )

        state.suggested_stake_fraction = round(max(0.0, min(1.0, fraction)), 3)


def rotation_report(session: Session, settings: Settings | None = None) -> dict:
    """Who to start following, who to stop. The operational summary."""
    engine = AllocationEngine(session, settings)
    states = engine.evaluate_all()

    by_stance: dict[str, list[dict]] = {}
    for state in states:
        by_stance.setdefault(state.stance.value, []).append(state.as_dict())

    follow = by_stance.get(Stance.FOLLOW.value, [])
    return {
        "generated_at": engine.now.isoformat(),
        "follow": follow,
        "probation": by_stance.get(Stance.PROBATION.value, []),
        "watch": by_stance.get(Stance.WATCH.value, []),
        "pause": by_stance.get(Stance.PAUSE.value, []),
        "drop": by_stance.get(Stance.DROP.value, []),
        "summary": {
            "evaluated": len(states),
            "followable": len(follow),
            "dropped_for_silence": sum(
                1 for s in states
                if s.stance is Stance.DROP and s.days_since_last_trade > MAX_SILENCE_DAYS
            ),
        },
        "note": (
            "Ranks current followability, not lifetime quality. A wallet silent for "
            f"more than {MAX_SILENCE_DAYS} days is dropped whatever its record. "
            "Stances are candidates to paper-trade, not recommendations to bet."
        ),
    }
