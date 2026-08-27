To: mlb
From: coordinator
Opened: 2026-08-26 21:19
Status: OPEN
Subject: Supplement to 020 - the opposite bucket IS knowable at entry, 8 times in 10

--- INSTRUCTION ---

**Supplement to mailbox 020. He asked the two questions that decide whether the
opposite bucket is tradable at all, and both are now measured. Fold these into
that job rather than treating them as new work.**

# 1. HOW OFTEN IT HAPPENS — it is not a rare bucket

All 114 settled games, classified exactly as the live desk would see them:

| bucket | games | share |
|---|---|---|
| agreed | 26 | **23 in 100** |
| **opposite** | **25** | **22 in 100** |
| alone | 63 | 55 in 100 |

**He suspected `agreed` looked good partly because it fired rarely. It does not
— the two buckets fire at almost the same rate.** So frequency is not the
explanation for the difference between them; the explanation is that `agreed`
reversed out of sample and `opposite` did not. **Tell him that plainly, because
he raised it as a possible artefact and it is not one.**

# 2. ⚠ IS IT KNOWABLE AT ENTRY — yes, 8 times in 10, and this is the decisive one

| | games |
|---|---|
| shared games where the other bot was **already in** when `starter` entered | **51** |
| shared games where it arrived **later** | 9 |
| how much later | median **3.7 hours**, worst 23.5 |
| of those 9 late ones, how many turned out opposite | **6** |

**The 25 opposite games in the result are already the entry-knowable ones** —
the classification in 020 uses only what was visible at the bet timestamp, so
late arrivals were counted as `alone`, not as opposite.

> **So the +32.6% figure is achievable as an ENTRY FILTER. No waiting, no
> mid-position reclassification.** That was the open question and it is closed.

**But there is a real cost hiding in it: 6 further games become opposite only
after entry, a median 3.7 hours later.** Those are currently scored as `alone`.
**Measure what they did.** If late-discovered opposites behave like the
entry-known ones, a rule that waits for the flag captures more of the bucket at
the price of a worse fill — and that trade-off is measurable rather than
arguable. **If they behave differently, then "opposite discovered late" is a
different animal and must not be pooled with the other 25.**

# 3. WHAT TO ADD TO THE 020 JOB

- **Report the bucket frequency alongside every return.** A 22-in-100 bucket at
  +32% is a different proposition from a 3-in-100 bucket at +32%, and only one
  of them can carry money.
- **Split `opposite` into entry-known and late-discovered** and report both. Do
  not pool them until they are shown to behave the same.
- **For the late-discovered six: how far had the price moved between `starter`'s
  entry and the moment the flag became true?** He assumes prices drift only a
  few points before first pitch. **Check it against the tape rather than
  accepting it** — if it is small, waiting is cheap; if it is not, the late
  bucket is untradeable and should be said so.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. Report games, never bets.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

