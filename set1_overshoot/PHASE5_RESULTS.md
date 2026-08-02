# PHASE 5 RESULTS

Status: **halted at Task 3e, pipeline rebuilding.** Two premises failed, one of
them mine and serious. Written 2026-08-01.

---

## 0. RETRACTION — the Phase 2 headline is void pending re-run

**The −2.53 pp undershoot reported in `RESULTS.md` is not a market property. It
is an artifact of how I chose which of two mirrored markets to keep, in Phase 0.
Do not act on any Phase 2 number until the re-run lands.**

### How it surfaced

Task 3e was a validity check, not a hypothesis: the same undershoot must appear
whether the favourite happens to be the YES side or the NO side of the market I
kept. It did not.

| side | n | implied | observed | miscalibration | 95% CI |
|---|---|---|---|---|---|
| favourite is the **YES** side | 1,198 | 0.3445 | 0.4850 | **+14.05 pp** | [+11.36, +16.80] |
| favourite is the **NO** side | 2,229 | 0.3750 | 0.2607 | **−11.43 pp** | [−13.15, −9.69] |
| pooled (the Phase 2 headline) | 3,427 | 0.3643 | 0.3391 | −2.53 pp | [−4.05, −1.00] |

**Difference: 25.49 pp, 95% CI [+22.31, +28.73].** Two halves that must agree,
disagreeing by twenty-five points.

The literal both-sides check — the same match priced from its two sibling
markets — showed no such gap (median entry-mid difference 0.00¢, outcome
agreement 1.0000, −0.59 vs −1.66 pp on 74 paired firings). So the price
arithmetic was fine. The problem was **which matches ended up in which half**.

### Tracing it upstream

Checking the **pre-match** price, which should be well calibrated and orientation-
free:

| orientation | n | implied | observed | miscalibration |
|---|---|---|---|---|
| favourite is YES side | 4,013 | 0.7213 | 0.8084 | **+8.70 pp** |
| favourite is NO side | 8,344 | 0.7920 | 0.7553 | **−3.67 pp** |

A pre-match market cannot be 8.7 pp wrong in a subgroup. This was selection, not
pricing, and it was present before a single in-play price was read.

### The cause

Phase 0 deduped mirrored markets by **keeping the higher-volume side**. Volume is
read from the API *after* settlement, Kalshi runs a **separate order book per
side**, and trading concentrates in the side that is winning. So the rule reads
the answer.

| dedupe rule | P(kept side wins) | z |
|---|---|---|
| **higher volume — the Phase 0 rule** | **0.5356** | **+10.04** |
| higher open interest | 0.5558 | +15.80 |
| first ticker alphabetically — **the fix** | 0.4969 | −0.88 |
| last ticker alphabetically | 0.5031 | +0.88 |
| hash-of-ticker parity | 0.4983 | −0.47 |

The winning side holds a mean **52.5%** of the event's total volume and is the
busier book in 53.6% of events.

### Why a 3.6 pp selection bias became a 25 pp split

The analysis orients every match to the favourite, so it splits on whether the
kept — that is, the winner-biased — player *is* the favourite:

- When the kept player is the favourite, the bias inflates the favourite's
  apparent win rate. → **+14.05 pp**
- When the kept player is the underdog, the identical bias deflates it.
  → **−11.43 pp**

Worse, the two halves are not equally sized in the event sample (1,198 vs
2,229). Conditioning on the favourite's price *falling* selects matches where
the favourite is likely losing, so the winner-biased kept side is
disproportionately the *underdog* — 65% of events, not 50%. **The pooled −2.53 pp
is the residual of two large opposite artifacts with unequal weights.** It is not
a measurement of anything.

### What this does and does not touch

| result | status |
|---|---|
| Phase 2 undershoot, −1.13 / −2.53 / −5.49 pp | **VOID** — must be re-measured |
| Phase 2 "no overshoot" verdict | **Unresolved.** The direction was set by the artifact; the true sign is unknown until the re-run |
| Phase 3 segments, Phase 4 holdout/walk-forward | **VOID** — all built on the same events |
| Phase 5 Task 1a cost anatomy | **Stands** — cost arithmetic does not depend on which side was kept |
| Detector accuracy (0.825), t0 tuning (+5 min) | **Stands** — validated against external scorelines, not against outcomes |
| Mirror equivalence, fee arithmetic, leak canary | **Stand** |

The honest read on the "monotonic strengthening with precision" argument I made
in `RESULTS.md` §2: deeper entry rules select harder on the favourite falling,
which pushes the kept-side/favourite split further from 50/50, which *amplifies
the artifact*. What I read as the effect getting cleaner was the bias getting
stronger. That is exactly the reasoning error this project keeps making, and I
made it.

### Fix and status

- Dedupe replaced with lexicographic ticker order, verified outcome-neutral.
- Universe rebuilt: 19,782 matches, unchanged in count, ~50% different in which
  side is kept.
- Candles refetching with **full ask OHLC** (needed anyway for Task 1b).
- Entire pipeline — Phases 1 through 5 — to be re-run on the corrected universe.

---

## 1. Task 1a — the brief's premise is also false

**The Phase 2 fade was already hold-to-settlement, one fee.** From
`src/p2_fade.py`: `net = 100*dog_won - fill - fee`, a single fee on the entry
fill, no exit leg, no target, no stop. The −1.10¢ already banks the entire
hold-to-settlement saving. The round-trip figures the brief has in mind are the
Phase 3 *exit surface*, which was a separate experiment on the favourite side.

So **Task 1a offers zero further improvement**, and forcing a round trip changes
net by +0.000¢ (a settled position exits at 0 or 100, where the fee formula
bottoms out).

### Anatomy of the cost bar — this reorders the phase

| component | ¢/contract | share |
|---|---|---|
| half-spread crossed | 1.197 | 33% |
| assumed slippage | 1.000 | 28% |
| taker fee | 1.439 | 40% |
| **total above fair value** | **3.636** | |

The brief treats 1a–1d as four independent reductions that "stack
multiplicatively". They do not:

| lever | ceiling ¢ | why |
|---|---|---|
| 1a hold to settlement | **0.000** | already banked |
| 1b maker | **3.636** | attacks all three components |
| 1c price geometry | ≤1.439 | only reallocates *within* the fee 1b already cuts |
| 1d spread filter | ≤1.197 | only reallocates *within* the spread 1b already avoids |

1c and 1d overlap 1b rather than stacking with it; multiplying the four would
double-count. The 1e stack will be computed as **one joint simulation**, never
as a product of separate savings.

**1b is the whole phase** — it is the only lever whose ceiling exceeds the gap.

### Distribution and drawdown (pre-correction figures, for method not for truth)

n = 3,427, mean −1.101¢, sd 45.1¢; wins 66.1% averaging +29.8¢, loses 33.9%
averaging −61.4¢. Worst peak-to-trough at 1 contract/match: **4,792¢ realised**,
median 5,029¢ over 200 shuffles, 95th pct 6,508¢. Hold-to-settlement has no
stop, so this is the honest companion to any expectancy figure.

*(These numbers are computed on the contaminated event set and will be
regenerated; the cost decomposition above is unaffected because it is
arithmetic on quoted prices.)*

---

## 2–9. Pending the re-run

Tasks 1b (maker and adverse selection), 1c, 1d, 1e, 2a, 2b, 2c, 3a–3d are
blocked on the corrected candle pull. Task 3e is complete and is the reason
everything else is blocked.

**Cumulative hypothesis ledger** stands at 90 entries from Phases 2–4, all of
which are void and will be re-run rather than carried forward. Phase 5 entries
will be added to a rebuilt ledger with BH across the cumulative total.

**Leak canary**: last honest reading +6.75 pp for the deliberately leaky rule
against −0.1 to −2.6 pp for honest rules. Note that the canary did **not** catch
this leak — it watches for *temporal* look-ahead within a match, and this was
*cross-sectional* selection between two markets. A second canary is warranted:
**P(kept side wins) must be 0.50**, asserted in code at universe-build time.
