To: mlb
From: coordinator
Opened: 2026-09-03 17:04
Status: OPEN
Subject: you have 10 empty slots you are already paying for - fill them with entry strategies, not exits

--- INSTRUCTION ---

He wants more strategies researched and added. For you specifically this is
close to FREE, and that is worth explaining before you start.

# YOU HAVE 10 EMPTY SLOTS YOU ARE ALREADY PAYING FOR

`JOINT_MULTIPLICITY.md` fixes ONE denominator of 32 across your 16 and tennis's
16, and **rule 1 says cancelled and zero-entry bots stay in it.** So the
statistical price of 16 bots is being paid whatever those 16 contain.

Right now 10 of yours are bit-for-bit duplicates - the exit dimension that fired
3 times in 1,516 bets. **So you are paying for 16 tests and running 5.**

**Filling those 10 slots with genuinely different strategies costs nothing that
is not already being spent.** Same denominator, three times the information.
That is the single cheapest improvement available to this project right now.

⚠ **Do NOT let this become 10 variations on one idea.** Ten near-copies would
re-create exactly the situation you just found, and the divergence check below
is how you prove it did not happen.

# WHAT TO ADD - the requirement is BREADTH, and it is measurable

Before promoting anything, run the same overlap test tennis has
(`analyse.py:t4_divergence`): for each pair of strategies, the share of games
they both entered on the same side. **Tennis's median is 0.149 and its reading
is right: under 0.5 means genuinely different instruments, over 0.8 means the
labels are decoration.** Your current five would score near 1.0 against their
own duplicates. **Publish that number with the new fleet or the breadth claim
is unevidenced.**

Ideas are available and you should not invent from scratch:
- **the strategy factory** has screened a large number of structural ideas and
  keeps a spec list; ask it for baseball-applicable candidates and its census
  of which market families are even quotable
- **the extractors/signal chat** has read outside sources into scored specs
- **your own archive** - 863 games with minute prices, so a candidate can be
  screened offline before it ever takes a slot

Cheap places to look that your current five do not touch, offered as prompts
rather than instructions: umpire assignment · travel and rest days · bullpen
usage in the previous 48 hours · weather beyond the park-air term · lineup
handedness against the starter · first-inning-only markets (KXMLBRFI is
half-fee too) · the run-total family rather than moneyline.

# THE DESIGN CHANGE THAT MAKES ALL OF IT CHEAPER

**Prefer strategies that can be tested PAIRED against an existing one on the
same game.** Measured on your own data: two strategies on the same game and
side have a difference-spread of 25.5c against 49.6c unpaired - it cuts the
games needed for a 3c comparison from about 1,050 to about 277, roughly 4x.

So a new strategy defined as *"`starter`, but also requiring X"* is far cheaper
to evaluate than an unrelated one, because it shares most of its games with
`starter` and the game outcome cancels. **Build some of the ten that way on
purpose.**

# THREE RULES, and they are not negotiable

1. **Pre-register each new strategy before it takes a slot** - hypothesis, why
   an edge might exist, entry, exit, and what result would make you drop it.
   `PREREGISTRATION_*.md` in your folder, committed before the first result.
2. **The denominator does not fall.** If you end up with more than 16, it
   rises and every previously reported number is recomputed. Say so in the
   write-up.
3. **Do not rank the new fleet and promote the winner.** Best-of-15 is still
   best-of-15. Anything that looks good needs games it was not chosen on.

# ONE THING NOT TO SPEND A SLOT ON

**Do not add more exit variants.** Tennis just measured the exit question
properly - its variants ARE alive - and holding beat selling early in **5 of 5
mentalities**: brief-led +2.2c held vs -6.4c sold, momentum -1.8 vs -8.3,
unconstrained -1.0 vs -5.4, underdog -1.1 vs -3.6, favourite -4.7 vs -6.6.
Five out of five in the same direction, on a fleet where the exits genuinely
fire. Combined with your own 81-configuration sweep where every stop-loss did
worse than holding, the exit question is answered well enough that spending
scarce slots on it again would be waste.

**Spend the slots on ENTRY ideas. That is where nothing is settled.**

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

