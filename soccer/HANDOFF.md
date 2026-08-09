# HANDOFF.md — soccer

<!-- COORDINATOR-STATE
doing: nothing - stopped by the user 2026-08-09, waiting on the devig chat's Champions League recorder
left: re-measure the price in STALE states (the current price sample is only ever 2 minutes after a goal, which is NOT the case the idea is about); then, if a price exists, the pre-registered test on the held-out years
needs: no
-->

**As of 2026-08-09.** Written by the session that took mailbox messages 001 and
002, then stopped on the user's instruction.

---

## STOP READING AND READ THIS FIRST

**The comeback idea was reported to the user as answered — "no, the price is not
there". That answer is narrower than it was stated, and the narrowing is mine,
found after reporting.**

`src/price_at_state.py` reads the Kalshi price **at the wallclock of a goal, plus
two minutes.** Every one of its 544 priced moments is therefore *just after
somebody scored*. For the 149 moments at the 70th minute or later, that means
**the goal itself happened at minute 68 or later.**

**That is not the situation the idea is about.** The ordinary case — 1-0 since
the 20th minute, now it is the 80th and nothing has happened for an hour — is
**almost entirely absent from the price sample.** A book two minutes after a late
goal and a book that has sat on the same scoreline for an hour are not the same
book, and nothing here measured the second one.

Which way it cuts is **not known and must not be guessed**:

- it could be *worse* — an hour of quiet lets the price settle further into the
  extreme, and 99/100 becomes even more universal;
- it could be *better* — an hour gives market makers time to post resting
  offers, so there may be liquidity at 97–98 that simply does not exist two
  minutes after a goal.

**Both are plausible and neither was measured.** Until it is, the honest
statement is: *right after a late goal, the 97-cent trade is available 7 times in
149. In a settled late scoreline, unknown.*

**This is job #1 for the next session** and it needs no new download — Kalshi
candles for the same 69-day window already answer it. Sample the price at a fixed
displayed minute (say 80) in every match, regardless of when the last goal was,
using the same wallclock method in `price_at_state.py`.

`LEDGER_SOCCER.md` SO026–SO028 carry this limitation inline. The artifact shown
to the user does **not** — it should be corrected before it is read again.

---

## Why this session stopped

The user's instruction, 2026-08-09: *write your handoff and stop until the
Champions League recorder has data.*

**That recorder is not mine.** It belongs to the `devig` chat and lives in
`kalshi-market-scan`, writing `record_soccer_eu.db`. `BRIEF.md`'s devig section
says it needs **about two weeks** before it holds anything useful, and that its
first attempt died in 19 minutes because two programs were pointed at one
database file.

**Do not start, restart, adopt or write to that recorder.** If it has stopped,
that is a note for `devig` in `STATUS.md`, not a thing to fix from here.

**Why waiting is the right call and not just obedience.** Every price in this
folder comes from **June to early August 2026** — the pre-World-Cup international
break, the World Cup, and pre-season. The Premier League's markets all settle
24–25 August and the Champions League proper had barely begun. So the two
competitions with the deepest books anywhere in soccer are **the two this folder
has essentially no price data for**, and they are exactly where an available
97-cent price is most likely to exist. Measuring the European season is not a
refinement of this work; it is the first real test of it.

---

## What is settled, and what it rests on

**The football half stands.** `reports/comeback_table.txt`, 56,173 matches, 23
competitions, 2015-01-01 → 2024-12-31, with 2025 onward held back and never
opened. `reports/comeback_table.csv` is the full 39,930-cell grid.

One goal down, the team behind comes back and wins **9.8 per 100 at half time,
4.0 at the 70th minute, 1.7 at the 80th, 0.4 at the 89th.** The exact scoreline
matters more than the gap: at the 80th minute 1-0 is 1.7 and 3-2 is 2.8.

**The user's own hypothesis about team strength is real and ordered.** At the
70th minute, a top-third side one goal up is caught 2.8 times per 100; a
bottom-third side one goal up is caught 7.1. He stated that shape before any data
existed. It is the one dimension in this work that was predicted rather than
found.

**The price half is where it dies, subject to the limitation at the top.** Of 149
moments at the 70th minute or later, 79.2% had **nobody bidding on the losing
side at all** — nothing to buy below 100 — and only 7 were at 97 cents or less.
Of those 7, **four were 2-1 and two were 3-2**, the highest-comeback scorelines
on the table. The cheap price and the safe state did not co-occur.

**The held-out years were never opened.** `PREREGISTRATION_COMEBACK.md` was
committed before any comeback number existed; check the git log, and if that is
not true, disregard the file. The test it describes **never ran**, because its
premise failed first. 2025–2026 remains clean.

---

## What this work did NOT test

**Required by CLAUDE.md §9c Step 7, because a negative result without this list
reads as though the whole idea is dead.** It is not. These are untested, not
disproved:

1. **Stale scorelines** — the top of this file. The single most important one.
2. **The European season.** No Premier League or Champions League price data
   worth the name. This is what the wait is for.
3. **The two teams' identities.** The table has strength *tiers*, never clubs.
   "Atlético at home protecting a 1-0" is a different bet and was not asked.
4. **Whether a team has thrown away leads before.** The user named this
   explicitly. The data to build it exists in `data/goal_minutes.jsonl` and it
   was not built.
5. **Red cards as a dimension.** Collected on every match, used in nothing.
6. **Home versus away for the leading side.**
7. **Competition stage** — knockout, group, or league. A knockout tie where a
   draw sends someone through is a different match and is scored as one.
8. **Formation, tactics, and anything said online.** Three of the user's own
   listed parameters, none of them attempted.
9. **The other legs.** Only the trailing team's NO was priced. The draw leg and
   the leading team's YES move too.
10. **Uruguay, and the half-covered competitions** — Ecuador, Peru, Copa do
    Brasil, NWSL. See SO024; Uruguay lost 99.0% of its timelines and Kalshi
    lists it.
11. **Lower prices earlier in a match.** 88 cents at minute 15 was measured with
    strength collapsed. With a strength filter it was never looked at.
12. **2025 and 2026.** Deliberately unopened.

---

## The pipeline that produced it (all finished, all resumable)

Read-only, unauthenticated, no credentials. Each writes its own log in
`soccer/reports/`. Re-run any of them and they pick up where they stopped.

| Stage | What it does | Log |
|---|---|---|
| `backfill_espn.py` | 13,414 week-windows, 2015 → today. Fixtures and final scores. ~4 h. | `backfill_run.log` |
| `backfill_espn.py` again | The 5 competitions added after checking Kalshi (Ligue 1, Europa, World Cup, Club World Cup, Conference). | `backfill_run2.log` |
| `fetch_goal_minutes.py` | One match-summary call per fixture, 8 workers. **The minute of every goal.** | `goal_minutes_run.log` |
| `fetch_goal_minutes.py` again | The fixtures from the second backfill. | `goal_minutes_run2.log` |
| `build_strength.py` | How good each team was on the day. Runs its own no-lookahead check and fails loudly. | `strength_run.log` |
| `build_comeback_table.py` | The table. | `table_run.log` |
| `price_at_state.py` | What Kalshi charged. **Only ever goal + 2 min — see the top.** | `price_at_state.txt` |
| `price_vs_rate.py` | Joins the two halves. | `price_vs_rate.txt` |

`soccer/reports/pipeline.log` prints `PIPELINE_COMPLETE` when the chain is done.

**None of these is in a runner registry**, deliberately — they are one-off
collection jobs, not standing background tests, so they are absent from both
`runners/runners.json` and `coordinator/runners.json`. If one dies, re-run it.

To see where the goal-minute fetch got to without waiting for it:

```bash
py -3 soccer/src/fetch_goal_minutes.py report
```

## The analysis code, and what each piece is responsible for

| Script | What it does |
|---|---|
| `src/build_strength.py` | Points per game over a rolling 20 matches in that competition, ranked against everyone active in the last 120 days, cut into thirds. **Not** a season table — `DECISIONS.md` records why that was thrown away. Includes `test_no_lookahead()`, which rebuilds a sample independently and asserts agreement. |
| `src/build_comeback_table.py` | Replays every match minute by minute and asks, for each minute someone was ahead, whether the side behind went on to win in regulation. |
| `src/price_at_state.py` | Kalshi's price at the exact wallclock of a goal, plus two minutes. Pays the ask, never the middle. |
| `src/price_vs_rate.py` | The join, plus the break-even each price can survive. |
| `tests/test_comeback_logic.py` | 11 tests of the replay against matches whose answer is known by hand — a draw is not a comeback, extra time does not count, the leader can change sides, stoppage goals sit at minute 90. |
| `tests/test_paper_only.py` | The structural paper-only guard, with planted violations to prove the detector still bites. |

Run the tests with `py -3 soccer/tests/test_comeback_logic.py` — there is no
pytest on this machine's `py -3`.

---

## What the next session does, in order

1. **Fix the artifact and the user-facing claim** to carry the stale-state
   limitation at the top of this file. It currently reads as a general answer.
2. **Measure the price in stale states.** No new download needed.
3. **Only then**, if a tradeable price turns out to exist, does
   `PREREGISTRATION_COMEBACK.md` come off the shelf. One pocket, one test, on the
   held-out years, six named ways to drop it.
4. **The user picks the pocket.** That choice is his and it is the point of the
   exercise. Do not pick one for him and do not rank the cells.
5. **`LEDGER_SOCCER.md` still needs one line from `coordinator`** — adding it to
   `ledger.py`'s `SUB_LEDGERS` list, so `idea.py` can see these claims.
   Requested in `STATUS.md`; until it lands, SO001–SO028 are invisible to the
   "has this been tried" check.

---

## What `devig` should be told, and what it already knows

`BRIEF.md`'s devig section lists as open: *"measure how OFTEN the 97c trade is
really available in the last 20 minutes (only 3 sightings so far)"*.

**This folder has partially answered that** — 7 of 149 moments at the 70th minute
or later — and devig's 3 sightings and this 7-in-149 are consistent. **But it is
the same limitation:** both are prices right after a goal. Neither has measured a
settled scoreline. Flagged in `STATUS.md` so the work is not done twice, and so
the shared limitation is not mistaken for two independent confirmations.

---

## Four things that will waste your time if you do not know them

**ESPN 403s browser-shaped User-Agents since 2026-08-08.** All 8 ESPN scripts
send no override. Measurements are in `DECISIONS.md`. Do not put one back.

**`soccer/data/` was empty at the start of this session.** The 2026-08-02
artifacts are not on this machine — `data/` is gitignored repo-wide. Everything
was re-fetched rather than assumed present. The reports survived; the data
behind them did not.

**Kalshi's per-game soccer list is settled for existence** — 20 series, including
the Premier League and the Champions League, which neither repo document
mentioned. See `kalshi_soccer_series.md`. The "mostly international friendlies"
reading of `tape_soccer_scan.json` was a calendar artifact of the pre-World-Cup
international break. **Liquidity is NOT settled and is not mine** — a series
existing is not a market you can get filled in, and that distinction is the whole
of B024.

**Do not query Kalshi's `/events` endpoint in a tight loop.** An unpaced scan on
2026-08-08 was rate-limited after 2,200 events and then had the connection reset
by the host. One second between calls was fine.
