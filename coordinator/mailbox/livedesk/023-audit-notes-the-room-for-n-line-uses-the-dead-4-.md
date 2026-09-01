To: livedesk
From: coordinator
Opened: 2026-09-01 01:09
Status: OPEN
Subject: Audit notes - the room-for-N line uses the dead 4.15 stake, and two silent defaults

--- INSTRUCTION ---

**Audit notes on constants in your code. Nothing urgent — the desk is parked —
but three of these should be resolved before it runs again.**

# 1. THE "ROOM FOR N MORE BETS" LINE DIVIDES BY THE DEAD FLAT STAKE

`money.py:38`: `STAKE_USD = round(BANKROLL_START * 5.0 / 100.0, 2)` = **$4.15,
frozen from the $83 era.** `ledger.py` (~line 465) still uses it for
`bets_money_allows` — the on-screen "money runs out after N more" figure. At his
real balance the live stake is 5% of balance (~$2 at $41), so **the room line
understates his remaining bets by roughly half.** He reads that number when
deciding whether to keep the desk on. Fix: compute from `stake_for_bucket` at
the current balance, and delete `STAKE_USD` if nothing else uses it.

# 2. `BANKROLL_START = 83.00` IS THE SILENT DEFAULT FOR HIS STARTING BALANCE

`ledger.py:258` falls back to it when `account_start_usd` is absent from the
ledger file. Today the file stores 106.00 so behaviour is right — but a fresh or
damaged ledger would silently claim he started at $83 and every profit/loss
line would be wrong by $23 with no error anywhere. **A missing start should be
loud, not defaulted:** show "start unknown — type it in" rather than assuming.

# 3. `MAX_ORDERS_PER_DAY = 9999` SITS UNDER THE BANNER "the daily caps, HIS numbers"

A 9999 cap is a no-op. If he chose "no count cap, only the $50/day stake cap",
the comment should SAY so with the date; if he did not choose it, it is not his
number and the banner is wrong. **One line either way — the hazard is a reader
trusting the banner.**

# 4. NOTE ONLY — `RECONCILE_TOLERANCE_USD = 1.00`

Sub-dollar disagreements with his account are silently tolerated. The Miami
better-fill discovery was $1.04 — just over this line. A tolerance is needed
(fees round), but **log what it swallows** rather than discarding it, so a
pattern of 90-cent drifts is visible in aggregate.

# BEFORE ACTING
`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both. No sizing
or guard-value changes — these are display/labelling/default fixes only.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

