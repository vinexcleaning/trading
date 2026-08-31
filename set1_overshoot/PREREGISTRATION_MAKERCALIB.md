# PREREGISTRATION — does MAKER execution turn the 90–95¢ favourite positive?

**Written 2026-08-30, before any result exists.** Origin: `tennis` mailbox 021.
What had already been looked at is declared in §8.

---

## 1. The question

A measurement on 34,218 settled tennis markets found that **prematch favourites
genuinely win more often than their price implies** — and that **every price
band still loses money when you buy at the ask.** The best band, 90–95¢, is
**0.7 points underwater.**

> **0.7 points is smaller than the spread. So: does resting a bid instead of
> crossing close it?**

**Restated without jargon:** the market is slightly wrong about heavy
favourites, in our favour, by less than it costs to place the bet. **The
question is whether waiting to be sold to, instead of buying at the offer,
saves more than 0.7 cents in every dollar.**

## 2. ⚠ Why this is NOT mailbox 017 again

017 asked the same execution question and answered **UNDECIDABLE**. It must be
said clearly why this is a different question rather than a re-run:

| | 017 | this |
|---|---|---|
| what is being executed | a **signal** — the set-1 deep fade | **whole-market calibration** — every favourite in a band |
| where the edge comes from | a strategy's selection | **the market's own mispricing**, with no selection at all |
| sample | 738 matches that fired a rule | every settled market in the band |

**017's null does not carry over**, because 017's edge was a strategy's edge and
this one is the market being wrong about a whole population. **What does carry
over is the method**, and it is reused unchanged (§5).

## 3. The hypothesis, pre-committed

> **H-CALIB.** For settled tennis markets whose prematch mid is 90–95¢, entering
> by a resting bid rather than at the ask produces a **positive net result per
> market after fees, after a fill model built only from observed trades, and
> after markets that never filled are counted as no-trades rather than dropped.**

## 4. Unit, sample, and the split

**Unit: one market.** At 90–95¢ only one side of a match can qualify, so a match
contributes at most one observation and no clustering correction is needed. That
is a property of the band, not an assumption — **it is asserted in code and the
run fails if a match ever contributes two.**

| | |
|---|---|
| universe | settled tennis markets, six series, with a usable prematch quote |
| window | **2026-06-14 → 2026-08-20** |
| bands | 75–80, 80–85, 85–90, **90–92.5**, **92.5–95**, 95–97.5 |
| **selection set** | 2026-06-14 → **08-01** |
| **untouched check period** | **08-02 → 08-20**, opened at most once |

**Reporting all six bands, not only 90–95.** The measurement that produced this
job found the effect **reverses above 95¢**, and a result that only shows the
favourable band hides that.

## 5. The fill model — carried across from 017 unchanged

1. **A resting bid at price P fills only when a real trade printed against it**
   — a trade whose aggressor was selling, at or below P. **No trade, no fill.
   No modelled fill, ever.**
2. **The queue is a BRACKET, not a number.** The candles carry no size, so
   queue position is unobservable: a **front** bound (any qualifying trade fills
   us) and a **back** bound (we sit behind the tier's typical resting size).
   **The truth is between them and this study will not claim to know where.**
3. **Unfilled markets stay in the denominator as no-trades.**
4. **One whole minute of latency.**
5. **Held to settlement.** Kalshi charges nothing at settlement, so there is no
   exit fee on either arm — the maker saves the spread and the entry fee
   difference only.
6. **Fees from `common/kalshi_fees.py` alone**, per series: **zero for makers on
   ITF and Challenger, charged on ATP and WTA main tour.**
7. **Block trades excluded** (there are none in this tape, and the filter stays
   anyway).

**The resting window.** The order rests from **60 minutes before play starts
until play starts**, then is cancelled. **Sensitivities at 30 and 240 minutes**,
pre-committed. If they disagree that is reported as a disagreement.

## 6. ⚠ JOB 0 — availability first, profitability second

**`GUARDS.md` #24 may end this before execution matters.** Its finding is that
*a quote is not a constant of nature* — a market maker declines to quote when
there is nothing left to be uncertain about, and measuring only where a quote
exists conditions the sample on the event still being uncertain.

**Two availability numbers are computed and reported BEFORE any profit
number:**

1. **Does a two-sided quote exist prematch in the band at all**, and how wide is
   it? (Partly true by construction — the band is defined by a prematch mid —
   so this is a check that the quote is real rather than a 1/99 shell.)
2. **How often could a resting bid have been filled at all?** This is the one
   that decides the job. **An edge that fills 3 times in 100 is not an edge.**

⚠ **And the selection trap #24 names applies here too:** markets that never
attract a seller are exactly the ones where the favourite was never in doubt.
**If fills concentrate on the markets where the favourite later wobbled, the
maker arm has quietly selected the riskier half of the band.** This is measured
by comparing the settled win rate of filled markets against unfilled ones. **A
gap there is a finding in its own right, and it is the most likely way this
produces a fake positive.**

## 7. The arms — three, and nothing added later

| arm | universe |
|---|---|
| **C1 (primary)** | 90–95¢, all six series pooled |
| **C2** | 90–95¢, ITF and Challenger only — where makers pay no fee |
| **C3** | 90–95¢, ATP and WTA main tour only — where makers pay |

**All six bands are reported as a picture; only C1–C3 get a verdict.** These
three join the single repo-wide Benjamini–Hochberg denominator, taking it from
**36 to 39.**

## 8. What has already been looked at

- **The coordinator's table** in mailbox 021 — the gaps, the intervals, and the
  EV-at-ask column for all six bands.
- **My own band counts and the fraction with trade tapes on disk** (~30% before
  the pull that is filling the rest).
- **The prematch spread** in this data, about 2.3¢ on main tour, which is what
  makes the question live at all.
- **No maker fill, fill rate, or net result has been computed for any band.**

## 9. The placebos

- **P1 — quote the WRONG side.** Rest an **ask** at the same level instead of a
  bid, on the same markets. **This must lose**, and lose roughly the same amount
  the real arm gains. *On the largest crypto series the wrong-side placebo beat
  the real result, and that is the only reason anyone knew the fill model was
  broken.*
- **P2 — a random market at a random minute**, drawn strictly inside the tape.
  ⚠ `RESULTS_MAKER.md` §6 records a placebo that drew minutes **after
  settlement**, where the book is pinned at the known result; it beat its own
  treatment by +12.40¢ and took three rounds to find.

## 10. WHAT WOULD MAKE ME DROP THIS

**Any one of these ends it.**

1. **Fewer than 1 market in 5 gets any fill** at the front-of-queue bound.
   Unreachable, regardless of the arithmetic.
2. **C1's net is ≤ 0 at the FRONT bound** — the most optimistic queue
   assumption. If the best case is negative there is no case.
3. **Filled markets have a materially different settled win rate from unfilled
   ones**, i.e. the fills are selecting the wobblier half. Then the maker number
   is not measuring the band it claims to.
4. **Either placebo produces an edge.** Void, and retracted rather than patched.
5. **C1 is positive on the selection set and ≤ 0 on the check period.**

**And what is NOT a drop:** a small positive that does not clear the no-skill
band is **UNDECIDABLE** and is reported as such, with the band stated.

## 11. Standing prediction

**I expect the fill rate to be the thing that decides it, and I expect it to be
low.** A resting bid at 92¢ needs someone willing to sell a near-certainty
cheaply, and the people holding it have little reason to. **Where it does fill,
I expect adverse selection** — the seller knows something, or the favourite is
about to wobble — which is criterion 3.

**I give the profitable outcome less than one chance in four, and I expect the
honest verdict to be UNDECIDABLE rather than either a clean yes or a clean no.**

---

# AMENDMENT B1 — 2026-08-30, before any result exists

**§5 said the order rests "from 60 minutes before play starts until play
starts". Building it exposed that as a LOOK-AHEAD, and this fixes it.**

The prematch quote in §4 is the one at **t0 − 1**, the last minute before play.
Resting a bid *at that price* during the hour *before* t0 − 1 means the order is
sitting at a price nobody knew yet. **No result was computed under the broken
version; it was caught while writing the code.**

**Two causal repairs, and BOTH are run rather than choosing one:**

| mode | decision | rests | causal because |
|---|---|---|---|
| **prematch** | the quote at **T = t0 − 60** | T → t0 | the band, the price and the window all come from the same moment, and nothing after T is consulted |
| **into play** | the prematch quote at t0 − 1 (what the coordinator's table uses) | t0 → t0 + 60 | the price is known before the order exists |

**⚠ `into play` is the realistic one and it is where the trap lives.** A resting
bid below the market only fills when the price comes **down** to it — which is
when the favourite is in trouble. **That is adverse selection by construction**,
and it is exactly what drop criterion 3 was written to catch. **If the fills
concentrate on wobbling favourites, a positive number there is not an execution
win, it is a worse population bought at a discount.**

**`prematch` should have the opposite problem:** far fewer fills, because before
play there is little reason for anyone to sell a near-certainty cheaply.

**Both are reported side by side. Neither is chosen in advance, and if they
disagree that disagreement is the finding.**
