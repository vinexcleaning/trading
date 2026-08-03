from __future__ import annotations

import argparse
import logging
from contextlib import closing
from datetime import timedelta

from .analysis import assess_trader, rebuild_positions
from .api import PublicApiClient, PublicApiError
from .backtest import (
    ReplayScenario,
    prepare_historical_data,
    run_historical_replay,
)
from .consensus import (
    ConsensusScenario,
    prepare_consensus_category,
    run_consensus_backtest,
)
from .collectors import (
    discover_candidates,
    ingest_market_metadata,
    ingest_wallet_trades,
    snapshot_orderbook,
    utc_now,
)
from .config import Settings
from .database import connect, initialize
from .monitor import (
    evaluate_pending_signals,
    invalidate_monitor_session,
    run_live_monitor,
    settle_paper_positions,
)
from .paper import invalidate_paper_run, run_shadow_scan
from .reports import (
    write_consensus_backtest_report,
    write_historical_backtest_report,
    write_research_report,
)
from .validation import run_quality_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PTIS public-data research tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="create the SQLite research database")

    discover = subparsers.add_parser("discover", help="capture a leaderboard candidate cohort")
    discover.add_argument("--limit", type=int, default=50)
    discover.add_argument("--category", default="OVERALL")
    discover.add_argument("--time-period", default="MONTH")
    discover.add_argument("--order-by", choices=("PNL", "VOL"), default="PNL")

    trades = subparsers.add_parser("ingest-trades", help="archive public trades for one wallet")
    trades.add_argument("--wallet", required=True)
    trades.add_argument("--page-size", type=int, default=500)
    trades.add_argument("--max-pages", type=int, default=20)

    markets = subparsers.add_parser(
        "ingest-markets", help="resolve stored trade conditions and fee observations"
    )
    markets.add_argument("--limit", type=int, default=100)
    markets.add_argument("--condition-id", action="append", dest="condition_ids")

    positions = subparsers.add_parser(
        "rebuild-positions", help="reconstruct positions from observed trades"
    )
    positions.add_argument("--wallet", required=True)

    assessment = subparsers.add_parser(
        "assess-trader", help="calculate preliminary behavior classification"
    )
    assessment.add_argument("--wallet", required=True)

    subparsers.add_parser("validate-data", help="run and save data-quality checks")

    shadow = subparsers.add_parser(
        "shadow-scan", help="run a current-market paper-only scan"
    )
    shadow.add_argument("--wallet", action="append", dest="wallets")
    shadow.add_argument("--top-candidates", type=int, default=3)
    shadow.add_argument("--delay-seconds", type=int, default=5)
    shadow.add_argument("--max-signal-age-seconds", type=int, default=300)
    shadow.add_argument("--notional-usd", type=float, default=1.0)
    shadow.add_argument("--max-signals", type=int, default=5)

    invalidate = subparsers.add_parser(
        "invalidate-paper-run", help="mark a paper run invalid without deleting it"
    )
    invalidate.add_argument("--run-id", type=int, required=True)
    invalidate.add_argument("--reason", required=True)

    monitor = subparsers.add_parser(
        "monitor", help="prospectively monitor wallets and paper-evaluate new trades"
    )
    monitor.add_argument("--wallet", action="append", dest="wallets", required=True)
    monitor.add_argument("--cycles", type=int, default=4)
    monitor.add_argument("--interval-seconds", type=int, default=15)
    monitor.add_argument("--delay-seconds", type=int, default=5)
    monitor.add_argument("--notional-usd", type=float, default=1.0)
    monitor.add_argument("--max-visibility-delay-seconds", type=int, default=300)
    monitor.add_argument("--max-signals-per-cycle", type=int, default=3)

    subparsers.add_parser(
        "settle-paper", help="settle open paper positions with archived official outcomes"
    )

    invalidate_monitor = subparsers.add_parser(
        "invalidate-monitor", help="mark an interrupted monitor session failed"
    )
    invalidate_monitor.add_argument("--session-id", type=int, required=True)
    invalidate_monitor.add_argument("--reason", required=True)

    pending = subparsers.add_parser(
        "evaluate-pending", help="paper-evaluate live signals not in a completed run"
    )
    pending.add_argument("--limit", type=int, default=2)
    pending.add_argument("--delay-seconds", type=int, default=5)
    pending.add_argument("--notional-usd", type=float, default=1.0)
    pending.add_argument("--max-visibility-delay-seconds", type=int, default=300)

    prepare_history = subparsers.add_parser(
        "prepare-history", help="archive bounded market tapes for historical replay"
    )
    prepare_history.add_argument("--wallet", action="append", dest="wallets", required=True)
    prepare_history.add_argument("--days", type=int, default=7)
    prepare_history.add_argument("--max-markets", type=int, default=5)
    prepare_history.add_argument("--tape-page-size", type=int, default=500)
    prepare_history.add_argument("--tape-max-pages", type=int, default=2)

    replay = subparsers.add_parser(
        "backtest-week", help="run the approximate one-week scenario matrix"
    )
    replay.add_argument("--wallet", action="append", dest="wallets", required=True)
    replay.add_argument("--days", type=int, default=7)
    replay.add_argument(
        "--output", default="outputs/HISTORICAL_BACKTEST_REPORT.md"
    )

    prepare_consensus = subparsers.add_parser(
        "prepare-consensus",
        help="archive a category cohort and candidate consensus market tapes",
    )
    prepare_consensus.add_argument("--category", required=True)
    prepare_consensus.add_argument("--days", type=int, default=14)
    prepare_consensus.add_argument("--top-traders", type=int, default=10)
    prepare_consensus.add_argument("--max-markets", type=int, default=25)
    prepare_consensus.add_argument("--minimum-agreement", type=int, default=2)
    prepare_consensus.add_argument("--window-hours", type=float, default=6)
    prepare_consensus.add_argument("--history-page-size", type=int, default=500)
    prepare_consensus.add_argument("--history-max-pages", type=int, default=2)
    prepare_consensus.add_argument("--tape-page-size", type=int, default=500)
    prepare_consensus.add_argument("--tape-max-pages", type=int, default=2)

    consensus = subparsers.add_parser(
        "backtest-consensus",
        help="compare historical specialist-cohort consensus scenarios",
    )
    consensus.add_argument(
        "--category", action="append", dest="categories", required=True
    )
    consensus.add_argument("--days", type=int, default=14)
    consensus.add_argument("--top-traders", type=int, default=10)
    consensus.add_argument(
        "--output", default="outputs/CONSENSUS_BACKTEST_REPORT.md"
    )

    report = subparsers.add_parser("report", help="write the current research status report")
    report.add_argument(
        "--output",
        default="outputs/PTIS_RESEARCH_STATUS.md",
    )

    book = subparsers.add_parser("snapshot-book", help="archive one current order book")
    book.add_argument("--token-id", required=True)
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args()
    settings = Settings.default()
    client = PublicApiClient(timeout_seconds=settings.request_timeout_seconds)
    try:
        if args.command == "init-db":
            initialize(settings.database_path)
            logging.info("Database initialized at %s", settings.database_path)
        elif args.command == "discover":
            count = discover_candidates(
                client,
                settings.database_path,
                settings.raw_data_dir,
                limit=args.limit,
                category=args.category,
                time_period=args.time_period,
                order_by=args.order_by,
            )
            logging.info("Saved %d point-in-time leaderboard candidates", count)
        elif args.command == "snapshot-book":
            snapshot_id = snapshot_orderbook(
                client,
                settings.database_path,
                settings.raw_data_dir,
                token_id=args.token_id,
            )
            logging.info("Saved order-book snapshot %d", snapshot_id)
        elif args.command == "ingest-trades":
            downloaded, inserted = ingest_wallet_trades(
                client,
                settings.database_path,
                settings.raw_data_dir,
                wallet=args.wallet,
                page_size=args.page_size,
                max_pages=args.max_pages,
            )
            logging.info(
                "Downloaded %d trades; inserted %d previously unseen trades",
                downloaded,
                inserted,
            )
        elif args.command == "ingest-markets":
            markets, fee_observations = ingest_market_metadata(
                client,
                settings.database_path,
                settings.raw_data_dir,
                condition_ids=args.condition_ids,
                limit=args.limit,
            )
            logging.info(
                "Saved %d markets and %d token fee observations",
                markets,
                fee_observations,
            )
        elif args.command == "rebuild-positions":
            count = rebuild_positions(settings.database_path, args.wallet)
            logging.info("Reconstructed %d outcome-token positions", count)
        elif args.command == "assess-trader":
            result = assess_trader(settings.database_path, args.wallet)
            logging.info("Trader assessment: %s", result)
        elif args.command == "validate-data":
            findings = run_quality_checks(settings.database_path)
            for finding in findings:
                logging.info(
                    "%s: %s affected=%d",
                    finding["severity"],
                    finding["check_name"],
                    finding["affected_rows"],
                )
        elif args.command == "shadow-scan":
            wallets = args.wallets
            if not wallets:
                with closing(connect(settings.database_path)) as connection:
                    wallets = [
                        row[0]
                        for row in connection.execute(
                            """SELECT proxy_wallet FROM leaderboard_snapshots
                               WHERE snapshot_at_utc=(
                                   SELECT MAX(snapshot_at_utc) FROM leaderboard_snapshots
                               )
                               ORDER BY rank LIMIT ?""",
                            (args.top_candidates,),
                        )
                    ]
            if not wallets:
                raise ValueError("no candidate wallets are available")
            result = run_shadow_scan(
                client,
                settings.database_path,
                settings.raw_data_dir,
                wallets=wallets,
                detection_delay_seconds=args.delay_seconds,
                max_signal_age_seconds=args.max_signal_age_seconds,
                requested_notional_usd=args.notional_usd,
                max_signals=args.max_signals,
            )
            logging.info("Shadow scan: %s", result)
        elif args.command == "report":
            output = write_research_report(
                settings.database_path,
                settings.project_root / args.output,
            )
            logging.info("Report written to %s", output)
        elif args.command == "invalidate-paper-run":
            invalidate_paper_run(settings.database_path, args.run_id, args.reason)
            logging.info("Paper run %d marked invalid", args.run_id)
        elif args.command == "monitor":
            result = run_live_monitor(
                client,
                settings.database_path,
                settings.raw_data_dir,
                wallets=args.wallets,
                cycles=args.cycles,
                polling_interval_seconds=args.interval_seconds,
                detection_delay_seconds=args.delay_seconds,
                requested_notional_usd=args.notional_usd,
                max_visibility_delay_seconds=args.max_visibility_delay_seconds,
                max_signals_per_cycle=args.max_signals_per_cycle,
            )
            logging.info("Monitor result: %s", result)
        elif args.command == "settle-paper":
            result = settle_paper_positions(settings.database_path)
            logging.info("Settlement result: %s", result)
        elif args.command == "invalidate-monitor":
            invalidate_monitor_session(
                settings.database_path, args.session_id, args.reason
            )
            logging.info("Monitor session %d marked invalid", args.session_id)
        elif args.command == "evaluate-pending":
            result = evaluate_pending_signals(
                client,
                settings.database_path,
                settings.raw_data_dir,
                limit=args.limit,
                detection_delay_seconds=args.delay_seconds,
                requested_notional_usd=args.notional_usd,
                max_visibility_delay_seconds=args.max_visibility_delay_seconds,
            )
            logging.info("Pending evaluation result: %s", result)
        elif args.command == "prepare-history":
            dataset_end = utc_now()
            dataset_start = dataset_end - timedelta(days=args.days)
            result = prepare_historical_data(
                client,
                settings.database_path,
                settings.raw_data_dir,
                wallets=args.wallets,
                dataset_start=dataset_start,
                dataset_end=dataset_end,
                max_markets=args.max_markets,
                tape_page_size=args.tape_page_size,
                tape_max_pages=args.tape_max_pages,
            )
            logging.info("Historical preparation: %s", result)
        elif args.command == "backtest-week":
            dataset_end = utc_now()
            dataset_start = dataset_end - timedelta(days=args.days)
            scenarios = [
                ReplayScenario(delay_seconds=delay, adverse_price_offset=adverse)
                for delay in (0, 5, 15, 60)
                for adverse in (0.0, 0.01, 0.02)
            ]
            run_id = run_historical_replay(
                settings.database_path,
                wallets=args.wallets,
                dataset_start=dataset_start,
                dataset_end=dataset_end,
                scenarios=scenarios,
            )
            output = write_historical_backtest_report(
                settings.database_path,
                settings.project_root / args.output,
            )
            logging.info("Historical replay %d written to %s", run_id, output)
        elif args.command == "prepare-consensus":
            dataset_end = utc_now()
            dataset_start = dataset_end - timedelta(days=args.days)
            result = prepare_consensus_category(
                client,
                settings.database_path,
                settings.raw_data_dir,
                category=args.category,
                dataset_start=dataset_start,
                dataset_end=dataset_end,
                top_traders=args.top_traders,
                minimum_agreement=args.minimum_agreement,
                agreement_window_seconds=int(args.window_hours * 3600),
                max_markets=args.max_markets,
                history_page_size=args.history_page_size,
                history_max_pages=args.history_max_pages,
                tape_page_size=args.tape_page_size,
                tape_max_pages=args.tape_max_pages,
            )
            logging.info("Consensus preparation: %s", result)
        elif args.command == "backtest-consensus":
            dataset_end = utc_now()
            dataset_start = dataset_end - timedelta(days=args.days)
            scenarios = [
                ConsensusScenario(
                    minimum_agreement=agreement,
                    delay_seconds=delay,
                    adverse_price_offset=adverse,
                )
                for agreement in (2, 3, 4)
                for delay in (15, 60)
                for adverse in (0.0, 0.01, 0.02)
            ]
            run_id = run_consensus_backtest(
                settings.database_path,
                categories=args.categories,
                dataset_start=dataset_start,
                dataset_end=dataset_end,
                scenarios=scenarios,
                top_traders=args.top_traders,
            )
            output = write_consensus_backtest_report(
                settings.database_path,
                settings.project_root / args.output,
            )
            logging.info("Consensus replay %d written to %s", run_id, output)
    except (PublicApiError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
