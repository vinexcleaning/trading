# PREREGISTRATION — PART B (the clean re-run)

Written **2026-08-01, before any number from the corrected universe existed.**
At the time of writing the candle refetch was at 10,500 of 19,782 markets and
`paths_state.parquet` was still the contaminated build. Nothing below was
informed by a clean calibration figure.

This document exists for one reason. In Phase 2 I argued the effect was real
because *it strengthened as detector precision improved*. That was the bias
getting stronger, and I rationalised it into evidence after the fact. Writing
the expectation down first is the only defence against doing it again.

---

## 1. What I expect, and why

**The sign is unknown. I am not neutral about it, and here is my actual prior
with its derivation, so it can be scored.**

The contaminated result decomposes cleanly. Let θ be the true miscalibration and
b the per-orientation bias:

| half | n | measured | model |
|---|---|---|---|
| favourite is YES side | 1,198 | +14.05 pp | θ + b |
| favourite is NO side | 2,229 | −11.43 pp | θ − b |

Solving on the assumption that b is symmetric:

> **θ ≈ (+14.05 − 11.43) / 2 = +1.31 pp**, b ≈ 12.74 pp

**So my point prediction is a small OVERSHOOT of roughly +1.3 pp**, not the
−2.53 pp undershoot I reported. The original hypothesis — that the market
overshoots the set-1 dip — is live again and is now the *more* likely of the
two, though barely.

The assumption of symmetric b is the weak link: the two halves have different
sample sizes and different pre-match price distributions (implied 0.3445 vs
0.3750), so b need not be equal. I therefore hold this loosely.

**Pre-registered interval: I expect θ in [−1, +3] pp.**

| outcome | how surprised | what I would conclude |
|---|---|---|
| θ in [−1, +3] pp | not at all | consistent with the bias decomposition; the honest answer is then whether it clears cost, which at ~3.6 ¢ it almost certainly does not |
| θ in [+3, +5] pp | mildly | real overshoot, worth Task 2/3; still check cost |
| θ in [−3, −1] pp | mildly | the undershoot partly survives; b was asymmetric |
| **\|θ\| > 5 pp either way** | **very** | **suspect a remaining bug before believing it.** No plausible market inefficiency of that size survives in a market that tracks Betfair at r = 0.9878 |
| θ ≈ −2.5 pp, i.e. the old answer returns | **very** | would mean the dedupe fix changed nothing, which contradicts a z = +10 selection bias. Treat as evidence the fix did not take |

## 2. The mirrored-consistency gate — run first, before any calibration number

The two orientations are different matches, so they may differ by sampling
noise. With n ≈ 1,200 and n ≈ 2,200 and a per-match sd of ~50 pp:

- SE(YES half) ≈ 1.44 pp, SE(NO half) ≈ 1.07 pp
- **SE(difference) ≈ 1.79 pp**

**Gate, fixed now:**

| condition | action |
|---|---|
| \|z\| of the orientation difference < 4 (≈ \|diff\| < 7 pp) | proceed |
| \|z\| ≥ 4 | **STOP. Debug. Do not pool, do not report a calibration number.** |

I am also pre-registering the *secondary* gate that would have caught this in
Phase 0 and did not exist then:

| condition | action |
|---|---|
| pre-match calibration, either orientation, \|residual\| > 1.5 pp | stop — a pre-match market that tracks Betfair at r=0.9878 cannot be that wrong in a subgroup |

The contaminated build read **+8.70 pp / −3.67 pp** on that second gate. Clean
should read within ±1.5 pp on both.

## 3. What would make me suspect a remaining bug rather than a real effect

Listed now so none of them can be explained away later:

1. Orientation gap fails the gate in §2.
2. Pre-match calibration off by more than 1.5 pp in either orientation.
3. **The effect strengthens monotonically as entry-rule precision increases.**
   In Phase 2 I called this the strongest evidence in the study. It is now a
   **warning sign**: deeper rules push the kept/favourite split further from
   50/50, so monotone strengthening is the *signature of a residual selection
   bias*, not of signal. If I see it again I look for the bias first.
4. Any honest entry rule approaching the leak canary's +6.75 pp.
5. \|θ\| > 5 pp.
6. The effect concentrated in one tour, one fortnight, or one tournament.
7. The `spread>15c exposure` filter still failing the strengthened guard at
   \|z\| > 4 on clean data. On the contaminated build it read **z = −6.28**.
   **Pre-registered prediction: if that was the dedupe artifact leaking through
   a liquidity-correlated channel, it should shrink to \|z\| < 3 on clean data.
   If it does not shrink, it is a real composition effect and the sample is
   tilted by liquidity independently of the dedupe bug.**

## 4. Directional priors from earlier phases — all measured on the biased universe

All of these are void as evidence and are re-tested from scratch. Recording what
they said so the re-run cannot be quietly matched to them:

| prior | what the biased run said | status |
|---|---|---|
| user: trade works at 70–80¢, fails near 51¢ | 70–80 = −1.85, 60–70 = −1.89, indistinguishable | **untested** |
| user: men's tennis more predictable | ATP −4.61, ITF-M −0.61, WTA −1.55, ITF-W −1.37, no consistent direction | **untested** |
| 90¢+ favourites | +7.93 train → +0.04 holdout | **untested** |
| larger dip → larger effect | 20–30¢ = −3.54, 30¢+ = +0.91, non-monotone | **untested** |

## 5. Analysis plan, fixed

1. Rebuild state from `candles_ohlc` on the corrected universe.
2. Re-run the pipeline-filter guard table on the **clean** universe; report
   every rule that moves relative to the contaminated baseline.
3. **3e mirrored-consistency gate.** Pass or stop.
4. Only then read the Phase 2 calibration table.
5. Phase 4 validation (holdout, purged walk-forward, day-clustered bootstrap).
6. Task 1b maker/adverse-selection, which does not depend on the sign of θ —
   it is a cost question and runs either way.
7. Task 2/3 only if §1's gate on cost is cleared, which requires θ to exceed
   the ~3.6 ¢ round trip.

Ledger: Phases 2–4 (90 entries) are void and are **not** carried forward as
tested hypotheses; the ledger restarts and the Phase 5 entries accumulate into
it, with BH across the new cumulative total. The count of *void* prior tests is
reported separately so the history is not hidden.

## 5c. AMENDMENT — time-of-day and tier segmentation (added 2026-08-01 08:30)

Written **before running any bucket**. θ, the pooled fade net (−1.195 ¢) and the
pooled maker net (−0.205 ¢) were known; no bucketed number was.

### Why the Phase 3 gate lifts here

The gate exists to stop slicing a **null** into subgroups until one looks
positive. θ is not null: −2.42 pp, p = 0.0009, replicating on holdout. The
question "is the effect uniform or concentrated?" is a real hypothesis with a
real mechanism — spreads and depth demonstrably vary by tier (ATP median 30 lots
at 3 ¢; Challenger 1,822 lots at 1 ¢) — and a concentrated effect could clear a
bar that the pooled effect does not. Gate lifted **for this test only**.

### The methodological requirement that makes it honest

**The cost bar is computed per bucket, never pooled.** Three adjacent columns
for every cell, which form an exact identity:

- `effect pp` = 100 × (observed − implied) — how mispriced the bucket is
- `bar pp` = 100 × (breakeven − implied) — what execution costs there
- `net ¢` = effect − bar — and this *equals* net ¢/contract exactly

A bucket where the effect grows but the bar grows faster is a loss. A pooled bar
would hide exactly that, and it is the failure mode most likely to produce a
false positive here.

### Power, computed in advance — this bounds what the exercise can show

Per-contract sd of net P&L is ≈ 45 ¢. To detect a **+2 ¢** edge at 80% power,
two-sided 5%:

> n ≥ (2.80 × 45 / 2)² ≈ **3,970 matches**

**The entire event sample is 3,436.** So **no bucket can be individually powered
to demonstrate a 2 ¢ edge** — the whole sample is not powered for it. Stated
consequences, fixed now:

1. Any bucket appearing to clear will be doing so on a sample too small to
   support it, **unless the effect is very large** (a +6 ¢ edge needs n ≈ 440).
2. Every bucket reports its own MDE. Buckets that cannot resolve the effect they
   appear to show are marked **UNTESTABLE**, not reported as results.
3. **A concentrated effect on a small subsample is the shape of an artifact.**
   If that is what it looks like, that is what I will call it.

### Buckets, fixed now

| # | Factor | Levels |
|---|---|---|
| T1 | Entry hour, **UTC**, 4-hour blocks | 00–04, 04–08, 08–12, 12–16, 16–20, 20–24 |
| T2 | Entry hour, **US/Eastern** (EDT = UTC−4), 4-hour blocks | same six |
| T3 | Tier | ATP, WTA, CHALL, ITF-M, ITF-W |
| T4 | Hour × tier | only cells with n ≥ 150 |

Entry time is the **entry minute**, not match start — that is when a trade would
be placed.

### The user's live observation, tested as four competing explanations

Reported profit overnight, losses once the main tournaments started. Candidates:

- **(a) effect size** varies by hour
- **(b) cost bar** varies by hour
- **(c) tier composition** varies by hour (ITF overnight, ATP/WTA in the day)
- **(d) none of the above** — the observation is noise

The tier mix per hour block is reported alongside, which discriminates (c)
directly. I hold no prior between them.

### Guards

Every bucket into the ledger; BH-FDR across the cumulative ledger; the
**expected-by-chance count** reported next to the results; two-period split on
anything that clears; and the holdout gate that killed the 90 ¢ cell applies
unchanged.

## 6. Cost reality, restated so a positive θ is not over-read

Even a clean +3 pp overshoot is not a strategy. The cost bar measured in Task 1a
is **3.636 ¢** as a taker (half-spread 1.197, slippage 1.000, fee 1.439). A
3 pp edge on a contract is 3 ¢. **θ must exceed ~3.6 pp before a taker breaks
even**, and the maker line in Task 1b is the only thing that moves that bar.
