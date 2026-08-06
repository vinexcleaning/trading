# PREREGISTRATION_DEVIG.md — H11, the reference-price test

**Written 2026-08-06, BEFORE any return, settlement, or gated-edge count
existed.** What had been measured when this file was committed is listed
exhaustively in §1.3, and it is all apparatus: coverage counts, join rates,
quoted spreads, and Pinnacle's overround. **No settlement outcome has been
joined to any price in this project's MLB data, and no P&L number of any kind
has been computed for this strategy.** Git history is the evidence for that
ordering, which is why this file is committed on its own.

This is a separate pre-registration from [PREREGISTRATION.md](PREREGISTRATION.md)
rather than an amendment to it, because it changes the role of a family that
document used as a control. §4 is about exactly that and is the part worth
reading if you read nothing else.

---

## 1. The question, and the honest state of it

### 1.1 What is being tested

> Take Pinnacle's price. Strip out the vig. Treat the result as fair value.
> Compare it to the executable Kalshi price. **Count it only when the gap beats
> cost.** Hold to settlement. Measure what that made.

### 1.2 Has this ever been run? **No.** Three things that look like it are not it.

| what exists | what it actually did | why it is not this test |
|---|---|---|
| **Step 6** ([RESULTS.md](RESULTS.md)) — 260 test cells + 148 control cells | H1–H9 on **Kalshi's own price only**: deciles, longshots, favourites, drift, spread, volume, staleness | **No external reference price appears anywhere in it.** [PREREGISTRATION.md](PREREGISTRATION.md) §0 says so in its own words: *"the only thing testable to completion on retrievable data is a STRUCTURAL test that needs no external reference price."* |
| **[RESULTS_CROSSVENUE.md](RESULTS_CROSSVENUE.md)** — 5,334 paired esports observations, three de-vig methods | measured the **distribution** of `fair − ask` | **No settlement, no gate, no P&L.** Its own §4.3 states it: *"No settlement outcomes yet — this measures price agreement, not realised P&L."* Nothing is ever filtered to `edge > cost`; every observation is pooled into a median. `src/crossvenue_join.py` contains no reference to settlement or result, and its docstring says *"NOTHING HERE IS AN EDGE CLAIM."* |
| **T012** (tennis, r = 0.9878 vs Betfair close) | correlation and mean absolute deviation vs a reference | a **calibration** statistic, not a gated strategy, and on a different sport and reference book |

So the mechanism that ranks **#1** in [SHORTLIST.md](SHORTLIST.md), and that is the
design behind the only strategy in any corpus attached to this repo with a public
wallet and a reconciled four-line P&L, **has never been run to a return by
anyone here.** That is the gap this file exists to close.

### 1.3 Everything measured before this file was written

Recorded here so that nothing in the design below can later be claimed to have
been chosen blind when it was not.

| measured | value | where |
|---|---|---|
| recorder window | 214 cycles, 2026-08-04T21:27Z → 2026-08-06T17:41Z (44.2 h) | `reports/mlb_scope.json` |
| Kalshi `KXMLBGAME` book snapshots | 12,720 over 120 tickers, **100.0% two-sided** | same |
| Kalshi `KXMLBGAME` quoted spread | **median 2.0¢, p90 7.0¢** (n = 12,720) | same |
| Pinnacle MLB matchups named | 36 distinct start times, 2026-08-04T22:34Z → 2026-08-07T01:40Z | same |
| Pinnacle MLB moneyline price rows | 304,383 over 645 matchups | same |
| Pinnacle MLB overround | **median 2.01pp** (p10 1.94, p90 2.36) | same |
| join on exact game start | **22 of 22 Kalshi events whose start falls inside the Pinnacle window**; 31 unmatched are all games from 2026-08-08 on, which Pinnacle has not listed yet | §3.2 |
| quote time alignment | median 11 s, p90 457 s | same |

**Not measured, and deliberately not:** any settlement result, any realised
return, any count of observations clearing any cost bar, any per-side or
per-band statistic conditioned on outcome.

> ⚠ **One number in the record is wrong and this file corrects it.**
> [RESULTS.md](RESULTS.md) §3 reports `KXMLBGAME` at a **1.0¢ median spread at
> every lead from 15 min to 24 h, p90 included**, and that reading is why MLB is
> described as the only family with a 1¢ cost bar. That figure came from
> **hourly candles on settled markets**. The **recorded live order book** puts
> the median at **2.0¢ and the p90 at 7.0¢**. Both can be true — a candle's
> `yes_bid`/`yes_ask` are period aggregates and the touch is an instant — but
> **the strategy pays the touch**, so 2.0¢ is the number this design uses, and
> every cost figure below is recomputed from the recorded book at trade time,
> never taken from either file.

---

## 2. What the strategy is, stated completely

### 2.1 Definition — **H11**

For a Kalshi MLB moneyline market `m` on side `s` of event `e`, at recorder
timestamp `t`:

```
p_home, p_away   = american_to_prob(Pinnacle moneyline, period 0, at time t')
fair_s           = devig(p_home, p_away)[method][s]          # probability
edge_buy(t)      = 100 * fair_s  -  yes_ask_c(t)             # cents
cost(t)          = fee(yes_ask_c(t))  +  slippage            # cents
ENTER  iff  edge_buy(t) > cost(t)
```

Enter **at the ask** for one contract, hold to settlement, realise
`100 - yes_ask_c` on a win and `-yes_ask_c` on a loss, minus `fee`.

`t'` is the Pinnacle observation nearest `t`; pairs more than **900 s** apart are
discarded, matching `crossvenue_join.py`.

### 2.2 The de-vig methods — all three, none chosen for us

`multiplicative`, `power`, and `worst_case` (the least favourable of the two),
exactly as implemented in `src/crossvenue_join.py`. All three are reported side
by side. **`worst_case` is the primary**; the other two are sensitivity arms.

The reason `worst_case` is primary and not the empirically-best-fitting `power`:
RESULTS_CROSSVENUE measured that **the choice of de-vig method decides most of
the apparent tail** (13.1% of observations over 2¢ under multiplicative, 5.9%
under worst-case), and the one author with a reconciled live P&L reported his
Shin implementation *"ran hot on favourites."* A method that manufactures the
tail it is being tested on is not a neutral instrument.

### 2.3 The cost bar — recomputed from data, never hardcoded

```
cost(t) = fee(ask) + slippage
```

- **`fee`** comes from `common/kalshi_fees.py` and nothing else. GUARDS #6 and
  `common/tests/test_no_fee_reimplementation.py` make that a test, not a
  convention. The fee is quadratic and peaks at 50¢, which is precisely where
  MLB moneylines live, so this term is **large**: roughly **1.8¢ per contract at
  50¢**, against the 2.0¢ median spread. `KXMLBGAME` is a taker trade here, so
  the taker rate applies regardless of the maker-fee series question.
- **No half-spread term.** Buying at the ask *is* paying the spread; adding a
  half-spread on top would double-count. The ask is taken from the recorded
  book at `t` and is never a mid. `record.py` computes no mid anywhere.
- **`slippage`** is swept at **0.0 / 0.5 / 1.0 / 2.0¢**, with **1.0¢ primary**,
  identical to [PREREGISTRATION.md](PREREGISTRATION.md) so the two grids stay
  comparable.
- **Size is not modelled and no size claim will be made.** Pinnacle publishes
  `maxRiskStake` and the recorder stores it; Kalshi depth at 5¢ is stored as
  `depth5_yes`/`depth5_no`. Both are **reported beside every result** as a
  capacity note. A per-contract edge that only exists for 3 contracts is
  recorded as such.

### 2.4 One trade per event, and the reason

An event yields ~23 aligned observations. Trading each one is 23 correlated bets
on one outcome dressed up as 23 observations — the exact error §6 of
[CLAUDE.md](../CLAUDE.md) names (*"490,464 fills from 762 matches are 762
observations"*).

**Fixed now:** at most **one entry per event**, taken at the **first** timestamp
at which the gate fires at or after the anchor, on **whichever side fires
first**; if both sides fire at the same timestamp the event is **discarded**, not
resolved by picking one — two sides of a binary both looking cheap against the
same de-vigged book is an arithmetic impossibility and marks a bad pair.

**Unit of observation = the event. Every CI is bootstrapped over events.**
Effective n is printed beside nominal n.

### 2.5 The anchor, and a trap specific to live Kalshi markets

> ⚠ **`close_time` on a LIVE Kalshi MLB market is the game start plus exactly
> 72 hours.** Measured on all 94 currently-active `KXMLBGAME` markets: the delta
> is `72.00 h` on every one. On **settled** markets Kalshi rewrites `close_time`
> to the actual settlement instant, which is why the same field reads 2.4–3.2 h
> after start on the 1,830 finalized markets. **The two are not the same field
> in practice**, and anything anchoring a live market on `close_time` is
> anchoring **69 hours after the first pitch**.

This is the same class of defect as **Amendment A1** (*"`close_time` is when the
market SETTLES, not when the match starts"*) and **LEDGER T010**
(`occurrence_datetime` is at or after match end). It is the third time this repo
has been bitten by a Kalshi time field, so:

**The game start is derived from the ticker and from nothing else.**
`KXMLBGAME-26AUG041940PITMIL` → `2026-08-04 19:40 America/New_York` →
`2026-08-04T23:40:00Z`. Verified exact against Pinnacle's independent
`starts_utc` on **22 of 22** jointly-listed games.

| | |
|---|---|
| **PRIMARY anchor** | the **first qualifying observation in the window `[start − 24 h, start − 30 min]`** |
| **SENSITIVITY** | windows `[start − 6 h, start − 30 min]` and `[start − 2 h, start − 30 min]` |
| **hard rule** | no observation at or after `start − 30 min` may ever enter. The 30-minute buffer absorbs a postponed or moved first pitch. |

### 2.6 The leak canary, which can void this design exactly as it voided the last

Run before any return is printed, on the entry population:

1. **T010/T011 extreme-quote signature.** If >1% of entry quotes are ≤2¢ or
   ≥98¢ **and** ≥99% of those are correct, the anchor is **VOID**.
2. **Start-time agreement.** Every entry must satisfy
   `|ticker_start − pinnacle_starts_utc| ≤ 15 min`. Any event failing this is
   dropped and **counted in the report**.
3. **Pinnacle liveness.** Any Pinnacle observation with `isLive = 1` is
   discarded. The recorder stores this flag; an in-play sharp line against a
   pre-match Kalshi quote is the leak this whole anchor exists to prevent.

**If canary 1 fires, no return from this design is reportable.** That is not
hypothetical — it is what happened to the −60 min anchor in Amendment A1.

---

## 3. Data, and the join

### 3.1 Source

**The recorder, and only the recorder.** `bot-hunt/data/record.db`, tables
`pin_matchup`, `pin_market`, `k_book`, `k_names`. Pinnacle has **no historical
endpoint at any price** (`DATA.md`), and of the historical sharp-odds sources
probed, the only free one — `football-data.co.uk`'s `PSCH`/`PSCD`/`PSCA` closing
odds — is **soccer only**. There is no way to backfill this test on baseball.
**It is forward-only, and every day the recorder is down is a day that cannot be
bought back.**

Settlement comes from Kalshi's own `result` field, pulled separately by
`src/pull_kalshi_soccer.py`. **The recorder does not store settlement and must
not**: mixing a live-price recorder with an outcome field is how a leak gets
built by accident.

### 3.2 The join — an exact key, not a fuzzy match

Esports cost this project two phantom joins (a CS2 contract paired to a Mobile
Legends matchup; a one-character team name swallowing a quarter of the
Polymarket sample). **MLB is structurally different and the join must exploit
that**:

1. **Primary key: exact UTC game start.** `ticker_start == pinnacle.starts_utc`.
   Both venues publish a scheduled first pitch and they agree to the minute.
2. **Confirmation: club names must agree on both sides.** Kalshi truncates
   (`Los Angeles D`, `Chicago WS`, `New York M`), so the test is
   nickname-contained-in-club-name with a **length floor of 4**, in both
   directions, and **both** sides must map, one to `home` and one to `away`.
3. **A Pinnacle matchup may be used by at most one Kalshi event**, and vice
   versa. Many-to-one is a phantom by construction.

**Why this matters more on MLB than it looks:** the same two clubs play three or
four consecutive days. A name-only join will happily pair Tuesday's Kalshi
contract with Wednesday's Pinnacle line, and every check based on team identity
will pass. The start-time key is what makes that impossible. **My own first pass
at this join, in `src/mlb_scope.py`, was name-only and is not trustworthy for
exactly this reason** — it is superseded by the rule above and its 34.6% figure
should not be quoted.

Any event failing any of the three is **counted and reported**, never silently
dropped.

### 3.3 ⚠ Disjointness from the control data — the binding constraint

The instruction is *do not re-use control data as test data*, and it is honoured
by a date boundary that can be checked mechanically:

| | control (already spent) | test (H11) |
|---|---|---|
| where | `data/kalshi_soccer.db`, **hourly candles** | `data/record.db`, **recorded order book + Pinnacle** |
| what | Kalshi price only | Kalshi price **+ external reference** |
| events | 909 settled `KXMLBGAME` events | games starting on or after the boundary |
| **latest game start in the control set** | **2026-08-04T23:40:00Z** *(measured)* | — |

> **RULE: no game with a start time earlier than `2026-08-05T00:00:00Z` may
> enter H11.** The control set's latest game starts at 2026-08-04T23:40Z, so the
> boundary clears it by 20 minutes and the two sets are **disjoint by
> construction**. The rule is asserted in code and the build refuses to write a
> panel that violates it.

This is a genuine separation and not a relabelling: different table, different
instrument, different variable, and no shared event.

---

## 4. ⚠ MLB was the negative control. What that does to this design.

This is the part that could invalidate everything and it is answered directly.

### 4.1 What the old control was, and what it was for

[PREREGISTRATION.md](PREREGISTRATION.md) §0 and §3.9: `KXMLBGAME` is *"known
efficient"*, every structural strategy runs on it too, and **if ≥2 strategies
"work" on it the run is declared broken**. It fired as designed —
[RESULTS.md](RESULTS.md) §1: *"negative-control gate — PASS, 0 positive
survivors of 148 cells."*

### 4.2 What is and is not broken by promoting it to the test family

**Not broken — the control has already discharged its duty and is spent.** It
gated one specific run, on candle data, for strategies H1–H9. That run is
finished and reported. A control is not a permanent property of a family; it is
a role a dataset played in one experiment. Re-using the *family* is fine.
Re-using the *data* is not, and §3.3 is why it is not being re-used.

**Broken — the family can no longer serve as the null-generator for this test.**
You cannot simultaneously assert *"MLB is efficient, so anything that works here
is an artifact"* and *"MLB is where I expect the reference-price edge to be."*
The old design's error-catching mechanism is unavailable to H11 and **must be
replaced, not quietly dropped.** §4.3 replaces it.

**Also broken — the prior.** Four independent measurements say MLB moneyline is
efficient: 0.37¢ against de-vigged DraftKings with 0 of 26 over the bar; a 1.0¢
candle spread at every lead; 0 of 148 structural cells; and the third-party API
finding *"Polymarket and Kalshi agree within 1 to 2 cents on most game-level
markets where both have liquidity."* **This design therefore carries a stated
prior against itself**, and §6 turns that into a harder decision rule rather
than pretending it away.

> **The clean way to do this, stated as the design choice it is:** run it on MLB,
> because MLB is the only family with a joinable reference price, a stable cost
> bar and a real forward event rate — and **treat MLB's known efficiency as a
> difficulty setting rather than as a disqualification.** Finding an edge on the
> family this project pre-declared efficient would be the strongest result it
> could produce. Finding none is the expected outcome and is a *fifth*
> confirmation, on a fifth instrument, that Kalshi is the sharp line. **Both
> outcomes are informative, which is the actual test of whether a design is
> worth running.**

### 4.3 The replacement controls — three, all internal, none needing a new family

A separate control *family* is not available: MLB is the only one that is both
joinable and reference-priced. So the controls are internal, which is stronger
anyway — they cannot be separately underpowered, because they run on the same
events as the test.

| | control | what a failure means |
|---|---|---|
| **N1** | **Mismatched-pair placebo.** Same Kalshi market, de-vigged fair value taken from a **different MLB game starting the same day**, assigned by a deterministic rotation (events sorted by start time, event *i* paired to matchup *i+1*). | An "edge" here is join artifact, estimator bias, or the cost bar being wrong. **If N1 produces a positive gated result, no H11 result is reportable.** |
| **N2** | **Stale-reference placebo.** Real pairing, but Pinnacle's fair value taken from the **nearest observation ≥ 24 h earlier**. | If a day-old reference performs as well as a live one, the "signal" is not information about this game. |
| **N3** | **Two-sided coherence.** Run the gate on the **sell** side too (`edge_sell = bid − 100·fair`). | If **both** buy and sell gates return positive net on the same population, the fair value is tracking noise, not truth. Arithmetically both cannot be right. |

**N1 is the gate.** N2 and N3 are diagnostics reported beside the result.

---

## 5. The two stages, because the powerful test is not the one that was asked for

### 5.1 Stage A — is the de-vigged reference **more accurate** than Kalshi's price?

Before any gate, on **every** aligned observation at the anchor:

```
Brier_pin    = (fair_s - y)^2
Brier_kalshi = (mid_or_ask_s - y)^2          # both reported; ask is executable
Δ            = Brier_kalshi - Brier_pin      # positive => Pinnacle is sharper
```

Paired, one observation per event, CI bootstrapped over events. Log-loss
reported alongside.

**This is the informative test and it is far more powerful than the gated one**,
because it uses every event rather than only the qualifying tail, and because the
paired difference cancels the enormous variance of a binary payoff.

> **Stage A is a gate on Stage B.** If the de-vigged Pinnacle fair value is
> **not** a better forecast than Kalshi's own price, then no threshold on
> `fair − ask` can be a real edge, and any positive gated P&L is selection on
> noise. **If Stage A's CI does not exclude zero in Pinnacle's favour, Stage B is
> reported as underpowered-or-null and no strategy claim is made.**

This is also the direct analogue of **T012** on tennis (r = 0.9878, MAD 1.95¢ vs
a 2.44¢ bar — null), which is the reason the expectation in §7 is what it is.

### 5.2 Stage B — the gated test, exactly as asked

Only if Stage A passes. `edge > cost` → one entry per event → hold to settlement
→ mean net cents per contract, CI clustered on event, reported beside:

- **the naive benchmarks**: `H0-RANDOM` (random side of every joined event) and
  `H0-ALLYES` (buy the home side of every joined event), both at the same anchor
  and cost;
- **the qualifying rate** `q` (events producing an entry / events joined);
- **the MDE**, always, per §6.4 of [CLAUDE.md](../CLAUDE.md).

### 5.3 Stage C — the holdout

**The newest 30% of joined events by game start is SEALED** and touched **once**,
only by a design that has already cleared Stage A, Stage B, BH-FDR and N1. A
second look voids it. Because the panel grows forward in time, the holdout is
defined **at the moment of the first Stage B run** and frozen by writing the
event list to `reports/devig_holdout.json` at that instant.

---

## 6. Decision rules, fixed now

1. **BH-FDR at q = 0.10** across the whole H11 grid — 3 de-vig methods × 3
   anchor windows × 4 slippage values = **36 cells**, one denominator. Cancelled
   or empty cells stay in the denominator.
2. **Two-sided p-values.** A systematic *negative* edge is a finding here — it
   is the fifth confirmation that Kalshi is the sharp line.
3. **The cost bar is recomputed per trade** from the recorded ask and
   `common/kalshi_fees.py`. Never hardcoded, never taken from RESULTS.md's 1.0¢.
4. **Every null reports its MDE.** Every CI is clustered on `event_ticker` and
   prints effective n beside nominal n.
5. **The surface, not the peak.** Each surviving cell is labelled PEAK or
   PLATEAU by the neighbour-gap rule already used in RESULTS.md.
6. **Monotone strengthening with join precision is CONTAMINATION, not
   evidence** — GUARDS #10, and the error H10 already tripped.
7. **N1 gates the run.** A positive gated result on the mismatched-pair placebo
   means nothing from that run is reportable.
8. **The asymmetric bar, because of §4.2.** MLB is pre-declared efficient on
   four independent measurements. A positive H11 result must therefore clear
   **all six** of: Stage A significant in Pinnacle's favour · BH-FDR · CI above
   the cost bar · N1 clean · a PLATEAU not a PEAK · and the sealed holdout.
   **Fewer than six and it is recorded as a lead, not a finding.**
9. **Capacity is reported, never assumed.** Pinnacle `maxRiskStake` and Kalshi
   `depth5` at the entry timestamp accompany every surviving cell. This repo's
   recurring shape is *a real effect smaller than the cost of reaching it*, and
   the esports arb author's edge died at 38% of gross to adverse selection.

---

## 7. What I expect, written down so a null is a measurement

**I expect Stage A to fail** — that is, the de-vigged Pinnacle moneyline will
**not** be a significantly better forecast of an MLB game than Kalshi's own ask,
and Stage B will consequently never be reportable. The reasons, all of them
already measured in this repo:

- **T012** — the identical test on tennis against Betfair: r = 0.9878, MAD 1.95¢
  against a 2.44¢ bar. Null.
- **MLB moneyline vs de-vigged DraftKings** — 0.37¢, 0 of 26 over the bar.
- **RESULTS_CROSSVENUE** — median buy edge **negative under all three de-vig
  methods** on esports, at 7-second alignment, against the sharpest book in the
  world.
- **0 of 148** structural cells on this very family.
- **~45 corrections in this programme and every one shrank the edge.**

And one that cuts the other way and is why it is still worth running: **the only
strategy in any corpus here with a public wallet and a reconciled four-line P&L
used exactly this mechanism** (+$8,293 arbitrage, −$3,184 unhedged residual,
−$134 cancellations, **+$4,973 net** over 3,858 fills) — *and its author switched
it off* as his win rate went 50.2 → 48.3 → 43.4% monthly. So the mechanism has
produced money for someone, on a venue that pays maker rebates, in a passive
implementation, and it decayed. **H11 is the taker version of a strategy whose
only known success was passive.** That asymmetry is stated now, before the
result, because it is the most likely way this test is a fair test of the wrong
thing.

## 8. What would make me revise

Stage A significant in Pinnacle's favour with a clustered CI excluding zero, on
≥ the pre-registered event count, with N1 clean. **That alone would be the most
interesting result this project has produced**, independently of whether any
gated P&L follows, because it would mean a free public endpoint carries
information Kalshi's book does not.

---

## 9. Sample size — the formula now, the numbers when `q` is measured

Fixed before measurement so the target cannot be moved to meet the data.

**Stage B (gated P&L).** Per-contract payoff on a binary at price `p` with win
probability `π` has `σ ≈ 100·√(π(1−π))` cents — **≈ 50¢ at a coin-flip**, which
is where MLB moneylines sit. Two-sided α = 0.05, power 0.80:

```
n_trades = (1.96 + 0.84)^2 · σ² / δ²  =  7.84 · 2500 / δ²
n_events = n_trades / q               q = P(an event produces an entry)
```

| detectable edge δ | n_trades | n_events at q = 0.05 | at q = 0.10 | at q = 0.25 |
|---|---|---|---|---|
| 2¢ | 4,900 | 98,000 | 49,000 | 19,600 |
| 3¢ | 2,178 | 43,560 | 21,780 | 8,712 |
| **5¢** | **784** | 15,680 | **7,840** | 3,136 |
| 8¢ | 306 | 6,120 | 3,060 | 1,224 |

**Stage A (paired Brier).** Far cheaper, because the paired difference cancels
the binary variance:

```
Δ_e = (p_kalshi − y)² − (p_pin − y)² = (p_kalshi − p_pin)·(p_kalshi + p_pin − 2y)
n_events = 7.84 · σ_Δ² / δ_Δ²
```

`σ_Δ` **must be measured, not assumed**, and will be, at the first run. As an
order-of-magnitude placeholder only: the two venues differ by ~1–2¢, giving
`σ_Δ ≈ 0.015`, so detecting `δ_Δ = 0.002` needs **≈ 440 events**. **That
placeholder is not a target** — the real figure is whatever `σ_Δ` turns out to
be, and it is reported before the Brier difference is.

The measured `q`, the measured `σ_Δ`, and the resulting event counts go in
`RESULTS_DEVIG.md`. **They were not known when this file was committed.**
