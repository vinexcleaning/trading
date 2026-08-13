# HANDOFF — livedesk

<!-- COORDINATOR-STATE
doing: STOOD DOWN. Another AI tool owns livedesk/ execution work from 2026-08-13 00:54 (mailbox 004). I have made no edits since, and will not.
left: nothing of mine. Everything is committed and pushed. Possible future role is reviewing what the other tool produces rather than writing more.
needs: no
-->

**⚠ STOOD DOWN 2026-08-13.** Another AI tool is editing this folder. **I have
stopped.** Everything below is written for whoever picks this up, not for me.

**As of 2026-08-13 01:10. 94 tests green** (`livedesk\test.bat` — that command
and no other; it sets `LIVEDESK_REQUIRE_GUI=1`, which turns a missing display
from a *skip* into a *failure*, and a silently skipped test reads as a green
run).

---

# ⚠ READ THESE THREE THINGS BEFORE YOU CHANGE ANY CODE

## 1. A test passing does not mean the path works. This bit me here.

**The practice-order button could never have fired. Not once.** Every test
passed. The adapter was correct. The guards were correct. And the button was
dead, because by the time a practice order is requested the entry is **already
in the ledger** — it is written on the copy click — so Guard 1 found the entry's
own signal in `signals_played()` and refused every single time.

**Nothing in the test suite could have caught it**, because every test
constructed the entry and the ledger separately, the way the tests were written
rather than the way the app runs.

**Thirty seconds of actually opening the window and clicking found it.** So did
the second bug the same evening: `configured()` reported "practice orders are
ready" on a machine with **no practice key at all**, because the client
constructs perfectly happily with no credentials and only fails later at
signing time.

**If you change anything in this folder, run the window and click the thing.**
`coordinator/REFLECT.md` records this same lesson eight separate times. It is
the single most reliable failure mode in this repo.

## 2. The demo lock is a URL check, not a flag, and that is deliberate

In `src/demo_exec.py`:

```python
client = KalshiClient(demo=True)     # <-- LITERAL
verify_demo(client)                  # <-- reads client.base, NOT client.demo
```

**You will be tempted to replace this with a config value or an environment
variable. Do not.** The reason:

- `client.demo` is **what somebody set**. It can be wrong, stale, overwritten,
  or set by a caller who meant well.
- `client.base` is **the URL the packet actually goes to**.

**If those two ever disagree, the URL is the truth and the flag is the lie.**
There is a test that plants exactly that disagreement — a production base URL
with `demo` still `True` — and proves nothing is sent and the client is never
even touched (`test_a_lying_demo_flag_does_not_help`).

`tests/test_paper_only.py` fails the build if `demo_exec.py` ever loses
`verify_demo`, `DEMO_HOST`, or the literal `demo=True`.

## 3. ⚠ NO PRACTICE ORDER HAS EVER BEEN SENT. NOT ONE.

**The instruction that stood me down asks me to write up "what the practice-order
run proved". There was no run, and I am not going to let that stand.**

Nothing has ever gone to Kalshi from this folder, for two independent reasons:

1. **There are no practice credentials on this machine.** `KALSHI_KEY_ID` is
   unset. `configured()` correctly reports "not set up" and the button is greyed
   out.
2. **The shared client refuses all writes anyway** — see the kill-switch section
   below.

**So the submit path has been exercised against test doubles only.** The
doubles are good ones and they misbehave on purpose, but **a double is not the
API**. Treat the whole submit-and-read-back path as *unproven against Kalshi*
until someone runs it with real practice credentials.

---

# What is here

| file | what it is |
|---|---|
| `src/desk.py` | the window. One card, one button, a log, the bets list |
| `src/picks.py` | reads `mlb-paper/data/paper.db` **read-only**. Decides nothing |
| `src/prices.py` | live Kalshi prices and settlement, public read API, GET only |
| `src/money.py` | what a bet costs and pays. Fees from `common/kalshi_fees.py` |
| `src/ledger.py` | the record of every bet, and where most guards live |
| `src/demo_exec.py` | **the only file that can submit anything.** Practice only |
| `src/killswitch.py` | `TRADING_DISABLED` in this folder kills the button |
| `PRACTICE_SETUP.md` | how he gets a practice key. Written click by click |

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
