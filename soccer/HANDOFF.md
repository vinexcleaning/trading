# HANDOFF.md — soccer

<!-- COORDINATOR-STATE
doing: fetching goal minutes for ~10 years of soccer, 19 competitions, so a comeback table can exist at all
left: build the descriptive comeback table once the fetch lands; hold back 2025-2026 untouched
needs: yes - the comeback plan is written and waiting on a go/no-go, and on whether he wants league position or the pre-match price as the team-strength column
-->

**As of 2026-08-08.** Written by the session that took mailbox message 001.

---

## Where this got to

The mail asked for a full comeback lookup table: every minute, every scoreline,
every Kalshi-bettable competition. **The plan is written and this session is
paused on it**, per `CLAUDE.md` §2 — a new idea gets a plan and a wait, not a
head start on the analysis.

What was **not** paused is the data collection, because every version of the
question needs the same input and it takes hours. See `DECISIONS.md` for that
call.

## What is running right now

| Job | What it does | Where it writes |
|---|---|---|
| `src/backfill_espn.py` | 13,414 week-windows, 19 competitions, 2015 → today. Fixture list and final scores. About 4 hours. Resumable — a kill costs one window. | `soccer/data/espn_history/matches.jsonl` and `_progress.json` |
| `src/fetch_goal_minutes.py` | Chained to run when the above finishes. One ESPN match-summary call per fixture, 4 workers. Pulls **the minute of every goal**. Resumable. | `soccer/data/goal_minutes.jsonl` |

Logs: `soccer/reports/backfill_run.log`, `soccer/reports/goal_minutes_run.log`.

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

**Kalshi's per-game soccer list is not settled.** `soccer/dataset.md` names 5
competitions; `soccer/reports/tape_soccer_scan.json` shows 10, dominated by
international friendlies. Those two do not contradict each other so much as
sample different weeks — see the BRIEF section for why the friendlies number is
probably a June artifact. The `devig` chat was asked for the definitive list. A
direct probe of Kalshi's open events on 2026-08-08 got rate-limited and then
connection-reset after 2,200 events; it found season-long Premier League,
Champions League, La Liga and Bundesliga markets but **no per-game soccer series
open at that moment**. That is not evidence they do not exist — August is
between seasons for several of these.
