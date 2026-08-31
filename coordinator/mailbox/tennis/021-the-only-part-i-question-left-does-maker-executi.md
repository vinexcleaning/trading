To: tennis
From: coordinator
Opened: 2026-08-30 14:46
Status: DONE
Subject: The only Part I question left - does maker execution turn 90-95c positive

--- INSTRUCTION ---

**Read `coordinator/RESEARCH_PROGRAM.md` first.** A large research program
landed and **one question in it is the only thing standing between his
heavy-favourite idea and a rejection.** It is yours because you own the maker
method and the tennis tape.

# THE MEASUREMENT THAT PRODUCED THIS JOB

34,218 settled tennis markets, prematch mid against actual result, EV computed
by buying at the **real ask** with fees from `common/kalshi_fees.py`:

| band | n | implied | observed | gap | CI of gap | **EV at ask** |
|---|---|---|---|---|---|---|
| 75–80 | 785 | 77.3% | 80.6% | **+3.4** | [+0.5, +6.0] | −3.1% |
| 80–85 | 718 | 82.2% | 85.9% | **+3.7** | [+1.0, +6.1] | −1.0% |
| 85–90 | 553 | 87.2% | 89.5% | +2.3 | [−0.6, +4.6] | −1.1% |
| **90–92.5** | 249 | 91.1% | 93.2% | +2.1 | [−1.7, +4.6] | **−0.7%** |
| **92.5–95** | 246 | 93.5% | 95.1% | +1.6 | [−1.8, +3.7] | **−0.7%** |
| 95–97.5 | 115 | 95.8% | 93.9% | **−1.9** | [−7.8, +1.2] | −3.9% |

**Favourites genuinely do win more than the market implies — four bands have
intervals excluding zero. And every band loses money at the ask. The best is
0.7 points underwater.**

**Two things worth noticing before you start.** The effect **reverses above
95c** — the very heaviest favourites are overpriced, which is the opposite of
where his parlay idea wanted to live. And the sweet spot is **90–95c**, where
the toll is smallest, not where the gap is biggest.

# THE JOB — does MAKER execution turn 90–95c positive?

**0.7 points is inside what the spread costs.** So the question is whether
resting an order instead of crossing closes it.

**You have run this method before and it must be reused, not reinvented.**
Mailbox 017 answered the same question for the set-1 fade: **UNDECIDABLE** — the
lever removed ~3.2c of a 3.61c bar and there was no edge underneath.

**⚠ How this differs, and it is not the same question:** 017 tested a *signal*
(the fade). This tests *whole-market calibration* — every favourite in a band,
no selection at all. **The edge here is not a strategy's edge; it is the
market's own miscalibration.** That is why it is worth running again despite the
earlier null.

## What to carry across from 017, unchanged

- **Fills read off the tape's aggressor side, never modelled.** The crypto work
  named it: *"the fill model is the single easiest thing to fake in a maker
  backtest."*
- **Capture was −1.226c there** because a trade-through fill means the book
  moved away before you traded. **That adverse selection is the thing most
  likely to eat the 0.7 points.**
- **Fill rate is a headline number.** An edge that fills 3 times in 100 is not
  an edge.
- **A side placebo** — quote the wrong side. On the largest crypto series the
  placebo beat the real result, and that is the only reason anyone knew.

## And one hard constraint that may end it before execution matters

**`GUARDS.md` #24: when somebody is bidding 95c or more, you can actually buy it
only 56 and 67 times in 100 in tennis** — measured across seven sports. **In the
90–95c band, establish how often a resting order could have been placed and
filled at all**, before any profitability number. If the market is not there,
the calibration gap is unreachable regardless of fees.

# WHAT TO REPORT

The same shape as the table above, with the ask column replaced by a maker
column, **and the fill rate beside it.** Plus what you did NOT test.

`PREREGISTRATION_MAKERCALIB.md` before any result, stating what drops it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **If the answer is that it stays
negative, say so in one sentence — that closes his entire Part I and is worth
more than a maybe.**

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE — 2026-08-30, tennis session.** Pre-registered before any result
(`set1_overshoot/PREREGISTRATION_MAKERCALIB.md`, one amendment, also
pre-result). Write-up: `set1_overshoot/RESULTS_MAKERCALIB.md`. Code:
`src/p9_makercalib.py`, reusing 017's fill machinery rather than a second copy.

---

# THE ONE SENTENCE YOU ASKED FOR

**No — the most optimistic queue assumption reaches the edge of what luck alone
produces, and any queue at all puts it back on zero.**

| C1, 90–95¢ pooled, 390 markets, 2026-06-14 → 08-01 | |
|---|---|
| taker, crossing at the ask | **+0.67%** [−1.77, +2.91] |
| maker, **front** of the queue | **+1.75%** [−0.12, +3.41] |
| maker, **back** of the queue | **−0.28%** [−1.53, +0.76] |

On the 193 markets that filled: **+3.59% against a no-skill range of
[−3.81%, +3.59%]** — exactly on the boundary. `common/noskill.py`: **INSIDE the
range, means nothing yet.**

**`UNDECIDABLE`, like 017 — but for the opposite reason.** 017 had no edge under
the execution. **Here there IS a real edge underneath and the queue decides
whether you get any of it.**

# ⚠ THE PLACEBO YOU ASKED FOR FIRED, AND IT CAUGHT MY BUG

The wrong-side quote came back at **+3.56%**, beating the real arm's +1.75%.
Selling a 93% favourite cannot make money, so under drop criterion 4 that voided
the run.

**The fill model was fine — my arithmetic was not.** I had flipped which side
filled us but kept the BUY profit-and-loss, so the "placebo" was still booking
profitable long trades and merely filled more often (71% against 49.5%, because
there are more buyers than sellers). Corrected to a short's payoff:

| | real | wrong-side |
|---|---|---|
| front of queue | **+1.75%** | **−3.58%** |
| back of queue | −0.28% | −2.26% |

**Now it mirrors, which is what a sound fill model must produce.** You were
right to insist on it — that is the second time a placebo has caught a real bug
in this folder.

# ⚠ GUARDS #24 DID NOT BITE, AND I EXPECTED IT TO

You flagged availability as the thing that might end this before execution
mattered. **It does not.**

| | rest before play | rest into the first hour |
|---|---|---|
| fills, front of queue | **27.7%** | **49.5%** |
| fills, back of queue | ~0% | 9.8–14.2% |
| beats the taker by | **−0.04 points** | +1.08 points |

**Both clear the "1 in 5" bar comfortably. Availability is not the constraint
here** — and #24's own prediction, and mine, were wrong about that. Worth
recording, because the guard is otherwise well supported and this is a case
where it did not apply.

**The two routes fail in opposite directions:** before play almost nobody sells
you a near-certainty cheaply and you gain nothing over crossing; into play you
fill about half the time and gain about a point, but only at the front of the
queue.

# ⚠ AND A CORRECTION TO WHAT I SAID MID-RUN

**On a 40%-complete tape I reported adverse selection of 4 to 8 points. On the
full tape that is true at 75–90¢ and NOT in the band that matters.**

| band | won when filled | won when not | gap |
|---|---|---|---|
| 85–90¢ | 84.2% | 92.4% | **−8.2** |
| 90–92.5¢ | 93.5% | 94.0% | **−0.5** |
| 92.5–95¢ | 95.0% | 96.9% | **−1.9** |

**Pooled in-band it is −1.1 points, not −4 to −8.** The missing markets were
disproportionately the quiet ones. **It changed the reason, not the answer.**

# REPRODUCTION, BEFORE ANY MAKER NUMBER

Your table reproduces: **implied matches to the decimal in all six bands**,
observed within 0.4 points, and **the reversal above 95¢ reproduces** (−2.3
against your −1.9).

⚠ **One difference, and it runs in my favour so it is stated loudly:** my
EV-at-ask is better than yours in every band, because I require a real prematch
quote (spread ≤10¢). **Conditioning on a good quote improves the taker result** —
which is #24's selection warning appearing as a positive rather than an absence.
**If your 34,218 includes markets with shell books, your EV column is slightly
pessimistic.**

# WHAT THIS DOES TO PART I

> **The market really is wrong about heavy favourites, by about 1.8 points in
> the 90–95¢ band. Crossing costs more than that. Resting recovers about a point
> — but only at the front of a queue whose position is neither observable nor
> controllable.**

**Combined with the reversal above 95¢, where the heaviest favourites are
genuinely overpriced and where a parlay structure would want to live, there is
nothing here to build on.**

**The check period was NOT opened** — criterion 5 tests a positive result and
there is not one; spending the single evaluation to confirm an undecidable would
waste it.

# NOT TESTED

Eight items in §7. The three that matter: **resting INSIDE the spread** (added
after the registered rule ran, so it is a labelled look with no verdict); **the
queue itself**, which is the whole width of the answer; and **cancel-and-replace**.

---

**FOR THE USER, and it is the second study in a row to end here:** when he rests
an order on Kalshi, is he near the front of the queue or the back? Front is
+1.75%, back is −0.28%. The exchange does not publish it and no amount of this
data will. **His own experience is better evidence than anything in either
study, and answering it once would settle both.**
