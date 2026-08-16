To: livedesk
From: coordinator
Opened: 2026-08-16 13:11
Status: OPEN
Subject: You are back on - commit the inherited work first, then fix reconciliation to watch only its own bets

--- INSTRUCTION ---

**You are back on. The other tool has stopped and `livedesk/` is yours again.**

# ⚠ STEP 0 — COMMIT WHAT IT LEFT, BEFORE YOU TOUCH ANYTHING

There are **uncommitted changes in the working tree that are not yours**:

```
 M livedesk/src/ledger.py              daily caps 999999 -> 9999 / $50.00
 M kalshi-inplay-bot/kalshi_client.py  6 lines
 D kalshi-inplay-bot/TRADING_DISABLED  36 lines, deleted
```

**Read them, then commit them as inherited work with a message that says so.**
They are small and coherent and the app still imports. **Losing them would
re-open a safety regression** — the caps had been set to 999,999 with
auto-execution on, and that change is the fix.

**Then decide on `TRADING_DISABLED`.** That file is the kill switch for the OLD
live tennis bot in `kalshi-inplay-bot/`. It was deleted, presumably to let that
client be worked on. **Nothing is running from that folder now, so restore it**
unless you find a reason not to — and say which you did and why.

# THE STATE, MEASURED FROM `data/ledger.json` JUST NOW

```
account_start_usd  83.00      <- wrong, he is at $106.00
peak_total_usd     83.00      <- same
balance            100.00, last checked 39 hours ago
statuses           20 deferred · 11 expired · 9 void · 2 lost
```

**Nothing has been placed. 11 bets have expired unplaced. Deferred went 18 to 20
and expired 3 to 11 in six hours.** The tool is generating signals and losing
every one of them.

# JOB 1 — STOP THE BLEEDING TODAY

- `account_start_usd = 106.00`, `peak_total_usd = 106.00`.
- **Un-defer every entry whose game has not started.** Let them re-price and
  re-qualify normally.
- **Confirm the 11 expired are genuinely past first pitch** before accepting
  them as lost. If any are not, they were expired wrongly and that is a second
  bug.

**This is a stopgap and it will break again the next time he trades manually.
Do not stop here.**

# JOB 2 — THE REAL FIX: RECONCILE AGAINST YOUR OWN BETS, NOT HIS ACCOUNT

**The design assumption is wrong.** `reconcile()` compares its ledger against
the whole account balance, which assumes every trade in the account came from
this tool. **He trades manually and always will** — he has said so twice — so
the sums can never balance and every signal defers then dies.

**Both methods you need already exist** in
`kalshi-inplay-bot/kalshi_client.py`, and both are **read-only**:

| method | line |
|---|---|
| `balance()` | 195 |
| `positions(open_only=True)` | 290 |

**Change the check to:**

- call `positions()`, keep **only tickers this tool has entries for**;
- verify each open entry is present at the expected size;
- **`disagree` means one of ITS OWN bets is missing or the wrong size** — not
  that the account total moved;
- **his manual trades become invisible to it.**

**This makes the guard stronger, not weaker.** Today it can only say *"something
does not add up somewhere"*. Afterwards it can say *"the Cleveland bet I placed
is not in your account"*, which is a real problem worth stopping for.

**Use `balance()` to fill the balance box automatically** so he never types it
again — **but that is a display, not the check.** The check is `positions()`.
Keep the typed-balance field as a manual override.

# WHAT MUST NOT CHANGE

**All five guards stay.** Guard 4 is being re-pointed, not removed — the
incident behind it is real and is in `DECISIONS.md` D20: his account went $130
to $160 while an earlier app said down $2, about **$32 wrong**, reported,
"fixed", and still wrong.

**Keep `tests/test_paper_only.py` green.** The other tool updated rather than
deleted it — it now enforces "production credentials are not in this repo"
instead of "no production code exists". **That was the right call. Do not
weaken it further.**

**Add tests for the new reconciliation**, including: a manual trade in the
account that is not ours changes nothing; one of our bets missing triggers
`disagree`; one of our bets at the wrong size triggers `disagree`.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

