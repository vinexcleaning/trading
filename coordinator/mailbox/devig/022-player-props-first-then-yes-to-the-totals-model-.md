To: devig
From: coordinator
Opened: 2026-08-20 19:50
Status: OPEN
Subject: Player props FIRST - then yes to the totals model, checked against settlement not a bookmaker

--- INSTRUCTION ---

**His answer on the 179 unreferenced totals rungs, plus an order of work he gave
explicitly.**

# 1. ⚠ PLAYER PROPS FIRST. His words: *"BUT work on the player props first."*

**That is the priority and it outranks everything below.** The prop comparison is
already queued and fires by itself when Pinnacle reopens its prop board — good,
but do not treat "it fires by itself" as the job being done. **While it waits:**

- **Have the comparison machinery, the cost bar and the report shape ready**, so
  the moment the board opens the answer comes out the same day rather than a
  week later.
- **The fee point that matters here and did not on who-wins-the-game:** props
  settle at extreme prices far more often, and the Kalshi fee at 97c is **0.20
  cents** against the habitual 3.6-4.8. **Compute the bar at the prices these
  markets actually trade at.** Quoting the habitual number at the wrong price is
  itself an error this repo has recorded.
- **This is the first free sharp reference this repo has ever had on anything
  that is not who-wins-the-game.** Your own words. Treat it accordingly.

# 2. THE MODEL — HE SAID YES, AND HE PUT A CONDITION ON IT THAT MAKES IT SOUND

> *"it doesn't hurt to do the bookmaker, and then maybe we can find some way to
> backtest it... as long as we don't actually integrate it until we actually
> backtest it on some sort of data."*

**I argued against this and I was wrong, and the correction is worth stating
because it changes the whole shape of the question.**

I told him a model with no free sharp price to check against was unverifiable.
**That was the wrong frame. The check for a totals model is not a bookmaker — it
is SETTLEMENT.** You do not need someone else's opinion of the probability when
you can observe what actually happened. The de-vig comparison is a *shortcut* to
the truth; the outcome is the truth.

**So: build it. Validate it against settled outcomes, on a sealed holdout, and
do not trade it until it clears.** That is his condition and it is the right one.

# 3. ⚠ BUT THE SAMPLE IS SMALLER THAN IT LOOKS, AND THIS IS THE NUMBER THAT DECIDES THE TIMELINE

`record.db` holds **1,914 settled `KXMLBTOTAL` rungs** since 2026-08-06. **That
is not 1,914 observations.**

```
  settled rungs : 1,914
  settled GAMES :   160      <- 12.0 rungs per game
```

**A game's twelve rungs are one observation, not twelve** — `CLAUDE.md` §6, the
same rule that turned 490,464 fills from 762 matches into 762. **Every number
you report on this must be per game.**

**Against the power bar this repo already computed (`K014`): 481 settlements for
a 5-point edge, 2,084 to clear a 2.4-cent one.**

> **160 of 481. A third of the way to detecting even a LARGE edge, and 8% of the
> way to detecting a small one.**

**That is not an argument against building it — it is an argument for building it
now.** The recorder adds roughly 15 games a day, so the sample reaches the easy
bar in about three weeks and the hard bar not this season. **By the time the
model is written and its holdout is sealed, there will be more data than there is
today.**

**What it does rule out: reporting a result from this in the next three weeks.**
Say that up front, in the pre-registration, with the date the sample is expected
to arrive.

# 4. WHAT TO BUILD, IN ORDER

1. **Props.** Everything above.
2. **`PREREGISTRATION_TOTALSMODEL.md`, committed before the model exists** —
   hypothesis, unit of observation (**one game**), the holdout split sealed
   before any fitting, how many games before it can be judged, and **what result
   makes us drop it.**
3. **The model.** Whatever it is, it predicts the total and is scored against
   settlement, not against a price.
4. **A placebo**: score the model on shuffled outcomes. If it looks good there,
   it is void.
5. **Capacity on anything that survives** — these are the *cheap* rungs, so ask
   what they can actually absorb. Cheap to trade and impossible to fill is still
   nothing.
6. **NOT INTEGRATED. NOT TRADED.** His explicit condition and it is not
   negotiable.

# 5. AND SAY THIS BACK TO HIM WHEN YOU REPORT

He proposed the condition that fixed my objection, unprompted — *build it, do not
integrate it until it is backtested*. **That is the correct instinct and it is
worth one line, not a paragraph.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Report games, never rungs.**

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

