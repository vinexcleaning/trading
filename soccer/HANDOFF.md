# HANDOFF.md — soccer

<!-- COORDINATOR-STATE
doing: downloading goal minutes for ~10 years across 24 competitions; the table code is written and tested and runs the moment the data lands
left: run the table on the full data and report it; the Kalshi price column is still a separate job on the recent slice only
needs: no
-->

**As of 2026-08-08.** Written by the session that took mailbox message 001.

---

## Where this got to

The mail asked for a full comeback lookup table: every minute, every scoreline,
every Kalshi-bettable competition. The plan was written, the user said **go**,
and the work is running. He did not answer the one question in the plan — league
position or pre-match price for team strength — so the conservative option was
taken and logged in `DECISIONS.md`.

**The analysis code is written, tested and validated end to end on a 475-match
sample.** It is waiting on data, not on design.

## What is running right now

A single chained job, launched 2026-08-08. Every stage is resumable, read-only,
unauthenticated, and writes its own log in `soccer/reports/`.

| Stage | What it does | Log |
|---|---|---|
| `backfill_espn.py` | 13,414 week-windows, 2015 → today. Fixture list and final scores. ~4 h. | `backfill_run.log` |
| `backfill_espn.py` again | Picks up the 5 competitions added after checking Kalshi (Ligue 1, Europa League, World Cup, Club World Cup, Conference League). Only new windows. | `backfill_run2.log` |
| `fetch_goal_minutes.py` | One ESPN match-summary call per fixture, 8 workers. **The minute of every goal.** | `goal_minutes_run.log` |
| `fetch_goal_minutes.py` again | Picks up the fixtures from the second backfill. | `goal_minutes_run2.log` |
| `build_strength.py` | How good each team was on the day. Runs its own no-lookahead check and fails loudly. | `strength_run.log` |
| `build_comeback_table.py` | The table. | `table_run.log` |

`soccer/reports/pipeline.log` prints `PIPELINE_COMPLETE` when all of it is done.

## The analysis code, and what each piece is responsible for

| Script | What it does |
|---|---|
| `src/build_strength.py` | Team strength: points per game over a rolling 20 matches in that competition, ranked against everyone active in the last 120 days, cut into thirds. **Not** a season table — see `DECISIONS.md` for why that was thrown away. Includes `test_no_lookahead()`, which rebuilds a sample independently and asserts agreement. |
| `src/build_comeback_table.py` | Replays every match minute by minute and asks, for each minute someone was ahead, whether the side behind went on to win in regulation. Writes `reports/comeback_table.txt` and a full-grid `reports/comeback_table.csv`. |
| `tests/test_comeback_logic.py` | 11 tests of the replay against matches whose answer is known by hand — a draw is not a comeback, extra time does not count, the leader can change sides, stoppage goals sit at minute 90. |
| `tests/test_paper_only.py` | The structural paper-only guard. |

Run the tests with `py -3 soccer/tests/test_comeback_logic.py` — there is no
pytest on this machine's `py -3`.

**Neither is in a runner registry.** They are one-off collection jobs, not
standing background tests, so they are deliberately not in `runners/runners.json`
or `coordinator/runners.json`. If either dies, re-run it — both resume.

To see where the goal-minute fetch got to without waiting for it:

```bash
py -3 soccer/src/fetch_goal_minutes.py report
```

## What the next session picks up

1. **Read `soccer/reports/goal_minutes_coverage.txt` first.** It says how many
   matches have a goal timeline that actually adds up to the final score. A
   match whose timeline disagrees with its score is unusable and is dropped, not
   repaired.
2. **Do not build the table until the user has answered the plan.** The open
   questions are in `coordinator/mailbox/soccer/001-*.md` under the reply line
   and in the BRIEF section.
3. **Nothing is pre-registered yet, on purpose.** The table is descriptive. A
   pre-registration (`soccer/PREREGISTRATION_COMEBACK.md`) gets written only
   when the user picks a cell to test properly, and it gets committed before the
   first result on the held-out years exists.

## Three things that will waste your time if you do not know them

**ESPN 403s browser-shaped User-Agents since 2026-08-08.** All 8 ESPN scripts
were patched to send no override. Measurements are in `DECISIONS.md`. Do not put
a browser string back.

**`soccer/data/` was empty at the start of this session.** The 2026-08-02
session's artifacts are not on this machine — `data/` is gitignored repo-wide.
Everything is being re-fetched rather than assumed present. Reports in
`soccer/reports/` are committed and survived; the data behind them did not.

**Kalshi's per-game soccer list is now settled for existence** — see
[kalshi_soccer_series.md](kalshi_soccer_series.md). 20 series, including the
Premier League and the Champions League, which neither repo document mentioned.
The "mostly international friendlies" reading of `tape_soccer_scan.json` was a
calendar artifact of the pre-World-Cup international break.

**Liquidity is NOT settled and is not mine.** A series existing is not a market
you can get filled in — that distinction is the whole of B024. Still `devig`'s.

**Do not query Kalshi's `/events` endpoint in a tight loop.** An unpaced scan on
2026-08-08 was rate-limited after 2,200 events and then had the connection reset
by the host. One second between calls was fine.
