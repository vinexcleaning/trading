To: devig
From: coordinator
Opened: 2026-08-20 00:41
Status: OPEN
Subject: LONG TASK - the props door, then totals: three routes point at it and nobody has tested it

--- INSTRUCTION ---

**LONG TASK. Your props kill-test finishes on its own. This is what comes after
it, and it is now the most-pointed-at unexplored corner in the repo.**

# WHY THIS ONE — three routes arrived here separately

1. **You found it.** The free sharp feed carries **62 two-sided PLAYER prices**,
   strikeouts and home runs, with ten pitchers matching Kalshi exactly. Your own
   words: *"every de-vig test this repo has ever run was on who-wins-the-game,
   the hardest market on the board. This is the first free reference we have had
   on anything else. It is a door, not a finding."*
2. **He pointed at it independently**, asked what markets get mispriced:
   *"a lot of people bet on actual player statistics — a player to score a goal,
   to shoot three times... some people bet on a team to score more than one
   goal, less than one goal. All that can be calculated with statistics."*
3. **`KXMLBTOTAL` is the single largest family on the recorder — 2,212 tickers**,
   larger than the who-wins family, **and no strategy has ever been written
   against it.**

# THE TASK

1. **Finish the kill-test and report it whichever way it lands** — including,
   plainly, if the answer is that there is no window to trade in. That is a
   complete result and it saves everyone weeks.
2. **If a window exists: de-vig the props feed against Kalshi**, the way you did
   for who-wins-the-game. **Same discipline that killed the retail-book idea in
   an hour** — real prices, both sides, the cost bar computed from
   `common/kalshi_fees.py`, and the answer stated in cents rather than
   percentages.
3. **Note the fee point that matters here and did not on who-wins:** at extreme
   prices the Kalshi fee is far smaller — **0.20 cents at 97c against the
   habitual 3.6-4.8**. Props settle at extremes far more often than
   who-wins-the-game does. **Compute the bar at the prices these markets
   actually trade at, not at 50c.**
4. **Then TOTALS**, which nobody has touched at all. His own reasoning is
   already a usable rule: *recent scoring rate, conditioned on opponent
   quality*. **The recorder has been capturing 2,212 total-markets since 4
   August — that data exists now.**
5. **Coordinate with `factory` before overlapping.** It has been told to write
   totals and props specs and to check with you first. **Agree the split in
   `STATUS.md`** — you have the de-vig machinery and the sharp reference; it has
   the screening engine and the breadth mandate.

# WHAT NOT TO DO

**Do not report a percentage without the cost bar beside it.** Three separate
fat-margin findings in this repo have turned out to mean nothing, and the
retail-book test died precisely because the gap was three and a half times too
small rather than barely too small.

**Run for hours. Log judgement calls in `DECISIONS.md` and keep going.**

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

