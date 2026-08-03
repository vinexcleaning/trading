from __future__ import annotations

from contextlib import closing
from pathlib import Path

from .collectors import _iso, utc_now
from .database import connect, initialize


CHECKS = (
    (
        "impossible_trade_prices",
        "error",
        "SELECT COUNT(*) FROM public_trades WHERE price < 0 OR price > 1",
        "Trades must have prices between zero and one.",
    ),
    (
        "nonpositive_trade_sizes",
        "error",
        "SELECT COUNT(*) FROM public_trades WHERE size_shares <= 0",
        "Trades must have positive share size.",
    ),
    (
        "missing_transaction_hash",
        "warning",
        "SELECT COUNT(*) FROM public_trades WHERE transaction_hash IS NULL OR transaction_hash=''",
        "Missing hashes weaken independent deduplication and chain reconciliation.",
    ),
    (
        "unresolved_market_metadata",
        "warning",
        """SELECT COUNT(DISTINCT condition_id) FROM public_trades
           WHERE condition_id NOT IN (SELECT condition_id FROM markets)""",
        "Traded conditions without metadata cannot be categorized or resolved.",
    ),
    (
        "trades_after_ingestion",
        "error",
        "SELECT COUNT(*) FROM public_trades WHERE executed_at_utc > ingested_at_utc",
        "Execution time after ingestion indicates clock or timestamp corruption.",
    ),
    (
        "crossed_books",
        "error",
        """SELECT COUNT(*) FROM orderbook_snapshots
           WHERE best_bid IS NOT NULL AND best_ask IS NOT NULL AND best_bid > best_ask""",
        "A crossed archived book is invalid for the current execution model.",
    ),
)


def run_quality_checks(database_path: Path) -> list[dict[str, int | str]]:
    initialize(database_path)
    checked_at = _iso(utc_now())
    findings: list[dict[str, int | str]] = []
    with closing(connect(database_path)) as connection:
        for name, severity, sql, details in CHECKS:
            affected = int(connection.execute(sql).fetchone()[0])
            finding = {
                "check_name": name,
                "severity": severity,
                "affected_rows": affected,
                "details": details,
            }
            findings.append(finding)
            connection.execute(
                """INSERT INTO data_quality_findings
                   (checked_at_utc, check_name, severity, affected_rows, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (checked_at, name, severity, affected, details),
            )
        connection.commit()
    return findings
