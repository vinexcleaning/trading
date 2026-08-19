# PREREGISTRATION — SF018, the hold-on trade

**Written 2026-08-19, before any European soccer price for the 2026/27 season
exists on tape, and before any number has been computed for this idea in this
folder.**

`soccer/CLOSED.md` handed this over rather than dropping it and listed five
things it needed. This file is item 4 of that list: *"A fresh pre-registration,
on the years nobody has looked at, stating what result would drop it.
`PREREGISTRATION_COMEBACK.md` does **not** cover this — it is a different bet in
the opposite direction and reusing it would be dishonest."*

**Amendments are numbered and dated at the bottom. Nothing above that line is
edited once a result exists.**

---

## 0. ⚠ The selection effect that this idea arrives with, named first

**This idea reached the top of the queue because the user knows soccer.** That
is a real reason to record the data and it is **not** evidence about the trade.

> **Choosing a market because he knows it is exactly as much a selection effect
> as choosing a strategy because it backtested well.**

So the burden of proof does not drop. It is the same forward test, the same
no-skill range, the same 100 settled units, and the same drop rules as every
other spec in this folder. `coordinator` mailbox 003 says this in the same
breath as handing the idea over, and it is repeated here because this is the
file somebody will read in November.

**What his knowledge legitimately buys:** he can look at a firing and say *"that
is obviously wrong"* — a sanity check that exists for no other market this
project trades, and emphatically not for baseball, where he says he knows
"literally close to nothing".

---

## 1. The question

> **Is a strong side that goes one goal up early underpriced to hold on?**

**Not** the comeback trade. That one is closed: `GUARDS.md` #24, *the market does
not quote a near-certainty*, measured on **seven sports**. This is the opposite
side of the same match — buying the **uncertain** side, cheap, where quotes
demonstrably do exist (**93 in 100 at the 15th minute**).

## 2. What is already known, and does not need redoing

From `soccer`'s own work, his own hypothesis stated **before** any data existed
and then confirmed on **56,927 matches over 26 competitions**:

| a side one goal up between the 20th and 35th minute | wins |
|---|---|
| **top-third team** (1,562 matches) | **72.6 in 100** |
| **bottom-third team** (944 matches) | **59.6 in 100** |

**That half is solid and is not re-tested here.** The open question was never
the football. It was whether a tradeable price exists on the right side of it.

## 3. What number answers it

**Cents per contract, entered at the real recorded ask, exited at settlement,
net of the real entry fee from `common/kalshi_fees.py`** — placed beside the
range the same number would fall in with no skill at all.

⚠ **The fee is the thing that kills this if anything does, and it is nine times
larger here than in the trade this descends from.** Computed on 2026-08-11 from
the repo's only fee implementation: **1.74 cents at a price of 53, against 0.20
cents at 97.** A cheap contract pays far more fee and has less to win per trade.
**Any version of this that reports a gross number is void.**

## 4. Unit of observation

**One match.** Not one price, not one minute, not one contract. A match settles
once.

Where both a Champions League and a Premier League match are played by the same
club in the same week, they remain two matches — but **effective sample size is
reported**, because a club's form is not independent week to week.

## 5. Sample, and what will actually exist

- **Start date: the Champions League group stage, September 2026**, plus
  Premier League matches from now.
- **Both families were pinned to the full-depth recorder on 2026-08-19**
  (`KXUCLGAME`, `KXEPLGAME`), so the whole order-book ladder is stored, not a
  summary. That is item 2 of `CLOSED.md`'s list — *"a deeper book than this
  window had... the Premier League and Champions League group stage would fix
  that, and only those."*
- **Judged at 100 matches where the rule fired.** Not before.

**Honest arithmetic on whether that arrives:** the group stage plus a Premier
League season is roughly 500–600 matches by December. The rule fires only when a
side goes one goal up in the window **and** a price is quoted **and** the spread
is inside the bar. If that is a third of matches, 100 firings arrives around
December. **This is declared SLOW and will not have an answer in a month.**
Saying that now makes it a prediction rather than an excuse.

## 6. What result makes us drop it

Any one of these:

1. **Inside its no-skill range at 100 fired matches.** Reported as "not
   distinguishable from no skill", never as a small edge.
2. **Negative at 50 fired matches.** Half the sample, direction already wrong.
3. **Fewer than 10 firings in the first 30 days of the group stage** — the
   availability failure that killed the parent idea, arriving on this one.
4. **Capacity below $25 per firing** when priced by walking the recorded ladder.
5. **The top-third / bottom-third split does not separate at all** in the new
   seasons. The entire thesis is that team strength is the variable; if strong
   and weak sides hold on equally often at these prices, there is no mechanism
   left and the result is void rather than weak.

## 7. The naive benchmarks, reported beside it

1. **Buy the same side at the same moment regardless of team strength** — this
   is the one that matters, because it isolates whether *strength* is doing any
   work or whether the trade is just "buy a leading team".
2. Buy at random in the same matches, same fees, same count.
3. Do nothing — zero.

## 8. How many strategies were screened to produce this one

**Zero.** This was not selected by a backtest; it was handed over by another
chat as an untested descendant and pinned by the user's domain knowledge. That
is a different provenance from every other spec here and it is stated so the
number cannot go missing later.

**It is also not an advantage.** A strategy nobody screened has not passed
anything.

## 9. What is NOT tested by this

A list, not a caveat (`CLAUDE.md` §9c step 7):

- Any competition outside the Premier League and Champions League.
- Any minute window other than the 20th–35th.
- Two goals up, or one goal down.
- Whether the effect differs home versus away.
- Whether a side resting players before a European tie changes the league match
  before it — **this is one of the questions batched to him**, because he is the
  only person on this project who can answer it.
- Anything about in-play latency. **This is paper only and stays paper only**
  (`CLAUDE.md` §9b item 2): his own bot was reading scores after 97.4% of the
  price move had already happened, on 4,398 score-change events.

---

## AMENDMENTS

**A1 — 2026-08-19.** None yet. This line exists so the first amendment is
visibly an amendment.

---

**A2 — 2026-08-19. THE STRENGTH VARIABLE IS WRONG AND IS REPLACED. Made before
any 2026/27 European price exists and before any result of any kind.**

**What changes.** Section 2 and the entry rule identified a strong side as
**top-third of the domestic table**. That is replaced by **a per-club measure of
what that club actually does after going one goal up, learned from that club's
own season.**

**Why, and it is his own words** (`coordinator` mailbox 004, recorded in
`DOMAIN_SOCCER.md`):

> *"Real Madrid's the type of team that if they score the first goal, they're
> gonna keep trying to score. But Manchester United, it's very likely that if
> they score the first goal, they're gonna park the bus no matter who they're
> playing against."*
>
> *"A better team with better players will sometimes park the bus even playing
> against the worst team."*

**So table position does not predict the behaviour this trade is built on.** A
league-wide strength average would mix clubs that push on with clubs that sit
back, and the two do the opposite thing to the price of the side that is ahead.

**Why this is a correction and not a fitted parameter.** This is the repo's most
expensive recorded mistake, in a new sport: a sweep over *price and market
features* was used to close a question about *individual players*, and a live
idea died because the wrong variable was measured. **He has now said the same
thing about soccer, in advance, before any number exists here.** Changing it
after a null would have been fitting; changing it before any data is the whole
point of a pre-registration having amendments at all.

**What this costs, stated honestly.** The per-club history has to be built from
each club's own season, which means:

1. **The sample shrinks.** It is no longer "top-third clubs" but "this club,
   after going ahead" — perhaps 10 to 20 matches per club per season.
2. **A club with no history yet cannot be classified.** Newly promoted sides and
   the first weeks of a season have no per-club record, and those matches are
   **excluded and counted as excluded**, not defaulted to the league average.
3. **It introduces a fitting risk the table-position version did not have.**
   Learning a club's behaviour from the same season it is traded in is
   look-ahead. **So the per-club label is built from matches BEFORE the traded
   match only, never from the full season.**

**New drop rule, replacing item 5 of section 6.** The old rule was that the
top-third / bottom-third split failing to separate voids the result. It is now:

> **5. If clubs classified as "pushes on" and clubs classified as "sits back"
> hold on equally often at these prices, the mechanism is absent and the result
> is void rather than weak.** And separately: **if the per-club label cannot be
> built for at least 60 of the 100 fired matches, this is UNMEASURABLE and is
> reported as unmeasurable, not as negative.**

**What does NOT change.** Unit of observation (one match), 100 fired matches
before judgement, the no-skill range beside every number, the SLOW declaration,
the fee as the likeliest killer, and the selection effect named in section 0.
**The burden of proof is unchanged.**
