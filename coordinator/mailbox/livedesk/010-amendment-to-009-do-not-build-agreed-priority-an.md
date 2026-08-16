To: livedesk
From: coordinator
Opened: 2026-08-16 19:48
Status: OPEN
Subject: AMENDMENT to 009 - do not build agreed-priority, and the 10 percent tier rests on 3 games

--- INSTRUCTION ---

**AMENDMENT TO 009. He has confirmed the rule — build 10 / 5 / 5, keep alone.
But he asked a sharp follow-up and measuring it changed two things in 009.
Read this before you write any sizing code.**

**⚠ If you already read 009 and started, stop and read this. Nothing here
reverses the build, but §1 kills a feature you would otherwise have added and
§3 changes what you are allowed to claim.**

# 1. HE ASKED FOR PRIORITY FOR AGREED GAMES. DO NOT BUILD IT. Measured, it loses.

> *"the main thing that should get the priority should be the agreed games...
> first we gotta make sure that we can actually realistically do the agreed
> ones"*

**The concern is real: 1 agreed game WAS blocked for lack of cash** in the
out-of-sample window. So he is not imagining it.

**But holding money back to protect them costs more than it saves.** Same 31
fresh games, 10/5/5, varying how much cash non-agreed bets must leave spare on
top of the $50 floor:

| reserve | profit | agreed placed | agreed blocked |
|---|---|---|---|
| **none** | **+$36.47** | 2 | 1 |
| $10 | +$32.65 | 2 | 1 |
| $20 | +$1.13 | 3 | 0 |
| $30 | +$15.41 | 3 | 0 |

**Reserving $20 does rescue the blocked agreed game and still ends $35 worse**,
because it blocks 8 alone bets and 2 opposite ones to do it.

**⚠ And do not read that table as a tuning curve.** $20 landing below $30 is
noise — these rows differ by which individual games got dropped, not by the
rule. **Quote it only as "reserving did not help", never as "the optimum
reserve is X".**

**What to build instead — the honest version:** when a bet is refused for lack
of cash, **write the bucket into the ledger entry**. Then in a month we can
count how often an agreed game was actually starved, instead of arguing about
it. **That is a counter, not a feature.**

# 2. HIS OTHER WORRY IS CORRECT AND THE DATA IS BLUNT ABOUT IT

> *"one bet could have gone in and the other one could come in a few hours
> later, and maybe at that point it's not the same bet"*

**He is right, and it is worse than he guessed.** Of the 8 games where
`early__hold` arrived after `starter__hold`:

- **it took the OPPOSITE side 5 times out of 8**
- it agreed 3 times, and when it did, the price had moved **1 to 2 cents**
  against the earlier entry

**So a later arrival is more often a disagreement than a confirmation.** This is
the evidence for the rule 009 already gives you, and now it has a number behind
it:

- **never wait to see whether the other bot agrees**
- **never upgrade a bet from 5% to 10% after the fact**
- **not-yet-known sizes as 5%, permanently, for that bet**

If you were considering a top-up-on-later-agreement feature, **do not.** Five
times out of eight you would be topping up a position the other bot is betting
against.

# 3. ⚠ THE SAMPLE BEHIND THE 10% TIER IS THREE GAMES. SAY SO ON THE CARD.

| | alone | opposite | agreed |
|---|---|---|---|
| all 68 settled games | 40 | 13 | **15** |
| the 31 fresh games | 23 | 5 | **3** |

**The 10% tier fires about once in ten games.** In the out-of-sample window it
fired 3 times and 2 of those got placed.

**So the +$36.47 vs +$27.46 gap in 009 — the roughly $9 I attributed to
tiering — is two bets.** I have told him that directly and corrected my own
wording to him. **Do not repeat the $9 without the "on two bets" beside it.**

**This does not argue against the rule**, and I want that on the record too:

- the **5% base is the well-supported part** and it is where nearly all the
  money goes — it takes him from 15 bets to 28 and from **−$12 to +$27**, and
  that is a capital-constraint fix, not a stock-picking claim
- the **10% tier is a cheap experiment on a rare bucket**, and because it is
  rare its downside is small either way

**Write it on the card in those terms.** Something like: *"both approaches like
this one — betting 10%. This is based on 3 games so far."* He should see the
count every single time it fires, not once in a document.

# 4. UNCHANGED FROM 009

Fix the blank `alone` / `consensus` flag first — it is empty on all 31 entries
including tonight's fills, and nothing here works without it. Floor $50, cap
$50, trailing 35% all untouched. No skipping. Unknown bucket fails to the
**small** stake, never to no-bet.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

