# RESULTS — SET-1 OVERSHOOT

> # ⚠ RETRACTED 2026-08-01 — DO NOT USE THE NUMBERS BELOW
>
> Phase 5's both-sides validity check found that the undershoot reported here
> measures **+14.05 pp** where the favourite is the market's YES side and
> **−11.43 pp** where it is the NO side — a 25.5 pp disagreement between two
> halves that must agree.
>
> **Cause: the Phase 0 dedupe rule kept the higher-volume side of each mirrored
> pair. Volume is read after settlement and the winning side attracts more
> trading, so the rule selected on the outcome** (kept side wins 53.56%,
> z = +10.0). Because the analysis orients to the favourite, that bias entered
> the two halves with opposite sign, and the pooled −2.53 pp headline is the
> residual of two large opposite artifacts with unequal weights.
>
> Everything built on the event set — the Phase 2 calibration tables, the Phase 3
> segments, the Phase 4 holdout and walk-forward, and the "no overshoot"
> verdict — is **void pending a re-run** on an outcome-independent dedupe.
>
> Still valid: detector accuracy (0.825) and t0 tuning, which were validated
> against external scorelines rather than outcomes; mirror equivalence; the fee
> arithmetic; the synthetic controls; and the Phase 5 cost anatomy.
>
> Full account: [PHASE5_RESULTS.md §0](PHASE5_RESULTS.md).

Kalshi tennis, 2026-05-25 to 2026-08-01. 19,782 matches pulled, 16,258 usable,
5,396 qualifying events. Run 2026-07-31 on the laptop. No live bot, no execution
code, no order endpoints touched; all data from public read-only market
endpoints.

---

## 1. The verdict, in three sentences

**No. The market does not overshoot on the set-1 dip.** Across all 28 honest
entry definitions the favourite wins *less* often than the dipped price implies,
not more — a miscalibration of −1.1 pp on the pre-committed rule and −2.5 pp on
the best-targeted one (p = 0.0007), which replicates on a temporal holdout it
never saw. The undershoot is real and points at the underdog, but it is smaller
than the cost of trading it in every configuration tested, so there is no edge
here in either direction.

---

## 2. The Phase 2 calibration table — the whole study in one table

Entry rule `deep:12`: the first minute the favourite's mid is ≥12¢ below its
pre-match level *and* has not made a new low for 8 minutes, entered 3 minutes
later. A stopping time. Entry at the **ask + 1¢**, exact `Decimal` fees, held to
settlement (one fee).

`impl p` is the market's implied probability at entry. `obs` is what actually
happened. `mis pp` is observed minus implied — **positive means overshoot, which
is the thing being looked for.** `BE win` is the win rate needed to break even.

| entry ¢ | n | impl p | obs | mis pp | p(1s) | p(2s) | fill | fee | BE win | net ¢ |
|---|---|---|---|---|---|---|---|---|---|---|
| 0–5 | 8 | 0.025 | 0.000 | −2.50 | 1.000 | 1.000 | 4.6 | 0.31 | 0.049 | −4.93 |
| 5–10 | 24 | 0.072 | 0.083 | +1.15 | 0.522 | 1.000 | 9.7 | 0.61 | 0.103 | −1.99 |
| 10–15 | 15 | 0.121 | 0.333 | +21.23 | 0.028 | 0.056 | 14.6 | 0.87 | 0.155 | +17.87 |
| 15–20 | 22 | 0.177 | 0.182 | +0.52 | 0.563 | 1.000 | 19.8 | 1.11 | 0.209 | −2.70 |
| 20–25 | 53 | 0.227 | 0.302 | +7.46 | 0.131 | 0.262 | 25.1 | 1.31 | 0.264 | +3.82 |
| 25–30 | 99 | 0.277 | 0.263 | −1.47 | 0.663 | 0.850 | 30.0 | 1.47 | 0.315 | −5.20 |
| 30–35 | 248 | 0.327 | 0.355 | +2.82 | 0.189 | 0.378 | 34.7 | 1.58 | 0.363 | −0.83 |
| 35–40 | 427 | 0.375 | 0.342 | −3.29 | 0.924 | 0.183 | 39.6 | 1.67 | 0.413 | −7.08 |
| 40–45 | 545 | 0.423 | 0.413 | −1.05 | 0.703 | 0.654 | 44.6 | 1.73 | 0.464 | −5.09 |
| 45–50 | 691 | 0.474 | 0.412 | −6.15 | 0.999 | 0.002 | 49.8 | 1.75 | 0.516 | −10.34 |
| 50–55 | 714 | 0.523 | 0.510 | −1.35 | 0.776 | 0.492 | 54.8 | 1.73 | 0.565 | −5.52 |
| 55–60 | 665 | 0.572 | 0.553 | −1.85 | 0.843 | 0.354 | 59.6 | 1.68 | 0.613 | −5.95 |
| 60–65 | 574 | 0.623 | 0.603 | −2.01 | 0.852 | 0.336 | 64.8 | 1.60 | 0.663 | −6.07 |
| 65–70 | 456 | 0.672 | 0.726 | +5.41 | 0.008 | 0.017 | 69.7 | 1.47 | 0.712 | +1.38 |
| 70–75 | 395 | 0.720 | 0.696 | −2.39 | 0.863 | 0.324 | 74.4 | 1.33 | 0.758 | −6.16 |
| 75–80 | 270 | 0.772 | 0.778 | +0.54 | 0.444 | 0.888 | 79.7 | 1.13 | 0.809 | −3.10 |
| 80–85 | 141 | 0.821 | 0.858 | +3.71 | 0.150 | 0.301 | 84.5 | 0.92 | 0.854 | +0.42 |
| 85–90 | 44 | 0.868 | 0.864 | −0.44 | 0.646 | 1.000 | 89.2 | 0.67 | 0.898 | −3.47 |
| 90–95 | 5 | 0.916 | 1.000 | +8.40 | 0.641 | 1.000 | 93.8 | 0.41 | 0.942 | +5.79 |

**Pooled, n = 5,396**

| | |
|---|---|
| implied / observed | 0.5403 / 0.5291 |
| **miscalibration** | **−1.13 pp**, 95% CI [−2.38, +0.12] |
| Poisson-binomial p | 0.961 one-sided for overshoot; 0.083 two-sided |
| **net expectancy** | **−5.08 ¢/contract**, 95% CI [−6.35, −3.83] |
| breakeven miscalibration required | **+3.96 pp** |

The two buckets with p < 0.05 (45–50 at −6.15, 65–70 at +5.41) point in opposite
directions. Out of 19 buckets you expect about one at p < 0.05 by chance; two,
disagreeing on sign, is what noise looks like.

The per-bucket null is a **Poisson-binomial** evaluated by exact simulation, not
a binomial at the bucket mean — the implied probabilities differ within a 5¢
bucket and the normal approximation misstates the tail at these n.

### Two stricter versions of the same test

| test | n | precision¹ | miscalibration | p (2-sided) | net ¢ |
|---|---|---|---|---|---|
| pre-committed `deep:12` | 5,396 | 0.559 | −1.13 [−2.38, +0.12] | 0.083 | −5.08 |
| **best-targeted `deep:30@38`** | 3,427 | 0.788 | **−2.53 [−3.99, −1.03]** | **0.0015** | −6.24 |
| **label-verified subsample²** | 476 | 1.000 | **−5.49 [−9.38, −1.39]** | **0.0092** | −9.15 |

¹ fraction of fired events where an external scoreline confirms the favourite
really did lose set 1. ² only matches where that is confirmed — no inference in
the state variable at all.

**The cleaner the measurement of "the favourite actually lost set 1", the more
negative the result gets.** That monotonicity is the strongest single piece of
evidence in the study, and it runs against the hypothesis.

---

## 3. Detector accuracy, and how much it limits confidence

Full detail in [PHASE1_DETECTOR_ACCURACY.md](PHASE1_DETECTOR_ACCURACY.md).
Validated against **2,787 matches** with externally sourced scorelines (Sackmann
frozen mirror, all tiers, first two weeks; tennis-data.co.uk, main tour, almost
the whole window). Kalshi's own settlement agrees with the external match winner
on 99.55% of joined rows, so join error is not in play.

| what | result |
|---|---|
| **Set-1 direction accuracy** | **0.825** (base rate 0.685) — clears the 0.80 bar |
| Match start `t0` | median **+5 min** vs true playing minutes, MAD 6 min, n = 2,150 |
| Timing sanity check | changepoint minute rises monotonically with games in set 1 (35 → 64 min for 6 → 13+ games), Spearman +0.273, p = 7e−49 |
| **Event precision** | **0.559** for `deep:12`, **0.788** for `deep:30@38` |

The 0.825 and the 0.559 measure different things and the gap matters. Direction
accuracy asks whether the sign of the biggest move identifies the set-1 winner.
Precision asks how many of the matches the *entry rule actually fires on* were
really set-1 losses. A favourite who goes down an early break, drops 12¢, and
then wins the set trips the rule. That is not a detector error — the price
really did fall — but it is not the hypothesis either.

**How much this limits the conclusion: less than it looks.** Three reasons.
First, the conclusion is identical across all 28 honest entry definitions
including eight that use no changepoint at all (fixed offsets from `t0`), so it
is not an artefact of the detector. Second, the effect gets *stronger* as
precision improves, which is the opposite of what detector noise does — noise
attenuates toward zero. Third, the label-verified subsample, which has no
inference in it whatsoever, gives the most negative estimate of all.

Where the detector genuinely does limit things is the Phase 3 segments: a
subgroup defined on inferred state is a subgroup defined partly on noise.

---

## 4. Segmentation

**The Phase 2 gate failed, so by the pre-registered rule Phase 3 should not have
run.** It was run anyway and is labelled throughout as exploratory, for two
reasons: you asked specific questions about favourite strength and about men's
versus women's tennis that deserve direct answers, and the output is a concrete
demonstration of what subgroup hunting produces on a null. Nothing in it is a
trading candidate. Full tables in
[reports/p3_segments.md](reports/p3_segments.md).

Phase 3 runs on the **train half only** (n = 3,238) so the holdout stays clean;
the 3a table below is the exception and is shown full-sample because the holdout
comparison for it is the point. Every other Phase 3 number in this section is a
train-half number.

**Total hypotheses evaluated: 90. Surviving Benjamini–Hochberg at q = 0.10: 28.**
See [HYPOTHESIS_LEDGER.md](HYPOTHESIS_LEDGER.md). BH is applied to **two-sided**
p-values across the whole ledger, because an undershoot is a finding here and a
one-sided overshoot test would hide it.

**26 of the 28 survivors are negative — the undershoot.** Exactly two are
positive, and neither is an edge:

- `cpleak-10` (+6.75 pp), which is the **deliberately leaky diagnostic** built to
  fabricate an edge from future data. Its survival is the control working.
- `90¢+` favourites (+7.93 pp), dismantled immediately below.

That is what a robust null with a consistent wrong-direction bias looks like:
almost everything that clears correction points the same way, and it is not the
way the hypothesis predicted.

### 3a — favourite strength. Your directional hypothesis is not supported.

You predicted the trade works when the favourite was genuinely strong (70–80%)
and failed around 51%. Full sample:

| pre-match | n | miscalibration | 95% CI | net ¢ |
|---|---|---|---|---|
| 60–70¢ | 2,189 | −1.89 | [−3.88, +0.17] | −5.90 |
| **70–80¢** | 1,668 | **−1.85** | [−4.16, +0.49] | −5.85 |
| 80–90¢ | 1,147 | −0.67 | [−3.40, +2.04] | −4.60 |
| 90¢+ | 392 | +4.89 | [+1.05, +8.73] | +1.32 |

70–80 and 60–70 are indistinguishable (−1.85 vs −1.89) and both are negative.
The band you identified as the good one is not better than the band you
identified as the bad one.

### The one positive cell in the entire study, and why it is not real

`90¢+` favourites is the only cell anywhere that shows a positive net
expectancy, and it survived FDR. Given this project's history the burden is on
it, and it fails:

| stress test | result |
|---|---|
| train → holdout | **+7.93 pp → +0.04 pp** (n 241 → 151). Gone. |
| by time fifth | +3.0, **+10.2, +7.0**, −2.4, −1.1 — confined to mid-June/early-July |
| **day-clustered net CI** | **[−3.27, +2.92] ¢** — straddles zero |
| by tour | WTA n=13 at +24 pp, CHALL n=25 at −14 pp — noise in the small cells |
| company it keeps | the only other positive BH survivor out of 90 is the deliberate leak canary |

The match-clustered CI made this look real; resampling whole days instead of
individual matches, which is the right unit when matches share a tournament and
a day, dissolves it. It is one cell out of 57, contradicts the pre-registered
direction, and does not persist. **Not an edge.**

### 3b/3c/3f — drop size, set closeness, series and gender

Every level is negative or indistinguishable from zero; none survives FDR.
On men's versus women's tennis specifically: ATP −4.61, ITF-M −0.61 versus
WTA −1.55, ITF-W −1.37. **No meaningful difference, and the direction is not
consistent** — the men's main tour is the worst cell and men's ITF is the best.
"Men's tennis is more predictable" is not supported here. Note ITF is 76% of the
book, so the pooled number is mostly an ITF number.

### 3d — serve order: **not answered.**

Serve order in set 2 is not recoverable from price and no reachable source
publishes it. Claiming otherwise would be inventing a variable. The tradeable
form of the question was tested instead — all five variants lose money, and
waiting for a further fall is the worst of them (−6.78 ¢, −2.82 pp).

### 3e — exit rules: **all 25 cells lose money.**

Best is hold-to-settlement at −5.25 ¢; the worst target/stop combination is
−7.49 ¢. There is no plateau because there is nothing to stand on. Early exits
pay two fees instead of one, which costs about 1.5 ¢ on its own and explains
most of the ranking.

### 3g — player tendencies: **dropped as underpowered, not reported as noise.**

1,862 distinct favourites, **median 1 qualifying match each**, zero with 10+.
Separating a genuine 60% comeback player from a 50% one at 80% power needs about
**392 matches per player**. The data offers one.

---

## 5. Holdout and walk-forward

Full detail in [reports/p4_validation.md](reports/p4_validation.md). Split at
2026-07-06, oldest 60% / newest 40%.

**Confound stated plainly:** the split sits inside the clay→grass→hard run of
the calendar, so a temporal holdout in tennis is also a surface and
tournament-mix change. Tour composition of both halves is printed in the report.

| | n | miscalibration | net ¢ |
|---|---|---|---|
| train | 3,238 | −1.20 [−2.84, +0.44] | −5.25 |
| holdout | 2,158 | −1.02 [−3.01, +1.06] | −4.83 |

**The undershoot replicates on the holdout** (best-targeted rule): train −2.17 pp
(p = 0.014), holdout **−3.05 pp** (p = 0.007). Purged walk-forward with a 48-hour
embargo: 4 of 5 folds negative, mean −1.39 pp, **net negative in all five**.

Of the three configurations selected on train and run once on holdout, all three
failed: `90+` collapsed from +7.93 to +0.04, `drop 30¢+` went +0.91 → +1.62 with
net still −1.96 ¢, `drop 10–20¢` went −0.32 → −0.49.

**Deflated Sharpe: 0.0000.** Per-trade Sharpe is −0.107 against an expected
maximum of +2.19 from 40 noise variants.

### The other side, since the market undershoots

The brief says to report an undershoot loudly and check the opposite side.
Fading the favourite means buying the underdog at `100 − favourite_bid`
(verified executable — see §7). Full table in
[reports/p2_fade.md](reports/p2_fade.md).

| entry rule | n | underdog mis pp | fill ¢ | breakeven | observed | **net ¢** |
|---|---|---|---|---|---|---|
| `deep:30@38` | 3,427 | +2.53 [+1.03, +4.06] | 65.8 | 0.6719 | 0.6609 | **−1.10** [−2.61, +0.46] |
| `deep:25` | 4,045 | +2.41 [+0.98, +3.86] | 59.8 | 0.6138 | 0.5998 | **−1.41** |
| `fixed+45` | 3,341 | +2.24 [+0.70, +3.81] | 50.7 | 0.5222 | 0.5058 | **−1.64** |
| `deep:20@38` | 4,190 | +2.06 [+0.63, +3.47] | 58.3 | 0.5981 | 0.5807 | **−1.74** |
| `deep:12` | 5,396 | +1.13 [−0.13, +2.40] | 48.4 | 0.4995 | 0.4709 | **−2.86** |
| `cp` | 3,518 | +0.17 [−1.24, +1.61] | 57.9 | 0.5929 | 0.5586 | **−3.43** |

**Zero of six configurations have positive mean net expectancy.** The reason is
arithmetic, not luck: after the dip the underdog is the *expensive* side, around
66¢, so the fee sits near its maximum and the fill eats most of the payout. A
2.5 pp edge cannot pay a 65.8¢ fill plus 1¢ slippage plus 1.4¢ fee, which
together demand a 67.2% win rate against the 66.1% observed. **The market is
mispriced by about 2.5 pp and the round trip costs about 3.6 pp.**

---

## 6. Synthetic control — run before the real Phase 2, both directions

| world | planted | recovered | p | net ¢ |
|---|---|---|---|---|
| null (bounded martingale, outcome drawn from terminal price) | 0 | **+0.06 pp** [−3.03, +3.07] | 0.504 | −2.96 |
| positive control | +5 pp | **+4.54 pp** [+1.51, +7.58] | 0.0029 | +1.50 |

The null world's −2.96 ¢ is exactly spread + 1¢ slippage + fees. The pipeline
invents nothing on fair data and is not blind to a real effect, so the null on
real data means *no effect* rather than *broken code* or *no power*.

**Live leak canary.** A deliberately leaky entry rule (using 10 minutes of future
data to place the entry) is kept in the grid and reports **+6.75 pp and +2.77 ¢**
on the real data — a large, entirely fabricated edge, next to −0.1 to −2.6 pp for
every honest rule. Any future run where the honest rules start resembling the
canary has a leak.

---

## 7. Data integrity checks

| check | result |
|---|---|
| Markets → matches | 40,526 → **19,782**; every event has exactly 2 markets and exactly one YES |
| Mirror relationship | `mid(A)+mid(B)−100`: median **+0.000¢**, 97.1% within 2¢, over 90,742 aligned minutes |
| Executable mirror | `(100−bid_A) − ask_B`: median **+0.000¢** — trading the favourite as NO on the kept market costs the same as YES on the sibling |
| Pseudo-replication | one market per match; **n is a match count everywhere** |
| Fee arithmetic | exact `Decimal`; 1.75¢@50, 0.63¢@90, 0.63¢@10, no float anywhere |
| Look-ahead | pre-match anchor asserted strictly before `t0`; entry asserted at or after the minute the signal became knowable |
| Filters | 68.9% of grid minutes have no quote (dormant pre-match), **4.8% dropped for spread > 15¢**, 0 crossed books |
| Liquidity honesty | median spread at entry 2¢, but **26% of entries quote ≥4¢** — the 1¢ slippage assumption is optimistic there |
| Retirements/walkovers | 365 scalar-settled matches; only **6** would ever be entered. Cost of excluding them: **−0.004 ¢**. Reason: retirements and walkovers overwhelmingly happen *before* meaningful play (171 of 363 never traded at all, median duration 20 min), so an entry ~40 min in barely touches them |
| Candle pull | 6.47M rows, 169 initial failures (0.84%) all recovered on retry — **0 unrecovered** |

---

## 8. Retracted or corrected during this session

Nothing about the *findings* was retracted, because no positive finding was ever
produced. Four defects were found in **my own code**, all before or independent
of any result being read:

1. **Look-ahead in the changepoint.** The step statistic reads 10 minutes past
   its candidate, so entering 3 minutes later used 8 minutes of the future.
   Worse, selecting the changepoint by argmax over a window is not a stopping
   time, so the martingale argument did not protect it. Fixed: primary rule is
   now a causal threshold rule, with an assertion. **Found before any real
   result existed.**
2. **Match start ~28 minutes too early.** A pure frozen-quote-gap rule let
   sparse pre-match repricing into the play window. Validated against real
   playing minutes and fixed with an activity-density floor: +28 min / MAD 24
   → +5 min / MAD 6. **Found before any real result existed.**
3. **Walk-forward embargo off by 1000×.** Parquet returns `datetime64[us]`, so
   an int64 cast is microseconds while `np.timedelta64(48,"h")` is nanoseconds
   — a 48-hour embargo became 5.5 years and silently emptied every fold. The
   first Phase 4 run printed an empty walk-forward table. **Found after the
   Phase 2 result, fixed, re-run.**
4. **Wrong verdict criterion in the fade analysis.** The code tested whether the
   CI upper bound was below zero rather than whether mean expectancy was
   positive, and printed an over-optimistic conclusion on its first run.
   Corrected before it reached this file.

Also corrected: the tennis-data name key. Names there are surname-first
(`Valentova T.`), which the existing helper keyed as `t|v`. The first truth
table silently contained **zero** tennis-data rows and covered only May–June;
fixing it added 723 matches and extended validation into July.

**Two pre-registration amendments**, logged with provenance in
[PREREGISTRATION.md](PREREGISTRATION.md#5b-amendments-with-their-provenance):
the entry rule was refined (A1) and 3d was weakened to a question price can
actually answer (A2).

---

## 9. Honest read: real edge, or noise?

**No edge. But the null here is not a shrug — it is a measurement, and it points
the other way from the hypothesis.**

The specific thing you asked about — the price falling further than the
favourite's true remaining win probability justifies — does not happen. The
opposite happens, consistently: after a favourite's price dips, the favourite
wins about 2.5 pp *less* often than the dipped price implies. That result
survives a temporal holdout it never saw, survives a purged walk-forward,
strengthens as the state measurement gets cleaner, and reaches its largest value
(−5.5 pp) on the subsample where an external scoreline confirms the set loss.
I believe the undershoot is real.

I do not believe it is tradeable. The mispricing is ~2.5 pp and the round trip
is ~3.6 pp, and the geometry is against you: the side with the edge is the
expensive side, so the fee is near its maximum exactly where you need it lowest.
Every one of the six fade configurations loses money. The gap is not close
enough to close with better execution — you would need to eliminate slippage
*and* halve the fee.

Two things worth saying about your live observation. The 70–80% band you
identified as working shows −1.85 pp, statistically identical to the 60–70% band
you identified as failing at −1.89. And the only cell in 57 that looked
profitable, `90¢+` favourites, is the one that most resembles a real pattern —
strong, plausible, FDR-surviving — and it is also the one that vanished on the
holdout and dissolved under a day-clustered bootstrap. Small samples of heavy
favourites in ITF events produce exactly that shape routinely.

The prior held. An audit of 129 prior claims in this project found 20
retractions, every one of which shrank the edge. This study adds no claim to
retract, and the one candidate that briefly looked like an exception shrank too,
on schedule. Of 90 hypotheses evaluated, 28 clear FDR and 26 of those point the
wrong way for the hypothesis; the two that point the right way are a diagnostic
I built to fake an edge, and a 241-match cell that evaporated on the holdout.

**What would change my mind:** a tick-level book with depth rather than 1-minute
candles, so entry could be modelled at real resting size instead of ask+1¢; a
point-by-point score feed, which would raise event precision from 0.79 to 1.0
and let the set-1 question be asked cleanly rather than inferred; and enough of
both to test whether the undershoot is larger in the thin ITF markets where the
2.5 pp might exceed a spread you could actually cross. None of that is available
from Kalshi's public endpoints today.
