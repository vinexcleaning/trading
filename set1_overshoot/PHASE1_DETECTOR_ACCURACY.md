# PHASE1_DETECTOR_ACCURACY.md

Set-1 state is inferred from price alone -- Kalshi publishes no scoreline and no
match-start field. This file measures how well that inference works. It gates
everything downstream.

## Validation sample

- **1,381 matches** with an externally sourced set-1 result.
- Sources: Sackmann frozen mirror (all tiers, tourney weeks to 2026-06-02) and
  tennis-data.co.uk (ATP/WTA main tour, to 2026-07-26).
- Join is on surname+initial pairs within a date window. Kalshi's own settlement
  agrees with the external match winner on **99.55%** of joined rows, so the
  join itself is sound and any error below is the detector's, not the join's.

| tour | n |
|---|---|
| ATP | 225 |
| CHALL | 180 |
| ITF-M | 373 |
| ITF-W | 382 |
| WTA | 221 |

## 1. Direction -- who won set 1

Detector: sign of the largest sustained price step in minutes 15-90 of play.

**Overall accuracy: 0.809** (n=1,381, base rate 0.697)

Alternative rules, for comparison -- sign of (mid at minute T) minus the pre-match mid:

| rule | accuracy |
|---|---|
| changepoint step | 0.809 |
| mid at +25min vs pre-match | 0.706 (n=1,381) |
| mid at +30min vs pre-match | 0.731 (n=1,378) |
| mid at +35min vs pre-match | 0.768 (n=1,377) |
| mid at +40min vs pre-match | 0.791 (n=1,374) |
| mid at +45min vs pre-match | 0.808 (n=1,367) |
| mid at +50min vs pre-match | 0.816 (n=1,358) |
| mid at +60min vs pre-match | 0.857 (n=1,335) |

Best rule: **mid at +60min, 0.857**.

### Accuracy by segment (changepoint rule)

| segment | n | accuracy |
|---|---|---|
| ATP | 225 | 0.769 |
| CHALL | 180 | 0.822 |
| ITF-M | 373 | 0.810 |
| ITF-W | 382 | 0.848 |
| WTA | 221 | 0.769 |
| pre-match <60 | 374 | 0.856 |
| pre-match 60-70 | 379 | 0.786 |
| pre-match 70-80 | 268 | 0.787 |
| pre-match 80-90 | 233 | 0.781 |
| pre-match 90+ | 127 | 0.835 |
| step<5c | 116 | 0.897 |
| 5-10c | 174 | 0.822 |
| 10-20c | 587 | 0.809 |
| 20c+ | 500 | 0.788 |

### The number that actually matters

Phase 2 conditions on: pre-match favourite (>=60c) whose price dropped >=5c by the
entry moment. Of those matches, how many really had the favourite lose set 1?

**0.518** (239 of 461 validated events)

This is far more damaging to the *interpretation* than the 0.825 direction accuracy
suggests, and it is worth being precise about why. The two numbers measure
different things. Direction accuracy asks, over all matches, whether the sign of
the biggest move identifies the set-1 winner. Event precision asks a harder
question: among matches the entry rule actually fires on, how many were really
a set-1 loss. A favourite who goes down an early break, sees the price fall 12c,
and then wins the set from there trips the entry rule and is counted as an event.
Those matches are not detector *errors* -- the price really did fall -- but they
are not what the hypothesis is about.

### Precision of each candidate entry rule

Chosen on labelled data, which is legitimate instrument calibration, and reported
here rather than buried. `after N` restricts firing to minute N onward, since a
set is rarely over before then.

| entry rule | events fired | precision | n validated |
|---|---|---|---|
| deep:8, after 0 min | 5,542 | 0.477 | 474 |
| deep:8, after 30 min | 5,182 | 0.519 | 445 |
| deep:8, after 38 min | 5,024 | 0.548 | 440 |
| deep:12, after 0 min | 5,390 | 0.518 | 461 |
| deep:12, after 30 min | 5,015 | 0.557 | 429 |
| deep:12, after 38 min | 4,827 | 0.579 | 420 |
| deep:16, after 0 min | 4,973 | 0.578 | 424 |
| deep:16, after 30 min | 4,664 | 0.619 | 399 |
| deep:16, after 38 min | 4,496 | 0.632 | 386 |
| deep:20, after 0 min | 4,551 | 0.651 | 384 |
| deep:20, after 30 min | 4,314 | 0.681 | 367 |
| deep:20, after 38 min | 4,188 | 0.688 | 359 |
| deep:25, after 0 min | 4,052 | 0.733 | 333 |
| deep:25, after 30 min | 3,910 | 0.755 | 322 |
| deep:25, after 38 min | 3,817 | 0.757 | 317 |
| deep:30, after 0 min | 3,611 | 0.758 | 302 |
| deep:30, after 30 min | 3,525 | 0.772 | 294 |
| deep:30, after 38 min | 3,436 | 0.780 | 286 |

Best-targeted rule: **deep:30, after 38 min**, precision **0.780**.

Even the best rule leaves a substantial minority of entries that were not set-1
losses. Price alone cannot separate "lost the set" from "went down a break and
recovered" without a scoreline feed. Phase 2 is therefore run **twice**: once on
the full fired population, which is the tradeable question, and once on the
label-verified subsample, which is the literal question the brief asks. Both are
reported. Neither is allowed to stand in for the other.

## 2. Timing -- when set 1 ended

Unvalidatable directly. Tested instead against a falsifiable prediction: the
changepoint should sit later in matches where set 1 took more games.

Spearman(games in set 1, changepoint minute) = **+0.266** (p=8.09e-24, n=1,377)

| games in set 1 | n | median changepoint minute |
|---|---|---|
| 6 | 61 | 27 |
| 7 | 152 | 33 |
| 8 | 242 | 35 |
| 9 | 292 | 48 |
| 10 | 339 | 52 |
| 12 | 116 | 57 |
| 13+ | 175 | 64 |

## 3. Verdict

Direction accuracy **0.809** clears the 0.80 bar set in the brief.

Structural caveat that applies regardless of the number above: the Phase 2
calibration test conditions on **entry price**, and conditioning on price is valid
whether or not the price move was caused by a set loss. If the detector mislabels
the state, the tested question degrades from *"the favourite lost set 1"* to
*"the favourite's price fell early in the match"* -- a different and still
meaningful question, and the one a live trader would actually face. Detector error
damages the interpretation of Phase 3 segments far more than it damages Phase 2.