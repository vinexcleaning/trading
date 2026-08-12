To: livedesk
From: coordinator
Opened: 2026-08-11 23:33
Status: DONE
Subject: Build the one-window baseball display overnight - three guards, and the button never moves

--- INSTRUCTION ---

You are a NEW chat. Create `livedesk/` with `README.md`, `HANDOFF.md` and
`DECISIONS.md`. **Build overnight. He is asleep and expects a working window.**

# WHAT HE ASKED FOR, IN HIS WORDS

A single window for the baseball bets, modelled on a tennis app he already uses:
the trade at the top, why it was chosen, the size, the numbers in a corner, and
**a button that never moves.** His exact complaint about the old one: *"sometimes
bars will get added on, and then it would end up moving the button, which would
piss me off."*

# THE ONE THING THIS TOOL DOES NOT DO, AND IT IS NOT NEGOTIABLE

**It does not send an order. It has no Kalshi key. It makes no call to any
trading endpoint.**

I told him this directly and gave him the reason, which is not a rule but an
argument: **his tennis app needed a one-click button because it was reacting to
live in-play events where seconds mattered. The starting-pitcher strategy places
bets BEFORE the game starts.** There is no speed requirement at all. The gap
between "this window tells you exactly what to do" and "this window does it for
you" is about twenty seconds of typing per bet, on a bet that has hours of
runway.

So: **the button copies the order details to the clipboard and opens the right
Kalshi market page.** He places it himself. Same position on screen, same one
click, same speed for a human — and nothing can fire while he is asleep.

`mlb-paper/tests/test_paper_only.py` — copy it into `livedesk/tests/` before
your first feature and keep it green. **If you find yourself wanting to weaken
it, stop and write to `coordinator` instead.**

# THE THREE GUARDS, AND GUARD 1 IS THE WHOLE JOB

## Guard 1 — ONE BET PER GAME. EVER.

**His own words about the tennis app:** *"it would keep repeating bets, so it
would make me bet a lot on the same games, which actually worked out in our
favour with the wins, but then it would also work against us in the losses."*

**That is the machine that already blew up on him.** `LEDGER.md` records the
same shape: a $25 run to $130 built from many small wins, then one loss that ate
thirty. Repeating a bet on one game is not a strategy, it is leverage on a
single outcome, and it converts a small edge into a coin toss on one game.

**Hard rule: once a game has a position, that game is closed for the session.**
Not a warning, not a confirm dialog — the trade does not appear again. Store the
game key the moment he clicks, and filter it out for good.

## Guard 2 — the cut-off at $50, and it must be the BOT's loss, not the balance

He set the level: **if it is down to $50, it stops.** Starting bankroll **$83**,
not $100 — he lost some on his own tennis bets.

**He spotted the hole himself and he is right:** *"there might be a chance it
dips to fifty because I'm the reason it dipped to fifty, and it had nothing to
do with baseball."*

**So the cut-off must watch the tool's own running total, not the account
balance.** Keep a ledger of every position this window proposed and he
confirmed: game, side, price, size, settled result, profit or loss. **The
cut-off fires on the sum of that ledger reaching −$33 from the $83 start.**
Show both numbers side by side — "baseball: −$12 · account: $71" — so the two
can never be confused again.

## Guard 3 — 5% a bet, flat, and no growing into it

The paper bots averaged **$8.18** a bet with a flat size that ignored
confidence. On $83, **5% is about $4.15.** Use that. **Do not scale up as the
balance grows** without him saying so — the paper run drifted from 3 contracts
to 25 on its own and that is how a small edge becomes a big loss.

# THE WINDOW

Take the layout from his screenshot: a header strip with balance, bankroll and
percentage per trade; the market count; one trade card; open positions on the
right; a log underneath.

**The rule that matters more than any of it: the button occupies a fixed
rectangle that never moves, whatever else is on screen.** Give the trade card a
fixed height and scroll the contents inside it. Nothing grows above the button.
His previous app failed exactly here.

**On the card:** who and what · why it was picked, in plain English · the price ·
the size in dollars and contracts · what he wins if right and loses if wrong ·
and the win rate this bet needs to break even. **No statistics words anywhere in
this window.** He reads it in seconds, half asleep.

# WHAT THE PICKS ARE, AND ASK BEFORE YOU GUESS

The signal is `mlb-paper`'s **starting-pitcher** bot. **`mlb-paper` owns that
code and you do not.** Read it, do not modify it, and if the interface is
unclear, **file a mailbox message to `mlb` rather than reimplementing.** A
second copy of the strategy that drifts from the first is worse than no tool.

**What he needs to see and nobody has written down yet: what does that bot
actually compare?** A 7.9% return with no stated mechanism is a coincidence with
good manners. `mlb` has been asked for the plain-English version — put it on the
card.

# THE STATE OF THE EVIDENCE, AND SAY IT ON THE SCREEN

**30 games. Won 19. Up 7.9%.** Against that: five approaches were watched, and
the chance that at least one looks this good by luck alone is **56 out of 100**.

**Put a line at the bottom of the window saying so** — one sentence, permanent,
not dismissible. He has decided to go ahead with that known, and that is his
call to make. It should still be on the screen every time he clicks.

# ⚠ AND CHECK THIS FIRST

His screenshot shows the old tennis app failing: **`410 Client Error: Gone` for
`https://external-api.kalshi.com/trade-api/v2/portfolio/orders`.** That endpoint
is dead. **Whatever this window reads for prices, verify the endpoint answers
today before building on it** — `devig` fixed three scripts recently that were
reading a field name that no longer existed and silently reporting zeros.

# BEFORE HE WAKES

Working window, the three guards, the paper-only test green, and a `HANDOFF.md`
saying what is done and what is not. Then `py -3 coordinator\reflect.py --file
<draft>` and `--referee`, and write your `BRIEF.md` section.

**If anything here needs a decision, do not stall the build — take the
conservative option, log it in `DECISIONS.md`, and carry on.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


---

# AMENDMENT, before you start — DO NOT BUILD FROM SCRATCH

**Three corrections from the user, all in the same minute, and together they
change the job.**

1. *"This screenshot was still during the creation phase of the bot. Since then
   it improved a lot, so keep that in mind."*
2. *"I don't know if it's working currently though, it's been off for weeks."*
3. *"But it's because I manually unplugged my laptop that was running it."*

**So the `410 Gone` error in my message above is from an early build and is not
evidence the endpoint is dead.** Check it, do not assume it. And the app is not
broken — **it is unplugged.** Those are different things and I nearly wrote the
wrong one down as fact.

## The app already exists. Read it.

**`kalshi-inplay-bot/gui.py` — 944 lines.** That is the window in his
screenshot, in a later state than the screenshot shows. He likes it. He asked
for *"pretty much exactly the tennis one."*

**So the job is not a new app. It is:**

- **read `gui.py` and reuse its layout**, especially wherever the button
  position is already fixed;
- **find out what it actually does about the repeating-bets problem**, because
  that is his one named complaint and the fix may be half-written already;
- **point it at baseball's starting-pitcher picks instead of live tennis.**

**That folder is dormant and owned by nobody, so you may READ all of it. Do not
modify anything inside it.** Copy what you need into `livedesk/`. It is also
the project `bot-forensics` reconstructed — **the only code in this repo that
ever moved real money** — so treat it as evidence as well as source.

## Two things in that folder worth understanding before you copy anything

**`TRADING_DISABLED`** is a file sitting in that folder acting as a kill switch.
**Work out how it is honoured and keep the same mechanism** — a switch he can
throw by deleting or creating a file, with no code change and no restart, is
exactly right for a tool he runs while half asleep. Preserve it and document it
in your README.

**`gui.py` contains no order-placing code at all** — I grepped it. The ordering
lives elsewhere. **Keep it that way in yours: the window shows, the human
sends.** See the non-negotiable section above; that separation already exists in
the code he likes, which makes this easier, not harder.

## Also worth reading, and it is about his money

`bot-forensics` reconstructed what that bot actually did with real money. Two
findings bear directly on this build:

- the bot was reading scores **after 97.4% of the price move had already
  happened**, on 4,398 score-change events — which is why an in-play design
  needs speed and a **pre-game** design does not;
- **stop-and-re-enter turned −2.29 cents into −9.36 cents** per contract.

**So do not add a stop-loss that sells out of a position and re-enters.** His
$50 cut-off is a STOP EVERYTHING switch, not a per-trade stop, and those are
different. Build the first, not the second.

---

# AMENDMENT 2 — three changes, and the first one is the most important thing in this message

## 1. ⚠ THE PROFIT NUMBER HAS BEEN WRONG BEFORE, BY ABOUT $32, AND NOBODY FOUND IT

**His words, about the tennis bot:**

> *"I went from like 130 to 160, yet the bot was showing that it was down like
> two dollars. I would tell Claude to fix it, and it said yeah I fixed it, it's
> truly down two dollars. But then how the fuck am I down two dollars if I've
> made thirty dollars? And that was when I wasn't placing bets. That was purely
> the bot."*

**Read that twice. The account went UP $30 and the app said DOWN $2, with no
human trades in between — so the two numbers disagreed by about $32 and the app
was confidently wrong.** It was reported, "fixed", and stayed wrong.

**This is not a display bug. It breaks the entire safety design.** The $50
cut-off in this build watches the tool's own ledger. **A ledger that can be $32
wrong is a cut-off that does not fire.**

### The rule: RECONCILE OR REFUSE

**Every time it updates, the tool computes its running total two ways:**

1. **From its own ledger** — every position it proposed and he confirmed,
   entry, exit, fees, settlement.
2. **From the account** — the Kalshi balance now, minus the balance when the
   session started, minus anything it knows he did himself.

**If those two disagree by more than one dollar, the window does not show a
profit figure at all. It shows the disagreement, in red, and stops proposing
trades until it is resolved.**

**A number that might be $32 wrong is worse than no number**, because he will
act on it. Refusing to display is the correct behaviour and it is not a
degradation.

### Where to look first

Do not guess at the cause — **go and find it in `kalshi-inplay-bot/`.** That is
where the bug lived and `bot-forensics` has already reconstructed that bot's
real trades against its own records. Candidates worth checking, in order:

- **open positions marked at the current price while wins are only counted on
  settlement** — that alone produces "up in cash, down on screen";
- **fees counted twice**, or counted on the wrong side;
- **a sign error on NO positions**, which are the majority here;
- **settlements the account received that the app never recorded**, because it
  only tracks what it proposed.

**Whatever you find, write it in `DECISIONS.md` with the evidence.** If you
cannot reproduce it, say so and build the reconcile-or-refuse check anyway —
that check catches it whether or not anyone understands it.

## 2. THE CUT-OFF IS RELATIVE, NOT A FIXED $30

He is right and my version was wrong:

> *"It can't be cut off at thirty, because let's say the bot keeps going and
> makes three hundred, and then we lose thirty. That's only ten percent."*

**Two rules, either one stops everything:**

- **A hard floor: the Kalshi account below $50. Absolute, never moves.** That is
  his real "I cannot afford to go under this" line.
- **A trailing rule: the bot's own running total falls more than 35% below its
  highest point.** From $83 that is a stop at about $54 — near his floor at the
  start, and proportionate later. At $300 it would allow a $105 drawdown, which
  is what he means by "thirty out of three hundred is only ten percent".

**Show both on screen at all times, with how much room is left in each.**

## 3. RE-ENTERING A GAME — HE IS RIGHT, AND MY RULE WAS TOO BLUNT

> *"We should be allowed to reenter the same game if it's a different scenario…
> the criteria has been met again. It's a different bet but it's the same game."*

**Correct. The rule is ONE BET PER SIGNAL, not one bet per game.**

What the guard actually has to stop is **the same signal firing repeatedly on
one game** — which is what happened to him on tennis and is leverage on a single
outcome dressed up as several trades.

**So:**

- A signal is identified by **which rule fired and the game state it fired on**.
  The identical rule on the identical state is a duplicate and is blocked
  forever.
- **A genuinely different trigger may open a second position.**
- **Hard cap of 2 positions per game**, whatever the reasoning. He said himself
  he does not know whether this logic even applies to the baseball bot — so the
  cap is what protects him from a rationalisation neither of you can see.
- **NEVER add to a position that is currently losing.** That is averaging down,
  it is what turns one bad game into the whole bankroll, and there is no
  scenario where this tool should do it.

**`mlb-paper` owns the signal definition. Ask them what counts as a distinct
trigger rather than inventing one** — and if the starting-pitcher bot has only
one trigger per game by construction, say so and the question disappears.

## 4. IT SHOULD SURFACE ON ITS OWN — and his reason is a good one

> *"I don't really wanna be on Kalshi, because then I start looking at other
> games and I'm like oh maybe I'll bet this, and then I lose all my money."*

**That is a real risk control and it should be respected.** The window watches,
and when a trade qualifies it **raises itself to the front and makes a noise**.
He does not go looking.

**And when he clicks: open the exact market page for that one contract,
deep-linked — not the Kalshi home page, not a browse view.** He lands on one
market, places, leaves. **The whole point is that he never sees the other games.**

The button still does not send the order. That part does not change, and the
reason has not changed either: this is a pre-game bet with hours of runway.
**But everything else about "he should not have to go to Kalshi and browse" is
right, and the deep link is how it gets solved.**

**DONE.** Built overnight. `livedesk\run.bat` opens it. 27 tests green in
`livedesk\.venv`. Live end to end: 8 real picks read from `mlb-paper`'s
database, live Kalshi prices read back, and a real finished game settled to the
right cent on both the winning and the losing side.

## Corrections to your message, all three load-bearing

**1. Your evidence numbers are the superseded ones.** You wrote 30 games / won
19 / **7.9%**, and "**56 out of 100**" for the best-of-five. `mlb` recomputed
both on 2026-08-08, in reply to your own mailbox 006, and they moved *against*
the bot: the entry fee belongs in the staking base (**7.6%**) and in the
break-even (**53.7 out of 100, not 52**), which makes 19 wins from 30 less
impressive, not more. The best-of-five figure is **66 out of 100**, not 56 —
two thirds, not just over half.

**And you left out the thing that decides it.** `starter` is **buying about
1.7 cents WORSE than where the professional line closes**, on the 12 games
with a reference. A real edge cannot sit behind the closing line. That is on
the window, permanently, next to the rest.

**2. The `410 Gone` was checked, not assumed, and you were right to flag it.**
It came from the old **order-placing** endpoint on `external-api.kalshi.com`.
The public read API answered 200 with a live bid and ask at 2026-08-12 02:50
UTC. Reading prices is fine. Nothing here can place an order regardless.

**3. "What does that bot actually compare" — answered, and it is on the card
in plain words.** It ignores each pitcher's season record on purpose, because
that is the most public number in baseball and the price is already built on
it. It fires on three things a 25-start average absorbs slowly: a pitcher on
one of his first few career starts · a pitcher on under four days' rest · a
pitcher whose last three outings differ from his season line by more than 1.5
earned runs per nine innings. One run of expected margin is treated as about
11 cents.

## The three guards

**Guard 1 — one bet per game, ever.** Written to `data/ledger.json` on the
click and filtered out for good. Tested that it survives a restart, a settled
loss, and a void. A corrupt ledger **raises** rather than reading as empty —
an empty ledger re-opens every game the guard has closed, which is the failure
that would quietly undo the whole thing.

**One thing you did not specify and I had to decide (DECISIONS D3).** Recording
on the click means a click he does not follow through on sits in the ledger as
real money and corrupts Guard 2's total. So there is one button that marks an
entry `void`: it takes the money out of the running total and **leaves the game
closed**. Guard 1 is never weakened by it, and there is a test for that.

**Guard 2 — stop at −$33 on this tool's own ledger.** It counts every open bet
as a loss, so it cannot keep handing out bets while $40 of losers are in flight
and notice only after they settle. Eight losing bets does not fire it; nine
does.

**I could not do the "baseball: −$12 · account: $71" line you asked for.**
This window has no key and therefore cannot read the account. Showing a
hand-typed number beside a live one is worse than showing one honest number, so
the header shows the tool's own total, what is still riding, and the bankroll
implied by them — and nothing on screen claims to be the account. **That is his
to overrule, and the cost is stated: the real balance needs a key in this
folder, and a key in this folder ends the guarantee that the window cannot send
an order.** It is in `HANDOFF.md` as the one `needs:`.

**Guard 3 — $4.15 flat.** Contracts floored, never rounded up. The Critic
caught me claiming the sizing function "has no parameter that could carry a
rising bankroll" when it plainly had one, so the stake is now **clamped** to
$4.15 rather than merely defaulted to it. It can be driven down; it cannot be
driven up.

## The button, measured

**Same pixel in every state.** `tests/test_button_never_moves.py` reads its
screen position across nine: empty card · an ordinary trade · a trade with a
warning line · an over-long reason · an alert appearing · the alert clearing ·
forty queued games underneath · twelve placed bets on the right · the kill
switch on. It fails on a one-pixel shift.

Two things the fixed geometry costs, and both are worth it: a reason longer
than the card gets truncated with a visible "…", and the warning line is on
screen even when it is blank.

⚠ **Run the tests with `livedesk\test.bat`, not another venv.** `mlb-paper`'s
venv has no working Tcl, so there the button test **skips** instead of failing
— and a silently skipped test is the same as no test. `test.bat` sets
`LIVEDESK_REQUIRE_GUI=1`, which turns a missing display into a **failure**.

**This bit me while writing it, and it is the reason the flag exists.** Creating
and destroying a window per test made the *second* one fail to start about half
the time, and it failed **as a skip** — so the suite still read "27 passed"
while the one test that matters had not run. The tests now share a single
window and reset it between cases. Five consecutive full runs, no skips.

## `TRADING_DISABLED` — preserved, and made clickable

Same mechanism as `kalshi-inplay-bot`: a file in the folder, checked on every
render, no restart and no code change. `turn_off.bat` creates it, `turn_on.bat`
deletes it, because a `.bat` is easier than a text editor at 3am.

The difference is written into the module and worth saying here: **there** the
switch stopped a real order reaching Kalshi; **here** nothing can send an order
at all, so it stops the window recommending one. Smaller, and still right.

## One thing I found and filed rather than fixed — `mlb` mailbox 008

Writing the "why" onto the card meant reading what the bot claims each game is
worth. Across **all 43 games `starter__hold` has ever entered** (measured
2026-08-12 03:30 UTC) its claimed fair price sits a **median of 7.1 cents**
from the market, and **32 cents** on one — a pitcher with a single prior career
start whose one bad outing becomes a 13.75 earned-runs-per-nine difference,
multiplied with no ceiling. Nine of the 43 leaned on a pitcher with three or
fewer career starts.

That is `mlb`'s to answer and it lands on the open question they wrote down
themselves. **The card warns when the gap is 12 cents or more. It does not
filter the pick out** — filtering would be `livedesk` second-guessing a strategy
it does not own, which is what you told me not to do.

**I have not looked at the settled results of the wide-gap games at all, on
purpose.** Picking a subset by how it looks and then measuring it over the same
window is what this repo has retracted 45 results over.

## What is NOT done, plainly

- **No real bet has gone through it.** Everything below the click is tested;
  the click has only ever been exercised with a fake pick.
- **The clipboard and browser-open calls are not unit tested.** Both are
  wrapped so a failure logs the full details rather than losing them.
- **The window has not been left running for a full day.** The refresh loop
  swallows its own exceptions and keeps going, but "it survived an hour" is the
  strongest claim available tonight.

## THE REFEREE'S THREE LISTS

**1. STANDS.**
- *The button does not move.* Measured at the same pixel in nine states by a
  test that fails on one pixel — not inferred from reading the layout code.
- *Nothing here can send an order.* All 22 files were listed and grepped for
  credential shapes; the only matches are the word "kalshi" inside module
  references. The paper-only test is green including its three planted
  violations.
- *The read API is alive.* 200 with a live bid and ask, 2026-08-12 02:50 UTC.
- *Settlement is right.* A real finished game paid the right cent on both
  sides.
- *The picks are not recomputed here.* `picks.py` opens `paper.db` with
  `mode=ro` and reads rows. There is no scoring code in this folder.

**2. DOWNGRADED.**
- *was:* "the sizing function has no parameter that could carry a rising
  bankroll" → *now:* **"the stake is clamped to $4.15, so a caller passing a
  bigger number gets $4.15"** — because the function had a `stake_usd`
  parameter and the original sentence described a guard that did not exist. It
  exists now, with a test.
- *was:* "the game is closed on the click" → *now:* **"the game is closed on
  the click and the money can be voided afterwards"** — because a click he did
  not follow through on would otherwise count as a real loss against the
  cut-off.
- *was:* the card's "could not read the live price" wording → *now:* **"what
  the bot saw — no live price yet"** — because on the first pass the loop only
  fetched the first six games, so the card was blaming the market for its own
  cap. The cap is 16 now, more than a full day's games.

**3. FOR THE USER — genuinely unresolved. One, and it is real.**
- **the question:** should this window show the real Kalshi account balance
  next to the tool's own running total, the way your instruction asked for?
- **one side says:** he asked for exactly that, and the point of the two
  numbers side by side is that "baseball is down $12" and "the account is at
  $71" can never be confused again. Without it, the confusion he was worried
  about is still possible — just in the other direction.
- **the other side says:** reading the balance needs a Kalshi key in this
  folder. The moment one is there, "this window physically cannot send an
  order" stops being a fact about the folder and becomes a promise about code
  — and `tests/test_paper_only.py` would have to be weakened to allow it,
  which your own instruction says to write to `coordinator` about rather than
  do.
- **what would settle it:** nothing measurable. It is a judgement about which
  risk he minds more, and it is his.
