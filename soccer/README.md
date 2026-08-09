# soccer/

**What this folder is.** Research into soccer markets on Kalshi. Right now it is
answering one question: **late in a match, when one team is ahead, how often
does the losing team actually come back and win?** Kalshi sells that as roughly
97 cents to make 3, so the whole bet is a single number — if the losing side
comes back fewer than 3 times in 100, buying against them makes money.

**Nothing here places an order and nothing here holds a credential.**
`tests/test_paper_only.py` walks every file in `src/` and fails if order-shaped
code, a credential, or a non-GET request appears. Run it before you commit.

**Owner:** the `soccer` chat. Mailbox: `coordinator/mailbox/soccer/`.

---

## The state of it, in one paragraph

A session on 2026-08-02 built the data plumbing — an ESPN fetcher, a Kalshi
tape scanner, a match joiner, and an event study of what the price does after a
goal. It stopped at 160 matches, which is Kalshi's ~69-day retention window and
far too few to answer anything. The session that started 2026-08-08 is
extending that to roughly a decade of match history across 19 competitions, and
adding the one field the old data never had: **the minute each goal was
scored.** Without it you know the final score and nothing about who was winning
in the 80th minute.

## What is written down here, and what each file is for

| File | What it holds |
|---|---|
| `dataset.md` | The 160-match joined dataset, its coverage, and an honest account of what is missing. Also records that Pinnacle's closing odds vanished from the 2026 data — a retraction of an earlier claim. |
| `inplay_events.md` | What the Kalshi price does after a goal, on 229 goals. Descriptive only. Contains the measured clock problem: the displayed match minute is 17.5 minutes away from real elapsed time at the median. |
| `data-sources.md` | Every data source probed, with what it does and does not carry. |
| `WHAT_IS_LEFT.md` | The 2026-08-02 session's own list of unfinished work and blockers. |
| `PAID_OPTIONS.md` | Data that costs money, and what it would buy. |
| `DECISIONS.md` | Every judgment call taken without asking, and why. |
| `HANDOFF.md` | Where the current session got to and what the next one should pick up. |

## The scripts, in the order they are used

| Script | What it does |
|---|---|
| `src/backfill_espn.py` | Walks ESPN's scoreboard week by week, 2015 → today, 19 competitions. Produces the fixture list and final scores. Resumable. |
| `src/fetch_goal_minutes.py` | Walks every one of those fixtures through ESPN's match summary and pulls **the minute of every goal and red card**, plus an absolute UTC timestamp for each. Resumable. This is the gate on everything. |
| `src/scan_tape_soccer.py` | Which soccer markets Kalshi actually quoted, and how heavily. |
| `src/build_dataset.py` | Joins ESPN matches to Kalshi markets into one row per match, with a "was this knowable before kickoff" stamp on every field. |
| `src/inplay.py`, `src/analyse_inplay.py` | The goal event study. |
| `src/teammatch.py` | Team-name matching between ESPN and Kalshi. Has its own tests. |

## Two things that will bite you

**1. ESPN blocks browser-shaped User-Agents.** Since 2026-08-08, sending
`Mozilla/...` — or any unrecognised custom string — gets a 403 from ESPN's
edge. Sending no override at all gets a 200. Every script here was patched on
2026-08-08. If a fetch starts failing, check this before anything else, and do
not "fix" it by putting a browser string back.

**2. The displayed match minute and real elapsed time are different things.**
"80'" on the clock is about 17.5 minutes earlier than 80 minutes after kickoff,
because halftime and stoppage are real time the clock does not count. Which one
is correct depends on the question:

- **Building a comeback table → use the displayed minute.** It is what a person
  watching the match sees, and "1-0 up in the 80th" means the 80th displayed
  minute.
- **Joining to a Kalshi price → use the absolute timestamp.** A minute-based
  join to a price is wrong by a quarter of an hour.

`src/fetch_goal_minutes.py` stores both on every event so neither question has
to be re-fetched.

## Which Python

`py -3`. This folder has no virtual environment of its own. `python` on PATH is
a Microsoft Store stub and will fail strangely.

```bash
py -3 soccer/src/backfill_espn.py
```
