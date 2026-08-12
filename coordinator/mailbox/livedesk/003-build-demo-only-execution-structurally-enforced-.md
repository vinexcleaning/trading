To: livedesk
From: coordinator
Opened: 2026-08-12 18:04
Status: OPEN
Subject: BUILD: demo-only execution, structurally enforced - full spec, trace already done

--- INSTRUCTION ---

**This supersedes nothing in 002 — do that too. This is the bigger job and it
came from the user via ChatGPT, written as a careful spec. He wants it built,
not described.**

**I have declined to write production order submission and that has not
changed.** This is different and the difference is not cosmetic: **a demo order
moves no money.** Kalshi's practice environment is fake money, which is what
`mlb-paper` already simulates locally — this just does it against the real API
so the whole loop gets exercised. **Build it demo-only, structurally, and it
stays that way.**

# WHAT I ALREADY TRACED, so you do not repeat it

| question | answer |
|---|---|
| proposal object | `Pick` — `picks.py:49`. Carries `ticker`, `event_ticker`, `side`, `quoted_price_c`, `signal`, `game_key` |
| costed bet | `Bet` — `money.py`. Carries `price_c`, `contracts`, `cost_usd`, `fee_usd` |
| button callback | `desk.py:493-496`, `command=lambda: self._confirm(p, bet)` |
| Guard 1 | `ledger.py:191` `signals_played()`, enforced in `add()` at `:224-227` |
| Guard 2 | `ledger.py:254` `trailing_stop_usd()` and the floor |
| Guard 3 | `money.py` `STAKE_USD` constant, $4.15 |
| Guard 4 | `ledger.py:295-327` `reconcile()` |
| kill switch | `killswitch.py` `disabled()` |
| client | `kalshi-inplay-bot/kalshi_client.py` — `__init__(demo=True, read_only=False)`, `_post`, `get_order`, `balance`, `positions`, `_check_writable` |

# THE SHAPE

`_confirm` currently copies to the clipboard, opens a browser and writes the
ledger. **Add a demo submission between the guards and the ledger write:**

```
Pick + Bet -> existing guards -> execution adapter -> KalshiClient(demo) ->
demo order -> read the order back -> record what ACTUALLY happened -> UI
```

**Create `livedesk/src/demo_exec.py`.** Keep it small. `desk.py` changes as
little as possible.

# THE DEMO-ONLY REQUIREMENT — STRUCTURAL, NOT A LABEL

**This is the part I care most about and the part a reviewer will check.**

- The adapter **constructs the client with demo hard-coded**. Not a default, not
  a parameter, not read from config or environment. A literal.
- **Before every submission, verify the client's effective environment really is
  demo** — check the base URL it will actually call, not a flag someone set.
  **If that cannot be verified, refuse.**
- **No parameter, constant, environment variable or config key exists anywhere
  in `livedesk/` that could switch this adapter to production.** Not
  `DEMO=false`, not `env="prod"`, nothing. If a future session wants production
  it has to write new code, visibly.
- **No production credentials.** Demo credentials only, read from outside the
  repo. The repo is public.

# THE PAPER-ONLY TEST — REFACTOR, DO NOT DELETE

`tests/test_paper_only.py` currently bans `kalshi_client` outright. **It must now
allow authenticated DEMO execution while still failing on any production path.**

**It must still fail if any of these appear in `livedesk/`:** a production base
URL · a way to set demo false · a credential file inside the repo · an order
submission that bypasses the adapter · the adapter losing its environment check.

**Keep the planted-violation test** — the one that proves the detector still
detects. Add planted violations for each new rule. **A detector that stops
detecting is worse than no detector, and this test has already caught itself
skipping silently once.**

# GUARDS — ALL OF THEM SURVIVE, AND TWO NEW ONES

Every existing guard stays exactly as it is. **Do not restate them in the
adapter — call the existing code.** Two copies of a guard is how they drift.

**New Guard 5 — daily caps.** `MAX_ORDERS_PER_DAY` and `MAX_STAKE_PER_DAY_USD`
as clearly named constants. Conservative: **6 orders and $25** unless you can
argue better. **Checked before every submission. Fail closed if either cannot be
determined** — an unreadable ledger means no order, not an unlimited one.

**New Guard 6 — one click, one order.** Disable the button on click and keep it
disabled until the outcome is recorded. A double-click, a repeated callback or a
retry must not produce two orders. **Carry an idempotency key derived from the
signal** so a resend of the same approval is recognised and refused.

**`TRADING_DISABLED` is checked immediately before every submission**, not at
startup.

**Reconcile is fail-closed:** if the ledger and the account do not agree, no
order is submitted. This is the guard that caught his $32 problem; it must gate
submission, not just the display.

# NEVER INVENT A FILL

**A successful HTTP response is not a fill.** This is the exact bug that put a
phantom $3.77 in his ledger.

After submitting: take the order id, **read it back with the client's existing
order-reading call**, and record only what actually happened. Distinguish
**rejected · resting/open · partially filled · filled · cancelled · unknown**
where the API supports it.

**Unknown is a real state and must be recorded as unknown**, never as filled and
never silently dropped. If the read-back fails, the ledger says so and the UI
says so.

# ERRORS ARE FOR HIM TO READ

No tracebacks in the window. A sentence he can act on: what was tried, what came
back, what to do. He reads this half asleep.

# TESTS — all of these, mocked network

button click → exactly one submission · no click → no submission · the $4.15
clamp · the $50 floor · the trailing stop · a reconcile mismatch ·
`TRADING_DISABLED` · a duplicate signal · the two-per-game maximum · the daily
order cap · the daily stake cap · a rejection · a resting order · a partial fill
· a successful fill · a failed order-status lookup · double-click protection ·
**and a test that proves this adapter cannot be configured for production.**

# WHEN IT IS DONE

Run the full suite. **Do not run a real demo order automatically** — write the
exact steps for him to run one himself, including where the demo credentials go
and how to get them, click by click. He has said he will create accounts and log
in when asked.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both. **No statistics words.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


---

# AMENDMENT — his numbers for Guard 5

> *"Keep the 25 dollar fail but remove the 6 order max, make it like 10."*

- `MAX_ORDERS_PER_DAY = 10`
- `MAX_STAKE_PER_DAY_USD = 25.00` — unchanged

**Both still fail closed if they cannot be determined.**

## ⚠ Tell him what these two numbers do together, on the screen

**At $4.15 a bet, the money cap binds first.** Six bets is $24.90; a seventh
would be $29.05 and is refused. **So the order limit of 10 can never actually be
reached while the stake is $4.15 and the daily money cap is $25.**

That is not wrong — a belt and braces where one is tighter is fine, and the
looser one starts mattering the moment either number changes. **But he should
not think he has raised his daily ceiling from 6 to 10 when he has not.**

**Show both counters with the room left in each**, the way Guard 2 already shows
the floor and the trailing stop:

```
today: 3 of 10 orders  ·  $12.45 of $25.00  ·  money runs out first, at 6 bets
```

**That last clause is the useful part.** Say which cap will actually stop him,
computed from the current numbers rather than hard-coded, so it stays true if
any of the three constants change.

---

# AMENDMENT 2 — he raised the daily money cap

> *"Raise the twenty five to fifty."*

- `MAX_STAKE_PER_DAY_USD = 50.00`
- `MAX_ORDERS_PER_DAY = 10` — unchanged

**Now the two caps are close to balanced.** At $4.15 a bet, $50 allows 12 bets
and the order limit stops him at 10 ($41.50). **So the ORDER cap now binds
first, where before it was the money.** The on-screen line that names which cap
will stop him must be computed, not hard-coded, exactly so it flips correctly
when a constant changes like this.

**Also worth putting in front of him:** $50 a day of stake against an $83
bankroll means **he could commit more than half his money in one day.** The
per-bet stake and the two cut-offs are what actually bound the downside; the
daily cap is a backstop against a loop misbehaving, not a risk limit. **Do not
present it as one.**
