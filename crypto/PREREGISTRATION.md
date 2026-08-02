# PREREGISTRATION.md

Written **2026-08-01 ~00:30 UTC**, before any strategy sweep is run. Every
hypothesis and parameter grid below is fixed at this timestamp. Anything added
later is marked `[POST-HOC]` and is reported separately from the pre-registered
set, never merged into it.

Multiple-comparison control: **Benjamini–Hochberg across the entire
`HYPOTHESIS_LEDGER.md`**, not per market, per venue, or per family. The total
count is reported in `MORNING_REPORT.md` §4.

---

## 0. Scope changes forced by Phase 0 findings

Three pre-registered items are **cancelled before running**, because Phase 0
established they are not answerable on this machine. Cancelling them here rather
than silently dropping them keeps the denominator honest.

| id | item | why cancelled |
|---|---|---|
| `X1` | Polymarket historical order-book replay | books were never public on any venue; the subgraph has no `orders` entity |
| `X2` | Polymarket historical short-dated backtest | settled short-dated markets stop resolving on Gamma (1/21 days); tape is a ~10-min rolling window |
| `X3` | Kalshi order-book replay (Tier B) | no historical book endpoint; recorded books live only on the desktop |

Consequence: **all Tier B work in this session depends on data recorded from
~2026-08-01 00:13 UTC onward.** Everything else is Tier A (upper bound) and is
labelled as such.

---

## 1. Unit of observation — fixed in advance

Failure mode #1 (pseudo-replication, 4 prior instances) is controlled by fixing
the clustering unit *before* any confidence interval is computed.

| analysis | unit of observation | clustered by |
|---|---|---|
| contract-level calibration | one settled contract | **event** (all strikes in one expiry share one settlement) |
| strategy P&L | one round trip | **event** |
| ladder / bucket arbitrage | one ladder snapshot | **event** |
| cross-venue gap | one matched contract pair | **the shared underlying window** |
| vol seasonality | one window | **calendar day** |

**Never** cluster by candle, by quote, by fill, or by book snapshot. A 188-strike
Kalshi ladder is **one** observation of the settlement, not 188. This is the
single most important line in this document: the hourly BTC ladder tempts a 188×
overstatement of n, which is exactly the error made four times before.

Every reported CI states its unit and its clustered n.

---

## 2. Hypotheses

Each has a pre-committed direction, a test, and a stopping rule. `H0` is always
"no effect / market is efficient".

### Group A — venue structure (model-free, no forecasting)

| id | hypothesis | test | pre-committed direction |
|---|---|---|---|
| `A1` | Kalshi bucket families sum to 100¢ net of fees | sum of `between` mids per event vs 100 | no violation |
| `A2` | Kalshi nested thresholds are monotone in strike | `greater` ladder monotonicity per event | no violation |
| `A3` | Cross-expiry consistency: four 15m constrain the hourly | implied vs quoted | no violation |
| `A4` | Cross-venue Kalshi↔Polymarket gap exceeds combined round-trip cost | matched-pair gap distribution | no exploitable gap |
| `A5` | Violations that do occur persist >30s with real depth | dwell-time distribution | violations are <200ms artifacts |

`A1`–`A3` need no model and are the cheapest possible tests. **Reported net of
the spread actually crossed on every leg and net of fees**, with dwell time.

### Group B — calibration vs the venue's own mid (the headline)

| id | hypothesis | test |
|---|---|---|
| `B1` | our model beats the venue mid on Brier, per series | paired Brier difference, clustered by event |
| `B2` | …and on log loss | paired log-loss difference |
| `B3` | edge localises by time-to-expiry | Brier diff within TTE buckets |
| `B4` | edge localises by distance-from-strike | Brier diff within \|ln(S/K)/√τ\| buckets |
| `B5` | edge localises by hour-of-day | Brier diff by UTC hour |
| `B6` | edge localises by vol regime | Brier diff by prev-window vol decile |

**The benchmark is the venue's own mid at the decision timestamp. Nothing else
counts.** Not climatology, not a coinflip, not a near-settlement price
(failure mode #5, 5 prior instances). Pre-committed: if the mid wins on `B1`,
the series is declared no-edge and `B3`–`B6` are reported but not used to
resurrect it.

### Group C — volatility (Phase 3)

| id | hypothesis | pre-committed direction |
|---|---|---|
| `C1` | HAR-RV beats EWMA out-of-sample on QLIKE | HAR better |
| `C2` | realized vol has minute-of-day seasonality | yes, significant |
| `C3` | Friday 08:00 UTC (Deribit expiry) shows elevated vol / strike pinning | elevated |
| `C4` | funding resets 00/08/16 UTC show elevated vol | elevated |
| `C5` | 13:30 / 14:00 UTC (US data, equity open) show elevated vol | elevated |
| `C6` | 21:00–22:00 UTC (CME settle) shows elevated vol | elevated |
| `C7` | CME weekend gaps fill; measure rate and time-to-fill | majority fill |
| `C8` | spot pins near round strikes more than a random walk predicts | pinning present |
| `C9` | returns are fat-tailed; Gaussian misprices tails | Student-t ν < 10 |
| `C10` | next-window vol depends on prev-window vol decile | positive dependence |

`C3`–`C6` and `C8` are the "structural times" set reported in
`MORNING_REPORT.md` §5. **All are pre-registered here including the ones I
expect to fail**, so a null on `C8` is reportable rather than quietly dropped.

### Group D — counterparty / microstructure (Phase 2)

| id | hypothesis | pre-committed direction |
|---|---|---|
| `D1` | taker flow one-sidedness is near-balanced on liquid crypto series | balanced (≈0.0–0.1), i.e. efficient |
| `D2` | depth at touch collapses as time-to-expiry → 0 | collapses |
| `D3` | informational edge and available liquidity are anti-correlated | anti-correlated |
| `D4` | resting orders fill disproportionately just before adverse moves | adverse selection present |
| `D5` | series rank from retail-like to bot-like on order-size/round-lot structure | Polymarket 5m most bot-like |

`D2`+`D3` are **decisive independent of any fee argument**: if the model is most
confident exactly where no liquidity exists, the edge is untradeable.

### Group E — strategy families (Phase 5)

Pre-registered parameter grids. Every cell is one ledger row.

| id | family | grid |
|---|---|---|
| `E-A` | fair-value divergence | threshold ∈ {2,3,4,5,7,10,15}¢ × {taker, maker} × {Kalshi, Poly} |
| `E-B` | hold-to-settlement | entry TTE ∈ {full, <50%, <25%} × threshold as above |
| `E-C` | **maker / market-making** | quote offset ∈ {1,2,3,5}¢ × inventory cap ∈ {50,100,250} × {Kalshi, Poly} |
| `E-D` | tail entries | price band ∈ {5–10, 10–20, 80–90, 90–95}¢ |
| `E-E` | late-window certainty | TTE ∈ {30,60,120}s × threshold ∈ {2,5,10}¢ |
| `E-F` | Deribit-relative | divergence ∈ {2,3,5,10}¢ vs implied digital |
| `E-G` | cross-venue | gap ∈ {2,3,5,10}¢, net of both round trips |
| `E-H` | time-of-day restricted | the above × {structural hours, rest} |
| `E-I` | vol-regime conditional | the above × prev-window vol tercile |

**`E-C` is the priority.** Phase 0 established it is the only axis on which the
venues materially differ (Polymarket maker fee 0 vs Kalshi ~0.44¢ at 50¢) and it
is untested in this project's entire history.

Maker sizing/fill assumptions, fixed now:
- **last-in-queue always.** A resting order fills only when the book trades
  *through* its price, never merely *to* it.
- adverse selection measured explicitly, not assumed away.
- partial fills honest; no assumed full fill at the touch.
- **fractional Kelly ≤ 0.25 in simulation. No martingale, no doubling, no
  averaging down.** Simulation only — no order-placement endpoint is imported
  anywhere in this repo.

---

## 2b. PHASE 2 ADDENDUM — pre-registered 2026-08-01 ~02:20 UTC

Written before the panel was built and before any model was scored. The
synthetic control (§4 `L4`) was run **first**, at 02:15 UTC, and passed all
three arms — see `reports/synthetic_control.json`.

### The headline test

| id | hypothesis | pre-committed direction |
|---|---|---|
| `B1-M1` | M1 (driftless GBM) beats the Kalshi mid on Brier | **mid wins** |
| `B1-M2` | M2 (settlement-aware, 60 s average) beats the mid | mid wins |
| `B1-M3` | M3 (empirical fat-tailed) beats the mid | mid wins |
| `B1-M4` | M4 (seasonal σ) beats the mid | mid wins |
| `B1-M5` | M5 (blended σ incl. DVOL) beats the mid | mid wins |
| `B1-M6` | M6 (gradient-boosted) beats the mid | mid wins |

**Pre-committed prior: the mid wins every one.** 24 corrections in this project
have every time shrunk the edge. Stating the expected direction in advance is
what makes a surprise interpretable rather than a licence to hunt.

**Benchmark: Kalshi's own mid at the decision timestamp. Nothing else.** Where
there is no two-sided quote there is no mid, and those rows are excluded rather
than back-filled with a fabricated mid — back-filling would be benchmark
inflation by construction.

**Each model must beat the previous out-of-sample to justify itself.** M6 must
clearly beat M5 or be discarded, not retained "for completeness".

### Model-ladder ordering test

| id | hypothesis |
|---|---|
| `B1-ORD` | each of M2…M6 beats its predecessor on out-of-sample Brier |

`M2` is expected to beat `M1` **by construction** — settlement is a 60-second
average, so M1's point-sample terminal variance is simply wrong. If M2 does not
beat M1, the pipeline is suspect and that is reported as a defect, not a null.

### Localisation buckets (run only if a model beats the mid)

`|ln(S/K)/√τ|`, time-to-expiry, ladder position (wing vs near-money),
hour-of-day UTC, vol regime (prev-window vol tercile), spread width, volume.
**Each bucket is one ledger row.** A diffuse advantage spread evenly across all
buckets is treated as a leak, not an edge.

### Cost test

Any bucket advantage is reported net of the Kalshi taker fee at that price
(exact decimal, `fees.py`) **and** the actual spread crossed. Maker variants use
one quarter of taker, last-in-queue, fill only on trade-through.

### Panel hygiene, fixed in advance

| rule | threshold |
|---|---|
| drop minutes with no two-sided quote | `not (0 < bid < ask < 1)` |
| drop minutes with spread > threshold | **> 10¢** — a quote that wide is not actionable; count reported |
| unit of observation | **EVENT**; bootstrap resamples events, never rows |
| splits | walk-forward, strictly time-ordered. **No shuffled CV, ever.** |

### Task 5 gate

The strategy sweep runs **only if** a model beats the mid in Task 3. Sweeping
exit rules over a signal with no edge produces a strategy that dies live, and
that has already happened in this project. **If the base result is null, Task 5
is not run** and that is recorded as a decision, not an omission.

---

## 3. Models (Phase 4), in the order each must beat the previous

| id | model | must beat |
|---|---|---|
| `M1` | driftless GBM `Φ(ln(S/K)/(σ√τ))` | — (the baseline everything beats or dies) |
| `M2` | settlement-aware (terminal = mean of final 60s) | `M1` |
| `M3` | fat-tailed (Student-t / empirical) | `M2` |
| `M4` | seasonal σ from the C2 minute-of-day curve | `M3` |
| `M5` | blended σ (realized + HAR + Deribit implied), weights fit OOS | `M4` |
| `M6` | Deribit-implied risk-neutral digital directly | `M5` |
| `M7` | gradient-boosted on `ln(S/K)/√τ`, τ, vol state, hour, flow | **`M6`, clearly** — else discarded |

`M2` is a **correctness fix, not a horse in the race**: Phase 0 established both
the strike and the settle are 60-second averages, so `M1`'s point-sample terminal
distribution is simply wrong and will overprice tails. Expected to win by
construction; if it does not, the pipeline is suspect.

Scoring for all: Brier + log loss, **walk-forward, strictly time-ordered
splits, no shuffled CV ever**, reliability curves in 5% buckets with counts.

---

## 4. Leak audit — pre-committed to run EARLY, not last

Failure mode #2. All four must pass before any result is believed.

| id | test | pass condition |
|---|---|---|
| `L1` | feature knowability assertion | every feature's knowability ts < decision ts, asserted in code |
| `L2` | shift-features-forward | edge disappears when features are shifted into the future |
| `L3` | shuffled-label | edge ≈ 0 on shuffled outcomes |
| `L4` | **synthetic-noise control** | full pipeline on a GBM random walk matched to BTC vol with random outcomes finds **no** edge |

**`L4` is the gate.** If the pipeline finds edge on noise, everything else in the
session is void and gets retracted, not caveated.

---

## 5. Stopping rules and what counts as a result

Fixed now so they cannot be moved later:

1. A candidate needs a **mechanism** — one sentence on why the counterparty is
   wrong and why that error persists. No mechanism, no candidate. This is a
   hard gate, applied before statistics.
2. Fee-inclusive per-trade edge with a **CI excluding zero**, clustered at the
   unit in §1.
3. Consistent across **two disjoint time periods** and across time-of-day
   buckets.
4. Survives **BH-FDR across the whole ledger**.
5. Report **full parameter surfaces, not peaks.** A sharp isolated peak is
   overfitting; a broad plateau may be real. Each candidate is labelled which.
6. Deflated Sharpe accounting for the number of trials.
7. Every result compared against the **fee-adjusted-coinflip null**, not a raw
   coinflip.

**A well-evidenced null is a successful outcome.** Assume efficiency until
disproven. If a positive result appears, assume it is overstated and hunt for
the reason before reporting it — 20 of 129 prior claims in this project were
retracted and *every single retraction shrank the edge*. None ever revealed a
larger effect.
