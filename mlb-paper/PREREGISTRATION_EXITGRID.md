# Pre-registration — the take-profit and stop-loss grid

**Written 2026-08-20, BEFORE any grid result exists.** His idea, via mailbox 019.
Registered under `CLAUDE.md` §10.

## His idea, in his words

> *"is there a version of this exact same bot that instead of holding, has take
> profit and stop loss... at a bunch of different percentages, and see which
> ones make the most money"*

## What the existing three arms actually do — stated plainly, because it has never been written down

- **`hold`** — never exits. Buys, waits for the game to settle at 100 or 0.
- **`exit-once`** — exits if the price moves **12 cents in either direction**.
  Take-profit and stop-loss are the **same number**, deliberately, so the arm is
  not secretly a directional bet. One entry per game.
- **`free`** — same ±12 cents, but allowed **two** entries per game.

**So the repo has tested exactly ONE level, 12 cents, and never said so.** Over
81 settled bets, 2026-08-08 → 08-19: hold **+7.8%**, exit-once **+7.7%**, free
**+7.4%** — indistinguishable. **That does not answer his question**, which is
about a *sweep*, and about take-profit and stop-loss being allowed to differ.

## The hypothesis

**Some combination of take-profit and stop-loss beats holding to settlement.**

## Unit of observation

**One game.** A market settles once.

## Sample and dates

Every settled position from the forward test, 2026-08-07 → 08-20. Prices from
the re-pulled Kalshi tape at **1-minute resolution** — real bid and real ask,
not the mid. Exit fees from `common/kalshi_fees.py` and nowhere else.

⚠ **A position held to settlement pays ONE fee. Any exit pays TWO.** That is not
a detail; it is the reason `hold` starts ahead and it must not be quietly
reversed by the grid's accounting.

## The grid, fixed NOW so the count cannot grow after seeing results

Take-profit ∈ {4, 6, 8, 10, 12, 15, 20, 25, never}
Stop-loss ∈ {4, 6, 8, 10, 12, 15, 20, 25, never}

**81 cells. That number is registered before looking.** The (never, never) cell
is `hold` and is the benchmark.

## ⚠ What this design CANNOT tell us, registered up front

**This is the best-of-N problem in its purest form.** With 81 cells, the best
one will look good **even if no level works at all**. So:

- **The winning cell's number is not evidence.** It is the maximum of 81 draws.
- What IS evidence: whether the **surface is smooth** (neighbouring levels agree,
  which suggests a real effect) or **spiky** (the winner's neighbours disagree,
  which is the signature of noise).
- **Placebo arm:** exit at a RANDOM minute, at the same rate the winning cell
  exits. If random exiting does as well, the threshold carries nothing.

## What result makes us DROP the idea

Registered before looking, any ONE of these is fatal:

- **The (never, never) cell — plain holding — is at or near the top.**
- **The random-exit placebo matches the best cell.**
- **The surface is spiky:** the best cell's immediate neighbours are much worse.
  A real effect does not switch off between 10 cents and 12.
- **The best cell beats holding by less than the spread it pays to exit.**

## What would make me DOUBT a positive result

Every exit pays a second fee and crosses the spread again. If a cell wins, the
first thing to check is whether it wins **because** it exits rarely — in which
case it is `hold` wearing a costume, and the win is noise on the few games where
it did fire.

## Prior work, and how his differs — all five fields (`CLAUDE.md` §2)

1. **What was tested:** `hold` vs `exit-once` vs `free`.
2. **The data:** 81 settled bets, one observation per game.
3. **Dates:** 2026-08-08 → 2026-08-19.
4. **Result:** +7.8% / +7.7% / +7.4%. Not retracted.
5. **How his differs:** those are **one threshold (12c), symmetric**. He is
   asking for a **sweep** with take-profit and stop-loss **allowed to differ**.
   **Nothing in this repo has tested that.**

Related and NOT the same question: his in-play bot's stop-and-re-enter
(−2.29¢ → −9.36¢) and the copy-trading bot's stop-outs (8 of 9 recovered). Both
fire on a **price move inside a live game**; this grid fires on a price move on
a **pre-match position**. The `CLAUDE.md` §9c rule applies — where the loss has
a floor, a stop tends to hurt. **This test is expected to confirm that, and the
expectation is registered here so a null is not later dressed up as a surprise.**
