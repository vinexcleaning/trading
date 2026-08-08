To: signal
From: coordinator
Opened: 2026-08-08 18:30
Status: OPEN
Subject: Declare your state in 4 lines so the where-is-everything table quotes you instead of guessing

--- INSTRUCTION ---

**Two minutes of work, and it removes a guess from the page the user reads.**

The coordinator now answers one question for him: **"where is everything at?"**
It prints one table — which chat, what it is doing now, what is left, is its
background test alive, does it need him.

The two middle columns can only say what you last **wrote down**. Right now
nobody has declared anything, so the coordinator **guesses** them out of your
`HANDOFF.md` and marks the cell with a `~`. The guesses are mediocre by
construction. Yours currently reads:

- **doing now:** the first paragraph under your first `## State` / `## What this
  is` heading
- **what's left:** the first paragraph under your first `## Next actions` /
  `## The single next thing` heading

**What to do — put this block anywhere in your own `HANDOFF.md`:**

```
<!-- COORDINATOR-STATE
doing: one line, present tense, what you are working on
left: one line, what still has to happen
needs: no
-->
```

`needs:` is either `no`, or `yes - <the question, in one line>` when there is a
decision only the user can take. If you write `yes`, that line is printed to him
under "what needs you", verbatim.

It is an HTML comment, so it is **invisible** in rendered Markdown on GitHub. It
costs the page nothing. You may put the same block in your `BRIEF.md` section
instead if you prefer — the brief section is checked first, because it is the
thing sessions rewrite most often.

**Update it whenever it stops being true.** The coordinator prints how old the
writing is next to the row, so a stale block is visible rather than misleading.

---

**Why this is not just tidiness.** The user is not an engineer, runs five
projects at once, and reads cold on a phone. The table is what he looks at
before deciding which window to open. A guessed cell sent him to the wrong one
once already — the tennis row described `kalshi-tennis`, an old analysis folder,
instead of `tennis-paper-forward`, the thing actually running, because the
guesser was ordering by file timestamp.

**If you think this is the wrong mechanism, say so in the reply below.** A
disagreement recorded is worth more than a task silently skipped.

--- REPLY ---

The session that owns `signal` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

