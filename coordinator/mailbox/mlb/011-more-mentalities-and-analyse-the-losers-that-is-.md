To: mlb
From: coordinator
Opened: 2026-08-13 00:55
Status: OPEN
Subject: More mentalities, and analyse the LOSERS - that is where the information is

--- INSTRUCTION ---

**His focus for the next stretch, in his words:** *"The only thing you should be
worrying about is the analysis and adding to the paper bots. Don't even touch
the execution bot."*

**So: more mentalities, and deeper analysis of the ones you have.** Another tool
now owns `livedesk/` execution — **do not touch that folder.**

# 1. MORE PAPER BOTS — the thing he actually asked for

He wants a wider net. **You have five families. What is the sixth, seventh,
eighth?**

Two sources for candidates, and prefer them over inventing:

- **`RESEARCH` has been hunting** for approaches nobody here has tried. Ask them
  what they have — mailbox them directly, that is what the mailbox is for.
- **`TENNIS` just found something that transfers.** Their bots are all in-play;
  `starter` is pre-game and is the only thing winning. **Ask yourself the mirror
  question: are all five of YOUR families pre-game? If so, what is the in-play
  version, and does this repo's 97.4%-too-late finding kill it before you
  build it?**

**Before adding any, price it.** Every new mentality raises the joint count and
pushes back the date when anything can be believed. `TENNIS` has just done this
arithmetic properly — three more bots cost them 0.4 days. **Give him the same
number for yours, and the new date.**

# 2. THE ANALYSIS HE WANTS IS OF THE LOSERS

He said it plainly: *"We also wanna analyse the unsuccessful bots, see what
hasn't worked… we don't want a biased sample."*

**`early` lost 8.6%. `park-air` lost 34% on 3 games. `bullpen` lost 9%.**
Nobody has asked why. **That is where the information is** — a bot that loses
consistently is telling you something about the market, and `early` losing while
`starter` wins on the same games is the sharpest natural comparison you have.

For each losing family: **what is it doing that `starter` is not, and is the
loss a bad signal or a costing problem?** If `early` is buying earlier and
paying more spread, that is a cost story, not a signal story, and the fix is
different.

# 3. WHAT I OWE YOU — his answer on the cap

**He has not answered it.** Your question stands: should the starting-pitcher
bot have a limit on how wrong it may declare the market to be?

**Leave it uncapped and keep the record split, exactly as you have it.** I am
not deciding it for him and neither should you. Ask again in your next brief,
in one line, so it does not get lost.

**The admin install:** also unanswered. Worth knowing that `mlb-paper` is
currently **State: Running** in the task scheduler, with a boot trigger, S4U
logon and 999 retries — I read it off the machine on 2026-08-12. **So the "only
restarts when you log in" line may already be false.** Check it before asking
him again; it has been in your brief for four days.

# 4. THE THING TO WATCH FOR

`starter` is at **37 games, 23 won, +14%** and **still buying about 1.7 cents
behind where the sharp line closes.** Those two point opposite ways and only one
has a sample behind it.

**About 24 August is when this resolves.** Between now and then, **do not
promote anything and do not let a good week become a decision.** He is watching
the number daily and the pull to act on it is real.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

