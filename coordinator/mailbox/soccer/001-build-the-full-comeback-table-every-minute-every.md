To: soccer
From: coordinator
Opened: 2026-08-08 20:32
Status: BLOCKED
Subject: Build the full comeback table: every minute, every score, every Kalshi competition

--- INSTRUCTION ---

You are a NEW chat. Your folder is `soccer/`, which already exists with data
scripts from a session on 2026-08-02. Read `soccer/WHAT_IS_LEFT.md` and
`soccer/dataset.md` before anything else. Create `soccer/README.md`,
`soccer/HANDOFF.md` and `soccer/DECISIONS.md` this session -- none exist.

# THE QUESTION

Late in a match, one team is ahead. You buy NO on the losing team, which pays
if the leading team wins OR it ends level. On Kalshi that is around 97 cents to
make 3 cents. The whole bet reduces to one number:

  **How often does the losing team actually come back and win?**

Fewer than 3 times in 100 and the bet makes money. More than 3 and it loses.

# WHAT THE USER ASKED FOR, AND IT IS A LOOKUP TABLE, NOT A SEARCH

He wants the full picture first, before any strategy: **every minute, every
scoreline, every Kalshi-bettable competition.** Out of 100 games in that exact
state, how often does the losing side come back and win -- and what does Kalshi
charge for it at that moment.

**Build this as a DESCRIPTIVE TABLE for a human to read. It is explicitly NOT a
hunt for the best-looking cell.** If you slice minute x scoreline x league you
will produce thousands of cells and the best of them will look excellent purely
by chance. That is not a hypothetical: `LEDGER.md` B023 ran 2,008 pre-registered
cells in this repo and found LESS than its own shuffled-data null. Do not
report a winner. Report the table.

The user will read it and choose where to go deep using football knowledge you
do not have. **That choice is his and it is the point of the exercise.** Only
then does a real test get pre-registered on data you have held back.

# WHAT HE TOLD ME, IN HIS OWN WORDS, THAT CHANGES THE DESIGN

**Team strength matters as much as the scoreline.** His example: if the 1st
place team is 1-0 down to the 20th place team in the 80th minute, he would not
bet against the 1st place team. A blanket comeback rate hides that completely.
So **team strength has to be a dimension of the table from the start**, not an
afterthought -- league position, or the pre-match price, or both.

**He expects the overall number to show no edge, and he is probably right.** He
said so himself. His argument is that the general rate averages away the
pockets, and the pockets are the point. Treat a flat overall result as the
expected outcome, not a failure, and make sure the table is fine-grained enough
that a pocket could still be visible.

**His starting parameter, if you need one to sanity-check the machinery:**
1-0 up in the 80th minute, buy NO against the losing team.

# A MEASURED TRAP IN YOUR OWN FOLDER

`soccer/reports/inplay_analysis.txt`: the displayed match minute differs from
real wallclock time by about **17.5 minutes at the median**, on 362 events, and
by more than 5 minutes in 55% of cases. **A minute-based join is wrong by a
quarter of an hour.** ESPN's `wallclock` field removes it and the existing study
used it. Any table you build keyed on the displayed minute is fiction.

# THE DATA PROBLEM, WHICH IS YOUR FIRST JOB

`soccer/reports/model_vs_market.txt` shows **24,172 completed matches with a
final score** across Mexico, Argentina, Brazil and USA. **Final scores alone
cannot answer this** -- you need the MINUTE each goal was scored to know who was
losing in the 80th.

ESPN publishes goal times and `soccer/src/` already fetches them, but it has
only been run on 127 fixtures. `WHAT_IS_LEFT.md` says roughly ten years per
league is reachable. **Getting goal times for a few thousand matches is the
gate on everything else.** Do that first, report how many you actually got, and
say plainly which competitions you could NOT get.

# WHAT IS ACTUALLY BETTABLE ON KALSHI -- CHECK, DO NOT ASSUME

Two documents in this repo disagree. `soccer/dataset.md` says Liga MX,
Argentina, Copa do Brasil, Colombia and MLS. `soccer/reports/tape_soccer_scan.json`
shows a different set: mostly **international friendlies** (139 of 210 tickers),
plus Uruguay, USL, Ecuador, Peru, NWSL, Chile, MLS, Colombia and Liga MX.

**Neither mentions the Premier League or the Champions League.** The `devig`
chat has been asked for the definitive list and the liquidity. Do not wait for
it -- build the machinery league-agnostic so any competition can be dropped in.

**If it turns out most of the book is international friendlies, say so loudly.**
A friendly is a different sport for this purpose: teams make six substitutions,
league position means nothing, and nobody is trying. That would not kill the
idea -- it might be where a market is most mispriced -- but it changes every
assumption about team strength.

# THE RULES THAT APPLY

`CLAUDE.md` is the contract; §6 is the evidence standard and §9b lists four
things not to re-open. In particular:

- **The unit of observation is the match.** Not the minute, not the market.
- **Hold back data you do not look at.** Split by time, not at random.
- **Report the naive benchmark** next to anything you find.
- **Paper only. No money, no keys, no order-placing code.** Copy
  `mlb-paper/tests/test_paper_only.py` into your folder before your first
  feature.
- **Pre-register anything that becomes a real test** as
  `soccer/PREREGISTRATION_COMEBACK.md`, committed before the first result
  exists, and it must say what result would make you drop the idea.

# HOW TO REPORT BACK

He is not an engineer and reads on a phone. **No statistics words at all** --
no "pp", no "confidence interval", no "n=". Say it in money, or say it out of
100. "Out of 100 games where a team was 1-0 down at 80 minutes, they came back
and won 4 times" is the right register. Every number gets bigger-is-better or
bigger-is-worse attached. `CLAUDE.md` §1 has the banned word list.

Write your section of `BRIEF.md` with
`py -3 coordinator\brief.py write soccer --file <a file>`, update `STATUS.md`,
write `HANDOFF.md`, and push.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

---

## soccer, 2026-08-08 -- BLOCKED on the user, data collection started anyway

**Status is BLOCKED, not DONE, and the block is deliberate.** This is a new
idea, so `CLAUDE.md` §2 applies: the plan is written and waiting for a go. The
plan and the two open questions are in the message to the user and in the
`BRIEF.md` soccer section.

### Housekeeping asked for, done

`soccer/README.md`, `soccer/HANDOFF.md` and `soccer/DECISIONS.md` all created.
`mlb-paper/tests/test_paper_only.py` copied to `soccer/tests/` and it passes,
including the planted-violation check.

### Four corrections to the tasking

**1. "Any table keyed on the displayed minute is fiction" is wrong for this
table, and right for the price column.** The 17.5-minute measurement in
`reports/inplay_analysis.txt` is correct and is not being disputed. It applies
to joining an ESPN event to a Kalshi price candle. It does not apply to asking
who was ahead in the 80th minute, because "the 80th minute" IS the clock on the
screen -- converting it to elapsed time would be the error. The comeback rate is
keyed on the displayed minute; the price is keyed on the absolute timestamp;
`src/fetch_goal_minutes.py` stores both on every event. Recorded in
`DECISIONS.md`.

**2. The 139-of-210 international friendlies figure is probably a calendar
artifact.** `tape_soccer_scan.json` covers 2026-05-24 to 06-11. That is the
international break immediately before the 2026 World Cup. Friendlies dominating
that particular fortnight is what you would expect, and it is not evidence that
Kalshi's soccer book is mostly friendlies year-round. The warning in the mail --
that a friendly is a different sport for this purpose -- is still right, and
friendlies are in the backfill as their own competition so the table can show
them separately rather than blending them in.

**3. `soccer/data/` was empty.** The 2026-08-02 session's artifacts are not on
this machine; `data/` is gitignored repo-wide. The "24,172 completed matches"
in the tasking is real but it is a number in a committed report, not a file on
disk. Everything is being re-fetched. This is worth knowing before any future
mail cites a `data/` artifact as present.

**4. ESPN was broken before any of this could run.** ESPN's edge now returns 403
to any browser-shaped or unrecognised User-Agent, and 200 to requests' own
default. All 8 ESPN-facing scripts in `soccer/src/` were sending
`Mozilla/5.0 (soccer-research/1.0)` and were dead. Patched, with the measurement
table in `DECISIONS.md`. **Other chats fetching from ESPN should check their own
scripts** -- this was not soccer-specific.

### What was verified before committing to the plan

- ESPN's match-summary endpoint carries goal minutes **and** absolute timestamps
  back to 2015, probed on mex.1 2015, usa.1 2016, bra.1 2019, col.1 2022. The
  gate the mail identified is open.
- All 19 competition slugs return 200, including the 8 Kalshi per-game series
  that were missing from the old 6-league backfill and the 5 European ones.

### Still unresolved and not mine

Kalshi's definitive per-game soccer list. A direct probe on 2026-08-08 got
rate-limited after 2,200 open events and then connection-reset; it found
season-long Premier League, Champions League, La Liga and Bundesliga markets but
no per-game soccer series open at that moment. August is between seasons for
several of these, so that is not evidence of absence. Still waiting on `devig`.
The backfill does not depend on the answer -- it is league-agnostic and 19
competitions wide.


---

# AMENDMENT, same day — the user's own words on the shape of the bet

## 1. Why the bet is safer than it first looks, and it is the point of the idea

At 1-0 down, the trailing team must score **twice** to beat us — one goal only
brings a draw, and we win on a draw. **That is the whole reason he thought of
it.** At 2-0 down they need three. So run **both 1-0 and 2-0**; his instinct is
that 2-0 is the safer bet and 1-0 the riskier one, and he wants to see both
rather than assume.

## 2. Run every minute, not a chosen one

His words: *"look at the sixtieth minute, sixty-fifth minute, seventieth minute,
seventy-fifth minute."* The table has a row for each. Do not pick a favourite.

## 3. Parameters he wants considered, beyond minute and score

Written down before you look at any result, per `CLAUDE.md` §9c step 2:

- the two teams specifically, not just the league;
- league position, or the pre-match price as a proxy for strength;
- **formation and how the teams are playing**;
- **how often this team has thrown away a lead before** — his phrase was "how
  many times has this team bottled a win";
- what people are saying online (the `signal` chat has extractors for this).

Not all of these have data. **List the ones you could not get, and say so** —
that list is a deliverable, not an excuse.

## 4. The European season, which changes the league question

The tape shows mostly international friendlies and small South American leagues
because it was recorded **2026-05-24 to 08-04, the European off-season.** The
Champions League and the Premier League were not being played. **Do not conclude
they are unavailable.** The `devig` chat has been asked for the series list.

## 5. Friendlies, in his words, and he knows this ground

*"Friendlies are a different animal. Friendlies are where you'll see the first
place in the Premier League lose to the last place in the Championship. But
there's also money to be made there still."*

Take that literally as a design instruction: **league position is close to
meaningless in a friendly** and any team-strength feature must be allowed to
behave differently there. It also means friendlies may be where the price is
worst — teams are unpredictable and nobody serious is pricing a Tuesday
friendly. **Report friendlies as their own group throughout. Never pool them
with competitive matches.**

## 6. A fake control, and it is required

Run the whole pipeline once over data with the outcomes shuffled. If it finds an
edge in noise, every number it produced is void. `crypto`'s `L4-A` is the worked
example. The user asked for this himself, unprompted.

## 7. If the answer is no, say what you did NOT test

`CLAUDE.md` §9c step 7. A negative result ends with an actual list of the
versions never tried, not a caveat sentence. **A dead idea with no such list
looks completely dead, and this repo has already killed a live idea that way.**
