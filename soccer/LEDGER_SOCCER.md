# LEDGER_SOCCER.md — claims produced by the soccer session

Same schema as [LEDGER.md](../LEDGER.md). Prefix **`SO`**.

**Why this file exists.** The `reopen` chat's audit on 2026-08-08 found that
`soccer/dataset.md`, `soccer/inplay_events.md` and `soccer/WHAT_IS_LEFT.md all
contain claims, and **none of them was in any ledger**, so none appeared in the
313 claims it audited and no cross-check in this repo could see them. This
repo's record on that is unusually blunt: ledgering a never-ledgered project has
turned up a verdict-relevant defect **three times out of three**.

**⚠ `coordinator/ledger.py` cannot see this file yet.** It reads a fixed
`SUB_LEDGERS` list and this path is not on it, so `idea.py check` will still
report soccer as having no prior work. That is a one-line change in the
coordinator's folder, which this session does not own; it is flagged in
`STATUS.md`. **Until it lands, item 2 of that audit is only half-fixed.**

Rows below 2026-08-08 were **read off existing write-ups, not recomputed**. Rows
dated 2026-08-08 were measured this session.

---

## ⚠ RETRACTED first, per the house convention

| ID | Retracted claim | Why it died |
|---|---|---|
| **SO001** | *(`market-selection/SHORTLIST.md`, carried into this folder)* "South American / Mexican soccer has free Pinnacle CLOSING odds backfillable to 2012 — Liga MX 4,437 matches, Argentina 5,928, Brazil 5,275, MLS 5,800." Ranked the family first partly on this. | Pinnacle is present on **0 of 139** rows inside the Kalshi window (≥2026-05-24). By year: 100% in 2022 falling to **0.0% in 2026** for all four leagues. The historical claim is true; the claim *where Kalshi prices exist* is false. Same failure as **T014** (tennis-data.co.uk) at a second site. `AvgCH/D/A` (market average) is used instead and is a **weaker** benchmark — a deviation from a consensus is much less interesting than a deviation from a sharp book. |
| **SO002** | *(this session, 2026-08-08, acted on for about an hour)* "ESPN serves stub bodies under concurrency, so an empty match timeline is a throttle to retry." Three retries with backoff were built on it. | The comparison behind it was broken — the fixture file was still being appended to, so the three "missing" matches used as evidence had never been requested at all. Measured properly: empty rate is **15.0% at one worker, 10.0% at four, 17.5% at eight**, so concurrency is not the cause; and **0 of 26** genuinely-empty matches recovered after four retries each. It is a real ESPN gap. See SO012. |

---

## Claims read off the 2026-08-02 write-ups

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO003** | The joined soccer dataset is **160 matches** over 5 competitions, one row each, every feature carrying a "when was this knowable" stamp. | `dataset.md`, `src/build_dataset.py` | 160 matches | **480 knowability assertions, 0 violations** — after the guard caught a real defect in the first version (159 of 480 failed on `known_at == decision_at`) | **SETTLED** |
| **SO004** | Kalshi's soccer price sits close to the consensus closing line. | `reports/kalshi_vs_book.json` | **32 matches** with both a de-vigged book price and a Kalshi mid | r = 0.9593; mean +0.47¢; **median \|gap\| 1.12¢** against a ~2.0¢ cost bar | **SUGGESTIVE** — n=32. Direction reproduces **T012** (tennis) and **M011** (MLB) on a third sport |
| **SO005** | The soccer closing line is **33% populated and structurally 0% for two competitions**. | `dataset.md` coverage table | 160 matches | closing line on 53 (33.1%); **col.1 0 of 25**, `bra.copa_do_brazil` 0 of 12 | **SETTLED** — football-data has no Colombian file (the `COL` code serves Poland, see **M017**) and cup ties are absent from the Serie A file |
| **SO006** | **The soccer selection canary is UNTESTABLE as built**, so it is not known whether matches carrying a closing line differ from those that do not. | `GUARDS #1 check_selection` | with = 53, without = 0 | one arm empty, because the outcome and the odds come from the same football-data row | **CLOSED 2026-08-09 BY DATA RETENTION, NOT BY EVIDENCE** — the question was never answered on its own terms and nothing here says the sample was clean — it rested on `data/dataset.json`, 160 matches inside Kalshi's window as of 2026-08-02. That file is gone and **cannot be rebuilt: Kalshi keeps ~69 days and those matches have fallen out of it.** The generalised question was run instead on the filters that are actually load-bearing — see **SO040/SO041** |
| **SO007** | The Kalshi price reacts to a goal, hard and fast. | `inplay_events.md`, `reports/inplay_analysis.txt` | **229 goals** from 130 fixtures | scorer's own leg moves median **+19.00¢** (mean +21.75, sd 19.08), up on **94%**; **~72% of the move is in within the same minute**, 91% within one | **SETTLED** (descriptive) |
| **SO008** | **Red cards move the price much LESS than goals**, not more. | same | **26 red cards**, 22 surviving to T+10 | median **−2.00¢** over ten minutes vs a goal's +20¢ | **UNVERIFIED** — n=26, mean and median diverge sharply, and the offending team is usually already at ~10¢ where there is little room to fall |
| **SO009** | The displayed match minute is **not** real elapsed time, by a large and measured margin. | `reports/inplay_analysis.txt` | **362 events** carrying both | median error **−17.52 min**; \|error\| > 5 min on **55.2%** | **SETTLED** — and see SO013, which says what it does and does not apply to |
| **SO010** | The scoring team's price drifts **+4¢ from T−5 to T−1**, before the goal. | `inplay_events.md` | 229 goals | 32.50¢ → 36.50¢ | **REFUTED AS A SIGNAL by its own author.** The sample is conditioned on having scored. A control sample of non-scoring team-minutes was never built. Do not read it as anticipation |
| **SO011** | A results-and-form model **loses to the bookmakers** on soccer. | `reports/model_vs_market.txt` | **2,875 test matches** (train <2024, test 2024+) | model Brier worse by **+0.02170 [+0.01626, +0.02750]** — entirely the wrong side of zero. Positive control (peeking) −0.60419, so the test can detect a large improvement | **SETTLED** — reproduces the tennis Stage 0–5 result on a second sport |

---

## Measured this session, 2026-08-08

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO012** | **ESPN has no play-by-play at all for some fixtures, and the gap clusters by competition.** | `src/fetch_goal_minutes.py`, `reports/goal_minutes_coverage.txt` | 26 empty matches retried 4× each; empty-rate trials at 1/4/8 workers | **0 of 26 ever recovered.** Rate 15.0% / 10.0% / 17.5% — flat in concurrency. Of 26: Uruguay 13, Ecuador 7, Peru 2, Copa do Brasil 2, friendlies 2, **and zero in mex.1 / arg.1 / bra.1 / col.1 / usa.1** | **SETTLED** — this is an uneven coverage loss across **Kalshi-bettable** leagues and is reported per competition, not hidden. Retracts SO002 |
| **SO013** | The 17.5-minute clock error (SO009) **applies to price joins and not to a comeback table**. | `soccer/DECISIONS.md`, `src/fetch_goal_minutes.py` | — | "the 80th minute" is a statement about the clock on the screen, which IS the displayed minute; converting it to elapsed time would be the error. Both keys are stored on every event | **SETTLED** (definitional) — recorded because the tasking asserted the opposite and it is the kind of thing that gets silently reversed |
| **SO014** | **ESPN's edge blocks browser-shaped User-Agents.** | `soccer/DECISIONS.md`, 8 patched scripts | 6 User-Agent strings, same URL, same minute | `Mozilla/5.0 (soccer-research/1.0)` **403**, Chrome/126 **403**, bare `Mozilla/5.0` **403**, `soccer-research/1.0` **403**, `curl/8.4.0` **200**, requests' default **200** | **SETTLED** — every ESPN script in this folder was dead, not degraded. `mlb/` and `market-selection/` also fetch from ESPN |
| **SO015** | **Kalshi lists 20 per-match soccer series, including the Premier League and the Champions League.** | `soccer/kalshi_soccer_series.md` | 20 series with settled events; 8 further tickers tried and empty | Both repo documents undercounted: `dataset.md` said 5 competitions, `tape_soccer_scan.json` said 10, and **neither mentioned any European league** | **SETTLED for existence, SAYS NOTHING ABOUT LIQUIDITY** — which is the distinction **B024** turns on entirely |
| **SO016** | The "**Kalshi soccer is mostly international friendlies**" reading of `tape_soccer_scan.json` (139 of 210 tickers) **is a calendar artifact**. | `soccer/kalshi_soccer_series.md` | scan window 2026-05-24 → 06-11 | that fortnight is the international break before the 2026 World Cup. The friendly series' last settled event is **26JUN11**, while ten club competitions carry settled events dated **August 2026** | **SETTLED** |
| **SO017** | ESPN carries goal minutes **and** absolute timestamps **back to 2015** for these competitions. | probes on mex.1 2015, usa.1 2016, bra.1 2019, col.1 2022 | 4 leagues × 1 match each | every goal carried both a displayed minute and a wallclock | **SUGGESTIVE** — 4 probes. Superseded by the full-run coverage report when it lands |
| **SO018** | The comeback replay reproduces football's own base rates. | `src/build_comeback_table.py` §6 | **472 matches** (validation sample) | home wins **46.8%**, draws **27.5%**, away **25.6%** | **SUGGESTIVE** — a sanity benchmark on a sample, re-run on the full data |

---

## The comeback table itself, 2026-08-09

**Every row below is DESCRIPTIVE and none of it is a finding.** It is built on
2015-01-01 → 2024-12-31. Everything from 2025-01-01 is held back and has not
been looked at. `PREREGISTRATION_COMEBACK.md` was committed **before** any of
these numbers existed — check the git log, and if it was not, disregard it.

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO019** | **How often the team that is behind comes back and wins, one goal down.** | `reports/comeback_table.txt` §1 | **56,173 matches**, 23 competitions, 2015–2024. Unit = the match | minute 45 **9.9 per 100** · 60 6.6 · 70 4.1 · 75 2.9 · **80 1.8** · 85 1.0 · 88 0.5 · 89 0.4 | **DESCRIPTIVE** — the same matches recur at every minute, so the columns are one sample seen repeatedly, not independent ones |
| **SO020** | **The exact scoreline is not the same as the goal gap.** | §2 | 80th minute | **1-0: 1.7** [1.5–2.0] on 13,662 · **2-1: 1.8** [1.5–2.1] on 7,980 · **3-2: 2.8** [2.1–3.7] on 1,507 · **2-0: 0.1** on 7,242 | **DESCRIPTIVE** — 3-2 is roughly 17× 2-0 at the same minute and the same "two goals of scoring already done" |
| **SO021** | **How good the two sides are moves the number by about 2.5×, and the direction is the user's.** | §3 | 70th minute, 1-0, 13,000+ matches across the grid | leader top third vs trailer **bottom** third **2.8 per 100**; leader **bottom** third vs trailer top third **7.1 per 100**. Monotonic in both directions | **DESCRIPTIVE, and it is the pre-stated hypothesis** — the user named this shape before any data was collected, which is the one thing here not chosen after seeing the numbers |
| **SO022** | The strength effect **shrinks as the clock runs down**. | §3 | minutes 70 / 80 / 85 | worst-vs-best cell: **7.1 → 2.3 → 0.7** per 100; best cell 2.8 → 1.0 → 0.4 | **DESCRIPTIVE** — by the 85th minute the strength dimension is nearly gone, because there is no time left for it to act through |
| **SO023** | **The replay reproduces football's own base rates**, which is the check that it is not lying. | §6 | 56,173 matches | home wins **45.8%**, draws **26.0%**, away **28.3%** | **SETTLED** as a sanity benchmark |
| **SO024** | **ESPN's timeline coverage is severely uneven across Kalshi-bettable leagues.** | `reports/goal_minutes_coverage.txt` | 75,016 fixtures attempted, **58,109** with a timeline | **uru.1 99.0% lost** (30 usable of ~3,300) · bra.copa_do_brazil 49.0% · ecu.1 49.4% · per.1 38.6% · usa.nwsl 27.8% · fifa.friendly 14.1% · **0.0–0.1% for mex.1, usa.1, bra.1, arg.1, col.1, chi.1, eng.1, esp.1, ita.1, ger.1, uefa.champions, usa.usl.1** | **SETTLED** — Uruguay is effectively absent from this table and Kalshi lists it. Extends SO012 to the full sample |
| **SO025** | The replayed timeline reproduces the final score per team on **99.4%** of matches. | same | 58,109 matches | 327 dropped for disagreeing, 5 for an unreadable minute, 29 for a goal credited to neither side; 140 knockout ties where extra time changed the score, scored on the regulation result | **SETTLED** |

## The price, 2026-08-09 — and it closes the question

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO026** | **The 97-cent price the whole idea rests on does not exist late in a match.** | `reports/price_vs_rate.txt` §1, `src/price_at_state.py` | **149 priced moments** at the 70th minute or later, read at the exact wallclock of a goal + 2 min, paying the ask | **79.2% of the time nobody is bidding on the losing side at all**, so there is nothing to buy below 100. 99c on 11.4%, 98c on 4.7%, **97c or less on 4.7% — 7 moments of 149** | **SETTLED** — this does not depend on the rate table at all, and it is the answer |
| **SO027** | At the price actually charged, **every state loses money.** | `reports/price_vs_rate.txt` §2 | 29 state-bands with ≥5 priced moments | **29 of 29 lose.** e.g. 70–79 min 1-0: pay 99c, survives 0.93 per 100, actually 2.83. 10–19 min 1-0: pay 86c, survives 12.68, actually 15.48 | **SUGGESTIVE, directional only** — the rates are 2015–2024 all competitions and the prices are a few hundred moments from a 69-day window. Different populations, deliberately not averaged |
| **SO028** | **The mechanism: the cheap price and the safe scoreline never co-occur.** | `reports/price_vs_rate.txt` §3 | the 7 late moments at ≤97c | 4 are **2-1**, 2 are **3-2**, 1 is 1-0 — i.e. the scorelines with the *highest* comeback rates (3-2 at the 80th is 2.8 per 100 against 1-0's 1.7). Where the rate is genuinely 1.7, the price is 99 or there is no market | **SETTLED as a mechanism** — the market charges less exactly where the risk is greater, which is what a working market does. n=7 is small; the 79.2%-no-market figure is what carries the conclusion |

## Measured 2026-08-09, second session — every minute, and the price at each

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO029** | **Any displayed minute can be placed on the real clock to within seconds**, which is what makes a price readable at a minute when nothing happened. | `src/clock_map.py`, `reports/clock_map_accuracy.txt` | **24,159 anchors** leave-one-out, 1,037 matches | median error **0.13 min**, **98.8% inside 1 min**, 99-in-100 inside 1.12 | **SETTLED** — does NOT contradict SO009, which measured `kickoff + displayed minute` (median 17.52 min out). Different method: this never crosses halftime |
| **SO030** | **Comebacks late in a one-goal match became MORE common after 2022.** | `src/era_split.py`, `reports/era_split.txt` | 2015-2018 vs 2022-2024, thousands of matches per cell | 80th minute **1.3 → 2.3 per 100**, ranges do not overlap. Same at 75th, 85th, 89th. **Nothing changed between the 15th and 65th.** 34 of 38 comparisons overlap; the 4 that do not are all one-goal-up late and all move the same way | **SUGGESTIVE, and it moves a headline** — five substitutes became permanent in 2022, which fits the pattern being late-only. Not a designed test of that, so the mechanism is a hypothesis and the shift is the measurement |
| **SO031** | **The earlier "four times in five there is no market" was a LATE-MATCH fact, not a general one.** | `src/price_by_minute.py`, `reports/gap_table.txt` §1 | **19,460 minute-readings**, 218 matches, every minute 1-90 | a market existed **83 in 100 at the 25th minute** and **30 in 100 at the 85th**, 9 in 100 at the 89th. Priced at 97c or less: **71 in 100 at the 25th**, 4 in 100 at the 85th | **SETTLED** — narrows SO026. Liquidity runs OPPOSITE to where the original idea looked |
| **SO032** | **The price is worse than the football says at essentially every minute.** | `reports/gap_table.txt` §4 | 4,848 readings matched to their OWN competition's 2022-2024 rate, restricted to where the two are within 10c | middle **−0.84c per contract**, average −1.15c. Worst early: ≈−8c at the 10th minute, −1.6c at the 25th. Approaches zero by the 70th-85th | **SUGGESTIVE** — two populations (rates 2022-2024 all competitions; prices a 69-day 2026 window). Not a profit measurement |
| **SO033** | **⚠ Comparing an average historical rate to a specific match's price cannot find edge, and the largest apparent edges are all this artifact.** | `reports/gap_table.txt` §4 | top 8 readings by apparent edge | all are a superpower a goal down early in a friendly — e.g. paying **27c** to bet against a side the market had at **73%** to win. The market knows the teams; the rate knows only the competition and a coarse strength band | **SETTLED as a limit of the method.** This is the reason the mean (+0.96c) and the middle (−0.84c) disagreed in sign before trimming |
| **SO034** | **Whether the market over-reacts to a weak team's goal cannot be answered in this window.** | `src/overreaction.py`, `reports/overreaction.txt` | goals opening the scoring, 20th-35th min, with a **tradeable** price | **8 to 18 goals per strength group.** Result column swings −16c to +16c across four groups | **UNTESTABLE HERE** — the football half is solid (top-third side going one up wins **72.6 in 100** on 1,562 matches; bottom-third **59.6 in 100** on 944). Only the price is missing |
| **SO035** | *(this session, caught by the Critic before it was written up)* "The price sample contains no European league at all." | — | — | **False as stated.** Kalshi had **66 settled Champions League events inside the candle window** on 2026-08-09. They were missed because ESPN files qualifying rounds under `uefa.champions_qual`, and `uefa.champions` returns **0** fixtures for 1 Jul – 8 Aug while `uefa.champions_qual` returns exactly **66**. `uefa.europa_qual` has 43 more | **RETRACTED BEFORE PUBLICATION** — the fourth absence claim in this repo's history and the fourth to be wrong. `coordinator/reflect.py` flagged the wording; the check was then done by hand |

**Kalshi's European per-game books ARE settled and listed**: `KXEPLGAME` 200 settled events (last 2026-05-24), `KXLALIGAGAME` 200 (last 2026-05-24), `KXUCLGAME` 200 (last **2026-08-05**). The Premier League and La Liga have **zero** inside the ~69-day candle window because their season ended before it opened; the Champions League has 66 because qualifying runs through July and August.

## The full-match answer, 2026-08-09 — every minute, with the European book in it

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO036** | **The market is there EARLY and gone LATE**, which is the opposite of where the original idea looked. | `reports/gap_table.txt` §1 | **30,648 minute-readings, 645 matches**, every minute 1-90 | somebody bidding on the losing side: **93 in 100 at the 10th–15th minute**, 92 at the 25th, 74 at the 60th, 47 at the 80th, **16 at the 89th**. Priced ≤97c: **83 in 100 at the 10th**, 19 at the 80th, **1 at the 89th** | **SETTLED** — supersedes SO026/SO031. Monotone decline across 17 sampled minutes |
| **SO037** | **The price is worse than the football says, and it is worst early where the market actually is.** | `reports/gap_table.txt` §4 | 15,216 readings matched to their OWN competition's 2022-2024 cell | overall middle **−0.40c per contract**. Stable across bars: −0.46c at 40 matches, −0.40c at 60, −0.48c at 100, −1.23c at 200 | **SUGGESTIVE** — two populations (rates 2022-2024; prices a 69-day 2026 window). Not a profit measurement and not a realised outcome |
| **SO038** | ~~"The deepest European book is among the WORST priced" — **second worst of eleven**.~~ **Rewritten 2026-08-11 after the `reopen` audit.** The claim that stands: **the European book was sought out specifically because it was the expected improvement, and it did not deliver one.** | `reports/gap_table.txt` §4 | **63 Champions League qualifying matches**, 2,546 readings, 1,016 compared | **−2.61c per contract.** A market existed 66 in 100; ≤97c on 47 in 100 | **SUGGESTIVE, AND EXPLICITLY NOT NOMINATED** — see the note below. Also **qualifying, not the group stage**, and it does not settle the group stage |
| **SO039** | Three competitions look positive and **none should be read as a finding**. | `reports/gap_table.txt` §4 | 11 competitions with enough history | NWSL **+1.86c**, Liga MX **+0.93c**, USL **+0.24c** | **EXPLICITLY NOT NOMINATED** — best three of eleven is the exact shape that looks good by chance, and NWSL rests on 696 matches of history against Liga MX's 3,289. Recorded so nobody re-derives them later as a discovery |

**Three separate defects were each hiding the European book, and each reported it as "no fixture" — indistinguishable in the output from Kalshi not listing the competition.** (1) ESPN files qualifying under `uefa.champions_qual`, not `uefa.champions`. (2) Exact-name joining matched 6 of 66 — Kalshi's "Kairat" against ESPN's "Kairat Almaty". (3) A required `kickoff` field that **53 of 66** Champions League qualifying matches simply do not carry. Fixed in that order; the sample went 12 → 39 → 63 matches. **The lesson is the failure mode, not the fix:** a filter that drops data silently produces an absence claim, and this folder has now produced four.

## The selection canary, 2026-08-09 — and it names why the idea fails

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO040** | **Whether a match got priced at all cannot be checked against the outcome.** | `src/selection_canary.py`, `reports/selection_canary.txt` | **528 in-window matches** with somebody ahead at the 70th minute: 429 priced, **99 not** | comeback rate **3.5 per 100 priced vs 2.0 unpriced**, z=+0.88, **MDE 4.69pp against a 2.0pp gap** → **UNTESTABLE** | **UNTESTABLE, and that is the answer.** Same verdict as SO006 for the same reason — not enough matches in the smaller arm. Not evidence of a clean sample and not evidence of a dirty one |
| **SO041** | **⚠ Kalshi stops quoting the losing side exactly when the match becomes near-certain — which is the state the whole idea wanted to buy.** | same | **one reading per match**, so the unit is the match, not the minute | at the 60th minute: **7.1 per 100 came back where you could bet, 0.0 where you could not.** 70th: 5.7 vs 0.0. 80th: 4.0 vs 0.4. 85th: 2.6 vs 0.0. Minute-level: 9.2 vs 0.1 on 19,900 vs 8,053 readings, z=+43 (inflated by the unit; the match-level table is the one to read) | **SETTLED — the mechanism.** Predicted in the file header before it was run |

**This is the sharpest statement of why the idea fails, and it is better than the price comparison.** The bet was *"pay about 97 cents for something almost certain"*. **The market does not quote almost-certain.** Every price that exists is a price on a match still in doubt — where the team behind comes back about 9 times in 100, not the 1 or 2 the idea was aimed at. The trade is not mispriced; it is absent, and it is absent by construction.

**So the −0.40c headline is conditional and must be stated that way:** *you overpay by about 0.4 cents a contract in the games and minutes where a trade was actually available.* SO037 is amended to carry that condition.

## The post-mortem probe, 2026-08-11 — does it transfer?

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **SO042** | **The near-certainty gap appears in every sport Kalshi runs per-game**, so it is market-maker behaviour rather than anything about soccer's three-way market. | `src/other_sports_probe.py`, `reports/other_sports_probe.txt` | **284 settled markets**, 7 sports, one-minute candles in the 5 h before close, measured 2026-08-11 | buyable when somebody bids 95c+: soccer **29 in 100**, women's basketball 31, basketball 37, hockey 51, baseball 53, men's tennis 56, women's tennis **67**. **Control at 40–70c: 100 in 100 in every sport, all 33,802 minutes** | **SETTLED for availability only.** The perfect control rules out thin books; six sports have no draw leg, killing the soccer-specific explanation. **Says nothing about price quality.** No event state — a 95c price may be a heavy pre-match favourite rather than a late near-certainty |

**Soccer was the worst of the eight rows to have tried this in, and tennis the
best** — quotes survive roughly twice as far into a near-certain state there.
That is a lead for `tennis`, **not a recommendation**: availability is necessary
and not sufficient, and soccer's book was a clean 100 in 100 early in a match
with a bad price anyway.

### ⚠ SO038 was a lapse and the `reopen` audit was right to call it

**The rule was applied to the positive tail and not the negative one.** SO039
refuses to nominate the best three of eleven competitions on the grounds that
best-of-eleven is exactly what chance produces. **Second-worst-of-eleven is the
same shape**, and it went through unchallenged — **precisely because it agreed
with the conclusion**, which is the direction bias runs in and is the harder one
to notice. Recorded rather than quietly fixed.

**One thing does survive the criticism, and it is not the ranking.** The European
book was not found by scanning eleven competitions and reading off the extreme.
It was **sought out deliberately, on the stated expectation that a deeper book
would price better**, and three defects were fixed to get it. **A pre-specified
expectation that fails is evidence; a rank order pulled from a table is not.**
So the claim is now *"the improvement that was expected did not appear"*, and
the words "second worst of eleven" are withdrawn.

**Neither version changes the verdict**, which rests on SO041 and the
availability figures, not on any competition's position in a table.

### ⚠ SO026–SO028 are narrower than first reported, and this was found after reporting

**Every price in `price_at_state.py` is read at a goal's wallclock plus two
minutes.** So all 149 "late" moments are matches where the goal itself happened
at minute 68 or later. **The ordinary case the idea is about — 1-0 since the 20th
minute, now the 80th, nothing having happened for an hour — is almost entirely
absent from the price sample.**

A book two minutes after a late goal is not the same book as one that has sat on
a scoreline for an hour, and which way it cuts is **not known**: an hour of quiet
could settle the price further into 99/100, or could give market makers time to
post resting offers at 97–98 that do not exist right after a goal. Both are
plausible. Neither was measured.

**The honest form of SO026 is therefore:** *right after a late goal, the
97-cent trade is available 7 times in 149. In a settled late scoreline,
unmeasured.* SO027 and SO028 inherit the same restriction.

Fixing it needs no new download — the same 69-day Kalshi candle window answers
it by sampling a fixed displayed minute regardless of when the last goal fell.
It is job #1 in `HANDOFF.md`.

**Verdict on the idea: NO for the states measured, and UNMEASURED for the
states the idea is actually about.** Not "too small to tell" and not "needs more data" —
the assumed price is absent in the states that matter. **The pre-registered test
was never run**, because its premise did not survive contact with the order book.
`PREREGISTRATION_COMEBACK.md` stands unused and the held-out years 2025–2026
remain unopened, which is the correct outcome and leaves them clean for a
different question.

**This is B024 happening a third time** (after B024 itself and K015/W011): a
number that is real on the football and gone at the price you can trade. It cost
one session rather than a project, because the price was measured before anything
was built on it.

### ⚠ What SO019–SO022 do NOT say, and the trap sitting right next to them

**1.8 comebacks per 100 at the 80th minute is below the 2.80 that a 97-cent
price needs. That is NOT an edge and must not be quoted as one.** Two reasons,
and the second is the one that kills things in this repo:

- **The 97 cents is the user's assumption, not a measurement.** Nothing above
  contains a Kalshi price. `src/price_at_state.py` is measuring the real one.
- **B024 is exactly this shape.** A signal that was real on the middle of the
  market and **gone at the price you could actually trade** — net −0.77¢ at the
  ask. If the real price in this state is 98 cents rather than 97, the bar moves
  to 1.86 per 100 and the gap closes on its own.

The pairing of a rate with a price is the test, it is pre-registered, and it runs
on the held-out years — not on anything in this table.
