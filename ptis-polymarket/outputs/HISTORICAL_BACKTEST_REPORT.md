# One-Week Historical Shadow-Copy Replay

Generated: 2026-07-24T02:40:28.544365Z

## Result

**Insufficient evidence: no realistic scenario produced at least 10 accepted resolved trades.**

This is an approximate retrospective diagnostic, not an exact fill backtest.
The replay does not reveal outcomes to entry selection. Outcomes are joined
only after simulated entry for hold-to-resolution settlement.

## Scope and evidence quality

- Dataset window: 2026-07-17T02:40:28.004980Z through 2026-07-24T02:40:28.004980Z
- Starting paper bankroll: $100.00
- Realism label: Approximate
- Selection method: Fixed wallets selected from current-session leaderboards; retrospective selection bias is present. All selected wallets are included.
- Method limitation: Approximate replay. Entry uses first subsequent BUY trade tape, not a historical order book. Current archived fee schedule is used. Outcomes are inaccessible to entry selection and used only for settlement.
- Cash baseline: $0 P&L and 0% return.

Official historical order-book depth was unavailable. Each follower entry
uses the first subsequent public BUY trade within the allowed wait, then
adds the scenario's adverse-price offset. This can neither prove fillability
nor measure historical slippage for a $1 order.

## Scenario results

| Delay | Adverse price | Signals | Portfolio accepted | Portfolio P&L | Return | Drawdown | Portfolio win rate | Eligible signals | Signal-level P&L | Signal win rate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0s | 0.000 | 895 | 11 | $-8.4586 | -8.46% | $10.4489 | 18.2% | 36 | $24.3931 | 55.6% |
| 0s | 0.010 | 895 | 11 | $-8.5141 | -8.51% | $10.4254 | 18.2% | 36 | $22.4223 | 55.6% |
| 0s | 0.020 | 895 | 11 | $-8.5665 | -8.57% | $10.4019 | 18.2% | 35 | $19.1699 | 54.3% |
| 5s | 0.000 | 895 | 9 | $-5.3224 | -5.32% | $7.1950 | 22.2% | 18 | $13.9226 | 55.6% |
| 5s | 0.010 | 895 | 7 | $-1.5671 | -1.57% | $5.1334 | 28.6% | 12 | $10.7168 | 58.3% |
| 5s | 0.020 | 895 | 6 | $-2.5955 | -2.60% | $5.1309 | 16.7% | 8 | $2.0310 | 37.5% |
| 15s | 0.000 | 895 | 7 | $-7.1950 | -7.20% | $7.1950 | 0.0% | 14 | $6.5387 | 42.9% |
| 15s | 0.010 | 895 | 6 | $-2.4662 | -2.47% | $5.1335 | 16.7% | 9 | $4.5836 | 44.4% |
| 15s | 0.020 | 895 | 6 | $-3.0400 | -3.04% | $5.1310 | 16.7% | 7 | $-0.9490 | 28.6% |
| 60s | 0.000 | 895 | 6 | $-2.6023 | -2.60% | $5.1377 | 16.7% | 11 | $9.6007 | 54.5% |
| 60s | 0.010 | 895 | 6 | $0.2599 | 0.26% | $4.1227 | 33.3% | 6 | $0.2599 | 33.3% |
| 60s | 0.020 | 895 | 6 | $0.0613 | 0.06% | $4.1207 | 33.3% | 6 | $0.0613 | 33.3% |

## Skip reasons by scenario

| Delay | Adverse price | Reason | Signals |
|---:|---:|---|---:|
| 0s | 0.000 | unresolved_or_missing_outcome | 781 |
| 0s | 0.000 | trader_behavior_filter | 78 |
| 0s | 0.000 | market_exposure_limit | 19 |
| 0s | 0.000 | trader_exposure_limit | 6 |
| 0s | 0.010 | unresolved_or_missing_outcome | 781 |
| 0s | 0.010 | trader_behavior_filter | 78 |
| 0s | 0.010 | market_exposure_limit | 19 |
| 0s | 0.010 | trader_exposure_limit | 6 |
| 0s | 0.020 | unresolved_or_missing_outcome | 781 |
| 0s | 0.020 | trader_behavior_filter | 78 |
| 0s | 0.020 | market_exposure_limit | 19 |
| 0s | 0.020 | trader_exposure_limit | 5 |
| 0s | 0.020 | price_moved_too_far | 1 |
| 5s | 0.000 | unresolved_or_missing_outcome | 781 |
| 5s | 0.000 | trader_behavior_filter | 78 |
| 5s | 0.000 | no_timely_buy_tape | 17 |
| 5s | 0.000 | market_exposure_limit | 9 |
| 5s | 0.000 | price_moved_too_far | 1 |
| 5s | 0.010 | unresolved_or_missing_outcome | 781 |
| 5s | 0.010 | trader_behavior_filter | 78 |
| 5s | 0.010 | no_timely_buy_tape | 17 |
| 5s | 0.010 | price_moved_too_far | 7 |
| 5s | 0.010 | market_exposure_limit | 5 |
| 5s | 0.020 | unresolved_or_missing_outcome | 781 |
| 5s | 0.020 | trader_behavior_filter | 78 |
| 5s | 0.020 | no_timely_buy_tape | 17 |
| 5s | 0.020 | price_moved_too_far | 11 |
| 5s | 0.020 | market_exposure_limit | 2 |
| 15s | 0.000 | unresolved_or_missing_outcome | 781 |
| 15s | 0.000 | trader_behavior_filter | 78 |
| 15s | 0.000 | no_timely_buy_tape | 20 |
| 15s | 0.000 | market_exposure_limit | 7 |
| 15s | 0.000 | price_moved_too_far | 2 |
| 15s | 0.010 | unresolved_or_missing_outcome | 781 |
| 15s | 0.010 | trader_behavior_filter | 78 |
| 15s | 0.010 | no_timely_buy_tape | 20 |
| 15s | 0.010 | price_moved_too_far | 7 |
| 15s | 0.010 | market_exposure_limit | 3 |
| 15s | 0.020 | unresolved_or_missing_outcome | 781 |
| 15s | 0.020 | trader_behavior_filter | 78 |
| 15s | 0.020 | no_timely_buy_tape | 20 |
| 15s | 0.020 | price_moved_too_far | 9 |
| 15s | 0.020 | market_exposure_limit | 1 |
| 60s | 0.000 | unresolved_or_missing_outcome | 781 |
| 60s | 0.000 | trader_behavior_filter | 78 |
| 60s | 0.000 | no_timely_buy_tape | 20 |
| 60s | 0.000 | price_moved_too_far | 5 |
| 60s | 0.000 | market_exposure_limit | 5 |
| 60s | 0.010 | unresolved_or_missing_outcome | 781 |
| 60s | 0.010 | trader_behavior_filter | 78 |
| 60s | 0.010 | no_timely_buy_tape | 20 |
| 60s | 0.010 | price_moved_too_far | 10 |
| 60s | 0.020 | unresolved_or_missing_outcome | 781 |
| 60s | 0.020 | trader_behavior_filter | 78 |
| 60s | 0.020 | no_timely_buy_tape | 20 |
| 60s | 0.020 | price_moved_too_far | 10 |

## Sixty-second, one-cent diagnostic by trader

This view ignores portfolio-cap rejections after a signal passed the
entry-price, timing, outcome-availability, and fee checks.

| Wallet | Eligible signals | Signal-level P&L | Average P&L | Win rate |
|---|---:|---:|---:|---:|
| `0x204f72f35326db932158cba6adff0b9a1da95e14` | 6 | $0.2599 | $0.0433 | 33.3% |

## Sixty-second, one-cent diagnostic by category

| Category | Eligible signals | Signal-level P&L | Average P&L |
|---|---:|---:|---:|
| Unknown | 6 | $0.2599 | $0.0433 |

## Interpretation

- Zero-second scenarios are theoretical upper bounds.
- Current-session leaderboard selection creates survivorship/selection bias.
- Current archived fees may differ from the exact historical fee schedule.
- A positive result is hypothesis-generating until walk-forward cohorts and
  prospectively collected order books reproduce it.
- A negative result is still useful evidence against this copy route.

## Recommended testing horizon

- Minimum decision sample: 100 resolved, strategy-eligible paper trades.
- Minimum diversity: at least 30 trades outside the dominant wallet and
  at least three market categories with usable metadata.
- Minimum live duration: four weeks; extend to eight–twelve weeks if
  fewer than 25 qualifying trades resolve per week.
- Early stop: pause the broad strategy if the first 30 resolved live
  trades are materially negative after costs and no predeclared segment
  remains positive.
- Promotion rule: require positive results at measured visibility delays,
  under 1¢ and 2¢ stress, in an untouched later window.
