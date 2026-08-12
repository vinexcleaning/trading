# HANDOFF — livedesk

<!-- COORDINATOR-STATE
doing: nothing running; amendment 2 of mailbox 001 is implemented and the window is ready to open
left: he opens it, types his Kalshi balance in once, and places one real bet so the ledger and the reconcile check get exercised with real money
needs: no
-->

**As of 2026-08-12 05:45.** Built overnight from
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
