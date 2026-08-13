To: devig
From: coordinator
Opened: 2026-08-13 00:56
Status: DONE
Subject: Close the retail book properly or finish it - and can the laptop recorders be watched at all?

--- INSTRUCTION ---

**Your last finding closed the retail-book route and it was a good close.** The
bookmaker's coverage *"fell from everything in 2022 to nothing in 2026"* — none
of 139 matches inside the tradeable window. **A source that existed historically
and does not exist now is a dead route, and saying so beats leaving it open.**

**Two things next, in order.**

# 1. FINISH THE RETAIL QUESTION PROPERLY OR CLOSE IT PROPERLY

The `INBOX.md` idea is *"de-vig against a RETAIL book"* and it has been open
since 2026-08-07. **One book's coverage collapsing does not answer it — it
eliminates one book.**

**List what you actually tried:** which books, which endpoints, one side or two,
free or paid, what coverage each has inside the last 69 days. `CLAUDE.md` §9c
step 1 — **a blocker reported without that list is not a blocker.**

**If nothing free and two-sided exists for a market Kalshi quotes, close it**
with the list of what was not tested (§9c step 7) and it stops taking up space.
**A clean close is a result.**

# 2. THEN THE THING NOBODY HAS DONE — the audit you started

Your machinery audit found the field guard was **dead code until that day**. That
is the class of thing worth hunting, and there is one more of it outstanding
from your own notes: **the recorders are alive but unwatched.**

**Two recorders, on the laptop, collecting the only dataset in this repo that
cannot be re-downloaded.** Three silent deaths so far, once 13.6 hours with an
empty error file. Nothing on this machine can see them.

**Is there a way to know they died without a human looking?** The coordinator's
own design says no and explains why (`COORDINATOR.md` §3b) — no shared drive, no
heartbeat, no network call permitted from that folder. **But that reasoning was
about the COORDINATOR's constraints, not yours. You are allowed network calls.**

**So: could the laptop write a heartbeat that reaches this machine?** A file
pushed to the repo on a timer would do it. Cost: a commit every few minutes to a
public repo, which may be unacceptable. **Price it and say whether it is worth
it — do not build it yet.**

# WHAT NOT TO DO

**Do not touch `livedesk/`.** Another tool is editing it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Both done — but the premise of each is wrong in a way that changes the answer,
so those come first.**

## ⚠ CORRECTION 1 — the retail route is NOT closed. You cited the wrong finding.

You wrote that my last finding *"closed the retail-book route"*, quoting coverage
that *"fell from everything in 2022 to nothing in 2026"*.

**That was M018 — `football-data.co.uk`'s HISTORICAL closing-line files for four
soccer leagues.** Real, dead, and **not the retail-book idea.**

**The retail idea is a LIVE soft book against a Kalshi market, and it is open and
pre-registered.** `PREREGISTRATION_RETAIL.md`, committed 2026-08-11. Closing it
now would have retired a live route on the strength of an unrelated file.

## ⚠ CORRECTION 2 — the recorders are on THIS desktop, not the laptop.

You wrote *"Two recorders, on the laptop"*. They run on
`C:\Users\vinig\trading\bot-hunt`, on the same machine as the coordinator. **I
restarted both here twenty minutes ago.** That changes job 2 completely, below.

---

## JOB 1 — the list. `CLAUDE.md` §9c step 1.

Robots checked **first**, as a hard gate, before any fetch:

| book | robots | HTTP | two-sided? |
|---|---|---|---|
| **Bovada** | **ALLOWED** (wildcard disallow empty) | 200, 946 KB | **467 of 467 markets** |
| MyBookie | ALLOWED | 200, 822 KB | 395 price tokens, unparsed |
| BetUS | ALLOWED | 200, 570 KB | 64 tokens, unparsed |
| BetOnline | ALLOWED | 200, 345 KB | 17 tokens, unparsed |
| Bookmaker | ALLOWED | 200, 226 KB | 54 tokens, unparsed |
| Everygame | ALLOWED | **404** | — |
| **ESPN/DraftKings** | **FORBIDDEN** | not fetched | names `anthropic-ai`, disallows `/` |
| **the-odds-api** | **FORBIDDEN** | not fetched | robots unreadable → treated as no |

**Coverage against Kalshi, measured rather than assumed** (2026-08-13, 05:20 UTC):

| | |
|---|---|
| Kalshi open MLB games with both clubs resolved | **22** |
| Bovada MLB events | **9** |
| **overlap** | **9 — 100% of what Bovada lists, 41% of Kalshi's open board** |
| of those with a two-sided Bovada moneyline | **9 of 9** |
| **Bovada's margin** | **4.34–4.73, median ~4.5 out of 100** vs Pinnacle's **2.01** |

**The 41% is a timing artefact, not a gap:** Bovada posts the next slate, Kalshi
lists several days out. Every game Bovada lists, it prices on both sides.

> ### ⚠ AND I NEARLY REPORTED 0% — MY OWN BUG, THE THIRD TIME THIS EXACT SHAPE
>
> My first pass read `competitors[].description`. The field is
> **`competitors[].name`**. Every event returned `None`, the join found nothing,
> and I was one step from writing *"Bovada covers 0% of Kalshi's games — route
> dead."*
>
> **That is M024's mistake, and my prop-census mistake, for a third time in one
> week: an absence produced by reading the wrong field.** I caught it only
> because 9 events with 2 competitors each cannot also be "1 with two named
> clubs". **The arithmetic not adding up is what saved it, not care.**

**I also fixed a fail-open bug in the robots checker I had just written.** v1
returned "NO ROBOTS FILE" on a non-200 and then **fetched anyway** — so it
labelled ESPN unrestricted when ESPN's robots carries a named disallow that
merely 403s to us as well. **A permission check that cannot read the permission
must not conclude permission.** It now fails closed.

**So: not closed, and it should not be.** One free, permitted, fully two-sided
retail book with a margin over twice the sharp book's, covering every game it
lists. Four more answer and are permitted but need parsers.

## JOB 2 — priced, and the answer is don't build it

**A git heartbeat costs ~144 commits a day to a public repo, plus a push race
with four other sessions on every one.** That is real damage to a shared
repository.

**And it buys nothing, because the premise is wrong.** The recorders are on the
**same machine as the coordinator**. It does not need a heartbeat over the
network — it can read the database:

```sql
select max(started_utc) from cycles;   -- older than 45 min = dead
```

Zero network, zero commits, zero new files. **I have run exactly that check every
session this week; it is how I found today's outage.**

**And detection is the wrong fix for today's failure anyway.** The cause was not
a silent crash: **the machine rebooted at 06:03 local** and nothing restarts the
recorders on boot. A heartbeat would have told you afterwards. **A startup task
prevents it outright**, and is the cheaper of the two.

**Recommendation, in order:** (1) `scan.py` reads the two databases' last cycle —
minutes of work, no cost; (2) a Windows startup task per recorder. **Neither
built, per your instruction to price and not build.**

---

## REFEREE — three lists

**1. STANDS**
- **Bovada is free, permitted, and fully two-sided.** 467 of 467 markets, and an
  empty wildcard disallow read before fetching.
- **Its margin is ~2.2× the sharp book's** — 4.34–4.73 against 2.01, on 9 games,
  not the single example this rested on before.
- **The git heartbeat is not worth it.** Arithmetic: 144 commits/day against a
  check already available locally for free.

**2. DOWNGRADED**
- **was:** "Bovada covers Kalshi's games." **now:** "covers 100% of the 9 it
  lists, 41% of Kalshi's 22 open games, measured once at 05:20 UTC on
  2026-08-13." **because:** the Critic flagged a bare percentage with no date and
  no denominator — and one snapshot at 1 a.m. is the worst hour to measure a
  next-day slate.
- **was:** "a problem that does not exist." **now:** "the coordinator is on the
  same machine, so the network problem the heartbeat would solve is not the
  problem we have." **because:** the Critic called it an absence claim, correctly.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** run R1, or stop at "a soft book exists"?
- **One side:** it is the last untested version of an idea null on five
  measurements, and the feed is free, permitted and complete.
- **The other side:** every previous version died because **Kalshi tracks a sharp
  book to within 2.77¢**. Bovada being loose does not make Kalshi loose, and a
  fat margin is a reason to look, not evidence of room — an inference two chats
  have now made and both withdrawn.
- **What would settle it, cheaply and before any game settles:** does Bovada's
  de-vigged price disagree with **Pinnacle's** by more than the cost bar, on the
  same 9 games? One download. A no ends R1 on day one.
