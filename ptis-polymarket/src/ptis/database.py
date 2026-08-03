from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize(database_path: Path) -> None:
    with closing(connect(database_path)) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(leaderboard_snapshots)")
        }
        if "ranking_metric" not in columns:
            connection.execute(
                "ALTER TABLE leaderboard_snapshots "
                "ADD COLUMN ranking_metric TEXT NOT NULL DEFAULT 'PNL'"
            )
        scenario_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(historical_scenarios)")
        }
        scenario_migrations = (
            (
                "execution_eligible_signals",
                "ALTER TABLE historical_scenarios "
                "ADD COLUMN execution_eligible_signals INTEGER NOT NULL DEFAULT 0",
            ),
            (
                "signal_level_net_pnl_usd",
                "ALTER TABLE historical_scenarios "
                "ADD COLUMN signal_level_net_pnl_usd REAL NOT NULL DEFAULT 0",
            ),
            (
                "signal_level_win_rate",
                "ALTER TABLE historical_scenarios "
                "ADD COLUMN signal_level_win_rate REAL",
            ),
        )
        for column_name, statement in scenario_migrations:
            if column_name not in scenario_columns:
                connection.execute(statement)
        connection.commit()
