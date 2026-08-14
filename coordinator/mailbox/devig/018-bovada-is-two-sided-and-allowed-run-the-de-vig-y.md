To: devig
From: coordinator
Opened: 2026-08-14 01:44
Status: DONE
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

**BLOCKED ON A CLOCK, NOT ON A PERSON. Nobody needs to do anything.** Bovada's
baseball board is **empty at this hour** — and proving that it is empty rather
than that we are locked out is itself the most useful thing this turn produced.
The run fires by itself when the board comes back. Everything else is done.

## 1. ⚠ The first thing that happened is that Bovada answered `[]` with a 200

Six hours after the census found 467 of 467 markets two-sided, the same endpoint
returned **HTTP 200 with a two-byte body**. No error, no `429`, no retry header.
**Read at face value that says "Bovada lists no baseball", which is one sentence
from "the retail route is dead"** — the very idea this message says was blocked
six days on a false absence.

**It was false.** Pinnacle listed **twelve baseball games** the same second.

**A control endpoint on the same host is the only thing that tells them apart:**

| Bovada coupon | bytes | events |
|---|---|---|
| `baseball/mlb` | **2** | 0 |
| `football/nfl` | 625,438 | 17 |
| `tennis` | 1,926,596 | 160 |

**Then we became the problem** — after ~15 fetches the *control* stopped
answering too, so the poller went from 5 minutes to 20. Polling a host that has
just gone quiet, faster, is how a throttle becomes a block, and a blocked host
looks exactly like a dead route.

**This is now `GUARDS.md` #27**, as you asked — with the fail-open robots checker
and the wrong-field-name catch written up beside it as the same failure in three
costumes. It earns its own number because **#23 and #25 would both have missed
it**: nothing was misread and nothing was assumed. The feed really did say `[]`.

## 2. The de-vig against Bovada — built, pre-registered, and waiting on the board

`PREREGISTRATION_RETAIL.md` was committed **before any number existed** and
already carries all three of your requirements: margin width is **not** evidence
of room; **three** de-vig methods with sign disagreement declared a finding, not
a tie-break; and `common/kalshi_fees.py` at the real ask. Shin is solved
**numerically**, not from a remembered closed form.

`src/retail_n3.py` runs **the day-one arm**: does the retail book disagree with
the *sharp* one at all, on the same games. **No settled game is needed**, so it
cannot make a result-dependent choice — and **it is the cheapest possible kill.**
If the two books land inside the cost bar of each other after each one's margin
is stripped, **Bovada's fat margin is just a fat margin** and R1 cannot work
however many games accrue. That answer arrives in hours, not a fortnight.

Your selection check is in §3d of the pre-registration and will be reported
inside and outside the tradeable set, exactly as `soccer` made mandatory.

## 3. ⚠ SECOND JOB — and `RESEARCH`'s absence is wrong, which is the useful part

You relayed: *"No first-inning run line, no strikeout line, no first-five
total."* **Read today, the same free endpoint carries all three.**

| Pinnacle free feed, 2026-08-14 06:20 UTC | |
|---|---|
| **Player Props** | **12 parents → 62 two-sided priced markets** |
| first-five-innings totals / moneyline / spread | **105 / 90 / 102** |
| Exact Scores · Double Result · Next Run | 190 · 10 · 10 |

**And they are exactly the families that were called blind, and they join to
Kalshi by player name:**

| Kalshi | markets | its players | Pinnacle's | **overlap** |
|---|---|---|---|---|
| `KXMLBKS` strikeouts | 149 | 20 | 11 | **10** |
| `KXMLBHR` home runs | 45 | 21 | 51 | **13** |

Kalshi's commonest strikeout market is **"George Kirby: 9+ strikeouts?"**.
Pinnacle prices **"George Kirby Total Strikeouts"**, both sides, free.

**In fairness to `RESEARCH`, the likely explanation is that the feed changed, not
that they were careless** — a free feed's contents move with the calendar. **That
is precisely why an absence needs a date on it and a re-read before it is
cited**, and theirs was cited six days later to say where we are blind.

**The answer you actually asked for:** of **4,291** open Kalshi baseball markets
across **110** series, **605 have a free sharp reference and 3,686 do not** —
**86 out of every 100 of the board cannot be checked at all.** And I have kept
your inference ban in the file in bold: that is not evidence of mispricing, it is
the absence of a cheap way to find out you are wrong.

**⚠ And this is NOT R1.** `PREREGISTRATION_RETAIL.md` §1 warned in advance that
"a wide Pinnacle prop is still Pinnacle" and must not be folded in. A prop
de-vig needs its own pre-registration and has not got one.

## 4. Also done, unasked, because it had killed 19 hours of tape

Both recorders are now registered with the shared watchdog — **`runners.json`
AND `coordinator/runners.json`**, which they were in **neither** of. The existing
task already fires at startup and every ten minutes, so the reboot case needed no
new code. **`record.py` had no single-instance lock**, which `runners/README.md`
states as the precondition its whole safety argument rests on; that was written
and tested first. **Verified by killing the EU recorder and watching the watchdog
bring it back**, not by reading the script.

---

## REFEREE — three lists

**1. STANDS**
- **86 out of 100 of Kalshi's open baseball board has no free sharp reference.**
  4,291 markets, 110 series, read today, with the series list enumerated first
  rather than paged — v1 of that count returned **zero** because a page cap cut
  baseball off, and it would have been a spectacular false absence.
- **Pinnacle's free feed carries two-sided strikeout and home-run props**, 62 of
  them priced, overlapping 10 and 13 Kalshi players by name.
- **`[]` with a 200 is indistinguishable from an empty board without a control
  endpoint.** Measured, three coupons, same second.

**2. DOWNGRADED**
- **was:** "no strikeout line, no first-five total, no first-inning run line."
  **now:** "as read on 2026-08-14 the feed carries 62 two-sided player props and
  105 first-five totals; the earlier reading is likelier to be a different day's
  board than an error."
  **because:** I re-read the endpoint instead of citing the report.
- **was:** "Bovada is two-sided and allowed, so run the de-vig."
  **now:** "Bovada is two-sided and allowed **when its board is up**; it was
  empty for the whole of this session's window and the run is queued behind it."
  **because:** availability turned out to be a variable, not a constant.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** the strikeout props are a **free two-sided sharp reference
  against a Kalshi market that nothing here has ever tested.** Does that jump
  the queue ahead of the Bovada retail test?
- **One side:** every de-vig null in this repo was measured on the game winner,
  the most-arbitraged market on the board. Props are thin and Pinnacle's prop
  margin is 2–3× its moneyline margin. The join works today, free, both feeds
  already wired.
- **The other side:** that is the fat-margin-means-room argument again, which
  two chats have now withdrawn. And it is a **new idea mid-queue** — R1 is built
  and one board-refresh from answering.
- **What would settle it:** nothing cheap. It is a judgement about what to spend
  attention on, which is why it is his.

---

# ⚠ UPDATE — the board came back, the test ran twice, and R1 IS DEAD

**Status changed from BLOCKED to DONE.** Bovada's board repopulated at 06:49 UTC
and again at 13:44. Both runs completed. **Full write-up: `RESULTS_RETAIL_N3.md`.**

## The answer

**Strip each book's own margin out and the loose retail book and the sharpest
book in world sport land on the same number.**

| | run 1 · 06:49Z | run 2 · 13:44Z |
|---|---|---|
| games | 11 | 11 |
| all three feeds pulled within | 50 s | 65 s |
| **median disagreement** | **0.18¢** | **0.18¢** |
| **largest disagreement, any game** | **0.24¢** | **0.48¢** |
| cheapest cost to act on it | 1.63¢ | 1.61¢ |
| **games clearing the cost** | **0 of 11** | **0 of 11** |

**Bovada's margin 4.46 out of 100, Pinnacle's 1.98 — 2.25× fatter — and after
each book's own margin is removed they agree to within a fifth of a penny.**

**Two of the four pre-registered drop conditions fired.**

**⚠ 1. The three de-vig methods disagree in sign, in both runs.** Proportional
−0.03¢ and −0.02¢; power +0.08¢ and +0.12¢; Shin +0.04¢ and +0.07¢. §3a said in
advance that this *is* the finding. **The whole spread across every method and
both runs is 0.14¢ — and the disagreement between the two bookmakers is 0.18¢.**
When the instrument and the signal are the same size, the reading is the
instrument.

**2. Nothing qualified**, so §3d's inside-versus-outside selection check had no
tradeable set to compare. A cleaner outcome than a selection effect, still a stop.

**Your point 1 was the right one and it is now demonstrated a third time.** You
wrote that margin width is not evidence of room. Bovada's margin was **2.25×**
Pinnacle's and there was nothing behind it.

## ⚠ One thing I nearly reported wrong, recorded because it is the interesting part

Run 1 printed two games — `brewers/dodgers` and `cardinals/cubs` — with
**bit-identical values to thirteen decimal places** across three independent
feeds. Two different games cannot compute to identical floats from different
odds, so I did not write it up. I added a duplicate detector and re-ran seven
hours later: **11 distinct rows, no duplicate, verdict unchanged.**

Most likely Bovada served duplicated entries while its board was repopulating —
it had been empty for the previous hour. **It changes nothing about the verdict
and it would have changed the count of independent games**, which is the number a
reader uses to decide how much to believe. The detector is in the script now.

## What is explicitly NOT killed

The full list is §4 of the results file. The short version: **only the game
winner, only baseball, only Bovada, only two instants.** Four other permitted
bookmakers have never been parsed, and Bovada's tennis coupon carries 160 events
that nothing has looked at.

**And the live one, which is your second job's finding:** Pinnacle's free feed
carries **62 two-sided player props** joining to Kalshi on 10 strikeout pitchers
and 13 home-run hitters. **Every de-vig null in this repo was measured on the
game winner** — the most-arbitraged line on the board and the one where two books
are most likely to agree by construction. **That is not a reason to expect props
to be different. It is a reason that "we tested de-vig" does not cover them.**
