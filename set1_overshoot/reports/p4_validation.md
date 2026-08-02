# Phase 4 -- validation

## Temporal split

Split at **2026-07-06 14:54 UTC** (oldest 60% / newest 40%).

- train: 3,234 events, 2026-05-25 to 2026-07-06
- holdout: 2,156 events, 2026-07-06 to 2026-08-01

**Confound to note explicitly:** the split falls inside the clay-to-grass-to-hard
run of the calendar. A temporal holdout in tennis is therefore also a surface and
tournament-mix change, and a configuration failing on holdout may be failing on
surface rather than on time. The composition of both halves is printed below so
that is visible rather than buried.

| tour | train | holdout |
|---|---|---|
| ATP | 194 | 108 |
| CHALL | 491 | 331 |
| ITF-M | 1,212 | 842 |
| ITF-W | 1,138 | 760 |
| WTA | 199 | 115 |

## Headline, train vs holdout

| sample | n | implied | observed | mis pp | 95% CI | p(1s) | net c | net 95% CI |
|---|---|---|---|---|---|---|---|---|
| all | 5,390 | 0.5403 | 0.5319 | -0.84 | [-2.09, +0.44] | 0.9043 | -4.792 | [-6.065, -3.503] |
| train (oldest 60%) | 3,234 | 0.5399 | 0.5275 | -1.24 | [-2.91, +0.37] | 0.9331 | -5.295 | [-6.951, -3.687] |
| holdout (newest 40%) | 2,156 | 0.5408 | 0.5385 | -0.23 | [-2.28, +1.77] | 0.5924 | -4.037 | [-5.982, -2.036] |

## Top configurations on the holdout, run once

Selected on **train only**, by train miscalibration, then evaluated once here.

| config | train mis pp | train n | holdout n | holdout mis pp | 95% CI | p(1s) | holdout net c |
|---|---|---|---|---|---|---|---|
| f_strength=90+ | +8.09 | 248 | 153 | +3.72 | [-2.72, +9.79] | 0.1590 | +0.268 |
| f_drop=30c+ | +0.55 | 479 | 283 | +2.09 | [-3.25, +7.46] | 0.2391 | -1.490 |
| f_drop=5-10c | -0.28 | 441 | 333 | +1.50 | [-3.39, +6.38] | 0.2923 | -2.225 |

## Purged walk-forward

Five sequential folds, each evaluated on data strictly after its training
window, with a **48-hour embargo** between them. Tennis matches settle within
hours, so 48h is comfortably longer than any single observation's life and no
information can straddle the boundary.

| fold | train n | test n | test window | test mis pp | 95% CI | test net c |
|---|---|---|---|---|---|---|
| 1 | 899 | 768 | 06-09 to 06-17 | -2.22 | [-5.61, +1.05] | -6.156 |
| 2 | 1,797 | 740 | 06-19 to 06-29 | -0.80 | [-4.28, +2.63] | -4.729 |
| 3 | 2,695 | 643 | 07-01 to 07-10 | -0.20 | [-3.89, +3.55] | -4.179 |
| 4 | 3,593 | 815 | 07-12 to 07-21 | +3.13 | [-0.04, +6.36] | -0.759 |
| 5 | 4,491 | 694 | 07-23 to 08-01 | -3.75 | [-7.43, -0.40] | -7.459 |

Fold-to-fold miscalibration: mean -0.77 pp, sd 2.30 pp, 1/5 positive.

## The undershoot on the holdout, and the fade it implies

Phase 2 found the market undershoots, so the direction with any edge in it is
buying the **underdog** at `100 - favourite_bid`. Phase 2 also showed that trade
losing money in every configuration. The question left for the holdout is narrow:
is the undershoot itself stable over time, or was it a property of the first half
of the sample?

| sample | n | fav implied | fav observed | mis pp | 95% CI | p(1s undershoot) | fade net c | fade net 95% CI |
|---|---|---|---|---|---|---|---|---|
| all | 3,436 | 0.3647 | 0.3405 | -2.42 | [-3.93, -0.89] | 0.0009 | -1.195 | [-2.712, +0.346] |
| train (oldest 60%) | 2,062 | 0.3651 | 0.3400 | -2.51 | [-4.45, -0.54] | 0.0058 | -1.200 | [-3.147, +0.725] |
| holdout (newest 40%) | 1,374 | 0.3640 | 0.3413 | -2.27 | [-4.66, +0.17] | 0.0310 | -1.188 | [-3.583, +1.236] |

## Day-clustered bootstrap

Each row is already one match, so the ordinary bootstrap is match-clustered by
construction. But matches on the same day at the same tournament share weather,
court, balls and draw quality, so the effective sample is smaller than the match
count. Resampling whole days instead of individual matches prices that in.

- distinct days: **69**, median 75 events per day
- miscalibration, day-clustered 95% CI: **[-2.32, +0.54] pp** (match-clustered was [-2.09, +0.44])
- net expectancy, day-clustered 95% CI: **[-6.272, -3.403] c** (match-clustered was [-6.065, -3.503])

## Deflated Sharpe

- variants evaluated (ledger rows): **39**
- per-trade Sharpe of the base configuration: **-0.1010** (skew -0.11, kurtosis 1.34)
- expected maximum Sharpe from 39 pure-noise variants: **+2.1795**
- **deflated Sharpe probability: 0.0000** (probability the true Sharpe exceeds zero once selection is accounted for)

The observed Sharpe does not exceed what this many variants would produce from noise alone.