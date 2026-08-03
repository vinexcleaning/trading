# Polymarket Trader Intelligence and Shadow Copy System

## Technical summary

**Decision: proceed, but only as a prospective research and paper-trading
project.** Public official interfaces are sufficient to discover markets and
candidate wallets, retrieve public trades and positions, read current order
books, and stream live market events. They are not sufficient by themselves for
a fully realistic historical copy backtest because official price history is a
sampled price series, not historical level-2 order-book depth.

The largest unknown is not whether public trades exist. It is whether a
follower can detect a particular wallet's completed trade quickly enough and
still execute at a profitable price. That delay must be measured; it must not be
assumed. The second major unknown is strategy completeness: a public proxy
wallet may omit other wallets, off-platform trades, and hedges.

The recommended minimum viable system (MVS) is therefore a timestamped data
recorder plus a hold-to-resolution shadow backtester. It must archive raw public
trade observations and full order-book snapshots prospectively, preserve both
source and receipt times, reject unfillable signals, and size accepted paper
orders at $1–$2 from a $100 simulated bankroll. No real-money trading component
is appropriate or included.

**Evidence status:** the official documentation establishes endpoint
capabilities, schemas, authentication requirements, and stated rate limits. It
does not establish measured visibility latency, historical fillability, or
copyable profitability. Those remain experiments.

## Official data is broad enough for live research

Polymarket currently separates public data across three services. Gamma covers
market and event discovery; the Data API covers public user trades, positions,
activity, holders, open interest, and leaderboards; the CLOB API covers books,
prices, spreads, and price history. Gamma, Data API, and public CLOB market-data
reads require no authentication. See the official [API
overview](https://docs.polymarket.com/api-reference/introduction) and
[authentication guide](https://docs.polymarket.com/api-reference/authentication).

| Need | Official source | Useful fields or events | Authentication | Fitness |
|---|---|---|---|---|
| Markets and categories | Gamma API | IDs, question, tokens, category/tags, dates, liquidity, fee flag | None | Strong for discovery and metadata |
| Public trades | Data API `/trades` | proxy wallet, BUY/SELL, asset, condition, shares, price, timestamp, transaction hash | None | Strong for observed fills; visibility delay unmeasured |
| Wallet activity | Data API `/activity` and `/trades` | trade and on-chain activity by public profile address | None | Good for public proxy-wallet history |
| Positions | Data API `/positions`, `/closed-positions` | size, average price, initial/current value, realized P&L | None | Useful cross-check; not a complete strategy |
| Candidate leaderboards | Data API `/v1/leaderboard` | rank, proxy wallet, displayed P&L and volume by period/category | None | Discovery only, not a copyability label |
| Current order books | CLOB `/book`, `/books` | timestamp, bids, asks, sizes, tick, last price | None | Strong for prospective execution modeling |
| Sampled prices | CLOB `/prices-history` | timestamp and price, configurable time range/fidelity | None | Not sufficient for historical spread/depth |
| Live market updates | Public CLOB market WebSocket | book, price changes, last trades, best bid/ask, resolution | None | Strong for prospective collection |
| Personal order lifecycle | CLOB user WebSocket | authenticated user's matched/confirmed trades and orders | Authentication | Not useful for monitoring arbitrary wallets |
| Resolution | Gamma event/market metadata and market WebSocket | resolution source, rules, closed/resolved state, winning outcome | None | Good, but rule ambiguity still needs flags |
| Fees | Market metadata and CLOB fee endpoints | per-market fee enabled/rate parameters | None for market reads | Must be captured per market and date |

The public trades schema explicitly reports `side`, `price`, `size`,
`timestamp`, token, condition, wallet, and transaction hash in the official
[user/market trades
reference](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets).
Current positions expose realized P&L alongside marked position values, but
those values are current-state data rather than a historically honest selection
series; see [positions
reference](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user).

Leaderboards can be queried by category, DAY/WEEK/MONTH/ALL period, P&L or
volume, with pagination to offset 1,000. The response does not define a
historical point-in-time selection record or explain enough accounting detail
to treat displayed P&L as audited skill. We must snapshot it ourselves and use
it only after its observation time. See [leaderboard
reference](https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings).

The public market WebSocket streams level-2 book changes and trade events, but
an arbitrary wallet is not identified in the documented market event contract.
The authenticated user channel concerns the authenticated user's own lifecycle.
Consequently, candidate-wallet detection is likely to combine the Data API or
chain observation with market-channel books. The end-to-end lag must be measured
for every route. See [WebSocket
overview](https://docs.polymarket.com/market-data/websocket/overview) and
[market channel](https://docs.polymarket.com/market-data/websocket/market-channel).

Official rate limits are generous for the MVS—Data API general 1,000 requests
per 10 seconds, `/trades` 200 per 10 seconds, CLOB `/book` 1,500 per 10 seconds,
and price history 1,000 per 10 seconds—but Cloudflare may throttle by delaying
requests. The collector still needs bounded concurrency, backoff, and latency
telemetry. See [official rate
limits](https://docs.polymarket.com/api-reference/rate-limits).

Fees are now per-market, not safely represented by one universal constant. The
official formula is `shares × feeRate × price × (1 − price)`, with taker-only
rates varying by category and geopolitics currently fee-free. The market's
`feesEnabled` and fee parameters must be recorded at ingestion time rather than
reconstructed from today's documentation. See [official fee
documentation](https://docs.polymarket.com/trading/fees).

## Missing evidence prevents a fully realistic retrospective claim

| Gap | Why it matters | Current treatment | Realism label |
|---|---|---|---|
| Historical level-2 books | Determines post-delay price, depth, partial fills, and exitability | Collect prospectively; do not substitute sampled price history | Insufficient for past realistic fills |
| Accurate post-trade executable price | A last price or midpoint may not have been available to the follower | Use timestamp-aligned ask/bid and depth only | Fully realistic only after collector runs |
| Public-visibility delay | Defines follower signal time | Log source execution time, first observed time, and local receipt time | Unknown until measured |
| Historical liquidity/spread | Controls skip decisions and slippage | Future snapshots/WebSocket archive | Approximate from other data only |
| Complete strategy | Visible position may be a hedge or one arbitrage leg | Behavior flags; exclude market-making/arbitrage-like wallets initially | Structurally unknowable |
| Multiple-wallet identity | Splits performance and hides net exposure | Never assume address equals person; optional clustering is probabilistic | Structurally uncertain |
| Cross-platform hedges | Can reverse the meaning of a public trade | Cannot observe reliably; disclose and classify conservatively | Structurally unknowable |
| Leaderboard accounting semantics | Can distort candidate selection | Treat as a sampling frame, independently reconstruct trades/P&L | Requires empirical reconciliation |

The official CLOB book endpoint returns current bids, asks, sizes, timestamp, and
book hash ([order-book
reference](https://docs.polymarket.com/api-reference/market-data/get-order-book)).
Official price history returns timestamp/price observations at a chosen
fidelity, not historical bids, asks, or depth ([order-book and price-history
guide](https://docs.polymarket.com/trading/orderbook)). A backtest that uses that
series as if it were executable must be labeled theoretical or approximate.

## The minimum viable system answers one narrow question

The first useful system has five components:

1. **Point-in-time candidate sampler.** Snapshot leaderboard cohorts plus a
   control sample without treating future success as eligibility.
2. **Public trade observer.** Poll or otherwise observe selected wallets, retain
   raw responses, deduplicate fills, and record execution time and first receipt.
3. **Market recorder.** Subscribe to selected outcome tokens and persist full
   book states or reconstructible deltas with local receipt time.
4. **Execution simulator.** At `observed time + assumed processing delay`, cross
   the actual ask for BUY or bid for SELL, walk depth, apply per-market taker
   fees, and skip missing or stale books.
5. **Hold-to-resolution paper ledger.** Size $1–$2 trades, cap correlated
   exposure, resolve with official outcomes, and report copyable P&L separately
   from original-wallet P&L.

SQLite is sufficient for the first evidence run. Raw JSON remains immutable on
disk; normalized rows enable audits and tests. A dashboard, AI classifier,
microservices, and order-routing code would add cost before answering the
question.

## Minimum database design

| Table | Minimum purpose and fields |
|---|---|
| `ingestion_runs` | source, endpoint, start/end UTC, status, raw path, error |
| `markets` | condition/event IDs, rules source, category, close/resolution, winner, fee state |
| `outcome_tokens` | token, condition, outcome, index |
| `traders` | proxy wallet, public name, first/last observed UTC |
| `leaderboard_snapshots` | observation UTC, period/category, rank, displayed P&L/volume |
| `public_trades` | stable dedupe key, wallet, token, side, shares, price, execution and ingestion UTC, transaction |
| `orderbook_snapshots` | token, source and receipt UTC, top of book, hash, raw path |
| `orderbook_levels` | snapshot, side, price priority, price, shares |
| `experiments` | code version, cutoff dates, parameters, results, interpretation, decision |
| `copy_signals` | source trade, follower timestamp, accept/skip reason, available/fill price, amount, fee, slippage |

Every historical selection query must enforce `observation_time <= decision_time`.
The same rule applies to books, market resolution, and trader metrics.

## Candidate discovery avoids a winner-only sample

The first cohort should be frozen at a documented UTC cutoff:

- 50 monthly P&L leaders, sampled by category as data volume allows.
- 50 monthly volume leaders, which includes active but not necessarily
  profitable wallets.
- 50 random active wallets from predefined liquid markets using a saved random
  seed.
- 25 previously sampled candidates retained into later windows, including
  underperformers and dropouts.

Deduplicate wallets, require a minimum of 30 eligible pre-cutoff fills across at
least 10 markets before skill scoring, and stratify by category. These are
research thresholds, not claims of statistical sufficiency. Rank candidates
using only pre-cutoff data, then evaluate the following window. Never backfill a
historical cohort from today's leaderboard.

Market makers, rapid two-sided traders, and related-market arbitrage patterns
should be classified and reported but excluded from the first directional-copy
test. Leaderboard P&L is used to broaden sampling, not as the target variable.

## The first honest backtest is deliberately simple

For each eligible wallet BUY:

1. Set signal time to the first time the completed public trade was observed.
2. Test fixed follower delays of 5 and 15 seconds separately.
3. Read the first complete book at or immediately before follower time, subject
   to a strict maximum staleness bound; never read a future book.
4. Reject if the ask is missing, the spread exceeds $0.03, the price is worse
   than the trader's fill by more than $0.02, market rules are flagged, the
   market is near its scheduled end, or $1 of notional cannot fill through
   visible depth.
5. Walk ask levels for the average fill, calculate the captured per-market
   taker fee, and open a $1 paper position. Run a separate $2 sensitivity case.
6. Hold to official resolution. Do not copy exits in the first test.
7. Record every skip and every cost. Compare with cash, a saved random-trade
   cohort, and equal-weight candidates.

Primary metric: net small-bankroll copyable P&L. Required supporting metrics:
trade count, copy rate, skip reasons, fee/spread/slippage/delay drag, maximum
drawdown, profit factor, outlier concentration, category/trader concentration,
and bankroll survival. The test is promising only if the result persists in an
untouched later window and under both delays without one wallet or trade
dominating.

## Technical risks ranked

| Rank | Risk | Severity | Mitigation / stop rule |
|---:|---|---|---|
| 1 | No official historical order-book depth | Critical | Collect prospectively; label older tests approximate |
| 2 | Wallet-trade visibility delay unknown | Critical | Instrument and compare execution, first-seen, receipt times |
| 3 | Trade API pagination/coverage or revisions | High | Raw retention, dedupe, overlap polling, reconciliation |
| 4 | Market and token identity mismatches | High | Foreign keys, resolution reconciliation, validation failures |
| 5 | WebSocket gaps/reconnects | High | Sequence/hash checks, periodic REST snapshots, gap flags |
| 6 | Fee schedule changes | High | Store per-market parameters and observation date |
| 7 | Timestamp precision/clock skew | High | UTC only, server-time checks, synchronized local clock |
| 8 | Rate throttling creates hidden latency | Medium | Backoff plus request-duration/first-seen telemetry |
| 9 | Local SQLite growth/locking | Low initially | WAL mode; graduate only after measured need |

## Strategy risks ranked

| Rank | Risk | Severity | Mitigation / stop rule |
|---:|---|---|---|
| 1 | Hidden hedges/arbitrage/multiple wallets | Critical | Conservative classification; never claim full strategy |
| 2 | Edge disappears before observation | Critical | Measured 5/15-second tests; abandon if price drag consumes edge |
| 3 | Survivorship and selection lookahead | Critical | Frozen cohorts and walk-forward eligibility |
| 4 | Apparent profit is one outlier | High | concentration limits and leave-one-out sensitivity |
| 5 | Insufficient small-order economics | High | $1/$2 depth, fee, spread, and bankroll tests |
| 6 | Exit/resolution risk | High | first test holds to resolution; rule-quality flags |
| 7 | Trader regime change/crowding | High | rolling monitoring and expiry of stale scores |
| 8 | Correlated event exposure | High | market/category/trader portfolio caps |
| 9 | Leaderboard P&L is misleading | Medium | reconstruct cash flows and settled outcomes |

## Ordered implementation plan

1. Freeze the data contracts, SQLite schema, raw-data policy, and no-lookahead
   invariant.
2. Validate official endpoint responses and capture point-in-time leaderboard
   cohorts.
3. Add paginated wallet trade ingestion with overlap, deduplication, and data
   quality checks.
4. Add market/token/resolution ingestion and per-market fee capture.
5. Build a resilient market WebSocket recorder with REST checkpoint recovery.
6. Run a latency experiment comparing trade execution timestamps with first
   public observation and local receipt.
7. Reconstruct positions and classify two-sided, rapid-turnover, and
   related-market behavior.
8. Implement depth-walking execution, fees, skip rules, and the $100 paper
   ledger.
9. Freeze an initial cohort and run the 5/15-second hold-to-resolution test.
10. Only after adequate prospective data, add walk-forward rankings,
    sensitivities, and live daily/weekly paper reports.

## First concrete action completed

The repository now contains the first implementation slice:

- A Python package and command-line entry point with no third-party runtime
  dependency.
- A normalized SQLite schema covering ingestion provenance, candidates, trades,
  books, experiments, and paper signals.
- An official public API client with bounded retries.
- A point-in-time leaderboard snapshot collector.
- A full current-order-book snapshot collector that preserves raw JSON, source
  time, local receipt time, top of book, and every visible level.
- Schema and explicit no-lookahead tests.

The next action is to validate one live leaderboard response and one active
token book, then add paginated wallet-trade ingestion. No real-money endpoint,
credential, or private key is needed.

## Questions the next evidence run must answer

- What is the empirical distribution of Data API first-seen delay for selected
  wallet fills?
- Does the public trade response expose enough stable identity to deduplicate
  repeated polling without collisions?
- How frequently must full book checkpoints supplement WebSocket deltas?
- Does displayed leaderboard P&L reconcile to reconstructed settled and open
  positions?
- How many independent candidate trades remain after classification, liquidity,
  rule-quality, and $1 fillability filters?

This report reflects official documentation reviewed on July 23, 2026. API and
fee behavior must be rechecked at the start of every evidence collection period.
