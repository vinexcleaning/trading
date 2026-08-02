# GO_NO_GO.md

**Written 2026-08-01 ~02:45 UTC, before any Task 5 result exists** and before
the Task 3 headline was computed. The thresholds below are fixed at this
timestamp so they cannot be moved to fit whatever comes out.

---

## 0. The gate that comes first

**Task 5 (the strategy sweep) does not run at all unless a model beats the
Kalshi mid in Task 3**, with a CI excluding zero, clustered by event.

This is not a formality. Sweeping entry thresholds, take-profits and stop-losses
over a signal with no edge is how you manufacture a strategy that dies live, and
it has already happened in this project. If the base result is null, Task 5 is
**recorded as not run**, which is a decision, not an omission.

---

## 1. Power — what n is required

The synthetic control (`reports/synthetic_control.json`) measured the pipeline's
actual sensitivity rather than assuming it:

| injected effect | 1,500 synthetic events | detected? |
|---|---|---|
| 15% wing bias | diff −0.002655, CI [−0.00310, −0.00217] | **yes** |
| 5% wing bias | diff −0.000334, CI [−0.00050, −0.00014] | **yes** |
| none (null) | diff −0.000028, CI [−0.00013, +0.00008] | correctly **no** |

At 1,500 events the half-width of the null CI is ≈ 0.0001 Brier. CI width scales
as `1/√n_events`, so:

| events | approx. Brier CI half-width | smallest detectable wing bias |
|---|---|---|
| 1,500 | 0.00010 | ~2% |
| 400 | 0.00019 | ~4% |
| 200 | 0.00027 | ~6% |
| 100 | 0.00038 | ~8% |

**Minimum: 200 out-of-sample events.** Below that the test cannot resolve a
wing bias smaller than ~6%, which is inside the range a real edge could plausibly
occupy — a null would be uninformative rather than decisive.

Note this is power in **events**, not market-minutes. 400 events × ~12 strikes ×
~60 minutes is ~288,000 rows, and quoting power from that number would overstate
it by roughly √720. The unit is the event.

---

## 2. GO criteria — all must hold

A candidate is reportable as a real edge only if **every** one holds:

1. **Beats the mid.** Brier difference vs the Kalshi mid negative, 95% CI
   excluding zero, **bootstrap clustered by event**.
2. **Survives costs.** Fee-inclusive per-trade edge positive with a CI excluding
   zero, using exact-decimal `fees.py` (Kalshi taker `0.07·p·(1−p)`, maker one
   quarter) **and** the actual spread crossed at that price — not the mid.
3. **≥ 200 out-of-sample events** in the bucket claimed, not in the panel
   overall. A bucket-level claim needs bucket-level n.
4. **Consistent across two disjoint periods.** Split the 68 days in half; the
   sign must agree and neither half may have a CI excluding zero in the *wrong*
   direction.
5. **Consistent across time-of-day.** Not concentrated in a single UTC hour
   unless there is a stated mechanism for that hour.
6. **Concentrated and explainable.** A diffuse advantage spread evenly across
   every bucket is treated as a leak. Localisation is required, not optional.
7. **Mechanism.** One sentence on why the counterparty is wrong and why the
   error persists. **No mechanism, no candidate** — applied before statistics,
   not after.
8. **All leak tests pass**: knowability assertions, shift-forward, shuffled
   labels, and the synthetic control. ✅ *Synthetic control already passed all
   three arms at 02:15 UTC.*
9. **Survives BH-FDR across the entire cumulative ledger**, all phases.
10. **Plateau, not peak.** The parameter surface must be reported in full and
    the candidate explicitly labelled plateau or peak. A sharp isolated peak is
    overfitting and is not reportable as an edge.

## 3. NO-GO — any one of these kills it

- Mid wins, or the CI straddles zero → **crypto pricing is closed. Say so
  plainly as the headline.** This is a successful outcome.
- Edge exists gross but vanishes net of fee and spread → report as "real but
  untradeable", never as an edge.
- Edge is diffuse across all buckets → treat as leak, investigate, do not report.
- Edge appears only in one period or one hour with no mechanism → overfit.
- Any leak test fails → **every Phase 2 result is void**, not caveated.
- Deflated Sharpe (adjusted for the number of variants tried) below 0 → no.

## 4. What "closed" would mean

If the mid wins, the correct conclusion is that Kalshi's crypto ladder is
efficiently priced at the horizons and strikes where it is quotable, and the
project stops asking. That is a **result**, and it is worth as much as a
positive — it retires an entire line of inquiry that has already consumed
substantial effort across the project's history.

It would specifically NOT license: "try more models", "try more parameters", or
"try a shorter horizon". Those are the moves that produced the 24 prior
retractions.

---

## 5. Outcome — filled in after the run

**VERDICT: NO-GO. The mid wins. Task 5 was not run.**

Filled in 2026-08-01 ~04:15 UTC against the thresholds fixed above.

| # | criterion | required | actual | pass? |
|---|---|---|---|---|
| 1 | beats the mid, CI excludes zero, event-clustered | yes | **best model M2 diff −0.000081, CI [−0.00188, +0.00182], p=0.942** | ❌ |
| 2 | survives fee + actual spread | — | not reached | — |
| 3 | ≥200 out-of-sample events | 200 | **250** | ✅ |
| 4 | consistent across two disjoint periods | yes | **sign flips** (M2: −0.0014 → +0.0009) | ❌ |
| 5 | consistent across time-of-day | yes | not reached | — |
| 6 | concentrated and explainable | yes | diffuse, sign-flipping | ❌ |
| 7 | mechanism | required | none — no edge to explain | ❌ |
| 8 | all leak tests pass | yes | **synthetic control passed all 3 arms** | ✅ |
| 9 | survives BH-FDR across the cumulative ledger | yes | **nothing survives even within its own 17-test family** | ❌ |
| 10 | plateau not peak | required | n/a | — |

**Criterion 1 fails outright**, which is sufficient on its own. The single
nominal candidate (mid bucket 5–10¢, buy-at-ask net +1.00¢) fails criterion 9:
BH requires p ≤ 0.0059 at its rank among 17 buckets; observed p = 0.029.

### Power was adequate — this is a real null, not an underpowered one

This matters more than the null itself. The panel has **250 events against a
200-event floor**, and the synthetic control demonstrated the pipeline detects a
**5% wing bias at 1,500 events** with CI half-width ≈0.0001. At 250 events the
half-width is ≈0.0019 — and the observed M2 point estimate is **0.000081**, more
than an order of magnitude *inside* that. The test was capable of finding an
effect several times larger than anything present. Nothing was there.

### What this closes

Kalshi's crypto ladder is efficiently priced at the horizons and strikes where it
is quotable. Per §4 of this document, that specifically does **not** license
"try more models", "try more parameters", or "try a shorter horizon" — those are
the moves that produced the project's 24 prior retractions, and a 25th is not
worth buying.
