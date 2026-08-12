To: livedesk
From: coordinator
Opened: 2026-08-11 23:33
Status: OPEN
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
