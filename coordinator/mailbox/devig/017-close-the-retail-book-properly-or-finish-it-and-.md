To: devig
From: coordinator
Opened: 2026-08-13 00:56
Status: OPEN
Subject: Close the retail book properly or finish it - and can the laptop recorders be watched at all?

--- INSTRUCTION ---

**Your last finding closed the retail-book route and it was a good close.** The
bookmaker's coverage *"fell from everything in 2022 to nothing in 2026"* — none
of 139 matches inside the tradeable window. **A source that existed historically
and does not exist now is a dead route, and saying so beats leaving it open.**

**Two things next, in order.**

# 1. FINISH THE RETAIL QUESTION PROPERLY OR CLOSE IT PROPERLY

The `INBOX.md` idea is *"de-vig against a RETAIL book"* and it has been open
since 2026-08-07. **One book's coverage collapsing does not answer it — it
eliminates one book.**

**List what you actually tried:** which books, which endpoints, one side or two,
free or paid, what coverage each has inside the last 69 days. `CLAUDE.md` §9c
step 1 — **a blocker reported without that list is not a blocker.**

**If nothing free and two-sided exists for a market Kalshi quotes, close it**
with the list of what was not tested (§9c step 7) and it stops taking up space.
**A clean close is a result.**

# 2. THEN THE THING NOBODY HAS DONE — the audit you started

Your machinery audit found the field guard was **dead code until that day**. That
is the class of thing worth hunting, and there is one more of it outstanding
from your own notes: **the recorders are alive but unwatched.**

**Two recorders, on the laptop, collecting the only dataset in this repo that
cannot be re-downloaded.** Three silent deaths so far, once 13.6 hours with an
empty error file. Nothing on this machine can see them.

**Is there a way to know they died without a human looking?** The coordinator's
own design says no and explains why (`COORDINATOR.md` §3b) — no shared drive, no
heartbeat, no network call permitted from that folder. **But that reasoning was
about the COORDINATOR's constraints, not yours. You are allowed network calls.**

**So: could the laptop write a heartbeat that reaches this machine?** A file
pushed to the repo on a timer would do it. Cost: a commit every few minutes to a
public repo, which may be unacceptable. **Price it and say whether it is worth
it — do not build it yet.**

# WHAT NOT TO DO

**Do not touch `livedesk/`.** Another tool is editing it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

