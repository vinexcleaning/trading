<!-- COORDINATOR-STATE
doing: coordinating with the factory chat over widening the Kalshi recorder - the measurements it needs are in STATUS.md; and watching whether the sharp bookmaker ever quotes strikeout prices, which gates the whole props idea
left: the props kill-test finishes on its own in 48 hours and answers, for free, whether there is any window to trade in; P1 itself is pre-registered and not started
needs: no
-->

# HANDOFF.md — bot-hunt, session of 2026-08-04

Desktop `C:\Users\vinig`. Ran autonomously. Every call public, unauthenticated,
read-only; no order endpoint exists in this folder's code by construction.

---

## 0. READ FIRST — two things that change what the next session should do

**1. `market-selection/` already did Step 2, on 2026-08-02.** Full 24 h
exchange-wide tape, 8,867,978 trades, 2,205 series, pre-registered kill gate.
It is referenced nowhere in `STATUS.md`'s thread tables. This session extended
it rather than re-deriving it.

**2. Its #1 entry is dead, and the kill is on an axis it never measured.**
South American / Mexican soccer was ranked first on *40–101 settlements per
week*. That is a rate. The **retrievable** settled events total **152 across all
five series** against LEDGER K014's bar of 481. See §2.

---

## 1. What is running RIGHT NOW — do not kill it

| what | started | writes |
|---|---|---|
| `src/record.py` (10-min cycles) | 2026-08-04 21:27 UTC · **restarted 08-06 00:23 UTC** to add `k_names` | `bot-hunt/data/record.db` |
| `src/pull_l2.py --since 2026-06-01 --until 2026-06-04` | **2026-08-05 20:08 UTC**, 96 files | `bot-hunt/data/l2/` |
| ~~`pull_kalshi_soccer.py`~~ | finished | `bot-hunt/data/kalshi_soccer.db` |
| ~~`pull_l2.py 05-30..05-31`~~ | finished, 47 files | `bot-hunt/data/l2/` |

The recorder is the only asset here that accrues in wall-clock time and cannot
be recovered later. Pinnacle, the Kalshi book and the Polymarket touch are all
**live-only**. Check health with:

```bash
C:\Users\vinig\trading\bot-hunt\.venv\Scripts\python.exe C:\Users\vinig\trading\bot-hunt\src\rec_status.py
```

---

## 2. The findings, in order of how much they change

### 2a. Pinnacle's guest API is free, and almost nobody uses it

`guest.api.arcadia.pinnacle.com` returns live priced markets unauthenticated:
**27,582** priced soccer markets, **3,728** tennis (incl. period-1 handicaps),
**1,920** baseball, **643 esports**, each with `maxRiskStake` limits.

Only **3 of 3,195** cached whole-repo archives in `signal-github` reference that
endpoint, against 129 using the keyed `the-odds-api`.

It is the fair-value input for the only strategy in any corpus attached to this
repo with a **public wallet and a reconciled four-line P&L** — Polymarket
esports, passive-only, de-vig sharp odds and quote them: **+$8,293 arbitrage,
−$3,184 unhedged residual, −$134 cancellations, +$4,973 net**, 3,858 fills,
$96k volume. **The author switched it off** as the win rate went 50.2 → 48.3 →
43.4% monthly.

> **The single most useful number found this session: adverse selection cost
> that author 38% of gross.** It is the term that appears in no fee model
> anywhere in this repo, and it is the exact mechanism S008/S009 found fatal on
> tennis. `signal-github` concluded maker-only quoting wins on fees; a 20-year
> professional in the YouTube corpus says be a taker. **Both are right, and
> 38% is the size of the missing term.**

### 2b. Dimension E, measured on retrievable events, re-ranks everything

LEDGER K014: **481** settled events for a 5 pp edge, **2,084** for a 2.4¢ bar.

| family | retrievable **events** | vs 481 |
|---|---|---|
| KXITFMATCH / KXITFWMATCH | 8,000 / 7,636 | 16.6× / 15.9× |
| KXCS2GAME | 1,648 | 3.43× |
| KXWTAMATCH / KXATPMATCH | 974 / 942 | 2.0× / 2.0× |
| KXMLBGAME / KXMLBRFI | 907 / 905 | 1.9× |
| **all 5 S. American soccer series** | **152** | **0.32×** |

**No entry has all five dimensions AND a runnable historical test:**

- **esports** has the only existence proof and **no historical reference price**
  (all five free esports sources dead: 404/403/402/403/404) → forward-test only.
- **tennis ITF** has 36× the sample and **no reference price at all**.
- **tennis ATP/WTA** has the reference — but that test is **already done**
  (T012, r 0.9878, MAD 1.95¢ vs a 2.44¢ bar. Null).
- **soccer** has 14 years of free Pinnacle closes and **152 matches**.

### 2c. Kalshi's retention is a fixed calendar boundary, not a rolling window

Four independent queries — `status=settled`, `min_close_ts` at −365 days, no
status filter, and a window placed entirely before the boundary — all return the
same earliest `close_time`, and **13 of 18 unrelated families share the identical
date 2026-05-25**.

⚠ **`market-selection/WHAT_IS_LEFT.md` calls this "THE DECAYING ITEM", 69 days
rolling one day per day, gone by 2026-08-19.** It bisected to 2026-05-25 on
08-02; I bisect to 2026-05-25 on 08-04 — the window **grew** to 71 days. Two
points is not enough to overturn it. It is enough to stop treating the deadline
as established. **Re-bisect before acting on it.**

Also new: the **market listing** and the **trade tape** have the same boundary,
and the listing is the binding one because it supplies the result label.

### 2d. The engine is validated, and one of its guards caught my own bug

`src/engine.py` imports `common/kalshi_fees.py` (never reimplements it) and
deliberately does **not** adopt `evan-kolberg`'s fill model, which says makers
pay 0 in its instrument metadata and charges them 0.07 in its fee model.

`src/validate_engine.py` — **5 of 5 pass**: martingale check on the generator
itself, null control, 5 pp positive control, 1 pp sensitivity floor, and a
deliberate mid-price leak that must light up (it lifts the result by +0.32¢,
which is half the quoted spread — exactly what T008 recovered by marking at
the mid).

### 2e. The leak canary reproduced T010/T011 on a different sport

On esports, at a **−0h** anchor: **23.62% of quotes are extreme (≤2¢ or ≥98¢)
and 100% of them are correct.** At **−60 min** and **−6 h**: **0% extreme.**

That is the T010/T011 signature exactly, found independently on a sport that
work never touched. It validates the −60 min anchor and is an independent
reproduction of a repo finding.

---

## 3. ⚠ Three corrections, recorded rather than buried

**C1 — my recorder produced a FALSE KILL on the best lead.** Cycle 1 queried
Polymarket with `tag_slug=esports` and read 11 quoted tokens of 95, **0%
two-sided** — which kills the family on dimension A. It was the probe: that slug
ordered by 24 h volume returns mostly `acceptingOrders=false` events (96 of 156).
Per-game slugs at the same minute: `dota-2` **51 of 60 two-sided**, top market
**$51,029/24 h at a 1.0¢ spread with 2,458 × 4,068 at the touch**.

> **Third occurrence of this failure mode in this repo** (`market-selection`'s
> stale-ticker bug produced 19 wrong kills; `killed.md` opens with its own
> correction of the same shape). **A dimension-A probe that samples the wrong
> markets fails silently and always in the direction of a kill.** Worth a
> `GUARDS.md` row.

**C2 — my own validation FAILED on a bad pass condition, not a bad engine.**
L1 read −2.4756¢ against −2.2172¢ expected and I had asserted a fixed 0.25¢
tolerance. The bootstrap SE at n=4,000 is **0.66¢**, so that gap is z ≈ −0.4.
The threshold was tighter than the noise. Replaced with a statistical condition
(the cost-only expectation must lie inside the bootstrap CI). A fixed threshold
on a sampling distribution is the error GUARDS #8 exists to prevent.

**C3 — my negative-control gate read ABSENT as CLEAN.** v1 of `run_grid.py` did
`ctl.get("n_survive_positive", 0)`, so a control family with **no data at all**
returned 0 and printed *"control clean → results are reportable"*. Fixed to
three-valued: an absent control is **UNTESTABLE**, which is not a pass, and the
run now refuses to report. Same class as the bug that once reported 358 repos
scored when 92 had real data.

---

## 3b. ✅ SUPERSEDED — Step 6 is now COMPLETE. Read [RESULTS.md](RESULTS.md).

Everything in §4 and §5 below describes the *first, non-reportable* run and is
kept because it records how the control gate caught itself. **The finished run
is in [RESULTS.md](RESULTS.md).** In one line:

**0 of 260 cells survive BH-FDR with a CI above zero (test: 2,779 esports
events); 0 of 148 on the MLB control; every survivor is significantly negative;
the holdout is untouched because nothing qualified.**

Two things happened on the way that matter more than the null:

1. **The leak gate voided my pre-registered −60 min anchor** (13.96% extreme,
   99.7% correct). `close_time` is when the market SETTLES, not when the match
   starts. Fixed by measurement in **Amendment A1**, committed before re-running.
2. **Dimension C is measured at a moment a pre-match strategy cannot trade.**
   Over all settled markets, CS2's p90 spread goes **12¢ → 69¢** between 15
   minutes and 24 hours and its mean triples. Esports' real pre-match cost is
   **3–6× the figure the shortlist ranked it on**. MLB is 1.0¢ at every lead.

**The single next thing is now H10**, which is newly runnable — see §5.

---

## 4. Step 6, FIRST RUN (superseded): RUN, NOT REPORTABLE

`src/run_grid.py` executes the pre-registered grid. On the data available at
session end:

| | |
|---|---|
| events with a usable candle panel | 271 (of ~2,867 target) |
| selection canary | **UNTESTABLE** — MDE 5.95pp > 2.0pp at n=271. Correctly not rendered as PASS. |
| leak canary | **PASS** — see §2e |
| cells swept | 92 |
| BH-FDR q=0.10 survivors with CI > 0 | **0** |
| **negative-control gate** | **UNTESTABLE — control family has 0 events with candles** |

**So no number from this run is reportable as a finding**, and the gate says so
itself. The candle pull was still running at session end (600 of 3,301 CS2
markets).

Preliminary and non-reportable, but worth knowing: every cell is negative or
straddles zero, and the random-side control `H0-RANDOM` sits at **−6.3¢ to
−9.9¢**, far wider than the ~2.2¢ cost bar measured at the touch during live
play. **If that holds, esports pre-match spreads hours before an event are much
wider than the 1.0¢ measured at the touch** — which would matter, because every
shortlist entry's cost estimate came from touch measurements.

---

## 4b. ✅ H10 IS DONE. Read [RESULTS_H10.md](RESULTS_H10.md).

Section 5 below was the build plan and is kept as a record; **it has been
executed.** 47 hourly files, ~13M L2 rows, 12,959 simulated resting orders,
81 events.

**One number from H10 is a measurement: the fill rate, 29–36% strict /
63–69% permissive, corroborated three independent ways.** Fill rate is *not*
the constraint on maker strategies here — the pre-registered <20% falsification
fails.

Everything else is noise or worse: net P&L **sign-flips** across nested
prefixes (−1.48 … +2.55¢), adverse selection **decays toward zero** as data is
added (−14.04 → −4.03pp — the artifact signature), and the one quantity that
*strengthens* with n is flagged by **GUARDS #10** as a contamination warning,
not a finding.

**Items 1 and 2 below are DONE — see [RESULTS_CROSSVENUE.md](RESULTS_CROSSVENUE.md)
and §4c. The live list starts at 3.**

1. ~~Contamination check on the "monopoly regime" effect.~~ **DONE.** Not
   killed, not confirmed: within-event keeps 74% of the effect (so it is *not*
   a between-event artifact) but the CI spans zero at 75 events, and a placebo
   split on the parity of the placement minute produces **45% of the claimed
   effect** — the estimator's noise floor. Stays a lead.
2. ~~More events.~~ **RUNNING** — 96 files, 2026-06-01..06-04.
3. **Re-run everything once the pull lands.** `src/h10_stability.py` and
   `src/contamination_check.py` both take the binding constraint (81 events) up
   by roughly 4×. **If net P&L still sign-flips and adverse selection still
   decays, H10 closes as underpowered rather than negative** — and that is a
   legitimate closing state, not a failure.
4. **Join the Polymarket leg.** 436 slugs are recorded and unjoined, and
   Polymarket is where the reconciled live P&L actually came from. Kalshi is
   done (§4c: no edge); Polymarket is untested and pays maker rebates, which is
   the one structural difference that could change the answer.
5. **Re-bisect the Kalshi retention boundary** before anyone acts on the
   2026-08-19 deadline in `market-selection/WHAT_IS_LEFT.md`.
6. **Re-establish the ESPN prop feed** (403 on 7 of 7 leagues) or withdraw
   `KXMLBRFI`'s no-free-reference property, which is the basis of shortlist #3.
7. **Tell the sibling their archive disk estimate is low** — tennis is 10.8% of
   a daytime hour, not the 0.6% measured overnight.

## 4c. Cross-venue: the shortlist's #1 mechanism is TESTED and shows no edge

[RESULTS_CROSSVENUE.md](RESULTS_CROSSVENUE.md). 5,334 paired Pinnacle/Kalshi
observations at a **median 7-second alignment**, 13 events. **Median buy edge is
negative under every de-vig method** — multiplicative −0.72¢, power −0.75¢,
worst-case −1.64¢. Fourth independent confirmation that Kalshi is the sharp
line.

**The join is the hard part and mine had a real phantom** — a `KXCS2GAME` market
paired to a *Mobile Legends* matchup, because the join never checked the league.
Game-consistency and roster-suffix-agreement filters added. **Matching on the
Kalshi ticker matches 3 of 218 events**; the full names live in
`yes_sub_title`, which the recorder now stores in `k_names`.

---

## 5. The build plan for H10 (EXECUTED — see §4b)

**Everything in the candle-based grid is done and null. The one pre-registered
strategy never run is H10, and it is the one that matters.**

Why it matters: the maker-vs-taker tension is the largest unresolved question in
this programme — `signal-github` says maker-only quoting is the one strategy
whose income need not overcome a fee first; a 20-year professional says be a
taker because adverse selection fills you only when you are wrong. **The only
number anyone has put on it is the 38% of gross it cost the esports arb author.**

It is newly runnable because the brief's premise was wrong: **Kalshi L2 history
exists** at `archive.pmxt.dev`, 550 hourly files, 2026-05-19T06 → 2026-06-11T03,
and it carries esports (498,434 rows and 74 tickers in one sampled hour, 2.58%).

The build, in order:

1. **Pull a NARROW window filtered to esports prefixes.** Do not pull all 37 GB.
   Model it on `social-signal/src/pull_kalshi_archive.py`, which streams
   row-group at a time and discards the raw. Budget ~1 GB of disk for esports
   across the window; **3–5 days is enough to measure a fill rate.** It is a
   volunteer-run archive and a sibling is already pulling the same files.
2. **Replay snapshot + deltas into a point-in-time book.** `market-selection`
   flagged this as *"the single biggest piece of unbuilt machinery"* and it is
   still unbuilt.
3. **Fill model: trade-through only, last in queue, honest partials** — already
   written in `src/engine.py::maker_fills`. Nothing in the repo corpus is worth
   adopting: of 3,201 archives, **queue position fires on 5.2% and trade-through
   on 3.0%**. Most "backtests" fill on a touch.
4. **Run the touch-counts-as-fill variant as a declared deliberate-leak
   diagnostic**, per the pre-registration, and report both.

Still open, unchanged:

- **Re-bisect the Kalshi retention boundary** before anyone acts on the
  2026-08-19 deadline in `WHAT_IS_LEFT.md`.
- **Re-establish the ESPN prop feed** (403 on 7 of 7 leagues) or withdraw
  `KXMLBRFI`'s no-free-reference property — the whole basis of shortlist #3.
- **Tell the sibling their archive disk estimate is low**: tennis is 10.8% of a
  daytime hour, not the 0.6% measured overnight.

**Do not** start a second heavy Kalshi puller while the recorder runs. C018 puts
the unauthenticated ceiling at 15 req/s and the recorder is the irreplaceable
process.

**Do not** start a second heavy puller while the recorder is running. C018
measured 15 req/s sustained as the unauthenticated ceiling; the recorder plus
one puller is already near it, and the recorder is the irreplaceable one.

---

## 6. What is NOT done, and is not pretended to be

- **The esports reference-price strategy has not been tested at all.** It cannot
  be, historically. The recorder is the entire apparatus and it needs weeks.
- **Polymarket weather** (shortlist #4) — not probed beyond the 15% two-sided
  reading. The London-wallet claim is unchecked.
- **`KXMLBRFI`** — no test run; its mechanism remains *an assertion about how
  the counterparty prices, with no evidence*.
- **H10 (passive quoting)** is in the pre-registration and is **not implemented**
  in `run_grid.py`. It needs the recorded book, not candles, and the recorder has
  hours of data rather than weeks. It is the most informative cell in the grid
  and it is the one that is missing.
- **The 3-way soccer panel** was built and abandoned on n, not analysed.

## 7. Files

| file | what |
|---|---|
| `PRIOR_ART.md` | Step 1 — what has been tried, by whom, with what evidence |
| `SHORTLIST.md` | Step 2 — the ranking, and the kill of the prior #1 |
| `DATA.md` | Step 3 — every source, fetch-verified |
| `PREREGISTRATION.md` | Step 5 — committed before any strategy ran |
| `DECISIONS.md` | 9 conservative calls, each naming what was given up |
| `src/engine.py`, `src/validate_engine.py` | Step 4 — the engine and its 5 controls |
| `src/record.py`, `src/rec_status.py` | the recorder and its content-level health check |
| `src/run_grid.py` | Step 6 — panel, guards, sweep, BH-FDR, control gate |
| `tools/` | corpus scanners: family census, de-vig scan, thread reader |

`data/` and `reports/` are gitignored — they hold recorded data and fetched
third-party content, and this repo is public.

---

## 8. 2026-08-06 — the de-vig test: PRE-REGISTERED, scoped, and NOT reachable on MLB

**Read [PREREGISTRATION_DEVIG.md](PREREGISTRATION_DEVIG.md) then
[RESULTS_DEVIG.md](RESULTS_DEVIG.md).** No settlement outcome has been joined to
any price; neither file contains a return.

### 8a. The de-vig test had never been run. Three things resemble it and are not it.

- **Step 6 / [RESULTS.md](RESULTS.md)** — H1–H9 on **Kalshi's own price only**.
  No external reference price appears anywhere in it, and PREREGISTRATION.md §0
  says so in its own words.
- **[RESULTS_CROSSVENUE.md](RESULTS_CROSSVENUE.md)** — measured the
  **distribution** of `fair − ask` on esports. No settlement, no gate, no P&L.
  `crossvenue_join.py` contains no reference to a result field, and its own §4.3
  says *"this measures price agreement, not realised P&L."*
- **T012** — a calibration statistic on tennis against Betfair.

### 8b. The answer is arithmetic and does not need more data

**The cost bar to take an MLB moneyline is larger than the entire vig being
removed from Pinnacle.** Pinnacle's MLB overround is **2.01 pp**; the Kalshi
taker fee at 50¢ is **1.75¢** and the quoted spread is **2.0¢**, so the bar at
1¢ slippage is **2.75¢**. De-vigging moves each side by roughly **1 pp**.

Measured `q` (fraction of events producing an entry): **0 of 17** at the primary
cell; 1 of 17 at zero slippage. The **best** per-event net gap, choosing the
entry with hindsight over each event's whole 24-hour window, is **−0.91¢** —
**no event is positive at any moment.** The rule-of-three upper bound on `q` is
0.18, and every timeline below uses that optimistic figure.

| | |
|---|---|
| **Stage A** — is the de-vigged reference a *better forecast* than Kalshi's price (paired Brier) | **≈ 440 events ≈ 30 MLB days ≈ early Sept 2026. REACHABLE.** |
| **Stage B** — the gated P&L test as asked | 5¢ edge needs **4,356 events = 1.8 seasons**; 3¢ needs **5.0 seasons**. The rest of this season resolves only an **11.6¢** edge. **NOT REACHABLE.** |

No historical shortcut exists: Pinnacle has no historical endpoint at any price,
and the only free historical sharp line found (`football-data.co.uk`) is
**soccer only**. Baseball is forward-only.

### 8c. ⚠ THE RECORDER WAS DEAD FOR 2.5 HOURS AND NOTHING NOTICED

Last cycle **2026-08-06T15:13Z**; no python process alive at 17:41Z; **zero
bytes written to `recorder3.err`.** It had been launched from a prior session's
shell and died with it. Restarted detached (and again at 17:51Z for the fix
below). **Nothing monitors it.** This is the only asset in the project that
cannot be bought back later — a watchdog is worth more than any analysis here.

### 8d. Two recorder defects found and fixed

1. **`record.py` probed `mkts[:60]` in Kalshi's undocumented listing order.**
   `KXMLBGAME` lists 85–104 markets, so ~40 got no book per cycle and the server
   decided which. Snapshots per MLB ticker ran **min 1, p25 25, median 94** over
   214 cycles. Now sorted by `close_time` ascending — the games about to start
   are never the ones dropped. **Recorder restarted to pick this up.**
2. **The club-name join silently dropped the Athletics.** Kalshi writes `A's` →
   normalises to `a s`, length 3, under the length-4 floor that exists to stop a
   one-character name swallowing the sample (the Polymarket phantom). 5 of 53
   events lost. Replaced with an exact 30-club code map on the ticker suffix:
   join **17 → 21 events**, and Pinnacle's aggregate props
   (`Home Runs (15 Games)`) become unmatchable too.

### 8e. ⚠ Third Kalshi time field to mislead this repo — and one number corrected

**`close_time` on a LIVE Kalshi MLB market is the game start plus exactly 72 h**
(94 of 94 active markets). On **settled** markets Kalshi rewrites it to the true
settlement instant, 2.4–3.2 h after start. Anchoring a live market on it anchors
**69 hours after first pitch**. After Amendment A1 and LEDGER T010, this is the
third Kalshi time field to mislead this repo. The design derives the start from
the ticker, verified exact against Pinnacle's `starts_utc` on **22 of 22**
jointly-listed games.

> ✅ **The old MLB control is NOT damaged.** It ran on settled markets, where
> `close_time` is the true settlement instant, so its −24 h anchor really was
> ~21 h pre-match. Checked specifically, because the opposite would have voided
> RESULTS.md's control gate.

> ⚠ **RESULTS.md §3's "KXMLBGAME is 1.0¢ at every lead" is a CANDLE
> measurement.** The recorded live touch is **median 2.0¢, p90 7.0¢**. The
> strategy pays the touch. Corrected inline in RESULTS_DEVIG.md; every cost
> figure in the new design is recomputed from the recorded book.

### 8f. MLB as control → MLB as test family: what breaks, and the clean way

**Spent, not reserved.** The control gated one candle-based run of H1–H9 and
reported PASS; a control is a role a dataset played in one experiment, not a
permanent property of a family. **The DATA is not reused** — a hard boundary
excludes any game starting before **2026-08-05T00:00:00Z**, clearing the control
set's latest game start (**2026-08-04T23:40:00Z**) by 20 minutes, asserted in
code.

**What genuinely breaks:** the family can no longer generate its own null.
Replaced by three internal controls — **mismatched-pair placebo (the gate)**,
stale-reference placebo, two-sided coherence — which run on the same events and
so cannot be separately underpowered. And the prior now runs against the test,
so a positive H11 must clear **all six** of Stage A, BH-FDR, a CI above cost, a
clean placebo, PLATEAU-not-PEAK, and the sealed holdout.

### 8g. The single next thing

**Build and schedule the settlement puller.** Every other leg is recording;
outcomes are the only leg with a **deadline** — Kalshi's window is ~69 days and
closed markets 404 for good. Stage A cannot run without them, and Stage A is the
only stage that is reachable. Then the **Polymarket leg**, where makers are paid
a rebate rather than charged a fee and the §8b arithmetic is genuinely different.

### 8h. Files added this session

| file | what |
|---|---|
| `PREREGISTRATION_DEVIG.md` | H11, committed at `d163484` before any return existed |
| `RESULTS_DEVIG.md` | the feasibility measurement — `q`, the event counts, no settlement |
| `src/mlb_scope.py` | apparatus census. ⚠ its name-only join is **superseded**; do not quote its 34.6% |
| `src/devig_power.py` | the pre-registered join + gate, measuring `q` only |

---

## 9. 2026-08-07 — the three de-vig questions, answered

Read [RESULTS_DEVIG_WHERE.md](RESULTS_DEVIG_WHERE.md). `src/devig_where.py`.

**⚠ A correction to this project's own claim comes first.** RESULTS_DEVIG.md §1
led with *"the cost bar is larger than the entire vig being removed"*. **That is
not a valid argument.** The overround is what you *strip* to estimate fair value;
it does **not bound** the edge. Corrected there and in SCOREBOARD.md.

**Q1 — not underpowered on MLB; decisive on evidence.** `|de-vigged fair − ask|`
over **1,460 paired observations on 30 joined games**: median **0.77¢**, p99
2.38¢, **max 2.77¢**, against a **2.75¢** cost bar. Positive after cost on
**0.00%**. The venues would have to disagree by ~4× their observed maximum.

**Q2 — on track, decides ≈ 2026-09-06.** 30 joined (was 21), **17 fully
settled**, **13.8 joined events/day** vs ~15 MLB games/day. The settlement leg —
§5's "single next thing", previously unbuilt — now exists and ran.

**Q3 — no, and it is a mechanism.** Overround 2.44pp (MLB) → **13.21pp** (CS2
EWC Qualifier). But Kalshi's recorded spread moves with it: **KXCS2GAME 8.0¢
median / 23.97¢ mean** vs **KXATPMATCH 1.0¢ / 1.98¢**. The widest markets
(Rwandan/Chilean basketball) have **no Kalshi counterpart**. The best ratio is
ATP/WTA — **which is T012, already null**.

### Recorder note

`k_names` + the exact start-time key + the 30-club code map are working: **1 of
67** events dropped on names. The other 36 drops are games **Pinnacle has not
listed yet** and resolve daily.

### The one number to carry

**Stage A is the only de-vig test still alive, and it is 30 days out.** If the
de-vigged sharp price is not a better *forecast* than Kalshi's own, no threshold
on the gap can be an edge and the thread closes for good.
