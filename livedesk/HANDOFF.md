# HANDOFF — livedesk

<!-- COORDINATOR-STATE
doing: the one-window baseball desk is built, tested and running; picks read live from mlb-paper
left: he opens it and places one real bet, so the ledger and the settlement path get exercised with real money
needs: yes - the window shows no account balance because it has no Kalshi key; does he want the real balance beside the tool's own total, knowing that needs a key in this folder?
-->

**As of 2026-08-12 03:45.** Built overnight from
`coordinator/mailbox/livedesk/001`. Working window, three guards, 26 tests
green.

## Open it

```bash
livedesk\run.bat
```

Off: `turn_off.bat`. On: `turn_on.bat`.

## What is DONE

- **The window.** `src/desk.py`. Header with the running total and the rules;
  one card; the bets he has placed on the right; a log; a permanent evidence
  line at the bottom.
- **The button does not move.** Measured, not asserted —
  `tests/test_button_never_moves.py` checks its screen position across eight
  states and fails on a one-pixel shift. Verified at x=107, y=500 in all of
  them.
- **Guard 1** — one bet per game, ever. Written to `data/ledger.json` on the
  click, survives restart, survives a settled loss, survives a void.
- **Guard 2** — stop everything at −$33 on this tool's own ledger, counting
  open bets as losses. Cannot read an account balance; there is a structural
  test that it has no path to one.
- **Guard 3** — $4.15 flat, contracts floored, no growth with a rising
  bankroll.
- **Kill switch** — `TRADING_DISABLED`, same mechanism as
  `kalshi-inplay-bot`. A file, no restart, no code change.
- **Paper-only test** copied from `mlb-paper` and green, including its
  guard-rot check against three planted violations.
- **Live end to end.** 8 real picks read from `mlb-paper`'s database, 6 live
  prices read from Kalshi's public API, and a real finished game
  (`KXMLBGAME-26AUG111940BALMIN-BAL`) settled to the right cent on both the
  winning and the losing side.

## What is NOT done

- **No real bet has been placed through it.** Everything below the click is
  tested; the click itself has only ever been tested with a fake pick. The
  first real one is the real test.
- **The clipboard and browser-open paths are not unit tested.** They are
  wrapped so a failure logs the details rather than losing them, but a
  headless test of `webbrowser.open` would only test the stub.
- **No account balance.** See the question above and DECISIONS.md D6.
- **Settlement runs only while the window is open.** If he places a bet and
  closes the window for two days, the ledger catches up the next time it opens
  — Kalshi keeps `result` on the market. It does not need the window to have
  been running.
- **The window has not been left running for a full day.** The refresh loop
  swallows its own exceptions and keeps going, but "it survived an hour" is
  the strongest claim available tonight.

## The thing to look at first tomorrow

`coordinator/mailbox/mlb/008` — the starter bot's claimed fair price is a
median of **7.1 cents** away from the market across all 43 games it has
entered, and **32 cents** on one, driven by a pitcher with a single career
start. That is `mlb`'s to answer; `livedesk` warns on the card and does not
filter.

## Where the picks come from

`mlb-paper/data/paper.db`, read-only, bot `starter__hold`. If that runner
stops, this window says so in words on the card rather than showing a stale
game. `mlb-paper` owns the strategy — nothing here recomputes it.
