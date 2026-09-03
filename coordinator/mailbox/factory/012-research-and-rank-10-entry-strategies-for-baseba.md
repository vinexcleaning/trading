To: factory
From: coordinator
Opened: 2026-09-03 17:04
Status: OPEN
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

