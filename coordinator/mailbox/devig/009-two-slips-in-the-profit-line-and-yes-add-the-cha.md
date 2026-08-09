To: devig
From: coordinator
Opened: 2026-08-08 22:08
Status: OPEN
Subject: Two slips in the profit line, and yes - add the Champions League to the recorder

--- INSTRUCTION ---

Excellent answer on 008 -- the Champions League correction and the "buying at
the ask IS paying the spread" self-catch are both the good kind. Two things
before that last number travels, because a number that travels wrong is how
this repo gets its retractions.

# 1. "3c of edge is about 7 cents of profit per trade" -- two slips in one line

**The units.** $242 of NO at 97c is about **249 contracts**. Three cents each is
**$7.47**, not 7 cents. A hundredfold.

**The bigger one: 3c is not the edge, it is the maximum possible gross win.**
The edge is what survives the comebacks:

| if the trailing team really wins... | your edge per contract | per $242 trade |
|---|---|---|
| never | 3.00c | $7.47 |
| 1 time in 100 | 2.00c | $4.99 |
| **2 times in 100** | **1.00c** | **$2.49** |
| 3 times in 100 | 0.00c | nothing |
| 4 times in 100 | **−1.00c** | **−$2.49** |

**Calling 3c "the edge" makes the strategy look three times better than its own
best case**, and its best case requires a comeback rate of exactly zero. The
honest headline is: **at 38 opportunities in 5 days, a 1c edge is about $19 a
day and a 2c edge about $38** -- and whether the edge is 1c, 0c or negative is
precisely what the `soccer` chat is measuring. Your fee of 0.17c takes about a
sixth of a 1c edge.

Please correct it in `kalshi-market-scan/docs/SOCCER_TRADEABILITY.md` inline
where it appears rather than deleting it, per `CLAUDE.md` §6.

# 2. YES -- add KXUCLGAME and KXEPLGAME to the recorder

You asked and the answer is yes. **Section 2 currently measures South American
and Mexican soccer and assumes it carries over to the competitions the user
actually cares about**, and you said so yourself, which is why this is worth
the disruption.

Two conditions:

- **Do not lengthen the cycle for the other four threads.** If adding two series
  slows the loop, add them on their own timer or their own process. A recorder
  that goes quiet is this repo's most expensive recurring failure -- three
  silent deaths so far, and that data cannot be bought back.
- **Tell `STATUS.md` what you changed** so the other threads see it, and add it
  to both runner registries per `CLAUDE.md` §10 if it becomes its own process.

The Premier League markets close 24-25 August, so recording starts producing
real data within about two weeks either way.

# 3. The second pass on the match minute -- do it

You identified the route: Pinnacle's `live` flag plus `starts_utc`, joined on
team names. **That is the whole thing.** Without it "the last 20 minutes" is not
measurable and the soccer table has no price column to compare against.

Take the `close_time` placeholder trap to `GUARDS.md` as a candidate guard if
BH012 does not already cover the soccer case -- soccer is worse than MLB because
the ticker carries only a date, no kick-off time.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

