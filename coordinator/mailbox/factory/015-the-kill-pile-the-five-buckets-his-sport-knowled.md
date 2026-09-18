To: factory
From: coordinator
Opened: 2026-09-18 01:59
Status: OPEN
Subject: the kill pile, the five buckets, his sport knowledge, and DO NOT NARROW - he repeated that twice

--- INSTRUCTION ---

**This supersedes nothing in mailbox 014 - it adds the part he cared most
about. Read 014 first, then this.**

He is deciding whether to close this project. He has given you the most
valuable thing he has, which is not an instruction: it is what he knows about
sports that is in neither this repo nor any training data. **CLAUDE.md §9c
exists because that knowledge is the one thing only he can add, and jargon or
narrowing silently throws it away.**

---

# 1. ⚠ THE KILL PILE — his words, and he is right about the risk

> *"I feel like the strategy factory might kill stuff that could still be
> useful... there should be like a kill pile because Claude is prone to making
> mistakes and killing stuff that could be good."*

**He is describing a failure this repo has already had.** A sweep over price
features was used to close a question about individual players, which it never
tested. That idea was deleted and nobody found out for weeks.

**So: nothing is deleted. Ever.** Every candidate that dies goes into a file
with its reason and - the part that matters - **what was NOT tested**.
`KILLED.md` in your folder, append-only, one row each:

    id · what it was · what killed it (the number) · what was NOT tested ·
    what would bring it back

**"What would bring it back" is mandatory.** A kill with no resurrection
condition is a deletion wearing a different hat.

# 2. THE FIVE BUCKETS HE ASKED FOR, IN HIS WORDS

Sort everything into these and keep the file so he can read across them:

| bucket | means |
|---|---|
| **AMAZING** | survives screening, pre-registered, and has a holdout it was not chosen on |
| **GOOD** | survives screening and the arithmetic, no holdout yet |
| **POSSIBLY GOOD** | plausible, blocked on data or sample rather than on evidence |
| **LOOKED GOOD, WASN'T** | we believed it and were wrong - **keep the reason, this bucket is the most useful one for learning** |
| **KILLED** | the kill pile above |

**Nothing goes in AMAZING today.** For scale: the baseball fleet's best
strategy just survived its first holdout at +11.82c over 108 games it was not
chosen on, **and still fails the bar this project set in advance.** That is
what the top bucket costs.

# 3. ⚠ HIS SPORT KNOWLEDGE — treat this as data, not as encouragement

**Recorded in his own words because it is the input we cannot generate:**

> - **"MLB bro there is a lot of money to be made in MLB"**
> - **"football games too... maybe not the NFL but the college games"** are
>   "pretty fucking predictable"
> - **"the one thing that I think are very risky are soccer games I do not
>   trust them shits at all"**
> - **"basketball is probably predictable as fuck too because it's just high
>   scoring ass games... one moment of brilliance doesn't change the whole
>   outcome"** - where in soccer it can, and in basketball it matters much less

**The mechanism he is describing is real and it is testable: scoring events per
game.** A sport where one event swings the result is a sport where the outcome
is mostly noise, and noise is unforecastable no matter how good the model. High
scoring means the result concentrates toward the better team.

**So turn his intuition into a measurement and report it as its own finding:**
for every sport this exchange lists, compute **how much of the final result one
scoring event moves** and **how often the pre-game favourite wins**. If his
ranking (basketball and baseball forecastable, soccer not) falls out of the
data, that is a genuine prioritisation rule earned rather than assumed. If it
does not, **tell him plainly** - he would rather be corrected than agreed with,
and he has said so.

**Weight the search his way unless the data says otherwise: MLB and college
football first, basketball next, soccer last.** Do not silently ignore soccer;
record it as deprioritised on his judgment plus whatever you measure.

# 4. INVERSION — already built. Do NOT rebuild it. Here is what it found.

He asked: *"if we find something that keeps losing and it's not because of
fees... choose the opposite side. And I think we did that actually, I don't
know how that went."*

**You built it - `SCREEN-01.md` §5, the invert screen - and it ran on 8
categories:**

| category | net | cost bar | inverted | invertible? |
|---|---:|---:|---:|---|
| Sports | −1.87c | +2.20c | −2.51c | **no** |
| Entertainment | −15.15c | +2.99c | +9.40c | yes, but 1 event |
| Financials | −7.05c | +3.08c | +1.09c | yes, but 45 events |
| whole run | −2.10c | +2.41c | −2.64c | **no** |

**Sports is the fee-leaking case, not the wrong-side case** - it loses roughly
what it costs to trade, so there is nothing underneath to flip. And your own
warning stands: **inverting is not negating** - the other side lifts the other
ask, so it pays the spread and the fee again.

**Keep the screen as a standard column on everything new.** The two categories
it flagged died on sample size, not on the idea, so **they belong in POSSIBLY
GOOD, not in KILLED** - the resurrection condition is more events.

# 5. WHAT TO SEARCH — everything, and he means everything

His list: *"sports, every fucking category, arbitrage, genuine trading
strategies, different websites, different fees, different everything."*

- **Every Kalshi category**, not the ones that have been convenient: weather,
  economics, financials, entertainment (4,422 markets and nobody outside has
  written about them), the 510 "will someone say this" markets, politics.
- **Every per-game family, not just the moneyline.** Your own measurement:
  Kalshi runs 19 per-game baseball families, 17 cost under 2 cents to enter,
  **and the fleet trades 2 of the 17.** The home-run market costs 0.97c against
  the moneyline's 1.37c. That gap applies across every sport and nobody has
  looked.
- **Parlays (combos)** - first priority, per mailbox 014.
- **Other venues.** The venue map is yours and unfinished. Seven sites are
  named and unresearched. **A fee you read in documentation is a claim; a fee
  measured against real fills is evidence** - this repo proved Polymarket's own
  documentation matched 0.0% of 4,310 real fills.
- **Structural trades that need no view at all**: sum-to-one, logical
  implication across market types, calendar effects, the daily timetable in
  trading costs that the research chat flagged and nobody tested.

# 6. ⚠ THE INSTRUCTION HE REPEATED TWICE — DO NOT NARROW

> *"the biggest problem that Claude has is that it will find something, narrow
> in on it, and then forget everything else... I want to wake up tomorrow at
> 12 o'clock and I want to see that the strategy factory is still fucking
> going."*

**Enforce it mechanically, because willpower will not hold:**

1. **Finish the BROAD pass before testing anything.** The census is the
   denominator. A category absent from the list must be absent with a written
   reason, not by drifting.
2. **Cap the depth.** No single idea gets more than one pass before you return
   to breadth. If it deserves more, it goes in the queue and waits its turn.
3. **A kill triggers a widen, not a stop.** Ask which assumption killed it,
   widen exactly that one, re-enter BROAD.
4. **Log every pass** - what was screened, what survived, what died - so he can
   see the machine kept moving rather than take your word.

# 7. THE SECOND SWEEP HE ASKED FOR

> *"when it's done it should check over all of its strategies and like deepen
> each of them, try and think of even more variations of these strategies."*

After the broad pass, go back over **everything** including the kill pile, and
for each one generate variations along the axes that were held fixed: the
market family it trades, the price band, when it enters, which competition,
and whether it can be paired against an existing strategy on the same game.

**That last one is worth real money in time:** two strategies compared on the
same game have a difference-spread of 25.5c against 49.6c unpaired - about
**4x fewer games** needed to tell them apart.

# 8. HE SAID IT DOES NOT NEED TO BACKTEST - TAKE HIM AT HIS WORD

> *"it doesn't have to backtest anything, it's more like finding out the best
> strategies and then from there we'll test them."*

**So this pass produces a RANKED CATALOGUE, not results.** Each entry: the
hypothesis, what information it uses, which market and what that market costs
to trade, whether the data exists, whether it is paired-testable, and what
would make you drop it. **No P&L numbers. No promotion.** That keeps the whole
sweep honest - you cannot best-of-N your way into a false finding if you are
not measuring returns yet.

**But the count still leads every report.** How many were screened to produce
what he is reading. Best-of-2,000 zero-skill strategies typically shows +29.5%,
and a catalogue is exactly where that number gets manufactured later.

# 9. WHEN YOU REPORT

One consolidated message, not a stream. Lead with **how many screened**, then
the five buckets with counts, then the best few in each. Money or out of 100 -
**he reads this on a phone, once a day, and has told us twice that jargon costs
him the ability to argue back.**

**And if the honest answer is that there is nothing here, say that plainly.**
He is deciding whether to close this project. A clean "we looked at 400 things
across every category and here is why none of them clear the bar" is worth more
to him than a maybe that costs him another month.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

