# PREREGISTRATION_COMEBACK.md

**Written 2026-08-09, before any comeback rate existed.** The goal-minute
download was still running when this was committed; the descriptive table had
never been built on the real data. That timing is the point — a pre-registration
written after seeing the numbers is a description of the numbers.

Check it against the git log. If this file's first commit is later than the
first commit containing `reports/comeback_table.txt`, **it is worthless and
should be treated as such.**

---

## The idea, in one sentence

Late in a match one team is ahead; you bet against the team that is behind,
which pays if the leader wins or if it finishes level, and the whole bet is the
question of how often the trailing team comes back and wins.

## Why this file is not about the table

**The descriptive table is not a test and is not pre-registered.** It is a
lookup: every minute, every scoreline, every strength pairing, every
competition, with the number of matches behind each cell. It nominates nothing.

The test is what happens *after* a human reads that table and picks a pocket
using football knowledge that is not in this repo. That choice is the user's,
it is the point of the exercise, and it is also **exactly the moment the whole
thing becomes vulnerable to picking the prettiest cell out of thousands**. This
file is the constraint on what happens next.

---

## The hypothesis, stated so it can fail

For the state the user picks — a minute, a scoreline, a strength pairing, and a
set of competitions — **the trailing team comes back and wins less often than
the price implies**, by enough to survive the fee and the spread.

## The unit of observation

**One match.** Not one minute, not one market, not one contract.

A match passes through many minutes and appears in many cells. Cells are
therefore heavily correlated and per-cell counts must never be summed as if they
were independent matches. Any number reported from this test is a count of
matches.

## The sample and the date range

- **Held-out period: 2025-01-01 onward.** Nothing in it has been looked at. The
  descriptive table is built strictly on 2015-01-01 → 2024-12-31.
- The test runs on matches in the held-out period **only**, in the competitions
  the chosen pocket names.
- Source: ESPN goal timelines, the same pipeline as the table, no re-fetch and
  no re-definition.

**Matches burned and excluded from the holdout in advance:** any match whose
Kalshi price was inspected by `src/price_at_state.py`, which reads recent
matches inside Kalshi's ~69-day window. That list is `data/price_at_state.json`
and those event ids are excluded from the test set. Looking at a price is not
looking at an outcome, but it is cheaper to exclude them than to argue about it.

## What gets measured

1. **The comeback rate in the held-out period**, out of 100 matches, with the
   range it could really be.
2. **The naive benchmark next to it**: the comeback rate for the same minute and
   scoreline with the strength dimension collapsed. If the pocket is no better
   than "one goal up at 80 minutes, anybody, anywhere", the strength dimension
   bought nothing and the pocket is not real.
3. **The rate the price actually needs**, computed from `common/kalshi_fees.py`
   at the price observed, paying the ask, held to settlement.

## What result makes me drop the idea

**This is the section that usually gets left out, so it is the specific one.**
Any single one of these kills it. No partial credit, no re-slicing afterwards.

1. **The held-out comeback rate is at or above the break-even rate for the price
   actually available.** At 97 cents that break-even is 2.80 in 100. If the
   held-out rate reaches it, the bet loses money and the idea is dead.
2. **The range the held-out rate could really be includes the break-even rate.**
   Not "the middle looks good". If the range touches break-even, the test was
   too small to have answered the question, and the answer is "we do not know",
   which is a stop and not a maybe.
3. **The pocket does not beat the naive benchmark on held-out data.** If
   collapsing the strength dimension gives the same answer, the pocket is a
   slice of a general fact and there is nothing here that needed the table.
4. **The held-out rate is materially worse than the descriptive years.** A
   pocket that only exists before 2025 is a pocket that existed in the search,
   not in football.
5. **Fewer than 200 held-out matches sit in the pocket.** Below that, at rates
   near 3 in 100, the test cannot distinguish 2 from 5 and reporting either
   would be noise with a decimal point.
6. **The price is not really there.** If the observed cost to actually cross the
   spread, on the matches in the pocket, is worse than the break-even the rate
   clears, it is dead regardless of the football. **This is B024's exact failure
   mode** — an edge that was real on the middle of the market and gone at the
   price you could trade — and it is the most likely way this dies.

## What I am NOT allowed to do after seeing the result

- Re-slice the pocket into a smaller one that works.
- Move the minute, the scoreline, or the competition set.
- Add a dimension that was not in the pocket when it was chosen.
- Test a second pocket on the same held-out data and report the better one.
  **One pocket, one test.** A second pocket needs a second pre-registration and
  it does not get the same held-out years.
- Report a result on the descriptive years as though it were evidence.

## What I expect

**No edge.** The user said so himself before any of this started, and he is
probably right — and this repo has produced about 45 recorded corrections, every
one of which shrank an effect and not one of which found a larger one.

Writing that here so that a flat result reads as the expected outcome rather
than as a failure, and so that an exciting result has to get past the fact that
I said this first.

## Paper only

No order-placing code, no credentials, no money, at any stage. Enforced by
`tests/test_paper_only.py`, which walks every file in `src/` and fails on
order-shaped code, a credential, or a non-GET request — and which plants its own
violations to check the detector still bites.
