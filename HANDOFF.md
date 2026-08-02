# HANDOFF.md — soccer data collection, 2026-08-02

Scope: **collect data.** No strategy tested, no backtester built, no model
fitted. Working directory `C:\Users\gianf\trading`, new work in `soccer/`.

Detail: [soccer/inplay_events.md](soccer/inplay_events.md),
[soccer/data-sources.md](soccer/data-sources.md),
[soccer/dataset.md](soccer/dataset.md),
[soccer/WHAT_IS_LEFT.md](soccer/WHAT_IS_LEFT.md),
[market-selection/DECISIONS.md](market-selection/DECISIONS.md).

---

## 1. THE IN-PLAY RESULT — what the price does after a goal

**130 completed fixtures, 255 events (229 goals, 26 red cards), 5 leagues,
2026-05-24 → 2026-08-02.** Zero fixtures missing an ESPN summary; zero missing
Kalshi candles.

**The scoring team's own contract, mid price in cents:**

| Offset (min) | −5 | −1 | **0** | +1 | +3 | +5 | +10 |
|---|---|---|---|---|---|---|---|
| median | 32.50 | 36.50 | **60.50** | 71.50 | 72.50 | 73.50 | 75.50 |
| median spread | 1.00 | 1.00 | **2.00** | 1.00 | 1.00 | 1.00 | 1.00 |

**Move T−1 → T+1: median +19.00¢, mean +21.75¢, positive on 94% of goals.**

**The distribution is the finding, not the mean:** p10 **+1.50¢**, p25 +9.00,
median +19.00, p75 +26.50, p90 **+43.00**, max +94.00. A goal is worth anywhere
from nothing to nearly the whole contract depending on scoreline, clock and
starting price. Quoting "a goal is worth 20¢" would be actively misleading.

**Speed:** **71.7% of the move is already in the price within the same minute**
the goal is scored, 91.3% by T+1, 95.9% by T+3, 98.3% by T+5. The spread widens
from 1¢ to 2¢ **exactly in the minute of the goal** and recovers by T+1 — the
moment of maximum movement is also the moment of maximum cost.

**Favourite vs underdog:** favourite goals move +19.75¢ (median, n=128),
underdog goals +17.50¢ (n=101). The 2¢ difference sits well inside a 19¢ standard
deviation and should not be treated as an established asymmetry.

**Red cards are SMALLER than goals here, not larger** as the tasking
anticipated: median **−2.00¢** over ten minutes on the offending team's leg,
n=26. Two reasons to distrust it as a general fact: n=22 survive to T+10, and
the offending team is typically already at ~10¢ with little room to fall.

---

## 2. WHAT DATA WAS FOUND — verified by pulling

**One free endpoint carries most of the wishlist.** ESPN `site.api.espn.com`,
no key, ~1,200 calls without a rate limit. A single `/summary` returns: timeline
with **UTC wallclock per event**, lineups with `starter` flags and **formation**,
**referee**, venue, bookmaker odds, standings, last-five form, head-to-head.

| League | ESPN teams | seasons | matches/wk (2015 → 2026) |
|---|---|---|---|
| mex.1 | 18 | 27 | 11 → 17 |
| arg.1 | 30 | 27 | 21 → 13 |
| bra.1 | 20 | 21 | 10 → 4 |
| col.1 | 20 | 22 | 15 → 9 |
| usa.1 | 30 | 31 | 10 → 18 |

**~a decade of back-catalogue per league, free.**

**Closing lines** (football-data.co.uk, League column verified, sha256 hashed):

| Code | League | Matches | Range |
|---|---|---|---|
| MEX | Liga MX | 4,673 | 2012-07-21 → 2026-07-27 |
| ARG | Liga Profesional + Copa de la Liga | 6,262 | 2012-08-03 → 2026-07-31 |
| BRA | Serie A | 5,525 | 2012-05-19 → 2026-07-31 |
| USA | MLS | 6,069 | 2012-03-10 → 2026-07-26 |

**Brazilian community dataset** (`leeofernandes1980/brasileirao-dataset`,
pushed today): 8,405 matches with **formation and coach**, 16,810 team-match
rows (shots, shots on target, possession, passes, fouls, cards, corners), 8,932
goals with minute, 18,857 cards with minute. **Ends 2023-12-06** — no 2024–26.
Formation on only 41%.

**Knowability, measured against live fixtures** — this is the important one:

| Time to kickoff | starters | formation | referee | odds |
|---|---|---|---|---|
| T−145h / −7.3h / −5.3h / −3.0h | **0** | `None` | none | present |
| **T−0.2h** | **22** | **`3-4-2-1`/`4-2-3-1`** | **`Luis Medina`** | present |

**Lineups, formations and the referee appear ~1 hour before kickoff.** After the
match the same endpoint reports who *actually played*, substitutes included —
a different fact. Deriving a "pre-match lineup" from a finished match is a
look-ahead leak of the T010 family. **A recorder was started for this.**

---

## 3. WHAT WAS NOT FOUND, AND WHAT IT RULES OUT

| Missing | Evidence | What it rules out |
|---|---|---|
| **xG / shot-level data for any shortlisted league** | Understat carries **big-5 European only**; FBref **403 Cloudflare**; StatsBomb has **2 Argentina matches and 6 MLS matches** | **The single most predictive public football statistic is unavailable.** Any model here rests on results, shots-on-target and lineups — not chance quality. |
| **Injury / suspension feed** | ESPN injuries endpoint returns **`count=0`** | No days-ahead availability signal. The lineup at T−1h is the only availability information, i.e. one hour of warning. |
| **Colombia closing line** | football-data `COL` file **is Poland's Ekstraklasa** (sha256-identical to `POL`) | KXDIMAYORGAME cannot be benchmarked cheaply at all. |
| **Pinnacle in 2026** | **0 of 139** window rows across all four leagues | See retraction R1 — the shortlist's stated benchmark does not exist for the tradeable period. |
| ClubElo for these leagues | **0 clubs** in MEX/ARG/BRA/COL/USA of 593 | No free Elo baseline. |
| API-Football, DataGolf-equivalents | 403 without a key | — |

---

## 4. DATASET COVERAGE

**160 matches**, one row each. **480 knowability assertions, 0 violations.**

| Feature | Present | % |
|---|---|---|
| ESPN identity + timeline | 160 | **100%** |
| Kalshi tickers + results | 160 | **100%** |
| In-play events with prices | 97 | 60.6% |
| Final score | 53 | 33.1% |
| Closing line (`AvgC*`) | 53 | **33.1%** |
| Pinnacle close | **0** | **0.0%** |

| League | Matches | With closing line |
|---|---|---|
| usa.1 | 52 | 28 (53.8%) |
| mex.1 | 28 | 12 (42.9%) |
| arg.1 | 43 | 13 (30.2%) |
| **col.1** | 25 | **0** |
| **bra.copa_do_brazil** | 12 | **0** |

**Only 33% of matches have all features.** Lineups, referee, H2H, standings,
form and rest days are *available* but **not yet joined onto these rows**.

---

## 5. RESULTS TABLE

| Measurement | n | Unit | Date range |
|---|---|---|---|
| Kalshi↔ESPN fixture join | 162 fixtures, **160 matched (98.8%)** | fixture | 2026-05-24 → 08-04 |
| In-play event study | **255 events** (229 goals, 26 reds) over 130 fixtures | event × scoring team's leg | 2026-05-24 → 08-02 |
| Clock divergence | 362 events | event | same |
| Kalshi vs closing line | **32** matches | match | same |
| Home advantage | 13 / 12 / 28 per league | match | same |
| Goal-time distribution | 229 goals | goal | same |
| football-data coverage | 22,529 rows indexed, 4 leagues | match | 2012 → 2026-07-31 |
| Pinnacle recency | 139 window rows | match | ≥ 2026-05-24 |
| Brasileirão dataset | 8,405 matches / 16,810 team-match stats | match | 2003-03-29 → 2023-12-06 |
| StatsBomb for our leagues | Argentina **2**, MLS **6** | match | 1981, 1997, 2023 |
| Team-matcher test suite | 34 cases (30 positive, 4 negative) | case | — |
| Pre-match recorder | 2 cycles × 10 fixtures | snapshot | 2026-08-02 17:46 → ongoing |

---

## 6. RETRACTIONS — as prominent as the findings

**R1. My own SHORTLIST.md claim is wrong for the period that matters.** It
ranked this market first partly on "free Pinnacle CLOSING odds, backfillable to
2012". Pinnacle is **0.0% populated in 2026** across MEX/ARG/BRA/USA — 100% in
2022–24, ~90% in 2025, then gone. In the Kalshi window it is present on **0 of
139** rows. **This is LEDGER T014 repeating on a different site** (T014: tennis-
data.co.uk dropped Pinnacle in 2026). The historical claim is true; the claim as
applied to the tradeable window is false. `AvgC*` (market-average close) is 100%
populated and is used instead — a consensus line, weaker than a sharp one.

**R2. The tasking's clock premise is half wrong.** "ESPN's minute stamps and
Kalshi's wall-clock timestamps are different clocks… measure the alignment
error." The *magnitude* warning is right and large: a minute-based join is off by
a **median −17.52 min** (p10 −21.8, max −29.5), wrong by >5 min on **55%** of
events. But ESPN publishes **`wallclock`**, an absolute UTC instant, on every
keyEvent (`wallclockAvailable: true`). **No mapping is needed; the alignment
error in this study is zero, not estimated.**

**R3. Red cards are not "rarer and larger".** Rarer yes (26 vs 229), larger no —
median −2¢ over ten minutes against a goal's +20¢.

**R4. My own join matched 48.8% and I nearly accepted it.** Kalshi names
Argentine clubs by region ("Racing Avellaneda", "Junin", "Rivadavia") where ESPN
uses club names. Rebuilt to resolve against each league's **closed ESPN roster**
by token overlap with an unmatched-token tie-break: **98.8% (160/162)**.

**R5. Three dead alias keys.** `vascodagama`, `defensayjusticia`,
`estudiantesdelaplata` could never fire, because normalisation strips `da`/`y`/
`de` before the alias table is consulted. Dead aliases look like coverage and
match nothing — GUARDS #1's "innocence by emptiness". A reachability check now
asserts every key is producible.

**R6. I reported ESPN Brazil as having zero matches in every year.** It was my
probe: I sampled the first week of **March**, which is Brazilian off-season.
Re-sampled in August: 10–11 matches/week back to 2015. Same artifact caused the
Argentine zeros.

**R7. I reported "StatsBomb includes Argentina Liga Profesional" as a major
find.** It is **2 matches** (River 1997, Boca 1981). I then reported StatsBomb as
having no MLS — my filter compared against lowercase `"united states"` and the
country string is `"United States of America"`. MLS is present and is **6
matches**. Both readings were wrong in opposite directions.

**R8. My knowability assertion failed 159 of 480 on its first run** — correctly.
I had stamped the closing line's `known_at` as the decision point itself, and
`known_at == decision_at` is not "known before". Sloppy stamping, not a leak;
fixed to stamp actual availability. **The guard earned its place on the first
run.**

**R9. The Brasileirão dataset's date range as I first reported it was wrong** —
I sorted `DD/MM/YYYY` as strings. True range **2003-03-29 → 2023-12-06**, which
matters because it means **no 2024–2026 coverage at all**.

**Nothing found this session revealed a larger effect than believed. Nine
corrections, all shrinking or removing a claim.**

---

## 7. CANARIES AND CONTROLS

| Guard | Ran? | Result |
|---|---|---|
| **Knowability assertion** (new) | ✅ | 480 checks, **0 violations** after catching 159 real stamping errors |
| **Selection canary** (#1) on the closing-line join | ⚠ **UNTESTABLE** | one arm empty (with=53, without=0) — the outcome and the feature come from **the same football-data row**, so there is no control arm. Needs ESPN's independent score. **Reported as UNTESTABLE, never as a pass.** |
| Dead-alias reachability (new) | ✅ | 122 keys, all reachable, after catching 3 dead |
| Team-matcher test suite | ✅ | 34 cases against real ESPN rosters, all pass |
| Join failure inspection | ✅ | all 16, then 2, residual failures printed and diagnosed, not swept |
| Content validation per row (#12) | ✅ | pre-match recorder validates event id, fetch stamp and block presence; distinguishes "empty but valid" from "fetch failed" |
| `fetched_at` stamped at fetch (CH031) | ✅ | stamped the instant the response returns |
| Wrong-country content hash | ✅ | sha256 across 14 files; COL≡POL, KOR≡NOR, CHL≡CHN re-confirmed |
| Fill at the ask, never the mid (#7) | ➖ | prices reported as mid **with the spread alongside**; no P&L computed anywhere |
| Synthetic null / positive control (#3,#4) | ❌ **not run** | no model was fitted. **Mandatory before step 5 fits anything.** |
| BH-FDR (#11) | ➖ n/a | no hypothesis tests with p-values |

---

## 8. WHAT IS RECORDING

| What | Where | Since | State |
|---|---|---|---|
| **Pre-match recorder** (NEW) — lineups, formations, referee, odds drift, 5 leagues, 10-min cycle | `soccer/data/prematch/<date>/prematch.jsonl` | 2026-08-02 17:46 UTC | alive; cycles 1–2: 10 fixtures each, **10 ok, 2 with lineups, 2 with referees, 0 failures** |
| Broad depth recorder | `market-selection/data/depth_broad/` | 06:38 UTC | alive; 98.5% non-empty. **Shortlisted soccer verified: LIGAMXGAME 876 rows, ARGPREMDIV 825, LIGAMXTOTAL 855, DIMAYOR 855, COPADOBRASIL 825 — all 100% two-sided.** KXMLSGAME 0 rows because it has **0 open markets**, not a recorder fault. Re-lists live (fixed last session). |
| pmxt L2 mirror | `market-selection/data/pmxt/` | complete | **662/662 files, 63.0 GB, bad=0** |
| Trade backfill | `market-selection/data/tape_pmxt_window/` | 07:17 UTC | **17 days complete, 23.6 GB**; 2026-06-11 finishing now — completes the whole pmxt overlap |
| Tennis depth (PID 17892), crypto 15m (PID 24756) | unchanged | 08-01 | **untouched**, alive |

Heartbeat now **logs to `market-selection/data/heartbeat.log` every 30 min and
reports only failures** — no more chat narration.

---

## 9. STILL OPEN

**Blocked on data:** xG for any shortlisted league (no free source exists);
injuries (ESPN returns `count=0`); Colombia's closing line (no file);
Pinnacle 2026 (withdrawn); Copa do Brasil closing line (cup, absent from the
Serie A file). football-data 503s after ~20 rapid downloads — needs backoff.

**Blocked on work, not data:** the selection canary (needs ESPN's independent
score — ~30 min, and it is the most important open item); joining lineups,
referee, H2H, standings, form and rest onto the 160 rows; backfilling ESPN's
decade of history; travel distance (needs geocoding).

**Two fixtures never joined** — Boyacá Chicó v Atlético Nacional (07-25) and
Chicago Fire v Vancouver (07-16). Names resolve; no ESPN fixture within ±2 days.
Likely postponements. Reported, not swept.

**Carried from before, untouched:** the v3 backtest dedupe field (CH057); the
desktop recorder `None` bug; the live bot position-sizing blowout (CH044).

---

## 10. NEXT THREE ACTIONS, by information gain per hour

1. **Close the selection canary using ESPN's score** (~30 min). It is currently
   UNTESTABLE, 33% of matches carry the closing line, and if those differ
   systematically then every comparison built on them is contaminated. This
   gates the value of everything else in the dataset.
2. **Join the already-fetched features onto the rows** — H2H, standings, form,
   rest days (~2 h). They cost nothing to add, they are the actual predictive
   content, and the dataset is presently 100% market data and ~0% football.
3. **Backfill ESPN's decade** (~3 h). 160 matches cannot fit anything. ESPN
   offers 10+ years per league free, and a form/rest/home model needs thousands
   of matches to be worth testing against the line.

---

## 11. WHAT THE COORDINATING CHAT HAS WRONG

**The Pinnacle benchmark it is counting on does not exist for 2026.** The
shortlist ranked this market first largely because a free, de-viggable, sharp
closing line was backfillable to 2012. Pinnacle is present on **0 of 139**
matches in the tradeable window across all four leagues. The usable benchmark is
a market-*average* close, which is a consensus number — a deviation from it is
much weaker evidence than a deviation from Pinnacle would have been. **This is
the second time this exact thing has happened** (T014, tennis, 2026). Assume any
"Pinnacle is available" claim is stale until re-measured.

**Kalshi already tracks the line on soccer too.** n=32, **r = 0.9593**, median
|Kalshi − de-vigged book| = **1.12¢** against a ~2.0¢ cost bar. That is a third
independent sport showing the same thing: tennis (T012), MLB moneyline (0.37¢),
now soccer. **The working hypothesis should be "Kalshi is the sharp line", and
the shortlist should be read as attempts to falsify that** — not as leads.

**"Rich domain data matters more than microstructure here" is the right
instinct and the data does not support acting on it.** There is **no free xG for
any shortlisted league** — the one statistic that would plausibly beat a
consensus line. What exists is results, form, rest, lineups at T−1h and a
referee name. That is a real feature set and it is the same one every other
participant can build. The dimension-D argument that put soccer on the shortlist
was about *quantity* of free data; measured, the *predictive* part is absent.

**The clock was never going to be the problem.** ESPN publishes an absolute UTC
wallclock on every event. The thing worth worrying about was the **team-name
join**, which silently matched 48.8% before it was fixed — and which the last
session's MLB join got wrong in exactly the same way (0 of 76). Name matching,
not clocks, is where this project loses data.

**The in-play price is fast.** 71.7% of a goal's price move is done inside the
same minute and 91.3% within one minute, while the spread doubles precisely
then. Any thought of reacting to goals needs to start from that, not from the
+19¢ headline.
