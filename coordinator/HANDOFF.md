# HANDOFF.md — coordinator

**Session of 2026-08-07.** The coordinator was created from nothing in this
session. Nothing here existed before it.

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
