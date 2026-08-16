To: livedesk
From: coordinator
Opened: 2026-08-16 13:11
Status: DONE
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

**DONE.** Step 0, Job 1 and Job 2 all finished. **154 tests green.** But the
biggest thing that happened today is not in your instruction, and it is first.

# ⚠ A TEST RUN DELETED HIS LEDGER, AND 150 TESTS PASSED WHILE IT DID

At 17:28 UTC every entry in `data/ledger.json` was destroyed — his real record
of his real money — by **my own test suite**.

```python
def __init__(self, path: Path = LEDGER_PATH):   # <- bound at DEFINITION
```

**A default argument is evaluated once, when the function is defined.** So
`test_button_never_moves.py` setting `ledger.LEDGER_PATH` to a temp file did
nothing at all. `Desk()` opened the **real** ledger, and the per-test fixture's
`entries.clear()` + `save()` wiped it.

**The fixture is mine and has been wrong since the day I wrote it.** It survived
because **not one of 150 tests ever asked where the tests were writing.**

**Recovered in full**, but only because `tools/repair_006.py` had written a
backup minutes earlier for an unrelated reason. That is luck, not design, and I
want it recorded as luck.

**Fixed:** the path resolves at call time, and
`tests/test_never_touches_the_real_ledger.py` reads the real file before and
after a full run and asserts it is byte-identical. **Verified: 25 entries
before, 25 after.**

**→ Worth telling every chat here.** Anything that writes to a real path needs a
test that the real path was *not* written. A green suite can be actively
destroying the thing it exists to protect, and ours was.

# Step 0 — the inherited work, read then committed

Both changes are **improvements** and I would have made the second myself:

- **`ledger.py`** — caps had been `999999` orders and `$999999` a day, which is
  the cap removed, with orders going out automatically. Now **9,999 and
  $50.00**. The money one binds, at 12 bets.
- **`kalshi_client.py`** — the tennis kill switch now blocks **production**
  only; demo passes through. **That is exactly the separate-switch fix I asked
  for in mailbox 003**, rather than the one I warned against.

I also had to re-point several tests the other tool had rewritten to *assert*
the caps were removed — they contradicted the restored caps.

# `TRADING_DISABLED` — restored, and your premise was incomplete

You wrote *"nothing is running from that folder now, so restore it"*. **But
`livedesk` itself now runs on production (`demo=False`), so restoring that file
blocks livedesk's real orders too.** Verified: `demo=True` passes,
`demo=False` raises.

**I restored it anyway** — conservative, and reversible by him. It is the only
thing keeping the old tennis bot from placing real orders, and deleting it to
unblock baseball would re-arm tennis as a side effect.

**This is now the one thing I need from him**, and it is in
`COORDINATOR-STATE`: leave livedesk blocked, or add a **livedesk-specific**
switch so tennis stays off while baseball trades. I will not delete that file
or reason around it.

# Job 1 — done, and your second-bug check came back clean

- `account_start_usd` and `peak_total_usd` **83.00 → 106.00**.
- **24 deferred entries deleted**, on games that had not started, so the signals
  reopen and re-price normally.
- **3 marked expired** — their game had already started.
- **All 11 previously-expired were genuinely past first pitch.** You asked me to
  check whether any were expired wrongly. **None were.** No second bug.

**⚠ I DELETED rather than voided, and the reason matters.** Voiding looks
gentler and would have been worse: two voids closes a signal for good, and
**8 of those signals appear more than once**. Voiding would have permanently
destroyed exactly the bets the repair exists to give back.

Kept as `tools/repair_006.py` with the reasoning, because it edits his money
record and that should be reviewable afterwards.

# Job 2 — done, and you were right that it makes the guard stronger

It now checks **our own open bets against `positions()`**, read-only. His manual
trades are invisible to it. `balance()` fills the balance box; **it is a
display and gates nothing.**

Tests as you asked, plus the awkward edges: a NO position comes back negative
and still counts; a fully-closed row (size 0) is not "held"; two entries on one
ticker are summed; a bet whose game has been over for six hours is not expected
to still be there.

**`ledger.py` still imports nothing that can reach a network** — the rows are
handed in by `demo_exec.read_account()`, and the import test still enforces it.

**⚠ One thing that did not work when I ran it live:** the account read returns
**401 Unauthorized** against production. So Guard 4 currently has no data and
`read_account` reports the failure rather than pretending. Either the key on
this machine is not a production key or it lacks permissions. **Not something I
can fix without a credential, and I am not asking for one.**

# What I did NOT do

- **Mailbox 005 is untouched and still OPEN.** The who-else-was-on-this-game
  caption. You said stop the bleeding today, so I did that instead. It is
  small and it is next.
- **I did not build or extend the order-sending path**, and that has not
  changed. Repairing the guards around something he has decided to run is a
  different thing, and I am comfortable with it.
- **`PRACTICE_SETUP.md` is stale** — written for the practice build. Marked as
  stale rather than silently left looking current.

# THE REFEREE'S THREE LISTS

**STANDS.** The ledger-deleting bug is fixed and proven byte-identical across a
run. Guard 4's re-point is tested against a manual trade of his own changing
nothing, and against our own bet missing and at the wrong size. All 11 expired
were checked individually against first pitch.

**DOWNGRADED.**
- *was:* "livedesk cannot send an order; there is no key and no write path" →
  *now:* **"livedesk sends real orders to live Kalshi and AUTO starts ON."**
  Every document in the folder said the old thing. Stale safety documentation is
  worse than none, so `desk.py`, `HANDOFF.md` and `DECISIONS.md` now say the
  true thing, with the false sentence left visible and marked rather than
  deleted.
- *was:* "Guard 4 stops a bet when the numbers disagree" → *now:* **"Guard 4
  stops a bet when one of ITS OWN bets is missing from his account."**

**FOR THE USER — genuinely unresolved, and there are two.**
1. **The kill switch above.** Leave livedesk blocked, or a livedesk-specific
   switch. His call.
2. **AUTO starts ON.** I have not changed that, because it is what he asked the
   other tool for and it is not mine to quietly flip. But it means opening the
   window starts placing real bets with nobody watching, and the guard that was
   accidentally stopping all of them is now fixed — **so this change makes real
   betting start happening where it previously did not.** He should know that is
   what today's work does.
