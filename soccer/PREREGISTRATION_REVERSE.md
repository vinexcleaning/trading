# PREREGISTRATION_REVERSE.md — backing a side to hold on

**Written 2026-09-02, before any 2026 European price outcome was looked at.**
Check the git log: if this file's first commit is later than the first commit of
any result on European domestic prices, it is worthless and should be treated
as such.

---

## What I HAD already seen when writing this, stated so it cannot be claimed later

Being precise, because "pre-registered" is worth nothing if the boundary is
vague:

- **Counts only.** 270 European matches sit inside Kalshi's ~69-day candle
  window; 99 of them are top-five-league domestic (England 20, Spain 31,
  Italy 20, France 19, Germany 9), the rest Champions/Europa qualifying.
- **A yield figure from HISTORICAL football**, not from any price: 22 in 100
  top-five matches have their first goal between the 20th and 35th minute, and
  71 in 100 have it in the first half.
- **A detection floor from the AUGUST soccer prices already reported**
  (SO037): the per-match result has a spread of 7.35 cents, so about 216
  matches are needed to see a 1-cent effect and about 863 to see half a cent.
- **No 2026 European price, and no outcome attached to any price, has been
  looked at.**

## The idea

The comeback idea died because **the market does not quote a near-certainty**
(SO041, GUARDS #24). This is the opposite bet, and that mechanism does not touch
it: **back a side that has just gone one goal up, as a cheap contract**, in the
part of the match where quotes exist a clean 100 times in 100.

## The hypothesis, stated so it can fail

**A side that goes one goal up is underpriced to win**, by more than the fee and
the spread — and **more so when it is a strong side**, because the market moves
roughly the same distance for anyone's goal while the football does not.

## The unit of observation

**One match.** Not one minute, not one quote. A match contributes exactly one
number: the result of a single hypothetical entry.

## The rule, fixed now

- **Entry:** the first goal of the match, scored between the **20th and 45th**
  minute. Read the price **two minutes after** it.
- **Which side:** the team that just went ahead.
- **Price paid:** the **ask**. Never the mid. If there is no ask below 100, the
  match is recorded as **no trade available** and is excluded from the result
  but **reported in the availability count**, per GUARDS #24.
- **Held to settlement.** No stop, no exit rule — the loss is capped at the
  price paid and this repo has measured stops making things worse (§9b).
- **Fee:** `common/kalshi_fees.py`, the repo's only implementation.
- **Outcome:** did that side win in regulation.

**The 20th-to-45th window is chosen NOW and on historical yield alone** — 22 in
100 for 20-35 against 33 in 100 for 20-45 — because the narrower window does not
produce enough matches. Widening it after seeing a result would be a different
thing entirely.

## The sample and the split

- **All European competitions Kalshi lists per-game**, inside the candle window.
- **Strength from domestic form**, and where a side has no reading it goes in an
  "unknown" bucket rather than being guessed or dropped.
- **The years 2025–2026 of FOOTBALL history remain unopened** and are not used
  to build any rate here. This test uses 2026 prices against 2026 outcomes
  directly, which needs no historical rate at all.

## How many matches before it can be judged

**216 matches with a tradeable entry**, from the floor above — the number needed
to see a 1-cent effect. Below that the honest verdict is **"cannot tell"**, and
I expect to reach it: about 99 matches currently have both a price and a
computable strength.

**Reporting "cannot tell" is the expected outcome and is not a failure.** It is
what SO040 did and it is why that row is trusted.

## What result drops the idea

Any one of these. No partial credit, no re-slicing afterwards.

1. **The middle result is at or below zero after the fee** on 216+ matches.
2. **The range it could really be includes zero** on 216+ matches — that is a
   stop, not a maybe.
3. **The strong-side version is no better than the all-sides version.** If
   strength buys nothing, the hypothesis as stated is wrong even if the base
   bet happens to be positive.
4. **Fewer than 216 matches with a tradeable entry.** Then the answer is
   "cannot tell" and the idea is neither alive nor dead — it is unmeasured, and
   saying otherwise is the failure this folder documented four times.
5. **The result depends on the entry window.** It is fixed at 20-45. If it only
   works at some other window, that is a different idea needing its own file.

## What I am not allowed to do afterwards

Move the window · change the price to the mid · add an exit rule · drop a
competition · report the best of several variants. **Every variant tried gets
counted and reported**, because this folder already withdrew a claim for
applying selection discipline in one direction only.

## What I expect

**"Cannot tell", on sample size.** Written down first so that a positive result
has to get past it, and so a flat one reads as expected.

## Paper only

No orders, no credentials, at any stage.

---

# AMENDMENT, 2026-09-02, after the first run — the threshold was built on the wrong number

**The verdict does not change: it was "cannot tell" at 73 matches under the old
threshold and it is still "cannot tell" under the corrected one.** No result
moves. What moves is the bar, and **it moves in the harder direction**, which is
the only direction an amendment like this is allowed to move without being a
retrofit.

**What was wrong.** The 216-match threshold came from a spread of **7.35 cents**.
That was the spread of *expected-value differences* — fair value minus the price
— measured on the August work (SO037). **This test measures realised outcomes:
you win about 30 cents or you lose about 70.** Its actual per-match spread is
**41.9 cents**, nearly six times larger.

**The corrected requirement**, from the 73 matches actually measured:

| to see an edge of | matches needed | at ~60 European matches a week |
|---|---|---|
| 1 cent | **7,022** | about two seasons |
| 2 cents | 1,755 | about seven months |
| 5 cents | **281** | about five weeks |
| 10 cents | 70 | already have it |

**So the live question narrows rather than dying.** The measured range at 73
matches is **−13.76c to +5.46c**, which already **rules out any edge bigger than
about 5½ cents**. What remains possible is an edge somewhere between zero and
about 5 cents, and **281 matches would resolve that** — roughly five more weeks
of European football.

**And an edge of 1 cent — the size this folder actually measures — needs about
7,000 matches, which cannot be assembled from Kalshi's ~69-day window at all.**
That is not a sample-size problem that patience fixes; it is a retention limit.
It needs a recorder running across seasons, and the one that exists has captured
**one snapshot** of European soccer.

**The threshold for any future run of this test is 281 matches, not 216.** The
rule, the entry window, the price basis and the five ways to drop it are all
unchanged.
