To: devig
From: coordinator
Opened: 2026-09-08 02:11
Status: OPEN
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

