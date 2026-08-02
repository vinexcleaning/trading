# PREREGISTRATION.md

Written **2026-07-31, before any Phase 2 or Phase 3 result had been computed or
looked at**. The candle download was still running when this was committed. The
only numbers seen at the time of writing were Phase 0 counts (market/match
totals, date range, per-series breakdown) and the detector-validation sample
size. No win rate, no calibration figure, no P&L.

Anything added to this file later is marked **[POST-HOC]** and does not get the
protection of pre-registration.

---

## 1. The single primary hypothesis

**H1 (overshoot).** Among matches where the pre-match favourite loses the first
set, the favourite's realised match-win rate conditional on the post-set-1
entry price `p` is **greater than `p`**.

- Test: pooled one-sided binomial test of observed wins against `sum(p_i)`
  expected wins, plus a per-bucket binomial test in 5¢ entry-price buckets.
- Unit of observation: **the match**. One market per match. n is a match count
  everywhere in this study.
- Primary estimand: `mean(win_i) - mean(p_i)`, in percentage points, over all
  qualifying matches. Call it **the miscalibration**.
- Direction: H1 is one-sided (overshoot). The two-sided p-value is reported as
  well, because a significant result in the *opposite* direction (undershoot)
  is a finding worth reporting and I do not want a one-sided test to hide it.

**Decision rule, fixed now:**

| Outcome | Action |
|---|---|
| Pooled miscalibration CI contains 0 | Declare null. **Stop. Do not run Phase 3.** |
| Miscalibration > 0 but below the cost breakeven at every price level | Declare "real but untradeable". Report; do not build a strategy. |
| Miscalibration > 0 and clears cost at some price level | Proceed to Phase 3. |
| Miscalibration < 0 significantly | Report undershoot loudly, then stop. |

## 2. Definitions, fixed before looking

- **Favourite**: the side whose last quoted mid strictly before the inferred
  first minute of play is ≥ 60¢. Ties/50¢ excluded by construction.
- **Pre-match price**: the last valid mid strictly before `t0`. Never a price
  at or after any decision point. Asserted in code.
- **Entry price `p`**: the favourite's **mid** at the entry moment, used for the
  calibration test. The **ask** at the same moment is used for the P&L test.
  These are deliberately different: calibration is a question about the
  market's belief; P&L is a question about what you can actually buy.
- **Entry moment**: the inferred set-1 conclusion plus a **3-minute
  stabilisation delay**. Because the detector's *timing* cannot be validated
  (no source gives set-1 end times), the primary result is reported at this
  definition **and** replicated across a grid of alternative entry moments
  (fixed offsets from `t0`, and the changepoint ±5/±10 min). If the conclusion
  flips across that grid, the conclusion is "detector-dependent", not a finding.
- **Drop**: pre-match mid minus entry mid, in cents. The event requires a drop
  of at least 5¢ — smaller than that and the "favourite lost set 1" reading is
  not credible from price alone.
- **Outcome**: `result == yes/no` on the kept market, oriented to the favourite.

## 3. Costs, fixed before looking

- Entry at the **ask**, never the mid. (The 2026-07-29 session found +14% to
  +25% ROI at mid-fill collapsing to −24% to −31% at executable fills. That is
  the single most expensive lesson in this project.)
- Plus **1¢ slippage** on entry.
- Fees: exact Decimal, `0.07 * P * (1-P)`, verified in `src/fees.py`
  (1.75¢ at 50¢, 0.63¢ at 90¢ and 10¢).
- Hold-to-settlement pays **one** fee; an early exit pays **two**.
- Matches that settle at a scalar value (retirement / walkover) are excluded
  from the main sample by Kalshi's own `result` field. They are **added back as
  a sensitivity check**, because a hold-to-settlement strategy is exposed to
  them and excluding them is a survivorship choice, not a neutral filter.

## 4. Phase 3 segmentation — the complete list, fixed now

Run **only if** Phase 2 clears. Each factor is tested one at a time against the
base effect. No factorial grid. Combinations are formed only from factors that
individually survive FDR.

| # | Factor | Levels | Pre-registered direction |
|---|---|---|---|
| 3a | Pre-match favourite strength | 60–70, 70–80, 80–90, 90+ | **Directional**: effect larger in 70–80 than in 60–70. This is the user's own live observation and is tested as stated, one-sided. |
| 3b | Drop size | <10, 10–20, 20–30, 30+ ¢ | Directional: larger drops → larger overshoot. |
| 3c | First-set closeness | inferred from drop magnitude conditional on pre-match price | Directional: a close set should produce a smaller drop. Tested as a property of the market first (does it?), then as an effect modifier. |
| 3d | Serve order in set 2 | favourite serves first / not; entry before vs after the first service game; entry after an immediate break | None. Report expectancy **and** variance. |
| 3e | Exit rule | hold; targets +10/+15/+20/+25¢; stops none/−15/−20/−25/−30¢ | None. Report the whole surface. A single sharp peak is called overfitting in the report; only a broad plateau counts. |
| 3f | Series / gender | ATP, WTA, CHALL, ITF-M, ITF-W, pooled | Directional: men's more predictable → smaller overshoot in ATP/ITF-M. Note ITF is ~76% of the book, so pooled ≈ ITF. |
| 3g | Player comeback tendency | rank on first half, evaluate on second half | Expected to be underpowered. Power will be computed and reported; if the sample cannot distinguish a 60% from a 50% comeback player, this is dropped rather than reported as noise. |

Multiplicity: **every** combination evaluated goes in `HYPOTHESIS_LEDGER.md`,
including ones abandoned mid-way and including the entry-timing grid.
Benjamini–Hochberg FDR at q=0.10 across the entire ledger. The total count
appears in the final report.

## 5. Validation, fixed now

- **Temporal split**: oldest 60% / newest 40% by match close time. Holdout is
  not touched until Phase 3 is finished. Only the top 2–3 configurations are
  run on it, once.
- **Synthetic control**: run *before* the real Phase 2, on price paths that are
  bounded martingales with matched volatility and matched duration, with
  outcomes drawn from the process. A fair market must show zero miscalibration
  and negative net expectancy equal to spread + fees. If the pipeline reports
  edge there, all results are void.
- **Bootstrap**: 10,000 resamples clustered by match for every P&L CI.
- **Deflated Sharpe** using the ledger's total variant count.

## 5b. Amendments, with their provenance

Recorded so the reader can discount them appropriately rather than take the
whole document as equally protected.

**A1 — entry rule refined (made before any full-data result existed, after
seeing a 1,500-market development subset).** Section 2 defined entry as "the
inferred set-1 conclusion plus 3 minutes". Building it exposed two problems:

1. The changepoint statistic reads 10 minutes past its own candidate, so
   entering 3 minutes later used 8 minutes of future information. Worse, picking
   the changepoint by argmax over the search window is not a stopping time at
   all. Both are look-ahead; both are fixed.
2. A causal first-8¢-move rule fires on whatever moved first, which for a
   favourite losing set 1 is usually the break of serve, not the set.

The primary rule is now **`deep:12`**: the first minute at which the favourite's
mid is ≥12¢ below pre-match *and* has not made a new low for 8 minutes. It is a
stopping time and it targets the completed dip, which is what section 2 meant.

What was seen before choosing it: on the development subset, all sixteen honest
entry definitions sat within ±3 pp of zero and the deliberately leaky one sat at
+10.9 pp. `deep:12` did not exist at the time of that comparison and was chosen
on the conceptual grounds above, not on its result. **The full grid is reported
regardless of which rule is called primary**, so this choice cannot hide a
disagreement between rules — if they disagree, that is the finding.

**A2 — 3d weakened.** Serve order in set 2 is not recoverable from price and no
reachable source publishes it. The pre-registered factor is replaced by the
tradeable form of the same question (does waiting through the first game or two,
or waiting for a further fall or a recovery, change expectancy and variance).
The original 3d is **not answered**; this is stated in the results rather than
quietly substituted.

## 7. PHASE 5 — pre-registration

Written **2026-08-01, before any Phase 5 analysis was run**, with two
exceptions stated honestly: Task 1a had already been completed (it was a premise
check, and its result is recorded below because it reorders everything after
it), and the availability of tournament/surface metadata had been checked. No
Phase 5 effect size, win rate or P&L had been computed at the time of writing.

### 7.0 A premise of the Phase 5 brief is false

The brief supposes the Phase 2 fade may have been round trips paying two fees,
so that switching to hold-to-settlement could be worth ~1.5¢ against the ~1.1¢
shortfall. **It was already hold-to-settlement, one fee.** Measured anatomy of
the 3.636¢ cost bar on `deep:30@38`:

| component | ¢ | share |
|---|---|---|
| half-spread crossed | 1.197 | 33% |
| assumed slippage | 1.000 | 28% |
| taker fee | 1.439 | 40% |

Consequences, fixed before running anything else:

- **1a offers zero further saving.** Already banked.
- **1c and 1d cannot stack with 1b in the way the brief assumes.** Price
  geometry only reallocates *within* the 1.439¢ fee, and spread filtering only
  reallocates *within* the 1.197¢ half-spread. A maker already targets both.
  Presenting 1a+1b+1c+1d as four independent multiplicative reductions would
  **double-count**. They are reported as overlapping, and the stack in 1e is
  computed as one joint simulation, never as a product of separate savings.
- **1b is the phase.** It is the only lever with a ceiling (3.636¢) exceeding
  the 1.101¢ gap.

### 7.1 Primary hypothesis

**H5 (maker viability).** Fading the favourite as a *maker* — resting the order
rather than crossing — produces positive net expectancy per opportunity after
exact fees, with a 95% day-clustered CI excluding zero.

Decision rule, fixed now:

| outcome | action |
|---|---|
| per-opportunity net > 0 with day-clustered CI excluding 0, surviving holdout | report as a tradeable candidate, with caveats |
| net > 0 but CI includes 0, or fails holdout | report as "not established" |
| adverse selection cancels the fee/spread saving | declare the maker line dead and say so as prominently as any positive |
| net < 0 | null; stop |

### 7.2 Maker fill model — fixed before running

- I sell the favourite (equivalently buy the underdog). Resting levels tested,
  in favourite-price terms: **join the ask**, **improve to bid+1**, and
  **ask+1** (more passive, better price).
- **Fill requires the book to trade strictly through my level**, i.e. the
  favourite's bid *high* in some later minute exceeds my resting price (or, for
  the NO-side orientation, the ask *low* falls strictly below it). This encodes
  last-in-queue: touching my price is not enough.
- Fill windows: 5, 10, 20, 30 minutes and to end of match.
- **Unfilled opportunities count as zero P&L in the per-opportunity number.** A
  maker strategy is judged per opportunity, not per fill; reporting only filled
  trades would be survivorship.
- Fill rate is reported for every cell.
- Maker fee is **not assumed**. Three scenarios are reported side by side: fee
  = 0, fee = 0.25¢ flat, fee = 0.25 × taker formula. I cannot verify Kalshi's
  current tennis maker schedule from public read-only data, so I will not pick
  one and present it as fact.

### 7.3 Adverse selection — the pre-specified kill test

A resting order that fades a favourite can only fill when the favourite ticks
**up**, which is by construction the direction that hurts. Three measurements,
all pre-specified:

1. Underdog win rate among **filled** vs **all** opportunities.
2. Fill price against the **mid at the moment of fill**, not the mid at signal
   time. A maker always fills worse than the post-fill mid; the question is
   whether the eventual outcome still beats the fill.
3. A matched comparison: for the same matches, maker-if-filled vs taker-at-signal.

**If the win-rate drop among fills consumes the fee and spread saving, the maker
line is dead and that is the headline of Task 1**, reported as prominently as
any positive would have been.

### 7.4 Task 2 and 3 hypotheses (complete list, fixed now)

| # | test | pre-registered direction |
|---|---|---|
| 5-2a-i | best-of-5 vs best-of-3 (Grand Slam men's main draw vs all else) | **Directional**: losing set 1 in best-of-5 is less damaging, so a market that misprices comebacks should misprice these differently. Sample will be small; power reported. |
| 5-2a-ii | surface (hard/clay/grass) | none |
| 5-2a-iii | tour tier under the Task 1 cost structure | none |
| 5-2a-iv | match duration, time of day | none — reported only if a mechanism can be stated |
| 5-2b | tournament level | **exploratory, hard-gated.** Floor set by power calculation; rank on train only; evaluate once on holdout; report expected-by-chance count; check temporal concentration; mechanism sentence required |
| 5-2c | player level | expected underpowered; drop rather than report noise |
| 5-3a | dip magnitude | Directional: larger dip → larger undershoot |
| 5-3b | time since dip (0/5/10/20/30 min) | none |
| 5-3c | symmetric case: underdog loses set 1, favourite's price rises | Directional: if the effect is a general overreaction to set outcomes, the favourite's risen price should also undershoot |
| 5-3d | mid-set dips as their own population | Directional: smaller effect, larger sample |
| 5-3e | both-sides consistency across mirrored markets | **validity check, not a hypothesis.** If the undershoot differs materially between the two sides of the same match, the measurement is broken and Phases 2 and 5 are both void |

### 7.5 Multiplicity

Every cell above enters `HYPOTHESIS_LEDGER.md` and Benjamini–Hochberg runs
across the **cumulative** ledger, Phases 2–5 together, on two-sided p-values.
The Phase 2–4 ledger stood at 90 entries; the cumulative total is reported.

### 7.6 Leak canary

The deliberately leaky entry rule stays in every grid. It read **+6.75 pp** in
Phase 2 against −0.1 to −2.6 pp for honest rules. Any honest rule approaching it
means stop and find the leak.

## 6. Things that would make me retract

Stated in advance so they are not rationalised away later:

1. Any price used in a decision that is timestamped at or after that decision.
2. Detector accuracy below ~80% with a result that does not survive the
   entry-timing grid.
3. A result that exists at mid-fill and disappears at ask-fill.
4. A result carried by one tournament, one week, or one player.
5. A result that inverts on the temporal holdout.
