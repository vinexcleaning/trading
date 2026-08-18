To: livedesk
From: coordinator
Opened: 2026-08-18 00:13
Status: OPEN
Subject: URGENT - reset peak, floor 40 as a PAUSE not a stop, and he is about to trade the same account by hand

--- INSTRUCTION ---

**⚠ URGENT — he wants this live within minutes. His decision, verbatim in
intent, plus one danger he has not seen and must be told about before he
restarts.**

# 1. HIS DECISION

> *"reset it and make the new floor 40, if it goes below that then the bot
> doesnt trade till its above... it should calculate the value itself and if it
> goes back above 40 it should like turn on"*

**Three changes, and the third is a behaviour change, not a number:**

1. **Reset `peak_total_usd`** to the bot's current running total ($62.61). The
   35% trailing stop fired at $68.90 off a $106 peak; he is clearing it.
2. **`ACCOUNT_FLOOR_USD` 50 → 40.**
3. **⚠ THE FLOOR BECOMES A PAUSE, NOT A STOP.** Today `stopped()` is terminal.
   He wants: **below $40 → place nothing; back above $40 → resume by itself, no
   restart, no button.**

**Note that resetting the peak makes the two rules agree by accident:**
$62.61 × 0.65 = **$40.70**, against a $40 floor. **So make the trailing stop a
pause too** — otherwise it fires at $40.70 and terminally kills a tool he has
just asked to resume automatically. **Both cut-offs pause. Neither is terminal.**

**Log every transition on screen and in the log** — *"PAUSED, $38.20 is under
your $40 floor"* / *"RESUMED, $41.10 is back above your $40 floor"*. He must be
able to see why it was quiet.

# 2. ⚠ THE DANGER HE HAS NOT SEEN — HE IS TRADING THE SAME ACCOUNT BY HAND

> *"i will also be trading at the same time so it will likely go below 40 on my
> balance for periods of times before the cash comes back"*

**This breaks three things and he needs telling before he restarts, not after.**

### a) THE RECONCILIATION WILL ADOPT HIS OWN BETS AS THE BOT'S

Mailbox 011 made the account the source of truth on every refresh. **That code
reads positions off his Kalshi account.** He is about to put his own positions
in that account. **Unless it filters to markets this tool actually bet on, it
will adopt his manual trades into the ledger** — and then his personal wins and
losses land in the bot's record, its running total, its peak, and its P&L.

**This is the same shape as every ledger defect this week and it is worse,
because it corrupts the evidence rather than the display.**

**Required: reconcile ONLY against tickers this tool has an entry for.** A
position on the account with no matching entry is **his**, must be left
completely alone, and should be shown separately as *"not this bot's — yours"*.
**Never adopted. Never voided. Never counted.**

### b) SIZING IS A PERCENTAGE OF A BALANCE THAT IS NO LONGER ALL THE BOT'S

10% / 5% comes off `account_balance_usd`. **If he is holding $30 of his own
positions, that cash is already spoken for and the bot will size as though it
were free.** At minimum say so on screen. Better: size off *(cash − what his own
open positions cost)* if it can tell them apart after (a) — and if it cannot, it
must not guess.

### c) THE PEAK MUST NOT MOVE ON HIS RESULTS

`_bump_peak()` uses `running_total_usd()`, which is `account_start + the bot's
own realised`. **Keep it that way. Do not repoint it at the live account
balance** — his winnings would raise the bot's peak and his losses would trip
its stop. **Say in your reply that you checked this specific line.**

# 3. ⚠ WHAT MUST NOT HAPPEN ON RESTART — his other explicit worry

> *"we gotta make sure it doesnt enter the trades that were deferred late like
> last time"*

**Checked the ledger at 2026-08-18 04:12 UTC. It splits cleanly:**

| | starts | verdict |
|---|---|---|
| Baltimore Orioles 9 @ 42c | 2026-08-17 22:05 | **already started — VOID it** |
| Kansas City Royals 11 @ 63c | 2026-08-17 23:40 | **already started — VOID it** |
| San Francisco 16 @ 42c | 2026-08-18 22:40 | 18h away |
| St. Louis 7 @ 50c | 2026-08-18 22:40 | 18h away |
| Toronto 6 @ 44c | 2026-08-18 22:40 | 18h away |
| Milwaukee 10 @ 59c | 2026-08-18 23:40 | 19h away |
| Texas 6 @ 58c | 2026-08-19 00:05 | 20h away |

**So the good news he should be given: nothing queued is actually late.** Five
games are still 18–20 hours out.

**But the prices are stale**, captured before the stop fired. **So:**

1. **Void the two that have started.** Never place a bet on a game in progress.
2. **Re-read the live price on every deferred bet before placing it.**
3. **⚠ Refuse it if the price has moved against us by more than 3 cents from
   what the strategy saw**, and say so on the card in words: *"skipped — the
   price moved from 42c to 47c while the bot was stopped."*
4. **Re-size at the current balance**, not the balance when the signal fired.
5. **Do not release all five at once.** He has roughly $21 above a $40 floor;
   five bets at 5% of $62 is $15.50 and would put him near it in one burst.
   **Place them one at a time, re-checking the floor between each.**

**The 3-cent number is mine and it is a guess, not a measurement.** Say so to
him. Then measure the right threshold afterwards from `mlb-paper`'s tape and
correct it.

# 4. ORDER OF WORK — he is waiting

1. Void the two started games. **(seconds, and it is the only irreversible one)**
2. Peak reset + floor 40 + pause/resume.
3. Filter reconciliation to this tool's own tickers.
4. Stale-price refusal on the deferred five.
5. Everything else.

**Do 1–3 before he restarts if at all possible. If you cannot do 3 in time, tell
him plainly to hold off on his own trading until it is in** — that is a
one-sentence ask and it protects the record.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Lead with what you changed and
whether it is safe for him to trade alongside it.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

