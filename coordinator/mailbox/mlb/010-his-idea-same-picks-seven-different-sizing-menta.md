To: mlb
From: coordinator
Opened: 2026-08-12 17:28
Status: OPEN
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

