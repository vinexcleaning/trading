# HANDOFF.md — coordinator

<!-- COORDINATOR-STATE
doing: built the dictator chat - the one window the user talks to. Two-layer report, a prior-work check that cannot say "we tried that", and a name for every chat
left: four folders still have no HANDOFF.md and five none DECISIONS.md (named in CLAUDE.md §10); the owning chats have to create them
needs: no
-->

**Session of 2026-08-07, extended 2026-08-08.** The coordinator was created from
nothing in the first session. The second turned it into something that can be
talked to as a main chat — see §"2026-08-08" at the bottom.

## State: built, tested, working end to end

- `coordinator\start.bat` runs and prints a plain-English digest. Verified.
- Both tests pass:
  - `tests/test_brief_isolation.py` — 12 checks, proves one session cannot
    overwrite another's `BRIEF.md` section.
  - `tests/test_no_money_no_network.py` — no network imports, no credentials,
    no order-placing vocabulary, `subprocess` only ever runs `git`, and only
    read-only git verbs.
- `BRIEF.md` exists at the repo root with five sections and a freshness stamp.

## One real bug was found and fixed during the build

`brief.py` checked `if not body` **after** `body.strip("\n")`, so a body of
whitespace-only text passed the empty check and silently blanked a section.
The isolation test caught it. Fixed: the check is now `if not body.strip()` and
runs first. Worth knowing because it is exactly the class of failure this whole
design exists to prevent.

## What is NOT done and is waiting on other sessions

**Four mailbox messages are OPEN and none has been answered**, because none of
those sessions has started since they were filed:

`coordinator/mailbox/{tennis,mlb,devig,signal}/001-...md`

They tell each session the new convention. Until each replies `DONE`, assume it
is still writing `BRIEF_*.md` and does not know the mailbox exists. The three
`BRIEF_*.md` redirect stubs are the backstop for that.

## Known gaps, in priority order

1. **No read receipt.** `Status: OPEN` is the only signal. A session that reads
   a message and ignores it looks identical to one that never looked. Accepted
   deliberately (DECISIONS D3) — a reply protocol with a tool would be skipped.
2. **Seven folders belong to no workstream** — `discord-trades-export`,
   `kalshi-chat-audit`, `kalshi-inplay-bot`, `polymarket-tennis-copy`,
   `ptis-polymarket`, `soccer`, `wallet-copy-study`. They are scanned and listed
   in `SCAN.md`, just not summarised on the one page. Add them to `WORKSTREAMS`
   in `scan.py` if any becomes live. **The scan says this out loud every run** so
   it cannot become a silent omission.
3. **The `signal` section was written by the coordinator, not by that
   workstream** (DECISIONS D7). It is labelled as such. Replace it the moment a
   real session works there.
4. **`BRIEF.md` will be cached and there is no way to stop it.** Handled, but
   read this: the `?v=` cache-buster I originally shipped **does not work** —
   the fetcher keys on path and discards query strings, tested by the user.
   Retracted in DECISIONS D9. Replaced by `briefs/BRIEF-<date>-<NN>.md`, one
   permanent path per changed generation, each page naming the next one's path.
   **The new failure mode is a snapshot that is not pushed:** the next link
   404s and a walking reader concludes a stale page is current. `scan.py`
   reports it first; `brief.py check` fails on any gap. Push `briefs/`.
5. **Lock contention is untested under real concurrency.** The lock is
   `mkdir`-based with a 60 s wait and a 300 s stale-break. Three sessions have
   never written at the same instant yet. If it ever fails it fails loudly and
   writes nothing, which is the correct direction.

## The next concrete step

When a sibling session next starts, confirm it (a) read its mailbox and (b)
wrote its section with `brief.py write`. Until at least one has, the convention
is documented but unproven.

---

## 2026-08-08 — the coordinator can now be the main chat

The user's ask: *"upgrade the coordinator so it can act as my main chat"* — read
every project's state off disk and explain it in plain English; answer "where is
everything at" with a table; say whether each background test is alive or stale
in that same table; take a new idea in plain English and write the prompt for a
new session; be one command. And: **write what it cannot do before you build.**

**The limits were written first**, into `COORDINATOR.md` §3b, and a test
(`tests/test_where_and_runners.py::test_the_docs_state_the_limits_before_the_features`)
fails if any of them is later deleted from the document.

### What was added

| File | What it does |
|---|---|
| `where.py` | The table. Writes `WHERE.md`. |
| `runners.py` | ALIVE / STALE / FINISHED / NEVER RUN per background test. |
| `runners.json` | The watch list. Hand-written; anything absent is unwatched. |
| `newprompt.py` | Plain-English idea → a prompt for a fresh session. |
| `prompt_template.md` | The text of that prompt. Edit this, not the module. |
| `tests/test_where_and_runners.py` | 60-odd checks, all passing. |

`start.bat` is unchanged as **the one command** and now leads with the table.

### The state of the table right now

**1 of 5 chats has declared its own state.** Only `coordinator` — the other four
have a mailbox message asking for four lines. Until they answer, their two
middle columns are guesses from `HANDOFF.md`, marked `~`, and the run says so
out loud. **If they ignore it, the table stays mostly guesses.**

### Three things found by looking at output, not by writing tests

1. **The guesser described the wrong project.** Ordering `HANDOFF.md` files by
   modification time put `kalshi-tennis` — an old analysis folder — ahead of
   `tennis-paper-forward`, the thing actually running. Registry order encodes
   which folder *is* the workstream. Fixed, tested.
2. **A bare `next` in the heading pattern** matched *"what the next session
   should do"* and put a sentence about reading order into "what's left". Fixed,
   tested.
3. **`crypto`'s tape pull is FINISHED, not dead** — its log ends `== DONE`. A
   two-state ALIVE/STALE check would have shouted at it forever. That is why
   there are four states. Same reasoning as D8.

### One thing that is a real hole and is not papered over

Two recorders run on the **laptop**, on `C:\Users\gianf\...` paths that do not
exist here. They read **"can't see from this machine"** and never STALE. If one
of them dies, **nothing here will notice.** They are recording the one dataset
in this repo that cannot be re-pulled.

### The next session's single next thing

**Check whether the other four chats answered their mailbox message.** If they
did, `py -3 coordinator\where.py` should report 5 of 5 declared and no `~`. If
they did not, that is the finding — say it plainly rather than improving the
guesser, which is polishing a fallback nobody should be relying on.

Second: **`devig` was asked to classify 15 unwatched log files** (mailbox 007)
as continuous or one-shot. When it answers, add them to `runners.json`. Nothing
running on this desktop writes to any of them right now, and the coordinator
deliberately guessed nothing about which of them died and which finished.

---

## 2026-08-08, third session — the dictator chat

**What was asked:** build the one window the user talks to. It does no project
work. It reports in two layers, it takes a plain-English idea and files it to
the right chat, and it names every chat it creates. Above all it may never say
*"we tried that"*.

**What is on disk now**, all inside `coordinator/` except the manual:

| File | What it does |
|---|---|
| `../DICTATOR.md` | The manual. Section 1 is what it CANNOT do and was written before the code. |
| `dictator.bat` | The one command. Layer 1 table, then layer 2 detail, then runners, names, scan, brief, mail. |
| `detail.py` | Layer 2. Per chat: what it tried, the sample, the dates, what came out, what was withdrawn and why. Nothing recomputed. |
| `idea.py` | The prior-work check, and filing an idea into a chat's mailbox. |
| `idea_template.md` | What the receiving chat is told to do. Lives in a document because it names a git verb that writes. |
| `ledger.py` | One parser for `LEDGER.md` and the three ledgers it points at. 342 claims. |
| `chats.py` / `chats.json` | Every chat's name, short code, folders, subjects and opening line. |
| `tests/test_dictator.py` | Six canaries, including one that fails if the report drops any of its six required fields. |

**Three defects this build found in its own first output**, all now tests:

1. It buried **B023** — the exact row whose misuse motivated the build.
   Fixed with a per-word pass, rare-word weighting, and claim-text weighting.
2. It routed *"de-vig a retail bookmaker on baseball"* to **tennis**, because
   the de-vig ledger rows have no project column and the tennis ones do.
   Fixed with two separate routing signals and an honest "cannot tell".
3. An escaped pipe (`max\|t\|`) inside a `LEDGER.md` cell was shifting seven
   rows' columns, so their STATUS could not be read. Fixed in the parser.

**Also this session:** every project folder was read and the shared rules
written into `CLAUDE.md` — a new **§10** (what each folder is, which four files
every folder must have, who is missing one, pre-registration naming, which
Python where, the two runner registries) and a new rule at the top of **§2**:
a new idea gets a plan and a pause before any work starts, and disagreement
must name what was tested rather than assert it.
