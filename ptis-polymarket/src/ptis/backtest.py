from __future__ import annotations

import math
from bisect import bisect_left
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .api import PublicApiClient
from .collectors import (
    _iso,
    ingest_market_metadata,
    ingest_market_trade_tape,
    utc_now,
)
from .database import connect, initialize
from .execution import taker_fee
from .risk import RiskLimits, check_entry


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass(frozen=True)
class ReplayScenario:
    delay_seconds: int
    adverse_price_offset: float
    max_tape_wait_seconds: int = 60
    requested_notional_usd: float = 1.0
    max_price_deterioration: float = 0.02
    minimum_gross_upside: float = 0.03


@dataclass
class ReplayDecision:
    source_trade_key: str
    proxy_wallet: str
    condition_id: str
    token_id: str
    signal_at_utc: str
    follower_at_utc: str
    tape_trade_at_utc: str | None
    accepted: bool
    rejection_reason: str | None
    original_price: float
    tape_price: float | None = None
    fill_price: float | None = None
    shares: float = 0.0
    fee_usd: float = 0.0
    payout_usd: float = 0.0
    net_pnl_usd: float = 0.0
    resolution_at_utc: str | None = None


def classify_prior_behavior(
    rows: list[tuple[str, str, str, str]],
    *,
    minimum_observations: int = 30,
) -> str:
    """Classify using only rows supplied by the caller; no outcomes are needed."""
    if len(rows) < minimum_observations:
        return "insufficient-prior-history"
    buys = sum(side == "BUY" for _, _, side, _ in rows)
    buy_share = buys / len(rows)
    condition_tokens: dict[str, set[str]] = {}
    previous_by_token: dict[str, tuple[str, datetime]] = {}
    reversals = 0
    for condition, token, side, timestamp in rows:
        if side == "BUY":
            condition_tokens.setdefault(condition, set()).add(token)
        moment = parse_utc(timestamp)
        previous = previous_by_token.get(token)
        if previous and previous[0] != side:
            if (moment - previous[1]).total_seconds() <= 3600:
                reversals += 1
        previous_by_token[token] = (side, moment)
    reversal_share = reversals / max(1, len(rows) - 1)
    two_sided_share = (
        sum(len(tokens) > 1 for tokens in condition_tokens.values())
        / max(1, len(condition_tokens))
    )
    if buy_share <= 0.05:
        return "sell-only-or-incomplete-history"
    if reversal_share >= 0.25 and two_sided_share >= 0.25:
        return "market-making-or-arbitrage-like"
    if two_sided_share >= 0.35:
        return "hedging-or-arbitrage-like"
    if reversal_share >= 0.25:
        return "rapid-trader"
    if buy_share >= 0.75 and reversal_share <= 0.10:
        return "directional-candidate"
    return "unknown"


def prepare_historical_data(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    wallets: list[str],
    dataset_start: datetime,
    dataset_end: datetime,
    max_markets: int = 5,
    tape_page_size: int = 500,
    tape_max_pages: int = 2,
) -> dict[str, int]:
    """Prepare a bounded set of frequently traded candidate markets."""
    initialize(database_path)
    normalized = [wallet.lower() for wallet in wallets]
    with closing(connect(database_path)) as connection:
        conditions = [
            row[0]
            for row in connection.execute(
                """SELECT condition_id, COUNT(*) AS signal_count
                   FROM public_trades
                   WHERE proxy_wallet IN ({})
                     AND executed_at_utc >= ? AND executed_at_utc < ?
                     AND condition_id NOT IN (
                         SELECT DISTINCT condition_id FROM public_trades
                         WHERE raw_file_path LIKE '%data_api_market_tape%'
                     )
                   GROUP BY condition_id
                   ORDER BY signal_count DESC, condition_id
                   LIMIT ?""".format(
                    ",".join("?" for _ in normalized)
                ),
                tuple(normalized)
                + (_iso(dataset_start), _iso(dataset_end), max_markets),
            )
        ]
    downloaded = 0
    inserted = 0
    markets_saved = 0
    for condition in conditions:
        saved, _ = ingest_market_metadata(
            client,
            database_path,
            raw_dir,
            condition_ids=[condition],
            limit=1,
        )
        markets_saved += saved
        tape_downloaded, tape_inserted = ingest_market_trade_tape(
            client,
            database_path,
            raw_dir,
            condition_id=condition,
            page_size=tape_page_size,
            max_pages=tape_max_pages,
        )
        downloaded += tape_downloaded
        inserted += tape_inserted
    return {
        "markets_prepared": len(conditions),
        "market_metadata_saved": markets_saved,
        "tape_rows_downloaded": downloaded,
        "new_tape_rows_inserted": inserted,
    }


def choose_replay_entry(
    *,
    signal_time: datetime,
    original_price: float,
    tape_rows: Iterable[tuple[str, float]],
    scenario: ReplayScenario,
) -> tuple[str | None, float | None, str | None]:
    """Choose a post-delay tape price without consulting the market outcome."""
    follower_time = signal_time + timedelta(seconds=scenario.delay_seconds)
    cutoff = follower_time + timedelta(seconds=scenario.max_tape_wait_seconds)
    for timestamp, price in tape_rows:
        moment = parse_utc(timestamp)
        if moment < follower_time:
            continue
        if moment > cutoff:
            return None, None, "no_timely_buy_tape"
        fill = min(0.999, float(price) + scenario.adverse_price_offset)
        if (
            fill - original_price
            > scenario.max_price_deterioration + 1e-9
        ):
            return timestamp, fill, "price_moved_too_far"
        if 1.0 - fill < scenario.minimum_gross_upside:
            return timestamp, fill, "insufficient_remaining_upside"
        return timestamp, fill, None
    return None, None, "no_timely_buy_tape"


def _scenario_metrics(
    decisions: list[ReplayDecision],
    starting_bankroll: float,
) -> dict[str, float | int | None]:
    accepted = [decision for decision in decisions if decision.accepted]
    pnls = [decision.net_pnl_usd for decision in accepted]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    total = sum(pnls)
    equity = starting_bankroll
    peak = equity
    maximum_drawdown = 0.0
    for decision in sorted(
        accepted,
        key=lambda item: item.resolution_at_utc or "9999",
    ):
        equity += decision.net_pnl_usd
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, peak - equity)
    profit_factor = (
        sum(wins) / abs(sum(losses))
        if losses
        else (math.inf if wins else None)
    )
    largest_share = (
        max(pnls) / total if total > 0 and pnls else None
    )
    return {
        "signals_considered": len(decisions),
        "trades_accepted": len(accepted),
        "trades_skipped": len(decisions) - len(accepted),
        "total_net_pnl_usd": total,
        "return_on_bankroll": total / starting_bankroll,
        "maximum_drawdown_usd": maximum_drawdown,
        "win_rate": len(wins) / len(accepted) if accepted else None,
        "profit_factor": profit_factor,
        "largest_trade_profit_share": largest_share,
    }


def run_historical_replay(
    database_path: Path,
    *,
    wallets: list[str],
    dataset_start: datetime,
    dataset_end: datetime,
    scenarios: list[ReplayScenario],
    starting_bankroll: float = 100.0,
) -> int:
    initialize(database_path)
    normalized_wallets = [wallet.lower() for wallet in wallets]
    selection_method = (
        "Fixed wallets selected from current-session leaderboards; retrospective "
        "selection bias is present. All selected wallets are included."
    )
    notes = (
        "Approximate replay. Entry uses first subsequent BUY trade tape, not a "
        "historical order book. Current archived fee schedule is used. Outcomes "
        "are inaccessible to entry selection and used only for settlement."
    )
    with closing(connect(database_path)) as connection:
        connection.execute(
            """UPDATE historical_backtest_runs
               SET status='failed',
                   notes=notes || ' Automatically closed after an interrupted run.'
               WHERE status='running'"""
        )
        cursor = connection.execute(
            """INSERT INTO historical_backtest_runs
               (created_at_utc, dataset_start_utc, dataset_end_utc,
                selection_method, realism_label, starting_bankroll_usd,
                status, notes)
               VALUES (?, ?, ?, ?, 'Approximate', ?, 'running', ?)""",
            (
                _iso(utc_now()), _iso(dataset_start), _iso(dataset_end),
                selection_method, starting_bankroll, notes,
            ),
        )
        run_id = int(cursor.lastrowid)
        signals = connection.execute(
            """SELECT t.trade_key, t.proxy_wallet, t.condition_id, t.token_id,
                      t.price, t.executed_at_utc, m.winning_token_id,
                      m.resolved_at_utc,
                      (
                          SELECT mo.fee_rate_decimal
                          FROM market_observations mo
                          WHERE mo.condition_id=t.condition_id
                            AND mo.fee_rate_decimal IS NOT NULL
                          ORDER BY mo.observed_at_utc DESC LIMIT 1
                      ) AS fee_rate
               FROM public_trades t
               LEFT JOIN markets m ON m.condition_id=t.condition_id
               WHERE t.proxy_wallet IN ({})
                 AND t.side='BUY'
                 AND t.executed_at_utc >= ?
                 AND t.executed_at_utc < ?
                 AND t.raw_file_path NOT LIKE '%data_api_market_tape%'
               ORDER BY t.executed_at_utc, t.trade_key""".format(
                ",".join("?" for _ in normalized_wallets)
            ),
            tuple(normalized_wallets) + (_iso(dataset_start), _iso(dataset_end)),
        ).fetchall()
        connection.commit()

    token_ids = list(dict.fromkeys(row[3] for row in signals))
    tape_map: dict[str, list[tuple[str, float]]] = {token: [] for token in token_ids}
    with closing(connect(database_path)) as connection:
        for start_index in range(0, len(token_ids), 400):
            chunk = token_ids[start_index : start_index + 400]
            if not chunk:
                continue
            rows = connection.execute(
                """SELECT token_id, executed_at_utc, price
                   FROM public_trades
                   WHERE side='BUY' AND token_id IN ({})
                   ORDER BY token_id, executed_at_utc, trade_key""".format(
                    ",".join("?" for _ in chunk)
                ),
                tuple(chunk),
            ).fetchall()
            for token, timestamp, price in rows:
                tape_map[token].append((timestamp, float(price)))
    tape_time_map = {
        token: [parse_utc(timestamp) for timestamp, _ in rows]
        for token, rows in tape_map.items()
    }
    history_map: dict[str, list[tuple[str, str, str, str]]] = {
        wallet: [] for wallet in normalized_wallets
    }
    history_time_map: dict[str, list[datetime]] = {
        wallet: [] for wallet in normalized_wallets
    }
    with closing(connect(database_path)) as connection:
        history_rows = connection.execute(
            """SELECT proxy_wallet, condition_id, token_id, side, executed_at_utc
               FROM public_trades
               WHERE proxy_wallet IN ({}) AND executed_at_utc < ?
               ORDER BY proxy_wallet, executed_at_utc, trade_key""".format(
                ",".join("?" for _ in normalized_wallets)
            ),
            tuple(normalized_wallets) + (_iso(dataset_end),),
        ).fetchall()
    for wallet, condition, token, side, timestamp in history_rows:
        history_map[wallet].append((condition, token, side, timestamp))
        history_time_map[wallet].append(parse_utc(timestamp))
    prior_classification: dict[str, str] = {}
    for (
        source_key, wallet, _, _, _, executed_at, _, _, _,
    ) in signals:
        signal_time = parse_utc(executed_at)
        cutoff_index = bisect_left(history_time_map.get(wallet, []), signal_time)
        prior_classification[source_key] = classify_prior_behavior(
            history_map.get(wallet, [])[:cutoff_index]
        )

    try:
        for scenario in scenarios:
            limits = RiskLimits(bankroll_usd=starting_bankroll)
            decisions: list[ReplayDecision] = []
            execution_eligible_pnls: list[float] = []
            open_positions: list[tuple[datetime, float, float, str, str]] = []
            cash = starting_bankroll
            total_exposure = 0.0
            market_exposure: dict[str, float] = {}
            trader_exposure: dict[str, float] = {}

            for (
                source_key, wallet, condition, token, original_price,
                executed_at, winner, resolved_at, fee_rate,
            ) in signals:
                signal_time = parse_utc(executed_at)
                still_open: list[tuple[datetime, float, float, str, str]] = []
                for (
                    resolution_time, position_cost, position_payout,
                    open_market, open_wallet,
                ) in open_positions:
                    if resolution_time <= signal_time:
                        cash += position_payout
                        total_exposure -= position_cost
                        market_exposure[open_market] = max(
                            0.0, market_exposure.get(open_market, 0.0) - position_cost
                        )
                        trader_exposure[open_wallet] = max(
                            0.0, trader_exposure.get(open_wallet, 0.0) - position_cost
                        )
                    else:
                        still_open.append(
                            (
                                resolution_time, position_cost, position_payout,
                                open_market, open_wallet,
                            )
                        )
                open_positions = still_open

                follower_at = _iso(
                    signal_time + timedelta(seconds=scenario.delay_seconds)
                )
                decision = ReplayDecision(
                    source_key, wallet, condition, token, executed_at, follower_at,
                    None, False, None, float(original_price),
                )
                if not winner or not resolved_at:
                    decision.rejection_reason = "unresolved_or_missing_outcome"
                    decisions.append(decision)
                    continue
                classification = prior_classification.get(
                    source_key, "insufficient-prior-history"
                )
                if classification == "insufficient-prior-history":
                    decision.rejection_reason = "insufficient_prior_trader_history"
                    decisions.append(decision)
                    continue
                if classification in {
                    "market-making-or-arbitrage-like",
                    "hedging-or-arbitrage-like",
                    "sell-only-or-incomplete-history",
                }:
                    decision.rejection_reason = "trader_behavior_filter"
                    decisions.append(decision)
                    continue
                if fee_rate is None:
                    decision.rejection_reason = "missing_fee_metadata"
                    decisions.append(decision)
                    continue

                tape_rows_all = tape_map.get(token, [])
                tape_times = tape_time_map.get(token, [])
                follower_time = signal_time + timedelta(
                    seconds=scenario.delay_seconds
                )
                tape_index = bisect_left(tape_times, follower_time)
                tape_rows = tape_rows_all[tape_index : tape_index + 100]
                tape_time, fill, rejection = choose_replay_entry(
                    signal_time=signal_time,
                    original_price=float(original_price),
                    tape_rows=tape_rows,
                    scenario=scenario,
                )
                decision.tape_trade_at_utc = tape_time
                decision.tape_price = (
                    None if fill is None else fill - scenario.adverse_price_offset
                )
                decision.fill_price = fill
                if rejection:
                    decision.rejection_reason = rejection
                    decisions.append(decision)
                    continue

                risk_reason = check_entry(
                    scenario.requested_notional_usd,
                    total_exposure,
                    market_exposure.get(condition, 0.0),
                    trader_exposure.get(wallet, 0.0),
                    limits,
                )
                assert fill is not None
                shares = scenario.requested_notional_usd / fill
                fee = taker_fee(shares, fill, float(fee_rate))
                cost = scenario.requested_notional_usd + fee
                payout = shares if token == winner else 0.0
                pnl = payout - cost
                execution_eligible_pnls.append(pnl)
                decision.shares = shares
                decision.fee_usd = fee
                decision.payout_usd = payout
                decision.net_pnl_usd = pnl
                if risk_reason:
                    decision.rejection_reason = risk_reason
                    decisions.append(decision)
                    continue
                if cost > cash:
                    decision.rejection_reason = "insufficient_cash"
                    decisions.append(decision)
                    continue
                decision.accepted = True
                decision.resolution_at_utc = resolved_at
                cash -= cost
                total_exposure += cost
                market_exposure[condition] = market_exposure.get(condition, 0) + cost
                trader_exposure[wallet] = trader_exposure.get(wallet, 0) + cost
                open_positions.append(
                    (parse_utc(resolved_at), cost, payout, condition, wallet)
                )
                decisions.append(decision)

            metrics = _scenario_metrics(decisions, starting_bankroll)
            with closing(connect(database_path)) as connection:
                cursor = connection.execute(
                    """INSERT INTO historical_scenarios
                       (backtest_run_id, delay_seconds, adverse_price_offset,
                        max_tape_wait_seconds, signals_considered, trades_accepted,
                        trades_skipped, total_net_pnl_usd, return_on_bankroll,
                        maximum_drawdown_usd, win_rate, profit_factor,
                        largest_trade_profit_share, execution_eligible_signals,
                        signal_level_net_pnl_usd, signal_level_win_rate)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, scenario.delay_seconds, scenario.adverse_price_offset,
                        scenario.max_tape_wait_seconds,
                        metrics["signals_considered"], metrics["trades_accepted"],
                        metrics["trades_skipped"], metrics["total_net_pnl_usd"],
                        metrics["return_on_bankroll"], metrics["maximum_drawdown_usd"],
                        metrics["win_rate"],
                        None if metrics["profit_factor"] == math.inf else metrics["profit_factor"],
                        metrics["largest_trade_profit_share"],
                        len(execution_eligible_pnls),
                        sum(execution_eligible_pnls),
                        (
                            sum(value > 0 for value in execution_eligible_pnls)
                            / len(execution_eligible_pnls)
                            if execution_eligible_pnls else None
                        ),
                    ),
                )
                scenario_id = int(cursor.lastrowid)
                connection.executemany(
                    """INSERT INTO historical_copy_trades
                       (scenario_id, source_trade_key, proxy_wallet, condition_id,
                        token_id, signal_at_utc, follower_at_utc, tape_trade_at_utc,
                        decision, rejection_reason, original_price, tape_price,
                        simulated_fill_price, filled_shares, fee_usd, payout_usd,
                        net_pnl_usd)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            scenario_id, item.source_trade_key, item.proxy_wallet,
                            item.condition_id, item.token_id, item.signal_at_utc,
                            item.follower_at_utc, item.tape_trade_at_utc,
                            "accepted" if item.accepted else "skipped",
                            item.rejection_reason, item.original_price, item.tape_price,
                            item.fill_price, item.shares, item.fee_usd,
                            item.payout_usd, item.net_pnl_usd,
                        )
                        for item in decisions
                    ],
                )
                connection.commit()

        with closing(connect(database_path)) as connection:
            connection.execute(
                "UPDATE historical_backtest_runs SET status='completed' WHERE id=?",
                (run_id,),
            )
            connection.commit()
    except Exception as exc:
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE historical_backtest_runs
                   SET status='failed', notes=notes || ? WHERE id=?""",
                (f" Failure: {exc}", run_id),
            )
            connection.commit()
        raise
    return run_id
