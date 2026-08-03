import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any

from ptis.collectors import poll_wallet_trades, utc_now
from ptis.database import connect, initialize
from ptis.monitor import record_first_seen

WALLET = "0x2222222222222222222222222222222222222222"


class MutableClient:
    def __init__(self, payload: list[dict[str, Any]]) -> None:
        self.payload = payload

    def get_json(self, base_url: str, path: str, params: dict[str, Any]) -> Any:
        del base_url, path, params
        return self.payload


def trade(timestamp: int, transaction: str) -> dict[str, Any]:
    return {
        "proxyWallet": WALLET,
        "side": "BUY",
        "asset": f"token-{transaction}",
        "conditionId": "0x" + ("b" * 64),
        "size": 1,
        "price": 0.5,
        "timestamp": timestamp,
        "transactionHash": transaction,
    }


class MonitorTests(unittest.TestCase):
    def test_baseline_is_never_actioned_and_new_trade_is_actioned_once(self) -> None:
        now = int(utc_now().timestamp()) - 1
        client = MutableClient([trade(now, "old")])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "ptis.sqlite3"
            initialize(database)
            with closing(connect(database)) as connection:
                cursor = connection.execute(
                    """INSERT INTO monitor_sessions
                       (started_at_utc, polling_interval_seconds, requested_cycles,
                        wallet_count, status)
                       VALUES ('2026-01-01T00:00:00Z', 1, 2, 1, 'running')"""
                )
                session_id = int(cursor.lastrowid)
                connection.commit()

            received, rows = poll_wallet_trades(
                client, database, root / "raw", wallet=WALLET
            )
            self.assertEqual(
                record_first_seen(
                    database, session_id, WALLET, received, rows, baseline=True
                ),
                [],
            )

            client.payload = [trade(now + 1, "new"), trade(now, "old")]
            received, rows = poll_wallet_trades(
                client, database, root / "raw", wallet=WALLET
            )
            actionable = record_first_seen(
                database, session_id, WALLET, received, rows, baseline=False
            )
            self.assertEqual(len(actionable), 1)
            self.assertEqual(actionable[0][1]["transactionHash"], "new")

            self.assertEqual(
                record_first_seen(
                    database, session_id, WALLET, received, rows, baseline=False
                ),
                [],
            )
