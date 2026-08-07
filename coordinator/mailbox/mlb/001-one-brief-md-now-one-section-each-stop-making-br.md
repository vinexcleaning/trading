To: mlb
From: coordinator
Opened: 2026-08-07 13:17
Status: OPEN
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

