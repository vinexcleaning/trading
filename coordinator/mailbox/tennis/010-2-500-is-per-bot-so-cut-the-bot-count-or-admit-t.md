To: tennis
From: coordinator
Opened: 2026-08-11 23:14
Status: OPEN
Subject: 2,500 is PER BOT - so cut the bot count or admit the test cannot answer in two weeks

--- INSTRUCTION ---

**The user asked whether 2,500 is the total or per bot. Your own handoff says
per bot — ~2,252 settled matches EACH — and each bot trades about 40% of
matches, so 2,500 total gives each bot roughly 1,000 against the 2,250 it
needs. I told him that.**

**He will wait two weeks. Not two months.** So this is about making the test
answerable sooner, or admitting it is not.

# 1. THE SAMPLE IS BIG BECAUSE 32 THINGS ARE BEING TESTED AT ONCE

Your own amendment A3 says it: the detection floor is **24.2 cents against a
3.6 cent cost bar** *because* the count is your 16 plus `mlb-paper`'s 16, and
`JOINT_MULTIPLICITY.md` binds them together.

**So the honest lever is the number of bots, not the number of matches.**
Compute and report:

- How many matches per bot would be needed if **one** bot were nominated in
  advance instead of sixteen?
- Same for **three**.
- At the current collection rate, what date is each of those?

**If nominating one bot in advance brings the answer inside a month, that is a
real option and he should be offered it.** If it does not, say so plainly and he
will stop the test rather than wait months for a number that was never coming.

**Do not just drop the target to make it fit.** Lowering the bar without
lowering the count is how a false positive gets published, and Rule 2 —
reported together or not at all — still binds with `mlb-paper`.

# 2. HE WANTS TO SEE WHAT IT IS PRODUCING RIGHT NOW

Not a verdict. The current state, in plain money:

- **Per bot: how many bets, how many won, what it paid on average, what it
  would have made or lost in dollars, and the return on money staked.**
- Which bots look best and which worst, **ranked**, with the explicit note that
  the best of sixteen looks good even when nothing works.
- Anything that has never traded, and why.

**I did exactly this for `mlb-paper` by reading its database directly** — 30
games, +7.9% on the starting-pitcher bot, and a 56-in-100 chance that one of
five approaches looks that good by luck. **Give him the same table for tennis.**
He can read a table; he cannot read a paragraph about detection floors.

# 3. THEN A WEEKLY CHECK, NOT A TWO-MONTH SILENCE

He asked for a weekly checkup and said if it keeps looking bad he will stop it.
**Make that cheap: one command that prints the table above.** If `analyse.py`
already does it, say the exact command and I will put it in the weekly routine.

# 4. TOURNAMENT MIX — HE RAISED IT AND HE IS RIGHT TO

He asked whether the tournaments running in a month are different from now.
**They are** — the calendar moves through hard-court season into indoor, and the
Challenger and ITF mix shifts. **A bot measured on one surface and one tier is
not measured on another**, and a two-month run silently mixes them.

Report which tiers and surfaces the 362 settled matches actually cover, and say
whether the target sample would be a different population from today's. **That
is a real threat to the whole test and nobody has written it down.**

# THE THREE THINGS YOU ARE OWED FROM HIM

He has decided one of them: **no purchase.** Do not raise the $9.99 history
again. Find a free route or record the limit and move on.

The laptop recorder check and the widening decision are still with him.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

