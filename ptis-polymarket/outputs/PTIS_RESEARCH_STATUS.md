# PTIS Research and Shadow-Paper Status

Generated: 2026-07-24T01:44:05.982431Z

## Decision-useful summary

The system now supports public-data candidate discovery, bounded wallet trade
ingestion, market and fee metadata, validation, behavior classification,
depth-based execution simulation, conservative $100-bankroll controls, and
current-market paper scans. It still does not establish profitability.

Historical execution remains approximate until prospective books and measured
first-visibility times accumulate. Preliminary trader scores are capped at 60
because delayed copy P&L and out-of-sample evidence are not yet available.

## Evidence inventory

| Record type | Rows |
|---|---:|
| Traders | 64 |
| Leaderboard Snapshots | 95 |
| Public Trades | 1467 |
| Markets | 84 |
| Orderbook Snapshots | 45 |
| Trader Assessments | 75 |
| Paper Runs | 19 |
| Paper Trades | 63 |
| Monitor Sessions | 4 |
| Live Trade First Seen | 226 |
| Paper Positions | 9 |

## Preliminary trader behavior assessments

| Wallet | Classification | Score (max 60) | Trades | Markets |
|---|---|---:|---:|---:|
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | directional-candidate | 47.1 | 267 | 156 |
| `0x5a218c7ad04135830a45c41aaed7294df7809318` | unknown | 45.2 | 251 | 149 |
| `0x511f9c771449162349795d17becf8b37031acbe1` | unknown | 41.5 | 200 | 69 |
| `0xb687f00464e33934f5d591f224e71c3559ecaee5` | sell-only-or-incomplete-history | 41.2 | 176 | 41 |
| `0xbe7c0363ec2f0d12630fd48ac4c87ce84f418356` | unknown | 40.8 | 200 | 98 |
| `0x204f72f35326db932158cba6adff0b9a1da95e14` | hedging-or-arbitrage-like | 36.7 | 373 | 70 |

## Latest data-quality checks

| Check | Severity | Affected rows | Meaning |
|---|---|---:|---|
| impossible_trade_prices | error | 0 | Trades must have prices between zero and one. |
| nonpositive_trade_sizes | error | 0 | Trades must have positive share size. |
| trades_after_ingestion | error | 0 | Execution time after ingestion indicates clock or timestamp corruption. |
| crossed_books | error | 0 | A crossed archived book is invalid for the current execution model. |
| missing_transaction_hash | warning | 0 | Missing hashes weaken independent deduplication and chain reconciliation. |
| unresolved_market_metadata | warning | 425 | Traded conditions without metadata cannot be categorized or resolved. |

## Latest current-market paper scan

Run 19 started at 2026-07-24T01:43:34.127996Z with a 5-second follower delay; status: completed. Notes: Prospective monitor session 4; no orders placed.

| Decision | Reason | Signals |
|---|---|---:|

| Wallet | Decision | Reason | Original | Best ask | Fill | Notional | Fee | Slippage |
|---|---|---|---:|---:|---:|---:|---:|---:|

## Prospective monitoring status

Session 4 started at 2026-07-24T01:43:34.127996Z; status: completed; completed 2 of 2 requested cycles across 2 wallets. Notes: Prospective public-data monitor; no orders placed.

Genuinely new trades first-seen after baseline: 26. Visibility delay averaged 65.9s (range 33.6s–260.3s).

### Completed prospective signal decisions

| Decision | Reason | Signals |
|---|---|---:|
| skipped | insufficient_remaining_upside | 14 |
| accepted | accepted | 9 |
| skipped | price_moved_too_far | 3 |

## Paper portfolio

The ledger contains 9 paper positions with $9.0758 of cost and fees. Realized resolution P&L is $0.0000; unresolved positions must not be counted as profit.

| Wallet | Market | Original | Fill | Cost | Fee | Shares | Status | Net P&L |
|---|---|---:|---:|---:|---:|---:|---|---:|
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | Will the highest temperature in Cape Town be 19°C on July 25? | 0.7100 | 0.7100 | $1.0000 | $0.014500 | 1.4085 | open | — |
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | Will the highest temperature in Cape Town be 18°C on July 25? | 0.9100 | 0.9000 | $1.0000 | $0.005000 | 1.1111 | open | — |
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | Will the highest temperature in Cape Town be 19°C on July 25? | 0.7100 | 0.7100 | $1.0000 | $0.014500 | 1.4085 | open | — |
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | Will the highest temperature in Cape Town be 18°C on July 25? | 0.9100 | 0.9000 | $1.0000 | $0.005000 | 1.1111 | open | — |
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | Will the highest temperature in Cape Town be 21°C on July 25? | 0.8300 | 0.8300 | $1.0000 | $0.008500 | 1.2048 | open | — |
| `0x03805a13a0b3e058f55f6c6af95389d4f431073d` | Will the highest temperature in Cape Town be 21°C on July 25? | 0.8300 | 0.8300 | $1.0000 | $0.008500 | 1.2048 | open | — |
| `0x5a218c7ad04135830a45c41aaed7294df7809318` | Will the highest temperature in Wellington be 15°C on July 24? | 0.9830 | 0.9290 | $1.0000 | $0.003550 | 1.0764 | open | — |
| `0x5a218c7ad04135830a45c41aaed7294df7809318` | Will the next Claude Opus model be released by July 31, 2026? | 0.6930 | 0.6820 | $1.0000 | $0.012720 | 1.4663 | open | — |
| `0x5a218c7ad04135830a45c41aaed7294df7809318` | Will the highest temperature in Wellington be 15°C on July 24? | 0.9810 | 0.9290 | $1.0000 | $0.003550 | 1.0764 | open | — |

## Interpretation and next evidence needs

- Accepted paper signals are simulated fills, not real orders or evidence of profit.
- A scan with zero eligible signals is a valid latency/liquidity result, not a failure.
- The next milestone is sustained prospective collection across multiple candidates.
- Copy P&L should be evaluated only after outcomes resolve and untouched test data exists.
- Hidden hedges, linked wallets, and off-platform activity remain unobservable risks.
