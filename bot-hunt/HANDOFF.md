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
| `src/record.py` (10-min cycles) | **2026-08-04 21:27 UTC** | `bot-hunt/data/record.db` |
| `src/pull_kalshi_soccer.py --series KXCS2GAME,KXLOLGAME,KXVALORANTGAME` | 2026-08-04 22:08 UTC | `bot-hunt/data/kalshi_soccer.db` |

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

## 4. Step 6 status: RUN, NOT REPORTABLE — and that is the correct outcome

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

## 5. The single next thing to do

**Pull the control family's candles, then re-run the grid.** The gate cannot
pass until `KXMLBGAME` has a panel, and nothing from the test family is
reportable until it does.

```bash
C:\Users\vinig\trading\bot-hunt\.venv\Scripts\python.exe C:\Users\vinig\trading\bot-hunt\src\pull_kalshi_soccer.py --series KXMLBGAME --days 80
```

Then, in order:

1. `src/run_grid.py` — train 70% only.
2. Only if the control gate PASSES and something survives BH-FDR **with a broad
   plateau**: `src/run_grid.py --holdout`, **once**.
3. Re-bisect the Kalshi retention boundary (§2c) before anyone acts on the
   2026-08-19 deadline in `WHAT_IS_LEFT.md`.
4. Re-establish the ESPN prop feed, or withdraw `KXMLBRFI`'s no-free-reference
   property, which is the whole basis of shortlist entry #3.

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
