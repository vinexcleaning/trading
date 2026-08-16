To: mlb
From: coordinator
Opened: 2026-08-16 19:04
Status: OPEN
Subject: Measure the capital squeeze - and price his 'only take the agreed games' rule against the alternatives

--- INSTRUCTION ---

**His observation, and nobody has measured it:** bets go on days before first
pitch and hold to settlement, so **money is locked up for a long time**. With
10-15 games a day and 5% a bet, he runs out of cash before he runs out of
signals. **He is already choosing which bets to take — by accident, in the order
they arrive.**

# JOB 1 — MEASURE THE CAPITAL CONSTRAINT

From `paper.db`, on `starter__hold`:

- **How long is a bet held?** From entry to settlement. Median, and the worst.
- **How much money is committed at once?** Day by day, the peak. Against an
  $83 bankroll at $4.15 a bet, when would he have run out?
- **How many signals would he have had to skip?** Per day: signals generated,
  signals affordable.
- **At 10% a bet, how much worse?** Same question, half the capacity.

**Report it as "on a $100 bankroll you could hold N bets at once, and the bot
generated M a day."** That is the sentence that decides everything below.

# JOB 2 — RE-RUN THE AGREEMENT SPLIT, AND SPLIT IT BY WHEN IT WAS FOUND

I ran this and got 66 games. **Check me** — I did it against `early__hold` only
and you may pair differently:

| | games | profit | staked | return |
|---|---|---|---|---|
| agreed | 17 | +$72.85 | $125.15 | +58.2% |
| opposite sides | 18 | +$44.80 | $184.20 | +24.3% |
| **alone** | **31** | **−$45.59** | $273.59 | **−16.7%** |

**Split before/after 2026-08-13**, the day the pattern was first found:

| | found on | new since |
|---|---|---|
| agreed | +47.8% (15) | **+160.9% (2)** |
| opposite | +19.7% (12) | +32.9% (6) |
| alone | −25.8% (19) | **−4.3% (12)** |

**The direction held on all three. The sizes are the problem:** 2 new agreed
games is nothing, and the alone bucket's loss shrank by four fifths, which is
equally consistent with the original −26% having been partly bad luck.

**Give him the honest number: how many more agreed games before this is a
decision rather than a hunch?** As a count and a date, the way `tennis` did.

# JOB 3 — HIS PROPOSAL, AND THE TRAP IN IT

> *"If there's too many games and too much stake tied up, wouldn't it be smarter
> to only put on the games where both agreed? It only uses our most successful
> games, doesn't include the ones that lose us money, and frees up money."*

**The logic is right and the trap is real, and he should get both.**

**Right:** when capital is the binding constraint you should spend it on the
best bets rather than the first ones. **He is already choosing; the only
question is whether he chooses deliberately.**

**Trap:** "take only the winning bucket" is selecting on the past. **But note
his version is the safe half** — he is declining a losing bucket, not doubling
into a winning one. Skipping costs missed bets; doubling down costs money.

**What I want measured, not argued:** what would the last 66 games have returned
under each rule — take everything · skip the alone ones · agreed only — **and
how much capital each needed**. If skipping frees enough money to take every
agreed bet, that is a real answer to his real problem.

**Do NOT change the live rule.** This is a measurement. **The `livedesk` desk
already shows `alone` on every card** and he can skip by hand today, which is
the reversible version.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100. **He does not know what this bot
does** — he asked today. Put one plain sentence at the top saying it backs the
team whose starting pitcher has been much better in his last three outings than
his season record, because the price is anchored to the season.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

