# The moment the $9.99 lands — what to run, in order

**Mailbox 008 asked for this**: write down exactly what happens the day the
purchase clears, so it becomes a result that day rather than a new project.

**The purchase:** `livetennisapi` history plan, **$9.99**, 43 monthly periods,
**January 2023 to July 2026, point-by-point, including ITF**. Named in
`bot-forensics/FINDINGS_T7.md` as "the single highest-value unlock". **It is a
payment, so only the user can make it.** Nobody in any session can enter card
details.

**One purchase, three answers** — S018, T002, B023.

---

## Before spending anything: 20 minutes that could save the $9.99

**Do these first.** Two of the three problems may already be partly solved for
free, and the third has a free substitute that was never checked.

| check | why | how |
|---|---|---|
| **Does the vendor still sell it, at that price, with ITF?** | The claim is from 2026-08-05 and this repo's own rule is that tool/price claims expire in 3–4 months. **A 404 or a price change makes the rest of this page moot.** | open the plan page and read it |
| **What does the free source already cover?** | `src/set1_labels.py` supplies **1,062 set-1 labels** for S006's window, free — but main tour only | `py -3 src/set1_labels.py` |
| **What is the actual ITF share of the universe?** | This decides whether the paid ITF data is the point or a rounding error. **Needs the laptop** — `set1_overshoot/data` is not on the desktop | count tiers in the universe file |

**If the ITF share is small, the $9.99 buys much less than it appears to**, and
the free source may be enough. That number does not exist yet and it is the one
that should decide the purchase.

---

## Then, in this order

### 1. Prove the file is what it says (30 min) — GUARDS #13

**Do not skip this and do not trust the row count.** `football-data.co.uk`
returned HTTP 200 and the *wrong file* — `COL.csv` was byte-identical to
`POL.csv`. A 200 is not a correct file.

- hash each period; assert no two are identical
- assert the date range of each file matches the period it claims
- assert the tier column actually contains ITF rows, and count them
- pick **five matches at random** and check them against a second source by hand

**Stop here if any of those fail.** Everything below inherits the answer.

### 2. S018 — label coverage (1 hour)

Join the new point-by-point to the set-1 universe on (date, both surnames), the
same key `src/set1_labels.py` already emits.

**Report the join RATE, not the row count.** The number that matters is
*labelled events as a share of the 3,436-event universe*, currently 13.9%.

Then recompute S006's minimum detectable effect at the new n. **The pre-computed
target is ~3,620 label-verified matches to see 3.6c.** Below that, the honest
verdict stays "this test cannot see it".

### 3. T002 / B023 — re-power the player features (half a day)

Features currently stop **2026-06-02** with 85% of markets after that. With
history to July 2026 the window closes.

**Re-run the Stage 0–5 pipeline and the 2,008-combination sweep** — but keep the
existing guards: the selection canary at build time, the within-match leak
canary, and one BH denominator over the whole sweep. **B023's own project says
its null should read "not demonstrated on 29 days of form data"**, so the
re-run's job is to replace that sentence with a measured one, in either
direction.

### 4. Say what did not change

Whatever the answer, write the row status back to `LEDGER.md` with the new n and
the new minimum detectable effect beside it. **A re-run that leaves a row saying
"SETTLED (null)" when it means "still cannot see it" is the exact defect the
reopen audit was created to find.**

---

## What this purchase does NOT fix

- **S022 / S023** — the fade-side re-run. Blocked on `set1_overshoot/data`,
  which is **laptop-only and gitignored**. New history does not help; it needs
  someone at that machine.
- **The cost bar.** Measured forward at **4.79c** on this project's pool
  (2.67 fees + 2.12 spread, n=81) against the 3.61c those closures assume. More
  data makes an effect sharper. It never makes it bigger than the cost of
  reaching it — which is the reason S021 was withdrawn, and it applies here too.
- **CH074** — already measured without it, see below.

---

## CH074 is done and did not need the $9.99 (2026-08-10)

`src/ch074_decomposition.py`. **53 player-sides across 27 live matchups.**

Buying a player through the exact-score legs instead of the match market costs
**4.0c more gross, 5.7c more net** at the median. **1 of 53 was cheaper net, by
0.38c** — inside the noise and far inside the 4.79c round trip.

**The closure's conclusion holds. It is now a measurement rather than an
argument from one worked example**, which is what CH074 asked for.
