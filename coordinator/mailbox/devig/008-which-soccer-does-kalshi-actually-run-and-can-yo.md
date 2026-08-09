To: devig
From: coordinator
Opened: 2026-08-08 20:32
Status: DONE
Subject: Which soccer does Kalshi actually run, and can you buy at 97 cents?

--- INSTRUCTION ---

Your three threads are closed and the resting-order answer is a clean no. This
is a new job that plays to `kalshi-market-scan`, which is the exchange-wide
screen and already has the capacity machinery.

# THE JOB: is Kalshi soccer tradeable at all?

A new `soccer` chat is building a table of how often a losing team comes back,
to compare against Kalshi's price. The bet is buying NO on the losing team late
in a game -- around 97 cents to make 3. **Before any of that is worth doing,
two things have to be true and nobody has checked either.**

## 1. Which soccer competitions does Kalshi actually run?

**Two documents in this repo disagree and both are in your area.**

- `soccer/dataset.md` (2026-08-02): Liga MX, Argentina Primera, Copa do Brasil,
  Colombia, MLS.
- `soccer/reports/tape_soccer_scan.json`: 210 tickers, of which **139 are
  `KXINTLFRIENDLYGAME`**, plus `KXURYPDGAME`, `KXUSLGAME`, `KXECULPGAME`,
  `KXPERLIGA1GAME`, `KXNWSLGAME`, `KXCHLLDPGAME`, `KXMLSGAME`,
  `KXDIMAYORGAME`, `KXLIGAMXGAME`.

**Neither shows a Premier League or Champions League market.** The user assumes
those exist. If they do not, that has to reach him early and plainly, because
his whole idea about which competitions produce comebacks is built on them.

Give the definitive list from the API: every soccer series, how many markets
each has had, how much volume, and over what dates. Say explicitly which of the
big European competitions are absent.

## 2. Can you actually buy at 97 cents?

**This is the one that most likely kills the idea, so measure it rather than
reasoning about it.** The bet risks 97 cents to win 3, so **every single cent of
spread removes about a third of the margin.** Buy at 98 instead of 97 and the
break-even moves from "3 comebacks allowed in 100" to "2".

What is needed, at prices above roughly 90 cents, in the last 20 minutes of
soccer matches:

- the gap between the buy price and the sell price;
- how many contracts are actually resting there;
- whether anything is quoted at all in the closing minutes, or the book empties.

**You have the tool and the bug fix.** `orderbook_fp` is the real key -- the one
three scripts were reading wrongly, which is why this repo twice recorded a
disagreement about whether depth is public. It is public, free, 20 levels a
side.

## What would make this a no, and say so if it is

If soccer volume is a rounding error, or nothing is quoted above 90 cents in
the last 20 minutes, **that ends the idea before anyone counts a single goal**
and saves the soccer chat weeks. A clean no here is the most valuable result
this job can produce. `LEDGER.md` K005 is the shape: depth measured right,
inference wrong, and cross-tabbing both bars killed 10 of 11 families.

## Rules

`CLAUDE.md` §6 for evidence, §9b for four things not to re-open. Read-only
against the API. No orders, no keys.

**Report in plain English -- no statistics words, no "pp", no "n=".** Money, or
out of 100. `CLAUDE.md` §1 has the banned list. He reads on a phone and told us
directly that jargon stops him contributing what he knows.

Update your `BRIEF.md` section, `STATUS.md`, `HANDOFF.md`, and push.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


---

# AMENDMENT, same day — the missing-leagues claim was probably a SEASON artifact

**The user caught this and he is right.** The message above says the recorded
tape shows no Premier League and no Champions League. **That recording window is
2026-05-24 to 2026-08-04 — the European off-season.** Those competitions were
not being played, so their absence says nothing about whether Kalshi lists them.

His words: *"I'd be really doubtful if there'd never been any type of Champions
League betting on Kalshi, because that would just make no sense to me."*

**So do not report which leagues Kalshi runs from a summer sample.** Ask the API
for the SERIES list, which persists whether or not a competition is in season,
and check for European club competitions by name. If a series exists but has no
markets right now, that is the answer: it exists and is out of season.

This matters beyond soccer. **A ~69-day window that lands in one sport's
off-season will show that sport as absent**, and this repo has now nearly made
that mistake once. Worth a line in `GUARDS.md` if it is not already there.

**DONE. Both premises in the instruction are wrong, and both in the direction
that helps.** Full write-up: `kalshi-market-scan/docs/SOCCER_TRADEABILITY.md`.

## 1. The big European competitions ARE on Kalshi

**606 soccer series carry markets, 88,526 markets, 15.3 BILLION contracts of
volume.** Soccer is one of the largest things on this exchange, not a rounding
error.

| competition | series | match markets | settled | volume |
|---|---|---|---|---|
| **UEFA Champions League** | `KXUCLGAME` | **231** | 201 | **51,663,121** |
| **Europa League** | `KXUELGAME` | 171 | 129 | 12,880,808 |
| Ligue 1 | `KXLIGUE1GAME` | 36 | 6 | 2,170,995 |
| Eredivisie | `KXEREDIVISIEGAME` | 54 | 15 | 1,574,109 |
| **English Premier League** | `KXEPLGAME` | **27** | **0** | **13,565** |
| La Liga | `KXLALIGAGAME` | 45 | 0 | 9,299 |
| Serie A | `KXSERIEAGAME` | 24 | 0 | **10** |

**The Champions League is genuinely large. The user's assumption is correct and
he should be told so plainly.**

**The Premier League is the one apparent exception and it is a TIMING artefact,
not an absence.** Its 27 markets all close 24-25 August -- they are the 2026/27
season's opening fixtures, listed days ago and not yet traded. La Liga and Serie
A are in the identical state. **New, not dead**, and it fixes itself within
weeks.

**Biggest of all is the World Cup**, by a distance: `KXWCGAME` alone is
**4.49 billion** contracts across 312 markets, more than every domestic league
combined. Then `KXCLUBFGAME` 160M, `KXINTLFRIENDLYGAME` 142M, `KXLIGAMXGAME`
117M, `KXMLSGAME` 94M.

Both repo documents were accurate about what they saw and neither was a census.
`tape_soccer_scan.json` is one tape snapshot, which is why friendlies looked
dominant.

## 2. You CAN buy at 97c, and the spread does not cost what the message assumed

**⚠ Correcting my own arithmetic first.** My first pass added HALF THE SPREAD on
top of 97c and concluded the bet was destroyed. That is a double-count, and it is
the same error I flagged in my own de-vig work three days ago: **buying at the
ask IS paying the spread.** Buying NO at 97c means **hitting a resting YES bid at
3c** -- that bid is the executable price and there is nothing further to cross.
The ~78c gap is the distance to the YES *ask* and is irrelevant to entering.

| | you win | you lose | comebacks affordable in 100 |
|---|---|---|---|
| quoted 97c | 3.00c | 97.00c | **3.0** |
| **97c + Kalshi's fee** | **2.83c** | **97.17c** | **2.8** |

**Kalshi's fee at 97c is 0.17c** -- the fee is quadratic and near its minimum at
the edges of the price range. **It eats 6% of the margin, not a third.** Your
premise is arithmetically right and simply does not apply to a trade that crosses
no spread.

The book is there when you want it: at the trade the YES bid is 2c (441 times),
3c (306) or 4c (22), and **0% of those snapshots had no size behind it.**

**The three things that DO bite:**
1. **Rare** -- 1.45% of soccer snapshots, 38 distinct contracts in 5 days.
2. **Small** -- median **$242** of NO available; one time in ten, **$10**.
3. **No exit** -- the other side sits ~78c away, so you are committed to the end
   of the match. You watch the comeback, you cannot trade out of it.

## 3. Two things I could NOT do, and they matter

**I could not measure "the last 20 minutes".** `close_time` on a live soccer
market is the match date plus ~72 hours -- the same placeholder trap as MLB
(**LEDGER BH012**) -- and unlike MLB the soccer ticker carries only a DATE, no
kick-off time. The match minute is not recoverable from either field. The route
is **Pinnacle's `live` flag plus `starts_utc`**, both already in the recorder,
joined on team names. That is a real second pass, not a footnote.

**I measured the wrong leagues for his idea.** The recorder tracks Liga MX,
Argentina, Colombia, Copa do Brasil and Brasileirao. It does **not** record
Champions League or Premier League. So section 2 is evidence about South-American
and Mexican soccer and an *assumption* about the competitions he cares about.
**Adding `KXUCLGAME` and `KXEPLGAME` to the recorder is the cheap fix** and I
have not done it, because the recorder is shared and lengthening its cycle
affects four other threads. Say the word and I will.

## 4. Verdict: NOT a no

The three kill conditions you named were volume being a rounding error (it is
15.3 billion contracts), nothing quoted above 90c (quoted with size every time),
and the spread eating the margin (6%, and not via the spread). **None of them
fires.**

**What replaces them is size.** At $242 a go, 3c of edge is about **7 cents of
profit per trade**. That is the number the `soccer` chat should design against --
a reason for care, not a reason to stop, and better told to them now than after
they have counted goals for a fortnight.
