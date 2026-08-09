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
| **SO006** | **The soccer selection canary is UNTESTABLE as built**, so it is not known whether matches carrying a closing line differ from those that do not. | `GUARDS #1 check_selection` | with = 53, without = 0 | one arm empty, because the outcome and the odds come from the same football-data row | **OPEN** — named **D6** in the root audit 2026-08-06, estimated ~30 min using ESPN's independent final score. Still open 2026-08-08. **Not upstream of the comeback table**, which does not select on price |
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
