# Mirrored-consistency gate (3e)

Run before any calibration number is read. Thresholds fixed in
`PREREGISTRATION_PARTB.md` §2 before the clean data existed:
G1 orientation difference |z| < 4.0;  G2 pre-match residual <= 1.5 pp in both orientations.

## G2 — pre-match calibration by orientation

| orientation | n | implied | observed | residual pp | verdict |
|---|---|---|---|---|---|
| favourite is YES side | 6,061 | 0.7668 | 0.7689 | +0.21 | pass |
| favourite is NO side | 6,237 | 0.7702 | 0.7757 | +0.55 | pass |

Contaminated build read **+8.70 / −3.67 pp** here. Clean reads **+0.21 / +0.55 pp**.

**G2b — orientation DIFFERENCE in the pre-match residual: -0.34 pp, z = -0.46** (pass). This is the leak-specific quantity; the contaminated build read +12.37 pp.

### Why is the residual negative in both orientations?

Three candidate causes, separated. Conditioning on `pre_mid >= 60` selects on the
same price whose calibration is then measured, so any noise in that quote biases
the selected subset upward and the residual downward. That is a property of my
filter, not of the market and not of the dedupe.

| diagnostic | n | implied | observed | residual pp |
|---|---|---|---|---|
| unconditional, no favourite filter | 16,203 | 0.7159 | 0.7184 | +0.24 |
| favourite 60-70¢ | 3,884 | 0.6471 | 0.6419 | -0.53 |
| favourite 70-80¢ | 3,502 | 0.7478 | 0.7501 | +0.23 |
| favourite 80-90¢ | 3,075 | 0.8460 | 0.8572 | +1.12 |
| favourite 90-101¢ | 1,837 | 0.9349 | 0.9483 | +1.34 |
| **selected on t0−1, scored on the mid 60 min earlier** | 9,072 | 0.7595 | 0.7621 | +0.27 |

If that last row is near zero while the filtered rows above are negative, the
negative residual is **regression to the mean in my own favourite filter**, not
a market bias and not a leak.

## G1 — in-play miscalibration by orientation

Entry rule `deep:30@38`.

| side | n | implied | observed | mis pp | 95% CI |
|---|---|---|---|---|---|
| both (pooled) | 3,436 | 0.3647 | 0.3405 | -2.42 | [-3.93, -0.87] |
| favourite is YES side | 1,707 | 0.3620 | 0.3263 | -3.57 | [-5.71, -1.50] |
| favourite is NO side | 1,729 | 0.3673 | 0.3545 | -1.28 | [-3.40, +0.88] |

**Difference (YES − NO): -2.29 pp, 95% CI [-5.30, +0.69], z = -1.49.**
Contaminated build read **+25.49 pp, z ≈ +15**.

## Verdict

- G1 orientation difference: **PASS** (|z| = 1.49 vs threshold 4.0)
- G2 pre-match calibration, each orientation: **PASS**
- G2b pre-match orientation DIFFERENCE (leak-specific): **PASS** (|z| = 0.46)

**GATE PASSED.** The two orientations agree and the pre-match price is
calibrated in both. Proceeding to read the Phase 2 calibration table.