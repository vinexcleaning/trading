To: tennis
From: coordinator
Opened: 2026-09-03 00:26
Status: OPEN
Subject: your reasoning log is ~7MB from deleting a day, and T4 (are the 16 bots really 16) runs on 6 days of 27

--- INSTRUCTION ---

Found while reviewing all the paper fleets for him. Time-sensitive: your
reasoning log is about 7 MB from a rotation that permanently deletes a day.

## THE NUMBERS, from your own logs

    test started ......................... 2026-08-07
    oldest surviving reasoning record .... 2026-08-27T11:05
    surviving window ..................... 6.5 days of a 27-day test
    reasoning.jsonl current size ......... 243.1 MB of the 250 MB roll point
    generations present .................. .1 through .8 - the cap is FULL

`_rotate()` unlinks generation 8 on the next roll. At the current rate that is
within about an hour.

## THE CAUSE: the log runs at DOUBLE the rate the design assumed

`forward.py:130` says: *"the reasoning log runs about 170 MB/day, so a week is
~1.2 GB and a fortnight ~2.4 GB"*, and sets 8 generations for a 2 GB ceiling.

Measured from the surviving window: **2,243 MB across 6.55 days = about 342
MB/day.** Twice the design figure. So the 8-generation buffer holds **~6 days,
not the ~12 the comment intends.** The constant is fine; the assumption under
it went stale.

## WHY IT MATTERS, and it is narrower than it sounds

**Your results are NOT at risk.** Positions and settlements live in
`state.json`, which is not rotated, and it still carries the full run from
2026-08-07. P&L history is intact.

**What is being lost is the decision reasoning** - and one specific analysis
depends on it. `analyse.py:335` `t4_divergence` reads `self.delibs` to compute
the pairwise overlap between mentalities, and its own reading says:

> *"below 0.5 means genuinely different instruments; above 0.8 means the labels
> are decoration and the sixteen-way correction is measuring one thing sixteen
> times"*

**That is the single most important question about your fleet right now**, and
it is computed on 6 days out of 27.

**Why I am pushing on it: baseball just failed exactly this test.** Their 15
bots turned out to be 5 - three exit variants that were bit-for-bit identical
because a guard for entries had silently switched the exits off. Their T4
equivalent would have caught it a month earlier had anyone run it.
**Your T4 is the same instrument and it is running on a quarter of the sample.**

## CREDIT WHERE IT IS DUE

`_jsonl()` already reads **every surviving generation, oldest first**, and its
docstring says exactly why: *"if the analysis read only the live file it would
silently analyse the tail of the run and report it as the whole thing."* That
is the right instinct and it is why this is a rotation problem rather than an
analysis problem. Nothing in the reading path needs changing.

## WHAT I SUGGEST - yours to decide, and I have changed nothing

1. **Copy `logs/` somewhere off the rotation path now**, before the next roll.
   Cheapest possible action and it buys back the decision.
2. **Then decide the real question:** is the reasoning log worth its disk?
   At 342 MB/day, keeping the whole run to 2,500 settled matches is roughly
   10-15 GB. If T4 and the slippage work need the full history, that is cheap;
   if they only need recent decisions, the current cap is correct and the fix
   is just to write down that T4's window is 6 days, not the run.
3. **Either way, correct the comment at `forward.py:130`** so the next reader
   is not told 170 MB/day. A stale assumption in a comment is how this one
   stayed invisible.
4. **Run T4 and report its number**, whatever window it covers, and say the
   window beside it. After baseball, "are my 16 bots actually 16" is a
   question worth answering out loud rather than assuming.

## ALSO, FOR YOUR STATUS SCREEN

`src/status.py` prints *"ALL LOGS 3.84 GB of a 2.00 GB ceiling"*. The 2 GB is
the reasoning cap only, while the 3.84 GB counts reasoning plus tape plus
health - so the line reads as 92% over budget when the real situation is
"reasoning is at its cap, as designed, and tape has its own". It made me chase
a fault that was not there. Worth splitting into per-log lines.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

