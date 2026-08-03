import unittest

from ptis.risk import RiskLimits, check_entry


class RiskTests(unittest.TestCase):
    def test_one_dollar_trade_is_allowed_for_hundred_dollar_bankroll(self) -> None:
        self.assertIsNone(check_entry(1, 0, 0, 0, RiskLimits()))

    def test_trade_over_two_percent_is_rejected(self) -> None:
        self.assertEqual(
            check_entry(2.01, 0, 0, 0, RiskLimits()),
            "trade_risk_limit",
        )

    def test_correlated_market_limit_is_enforced(self) -> None:
        self.assertEqual(
            check_entry(1, 4.5, 4.5, 0, RiskLimits()),
            "market_exposure_limit",
        )
