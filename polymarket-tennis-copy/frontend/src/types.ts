/**
 * Types mirroring the backend Pydantic schemas.
 *
 * Decimal fields arrive as JSON strings so precision survives the wire; they are
 * typed as `string` here deliberately rather than being coerced to `number`,
 * which would reintroduce the float error the backend works to avoid.
 */

export type Decimal = string

export interface Wallet {
  id: number
  address: string
  nickname: string | null
  pseudonym: string | null
  source: string
  source_detail: string | null
  status: string
  manually_approved: boolean
  on_watchlist: boolean
  notes: string | null
  risk_flags: string[]
  suspected_cluster_id: number | null
  first_activity_at: string | null
  last_activity_at: string | null
  last_sync_success_at: string | null
  last_sync_error: string | null
  backfill_complete: boolean
  observed_portfolio_value: Decimal | null
  sync_priority: number
  created_at: string
}

export interface ScoreComponents {
  copyable_roi: number
  profit_factor: number
  sample_confidence: number
  consistency: number
  drawdown: number
  recency: number
  liquidity_fit: number
  concentration: number
  data_quality: number
}

export interface WalletScore {
  skill_score: number
  base_score: number
  components: ScoreComponents
  penalties_applied: Record<string, number>
  total_penalty_multiplier: number
  risk_flags: string[]
  qualified: boolean
  disqualification_reasons: string[]
  confidence_level: string
  explanation: string | null
  formula_version: string
  computed_at: string
}

export interface DelayBreakdown {
  roi: number | null
  win_rate: number | null
  net_profit: number | null
  n: number
  /** Trades dropped because their price evidence was too weak to count. */
  excluded_weak_evidence: number
  avg_copyability: number | null
}

export interface WalletMetrics {
  scope: string
  total_positions: number
  completed_positions: number
  open_positions: number
  volume_usdc: Decimal | null
  capital_deployed: Decimal | null
  gross_profit: Decimal | null
  gross_loss: Decimal | null
  net_profit: Decimal | null
  roi: number | null
  /** Equal-weighted per-trade ROI — the only raw figure comparable to copyable ROI. */
  roi_equal_weighted: number | null
  win_rate: number | null
  profit_factor: number | null
  avg_profit_per_trade: Decimal | null
  median_profit_per_trade: Decimal | null
  expected_value_per_dollar: number | null
  avg_entry_price: Decimal | null
  avg_holding_seconds: number | null
  max_drawdown: number | null
  max_drawdown_usdc: Decimal | null
  longest_win_streak: number
  longest_loss_streak: number
  pct_profit_from_largest_trade: number | null
  pct_profit_from_top5_trades: number | null
  sharpe_like: number | null
  benchmark_delay_seconds: number
  copyable_roi: number | null
  copyable_win_rate: number | null
  copyable_net_profit: Decimal | null
  copyable_profit_factor: number | null
  avg_copyability_score: number | null
  copyable_coverage: number | null
  /** Keyed by delay in seconds. Each entry is a full breakdown, not a bare ROI. */
  roi_by_delay: Record<string, DelayBreakdown | null>
  roi_ci_low: number | null
  roi_ci_high: number | null
  copyable_roi_ci_low: number | null
  copyable_roi_ci_high: number | null
  shrunk_copyable_roi: number | null
  prob_positive_edge: number | null
  // 0-100 confidence in the sample size, not a label.
  sample_confidence: number | null
  data_quality_score: number | null
  performance_by_market_type: Record<string, any>
  performance_by_tournament: Record<string, any>
  performance_by_player: Record<string, any>
  performance_by_entry_bucket: Record<string, any>
  performance_by_size_bucket: Record<string, any>
  performance_by_period: Record<string, any>
  computed_at: string
}

export interface ClusterMember {
  wallet_id: number
  address: string
  shared_market_count: number
  jaccard_similarity: number | null
  timing_correlation: number | null
  size_correlation: number | null
  coordinated_exit_count: number
}

export interface Cluster {
  id: number
  label: string | null
  relation: string
  confidence: number
  evidence: string | null
  member_count: number
  members: ClusterMember[]
}

export interface WalletDetail {
  wallet: Wallet
  score: WalletScore | null
  metrics: Record<string, WalletMetrics>
  tags: string[]
  cluster: Cluster | null
  behavioural_profile: Record<string, any>
}

export interface RankingRow {
  rank: number
  wallet_id: number
  address: string
  nickname: string | null
  skill_score: number
  qualified: boolean
  confidence_level: string
  completed_positions: number
  roi: number | null
  copyable_roi: number | null
  shrunk_copyable_roi: number | null
  copyable_coverage: number | null
  net_profit: Decimal | null
  max_drawdown: number | null
  prob_positive_edge: number | null
  last_activity_at: string | null
  risk_flags: string[]
  cluster_id: number | null
}

export interface Ranking {
  key: string
  label: string
  description: string
  scope: string
  rows: RankingRow[]
  caveat: string
}

export interface Copyability {
  delay_seconds: number
  wallet_entry_price: Decimal | null
  price_after_delay: Decimal | null
  estimated_fill_price: Decimal | null
  price_deterioration: Decimal | null
  slippage: Decimal | null
  available_liquidity: Decimal | null
  follower_roi: number | null
  follower_is_win: boolean | null
  copyability_score: number | null
  price_source_quality: string | null
  data_confidence: number | null
  notes: string | null
}

export interface Position {
  id: number
  token_id: string
  condition_id: string | null
  market_question: string | null
  outcome_label: string | null
  status: string
  tennis_market_type: string
  entry_phase: string
  opened_at: string
  closed_at: string | null
  first_entry_price: Decimal
  avg_entry_price: Decimal
  avg_exit_price: Decimal | null
  entry_tx_count: number
  accumulated: boolean
  partial_exit_count: number
  capital_committed: Decimal
  max_shares: Decimal
  realized_pnl: Decimal
  net_pnl: Decimal | null
  roi: number | null
  is_win: boolean | null
  holding_seconds: number | null
  behaviour: string
  flags: string[]
  reconstruction_confidence: number
  pct_of_wallet_capital: number | null
  copyability: Copyability[]
}

export interface Transaction {
  id: number
  timestamp: number
  occurred_at: string
  activity_type: string
  side: string | null
  size: Decimal
  price: Decimal | null
  usdc_size: Decimal | null
  token_id: string | null
  condition_id: string | null
  market_question: string | null
  outcome_label: string | null
  market_phase: string
  is_tennis: boolean
  transaction_hash: string | null
}

export interface SignalWallet {
  wallet_id: number
  address: string
  nickname: string | null
  entry_price: Decimal | null
  position_usdc: Decimal | null
  traded_at: string
  skill_score: number | null
  copyable_roi: number | null
  tennis_trade_count: number | null
  cluster_id: number | null
  counted_as_independent: boolean
  has_begun_exiting: boolean
}

export interface Signal {
  id: number
  signal_type: string
  status: string
  qualified: boolean
  token_id: string
  condition_id: string | null
  outcome_label: string | null
  market_question: string | null
  market_phase: string
  first_wallet_trade_at: string
  detected_at: string
  expires_at: string | null
  signal_age_seconds: number | null
  wallet_count: number
  independent_cluster_count: number
  wallet_entry_price_min: Decimal | null
  wallet_entry_price_max: Decimal | null
  wallet_entry_price_median: Decimal | null
  current_price: Decimal | null
  estimated_follower_price: Decimal | null
  price_deterioration: Decimal | null
  available_liquidity: Decimal | null
  spread: Decimal | null
  total_wallet_position_usdc: Decimal | null
  median_skill_score: number | null
  median_copyable_roi: number | null
  copyability_score: number | null
  consensus_score: number | null
  estimated_edge: number | null
  edge_method: string | null
  data_confidence: number | null
  rejection_reasons: string[]
  risk_flags: string[]
  explanation: string | null
  qualification_detail: Array<Record<string, any>>
  wallets: SignalWallet[]
}

export interface PaperTrade {
  id: number
  signal_id: number | null
  token_id: string
  outcome_label: string | null
  market_question: string | null
  status: string
  exit_strategy: string
  signal_detected_at: string
  execution_delay_seconds: number
  entered_at: string | null
  exited_at: string | null
  wallet_entry_price: Decimal | null
  reference_price: Decimal | null
  fill_price: Decimal | null
  slippage_applied: Decimal | null
  exit_price: Decimal | null
  exit_reason: string | null
  stake_usdc: Decimal
  shares: Decimal | null
  stake_reduced_for_liquidity: boolean
  realized_pnl: Decimal | null
  unrealized_pnl: Decimal | null
  roi: number | null
  is_win: boolean | null
  wallet_roi: number | null
  roi_gap_vs_wallet: number | null
  price_source_quality: string | null
  data_confidence: number | null
  rejection_reason: string | null
  notes: string | null
}

export interface PaperSummary {
  trades: number
  open_trades: number
  closed_trades: number
  wins: number
  losses: number
  total_staked: Decimal
  realized_pnl: Decimal
  unrealized_pnl: Decimal
  net_pnl: Decimal
  roi: number | null
  win_rate: number | null
  rejected: number
  rejection_reasons: Record<string, number>
  avg_roi_gap_vs_wallet: number | null
  disclaimer: string
}

export interface Overview {
  wallets_tracked: number
  wallets_approved: number
  wallets_qualified: number
  tennis_markets_tracked: number
  tennis_markets_open: number
  active_signals: number
  signals_today: number
  qualified_signals_today: number
  rejected_signals_today: number
  paper_open_positions: number
  paper_realized_pnl: Decimal
  paper_unrealized_pnl: Decimal
  paper_win_rate: number | null
  paper_roi: number | null
  median_qualified_copyable_roi: number | null
  current_drawdown: number | null
  last_market_sync: string | null
  last_wallet_sync: string | null
  benchmark_delay_seconds: number
  disclaimer: string
}

export interface Health {
  status: string
  version: string
  environment: string
  database: string
  scheduler_running: boolean
  jobs: Array<Record<string, any>>
  freshness: Record<string, any>
  recent_errors: number
  unacknowledged_drift: number
  notification_channels: string[]
}

export interface DataQuality {
  wallets_tracked: number
  wallets_stale: number
  markets_tracked: number
  markets_needing_review: number
  transactions_total: number
  transactions_unmatched_market: number
  positions_total: number
  positions_low_confidence: number
  price_quality_breakdown: Record<string, number>
  avg_data_confidence: number | null
  warnings: string[]
}

export interface Settings {
  follower_delays_seconds: number[]
  benchmark_delay_seconds: number
  modeled_slippage_bps: number
  score_weights: Record<string, number>
  alert_thresholds: Record<string, any>
  consensus_thresholds: Record<string, any>
  paper_settings: Record<string, any>
  sync_intervals: Record<string, number>
  notification_channels_configured: string[]
  min_copyable_data_confidence: number
}

export interface MarketOutcome {
  token_id: string
  outcome_index: number
  label: string
  player_name: string | null
  is_winner: boolean | null
  last_price: Decimal | null
}

export interface Market {
  id: number
  condition_id: string
  slug: string | null
  question: string | null
  is_tennis: boolean
  tennis_market_type: string
  sports_market_type_raw: string | null
  classification_confidence: number
  classification_methods: string[]
  classification_notes: string | null
  needs_review: boolean
  reviewed_by_human: boolean
  period_number: number | null
  game_start_time: string | null
  closed: boolean
  resolved: boolean
  winning_outcome_index: number | null
  accepting_orders: boolean
  liquidity: Decimal | null
  volume_24hr: Decimal | null
  spread: Decimal | null
  best_bid: Decimal | null
  best_ask: Decimal | null
  tick_size: Decimal | null
  outcomes: MarketOutcome[]
  tournament: string | null
  player_a: string | null
  player_b: string | null
  surface: string | null
  tour: string | null
  best_of: number | null
}

export interface PricePoint {
  token_id: string
  timestamp: number
  price: Decimal
  kind: string
  size: Decimal | null
}

export interface MarketDetail {
  market: Market
  price_history: PricePoint[]
  wallet_activity: Array<Record<string, any>>
  open_positions: Array<Record<string, any>>
  liquidity: Record<string, any> | null
  signals: Signal[]
  paper_trades: PaperTrade[]
}

export interface BacktestRun {
  id: number
  name: string
  status: string
  progress_pct: number
  config: Record<string, any>
  period_start: string
  period_end: string
  delay_seconds: number
  total_trades: number
  wins: number
  losses: number
  total_staked: Decimal | null
  total_pnl: Decimal | null
  total_return: number | null
  win_rate: number | null
  profit_factor: number | null
  max_drawdown: number | null
  avg_trade_pnl: Decimal | null
  median_trade_pnl: Decimal | null
  sharpe_like: number | null
  in_sample_return: number | null
  validation_return: number | null
  out_of_sample_return: number | null
  walk_forward: Array<Record<string, any>>
  equity_curve: number[]
  drawdown_curve: number[]
  delay_sensitivity: Record<string, any>
  outcome_distribution: Record<string, number>
  by_market_type: Record<string, any>
  by_wallet: Record<string, any>
  return_ci_low: number | null
  return_ci_high: number | null
  pct_pnl_from_top_trade: number | null
  lookahead_violations: number
  skipped_trades: number
  skip_reasons: Record<string, number>
  warnings: string[]
  error: string | null
  started_at: string
  finished_at: string | null
}

export interface BacktestTrade {
  wallet_id: number | null
  token_id: string
  decision_at: string
  entered_at: string | null
  exited_at: string | null
  wallet_entry_price: Decimal | null
  fill_price: Decimal | null
  exit_price: Decimal | null
  stake_usdc: Decimal | null
  pnl: Decimal | null
  roi: number | null
  is_win: boolean | null
  exit_reason: string | null
  market_type: string | null
  market_phase: string | null
  copyability_score: number | null
  price_source_quality: string | null
  split: string | null
  decision_inputs: Record<string, any>
}

export interface AlertRow {
  id: number
  signal_id: number
  alert_type: string
  channel: string
  title: string
  body: string
  payload: Record<string, any>
  delivered: boolean
  delivery_error: string | null
  read_at: string | null
  created_at: string
}
