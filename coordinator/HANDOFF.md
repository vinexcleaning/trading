# HANDOFF.md — coordinator

<!-- COORDINATOR-STATE
doing: the coordinator now answers "where is everything at" and watches whether each background test is still alive
left: get the other four chats to add their own COORDINATOR-STATE block, so their two columns are quoted instead of guessed
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
