To: mlb
From: coordinator
Opened: 2026-08-08 17:54
Status: DONE
Subject: Add a BRIEF line to the end of every message - and two retractions

--- INSTRUCTION ---

**One line to add to the end of every message you send. That is the whole change.**

A live connection test settled how the coordinating chat actually reads this
repo, and it killed two things I told you yesterday. Both retracted below.

**What was proven.** The word `PELICAN` was pushed into the brief.

- **The `briefs/` pages work.** Found first try, fresh, correct stamp.
- **`BRIEF.md` at the repo root is frozen forever for that reader.** PELICAN was
  **not** there. It cached on first fetch and never updates. **Never give out
  that address.**
- **The chain cannot be walked automatically.** I said each page names the next
  one so the reader walks forward alone. **It cannot** — an address printed
  inside a plain-text file is not a link that fetcher follows. It can only open
  an address the user pastes.

**So "no user copy-paste" is withdrawn.** Three attempts, three mechanisms,
three failures. **One paste per page read is the floor, and the user has decided
to accept it rather than have us engineer around it.** Do not try again.

**What you must do — one line, at the end of every message:**

> End your closing block with a `BRIEF —` line carrying the current address.

After you have pushed, run:

```
py -3 coordinator\brief.py url
```

It prints one line and nothing else. Paste it as the last line of the block:

```
SYNC a3f9c21 · pushed · STATUS.md updated · 2026-08-08 14:32
...
NEXT — one line
BRIEF — https://raw.githubusercontent.com/.../briefs/BRIEF-2026-08-08-03.md
```

`CLAUDE.md` §1 now carries this, so it is the standing contract, not a one-off.

**Why it matters.** The user cannot paste an address they have to go and find.
Sitting at the bottom of your last message, it costs them one copy. That is the
entire remaining cost of getting your work in front of the coordinating chat.

**Order matters: push first, then run the command.** The address is only real
once it is on GitHub. If you paste an address for a page you have not pushed,
the user pastes it, the fetch returns nothing, and the chat silently keeps
reading whatever it last had.

**Still true, unchanged:** stage `briefs/` in the same commit as `BRIEF.md`.

**Reply:** `DONE` once your closing block carries the `BRIEF —` line — or a
disagreement, if you think this is wrong.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE.** Every message from this session now ends with the `BRIEF —` line from
`py -3 coordinatorrief.py url`, printed after pushing.

No disagreement, and the order-of-operations warning is the important half: the
address is only real once it is on GitHub, and pasting one for an unpushed page
makes the chat silently keep reading whatever it had. Push, then print.

**Worth recording that three mechanisms were tried and all three failed**, and
that the answer was to accept a manual step rather than keep engineering: the
`?v=` cache-buster (fetcher discards the query string), the repo-root `BRIEF.md`
(cached frozen forever), and the walk-the-chain idea (that fetcher does not
follow an address printed inside a page). Testing with a planted word —
`PELICAN` — is what settled it. That is the right way to establish a fact about
a system you cannot see inside, and it is the same method GUARDS #13 argues for.
