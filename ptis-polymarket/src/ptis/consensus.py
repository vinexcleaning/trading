from __future__ import annotations

from collections import defaultdict, deque
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Iterable

from .api import PublicApiClient
from .backtest import ReplayScenario, choose_replay_entry, parse_utc
from .collectors import (
    _iso,
    ingest_market_metadata,
    ingest_market_trade_tape,
    ingest_wallet_trades,
    utc_now,
)
from .database import connect, initialize
from .execution import taker_fee


@dataclass(frozen=True)
class ConsensusSignal:
    condition_id: str
    token_id: str
    signal_at_utc: str
    agreeing_wallets: tuple[str, ...]
    reference_price: float


@dataclass(frozen=True)
class ConsensusScenario:
    minimum_agreement: int
    agreement_window_seconds: int = 21_600
    delay_seconds: int = 60
    adverse_price_offset: float = 0.01
    max_tape_wait_seconds: int = 60
    requested_notional_usd: float = 1.0


@dataclass
class _PriorBehaviorState:
    observations: int = 0
    buys: int = 0
    reversals: int = 0
    two_sided_conditions: int = 0
    condition_tokens: dict[str, set[str]] | None = None
    previous_by_token: dict[str, tuple[str, datetime]] | None = None

    def __post_init__(self) -> None:
        self.condition_tokens = {}
        self.previous_by_token = {}

    def classification(self, minimum_observations: int = 30) -> str:
        if self.observations < minimum_observations:
            return "insufficient-prior-history"
        buy_share = self.buys / self.observations
        reversal_share = self.reversals / max(1, self.observations - 1)
        two_sided_share = self.two_sided_conditions / max(
            1, len(self.condition_tokens or {})
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

    def observe(
        self, condition: str, token: str, side: str, moment: datetime
    ) -> None:
        assert self.condition_tokens is not None
        assert self.previous_by_token is not None
        tokens = self.condition_tokens.setdefault(condition, set())
        before = len(tokens)
        if side == "BUY":
            tokens.add(token)
            self.buys += 1
        if before <= 1 and len(tokens) > 1:
            self.two_sided_conditions += 1
        previous = self.previous_by_token.get(token)
        if (
            previous
            and previous[0] != side
            and (moment - previous[1]).total_seconds() <= 3600
        ):
            self.reversals += 1
        self.previous_by_token[token] = (side, moment)
        self.observations += 1


def filter_prior_directional_buys(
    rows: Iterable[tuple[str, str, str, str, float, str]],
    *,
    minimum_observations: int = 30,
) -> list[tuple[str, str, str, float, str]]:
    """Allow a BUY vote only when that wallet looked directional beforehand."""
    ordered = sorted(rows, key=lambda row: (row[5], row[0], row[1], row[2]))
    states: dict[str, _PriorBehaviorState] = defaultdict(_PriorBehaviorState)
    accepted: list[tuple[str, str, str, float, str]] = []
    for wallet, condition, token, side, price, timestamp in ordered:
        state = states[wallet.lower()]
        if (
            side == "BUY"
            and state.classification(minimum_observations)
            == "directional-candidate"
        ):
            accepted.append(
                (wallet.lower(), condition, token, float(price), timestamp)
            )
        state.observe(condition, token, side, parse_utc(timestamp))
    return accepted


def find_consensus_signals(
    rows: Iterable[tuple[str, str, str, float, str]],
    *,
    minimum_agreement: int,
    agreement_window_seconds: int,
    reject_conflicting_conditions: bool = True,
) -> list[ConsensusSignal]:
    """Return the first same-token consensus, with one equal vote per wallet.

    Rows are ``wallet, condition_id, token_id, price, executed_at_utc``. The
    detector is outcome-blind and trade size is deliberately absent.
    """
    if minimum_agreement < 2:
        raise ValueError("minimum agreement must be at least two wallets")
    if agreement_window_seconds <= 0:
        raise ValueError("agreement window must be positive")

    grouped: dict[
        tuple[str, str], list[tuple[datetime, str, float, str]]
    ] = defaultdict(list)
    for wallet, condition, token, price, timestamp in rows:
        grouped[(condition, token)].append(
            (parse_utc(timestamp), wallet.lower(), float(price), timestamp)
        )

    found: list[ConsensusSignal] = []
    window = timedelta(seconds=agreement_window_seconds)
    for (condition, token), trades in grouped.items():
        trades.sort(key=lambda item: (item[0], item[1]))
        active: deque[tuple[datetime, str, float]] = deque()
        latest_by_wallet: dict[str, tuple[datetime, float]] = {}
        for moment, wallet, price, original_timestamp in trades:
            active.append((moment, wallet, price))
            latest_by_wallet[wallet] = (moment, price)
            cutoff = moment - window
            while active and active[0][0] < cutoff:
                old_moment, old_wallet, _ = active.popleft()
                latest = latest_by_wallet.get(old_wallet)
                if latest and latest[0] == old_moment:
                    replacement = next(
                        (
                            (candidate_moment, candidate_price)
                            for candidate_moment, candidate_wallet, candidate_price
                            in reversed(active)
                            if candidate_wallet == old_wallet
                        ),
                        None,
                    )
                    if replacement is None:
                        latest_by_wallet.pop(old_wallet, None)
                    else:
                        latest_by_wallet[old_wallet] = replacement
            if len(latest_by_wallet) >= minimum_agreement:
                agreeing = tuple(sorted(latest_by_wallet))
                found.append(
                    ConsensusSignal(
                        condition_id=condition,
                        token_id=token,
                        signal_at_utc=original_timestamp,
                        agreeing_wallets=agreeing,
                        reference_price=float(
                            median(item[1] for item in latest_by_wallet.values())
                        ),
                    )
                )
                break

    if reject_conflicting_conditions:
        tokens_by_condition: dict[str, set[str]] = defaultdict(set)
        for signal in found:
            tokens_by_condition[signal.condition_id].add(signal.token_id)
        conflicts = {
            condition
            for condition, tokens in tokens_by_condition.items()
            if len(tokens) > 1
        }
        found = [
            signal for signal in found if signal.condition_id not in conflicts
        ]
    return sorted(found, key=lambda item: (item.signal_at_utc, item.condition_id))


def latest_category_cohort(
    database_path: Path,
    category: str,
    *,
    top_traders: int,
) -> list[str]:
    initialize(database_path)
    with closing(connect(database_path)) as connection:
        return [
            row[0]
            for row in connection.execute(
                """SELECT proxy_wallet
                   FROM leaderboard_snapshots
                   WHERE category=? AND ranking_metric='PNL'
                     AND snapshot_at_utc=(
                         SELECT MAX(snapshot_at_utc)
                         FROM leaderboard_snapshots
                         WHERE category=? AND ranking_metric='PNL'
                     )
                   ORDER BY rank, proxy_wallet LIMIT ?""",
                (category.upper(), category.upper(), top_traders),
            )
        ]


def _cohort_buy_rows(
    database_path: Path,
    wallets: list[str],
    dataset_start: datetime,
    dataset_end: datetime,
    *,
    directional_only: bool = True,
) -> list[tuple[str, str, str, float, str]]:
    if not wallets:
        return []
    with closing(connect(database_path)) as connection:
        rows = connection.execute(
            """SELECT proxy_wallet, condition_id, token_id, side, price,
                      executed_at_utc
               FROM public_trades
               WHERE proxy_wallet IN ({})
                 AND executed_at_utc < ?
                 AND raw_file_path NOT LIKE '%data_api_market_tape%'
               ORDER BY executed_at_utc, trade_key""".format(
                ",".join("?" for _ in wallets)
            ),
            tuple(wallets) + (_iso(dataset_end),),
        ).fetchall()
    if directional_only:
        candidates = filter_prior_directional_buys(rows)
    else:
        candidates = [
            (wallet, condition, token, float(price), timestamp)
            for wallet, condition, token, side, price, timestamp in rows
            if side == "BUY"
        ]
    return [
        row
        for row in candidates
        if parse_utc(row[4]) >= dataset_start
    ]


def prepare_consensus_category(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    category: str,
    dataset_start: datetime,
    dataset_end: datetime,
    top_traders: int = 10,
    history_page_size: int = 500,
    history_max_pages: int = 2,
    minimum_agreement: int = 2,
    agreement_window_seconds: int = 21_600,
    max_markets: int = 25,
    tape_page_size: int = 500,
    tape_max_pages: int = 2,
) -> dict[str, int]:
    """Archive cohort histories and tapes for consensus candidate conditions."""
    wallets = latest_category_cohort(
        database_path, category, top_traders=top_traders
    )
    if not wallets:
        raise ValueError(f"no PNL leaderboard cohort is stored for {category}")

    downloaded = inserted = 0
    for wallet in wallets:
        row_count, new_count = ingest_wallet_trades(
            client,
            database_path,
            raw_dir,
            wallet=wallet,
            page_size=history_page_size,
            max_pages=history_max_pages,
        )
        downloaded += row_count
        inserted += new_count

    candidates = find_consensus_signals(
        _cohort_buy_rows(database_path, wallets, dataset_start, dataset_end),
        minimum_agreement=minimum_agreement,
        agreement_window_seconds=agreement_window_seconds,
    )
    condition_ids = list(
        dict.fromkeys(signal.condition_id for signal in candidates)
    )[:max_markets]
    metadata_saved = tape_downloaded = tape_inserted = 0
    for condition in condition_ids:
        saved, _ = ingest_market_metadata(
            client,
            database_path,
            raw_dir,
            condition_ids=[condition],
            limit=1,
        )
        metadata_saved += saved
        count, new_count = ingest_market_trade_tape(
            client,
            database_path,
            raw_dir,
            condition_id=condition,
            page_size=tape_page_size,
            max_pages=tape_max_pages,
        )
        tape_downloaded += count
        tape_inserted += new_count
    return {
        "cohort_wallets": len(wallets),
        "wallet_trades_downloaded": downloaded,
        "new_wallet_trades": inserted,
        "candidate_consensus_signals": len(candidates),
        "markets_prepared": len(condition_ids),
        "market_metadata_saved": metadata_saved,
        "tape_rows_downloaded": tape_downloaded,
        "new_tape_rows": tape_inserted,
    }


def _tape_map(
    database_path: Path, tokens: list[str]
) -> dict[str, list[tuple[str, float]]]:
    result: dict[str, list[tuple[str, float]]] = {token: [] for token in tokens}
    with closing(connect(database_path)) as connection:
        for start in range(0, len(tokens), 400):
            chunk = tokens[start : start + 400]
            if not chunk:
                continue
            rows = connection.execute(
                """SELECT token_id, executed_at_utc, price
                   FROM public_trades
                   WHERE token_id IN ({}) AND side='BUY'
                     AND raw_file_path LIKE '%data_api_market_tape%'
                   ORDER BY token_id, executed_at_utc, trade_key""".format(
                    ",".join("?" for _ in chunk)
                ),
                tuple(chunk),
            ).fetchall()
            for token, timestamp, price in rows:
                result[token].append((timestamp, float(price)))
    return result


def run_consensus_backtest(
    database_path: Path,
    *,
    categories: list[str],
    dataset_start: datetime,
    dataset_end: datetime,
    scenarios: list[ConsensusScenario],
    top_traders: int = 10,
) -> int:
    initialize(database_path)
    categories = [category.upper() for category in categories]
    notes = (
        "Approximate replay using current category PNL leaderboard cohorts. "
        "This creates survivorship/selection bias. Consensus generation is "
        "outcome-blind, equal-weighted, one vote per wallet, and rejects "
        "conditions where opposing tokens both reach consensus. A wallet may "
        "vote only when its strictly prior public behavior passes the directional "
        "gate (30+ observations, at least 75% buys, low rapid reversal rate). Entry uses the "
        "first archived public BUY after the delay, not historical L2 depth."
    )
    with closing(connect(database_path)) as connection:
        connection.execute(
            """UPDATE consensus_backtest_runs SET status='failed',
                      notes=notes || ' Interrupted run closed automatically.'
               WHERE status='running'"""
        )
        cursor = connection.execute(
            """INSERT INTO consensus_backtest_runs
               (created_at_utc, dataset_start_utc, dataset_end_utc,
                top_traders_per_category, selection_method, realism_label,
                status, notes)
               VALUES (?, ?, ?, ?, ?, 'Approximate', 'running', ?)""",
            (
                _iso(utc_now()),
                _iso(dataset_start),
                _iso(dataset_end),
                top_traders,
                "Latest stored category PNL leaderboard, top N per category",
                notes,
            ),
        )
        run_id = int(cursor.lastrowid)
        connection.commit()

    try:
        for category in categories:
            wallets = latest_category_cohort(
                database_path, category, top_traders=top_traders
            )
            rows = _cohort_buy_rows(
                database_path, wallets, dataset_start, dataset_end
            )
            for scenario in scenarios:
                signals = find_consensus_signals(
                    rows,
                    minimum_agreement=scenario.minimum_agreement,
                    agreement_window_seconds=scenario.agreement_window_seconds,
                )
                tapes = _tape_map(
                    database_path,
                    list(dict.fromkeys(signal.token_id for signal in signals)),
                )
                trade_rows: list[tuple[object, ...]] = []
                accepted_pnls: list[float] = []
                resolved = 0
                for signal in signals:
                    with closing(connect(database_path)) as connection:
                        outcome = connection.execute(
                            """SELECT winning_token_id, resolved_at_utc,
                                      COALESCE((
                                        SELECT fee_rate_decimal
                                        FROM market_observations
                                        WHERE condition_id=markets.condition_id
                                          AND fee_rate_decimal IS NOT NULL
                                        ORDER BY observed_at_utc DESC LIMIT 1
                                      ), 0)
                               FROM markets WHERE condition_id=?""",
                            (signal.condition_id,),
                        ).fetchone()
                    reason: str | None = None
                    fill: float | None = None
                    fee = payout = pnl = 0.0
                    accepted = False
                    if not outcome or not outcome[0] or not outcome[1]:
                        reason = "unresolved_or_missing_outcome"
                    else:
                        resolved += 1
                        replay = ReplayScenario(
                            delay_seconds=scenario.delay_seconds,
                            adverse_price_offset=scenario.adverse_price_offset,
                            max_tape_wait_seconds=scenario.max_tape_wait_seconds,
                            requested_notional_usd=scenario.requested_notional_usd,
                        )
                        _, fill, reason = choose_replay_entry(
                            signal_time=parse_utc(signal.signal_at_utc),
                            original_price=signal.reference_price,
                            tape_rows=tapes.get(signal.token_id, []),
                            scenario=replay,
                        )
                        if reason is None and fill is not None:
                            shares = scenario.requested_notional_usd / fill
                            fee = taker_fee(shares, fill, float(outcome[2]))
                            payout = shares if signal.token_id == outcome[0] else 0.0
                            pnl = payout - scenario.requested_notional_usd - fee
                            accepted = True
                            accepted_pnls.append(pnl)
                    trade_rows.append(
                        (
                            signal.condition_id,
                            signal.token_id,
                            signal.signal_at_utc,
                            len(signal.agreeing_wallets),
                            "accepted" if accepted else "skipped",
                            reason,
                            signal.reference_price,
                            fill,
                            fee,
                            payout,
                            pnl,
                        )
                    )
                with closing(connect(database_path)) as connection:
                    cursor = connection.execute(
                        """INSERT INTO consensus_results
                           (consensus_run_id, category, minimum_agreement,
                            agreement_window_seconds, delay_seconds,
                            adverse_price_offset, raw_consensus_signals,
                            resolved_signals, accepted_signals,
                            total_net_pnl_usd, win_rate, average_pnl_usd)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            run_id,
                            category,
                            scenario.minimum_agreement,
                            scenario.agreement_window_seconds,
                            scenario.delay_seconds,
                            scenario.adverse_price_offset,
                            len(signals),
                            resolved,
                            len(accepted_pnls),
                            sum(accepted_pnls),
                            (
                                sum(value > 0 for value in accepted_pnls)
                                / len(accepted_pnls)
                                if accepted_pnls
                                else None
                            ),
                            (
                                sum(accepted_pnls) / len(accepted_pnls)
                                if accepted_pnls
                                else None
                            ),
                        ),
                    )
                    result_id = int(cursor.lastrowid)
                    connection.executemany(
                        """INSERT INTO consensus_copy_trades
                           (consensus_result_id, condition_id, token_id,
                            signal_at_utc, agreeing_wallets, decision,
                            rejection_reason, original_reference_price,
                            simulated_fill_price, fee_usd, payout_usd,
                            net_pnl_usd)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [(result_id,) + row for row in trade_rows],
                    )
                    connection.commit()
        with closing(connect(database_path)) as connection:
            connection.execute(
                "UPDATE consensus_backtest_runs SET status='completed' WHERE id=?",
                (run_id,),
            )
            connection.commit()
    except Exception as exc:
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE consensus_backtest_runs SET status='failed',
                          notes=notes || ? WHERE id=?""",
                (f" Failure: {exc}", run_id),
            )
            connection.commit()
        raise
    return run_id
