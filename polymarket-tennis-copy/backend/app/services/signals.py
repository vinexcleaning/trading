"""Signal detection, consensus, and alert qualification.

Three ideas drive this module:

1. **Not every wallet trade is a signal.** Candidates must clear a long list of
   configurable minimums. Rejections are recorded with reasons rather than
   discarded, because the rejection log is how an operator calibrates trust in
   the thresholds.

2. **Consensus counts opinions, not addresses.** Wallets in the same behavioural
   cluster collapse to one vote (see :mod:`clustering`), so a single trader
   splitting across three addresses cannot manufacture the strongest signal.

3. **Edge is a heuristic, and is labelled as one.** No calibrated probability
   model exists in v1. The estimate here is a transparent blend of wallet
   quality, agreement and price context, and it is stored with its method name so
   nobody mistakes it for a fitted probability.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..config import Settings, get_settings
from ..enums import (
    MarketPhase,
    PriceSourceQuality,
    RejectionReason,
    RiskFlag,
    SignalStatus,
    SignalType,
)
from ..logging_setup import get_logger

log = get_logger(__name__)

ZERO = Decimal("0")
EDGE_METHOD = "heuristic_v1"


@dataclass(slots=True)
class WalletSignalCandidate:
    """One wallet's contribution to a potential signal."""

    wallet_id: int
    address: str
    nickname: str | None
    traded_at: datetime
    entry_price: Decimal
    position_usdc: Decimal
    skill_score: float
    copyable_roi: float | None
    tennis_trade_count: int
    qualified_wallet: bool
    cluster_id: int | None = None
    risk_flags: list[str] = field(default_factory=list)
    is_position_increase: bool = False
    has_begun_exiting: bool = False
    position_id: int | None = None
    max_drawdown: float | None = None
    data_confidence: float = 0.0


@dataclass(slots=True)
class MarketConditions:
    """Live market state at evaluation time."""

    token_id: str
    condition_id: str | None
    market_id: int | None
    outcome_label: str | None
    current_price: Decimal | None
    estimated_follower_price: Decimal | None
    spread: Decimal | None
    available_liquidity: Decimal | None
    market_phase: str
    classification_confidence: float
    closed: bool
    accepting_orders: bool
    price_source_quality: PriceSourceQuality = PriceSourceQuality.UNAVAILABLE
    copyability_score: float | None = None
    game_start_time: datetime | None = None


@dataclass
class SignalEvaluation:
    """Result of evaluating a candidate signal."""

    signal_type: SignalType
    status: SignalStatus
    qualified: bool
    dedupe_key: str

    wallets: list[WalletSignalCandidate] = field(default_factory=list)
    counted_wallet_ids: list[int] = field(default_factory=list)
    suppressed_wallet_ids: list[int] = field(default_factory=list)
    independent_cluster_count: int = 0

    wallet_entry_price_min: Decimal | None = None
    wallet_entry_price_max: Decimal | None = None
    wallet_entry_price_median: Decimal | None = None
    price_deterioration: Decimal | None = None
    total_wallet_position_usdc: Decimal | None = None

    median_skill_score: float | None = None
    median_copyable_roi: float | None = None
    copyability_score: float | None = None
    consensus_score: float | None = None
    estimated_edge: float | None = None
    edge_method: str = EDGE_METHOD
    data_confidence: float | None = None

    signal_age_seconds: int | None = None
    expires_at: datetime | None = None
    market_phase: str = MarketPhase.UNKNOWN

    rejection_reasons: list[RejectionReason] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    explanation: str = ""

    def rejection_json(self) -> str | None:
        return (
            json.dumps([r.value for r in self.rejection_reasons])
            if self.rejection_reasons
            else None
        )

    def risk_flags_json(self) -> str | None:
        return json.dumps(sorted(set(self.risk_flags))) if self.risk_flags else None

    def checks_json(self) -> str:
        return json.dumps(self.checks, default=str)


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")


def _median_float(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def make_dedupe_key(
    signal_type: SignalType, token_id: str, wallet_ids: list[int], bucket_ts: int
) -> str:
    """Stable identity for a signal.

    Timestamps are bucketed so that the same underlying wallet action observed on
    consecutive scheduler ticks maps to one signal rather than a stream of
    near-duplicates.
    """
    payload = f"{signal_type.value}|{token_id}|{sorted(wallet_ids)}|{bucket_ts}"
    return hashlib.sha256(payload.encode()).hexdigest()[:40]


class SignalEngine:
    """Builds and qualifies signals from wallet activity."""

    def __init__(self, settings: Settings | None = None, *, now: datetime | None = None) -> None:
        self.settings = settings or get_settings()
        self.now = now or datetime.now(timezone.utc)

    # ------------------------------------------------------------ evaluation
    def evaluate(
        self,
        candidates: list[WalletSignalCandidate],
        market: MarketConditions,
        *,
        cluster_membership: dict[int, int | None] | None = None,
        signal_type: SignalType | None = None,
    ) -> SignalEvaluation:
        from .clustering import count_independent_groups, deduplicate_by_cluster

        s = self.settings
        membership = cluster_membership or {
            c.wallet_id: c.cluster_id for c in candidates
        }

        if not candidates:
            raise ValueError("evaluate() requires at least one candidate wallet")

        wallet_ids = [c.wallet_id for c in candidates]
        counted, suppressed = deduplicate_by_cluster(wallet_ids, membership)
        independent = count_independent_groups(wallet_ids, membership)

        # Type is decided by what was *observed*, not by what survived
        # de-duplication. If several wallets entered the same outcome, this is a
        # consensus candidate and must satisfy the consensus rules -- including
        # independence. Typing it from the post-dedup count would let three
        # related wallets collapse to one and quietly re-qualify under the laxer
        # single-wallet path, bypassing the very check meant to catch them.
        resolved_type = signal_type or (
            SignalType.CONSENSUS if len(candidates) > 1 else SignalType.SINGLE_WALLET
        )

        first_trade = min(c.traded_at for c in candidates)
        last_trade = max(c.traded_at for c in candidates)
        age = int((self.now - first_trade).total_seconds())

        entry_prices = [c.entry_price for c in candidates]
        # Only wallets that actually count contribute to the quality medians.
        counted_candidates = [c for c in candidates if c.wallet_id in counted]

        ev = SignalEvaluation(
            signal_type=resolved_type,
            status=SignalStatus.EVALUATING,
            qualified=False,
            dedupe_key=make_dedupe_key(
                resolved_type,
                market.token_id,
                counted,
                # 60-second buckets.
                int(first_trade.timestamp()) // 60,
            ),
            wallets=candidates,
            counted_wallet_ids=counted,
            suppressed_wallet_ids=suppressed,
            independent_cluster_count=independent,
            wallet_entry_price_min=min(entry_prices),
            wallet_entry_price_max=max(entry_prices),
            wallet_entry_price_median=_median(entry_prices),
            total_wallet_position_usdc=sum((c.position_usdc for c in candidates), ZERO),
            median_skill_score=_median_float([c.skill_score for c in counted_candidates]),
            median_copyable_roi=_median_float(
                [c.copyable_roi for c in counted_candidates if c.copyable_roi is not None]
            ),
            copyability_score=market.copyability_score,
            signal_age_seconds=age,
            market_phase=market.market_phase,
            data_confidence=(
                sum(c.data_confidence for c in counted_candidates) / len(counted_candidates)
                if counted_candidates
                else 0.0
            ),
        )

        reference = ev.wallet_entry_price_median or ev.wallet_entry_price_min
        follower_price = market.estimated_follower_price or market.current_price
        if reference is not None and follower_price is not None:
            ev.price_deterioration = follower_price - reference

        ev.expires_at = self._expiry(first_trade, market.market_phase)
        ev.estimated_edge = self._estimate_edge(ev, market)

        for c in candidates:
            ev.risk_flags.extend(c.risk_flags)
        if suppressed:
            ev.risk_flags.append(RiskFlag.SUSPECTED_RELATED_WALLET)
        if market.classification_confidence < 70:
            ev.risk_flags.append(RiskFlag.AMBIGUOUS_CLASSIFICATION)
        if market.market_phase == MarketPhase.LIVE:
            ev.risk_flags.append(RiskFlag.FAST_MOVING_MARKET)

        self._run_checks(ev, market)

        ev.qualified = not ev.rejection_reasons
        ev.status = SignalStatus.QUALIFIED if ev.qualified else SignalStatus.REJECTED
        if ev.qualified and age > (
            s.alert_max_age_live_seconds
            if market.market_phase == MarketPhase.LIVE
            else s.alert_max_age_prematch_seconds
        ):
            ev.status = SignalStatus.EXPIRED

        ev.explanation = self._explain(ev, market)
        ev.risk_flags = sorted(set(ev.risk_flags))
        return ev

    # ---------------------------------------------------------------- checks
    def _check(
        self,
        ev: SignalEvaluation,
        name: str,
        passed: bool,
        *,
        value: object,
        threshold: object,
        reason: RejectionReason | None,
        detail: str = "",
    ) -> None:
        """Record a threshold check and its verdict.

        Every check is stored whether it passes or fails, so the UI can show the
        full decision, not only the first failure.
        """
        ev.checks.append(
            {
                "check": name,
                "passed": passed,
                "value": value,
                "threshold": threshold,
                "detail": detail,
            }
        )
        if not passed and reason is not None and reason not in ev.rejection_reasons:
            ev.rejection_reasons.append(reason)

    def _run_checks(self, ev: SignalEvaluation, market: MarketConditions) -> None:
        s = self.settings
        is_live = market.market_phase == MarketPhase.LIVE
        is_consensus = ev.signal_type is SignalType.CONSENSUS

        # --- market tradeability -------------------------------------------
        self._check(
            ev, "market_open", not market.closed,
            value=market.closed, threshold=False,
            reason=RejectionReason.MARKET_CLOSED,
        )
        self._check(
            ev, "accepting_orders", market.accepting_orders,
            value=market.accepting_orders, threshold=True,
            reason=RejectionReason.MARKET_CLOSED,
        )
        self._check(
            ev, "classification_confidence",
            market.classification_confidence >= 70.0,
            value=market.classification_confidence, threshold=70.0,
            reason=RejectionReason.AMBIGUOUS_CLASSIFICATION,
            detail="market type must be unambiguous before acting on it",
        )

        # --- wallet quality (every counted wallet must qualify) -------------
        counted = [c for c in ev.wallets if c.wallet_id in ev.counted_wallet_ids]
        unqualified = [c for c in counted if not c.qualified_wallet]
        self._check(
            ev, "wallets_qualified", not unqualified,
            value=[c.address[:10] for c in unqualified], threshold="all qualified",
            reason=RejectionReason.WALLET_NOT_QUALIFIED,
        )

        min_trades = min((c.tennis_trade_count for c in counted), default=0)
        self._check(
            ev, "min_tennis_trades", min_trades >= s.alert_min_tennis_trades,
            value=min_trades, threshold=s.alert_min_tennis_trades,
            reason=RejectionReason.INSUFFICIENT_TRADES,
        )

        skill_threshold = (
            s.consensus_min_median_skill if is_consensus else s.alert_min_skill_score
        )
        self._check(
            ev, "skill_score",
            (ev.median_skill_score or 0.0) >= skill_threshold,
            value=ev.median_skill_score, threshold=skill_threshold,
            reason=RejectionReason.LOW_SKILL_SCORE,
            detail="median across independently counted wallets",
        )

        self._check(
            ev, "copyable_roi",
            ev.median_copyable_roi is not None
            and ev.median_copyable_roi > s.alert_min_copyable_roi,
            value=ev.median_copyable_roi, threshold=s.alert_min_copyable_roi,
            reason=RejectionReason.NEGATIVE_COPYABLE_ROI,
            detail=f"measured at a {s.benchmark_delay_seconds}s follower delay",
        )

        worst_dd = max((c.max_drawdown or 0.0 for c in counted), default=0.0)
        self._check(
            ev, "max_drawdown", worst_dd <= s.alert_max_drawdown,
            value=worst_dd, threshold=s.alert_max_drawdown,
            reason=RejectionReason.EXCESSIVE_DRAWDOWN,
        )

        self._check(
            ev, "data_confidence",
            (ev.data_confidence or 0.0) >= s.alert_min_data_confidence,
            value=ev.data_confidence, threshold=s.alert_min_data_confidence,
            reason=RejectionReason.LOW_DATA_CONFIDENCE,
        )

        # --- execution realism ----------------------------------------------
        max_deterioration = (
            s.consensus_max_price_deterioration
            if is_consensus
            else s.alert_max_price_deterioration
        )
        deterioration_ok = (
            ev.price_deterioration is not None
            and ev.price_deterioration <= max_deterioration
        )
        self._check(
            ev, "price_deterioration", deterioration_ok,
            value=str(ev.price_deterioration), threshold=str(max_deterioration),
            reason=RejectionReason.PRICE_MOVED_TOO_FAR,
            detail="follower price versus median wallet entry",
        )

        liquidity_ok = (
            market.available_liquidity is not None
            and market.available_liquidity >= s.alert_min_liquidity_usdc
        )
        self._check(
            ev, "liquidity", liquidity_ok,
            value=str(market.available_liquidity),
            threshold=str(s.alert_min_liquidity_usdc),
            reason=RejectionReason.INSUFFICIENT_LIQUIDITY,
        )

        spread_ok = market.spread is not None and market.spread <= s.alert_max_spread
        self._check(
            ev, "spread", spread_ok,
            value=str(market.spread), threshold=str(s.alert_max_spread),
            reason=RejectionReason.SPREAD_TOO_WIDE,
        )

        self._check(
            ev, "copyability",
            (market.copyability_score or 0.0) >= s.alert_min_copyability_score,
            value=market.copyability_score, threshold=s.alert_min_copyability_score,
            reason=RejectionReason.LOW_COPYABILITY,
        )

        self._check(
            ev, "position_size",
            (ev.total_wallet_position_usdc or ZERO) >= s.alert_min_position_usdc,
            value=str(ev.total_wallet_position_usdc),
            threshold=str(s.alert_min_position_usdc),
            reason=RejectionReason.POSITION_TOO_SMALL,
            detail="tiny wallet positions carry little conviction",
        )

        # --- timing -----------------------------------------------------------
        max_age = (
            s.alert_max_age_live_seconds if is_live else s.alert_max_age_prematch_seconds
        )
        self._check(
            ev, "signal_age", (ev.signal_age_seconds or 0) <= max_age,
            value=ev.signal_age_seconds, threshold=max_age,
            reason=RejectionReason.SIGNAL_TOO_OLD,
            detail="live markets expire far faster than prematch",
        )

        # --- wallet still in the trade ---------------------------------------
        exiting = [c for c in counted if c.has_begun_exiting]
        self._check(
            ev, "wallets_still_holding", not exiting,
            value=[c.address[:10] for c in exiting], threshold="none exiting",
            reason=RejectionReason.WALLET_ALREADY_EXITING,
            detail="copying a wallet that is already selling is backwards",
        )

        # --- behaviour exclusions --------------------------------------------
        mm = [c for c in counted if RiskFlag.LIKELY_MARKET_MAKING in c.risk_flags]
        self._check(
            ev, "no_market_making", not mm,
            value=[c.address[:10] for c in mm], threshold="none",
            reason=RejectionReason.MARKET_MAKING_BEHAVIOUR,
        )

        # --- consensus-specific ----------------------------------------------
        if is_consensus:
            self._check(
                ev, "consensus_wallet_count",
                len(ev.counted_wallet_ids) >= s.consensus_min_wallets,
                value=len(ev.counted_wallet_ids), threshold=s.consensus_min_wallets,
                reason=RejectionReason.INSUFFICIENT_CONSENSUS,
                detail="counts independent wallets, after cluster de-duplication",
            )
            self._check(
                ev, "independent_clusters",
                ev.independent_cluster_count >= s.consensus_min_independent_clusters,
                value=ev.independent_cluster_count,
                threshold=s.consensus_min_independent_clusters,
                reason=RejectionReason.CLUSTERED_WALLETS,
                detail="related wallets are not independent confirmations",
            )
            window = int(
                (
                    max(c.traded_at for c in ev.wallets)
                    - min(c.traded_at for c in ev.wallets)
                ).total_seconds()
            )
            self._check(
                ev, "consensus_window", window <= s.consensus_window_seconds,
                value=window, threshold=s.consensus_window_seconds,
                reason=RejectionReason.INSUFFICIENT_CONSENSUS,
                detail="entries must cluster in time to count as agreement",
            )
            self._check(
                ev, "median_copyability",
                (market.copyability_score or 0.0) >= s.consensus_min_median_copyability,
                value=market.copyability_score,
                threshold=s.consensus_min_median_copyability,
                reason=RejectionReason.LOW_COPYABILITY,
            )
            ev.consensus_score = self._consensus_score(ev, market)

    # ------------------------------------------------------------------ edge
    def _estimate_edge(
        self, ev: SignalEvaluation, market: MarketConditions
    ) -> float | None:
        """Heuristic edge estimate -- explicitly not a calibrated probability.

        Built from wallet track record, independent agreement, and how much price
        has already moved. A real probability model would need match state and
        player data, which v1 does not have; inventing one here would be exactly
        the false precision the spec forbids.
        """
        if ev.median_copyable_roi is None or market.estimated_follower_price is None:
            return None

        # Start from the wallets' historical copyable edge per dollar, damped:
        # past copyable ROI is evidence of an edge, not a forecast of this trade.
        base = ev.median_copyable_roi * 0.5

        # Independent agreement adds a little; correlated wallets add nothing.
        if ev.independent_cluster_count >= 3:
            base *= 1.3
        elif ev.independent_cluster_count == 2:
            base *= 1.15

        # Price already moved against the follower: that much edge is spent.
        if ev.price_deterioration is not None and ev.price_deterioration > ZERO:
            price = market.estimated_follower_price
            if price > ZERO:
                base -= float(ev.price_deterioration / price)

        # Weak data cannot support a confident edge claim.
        confidence_factor = (ev.data_confidence or 0.0) / 100.0
        return round(base * confidence_factor, 4)

    def _consensus_score(
        self, ev: SignalEvaluation, market: MarketConditions
    ) -> float:
        """0-100 strength of agreement among independent wallets."""
        s = self.settings

        # Independence matters more than headcount.
        independence = min(1.0, ev.independent_cluster_count / max(s.consensus_min_independent_clusters, 1))
        count = min(1.0, len(ev.counted_wallet_ids) / max(s.consensus_min_wallets, 1))
        skill = min(1.0, (ev.median_skill_score or 0.0) / 100.0)
        copyability = min(1.0, (market.copyability_score or 0.0) / 100.0)

        # Tight timing is stronger evidence of genuine agreement.
        window = int(
            (
                max(c.traded_at for c in ev.wallets)
                - min(c.traded_at for c in ev.wallets)
            ).total_seconds()
        )
        timing = max(0.0, 1.0 - (window / max(s.consensus_window_seconds, 1)))

        score = 100.0 * (
            0.30 * independence
            + 0.20 * count
            + 0.25 * skill
            + 0.15 * copyability
            + 0.10 * timing
        )
        return round(max(0.0, min(100.0, score)), 1)

    def _expiry(self, first_trade: datetime, phase: str) -> datetime:
        s = self.settings
        window = (
            s.alert_max_age_live_seconds
            if phase == MarketPhase.LIVE
            else s.alert_max_age_prematch_seconds
        )
        return first_trade + timedelta(seconds=window)

    # ----------------------------------------------------------- explanation
    def _explain(self, ev: SignalEvaluation, market: MarketConditions) -> str:
        parts: list[str] = []
        n = len(ev.counted_wallet_ids)

        if ev.signal_type is SignalType.CONSENSUS:
            window = int(
                (
                    max(c.traded_at for c in ev.wallets)
                    - min(c.traded_at for c in ev.wallets)
                ).total_seconds()
            )
            parts.append(
                f"{n} independently counted wallet(s) across "
                f"{ev.independent_cluster_count} unrelated group(s) bought "
                f"{market.outcome_label or 'this outcome'} within {window}s."
            )
            if ev.suppressed_wallet_ids:
                parts.append(
                    f"{len(ev.suppressed_wallet_ids)} additional wallet(s) were "
                    "suppressed as behaviourally related, so they do not count as "
                    "extra confirmation."
                )
            if n == 1:
                parts.append(
                    f"All {len(ev.wallets)} observed wallets collapsed to a single "
                    "independent opinion, so this is not consensus. Evaluate the "
                    "surviving wallet on its own merits if a single-wallet alert "
                    "is wanted."
                )
        else:
            parts.append(
                f"Single qualified wallet bought {market.outcome_label or 'this outcome'}."
            )

        if ev.wallet_entry_price_min is not None:
            if ev.wallet_entry_price_min == ev.wallet_entry_price_max:
                parts.append(f"Wallet entry: ${ev.wallet_entry_price_min}.")
            else:
                parts.append(
                    f"Wallet entry range: ${ev.wallet_entry_price_min}-"
                    f"${ev.wallet_entry_price_max}."
                )
        if market.current_price is not None:
            parts.append(f"Current price: ${market.current_price}.")
        if market.estimated_follower_price is not None:
            parts.append(f"Estimated follower price: ${market.estimated_follower_price}.")
        if ev.price_deterioration is not None:
            parts.append(f"Price deterioration: ${ev.price_deterioration}.")
        if market.available_liquidity is not None:
            parts.append(f"Available liquidity: ${market.available_liquidity:,.0f}.")
        if ev.median_copyable_roi is not None:
            parts.append(
                f"Median wallet copyable ROI at "
                f"{self.settings.benchmark_delay_seconds}s delay: "
                f"{ev.median_copyable_roi:.1%}."
            )
        if market.copyability_score is not None:
            parts.append(f"Copyability score: {market.copyability_score:.0f}/100.")
        if ev.consensus_score is not None:
            parts.append(f"Consensus score: {ev.consensus_score:.0f}/100.")
        if ev.estimated_edge is not None:
            parts.append(
                f"Heuristic edge estimate: {ev.estimated_edge:+.1%} "
                "(not a calibrated probability)."
            )
        parts.append(f"Market status: {market.market_phase}.")
        parts.append(f"Signal age: {ev.signal_age_seconds}s.")

        if ev.qualified:
            passed = [c["check"] for c in ev.checks if c["passed"]]
            parts.append(f"Qualified: passed all {len(passed)} checks.")
        else:
            failed = [c for c in ev.checks if not c["passed"]]
            parts.append(
                "Rejected: "
                + "; ".join(
                    f"{c['check']} (value {c['value']} vs threshold {c['threshold']})"
                    for c in failed
                )
                + "."
            )
        if ev.risk_flags:
            parts.append(f"Risk flags: {', '.join(sorted(set(ev.risk_flags)))}.")
        return " ".join(parts)


def group_into_consensus_windows(
    candidates: list[WalletSignalCandidate], window_seconds: int
) -> list[list[WalletSignalCandidate]]:
    """Group same-outcome entries into time-clustered batches.

    A greedy sweep in time order: a new group starts whenever the next entry
    falls outside the window from the group's first entry.
    """
    if not candidates:
        return []
    ordered = sorted(candidates, key=lambda c: c.traded_at)
    groups: list[list[WalletSignalCandidate]] = [[ordered[0]]]

    for candidate in ordered[1:]:
        anchor = groups[-1][0].traded_at
        if (candidate.traded_at - anchor).total_seconds() <= window_seconds:
            groups[-1].append(candidate)
        else:
            groups.append([candidate])
    return groups
