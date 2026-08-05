# RESULTS_H10.md — passive quoting, measured on real Kalshi L2

> # ⚠ CORRECTION, SAME SESSION — THE HEADLINE BELOW WAS UNSTABLE
>
> The first version of this file, committed at `5186158`, led with **"you set
> out to earn +1.50¢ and you get −1.50¢."** That was measured on 21 hourly
> files. Adding **7 more hours** moved it:
>
> | | 21 hours | 28 hours |
> |---|---|---|
> | JOIN net P&L per filled contract | **−1.50¢** | **+0.38¢** |
> | IMPROVE net P&L per filled contract | −1.65¢ | +0.48¢ |
> | raw adverse selection (JOIN) | −13.47pp, CI excluded zero | −8.52pp, **CI contains zero** |
> | **fill rate, strict (JOIN)** | **31.0%** | **31.1%** |
>
> **The sign of the headline flipped on a 33% increase in data.** The CI
> contained zero at both sample sizes, so nothing here was ever significant —
> but I led with the point estimate anyway, and the point estimate was noise.
>
> **What survived the change:** the fill rate, essentially unmoved at 31.0% →
> 31.1%. **What did not:** every P&L and adverse-selection number.
>
> The correct reading of this whole page is therefore: **passive quoting on
> Kalshi esports is indistinguishable from zero, the sign is not stable, and
> the mechanism is unconfirmed.** The tables below are kept as measured, with
> the sample size against each, because deleting them is how somebody
> re-derives them. **§4 is the part that holds.**

---

# 0. THE STABILITY CURVE — which of these numbers is a measurement at all

The sign flip above was found by accident. `src/h10_stability.py` then measured
it on purpose: re-run the whole simulation over **nested prefixes** of the same
corpus (6, 9, … 28 hourly files) and watch each statistic's trajectory. This is
the method that killed this repo's own stars-vs-substance false positive —
ρ went **+0.241 at n=105 to −0.007 at n=3,165**, decaying monotonically, which
is what a small-sample artifact looks like from the inside.

| statistic | range across prefixes | verdict |
|---|---|---|
| **fill rate, strict (JOIN)** | **30.8 – 31.2%**, last-3 drift **0.01** | ✅ **STABLE** |
| fill rate, permissive (JOIN / IMPROVE) | 55.5–62.3% / 39.8–46.4% | ✅ STABLE |
| **net P&L per filled contract (JOIN)** | **−1.71¢ … +1.34¢** | ❌ **SIGN-FLIPS — noise** |
| net P&L per filled contract (IMPROVE) | −3.09¢ … +0.93¢ | ❌ **SIGN-FLIPS — noise** |
| adverse selection (JOIN) | −13.29 → **−8.52pp**, monotone toward zero | ⚠️ decaying — artifact signature |
| adverse selection (IMPROVE) | −7.59 → **−5.41pp**, monotone toward zero | ⚠️ decaying — artifact signature |
| "monopoly regime" thin-far-side edge | +1.47 → **+6.70pp** (JOIN), +2.38 → **+13.32pp** (IMPROVE) | ⚠️ **strengthening — see below** |

### ⚠️ The one result that got better with more data is the one to distrust most

The thin-far-side edge is the only quantity that **strengthened monotonically**
as the sample grew, and at 28 hours IMPROVE reads **+10.25pp with a CI of
[+1.35, +19.92] that excludes zero.** It is the most exciting number produced in
this session.

**This repo pre-registered exactly that pattern as a warning sign.** GUARDS #10:

> *"Monotone strengthening is evidence of contamination until proven otherwise."*
> The archive's single worst inference was arguing an effect was real *because*
> it strengthened with detector precision — when precision and bias were the
> same knob.

So it is recorded as **a lead requiring a contamination check**, not as a
finding. The obvious candidate: "thin far side" is measured at placement, and
thin books are also the ones most likely to be stale or near settlement, so the
split may be selecting on something correlated with the outcome rather than on
competition. **Untested. Do not trade it.**

### What this section actually establishes

**One number from H10 is a measurement: the fill rate.** Everything about P&L
is noise at this sample size, and both directional mechanisms — adverse
selection and the monopoly regime — move with n in the directions that this
repo's own guards say mean "artifact".

**2026-08-05.** H10 was pre-registered on 2026-08-04 and left unrun because it
needs the order book, not candles. It became runnable when a sibling session
refuted the premise that Kalshi has no L2 history.

**Headline, and the two halves point opposite ways:**

- **Fill rate is not the constraint.** 31.0% by the strict trade-through
  measure, 62.3% by the permissive one. The pre-registered falsification
  (fill rate < 20%) is **not** met.
- **Net P&L per filled contract is −1.50¢, against the +1.50¢ half-spread the
  strategy exists to earn.** The entire price improvement is consumed.
- **But the null control does NOT confirm the mechanism at this sample size**,
  and it disagrees with the bootstrap CI. §4. That disagreement is the most
  transferable thing on this page.

---

## 1. What was built

| piece | file | note |
|---|---|---|
| range-request puller | `src/pull_l2.py` | reads only the 6 needed columns over HTTP `Range`; **72–76% of each file instead of 100%**, on a volunteer archive a sibling is already using |
| book replay | `src/replay.py` | snapshot + deltas → point-in-time book. `market-selection` called this *"the single biggest piece of unbuilt machinery"* |
| fill model | `src/h10_passive.py` | queue-aware, trade-through, no touch-counts-as-fill |

**Data:** 21 hourly files, 2026-05-30, **~6.9M L2 rows**, 112 esports markets,
microsecond timestamps.

### Two bugs the canaries caught, both mine

**B1 — the replay never re-synced.** v1 skipped a snapshot whenever the ticker
already had carried-forward state, to protect the ~62-of-99 tickers per hour
that have no snapshot. Effect: stale levels accumulated all day and the replay
ended with books like **bid 99 / ask 16 — crossed by 83¢**, which is impossible.
**The conservation canary passed throughout (0.047%)** because stale levels are
not negative levels. It took *looking at the output*. Fixed: a snapshot
replaces the book.

**B2 — a fill metric that measured nothing.** v1 tested "best bid < our price"
as trade-through for both modes and reported IMPROVE at a **99.6% lower bound
against a 45.8% upper bound** — bounds inverted, which is impossible and is what
gave it away. For an IMPROVE order the market's best bid is *by construction*
below our price and our own order is not in the replayed book, so the test fires
on every order. Trade-through is now applied to JOIN only.

### The crossed-book canary, and what it decided

Added after B1, because conservation alone could not see it:

| phase | observations | crossed (my price convention) | crossed (alternative) |
|---|---|---|---|
| **pre-event** | 626,443 | **5.60%** | 100.00% |
| post-event | 5,082,794 | **83.65%** | 99.93% |

Two things settled at once. **My price convention is right** — the alternative
reading (no-side prices already in YES space) crosses ~100% of the time and is
refuted. And **settled books are not maintained**, so crossing is a post-event
artifact. Everything below restricts to **pre-event** observations.

---

## 2. The result

5,581 simulated resting orders across ~55 events and 110 markets.

| | **JOIN** (rest at the touch, behind the queue) | **IMPROVE** (better the touch by 1¢, alone) |
|---|---|---|
| orders | 2,870 | 2,345 |
| fill rate, removal-based *(upper bound)* | **62.3%** | 45.8% |
| fill rate, trade-through *(lower bound)* | **31.0%** | n/a — see B2 |
| median minutes to fill | 39 | 45 |
| **net P&L per filled contract** | **−1.50¢** [−5.56, +2.78] | **−1.65¢** [−7.97, +4.45] |
| half-spread it was trying to earn | **+1.50¢** | +2.00¢ |
| adverse selection (filled − unfilled) | **−13.47pp** [−24.35, −0.07] | −8.09pp [−19.69, +5.73] |

> **The arithmetic of the whole maker question, in one line: you set out to earn
> +1.50¢ and you get −1.50¢.** The fee saving is real — Kalshi charges makers
> **nothing** on these series (`fee_type = quadratic`, verified, and C1a is the
> correction where two rigorous repos wrongly charged themselves) — and it is
> irrelevant, because selection takes more than the spread pays.

### The 31% is independently corroborated

The corpora were queried *before* this was run. An r/quant bot author diagnosing
his own too-good results: *"the reason my results are too good is likely the
100% fill rate; when it's 30% it will be way less."* A reply: *"the 30% fill
rate alone kills a huge chunk of that profit."*

**My strict measure lands at 31.0%.** Two independent routes, one number.

---

## 3. What this settles about the standing tension

| position | verdict |
|---|---|
| `signal-github`: maker-only quoting is *"the one strategy whose income is not required to overcome a fee first"* | **Correct on its own terms and irrelevant.** The maker fee here is literally zero. |
| youtube `rrKRhjye1sw`, 20-year professional: *"a resting offer is only taken when it is good for the taker… you are effectively being free-rolled"* | **Directionally supported, magnitude unconfirmed.** §4. |
| this repo's **S008/S009** (tennis): all 15 maker configurations net-negative, adverse selection exceeding price improvement at every window | **Independently reproduced on a different sport and venue segment** — and now with a number and a fill rate attached, which S008 never had. |

**The Paradigm challenge's mechanism claim, tested rather than assumed.**
r/quant `1ski9e8` (placed #2): *"the monopoly regime — when competitor quotes
vanish — accounted for 60% of total edge."* Proxying "competitor quotes vanish"
by thin depth on the far side at placement:

| | thin far side | thick far side |
|---|---|---|
| JOIN | **+3.91pp** [−3.31, +11.84] | −6.46pp [−16.53, +3.26] |
| IMPROVE | **+6.38pp** [−3.85, +18.53] | −8.41pp [−19.51, +2.44] |

**Direction supports it in both modes; the intervals overlap heavily.**
Suggestive, not settled — and it is the most promising thread here, because it
says maker income is not uniform but concentrated where competition is absent.

---

## 4. ⚠ THE NULL CONTROL DOES NOT CONFIRM IT, AND IT BEATS THE BOOTSTRAP

The standing rule is to validate on data with no effect and confirm none is
found. Here the effect is the *link* between getting filled and the outcome, so
the control permutes outcomes **across events**, destroying that link while
preserving the fill rate, the price distribution and the clustering. 400 draws.

| mode | observed | null mean | null sd | permutation p |
|---|---|---|---|---|
| JOIN | **−11.96pp** | **−2.22pp** | 7.30pp | **0.135** |
| IMPROVE | −6.26pp | −2.08pp | 5.84pp | 0.328 |

**Neither clears a 10% threshold.** And the bootstrap CI on JOIN said
[−24.35, −0.07] — excluding zero. **The two tests disagree, and the permutation
test is the one to believe**, for a reason the null itself exposes:

> **The estimator is biased by about −2pp under the null.** With outcomes fully
> shuffled, filled orders still look ~2pp worse than unfilled ones — because
> filled and unfilled orders have different price distributions, and
> `outcome − price` is not mean-zero across prices. A bootstrap CI centred on
> the raw difference inherits that bias and is **anti-conservative**. The
> permutation null absorbs it automatically, which is exactly why it is the
> right test.

**So the honest statement is:** passive quoting on Kalshi esports returned
**−1.50¢ per filled contract against a +1.50¢ target** on 1,787 fills, and the
adverse-selection mechanism is **directionally as predicted, large in point
estimate, and not statistically confirmed at 55 events.**

This is a one-day sample. The pull is extending it; **the result to trust is the
one after the null control is re-run on the full window**, and it is entirely
possible it stays unconfirmed.

---

## 5. Limitations, stated rather than discovered later

1. **Cancels are indistinguishable from trades in this feed.** Hence a band
   (31%–62%) rather than a number. Every P&L figure uses the permissive fill
   set, which **flatters** the strategy — and it still loses.
2. **The unfilled counterfactual is idealised.** A real quoter cancels and
   requotes; these orders rest up to 180 minutes. That biases *against* the
   strategy on time-to-fill and is neutral on selection.
3. **One day, 55 events.** The unit of observation is the event and every CI is
   clustered on it, but 55 is small and the permutation null says so.
4. **No inventory management.** The Paradigm entry found *"inventory skew
   removal = catastrophic — settlement risk dominates"*. This simulates single
   unhedged resting bids, which is the worst case and is deliberate: it is the
   naive strategy the fee argument recommends.
5. **Esports only, and one venue.** S008 found the same shape on Kalshi tennis;
   whether it holds on Polymarket, where makers are paid rebates, is untested.
