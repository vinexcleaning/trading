# HANDOFF.md — soccer

<!-- COORDINATOR-STATE
doing: the comeback table is BUILT on 56,173 matches 2015-2024; measuring what Kalshi actually charges in those states
left: the user picks one pocket from the table, then the pre-registered test runs on the held-out 2025-2026 years
needs: no
-->

**As of 2026-08-09.** Written by the session that took mailbox messages 001 and 002.

---

## Where this got to

The mail asked for a full comeback lookup table: every minute, every scoreline,
every Kalshi-bettable competition. **It is built.** 56,173 matches, 23
competitions, 2015-01-01 to 2024-12-31, with 2025 onward held back and never
opened. `reports/comeback_table.txt` is the write-up; `reports/comeback_table.csv`
is 39,930 cells.

The user said **go** without answering the one question in the plan — league
position or pre-match price for team strength — so the conservative option was
taken and logged in `DECISIONS.md`.

**Headline, and the warning that must travel with it.** One goal down, the team
behind comes back and wins 4.0 times per 100 at the 70th minute, 1.7 at the 80th,
0.4 at the 89th. At 97 cents the break-even is 2.80. **That is not an edge.**
There is no Kalshi price in the table at all — the 97 cents is the user's
assumption. `src/price_at_state.py` is measuring the real one, and B024 is the
standing reminder that this is exactly how a number dies.

## The pipeline that produced it (all finished)

Every stage is resumable, read-only, unauthenticated, and writes its own log in
`soccer/reports/`. Re-run any of them and they pick up where they stopped.

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

1. **Read `reports/goal_minutes_coverage.txt` first.** Coverage is severely
   uneven. Uruguay lost 99.0% of its matches, Copa do Brasil and Ecuador about
   half, Peru four in ten. Twelve competitions lost essentially nothing.
2. **The user picks ONE pocket from the table.** That choice is his and it is
   the point of the exercise. Do not pick one for him and do not rank the cells.
3. **`PREREGISTRATION_COMEBACK.md` was committed before any comeback number
   existed** — check the git log, and if that is not true, disregard the file.
   It allows one pocket and one test, on the held-out years, with six named ways
   to drop the idea.
4. **`src/price_at_state.py`** measures what Kalshi charges, read at the exact
   wallclock of a goal so nothing has to be interpolated. Its output is
   `reports/price_at_state.txt`. Matches it touches are excluded from the
   held-out test set in advance.
5. **`LEDGER_SOCCER.md` needs one line from `coordinator`** to be visible to
   `idea.py` — `ledger.py`'s `SUB_LEDGERS` list. Requested in `STATUS.md`.

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
