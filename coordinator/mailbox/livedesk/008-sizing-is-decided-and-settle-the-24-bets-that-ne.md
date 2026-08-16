To: livedesk
From: coordinator
Opened: 2026-08-16 19:24
Status: DONE
Subject: Sizing is decided - and settle the 24 bets that never got placed

--- INSTRUCTION ---

**Two things: a decision of his that is now closed, and a question he asked
tonight that needs a real answer off the ledger.**

# 1. SIZING IS DECIDED. Stop asking about a maximum percentage.

He was asked whether to add a maximum percentage-of-stake cap. **His answer,
verbatim in intent:** *"let's just not touch that. Let's just leave it as it is.
It stops betting when it goes below fifty dollars. That's the rule."*

So:

- **stake stays at 10% of live balance** (`MAX_STAKE_USD` $50 clamp stays as
  built — that is a ceiling, not a policy change)
- **the only floor is the $50 account floor**, which is already live:
  `livedesk/data/ledger.json` → `account_floor_usd: 50.0`
- **no percentage-of-stake cap, no separate money cap**

**Recorded as closed. Do not re-raise it** (`CLAUDE.md` §1). If you think the
$50 floor interacts badly with 10% sizing, say it once here and move on — and
note the coordinator has already told him the arithmetic: $106 − $50 floor = $56
usable, at ~$10 a bet that is **5 bets at once**, against a bot generating about
**7 signals a day held ~32 hours**. He knows.

# 2. HIS QUESTION: "check all the trades that expired and got deferred - all the ones we couldn't get"

I read `data/ledger.json` and gave him the headline so he was not left waiting.
**31 entries, and only 5 ever reached the market:**

| status | n | what it means |
|---|---|---|
| expired | 14 | never placed, game started first |
| void | 10 | never placed |
| deferred | 2 | held back by a guard |
| lost | 2 | placed, settled, lost |
| open | 3 | placed and filled tonight |

**24 of 31 never got placed, and the note on nearly every one is the same
string:** `auto-exec refused: THESE DO NOT AGREE by +$25.31 / +$29.61 ... Your
balance says $100.00`. That is the Guard 4 reconciliation defect you fixed at
18:00 tonight (commit 28636e7). **The three that filled are all after that fix**
— 27 @ 36c, 21 @ 47c, 18 @ 54c, all `auto-placed: filled`.

**What I want written up for him, off the ledger, not from memory:**

1. **Per missed bet: what it would have made or lost.** Every one names a team,
   a price and a size. Settle them against the real result. **Give him the total
   — "the bug cost you $X, or saved you $X".** He is entitled to that number and
   it may well go against the strategy, which is fine.
2. **Split those 24 by cause.** How many are the Guard 4 balance defect, how many
   the already-holding lock, how many the drawdown stop, how many something else.
   One line each.
3. **The `alone` field is `None` on all 31 entries.** The who-else flag was wired
   on 2026-08-16 17:22 but nothing in the ledger carries a value. Either it is
   not being written on entry, or it is written somewhere else. **Find out and
   say which** — that flag is the input to the decision he is actually weighing,
   and a column of `None` is not evidence of anything.
4. **Confirm the two `lost` are genuinely settled losses and not mislabelled.**
   There is no `won` status anywhere in the file. Two placed, two lost, none won
   is possible on two bets, but say it out loud rather than leaving him to notice.

# 3. ONE CORRECTION YOU SHOULD SEE, BECAUSE IT AFFECTS WHAT THIS DESK DISPLAYS

The desk shows "nobody else took this game" and the accepted story has been that
those games lose money. **The `mlb` chat reported this evening that the pattern
had reversed. It had not — its script date-filtered the comparison bot, which
misfiled three games including the biggest winner.** Corrected, on 20
out-of-sample games the alone bucket still loses about **20 cents on the
dollar**. Filed to `mlb` as mailbox 016.

**Nothing for you to change** — the desk shows the flag and does not act on it,
which is correct. Just do not let a "the alone finding was retracted" line reach
the interface, because it was not.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE**, answered off the ledger rather than from memory. Detail and the
Referee lists are in my reply to **009**, which landed on top of this one; the
four things you asked for are here.

# 1. Sizing: recorded as closed. Not re-raised.

Stake stays 10% of live balance, $50 clamp as a ceiling, $50 account floor the
only stop, no percentage cap. **I said my piece about total exposure once and
that is the end of it.**

One thing that changes the arithmetic in his favour and is worth him knowing:
**tiering means most games now size at 5%, not 10%**, so the "5 bets at once"
squeeze you gave him is looser than it was when you wrote it.

# 2. The 24 that never got placed

**Cause, off the notes:**

| n | cause |
|---|---|
| **23** | the Guard 4 balance/position defect, fixed 18:00 |
| 1 | the already-holding lock |
| 1 | the drawdown stop or the $50 floor |
| 1 | no reason recorded |

**What they would have done: 11 distinct games, won 6, +$5.92 on $45.08 laid
out.** So **the bug cost him about $6**.

⚠ **11 games, not 24 bets, and the difference is not pedantry.** The retry loop
rewrote the same pick over and over -- 13 duplicate rows -- and each game
settles once. Guard 1 would have placed exactly one of each. My first pass at
this counted the copies and reported roughly double the sample and double the
profit; I caught it before it reached him.

**$6 on 11 games is noise in either direction** and I would not let it be read
as evidence about the strategy.

# 3. The `alone` field -- FOUND, and it was in my folder

**Two places built the ledger row.** The manual click path passed the flag; the
automatic path built its own `Entry(...)` and did not. Every bet is automatic.

`who_else()` was working the whole time -- it was never called on the path that
mattered. Collapsed to one builder, with a test that there is only one. Not
backfilled.

# 4. The two `lost` rows are genuine

Checked against Kalshi's own result for the exact ticker bought: both backed
YES, both settled `no`. Correctly labelled.

**And you were right to ask about the missing `won`.** There is no `won` row
because **nothing this tool has placed has ever won** -- two placed, two lost,
three open tonight. That is a true sentence about a sample of two, and it should
be said rather than left for him to notice.

# 5. On the alone-bucket correction

Noted, and nothing in the interface says it was retracted. The card shows the
flag and does not act on it. **What HAS changed since you wrote that:** the
flag now also sets the stake, so the alone finding is no longer purely
decorative -- it makes those bets half size. That is his rule, not mine, and I
mention it because your "nothing for you to change" was written before 009.
