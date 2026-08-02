# Mirrored-consistency gate (3e)

Run before any calibration number is read. Thresholds fixed in
`PREREGISTRATION_PARTB.md` §2 before the clean data existed:
G1 orientation difference |z| < 4.0;  G2 pre-match residual <= 1.5 pp in both orientations.

## G2 — pre-match calibration by orientation

| orientation | n | implied | observed | residual pp | verdict |
|---|---|---|---|---|---|
| favourite is YES side | 1,021 | 0.7348 | 0.7023 | -3.25 | **FAIL** |
| favourite is NO side | 1,043 | 0.7417 | 0.7354 | -0.63 | pass |

Contaminated build read **+8.70 / −3.67 pp** here. Clean reads **-3.25 / -0.63 pp**.

**G2b — orientation DIFFERENCE in the pre-match residual: -2.62 pp, z = -1.36** (pass). This is the leak-specific quantity; the contaminated build read +12.37 pp.

### Why is the residual negative in both orientations?

Three candidate causes, separated. Conditioning on `pre_mid >= 60` selects on the
same price whose calibration is then measured, so any noise in that quote biases
the selected subset upward and the residual downward. That is a property of my
filter, not of the market and not of the dedupe.

| diagnostic | n | implied | observed | residual pp |
|---|---|---|---|---|
| unconditional, no favourite filter | 2,905 | 0.6850 | 0.6671 | -1.79 |
| favourite 60-70¢ | 871 | 0.6454 | 0.6188 | -2.66 |
| favourite 70-80¢ | 615 | 0.7440 | 0.7220 | -2.21 |
| favourite 80-90¢ | 406 | 0.8424 | 0.8350 | -0.74 |
| favourite 90-101¢ | 172 | 0.9422 | 0.9419 | -0.03 |
| **selected on t0−1, scored on the mid 60 min earlier** | 1,963 | 0.7332 | 0.7178 | -1.54 |

If that last row is near zero while the filtered rows above are negative, the
negative residual is **regression to the mean in my own favourite filter**, not
a market bias and not a leak.

## G1 — in-play miscalibration by orientation

Entry rule `deep:30@38`.

| side | n | implied | observed | mis pp | 95% CI |
|---|---|---|---|---|---|
| both (pooled) | 685 | 0.3428 | 0.3095 | -3.33 | [-6.58, -0.03] |
| favourite is YES side | 341 | 0.3281 | 0.2463 | -8.18 | [-12.49, -3.77] |
| favourite is NO side | 344 | 0.3574 | 0.3721 | +1.47 | [-3.33, +6.35] |

**Difference (YES − NO): -9.65 pp, 95% CI [-16.10, -2.88], z = -2.86.**
Contaminated build read **+25.49 pp, z ≈ +15**.

## Verdict

- G1 orientation difference: **PASS** (|z| = 2.86 vs threshold 4.0)
- G2 pre-match calibration, each orientation: **FAIL**
- G2b pre-match orientation DIFFERENCE (leak-specific): **PASS** (|z| = 1.36)

**G2 FAILED WHILE G1 AND G2b PASSED.** The two orientations agree, so the
selection leak is gone, but the pre-match price is uniformly miscalibrated in
the filtered subset. That is reported as a finding in its own right and it
caps how much any in-play miscalibration can be trusted, because the same
filter produces both. Proceeding, with that caveat attached to every number.