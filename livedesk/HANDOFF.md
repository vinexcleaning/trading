# HANDOFF — livedesk

<!-- COORDINATOR-STATE
doing: nothing running; mailboxes 001, 002 and 003 are all built and replied to, 94 tests green
left: he opens it and uses it; practice orders need a demo key (PRACTICE_SETUP.md) and are additionally blocked by the tennis bot's TRADING_DISABLED file
needs: yes - the tennis kill switch blocks practice orders too. Leave it, add a separate practice switch to kalshi-inplay-bot, or something else? I will not delete it or reason around it.
-->

**As of 2026-08-12 21:00.** Built overnight from
`coordinator/mailbox/livedesk/001` **and its amendment 2**, which I missed on
the first pass. 46 tests green. Nothing is running in the background; the
window does its own work while it is open.

## Open it

```bash
livedesk\run.bat
```

Off: `turn_off.bat`. On: `turn_on.bat`. Tests: `test.bat` — **that command and
no other**, because it sets `LIVEDESK_REQUIRE_GUI=1`, which turns a missing
display from a skip into a failure.

## ⚠ THE PROCESS FAILURE, AND IT IS THE MOST USEFUL THING ON THIS PAGE

**I read mailbox 001 at 23:34 and pushed at 04:15. A 120-line amendment landed
on that same file at 23:47 — thirteen minutes after I read it — and I never
re-read it before pushing.** My opening `git pull` said "already up to date"
and I trusted that for five hours.

The amendment changed two of the three guards and added a fourth. Two of the
things I shipped were things the user had already corrected.

**The fix is mechanical and every chat here should take it: `git pull` and
re-read your mailbox immediately BEFORE you commit, not only at the start.**
A mailbox is not a message you receive once — the user is awake and talking to
the dictator chat while you work.

## What is DONE

- **The window.** `src/desk.py`. Header with the running total and the rules ·
  a balance box · the two cut-offs with the room left in each · one card ·
  the bets placed · a log · a permanent evidence line.
- **The button does not move.** Measured across **nine** states, test fails on
  a one-pixel shift.
- **Guard 1 — one bet per SIGNAL**, a genuinely different trigger allowed, two
  per game maximum, never adding to a losing position.
- **Guard 2 — two cut-offs:** an absolute $50 floor and a 35% trailing drop
  from the peak. Both shown. Peak survives a restart and only ever rises.
- **Guard 3 — $4.15 flat, clamped** so a caller cannot ask for more.
- **Guard 4 — reconcile or refuse.** Ledger against the typed balance; more
  than $1 apart and the window shows no profit figure and proposes nothing.
  Winnings settled inside 3 hours are held back so it does not cry wolf.
- **It surfaces itself** — raises and chimes once per new bet — and deep-links
  to that one game's page.
- **A withdrawn pick is retired and logged.** This caught a real one: the
  Dodgers pick from before `mlb`'s A3 fix, which their own newest view now
  rejects.
- **Live end to end.** 7 picks offered, 1 correctly retired, 7 live prices, a
  real finished game settled to the right cent on both sides, and the whole
  reconcile lifecycle exercised including the $32 case.

## What is NOT done

- **No real bet has gone through it.** Everything below the click is tested;
  the click has only been exercised with a fake pick.
- **The clipboard and browser-open calls are not unit tested.** Both are
  wrapped so a failure logs the details rather than losing them.
- **The $32 bug in `kalshi-inplay-bot` was diagnosed by READING, not
  reproduced.** That needs a key and a live account and this folder has
  neither. See DECISIONS D20 — it is labelled as a code reading throughout,
  and the reconcile check is built so that being wrong about it costs nothing.
- **The window has not been left running for a full day.**

## The first thing to do tomorrow

He opens it and **types his Kalshi balance into the box once**. Until a bet
settles nothing depends on it, but the moment one does, the window will refuse
to show a profit figure until it has been checked — which is the point.

## Where the picks come from

`mlb-paper/data/paper.db`, read-only, bot `starter__hold`, re-checked against
`starter__shadow` for withdrawals. If that runner stops, the window says so in
words on the card rather than showing a stale game. `mlb-paper` owns the
strategy; nothing here recomputes it.

## Open threads with `mlb`

- **008 — DONE.** They found the uncapped-divergence problem was a rule, not
  one pitcher (one third of an inning counted as "recent form"), fixed it in
  amendment A3, and split their record into arm A and arm B rather than
  merging.
- **009 — OPEN, not blocking.** Confirming my reading that the starter
  strategy has one signal per game by construction. I have shipped on that
  reading and it is one line to reverse.

---

# 2026-08-12 evening — mailboxes 002 and 003

## 002, the hand-off — DONE

After COPY & OPEN the card is replaced by numbered clicks for that page, and it
stays until he says whether the bet went on. Button measured on the same pixel
across ten card states.

**The bigger fix was a guard of mine, not the page.** Guard 1 closed a signal on
any entry including a void — so his three copied-and-voided games (Pittsburgh,
Cleveland, Seattle) were closed for ever having never been bet. A void means no
money was placed, so re-offering is not "the same bet twice". **One void now
re-offers; a second closes it.** His three are live again.

**That change created a crash and running it found it:** the same ticker can now
appear twice, and the bets list keyed rows on ticker — the duplicate raised
inside `_render` and would have taken the window down on his next click. Keyed
on position now.

## 003, practice orders — DONE

`src/demo_exec.py`, the one door. `demo=True` as a literal, and **the host the
client will really call is checked before every submission** — a flag can be
wrong, the URL is where the packet goes. Never invents a fill: reads the order
back and records filled / partial / resting / cancelled / rejected / **unknown**.

`test_paper_only.py` refactored rather than deleted — allows the adapter, still
fails on production URLs, on any way to unset demo, on credentials in the repo,
on submission from elsewhere, and on the adapter losing its own check. Eight
planted violations.

**Two bugs found by running it, neither findable by reading:**
- the practice button **could never have fired** — the entry is already in the
  ledger by then, so Guard 1 saw its own signal and refused every time
- `configured()` said "ready" with **no key on the machine**, because the client
  constructs fine without credentials and only fails at signing

## ⚠ NEEDS HIM: the tennis kill switch blocks practice orders

`kalshi_client` refuses **all** writes while `kalshi-inplay-bot/TRADING_DISABLED`
exists, and it does — from 2026-08-03. So practice orders are off today because
of a file about the tennis strategy's real money.

**I did not delete it and will not.** It is the only thing keeping the tennis bot
from placing real orders. Options in the 003 reply; the decision is his.

## What is still NOT done

- **No real bet and no practice order has ever gone through this.** Everything
  below the click is tested; the click itself has only been exercised with
  doubles.
- **The Kalshi web pages are still unverified** — their site builds in the
  browser and returns nothing to any tool here. Both the hand-off card and
  `PRACTICE_SETUP.md` say so and describe things functionally.
- **The void rate has not been watched** since the hand-off fix. That is the
  measurement that says whether the page was really the problem, and it needs
  him to use it.
