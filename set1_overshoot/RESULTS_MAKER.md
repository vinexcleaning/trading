# The fade as a MAKER — the lever works, and there is nothing under it

**2026-08-21.** Pre-registered in `PREREGISTRATION_MAKER_FADE.md` with five
amendments, all before any result existed. Data audit in `MAKER_DATA_AUDIT.md`.

---

## The answer, in one paragraph

**Waiting in the queue instead of paying to jump it really does remove the cost
— about 3 cents a contract, which is exactly what the study said the cost was.
And it buys nothing, because the edge underneath it is not distinguishable from
zero.** Measured on 738 matches between 2026-06-14 and 2026-08-01, being a patient
buyer turns a bet that loses 2.35¢ a contract into one that makes 0.83¢ if you are at the front of the queue and loses 2.78¢ if you are at the
back. **We cannot observe which**, and the optimistic end sits inside the range
that pure luck produces.

**This does not kill the idea on evidence. It is `UNDECIDABLE`** (GUARDS #21):
the test could not tell, and saying otherwise in either direction would be the
mistake this repo has recorded more than any other.

**And the more useful half of the answer is §8: it is not going to become
decidable.** Telling a +1.29% effect apart from luck needs about **8,000
matches**. The entire universe Kalshi will still hand over holds **902**, the
history cannot be extended backwards because the retention window moves forward
a day every day, and collecting forward runs at **8.6 firing matches a day** —
**about two and a half years** to get there. **No amount of cleverness with the
existing data closes a nine-fold shortfall.**

---

## 1. What was measured

| | |
|---|---|
| entry rule | `deep:30@38` — the study's own, imported and called, not re-implemented |
| period | **2026-06-14 → 08-01** (selection). The check period was **not opened** — §6 |
| matches that fired | **738** |
| price path | one-minute `yes_bid`/`yes_ask` from Kalshi, 13.2M candle rows |
| fills | from **11.7M real trades**; a resting order is credited only when a trade printed on the correct side at a price that would have reached it |

**First, the pipeline agrees with the original study**, which is the only reason
anything below is worth reading:

| | this rebuild | the study |
|---|---|---|
| mispricing vs mid | **+0.94pp [−2.33, +4.10]** | +2.53pp |
| taker net, pooled | **−2.35¢ [−5.62, +0.80]** | −1.10¢ |
| taker net, main tour | **−1.48¢** | −1.10¢ |

**My range contains the study's number and also contains zero.** That is the
first hint of the whole result.

## 2. The three registered arms

Per contract, in cents. **"Per attempt" counts the matches we never got into as
zero**, which is the number a maker backtest usually omits.

### M1 — all tiers pooled, 738 matches, underdog won 69.9%

| | fill rate | per FILL | per ATTEMPT |
|---|---|---|---|
| **R1** bid on the underdog, front of queue | 90.3% | +0.00 [−3.38, +3.23] | +0.00 [−3.04, +3.03] |
| **R1** bid on the underdog, back of queue | 53.3% | −9.46 [−14.23, −4.86] | **−5.05 [−7.47, −2.56]** |
| **R2** ask on the favourite, front of queue | **95.0%** | +0.88 [−2.38, +4.17] | **+0.83 [−2.21, +3.89]** |
| **R2** ask on the favourite, back of queue | 80.1% | −3.47 [−7.22, +0.31] | −2.78 [−5.72, +0.17] |
| *taker benchmark* | 100% | −2.35 [−5.62, +0.80] | −2.35 [−5.62, +0.80] |
| *doing nothing* | — | 0.00 | 0.00 |

**M2 (maker-free tiers, 632 matches)** and **M3 (main tour, 106 matches)** say
the same thing: R2 front +0.78 and +1.14, R2 back −2.63 and −3.65, taker −2.50
and −1.48. **No arm separates from zero and no arm separates from the others.**

## 3. Three things that ARE established

**(a) My own prediction was wrong: fills are plentiful.** I predicted before
running that this would fail for want of fills. **R2 fills on 95% of matches at
the front of the queue and 80% at the back.** The pre-registered kill switch —
fewer than 1 match in 5 getting filled — is cleared by a mile.

**(b) Which side you rest on matters, and R2 is the better side.** Resting an
ask on the favourite fills 95% / 80%; resting a bid on the underdog fills
90% / **53%**. Selling the favourite *is* being long the underdog, and it sits
where the flow is: takers buy about three times in four, on both tickers of a
match. **That is a real, reusable structural fact about this market.**

**(c) The maker lever removes roughly the cost the study said it would.** Taker
−2.35¢ against R2-front +0.83¢ is a **3.2¢** swing, against the study's stated
3.61¢ cost bar. **The mechanism is confirmed. The mechanism was never the
question.**

## 4. And the thing that is not established: any edge at all

Using `common/noskill.py` — where a strategy making *these* bets at *these*
prices lands 9 times in 10 if the market price is exactly right:

| | observed | no-skill range | verdict |
|---|---|---|---|
| R2 front | +1.29% | [−4.21%, +4.05%] | **INSIDE — means nothing yet** |
| R1 front | +0.00% | [−4.46%, +4.24%] | **INSIDE — means nothing yet** |
| R2 back | −5.16% | [−4.65%, +4.43%] | **OUTSIDE, worse than no skill** |

**So the honest bracket runs from "cannot tell" to "worse than doing nothing",
and where you land inside it depends on queue position, which is not in the
data.**

## 5. The depth grid — a PICTURE, and the trap inside it

Pre-registered as a look with no verdict. `deep:40` is included because it is
the version that was asked for.

| depth | fired | dog mid | won | **mispricing vs mid** | taker fee | taker net |
|---|---|---|---|---|---|---|
| 8 | 1,336 | 50.0¢ | 48.4% | −1.55pp [−3.99, +0.92] | 1.53¢ | −5.58 |
| 12 | 1,168 | 53.7¢ | 52.7% | −0.98pp [−3.55, +1.71] | 1.53¢ | −4.97 |
| 20 | 936 | 60.9¢ | 61.2% | +0.27pp [−2.58, +3.15] | 1.49¢ | −3.36 |
| **30** | 738 | 69.0¢ | 69.9% | **+0.94pp [−2.27, +4.10]** | 1.35¢ | −2.35 |
| 35 | 617 | 73.5¢ | 74.4% | +0.87pp [−2.28, +4.17] | 1.20¢ | −2.21 |
| **40** | 497 | 78.4¢ | 79.9% | **+1.51pp [−1.69, +4.67]** | 1.02¢ | −1.36 |

**The net result really does improve with depth, from −5.58¢ to −1.36¢. His
instinct is right about the direction — for the third time.**

**And it is mostly not an edge.** Two things move together as the trigger
deepens:

1. **The underdog gets more expensive** (50¢ → 78¢), and **the Kalshi fee falls
   as the price leaves the middle** — 1.53¢ down to 1.02¢, because the fee is
   proportional to price × (1 − price).
2. **The mispricing itself stays flat and never separates from zero** — every
   single row's range crosses zero, from −1.55pp to +1.51pp.

**GUARDS #10 warns that a monotone improvement along the selection knob is
evidence of contamination until proven otherwise.** Here there is a plainer
explanation and it is arithmetic: **a deeper trigger buys at a more extreme
price, where the fee is smaller.** The edge is not growing. The toll is
shrinking.

**`deep:40` is therefore not a promotion candidate.** It is the least-bad row of
a grid in which nothing clears zero, on the smallest sample in the grid.

## 6. Placebos, and one that failed for a reason worth keeping

**P1 — shuffle which side was the aggressor.** Real +0.83¢, shuffled +0.66¢ (738 matches, 2026-06-14 → 08-01).
**Nothing collapsed, because there was nothing to collapse.** With the real
result inside the no-skill range this test has no power here; it is reported as
uninformative rather than as a pass.

**P2 — a random market at a random minute. PASSES.** On **728 control matches**
that fire at no depth in the grid, with tapes pulled specifically to serve as
this control rather than borrowed from the treatment group:

| | real signal | control |
|---|---|---|
| R2 fill rate | 95.0% | 67.0% |
| R2 per attempt | +0.83¢ | **−5.01¢** |
| R1 per attempt | +0.00¢ | **−5.08¢** |

**The control loses about 5¢ a contract, which is what resting into a market for
no reason should cost.**

**And one thing the control shows that the treatment cannot:** the signal minute
is a moment of unusually heavy trading — fills run **95%** there against **67%**
at a random minute in the same kind of match. **Being easy to fill is a property
of the moment, not of the strategy**, and it is worth knowing for any other
maker idea aimed at a moment of sudden movement.

**⚠ P2 failed twice first, and the third cause is a live trap for anyone using
this data.** It returned **+12.40¢ against the real signal's +0.83¢** — the
placebo beating the thing it controlled for. Three look-aheads, found in order:
it read the underdog's own price path; it could rest *after the match ended*,
where the winner's book is pinned near 100¢; and —

> **the event set is conditioned on the favourite collapsing later.** Entering at
> a random minute on those matches buys the underdog cheap, at 48¢ on average,
> before a fall the selection has already guaranteed, in matches where the
> underdog goes on to win 69.9%.

**Any analysis that enters BEFORE the trigger minute on these matches is reading
the future**, however innocent the entry rule looks. That is amendment A5 and it
is the most reusable thing in this document.

## 7. Sensitivities — the answer does not hinge on my choices

| resting time | R2 front | R2 back |
|---|---|---|
| 10 min | +1.14 [−1.87, +4.14] | −2.15 |
| **30 min (registered)** | **+0.83 [−2.21, +3.89]** | −2.78 |
| 120 min | +0.79 [−2.26, +3.88] | −2.71 |

Pre-match quote gate at 5¢ instead of 10¢: +0.44 [−3.07, +3.80] on 647 matches.
**Every variant lands in the same place.**

## 8. The pre-registered drop criteria, applied honestly

| # | criterion | outcome |
|---|---|---|
| 1 | M1's net ≤ 0 on selection → drop | **INDETERMINATE.** Front +0.83, back −2.78. Amendment A3 turned the single number into a bracket and the criterion was written for a point estimate. **Stating this rather than picking the bound that gives a cleaner answer.** |
| 2 | a placebo produces an edge → void | **Passed**, after P2 was rebuilt twice |
| 3 | fewer than 1 match in 5 fills → drop | **Passed comfortably** — 80–95% |
| 4 | positive on selection, ≤ 0 on the check period | **Not evaluated.** See below |
| 5 | effective sample under 100 matches → UNDECIDABLE | 738 matches, counted one per match rather than one per fill |

### Why the check period was NOT opened, with the arithmetic

**Not asserted — computed.** Using `common/noskill.py` on the real entry-price
distribution, here is how wide the range of pure luck is at each sample size,
against an effect of about **+1.29%**:

| matches | where luck alone lands, 9 times in 10 | effect visible? |
|---|---|---|
| **164** — the whole check period | −8.35% to +7.99% | no, by a factor of six |
| **738** — the selection period | −3.82% to +3.92% | no |
| 5,000 | −1.52% to +1.51% | no |
| **8,000** | −1.23% to +1.23% | **yes, just** |
| 20,000 | −0.76% to +0.76% | comfortably |

**So the check period could neither confirm nor refute this**, and §5 allows one
evaluation and no second pass. Spending it here would leave nothing for a future
version of the idea that actually has something to test. **The check period
stays sealed.** Logged in `DECISIONS.md` as decision 21.

### ⚠ AND THIS IS THE REAL RESULT: the question is not answerable yet

**You would need roughly 8,000 matches. The entire retrievable universe holds
902** — 738 in the selection period and 164 in the check period, at
`deep:30@38`, between 2026-06-14 and 08-20.

**The history cannot be extended backwards.** Kalshi's retention window ends at
2026-06-14 and moves forward a day every day; everything older is gone for good.

**So the only route is forward, and it is slow.** The check period ran 19 days
and produced 164 firing matches — **8.6 a day**. At that rate, 8,000 matches is
**about two and a half years** of collecting.

**That is a far more useful answer than "undecidable".** It says: no amount of
cleverness with the existing data will settle this, the shortfall is roughly
nine-fold, and the only cure is time nobody is going to spend on a strategy
whose central estimate is already sitting on zero.

## 9. What was NOT tested — CLAUDE.md §9c step 7

1. **Anything before 2026-06-14.** Permanently gone; the study's first three
   weeks cannot be re-pulled, ever.
2. **Queue position**, which is the whole width of the bracket. Not in the
   candles. Only resting real orders would settle it, which is live money.
3. **Exiting as a maker.** Every arm here holds to settlement and exits free.
4. **Resting away from the touch** — a cent better, a cent worse. Only at-touch
   was tested, and a maker's price is a free parameter this study fixed.
5. **Sizing.** Every fill is treated as one contract; nothing about how much of
   the available size you could actually take.
6. **The 4 markets** whose candles never returned (0.011%), and the **81% of
   ITF** dropped for having no real pre-match book. Those are a different
   market, not a smaller one.
7. **Anything conditioned on the players, tournament, surface, or round.** Not
   touched. This is a pure price rule.
8. **The check period**, deliberately.
9. **A maker on the OTHER side** — selling the underdog into the overshoot
   rather than buying it. The study looked at both sides as a taker; this only
   built the buy side.

## 10. Standing prediction, scored

**I predicted, before the numbers existed, that it would fail on adverse
selection with R2 filling well and R1 filling poorly.**

- **R2 filling well and R1 poorly: correct** (95%/80% against 90%/53%).
- **"It fails": not established.** It did not fail. It could not be told apart
  from zero, which is a different verdict and a weaker one.
- **An earlier version of the prediction — that it would fail for want of fills
  — was wrong**, and is kept in the pre-registration rather than deleted.

---

# THE REFEREE — three lists, and the third is not empty

## 1. STANDS

- **The pipeline reproduces the original study.** Three independent numbers
  overlap it: mispricing +0.94pp against +2.53pp, taker net −2.35¢ against
  −1.10¢, main tour −1.48¢ against −1.10¢. Nothing below would be worth reading
  without this.
- **Fills are plentiful — 80% to 95%.** Survives because every fill comes from a
  real trade on the correct side at a price that would have reached the order,
  out of 11.7M trades, with 26 tests pinning that rule including planted markets
  where a resting bid is offered only taker *buys* and must not fill.
- **Resting an ask on the favourite fills far better than a bid on the
  underdog.** Survives on an independently measured mechanism: takers buy on
  **both** tickers of a match, 126 of 126 events with over 200 trades a side.
- **The grid's improvement with depth is mostly the fee, not the edge.**
  Survives on arithmetic rather than inference: the Kalshi fee is proportional
  to price × (1 − price), the underdog price moves 50¢ → 78¢, and the measured
  fee falls 1.53¢ → 1.02¢ while the mispricing crosses zero at every depth.
- **~8,000 matches would be needed and 902 exist.** Survives because it is
  computed with the shared `common/noskill.py` on the real entry-price
  distribution, not asserted.

## 2. DOWNGRADED

- **was:** "the maker version makes +0.83¢ a contract."
  **now:** *"+0.83¢, which is inside the range luck alone produces (−4.21% to
  +4.05%). It means nothing yet."*
  **because:** the no-skill band contains it.

- **was:** "placebo P1 passed."
  **now:** *"P1 is uninformative here. The real result is inside the no-skill
  range, so there was no fill advantage for a shuffle to collapse."*
  **because:** a placebo run against a null effect tests nothing, and calling
  that a pass is the vacuous-check failure this repo has recorded.

- **was:** my standing prediction, "it fails on adverse selection."
  **now:** *"the fill-side half was right — R2 fills well, R1 poorly. The
  'it fails' half is not established: it could not be told apart from zero,
  which is weaker than failing."*
  **because:** UNDECIDABLE is not a negative.

- **was:** "R1 and R2 are the same bet."
  **now:** *"the same bet to within about a cent — the two tickers mirror at a
  median of 0¢ but a mean of 0.81¢, and only 44% of paired minutes are exact."*
  **because:** the underdog's quotes here are derived from the favourite's book
  rather than read from its own, which is what removed the clock bug; that
  choice costs about a cent of precision and it should be stated, not hidden.

## 3. FOR THE USER — genuinely unresolved

**Not empty, and the first one is a question only he can answer.**

- **The question:** when you have rested an order on Kalshi, did it actually get
  filled — and how big were you?
  **Why it decides this:** the entire width of the answer is queue position.
  Front of the queue is +$1.20 per $100 risked; back of the queue is −$4.00. The
  exchange does not publish where in the queue an order sits, so **this data
  cannot settle it and his own experience is better evidence than anything here.**
  A small order on a thin ITF book may genuinely sit near the front far more
  often than the pessimistic bound assumes.
  **What would settle it otherwise:** resting real orders and watching, which is
  live money and therefore not ours to start.

- **The question:** is it worth collecting forward for about two and a half
  years to settle this?
  **One side:** it is free and unattended, the recorder already exists, and the
  shortfall is only time.
  **The other side:** the central estimate is already sitting on zero, so the
  most likely purchase is a confident "no" in 2028, and every day of collection
  is attention that could go to an idea with a larger claimed edge.
  **My recommendation, which is not a decision:** no. But it is a judgment about
  what his time is worth, not a measurement.
