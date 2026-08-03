import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any

from ptis.collectors import ingest_market_metadata
from ptis.database import connect

CONDITION = "0x" + ("a" * 64)


class MarketClient:
    def get_json(self, base_url: str, path: str, params: dict[str, Any]) -> Any:
        del base_url
        if path == "/fee-rate":
            return {"base_fee": 40}
        return [
            {
                "id": "7",
                "conditionId": CONDITION,
                "question": "Example?",
                "slug": "example",
                "category": "Politics",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.6", "0.4"]',
                "clobTokenIds": '["token-yes", "token-no"]',
                "active": True,
                "closed": False,
                "acceptingOrders": True,
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.04, "exponent": 1, "takerOnly": True},
                "liquidityNum": 1000,
                "volumeNum": 5000,
            }
        ]


class MarketIngestionTests(unittest.TestCase):
    def test_saves_tokens_and_fee_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "ptis.sqlite3"
            result = ingest_market_metadata(
                MarketClient(),
                database,
                root / "raw",
                condition_ids=[CONDITION],
            )
            self.assertEqual(result, (1, 2))
            with closing(connect(database)) as connection:
                tokens = connection.execute(
                    "SELECT token_id, outcome_name FROM outcome_tokens ORDER BY outcome_index"
                ).fetchall()
                fee = connection.execute(
                    "SELECT fee_rate_decimal FROM market_observations"
                ).fetchone()[0]
            self.assertEqual(tokens, [("token-yes", "Yes"), ("token-no", "No")])
            self.assertAlmostEqual(fee, 0.04)
