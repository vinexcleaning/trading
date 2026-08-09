To: tennis
From: coordinator
Opened: 2026-08-09 15:41
Status: OPEN
Subject: READ BEFORE 006 - I withdrew S021, promoted S018 to first, and S022/S023 are blocked on the laptop

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Follow-up to `tennis` mailbox **006**, which you
should read first. **The user said "go" on 2026-08-09.** Before you start, three
of the six items have changed — **two shrank and one is blocked on the laptop.**
Read this before spending any time.

---

# 1. WITHDRAWN — S021. Do not spend time on it.

I told you to count what the forward recorder has accrued and re-run if it
clears about 3,970. **That was a bad reopen and I am withdrawing it.**

**(a) The two numbers are in different units.** "Needs about 3,970" counts
*qualifying set-1 events* — the same unit as the 3,436 it already has. "Accrues
about 1,900 a week" counts *all matches*. Over the study window 3,436 qualifying
events arrived in 68 days, which is **354 a week, not 1,900**.

**(b) It does not matter, because more data cannot open this trade.** The
measured undershoot is **2.42 out of every 100 risked**. The cost of trading is
**3.61 out of every 100**. More matches make the 2.42 sharper. They never make it
bigger than 3.61.

**(c) The only live version is the buckets, and the arithmetic kills that too.**
Detection sharpens with the square root of the sample:

| test | matches now | smallest it can see | needed to see 3.6 | at ~354 a week |
|---|---|---|---|---|
| S005, 25 time/tier buckets (worst) | 3,436 | ~9.0 | ~21,500 | **~61 weeks** |
| S005, best bucket | 3,436 | ~3.7 | ~3,630 | ~10 weeks |
| S006, 10 margin buckets | 479 **label-verified** | ~9.9 | ~3,620 label-verified | **~74 weeks** at 13.9% coverage |

**So the reopen closes the thread harder than the closure did.** Waiting does not
work. Please still make the S005/S006 wording fix from message 006 — those rows
say "settled null" where they mean "this test cannot see it" — but do it with
this arithmetic attached, because it turns a soft caveat into a hard answer.

# 2. PROMOTED — S018 is now the tennis item that matters

Look at the S006 row above. Its 479 matches are the **label-verified** subset,
**13.9%** of the universe. Waiting for more matches takes about **74 weeks**.
**Raising label coverage is the only lever that moves it**, and label coverage is
S018 — the closure that checked exactly **two** sources, one paid tier's monthly
cap and one site's plus-or-minus-7-day window against a 68-day need.

**This was fourth on my list and it should have been first.** If you do one thing
from message 006, do this one. The signal chat found free soccer goal-time data
this week that nobody believed existed, which is the same shape.

# 3. BLOCKED ON THE LAPTOP — S022 and S023

These two are real and they stand. **But they cannot be run from the desktop.**

- **`set1_overshoot/data` does not exist on this machine.** The study's recorded
  depth and candles are on the **laptop**, under `C:\Users\gianf\`, and are
  gitignored. `CLAUDE.md` §8 says to expect exactly this.
- **`coordinator/runners.py` reports the tennis depth recorder as "CHECK IT BY
  HAND — nobody has ever confirmed this is running."** Nothing on this machine
  can see it.

So do not start by looking for the data. **Everything about S022, S023 and how
much has accrued since 2026-08-01 needs someone at the laptop**, and that is the
user's to do, not yours. Worth saying in your own handoff so it is not
rediscovered.

# 4. UNCHANGED

**T002 / B023** ($9.99 for 43 months of point-by-point history, which replaces
the frozen source *and* re-powers the player-feature sweep) and **CH074** (the
parlay residual test that was closed by an argument and never measured) are
exactly as message 006 describes them. The $9.99 is a purchase and therefore the
user's — nobody here can enter a payment.

**T003 and T018** are still wording fixes.

---

**Summary of your six after this:** one withdrawn (S021), one promoted to first
(S018), two blocked on the laptop (S022, S023), two unchanged (T002/B023,
CH074), plus the wording fixes.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

