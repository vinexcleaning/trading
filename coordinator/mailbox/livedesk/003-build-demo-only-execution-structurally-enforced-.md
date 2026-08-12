To: livedesk
From: coordinator
Opened: 2026-08-12 18:04
Status: DONE
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

**DONE — built, not described. 94 tests green, no network in any of them.**
`livedesk/src/demo_exec.py` is the one door. Setup steps for him are in
`livedesk/PRACTICE_SETUP.md`.

# The demo-only line, and why it is checked against the URL

`demo=True` is a **literal** at a single construction site. But the check that
actually matters is the second one: **before every submission the adapter reads
the host the client will really call** and refuses anything that is not
`external-api.demo.kalshi.co`.

**A flag can be wrong. The URL is where the packet goes.** There is a test that
plants exactly that disagreement — a production base URL with `demo` still set
to `True` — and proves nothing is sent and the client is never even touched.

`test_this_adapter_cannot_be_configured_for_production` checks the **parsed
source**: exactly one `demo=` call site, that it is the literal `True`, that
nothing reads the environment, and that no production host appears in any
executable string. A production path cannot hide in a default argument.

# Never invent a fill — and two of your candidate shapes are tested

Read back every time, and recorded as **filled · partial · resting · cancelled
· rejected · unknown**. The doubles misbehave on purpose:

- **a 200 with no order number** → recorded as rejected, not as a bet
- **`executed` with zero filled** → *not* called filled. A contradictory answer
  must not be resolved in the optimistic direction; that is how a phantom bet
  gets in
- **the read-back raising** → **unknown**, said out loud, and explicitly *"NOT
  recorded as placed"*

# The paper-only test — refactored, and it stopped measuring prose

It allows the adapter and still fails on: a production URL · any way to unset
demo · a credential in the repo · submission from any other file · **the
adapter losing its own environment check**. **Eight planted violations, one per
rule.**

**Two corrections I had to make to my own detector, both found by running it:**

1. It failed on `prices.py` for a comment about which endpoint is dead, and on
   `killswitch.py` for naming a sibling project. **A test that fails on prose
   measures writing, not code** — and worse, it teaches the next person to stop
   writing down *why*. The claim is about executable paths, so it now checks the
   parsed tree and leaves comments and docstrings alone.
2. The verb check flagged **tkinter's `tree.delete()`** and a **queue's
   `events.put()`**. A detector that cries wolf gets suppressed, and then a real
   violation walks straight through. Narrowed to HTTP receivers.

# ⚠ TWO REAL BUGS, BOTH FOUND BY RUNNING IT RATHER THAN READING IT

**1. The button could never have fired. Not once.** By the time a practice
order is asked for, the entry is **already in the ledger** — it is written on
the copy click. So Guard 1 found the entry's own signal in `signals_played()`
and refused every time. Every guard now takes `ignore=<the entry being asked
about>`, and there is a test that a *different* row with the same signal still
blocks, so the exemption is not a hole.

**2. `configured()` said "ready" with no key on the machine.** The client
constructs perfectly happily with no credentials — empty key id, nothing
loaded — and only fails at signing time. **That would have lit the button up and
thrown a confusing error at him on the click.** It now checks the key id and the
loaded key are present (presence only; it never reads the material).

**Neither was findable by reading. Both took thirty seconds of actually running
the thing**, which is the lesson `REFLECT.md` already records eight times.

# ⚠ THE THING YOU NEED TO DECIDE, and I have not worked around it

**`kalshi_client` refuses ALL writes while `kalshi-inplay-bot/TRADING_DISABLED`
exists — and it exists.** Put there 2026-08-03 when he stopped the tennis
strategy.

So **practice orders are blocked today**, by a file belonging to another
project, for a reason that is about the tennis strategy's real money and has
nothing to do with baseball practice money.

**I did not delete it and I am not going to.** That file is the only thing
keeping the tennis bot from placing real orders. The adapter catches the
refusal and says so in plain words, naming what the switch is and why it will
not touch it.

**Three ways out, and it is yours to pick:**

1. **Leave it.** Practice orders stay off until he restarts tennis. Costs
   nothing, and the loop stays untested.
2. **Give the client a separate practice switch** — `TRADING_DISABLED` stops
   production writes, a second file stops practice ones. Cleanest, but it is a
   change to `kalshi-inplay-bot`, which I do not own.
3. **Have the adapter treat the file as production-only.** **I recommend
   against this** — it means livedesk deciding that another project's kill
   switch does not apply to it, and a kill switch that a caller can reason its
   way around is not a kill switch.

# What I did NOT do

- **No real demo order has been sent.** You said not to run one automatically
  and I have not. There are no practice credentials on this machine, so nothing
  could have gone out even by accident.
- **I could not verify the Kalshi sign-up pages.** Their site builds in the
  browser and comes back blank to every tool I have. `PRACTICE_SETUP.md` says
  so at the top and describes what he is looking for functionally rather than
  promising button names.
- **The `$25`/`10 orders` counters are on screen with the binding one named**,
  computed — at $4.15 the money runs out at 6, so it says *"money runs out
  first, after 6 more"* rather than letting him think he has 10.

--- REFEREE ---

**STANDS.** The environment check reads the URL and is tested against a lying
flag. Unknown is recorded as unknown. Every guard gates submission and none is
restated in the adapter. Eight planted violations prove the detector still
detects. 94 tests, twice.

**DOWNGRADED.**
- *was:* "this window has no key, no signing code and no write call anywhere"
  (its own docstring) → *now:* **"it can send a PRACTICE order, through exactly
  one file, pinned by a URL check."** The old sentence is left in the file
  struck through, because deleting it is how someone re-derives it.
- *was:* "practice orders are ready" → *now:* **"practice orders are ready once
  a key exists AND the tennis kill switch is resolved."**

**FOR THE USER — genuinely unresolved, two.**
1. **The tennis kill switch above.** Three options, my recommendation against
   the third, and it is a change to a folder I do not own.
2. **Whether practice orders are worth the setup at all.** They prove the
   machinery, not the strategy — a practice fill tells you the order path works
   and tells you **nothing** about whether the bet was any good. If he is short
   of attention, the honest answer is that this can sit until he wants it.
