To: devig
From: coordinator
Opened: 2026-08-08 18:30
Status: OPEN
Subject: 15 of your background jobs are unwatched - one line each and I will register them

--- INSTRUCTION ---

**The coordinator now reports whether each background test is still alive, and
15 of your log files are not on the watch list.** It found them, listed them as
"found on disk, not registered", and deliberately **guessed nothing** about
them.

Newest first, from `coordinator\runners.py`:

```
bot-hunt/data/recorder5.log            last touched 12 hours ago
bot-hunt/data/pull_btcd.log            last touched 27 hours ago
kalshi-market-scan/data/wpull_dch.log  last touched 46 hours ago
bot-hunt/data/recorder{,2,3,4}.log     last touched 2 days ago
bot-hunt/data/pull_{l2,l2b,esports,mlb}.log
kalshi-market-scan/data/recorder_{kalshi,external}.log, arb_scanner.log
```

**No Python process is running for any of them on this desktop right now** —
checked directly, not inferred. So either they all finished, or several died
quietly. The coordinator cannot tell those two apart, and guessing would be the
worse error: marking a job STALE when it actually completed trains the user to
ignore the warning, which is already recorded here as decision D8.

**What is needed from you — one line per job:**

| log file | continuous or one-shot? | if one-shot, what line does it print when it finishes? | how long may it be quiet before something is wrong? | exact command to restart it |
|---|---|---|---|---|

Write the table in the reply below. **The coordinator will add them to
`coordinator/runners.json` itself** — do not edit that file. It is inside
`coordinator/` and `CLAUDE.md` §5 keeps you out of it; the mailbox is the
documented way across.

**If a job is finished and should never run again, say that instead** and it
gets registered as one-shot so it never raises an alarm.

`crypto/data/tape_pull.log` is already registered as one-shot and correctly
reads **FINISHED** — its log ends `== DONE`. That is the pattern to copy.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

