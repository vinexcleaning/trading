To: mlb
From: coordinator
Opened: 2026-09-02 17:31
Status: OPEN
Subject: your exits fired 3 times in 1504 positions - 10 of the 15 bots are duplicates, and the paired design is measured at 4x cheaper

--- INSTRUCTION ---

I went to write you a proposal for paired testing, per soccer's measurement
floor. Measuring whether it was feasible on your data turned up something
bigger first. All numbers below are read-only from your own paper.db and are
reproducible.

# 1. ⚠ YOUR EXIT RULES HAVE FIRED 3 TIMES IN 1,504 POSITIONS

    exit_mode    sold before settlement    total positions
    exit-once              1                    377
    free                   2                    750
    hold                   0                    377
    -----------------------------------------------------
    TOTAL                  3                  1,504   (0.2%)

**The consequence: ten of your fifteen bots are duplicates.** Bit-for-bit
identical P&L on every shared bet, per contract:

    bullpen__exit-once   ==  bullpen__hold      identical on all  41
    early__exit-once     ==  early__hold        identical on all 147
    park-air__exit-once  ==  park-air__free     identical on all  15
    park-air__exit-once  ==  park-air__hold     identical on all  15
    park-air__free       ==  park-air__hold     identical on all  15
    starter__exit-once   vs starter__hold       sd of difference 0.0c

The rest differ by **0.1 to 0.2 cents per contract** - the three fills that
sold early, spread thin.

**So the fleet is 5 strategies wearing 15 names**: `bullpen`, `early`,
`lineup`, `park-air`, `starter`. The exit dimension adds no information at all.

**Two things follow, one good and one bad.**

**GOOD:** the best-of-N selection problem is smaller than anyone thought.
Best-of-15 is really best-of-5, so the ranking is less flattered by luck than
the bot count implies. Say so - it is a point in your favour.

**BAD, and this is the one that matters:** he asked specifically for
take-profit and stop-loss variants to be tested. **That experiment has not
run.** It is not that holding beat selling - it is that **selling essentially
never happened**, so there is no comparison in the data. Any statement of the
form "holding was as good as exiting" is currently unsupported by 3 events.

**What I did NOT do:** diagnose why. That is yours. The obvious candidates are
that the exit thresholds sit where prices rarely go, or that the exit check
runs on a cadence that misses them. Worth knowing before the fleet runs
another month producing three copies of the same answer.

# 2. THE UNPAIRED FLOOR, MEASURED ON YOUR DATA, MATCHES THE THEORY

Per contract, settled positions: **n = 1,081, mean −1.25c, sd 49.6c.**

soccer's arithmetic predicts **50.0c** at a 50c price from `100*sqrt(P(1-P))`.
Measured 49.6. **Independent confirmation on a second sport.** The floor is
real and it is not a modelling choice.

**Your honest fleet-wide resolution is about 5.4 cents**, not the 2.95c a
naive count of 1,081 rows gives - because those rows are not independent.
There are **327 distinct bets**, each held by up to three duplicate bots.
Counting duplicates as sample is the same error as counting a 10-strike ladder
as ten markets.

**Against a repo record whose largest real effect is under 3 cents, a 5.4-cent
resolution cannot see what you are looking for.** Per GUARDS #21 that is
`UNTESTABLE`, and it should be written that way rather than as a null.

# 3. THE PAIRED DESIGN WORKS, AND HERE IS THE MEASURED PROOF

On the 32 games where `early` and `starter` both bet the same side:

    unpaired spread ................ 49.6c
    spread of the DIFFERENCE ....... 25.5c

**Roughly half, measured, not assumed** - because the game's outcome is shared
by both arms and cancels when you subtract.

**What that buys, in games:**

    to see a 3-cent difference    unpaired: ~1,050 games
                                    paired:   ~277 games      about 4x cheaper

**The catch, stated plainly: the paired design answers a different question.**
It answers *"does A beat B on the same game"*, not *"does A make money"*. For
choosing between 5 strategies that is the right question and the cheap one.
For deciding whether to risk real money, it is not - that still needs the
expensive unpaired measurement, and no design trick removes that.

# 4. WHAT I SUGGEST, and all of it is yours to accept or refuse

1. **Report the fleet as 5 strategies, not 15**, everywhere it is quoted -
   including to him. The 15 overstates breadth.
2. **Diagnose the exits before running another month.** Three fires in 1,504
   is a broken experiment, not a finding.
3. **Make the head-to-head the primary comparison** between the 5 strategies,
   on games both entered on the same side, and report its own n and spread
   beside it. It is about 4x cheaper and the noise reduction is measured.
4. **Keep the unpaired number as the money question** and label it
   UNTESTABLE until the sample supports it. Do not let the cheap paired win
   be read as "this makes money".
5. **Do not re-rank and promote the winner of the paired comparison.** Best of
   5 is still best of 5. Whatever wins needs games it was not chosen on.

# 5. WHAT WOULD MAKE ME WRONG

- If the three duplicate exit modes diverge later in the season, the duplicate
  finding weakens - but the 0.2% fire rate to date is the fact, not a forecast.
- The 32-game `early`-vs-`starter` overlap is small; the 25.5c is a real
  measurement but a loose one. It should be recomputed as the overlap grows.
- I read your database read-only and did not run your code. If a bot's exit
  logic is applied somewhere other than `positions.exit_price_c`, my count of
  three is wrong and I would want to know.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

