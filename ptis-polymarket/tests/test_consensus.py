import unittest

from ptis.consensus import (
    filter_prior_directional_buys,
    find_consensus_signals,
)


class ConsensusTests(unittest.TestCase):
    def test_requires_distinct_wallets_and_ignores_trade_size(self) -> None:
        rows = [
            ("0xaaa", "c1", "yes", 0.50, "2026-01-01T00:00:00Z"),
            ("0xaaa", "c1", "yes", 0.51, "2026-01-01T00:01:00Z"),
            ("0xbbb", "c1", "yes", 0.52, "2026-01-01T00:02:00Z"),
        ]
        signals = find_consensus_signals(
            rows, minimum_agreement=2, agreement_window_seconds=3600
        )
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].agreeing_wallets, ("0xaaa", "0xbbb"))
        self.assertAlmostEqual(signals[0].reference_price, 0.515)

    def test_old_votes_expire(self) -> None:
        rows = [
            ("0xaaa", "c1", "yes", 0.50, "2026-01-01T00:00:00Z"),
            ("0xbbb", "c1", "yes", 0.52, "2026-01-01T02:00:00Z"),
        ]
        self.assertEqual(
            find_consensus_signals(
                rows, minimum_agreement=2, agreement_window_seconds=3600
            ),
            [],
        )

    def test_opposing_consensus_is_rejected(self) -> None:
        rows = [
            ("0xaaa", "c1", "yes", 0.50, "2026-01-01T00:00:00Z"),
            ("0xbbb", "c1", "yes", 0.52, "2026-01-01T00:01:00Z"),
            ("0xccc", "c1", "no", 0.48, "2026-01-01T00:02:00Z"),
            ("0xddd", "c1", "no", 0.49, "2026-01-01T00:03:00Z"),
        ]
        self.assertEqual(
            find_consensus_signals(
                rows, minimum_agreement=2, agreement_window_seconds=3600
            ),
            [],
        )

    def test_first_threshold_crossing_is_used(self) -> None:
        rows = [
            ("0xaaa", "c1", "yes", 0.40, "2026-01-01T00:00:00Z"),
            ("0xbbb", "c1", "yes", 0.50, "2026-01-01T00:01:00Z"),
            ("0xccc", "c1", "yes", 0.80, "2026-01-01T00:02:00Z"),
        ]
        signals = find_consensus_signals(
            rows, minimum_agreement=2, agreement_window_seconds=3600
        )
        self.assertEqual(signals[0].signal_at_utc, "2026-01-01T00:01:00Z")
        self.assertAlmostEqual(signals[0].reference_price, 0.45)

    def test_directional_gate_uses_only_prior_behavior(self) -> None:
        rows = [
            (
                "0xaaa",
                f"c{index}",
                f"t{index}",
                "BUY",
                0.5,
                f"2026-01-01T00:00:{index:02d}Z",
            )
            for index in range(31)
        ]
        accepted = filter_prior_directional_buys(rows)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0][1], "c30")

    def test_rapid_reverser_cannot_vote(self) -> None:
        rows = []
        for index in range(30):
            rows.append(
                (
                    "0xaaa",
                    "c1",
                    "t1",
                    "BUY" if index % 2 == 0 else "SELL",
                    0.5,
                    f"2026-01-01T00:{index:02d}:00Z",
                )
            )
        rows.append(
            ("0xaaa", "c2", "t2", "BUY", 0.5, "2026-01-01T00:31:00Z")
        )
        self.assertEqual(filter_prior_directional_buys(rows), [])
