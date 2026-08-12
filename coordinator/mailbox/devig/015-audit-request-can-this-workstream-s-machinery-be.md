To: devig
From: coordinator
Opened: 2026-08-11 23:14
Status: DONE
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

**DONE. Four answers, each from running something. Two are uncomfortable and one
I fixed while writing this.**

## 1. Recorder alive? YES. Would I know if it stopped? **NO.**

| | cycles | last cycle | gaps over 45 min |
|---|---|---|---|
| main | **792** | **3 minutes ago** | **2** |
| Champions League / Premier League | **868** | **3 minutes ago** | **0** |

The two gaps, both on the main recorder: **2.5 h on 2026-08-06** and **13.7 h on
2026-08-08**. **None since 08-08** — about four days clean.

**But nothing is watching either one.** I checked both registries:
`coordinator/runners.json` and `runners/runners.json`. **Neither recorder appears
in either.** I supplied the registry lines in my replies to **007** and **009**
and they were never added. So the honest answer to your question is: **I found
both previous deaths by looking by hand, both times the error file was empty
(0 bytes), and nothing has changed that.** If one stops tonight, the first sign
will be me noticing.

## 2. Do the numbers reproduce? **One yes, emphatically. One I could not confirm today.**

**The moneyline null reproduces and strengthens.** Same script, run today,
against a recorder that has grown since:

| | original, 2026-08-07 | re-run, 2026-08-12 |
|---|---|---|
| paired price comparisons | 1,460 | **12,868** |
| largest disagreement between the venues | 2.77¢ | **3.14¢** |
| cost to act | 2.75¢ | 2.75¢ |
| **profitable after cost** | **0.00%** | **0.00%** |
| games joined / fully settled | 30 / 17 | **97 / 82** |

**Nine times the data, same answer.**

⚠ **The resting-order figure (−0.85¢) I could NOT re-derive today, and I am
reporting that rather than leaving it implied.** The script runs — it is not
broken — but it replays 70 order-book files and takes ~20 minutes. Three attempts
have now been made; the stored numbers still carry their 2026-08-08 timestamp.
**So: reproduces = unconfirmed as of this reply.** A headline number I cannot
re-derive inside a session is a weaker number than I have been treating it as,
and the fix is to make the replay cache its intermediate panel.

## 3. Would a field rename be caught? **It would not have been. Now it is.**

`common/kalshi_fields.py::assert_priced` exists and was written for exactly this.
**I searched the entire repository: nothing called it.** Not my four folders, not
anywhere outside `common/` itself. **A guard nobody imports is documentation.**

Wired into the recorder's read path — once per family per cycle, on the first
market. On a rename it prints which dead name was reached for, instead of writing
silent nulls. Smoke-tested on `KXMLBGAME`.

**Two limits, stated because they matter:** it takes effect when the recorder
next **restarts**, so the running process still has the old code; and it covers
the recorder, not every analysis script — the tape puller has its own version,
the rest have none.

## 4. Still asserted, never verified

- **C024** — a parse bug wrote real row counts with empty content for 1h45m and
  was caught by accident. **The fix status is UNVERIFIED in the ledger.** The
  thing that would settle it is a content-level health check on that recorder's
  output; `crypto/`'s own coverage table marks GUARD #12 as *"specified, status
  unknown"* there, and I have not run it.
- **K010** — "prices are calibrated bucket by bucket" is a *failure to detect*,
  not a demonstration. Already marked overstated; still quoted.
- **M011** — the 13-game, one-snapshot, retail-book figure behind "baseball is
  efficient". Corrected in two files, and it is still what made baseball the
  negative control.
- **My own worst one is §2's second half** — a headline result I cannot currently
  re-derive in a session.

## Correction accepted

Thank you for carrying the wider-margin correction to him directly. Your
restatement is right: **the only thing that shows room is a measured
disagreement between two venues.**

---

## THE REFEREE — three lists

**1. STANDS**
- **Both recorders alive, 792 and 868 cycles, none missed since 08-08.** Read
  from the cycle tables, not from a process check.
- **The moneyline null.** Survives on 12,868 comparisons — 9× the original — with
  the same 0.00%.
- **`assert_priced` was dead code.** Survives on a whole-tree search returning no
  callers.

**2. DOWNGRADED**
- **was:** the resting order loses 0.85¢ per contract *(stated as established)*.
  **now:** stated on 2026-08-08 and **not re-derived since**; the script is too
  slow to verify inside a session. **because:** three re-run attempts did not
  finish, and I will not call something reproduced that I have not reproduced.
- **was:** "the fix has never been verified" (C024). **now:** "the ledger marks
  the fix UNVERIFIED and the check that would settle it — a content-level health
  check on that recorder — has not been run by me." **because:** the Critic
  correctly flagged the first as an absence claim.

**3. FOR THE USER — genuinely unresolved. NOT empty.**
- **The question:** should the recorders be put on a watchdog, given nothing
  watches them and they have died twice?
- **One side:** they are the only asset here that cannot be re-bought at any
  price, and both deaths were silent with empty error files.
- **The other side:** a watchdog that restarts blindly can mask a real fault, and
  this repo's decision **D8** already records that false alarms train the user to
  ignore warnings.
- **What would settle it:** it is a judgement about which failure he prefers, not
  a measurement — **which is why it is on this list and not resolved by me.**


---

### ✅ RESOLVED, same night — the resting-order figure DOES reproduce, bit for bit

The fourth attempt completed. **Every field matches to four decimal places:**

| | original 2026-08-08 | re-derived 2026-08-12 |
|---|---|---|
| fills / days / events | 17,325 / 23 / 1,161 | **identical** |
| capture | −1.2264¢ | **−1.2264¢** |
| adverse @60 s | −0.4599¢ | **−0.4599¢** |
| **net** | **−0.7664¢** | **−0.7664¢** |
| day-clustered | −0.8534 [−1.6321, −0.1852] | **identical** |
| N1 side placebo | −0.0041¢ | **−0.0041¢** |

**So §2's second half is withdrawn: it was a TIMEOUT, not a reproducibility
problem.** The script takes ~22 minutes and my session limit is 10.

**What I said stands anyway, and I am keeping it:** a headline number that needs
a 22-minute run is one nobody will re-check casually, and I only found this out
because you asked. Caching the intermediate panel is still worth doing.

