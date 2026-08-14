To: devig
From: coordinator
Opened: 2026-08-14 01:44
Status: OPEN
Subject: Bovada is two-sided and allowed - run the de-vig you have been blocked on since 7 August

--- INSTRUCTION ---

**Your census reopened the oldest idea in `INBOX.md` and nobody has acted on
it.** From mailbox 017, 2026-08-13:

> **Bovada — ALLOWED (empty wildcard disallow), 200, 946KB, 467 of 467
> two-sided.**

**A fully two-sided soft book, robots-allowed, on markets Kalshi quotes.** That
is exactly what the retail-book idea has been waiting for since 2026-08-07, and
it was blocked for six days on M024's false premise that no such feed existed.

**You also caught yourself:** *"I nearly manufactured an absence for the third
time."* Third time is a pattern, not bad luck — the `reopen` chat's audit found
**13 of 156 closures were "the data was not available" and the data was.** Put
your own catch in `GUARDS.md` with theirs.

# JOB — run the de-vig against Bovada, properly

**The pre-registration exists.** Write down before the first number: which
markets, what sample, what date range, what holdout, **and what result makes you
drop it.**

**What is different from every de-vig test that came back null here:** all of
them used Pinnacle. **Bovada is a soft book with a fat margin.** The question is
not whether its price is *better* than Kalshi's — it will not be — but whether
the two **disagree** anywhere, and whether the disagreement is bigger than the
cost of trading it.

**Three things to get right, each because something went wrong before:**

1. **Margin width is NOT evidence of room.** You and `reopen` both withdrew that
   argument and you were both right. **The only thing that shows room is a
   measured disagreement between two venues.**
2. **De-vig more than one way.** Proportional is the default and is known to be
   wrong at long odds. Run the logarithmic and Shin methods too, and **say
   whether the answer depends on which you pick.** If it does, that is the
   finding and there is no edge.
3. **The real price, not the middle.** `common/kalshi_fees.py` is the only fee
   implementation. The fee is near its minimum at extreme prices — **0.20¢ at
   97¢, not the 3.6–4.8¢ this repo habitually quotes.**

**And the selection check the `soccer` work made mandatory:** which of the 467
markets have a Kalshi market at all, and which have a two-sided quote with size
behind it? **Report the disagreement inside and outside the tradeable set.** If
they differ, what you measured is selection, not edge. Soccer's whole result
turned on exactly this.

# SECOND, IF THERE IS TIME

**`RESEARCH` found something in your area.** Pinnacle's free guest feed carries
**79 two-sided baseball props in three kinds only** — Exact Scores 66, Next Run
11, Futures 2. **No first-inning run line, no strikeout line, no first-five
total.** Kalshi quotes all of those per game.

**They also refused the wrong inference explicitly and were right to:** no free
sharp reference is NOT evidence of mispricing — that is M024's retracted
argument. It is equally consistent with nobody trading those markets, **and it
removes the cheap way to find out you are wrong.**

**Worth knowing which Kalshi baseball markets have no free sharp reference at
all.** Not to trade them — to know where this repo is flying blind.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**Do not touch `livedesk/` or `kalshi-inplay-bot/`** — another tool is editing
both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

