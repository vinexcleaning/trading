# THE KILL PILE — nothing is deleted, ever

**Started 2026-09-18, on his instruction, in his words:**

> *"I feel like the strategy factory might kill stuff that could still be
> useful... there should be like a kill pile because Claude is prone to making
> mistakes and killing stuff that could be good."*

**He is describing a failure this repo has already had.** A sweep over price
features was used to close a question about individual players, which it never
tested. That idea was deleted and nobody found out for weeks.

## The rule

**Append-only. Rows are never edited and never removed.** A row that turns out
to be wrong gets a new row below it saying so.

**Every row must carry a resurrection condition.** A kill with no way back is a
deletion wearing a different hat, and it is not allowed here.

**"What was NOT tested" is the column the next broad pass reads.** It is not a
caveat — it is the input to the next cycle.

---

| id | what it was | what killed it (the number) | what was NOT tested | what brings it back |
|---|---|---|---|---|
| **K-01** | Seven-inning doubleheaders mispricing a nine-inning total | **All 2,060 games scheduled in 2026 are 9 innings.** The seven-inning rule is gone from the sport | Nothing — the premise does not exist any more | MLB reinstating shortened doubleheaders. Check once a season, not again this year |
| **K-02** | Inning-winner market (`KXMLBINNINGWIN`) | Measured cost to enter **7.07c**, 18 Aug – 4 Sep 2026 | Whether the cost falls in the playoffs when volume rises; whether a resting order gets filled cheaper than taking | Cost bar under 3c on 500+ two-sided touches |
| **K-03** | "The two team totals must add to the game total" | **It is not an identity.** Two "over" prices do not add — the game total depends on how the clubs' runs combine, not on a sum of thresholds | Nothing. This is arithmetic, not evidence | Nothing. It is wrong, not unproven |
| **K-04** | Four price-pattern entries (spread narrowing, stale quote, volume spike, drift from open) | **148 price-pattern strategies on 909 baseball games returned 0 positive** (`LEDGER` BH002) | Price patterns on NON-baseball families; price patterns at the extremes (above 90c) where the fee collapses; patterns over days rather than within a day | A price-pattern test on a family and a price band BH002 never covered, pre-registered first |
| **K-05** | Home-plate umpire strike zone → strikeouts and totals (`SF215`) | **Officials absent on 57 of 57 scheduled games**, including with the API's own `hydrate=officials`; the same field fills the moment a game goes final | **Whether any OTHER free source publishes crew assignments the day before.** I checked one API and nothing else | A free pre-game source for umpire assignments. This is the most likely row here to come back |
| **K-06** | Catcher framing → totals (`SF216`) | Fails on arithmetic before it is run: 0.08 runs is about **0.7c** against a measured **1.32c** cost bar | The **tail** — the handful of games with an extreme framing gap, which is where the whole effect would have to live; and framing on the strikeout market, which is cheaper and more directly affected | A framing measure whose top decile is worth more than 2c, tested on `KXMLBKS` rather than totals |
| **K-07** | **TAKING Kalshi parlays (combos)** | **Median markup +6.6% over the product of the legs' own pre-game asks**, on 5,230 settled combos, against a pre-registered kill threshold of 3%. Plus a fee of **6.7% of the money staked**. Real settled outcomes: **−49 per 100 risked**, against −38 for the same legs | **QUOTING into other people's requests — the opposite side of exactly this trade, and it is untouched.** Also: combos whose legs are not sports (41,960 of them), combos with NO legs (6,035), and every combo before 18 Aug where our own price tape does not reach | A measured markup under 3% on a wider slice, **or** the quoting side being tested, which is a different trade and is NOT killed by this row |
| **K-08** | My own combo recorder, as a duplicate of `devig`'s | Two recorders on one public endpoint is waste, flagged 2026-09-15 | Whether the two tapes AGREE — they were never compared, and mine spans 2026-04-17 onward against `devig`'s 08-06 | **ALREADY BACK.** Reinstated 2026-09-18: mine holds **20,534,685 combos back to April**, most of which Kalshi has since deleted, so stopping it would have destroyed history rather than saved effort. **This row is the kill pile working** |

---

## Two things in here that are NOT kills, and must not be read as kills

**`UNTESTABLE` is a verdict about the test, never about the idea** — `GUARDS.md`
#21. These belong in POSSIBLY GOOD in `BUCKETS.md`, not here:

- **Entertainment and Financials, on the invert screen.** The screen flagged
  both as possibly worth taking the other side of, and both died on **1 event
  and 45 events** respectively. That is a sample size, not a finding.
- **`SF215`, the umpire**, is in this pile as **unmeasurable from statsapi** —
  a much narrower sentence than "no edge there", and K-05 records exactly what
  would reopen it.

## What this file is for

The next BROAD pass reads the "what was NOT tested" column first. That is the
whole mechanism: **a kill triggers a widen, not a stop.**
