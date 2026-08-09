To: reopen
From: coordinator
Opened: 2026-08-08 22:45
Status: OPEN
Subject: Audit all 342 closed claims: which died on evidence, and which on a bug, a missing feed, or a test too small

--- INSTRUCTION ---

You are a NEW chat. Your folder is `reopen/` and it does not exist yet -- create
it, with `README.md`, `HANDOFF.md` and `DECISIONS.md`.

**You READ every folder in this repo and WRITE only in your own.** You do not
fix another chat's work. When you find something, you write it up and file a
mailbox message to the chat that owns it. That is the whole shape of this job.

# WHY YOU EXIST

The user, 2026-08-09: *"I've been feeling that there's some stuff that we closed
for the wrong reason."*

He is right, and it is not a feeling — **it has happened at least twice and both
are documented:**

- **B021.** A tennis thread was closed because "no free ITF data source exists."
  One does. **The thread was closed on a false premise.**
- **M001.** "Kalshi's order book returns empty; depth is not public." Held by a
  prior session and *independently reproduced on 85 markets*. Both readings
  parsed a key that does not exist. Depth is public, free, 20 levels a side.
  **Three scripts carried the bug and the crypto market-making thread sat
  blocked on it for six days.**

`LEDGER.md` and the ledgers it points at hold **342 recorded claims**, 51 of
them withdrawn. **Nobody has ever audited the closures.** Every audit this repo
has run has paid, three times out of three.

# THE JOB: sort every closed thread into one of two piles

**Closed on EVIDENCE** — it was measured properly and it did not work. Leave it
alone. Most will be this, and saying so is a real result.

**Closed on something else** — and there are four kinds. These are your
categories and I want counts for each:

### 1. Closed by a bug
A script was wrong and the conclusion followed the bug. **M001 is the worked
example.** Look for conclusions that rest on a single script's output where the
script was later patched, and for anything reading a field name that has since
changed.

### 2. Closed because data "wasn't available"
**B021 is the worked example.** Any thread whose stated blocker is a missing
feed, a paywall, an API limit or a dead source. **Data availability changes.**
For each, say what was actually checked at the time and whether anyone has
looked since.

### 3. Closed by over-generalising one test
One version was tested, it failed, and the whole idea was declared dead. **The
worked example is the one that caused this repo's biggest correction: a sweep
over PRICE AND MARKET features was cited to close a question about INDIVIDUAL
PLAYERS, which it never tested.** For each, name what the test actually covered
and what it did not.

### 4. Closed by a test too small to find what it says is absent
**This is probably the largest category and the least visible.** A write-up that
says "no effect" when the honest statement is "this test could not have detected
an effect smaller than X, and the effect we are looking for is smaller than X."

**The two sentences look identical on the page and mean opposite things.** For
every null result, work out the smallest effect that test could have detected,
and compare it to the size of effect the idea would need to be worth trading.
Where the second is smaller than the first, **the thread is not closed — it is
unmeasured**, and it should be labelled that way.

`LEDGER.md` B024 already does this correctly and is your model: it reports its
own detection floor and says in plain terms that a real effect is *"not
excluded, only unevidenced."* Very few rows do that.

# HOW TO REPORT IT

One table, `reopen/REOPENED.md`, ordered by how much it would matter if the
closure was wrong:

| claim | what closed it | which of the four | what would settle it | how long |
|---|---|---|---|---|

**Rules that keep this honest:**

- **A reopen is a claim and needs evidence.** "I want another go" is not a
  finding. Say specifically *why the original close was wrong* and what would
  have shown it at the time.
- **Do not reopen anything closed on evidence.** Wanting a different answer is
  not a reason, and a chat that reopens everything is worth nothing.
- **Report the count that closed correctly**, prominently. If 300 of 342 were
  closed properly, that is the headline and it is good news.
- **You cannot re-run the tests.** You are auditing closures, not redoing the
  work. When something should be reopened, file a mailbox message to the chat
  that owns that folder and let them do it.

# RULES

`CLAUDE.md` is the contract. §9c is the method, §6 the evidence standard.
**Before you report anything, run the Critic and the Referee** —
`coordinator/REFLECT.md` — and the mechanical scan,
`py -3 coordinator\reflect.py --file <your draft>`. Your whole job is finding
where someone concluded too fast, so being caught doing it yourself would be
the obvious way to fail.

**No statistics words to the user.** Money, or out of 100. `CLAUDE.md` §1 has
the banned list. Say "the test was too small to spot anything under 5 in 100",
never the technical term for it.

Write your `BRIEF.md` section with
`py -3 coordinator\brief.py write reopen --file <a file>`, update `STATUS.md`,
write `HANDOFF.md`, and push.

--- REPLY ---

The session that owns `reopen` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

