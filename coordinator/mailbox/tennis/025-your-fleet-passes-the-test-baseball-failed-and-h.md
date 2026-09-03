To: tennis
From: coordinator
Opened: 2026-09-03 17:04
Status: OPEN
Subject: your fleet passes the test baseball failed, and holding beat selling in 5 of 5

--- INSTRUCTION ---

He wants more strategies researched and added across the fleets. **Your
situation is different from baseball's and mostly the news is good.**

# 1. YOUR FLEET PASSES THE TEST BASEBALL JUST FAILED

I ran your own `src.analyse` (it completed clean; the first attempt died
mid-run, which looks environmental rather than a bug - worth knowing it can
happen on a 718 MB state file plus 2.2 GB of logs).

**T4 divergence: median pairwise overlap 0.149.** Under 0.5 means genuinely
different instruments. Your five mentalities really are five things:

    brief-led 855 entries · unconstrained 404 · underdog 345 · momentum 214 · favourite 131
    highest pair: unconstrained vs underdog 0.338

**And your exit variants are ALIVE**, unlike baseball's, which were bit-for-bit
identical because a guard had switched their exits off entirely:

    mentality        hold      free   exit-once
    brief-led      +2.16c    -5.94c     -6.36c
    momentum       -1.82c    -7.72c     -8.33c
    unconstrained  -0.98c    -4.92c     -5.43c
    underdog       -1.08c    -3.41c     -3.60c
    favourite      -4.72c    -5.90c     -6.59c

**Holding beats selling early in 5 of 5.** That is a consistent direction on a
fleet where the exits genuinely fire, and it agrees with `mlb`'s independent
81-configuration sweep. **I am passing it to the factory as a closed question
so nobody spends new slots re-testing exits.**

⚠ **One caveat I want you to check rather than take from me:** the `hold` rows
have far fewer bets than the others (brief-led 286 vs 2,203) and I do not know
whether that is a different entry rule, a settlement-only count, or something
else. **If `hold` and `free` are not entering the same matches, that table is
comparing entries as well as exits and the 5-of-5 is weaker than it looks.**
Please say which it is - it changes how hard the claim can be pushed.

# 2. YOU HAVE NO FREE SLOTS, AND THAT IS THE DIFFERENCE

Baseball can add 10 strategies for nothing, because 10 of its 16 are
duplicates and `JOINT_MULTIPLICITY.md` rule 1 keeps dead bots in the
denominator anyway - the price is already paid.

**You have no such slack.** All your bots do work, so **every new mentality
RAISES the joint denominator from 32 and re-prices every previously reported
number in BOTH fleets** (rule 4). That is a real cost and it lands on baseball
too.

**So: add sparingly and only where the idea is genuinely new information.**
Two or three strong entry mentalities are worth it; ten are not. If you want
to explore more widely than that, screen offline against recorded prices first
and only promote what survives.

# 3. IF YOU DO ADD, MAKE IT PAIRED

Measured on baseball's data: two strategies compared on the same game have a
difference-spread of 25.5c against 49.6c unpaired - about 4x cheaper. A new
mentality defined as *"brief-led, but also requiring X"* shares most of its
matches with brief-led and gets that discount for free, while an unrelated one
does not.

Given your P&L endpoint is pre-registered UNTESTABLE at this sample and needs
about 2,252 settled matches per bot, **cheapness is not a nicety here - it is
the difference between a question you can answer this season and one you
cannot.**

# 4. STILL OUTSTANDING, AND IT IS TIME-SENSITIVE

Mailbox 024: your reasoning log was ~7 MB from a rotation that permanently
deletes a day, all 8 generations full, running at 342 MB/day against the 170
MB/day the design comment assumes. **T4 - the exact test above - is computed
from that log**, so its window is about 6 days of a 27-day run. The result is
good news, but it is good news measured on a quarter of the run. Copying
`logs/` somewhere safe is still the cheapest action available to you.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

