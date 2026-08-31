# Does maker execution turn the 90–95¢ favourite positive? Not reliably.

**2026-08-30.** Mailbox 021. Pre-registered in `PREREGISTRATION_MAKERCALIB.md`
with one amendment, both before any result. Code: `src/p9_makercalib.py`.

Selection period **2026-06-14 → 2026-08-01**. Entries at the ask for the taker
arm and at the resting bid for the maker arm, fills only from observed trades,
fees from `common/kalshi_fees.py`, held to settlement.

---

## The answer, in one sentence

**No — the most optimistic queue assumption reaches the edge of what luck alone
produces, and any queue at all puts it back on zero.**

| C1, 90–95¢ pooled, 390 markets closing 2026-06-14 → 08-01 | resting into play |
|---|---|
| taker, crossing at the ask | **+0.67%** [−1.77, +2.91] |
| maker, **front** of the queue | **+1.75%** [−0.12, +3.41] |
| maker, **back** of the queue | **−0.28%** [−1.53, +0.76] |

**On the 193 markets that actually filled, the return is +3.59% against a
no-skill range of [−3.81%, +3.59%] — sitting exactly on the boundary.** (Same
window; the range is what `common/noskill.py` says luck alone produces from bets
at those prices.)
`common/noskill.py` calls it **INSIDE the range: means nothing yet.**

**Resting before the match instead is worth −0.04 points against simply
crossing** — taker +0.32%, maker front +0.28%, back +0.02%, on 292 markets over
the same window. Not "nothing" as a figure of speech: a measured difference of
four hundredths of a point.

> **So `UNDECIDABLE`, like mailbox 017 — but for a different reason.** 017 had
> no edge underneath the execution. **Here there is a real edge underneath and
> the queue decides whether you get any of it, and the queue is the one thing
> the data cannot show.**

---

## 1. ⚠ A CORRECTION TO WHAT I REPORTED MID-RUN

**On roughly 40% of the tape I reported that fills happen only when the
favourite is in trouble, with a penalty of 4 to 8 points. On the full tape that
is TRUE FOR 75–90¢ AND NOT TRUE FOR THE BAND THAT MATTERS.**

| band | won when filled | won when not | gap |
|---|---|---|---|
| 85–90¢ | 84.2% | 92.4% | **−8.2** |
| **90–92.5¢** | 93.5% | 94.0% | **−0.5** |
| **92.5–95¢** | 95.0% | 96.9% | **−1.9** |

**Pooled across 90–95¢ the adverse selection is −1.1 points, not −4 to −8.**
The earlier figure came from a partly-downloaded tape where the missing markets
were disproportionately the quiet ones. **It changed the reason for the answer,
though not the answer.**

## 2. ⚠ THE PLACEBO FAILED FIRST, AND IT WAS MY ARITHMETIC

The pre-registered wrong-side placebo — rest an **ask** instead of a bid, i.e.
sell the favourite — came back at **+3.56%**, better than the real arm's +1.75%.
**Selling a 93% favourite cannot make money. Under drop criterion 4 that voided
the run.**

**The fill model was fine. I had flipped which side filled us but kept the BUY
profit-and-loss**, so the "placebo" was still booking profitable long trades and
merely filled more often — there are more buyers than sellers, so it filled 71%
of the time against the real arm's 49.5%.

Corrected, a short's payoff flipped properly:

| | real arm | wrong-side placebo |
|---|---|---|
| C1 front of queue | **+1.75%** | **−3.58%** |
| C1 back of queue | −0.28% | −2.26% |

**Selling the favourite now loses about what buying it gains, which is what a
sound fill model must produce. Placebo passes.**

**This is the second time a placebo has caught a real bug in this folder** — the
first was the free-roll's random-minute test. They keep earning their place.

## 3. The reproduction check, first

Before any maker number, the coordinator's own table was reproduced:

| band | their implied / observed | mine |
|---|---|---|
| 80–85 | 82.2% / 85.9% | 82.2% / 85.8% |
| 85–90 | 87.2% / 89.5% | 87.3% / 89.6% |
| 90–92.5 | 91.1% / 93.2% | 91.1% / 92.9% |
| 92.5–95 | 93.5% / 95.1% | 93.5% / 95.3% |
| **95–97.5** | **95.8% / 93.9%** | **95.8% / 93.5%** |

**Implied matches to the decimal in every band, and the reversal above 95¢
reproduces.** Their heaviest favourites really are overpriced.

⚠ **One difference, in my favour and therefore worth stating loudly:** my
EV-at-ask is better than theirs in every band, because I require a real prematch
quote (spread ≤10¢). **Conditioning on a good quote improves the taker result** —
which is `GUARDS #24`'s selection warning showing up as a positive rather than
as an absence.

## 4. Job 0 — availability, per GUARDS #24

**Two routes, and they fail in opposite directions.**

| | rest before play | rest into the first hour |
|---|---|---|
| fills, front of queue | **27.7%** | **49.5%** |
| fills, back of queue | **~0%** | 9.8–14.2% |
| adverse selection | **−2.7 points** | −1.1 points |
| beats the taker by | **−0.04 points** | +1.08 points |

**Before play, almost nobody sells you a near-certainty cheaply** — you fill 28
times in 100 at the front of the queue and essentially never behind it, and you
gain nothing over just crossing.

**Into play you fill about half the time and do gain about a point over the
taker** — but only at the front of the queue, and the gain is inside the
no-skill range.

**Neither route trips drop criterion 1** (fewer than 1 in 5 filling): 27.7% and
49.5% both clear it. **Availability is not what kills this.** That is worth
saying plainly, because `GUARDS #24` predicted it would be.

## 5. The pre-registered drop criteria, applied

| # | criterion | outcome |
|---|---|---|
| 1 | fewer than 1 in 5 fills at the front bound | **No** — 27.7% and 49.5% |
| 2 | C1 net ≤ 0 at the front bound | **No** — +1.75%, but its range touches zero at −0.12 |
| 3 | filled markets settle differently from unfilled | **Partly** — −1.1 points in-band, and −8.2 at 85–90¢ |
| 4 | a placebo produces an edge | **Fired, then fixed.** §2 |
| 5 | positive on selection, ≤ 0 on the check period | **Not evaluated** — see below |

### The check period was NOT opened

**C1 is not positive on the selection set in any way worth carrying forward** —
it is inside the no-skill range at the optimistic bound and negative at the
pessimistic one. **Criterion 5 tests a positive result, and there is not one.**
Opening the check period to confirm an undecidable would spend the single
evaluation for nothing. **It stays sealed.**

## 6. What this does to his Part I

021 asked for one sentence if the answer stays negative. **It is not quite
negative — it is "not reachable", which for a decision is the same thing:**

> **The market really is wrong about heavy favourites, by about 1.8 points in
> the 90–95¢ band. Crossing the spread costs more than that. Resting instead
> recovers about a point of it — but only if you are first in the queue, and
> where in the queue you are is not observable and not controllable.**

**Combined with the reversal above 95¢** — where the very heaviest favourites
are genuinely overpriced, which is where a parlay structure would want to live —
**there is nothing here to build on.**

## 7. What was NOT tested — CLAUDE.md §9c step 7

1. **Resting INSIDE the spread.** The registered rule rests at the best bid.
   `--improve` exists and is deliberately labelled a look with no verdict,
   because it was added after the registered rule ran.
2. **The queue itself.** The whole width of the answer. Only resting real
   orders would settle it, which is live money.
3. **Resting windows other than 60 minutes.** 30 and 240 are pre-registered and
   were not run.
4. **Sizes other than 100 contracts.**
5. **Cancel-and-replace**, chasing the price down. Every order here rests at one
   price and is cancelled unfilled.
6. **The check period**, deliberately.
7. **Baseball, soccer, and the other 3,600 recorded families.** The
   calibration measurement that started this covers tennis only.
8. **Bands below 75¢ and above 97.5¢.**

## 8. Standing prediction, scored

**I predicted the fill rate would decide it and be low, with adverse selection
where it did fill, and gave the profitable outcome less than one chance in
four.**

- **Fill rate low: WRONG.** 49.5% resting into play is not low, and availability
  is not what kills this. `GUARDS #24` predicted otherwise too.
- **Adverse selection where it fills: right, but much smaller than I said**
  in-band — −1.1 points, not the −4 to −8 I reported mid-run.
- **Verdict UNDECIDABLE rather than a clean yes or no: right.**

---

# THE REFEREE

## 1. STANDS

- **The coordinator's calibration table reproduces** — implied to the decimal in
  all six bands, and the reversal above 95¢ with it. Nothing here would be worth
  reading otherwise.
- **The maker gains about a point over the taker when resting into play**, and
  nothing when resting before it. Same markets, same settlement, both arms
  drawn from an identical population — asserted in code, and the run aborts if a
  match ever contributes two observations.
- **The wrong-side placebo now mirrors the real arm** (−3.58% against +1.75%),
  which is what a sound fill model must produce.
- **Availability is NOT the constraint**, against `GUARDS #24`'s expectation:
  27.7% and 49.5% of markets fill at the front of the queue.

## 2. DOWNGRADED

- **was:** *"fills happen only when the favourite is in trouble — a 4 to 8 point
  penalty."*
  **now:** *"true at 75–90¢, where the gap reaches −8.2 points. In the 90–95¢
  band it is −1.1."*
  **because:** the first figure came from a 40%-complete tape whose missing
  markets were disproportionately quiet ones.
- **was:** *"the maker arm returns +1.75%."*
  **now:** *"+1.75% at the front of the queue, whose range runs [−0.12, +3.41]
  and touches zero, and −0.28% at the back. On the filled markets it sits
  exactly on the edge of the no-skill range."*
  **because:** a bracket that straddles zero is not a return.
- **was:** my own prediction that a low fill rate would decide it.
  **now:** *"wrong — 49.5% is not a low fill rate, and availability is not what
  kills this."*

## 3. FOR THE USER — genuinely unresolved

**One item, and it is the same one the earlier maker study ended on.**

- **The question:** when you rest an order on Kalshi, are you near the front of
  the queue or the back?
  **Why it decides this:** front is +1.75%, back is −0.28%. **That is the entire
  answer**, the exchange does not publish it, and no amount of this data will.
  **Your own experience of resting orders is better evidence than anything
  here** — and it is now the second study in a row to end on this exact
  question, which is itself a reason to answer it once and reuse it.
  **What would settle it otherwise:** resting real orders and watching. Live
  money, so not ours to start.
