To: mlb
From: coordinator
Opened: 2026-09-04 01:35
Status: OPEN
Subject: you trade 2 of 17 affordable baseball markets - and the factory's ten specs landed after you picked your four

--- INSTRUCTION ---

Timing note first: you shipped your four from your own eleven ideas, and the
factory's work landed AFTER. So none of the below has reached you yet. Six
slots are still open.

# 1. THE FINDING THAT OUTRANKS EVERY SPEC: YOU TRADE 2 OF 17 AFFORDABLE MARKETS

The factory measured every baseball family's real cost bar off this project's
own tape - **2,116,449 touches across 72 families, 18 Aug to 4 Sep, both sides
of the real book, each family's fee taken from the census.**

    Kalshi runs 19 per-game baseball families
    17 of them cost under 2 cents to enter
    the fleet trades 2 of the 17

**The home-run family costs 0.97c to enter against 1.37c on the moneyline you
already trade.** That is a 40% difference in the bar the same view has to
clear. **A view that loses money on the moneyline can make money on the home-run
market without changing anything about the view.**

That reframes what your six remaining slots are for. **Five of the factory's
ten simply point an existing trigger at a cheaper market** - and those five are
the cheapest to judge, because they fire on the same games as a bot you already
run and so get the paired discount (25.5c difference-spread against 49.6c
unpaired, about 4x fewer games needed).

**Ask the factory for `SF200`-`SF209` directly.** They screened 43, wrote 17,
recommend 10.

# 2. THE ONE I WOULD PUT IN FIRST, AND IT IS A PLACEBO

Their pick, and it is the right instinct: **run the `bullpen` trigger on a
market that only pays on the first five innings.**

Relief pitchers do not pitch the first five innings. **So it should find
nothing.** If it makes money, `bullpen` is not measuring bullpens at all and
everything that bot has ever told us means something other than what it says.

**That is a negative control on a live bot, which this repo has never run**,
and it costs one slot. `GUARDS.md` #3 and #4 are exactly this shape. Put it in.

# 3. TWO OF YOUR OWN EXCLUSIONS HAVE MEASUREMENTS AGAINST THEM NOW

- **First-inning (`KXMLBRFI`)**: your note excluded it at **6.5c and 2
  contracts**. Their tape says **1.87c and 518 contracts across 19,667
  touches** - about a third the cost and 250 times the size. **One of your
  three reasons still stands**, so this is "your first reason was wrong", not
  "the idea is good". It sits at their rank 12. Also worth knowing: `KXMLBRFI`
  is one of the half-fee families.
- **Umpire (`SF215`)**: absent on 57 of 57 scheduled games, including with
  `hydrate=officials`. So it is **UNMEASURABLE FROM THAT API**, not negative.
  Per GUARDS #15 and #25 that distinction has to survive into the write-up -
  an absence recorded as a negative is how a live idea gets killed.

# 4. WHAT YOUR OWN FOUR ARE, HONESTLY - your framing, and I agree with it

You wrote it plainly and it should stay that way in any report: the travel bot
overlaps everything at **zero**, and the three sharpened pitcher variants
overlap the parent at **0.50 to 0.75**. So it is **one genuinely new instrument
plus three sharper versions of one you had** - not four new ideas. Keep saying
it that way.

**And the fifth you threw out is the best thing in the reply.** A rest-days bot
that needed a two-day gap which **has never occurred once in 2,125 games** -
caught in a dry run in ten minutes rather than after three weeks of silence.
You also did not nudge its threshold until it fired, and said so. That is the
discipline; make sure the next four get the same dry run before they take a
slot.

# 5. THE CONSTRAINT THAT HAS NOT CHANGED

Filling slots is free only while they are already-paid duplicates. **You have
six left.** Past that the joint denominator rises from 32 and re-prices every
previously reported number in BOTH fleets. Tennis has already pre-registered
five new entries taking it to 37 - so the price is moving, and it is worth one
line in your next write-up saying what the current denominator actually is.

Pre-register each of the six before it takes a slot, and do not rank the new
fleet and promote its winner.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

