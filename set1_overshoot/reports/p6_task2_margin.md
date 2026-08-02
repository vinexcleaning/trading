# Task 2 (C3) — selection on set-1 margin

**Task 1 is blocked** (Apify monthly hard limit + `dayOffsets` range −7..+7 cannot
reach a −68-day window). This runs on the existing 2,887-row truth set, which
already carries set-1 game scores.

## Sample, before analysing it

- label-verified events where the favourite truly lost set 1: **479**
- drawn from: Sackmann frozen mirror (all tiers, tourney weeks to 2026-06-02) + tennis-data (ATP/WTA main tour, to 2026-07-26)
- date range: 2026-05-25 → 2026-07-26
- tier mix: ITF-M 123, ITF-W 118, WTA 89, ATP 79, CHALL 70
- **not a random sample of the 3,436 events** — it is whatever the two external sources happened to cover

Expected in advance: at this n, buckets run 40–180 and MDE is 7–12 ¢. Almost
everything should come back UNTESTABLE. That is the honest answer at this sample
size, not a failure to look.

## Reference

| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |
|---|---|---|---|---|---|---|
| all label-verified | 479 | +5.75 | +3.61 | **+2.14** | [-1.9, +6.0] | UNTESTABLE (MDE 5.7¢) |

## Set-1 margin

| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |
|---|---|---|---|---|---|---|
| 6-0 / 6-1 | 36 | – | – | – | – | *n<40* |
| 6-2 / 6-3 | 160 | +8.15 | +3.58 | **+4.56** | [-2.0, +11.1] | UNTESTABLE (MDE 9.5¢) |
| 6-4 / 7-5 | 190 | +4.12 | +3.66 | **+0.47** | [-6.4, +7.0] | UNTESTABLE (MDE 9.5¢) |
| 7-6 tiebreak | 93 | +1.84 | +3.47 | **-1.63** | [-10.9, +7.2] | loses |

## Tiebreak flag

| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |
|---|---|---|---|---|---|---|
| set 1 went to a tiebreak | 93 | +1.84 | +3.47 | **-1.63** | [-11.0, +7.3] | loses |
| set 1 did not | 386 | +6.69 | +3.64 | **+3.05** | [-1.4, +7.4] | UNTESTABLE (MDE 6.3¢) |

## Games played in set 1

| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |
|---|---|---|---|---|---|---|
| 6–8 games (blowout) | 99 | +10.86 | +3.66 | **+7.20** | [-1.2, +14.8] | UNTESTABLE (MDE 11.3¢) |
| 9–10 games | 223 | +5.58 | +3.58 | **+1.99** | [-3.9, +8.0] | UNTESTABLE (MDE 8.5¢) |
| 11+ games (long set) | 157 | +2.77 | +3.60 | **-0.83** | [-8.2, +6.2] | loses |

## Best-of format

| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |
|---|---|---|---|---|---|---|
| *(best-of-5 identified: 73 events)* | | | | | | |
| best-of-5 (Slam men's main draw) | 73 | +6.22 | +3.19 | **+3.03** | [-7.3, +13.0] | UNTESTABLE (MDE 14.7¢) |
| best-of-3 (everything else) | 406 | +5.66 | +3.68 | **+1.98** | [-2.3, +6.3] | UNTESTABLE (MDE 6.2¢) |

## Multiplicity and verdict

- buckets tested: **10** (added to the ledger)
- positive mean net: **7**; expected by chance if all truly zero: **5.0**
- **CI entirely above zero: 0**; expected by chance at 5% one-sided: **0.25**
- median MDE across buckets: **9.9 ¢** against a target effect of ~2 ¢

**No bucket has a confidence interval above zero.** Nothing to holdout-test.

## Selection canary on the label join

```
join canary
===========
  UNTESTABLE [label join (labelled vs unlabelled events)] calibration residual: kept +0.0597 (n=604) vs dropped +0.0166 (n=2,832); diff +0.0431, z = +2.15, MDE = 5.60 pp  <-- UNTESTABLE: the smaller arm (604 rows) cannot resolve a 2.0 pp shift.

1 rules: 0 pass, 0 fail, 1 untestable
```