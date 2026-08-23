# AGENT_PROTOCOL.md — how a non-Claude AI participates

**This file exists because one mechanism in this repo is Claude-specific: Claude
Code auto-loads `CLAUDE.md` into every session. Nothing else is.** Everything
else is Markdown, JSON and git. This document is the same contract, written so an
agent that cannot rely on auto-loading can follow it from a standing start.

**Read this whole file before writing anything. It is short on purpose.**

---

## 0. THE ONE RULE THAT OVERRIDES EVERYTHING

> **Reading is free. Writing is narrow. Executing is not yours.**

If you are ever unsure whether an action is allowed, **it is not** — file a
message asking, and stop. A message costs nothing. A wrong write costs someone
else's day, and this repo has already lost days to exactly that.

---

## 1. IDENTIFY YOURSELF

You are a **participant** with a **slug** — a short lowercase name that is your
identity everywhere in this system. Your slug is a row in
[`coordinator/chats.json`](chats.json). **If you do not have a row there, you are
not a participant and you must not write.**

Your row states: your `folders` (what you own), `may_write`, `read_only`,
`never_touch`, and whether `execution` is permitted. **Read your own row first.**
It is the authority on what you may do, not this document and not your
assumptions.

**Every message you file carries `From: <your-slug>`.** That is how a human or
another agent knows a message was not written by Claude.

---

## 2. WHERE THE CURRENT STATE LIVES

Read in this order. **Do not skip to the mailbox.**

| # | file | what it tells you |
|---|---|---|
| 1 | **`BRIEF.md`** | the whole picture, one section per participant. **Start here.** |
| 2 | `STATUS.md` | the detailed channel *between* participants. Long. Contradictions are flagged here. |
| 3 | `<folder>/HANDOFF.md` | that participant's own detailed state |
| 4 | `<folder>/DECISIONS.md` | judgement calls it took without asking, and why |
| 5 | `LEDGER.md`, `GUARDS.md` | the evidence memory: every recorded claim, its sample, its dates, its result, and whether it was later withdrawn |
| 6 | `INBOX.md` | ideas received but not yet routed |
| 7 | `CLAUDE.md` | the full contract. **Written for Claude, but its content is not Claude-specific — read §§1, 2, 5, 6 at minimum.** |

**⚠ `BRIEF.md` at the repo root may be cached stale by whatever is fetching it.**
The immutable snapshots under `briefs/BRIEF-YYYY-MM-DD-NN.md` are never edited
after publication. **If you are reading over the web, prefer the newest snapshot
and say which one you read.**

---

## 3. HOW TO READ THE CURRENT OBJECTIVE AND STATUS

Every participant declares its own state in an HTML comment. It lives in either
its `HANDOFF.md` or its `BRIEF.md` section:

```
<!-- COORDINATOR-STATE
doing: one line, present tense, what it is working on
left:  one line, what still has to happen
needs: no        (or)   needs: yes - <the question, in one line>
-->
```

**Three things to understand about this block, or you will misread the system:**

1. **It is a self-report, not an observation.** Nothing watches a participant
   work. The block says what that participant last *wrote down*.
2. **It can be stale.** Always check when it was last written — the git log for
   that file is the honest answer.
3. **`needs: no` means "no alarm fired", not "all is well".**

---

## 4. HOW TO READ MAIL

Your mailbox is `coordinator/mailbox/<your-slug>/`. Every file is one message:

```
To: <slug>
From: <sender-slug>
Opened: YYYY-MM-DD HH:MM
Status: OPEN | DONE | BLOCKED
Subject: <one line>

--- INSTRUCTION ---
<the body>

--- REPLY ---
<the receiving participant writes here>
```

**Read every message with `Status: OPEN` in your box, oldest first.** Messages
are numbered `NNN-` and that number is how humans refer to them ("mailbox 016").

**⚠ `Status:` is measured unreliable.** At the time this was written, seven
messages read `OPEN` while the git history proved the work was finished. **Do not
treat `Status: DONE` as evidence that something happened, and do not treat
`OPEN` as evidence that it did not. Check the commits.**

---

## 5. HOW TO FILE A MESSAGE

**Preferred — use the tool.** It handles numbering safely against other writers:

```bash
py -3 coordinator/mail.py send <recipient-slug> \
     --subject "one line" --file body.md --from <your-slug>
```

**If you can only write files directly** (e.g. through a GitHub API with no shell):

1. List `coordinator/mailbox/<recipient>/` and find the **highest** `NNN`.
2. Your file is `NNN+1` padded to three digits, then `-`, then your subject
   lowercased with non-alphanumerics turned into hyphens, then `.md`.
3. Write the exact header block above, with `Status: OPEN` and your own slug in
   `From:`.

**⚠ Direct writing is not collision-safe.** `mail.py` claims a number atomically
before writing; a plain file write cannot. **If there is any chance another agent
is filing at the same moment, use the tool.** If you must write directly, say so
in the message body so a human knows the number could be contested.

**Never renumber, rename, or delete an existing message.** Other messages and
documents cite those numbers.

---

## 6. HOW TO REPORT COMPLETION, BLOCKERS, FINDINGS AND ERRORS

**In the message file you were given.** Edit that same file:

- change `Status: OPEN` to `Status: DONE` or `Status: BLOCKED`
- write your answer **under** the `--- REPLY ---` line
- **never edit the `--- INSTRUCTION ---` section.** It is the record of what you
  were asked, and changing it destroys the ability to tell whether you answered
  the question or a different one.

**Disagreement is a valid reply and is wanted.** The template says so: *"a
disagreement recorded is worth more than a task silently skipped."* If the
instruction is wrong, say why, in the reply, and set `BLOCKED`.

**If your finding contradicts another participant's**, do not overwrite theirs.
Flag it in `STATUS.md`, say which measurement you trust and why, and name both.

---

## 7. WHAT YOU MAY WRITE

**Your row in `chats.json` is the authority. This is the general shape:**

| | |
|---|---|
| ✅ **write** | replies inside messages addressed to you · new messages to other participants · `INBOX.md` (append only) · everything inside your own folder |
| 📖 **read only** | `CLAUDE.md` · `DICTATOR.md` · `chats.json` · `STATUS.md` · `LEDGER.md` · `GUARDS.md` · `runners.json` · every other participant's folder |
| ⛔ **never** | `livedesk/` — **it places real orders with real money** · `common/kalshi_fees.py` — one implementation, enforced by a repo-wide test · `briefs/*` — immutable once published |

**`BRIEF.md` is a special case.** You may write **only your own section**, and
**only** via:

```bash
py -3 coordinator/brief.py write <your-slug> --file section.md
```

**Do not edit `BRIEF.md` directly.** That tool holds a lock, re-reads inside it,
replaces only the text between your two markers, and writes atomically. A direct
edit defeats all of that and can silently destroy another participant's section.

---

## 8. HOW TO AVOID INTERFERING WITH OTHER PARTICIPANTS

1. **Work only inside folders your row lists.** The single documented exception
   is `coordinator/mailbox/<your-slug>/`.
2. **Stage explicit paths when committing. Never `git add -A`.** Two sessions
   have already cross-contaminated commits that way.
3. **`git pull` before you read state, and again before you write.**
4. **Assume something else is running.** A live process can hold a file open and
   overwrite your change within the minute — that has happened here and reverted
   four separate committed repairs. **If a file looks like it belongs to a
   running tool, do not edit it; file a message instead.**
5. **Never touch another project's repo.** Trading work stays here; other
   domains have their own repos and are explicitly out of scope.

---

## 9. WHEN NOT TO EXECUTE ANYTHING

**Stop and file a message instead of acting, whenever any of these is true:**

- your row says `"execution": false` — **then you never execute, full stop**
- the action would place, cancel, or modify a trade
- the action would spend money, or commit to spending it
- the action needs a credential, a login, or an API key
- the action deletes or overwrites data you did not create
- the action touches `livedesk/`
- two readings of the instruction would lead to materially different work
- you would be acting on something you inferred rather than something you read

**Reporting a blocker is a complete and valuable answer.** The most expensive
failures recorded in this repo were confident actions taken on one unchecked
source — not refusals.

---

## 10. EVIDENCE RULES THAT APPLY TO YOU TOO

These are not Claude-specific and this repo enforces them socially and, in
places, with tests. **Full detail in `CLAUDE.md` §6 and §9c.**

- **"We tried that" is banned.** If you claim something was already tested you
  must give: what was tested, in its recorded words, with its ID · what the data
  was and what *one observation* was · what dates it covers · what came out and
  whether it was later corrected · **and how the new version differs, or an
  explicit "I cannot tell".**
- **Report the sample at the right unit.** 490,464 fills from 762 matches is
  **762** observations.
- **Say how many things you tried** before showing the one that looked best.
- **A backtest chooses candidates. Only a forward test on unseen data counts.**
- **Report corrections as prominently as findings**, inline where the original
  claim appears. Deleting a wrong number is how somebody re-derives it.

---

## 11. THE MINIMUM ROUND TRIP

If you do nothing else, this is what proves you are wired in correctly:

1. `git pull`
2. Read the newest `briefs/BRIEF-*.md`
3. Read `coordinator/mailbox/<your-slug>/` for `Status: OPEN`
4. Do the read-only thing you were asked
5. Reply in that same file; set `Status: DONE`
6. File **one** message back to `coordinator` with what you found
7. Commit **only** the files you touched, with an explicit path list
8. Push

**A human then runs `py -3 coordinator/where.py` and sees your message. That
round trip working is the whole integration.**
