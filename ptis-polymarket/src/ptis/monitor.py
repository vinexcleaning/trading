from __future__ import annotations

import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analysis import assess_trader
from .api import PublicApiClient
from .collectors import (
    _iso,
    _unix_timestamp_to_utc,
    collect_orderbook,
    ingest_market_metadata,
    poll_wallet_trades,
    utc_now,
)
from .database import connect, initialize
from .execution import ExecutionPolicy, ExecutionResult, simulate_buy
from .risk import RiskLimits, check_entry


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def record_first_seen(
    database_path: Path,
    session_id: int,
    wallet: str,
    received_at: datetime,
    rows: list[tuple[str, dict[str, Any]]],
    *,
    baseline: bool,
) -> list[tuple[str, dict[str, Any], float]]:
    """Persist first visibility and return only genuinely new non-baseline trades."""
    newly_actionable: list[tuple[str, dict[str, Any], float]] = []
    with closing(connect(database_path)) as connection:
        for key, row in rows:
            executed_at = _unix_timestamp_to_utc(row["timestamp"])
            delay = max(0.0, (received_at - _parse_utc(executed_at)).total_seconds())
            result = connection.execute(
                """INSERT OR IGNORE INTO live_trade_first_seen
                   (trade_key, monitor_session_id, proxy_wallet, executed_at_utc,
                    first_seen_at_utc, visibility_delay_seconds, was_baseline)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    key, session_id, wallet.lower(), executed_at, _iso(received_at),
                    delay, int(baseline),
                ),
            )
            if result.rowcount and not baseline:
                newly_actionable.append((key, row, delay))
        connection.commit()
    return newly_actionable


def _skip(policy: ExecutionPolicy, reason: str) -> ExecutionResult:
    return ExecutionResult(
        False, reason, policy.requested_notional_usd, 0, 0, None,
        None, None, 0, 0,
    )


def _insert_paper_decision(
    database_path: Path,
    paper_run_id: int,
    trade_key: str,
    row: dict[str, Any],
    result: ExecutionResult,
) -> None:
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO paper_trades
               (paper_run_id, source_trade_key, proxy_wallet, condition_id,
                token_id, decision_at_utc, decision, rejection_reason,
                requested_notional_usd, filled_notional_usd, filled_shares,
                average_fill_price, fee_usd, slippage_usd,
                original_trade_price, best_bid, best_ask)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                paper_run_id,
                trade_key,
                str(row["proxyWallet"]).lower(),
                str(row["conditionId"]),
                str(row["asset"]),
                _iso(utc_now()),
                "accepted" if result.accepted else "skipped",
                result.rejection_reason,
                result.requested_notional_usd,
                result.filled_notional_usd,
                result.filled_shares,
                result.average_fill_price,
                result.fee_usd,
                result.slippage_usd,
                float(row["price"]),
                result.best_bid,
                result.best_ask,
            ),
        )
        if result.accepted and cursor.rowcount:
            connection.execute(
                """INSERT INTO paper_positions
                   (paper_trade_id, opened_at_utc, status)
                   VALUES (?, ?, 'open')""",
                (cursor.lastrowid, _iso(utc_now())),
            )
        connection.commit()


def _current_open_exposure(
    database_path: Path,
) -> tuple[float, dict[str, float], dict[str, float]]:
    total = 0.0
    by_market: dict[str, float] = {}
    by_trader: dict[str, float] = {}
    with closing(connect(database_path)) as connection:
        rows = connection.execute(
            """SELECT t.condition_id, t.proxy_wallet,
                      t.filled_notional_usd + t.fee_usd
               FROM paper_positions p
               JOIN paper_trades t ON t.id=p.paper_trade_id
               WHERE p.status='open'"""
        ).fetchall()
    for condition, wallet, exposure in rows:
        value = float(exposure)
        total += value
        by_market[condition] = by_market.get(condition, 0.0) + value
        by_trader[wallet] = by_trader.get(wallet, 0.0) + value
    return total, by_market, by_trader


def settle_paper_positions(database_path: Path) -> dict[str, float | int]:
    initialize(database_path)
    settled = 0
    total_pnl = 0.0
    with closing(connect(database_path)) as connection:
        rows = connection.execute(
            """SELECT p.id, t.token_id, t.filled_shares,
                      t.filled_notional_usd, t.fee_usd,
                      m.winning_token_id, m.resolved_at_utc
               FROM paper_positions p
               JOIN paper_trades t ON t.id=p.paper_trade_id
               JOIN markets m ON m.condition_id=t.condition_id
               WHERE p.status='open' AND m.winning_token_id IS NOT NULL"""
        ).fetchall()
        for position_id, token, shares, notional, fee, winner, resolved_at in rows:
            payout = float(shares) if token == winner else 0.0
            pnl = payout - float(notional) - float(fee)
            connection.execute(
                """UPDATE paper_positions
                   SET status='resolved', resolved_at_utc=?, payout_usd=?, net_pnl_usd=?
                   WHERE id=?""",
                (resolved_at or _iso(utc_now()), payout, pnl, position_id),
            )
            settled += 1
            total_pnl += pnl
        connection.commit()
    return {"settled": settled, "net_pnl_usd": round(total_pnl, 6)}


def invalidate_monitor_session(database_path: Path, session_id: int, reason: str) -> None:
    if not reason.strip():
        raise ValueError("invalidation reason is required")
    with closing(connect(database_path)) as connection:
        existing = connection.execute(
            "SELECT notes FROM monitor_sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not existing:
            raise ValueError(f"monitor session {session_id} does not exist")
        notes = f"INVALIDATED: {reason}. Prior notes: {existing[0] or ''}"
        connection.execute(
            """UPDATE monitor_sessions
               SET status='failed', completed_at_utc=COALESCE(completed_at_utc, ?),
                   notes=? WHERE id=?""",
            (_iso(utc_now()), notes, session_id),
        )
        connection.commit()


def evaluate_pending_signals(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    limit: int = 2,
    detection_delay_seconds: int = 5,
    requested_notional_usd: float = 1.0,
    max_visibility_delay_seconds: int = 300,
) -> dict[str, float | int]:
    """Evaluate live-seen trades not yet recorded in a completed paper run."""
    initialize(database_path)
    policy = ExecutionPolicy(requested_notional_usd=requested_notional_usd)
    limits = RiskLimits()
    started = utc_now()
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """INSERT INTO paper_runs
               (started_at_utc, starting_bankroll_usd, detection_delay_seconds,
                max_signal_age_seconds, status, notes)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (
                _iso(started), limits.bankroll_usd, detection_delay_seconds,
                max_visibility_delay_seconds,
                "Resumable evaluation of prospectively observed signals; no orders placed.",
            ),
        )
        run_id = int(cursor.lastrowid)
        pending = connection.execute(
            """SELECT t.trade_key, t.proxy_wallet, t.condition_id, t.token_id,
                      t.side, t.size_shares, t.price, t.executed_at_utc,
                      t.transaction_hash, s.visibility_delay_seconds
               FROM live_trade_first_seen s
               JOIN public_trades t ON t.trade_key=s.trade_key
               WHERE s.was_baseline=0
                 AND NOT EXISTS (
                     SELECT 1 FROM paper_trades pt
                     JOIN paper_runs pr ON pr.id=pt.paper_run_id
                     WHERE pt.source_trade_key=s.trade_key
                       AND pr.status='completed'
                 )
               ORDER BY s.first_seen_at_utc, t.trade_key
               LIMIT ?""",
            (limit,),
        ).fetchall()
        connection.commit()

    accepted = 0
    skipped = 0
    total_exposure, market_exposure, trader_exposure = _current_open_exposure(
        database_path
    )
    starting_exposure = total_exposure
    try:
        for row_data in pending:
            (
                key, wallet, condition, token, side, size, price,
                executed_at, transaction_hash, visibility_delay,
            ) = row_data
            row = {
                "proxyWallet": wallet,
                "conditionId": condition,
                "asset": token,
                "side": side,
                "size": size,
                "price": price,
                "timestamp": int(_parse_utc(executed_at).timestamp()),
                "transactionHash": transaction_hash,
            }
            result: ExecutionResult | None = None
            if visibility_delay > max_visibility_delay_seconds:
                result = _skip(policy, "visibility_delay_too_long")
            elif side != "BUY":
                result = _skip(policy, "sell_signal_not_supported")
            if result is None:
                risk_reason = check_entry(
                    requested_notional_usd,
                    total_exposure,
                    market_exposure.get(condition, 0),
                    trader_exposure.get(wallet, 0),
                    limits,
                )
                if risk_reason:
                    result = _skip(policy, risk_reason)
            if result is None:
                assessment = assess_trader(database_path, wallet)
                if assessment["classification"] in {
                    "market-making-or-arbitrage-like",
                    "hedging-or-arbitrage-like",
                    "sell-only-or-incomplete-history",
                }:
                    result = _skip(policy, "trader_behavior_filter")
            if result is None:
                with closing(connect(database_path)) as connection:
                    fee_row = connection.execute(
                        """SELECT fee_rate_decimal FROM market_observations
                           WHERE condition_id=? AND fee_rate_decimal IS NOT NULL
                           ORDER BY observed_at_utc DESC LIMIT 1""",
                        (condition,),
                    ).fetchone()
                if not fee_row:
                    ingest_market_metadata(
                        client,
                        database_path,
                        raw_dir,
                        condition_ids=[condition],
                        limit=1,
                    )
                    with closing(connect(database_path)) as connection:
                        fee_row = connection.execute(
                            """SELECT fee_rate_decimal FROM market_observations
                               WHERE condition_id=? AND fee_rate_decimal IS NOT NULL
                               ORDER BY observed_at_utc DESC LIMIT 1""",
                            (condition,),
                        ).fetchone()
                if not fee_row:
                    result = _skip(policy, "missing_fee_metadata")
                else:
                    _, book = collect_orderbook(
                        client, database_path, raw_dir, token_id=token
                    )
                    result = simulate_buy(book, float(price), float(fee_row[0]), policy)

            _insert_paper_decision(database_path, run_id, key, row, result)
            if result.accepted:
                accepted += 1
                exposure = result.filled_notional_usd + result.fee_usd
                total_exposure += exposure
                market_exposure[condition] = market_exposure.get(condition, 0) + exposure
                trader_exposure[wallet] = trader_exposure.get(wallet, 0) + exposure
            else:
                skipped += 1

        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE paper_runs SET completed_at_utc=?, status='completed'
                   WHERE id=?""",
                (_iso(utc_now()), run_id),
            )
            connection.commit()
    except Exception as exc:
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE paper_runs SET completed_at_utc=?, status='failed', notes=?
                   WHERE id=?""",
                (_iso(utc_now()), str(exc), run_id),
            )
            connection.commit()
        raise
    return {
        "paper_run_id": run_id,
        "signals_evaluated": len(pending),
        "accepted": accepted,
        "skipped": skipped,
        "new_exposure_usd": round(total_exposure - starting_exposure, 6),
        "total_open_exposure_usd": round(total_exposure, 6),
    }


def run_live_monitor(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    wallets: list[str],
    cycles: int = 4,
    polling_interval_seconds: int = 15,
    detection_delay_seconds: int = 5,
    requested_notional_usd: float = 1.0,
    max_visibility_delay_seconds: int = 300,
    max_signals_per_cycle: int = 3,
) -> dict[str, float | int]:
    initialize(database_path)
    started = utc_now()
    policy = ExecutionPolicy(requested_notional_usd=requested_notional_usd)
    limits = RiskLimits()
    with closing(connect(database_path)) as connection:
        session_cursor = connection.execute(
            """INSERT INTO monitor_sessions
               (started_at_utc, polling_interval_seconds, requested_cycles,
                wallet_count, status, notes)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (
                _iso(started), polling_interval_seconds, cycles, len(wallets),
                "Prospective public-data monitor; no orders placed.",
            ),
        )
        session_id = int(session_cursor.lastrowid)
        run_cursor = connection.execute(
            """INSERT INTO paper_runs
               (started_at_utc, starting_bankroll_usd, detection_delay_seconds,
                max_signal_age_seconds, status, notes)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (
                _iso(started), limits.bankroll_usd, detection_delay_seconds,
                max_visibility_delay_seconds,
                f"Prospective monitor session {session_id}; no orders placed.",
            ),
        )
        paper_run_id = int(run_cursor.lastrowid)
        connection.commit()

    new_seen = 0
    accepted = 0
    skipped = 0
    total_exposure, market_exposure, trader_exposure = _current_open_exposure(
        database_path
    )
    starting_exposure = total_exposure
    try:
        for cycle_index in range(cycles):
            cycle_new: list[tuple[str, dict[str, Any], float, datetime]] = []
            for wallet in wallets:
                received_at, rows = poll_wallet_trades(
                    client, database_path, raw_dir, wallet=wallet, limit=100
                )
                with closing(connect(database_path)) as connection:
                    has_baseline = bool(
                        connection.execute(
                            """SELECT 1 FROM live_trade_first_seen
                               WHERE proxy_wallet=? LIMIT 1""",
                            (wallet.lower(),),
                        ).fetchone()
                    )
                new_rows = record_first_seen(
                    database_path,
                    session_id,
                    wallet,
                    received_at,
                    rows,
                    baseline=not has_baseline,
                )
                cycle_new.extend(
                    (key, row, delay, received_at) for key, row, delay in new_rows
                )
            new_seen += len(cycle_new)

            for key, row, visibility_delay, first_seen in cycle_new[:max_signals_per_cycle]:
                result: ExecutionResult | None = None
                if visibility_delay > max_visibility_delay_seconds:
                    result = _skip(policy, "visibility_delay_too_long")
                elif str(row["side"]).upper() != "BUY":
                    result = _skip(policy, "sell_signal_not_supported")

                wallet = str(row["proxyWallet"]).lower()
                condition = str(row["conditionId"])
                if result is None:
                    risk_reason = check_entry(
                        requested_notional_usd,
                        total_exposure,
                        market_exposure.get(condition, 0.0),
                        trader_exposure.get(wallet, 0.0),
                        limits,
                    )
                    if risk_reason:
                        result = _skip(policy, risk_reason)
                if result is None:
                    assessment = assess_trader(database_path, wallet)
                    if assessment["classification"] in {
                        "market-making-or-arbitrage-like",
                        "hedging-or-arbitrage-like",
                        "sell-only-or-incomplete-history",
                    }:
                        result = _skip(policy, "trader_behavior_filter")

                if result is None:
                    ingest_market_metadata(
                        client,
                        database_path,
                        raw_dir,
                        condition_ids=[condition],
                        limit=1,
                    )
                    with closing(connect(database_path)) as connection:
                        fee_row = connection.execute(
                            """SELECT fee_rate_decimal FROM market_observations
                               WHERE condition_id=? AND fee_rate_decimal IS NOT NULL
                               ORDER BY observed_at_utc DESC LIMIT 1""",
                            (condition,),
                        ).fetchone()
                    if not fee_row:
                        result = _skip(policy, "missing_fee_metadata")
                    else:
                        elapsed = (utc_now() - first_seen).total_seconds()
                        if elapsed < detection_delay_seconds:
                            time.sleep(detection_delay_seconds - elapsed)
                        _, book = collect_orderbook(
                            client,
                            database_path,
                            raw_dir,
                            token_id=str(row["asset"]),
                        )
                        result = simulate_buy(
                            book,
                            float(row["price"]),
                            float(fee_row[0]),
                            policy,
                        )

                _insert_paper_decision(database_path, paper_run_id, key, row, result)
                if result.accepted:
                    accepted += 1
                    exposure = result.filled_notional_usd + result.fee_usd
                    total_exposure += exposure
                    market_exposure[condition] = market_exposure.get(condition, 0) + exposure
                    trader_exposure[wallet] = trader_exposure.get(wallet, 0) + exposure
                else:
                    skipped += 1

            with closing(connect(database_path)) as connection:
                connection.execute(
                    "UPDATE monitor_sessions SET completed_cycles=? WHERE id=?",
                    (cycle_index + 1, session_id),
                )
                connection.commit()
            if cycle_index + 1 < cycles:
                time.sleep(polling_interval_seconds)

        completed = _iso(utc_now())
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE monitor_sessions
                   SET completed_at_utc=?, status='completed' WHERE id=?""",
                (completed, session_id),
            )
            connection.execute(
                """UPDATE paper_runs
                   SET completed_at_utc=?, status='completed' WHERE id=?""",
                (completed, paper_run_id),
            )
            connection.commit()
    except Exception as exc:
        completed = _iso(utc_now())
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE monitor_sessions
                   SET completed_at_utc=?, status='failed', notes=? WHERE id=?""",
                (completed, str(exc), session_id),
            )
            connection.execute(
                """UPDATE paper_runs
                   SET completed_at_utc=?, status='failed', notes=? WHERE id=?""",
                (completed, str(exc), paper_run_id),
            )
            connection.commit()
        raise

    return {
        "monitor_session_id": session_id,
        "paper_run_id": paper_run_id,
        "new_trades_first_seen": new_seen,
        "accepted": accepted,
        "skipped": skipped,
        "new_exposure_usd": round(total_exposure - starting_exposure, 6),
        "total_open_exposure_usd": round(total_exposure, 6),
    }
