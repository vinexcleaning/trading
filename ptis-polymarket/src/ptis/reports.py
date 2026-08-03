from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .database import connect


def write_research_report(database_path: Path, output_path: Path) -> Path:
    with closing(connect(database_path)) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "traders",
                "leaderboard_snapshots",
                "public_trades",
                "markets",
                "orderbook_snapshots",
                "trader_assessments",
                "paper_runs",
                "paper_trades",
                "monitor_sessions",
                "live_trade_first_seen",
                "paper_positions",
            )
        }
        latest_assessments = connection.execute(
            """SELECT a.proxy_wallet, a.classification,
                      a.preliminary_copyability_score, a.observation_count,
                      a.market_count
               FROM trader_assessments a
               JOIN (
                   SELECT proxy_wallet, MAX(assessed_at_utc) AS latest
                   FROM trader_assessments GROUP BY proxy_wallet
               ) latest ON latest.proxy_wallet=a.proxy_wallet
                       AND latest.latest=a.assessed_at_utc
               ORDER BY a.preliminary_copyability_score DESC"""
        ).fetchall()
        quality = connection.execute(
            """SELECT check_name, severity, affected_rows, details
               FROM data_quality_findings
               WHERE checked_at_utc=(SELECT MAX(checked_at_utc) FROM data_quality_findings)
               ORDER BY CASE severity WHEN 'error' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END"""
        ).fetchall()
        latest_run = connection.execute(
            """SELECT id, started_at_utc, detection_delay_seconds, status, notes
               FROM paper_runs ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        latest_monitor = connection.execute(
            """SELECT id, started_at_utc, completed_at_utc, requested_cycles,
                      completed_cycles, wallet_count, status, notes
               FROM monitor_sessions ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        latency = connection.execute(
            """SELECT COUNT(*), AVG(visibility_delay_seconds),
                      MIN(visibility_delay_seconds), MAX(visibility_delay_seconds)
               FROM live_trade_first_seen WHERE was_baseline=0"""
        ).fetchone()
        prospective_decisions = connection.execute(
            """SELECT pt.decision, COALESCE(pt.rejection_reason, 'accepted'), COUNT(*)
               FROM paper_trades pt
               JOIN paper_runs pr ON pr.id=pt.paper_run_id
               JOIN live_trade_first_seen s ON s.trade_key=pt.source_trade_key
               WHERE pr.status='completed' AND s.was_baseline=0
               GROUP BY pt.decision, COALESCE(pt.rejection_reason, 'accepted')
               ORDER BY COUNT(*) DESC"""
        ).fetchall()
        portfolio_summary = connection.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(t.filled_notional_usd + t.fee_usd), 0),
                      COALESCE(SUM(CASE WHEN p.status='resolved'
                                       THEN p.net_pnl_usd ELSE 0 END), 0)
               FROM paper_positions p
               JOIN paper_trades t ON t.id=p.paper_trade_id"""
        ).fetchone()
        open_positions = connection.execute(
            """SELECT t.proxy_wallet, COALESCE(m.question, t.condition_id),
                      t.original_trade_price, t.average_fill_price,
                      t.filled_notional_usd, t.fee_usd, t.filled_shares,
                      p.status, p.net_pnl_usd
               FROM paper_positions p
               JOIN paper_trades t ON t.id=p.paper_trade_id
               LEFT JOIN markets m ON m.condition_id=t.condition_id
               ORDER BY p.id"""
        ).fetchall()
        decisions = []
        paper_details = []
        if latest_run:
            decisions = connection.execute(
                """SELECT decision, COALESCE(rejection_reason, 'accepted'), COUNT(*)
                   FROM paper_trades WHERE paper_run_id=?
                   GROUP BY decision, COALESCE(rejection_reason, 'accepted')
                   ORDER BY COUNT(*) DESC""",
                (latest_run[0],),
            ).fetchall()
            paper_details = connection.execute(
                """SELECT proxy_wallet, decision, COALESCE(rejection_reason, 'accepted'),
                          original_trade_price, best_ask, average_fill_price,
                          filled_notional_usd, fee_usd, slippage_usd
                   FROM paper_trades WHERE paper_run_id=?
                   ORDER BY id""",
                (latest_run[0],),
            ).fetchall()

    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines = [
        "# PTIS Research and Shadow-Paper Status",
        "",
        f"Generated: {generated}",
        "",
        "## Decision-useful summary",
        "",
        "The system now supports public-data candidate discovery, bounded wallet trade",
        "ingestion, market and fee metadata, validation, behavior classification,",
        "depth-based execution simulation, conservative $100-bankroll controls, and",
        "current-market paper scans. It still does not establish profitability.",
        "",
        "Historical execution remains approximate until prospective books and measured",
        "first-visibility times accumulate. Preliminary trader scores are capped at 60",
        "because delayed copy P&L and out-of-sample evidence are not yet available.",
        "",
        "## Evidence inventory",
        "",
        "| Record type | Rows |",
        "|---|---:|",
    ]
    lines.extend(f"| {name.replace('_', ' ').title()} | {value} |" for name, value in counts.items())
    lines.extend(
        [
            "",
            "## Preliminary trader behavior assessments",
            "",
            "| Wallet | Classification | Score (max 60) | Trades | Markets |",
            "|---|---|---:|---:|---:|",
        ]
    )
    if latest_assessments:
        lines.extend(
            f"| `{wallet}` | {classification} | {score:.1f} | {trades} | {markets} |"
            for wallet, classification, score, trades, markets in latest_assessments
        )
    else:
        lines.append("| — | No assessments yet | — | — | — |")
    lines.extend(
        [
            "",
            "## Latest data-quality checks",
            "",
            "| Check | Severity | Affected rows | Meaning |",
            "|---|---|---:|---|",
        ]
    )
    if quality:
        lines.extend(
            f"| {name} | {severity} | {affected} | {details} |"
            for name, severity, affected, details in quality
        )
    else:
        lines.append("| — | — | — | Checks have not run |")
    lines.extend(["", "## Latest current-market paper scan", ""])
    if latest_run:
        lines.append(
            f"Run {latest_run[0]} started at {latest_run[1]} with a "
            f"{latest_run[2]}-second follower delay; status: {latest_run[3]}. "
            f"Notes: {latest_run[4] or '—'}"
        )
        lines.extend(
            [
                "",
                "| Decision | Reason | Signals |",
                "|---|---|---:|",
            ]
        )
        lines.extend(f"| {decision} | {reason} | {count} |" for decision, reason, count in decisions)
        lines.extend(
            [
                "",
                "| Wallet | Decision | Reason | Original | Best ask | Fill | Notional | Fee | Slippage |",
                "|---|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in paper_details:
            wallet, decision, reason, original, ask, fill, notional, fee, slippage = row
            lines.append(
                f"| `{wallet}` | {decision} | {reason} | {original:.4f} | "
                f"{'—' if ask is None else f'{ask:.4f}'} | "
                f"{'—' if fill is None else f'{fill:.4f}'} | "
                f"${notional:.4f} | ${fee:.6f} | ${slippage:.6f} |"
            )
    else:
        lines.append("No paper scan has run.")
    lines.extend(["", "## Prospective monitoring status", ""])
    if latest_monitor:
        lines.append(
            f"Session {latest_monitor[0]} started at {latest_monitor[1]}; "
            f"status: {latest_monitor[6]}; completed "
            f"{latest_monitor[4]} of {latest_monitor[3]} requested cycles across "
            f"{latest_monitor[5]} wallets. Notes: {latest_monitor[7] or '—'}"
        )
    else:
        lines.append("No prospective monitor session has run.")
    observed_count, average_delay, minimum_delay, maximum_delay = latency
    if observed_count:
        lines.append(
            f"\nGenuinely new trades first-seen after baseline: {observed_count}. "
            f"Visibility delay averaged {average_delay:.1f}s "
            f"(range {minimum_delay:.1f}s–{maximum_delay:.1f}s)."
        )
    else:
        lines.append("\nNo genuinely new post-baseline trades have been observed yet.")
    lines.extend(
        [
            "",
            "### Completed prospective signal decisions",
            "",
            "| Decision | Reason | Signals |",
            "|---|---|---:|",
        ]
    )
    if prospective_decisions:
        lines.extend(
            f"| {decision} | {reason} | {count} |"
            for decision, reason, count in prospective_decisions
        )
    else:
        lines.append("| — | No completed prospective decisions | 0 |")
    position_count, invested, resolved_pnl = portfolio_summary
    lines.extend(
        [
            "",
            "## Paper portfolio",
            "",
            f"The ledger contains {position_count} paper positions with "
            f"${invested:.4f} of cost and fees. Realized resolution P&L is "
            f"${resolved_pnl:.4f}; unresolved positions must not be counted as profit.",
            "",
            "| Wallet | Market | Original | Fill | Cost | Fee | Shares | Status | Net P&L |",
            "|---|---|---:|---:|---:|---:|---:|---|---:|",
        ]
    )
    if open_positions:
        for wallet, question, original, fill, notional, fee, shares, status, pnl in open_positions:
            clean_question = str(question).replace("|", "/")
            lines.append(
                f"| `{wallet}` | {clean_question} | {original:.4f} | {fill:.4f} | "
                f"${notional:.4f} | ${fee:.6f} | {shares:.4f} | {status} | "
                f"{'—' if pnl is None else f'${pnl:.4f}'} |"
            )
    else:
        lines.append("| — | No positions | — | — | — | — | — | — | — |")
    lines.extend(
        [
            "",
            "## Interpretation and next evidence needs",
            "",
            "- Accepted paper signals are simulated fills, not real orders or evidence of profit.",
            "- A scan with zero eligible signals is a valid latency/liquidity result, not a failure.",
            "- The next milestone is sustained prospective collection across multiple candidates.",
            "- Copy P&L should be evaluated only after outcomes resolve and untouched test data exists.",
            "- Hidden hedges, linked wallets, and off-platform activity remain unobservable risks.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_historical_backtest_report(database_path: Path, output_path: Path) -> Path:
    with closing(connect(database_path)) as connection:
        run = connection.execute(
            """SELECT id, created_at_utc, dataset_start_utc, dataset_end_utc,
                      selection_method, realism_label, starting_bankroll_usd,
                      status, notes
               FROM historical_backtest_runs
               WHERE status='completed' ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        if not run:
            raise ValueError("no completed historical backtest is available")
        scenarios = connection.execute(
            """SELECT id, delay_seconds, adverse_price_offset,
                      signals_considered, trades_accepted, trades_skipped,
                      total_net_pnl_usd, return_on_bankroll,
                      maximum_drawdown_usd, win_rate, profit_factor,
                      largest_trade_profit_share, execution_eligible_signals,
                      signal_level_net_pnl_usd, signal_level_win_rate
               FROM historical_scenarios WHERE backtest_run_id=?
               ORDER BY delay_seconds, adverse_price_offset""",
            (run[0],),
        ).fetchall()
        skip_reasons = connection.execute(
            """SELECT s.delay_seconds, s.adverse_price_offset,
                      t.rejection_reason, COUNT(*)
               FROM historical_copy_trades t
               JOIN historical_scenarios s ON s.id=t.scenario_id
               WHERE s.backtest_run_id=? AND t.decision='skipped'
               GROUP BY s.delay_seconds, s.adverse_price_offset, t.rejection_reason
               ORDER BY s.delay_seconds, s.adverse_price_offset, COUNT(*) DESC""",
            (run[0],),
        ).fetchall()
        diagnostic_scenario = connection.execute(
            """SELECT id FROM historical_scenarios
               WHERE backtest_run_id=? AND delay_seconds=60
                 AND ABS(adverse_price_offset - 0.01) < 0.0000001
               LIMIT 1""",
            (run[0],),
        ).fetchone()
        trader_breakdown = []
        category_breakdown = []
        if diagnostic_scenario:
            trader_breakdown = connection.execute(
                """SELECT t.proxy_wallet, COUNT(*), SUM(t.net_pnl_usd),
                          AVG(t.net_pnl_usd),
                          AVG(CASE WHEN t.net_pnl_usd > 0 THEN 1.0 ELSE 0.0 END)
                   FROM historical_copy_trades t
                   WHERE t.scenario_id=? AND t.filled_shares > 0
                   GROUP BY t.proxy_wallet
                   ORDER BY SUM(t.net_pnl_usd) DESC""",
                (diagnostic_scenario[0],),
            ).fetchall()
            category_breakdown = connection.execute(
                """SELECT COALESCE(m.category, 'Unknown'), COUNT(*),
                          SUM(t.net_pnl_usd), AVG(t.net_pnl_usd)
                   FROM historical_copy_trades t
                   LEFT JOIN markets m ON m.condition_id=t.condition_id
                   WHERE t.scenario_id=? AND t.filled_shares > 0
                   GROUP BY COALESCE(m.category, 'Unknown')
                   ORDER BY SUM(t.net_pnl_usd) DESC""",
                (diagnostic_scenario[0],),
            ).fetchall()

    realistic = [
        row for row in scenarios
        if row[1] >= 5 and row[2] >= 0.01 and row[4] >= 10
    ]
    if not realistic:
        conclusion = (
            "Insufficient evidence: no realistic scenario produced at least 10 "
            "accepted resolved trades."
        )
    elif all(row[6] > 0 for row in realistic):
        conclusion = (
            "Promising but not validated: every adequately sampled realistic "
            "scenario was positive, but selection bias and tape-price approximation remain."
        )
    elif all(row[6] <= 0 for row in realistic):
        conclusion = (
            "Early negative evidence: every realistic scenario with at least 10 "
            "accepted resolved trades lost money. The sample remains too small "
            "for a final strategy verdict."
        )
    else:
        conclusion = (
            "Fragile: adequately sampled realistic scenarios disagree on profitability."
        )

    lines = [
        "# One-Week Historical Shadow-Copy Replay",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        "",
        "## Result",
        "",
        f"**{conclusion}**",
        "",
        "This is an approximate retrospective diagnostic, not an exact fill backtest.",
        "The replay does not reveal outcomes to entry selection. Outcomes are joined",
        "only after simulated entry for hold-to-resolution settlement.",
        "",
        "## Scope and evidence quality",
        "",
        f"- Dataset window: {run[2]} through {run[3]}",
        f"- Starting paper bankroll: ${run[6]:.2f}",
        f"- Realism label: {run[5]}",
        f"- Selection method: {run[4]}",
        f"- Method limitation: {run[8]}",
        "- Cash baseline: $0 P&L and 0% return.",
        "",
        "Official historical order-book depth was unavailable. Each follower entry",
        "uses the first subsequent public BUY trade within the allowed wait, then",
        "adds the scenario's adverse-price offset. This can neither prove fillability",
        "nor measure historical slippage for a $1 order.",
        "",
        "## Scenario results",
        "",
        "| Delay | Adverse price | Signals | Portfolio accepted | Portfolio P&L | Return | Drawdown | Portfolio win rate | Eligible signals | Signal-level P&L | Signal win rate |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in scenarios:
        (
            _, delay, adverse, signals, accepted, _, pnl, return_value,
            drawdown, win_rate, profit_factor, largest_share,
            eligible_count, signal_pnl, signal_win_rate,
        ) = row
        lines.append(
            f"| {delay}s | {adverse:.3f} | {signals} | {accepted} | "
            f"${pnl:.4f} | {return_value:.2%} | ${drawdown:.4f} | "
            f"{'—' if win_rate is None else f'{win_rate:.1%}'} | "
            f"{eligible_count} | ${signal_pnl:.4f} | "
            f"{'—' if signal_win_rate is None else f'{signal_win_rate:.1%}'} |"
        )
    lines.extend(
        [
            "",
            "## Skip reasons by scenario",
            "",
            "| Delay | Adverse price | Reason | Signals |",
            "|---:|---:|---|---:|",
        ]
    )
    lines.extend(
        f"| {delay}s | {adverse:.3f} | {reason} | {count} |"
        for delay, adverse, reason, count in skip_reasons
    )
    lines.extend(
        [
            "",
            "## Sixty-second, one-cent diagnostic by trader",
            "",
            "This view ignores portfolio-cap rejections after a signal passed the",
            "entry-price, timing, outcome-availability, and fee checks.",
            "",
            "| Wallet | Eligible signals | Signal-level P&L | Average P&L | Win rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    if trader_breakdown:
        lines.extend(
            f"| `{wallet}` | {count} | ${pnl:.4f} | ${average:.4f} | {win_rate:.1%} |"
            for wallet, count, pnl, average, win_rate in trader_breakdown
        )
    else:
        lines.append("| — | 0 | $0.0000 | — | — |")
    lines.extend(
        [
            "",
            "## Sixty-second, one-cent diagnostic by category",
            "",
            "| Category | Eligible signals | Signal-level P&L | Average P&L |",
            "|---|---:|---:|---:|",
        ]
    )
    if category_breakdown:
        lines.extend(
            f"| {category} | {count} | ${pnl:.4f} | ${average:.4f} |"
            for category, count, pnl, average in category_breakdown
        )
    else:
        lines.append("| — | 0 | $0.0000 | — |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Zero-second scenarios are theoretical upper bounds.",
            "- Current-session leaderboard selection creates survivorship/selection bias.",
            "- Current archived fees may differ from the exact historical fee schedule.",
            "- A positive result is hypothesis-generating until walk-forward cohorts and",
            "  prospectively collected order books reproduce it.",
            "- A negative result is still useful evidence against this copy route.",
            "",
            "## Recommended testing horizon",
            "",
            "- Minimum decision sample: 100 resolved, strategy-eligible paper trades.",
            "- Minimum diversity: at least 30 trades outside the dominant wallet and",
            "  at least three market categories with usable metadata.",
            "- Minimum live duration: four weeks; extend to eight–twelve weeks if",
            "  fewer than 25 qualifying trades resolve per week.",
            "- Early stop: pause the broad strategy if the first 30 resolved live",
            "  trades are materially negative after costs and no predeclared segment",
            "  remains positive.",
            "- Promotion rule: require positive results at measured visibility delays,",
            "  under 1¢ and 2¢ stress, in an untouched later window.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_consensus_backtest_report(
    database_path: Path, output_path: Path
) -> Path:
    with closing(connect(database_path)) as connection:
        run = connection.execute(
            """SELECT id, created_at_utc, dataset_start_utc, dataset_end_utc,
                      top_traders_per_category, selection_method,
                      realism_label, notes
               FROM consensus_backtest_runs
               WHERE status='completed' ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        if not run:
            raise ValueError("no completed consensus backtest is available")
        results = connection.execute(
            """SELECT category, minimum_agreement, agreement_window_seconds,
                      delay_seconds, adverse_price_offset,
                      raw_consensus_signals, resolved_signals,
                      accepted_signals, total_net_pnl_usd, win_rate,
                      average_pnl_usd
               FROM consensus_results
               WHERE consensus_run_id=?
               ORDER BY category, minimum_agreement, delay_seconds,
                        adverse_price_offset""",
            (run[0],),
        ).fetchall()
        cohort_counts = connection.execute(
            """WITH latest AS (
                   SELECT category, MAX(snapshot_at_utc) AS snapshot_at_utc
                   FROM leaderboard_snapshots
                   WHERE ranking_metric='PNL'
                   GROUP BY category
               ), cohort AS (
                   SELECT s.category, s.proxy_wallet
                   FROM leaderboard_snapshots s
                   JOIN latest l ON l.category=s.category
                                AND l.snapshot_at_utc=s.snapshot_at_utc
                   WHERE s.ranking_metric='PNL'
               )
               SELECT c.category, COUNT(DISTINCT c.proxy_wallet),
                      MIN(CASE WHEN t.raw_file_path NOT LIKE
                          '%data_api_market_tape%' THEN t.executed_at_utc END),
                      MAX(CASE WHEN t.raw_file_path NOT LIKE
                          '%data_api_market_tape%' THEN t.executed_at_utc END)
               FROM cohort c
               LEFT JOIN public_trades t ON t.proxy_wallet=c.proxy_wallet
               GROUP BY c.category"""
        ).fetchall()
        broad_run = connection.execute(
            """SELECT MAX(id) FROM consensus_backtest_runs
               WHERE status='completed' AND id < ?
                 AND notes NOT LIKE '%directional gate%'""",
            (run[0],),
        ).fetchone()
        broad_control = []
        if broad_run and broad_run[0]:
            broad_control = connection.execute(
                """SELECT category, raw_consensus_signals, resolved_signals,
                          accepted_signals, total_net_pnl_usd, win_rate
                   FROM consensus_results
                   WHERE consensus_run_id=? AND minimum_agreement=2
                     AND delay_seconds=60
                     AND ABS(adverse_price_offset - 0.01) < 0.0000001
                   ORDER BY category""",
                (broad_run[0],),
            ).fetchall()

    main_rows = [
        row
        for row in results
        if row[1] == 3
        and row[3] == 60
        and abs(row[4] - 0.01) < 0.0000001
    ]
    validated = [
        row for row in main_rows if row[7] >= 20 and row[8] > 0
    ]
    if validated:
        best = max(validated, key=lambda row: (row[8], row[7]))
        result_text = (
            f"{best[0]} is the strongest historically promising cohort in the "
            "predeclared main setting, but it is not proof of future profit."
        )
    else:
        best = max(
            main_rows,
            key=lambda row: (row[8], row[7]),
            default=None,
        )
        result_text = (
            "No niche is historically validated. None produced both positive "
            "after-cost P&L and at least 20 accepted resolved consensus entries "
            "in the predeclared main setting."
        )

    lines = [
        "# Specialist Consensus Historical Backtest",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        "",
        "## Bottom line",
        "",
        f"**{result_text}**",
        "",
        "This test asks whether several current category leaders buying the same",
        "outcome within six hours would have been profitable historically. It uses",
        "one equal vote per wallet, ignores whale size, rejects opposing-outcome",
        "consensus, and reveals the winner only during settlement.",
        "",
        "## Evidence quality",
        "",
        f"- Window: {run[2]} through {run[3]}",
        f"- Cohort size requested per niche: {run[4]}",
        f"- Selection: {run[5]}",
        f"- Realism: {run[6]}",
        f"- Limitation: {run[7]}",
        "- Each accepted signal risks a flat $1 paper notional and holds to resolution.",
        "- The main setting is 3 agreeing wallets, a 6-hour agreement window,",
        "  60-second delay, and 1-cent adverse execution stress.",
        "",
        "## Main-setting comparison",
        "",
        "| Niche cohort | Raw consensus | Resolved | Accepted | Net P&L | Average | Win rate | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in main_rows:
        category, _, _, _, _, raw, resolved, accepted, pnl, win_rate, average = row
        verdict = (
            "promising, not proven"
            if accepted >= 20 and pnl > 0
            else "negative"
            if accepted >= 20 and pnl <= 0
            else "insufficient sample"
        )
        lines.append(
            f"| {category} | {raw} | {resolved} | {accepted} | "
            f"${pnl:.4f} | "
            f"{'—' if average is None else f'${average:.4f}'} | "
            f"{'—' if win_rate is None else f'{win_rate:.1%}'} | {verdict} |"
        )
    if not main_rows:
        lines.append("| — | 0 | 0 | 0 | $0.0000 | — | — | insufficient data |")

    lines.extend(
        [
            "",
            "## Full sensitivity matrix",
            "",
            "| Niche | Votes | Window | Delay | Stress | Raw | Resolved | Accepted | P&L | Win rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in results:
        category, agreement, window, delay, adverse, raw, resolved, accepted, pnl, win_rate, _ = row
        lines.append(
            f"| {category} | {agreement} | {window / 3600:.0f}h | {delay}s | "
            f"{adverse:.3f} | {raw} | {resolved} | {accepted} | ${pnl:.4f} | "
            f"{'—' if win_rate is None else f'{win_rate:.1%}'} |"
        )

    lines.extend(
        [
            "",
            "## Broad-cohort control",
            "",
            "For comparison, this control allows every current category leader to",
            "vote without the prior directional-behavior gate. It is diagnostic,",
            "not the recommended strategy.",
            "",
            "| Niche | Raw | Resolved | Accepted | P&L | Win rate |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    if broad_control:
        for category, raw, resolved, accepted, pnl, win_rate in broad_control:
            lines.append(
                f"| {category} | {raw} | {resolved} | {accepted} | "
                f"${pnl:.4f} | "
                f"{'—' if win_rate is None else f'{win_rate:.1%}'} |"
            )
    else:
        lines.append("| — | 0 | 0 | 0 | $0.0000 | — |")
    lines.extend(
        [
            "",
            "## Cohort coverage",
            "",
            "| Stored leaderboard category | Wallets | Earliest archived cohort trade | Latest archived cohort trade |",
            "|---|---:|---|---|",
        ]
    )
    lines.extend(
        f"| {category} | {count} | {earliest or '—'} | {latest or '—'} |"
        for category, count, earliest, latest in cohort_counts
    )
    lines.extend(
        [
            "",
            "## What this can and cannot establish",
            "",
            "- A stable positive result across vote thresholds, delays, and execution",
            "  stresses is useful historical evidence, not a profit guarantee.",
            "- Current winners were selected retrospectively; this is survivorship bias.",
            "- Public trade timestamps do not prove the trader initiated the idea, and",
            "  linked wallets can make apparent agreement less independent.",
            "- Historical public trade tape approximates availability; exact historical",
            "  order-book depth and a guaranteed $1 fill are unavailable.",
            "- A tiny positive result or one driven by only a few resolutions is noise.",
            "",
            "## Decision",
            "",
        ]
    )
    if validated:
        lines.extend(
            [
                f"Paper-monitor the {best[0]} cohort using the main setting. Do not",
                "raise stake from this backtest alone. Freeze the rules and evaluate",
                "the next untouched set of resolved signals.",
            ]
        )
    else:
        lines.extend(
            [
                "Reject broad leaderboard consensus copying: its best-resolved",
                "control was materially negative. No niche qualifies for deployment.",
                "Keep only the past-only directional version as a paper monitor and",
                "rerun the frozen matrix when additional signals resolve.",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
