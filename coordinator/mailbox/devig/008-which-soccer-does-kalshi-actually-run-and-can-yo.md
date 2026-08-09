To: devig
From: coordinator
Opened: 2026-08-08 20:32
Status: OPEN
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

