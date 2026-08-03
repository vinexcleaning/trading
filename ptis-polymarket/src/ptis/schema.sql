CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    raw_file_path TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS markets (
    condition_id TEXT PRIMARY KEY,
    gamma_market_id TEXT,
    event_id TEXT,
    slug TEXT,
    question TEXT NOT NULL,
    category TEXT,
    resolution_source TEXT,
    end_at_utc TEXT,
    resolved_at_utc TEXT,
    winning_token_id TEXT,
    fees_enabled INTEGER,
    source_updated_at_utc TEXT,
    ingested_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcome_tokens (
    token_id TEXT PRIMARY KEY,
    condition_id TEXT NOT NULL REFERENCES markets(condition_id),
    outcome_name TEXT NOT NULL,
    outcome_index INTEGER NOT NULL,
    UNIQUE (condition_id, outcome_index)
);

CREATE TABLE IF NOT EXISTS traders (
    proxy_wallet TEXT PRIMARY KEY,
    username TEXT,
    first_observed_at_utc TEXT NOT NULL,
    last_observed_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id INTEGER PRIMARY KEY,
    snapshot_at_utc TEXT NOT NULL,
    category TEXT NOT NULL,
    time_period TEXT NOT NULL,
    ranking_metric TEXT NOT NULL DEFAULT 'PNL',
    rank INTEGER NOT NULL,
    proxy_wallet TEXT NOT NULL REFERENCES traders(proxy_wallet),
    reported_volume REAL,
    reported_pnl REAL,
    source_name TEXT NOT NULL,
    ingestion_run_id INTEGER REFERENCES ingestion_runs(id),
    UNIQUE (snapshot_at_utc, category, time_period, ranking_metric, proxy_wallet)
);

CREATE TABLE IF NOT EXISTS public_trades (
    trade_key TEXT PRIMARY KEY,
    proxy_wallet TEXT NOT NULL REFERENCES traders(proxy_wallet),
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    size_shares REAL NOT NULL CHECK (size_shares >= 0),
    price REAL NOT NULL CHECK (price >= 0 AND price <= 1),
    executed_at_utc TEXT NOT NULL,
    transaction_hash TEXT,
    source_name TEXT NOT NULL,
    ingested_at_utc TEXT NOT NULL,
    raw_file_path TEXT
);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id INTEGER PRIMARY KEY,
    token_id TEXT NOT NULL,
    source_timestamp_utc TEXT,
    received_at_utc TEXT NOT NULL,
    best_bid REAL CHECK (best_bid >= 0 AND best_bid <= 1),
    best_ask REAL CHECK (best_ask >= 0 AND best_ask <= 1),
    spread REAL,
    last_trade_price REAL,
    book_hash TEXT,
    source_name TEXT NOT NULL,
    raw_file_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orderbook_levels (
    snapshot_id INTEGER NOT NULL REFERENCES orderbook_snapshots(id),
    side TEXT NOT NULL CHECK (side IN ('BID', 'ASK')),
    level_index INTEGER NOT NULL CHECK (level_index >= 0),
    price REAL NOT NULL CHECK (price >= 0 AND price <= 1),
    size_shares REAL NOT NULL CHECK (size_shares >= 0),
    PRIMARY KEY (snapshot_id, side, level_index)
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    code_version TEXT,
    research_question TEXT NOT NULL,
    dataset_start_utc TEXT,
    dataset_end_utc TEXT,
    parameters_json TEXT NOT NULL,
    results_json TEXT,
    interpretation TEXT,
    decision TEXT
);

CREATE TABLE IF NOT EXISTS copy_signals (
    id INTEGER PRIMARY KEY,
    source_trade_key TEXT NOT NULL REFERENCES public_trades(trade_key),
    experiment_id INTEGER NOT NULL REFERENCES experiments(id),
    signal_at_utc TEXT NOT NULL,
    follower_at_utc TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'skipped')),
    rejection_reason TEXT,
    available_price REAL,
    simulated_fill_price REAL,
    filled_shares REAL,
    fee_usdc REAL,
    slippage_usdc REAL,
    UNIQUE (source_trade_key, experiment_id)
);

CREATE INDEX IF NOT EXISTS idx_books_token_received
ON orderbook_snapshots(token_id, received_at_utc);

CREATE INDEX IF NOT EXISTS idx_trades_wallet_time
ON public_trades(proxy_wallet, executed_at_utc);

CREATE TABLE IF NOT EXISTS market_observations (
    id INTEGER PRIMARY KEY,
    condition_id TEXT NOT NULL REFERENCES markets(condition_id),
    observed_at_utc TEXT NOT NULL,
    active INTEGER,
    closed INTEGER,
    accepting_orders INTEGER,
    liquidity_usd REAL,
    volume_usd REAL,
    best_bid REAL,
    best_ask REAL,
    fees_enabled INTEGER,
    fee_rate_decimal REAL,
    source_name TEXT NOT NULL,
    raw_file_path TEXT NOT NULL,
    UNIQUE (condition_id, observed_at_utc)
);

CREATE TABLE IF NOT EXISTS reconstructed_positions (
    proxy_wallet TEXT NOT NULL REFERENCES traders(proxy_wallet),
    token_id TEXT NOT NULL,
    as_of_utc TEXT NOT NULL,
    shares REAL NOT NULL,
    average_cost REAL,
    realized_pnl_from_observed_trades REAL NOT NULL,
    buys INTEGER NOT NULL,
    sells INTEGER NOT NULL,
    history_incomplete INTEGER NOT NULL,
    PRIMARY KEY (proxy_wallet, token_id, as_of_utc)
);

CREATE TABLE IF NOT EXISTS trader_assessments (
    id INTEGER PRIMARY KEY,
    proxy_wallet TEXT NOT NULL REFERENCES traders(proxy_wallet),
    assessed_at_utc TEXT NOT NULL,
    observation_count INTEGER NOT NULL,
    market_count INTEGER NOT NULL,
    buy_share REAL NOT NULL,
    rapid_reversal_share REAL NOT NULL,
    two_sided_market_share REAL NOT NULL,
    top_category_share REAL,
    classification TEXT NOT NULL,
    preliminary_copyability_score REAL NOT NULL,
    limitations TEXT NOT NULL,
    UNIQUE (proxy_wallet, assessed_at_utc)
);

CREATE TABLE IF NOT EXISTS data_quality_findings (
    id INTEGER PRIMARY KEY,
    checked_at_utc TEXT NOT NULL,
    check_name TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    affected_rows INTEGER NOT NULL,
    details TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_runs (
    id INTEGER PRIMARY KEY,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    starting_bankroll_usd REAL NOT NULL,
    detection_delay_seconds INTEGER NOT NULL,
    max_signal_age_seconds INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY,
    paper_run_id INTEGER NOT NULL REFERENCES paper_runs(id),
    source_trade_key TEXT NOT NULL REFERENCES public_trades(trade_key),
    proxy_wallet TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    decision_at_utc TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'skipped')),
    rejection_reason TEXT,
    requested_notional_usd REAL NOT NULL,
    filled_notional_usd REAL NOT NULL,
    filled_shares REAL NOT NULL,
    average_fill_price REAL,
    fee_usd REAL NOT NULL,
    slippage_usd REAL NOT NULL,
    original_trade_price REAL NOT NULL,
    best_bid REAL,
    best_ask REAL,
    UNIQUE (paper_run_id, source_trade_key)
);

CREATE INDEX IF NOT EXISTS idx_market_observations_condition_time
ON market_observations(condition_id, observed_at_utc);

CREATE INDEX IF NOT EXISTS idx_paper_trades_run
ON paper_trades(paper_run_id, decision);

CREATE TABLE IF NOT EXISTS monitor_sessions (
    id INTEGER PRIMARY KEY,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    polling_interval_seconds INTEGER NOT NULL,
    requested_cycles INTEGER NOT NULL,
    completed_cycles INTEGER NOT NULL DEFAULT 0,
    wallet_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS live_trade_first_seen (
    trade_key TEXT PRIMARY KEY REFERENCES public_trades(trade_key),
    monitor_session_id INTEGER NOT NULL REFERENCES monitor_sessions(id),
    proxy_wallet TEXT NOT NULL,
    executed_at_utc TEXT NOT NULL,
    first_seen_at_utc TEXT NOT NULL,
    visibility_delay_seconds REAL NOT NULL,
    was_baseline INTEGER NOT NULL,
    CHECK (visibility_delay_seconds >= 0)
);

CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY,
    paper_trade_id INTEGER NOT NULL UNIQUE REFERENCES paper_trades(id),
    opened_at_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
    resolved_at_utc TEXT,
    payout_usd REAL,
    net_pnl_usd REAL
);

CREATE INDEX IF NOT EXISTS idx_live_seen_wallet_time
ON live_trade_first_seen(proxy_wallet, first_seen_at_utc);

CREATE INDEX IF NOT EXISTS idx_paper_positions_status
ON paper_positions(status);

CREATE TABLE IF NOT EXISTS historical_backtest_runs (
    id INTEGER PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    dataset_start_utc TEXT NOT NULL,
    dataset_end_utc TEXT NOT NULL,
    selection_method TEXT NOT NULL,
    realism_label TEXT NOT NULL,
    starting_bankroll_usd REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_scenarios (
    id INTEGER PRIMARY KEY,
    backtest_run_id INTEGER NOT NULL REFERENCES historical_backtest_runs(id),
    delay_seconds INTEGER NOT NULL,
    adverse_price_offset REAL NOT NULL,
    max_tape_wait_seconds INTEGER NOT NULL,
    signals_considered INTEGER NOT NULL,
    trades_accepted INTEGER NOT NULL,
    trades_skipped INTEGER NOT NULL,
    total_net_pnl_usd REAL NOT NULL,
    return_on_bankroll REAL NOT NULL,
    maximum_drawdown_usd REAL NOT NULL,
    win_rate REAL,
    profit_factor REAL,
    largest_trade_profit_share REAL,
    execution_eligible_signals INTEGER NOT NULL DEFAULT 0,
    signal_level_net_pnl_usd REAL NOT NULL DEFAULT 0,
    signal_level_win_rate REAL,
    UNIQUE (backtest_run_id, delay_seconds, adverse_price_offset)
);

CREATE TABLE IF NOT EXISTS historical_copy_trades (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES historical_scenarios(id),
    source_trade_key TEXT NOT NULL REFERENCES public_trades(trade_key),
    proxy_wallet TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    signal_at_utc TEXT NOT NULL,
    follower_at_utc TEXT NOT NULL,
    tape_trade_at_utc TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'skipped')),
    rejection_reason TEXT,
    original_price REAL NOT NULL,
    tape_price REAL,
    simulated_fill_price REAL,
    filled_shares REAL NOT NULL,
    fee_usd REAL NOT NULL,
    payout_usd REAL NOT NULL,
    net_pnl_usd REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_historical_copy_scenario
ON historical_copy_trades(scenario_id, decision);

CREATE TABLE IF NOT EXISTS consensus_backtest_runs (
    id INTEGER PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    dataset_start_utc TEXT NOT NULL,
    dataset_end_utc TEXT NOT NULL,
    top_traders_per_category INTEGER NOT NULL,
    selection_method TEXT NOT NULL,
    realism_label TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consensus_results (
    id INTEGER PRIMARY KEY,
    consensus_run_id INTEGER NOT NULL REFERENCES consensus_backtest_runs(id),
    category TEXT NOT NULL,
    minimum_agreement INTEGER NOT NULL,
    agreement_window_seconds INTEGER NOT NULL,
    delay_seconds INTEGER NOT NULL,
    adverse_price_offset REAL NOT NULL,
    raw_consensus_signals INTEGER NOT NULL,
    resolved_signals INTEGER NOT NULL,
    accepted_signals INTEGER NOT NULL,
    total_net_pnl_usd REAL NOT NULL,
    win_rate REAL,
    average_pnl_usd REAL,
    UNIQUE (
        consensus_run_id, category, minimum_agreement,
        agreement_window_seconds, delay_seconds, adverse_price_offset
    )
);

CREATE TABLE IF NOT EXISTS consensus_copy_trades (
    id INTEGER PRIMARY KEY,
    consensus_result_id INTEGER NOT NULL REFERENCES consensus_results(id),
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    signal_at_utc TEXT NOT NULL,
    agreeing_wallets INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'skipped')),
    rejection_reason TEXT,
    original_reference_price REAL NOT NULL,
    simulated_fill_price REAL,
    fee_usd REAL NOT NULL,
    payout_usd REAL NOT NULL,
    net_pnl_usd REAL NOT NULL
);
