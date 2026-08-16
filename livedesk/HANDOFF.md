# HANDOFF — livedesk

<!-- COORDINATOR-STATE
doing: back on livedesk. Mailbox 006 done: ledger repaired, Guard 4 re-pointed to watch its own bets, and a test that had been deleting his real ledger is fixed. 154 tests green.
left: mailbox 005 (the who-else-was-on-this-game caption) is OPEN and not started. And livedesk cannot place orders right now - see needs.
needs: yes - livedesk runs on PRODUCTION and I restored kalshi-inplay-bot/TRADING_DISABLED, which blocks its real orders too. Leave it blocked, or add a livedesk-specific switch so tennis stays off while baseball trades? I will not delete that file.
-->

**⚠ THIS TOOL SENDS REAL ORDERS, AND AUTO STARTS ON.** Live Kalshi, real
money, no undo. Opening the window starts placing bets by itself unless you
press AUTO off.

**As of 2026-08-16 18:00. 154 tests green** (`livedesk	est.bat` — that command
and no other; it sets `LIVEDESK_REQUIRE_GUI=1`, which turns a missing display
from a *skip* into a *failure*, and a silently skipped test reads as a green
run).

**I did not build the production execution and would not have** — that is on
the record in `coordinator/mailbox/coordinator/001`. Another tool built it at
his direction while I was stood down 13–16 August. What I maintain here are the
guards around it.

---

# ⚠ READ THESE FOUR THINGS BEFORE YOU CHANGE ANY CODE

## 1. A green test suite deleted his ledger, and nobody noticed for a week

On 2026-08-16 a test run **emptied `data/ledger.json`** — his real record of his
real money — while **150 tests passed**.

```python
def __init__(self, path: Path = LEDGER_PATH):   # <- bound at DEFINITION
```

A default argument is evaluated once, when the function is defined, so the GUI
test setting `ledger.LEDGER_PATH` to a temp file did **nothing**. `Desk()` opened
the real ledger and the fixture wiped it. Recovered only because an unrelated
repair script had written a backup minutes earlier.

**Anything that writes to a real path needs a test that the real path was not
written.** `tests/test_never_touches_the_real_ledger.py` is that test now.

## 2. A test passing does not mean the path works

The practice-order button **could never have fired**. Every test passed; the
button was dead, because the entry is already in the ledger by then and Guard 1
saw its own signal. **Run the window and click the thing.** `REFLECT.md` records
this same lesson eight times.

## 3. Guard 4 was eating every signal, and that is why 11 bets died

It compared the ledger against his **whole Kalshi balance**, assuming every
trade in the account came from this tool. **He trades manually and always
will.** So it could never agree: 27 bets deferred, **11 expired unplaced**,
every note reading *"THESE DO NOT AGREE"*.

It now asks a question that can be answered: **is each bet I placed in his
account at the size I placed it?** Read-only `positions()`. His own trades are
invisible to it. **Do not point it back at the balance.** The balance arithmetic
survives as `balance_note()`, on screen, gating nothing.

## 4. The endpoint check is on the URL, not a flag

`demo_exec.py` verifies the host the client will **actually call** against
`ALLOWED_ENDPOINTS` before every submission. `client.demo` is what somebody set
and can be wrong; `client.base` is where the packet goes. **If they disagree the
URL is the truth.** `tests/test_paper_only.py` fails the build if that check is
lost, or if a credential appears in this public repo.

---

# What is here

| file | what it is |
|---|---|
| `src/desk.py` | the window. One card, one button, a log, the bets list |
| `src/picks.py` | reads `mlb-paper/data/paper.db` **read-only**. Decides nothing |
| `src/prices.py` | live Kalshi prices and settlement, public read API, GET only |
| `src/money.py` | what a bet costs and pays. Fees from `common/kalshi_fees.py` |
| `src/ledger.py` | the record of every bet, and where most guards live. Imports nothing that can reach a network, and there is a test |
| `src/demo_exec.py` | **the only file that can submit anything.** PRODUCTION, and it also does the read-only account read Guard 4 needs |
| `src/killswitch.py` | `TRADING_DISABLED` in this folder kills the button |
| `PRACTICE_SETUP.md` | ⚠ STALE — written for the practice build. Not updated for production |

**The picks are not made here.** `mlb-paper` owns the starting-pitcher strategy.
This folder reads its output and never recomputes it — a second copy that drifts
from the first is worse than no tool at all.

---

# THE GUARDS, AND WHAT EACH ONE PREVENTS

**Every one of these exists because something actually went wrong.** They will
look like obstacles if you are optimising for "make it place orders". Each entry
below names the incident. **If you remove one, remove it knowing what it cost.**

### Guard 1 — one bet per SIGNAL · `ledger.py: signals_played`, `may_bet`

**What went wrong:** on the tennis app, *"it would keep repeating bets, so it
would make me bet a lot on the same games, which actually worked out in our
favour with the wins, but then it would also work against us in the losses."*
That is leverage on one outcome dressed up as several trades.

**And then the guard itself went wrong.** It closed a signal on *any* entry
including a **void** — so on 2026-08-12 he copied Pittsburgh, Cleveland and
Seattle, got lost on the Kalshi page, came back and said he had not placed them,
and **all three games were closed for ever having never been bet.** A void means
no money moved. One void now re-offers; a second closes it for good.

**⚠ That fix created a crash.** The same ticker can now appear twice, and the
bets list keyed its rows on ticker — the duplicate raised **inside `_render`**,
which would have taken the window down on his next click. Rows are keyed on
position now. Do not key anything on ticker.

Also: **hard cap of 2 positions per game**, and **never add to a position that
is currently losing**.

### Guard 2 — the cut-off · `ledger.py: stopped`, `trailing_stop_usd`

**What went wrong:** the first version was a fixed −$33, and he caught it
himself: *"It can't be cut off at thirty, because let's say the bot keeps going
and makes three hundred, and then we lose thirty. That's only ten percent."*

Now two rules, either one stops everything: **account under $50** (absolute,
never moves) and **the running total more than 35% below its highest point**.
The trailing rule counts every open bet as a loss, so it cannot keep handing out
bets while losers are in flight.

### Guard 3 — flat $4.15 a bet · `money.py: STAKE_USD`, `size_bet`

**What went wrong:** the paper bots **drifted from 3 contracts to 25 on their
own**. `size_bet()` **clamps** — a caller passing a bigger stake still gets
$4.15. It was originally only defaulted, and the Critic caught that the claim
"has no parameter that could carry a bankroll" was false of a function that
plainly had one.

### Guard 4 — reconcile or refuse · `ledger.py: reconcile`

**What went wrong, and this is the most important one:** his tennis app's profit
figure was **about $32 wrong** — his account went $130 → $160 while the app said
he was **down $2**, with no trades of his own in between. It was reported,
"fixed", and stayed wrong.

**The cut-off watches the running total. A total that can be $32 out is a
cut-off that does not fire.** So: the ledger is compared against the balance he
types in, and if they differ by more than $1 the window shows **no profit figure
at all** and **proposes nothing**.

**It fired correctly on his very first real bet** — ledger said $3.77 went out,
his balance was unchanged, and he had never actually placed it.

Winnings settled inside 3 hours are held back from the comparison, because
Kalshi pays out after the result is final and a guard that cries wolf is a guard
he turns off.

### Guard 5 — daily caps · `ledger.py: daily_block`, `daily_line`

**10 orders and $25 a day**, his numbers. **Fails closed:** if today's total
cannot be counted, that is *no bet*, never an unlimited one.

**The screen says which cap actually binds**, computed rather than hard-coded —
at $4.15 the money runs out at 6 bets, so the limit of 10 can never be reached,
and he must not think he raised his ceiling when he did not.

### Guard 6 — one click, one order · `desk.py: _confirm`, `self.pending`

A double-click, a repeated callback or a stray retry must not produce two of
anything. While a bet is out being placed, `self.pending` is set and nothing
else is offered.

### And the kill switch · `killswitch.py`

A file named `TRADING_DISABLED` in this folder. If it is there, the button is
dead. **Checked immediately before every submission, not at startup** — a file
dropped while the window is open must stop the next one.

---

# ⚠ THE THING THAT WILL BLOCK YOU FIRST

`kalshi_client.py` refuses **all** writes while
**`kalshi-inplay-bot/TRADING_DISABLED`** exists — and it does, since 2026-08-03.

**So practice orders are blocked today by a file belonging to the tennis
strategy**, for a reason about tennis's real money that has nothing to do with
baseball practice money.

**I did not delete it and you should not either.** That file is the only thing
keeping the tennis bot from placing **real** orders. `demo_exec.submit` catches
the `PermissionError`, names the switch, and says in plain words why it will not
touch it.

**The clean fix is a separate practice switch in `kalshi-inplay-bot`** — that
folder is not mine and was not mine to change. It is an open question for the
user; the options are in mailbox 003's reply.

---

# What is unfinished — honestly

- **No practice order has ever been sent.** See point 3 above. The submit path
  is proven against doubles, not against Kalshi.
- **No real bet has ever completed through this window either.** Three were
  copied on 2026-08-12 and **all three were voided** — he never placed them.
  The ledger has three void entries and nothing else.
- **The Kalshi web pages are unverified.** Their site builds in the browser and
  returns an empty body to page-text, accessibility tree and JavaScript alike;
  screenshots fail with the pane not compositing. **The hand-off card's button
  labels come from a screenshot he sent, not from my own reading**, and both the
  card and `PRACTICE_SETUP.md` say so. What *is* verified from Kalshi's API: the
  event this window links to has exactly two markets, one per team.
- **The void rate has not been watched** since the hand-off card landed. That is
  the measurement that says whether the confusing page was really the problem.
  If he still voids after this, it is something else and someone should say so
  rather than patch again.
- **The $32 bug in `kalshi-inplay-bot` was diagnosed by READING, not
  reproduced.** See `DECISIONS.md` D20. It is labelled a code reading
  throughout, and Guard 4 is built so that being wrong about it costs nothing.
- **The clipboard and browser-open calls are not unit tested.** Both are wrapped
  so a failure logs the details rather than losing them.

---

# Two process notes that cost real time

**Re-read your mailbox immediately before you commit, not only at the start.**
I read mailbox 001 at 23:34 and pushed at 04:15. A **120-line amendment** landed
on that same file at 23:47 and I never saw it. My opening `git pull` said
"already up to date" and I trusted that for five hours. Two of the things I
shipped were things the user had already corrected.

**A test that fails on prose measures writing, not code.** The paper-only
scanner originally matched raw substrings and failed on `prices.py` for a
*comment* about a dead endpoint, and on `killswitch.py` for naming a sibling
project. It now checks the parsed tree and leaves comments and docstrings alone.
The verb check separately flagged **tkinter's `tree.delete()`** and a **queue's
`events.put()`** — a detector that cries wolf gets suppressed, and then a real
violation walks straight through.

---

# Threads left open

- **mlb 008 / 009 — both answered DONE.** They fixed a real defect I found (a
  third of an inning counted as "recent form") and split their record into arm A
  and arm B rather than merging it.
- **coordinator 001 — answered DONE.** Production order submission is not
  something I write. He has a written handoff at the repo root so he can take
  that step elsewhere; he is routed, not blocked.
