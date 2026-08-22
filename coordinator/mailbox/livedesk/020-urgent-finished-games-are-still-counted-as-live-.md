To: livedesk
From: coordinator
Opened: 2026-08-22 13:59
Status: OPEN
Subject: URGENT - finished games are still counted as live, and his total is 20 dollars off

--- INSTRUCTION ---

**⚠ THE LEDGER IS CARRYING FINISHED GAMES AS LIVE POSITIONS. He read his account
again and caught it, and I had already repeated the wrong number back to him as
if he were up money when he is down $15.**

# 1. THE NUMBERS

| | |
|---|---|
| he reads: cash | **$63** (ledger $63.06 — matches) |
| he reads: positions | **$28**, of which **$5 is his own tennis bet** |
| he reads: games active | **7**, and **only ONE is live** (Toronto vs New York) |
| **his real total** | **~$91** against a $106 start — **down about $15** |
| **the ledger says riding** | **$48.70 across 11** |
| **I reported to him** | **$111.76, up $5.76.** Wrong by roughly $20 |

# 2. THE CAUSE — 8 OF THE 11 HAVE ALREADY STARTED

Sorted by start time against the clock:

```
  Kansas City   $6.15  awaiting-settlement  started 08-20 18:10
  LA Angels     $5.05  awaiting-settlement  started 08-21 00:10
  Philadelphia  $5.02  awaiting-settlement  started 08-21 22:40
  Kansas City   $2.99  open                 started 08-22 00:10
  San Diego     $2.74  awaiting-settlement  started 08-22 01:40
  Pittsburgh    $3.07  open                 started 08-22 02:10
  Seattle       $2.79  open                 started 08-22 02:10
  New York      $3.35  open                 started 08-22 17:35   <- his one live game
  LA Angels     $7.11  open                 not yet
  San Francisco $3.31  open                 not yet
  Baltimore     $7.12  open                 not yet
```

**Three have not started. One is live. Seven have finished and are still counted
at what they cost, as though the outcome were unknown.**

**This is not the phantom-position defect from last week.** These were real
bets. **The failure is that nothing retires them when the game ends.** Four
still carry status `open` on games that started hours or days ago, which means
the settlement path is not even being attempted on them.

# 3. ⚠ WHY THIS IS WORSE THAN A DISPLAY BUG

1. **It over-states what is at risk** — $48.70 against a real ~$23.
2. **It hides the result of seven settled bets.** His profit-and-loss is frozen
   at the moment of purchase. The record cannot tell him how he is doing, which
   is the one thing it exists for.
3. **The wins have already paid out in cash** — that is why his cash reads $63
   while the ledger's own settled list has not moved. **The money is in the
   account and the reason for it is not in the record.**
4. **It feeds the stop.** `at_risk_usd()` sums status `open`, and four finished
   games still carry it. **The tool is subtracting money that is no longer at
   risk when it decides whether to stop.**

# 4. WHAT TO BUILD

1. **A game that has started is not an open position for settlement purposes.**
   Once `starts_utc` has passed, poll for the result rather than waiting to be
   told.
2. **Settle from the account, on every refresh.** A market Kalshi reports as
   settled becomes `won` or `lost` with the real profit, taken from the account
   and not computed.
3. **`open` must mean "not yet started".** Anything past its start time is
   `live` or `settled` and never `open` — the current mixing is what let four of
   them sit unnoticed.
4. **Show the age of the oldest unsettled position on screen.** A game that
   finished two days ago and is still counted should be visible without him
   reading Kalshi. **Every single one of these has been found by him, not by the
   tool — this is the fifth time.**
5. **A test with a market whose start time has passed**, asserting it is not
   counted as at-risk and is chased for settlement.

# 5. AND FIX WHAT IT REPORTS

**`riding` must be positions that are genuinely undecided.** Show the finished-
but-unsettled ones separately and say so plainly: *"3 games waiting on results
from Kalshi"*. **Never fold them into a total that reads as his current
worth** — that is precisely the number I got wrong.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Lead with what his real total is,
and say how many bets the tool still cannot account for.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

