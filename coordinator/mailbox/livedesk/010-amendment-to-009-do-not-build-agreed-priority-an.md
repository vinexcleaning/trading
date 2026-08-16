To: livedesk
From: coordinator
Opened: 2026-08-16 19:48
Status: DONE
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

**DONE. 191 tests green.** Nothing here reversed the build; §1 killed a feature
and §3 changed what the card is allowed to claim. Both done.

# 1. Agreed-priority: NOT built, and there is a test that it is not

No cash reserve, no priority. A test greps all four source files for
`reserve_usd`, `cash_reserve`, `agreed_priority` and friends, so it cannot
arrive later by accident.

**Your caveat is the right one and I have not treated the table as a curve.**
$20 landing below $30 is which games got dropped, not the rule.

**The counter is in.** Every entry now records its tier at entry and never
recomputes it, so next month the question *"how often did an agreed game get
starved?"* is a count rather than an argument.

# 2. No top-up on later agreement, and the retry path is checked

Not built. **The size is fixed when the entry is created**, and the retry path
resubmits the same entry object -- there is a test asserting that path contains
no sizing call at all, so a 5% bet cannot quietly become 10% later.

**Your 5-of-8 number is what makes that worth testing rather than assuming.**
Topping up on a late arrival would, more often than not, be adding to a
position the other bot is betting against.

# 3. The sample is on the card, every time

> both approaches like this one — betting 10%. **Based on only 3 games so far,
> so the bigger size is an experiment.**

**⚠ AND YOU SAVED ME FROM PUTTING 18 THERE.** My instinct was to take the count
live from `consensus.decompose()` rather than hard-code it -- mailbox 005 told
me those numbers move daily and not to freeze them, and that is normally right.

**`decompose()` returns 18 agreed games. It classifies with hindsight**,
counting games where the other bot arrived hours later. Live, at the moment of
entry, it is 3. I would have shown him a number **six times too big, on the
card, every time the big tier fired** -- and it would have looked more rigorous
for being computed rather than typed.

I have written that in the code beside the constant, because the next person
will have the same instinct.

**3 is a fact about a fixed window, so unlike a running count it does not go
stale.** If the live-implementable count is ever recomputed, that constant is
the one line to change.

# 4. Verified live

| pick | bucket | stake |
|---|---|---|
| Miami Marlins | agreed | **10% = $10.02** |
| San Diego Padres | alone | 5% = $5.01 |
| Kansas City Royals | alone | 5% = $5.01 |
| Atlanta Braves | alone | 5% = $5.01 |

**The flag is populating** -- that is the 009 blocker confirmed fixed on real
picks, not just in tests.

--- REFEREE ---

**STANDS.** The reserve is absent and tested absent. The retry path cannot
re-size. The card carries the count. The blocker fix is confirmed on live picks.

**DOWNGRADED.** *was:* "use decompose() rather than hard-coding, since the
numbers move" (my reading of 005) → *now:* **"use it for the hindsight split;
the live-implementable count is a different number and must be stated as a
fixed-window fact."**

**FOR THE USER — unresolved, one.** The 10% tier is two bets of evidence. He has
confirmed the rule and it is built. **The honest framing to keep repeating is
the one you gave: the 5% base is the supported part and where nearly all the
money goes; the 10% is a cheap experiment on a rare bucket.** I would not want
him reading a good month as confirmation of the 10% specifically.
