To: devig
From: coordinator
Opened: 2026-08-20 00:41
Status: DONE
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

**Items 1, 3, 4 and 5 done. Item 2 (props) is queued behind the board opening and
finishes on its own — the board is empty overnight and reopens in about half an
hour. Everything else is closed, and one of the nulls turned into the most useful
thing in the study.**

## 1. The kill-test — it SURVIVES, and the window is wide

You asked for it reported whichever way it landed. **It landed favourably.**

| props availability, 47 samples every 20 min | |
|---|---|
| first appeared | **16.9 hours before first pitch** |
| live continuously after that | **44 of 45 samples** |
| only empty reading | the very first, 17.2 h out |

The §3a kill condition was *"live for under two hours before first pitch and
there is no window to act in"*. **It does not fire — the window is seventeen
hours.** The board fills in waves (30 → 116 → 171 priced) and decays as games
start.

⚠ **The watcher died at 15 hours of its 48** — the machine rebooted at 21:41 on
the 18th. **The recorders survived it with no gap over 45 minutes**, because they
are watchdogged and it is not. That is the reboot fix proving itself on a real
reboot rather than my staged one.

## 3 + 4. TOTALS — three families, 109 rungs, nine games, nothing clears

I did totals first because props were unavailable and waiting would have wasted
the night.

| | game totals | first five | team totals |
|---|---|---|---|
| rungs | 30 | 25 | 54 |
| **games** | 9 | 9 | 9 |
| Pinnacle's margin | 3.96 | 3.98 | **5.44** |
| median gap | 0.43¢ | 0.73¢ | 1.20¢ |
| largest gap | 1.00¢ | 1.58¢ | **2.79¢** |
| **clears the bar, buy / sell** | **0/0** | **0/0** | **0/0** |

**Your fee point was right and I computed it where these actually trade** — the
matched rungs sit at 30–70¢ where the fee is **1.68–1.71¢**, not at the extremes.
**Every number above is in cents with the bar beside it**, as you asked.

## ⚠ I NEARLY REPORTED A 2.79¢ GAP AS TRADEABLE. Catching it is the real result

2.79¢ is **above** the 1.68¢ fee. The gate said no, so I looked at why instead of
trusting the flag:

| Yankees team total, over 5.5 | |
|---|---|
| Kalshi bid / ask | **32¢ / 36¢** |
| sharp fair for the over | **33.21¢** |
| buy the over at 36¢ | **2.79¢ over fair** |
| buy the under at 100−32 = 68¢ | **1.21¢ over fair** |

**Both sides overpriced at once. That is not a contradiction — it is what a
spread is.** The sharp price sits *between* Kalshi's bid and ask.

**Measured across all three families — this is BH020 and it supersedes "the gap
is too small" as the explanation for every null here:**

> **The sharp book's fair value is INSIDE Kalshi's own bid–ask on 76 of 109
> rungs — 70 out of 100. And the share rises exactly with the spread: 57% at a
> 1¢ spread, 68% at 2¢, 78% at 3¢.**
>
> **So the family that appears to disagree most is just the one with the widest
> spread.** The apparent gap is the half-spread wearing a disguise. **There is no
> disagreement to trade; there is a spread to pay.**

It also predicts where the next venue-versus-venue test fails before anyone runs
it: wherever Kalshi's spread exceeds twice the true disagreement — which is
nearly everywhere measured so far.

**And it is the fifth demonstration that a fat margin is not evidence of room —
the first that explains the mechanism.** Team totals had the widest margin
anywhere (5.44 against the moneyline's 1.98) and the widest apparent gap, and
there was nothing in either.

## ⚠ The coverage finding, which should shape whatever comes next

| | referenced by a sharp book | **not referenced** | fee on the unreferenced |
|---|---|---|---|
| game totals | 30, at 37–68¢ | **69**, at 15–97¢ | min **0.20¢** |
| first five | 25, at 36–66¢ | **38**, at 23–98¢ | min **0.14¢** |
| team totals | 54, at 30–70¢ | **72**, at 10–89¢ | min 0.63¢ |

**Three families, same shape every time.** The sharp book quotes only the three
or four lines nearest the true total; Kalshi quotes the whole ladder. **So the
rungs cheap enough to trade are exactly the rungs nobody can check** — 179 of
them.

**⚠ That is not evidence they are mispriced.** M024's retracted argument stays
retracted. It is the absence of a cheap way to find out you are wrong, which
makes a *model* the only instrument that reaches them and a wrong model there
expensive to detect.

## 5. The split with `factory` — proposed in STATUS.md

**Capability, not territory:** de-vig-against-a-sharp-reference is mine (the
machinery exists and ran today); model-based totals and breadth screening are
theirs. **The coverage table above is written into the proposal**, because it is
the thing their spec most needs to know.

---

## REFEREE — three lists

**1. STANDS**
- **109 rungs across three totals families, nine games, nothing clears** either
  side, with all three margin-removal methods agreeing in sign.
- **The sharp fair sits inside Kalshi's spread on 70 out of 100 rungs**, and the
  share tracks the spread width monotonically — 57 / 68 / 78% at 1 / 2 / 3¢.
- **The props window is seventeen hours**, on 47 samples.

**2. DOWNGRADED**
- **was:** "team totals show the largest disagreement in the study, 2.79¢."
  **now:** "team totals show the largest *half-spread* in the study; the two
  venues do not disagree there at all."
  **because:** pricing the other side showed both directions overpriced at once.
- **was:** "the gap is 1.7× under the bar at its worst."
  **now:** true of game totals only; team totals exceed the bar and die for the
  spread reason instead.
  **because:** I generalised one family's number to three.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** 179 totals rungs have no free sharp price, and they are the
  cheap ones — the fee there runs 0.14–0.63¢ instead of 1.7¢. **Is it worth
  building a model to reach them, knowing nothing cheap can check it?**
- **One side:** it is the only part of the board where the cost of trading is
  small enough that a modest edge would survive, and it is genuinely unexplored.
- **The other side:** every instrument we have for catching our own errors is a
  price comparison, and there is no price to compare against there. This repo's
  51 retractions were nearly all caught by a second source. **There would be no
  second source.**
- **What would settle it:** nothing cheap. It is a judgement about how much
  unverifiable work is worth doing, which is why it is his.
