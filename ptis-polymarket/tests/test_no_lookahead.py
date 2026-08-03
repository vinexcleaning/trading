from datetime import datetime, timezone
import unittest


def eligible_observation(observed_at: datetime, decision_at: datetime) -> bool:
    """The invariant future ranking/market data must satisfy."""
    if observed_at.tzinfo is None or decision_at.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return observed_at <= decision_at


class NoLookaheadTests(unittest.TestCase):
    def test_future_observation_is_never_eligible(self) -> None:
        decision_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        future = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertFalse(eligible_observation(future, decision_at))

    def test_past_observation_is_eligible(self) -> None:
        decision_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        past = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(eligible_observation(past, decision_at))
