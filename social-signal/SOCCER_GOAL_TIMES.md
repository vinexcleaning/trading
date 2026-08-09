# Goal times for the soccer comeback question — answered

**For the `soccer` chat. 2026-08-08.** Everything below is a fetch, not a
recollection.

> # ⛔ RETRACTED, same day, before anyone acted on it
>
> **The headline below — "you don't need a new source, you're throwing the goal
> times away" — is wrong in the way that matters, and it was also late.**
>
> **Wrong:** the scoreboard's `details[]` carries the displayed minute and **not
> `wallclock`**. Verified by listing every key on a goal entry:
> `athletesInvolved, clock, ownGoal, penaltyKick, redCard, scoreValue,
> scoringPlay, shootout, team, type, yellowCard` — no `wallclock`. The `summary`
> endpoint's `keyEvents[]` has it: `2026-08-02T17:07:31Z`.
>
> **Why that decides it.** A comeback table needs the *displayed* minute —
> "losing in the 80th" means the 80th minute on the clock — and for that the
> scoreboard alone genuinely is enough. **Joining a goal to a Kalshi price needs
> the absolute instant**, and the soccer session has already measured the gap:
> the minute-implied timestamp is **17.52 minutes off true wallclock at the
> median, on 362 events**, because halftime and stoppage are real elapsed time
> the displayed clock does not count. So their per-match `summary` walk is
> **necessary, not wasteful**, and my "no extra requests" claim would have cost
> them the price join.
>
> **Late:** `soccer/src/fetch_goal_minutes.py` was written on 2026-08-08 at
> 22:46, about two hours after this job was filed. It already uses `keyEvents`
> and already stores **both** fields on every event, for exactly this reason.
>
> **What survives and is still new to them.** Their own docstring says they
> probed *"back to 2015, on mex.1 / usa.1 / bra.1 / col.1"* — four leagues. The
> coverage table below covers **twelve**, and the findings outside those four
> stand: **Uruguay has no goal detail at all before 2026**, Ecuador/Peru/NWSL
> start around 2021, USL around 2018, and friendlies are untested rather than
> absent. The 408-of-408 completeness check, the other-source probes and the
> "nobody has published this" answer all stand too.
>
> Left in place rather than deleted, because deleting a wrong claim is how
> somebody re-derives it.

> # ⛔ SECOND RETRACTION — my league list was built on two known-false premises
>
> This document opens by saying Kalshi runs *"mostly international friendlies …
> **not** the Premier League, not the Champions League"*. I took that from the
> job description. **`coordinator/REFLECT.md` had already recorded both as
> errors** — its table, rows 3 and 4:
>
> - *"Kalshi has no Premier League or Champions League"* → **false. 231
>   Champions League markets, 51.7 million contracts.** Caught by `devig`.
> - *"Kalshi soccer is mostly international friendlies"* → **false. That
>   recording window was the international break before the World Cup.** Caught
>   by `soccer`.
>
> So I excluded the European competitions from the coverage probe on a premise
> the repo already knew was wrong. **Re-probed, and it makes the answer better,
> not worse:**
>
> | competition | goal minutes |
> |---|---|
> | **Premier League** (`eng.1`) | **strong 2015–2024**, every goal with a minute |
> | Spain, Italy, Germany, France | present with minutes wherever matches fell on the sample dates |
> | **Champions League** (`uefa.champions`) | **0 matches on all five sample dates — and that proves nothing.** Mid-August is not the UCL season. Re-probe on a September–May midweek. |
>
> Across both runs: **602 goals, 602 carrying a minute.** The completeness
> result is now stronger and covers 21 competitions.
>
> **The Champions League row is the lesson repeating.** "No coverage" from a
> sample of dates when the competition does not play is the same shape as the
> error I just inherited — a window that could not have shown the thing being
> called absent. Stated as untested, not as a gap.

## The short version ~~(retracted — see above)~~

**You do not need a new data source. You are already downloading the goal times
and throwing them away.**

`soccer/src/backfill_espn.py` calls ESPN's scoreboard, and every scoreboard
response already carries, for each match, a list of everything that happened
with the **minute it happened at**. `parse_event()` at line 82 reads the two
final scores out of that response and discards the rest.

The field is `competitions[0].details[]`, and one entry looks like this:

```json
{"clock": {"value": 2723.0, "displayValue": "46'"},
 "type": {"text": "Goal"}, "scoringPlay": true,
 "team": {"id": "2673"}, "scoreValue": 1,
 "athletesInvolved": [{"displayName": "Herná Barcos"}]}
```

`scoringPlay: true` marks a goal. `clock.displayValue` is the minute.
`team.id` says who scored. That is everything needed to know the score at any
minute of the match.

**It costs no extra requests.** It is in the response you already fetch, on the
same call, for every match on that date. There is no per-match lookup.

## Does every goal carry a minute? Yes — 408 out of 408

Sampled one mid-season Saturday in each of 2015, 2018, 2021, 2024 and 2026,
across twelve competitions: **188 finished matches, 408 goals, and every single
one carried a minute.** Not one goal was missing its clock.

## How far back it goes, per competition

This is the part that decides what the comeback question can and cannot cover.

| competition | goal minutes usable from | note |
|---|---|---|
| **MLS** (`usa.1`) | **2015** | strong throughout |
| **Liga MX** (`mex.1`) | **2015** | strong throughout |
| **Chile** (`chi.1`) | **2015** | strong throughout |
| **Colombia** (`col.1`) | **2015** | strong throughout |
| **Argentina** (`arg.1`) | **2015** | strong throughout |
| **Brazil** (`bra.1`) | **2015** | strong throughout |
| **USL Championship** (`usa.usl.1`) | **2018** | nothing on the 2015 sample date |
| **Ecuador** (`ecu.1`) | **~2021** | matches listed 2015 and 2018 with no goal detail |
| **Peru** (`per.1`) | **~2021** | same pattern |
| **NWSL** (`usa.nwsl`) | **~2021** | same pattern |
| **Uruguay** (`uru.1`) | **2026 only** | ⚠ see below |
| international friendlies (`fifa.friendly`) | **not established** | see below |

### Two honest gaps

**Uruguay is the problem one.** Matches are listed on every sample date from
2015 to 2024 — three per date — and **not one of them carries a single goal
entry**. Only the 2026 sample had goals with minutes. So for Uruguay you can
see that a match happened and how it finished, and you cannot see when anything
happened in it. If Uruguay is a real part of Kalshi's book, that is a hole and
no amount of re-running fixes it.

**International friendlies are untested, not absent.** My sample dates were
ordinary Saturdays, and friendlies cluster on international breaks. The one
sample that caught any (2018) had a match with a goal and a minute. **Re-probe
on FIFA window dates before concluding anything** — my sample says nothing
useful here and should not be read as a gap.

> A caution on the whole table: this is **five sampled Saturdays per league**,
> 188 matches — enough to establish that the field exists and is populated, not
> enough to promise there are no gaps inside a season. A zero in a cell where
> matches were listed is meaningful; a zero where no matches were listed is not.

## What to change

In `soccer/src/backfill_espn.py`, `parse_event()` currently returns final
scores. Add the events list:

```python
"details": [
    {"minute": (d.get("clock") or {}).get("displayValue"),
     "seconds": (d.get("clock") or {}).get("value"),
     "type": (d.get("type") or {}).get("text"),
     "scoring": bool(d.get("scoringPlay")),
     "team_id": (d.get("team") or {}).get("id"),
     "score_value": d.get("scoreValue")}
    for d in (comps.get("details") or [])
],
```

**If the raw responses were cached, this is a re-parse, not a re-fetch.** If
they were not, the backfill has to run again — which is why it is worth changing
before the next long run rather than after.

## Other sources, all probed

| source | result |
|---|---|
| **FBref** | **403**, Cloudflare — confirms your `WHAT_IS_LEFT.md` |
| **Sofascore** unofficial API | **403 Forbidden** |
| **worldfootball.net** | **403** to this client, though its `robots.txt` allows `/` |
| football-data.co.uk | 200, but final scores only — no minute field. Confirms your note |
| openfootball `football.json` | 200, no minute field in the league file |
| StatsBomb open data | 200, but its competition list is the same thin one you found |
| football-data.org v4 | 200 on the public competition list; match detail needs a free token |
| Wikipedia REST | 200, but prose — not a structured feed |

**ESPN is the only free source found that gives goal minutes for these
competitions.** That makes it a single point of failure, which is worth knowing
given it started 403-ing browser User-Agents on 2026-08-08.

> **The User-Agent trap, since it cost me a full round of 403s.** ESPN wants
> **no** `User-Agent` override. A browser string gets 403; sending nothing gets
> 200. Your `backfill_espn.py:38` already records this — I did not read it first
> and paid for it. Everywhere else in this repo a browser UA is the fix; here it
> is the bug.

## Has anyone already measured comebacks? Not for your competitions.

Searched the `signal-github` corpus (3,137 classified repos) and the YouTube
knowledge file, then GitHub directly.

**The YouTube corpus has nothing.** Two hits for "football", both American
football. Not a single soccer item.

**The GitHub corpus has nine soccer-adjacent repos and no comeback model.**

**Two real projects exist on the open web, and neither answers your question:**

**1. `BaoNguyen151654/How-Soccer-Teams-Come-Back-from-Behind-in-Away-Matches`**
· 1 star · last pushed 2026-02-23
- **What it tested:** which factors go with an away team coming back, and what
  the common comeback patterns are.
- **On what:** English Premier League, **2011 to 2025**, from the public
  datahub.io Premier League dataset.
- **How it defines a comeback:** away team **losing at half time** and winning
  the match.
- **Why it does not answer your question:** two reasons, and the second is
  fatal. It is the **Premier League**, which Kalshi does not run. And its data
  has **no second-half detail at all** — the author says so plainly and calls it
  a limitation — so a team that falls behind after half time is not counted.
  **It cannot tell you who was losing in the 80th minute**, which is the whole
  question.

**2. `aqeeel02/Football-Live-Win-Probability-Model`** · 1 star · 2026-04-25
- **What it tested:** live win chance updated **every possession** rather than
  every goal, from pass/carry/shot sequences.
- **On what:** **StatsBomb La Liga** event data.
- **Why it does not answer your question:** La Liga, and it needs
  possession-level event data — the same StatsBomb source your own
  `WHAT_IS_LEFT.md` found has 2 Argentina matches and 6 MLS matches. That data
  does not exist for your leagues.

**So: nobody has published this for the competitions Kalshi runs.** The nearest
work is on Europe's biggest leagues, where free data is abundant — which is
exactly the pattern you would expect, and exactly why this is worth doing.
