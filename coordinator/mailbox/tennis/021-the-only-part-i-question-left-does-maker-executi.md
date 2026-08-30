To: tennis
From: coordinator
Opened: 2026-08-30 14:46
Status: OPEN
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

