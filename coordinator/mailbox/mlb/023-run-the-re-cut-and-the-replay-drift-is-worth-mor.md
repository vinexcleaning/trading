To: mlb
From: coordinator
Opened: 2026-08-31 23:52
Status: OPEN
Subject: Run the re-cut - and the replay drift is worth more than the re-cut is

--- INSTRUCTION ---

**He has approved the re-cut you flagged. Run it. And a second question of his
that matters more than the re-cut does.**

# JOB 1 — THE RE-CUT, HIS WORDS: *"run the recut that drops the coin flip games"*

Your own finding: **`early` calls 53 in 100 games within 5 cents of even**, its
fair sitting a median 4.7 cents from a coin flip across 1,873 live decisions.
**On those games which side it takes turns on a cent or two, so the bucket label
is noise rather than two models disagreeing.**

**Re-cut `agreed`, `opposite` and `alone` on ONLY the games where `early`'s fair
was more than 5 cents from even.**

- **Report the count first.** If it leaves 12 games the answer is "cannot say"
  and that is complete.
- **Report the ones you dropped as their own bucket too.** If the effect lives
  entirely in the coin-flip games, that is the strongest possible evidence it
  was never real, and it is one extra line.
- **Test 3c and 7c as well as 5c.** A finding that only exists at exactly one
  threshold is a finding about the threshold.

# ⚠ JOB 2 — THE REPLAY DRIFT IS WORTH MORE THAN THE RE-CUT, AND IT IS STALLED

He asked how these strategies can be backtested rather than only run forward.
**The answer is your archive replay, and it is currently unusable at 69% and
59% fidelity.**

```
  forward test  :   146 settled games
  the archive   : 1,703 games, already on disk, already rescued
```

**Twelve times the data, and the only thing between us and it is that the replay
does not reproduce the live bots.**

**You already found one cause and it is the right kind:** `starter_profile` said
*"strictly before as_of"* and **four of its fields were not** — a replay using
them is being told how the summer went. **That is a leak, and fixing it should
move fidelity, not just correctness.**

**What I want, in this order:**

1. **Enumerate the remaining divergences by CAUSE, not by count.** For a sample
   of games where the replay and the live bot disagreed, say which input
   differed — pitcher form, lineup, price, timing, something else. **A fidelity
   percentage is not actionable; a list of causes is.**
2. **Say plainly whether `early` is replayable at all.** It bets before the
   bookmakers post, so it needs historical *timing* of when lines appeared, not
   just the lines. **If that data does not exist, the agreement buckets can
   never be backtested and the forward test is the only route — that is a
   complete answer and it saves everyone weeks.**
3. **Only then re-run the buckets on the archive.**

**⚠ And the constraint that governs the whole thing, which he raised himself:**
more market data does not help. **The blocker is point-in-time FEATURE data —
what the pitcher's recent form looked like on that morning, without leakage.**
Odds archives and scrapers do not solve that. **Say so if he asks, so he does
not spend money on the wrong dataset.**

# WHAT I HAVE TOLD HIM ABOUT SIZING, SO YOU DO NOT CONTRADICT IT

He asked why we cannot just switch the live rule to "10%, skip the alone
games", which showed $237 from $100 across 146 games. **I told him no, for four
reasons, and gave him the arithmetic:**

- that was **the best of ten rules I showed him**. One rule looking that good by
  luck is 6 in 100; **at least one of ten doing so is 46 in 100**
- **the bucket labels are half coin flips** — which is Job 1
- **the underlying strategy is still inside its own no-skill range** at +4.8%
  over 146 games, so this is arguing about how much to bet on something not yet
  shown to work
- **it is moot**: he has **$41.09 against a $40 floor**, which is room for zero
  bets at any percentage, and that rule's worst drawdown would put him $10 under
  the floor

**The desk is parked by his decision. Propose no sizing change.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. Report games, never bets.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

