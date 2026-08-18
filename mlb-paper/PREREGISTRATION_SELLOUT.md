# Pre-registration — selling out when the other mentality disagrees

**Written 2026-08-17, BEFORE any real-tape result exists.** His idea, arriving
via mailbox 017. Registered under `CLAUDE.md` §10.

## One plain sentence about the other bot, because he has not met it

`early` bets **before the professional bookmakers have posted a price**, on the
pre-match brief alone. `starter` bets **after**, when a sharp line exists to
compare against. They are different bots and they see the game at different
times.

## The hypothesis

**When `starter` is holding a live position and `early` later takes the OPPOSITE
side, selling out immediately beats holding to settlement.**

His reasoning, in his words: *"would it make more sense for us to just sell the
bet and take the one dollar loss than to hold on and risk nine dollars on
something that's much riskier?"*

## Unit of observation

**One game.** Not one contract and not one fill. A game settles once. A
`starter` position of 25 contracts is one observation.

## Sample and dates

Every game where `starter` held a live position at the moment `early` entered
the same game. **On today's book that is 5 of 72 games — about 1 in 14.**

Prices come from the **12,059 rescued Kalshi markets** (2026-06-07 → 08-14,
110,466 minute-by-minute rows). Real bid, real ask, at the minute `early`
entered. Exit fee from `common/kalshi_fees.py` and nowhere else.

## Holdout split

**There is no honest holdout at n=5 and I am not going to pretend otherwise.**
The split is on the FOUR ARMS instead — arm 3 is a placebo that must fail, and
the shuffled-label control must find nothing. **This is registered as a
mechanical question, not a statistical one:** the thing being measured is
whether the price has actually moved by the time we know, which does not need a
large sample to answer.

## The four arms — all run, all reported

1. **never sell** — what happens now
2. **sell when the other side disagrees** — his idea
3. **sell when the other side AGREES** — the placebo. **If this also "works",
   the pipeline is finding noise and every number here is void**
4. **sell on either** — does the act of selling matter at all

Plus a **shuffled-label control**: same machinery, agree/disagree labels
randomly reassigned. **If it finds an edge in shuffled labels, all of the above
is void.** (`CLAUDE.md` §9c step 4.)

## What result makes us DROP the idea

**Registered before looking, and any ONE of these is fatal:**

- **The placebo arm (3) also beats holding.** Then selling is not responding to
  information, it is just selling, and the result is an artifact.
- **The shuffled-label control finds anything.** All numbers void.
- **Selling loses money against holding**, at real bid/ask with real fees.
- **The disagreement bucket keeps making money.** ⚠ **This one is already
  half-answered and it is registered here as prior work, not as a result of
  this test:** `starter` on games where `early` took the other side is
  **+24.3% on 18 games**. A rule that sells those is selling a bucket that
  currently makes money. **If that survives the tape, the idea is dead
  regardless of what the 5 firing games say.**

## What would make me DOUBT a positive result

The sell price is the whole thing. If it turns out the price had **not moved**
by the time `early` entered, then "sell and take the small loss" and "hold" are
being compared at nearly the same price, and any difference is the settlement
coin, not the rule.

## The trap 017 raised, tested separately and reported whatever it says

`early__hold` is **−12.4% on 65 bets**. It is a losing bot. Whether its opinion
carries information at all is a **more important question than the sell rule**,
because the 10%-on-agreed staking tier rests on it.
