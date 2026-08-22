# ARCHITECTURE AUDIT — the existing Claude orchestration system

**Read-only audit, 2026-08-22.** Nothing was redesigned, nothing existing was
modified. This file is the only thing created. Every claim below was read off
the files, not recalled — where something is inferred rather than verified it
says so.

**Audience: another AI deciding how ChatGPT and Nexus integrate with this.**

---

## THE ARCHITECTURE, AS IT ACTUALLY IS

```
                          THE USER (voice dictation, one window)
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   DICTATOR CHAT       │  owns: coordinator/, common/
                        │   (a Claude Code      │  does NO project work
                        │    window, nothing    │  no network, no credentials
                        │    more)              │  enforced by a test
                        └───────────┬───────────┘
                                    │ writes
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  coordinator/mailbox/<slug>/  coordinator/chats.json      STATUS.md
  NNN-subject.md               (worker registry)           (contradictions,
  Status: OPEN                                              cross-session notes)
        │
        │  ⚠ NOT DELIVERED. The file sits there.
        │     The user must open that window and type a word.
        ▼
  ┌──────────────────────────────────────────────────────────┐
  │  WORKER CHATS — 9 registered, 1 window each               │
  │  tennis · mlb · devig · signal · reopen · livedesk ·      │
  │  extractors · factory · soccer(dormant)                   │
  │                                                           │
  │  Each owns 1-5 folders. CLAUDE.md §5: work only in yours. │
  └──────────────────────┬───────────────────────────────────┘
                         │ writes back, four channels
       ┌─────────────────┼──────────────────┬─────────────────┐
       ▼                 ▼                  ▼                 ▼
  the SAME mail     <folder>/HANDOFF.md   BRIEF.md        git commit
  file, edited      + COORDINATOR-STATE   own section     message
  Status: DONE      HTML comment          via brief.py    (the real log)
  reply below line
       │
       └────────────────────────────────────┐
                                            ▼
                             ┌──────────────────────────┐
                             │  DICTATOR READS FILES    │
                             │  where.py · detail.py ·  │
                             │  runners.py · scan.py    │
                             │  (dictator.bat = all)    │
                             └──────────┬───────────────┘
                                        ▼
                                    THE USER
```

**The single most important structural fact: there is no message bus, no
scheduler and no daemon. Every arrow above is a file on disk, plus a human
opening a window and typing one word.** The system is a set of file conventions
that Claude sessions have been instructed to obey.

---

## THE 30 QUESTIONS

### 1. What is the Dictator chat responsible for?

Four jobs, from `DICTATOR.md` §2 and `COORDINATOR.md` §2:

- **Report state** — "where is everything at": a table plus plain-English detail
  per worker, all of it **quoted from what each worker wrote about itself**, never
  recomputed.
- **Route ideas** — take a plain-English idea, run a prior-work check against
  every recorded claim, present it, pause, and on "go" write the instruction into
  the right worker's mailbox.
- **Name and register workers** — `chats.json`, so "the second tennis one" is not
  a question anyone answers from memory.
- **Reach the outside coordinating chat** — publish `BRIEF.md` and immutable
  snapshots under `briefs/`.

**It does no project work.** It does not run tests, analyse markets, or write
trading code. This is stated before the feature list in both documents, on
purpose.

### 2. What are worker chats responsible for?

Each owns **one workstream and 1–5 folders** (`chats.json` `folders[]`). It does
the actual analysis, writes code in its own folders, maintains that folder's
`HANDOFF.md` / `DECISIONS.md` / `PREREGISTRATION_*.md`, writes its own section of
`BRIEF.md`, and answers its mailbox.

`CLAUDE.md` §2 tells it to run autonomously for an hour or more, never ask
"should I continue", take the conservative option on judgement calls, log it, and
keep going.

### 3. How does the Dictator assign work?

```
py -3 coordinator\mail.py send <slug> --subject "..." --file body.md
```

Writes `coordinator/mailbox/<slug>/NNN-<slugified-subject>.md`. That is the whole
mechanism. **It prints, verbatim, "It is NOT delivered yet."**

### 4. How do worker chats discover their tasks?

**A human opens that window and types a word.** `chats.json` carries the exact
opening line per worker — usually `next`, sometimes
`you are the <x> chat, check your mail`.

`CLAUDE.md` §5 also instructs every session to read its mailbox at the start of
every session. **There is no polling, no notification, no push.** The dictator
cannot deliver; it can only leave.

### 5. What files are used for mail, handoffs, shared state, status, instructions, memory?

| purpose | file(s) | count |
|---|---|---|
| **protocol / instructions** | `CLAUDE.md` (947 lines, auto-loaded into every session) | 1 |
| dictator manual | `DICTATOR.md` (385), `HOW_THIS_WORKS.md` (58) | 2 |
| dictator design + limits | `coordinator/COORDINATOR.md` (539) | 1 |
| **mail** | `coordinator/mailbox/<slug>/NNN-*.md` | **119 across 10 boxes** |
| **worker registry** | `coordinator/chats.json` (326 lines, 9 workers) | 1 |
| **per-worker handoff** | `<folder>/HANDOFF.md` | **20** |
| **per-worker decisions** | `<folder>/DECISIONS.md` | **19** |
| **shared state between workers** | `STATUS.md` (6,703 lines) | 1 |
| **shared state outward** | `BRIEF.md` (522) + immutable `briefs/BRIEF-YYYY-MM-DD-NN.md` | many |
| **evidence memory** | `LEDGER.md` (747), `GUARDS.md` (1,341), `SCOREBOARD.md` (629), plus 6 per-project ledgers | ~9 |
| idea intake | `INBOX.md` (41) | 1 |
| background-job registry | `coordinator/runners.json` (11 runners), `runners/runners.json` | 2 |
| generated worker prompts | `coordinator/prompts/SESSION-*.md` | many |

### 6. What exact format/protocol do those files use?

**Mail** — plain Markdown with a header block, from `mail.py TEMPLATE`:

```
To: <slug>
From: coordinator
Opened: YYYY-MM-DD HH:MM
Status: OPEN
Subject: <one line>

--- INSTRUCTION ---
<body>

--- REPLY ---
<the worker writes here and changes Status: above>
```

Parsed by three regexes: `^Status:\s*(\S+)`, `^Subject:\s*(.+)$`,
`^Opened:\s*(.+)$`. **Status values seen in use: `OPEN`, `DONE`, `BLOCKED`.**

**Worker state** — an HTML comment, so it is invisible in rendered Markdown. Read
by `where.py` (`STATE_RE = <!--\s*COORDINATOR-STATE(.*?)-->`) from **either**
`HANDOFF.md` **or** that worker's `BRIEF.md` section:

```
<!-- COORDINATOR-STATE
doing: one line, present tense
left:  one line
needs: no      |     yes - <the question, shown to the user verbatim>
-->
```

**BRIEF.md** — one section per worker between HTML markers:

```
<!-- SECTION:<slug> updated=YYYY-MM-DDTHH:MM -->
## Title
**As of YYYY-MM-DD.**
...
<!-- /SECTION:<slug> -->
```

**Worker registry** — JSON: `name`, `slug`, `folders[]`, `purpose`, `opening`,
`created`, `subjects[]` (keywords for routing), `window_title`.

**Runner registry** — JSON: `id`, `workstream`, `title`, `plain_english`,
`monitor` (`heartbeat` | manual), `kind`, `machine` (`desktop`/`laptop`),
`watchdog_name`, `heartbeat[]` (paths whose mtime is the liveness signal).

### 7. How do workers report completion, blockers, findings, errors?

**Four channels, and they carry different things:**

1. **The mail file itself** — edit `Status: OPEN` → `DONE` or `BLOCKED`, type
   under `--- REPLY ---`. The template explicitly invites disagreement: *"a
   disagreement recorded is worth more than a task silently skipped."*
2. **`COORDINATOR-STATE`** — `needs: yes - <question>` is surfaced to the user
   **verbatim** in the dictator's report.
3. **`STATUS.md`** — where a worker flags that its result **contradicts** another
   worker's, and says which measurement it trusts and why (`CLAUDE.md` §5).
4. **Git commit messages** — in practice the richest record. They routinely run
   40+ lines and carry the actual reasoning, corrections and retractions.

### 8. How does the Dictator know what has been completed?

**It reads files. It has no other sense.** Specifically:

- `mail.py open` / `list` — greps `Status:` across all 119 messages
- `where.py` — parses `COORDINATOR-STATE`, and **marks a cell `~` when it had to
  guess** from `HANDOFF.md` instead
- `scan.py` — folder-level: last commit, newest file touched, uncommitted
  changes, whether `HANDOFF.md`/`DECISIONS.md` exist
- `runners.py` — is each background job alive, by log-file mtime
- git itself — `head()`, `unpushed()`, `dirty_by_folder()`

**⚠ Verified weakness: mail `Status:` is unreliable in practice.** At audit time
`livedesk` had commits proving 011–017 were finished while all seven still read
`Status: OPEN`. **Commit history was accurate; the status field was not.** The
dictator's own `where.py` correctly prints how old each self-report is, which is
the honest part.

### 9. How is context preserved across separate Claude conversations?

**Entirely through files, in five layers:**

1. `CLAUDE.md` — **auto-loaded into every session in this repo.** This is the
   load-bearing mechanism. A brand-new window knows the protocol without being
   told.
2. `<folder>/HANDOFF.md` — the detailed state of that workstream.
3. `<folder>/DECISIONS.md` — judgement calls taken without asking, and why.
4. `LEDGER.md` / `GUARDS.md` / `SCOREBOARD.md` — the evidence memory. Claims with
   IDs, samples, dates, results and retractions.
5. Git history — and `coordinator/NEXT_DICTATOR.md` exists specifically for
   handing over when a dictator window runs out of usage. **It is deliberately
   short**: it carries only what cannot be read off disk (how the user works,
   what the last dictator got wrong), on the stated grounds that a long handoff
   goes stale and a chat that reads the repo cannot.

### 10. What prevents worker chats from interfering?

**Convention plus two mechanical guards.**

- **Folder ownership** — `chats.json` `folders[]`, enforced only by instruction
  (`CLAUDE.md` §5: "Work only inside your own folder"). **One documented
  exception:** a worker may write inside `coordinator/mailbox/<its-own-slug>/`.
- **`BRIEF.md` section isolation — genuinely enforced.** `brief.py write` has
  **no whole-file mode**; it replaces only the text between that worker's two
  markers, re-reads inside a lock, and `test_brief_isolation.py` mutates a
  neighbouring section and asserts every byte survives.
- **Staging discipline** — `CLAUDE.md`: *"Stage explicit paths. NEVER
  `git add -A`."* Recorded as having already caused two cross-contaminated
  commits.

**Everything else is honour system.** Nothing stops a worker writing into another
worker's folder.

### 11. What is trading-specific?

- Every ledger and its claim IDs (`LEDGER.md`, `GUARDS.md`, `SCOREBOARD.md`, six
  per-project ledgers)
- `idea.py` — the prior-work checker reads those ledgers
- `ledger.py` — parses ledger tables
- `common/kalshi_fees.py` — the single fee implementation, test-enforced
- `reflect.py` Critic/Referee — generic *machinery*, but `REFLECT.md`'s nine
  worked examples are all trading errors
- `runners.json` — Kalshi recorders and paper tests
- `CLAUDE.md` §§6, 7, 8, 9b, 9c — evidence standards, the four repos, machines,
  the four re-argued lines, the strategy pipeline
- The `paper-only` canaries (`test_paper_only.py` in two folders)

### 12. What is completely generic and reusable?

**This is the valuable answer, and it is most of the orchestration layer:**

| component | why it is generic |
|---|---|
| **`mail.py`** (199 lines) | slug + subject + body + status. **Zero trading references.** |
| **The `COORDINATOR-STATE` convention** | three fields, domain-free |
| **`where.py`** (503) | reads state blocks, git, folders. Domain-free except the workstream list |
| **`scan.py`** (426) | folder health: last commit, newest file, uncommitted, has-handoff |
| **`brief.py`** (461) | **the best single piece.** Multi-writer section-isolated document with a real lock, atomic write and an immutable snapshot chain |
| **`chats.py` / `chats.json`** | worker identity registry |
| **`newprompt.py`** (221) | bootstraps a new worker from a template |
| **`runners.py`** (623) | background-job liveness by log mtime; four states not two |
| **`dictator.bat`** | one command that runs the whole read layer |
| **`reflect.py`** | Critic → Referee pattern |
| **The HANDOFF / DECISIONS / PREREGISTRATION file conventions** | generic project hygiene |
| **`test_no_money_no_network.py`** | a capability canary — reusable for any "this component must not reach X" rule |

### 13. Which of these concepts already exist?

| concept | exists? | how |
|---|---|---|
| **shared mailbox** | **YES** | `coordinator/mailbox/<slug>/`, 119 messages |
| **task queue** | **partial** | numbered files per box; ordering only, no dequeue, no claim |
| **worker identity** | **YES** | `chats.json`: name, slug, folders, opening line, window title |
| **locks** | **YES, one** | `brief.py` mkdir-lock + stale-lock timeout. **Nowhere else.** |
| **task ownership** | **YES** | a message is addressed to exactly one slug; folders are owned |
| **status** | **YES** | `OPEN` / `DONE` / `BLOCKED`, plus `COORDINATOR-STATE` |
| **priority** | **NO** | zero occurrences. Order is filing order; urgency is prose ("⚠ URGENT") |
| **dependencies** | **NO** | expressed only as English inside a message ("do 016 first") |
| **retry** | **NO** | zero occurrences |
| **completion ack** | **partial** | worker flips `Status:`; **nothing verifies it, and it is demonstrably unreliable** |
| **escalation** | **NO** | zero occurrences. `needs: yes` is the only path and it goes to the human |
| **logging** | **YES** | git commit messages, `logs/*.log`, `logs/health.jsonl` |
| **history** | **YES** | git + `briefs/` immutable snapshots + ledger retractions |
| **checkpoints** | **NO** as a primitive | approximated by `HANDOFF.md` + commits |
| **persistent memory** | **YES** | `CLAUDE.md` (auto-loaded), ledgers, HANDOFF, DECISIONS |

### 14. What happens if two chats update the same file?

- **`BRIEF.md` — handled properly.** Lock, re-read inside it, section-scoped
  replace, atomic `os.replace`, and a test proving a neighbour survives.
- **`STATUS.md` — not handled.** Plain edits. `CLAUDE.md` says read it first and
  never overwrite another session's entries. Convention only.
- **Mail — a real race.** `cmd_send` computes `n = len(messages(slug)) + 1` with
  **no lock**. Two senders in the same instant produce the same `NNN` and one
  silently overwrites the other. Low probability today (one dictator), **but it is
  the exact thing that breaks if ChatGPT starts filing mail concurrently.**
- **Git — last writer wins**, with the usual merge conflicts.
- **⚠ Observed in the wild, worse than any of the above:** the `livedesk` GUI
  held `data/ledger.json` in memory and rewrote it every 60 seconds, **silently
  reverting four separate committed repairs.** A running process beat every
  file-level convention. This is the one that actually cost days.

### 15. Race conditions, stale context, duplication, cross-project contamination?

**All four are real and three are documented in the repo's own words.**

- **Race:** the mail numbering above; and last-writer-wins on any long-running
  process holding a file open.
- **Stale context:** structural and acknowledged. `where.py` prints the age of
  every self-report because the dictator *cannot* know what a worker is doing
  now. At audit time `mlb-paper`'s state block advertised 71 settled games and
  asked for an install that had already been done.
- **Duplication:** two runner registries deliberately do not match
  (`runners/runners.json` = what runs; `coordinator/runners.json` = how to tell
  it is producing). A new job must be added to both or it is unwatched or
  unrestarted. `dictator.bat` prints the drift.
- **Cross-project contamination:** `CLAUDE.md` §7 names four repos and forbids
  mixing. Observed once during this audit period: one session's 23 files landed
  inside another session's commit; the affected chat **flagged it rather than
  rewriting history**.

### 16. How does the system recover if a worker stops midway?

- **Its work survives** — `HANDOFF.md`, `DECISIONS.md`, and commits.
- **Its mail survives** — an unanswered message stays `OPEN` and is re-read on
  next start.
- **Its background jobs** are separate OS processes with their own watchdog
  (`runners/watchdog.ps1`, scheduled tasks) and do not stop with the chat.
- **The dictator itself** has `NEXT_DICTATOR.md` and a one-line restart:
  *"read coordinator/NEXT_DICTATOR.md then tell me where everything is at"*.
- **⚠ Nothing detects a stopped worker.** There is no timeout, no heartbeat on
  chats (only on background jobs), no reassignment. A window that dies mid-task
  looks exactly like one thinking hard. The only signal is the age column.

### 17. How does a new Claude chat learn the protocol?

**`CLAUDE.md` is auto-loaded into every session in this repo.** That is the whole
answer and it is the system's keystone. 947 lines covering how to talk to the
user, autonomy rules, evidence standards, folder conventions, the mailbox, and
the required message format.

Beyond that: `newprompt.py` generates a bootstrap prompt for a brand-new worker
that names the files to read before writing code, and `chats.json` carries the
opening line for existing ones.

### 18. Where are the protocol instructions stored?

| file | role |
|---|---|
| **`CLAUDE.md`** | **the contract.** Auto-loaded. Wins over habit. |
| `DICTATOR.md` | the dictator's manual; §1 is what it *cannot* do, written before the code |
| `coordinator/COORDINATOR.md` | engineering design + the long limits list |
| `HOW_THIS_WORKS.md` | 58-line operating summary |
| `coordinator/NEXT_DICTATOR.md` | dictator-to-dictator handover |
| `coordinator/prompt_template.md` | the shape of a new worker's first message |
| `coordinator/REFLECT.md` | the Critic/Referee checklist |
| `GUARDS.md` | reusable canaries; do not reimplement |

### 19. Which parts depend on Claude-specific behaviour?

**Almost none of the substrate.**

**Claude-specific:** `CLAUDE.md` auto-loading (a Claude Code feature); the window
model itself; the user typing an opening word.

**Not Claude-specific — plain files and git:** the entire mailbox, `chats.json`,
`BRIEF.md` and its lock, `STATUS.md`, every `HANDOFF.md`/`DECISIONS.md`, the
ledgers, `runners.json`, and all eleven Python tools, which are stdlib-only with
**no network imports by construction** (test-enforced).

> **Any agent that can read and write files in a git repo can participate.** The
> protocol is Markdown and JSON. Nothing is a Claude API call.

### 20. Could ChatGPT safely read and write through GitHub/files?

**Read: yes, immediately, with zero changes.** The repo is public; ChatGPT
already reads `BRIEF.md` snapshots today.

**Write: yes for a narrow set, with caveats:**

- ✅ **File mail** — as long as the numbering race in §14 is addressed
- ✅ **Reply in a mail file** — edit `Status:` and write under `--- REPLY ---`
- ✅ **Append to `INBOX.md`**
- ⚠ **`BRIEF.md`** — only via `brief.py write <slug>`. Editing it directly
  defeats the lock and the isolation test.
- ⚠ **`STATUS.md`** — append-only in practice, no lock, read-before-write
- ❌ **Another worker's folder** — breaks the ownership convention
- ❌ **`LEDGER.md` / `GUARDS.md`** — claim IDs and retraction discipline;
  needs a human or a worker that understands the evidence rules

### 21. Minimum interface ChatGPT would need

1. **Read the repo** (already possible — public).
2. **Write four paths:** `coordinator/mailbox/<slug>/*.md`, `INBOX.md`, its own
   `<folder>/` if given one, and replies inside existing mail files.
3. **A worker identity** — a row in `chats.json` (`slug: chatgpt`) so it is
   addressable and its folder ownership is declared.
4. **Read `CLAUDE.md`** at the start of every session. It is the protocol; it is
   not Claude-specific in content.
5. **Emit the message format** — the mail header block, and a
   `COORDINATOR-STATE` block wherever it declares state.
6. **A collision-safe filing method** — see §14. Simplest fix: a filename that
   cannot collide (timestamp or sender prefix) rather than a counter.

### 22. What should ChatGPT write vs read-only?

| | |
|---|---|
| **Write** | its own mailbox replies · new mail to workers · `INBOX.md` · its own folder · its own `BRIEF.md` section via `brief.py` |
| **Read-only** | `CLAUDE.md` · `DICTATOR.md` · `chats.json` · every other worker's folder · `LEDGER.md` · `GUARDS.md` · `runners.json` |
| **Never** | anything under `livedesk/` (real money) · `common/kalshi_fees.py` (single implementation, test-enforced) · `briefs/` snapshots (immutable by design) |

### 23. What should remain Claude-only?

- **`livedesk/`** — real orders, real money, mid-repair, five money-record
  defects in one week
- **Anything holding a credential** — the coordinator is provably credential-free
  and should stay that way
- **Ledger claim adjudication** — retraction and status discipline
- **The Critic/Referee pass** — or at minimum, whoever runs it must not also be
  the author

### 24. Could desktop control drive the loop?

**Mechanically, yes.** Every step is a keystroke in a known window:

| step | how |
|---|---|
| open dictator | window title from `chats.json` `window_title` |
| "check state" | type `where is everything at` |
| open worker | `window_title` |
| "check mail" | type the `opening` string from `chats.json` |
| **wait for completion** | ⚠ **this is the hard one** |
| return, "next" | typing is trivial |

**`chats.json` already contains everything an automation needs** — the window
title and the exact opening line, per worker. That was not built for automation
but it is exactly the right table.

### 25. What could go wrong with desktop control?

1. **"Wait for completion" is not observable.** A thinking window and a dead
   window look identical. There is no completion signal — `Status: DONE` is set
   by the worker and was **wrong on seven messages at audit time**.
2. **The desk window overwrites files while running.** A running GUI already
   silently reverted four committed repairs. Automation that opens windows while
   others run makes this class of bug more likely, not less.
3. **Never run two instances on one account** — the repo's own
   `MOVING_TO_LAPTOP.md` calls this the only irreversible mistake in a migration:
   both place orders, both act on the same position.
4. **Typing into the wrong window.** Titles are user-set and not unique by
   construction.
5. **Interrupting an autonomous run.** `CLAUDE.md` §2 has workers run an hour
   without stopping; a mid-run message queues behind the work.
6. **Permission prompts and mid-turn interjections** are not keystroke-shaped.
7. **Cost.** Every "check your mail" starts a session that may run for an hour.

### 26. Safety checks before automating

- **A real completion signal.** A worker writes a machine-readable marker
  (`COORDINATOR-STATE` with a run id, or a sentinel file) that the automation
  polls. **Do not trust `Status:`** — measured unreliable.
- **A liveness signal for chats.** `runners.py` already does this for background
  jobs by log mtime; nothing equivalent exists for windows.
- **Single-instance guard per worker**, before any window is opened twice.
- **Nothing touching `livedesk/`.** Real money, and it must be excluded by name.
- **A dry-run mode** that logs the keystrokes it would send.
- **A kill switch the user controls**, and a cap on sessions started per hour.
- **Idempotence:** re-sending `check your mail` must be harmless. It currently is,
  because mail is a file — that is a genuine property worth preserving.

### 27. Should trading stay isolated from Nexus?

**Yes for the trading content. No for the orchestration layer.**

`CLAUDE.md` §7 is explicit: four repos, never mixed, and `nexus` is the user's
own. `DICTATOR.md` §2 restates it — the dictator covers the five trading chats
and nothing else, confirmed by the user 2026-08-08.

**But the orchestration layer has no trading in it.** `mail.py` contains zero
trading references. `brief.py`, `where.py`, `scan.py`, `chats.py` are all
domain-free apart from a workstream list that is data, not code.

**The clean move is to extract the layer, not to merge the repos.** A shared
`orchestration/` package that trading and Nexus both depend on, with the ledgers,
guards and `runners.json` staying with trading.

### 28. What should be reused if extracted?

**Reuse verbatim:**
- `mail.py` — plus a collision-safe filename
- `brief.py` — the strongest piece; lock, isolation, atomic write, snapshot chain
- `chats.py` + `chats.json` schema
- `where.py`, `scan.py`, `detail.py` — with the workstream list as config
- `newprompt.py` + `prompt_template.md`
- `runners.py` + `runners.json` schema
- `dictator.bat`
- `test_no_money_no_network.py` — as a template for capability canaries
- `test_brief_isolation.py` — proves multi-writer isolation
- The `COORDINATOR-STATE` convention
- The HANDOFF / DECISIONS / PREREGISTRATION file conventions

**Reuse the pattern, rewrite the content:** `CLAUDE.md` (the *shape* — contract
auto-loaded per repo), `reflect.py` (Critic → Referee), `NEXT_DICTATOR.md`
(short handover carrying only what is not on disk).

**Do not extract:** ledgers, guards, `idea.py`, `ledger.py`, `kalshi_fees.py`.

### 29. What would a clean boundary look like?

```
  orchestration/                 ← generic, no domain content
    mail.py  brief.py  chats.py  where.py  scan.py
    runners.py  newprompt.py  reflect.py
    schemas: chats.json, runners.json, COORDINATOR-STATE
    tests: isolation, capability-canary
        │
        ├──────────────┬───────────────┬──────────────┐
        ▼              ▼               ▼              ▼
   trading/        nexus/          roblox/        <future>
   CLAUDE.md       CLAUDE.md       CLAUDE.md      own contract
   own mailbox     own mailbox     own mailbox    own mailbox
   own BRIEF.md    own BRIEF.md    own BRIEF.md   own brief
   LEDGER/GUARDS   own memory      own memory
   livedesk ⛔      (ChatGPT-led)
```

**Rules that make the boundary hold:**
- **One mailbox namespace per project.** Never a shared box.
- **`CLAUDE.md` stays per-repo.** It is the contract for *that* domain.
- **No cross-project mail.** A trading worker cannot address a Nexus worker; the
  human routes across.
- **`livedesk/` is outside every boundary.** Real money, Claude-only, named
  explicitly in whatever config an automation reads.
- **Agent identity is a row in `chats.json`**, so ChatGPT is just another worker
  with declared folders — no special case.

### 30. What is already built that should NOT be rebuilt?

1. **`brief.py`'s multi-writer isolation.** Lock, re-read-inside-lock, atomic
   write, section-scoped replace, immutable snapshot chain, and a test that
   proves a neighbouring section survives. **This is production-grade and took
   real measurements to get right.**
2. **The mailbox convention.** One file, one instruction, edited in place. No
   server, no schema migration, works over git, human-readable.
3. **`CLAUDE.md` as an auto-loaded contract.** 947 lines of accumulated
   corrections. Rebuilding it would cost every lesson in it.
4. **`runners.py`'s four states.** ALIVE / QUIET / FINISHED / CHECK-IT-BY-HAND,
   plus the explicit refusal to call a laptop recorder dead when it cannot be
   seen. **Tested: `laptop_is_never_called_dead`,
   `confirmation_is_never_dressed_up_as_liveness`.**
5. **The prior-work protocol.** "We tried that" banned, five required fields.
6. **The capability canary pattern** (`test_no_money_no_network.py`).
7. **The limits-before-features documentation convention** — tested by
   `the_docs_state_the_limits_before_the_features`.

---

## FILE-BY-FILE INDEX

### The read layer — how state is discovered

| file | lines | role |
|---|---|---|
| `coordinator/dictator.bat` | 79 | **the one command.** Runs where → runners → detail → chats check → scan → brief check |
| `coordinator/where.py` | 503 | Layer 1: the table. Parses `COORDINATOR-STATE`, git head/unpushed/dirty, marks guesses `~` |
| `coordinator/detail.py` | 303 | Layer 2: plain-English per worker, quoted from its `BRIEF.md` section |
| `coordinator/scan.py` | 426 | folder health: last commit, newest file, uncommitted, has HANDOFF/DECISIONS. Owns `WORKSTREAMS` |
| `coordinator/runners.py` | 623 | background-job liveness by log mtime. Four states. Detects registry drift |
| `coordinator/chats.py` | 255 | worker registry reader; `check` cross-validates `chats.json` against disk |

### The write layer — how work is assigned and published

| file | lines | role |
|---|---|---|
| `coordinator/mail.py` | 199 | **the assignment mechanism.** send / list / open / show. ⚠ no lock on numbering |
| `coordinator/brief.py` | 461 | **the outward channel.** Section-isolated writes, mkdir lock, atomic replace, immutable snapshots |
| `coordinator/newprompt.py` | 221 | bootstraps a new worker from `prompt_template.md`; copies the idea verbatim (tested) |
| `coordinator/idea.py` | 653 | **trading-specific.** Prior-work check across 653 claims in 7 ledgers |
| `coordinator/ledger.py` | 307 | **trading-specific.** Ledger table parser |
| `coordinator/reflect.py` | 254 | Critic (`--file`) then Referee (`--referee`) |

### State and registry files

| file | role |
|---|---|
| `coordinator/chats.json` | 9 workers: name, slug, folders, purpose, **opening line**, subjects, **window_title** |
| `coordinator/runners.json` | 11 background jobs: monitor kind, machine, heartbeat paths |
| `runners/runners.json` | the *other* registry — what runs on this machine. Deliberately not merged |
| `coordinator/mailbox/<slug>/NNN-*.md` | 119 messages, 10 boxes |
| `coordinator/prompts/SESSION-*.md` | generated bootstrap prompts |

### Protocol and contract

| file | lines | role |
|---|---|---|
| `CLAUDE.md` | 947 | **the contract. Auto-loaded into every session.** |
| `DICTATOR.md` | 385 | dictator manual; §1 = what it cannot do |
| `coordinator/COORDINATOR.md` | 539 | design + long limits list |
| `coordinator/NEXT_DICTATOR.md` | 132 | dictator handover — deliberately short |
| `coordinator/prompt_template.md` | 141 | new-worker bootstrap shape |
| `coordinator/REFLECT.md` | 135 | Critic/Referee checklist + nine worked errors |
| `HOW_THIS_WORKS.md` | 58 | short operating manual |
| `coordinator/README.md` / `WHERE.md` / `SCAN.md` | 125/104/54 | tool-level docs |

### Shared state

| file | lines | role |
|---|---|---|
| `STATUS.md` | 6,703 | **between** workers. Contradictions, threads, data inventory. No lock |
| `BRIEF.md` | 522 | **outward.** One section per worker, marker-delimited |
| `briefs/BRIEF-*.md` | many | immutable snapshots. Never edited after publication |
| `INBOX.md` | 41 | idea intake before routing |
| `LEDGER.md` / `GUARDS.md` / `SCOREBOARD.md` | 747/1341/629 | **trading.** Evidence memory |
| `<folder>/HANDOFF.md` | ×20 | per-workstream detailed state + `COORDINATOR-STATE` |
| `<folder>/DECISIONS.md` | ×19 | judgement calls taken without asking |

### Tests — what is actually enforced

| file | asserts |
|---|---|
| `test_no_money_no_network.py` | no network imports, no order-shaped tokens, no credential names anywhere in `coordinator/` |
| `test_brief_isolation.py` | writing one section leaves every byte of a neighbour intact |
| `test_brief_chain.py` | the snapshot chain is unbroken |
| `test_where_and_runners.py` | four runner states not two; laptop never called dead; confirmation never dressed as liveness; guessed cells marked; registry drift detected |
| `test_dictator.py` | prompt generator copies the idea verbatim; writes only inside `coordinator/`; docs state limits before features |

---

## WHAT ALREADY EXISTS

A working file-based multi-agent orchestration system, running nine workers in
production for roughly three weeks. Mailbox, worker registry, per-worker state
declarations, a section-isolated shared publication with a real lock, background-
job liveness monitoring, an auto-loaded protocol contract, a generated bootstrap
for new workers, immutable history snapshots, and a test suite enforcing the
guarantees that matter. **~4,000 lines of stdlib-only Python, no server, no
database, no network.**

## WHAT IS TRADING-SPECIFIC

The ledgers and their claim discipline; `idea.py` and `ledger.py`;
`common/kalshi_fees.py`; `runners.json` contents; `livedesk/` entirely;
`CLAUDE.md` §§6–9c; the paper-only canaries; `REFLECT.md`'s worked examples.

## WHAT IS REUSABLE

`mail.py` · `brief.py` · `chats.py`+schema · `where.py` · `scan.py` ·
`detail.py` · `newprompt.py`+template · `runners.py`+schema · `dictator.bat` ·
`reflect.py` · the `COORDINATOR-STATE` convention · HANDOFF/DECISIONS/
PREREGISTRATION conventions · both isolation and capability-canary tests · the
auto-loaded-contract pattern · the short-handover pattern.

**Roughly 80% of the orchestration layer is domain-free.**

## WHAT CHATGPT COULD PLUG INTO

Read everything today, unchanged. Write into: its own mailbox replies, new mail
to workers, `INBOX.md`, its own folder, its own `BRIEF.md` section via
`brief.py`. Needs: a row in `chats.json`, to read `CLAUDE.md`, to emit the mail
and state formats, and a collision-safe filing method.

**No changes to the Claude workflow are required for ChatGPT to read. Writing
needs exactly one fix (mail numbering) to be safe.**

## DESKTOP-CONTROL AUTOMATION FEASIBILITY

**Feasible for every step except "wait for completion", which is the whole
problem.** `chats.json` already carries window titles and exact opening lines.
What is missing is any observable completion or liveness signal for a chat
window — `Status:` is set by the worker and was wrong on seven messages at audit
time. Automation is safe only after a machine-readable completion marker exists,
a single-instance guard exists, and `livedesk/` is excluded by name.

## RISKS / FAILURE MODES

1. **A running process silently reverting committed files** — observed, cost days
2. **Mail numbering race** — becomes real the moment a second agent files mail
3. **`Status:` is unreliable** — seven false OPENs at audit time
4. **No stopped-worker detection** — a dead window looks like a busy one
5. **Stale self-reports** — structural; mitigated only by printing the age
6. **`STATUS.md` has no lock** — 6,703 lines, convention only
7. **Two runner registries** — drift is printed, not prevented
8. **Cross-project contamination** — observed once; convention only
9. **Ownership is honour-system** — nothing stops a worker writing elsewhere

## MINIMUM CHANGES NEEDED

**For ChatGPT to read: none.**

**For ChatGPT to write safely, three:**
1. Collision-safe mail filenames (timestamp or sender prefix, not a counter)
2. A `chatgpt` row in `chats.json` declaring folders
3. An explicit deny-list naming `livedesk/`, `common/kalshi_fees.py`, `briefs/`

**For desktop automation, three more:**
4. A machine-readable completion marker written by workers
5. A single-instance guard per worker
6. A dry-run mode plus a user-controlled kill switch

## THINGS WE SHOULD NOT TOUCH

`livedesk/` · `common/kalshi_fees.py` · `briefs/*` (immutable by design) ·
`brief.py`'s locking · `CLAUDE.md` (extend, never rewrite) · the ledgers'
claim-ID and retraction discipline · `test_no_money_no_network.py` ·
`runners.py`'s refusal to call a laptop recorder dead.

## RECOMMENDED NEXT STEP

**Do not extract anything yet. Do one measurement first.**

The single unknown that governs every downstream decision is **whether an agent
other than Claude can complete a full round trip through this system** — read
`CLAUDE.md`, read a mailbox, file a correctly-formatted message, and have the
existing `where.py` / `mail.py open` report it correctly, **with no change to any
existing file.**

**Proposed: give ChatGPT the slug `chatgpt`, a row in `chats.json`, and one
read-only task** — read `BRIEF.md` and file one mail to `coordinator` reporting
what it found. **If that round trip works untouched, the integration is a
configuration problem. If it does not, the failure point tells you exactly which
of the three minimum changes is actually required** — and that is worth knowing
before extracting 4,000 lines into a shared package.
