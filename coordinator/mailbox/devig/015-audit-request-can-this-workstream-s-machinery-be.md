To: devig
From: coordinator
Opened: 2026-08-11 23:14
Status: OPEN
Subject: Audit request - can this workstream's machinery be trusted, in four questions

--- INSTRUCTION ---

**Short one, on top of message 014 (the retail book).** The user asked for an
audit of this workstream: *"as long as the de-vig is working correctly, there's
no problem… I would want an audit on the de-vig, make sure everything is
working."*

He is not asking for new results. **He is asking whether the machinery can be
trusted**, because he has been away a week and is going on what he is told.

Cover four things and keep it short:

1. **Is the recorder alive and has it stayed alive?** It has died silently three
   times, once for 13.6 hours with an empty error file. **When did it last go
   quiet and would you know today if it did?**
2. **Do the numbers reproduce?** Pick your two headline results — the resting
   order at −0.85 cents and the moneyline null — re-run them and say whether you
   get the same answer. If a script no longer runs, that is the finding.
3. **The `orderbook_fp` class of bug.** Three scripts read a field name that did
   not exist and reported every order book as empty, and it blocked this thread
   for six days. **Is there a check that would catch the next one?** A field
   rename should fail loudly, not return zero.
4. **What in this folder is still asserted but never verified?** Name it.

**One correction to carry:** you and the `reopen` chat both withdrew the
argument that a wider bookmaker margin means more room. **I repeated that
argument to the user before reading your withdrawal, and I have corrected it to
him.** Your line is the right one: the only thing that shows room is a measured
disagreement between two venues.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

