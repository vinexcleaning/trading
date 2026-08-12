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
at baseball's starting-pitcher picks instead of live tennis, with every guard
he asked for built in and tested by breaking it on purpose.

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

## The four guards

**Guard 1 — one bet per SIGNAL.** Not per game. He corrected that himself and
he was right: *"We should be allowed to reenter the same game if it's a
different scenario… It's a different bet but it's the same game."* What has to
be stopped is the same rule firing again on the same state, which is what
happened to him on tennis: *"it would keep repeating bets… which actually
worked out in our favour with the wins, but then it would also work against us
in the losses."* So: the same signal is blocked for ever, a genuinely different
trigger may open a second position, **two per game is the hard limit**, and it
**never adds to a position that is currently losing**.

**Guard 2 — two cut-offs, either one stops everything.** An **absolute floor**
at $50 in the account, which never moves. And a **trailing rule**: the running
total more than 35% below its highest point. From $83 that is $53.95; at a peak
of $300 it allows a $105 drawdown, which is his point — *"let's say the bot
keeps going and makes three hundred, and then we lose thirty. That's only ten
percent."* Both are on screen with the room left in each. The trailing rule
counts every open bet as a loss, so it cannot keep betting while $40 of losers
are in flight.

**Guard 3 — $4.15 a bet, flat.** 5% of $83. It does not grow when he is
winning: the stake is **clamped**, so a caller passing a bigger number still
gets $4.15. The paper bots drifted from 3 contracts to 25 on their own.

**Guard 4 — reconcile or refuse, and this is the one that protects the others.**
The profit figure on the tennis app was once about **$32 wrong** — his account
went $130 to $160 while it said he was down $2, with no trades of his own in
between. It was reported, "fixed", and stayed wrong. **The cut-off watches that
figure, so a ledger that can be $32 out is a cut-off that does not fire.**

So the window computes its running total two ways: from its own ledger, and
from the Kalshi balance you type into the box at the top. **If they differ by
more than a dollar it shows no profit figure at all and proposes nothing** until
it is sorted. A number that might be $32 wrong is worse than no number, because
you will act on it. (What that bug actually was, with the lines of code:
[DECISIONS.md](DECISIONS.md) D20.)

**The balance is TYPED IN, not read.** Reading it automatically needs a Kalshi
key, and a key in this folder would end the guarantee that the window cannot
send an order. Typing it costs five seconds after a game settles and keeps
`tests/test_paper_only.py` exactly as strict.

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

## It comes to you

When a new bet qualifies the window raises itself to the front and chimes —
**once per bet, not once per refresh**. His reason is a real risk control:
*"I don't really wanna be on Kalshi, because then I start looking at other
games and I'm like oh maybe I'll bet this, and then I lose all my money."* The
button then opens **that one game's page**, not the home page and not a browse
view.

## A pick can be withdrawn, and you are told

`starter__hold` takes at most one bet per game and then never writes another
row for it — so a superseded pick would sit on the card for ever. On
2026-08-12 that happened: `mlb` fixed a defect that cut one game's claimed
value from 99 cents to 71, below its own cost bar, and the old pick was still
being offered. The window now re-checks every pick against `mlb-paper`'s newest
unconstrained view and **drops it, with a line in the log saying why**, if the
strategy no longer wants it.

## The unusual-pick warning

When the bot claims a game is worth 12 cents or more away from what the market
says, the card carries a warning. That is not the bot making a small
correction; it is the bot calling the market badly wrong, and it is almost
always one pitcher with a tiny record being treated as if one bad outing were
a whole season. **3 of the 8 picks live on 2026-08-12 carried it** — one of
them leaning on a pitcher with a single career start. Filed to `mlb` as mailbox
008; **they found it was a rule and not one pitcher** (one third of an inning
qualified as "recent form") and fixed it in their amendment A3.

At their request there is now a second trigger: **a pitcher with 3 or fewer
career starts warns at a 6-cent gap**, because after A3 the huge gaps mostly
stop appearing and the gap alone would stop catching the thin cases. The
warning does not filter anything out; filtering would be this folder
second-guessing a strategy it does not own.

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
there the button test **skips** rather than fails — and a silently skipped test
is the same as no test. `test.bat` runs `livedesk\.venv` and sets
`LIVEDESK_REQUIRE_GUI=1`, which turns "no display" from a skip into a
**failure**. That command cannot come back green with the button untested.

This is not hypothetical. Creating and destroying a window per test made the
*second* one fail to start about half the time, and it failed **as a skip** —
so the run still read green while the test that matters had not run. The tests
now share one window and reset it between cases.

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
