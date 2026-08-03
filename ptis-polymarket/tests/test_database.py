import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from ptis.database import connect, initialize


class DatabaseSchemaTests(unittest.TestCase):
    def test_schema_initializes_all_core_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "ptis.sqlite3"
            initialize(database_path)
            with closing(connect(database_path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
        self.assertTrue(
            {
                "ingestion_runs",
                "markets",
                "traders",
                "leaderboard_snapshots",
                "public_trades",
                "orderbook_snapshots",
                "orderbook_levels",
                "experiments",
                "copy_signals",
                "market_observations",
                "reconstructed_positions",
                "trader_assessments",
                "data_quality_findings",
                "paper_runs",
                "paper_trades",
                "monitor_sessions",
                "live_trade_first_seen",
                "paper_positions",
                "historical_backtest_runs",
                "historical_scenarios",
                "historical_copy_trades",
                "consensus_backtest_runs",
                "consensus_results",
                "consensus_copy_trades",
            }
            <= tables
        )
