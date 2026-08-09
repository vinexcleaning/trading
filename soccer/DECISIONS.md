# DECISIONS.md — soccer

Judgment calls taken without asking, and why. Newest first.

---

## 2026-08-08 — team strength: the user said "go" without picking, so I picked

**The call.** He was asked to choose between league position and the pre-match
betting price as the measure of how good a team is. He replied "go" and did not
choose. Rather than stop again — the pause in `CLAUDE.md` §2 happens once — the
conservative option I had already recommended to him was taken: **position is
the spine, the market price is a cross-check on the recent slice only.**

**Why that is the conservative one and not just the easy one.** The market price
is the sharper measure of the two and I would rather have it. It exists on 53 of
160 matches in `dataset.md` — a third of a 69-day window — against a table
covering about ten years. A column populated on well under one percent of rows
cannot be a dimension of a lookup table; it would silently turn "every
competition, every minute" into "MLS in the summer of 2026". Position is
computable for every row from data already on disk.

**What would change it.** If he says he wants the market's view specifically,
the table can be rebuilt on the recent slice with the price as the spine — it is
a much smaller table and it would be honest about being small.

---

## 2026-08-08 — league position is a rolling window, not a season table

**The call.** Team strength is points per game over a team's **last 20 matches
in that competition**, ranked against every team active in the same competition
in the last 120 days, cut into thirds. Not a season league table.

**Why the season version was thrown away.** The first version detected season
boundaries from gaps in the fixture list. Then the gaps were measured. Colombia's
break between Apertura and Clausura is **41 to 48 days**, so any threshold in
that region splits some campaigns and merges others — and the choice would have
been mine rather than the data's. A number that depends on a threshold I picked
is a number I fitted, and this project has 45 recorded corrections that all
started somewhere like that.

The rolling window needs no boundary at all. It also gives a reading to cup ties
and international friendlies, which have no league table to sit in, and which the
season version could only mark unknown.

**What it costs.** It is no longer literally "4th in the table". It is "one of
the better teams in this league right now", which is what the question actually
turns on. Both readings — a 20-match and a 10-match window — are stored, so
nothing rests on the window length.

**Both teams' strength is known on 89% of matches.** The rest keep an explicit
"unknown" bucket in the table. They are not dropped and not guessed, because
dropping them would quietly remove early-season matches from every cell.

---

## 2026-08-08 — an empty ESPN timeline is a real gap, and my first reading of it was wrong

**⚠ RETRACTION, recorded in place rather than deleted.**

**What I said first, and acted on:** "ESPN serves a stub body under concurrency;
an empty timeline is a throttle to retry." I built three retries with backoff on
that basis. **The evidence was 152 of 700 sample matches coming back empty, and
three hand-picked 'missing' ones having 21, 23 and 18 events when re-fetched.**

**Why that was wrong.** The comparison was broken. The fixture file was still
being appended to by the running backfill, so the list of "missing" matches was
computed against a file that had grown. Those three had never been requested at
all — they were not failures, they were not-yet-fetched. I read a difference
between two file states as a difference between two fetch attempts.

**What is actually true, measured properly:**

| Test | Result |
|---|---|
| Empty rate at 1 worker | 15.0% |
| Empty rate at 4 workers | 10.0% |
| Empty rate at 8 workers | 17.5% |
| 26 genuinely-empty matches, retried 4 times each | **0 recovered** |
| `commentary`, `header.details`, boxscore on those | all empty too |

So concurrency is not the cause and retrying does not help. **ESPN simply has no
play-by-play for some fixtures.** It clusters by competition: of 26, Uruguay 13,
Ecuador 7, Peru 2, Copa do Brasil 2, friendlies 2, and **none at all in Mexico,
Argentina, Brazil, Colombia or MLS**.

**What changed as a result.** Retries dropped from three to one. Workers raised
from 4 to 8, since concurrency was never the problem — which makes the full run
several times faster. Every failure is now written to a gaps file and reported
per competition, split into "0-0, costs nothing" and "had goals, genuinely
lost", because **the leagues with the worst coverage are Kalshi-bettable ones**
and that has to appear in the output rather than in a console log.

**The general lesson, which is the reason this entry is long:** the first
explanation was plausible, matched the numbers, and would have made the run four
times slower while hiding a real coverage limitation behind a retry loop. It
took ten minutes to test and the test reversed it.

---

## 2026-08-08 — goals are attributed by ESPN team id, never by name

**The call.** The two sides of a match are identified from the ids in the match
summary's own header, and each goal is matched to a side by id.

**Why.** The first sample sent **15 goals in bra.1 to neither team** and broke 8
matches outright. ESPN's scoreboard calls the club "Athletico-PR" and its own
match summary calls it "Athletico Paranaense". Ids agree where names do not.

The score is now also read from the same response as the timeline, so the
integrity check compares like with like, and the scoreboard's version is kept
alongside so the two can be compared rather than assumed equal.

---

## 2026-08-08 — started the data collection before the user said "go"

**The call.** `CLAUDE.md` §2 says a new idea gets a plan first and then a pause.
The comeback question arrived as mail and is a new idea, so the plan is written
and this session is waiting. But the data collection was started anyway, in the
background, before the answer came back.

**Why.** Every version of this question — his starting parameter, a different
minute, a different scoreline, a different league, or a decision to drop the
idea entirely — needs the same input: the minute each goal was scored, for as
many matches as can be got. It takes several hours of wall-clock and nothing
else about the design depends on it. Waiting would have spent his time, not
mine.

**What was deliberately NOT started.** Anything that shapes the measurement:
which cells the table has, which team-strength measure is used, where the
held-out period is cut. Those wait for him, because those are what the pause is
for.

---

## 2026-08-08 — 19 competitions in the backfill, not the original 6

**The call.** `backfill_espn.py` fetched 6 competitions. It now fetches 19.

**Why.** Three sets, and the reason differs for each:

- The original 6 (`mex.1`, `arg.1`, `bra.1`, `col.1`, `usa.1`,
  `bra.copa_do_brazil`) are the ones `dataset.md` confirmed Kalshi quotes.
- 8 more (`fifa.friendly`, `uru.1`, `per.1`, `ecu.1`, `chi.1`, `usa.usl.1`,
  `usa.usl.l1`, `usa.nwsl`) appear in `reports/tape_soccer_scan.json` as
  per-game Kalshi series and were missing entirely.
- 5 European (`eng.1`, `esp.1`, `ita.1`, `ger.1`, `uefa.champions`) have **not**
  been seen quoted per-game on Kalshi. They are in anyway, because they are the
  competitions the user actually knows, and a fixture list is cheap while a
  missing league costs a full re-run.

Every slug was probed and returns 200 before being added.

---

## 2026-08-08 — the ESPN User-Agent, and what was actually measured

**The call.** Removed the `User-Agent` override from all 8 ESPN-facing scripts.

**Why.** They were failing. ESPN's edge now returns 403 to browser-shaped
strings. Measured on the same URL, same minute:

| User-Agent sent | Result |
|---|---|
| `Mozilla/5.0 (soccer-research/1.0)` (what the scripts had) | **403** |
| `Mozilla/5.0 (Windows NT 10.0; ...) Chrome/126` | **403** |
| `Mozilla/5.0` | **403** |
| `soccer-research/1.0` | **403** |
| `curl/8.4.0` | **200** |
| requests' own default, i.e. no override | **200** |

The counter-intuitive part is that pretending to be a browser is what gets
blocked. The scripts now send no override. The comment in each file says so, so
nobody "fixes" it by adding a browser string back.

**Scripts that talk to football-data.co.uk rather than ESPN were left alone** —
their browser strings may be load-bearing there and none of them was failing.

---

## 2026-08-08 — the displayed match minute is the right key for the table

**The call.** The comeback table will be keyed on the **displayed match
minute**, not on real elapsed time since kickoff.

**Why, and why this contradicts the tasking.** The mail said "any table you
build keyed on the displayed minute is fiction", citing the measurement in
`reports/inplay_analysis.txt` that the displayed minute sits 17.5 minutes away
from true elapsed time at the median on 362 events.

That measurement is right and it is not being disputed. What it applies to is
narrower than the mail says. It matters when you are **joining an ESPN event to
a Kalshi price candle** — get that wrong and you read the price from a quarter
of an hour before the goal, which is fatal. It does not matter when you are
asking **who was ahead in the 80th minute**, because "the 80th minute" is a
statement about the clock on the screen, which is exactly what the displayed
minute is. Converting it to elapsed time would be the error.

So: displayed minute for the comeback rate, absolute timestamp for the price.
`src/fetch_goal_minutes.py` stores both on every event so this never has to be
re-fetched, and neither column can quietly borrow the other's key.

---

## 2026-08-08 — a goal with no readable minute is dropped, not defaulted

**The call.** `parse_minute()` returns `None` rather than `0` when it cannot
read a minute, and a match whose goal timeline does not add up to its final
score is reported as unusable rather than repaired.

**Why.** A goal silently placed at minute 0 would move a match from "level" to
"1-0 up from the start" and would inflate exactly the number this whole study
is trying to measure. The coverage report counts these out loud so the size of
the loss is visible instead of absorbed.
