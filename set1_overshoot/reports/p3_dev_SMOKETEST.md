# Phase 3 -- segmentation (TRAIN (oldest 60%))

Split at **2026-07-13 18:50 UTC**. train n=227, holdout n=151. Working set: **n=227**.

Every level below is written to `HYPOTHESIS_LEDGER.md` and carried into the Benjamini-Hochberg correction, including the levels skipped for small n.

### 3a favourite strength (pre-match mid)

| level | n | implied | observed | mis pp | 95% CI | p(1s) | net c/contract |
|---|---|---|---|---|---|---|---|
| 60-70 | 104 | 0.408 | 0.462 | +5.37 | [-3.84, +14.30] | 0.1469 | +1.788 |
| 70-80 | 69 | 0.513 | 0.493 | -2.04 | [-13.05, +9.81] | 0.6829 | -5.536 |
| 80-90 | 43 | 0.605 | 0.581 | -2.36 | [-16.64, +11.52] | 0.6883 | -5.796 |
| 90+ | 11 | - | - | *n too small* | - | - | - |

### 3b drop size

| level | n | implied | observed | mis pp | 95% CI | p(1s) | net c/contract |
|---|---|---|---|---|---|---|---|
| 5-10c | 35 | - | - | *n too small* | - | - | - |
| 10-20c | 57 | 0.603 | 0.667 | +6.39 | [-6.52, +18.51] | 0.1911 | +2.906 |
| 20-30c | 75 | 0.463 | 0.400 | -6.34 | [-17.11, +5.12] | 0.8914 | -9.927 |
| 30c+ | 60 | 0.342 | 0.317 | -2.50 | [-14.27, +9.57] | 0.7122 | -5.959 |

### 3c first-set closeness (drop vs cohort median)

| level | n | implied | observed | mis pp | 95% CI | p(1s) | net c/contract |
|---|---|---|---|---|---|---|---|
| close set (small drop) | 112 | 0.585 | 0.643 | +5.80 | [-3.21, +14.46] | 0.1171 | +2.213 |
| decisive set (large drop) | 115 | 0.406 | 0.357 | -4.98 | [-13.49, +3.56] | 0.8902 | -8.448 |

### 3f series and gender

| level | n | implied | observed | mis pp | 95% CI | p(1s) | net c/contract |
|---|---|---|---|---|---|---|---|
| CHALL | 227 | 0.494 | 0.498 | +0.34 | [-5.84, +6.51] | 0.4836 | -3.188 |

### 3-extra entry price band

| level | n | implied | observed | mis pp | 95% CI | p(1s) | net c/contract |
|---|---|---|---|---|---|---|---|
| <30c | 18 | - | - | *n too small* | - | - | - |
| 30-40c | 53 | 0.361 | 0.302 | -5.92 | [-17.72, +7.09] | 0.8534 | -9.435 |
| 40-50c | 54 | 0.449 | 0.519 | +6.96 | [-6.26, +20.25] | 0.1855 | +3.431 |
| 50-60c | 42 | 0.552 | 0.571 | +1.98 | [-13.83, +16.35] | 0.4631 | -1.708 |
| 60c+ | 60 | 0.693 | 0.667 | -2.63 | [-15.08, +9.00] | 0.7248 | -6.019 |

### 3e exit rules

Entry fill is the ask plus 1c of slippage in every cell. Exits sell at the **bid**.
Hold-to-settlement pays **one** fee; every early exit pays **two**.

| target | stop | net c/contract | 95% CI | sd | % exited early |
|---|---|---|---|---|---|
| - | - | -3.188 | [-9.634, +3.152] | 47.9 | 0.0% |
| - | 15 | -5.213 | [-8.912, -1.565] | 29.4 | 73.6% |
| - | 20 | -6.153 | [-10.255, -1.936] | 32.9 | 68.3% |
| - | 25 | -5.908 | [-10.714, -1.220] | 36.3 | 62.6% |
| - | 30 | -4.110 | [-9.086, +1.309] | 40.1 | 51.5% |
| 10 | - | -6.813 | [-10.460, -3.450] | 28.2 | 70.0% |
| 10 | 15 | -6.989 | [-9.099, -4.823] | 16.1 | 98.7% |
| 10 | 20 | -7.307 | [-9.692, -4.903] | 18.6 | 98.2% |
| 10 | 25 | -7.299 | [-10.069, -4.730] | 20.8 | 97.8% |
| 10 | 30 | -6.799 | [-9.717, -3.918] | 22.6 | 95.6% |
| 15 | - | -6.674 | [-10.923, -2.550] | 31.5 | 65.2% |
| 15 | 15 | -7.158 | [-9.377, -4.953] | 17.8 | 98.7% |
| 15 | 20 | -7.715 | [-10.320, -5.055] | 20.6 | 97.4% |
| 15 | 25 | -7.786 | [-10.717, -4.797] | 23.0 | 96.9% |
| 15 | 30 | -6.836 | [-10.086, -3.571] | 25.2 | 94.3% |
| 20 | - | -6.726 | [-11.202, -2.307] | 35.0 | 58.6% |
| 20 | 15 | -6.587 | [-9.139, -3.954] | 19.8 | 97.4% |
| 20 | 20 | -7.332 | [-10.255, -4.330] | 22.9 | 96.0% |
| 20 | 25 | -7.213 | [-10.460, -3.972] | 25.3 | 95.2% |
| 20 | 30 | -6.445 | [-9.947, -3.022] | 27.6 | 92.5% |
| 25 | - | -4.161 | [-9.076, +0.619] | 37.6 | 55.1% |
| 25 | 15 | -5.613 | [-8.514, -2.745] | 22.0 | 96.5% |
| 25 | 20 | -6.037 | [-9.377, -2.600] | 25.3 | 94.7% |
| 25 | 25 | -5.487 | [-9.153, -1.836] | 27.8 | 93.8% |
| 25 | 30 | -4.528 | [-8.421, -0.602] | 30.2 | 91.2% |

Best cell: target=- stop=- at -3.188 c. 1 of 25 cells sit within 0.5c of it, so this is **an isolated peak -- treat as overfitting**.

### 3d serve order in set 2, and waiting for the first game

Serve order itself is **not recoverable from price**, and no source in reach
publishes it. Saying otherwise would be inventing a variable. What *is* testable
is the tradeable form of the same question: does waiting through the first game
or two of set 2 -- and in particular waiting to see whether the favourite holds or
is broken again -- change the risk-adjusted result? Each rule below is causal: it
only ever looks at prices at or before its own entry minute.

| rule | n | implied | observed | mis pp | 95% CI | net c | sd of net |
|---|---|---|---|---|---|---|---|
| enter immediately | 227 | 0.494 | 0.498 | +0.34 | [-5.88, +6.79] | -3.188 | 47.9 |
| wait 7 min (about one game) | 225 | 0.502 | 0.498 | -0.38 | [-6.66, +5.79] | -3.872 | 46.2 |
| wait 14 min (about two games) | 223 | 0.498 | 0.493 | -0.51 | [-6.35, +5.33] | -3.956 | 43.8 |
| wait for a further 5c fall | 184 | 0.414 | 0.397 | -1.69 | [-8.49, +4.94] | -5.385 | 47.0 |
| wait for a 5c recovery | 183 | 0.578 | 0.612 | +3.41 | [-3.30, +9.99] | -0.238 | 46.4 |

### 3g player-level comeback tendency

- distinct favourites in the sample: **169**
- median matches per favourite: **1**, p90 2, max 4
- favourites with 10+ qualifying matches: **0**

To separate a genuine 60% comeback player from a 50% one at 80% power needs about **392 qualifying matches per player**. The sample offers a median of 1.

**Dropped as underpowered.** Fewer than 30 favourites reach even 10 qualifying matches, so any per-player comeback rate here is noise with a decimal point on it.