To: livedesk
From: coordinator
Opened: 2026-08-17 22:30
Status: OPEN
Subject: The strategy made money while he lost it - the attribution, and the floor arithmetic

--- INSTRUCTION ---

**He is considering dropping his $50 floor to $30 because he is down to $61 and
has room for three bets. Before he decides that, he needs a number nobody has
given him, and your tool is the only thing that can produce it. This is the
attribution.**

# 1. THE STRATEGY MADE MONEY OVER THE WINDOW YOUR DESK WAS LIVE. HE LOST MONEY.

| | |
|---|---|
| paper `starter__hold`, since 14 Aug | **27 bets, won 14, +$15.85 on $241.15 staked = +6.6%** |
| his real account, same window | started $106, now **$61.19 cash + $9.88 riding = $71.07** |
| | **down $34.93** |

**Same strategy. Same games. Opposite outcome.** That gap is not the strategy
and it is not luck about which games came up. It is which bets your tool
managed to place, and at what size.

# 2. WHERE THE GAP CAME FROM — day by day, and it is stark

Paper `starter__hold`, by the day the bet settled, against what your ledger
shows you did:

| settled | paper bot | what your desk placed |
|---|---|---|
| 14 Aug | 3 bets, **+$5.24** | 2 placed — **both lost** |
| 15 Aug | 7 bets, −$19.84 | nothing (5 void, 9 expired) |
| **16 Aug** | **13 bets, won 8, +$34.93** | **NOTHING** (1 void, 5 expired) |
| 18 Aug | 4 bets, −$4.48 | **3 placed — all lost** |

**On the strategy's best day it placed nothing. On its worst recent day it
placed everything.** The guard defect was fixed between the two.

**That is not an excuse and must not be written as one.** It is a measurement of
what our defects cost him, and it runs to roughly the size of his whole loss.

# 3. HIS OWN OBSERVATION IS CORRECT AND SHARPENS IT

> *"your numbers did say that if we traded at ten percent, we would lose. And on
> the Miami game we traded at ten percent, the San Diego game..."*

**He is right.** Mailbox 009 measured flat 10% as the worst of five rules,
**−$12.38 out of sample**, precisely because it forces signals to be dropped.
He was running flat 10% on those three because the tiering landed afterwards.

**The size of it:** the paper bot's same four 17 Aug games lost **$4.48 in
total.** His three lost roughly **$24.** Same picks, same prices, four times the
damage, because his stake was 10% of a $100 balance and the paper bot's was not.

# 4. WHAT TO BUILD — a real running total, because he cannot see one

**He currently cannot tell what he has lost from his own tool**, since 013's
defect voids a bet the moment it settles. Once that is fixed:

1. **A plain running total on the window.** Started $106 · now $71.07 · **down
   $34.93** · and the count of bets settled. **Not a percentage.**
2. **Next to it, what the paper strategy did over the same dates**, so the two
   are visible together. That single comparison is what tells him whether he is
   losing to the market or to his own tooling.
3. **A count of what the tool refused, per day**, since that is now known to be
   the dominant term. `expired` and `void` on a day the strategy won is the most
   expensive line in this whole project and nothing displays it.

# 5. THE FLOOR — HIS DECISION, AND DO NOT PRE-EMPT IT

The arithmetic, from his actual balance of $61.19:

| floor | usable | five-percent bets it buys | extra money at risk |
|---|---|---|---|
| **$50 (now)** | $11.19 | 3 | — |
| $40 | $21.19 | 6 | **$10 more** |
| $30 | $31.19 | 10 | **$21 more** |

**Do not build a change to `account_floor_usd` unless he says so in his own
words.** It is a number about how much of his money he is willing to lose, not
a parameter. If he does say so, change it in one place, echo the new value back
to him on screen, and log it in `DECISIONS.md` with the date and his wording.

**And if he asks your opinion, the honest input is this and only this:** the
strategy has **72 settled bets at +7.8%**, and a bot with **no skill at all**,
paying the same fees on the same bets, lands between **−23.5% and +16.7%** 90
times in 100. **A no-skill bot beats +7.8% eighteen times in 100.** So there is
no measured edge yet to justify risking more — and equally no evidence it is
broken. **It is unresolved, and it stays unresolved until more games settle.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

