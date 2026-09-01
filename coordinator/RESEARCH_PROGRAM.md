# THE STRATEGY RESEARCH PROGRAM — master plan

**His brief, 2026-08-28.** Parlays, cross-platform arbitrage, strategy
discovery, and a future real-markets track.

**This document exists because a large part of the program already exists, and
two parts of it are already answered.** The dictator's job is to route, not to
rebuild — so this maps his twenty questions onto what is built, what is
measured, and what is genuinely new.

**No live money anywhere in this program.**

---

## ⚠ PRIORITY 1 — CORRECTED 2026-09-02. THE ORIGINAL TABLE BELOW WAS CONTAMINATED.

> **⚠ CORRECTION, found in a fresh-eyes audit of my own script.** The table
> below used every `state` row carrying a prematch price — **34,218 markets —
> without reading the `ok` flag the source study stores on every row. 22,974 of
> those rows (67%) were rows the study itself had REJECTED, almost all as
> `pre-match book empty`: the quote existed but the spread was wider than 10
> cents, so its mid is a poor probability estimate and its ask is far from fair.
> `calib.py` filtered on `pre_bid IS NOT NULL` and assumed that meant usable.
> **It did not, and the assumption was exactly the class of error this repo
> keeps recording.**
>
> **Re-run on the 11,079 clean rows only:**
>
> | band | n | implied | observed | gap | EV at ask |
> |---|---|---|---|---|---|
> | 50–55 | 761 | 52.3% | 51.4% | −0.9 | −8.1% |
> | 55–60 | 814 | 57.3% | 59.5% | +2.2 | −2.0% |
> | 60–65 | 749 | 62.3% | 65.3% | +3.0 | −0.7% |
> | 65–70 | 664 | 67.2% | 64.9% | **−2.3** | −8.0% |
> | 70–75 | 619 | 72.3% | 70.8% | **−1.6** | −6.7% |
> | 75–80 | 589 | 77.3% | 79.5% | +2.2 | −1.7% |
> | 80–85 | 562 | 82.2% | 85.8% | +3.5 | **+0.8%** |
> | 85–90 | 480 | 87.3% | 89.6% | +2.3 | −0.4% |
> | 90–92.5 | 240 | 91.1% | 92.9% | +1.8 | −0.9% |
> | 92.5–95 | 232 | 93.5% | 95.3% | +1.7 | −0.6% |
> | 95–97.5 | 107 | 95.8% | 93.5% | −2.3 | −4.4% |
>
> **What changes:** the "favourites are underpriced" gap is smaller and no
> longer consistent — two mid bands are NEGATIVE. The clean story is patchy,
> not uniform. **"Every band is negative at the ask" is also no longer exactly
> true**: 80–85 shows +0.8% — one band of eleven, small, and not a finding.
> **What does not change:** no reliably tradeable calibration edge, and the
> reversal above 95c. **The 90–95c bands were almost entirely clean rows
> (240/249 and 232/246), so the maker-execution test built on them is
> unaffected.** The baseball half was checked for the same class of error and
> is clean — all 1,706 earliest prices are before first pitch.
>
> **The wide-book rows, run alone, show why the contamination flattered the
> original:** apparent gaps up to +10.2 points (the mid of a 1/99 book says 50
> and means nothing) with EV at the ask as bad as −42%.

## ~~PRIORITY 1 IS ANSWERED TONIGHT. THE CALIBRATION EDGE IS REAL AND THE SPREAD EATS ALL OF IT.~~ (superseded above; kept for the record)

**Method:** one market = one observation. Implied probability is the **prematch
mid**; the EV column is what you get **buying at the real ask** and holding to
settlement, fees from `common/kalshi_fees.py`. Wilson intervals.

**TENNIS, all series pooled — 34,218 settled markets:**

| price band | n | implied | observed | gap | 95% CI of gap | **EV at the ask** |
|---|---|---|---|---|---|---|
| 50–55 | 4,953 | 50.9% | 53.6% | **+2.7** | [+1.3, +4.1] | **−38.7%** |
| 55–60 | 1,553 | 57.2% | 60.9% | **+3.7** | [+1.3, +6.1] | −16.4% |
| 60–65 | 1,289 | 62.2% | 63.8% | +1.5 | [−1.1, +4.1] | −14.5% |
| 65–70 | 1,119 | 67.2% | 66.4% | −0.8 | [−3.6, +1.9] | −14.0% |
| 70–75 | 947 | 72.2% | 74.6% | +2.3 | [−0.5, +5.0] | −7.5% |
| 75–80 | 785 | 77.3% | 80.6% | **+3.4** | [+0.5, +6.0] | −3.1% |
| 80–85 | 718 | 82.2% | 85.9% | **+3.7** | [+1.0, +6.1] | −1.0% |
| 85–90 | 553 | 87.2% | 89.5% | +2.3 | [−0.6, +4.6] | −1.1% |
| **90–92.5** | 249 | 91.1% | 93.2% | +2.1 | [−1.7, +4.6] | **−0.7%** |
| **92.5–95** | 246 | 93.5% | 95.1% | +1.6 | [−1.8, +3.7] | **−0.7%** |
| 95–97.5 | 115 | 95.8% | 93.9% | **−1.9** | [−7.8, +1.2] | −3.9% |

**Four findings, and the fourth is the one that governs the whole program:**

1. **Favourites really do win slightly more often than the market implies.**
   +2.7 to +3.7 points, and four bands have intervals that exclude zero. **His
   hypothesis is not wrong.**
2. **The effect REVERSES above 95c.** −1.9 points. **The very heaviest
   favourites are the one place favourites are overpriced** — the opposite of
   where the parlay idea wants to live.
3. **The sweet spot is 90–95c**, where the cost of trading is smallest.
4. **⚠ EVERY SINGLE BAND IS NEGATIVE AFTER PAYING THE ASK. The best is −0.7%.**
   A +3.7 point calibration gap at 80–85c becomes −1.0% once you buy it. **The
   edge is real and it is entirely inside the spread.**

**BASEBALL who-wins — 1,706 archive markets.** Not a favourite story at all: the
sample is 978 markets in the 50–55 band. The 65–70 band shows implied 67.2% vs
observed 46.3%, **−20.9 points, interval excluding zero, on 54 markets.**

### What this does to PART I before a single parlay is built

**A parlay is a product of its legs. Combining negative-EV legs cannot produce
positive EV — that is arithmetic, not an opinion.** Every band is negative at
the ask, so:

- **multi-leg favourite structures are dead on arrival unless the leg EV turns
  positive.** More legs multiplies a number below 1 by another number below 1.
- **the leg count question — 2 vs 3 vs 7 — is downstream of a gate none of them
  pass.** It is not worth an experiment matrix yet.
- **the one live question is whether MAKER execution turns any band positive.**
  90–95c is only 0.7 points underwater. **That is the whole of Part I now.**

**⚠ And tennis already tested maker execution once (mailbox 017): UNDECIDABLE —
the lever removes ~3.2c of a 3.61c cost bar and there was no edge underneath.
This is a different question** (whole-market calibration, not the set-1 fade)
and the same method applies. **That is the single highest-value experiment in
this brief.**

---

## WHAT ALREADY EXISTS — do not rebuild these

| his ask | what exists |
|---|---|
| **market ingestion, multi-platform** | `bot-hunt/data/record.db`, **66 GB**: Kalshi bid/ask **with depth**, Polymarket books, Pinnacle prices, **on one clock**, since 2026-08-04 |
| **platform matrix** | `coordinator/runners.json`, `kalshi-market-scan`, and the factory's census of **3,654 live Kalshi families** |
| **fee engine** | `common/kalshi_fees.py` — the ONLY implementation, enforced by a repo-wide test. Maker and taker paths both present |
| **strategy discovery framework** | the `factory` chat: census → spec → screen → pre-register → forward test, with a placebo arm. `SCREEN-01` already ran |
| **strategy card** | `PREREGISTRATION_*.md` convention across 8 folders |
| **anti-overfitting review** | the Critic/Referee in `coordinator/reflect.py`, plus `reopen`, whose entire job is auditing conclusions |
| **backtest framework** | `coordinator/studies/rebound2.py` — conditional baselines, no look-ahead, BH correction, train/test split |
| **historical data** | tennis: 13.2M candles / 35,990 markets. Baseball: 8.7M candles / 1,703 games. Crypto ladders. Soccer |
| **database + timestamps** | already per-project SQLite with settled results |

**Roughly two thirds of his infrastructure list is built.**

## WHAT IS ALREADY ANSWERED — with the five fields, so nothing is re-run blind

**1. Martingale.** `CH090`: EV is **−1.75% of every dollar staked on a true coin
flip**; ten doublings risks **$10,230 to net $10**, and fees mean straight
doubling does not even fully recover. **SETTLED. His own brief predicts this
answer; it is confirmed, not assumed.**

**2. Same-platform ladder arbitrage.** Crypto: **0 monotonicity violations in
3,187 scans**; 1 gross bucket-sum violation in 1,135, **unprofitable net**.
`K007` scanned ~9 hours and found **52 genuine violations, none with tradeable
size**. **SETTLED — the ladder is wide enough that legging it is
self-defeating.**

**3. Prediction-market vs sportsbook arbitrage on who-wins.** `devig`: Bovada
charges **4.5 out of 100** where Pinnacle charges 2.0, and **once each margin is
removed they agree to within a fifth of a penny.** Zero of 11 games worth
trading. **SETTLED negative.**

**4. Sportsbook vs Kalshi on totals.** 109 rungs, 9 games, 0 clear — **and the
mechanism is better than the verdict: the sharp price sits INSIDE Kalshi's
spread on 70 of 100 rungs.** There is no gap to see, not a gap too small.
**SETTLED.**

**5. Player props vs a sharp reference.** `BH023`: 14 props, **0 of 14 clear the
bar**, and the three de-vig methods **disagree in sign on 8 of 14** — a
pre-registered drop condition. **SETTLED.**

**6. Near-certainty availability.** `GUARDS #24`: when somebody is bidding 95c+
you can actually buy it **29 times in 100 in soccer, 53 in baseball, 56 and 67
in tennis** — measured across **seven sports**. **This is a hard constraint on
every heavy-favourite structure in Part I: the contracts often cannot be
bought.**

## WHAT IS GENUINELY NEW

1. **Whole-market calibration as maker** — the 90–95c band is 0.7 points
   underwater. **Priority 1a.**
2. **Cross-platform arbitrage measured on the tape we already have.** Kalshi,
   Polymarket and Pinnacle are already on one clock in `record.db` and **nobody
   has run a cross-platform scan over it.** Not a build — a query. **Priority 2.**
3. **Canonical event matching** across those three venues. Genuinely unbuilt and
   genuinely hard.
4. **How long an apparent arbitrage persists** — answerable from the recorded
   tape rather than from a live scanner.
5. **Correlation between legs** — never measured here.
6. **Sports beyond tennis/baseball/soccer** — NCAA, NBA, NFL, NHL calibration.
   The recorder covers 3,654 families; most have never been looked at.
7. **The barbell/paired-parlay structure** — pure arithmetic, answerable in an
   hour, and almost certainly a synthetic position plus extra fees.

---

## ROUTING — existing chats, no new ones yet

| workstream | chat | first job |
|---|---|---|
| **calibration as maker (P1a)** | `tennis` | it owns the maker method and the tennis tape |
| **calibration across other sports** | `factory` | it owns the 3,654-family census |
| **cross-platform arb on the existing tape (P2)** | `devig` | it owns `bot-hunt`/`record.db` and every de-vig result |
| **event matching across venues** | `devig` | same folder, same data |
| **the barbell arithmetic** | `coordinator` (me) | an hour, no data needed |
| **correlation between legs** | `mlb` | it has the only multi-bot same-game data |
| **anti-overfitting review** | `reopen` | already its standing job |
| **real financial markets** | **nobody yet** | already in `INBOX.md`, correctly parked |

**No new chats are created tonight.** Twelve new windows would each need a
folder, a handoff, a decisions log and a human typing into them. **Every
workstream above has an owner that already exists.**

---

## THE STANDARD, AND WHERE IT ALREADY BINDS

He asked for `N=`, implied, observed, gap, CI, EV, out-of-sample, conclusion.
**That is already the house standard** — `CLAUDE.md` §6, `GUARDS.md`, the
pre-registration convention, and the Critic/Referee pass. **The calibration
table above is written in exactly that form.**

**The one thing to add to it, which his brief implies and does not name:** every
result must state **how many variants were screened to produce it.** The factory
already measured what that costs — the best of 2,000 zero-skill strategies
typically looks like **+29.5%**.

## NEXT STEPS, IN ORDER

1. **Maker calibration on the 90–95c band** — the only Part I question still
   open, and 0.7 points from break-even.
2. **Cross-platform scan over `record.db`** — the data is already on disk and on
   one clock. Nobody has looked.
3. **The barbell arithmetic** — cheap, and likely a rejection.
4. **Calibration in sports nobody has touched** — NCAA basketball especially,
   since his brief names it first.
5. Everything else waits on those four.
