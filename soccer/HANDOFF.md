# HANDOFF.md — soccer

<!-- COORDINATOR-STATE
doing: nothing - mailboxes 003 and 004 closed, waiting on the user's call
left: the user decides whether to stop. My recommendation is now STOP, changed after the selection canary showed the market does not quote a finished match - which September will not change
needs: no
-->

**As of 2026-08-09.** Written by the session that took mailbox messages 001 and
002, then stopped on the user's instruction.

---

## STOP READING AND READ THIS FIRST

**The stale-price limitation that used to be here is FIXED.** Prices are now
read at every displayed minute, whether or not anything had just happened,
using `clock_map.py` (median error 8 seconds, leave-one-out on 24,159 anchors).
645 matches, 30,648 minute-readings.

**What that changed:** the market is there EARLY and gone LATE. Somebody was
bidding on the losing side **93 times in 100 at the 15th minute and 16 times in
100 at the 89th**. The earlier "four times in five there is no market" was a
late-match fact reported as a general one.

**What it did not change:** there is still no edge. Competition-matched, middle
**−0.40c per contract**, stable across every sample bar tried — and that number
is **conditional on a trade having been available**, see below.

### ⚠ READ THIS BEFORE RE-RUNNING ANYTHING IN SEPTEMBER

`reports/selection_canary.txt` (SO041). **Kalshi stops quoting the losing side
exactly when the match becomes near-certain — the state the idea wanted to buy.**
One reading per match: at the 60th minute the team behind came back **7.1 times
in 100 where you could bet and 0.0 times where you could not**; 5.7 vs 0.0 at the
70th, 4.0 vs 0.4 at the 80th, 2.6 vs 0.0 at the 85th.

**The trade is not mispriced. It is absent by construction, and a deeper book in
September will not create it** — this is about how market makers behave, not
about which league. If you restart this work, that is the thing to disprove
first, and it is cheap to check on any new data.

### The failure mode this folder should be remembered for

**Three separate defects each hid the European book, and each one reported it as
"no fixture" — which in the output is indistinguishable from Kalshi not listing
the competition.**

1. ESPN files Champions League qualifying under `uefa.champions_qual`.
   `uefa.champions` returns **0** fixtures for 1 Jul – 8 Aug; the other returns
   exactly the **66** that Kalshi has settled events for.
2. Exact-name joining matched **6 of 66** — Kalshi's "Kairat" against ESPN's
   "Kairat Almaty". `fixture_join.py` fixes it and is validated by settled-result
   agreement: **57 of 57, 0 disagreements**.
3. `price_by_minute.py` required a `kickoff` field that **53 of 66** of those
   matches do not carry.

Each fix roughly doubled the European sample: 12 → 39 → **63**. **A filter that
drops rows silently becomes an absence claim, and this repo has now made four.**
`coordinator/reflect.py` flagged the wording; the verification was by hand.

## Why this session stopped

The user's instruction, 2026-08-09: *write your handoff and stop until the
Champions League recorder has data.*

**That recorder is not mine.** It belongs to the `devig` chat and lives in
`kalshi-market-scan`, writing `record_soccer_eu.db`. `BRIEF.md`'s devig section
says it needs **about two weeks** before it holds anything useful, and that its
first attempt died in 19 minutes because two programs were pointed at one
database file.

**The recorder is still worth having for the GROUP STAGE**, which is the deep
book and starts in September. It was not needed for qualifying — that data was
already inside Kalshi's window.

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

**The football half stands.** `reports/comeback_table.txt`, **56,927 matches, 26
competitions**, 2015-01-01 → 2024-12-31, with 2025 onward held back and never
opened. `reports/comeback_table.csv` is the full grid.

One goal down, the team behind comes back and wins **9.8 per 100 at half time,
4.0 at the 70th minute, 1.7 at the 80th, 0.4 at the 89th** — but those are
TEN-YEAR AVERAGES. **In 2022-2024 the 80th-minute number is 2.3, not 1.7**, and
the rise is late-only (see SO030). Quote the modern number.

**The user's own hypothesis about team strength is real and ordered.** At the
70th minute, a top-third side one goal up is caught 2.8 times per 100; a
bottom-third side one goal up is caught 7.1. He stated that shape before any data
existed. It is the one dimension in this work that was predicted rather than
found.

**The price half is where it dies.** 645 matches priced at every minute:
a market existed **93 in 100 at the 15th minute** and **16 in 100 at the 89th**.
Competition-matched per reading, the middle result is **−0.40c per contract**,
stable whether a comparison needs 40 matches of history behind it or 200.
**Champions League qualifying, the only European book here, came in at −2.61c,
second worst of ten.**

**The held-out years were never opened.** `PREREGISTRATION_COMEBACK.md` was
committed before any comeback number existed; check the git log, and if that is
not true, disregard the file. The test it describes **never ran**, because its
premise failed first. 2025–2026 remains clean.

---

## What this work did NOT test

**Required by CLAUDE.md §9c Step 7, because a negative result without this list
reads as though the whole idea is dead.** It is not. These are untested, not
disproved:

1. **The Champions League and Premier League GROUP STAGE.** Qualifying is
   measured; the deep book starts in September and is untouched. This is the
   one that matters and it is what the `devig` recorder is for.
2. **The Premier League at all.** `KXEPLGAME` has 200 settled events but the
   last is 2026-05-24, so **zero** fall inside Kalshi's ~69-day candle window.
   Nothing could be measured, and that is a venue limit, not a gap to fill.
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
11. **The strength dimension crossed with price.** The gap table collapses
    strength; only 120 of 572 Champions League qualifying matches get a reading
    on both sides anyway, because those teams play too few ties. Fixing that
    needs each club's DOMESTIC form — a new source per country.
12. **The other legs.** Only the trailing team's NO was priced.
13. **2025 and 2026.** Deliberately unopened, and the pre-registered test has
    still never run.

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
