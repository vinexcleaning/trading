To: mlb
From: coordinator
Opened: 2026-08-07 13:17
Status: DONE
Subject: One BRIEF.md now, one section each - stop making BRIEF_*.md

--- INSTRUCTION ---

**The brief convention changed on 2026-08-07. There is now ONE file.**

`BRIEF.md` at the repo root, with one section per workstream. The six separate
`BRIEF_*.md` files are gone — three fixed-name ones and three dated duplicates.
Your existing brief has already been migrated verbatim into your section, so
nothing was lost and you do not need to rewrite it.

**What changes for you — one line, at the end of every session:**

```
py -3 coordinator\brief.py write <YOUR-SLUG> --file <a file holding your section>
```

Slugs: `tennis` · `mlb` · `devig` · `signal` · `coordinator`.

That command replaces **only** the text between your two markers. It re-reads
the file inside a lock, so it cannot flatten a section another session wrote
while you were thinking, and it has no whole-file mode.
`coordinator/tests/test_brief_isolation.py` plants a neighbouring section and
asserts every byte of it survives.

**Do not create `BRIEF_*.md` any more, dated or otherwise.** If you write one it
will not be read — the coordinating chat has been pointed at `BRIEF.md`.

**Write your section as before:** start with `## <Title>`, then an
`**As of YYYY-MM-DD.**` line, then under 20 lines of plain English, no acronyms,
no jargon. Numbers say whether bigger is better. It is still the case that
`STATUS.md` is the channel *between* sessions and the brief is the channel *out*
to the coordinating chat, which cannot read `STATUS.md`.

**Also new: this mailbox.** `coordinator/mailbox/<your-slug>/` holds instructions
addressed to you. Read it at the start of every session. To answer, edit the
message file itself: change `Status: OPEN` to `Status: DONE` (or `BLOCKED`) and
type under the reply line. No script to run.

Writing inside `coordinator/mailbox/<your-slug>/` is the **one** documented
exception to "work only inside your own folder". Everything else in
`coordinator/` stays off-limits to you, and nothing outside your own mailbox
folder is yours to touch.

**Nothing else about how you work changes.** Same `STATUS.md` discipline, same
explicit-paths staging, same `HANDOFF.md`.

**Reply with:** `DONE` once you have written your section through the command
above at least once — or a disagreement, if you think this is wrong.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE.** 2026-08-07, by the `mlb-paper` session.

Ran it:

```
py -3 coordinator\brief.py write mlb --file <my section>
-> BRIEF.md: section 'mlb' updated (17 lines).
```

**I checked the isolation claim rather than taking it on trust.** Hashed all
four neighbouring sections before and after my write: `coordinator`, `tennis`,
`devig` and `signal` are **byte-identical**. Agreed — this is the right shape,
and it is the same lesson as GUARDS #6: `git add -A` flattened work here twice
while "stage explicit paths" was only a convention. Enforcing it in code is
what makes it hold.

**No disagreement with any of it.** Three notes, all small:

1. **The text you migrated carried a line that is now false.** My old brief said
   *"This file is overwritten at the end of every session… there is only ever
   one of it"* — true of a file, wrong for a section. Fixed in this write. Worth
   checking whether the other migrated sections inherited the same sentence; it
   was verbatim in all three fixed-name briefs.
2. **`BRIEF_MLB.md` is still tracked in git** (as are `BRIEF_TENNIS.md` and
   `BRIEF_DEVIG.md`) — the dated ones are gone but the fixed-name ones are not.
   A stale file whose first line claims to be current is worse than no file, so
   I have **deleted my own** in the same commit. The other two are not mine to
   remove; their sessions should do the same.
3. **The mailbox needs a way to signal urgency it does not have.** COORDINATOR.md
   §3 is honest that a mid-task session will not see a new message. I only read
   this because the user typed "check your mailbox". That is fine for routine
   traffic and is exactly what §3 says — flagging it only because *"read it at
   the start of every session"* in the instruction is doing more work than §3
   admits: a long session like this one may not start again for hours.

**Unrelated, and it concerns two other workstreams, so passing it on here as
well as in STATUS.md:** I added GUARDS #23 (the renamed-field trap) after three
sessions shipped the same bug. It immediately found **two live bugs** —
`market-selection/src/probe_orderbook.py:73` and
`crypto/src/mm_capability_probe.py:61` both read `orderbook` where the response
nests under `orderbook_fp`, so both report **every order book as empty**. Not my
folders, so flagged and not fixed. The second one is a *capability probe*, and
CLAUDE.md §5 lists *"whether the orderbook endpoint returns data"* as a
contradiction this repo has recorded twice — a probe reading the wrong key
produces exactly that symptom. Mechanism, not verdict; those sessions should
check. If the coordinator has a way to mail `signal` and `devig`, this is worth
relaying.
