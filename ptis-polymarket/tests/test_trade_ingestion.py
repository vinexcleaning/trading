import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any

from ptis.collectors import ingest_wallet_trades, trade_key
from ptis.database import connect

WALLET = "0x1111111111111111111111111111111111111111"


class FakeClient:
    def __init__(self, payload: list[dict[str, Any]]) -> None:
        self.payload = payload

    def get_json(self, base_url: str, path: str, params: dict[str, Any]) -> Any:
        del base_url, path, params
        return self.payload


def sample_trade() -> dict[str, Any]:
    return {
        "proxyWallet": WALLET,
        "side": "BUY",
        "asset": "12345",
        "conditionId": "0x" + ("a" * 64),
        "size": 2.5,
        "price": 0.42,
        "timestamp": 1_700_000_000,
        "transactionHash": "0xabc",
    }


class TradeIngestionTests(unittest.TestCase):
    def test_trade_key_is_stable_across_field_order(self) -> None:
        first = sample_trade()
        second = dict(reversed(list(first.items())))
        self.assertEqual(trade_key(first), trade_key(second))

    def test_repeated_overlap_does_not_duplicate_trades(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "ptis.sqlite3"
            raw = root / "raw"
            client = FakeClient([sample_trade()])

            self.assertEqual(
                ingest_wallet_trades(
                    client, database, raw, wallet=WALLET, page_size=10, max_pages=1
                ),
                (1, 1),
            )
            self.assertEqual(
                ingest_wallet_trades(
                    client, database, raw, wallet=WALLET, page_size=10, max_pages=1
                ),
                (1, 0),
            )
            with closing(connect(database)) as connection:
                count = connection.execute("SELECT COUNT(*) FROM public_trades").fetchone()[0]
            self.assertEqual(count, 1)

    def test_invalid_price_fails_run_without_inserting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = sample_trade()
            invalid["price"] = 1.2
            with self.assertRaises(ValueError):
                ingest_wallet_trades(
                    FakeClient([invalid]),
                    root / "ptis.sqlite3",
                    root / "raw",
                    wallet=WALLET,
                    page_size=10,
                    max_pages=1,
                )
            with closing(connect(root / "ptis.sqlite3")) as connection:
                statuses = connection.execute(
                    "SELECT status FROM ingestion_runs ORDER BY id"
                ).fetchall()
                count = connection.execute("SELECT COUNT(*) FROM public_trades").fetchone()[0]
            self.assertEqual(statuses, [("failed",)])
            self.assertEqual(count, 0)
