To: mlb
From: coordinator
Opened: 2026-08-20 00:40
Status: OPEN
Subject: LONG TASK - settle the lineup bot, then his take-profit and stop-loss grid

--- INSTRUCTION ---

**LONG TASK. Two jobs, in this order. Mailbox 018 is still open and is job one.**

# JOB 1 — `lineup` has never fired. Settle it. (018)

Three of sixteen slots, 13 days, 2,382 declines, zero entries. **Say which it is
— threshold set impossibly high, or genuinely rare — with the actual number and
how many absences would have been needed to trigger one entry.** Then either fix
it or state up front how many games it needs before it can say anything.

**Same treatment for `park-air`:** 5 entries in 13 days. Its per-contract figure
must never appear without that count beside it.

# JOB 2 — HIS TAKE-PROFIT AND STOP-LOSS IDEA, in his own words

> *"is there a version of this exact same bot that instead of holding, has take
> profit and stop loss... at a bunch of different percentages, and see which
> ones make the most money"*

**Pre-register first: `PREREGISTRATION_EXITGRID.md`, committed before any
result.**

**Prior work, with the five fields, and it does NOT settle this:** you already
run `hold`, `exit-once` and `free` — +7.8%, +7.7%, +7.4% over 81 settled bets,
2026-08-08 to 2026-08-19, one observation per game. **How his differs: nobody has
stated what threshold `exit-once` actually uses, and he is asking for a SWEEP of
levels rather than one setting. State plainly what those three modes do before
claiming they cover it.**

**The grid:** take-profit at a range of levels, stop-loss at a range of levels,
and both together. **On the rescued tape, real bid and ask, real exit fees.**

**⚠ And the warning that must be in the report, not just in your head:** a grid
of levels is the best-of-N problem in its purest form. **Try 50 combinations and
the best will look good even if no level works.** Report how many cells were
tried beside any winner, include a placebo arm, and state that no cell means
anything until it runs forward.

**Also answer, because he asked and it is cheap:** the arithmetic of cashing out
a near-certain position early. He noticed a bet showing $5.87 to sell against
$6.00 held. **The price is the probability — so the gap is the fee and spread
paid to leave early, roughly 1-2% every time.** Confirm or correct that from the
tape.

# WHAT NOT TO DO

**Do not propose a three-tier sizing rule** off the opposite/alone split in 018.
Pre-register a count and a date; leave the live rule alone.

**Also: your `COORDINATOR-STATE` says 71 games settled and asks him to run
`install_task.ps1`. He ran it tonight — it is installed and verified. Update it.**

**Run for hours. Do not stop to report progress.**

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

