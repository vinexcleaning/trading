# livedesk

**One window for the baseball bets.** It shows the next bet, why it was
picked, what it costs and what it pays. **You place it. This window cannot.**

```bash
livedesk\run.bat
```

To turn it off: `livedesk\turn_off.bat`. To turn it back on: `turn_on.bat`.

---

## What it is

It is the tennis window he already uses (`kalshi-inplay-bot/gui.py`), pointed
at baseball's starting-pitcher picks instead of live tennis, with the three
things he asked for built in and tested.

**It does not send an order.** There is no key in this folder, no signing
code, and no write call anywhere in it. `tests/test_paper_only.py` walks every
file here and fails the build if any appears.

That is not caution for its own sake. The tennis window needed one-click
because it was chasing live in-play events where seconds mattered. **The
starting-pitcher strategy places bets before the game starts** — the picks
land 14 to 22 hours out. The gap between "this window tells you exactly what
to do" and "this window does it for you" is about twenty seconds of typing,
on a bet with hours of runway. Nothing can fire while he is asleep.

The button copies the bet to the clipboard and opens the right Kalshi page.

## The three guards

**Guard 1 — one bet per game, ever.** The moment you click, that game is
written to `data/ledger.json` and never offered again. Not this session, not
after a restart, not after it wins, not after it loses. His words about the
old app: *"it would keep repeating bets, so it would make me bet a lot on the
same games, which actually worked out in our favour with the wins, but then it
would also work against us in the losses."*

**Guard 2 — stop everything at −$33, on this tool's own ledger.** Not on the
account balance. He spotted the hole himself: *"there might be a chance it
dips to fifty because I'm the reason it dipped to fifty, and it had nothing to
do with baseball."* Nothing in `ledger.py` can reach the network or read a
broker, so nothing he does to the account can trip it. It counts every open
bet as a loss, so it cannot keep handing out bets while $40 of losers are
still in flight.

**Guard 3 — $4.15 a bet, flat.** 5% of $83. It does not grow when he is
winning; `size_bet()` takes no argument that could carry a rising bankroll.
The paper bots drifted from 3 contracts to 25 on their own.

**And the kill switch.** A file called `TRADING_DISABLED` in this folder. If
it is there, the button is dead. No flag, no restart, no code change — the
same mechanism as `kalshi-inplay-bot`, which is the app he already trusts.

## Where the picks come from — and where they do NOT

They come from **`mlb-paper`**, which owns the starting-pitcher strategy.
`src/picks.py` opens that project's `paper.db` **read-only** and reads the
decisions its runner has already written. Bot `starter__hold` — the one that
takes at most one position per game.

**Nothing here scores a game, adjusts a price, or decides anything.** A second
copy of the strategy that drifts from the first is worse than no tool at all.
If a pick is wrong, it is wrong in `mlb-paper` and that is where it is fixed.

## What the bot is actually comparing

It ignores each pitcher's season record on purpose — that is the most public
number in baseball and the price is already built on it. It fires on three
things a 25-start average absorbs slowly:

- a pitcher making one of his first few career starts
- a pitcher on under four days' rest
- a pitcher whose last three outings differ from his season line by more than
  1.5 earned runs per nine innings

It turns that into cents — one run of expected margin is worth about 11 cents
— and bets only if that beats the spread plus the fee.

## What the evidence is, and it is on the screen permanently

**30 games. Won 19. Up 7.6 cents for every dollar laid out.** Five approaches
were watched at once, so **66 times out of 100 one of five looks this good
with nothing behind it**. And on the 12 games with a professional line to
check against, it was buying about **1.7 cents worse than where that line
closed** — a real edge cannot sit behind the closing line.

Those are `mlb`'s recomputed numbers from 2026-08-08, not the first pass. The
first pass said 7.9% and 56 out of 100; the fee belongs in the staking base
and in the break-even, and putting it there made the record *less* impressive,
not more.

He decided to run it knowing all of that. **That is his call, and the line
stays at the bottom of the window every time he clicks.**

## The unusual-pick warning

When the bot claims a game is worth 12 cents or more away from what the market
says, the card carries a warning. That is not the bot making a small
correction; it is the bot calling the market badly wrong, and it is almost
always one pitcher with a tiny record being treated as if one bad outing were
a whole season. **3 of the 8 picks live on 2026-08-12 carried it** — one of
them leaning on a pitcher with a single career start. Filed to `mlb` as
mailbox 008. The warning does not filter anything out; filtering would be this
folder second-guessing a strategy it does not own.

## The layout, and the one rule above all others

**The button occupies a fixed rectangle that never moves.** `tests/
test_button_never_moves.py` measures its screen position across eight states —
empty card, a trade, a warning line, an over-long reason, an alert appearing
and clearing, forty queued games, twelve placed bets, the kill switch — and
fails if it shifts by one pixel. His previous app failed exactly here.

## Running the tests

```bash
livedesk\test.bat
```

**Use that, not another venv.** `mlb-paper`'s venv has no working Tcl, so
there the button test **skips** rather than fails — and a silently skipped
test is the same as no test. `test.bat` runs `livedesk\.venv`, which has one,
and prints the skip reasons.

## Files

```
run.bat        open the window
turn_off.bat   create TRADING_DISABLED — the button goes dead
turn_on.bat    delete it
src/desk.py    the window
src/picks.py   reads mlb-paper's decisions, read-only, and writes the plain English
src/prices.py  Kalshi's public read API. GET only, no key
src/money.py   sizing, fees, break-even. Guard 3
src/ledger.py  the record of every bet. Guards 1 and 2
src/killswitch.py
tests/         paper-only, the three guards, the button
data/          gitignored. ledger.json lives here — his money records
```

Related: [DECISIONS.md](DECISIONS.md) · [HANDOFF.md](HANDOFF.md) ·
[../mlb-paper/README.md](../mlb-paper/README.md)
