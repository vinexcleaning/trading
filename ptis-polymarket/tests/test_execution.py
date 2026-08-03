import unittest

from ptis.execution import ExecutionPolicy, simulate_buy, taker_fee


class ExecutionTests(unittest.TestCase):
    def test_walks_depth_and_charges_dynamic_fee(self) -> None:
        book = {
            "bids": [{"price": "0.49", "size": "10"}],
            "asks": [
                {"price": "0.50", "size": "1"},
                {"price": "0.51", "size": "10"},
            ],
        }
        result = simulate_buy(
            book,
            original_price=0.50,
            fee_rate_decimal=0.04,
            policy=ExecutionPolicy(requested_notional_usd=1.0),
        )
        self.assertTrue(result.accepted)
        self.assertGreater(result.average_fill_price or 0, 0.50)
        self.assertGreater(result.slippage_usd, 0)
        self.assertGreater(result.fee_usd, 0)

    def test_rejects_price_deterioration(self) -> None:
        book = {
            "bids": [{"price": "0.49", "size": "10"}],
            "asks": [{"price": "0.55", "size": "10"}],
        }
        result = simulate_buy(
            book,
            original_price=0.50,
            fee_rate_decimal=0,
            policy=ExecutionPolicy(max_spread=0.10, max_price_deterioration=0.02),
        )
        self.assertEqual(result.rejection_reason, "price_moved_too_far")

    def test_fee_is_symmetric_around_half_probability(self) -> None:
        self.assertAlmostEqual(taker_fee(10, 0.3, 0.04), taker_fee(10, 0.7, 0.04))

    def test_rejects_contract_with_too_little_remaining_upside(self) -> None:
        book = {
            "bids": [{"price": "0.995", "size": "10"}],
            "asks": [{"price": "0.999", "size": "10"}],
        }
        result = simulate_buy(
            book,
            original_price=0.999,
            fee_rate_decimal=0.05,
            policy=ExecutionPolicy(max_spread=0.01),
        )
        self.assertEqual(result.rejection_reason, "insufficient_remaining_upside")
