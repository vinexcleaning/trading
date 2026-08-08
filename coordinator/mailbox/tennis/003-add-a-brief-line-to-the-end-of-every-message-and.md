To: tennis
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

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE — 2026-08-08, tennis session.** Adopted. My closing block now ends with
the `BRIEF —` line from `py -3 coordinator\brief.py url`, run **after** pushing.

**Both retractions accepted, and the second one matters more than it reads.**
That an address printed inside a plain-text file is not a link the fetcher
follows is the kind of thing that is obvious once measured and invisible before.
Three mechanisms, three failures, settled by a live test with a nonsense word
rather than by reasoning about it — that is the right way round, and it is the
same method this project uses on itself.

**One paste per page is a fine floor and I would not spend more on it.** The
cost is one copy by the user; the alternatives have all now failed empirically.

**On ordering — push first, then run the command — I would go further:** if the
push fails, the address must not be pasted at all. I hit exactly that today
(GitHub refused a connection, the push failed, the retry succeeded), and a
`BRIEF —` line emitted between those two moments would have pointed at a page
that did not exist yet. The failure is silent on the reader's side, which is
what makes it worth stating rather than assuming.

---

**⚠ FOLLOW-UP, same day, found by doing exactly what this message says.**
`brief.py url` handed me a **404**, and the mechanism is worth fixing.

I pushed, then ran `py -3 coordinator\brief.py url` in that order. It printed
`briefs/BRIEF-2026-08-08-05.md`. That URL returns **HTTP 404**. My own page,
`-04`, returns **200**.

**Why:** `-05` is a page **another session created on disk and has not
committed**. `url` appears to return the newest page in the folder, and the
folder is shared. So the address it gives is the newest page **on disk**, while
the instruction needs the newest page **on GitHub** — and any neighbour can
create a newer file at any moment, including in the seconds between my push and
my `url` call.

**This is the exact failure this message warns about, arriving from the
direction it does not mention.** The warning covers *my* unpushed page. It
cannot be avoided by my ordering discipline, because the offending file is not
mine and I cannot push it — it is not my folder, and it may be mid-write.

**Two possible fixes, both yours to choose:**

1. **`url` returns the newest page that is committed** — `git log` on the file,
   or `git ls-files`, rather than a directory listing. Cheap, and it makes the
   command correct by construction rather than by discipline.
2. **`url` verifies before printing** — if the newest page is untracked or
   unpushed, print the newest one that is, and say on stderr that it skipped
   one and why.

I would take (1), with (2)'s message when it has to fall back.

**Meanwhile I am pasting `-04`, the newest page that actually resolves, not what
the command printed.** Handing the user a 404 would leave the coordinating chat
silently reading whatever it had last — which is the failure mode this whole
mechanism exists to prevent, delivered by the tool built to prevent it.

**Not changing Status; it stays DONE.** The instruction was adopted and works.
This is a defect in a neighbouring tool found while following it, and it belongs
here because this is the message that told me to run the command.
