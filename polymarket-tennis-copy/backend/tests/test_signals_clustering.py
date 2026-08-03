"""Clustering, consensus and alert-qualification tests.

The pivotal assertion: three behaviourally identical wallets must NOT satisfy a
consensus alert, because they represent one opinion.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import (
    ClusterRelation,
    MarketPhase,
    PriceSourceQuality,
    RejectionReason,
    RiskFlag,
    SignalStatus,
    SignalType,
)
from app.services.clustering import (
    WalletActivitySignature,
    WalletClusterer,
    count_independent_groups,
    deduplicate_by_cluster,
)
from app.services.notifications import (
    DeliveryResult,
    DiscordNotifier,
    NotificationDispatcher,
    Notifier,
    build_signal_notification,
)
from app.services.signals import (
    MarketConditions,
    SignalEngine,
    WalletSignalCandidate,
    group_into_consensus_windows,
)

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)
BASE_TS = int(NOW.timestamp())


def sig(wallet_id: int, tokens: dict[str, int], sizes: dict[str, str] | None = None,
        exits: dict[str, int] | None = None) -> WalletActivitySignature:
    return WalletActivitySignature(
        wallet_id=wallet_id,
        address=f"0x{wallet_id:040x}",
        entries=tokens,
        sizes={k: Decimal(v) for k, v in (sizes or {}).items()},
        exits=exits or {},
    )


class TestClustering:
    def test_identical_timing_and_markets_is_highly_correlated(self):
        tokens = {f"t{i}": BASE_TS + i * 1000 for i in range(6)}
        near = {f"t{i}": BASE_TS + i * 1000 + 20 for i in range(6)}
        sizes = {f"t{i}": "500" for i in range(6)}
        c = WalletClusterer()
        result = c.compare(sig(1, tokens, sizes), sig(2, near, sizes))
        assert result.relation is ClusterRelation.HIGHLY_CORRELATED
        assert result.timing_correlation == 1.0
        assert result.confidence > 0.7

    def test_same_markets_but_different_times_is_independent(self):
        """Trading popular markets is not evidence of coordination."""
        tokens = {f"t{i}": BASE_TS + i * 1000 for i in range(8)}
        much_later = {f"t{i}": BASE_TS + i * 1000 + 20_000 for i in range(8)}
        c = WalletClusterer()
        result = c.compare(sig(1, tokens), sig(2, much_later))
        assert result.timing_correlation == 0.0
        assert result.relation is ClusterRelation.LIKELY_INDEPENDENT

    def test_no_overlap_is_independent(self):
        c = WalletClusterer()
        result = c.compare(
            sig(1, {"a": BASE_TS}), sig(2, {"b": BASE_TS})
        )
        assert result.relation is ClusterRelation.LIKELY_INDEPENDENT
        assert result.shared_markets == 0

    def test_small_overlap_is_insufficient_evidence(self):
        c = WalletClusterer()
        result = c.compare(
            sig(1, {"a": BASE_TS, "b": BASE_TS}), sig(2, {"a": BASE_TS, "b": BASE_TS})
        )
        assert result.relation is ClusterRelation.INSUFFICIENT_EVIDENCE

    def test_coordinated_exits_recorded(self):
        tokens = {f"t{i}": BASE_TS + i * 100 for i in range(5)}
        exits = {f"t{i}": BASE_TS + 9000 + i for i in range(5)}
        c = WalletClusterer()
        result = c.compare(sig(1, tokens, exits=exits), sig(2, tokens, exits=exits))
        assert result.coordinated_exits == 5
        assert any("coordinated exits" in e for e in result.evidence)

    def test_clusters_group_transitively(self):
        tokens = {f"t{i}": BASE_TS + i * 500 for i in range(6)}
        near1 = {k: v + 10 for k, v in tokens.items()}
        near2 = {k: v + 20 for k, v in tokens.items()}
        lone = {f"z{i}": BASE_TS + i * 777 for i in range(6)}

        clusters, pairs = WalletClusterer().build_clusters(
            [sig(1, tokens), sig(2, near1), sig(3, near2), sig(4, lone)]
        )
        assert len(clusters) == 1
        assert clusters[0].wallet_ids == {1, 2, 3}
        assert 4 not in clusters[0].wallet_ids
        assert "not a claim of common ownership" in clusters[0].evidence_summary()

    def test_never_asserts_ownership(self):
        """Labels describe behaviour; the strongest is still not 'same owner'."""
        assert {r.value for r in ClusterRelation} == {
            "likely_independent", "possibly_related",
            "highly_correlated", "insufficient_evidence",
        }

    def test_independent_group_counting(self):
        # Wallets 1,2,3 share cluster 10; wallet 4 is unclustered.
        membership = {1: 10, 2: 10, 3: 10, 4: None}
        assert count_independent_groups([1, 2, 3], membership) == 1
        assert count_independent_groups([1, 2, 3, 4], membership) == 2

    def test_deduplication_keeps_one_per_cluster(self):
        membership = {1: 10, 2: 10, 3: None}
        counted, suppressed = deduplicate_by_cluster([1, 2, 3], membership)
        assert counted == [1, 3]
        assert suppressed == [2]


def candidate(
    wallet_id: int,
    *,
    offset_seconds: int = 0,
    entry: str = "0.66",
    size: str = "2000",
    skill: float = 82.0,
    copyable_roi: float | None = 0.09,
    trades: int = 60,
    qualified: bool = True,
    cluster_id: int | None = None,
    flags: list[str] | None = None,
    exiting: bool = False,
    drawdown: float = 0.15,
    data_conf: float = 92.0,
) -> WalletSignalCandidate:
    return WalletSignalCandidate(
        wallet_id=wallet_id,
        address=f"0x{wallet_id:040x}",
        nickname=None,
        traded_at=NOW - timedelta(seconds=30 - offset_seconds),
        entry_price=Decimal(entry),
        position_usdc=Decimal(size),
        skill_score=skill,
        copyable_roi=copyable_roi,
        tennis_trade_count=trades,
        qualified_wallet=qualified,
        cluster_id=cluster_id,
        risk_flags=flags or [],
        has_begun_exiting=exiting,
        max_drawdown=drawdown,
        data_confidence=data_conf,
    )


def market(
    *,
    current: str = "0.67",
    follower: str = "0.68",
    spread: str = "0.01",
    liquidity: str = "4800",
    phase: str = MarketPhase.PREMATCH,
    classification: float = 100.0,
    closed: bool = False,
    accepting: bool = True,
    copyability: float = 81.0,
) -> MarketConditions:
    return MarketConditions(
        token_id="tok1",
        condition_id="0xcond",
        market_id=1,
        outcome_label="Player A",
        current_price=Decimal(current),
        estimated_follower_price=Decimal(follower),
        spread=Decimal(spread),
        available_liquidity=Decimal(liquidity),
        market_phase=phase,
        classification_confidence=classification,
        closed=closed,
        accepting_orders=accepting,
        copyability_score=copyability,
        price_source_quality=PriceSourceQuality.OBSERVED_TRADE,
    )


class TestSingleWalletQualification:
    def test_good_single_wallet_qualifies(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market())
        assert ev.qualified is True
        assert ev.status is SignalStatus.QUALIFIED
        assert ev.signal_type is SignalType.SINGLE_WALLET
        assert ev.rejection_reasons == []
        assert all(c["passed"] for c in ev.checks)

    def test_unqualified_wallet_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, qualified=False)], market())
        assert ev.qualified is False
        assert RejectionReason.WALLET_NOT_QUALIFIED in ev.rejection_reasons

    def test_insufficient_trade_count_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, trades=12)], market())
        assert RejectionReason.INSUFFICIENT_TRADES in ev.rejection_reasons

    def test_low_skill_score_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, skill=60.0)], market())
        assert RejectionReason.LOW_SKILL_SCORE in ev.rejection_reasons

    def test_negative_copyable_roi_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, copyable_roi=-0.02)], market())
        assert RejectionReason.NEGATIVE_COPYABLE_ROI in ev.rejection_reasons

    def test_price_moved_too_far_rejected(self):
        """Entry 0.66, follower price 0.76 -- the edge is already gone."""
        ev = SignalEngine(now=NOW).evaluate(
            [candidate(1, entry="0.66")], market(current="0.75", follower="0.76")
        )
        assert RejectionReason.PRICE_MOVED_TOO_FAR in ev.rejection_reasons
        assert ev.price_deterioration == Decimal("0.10")

    def test_thin_liquidity_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market(liquidity="100"))
        assert RejectionReason.INSUFFICIENT_LIQUIDITY in ev.rejection_reasons

    def test_wide_spread_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market(spread="0.12"))
        assert RejectionReason.SPREAD_TOO_WIDE in ev.rejection_reasons

    def test_low_copyability_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market(copyability=30.0))
        assert RejectionReason.LOW_COPYABILITY in ev.rejection_reasons

    def test_ambiguous_classification_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market(classification=45.0))
        assert RejectionReason.AMBIGUOUS_CLASSIFICATION in ev.rejection_reasons
        assert RiskFlag.AMBIGUOUS_CLASSIFICATION in ev.risk_flags

    def test_closed_market_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market(closed=True))
        assert RejectionReason.MARKET_CLOSED in ev.rejection_reasons

    def test_wallet_already_exiting_rejected(self):
        """Copying a wallet that is selling is backwards."""
        ev = SignalEngine(now=NOW).evaluate([candidate(1, exiting=True)], market())
        assert RejectionReason.WALLET_ALREADY_EXITING in ev.rejection_reasons

    def test_market_making_wallet_rejected(self):
        ev = SignalEngine(now=NOW).evaluate(
            [candidate(1, flags=[RiskFlag.LIKELY_MARKET_MAKING])], market()
        )
        assert RejectionReason.MARKET_MAKING_BEHAVIOUR in ev.rejection_reasons

    def test_stale_live_signal_rejected(self):
        old = candidate(1)
        old.traded_at = NOW - timedelta(seconds=300)
        ev = SignalEngine(now=NOW).evaluate([old], market(phase=MarketPhase.LIVE))
        assert RejectionReason.SIGNAL_TOO_OLD in ev.rejection_reasons

    def test_prematch_tolerates_longer_age_than_live(self):
        old = candidate(1)
        old.traded_at = NOW - timedelta(seconds=300)
        pre = SignalEngine(now=NOW).evaluate([old], market(phase=MarketPhase.PREMATCH))
        assert RejectionReason.SIGNAL_TOO_OLD not in pre.rejection_reasons

    def test_tiny_position_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, size="20")], market())
        assert RejectionReason.POSITION_TOO_SMALL in ev.rejection_reasons

    def test_low_data_confidence_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, data_conf=40.0)], market())
        assert RejectionReason.LOW_DATA_CONFIDENCE in ev.rejection_reasons

    def test_excessive_drawdown_rejected(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, drawdown=0.75)], market())
        assert RejectionReason.EXCESSIVE_DRAWDOWN in ev.rejection_reasons

    def test_every_check_is_recorded_even_when_passing(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market())
        names = {c["check"] for c in ev.checks}
        for expected in (
            "market_open", "liquidity", "spread", "price_deterioration",
            "signal_age", "wallets_still_holding", "copyability", "skill_score",
        ):
            assert expected in names


class TestConsensus:
    def test_three_independent_wallets_qualify(self):
        candidates = [
            candidate(1, offset_seconds=0, entry="0.66"),
            candidate(2, offset_seconds=20, entry="0.68"),
            candidate(3, offset_seconds=42, entry="0.70"),
        ]
        ev = SignalEngine(now=NOW).evaluate(
            candidates, market(), cluster_membership={1: None, 2: None, 3: None}
        )
        assert ev.signal_type is SignalType.CONSENSUS
        assert ev.qualified is True
        assert ev.independent_cluster_count == 3
        assert ev.consensus_score is not None and ev.consensus_score > 60
        assert ev.wallet_entry_price_min == Decimal("0.66")
        assert ev.wallet_entry_price_max == Decimal("0.70")

    def test_three_related_wallets_do_not_qualify(self):
        """The pivotal case: one trader across three addresses is one opinion."""
        candidates = [
            candidate(1, offset_seconds=0, cluster_id=99),
            candidate(2, offset_seconds=5, cluster_id=99),
            candidate(3, offset_seconds=9, cluster_id=99),
        ]
        ev = SignalEngine(now=NOW).evaluate(
            candidates, market(), cluster_membership={1: 99, 2: 99, 3: 99}
        )
        assert ev.independent_cluster_count == 1
        assert len(ev.counted_wallet_ids) == 1
        assert len(ev.suppressed_wallet_ids) == 2
        assert ev.qualified is False
        assert RejectionReason.CLUSTERED_WALLETS in ev.rejection_reasons
        assert RiskFlag.SUSPECTED_RELATED_WALLET in ev.risk_flags
        assert "suppressed as behaviourally related" in ev.explanation
        # Must stay typed as consensus so the independence check actually runs,
        # rather than silently downgrading to the laxer single-wallet path.
        assert ev.signal_type is SignalType.CONSENSUS
        assert "not consensus" in ev.explanation

    def test_clustered_group_cannot_downgrade_to_single_wallet_alert(self):
        """Regression: dedup collapsing to 1 must not bypass consensus rules."""
        candidates = [
            candidate(1, offset_seconds=0, cluster_id=99, skill=95.0, trades=500),
            candidate(2, offset_seconds=5, cluster_id=99, skill=95.0, trades=500),
        ]
        ev = SignalEngine(now=NOW).evaluate(
            candidates, market(), cluster_membership={1: 99, 2: 99}
        )
        # Even with excellent individual wallets, a collapsed consensus fails.
        assert len(ev.counted_wallet_ids) == 1
        assert ev.signal_type is SignalType.CONSENSUS
        assert ev.qualified is False
        assert RejectionReason.CLUSTERED_WALLETS in ev.rejection_reasons

    def test_partially_clustered_consensus_counts_correctly(self):
        """Two related + two independent = three opinions, not four."""
        candidates = [
            candidate(1, offset_seconds=0, cluster_id=7),
            candidate(2, offset_seconds=5, cluster_id=7),
            candidate(3, offset_seconds=15),
            candidate(4, offset_seconds=25),
        ]
        ev = SignalEngine(now=NOW).evaluate(
            candidates, market(),
            cluster_membership={1: 7, 2: 7, 3: None, 4: None},
        )
        assert ev.independent_cluster_count == 3
        assert len(ev.counted_wallet_ids) == 3
        assert ev.qualified is True

    def test_entries_spread_too_far_apart_rejected(self):
        candidates = [
            candidate(1, offset_seconds=0),
            candidate(2, offset_seconds=0),
            candidate(3, offset_seconds=0),
        ]
        candidates[2].traded_at = NOW - timedelta(seconds=600)
        ev = SignalEngine(now=NOW).evaluate(
            candidates, market(), cluster_membership={1: None, 2: None, 3: None}
        )
        assert RejectionReason.INSUFFICIENT_CONSENSUS in ev.rejection_reasons

    def test_consensus_window_grouping(self):
        candidates = [
            candidate(1, offset_seconds=0),
            candidate(2, offset_seconds=30),
            candidate(3, offset_seconds=31),
        ]
        candidates[2].traded_at = NOW + timedelta(seconds=500)
        groups = group_into_consensus_windows(candidates, 90)
        assert len(groups) == 2
        assert len(groups[0]) == 2

    def test_consensus_score_rewards_independence(self):
        engine = SignalEngine(now=NOW)
        independent = engine.evaluate(
            [candidate(i, offset_seconds=i * 5) for i in (1, 2, 3)],
            market(), cluster_membership={1: None, 2: None, 3: None},
        )
        clustered = engine.evaluate(
            [candidate(i, offset_seconds=i * 5, cluster_id=5) for i in (1, 2, 3)],
            market(), cluster_membership={1: 5, 2: 5, 3: 5},
        )
        assert independent.consensus_score > (clustered.consensus_score or 0)

    def test_dedupe_key_is_stable_and_distinct(self):
        engine = SignalEngine(now=NOW)
        a = engine.evaluate([candidate(1)], market())
        b = engine.evaluate([candidate(1)], market())
        c = engine.evaluate([candidate(2)], market())
        assert a.dedupe_key == b.dedupe_key
        assert a.dedupe_key != c.dedupe_key


class TestEdgeEstimate:
    def test_edge_is_labelled_heuristic(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1)], market())
        assert ev.edge_method == "heuristic_v1"
        assert "not a calibrated probability" in ev.explanation

    def test_edge_is_damped_below_historical_roi(self):
        """Past copyable ROI is evidence, not a forecast of this trade."""
        ev = SignalEngine(now=NOW).evaluate([candidate(1, copyable_roi=0.20)], market())
        assert ev.estimated_edge is not None
        assert ev.estimated_edge < 0.20

    def test_price_deterioration_reduces_edge(self):
        engine = SignalEngine(now=NOW)
        tight = engine.evaluate([candidate(1, entry="0.66")], market(follower="0.665"))
        wide = engine.evaluate([candidate(1, entry="0.66")], market(follower="0.69"))
        assert wide.estimated_edge < tight.estimated_edge

    def test_no_edge_without_copyable_history(self):
        ev = SignalEngine(now=NOW).evaluate([candidate(1, copyable_roi=None)], market())
        assert ev.estimated_edge is None


class TestNotifications:
    def test_alert_contains_every_required_field(self):
        n = build_signal_notification(
            signal_type="consensus", market_title="DC Open: A vs B",
            outcome_label="Player A", wallet_count=3, independent_groups=2,
            wallet_entry_min=Decimal("0.66"), wallet_entry_max=Decimal("0.70"),
            current_price=Decimal("0.71"), follower_price=Decimal("0.72"),
            price_deterioration=Decimal("0.02"), liquidity=Decimal("4800"),
            spread=Decimal("0.01"), median_copyable_roi=0.087,
            copyability_score=81.0, consensus_score=87.0, skill_score=84.0,
            estimated_edge=0.04, sample_size=142, signal_age_seconds=42,
            data_confidence=91.0, risk_flags=["fast_moving_market"],
            explanation="Three wallets bought within 42s.",
            market_phase="live",
        )
        for required in (
            "Market", "Outcome", "Wallets", "Wallet entry", "Current price",
            "Est. follower price", "Price deterioration", "Liquidity", "Spread",
            "Median copyable ROI", "Copyability", "Skill score",
            "Consensus score", "Sample size", "Signal age", "Data confidence",
            "Risk flags", "Market status",
        ):
            assert required in n.payload, f"missing {required}"

    def test_no_hype_language_anywhere(self):
        """The spec bans guarantee language; check the rendered alert."""
        n = build_signal_notification(
            signal_type="single", market_title="M", outcome_label="A",
            wallet_count=1, independent_groups=1,
            wallet_entry_min=Decimal("0.5"), wallet_entry_max=Decimal("0.5"),
            current_price=Decimal("0.5"), follower_price=Decimal("0.51"),
            price_deterioration=Decimal("0.01"), liquidity=Decimal("1000"),
            spread=Decimal("0.01"), median_copyable_roi=0.05,
            copyability_score=80.0, consensus_score=None, skill_score=80.0,
            estimated_edge=0.02, sample_size=50, signal_age_seconds=10,
            data_confidence=90.0, risk_flags=[], explanation="Qualified entry.",
            market_phase="prematch",
        )
        text = (n.title + n.body + n.payload_json()).lower()
        for banned in (
            "guaranteed", "lock", "risk-free", "risk free", "can't lose",
            "cannot lose", "free money", "sure thing",
        ):
            assert banned not in text, f"found banned phrasing: {banned}"

    def test_unconfigured_channels_are_skipped(self):
        d = DiscordNotifier(webhook_url=None)
        assert d.is_configured() is False
        result = d.send(
            build_daily := __import__(
                "app.services.notifications", fromlist=["build_daily_summary_notification"]
            ).build_daily_summary_notification({"pnl": "0"})
        )
        assert result.delivered is False
        assert "not configured" in (result.error or "")

    def test_dispatcher_isolates_channel_failures(self):
        """One broken channel must not stop the others."""

        class Boom(Notifier):
            channel = "boom"

            def is_configured(self) -> bool:
                return True

            def send(self, notification) -> DeliveryResult:
                return DeliveryResult(self.channel, False, "exploded")

        class Fine(Notifier):
            channel = "fine"

            def is_configured(self) -> bool:
                return True

            def send(self, notification) -> DeliveryResult:
                return DeliveryResult(self.channel, True)

        from app.services.notifications import build_pipeline_failure_notification

        dispatcher = NotificationDispatcher([Boom(), Fine()])
        dispatcher.enabled = True
        results = dispatcher.dispatch(build_pipeline_failure_notification("x", "y"))
        assert {r.channel: r.delivered for r in results} == {"boom": False, "fine": True}

    def test_disclaimer_present_in_alert(self):
        from app.services.notifications import DISCLAIMER

        assert "not financial advice" in DISCLAIMER.lower()
        assert "do not guarantee" in DISCLAIMER.lower()
