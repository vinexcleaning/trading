# COORDINATOR.md

The design of the coordinator, and — stated before anything was built — **what
it cannot do.** Read the limits section first. It is the honest half.

---

## 1. The problem this exists to solve

Several Claude Code sessions run in this repo at once. None can see each other.
A separate chat (the **coordinating chat**) holds the whole picture and decides
what is worth doing next — but it reads this repo **over the public web**. That
gives it three hard handicaps:

1. **It cannot see disk.** Uncommitted and unpushed work is invisible to it.
2. **It cannot read `STATUS.md`.** That URL is cached frozen on its end.
   `STATUS.md` is also 3,122 lines, which is not a briefing.
3. **It cannot write anything.** It can only talk to the user.

So every instruction it produces has to be **copy-pasted by the user** from that
window into each session window, and every result copy-pasted back. With five
threads that is the bottleneck. It is not a technical bottleneck — it is the
user doing routing by hand.

## 2. What the coordinator is

**A Claude Code session that runs in `coordinator/` and does two jobs.**

### Job A — collapse many reports into one page

`BRIEF.md` at the repo root. **One file, one section per project.** Every
session overwrites **only its own section**, mechanically, through one command
that cannot reach another section. The coordinating chat reads **one URL**
instead of hunting through a growing pile of `BRIEF_*.md` files and guessing
which is newest.

### Job B — collapse many pastes into one paste

A **mailbox**. The user pastes an instruction **once**, into the coordinator
session. The coordinator files it as a Markdown message addressed to each
session that needs it. Each session finds it and replies **in the same file**.

The user goes from *"paste this into five windows and paste five answers back"*
to *"paste this once"*.

### And one thing only a session on disk can do

The coordinator reads the **actual filesystem** — uncommitted changes, unpushed
commits, file timestamps, what each project last touched. It reports what the
coordinating chat is **blind to**, which is exactly the class of thing that goes
wrong silently.

---

## 3. What it CANNOT do

**This section is the point of this document.** Every item here is a real limit,
not a to-do.

### It cannot deliver a message. It can only leave one.

There is **no way for one Claude Code session to interrupt another.** No shared
memory, no signal, no notification. The coordinator writes a file into a folder
and that is the end of its power.

A message is delivered when the receiving session **looks**. That happens:

- **at the start of a session** — because `CLAUDE.md` now tells every session to
  check its mailbox first, and `CLAUDE.md` is auto-loaded; or
- **when the user says "check your mail"** in that window.

**A session that is already mid-task will not see a new message until it
finishes.** If something is urgent, the user still has to type into that window.
The mailbox removes *routine* relaying, not *urgent* relaying.

### It cannot start, stop, or steer a running session

It cannot launch a Claude Code window, cannot cancel a task, cannot answer a
permission prompt, cannot see another session's transcript. The user opens
windows. Always.

### It cannot make the coordinating chat see fresh data

The coordinating chat reads GitHub. Therefore:

- **Unpushed work stays invisible.** The coordinator will *tell you* it is
  unpushed, which is the fix — but it cannot push another session's work for it,
  because that would cross into another session's folder.
- **`BRIEF.md` will eventually be cached too.** It is a new filename today, so
  it is not cached now, but the same freeze that hit `STATUS.md` can hit it.
  Two mitigations, both in §7: a freshness stamp the chat can self-check, and a
  cache-busting URL.

### It cannot judge the trading work

It reports **state**, not **truth**. It will say *"tennis last committed 4 hours
ago and has 2 open questions"*. It will never say *"the tennis result is real"*.
Every claim in `BRIEF.md` is written by the session that did the work and is
that session's responsibility. The coordinator moves text; it does not audit it.
[LEDGER.md](../LEDGER.md) and [GUARDS.md](../GUARDS.md) are where claims get
tested, and neither is replaced by this.

### It cannot resolve a contradiction between two sessions

If two sections of `BRIEF.md` disagree, the coordinator **surfaces the
disagreement**. Deciding which measurement is right requires reading both
codebases, which is the sessions' job — per `CLAUDE.md` §5, the session that
notices flags it and says which it trusts and why. The coordinator makes the
contradiction **visible**, which is the part that has failed before.

### It cannot touch money. By construction.

- **No credential is ever read, stored, or passed on.** There is no key, no
  `.env`, no token anywhere in `coordinator/`.
- **No network call of any kind.** Not to an exchange, not to a broker, not to
  anything. Local files and local `git` reads only.
- **No order-placing code, and none can be added quietly.**
  `coordinator/tests/test_no_money_no_network.py` fails the moment any
  coordinator file imports a network library or contains order-shaped
  vocabulary. It is a canary in the style of [GUARDS.md](../GUARDS.md): it
  plants nothing and asserts nothing about intent — it just makes the change
  loud.

If the coordinator is ever asked to place a trade, the correct behaviour is to
refuse and say so in `BRIEF.md`.

### It cannot write another project's section, files, or folder

`brief.py` takes a slug and can only rewrite the text between that slug's two
markers. It has no mode that rewrites the whole file. This is enforced in code,
not by convention, because convention already failed here once — the fee formula
went from 3 copies to 17 while the rule was only a convention.

### It cannot recover from being ignored

If sessions stop writing their `BRIEF.md` section, the page silently goes stale.
Mitigation, not cure: every section carries a **last-written timestamp**, and
the scan flags any section older than its project's last commit — i.e. *"this
project did work it has not told you about"*. That catches neglect. It does not
prevent it.

---

## 4. The pieces

| File | What it is |
|---|---|
| `../BRIEF.md` | **The output.** One page, one section per project. The only thing the coordinating chat needs to read. |
| `brief.py` | Writes exactly one section of `BRIEF.md`. Locked, atomic, section-scoped. |
| `scan.py` | Reads every project's state off disk. Writes `SCAN.md`. |
| `mail.py` | Creates and lists mailbox messages. |
| `mailbox/<slug>/` | Messages addressed to that project. Markdown. Edited in place to reply. |
| `SCAN.md` | Latest machine-read state of every project. Regenerated, never hand-edited. |
| `start.bat` | **The one command.** Runs the scan, refreshes the stamp, prints a plain-English digest. |

## 5. `BRIEF.md` — how one section per project is enforced

The file is plain Markdown with invisible HTML-comment markers:

```
<!-- SECTION:tennis -->
## Tennis — paper test
...whatever the tennis session wrote...
<!-- /SECTION:tennis -->
```

Writing is one command:

```
py -3 coordinator\brief.py write tennis --file mysection.md
```

What that command does, in order:

1. Takes a **lock** (`coordinator/.brieflock/`, created with `mkdir`, which is
   atomic on Windows). Waits up to 60 s, then fails loudly rather than racing.
2. **Re-reads `BRIEF.md` from disk** — so it picks up any section another
   session wrote while this session was thinking.
3. Replaces **only** the bytes between that slug's two markers. If the slug has
   no section yet, it appends a new one. Every other byte of the file is copied
   through untouched.
4. Writes to a temp file and **atomically replaces** `BRIEF.md`.
5. Releases the lock.

There is deliberately **no** "write the whole file" mode. The failure this
prevents — one session flattening another's work — has already happened twice in
this repo through `git add -A`.

## 6. The mailbox — how an instruction reaches a session

A message is **one Markdown file** and needs no tooling to answer:

```
coordinator/mailbox/tennis/001-stop-dating-briefs.md
```

```
To: tennis
From: coordinator
Opened: 2026-08-07 13:12
Status: OPEN
Subject: Stop writing BRIEF_TENNIS.md

--- INSTRUCTION ---
...plain English...

--- REPLY (the tennis session writes below, and sets Status above) ---
```

The receiving session edits `Status: OPEN` to `Status: DONE` (or `BLOCKED`) and
writes under the reply line. That is the whole protocol. **No script to run, no
format to learn** — which matters, because a session that has to learn a tool
will skip it.

`scan.py` counts `OPEN` versus `DONE` per project, so an ignored instruction is
visible rather than lost.

> **One documented exception to `CLAUDE.md` §5** ("work only inside your own
> folder"): a session may write inside `coordinator/mailbox/<its-own-slug>/`,
> and nowhere else in `coordinator/`. Replying to a message is not reaching into
> someone else's work.

## 7. Beating the cache

Two things, both automatic:

1. **A freshness stamp at the top of `BRIEF.md`** — the commit hash it was
   generated at, and the time. The coordinating chat can compare that hash
   against the repo's commit list, which is a different URL. If they disagree,
   it is reading a cached copy and **knows it**. That is the whole trick: a
   stale page that announces its own staleness is not dangerous.
2. **A cache-busting URL**, printed by `start.bat` each run:
   `https://raw.githubusercontent.com/vinexcleaning/trading/main/BRIEF.md?v=<hash>`
   The query string changes every commit, so it is a new URL to any cache. Give
   the coordinating chat the freshly printed one.

## 8. How the user actually uses it

**Starting it:** open a Claude Code session in this repo and say

> run the coordinator

The session runs `coordinator\start.bat`, reads the digest, and reports in plain
English. Nothing else is required. There is nothing to install and nothing to
edit.

**Sending an instruction to a session:** paste it into the coordinator session
and say who it is for. The coordinator writes the mailbox message. The user
opens that session's window and says "check your mail" — or just waits, because
the next session start reads it automatically.

**Giving the coordinating chat the picture:** hand it the URL printed by
`start.bat`.

## 9. Deliberate non-goals

- **Not a dashboard.** No web server, no port, no process to leave running.
- **Not a scheduler.** It runs when asked. There is no daemon.
- **Not a replacement for `STATUS.md`.** `STATUS.md` stays the detailed channel
  *between sessions*. `BRIEF.md` is the short channel *out to the coordinating
  chat and the user*. Different audiences, different lengths.
- **Not a source of truth.** Everything it prints is derived from git and the
  filesystem, and is regenerated. Delete `SCAN.md` and nothing is lost.
