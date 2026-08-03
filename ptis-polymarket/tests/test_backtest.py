import unittest
from datetime import datetime, timezone

from ptis.backtest import (
    ReplayScenario,
    choose_replay_entry,
    classify_prior_behavior,
)


class HistoricalReplayTests(unittest.TestCase):
    def test_prior_classifier_requires_history_without_using_future_rows(self) -> None:
        rows = [
            (
                f"condition-{index}",
                f"token-{index}",
                "BUY",
                f"2026-01-01T00:00:{index:02d}Z",
            )
            for index in range(30)
        ]
        self.assertEqual(classify_prior_behavior(rows), "directional-candidate")
        self.assertEqual(
            classify_prior_behavior(rows[:29]),
            "insufficient-prior-history",
        )
    def test_uses_first_trade_at_or_after_follower_time(self) -> None:
        signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
        tape = [
            ("2026-01-01T00:00:03Z", 0.50),
            ("2026-01-01T00:00:05Z", 0.51),
            ("2026-01-01T00:00:06Z", 0.52),
        ]
        timestamp, fill, rejection = choose_replay_entry(
            signal_time=signal,
            original_price=0.50,
            tape_rows=tape,
            scenario=ReplayScenario(delay_seconds=5, adverse_price_offset=0),
        )
        self.assertEqual(timestamp, "2026-01-01T00:00:05Z")
        self.assertEqual(fill, 0.51)
        self.assertIsNone(rejection)

    def test_adverse_offset_can_trigger_deterioration_rejection(self) -> None:
        signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
        timestamp, fill, rejection = choose_replay_entry(
            signal_time=signal,
            original_price=0.50,
            tape_rows=[("2026-01-01T00:00:05Z", 0.51)],
            scenario=ReplayScenario(delay_seconds=5, adverse_price_offset=0.02),
        )
        self.assertEqual(timestamp, "2026-01-01T00:00:05Z")
        self.assertAlmostEqual(fill or 0, 0.53)
        self.assertEqual(rejection, "price_moved_too_far")

    def test_trade_after_wait_window_is_not_used(self) -> None:
        signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
        timestamp, fill, rejection = choose_replay_entry(
            signal_time=signal,
            original_price=0.50,
            tape_rows=[("2026-01-01T00:02:00Z", 0.50)],
            scenario=ReplayScenario(
                delay_seconds=5,
                adverse_price_offset=0,
                max_tape_wait_seconds=60,
            ),
        )
        self.assertIsNone(timestamp)
        self.assertIsNone(fill)
        self.assertEqual(rejection, "no_timely_buy_tape")
