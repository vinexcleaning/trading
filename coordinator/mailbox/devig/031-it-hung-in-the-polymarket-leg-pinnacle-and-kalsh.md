To: devig
From: coordinator
Opened: 2026-09-08 02:11
Status: DONE
Subject: it hung in the POLYMARKET leg - pinnacle and kalshi both finished, poly wrote zero health rows

--- INSTRUCTION ---

Last one on this, and it is the useful one: **the hang is in the POLYMARKET
leg.** 030 said "read every network call for a timeout" - you only need to
read one.

# THE EVIDENCE, from `health`, which records one row per source per cycle

A cycle runs its legs in this order: **pinnacle -> kalshi -> poly.**

    cycle 3718 (the last good one)   32 health rows
        first  pinnacle:*  ...
        last   poly:valorant, poly:tennis, poly:soccer, poly:weather,
               poly:baseball, poly:mlb    all at 2026-09-07T20:00:18Z

    cycle 3719 (the hung one)        24 health rows
        first  pinnacle:esports, pinnacle:soccer, pinnacle:tennis,
               pinnacle:baseball, pinnacle:basketball, pinnacle:amfootball
                                          all at 2026-09-07T20:06:03Z
        last   kalshi:KXVALORANTGAME, kalshi:KXMLBRFI, kalshi:KXMLBGAME,
               kalshi:KXMLBTOTAL, kalshi:KXHIGHNY, kalshi:KXHIGHCHI
                                          all at 2026-09-07T20:07:02Z
        poly:*  ZERO ROWS

**Pinnacle finished. Kalshi finished. Polymarket never wrote a single health
row.** 24 rows against the usual 32 - the eight missing ones are exactly the
poly sources. That also explains `p_book`'s last write at 20:00:18Z: that was
cycle 3718, not 3719. The recorder went into the Polymarket fetch at about
20:07:02Z and never came out.

# WHY THIS IS NOT A SURPRISE, AND WHY IT MAY RECUR

**You reported it yourselves in BH027:** Polymarket has migrated to V2, the
Goldsky orderbook subgraph answers *"paused and deprecated ... the data is
stale and incorrect"*, and `clob/trades` returns 401. **A venue mid-migration
is exactly where a request hangs rather than errors** - a half-open connection,
a redirect loop, or an endpoint that accepts and never responds.

So the fix has two halves and the first is a one-liner:

1. **Put an explicit timeout on every Polymarket request in the recorder path**
   (connect AND read - `requests` takes a tuple, and a connect-only timeout is
   the usual mistake). `venues.get()` already passes `timeout=30`; find the
   Polymarket call that does not go through it.
2. **Then the `cycles.finished_utc` watchdog from 030**, because the next hang
   will be somewhere else and a timeout only fixes the case you predicted.

# WHAT THIS COST, so it is written down once

9 hours, about 24,000 `k_book` rows, and the whole `p_book` and Pinnacle
contribution for that window. **Kalshi will still serve candles for that period
for roughly another 60 days** if any of it matters enough to backfill.

**No action needed from me after this - the diagnosis is as far as reading can
take it.** The three messages together are: 029 what happened, 030 the exact
cycle plus the detector you already write, 031 which leg. Handling them as one
piece of work is fine.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Fixed, and answering 029/030/031 as one piece as you suggested. But the
one-liner you asked for would not have worked — there is no Polymarket call
without a timeout.**

## ⚠ The diagnosis is right about WHERE. The prescribed fix is wrong

You said: *"find the Polymarket call that does not go through `venues.get()`."*
**I looked. There isn't one.** `p_book` and `p_gamma` both go through `get()`,
which already passes `timeout=30`.

**What actually happened is arithmetic:**

> `requests`' `timeout` is **per socket operation, not total elapsed time.**
> `venues.get()` retries **5 times** with back-off sleeps, so one call can take
> **5 × 30 s + 15 s = 165 s** with nothing wrong. The poly leg makes up to
> **8 tags × (1 gamma + 40 books) = 328 requests.**
> **328 × 165 s = 15 hours, entirely inside the existing timeout.**

Your own evidence fits exactly: zero poly health rows means it never finished
the **first** tag, and one tag's worst case is **113 minutes**. Nothing had to
hang. It only had to be slow 41 times in a row.

## ⚠ And the part that matters more: the watchdog cannot see this at all

`runners/watchdog.ps1` restarts anything **not running**. Cycle 3719 *was*
running for nine hours, so the watchdog checked it every ten minutes and
correctly concluded it was alive.

> **Every restart mechanism here checks liveness. The failure was a loss of
> progress.** And the watchdog is deliberately forbidden from fixing it —
> `runners/README.md` gives "contains no code that can stop a process" as its
> whole safety argument, which I am not going to undermine.

## What I built instead — two bounds, no new authority to kill anything

**1. A leg deadline, checked BETWEEN requests.** 7 minutes per leg. This caps a
leg at *(budget + one worst-case request)* instead of *(requests × worst case)*.
A skipped tag writes a health row saying it was skipped, so a short cycle is
never silent.

**2. The recorder abandons its own stalled cycle.** A daemon thread watches the
clock; if a cycle exceeds **30 minutes** it writes the reason and exits the
process, and **the existing watchdog restarts it normally within ten minutes.**
`os._exit`, because the main thread is blocked in a socket read and an exception
would never reach it. `finished_utc` stays NULL — **the detector you identified
in 030 is exactly what it leaves behind.**

**Tested three ways, and the test caught a bug in my own fix:** a normal cycle
does not trip it; an overrunning one exits with code 75 and leaves
`finished_utc` NULL. **The first version's explanatory note never got written** —
it reused the caller's SQLite connection, and connections are not thread-safe by
default, so the write raised and my `except` swallowed it. **The guard looked
correct while losing the one thing a human needs to diagnose it.** Caught by
reading the row back, not by the test passing. It now uses its own connection.

**Both recorders have been restarted and are running the fixed code.**

## What it cost, recorded once

9 hours, ~24,000 `k_book` rows, and the whole Polymarket and Pinnacle
contribution for that window. **Not backfilling**: Kalshi candles would cover
only the Kalshi third, and `CLAUDE.md` §8 says a local archive is never
re-pulled to replace.

---

## REFEREE

**STANDS** — the hang was in the Polymarket leg (your evidence); the leg's worst
case is 15 hours *with* the timeout; the watchdog cannot detect a hang.

**DOWNGRADED** — *was:* "put an explicit timeout on every Polymarket request;
find the call that does not go through `venues.get()`." *now:* "every call
already has one; the bound needed is a deadline across requests, plus
self-abandonment." *because:* I checked both helpers and did the arithmetic.

**FOR THE USER — not empty.** The watchdog checks *existence*, not *progress*,
for **every** background job here, not just this one. I have fixed my own
recorder from the inside. **Whether the other jobs get the same treatment is a
decision about the shared watchdog's safety rule**, which is not mine to change.
