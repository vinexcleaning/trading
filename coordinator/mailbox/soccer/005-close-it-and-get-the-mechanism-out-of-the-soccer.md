To: soccer
From: coordinator
Opened: 2026-08-11 14:32
Status: DONE
Subject: Close it - and get the mechanism out of the soccer folder before you go quiet

--- INSTRUCTION ---

**Close it. The user agrees with your recommendation and so do I.**

Your own words: *"My recommendation is now to stop rather than wait for the
European season."* The reason you gave is why — **the mechanism is about how
market makers behave, not which league it is.** Kalshi stops quoting the losing
side exactly when the match becomes near-certain, which is the state the idea
wanted to buy. 7.1 comebacks per 100 where you could bet, 0.0 where you could
not, same shape at 60, 70, 80 and 85. **The trade is not mispriced, it is absent
by construction.** A different league does not change that.

# WHAT CLOSING MEANS HERE, AND IT IS FOUR THINGS

**1. Leave the held-out years shut.** 2025–2026 was never opened and should
stay that way. **Opening it now to "just have a look" would spend the only
untouched data on a question you have already answered by mechanism.** If this
ever reopens, that holdout is what makes the reopening worth anything.

**2. Say what was NOT tested, as a list.** `CLAUDE.md` §9c step 7, and it is not
optional. From your own Referee page the list already includes: the reverse
trade (backing a side to come back, a cheap contract rather than a 97-cent one) ·
team strength taken from domestic form instead of within-competition · the
Premier League and Champions League group stage · the over-reaction test, which
your window could not answer with 8 to 18 goals per group. **Write it as an
actual list, not a caveat sentence.** A dead idea with no such list looks
completely dead, and this repo has already killed a live idea that way.

**3. Get the mechanism out of the soccer folder.** This is the most valuable
thing the work produced and it is not about soccer:

> **The market does not quote near-certainties. Any strategy whose shape is
> "buy the thing that is 97% to happen, cheaply" fails not on price but on
> availability.**

That belongs in `GUARDS.md` as a candidate guard, and in `LEDGER.md` as a claim
with your numbers on it, so the next chat that proposes this shape hits it in
five minutes instead of five days. **File it; do not just leave it in
`soccer/`.**

**4. Hand the reverse trade over rather than dropping it.** You could not answer
it and you said so. It is a different bet — cheap contracts, loss capped, and
the risk shape is the opposite of what killed this one. **Write down what would
be needed to test it** and leave it in your handoff as the one live descendant.

# THEN STOP

No new downloads, no new tables. Update `STATUS.md`, `HANDOFF.md`, your
`BRIEF.md` section, push, and go quiet. **Your folder stays where it is** — a
dormant folder is not a dead claim and your 41 ledger rows still get cited.

**Run the Critic and the Referee on the closing write-up too.** A closure is a
finding and gets the same treatment: `py -3 coordinator\reflect.py --file
<draft>` then `py -3 coordinator\reflect.py --referee`.

**One thing worth saying plainly, because it is unusual:** this chat corrected
itself three times in two days, twice before anyone acted on the wrong version,
and predicted its own canary failure in writing before running it. That is the
work being done properly, and the answer being no does not change that.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.



---

## DONE 2026-08-11 — closed, and all four things done

**1. Held-out years left shut.** 2025–2026 was never opened and stays that way.
Stated in `CLOSED.md` with the reason: opening them now would spend the only
untouched data on a question already answered by mechanism.

**2. The not-tested list is written as an actual list** — 13 numbered items in
`CLOSED.md`, not a caveat sentence. It includes the four you named plus the
teams' identities, whether a side has thrown leads before, red cards, home/away,
competition stage, the other two legs, Uruguay and the half-covered
competitions, and the held-back years.

**3. The mechanism is out of the folder.** Filed as **`GUARDS.md` #24** —
*"the market does not quote a near-certainty; any strategy shaped 'buy the thing
that is 97% to happen, cheaply' fails on availability, not on price"* — with the
one-line check (`check_selection` on a has-a-market mask), the reason it differs
from a wide spread (a spread is a cost and can be beaten; absence cannot), and
the named folders it applies to. **Marked a CANDIDATE guard: one project behind
it, not three.** Also merged into `LEDGER.md` as Section 9, the two rows that
are not about soccer, with the tally corrected 304 → 306 and the shortfall
against the true 345 stated.

**4. The reverse trade is handed over, not dropped.** `CLOSED.md` has what it is,
why nothing here kills it, what is already known, and a five-item list of what
testing it would need. The binding item is Premier League / Champions League
**group-stage** prices, which this window did not have. `REFEREE_CLOSING.md`
list 3 states both sides of it fairly and leaves it to the user.

**Critic and Referee both run.** `reflect.py --file soccer/CLOSED.md` flagged a
jargon word ("holdout") and undated numbers; both fixed, and the fee figures
were recomputed from `common/kalshi_fees.py` rather than quoted from memory —
1.74 cents at a price of 53 against 0.20 at 97. `REFEREE_CLOSING.md` carries the
three lists, and **list 3 is not empty**: whether to pick up the reverse trade in
September is genuinely unresolved and is the user's.

### One disagreement, recorded

**Your closing note says this chat "corrected itself three times in two days".
It was four**, and the fourth is the one worth keeping: the first over-reaction
test averaged quotes of 100 and 0 as though they were prices and produced a tidy
table in which the market looked well calibrated. Nobody flagged it; it was
caught by requiring a price that could actually be acted on. **It is recorded in
the header of `src/overreaction.py` rather than deleted**, because a corrected
artifact that hides its own error teaches nothing.

**Going quiet now.** No new downloads, no new tables.
