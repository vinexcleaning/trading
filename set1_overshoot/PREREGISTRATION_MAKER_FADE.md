# PREREGISTRATION — the deep-fade entered as a MAKER, not a taker

**Written 2026-08-20, before any result exists.** The data pull was running
while this was written; **no entry rule, no fill rule and no cut below has been
evaluated against any outcome.** What had already been looked at is declared in
§8, because a pre-registration that hides a prior look is worthless.

Origin: mailbox `tennis/017`. Prior work: `RESULTS.md`, `LEDGER.md` S008, S009,
S010, S025; `crypto/MM_RESULTS_MAKER.md`.

---

## 1. The question, in one sentence

The fade is **+2.42¢ before costs and −1.10¢ after them.** The entire gap is the
cost of crossing the spread and paying a taker fee. **So: if the same trade is
entered as a resting order instead of a market order, does the surviving edge
clear zero?**

**Restated without jargon:** the bet already wins about two and a half cents per
contract on paper. Paying to jump the queue costs three and a half. **The
question is whether waiting in the queue instead of jumping it turns a loser into
a winner — and whether you get served at all while you wait.**

## 2. Hypothesis, pre-committed

> **H-MAKER.** For the pre-existing entry rule `deep:30@38`, entering by a
> resting bid rather than at the ask produces a **positive net result per match
> after fees, after a fill model built from the observed trade tape, and after
> the trades that never filled are counted as no-trades rather than dropped.**

**`deep:30@38` is not chosen here.** It was the best-targeted arm of a grid run
before this document existed (`RESULTS.md`). Choosing it now is deliberate reuse
of a prior selection, and it means **the selection window is contaminated for
this test too** — which is what §5's holdout exists to handle.

## 3. Unit of observation

**One match.** Not one fill, not one contract, not one market.

A match is two mirrored markets and can produce hundreds of fills; those fills
share one outcome and are one observation. The repo's recorded failure is
exactly this — *"490,464 fills from 762 matches are 762 observations"*.
Confidence intervals are clustered on the match.

**Effective sample size is reported alongside nominal**, because fills within a
match are near-perfectly correlated.

## 4. Sample and date range

| | |
|---|---|
| series | `KXATPMATCH`, `KXWTAMATCH`, `KXATPCHALLENGERMATCH`, `KXWTACHALLENGERMATCH`, `KXITFMATCH`, `KXITFWMATCH` |
| markets | every **settled** market in the window: **35,994 markets = 17,997 matches**, measured, exactly 2 markets per match with no exceptions |
| price path | 1-minute candles, `yes_bid` and `yes_ask` separately |
| trades | full per-market history with the aggressor field |
| window | **2026-06-14 → 2026-08-20** |

**2026-06-14 is a hard floor, not a choice.** Probed across seven dates: 06-12 returns nothing, 06-14 returns markets. **A second and independent source agrees** — `CLAUDE.md` §8 records Kalshi's API as a ~69-day window with closed markets 404ing permanently, which puts the boundary at almost exactly this date. Two sources, not one. The original study ran 2026-05-25 → 08-01, so
**its first twenty days are permanently unavailable** and no result here can
speak to them.

## 5. The holdout, and why it is a date split

| | |
|---|---|
| **selection set — may be looked at freely** | **2026-06-14 → 2026-08-01** — **13,865 matches** |
| **untouched check period — not opened until the rule is frozen** | **2026-08-02 → 2026-08-20** — **4,132 matches** |

**The split is by date and it is not arbitrary.** The original study's window
*ended 2026-08-01*. Everything after that date is data the fade rule has never
been fitted to, by anyone, at any point. That makes it the only genuinely clean
ground available, and it is 19 days and 4,132 matches.

**A random split would have been wrong here** — the rule was already selected on
the earlier period, so randomly mixing those days into a "holdout" would leak
the original selection straight into it.

**Rules for the holdout, binding:**

- It is not queried, plotted, counted or described until §6's arms are frozen in
  a commit.
- **One evaluation. No second pass.** If the holdout is looked at and the rule is
  then changed, the holdout is spent and must be declared spent.
- Its size is stated up front and it is **not** a token slice: **4,132 matches**
  against 13,865 in the selection set, a 23/77 split. For comparison the
  study's entire headline rested on 3,436 events. It is still smaller than the
  selection set, so **failing to confirm is not the same as refuting** — but it
  is large enough to kill a real effect rather than merely fail to see one.

## 6. The arms, fixed now — three, and nothing added later

| arm | universe | maker fee |
|---|---|---|
| **M1 (primary)** | all six series pooled | per series, from the API |
| **M2** | ITF and Challenger only | **zero** |
| **M3** | ATP and WTA main tour only | charged |

M2 and M3 are split because they are **structurally different markets**, not
because a split looked promising: one charges makers nothing and has many small
fills, the other charges them and holds most of the contract volume (S025).

**Multiple-testing correction.** These three join the single repo-wide
Benjamini–Hochberg denominator, taking it from **33 to 36**. Not a separate
family, not its own correction.

### The depth grid is LOOKED at, including `deep:40`, and gets no verdict

**A Critic pass on this document caught a real fault in it.** Fixing the depth
at `deep:30@38` and registering nothing else would have silently discarded
`deep:40` — which is the user's actual suggestion, the thing that started this.
**That is precisely the narrowing failure §9c step 7 exists to prevent:** the
recorded case in this repo is a sweep over price features being used to close
down a question about individual players, which it never tested.

The resolution is the one §9c already gives — **slicing is fine for LOOKING, not
for CONCLUDING:**

- **The whole depth grid, `deep:8` through `deep:40`, is run on the selection
  set and reported in full**, as a picture, with `deep:40` called out by name
  because it was asked for.
- **None of it gets a verdict.** No p-value, no place in the correction, no
  entry in `LEDGER.md`. It is a chart, and it is labelled a chart.
- **If a depth other than 30 looks better, that does not promote it.** It goes
  in the "not tested" list as a candidate for a future pre-registration on data
  nobody has looked at yet. Promoting it here would be fitting the rule to the
  same data twice, which is how every one of the retractions started.

### The naive benchmark, reported beside every maker number

**The benchmark is the taker version of the same trade on the same matches:
−1.10¢ per contract for `deep:30@38`.** A maker result is meaningless without
it — "the maker version made 0.4¢" only means something next to "and the taker
version lost 1.10¢ on the identical signal."

**Second benchmark, and it is the harsher one: doing nothing.** A strategy that
fills on 1 match in 10 and nets a fraction of a cent is competing against
leaving the money alone, and the report says so in money rather than in cents
per contract.

## 7. The fill model — the part most likely to be faked

**The crypto maker work names this as the single easiest thing to fake, so every
choice below is pre-committed and every one is deliberately pessimistic.**

1. **A resting YES bid at price P fills only when a real trade printed against
   it** — a trade whose aggressor was selling, at a price at or below P. No
   trade, no fill. No modelled fill, ever.
2. **We are last in the queue.** Fill is credited only after the size already
   showing at that level has been consumed by that minute's trading. Queue
   position is unobservable, so it is assumed to be the worst case.
3. **Fill size is capped by the real traded size.** No partial-fill optimism.
4. **Unfilled entries are recorded as no-trades and stay in the denominator per
   match.** A maker strategy that only counts the matches it got into is the
   classic maker backtest lie.
5. **Latency: one whole minute-bar.** A signal at minute *t* can only rest an
   order from minute *t+1*, matching the forward test's existing convention.
6. **Exit is taker unless separately stated.** Assuming a maker exit as well
   would double an unproven advantage.
7. **Block trades are excluded.** A negotiated block is not a fill any resting
   order could have won.
8. **Fees from `common/kalshi_fees.py` only**, with the per-series schedule read
   from the API and stored beside the prices. Guard #6 forbids a second
   implementation.

## 8. ⚠ What had ALREADY been looked at before this was written

Declared because concealing it would invalidate everything above.

- The **grid results** `deep:8` … `deep:30@38`, gross and net, from the original
  study. That is why `deep:30@38` is the arm.
- The **aggressor split** on 2026-07-30 and on six ATP markets: **75.6% of
  trades are takers buying**, so the resting order that fills is usually an
  **ask**, and the fade needs a resting **bid** — the 24.4% side.
- The **fee schedule** per series.
- **No outcome, return, or win rate has been computed under any maker fill
  model.** That is the thing this document is registered against.

## 9. The placebos — required before any result is believed

Run alongside, and **a failure in either voids the run**:

- **P1 — shuffle the aggressor.** Randomly reassign which side was the taker,
  keeping prices and times. **A real fill advantage must collapse.** If P1 still
  produces an edge, the edge is coming from the price path and not from the
  fill, and the pipeline is broken. This is the test that killed the crypto
  maker result (+1.351¢ shuffled versus +0.873¢ real, p=0.995).
- **P2 — rest a bid on a random market at a random minute**, same sizing, same
  fill rules, no signal. **Must return nothing.**

**A third check, because a placebo can be a no-op:** P1 is asserted to have
actually changed the assignment (a planted-difference check). The repo's first
placebo was algebraically a no-op and passed vacuously.

## 10. WHAT WOULD MAKE ME DROP THIS — the part usually left out

**Any one of these ends it. No re-slicing, no "but on Challenger".**

1. **M1's net per match is ≤ 0 on the selection set.** Dropped. The whole
   premise is that removing the crossing cost flips the sign; if it does not,
   there is nothing to salvage.
2. **P1 or P2 produces an edge.** The pipeline is broken; every number is void
   and gets retracted rather than patched.
3. **The fill rate is so low the strategy cannot be run** — pre-committed floor:
   **fewer than 1 match in 5 achieves any fill.** A rule that fires 3,436 times
   and fills 200 is not a strategy.
4. **M1 is positive on selection and its holdout result is ≤ 0.** Dropped, and
   recorded as a retraction rather than as "needs more data".
5. **Effective sample size after clustering is under 100 matches.** Then it is
   reported as UNDECIDABLE (Guard #21) — not as a negative, and not as a
   positive.

**And one that is not a drop criterion:** a *small* positive that does not clear
the no-skill band is **UNDECIDABLE**, reported as such, with the band stated.
"Could not tell" is not "no", and treating it as "no" is the mistake this repo
has recorded more than any other.

## 11. Standing prediction

**I expect M1 to fail, for the crypto reason: adverse selection.** Takers
overwhelmingly buy, so the fade's resting bid sits on the hard side; and a thin
ITF book is where a stale quote is most exposed, not least. The zero maker fee
on ITF and Challenger is a genuine structural gain over crypto and I do not
think it is enough.

**Recorded now so it cannot be adjusted after the number is seen.**
