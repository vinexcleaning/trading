# PROGRESS.md — SET-1 OVERSHOOT

Box time, 2026-07-31. **Laptop only** — the desktop crypto session was never
touched. No live bot, no execution code, no order endpoints. Public read-only
market data throughout.

**Status: COMPLETE.** See [RESULTS.md](RESULTS.md).

| Time | Unit | Status |
|---|---|---|
| ~20:05 | Env check, prior-project defect review | done |
| ~20:10 | API probe — 1-min candles, `linear_cent` grid | done |
| ~20:15 | **P0a** 40,526 markets across 5 series | done |
| ~20:20 | **P0b** dedupe → 19,782 matches; every event exactly 2 markets, one YES | done |
| ~20:25 | **P0d** truth table: 2,886 matches, 5 tours, 99.55% settlement agreement | done |
| ~20:35 | **P0c** candle pull launched | done, 93.9 min |
| ~20:40 | Exact `Decimal` fees, verified | done |
| ~20:45 | `PREREGISTRATION.md` — written before any Phase 2 number existed | done |
| ~21:00 | **P1** `t0` tuned against Sackmann playing minutes | done |
| ~21:15 | **Own look-ahead leak found and fixed** | done |
| ~21:35 | Synthetic controls, both directions | **passed** |
| ~22:20 | Causal stopping-time rules; `deep:12` made primary | done |
| ~22:45 | Candle pull finished: 6.47M rows, 169 failures → **all recovered on retry** | done |
| ~22:55 | **P0e** mirror verification: median difference **0.00¢** | done |
| ~23:00 | **P1** state extraction: 16,258 usable matches | done |
| ~23:05 | **P1** detector: direction **0.825**, `t0` **+5 min / MAD 6** on n=2,150 | done |
| ~23:10 | **P1** event precision measured: 0.559 → 0.788 across rules | done |
| ~23:20 | **P2 BASE TEST** — no overshoot; significant **undershoot** | done |
| ~23:30 | **P2b/2c** best-targeted and label-verified: effect grows as measurement cleans up | done |
| ~23:40 | **Fade analysis** — opposite side also loses in all 6 configurations | done |
| ~23:50 | **P4** holdout, walk-forward (embargo bug found and fixed), day-clustered bootstrap, deflated Sharpe | done |
| ~00:00 | Retirement/walkover add-back: −0.004¢ | done |
| ~00:10 | **P3** run post-gate, explicitly labelled exploratory | done |
| ~00:25 | Ledger completed (90 hypotheses), BH on two-sided p | done |
| ~00:35 | `RESULTS.md` written | done |

---

# PHASE 5 — 2026-08-01

| Time | Unit | Status |
|---|---|---|
| ~09:10 | **Task 1a** — brief's premise checked: Phase 2 fade was **already** hold-to-settlement | done |
| ~09:20 | Cost anatomy: fee is 40% of the 3.636¢ bar, spread+slippage 60%. 1c/1d overlap 1b rather than stacking | done |
| ~09:35 | Phase 5 pre-registered before running anything further | done |
| ~09:45 | Ask OHLC missing from the Phase 0 pull; refetch launched | superseded |
| ~10:00 | **Task 3e validity check — FAILED.** Orientations disagree by 25.5 pp | done |
| ~10:15 | **Traced to a Phase 0 selection leak. Phase 2 retracted.** | done |
| ~10:25 | Dedupe fixed to lexicographic ticker; selection canary asserted in code | done |
| ~10:30 | Universe rebuilt; candle refetch relaunched on the corrected set with OHLC | running |
| ~10:50 | Task 1b maker model written, awaiting data | ready |

## RETRACTION — Phase 2 is void

The Phase 0 dedupe kept **the higher-volume side** of each mirrored pair. Volume
is read after settlement, Kalshi runs a separate order book per side, and
trading concentrates in the winning side. **The rule read the answer:** the
higher-volume side wins **53.56%** of the time (z = +10.0); open interest is
worse (55.58%, z = +15.8). Lexicographic ticker order is clean (49.69%, z = −0.88).

Because the analysis orients to the favourite, one selection error entered the
two halves with **opposite sign**: +14.05 pp where the favourite is the YES side,
−11.43 pp where it is the NO side. The pooled −2.53 pp "undershoot" is the
residual of two large opposite artifacts with unequal weights (1,198 vs 2,229),
and the weights themselves are set by the bias — conditioning on the favourite's
price falling makes the winner-biased side disproportionately the underdog.

The "effect strengthens as precision improves" argument in `RESULTS.md` was
wrong in the same way: deeper entry rules push the split further from 50/50 and
**amplify the artifact**. I read a growing bias as a cleaner signal.

Void: Phase 2 calibration, Phase 3 segments, Phase 4 holdout and walk-forward,
and the "no overshoot" verdict. Still standing: detector accuracy and t0 tuning
(validated against external scorelines, not outcomes), mirror equivalence, fee
arithmetic, synthetic controls, and the Phase 5 cost anatomy.

**New permanent canary**, asserted at universe build: `P(kept side wins)` must
be 0.50. The existing leak canary could not have caught this — it watches for
look-ahead *within* a match; this was selection *between* two markets.

## The answer (Phases 2–4, NOW RETRACTED — kept for the audit trail)

No overshoot. A **significant undershoot** instead: −1.1 pp on the pre-committed
rule, −2.5 pp best-targeted (p=0.0007), −5.5 pp on the label-verified subsample.
It replicates on a temporal holdout and strengthens as the state measurement gets
cleaner. It is **not tradeable** — mispricing ~2.5 pp against a ~3.6 pp round
trip, and the edge sits on the expensive side where fees peak. All six fade
configurations lose money.

## Four defects found in my own code

1. **Look-ahead in the changepoint** — statistic read 10 min past its candidate;
   argmax-over-window is not a stopping time. Fixed with assertions. *Before any
   real result.*
2. **Match start ~28 min early** — fixed with an activity-density floor, +28/MAD 24
   → +5/MAD 6. *Before any real result.*
3. **Walk-forward embargo 1000× too large** — parquet gives `datetime64[us]`, so an
   int64 cast is microseconds while `np.timedelta64(48,"h")` is nanoseconds; the
   embargo became 5.5 years and emptied every fold. *Found after Phase 2, fixed,
   re-run.*
4. **Wrong verdict criterion in the fade analysis** — tested the CI bound instead
   of mean expectancy. *Corrected before it reached the report.*

Plus: the tennis-data name key (surname-first format) silently contributed **zero**
rows to the first truth table. Fixing it added 723 matches and extended detector
validation into July.

## Leak canary, kept live

A deliberately leaky entry rule stays in the grid. It reports **+6.75 pp / +2.77¢**
on real data against −0.1 to −2.6 pp for all 28 honest rules. If a future run
shows honest rules resembling the canary, there is a leak.
