# Task 3e — both-sides consistency (validity check)

If the undershoot differs materially between the two sides of the same match, the
measurement is broken and Phases 2 and 5 are both void. Run first, before any
Phase 5 conclusion depends on it.

## 1. Orientation split — full sample

`fav is YES` reads prices directly. `fav is NO` reconstructs every price as
`100 − kept_ask` / `100 − kept_bid`. Different code path, same claimed quantity.

| side | n | implied | observed | mis pp | 95% CI | p(2s) | fade net ¢ |
|---|---|---|---|---|---|---|---|
| both (Phase 2 headline) | 3,427 | 0.3643 | 0.3391 | -2.53 | [-4.05, -1.00] | 0.0013 | -1.101 |
| favourite is YES side | 1,198 | 0.3445 | 0.4850 | +14.05 | [+11.36, +16.80] | 0.0000 | -17.542 |
| favourite is NO side | 2,229 | 0.3750 | 0.2607 | -11.43 | [-13.15, -9.69] | 0.0000 | +7.736 |

**Difference (YES minus NO): +25.49 pp, 95% CI [+22.31, +28.73].**

**The two orientations DISAGREE.** Something is wrong with the price
reconstruction or with the market. Everything downstream is suspect.

Spread at entry: YES-side median 1¢, NO-side median 2¢ — a reconstruction that flipped bid and ask would show a negative or inflated spread on one side.

## 2. Mirror pairs — the same match priced twice

Events firing on **both** sides of the same match: **74**

- favourite's entry mid, kept side vs sibling side: median difference **+0.00¢**, 66.2% within 2¢
- outcome agreement: **1.0000**

| measured on | n | implied | observed | mis pp | 95% CI | p(2s) | fade net ¢ |
|---|---|---|---|---|---|---|---|
| kept side | 74 | 0.3303 | 0.3243 | -0.59 | [-10.70, +9.60] | 1.0000 | -2.959 |
| sibling side | 74 | 0.3409 | 0.3243 | -1.66 | [-11.70, +8.82] | 0.8551 | -1.731 |
