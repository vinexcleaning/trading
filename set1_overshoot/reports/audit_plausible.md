# Resolving the `plausible` duration filter

Current rule: keep 25 <= duration <= 330 minutes. Of 16,921 markets with a play window, **718 are dropped** (4.2%).

## What is actually being dropped

| bucket | n | favourite win rate |
|---|---|---|
| < 25 min (too short to be a match) | 684 | 0.9342 |
| 25-330 min (kept) | 16,203 | 0.7184 |
| > 330 min (suspended / stale book) | 34 | 0.5882 |

## Does the filter change theta?

Two estimates of the same quantity, at full power. If they agree, the filter is
immaterial whatever its residual test says.

| variant | n events | theta pp | 95% CI | p(2s) |
|---|---|---|---|---|
| plausible ON (current) | 3,436 | -2.42 | [-3.90, -0.93] | 0.0027 |
| plausible OFF (all play windows) | 3,437 | -2.40 | [-3.89, -0.90] | 0.0024 |
| bounds 15-400 min | 3,436 | -2.42 | [-3.88, -0.88] | 0.0019 |
| bounds 35-300 min | 3,433 | -2.38 | [-3.90, -0.81] | 0.0025 |
| bounds 45-240 min | 3,406 | -2.66 | [-4.23, -1.14] | 0.0006 |

**Difference (OFF minus ON): +0.02 pp, 95% CI [-2.05, +2.16].**

The filter does not move theta. It is immaterial to the headline, and the
z = -3.53 residual reflects that the excluded matches are genuinely odd
objects -- sub-25-minute 'matches' and multi-day stale books -- not that the
filter is selecting on the outcome among comparable matches.

## Can the residual test be made powerful enough?

Widening the kept band shrinks the dropped arm further; narrowing it grows the
dropped arm until the test has power. Narrowing is not a proposal to change the
filter -- it is a way to interrogate the same boundary at a sample size where the
guard can actually speak.

```
duration-band residual tests
============================
  UNTESTABLE [duration band 25-330 min] calibration residual: kept +0.0024 (n=16,203) vs dropped +0.0370 (n=718); diff -0.0346, z = -3.53, MDE = 2.75 pp  <-- UNTESTABLE: the smaller arm (718 rows) cannot resolve a 2.0 pp shift.
  UNTESTABLE [duration band 35-300 min] calibration residual: kept +0.0011 (n=15,801) vs dropped +0.0439 (n=1,120); diff -0.0429, z = -5.39, MDE = 2.23 pp  <-- UNTESTABLE: the smaller arm (1,120 rows) cannot resolve a 2.0 pp shift.
  UNTESTABLE [duration band 45-240 min] calibration residual: kept -0.0008 (n=15,213) vs dropped +0.0459 (n=1,708); diff -0.0467, z = -6.23, MDE = 2.10 pp  <-- UNTESTABLE: the smaller arm (1,708 rows) cannot resolve a 2.0 pp shift.
  UNTESTABLE [duration band 55-200 min] calibration residual: kept -0.0020 (n=14,081) vs dropped +0.0334 (n=2,840); diff -0.0354, z = -4.89, MDE = 2.03 pp  <-- UNTESTABLE: the smaller arm (2,840 rows) cannot resolve a 2.0 pp shift.
  **FAIL**   [duration band 65-180 min] calibration residual: kept -0.0041 (n=12,718) vs dropped +0.0281 (n=4,203); diff -0.0321, z = -4.78, MDE = 1.88 pp  <-- THE FILTER SHIFTS CALIBRATION. It is selecting on something correlated with the outcome.

5 rules: 0 pass, 1 fail, 4 untestable
```

Read the MDE column, not just z. A band only becomes testable once the dropped
arm is large enough, and by then it is a different filter. The honest summary is
that the 25-330 boundary cannot be cleared by this test at this sample size, and
the theta comparison above is what settles whether that matters.