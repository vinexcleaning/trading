# Specialist Consensus Historical Backtest

Generated: 2026-07-24T03:39:43.659227Z

## Bottom line

**No niche is historically validated. None produced both positive after-cost P&L and at least 20 accepted resolved consensus entries in the predeclared main setting.**

This test asks whether several current category leaders buying the same
outcome within six hours would have been profitable historically. It uses
one equal vote per wallet, ignores whale size, rejects opposing-outcome
consensus, and reveals the winner only during settlement.

## Evidence quality

- Window: 2026-03-26T03:37:10.872704Z through 2026-07-24T03:37:10.872704Z
- Cohort size requested per niche: 10
- Selection: Latest stored category PNL leaderboard, top N per category
- Realism: Approximate
- Limitation: Approximate replay using current category PNL leaderboard cohorts. This creates survivorship/selection bias. Consensus generation is outcome-blind, equal-weighted, one vote per wallet, and rejects conditions where opposing tokens both reach consensus. A wallet may vote only when its strictly prior public behavior passes the directional gate (30+ observations, at least 75% buys, low rapid reversal rate). Entry uses the first archived public BUY after the delay, not historical L2 depth.
- Each accepted signal risks a flat $1 paper notional and holds to resolution.
- The main setting is 3 agreeing wallets, a 6-hour agreement window,
  60-second delay, and 1-cent adverse execution stress.

## Main-setting comparison

| Niche cohort | Raw consensus | Resolved | Accepted | Net P&L | Average | Win rate | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 0 | 0 | 0 | $0.0000 | — | — | insufficient sample |
| ECONOMICS | 1 | 0 | 0 | $0.0000 | — | — | insufficient sample |
| POLITICS | 0 | 0 | 0 | $0.0000 | — | — | insufficient sample |
| SPORTS | 0 | 0 | 0 | $0.0000 | — | — | insufficient sample |
| TECH | 84 | 0 | 0 | $0.0000 | — | — | insufficient sample |

## Full sensitivity matrix

| Niche | Votes | Window | Delay | Stress | Raw | Resolved | Accepted | P&L | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 2 | 6h | 15s | 0.000 | 7 | 4 | 1 | $-1.0686 | 0.0% |
| CRYPTO | 2 | 6h | 15s | 0.010 | 7 | 4 | 1 | $-1.0679 | 0.0% |
| CRYPTO | 2 | 6h | 15s | 0.020 | 7 | 4 | 1 | $-1.0672 | 0.0% |
| CRYPTO | 2 | 6h | 60s | 0.000 | 7 | 4 | 0 | $0.0000 | — |
| CRYPTO | 2 | 6h | 60s | 0.010 | 7 | 4 | 0 | $0.0000 | — |
| CRYPTO | 2 | 6h | 60s | 0.020 | 7 | 4 | 0 | $0.0000 | — |
| CRYPTO | 3 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 3 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 3 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 3 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 3 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 3 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 4 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 4 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 4 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 4 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 4 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| CRYPTO | 4 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 2 | 6h | 15s | 0.000 | 4 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 2 | 6h | 15s | 0.010 | 4 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 2 | 6h | 15s | 0.020 | 4 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 2 | 6h | 60s | 0.000 | 4 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 2 | 6h | 60s | 0.010 | 4 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 2 | 6h | 60s | 0.020 | 4 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 3 | 6h | 15s | 0.000 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 3 | 6h | 15s | 0.010 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 3 | 6h | 15s | 0.020 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 3 | 6h | 60s | 0.000 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 3 | 6h | 60s | 0.010 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 3 | 6h | 60s | 0.020 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 4 | 6h | 15s | 0.000 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 4 | 6h | 15s | 0.010 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 4 | 6h | 15s | 0.020 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 4 | 6h | 60s | 0.000 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 4 | 6h | 60s | 0.010 | 1 | 0 | 0 | $0.0000 | — |
| ECONOMICS | 4 | 6h | 60s | 0.020 | 1 | 0 | 0 | $0.0000 | — |
| POLITICS | 2 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 2 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 2 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 2 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 2 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 2 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 3 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 3 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 3 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 3 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 3 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 3 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 4 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 4 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 4 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 4 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 4 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| POLITICS | 4 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 2 | 6h | 15s | 0.000 | 2 | 2 | 0 | $0.0000 | — |
| SPORTS | 2 | 6h | 15s | 0.010 | 2 | 2 | 0 | $0.0000 | — |
| SPORTS | 2 | 6h | 15s | 0.020 | 2 | 2 | 0 | $0.0000 | — |
| SPORTS | 2 | 6h | 60s | 0.000 | 2 | 2 | 0 | $0.0000 | — |
| SPORTS | 2 | 6h | 60s | 0.010 | 2 | 2 | 0 | $0.0000 | — |
| SPORTS | 2 | 6h | 60s | 0.020 | 2 | 2 | 0 | $0.0000 | — |
| SPORTS | 3 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 3 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 3 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 3 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 3 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 3 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 4 | 6h | 15s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 4 | 6h | 15s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 4 | 6h | 15s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 4 | 6h | 60s | 0.000 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 4 | 6h | 60s | 0.010 | 0 | 0 | 0 | $0.0000 | — |
| SPORTS | 4 | 6h | 60s | 0.020 | 0 | 0 | 0 | $0.0000 | — |
| TECH | 2 | 6h | 15s | 0.000 | 315 | 0 | 0 | $0.0000 | — |
| TECH | 2 | 6h | 15s | 0.010 | 315 | 0 | 0 | $0.0000 | — |
| TECH | 2 | 6h | 15s | 0.020 | 315 | 0 | 0 | $0.0000 | — |
| TECH | 2 | 6h | 60s | 0.000 | 315 | 0 | 0 | $0.0000 | — |
| TECH | 2 | 6h | 60s | 0.010 | 315 | 0 | 0 | $0.0000 | — |
| TECH | 2 | 6h | 60s | 0.020 | 315 | 0 | 0 | $0.0000 | — |
| TECH | 3 | 6h | 15s | 0.000 | 84 | 0 | 0 | $0.0000 | — |
| TECH | 3 | 6h | 15s | 0.010 | 84 | 0 | 0 | $0.0000 | — |
| TECH | 3 | 6h | 15s | 0.020 | 84 | 0 | 0 | $0.0000 | — |
| TECH | 3 | 6h | 60s | 0.000 | 84 | 0 | 0 | $0.0000 | — |
| TECH | 3 | 6h | 60s | 0.010 | 84 | 0 | 0 | $0.0000 | — |
| TECH | 3 | 6h | 60s | 0.020 | 84 | 0 | 0 | $0.0000 | — |
| TECH | 4 | 6h | 15s | 0.000 | 10 | 0 | 0 | $0.0000 | — |
| TECH | 4 | 6h | 15s | 0.010 | 10 | 0 | 0 | $0.0000 | — |
| TECH | 4 | 6h | 15s | 0.020 | 10 | 0 | 0 | $0.0000 | — |
| TECH | 4 | 6h | 60s | 0.000 | 10 | 0 | 0 | $0.0000 | — |
| TECH | 4 | 6h | 60s | 0.010 | 10 | 0 | 0 | $0.0000 | — |
| TECH | 4 | 6h | 60s | 0.020 | 10 | 0 | 0 | $0.0000 | — |

## Broad-cohort control

For comparison, this control allows every current category leader to
vote without the prior directional-behavior gate. It is diagnostic,
not the recommended strategy.

| Niche | Raw | Resolved | Accepted | P&L | Win rate |
|---|---:|---:|---:|---:|---:|
| CRYPTO | 296 | 113 | 40 | $-40.1708 | 2.5% |
| ECONOMICS | 5 | 0 | 0 | $0.0000 | — |
| POLITICS | 1 | 0 | 0 | $0.0000 | — |
| SPORTS | 2 | 2 | 0 | $0.0000 | — |
| TECH | 435 | 0 | 0 | $0.0000 | — |

## Cohort coverage

| Stored leaderboard category | Wallets | Earliest archived cohort trade | Latest archived cohort trade |
|---|---:|---|---|
| CRYPTO | 10 | 2026-03-09T20:02:17Z | 2026-07-24T03:28:40Z |
| ECONOMICS | 10 | 2026-04-30T14:49:50Z | 2026-07-24T03:18:33Z |
| OVERALL | 20 | 2026-07-11T02:43:46Z | 2026-07-24T03:24:01Z |
| POLITICS | 10 | 2025-12-10T02:39:36Z | 2026-07-24T03:17:39Z |
| SPORTS | 10 | 2026-07-11T02:43:46Z | 2026-07-24T03:24:01Z |
| TECH | 10 | 2026-04-07T23:31:17Z | 2026-07-24T03:23:18Z |

## What this can and cannot establish

- A stable positive result across vote thresholds, delays, and execution
  stresses is useful historical evidence, not a profit guarantee.
- Current winners were selected retrospectively; this is survivorship bias.
- Public trade timestamps do not prove the trader initiated the idea, and
  linked wallets can make apparent agreement less independent.
- Historical public trade tape approximates availability; exact historical
  order-book depth and a guaranteed $1 fill are unavailable.
- A tiny positive result or one driven by only a few resolutions is noise.

## Decision

Reject broad leaderboard consensus copying: its best-resolved
control was materially negative. No niche qualifies for deployment.
Keep only the past-only directional version as a paper monitor and
rerun the frozen matrix when additional signals resolve.