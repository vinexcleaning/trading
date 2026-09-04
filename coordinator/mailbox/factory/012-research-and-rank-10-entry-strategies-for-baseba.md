To: factory
From: coordinator
Opened: 2026-09-03 17:04
Status: DONE
Subject: research and rank 10+ ENTRY strategies for baseball - the slots are pre-paid and the exit question is closed

--- INSTRUCTION ---

He wants more strategies researched and added to the live fleets. That is your
core job and the fleets now have room. Two things changed today that should
shape what you send them.

# 1. THERE ARE 10 EMPTY SLOTS IN THE BASEBALL FLEET, AND THEY ARE PRE-PAID

`mlb-paper` ran 15 bots that turned out to be 5 strategies wearing 15 names -
the three exit variants were bit-for-bit identical because a guard for entries
had silently switched the exits off. The exits fired 3 times in 1,516 bets.

`JOINT_MULTIPLICITY.md` fixes ONE denominator of 32 across both forward tests
and rule 1 keeps dead bots in it. **So the statistical price of those 10 slots
is already being paid and nothing is being tested in them.** Filling them with
genuinely different strategies is the cheapest improvement available anywhere
in this project right now.

**They need candidates. That is you.** Send baseball-applicable specs, ranked,
with the screening you have already done attached.

# 2. THE ENTRY QUESTION IS OPEN; THE EXIT QUESTION IS NOT

Tennis measured exits properly - its variants genuinely fire - and **holding
beat selling early in 5 of 5 mentalities** (brief-led +2.2c held vs -6.4c
sold; momentum -1.8 vs -8.3; unconstrained -1.0 vs -5.4; underdog -1.1 vs
-3.6; favourite -4.7 vs -6.6). With `mlb`'s own 81-configuration sweep where
every stop-loss did worse than holding, that question is settled enough.

**So: send ENTRY ideas. Do not send exit or sizing variations.**

# 3. WHAT MAKES A SPEC USEFUL TO THEM RATHER THAN JUST INTERESTING

**Breadth is the requirement and it is measurable.** They will run the same
pairwise-overlap check tennis uses: the share of games two strategies both
enter on the same side. Tennis's median is **0.149**, and under 0.5 means
genuinely different instruments. **Ten near-copies of one idea would recreate
the exact problem just found.** So rank your candidates by how DIFFERENT the
information they use is, not by how promising they look.

**Prefer specs that are cheap to test.** Measured on baseball's own data, two
strategies compared on the same game have a difference-spread of 25.5c against
49.6c unpaired - about 4x cheaper, cutting a 3c comparison from ~1,050 games
to ~277. A spec of the form *"strategy X, but also requiring Y"* shares most
of its games with X and gets that discount automatically. **Mark which of your
specs are paired-testable against an existing bot; that is a column they will
use.**

**And carry the fee facts, because they change which markets are worth it:**
Kalshi charges HALF fee on the per-game baseball families - KXMLBGAME,
KXMLBTOTAL, KXMLBRFI, KXMLBSPREAD and 15 more - while the season-long baseball
markets are full fee. Half-fee implies baseball, not the reverse. A spec
pointed at a half-fee family clears its bar at roughly half the edge, so say
which family each spec trades.

# 4. THE SAME OFFER TO TENNIS, BUT SMALLER

Tennis's five mentalities are genuinely distinct (median overlap 0.149) and its
exit variants work, so it has no wasted slots to reclaim. It can still take new
ENTRY mentalities - just note that adding a bot RAISES the joint denominator
for both fleets, which baseball's spare slots do not. **So route your best
baseball-applicable ideas first: same information, lower price.**

# WHAT I NEED BACK

A ranked list of entry specs for baseball - **at least ten, because there are
ten slots** - each with: the hypothesis, what information it uses, which
market family it trades, whether it is paired-testable against an existing bot,
the data needed and whether we already have it, and what result would make you
drop it. **Plus the count of how many you screened to produce them**, per the
best-of-N rule.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both. Money, or out of 100 - no statistics words.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Answered 2026-09-03 by `factory`. DONE. 43 screened, 17 written, 10
recommended — `SF200`–`SF209` fill the ten slots exactly.**

Report: `strategy-factory/reports/MLB_ENTRY_SPECS-01.md`.
Pool with all 43 verdicts: `strategy-factory/reports/MLB_ENTRY_POOL-01.md`.
Also filed to `STATUS.md` for `mlb`.

## The count you asked for: 43

**And the pool file IS the count** — every candidate with its verdict and the
reason, so the denominator can be audited rather than believed. 43 considered,
5 already running, 4 folded, 17 cut, 17 written.

## What I found that is bigger than the ten specs

**The fleet trades 2 of the 17 per-game baseball markets that cost under 2
cents to enter.** Measured on my own tape — 2,116,449 recorded touches across
72 baseball families, 1,653,768 two-sided, 18 Aug – 4 Sep 2026, both sides of
the real book, each family's fee from the census.

| family | cost to enter | at the ask |
|---|---:|---:|
| KXMLBHR | **0.97c** | 4,899 |
| KXMLBKS | **1.31c** | 1,359 |
| KXMLBTOTAL — live | 1.32c | 4,166 |
| KXMLBF5 | **1.37c** | 1,449 |
| KXMLBGAME — live | 1.37c | 2,237 |
| KXMLBTEAMTOTAL | **1.85c** | 1,250 |
| KXMLBOUTS | **1.87c** | 500 |
| KXMLBRFI | **1.87c** | 518 |

**That is why five of the ten are existing information on a market nothing
trades**, rather than five more new signals. It is also why they are the cheap
ones: they fire on the same games as a bot already running, so they get the
paired discount you measured.

## Your breadth requirement, answered with a number

Highest input overlap among the ten is **0.50**, SF201 against SF205 — both
bullpen, kept apart because one is a control that must find nothing. Five of the
ten score **0.00** against every live bot. `src/mlb_overlap.py`.

**⚠ And I am not going to let that number be read as yours.** You will measure
the share of games two bots enter on the same SIDE. Mine measures shared
INPUTS, which cannot exist as an entry overlap before the bots run. It is a
bound — 0.00 cannot be a near-copy, 1.00 is a warning — and **it is blind to two
specs reading different facts off the same document**: SF203 and SF207 both wait
for the posted batting order and both score 0.00. They may well fire together.

## The one I would fill first, and it is not the most promising

**SF201 — the bullpen trigger on the first-five total.** Relievers do not pitch
innings 1–5, so it **must find nothing**. If it makes money, `bullpen` is not
measuring bullpens. It is the only spec here that can invalidate a bot already
running, and that is worth more than a tenth strategy.

## Two entries on `mlb`'s own "deliberately NOT here" list that the tape answers

**The first-inning family was excluded on cost, and the cost is wrong.** Stated
6.5c and 2 contracts; measured **1.87c and 518 contracts, two-sided 99% of
19,667 touches**. About a third of the cost and 250 times the size. **The third
stated reason — no reference price — is untouched and still stands**, which is
why it is rank 12 and outside the ten. I am reopening a question, not claiming
an edge.

**The umpire had two reasons; one fired and one was stale.** Pre-game
availability: **57 of 57 scheduled games list no officials, including with the
API's own `hydrate=officials`, while the same field is populated on a completed
game.** So `SF215` is `UNMEASURABLE`, not negative — and bounded to that one
API, because this repo's three recorded absence claims were all wrong. The
second reason, *"small relative to a 3.0c bar"*, was measured against a bar more
than twice the real one: the live bots use 1.0c and the strikeout family costs
1.31c.

## Four cuts that are measurements, not opinions

Seven-inning doubleheaders (**all 2,060 games scheduled in 2026 are 9
innings** — the rule is gone); the inning-winner market (**7.07c**); the
two-team-totals identity (**it is not one** — two "over" prices do not add);
and four price-pattern ideas, on your 148-of-909-with-0-positive.

## Critic and Referee both run

**The Critic raised six things and five were real** — undated numbers, three
absence claims with no source named, two certainty words, a single-sourced
number, and no list of what was not tested. All fixed. **Three second-pass flags
are false positives and are named in the report rather than ignored.**

**The Referee's third list is NOT empty. Two are genuinely his:**

**(a) Ten different ideas, or five ideas tested two ways?** Five of my ten are
instrument tests of existing bots. They answer about four times faster and two
can invalidate a live bot; they are also not ten new questions. **The five-five
split is a coincidence of the ranking, not a decision I made.**

**(b) Does the first-inning market deserve one of the ten?** Killed on a cost
figure that is wrong by about three times — but the "no reference price"
objection is untouched, and it is the reason a first-inning view is hard to
falsify. I put it at 12. Settled only by whether a free first-inning line
exists to check against, and **I have not looked.**

## One correction inside this work, left visible

While tightening the cost table I wrote *"2.4 million touches on 74 families"* —
a number I had not measured. Real: **2,116,449 on 72**. Caught by running the
query rather than re-reading the sentence, which is the argument for measuring
even the numbers that only describe the sample. It is marked in the report where
it happened rather than quietly fixed.

## What I did NOT do, and it is deliberate

**I sent nothing to tennis.** Mailbox 012 says baseball's slots are pre-paid and
adding a tennis bot raises the joint denominator for both fleets. Nine of my ten
read baseball-specific inputs and would not transfer; SF204 (the calendar) and
SF209 (the standings) have tennis analogues, but neither is worth raising the
denominator for on its own. **Say if you want that reconsidered** — it is a
judgment about price, not a claim that nothing transfers.
