To: mlb
From: coordinator
Opened: 2026-08-12 17:28
Status: DONE
Subject: His idea: same picks, seven different sizing mentalities, $250 each, paper only

--- INSTRUCTION ---

**His idea, and it is a good one.** In his words:

> *"I wanna keep thinking of more strategies and integrating more and more bots
> — but just paper trading. We'll see the results after a week or two, see which
> bots are doing the best. We'll give them all a $250 balance, and they have
> different mentalities so they can place however much money they want. We could
> put one bot that literally gambles half their portfolio, one that only gambles
> five percent."*

# WHY THIS IS WORTH BUILDING EVEN THOUGH THE ANSWER IS PARTLY KNOWN

**Same picks, different money management.** That is a clean experiment and it is
free, because the signals already exist and nothing new needs collecting.

**What is known in advance, and say it in the pre-registration so nobody claims
it as a discovery later:** sizing cannot change the expected result. Betting
half the pot and betting 5% of it have the same average outcome. **What sizing
changes is the chance of going broke**, and that is the thing worth showing him
with his own bots rather than with my arithmetic.

**He has heard the table from me and it did not land.** Watching a
half-the-pot bot blow up on a $250 paper balance will, and it costs nothing.

# THE ARMS

Same starting balance, **$250**, same signals, same entry prices. Only the stake
rule differs:

| arm | stake |
|---|---|
| flat-5 | 5% of the STARTING balance, fixed forever |
| flat-5-compounding | 5% of the CURRENT balance |
| flat-20 | 20% of current |
| half | 50% of current |
| all-in | 100% of current |
| kelly | the mathematically optimal fraction for the edge it believes it has |
| kelly-half | half of that, which is what people actually use |

**Report per arm: final balance · biggest drop from a peak · how many went
below $50 · how many went to zero · and the WORST single day.**

**Run each arm many times over the same games in a different order** if the
machinery allows it. One pass tells you one story; a hundred passes tells you
the range, and the range is the entire point. If reordering is not meaningful
for settled games, say so and report the single pass with that limit stated.

# THE TRAP, AND IT IS THE WHOLE REASON TO PRE-REGISTER THIS

**After a week, one arm will be ahead. It will probably be one of the aggressive
ones.** That is what aggressive sizing does over short runs — it wins bigger
when it wins.

**Write down NOW, before any result exists, how the winner gets judged.** My
suggestion, and it is his to accept or change: an arm only counts as better if
it is ahead **and** never went below $50 **and** its worst drop was smaller than
its final gain. Whatever the rule is, it goes in
`mlb-paper/PREREGISTRATION_SIZING.md` before the first number.

# ALSO WORTH ADDING, SINCE THE MACHINERY IS BEING TOUCHED

He wants **more strategies**, not just more sizing rules. The `signal` chat has
been redirected to hunt for approaches nobody here has tried. **When something
comes back, this is the folder that would paper-test it.** Say what a new
mentality costs to add — an afternoon, or a week — because that number decides
how many ideas are worth taking.

# TWO THINGS HE HAS NOT ANSWERED YET

Both from your own brief, and I am relaying rather than deciding:

1. **The cap on how wrong the starter bot may declare the market to be.** You
   said a 32-cent disagreement is indefensible but that a cap is a new rule.
   **I agree with your refusal to slip it in, and I have put the question to
   him.** Until he answers, leave it uncapped and keep the record split.
2. The 60-second admin install for the restart-on-failure.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.

**No statistics words.** Money, or out of 100. He reads this on a phone.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. Built, pre-registered first, and run.** `PREREGISTRATION_SIZING.md` was written and committed before `src/sizing.py` existed; §1 states the known-in-advance answer above every number, as you asked.

## The result, 73 settled picks, 2,000 orderings each, 2026-08-12

| arm | median final | ever below $50 | to zero | biggest fall | rule |
|---|---|---|---|---|---|
| `flat-5` | **$405.59** | 0.0% | 0.0% | $74 | **PASS** |
| `flat-5-comp` | **$419.67** | 0.0% | 0.0% | $103 | **PASS** |
| `flat-20` | **$572.04** | 7.0% | 0.0% | $755 | fail |
| `half` | **$1.92** | 100% | 0.0% | $688 | fail |
| `all-in` | **$0.24** | 100% | 2.2% | $439 | fail |
| `kelly` | $293.82 | 6.3% | 0.0% | $449 | fail |
| `kelly-half` | $364.11 | 0.0% | 0.0% | $196 | fail |

**Same picks. Same games. Same prices. $250 each.** The half-the-pot bot ends with **$1.92** and the all-in bot with **24 cents**.

## ⚠ Your trap fired on the very first run, exactly as you wrote it

**`flat-20` finished HIGHEST of all seven — $572 — and fails the rule.** 7% of orderings dipped under $50 and its worst fall was $755, more than twice its gain. Judged on final balance alone it would have been crowned. **That is the single most valuable thing in this test and it exists because you insisted the rule be fixed first.**

## Two of my own predictions were wrong, both recorded in A1

1. I predicted `kelly-half` would clear all three. **It fails condition 3** — biggest fall $196 against a $114 gain. Safe, but not clearing the bar.
2. I predicted `all-in` reaches zero **over 90%** of the time. Measured: **2.2%.**

**The second was badly wrong and the mechanism is worth having.** Contracts are integers, so `all-in` can only buy `floor(balance / price)` and **the change always stays behind**. It never quite dies — it *decays*. Median $0.24 from $250 is a **99.9% loss**, which is a worse sentence than "goes broke 90% of the time" and I would rather have the wrong prediction on the record than restate it quietly.

## Your reordering instruction was the right call, and here is what it bought

2,000 shuffles rather than one pass. The single real ordering for `flat-20` is $569.87 and its median is $572.04 — **almost identical, which would have looked like stability.** The range is where the truth is: the same arm goes under $50 in 7% of orderings. **One pass would have shown a well-behaved winner.**

## What a new mentality costs to add — you asked, and the number decides how many ideas are worth taking

**About half a day each**, provided the data is already in the brief (pitchers, bullpen, lineups, park, weather, form, the sharp reference). That is: write the decision function with its magnitude stated in cents, add it to the registry, add a pre-registration section, and let it run.

**It is a week, not an afternoon, if the idea needs a new data source** — a new source means a robots check, a fetcher, a cache, a schema assert and a field-trap review. Weather cost a day on its own because the two obvious providers both forbid crawling.

**And the real cost is not building — it is the denominator.** Every new mentality is another bot in the joint correction, currently 32 across both tests. Adding five ideas raises the bar every existing result must clear. **Cheap to build, not free to add.** Worth saying to him plainly before he asks for ten.

## The two open questions

1. **The cap.** Agreed, and thank you for not letting me slip it in. Leaving it uncapped, record still split.
2. **The admin install.** Still outstanding. It cost 12.7 hours once already.

## One thing I did NOT do

I did not run the arms on `bullpen` or `park-air`. Those have 11 and 3 settled games, and a compounding arm over 3 games is not a measurement of anything. `starter` + `early` gives 73. **Stated rather than silently pooled.**

## What this cannot show, per §6

Whether any pick is good. **`starter` is still buying behind the closing sharp line**, so if the edge is negative every arm loses and the aggressive ones lose faster. This is a result about *sizing*, not a rescue of the signal — and `flat-5` finishing at $405 must not be read as the strategy working.
