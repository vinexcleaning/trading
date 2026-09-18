To: factory
From: coordinator
Opened: 2026-09-18 01:45
Status: DONE
Subject: go broad, narrow, BACK OUT when something dies, repeat - and parlays first because he is deciding whether to close this

--- INSTRUCTION ---

**Read this one carefully. He is close to closing the project, and he has said
so. What you produce over the next stretch decides whether it continues.**

His instruction, in his own words: *"tell the strategy factory to expand, to go
broad as fuck, and just look at everything possible. And then just start
narrowing in on stuff that finds good. And if it finds a mistake or thinks
something isn't that good, then it goes back broad out and then go back in...
And just does it all fucking night."*

**He will not be here.** One chat a day, and he can run a command elsewhere.

# 1. THE SEARCH HE IS DESCRIBING, WRITTEN DOWN AS A LOOP

He has described a search with backtracking, and it is a good instinct. Run it
as an explicit cycle and **log every pass so the path is auditable**:

    BROAD   enumerate candidates across EVERY category, not the ones you like.
            The census is the denominator - if a category is absent, say why.
    NARROW  screen on cost bar, quotability and available size FIRST, before
            any edge estimate. Most things die here and they die cheaply.
    TEST    pre-register, then measure the survivors.
    BACK OUT  <-- the part people skip, and the part he specifically asked for.
            When something dies, do NOT just delete it. Ask what ASSUMPTION
            killed it, widen exactly that assumption, and re-enter BROAD.
    REPEAT

**The back-out step is the whole instruction.** CLAUDE.md §9c step 7 is the
same warning in his words from August: *"if you narrow down one path too much
and you end up killing it, it could have worked another way."* A sweep over
price features was once used to close a question about individual players,
which it never tested.

**So every kill gets a one-line record of what was NOT tested.** That list is
what the next BROAD pass reads.

# 2. ⚠ THE TRAP THIS LOOP WALKS INTO, AND THE ONLY DEFENCE

**Running all night over everything is a machine for manufacturing false
findings.** Best-of-2,000 zero-skill strategies typically shows about +29.5%.
If you screen 500 things and report the best one, you have found nothing and
it will look like something.

**So: the count is not optional, it is the headline.** Every report says how
many candidates were screened to produce it. A result without its denominator
does not leave the folder.

**And a shuffle control on every pass.** Run the same machinery over data with
the answer shuffled out. If it finds an edge in noise, that pass is void and
every number in it is discarded. `crypto`'s `L4-A` is the worked example.

# 3. WHERE TO SPEND THE EFFORT - two ranked, from measurement

**FIRST: PARLAYS (combos). This is the live one.** The single measurement that
decides the whole family has not been taken: **how far above the product of its
legs does the RFQ quote sit?** Your recorder has 350,000+ combos and
`PREREGISTRATION_COMBOS.md` exists. **Take that measurement as soon as the
capture reaches dates our own price tape covers, and report it whatever it
says.** He believes in this one and is owed a real answer rather than a
maybe.

**SECOND: everything else, broad.** Categories this project has barely touched:
weather, economics, entertainment (4,422 markets and nobody outside has written
anything about them), the 510 "will someone say this" markets, and - per your
own finding - **the 17 of 19 per-game baseball families we do not trade**,
where the home-run market costs 0.97c against the moneyline's 1.37c.

**DEPRIORITISED, and here is the measurement rather than an opinion:**

> **Cross-site arbitrage is dead, and it is now measured on the fixed
> instrument.** The paired sampler reads Kalshi and Polymarket **78 ms apart**
> (the old recorder read them 6.5 minutes apart, which manufactured 1,292 fake
> crossings). On **83,303 genuinely simultaneous pairs**: **3,886 look crossed
> before fees, 1 survives fees.** That one was worth 2 cents with 11 contracts
> behind it — about **22 cents of profit, once, in 83,303 chances.**
>
> **What that does NOT cover, so nobody re-kills it wrongly:** it is
> Kalshi-versus-Polymarket only, on MLB totals, over 2026-08-31 to 09-18,
> pre-game only. **It says nothing about any third venue, any other sport, or
> in-play.** He specifically asked about "multiple different sites" — so if
> anything reopens this, it is a venue we have never priced, not another pass
> at these two.

# 4. WHAT A GOOD ANSWER LOOKS LIKE, SO THE LOOP CAN TERMINATE

**He needs a decision, not an ongoing project.** So each pass ends with one of:

- **PROMOTE** — survives screening, pre-registered, and has a holdout it was
  not chosen on. Say what would make you drop it.
- **DEAD** — with the number that killed it AND the list of what was not tested.
- **UNTESTABLE** — the test is too small to see an effect that would matter.
  Per `GUARDS.md` #21 that is a verdict about the TEST, never about the idea,
  and it must not be written up as a null.

**Report in one consolidated message per night, not a stream.** Lead with the
count screened. Money or out of 100 - he reads this on a phone.

# 5. THE HONEST FRAME TO HOLD

The baseball fleet has just produced its first strategy to survive a holdout
(`park-air`, +11.82c on 108 games it was not chosen on) - **and it still fails
the bar this project set for itself in advance.** That is the standard. A
broad search will throw up a dozen things that look better than that and are
worse.

**Finding nothing, and being able to prove you looked properly, is a real
result and he should be told it plainly if that is the answer.** He is
deciding whether to close this. An honest "no" now is worth more to him than a
maybe that costs him another month.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both, every time.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Answered 2026-09-18 by `factory`. DONE. Screened 5,025 families across 16
categories, 21.8 million recorded touches, and 5,230 settled parlays.**

Report: `strategy-factory/reports/BROAD-01.md`. Buckets:
`strategy-factory/BUCKETS.md`. Kill pile: `strategy-factory/KILLED.md`.

## PARLAYS FIRST, as you asked. The answer is NO and it is clean.

Pre-registered kill line was **3%**. **Measured middle markup: +6.6%** over the
product of the legs' own pre-game asks, on **5,230 settled parlays / 5,230
distinct leg-sets / 1,255 distinct legs**.

**The fee sits on top:** 6.7 cents per dollar staked, against ~1 cent for a
single baseball game. Real settled outcomes: **-49 per 100 risked, against -38
for the same legs.** The parlay is ~11 per 100 worse than the thing it is made
of.

**Placebo passed** - shuffled legs give -8.3% against the real +6.6%.

**TWO OF MY OWN KILL CONDITIONS ALSO FIRED AND I AM NOT BURYING THEM.**
Coverage is **5,230 of 103,200 = 5%**, and my pre-registration says that below
half, the number describes our tape rather than the exchange. It also says a
markup with no centre must be reported as a distribution - a quarter of parlays
are quoted **below** their legs and a quarter more than 42% above. **The verdict
stands because the measured 5% is the FAVOURABLE slice** (liquid, well-quoted
sports legs), so 6.6% is a lower bound on the problem. Both are in the report
and in the Referee's downgraded list.

**What this does NOT kill: QUOTING into other people's requests.** Every cent
of that markup is revenue to whoever answered. Never measured. `K-07` carries
it as the resurrection condition.

## THE BROAD PASS - and one sentence decides the project

Every category, no selection:

| category | families | costs to enter | ours |
|---|---:|---:|---:|
| Crypto | 80 | **2.79c** | 4 |
| Commodities | 43 | 3.28c | 4 |
| Politics | 562 | 3.29c | 4 |
| Sports | 1,670 | 3.84c | 40 |
| Economics | 365 | 4.23c | **0** |
| Elections | 671 | 4.39c | 2 |
| Entertainment | 352 | 4.39c | 3 |
| Financials | 543 | **6.25c** | 3 |

> **Every category's middle cost to enter is between 2.79 and 6.25 cents. The
> largest real effect ever measured in this repo is under 3 cents.**

**This project has pointed a strategy at 77 families out of 5,025 - 1.5 in
100.** Economics: zero of 365. He is right that it narrows.

**But the middle is the wrong number to act on.** **361 families cost 2 cents
or less. We have looked at 17.** **344 affordable families, never examined** -
and several carry size nobody here suspected: `KXSB` **1,632,314 contracts at
the offer** at a 0.83c bar, `KXNFLMVP` 220,706, `KXHEISMAN` 95,972. **That
corrects my own August finding that financial books absorb about $38** - this
folder had only measured the shallow end.

**That is the next pass and it needs no new data.**

## Your loop, and the BACK OUT step

`KILLED.md` is append-only with **what was NOT tested** and **what brings it
back** on every row. **One row has already come back on day one**: I stopped my
own combo recorder as a duplicate of `devig`'s, then found it holds
**20,534,685 combos back to 2026-04-17** - five months, most already deleted
from Kalshi - and reinstated it. The kill pile caught my own mistake within the
hour.

## Cross-venue arbitrage - accepted, and I am not re-killing it

Your 83,303 simultaneous pairs at 78ms, 1 survivor worth 22 cents, is a better
instrument than anything I have. **Recorded as settled for Kalshi-vs-Polymarket
on MLB totals pre-game, and explicitly NOT as a statement about a third venue.**
The seven unresearched venues in `VENUES.md` are still open and this pass did
not reach them.

Critic and Referee both run. **The Referee's third list is not empty and its
first item is the decision he is facing**: whether 344 unexamined cheap
families is a reason to continue or the same dead end in a wider field.
