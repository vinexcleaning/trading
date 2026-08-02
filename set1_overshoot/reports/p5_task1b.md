# Task 1b — maker versus taker

Entry rule `deep:30@38`, n = **3,436** opportunities. Fade = sell the favourite.

**Taker baseline**: fills 100% by assumption, mean fill 65.70¢, fee 1.44¢, net **-1.195¢** [-2.670, +0.318].

## Fill rates

Fill requires the favourite's bid to trade **strictly above** the resting level in
some later minute — last in queue, no credit for merely being touched.

| resting style | mean level ¢ | 5 min | 10 min | 20 min | 30 min | to end of match |
|---|---|---|---|---|---|---|
| improve | 36.29 | 70.9% | 79.7% | 84.3% | 86.5% | 88.2% |
| join_ask | 37.65 | 63.1% | 73.6% | 80.0% | 82.9% | 85.6% |
| passive | 38.65 | 55.0% | 67.3% | 75.5% | 79.3% | 82.8% |

## Net expectancy, maker vs taker

`per fill` is the mean over filled trades only. **`per opportunity` is the number
that matters** — unfilled chances earn nothing, and a strategy is judged on the
signals it acts on, not the subset it happened to catch.

| resting style | window | fill % | fill px ¢ | per fill, verified schedule ¢ | per fill, pessimistic (1/4 taker everywhere) ¢ | per opportunity (verified fee) ¢ |
|---|---|---|---|---|---|---|
| improve | 5 | 70.9% | 62.82 | -1.338 | -1.683 | **-0.949** |
| improve | 10 | 79.7% | 62.90 | -1.093 | -1.439 | **-0.871** |
| improve | 20 | 84.3% | 62.81 | -0.985 | -1.332 | **-0.831** |
| improve | 30 | 86.5% | 62.81 | -1.046 | -1.393 | **-0.905** |
| improve | end | 88.2% | 62.79 | -1.384 | -1.731 | **-1.220** |
| join_ask | 5 | 63.1% | 61.62 | -0.326 | -0.672 | **-0.205** |
| join_ask | 10 | 73.6% | 61.50 | -0.413 | -0.762 | **-0.304** |
| join_ask | 20 | 80.0% | 61.40 | -0.570 | -0.921 | **-0.456** |
| join_ask | 30 | 82.9% | 61.37 | -0.714 | -1.066 | **-0.592** |
| join_ask | end | 85.6% | 61.33 | -1.018 | -1.370 | **-0.871** |
| passive | 5 | 55.0% | 60.30 | -0.572 | -0.923 | **-0.314** |
| passive | 10 | 67.3% | 60.28 | -0.625 | -0.978 | **-0.421** |
| passive | 20 | 75.5% | 60.25 | -0.775 | -1.130 | **-0.585** |
| passive | 30 | 79.3% | 60.21 | -0.825 | -1.181 | **-0.654** |
| passive | end | 82.8% | 60.15 | -1.179 | -1.536 | **-0.976** |

## Adverse selection — the pre-specified kill test

A resting sell of the favourite fills only when the favourite ticks **up**. If the
fills are systematically the matches about to go wrong, the fee and spread saving
is illusory.

| resting style | window | fill % | dog win, filled | dog win, all | shift pp | fav mid at signal | fav mid at fill | drift ¢ |
|---|---|---|---|---|---|---|---|---|
| improve | 10 | 79.7% | 0.6183 | 0.6595 | -4.12 | 37.33 | 40.32 | +3.00 |
| improve | 30 | 86.5% | 0.6180 | 0.6595 | -4.15 | 37.40 | 40.43 | +3.03 |
| improve | end | 88.2% | 0.6144 | 0.6595 | -4.51 | 37.41 | 40.46 | +3.05 |
| join_ask | 10 | 73.6% | 0.6112 | 0.6595 | -4.83 | 37.40 | 41.46 | +4.07 |
| join_ask | 30 | 82.9% | 0.6069 | 0.6595 | -5.26 | 37.48 | 41.65 | +4.17 |
| join_ask | end | 85.6% | 0.6034 | 0.6595 | -5.61 | 37.51 | 41.72 | +4.21 |
| passive | 10 | 67.3% | 0.5969 | 0.6595 | -6.26 | 37.61 | 42.75 | +5.13 |
| passive | 30 | 79.3% | 0.5941 | 0.6595 | -6.54 | 37.65 | 42.89 | +5.24 |
| passive | end | 82.8% | 0.5900 | 0.6595 | -6.95 | 37.69 | 42.98 | +5.29 |

### Decomposition on the best cell (`join_ask`, 5 min)

Same matches, both ways — this isolates the price improvement from the
selection effect.

| quantity | value |
|---|---|
| opportunities | 3,436 |
| filled | 2,167 (63.1%) |
| price improvement vs taker, same matches | +3.179 ¢ |
| fee saving vs taker, same matches | +1.431 ¢ |
| **gross saving from being a maker** | **+4.610 ¢** |
| underdog win rate, all opportunities | 0.6595 |
| underdog win rate, filled only | 0.6133 |
| **cost of adverse selection** | **-4.620 ¢** (1 pp of win rate = 1 ¢) |


### Four-way decomposition, per opportunity

Reported in the same units as the sibling crypto market-making run so the two
are comparable, but **this is not two-sided market making** and the terms are
not the same objects. A passive directional entry quotes one side, so there is
no bid-ask capture; the analogue is price improvement against fair value. And
because the position is held to settlement, **the residual is marked at the
actual 0/100 outcome, never defaulted to 0.5** — the inventory-carry defect that
fabricated +2.96¢ in the crypto session cannot arise here.

| term | ¢/opportunity |
|---|---|
| edge at fair value (63.1% × 65.95% vs 62.71¢) | +2.040 |
| **adverse selection** (-4.62 pp on filled) | **-2.914** |
| price improvement vs fair value | +0.689 |
| maker fees (verified schedule) | -0.021 |
| **net per opportunity** | **-0.205** |
| identity check vs direct calculation | -0.205 (diff +0.0000) |

| bottom line | ¢/contract |
|---|---|
| taker, all 3,436 opportunities | -1.195 |
| taker, the 2,167 that would have filled | -4.936 |
| maker, those same fills | -0.326 |
| **maker, per opportunity** | **-0.205** |
| 95% CI, match-clustered | [-1.446, +1.062] |
| 95% CI, day-clustered | [-1.454, +1.061] |