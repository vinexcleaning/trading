To: devig
From: coordinator
Opened: 2026-08-20 19:50
Status: DONE
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

**Props are armed and cannot be missed now. The model is pre-registered. But I
have to retract something I told him two days ago, and correct the number this
whole plan was scoped on — both of them first.**

## ⚠ 1. RETRACTION — the seventeen-hour prop window came from ONE day and has now failed twice

**I reported that the prop board opens 16.9 hours before first pitch and that the
kill condition therefore did not fire.** It is in my 021 reply, in `BRIEF.md`, and
I said it to him directly.

| day | watched | result |
|---|---|---|
| **08-18** | 47 samples, 05:21→20:04Z | props appeared **16.9 h out**, live **44 of 45 samples** |
| **08-20** | 17 samples, 04:52→08:55Z | **EMPTY throughout** — inside the window that was full on the 18th |
| **08-21** | checked at **16.1 h out**, the same point in the cycle as the 18th's first sighting | **EMPTY.** 18 games listed, 17 upcoming |

**All three passed the GUARDS #27 control** — the same call returned Exact Scores,
Next Run and Double Result each time. **It is a genuinely empty prop board on all
three days, not a block.**

**The honest statement: the board was live fifteen hours on one day and absent
through comparable windows on two others, and I do not know what makes the
difference.** A hypothesis I have NOT tested: pitcher props may appear only once
starting pitchers are confirmed, which is irregular. Naming it so it is not
mistaken for a measurement.

**And the kill condition was written against the wrong failure.** §3a says "under
two hours before first pitch". Read literally it still does not fire — when the
board is up it is up for hours. **But the risk is not a short window, it is an
unpredictable one.** A strategy that only trades on the days a feed happens to be
posted is not the same strategy, and that difference is most of the value. **The
gate is amended before any price is compared: the board must be present on a
majority of days at a usable offset, across at least a week. That has not been
passed.** Written up in `RESULTS_PROPS_WINDOW.md`.

## 2. Props — armed, idempotent, and watchdogged, which the last one was not

You were right that "it fires by itself" is not the job being done.

`props_n3.py --wait 4320 --once-only`, **registered in `runners/runners.json`**:
waits up to **72 hours**, fires the comparison the first time the board opens, and
**exits immediately if the capture already exists** — which is what makes it safe
for the watchdog to restart forever.

**The Kalshi half is tested and works** — 23 player ladders, 111 rungs, all
monotone, all two-sided. So the machinery is ready and the report shape is
written; when the board opens the answer comes out the same day.

**⚠ And this matters: the previous prop watcher died at 15 hours of its 48 when
the machine rebooted at 21:41 on the 18th. The recorders came through the same
reboot with no gap over 45 minutes, because they are watchdogged.** That is the
registration difference, measured on a real reboot rather than my staged one.

**On the fee point — taken, and already applied.** On totals it turned out the
matched rungs sit at 30–70¢ where the fee is 1.68–1.71¢, *not* at the extremes,
and the cheap rungs had no reference at all. The props bar is computed per rung
from the price that rung actually trades at, and its distribution is printed, not
a single number.

## ⚠ 3. CORRECTION — 854 settled games, not 160. The three-week wait does not exist

**Your count came from `record.db`, which only began on 2026-08-06 and only holds
what the recorder saw. Kalshi's API still serves settled markets back to
2026-06-30.**

| checked 2026-08-21 | |
|---|---|
| settled `KXMLBTOTAL` rungs retrievable | **10,431** |
| **settled GAMES** | **854** |
| game-days covered | **66** |
| historical prices | **retrievable** — candlesticks return `yes_ask.close_dollars` per minute |

**Against `K014`'s bar — 481 to detect a large edge, 2,084 for a small one — we
are already past the first and 41% of the way to the second.**

**What has not changed, and belongs in the report either way: the small-edge bar
needs 2,084 games at ~15 a day, so a small edge stays undetectable this season.**

## 4. The dataset needs no external source, which I did not expect

**The settlement ladder is self-describing.** "Over 10.5 = yes" with
"over 11.5 = no" means the game finished on exactly 11 runs. **Checked on 104
consecutive ladders: every one crosses exactly once, none contradicts itself.**

**So one free endpoint gives the outcome and a second gives the price we would
have paid.** No scraper, no paid feed, no login, and nothing to ask him for.

## 5. `PREREGISTRATION_TOTALSMODEL.md` — committed before the model exists

Unit is **one game**, never a rung. Holdout is the **newest 30% of game-DAYS**,
sealed as a constant before the first fit, opened once. Features strictly from
games finishing before the one predicted, price from before first pitch, cost per
rung from `common/kalshi_fees.py`.

**Four controls, and P3 is the one I expect to bite:** shuffled outcomes; the
market's own price as the forecast; **a constant league-average total**; and the
sell side. **Weather died on exactly P3** — climatology beat the real model
+1.37¢ to +0.43¢, and a know-nothing 50% model still cleared the gate at +1.01¢.
If a constant trades as well as team form, team form is decoration.

**Not integrated, not traded, no credential, no order code.** And if it ever
survives that far, the paper-only canary gets written before the feature does.

## 6. Say back to him

**He proposed the condition that fixed the objection, unprompted — build it,
don't integrate it until it's backtested. That is the right instinct.** It is
also what makes the 854-game correction useful rather than tempting: more data
brings the *test* forward, not the trading.

---

## REFEREE — three lists

**1. STANDS**
- **854 settled games with retrievable pre-game asks**, and the final total
  recoverable from the ladder alone on **104 of 104** checked.
- **The props machinery is ready and the Kalshi half is tested** — 111 rungs, all
  monotone.
- **Registration survives reboots and non-registration does not**, measured on
  the same reboot.

**2. DOWNGRADED**
- **was:** "the prop board opens 16.9 hours before first pitch, so the kill
  condition does not fire."
  **now:** "the board was live fifteen hours on one day and absent on two others
  at the same offset; availability is unpredictable and the gate is now a
  majority of days across a week, which has not been passed."
  **because:** one day is a look, not a conclusion, and I generalised it.
- **was:** "160 settled games, three weeks to the easy bar."
  **now:** "854 settled games, already past it; the small-edge bar is still out
  of reach this season."
  **because:** the API retains far more than the recorder captured.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** the prop board's availability is unpredictable. **Do we spend
  a week measuring when it is up before comparing any prices, or compare on the
  first day it opens and treat availability as a separate problem?**
- **One side:** the comparison is cheap and could kill the idea in an hour, the
  way the retail test did. Waiting a week to find out *when* we could have run a
  test we could run tomorrow is backwards.
- **The other side:** if the board is only up two days in seven, the answer to
  "do they disagree" is nearly irrelevant — there is no strategy either way, and
  we would have spent the effort to learn something we cannot use.
- **What would settle it:** nothing cheap; both cost about the same. It is a
  judgement about which failure he would rather find out about first.
