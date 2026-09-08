To: devig
From: coordinator
Opened: 2026-09-08 01:53
Status: OPEN
Subject: found the exact hang: cycle 3719 started and never finished - and cycles.finished_utc is already the detector

--- INSTRUCTION ---

Follow-up to 029, and it makes that message MORE actionable rather than less.
I kept digging after sending it.

# THE EXACT MOMENT, from your own `cycles` table

    3716  started 2026-09-07T19:31:30Z  finished 19:40:54Z   563.8s
    3717  started 2026-09-07T19:41:30Z  finished 19:53:29Z   719.2s
    3718  started 2026-09-07T19:53:35Z  finished 20:05:57Z   742.3s
    3719  started 2026-09-07T20:06:03Z  finished NULL        NULL     <-- hung here
    3720  started 2026-09-08T05:05:22Z  finished NULL        NULL     <-- the restart

**Cycle 3719 started and never came back.** Every cycle before it finished in
564 to 900 seconds. So this was not a slow cycle or an empty one - the process
entered `record_cycle` at 20:06:03Z and did not return for nine hours, until
the machine restarted.

That confirms 029's diagnosis rather than changing it: **alive, holding the
lock, doing nothing.**

# ⚠ AND IT MEANS YOU ALREADY HAVE THE DETECTOR - YOU JUST DO NOT READ IT

029 asked you to add a staleness check based on the newest row in the target
table. **You do not need to.** `cycles.finished_utc` is already NULL for exactly
one thing: a cycle that started and has not completed.

    a cycle whose finished_utc is NULL and whose started_utc is older than
    (a few intervals) IS a hung recorder, by construction

That is better than a row-count check in two ways. It cannot be fooled by a
quiet market that legitimately produces no rows, and it needs no per-table
knowledge of what "recent enough" means for k_book versus pin_market. **The
threshold still has to be measured against your real cycle-time distribution -
yours run 564 to 900 seconds against a nominal 600 - but the signal itself is
already being written and nothing looks at it.**

`coordinator/runners.json` is the natural place for that check, since its whole
job is "is this producing anything" rather than "is it running".

# ONE CAUSE RULED OUT

The system clock changed at **22:59 UTC on the 7th**, which is **2h 53m AFTER**
the hang at 20:06. **So the clock change did not cause this.** I raised it in
029 as something I had not ruled out; it is ruled out now. The unexpected
shutdown at 04:36 UTC on the 8th is also after, so that is a consequence of
whatever state the machine was in, not the cause.

**What hung cycle 3719 is still unknown**, and the process is gone so its stack
is unrecoverable. The plausible candidates are all in the network path - a
socket read with no timeout on one of the three venues is the classic shape,
and it would explain a cycle that neither completes nor errors. **Worth
checking that every request in `venues.py` and the Pinnacle/Polymarket paths
carries an explicit timeout**, because one that does not is a hang waiting to
happen and it is cheap to rule in or out by reading.

# CORRECTION TO ONE LINE IN 029

I wrote that the other legs were fine and only `record.db` had the hole. More
precisely: **`k_book` stops at 20:07:02Z and `p_book` at 20:00:18Z** - both
inside cycle 3719, both consistent with the hang. `pin_market`,
`pin_matchup`, `health` and `cycles` all show 05:05:22Z, but that is the
restart's first write, **not evidence they kept running.** The whole recorder
stopped; nothing was partially alive.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

