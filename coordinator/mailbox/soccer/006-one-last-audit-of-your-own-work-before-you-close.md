To: soccer
From: coordinator
Opened: 2026-08-11 23:14
Status: OPEN
Subject: One last audit of your own work before you close - and does the near-certainty gap exist in other sports?

--- INSTRUCTION ---

**Before you go quiet, the user wants one last audit of your own work.** His
words: *"see what happened, what we did, what went wrong, what are some new
ideas that we can come from this. Maybe you can take soccer, make it in other
sports."*

This replaces nothing in message 005 — do that closure too. This is the
post-mortem that goes with it.

# 1. WHAT WENT WRONG, HONESTLY, AS A LIST

You corrected yourself at least three times in two days. **Write them down in
one place**, because the pattern is worth more than any single correction:

- the price sample was all within two minutes of a goal, and the headline said
  otherwise;
- "no European league in the price sample" was false — three separate defects
  were hiding it;
- the ten-year comeback rate was compared against a 69-day price sample.

**For each: what would have caught it earlier?** That list is the deliverable,
not the apology.

# 2. THE ONE THING THAT SHOULD OUTLIVE THIS FOLDER

> **The market does not quote near-certainties.**

7.1 comebacks per 100 where you could bet, 0.0 where you could not. **Get it
into `GUARDS.md` and `LEDGER.md` with the numbers on it.** Message 005 says the
same; it is repeated because it is the single most reusable thing produced here.

# 3. OTHER SPORTS — HIS IDEA, AND IT IS A GOOD ONE

He asked whether this transfers. **Answer it properly rather than guessing**,
because the answer probably differs by sport and that is the interesting part:

- **Tennis** has no draw, so there is no double-chance bet at all. Does the
  near-certainty gap still appear — does Kalshi stop quoting a player at 95
  cents up two sets?
- **Baseball** has no clock. A team three runs down in the 8th is a different
  shape from a team a goal down in the 80th minute. **Does the quote survive
  further into a near-certain state because there is no clock forcing it?**
- **Basketball, if Kalshi runs it.**

**You do not have to test these.** Write the question down for each, say what
data would answer it, and hand it over. `tennis` and `mlb` own those folders.

**And be clear about what would make this NOT transfer:** if the gap is caused
by market makers pulling quotes when the outcome is near-certain, it should
appear anywhere with in-play quoting. If it is caused by something specific to
soccer's three-way market, it will not. **Say which you believe and why.**

# 4. THE LIVE DESCENDANT

The reverse trade — backing a side to come back, a cheap contract with the loss
capped — is the one thing here nobody killed. Your sample could not answer it.
**Write what would answer it**, in one paragraph, and leave it where the next
chat will find it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. **Both.** A
post-mortem is exactly the document where a chat is tempted to be kind to
itself, so the Critic is not optional here.

**No statistics words.** Money, or out of 100. He has not read your folder and
will not.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

