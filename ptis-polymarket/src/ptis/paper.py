from __future__ import annotations

import time
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from .analysis import assess_trader
from .api import PublicApiClient
from .collectors import (
    _iso,
    collect_orderbook,
    ingest_market_metadata,
    ingest_wallet_trades,
    utc_now,
)
from .database import connect, initialize
from .execution import ExecutionPolicy, ExecutionResult, simulate_buy
from .risk import RiskLimits, check_entry


def invalidate_paper_run(database_path: Path, run_id: int, reason: str) -> None:
    if not reason.strip():
        raise ValueError("invalidation reason is required")
    with closing(connect(database_path)) as connection:
        existing = connection.execute(
            "SELECT notes FROM paper_runs WHERE id=?", (run_id,)
        ).fetchone()
        if not existing:
            raise ValueError(f"paper run {run_id} does not exist")
        prior_notes = existing[0] or ""
        notes = f"INVALIDATED: {reason}. Prior notes: {prior_notes}"
        connection.execute(
            """UPDATE paper_runs
               SET notes=?, status='failed',
                   completed_at_utc=COALESCE(completed_at_utc, ?)
               WHERE id=?""",
            (notes, _iso(utc_now()), run_id),
        )
        connection.commit()


def _skipped(policy: ExecutionPolicy, reason: str) -> ExecutionResult:
    return ExecutionResult(
        accepted=False,
        rejection_reason=reason,
        requested_notional_usd=policy.requested_notional_usd,
        filled_notional_usd=0.0,
        filled_shares=0.0,
        average_fill_price=None,
        best_bid=None,
        best_ask=None,
        fee_usd=0.0,
        slippage_usd=0.0,
    )


def run_shadow_scan(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    wallets: list[str],
    detection_delay_seconds: int = 5,
    max_signal_age_seconds: int = 300,
    requested_notional_usd: float = 1.0,
    max_signals: int = 5,
) -> dict[str, int | float]:
    """Run one current-market paper scan without placing or signing any order."""
    initialize(database_path)
    started_at = utc_now()
    limits = RiskLimits()
    policy = ExecutionPolicy(requested_notional_usd=requested_notional_usd)
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """INSERT INTO paper_runs
               (started_at_utc, starting_bankroll_usd, detection_delay_seconds,
                max_signal_age_seconds, status, notes)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (
                _iso(started_at), limits.bankroll_usd, detection_delay_seconds,
                max_signal_age_seconds,
                "Current-market observational scan; no orders placed.",
            ),
        )
        run_id = int(cursor.lastrowid)
        connection.commit()

    try:
        for wallet in wallets:
            ingest_wallet_trades(
                client,
                database_path,
                raw_dir,
                wallet=wallet,
                page_size=100,
                max_pages=1,
            )
        if detection_delay_seconds:
            time.sleep(detection_delay_seconds)

        cutoff = _iso(started_at - timedelta(seconds=max_signal_age_seconds))
        with closing(connect(database_path)) as connection:
            candidates = connection.execute(
                """SELECT t.trade_key, t.proxy_wallet, t.condition_id, t.token_id,
                          t.price, t.executed_at_utc
                   FROM public_trades t
                   JOIN (
                       SELECT proxy_wallet, MAX(executed_at_utc) AS latest
                       FROM public_trades
                       WHERE proxy_wallet IN ({})
                       GROUP BY proxy_wallet
                   ) latest
                     ON latest.proxy_wallet=t.proxy_wallet
                    AND latest.latest=t.executed_at_utc
                   WHERE t.side='BUY' AND t.executed_at_utc >= ?
                   ORDER BY t.executed_at_utc DESC""".format(
                    ",".join("?" for _ in wallets)
                ),
                tuple(wallet.lower() for wallet in wallets) + (cutoff,),
            ).fetchall()
        candidates = candidates[:max_signals]
        candidate_conditions = list(dict.fromkeys(row[2] for row in candidates))
        unresolved_conditions: list[str] = []
        if candidate_conditions:
            with closing(connect(database_path)) as connection:
                for condition_id in candidate_conditions:
                    fee_row = connection.execute(
                        """SELECT fee_rate_decimal FROM market_observations
                           WHERE condition_id=? AND fee_rate_decimal IS NOT NULL
                           ORDER BY observed_at_utc DESC LIMIT 1""",
                        (condition_id,),
                    ).fetchone()
                    if not fee_row:
                        unresolved_conditions.append(condition_id)
        if unresolved_conditions:
            ingest_market_metadata(
                client,
                database_path,
                raw_dir,
                condition_ids=unresolved_conditions,
                limit=len(unresolved_conditions),
            )

        total_exposure = 0.0
        market_exposure: dict[str, float] = {}
        trader_exposure: dict[str, float] = {}
        for trade_key_value, wallet, condition_id, token_id, price, _ in candidates:
            risk_reason = check_entry(
                requested_notional_usd,
                total_exposure,
                market_exposure.get(condition_id, 0.0),
                trader_exposure.get(wallet, 0.0),
                limits,
            )
            result = _skipped(policy, risk_reason) if risk_reason else None

            if result is None:
                try:
                    assessment = assess_trader(database_path, wallet)
                    if assessment["classification"] in {
                        "market-making-or-arbitrage-like",
                        "hedging-or-arbitrage-like",
                    }:
                        result = _skipped(policy, "trader_behavior_filter")
                except ValueError:
                    result = _skipped(policy, "insufficient_trader_history")

            if result is None:
                with closing(connect(database_path)) as connection:
                    fee_row = connection.execute(
                        """SELECT fee_rate_decimal FROM market_observations
                           WHERE condition_id=? ORDER BY observed_at_utc DESC LIMIT 1""",
                        (condition_id,),
                    ).fetchone()
                if not fee_row or fee_row[0] is None:
                    result = _skipped(policy, "missing_fee_metadata")
                else:
                    fee_rate = float(fee_row[0])
                    _, book = collect_orderbook(
                        client, database_path, raw_dir, token_id=token_id
                    )
                    result = simulate_buy(book, float(price), fee_rate, policy)

            with closing(connect(database_path)) as connection:
                connection.execute(
                    """INSERT OR IGNORE INTO paper_trades
                       (paper_run_id, source_trade_key, proxy_wallet, condition_id,
                        token_id, decision_at_utc, decision, rejection_reason,
                        requested_notional_usd, filled_notional_usd, filled_shares,
                        average_fill_price, fee_usd, slippage_usd,
                        original_trade_price, best_bid, best_ask)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, trade_key_value, wallet, condition_id, token_id,
                        _iso(utc_now()), "accepted" if result.accepted else "skipped",
                        result.rejection_reason, result.requested_notional_usd,
                        result.filled_notional_usd, result.filled_shares,
                        result.average_fill_price, result.fee_usd,
                        result.slippage_usd, price, result.best_bid, result.best_ask,
                    ),
                )
                connection.commit()
            if result.accepted:
                total_exposure += result.filled_notional_usd + result.fee_usd
                market_exposure[condition_id] = (
                    market_exposure.get(condition_id, 0.0) + result.filled_notional_usd
                )
                trader_exposure[wallet] = (
                    trader_exposure.get(wallet, 0.0) + result.filled_notional_usd
                )

        with closing(connect(database_path)) as connection:
            connection.execute(
                "UPDATE paper_runs SET completed_at_utc=?, status='completed' WHERE id=?",
                (_iso(utc_now()), run_id),
            )
            accepted = connection.execute(
                "SELECT COUNT(*) FROM paper_trades WHERE paper_run_id=? AND decision='accepted'",
                (run_id,),
            ).fetchone()[0]
            skipped = connection.execute(
                "SELECT COUNT(*) FROM paper_trades WHERE paper_run_id=? AND decision='skipped'",
                (run_id,),
            ).fetchone()[0]
            connection.commit()
        return {
            "paper_run_id": run_id,
            "signals_considered": len(candidates),
            "accepted": int(accepted),
            "skipped": int(skipped),
            "open_exposure_usd": round(total_exposure, 6),
        }
    except Exception as exc:
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE paper_runs SET completed_at_utc=?, status='failed', notes=?
                   WHERE id=?""",
                (_iso(utc_now()), str(exc), run_id),
            )
            connection.commit()
        raise
