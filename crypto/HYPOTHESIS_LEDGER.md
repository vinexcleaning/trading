# HYPOTHESIS_LEDGER.md

Every model / parameter / market combination evaluated this session. BH-FDR is
applied **across this entire table**, not per market or per venue. The total
count is reported in `MORNING_REPORT.md` §4.

Status: `RUN` (evaluated), `PENDING` (pre-registered, not yet run),
`CANCELLED` (pre-registered but unanswerable on this machine — cancelled before
running, kept here so the denominator stays honest).

Last updated 2026-08-01 00:45 UTC.

---

## Evaluated

| # | id | hypothesis | unit | n (clustered) | result | p | status |
|---|---|---|---|---|---|---|---|
| 1 | `A2` | Kalshi `greater` ladders are monotone in strike (KXBTCD/KXETHD/KXSOLD/KXXRPD) | ladder snapshot, clustered by **event** | 3,187 scans / 26 events / 10.5 min | **0 violations, gross or net** | — (no test needed; zero events) | RUN |
| 2 | `A1` | Kalshi `between` bucket families sum to 100¢ (KXBTC/KXETH/KXXRP) | complete ladder snapshot, clustered by **event** | 1,135 complete scans / 26 events | **1 gross violation (sum = 1.0100, +1.00¢), 0 profitable net of fees** | — | RUN |
| 3 | `C8` | BTC/ETH settlements pin near round numbers | **event** (one hourly settlement) | 1,593 events, 68 days | **NOT SUPPORTED — 6/20 nominally "significant" results are artifacts of an invalid null; see below** | invalid | RUN, **retracted** |
| 4 | `F1` | Polymarket fee = documented `0.07·p(1−p)` | on-chain fill | 4,310 fee-bearing fills, 2026-04-20→27 | **REJECTED.** True form is `0.10·min(p,1−p)`; median rel. err 0.000000, 100% within 1% | — (exact) | RUN |
| 5 | `C9` | hourly BTC/ETH returns are fat-tailed vs Gaussian | **event** (one hourly settlement) | 1,582 returns / 1,593 events, 68 days | **SUPPORTED, strongly.** Excess kurtosis 13.08 (BTC) / 12.85 (ETH); Student-t ν≈2.03/2.02; Hill α 2.55/2.69; JB p≈0 | p < 1e-300 | RUN |
| 6 | `C9-econ` | the tail mispricing is economically tradeable | — | — | **NOT ESTABLISHED — benchmark inflation; see below** | invalid | RUN, **withdrawn** |
| 7 | `L4-A` | pipeline finds no edge on synthetic data with **no edge in it** | synthetic event | 1,500 events × 9 strikes | **PASS** — diff −0.000028, CI [−0.00013, +0.00008] **contains zero** | 0.593 | RUN |
| 8 | `L4-B` | pipeline **detects** a deliberately injected 15% wing bias | synthetic event | 1,500 events | **PASS** — diff −0.002655, CI [−0.00310, −0.00217] | <0.0001 | RUN |
| 9 | `L4-B5` | …and a 5% wing bias (sensitivity floor) | synthetic event | 1,500 events | **PASS** — diff −0.000334, CI [−0.00050, −0.00014] | <0.0001 | RUN |
| 10 | `L4-C` | pipeline **detects** outcome leaked into a feature | synthetic event | 1,500 events | **PASS** — Brier 0.0004 vs 0.1032 | <0.0001 | RUN |

**Pipeline validated on partial data before the full run.** The analysis was
dry-run against the first 13 events of the panel while the rest was still
building. This is a rehearsal, **not a result** — 13 events cannot support any
conclusion and none is drawn from it. It caught one real defect: the BRTI basis
estimator iterated *markets* rather than *settlement boundaries*, reporting
n=5,908 boundaries against 1,593 real events, because every market in an event
carries the same `expiration_value`. That over-weighted events by how many
strikes they happen to list. Fixed by deduplicating on the close timestamp.

### Notes on the two evaluated rows

**`A2` — clean null.** No monotonicity violation ever appeared, gross or net,
across 3,187 ladder scans. Nested thresholds are internally consistent.

**`A1` — one gross violation, and it is not tradeable.** A single `KXXRP`
snapshot had bids summing to 1.0100 — a 1.00¢ gross edge on a 75-leg ladder.
Crossing all 75 legs costs **1.93¢ in fees alone**, before any spread, so the
trade nets **−0.93¢**.

**Mechanism for the null:** the constraint is enforced not by arbitrageurs
racing to it but by the *width of the ladder itself*. A KXBTC hourly event has
80–188 legs; a KXXRP event 75. Any bucket-sum edge must exceed the sum of the
per-leg quadratic fees, which grows linearly in the number of legs while the
mispricing does not. At 75 legs the fee floor is ~1.9¢, so a violation must
exceed ~2¢ to be worth anything — and none did. **The ladder is wide enough that
legging it is self-defeating.** This is a structural reason the null should
persist, not a coincidence of a short sample.

**`C8` — a positive result that did not survive scrutiny.** The raw output looked
strong: 6 of 20 tests survived Benjamini–Hochberg with p ≈ 0, Rayleigh R up to
0.244, on n = 1,593 events. It is not real. Three independent reasons, any one
of which is disqualifying:

1. **The effects run the wrong way.** Every "significant" result is *repulsion*,
   not attraction: BTC near ±10% of a multiple of 5000 is **18.83%** vs 20%
   expected; ETH near a multiple of 50 is **13.81%**; ETH near 100 is 17.14%.
   The pre-registered hypothesis was pinning — attraction. Nothing found
   attraction anywhere.
2. **The null is invalid at exactly the levels that "worked".** The test assumes
   the fractional position within a round-number period is uniform, which holds
   only when the price range spans many periods. BTC's settlements span
   58,132–77,677 (19.5k) — about **4 periods** of 5000. ETH spans 1,522–2,135
   (612) — about **6 periods** of 100. Over so few periods the null is not
   uniformity of a fractional part; it is the actual 68-day distribution of the
   price, which is wherever BTC happened to trade. The diagnostic is decisive:
   **the tests that survive are precisely the ones with the fewest periods in
   range** (5000 for BTC; 50 and 100 for ETH), while every fine level where the
   uniform null is nearly valid (100, 250, 500 for BTC; 5, 10, 25 for ETH) is
   comfortably non-significant. That is the signature of a broken null, not of
   an effect.
3. **Half the tests were duplicates.** `KXBTC` and `KXBTCD` are two ladders over
   the *same* hourly settlements, so their settlement series are identical — the
   outputs match to every decimal. Likewise `KXETH`/`KXETHD`. Of 20 tests only
   **10 are distinct**; reporting 20 would be pseudo-replication (failure mode
   #1) at the test level.

**Verdict: `C8` is not supported, and no pinning claim is made.** A valid test
needs a null that preserves the realised price path — a block bootstrap or a
matched random walk — rather than assuming uniformity. Logged as `PENDING-VALID`
below. This is the session's second manufactured positive, and as with the
first, correcting it removed the effect entirely.

**`C9` — a real effect.** Hourly crypto returns are severely fat-tailed and the
outliers are genuine, not corruption: the largest BTC move (−5.05%,
2026-06-25 13:00→14:00) coincides with ETH −6.27% in the same hour, which is a
market event, not a bad `expiration_value`. Empirical vs Gaussian tail mass:

| threshold | P(Gaussian) | P(empirical) | ratio |
|---|---|---|---|
| 2σ | 0.0455 | 0.0506 | 1.11× |
| 2.5σ | 0.0124 | 0.0316 | 2.54× |
| 3σ | 0.0027 | 0.0190 | **7.0×** |
| 4σ | 0.00006 | 0.0089 | **140×** |

Two caveats that reduce this to **one** finding, not two:

- **BTC and ETH are not independent.** corr(hourly returns) = **0.891**, and
  **62%** of BTC's extreme hours are also ETH's. Counting them as two
  confirmations would be pseudo-replication at the asset level.
- **ν ≈ 2.03 sits on the infinite-variance boundary**, so the sample σ used to
  define "3σ" is itself unstable and dominated by a handful of observations.
  The *direction* is robust; the exact multipliers are not.

**`C9-econ` — withdrawn for benchmark inflation (failure mode #5).** The
analysis printed an "edge − fee" column showing 1.5–1.9¢ apparently tradeable at
2.5–3σ. That number is meaningless as stated: it is the gap between the
empirical distribution and **a Gaussian strawman**, and *nothing in this session
has shown that Kalshi prices its wings with a Gaussian*. The benchmark that
counts is Kalshi's own mid at the decision timestamp, which requires the
candlestick quotes and has not been run. A market that already prices fat tails
correctly offers zero edge no matter how fat the tails are. **No tradeable claim
is made.** The 1σ/1.5σ rows in the same table are negative (−12.6¢, −4.4¢),
which is simply the flip side of fat tails — more mass in the tails *and* the
centre, less in the shoulders — and is not an "edge" in either direction.

**Sample caveat on `A1`/`A2`, stated plainly:** 10.5 minutes of recording, 26
events. This is
a *preliminary* null, not a strong one. It extends prior work's "zero violations
in 1,083 scans" in kind (adding fee-inclusive accounting and the monotonicity
constraint) but not yet in duration. No FDR correction is applied to these two
rows because neither produced a positive to correct.

---

## Cancelled before running (Phase 0 findings)

| # | id | item | why |
|---|---|---|---|
| — | `X1` | Polymarket historical order-book replay | books were never public; subgraph has no `orders` entity — matching is off-chain |
| — | `X2` | Polymarket historical short-dated backtest | settled markets stop resolving on Gamma (1/21 days); tape is a ~10-min rolling window |
| — | `X3` | Kalshi order-book replay (Tier B) | no historical book endpoint; recorded books live only on the desktop |
| — | `X4` | **Deribit-vs-Kalshi comparison on the hourly ladders** | Deribit's shortest *usable* expiry is **54.2 h**; Kalshi ladder median lifetime is **1.0 h**, and only **0.1%** reach 54 h. A 54× extrapolation is not a reference price. Survives only for `KXBTC` weekly events (the 0.1%). |

These are **not** counted in the FDR denominator — they were never tested.

---

## Pending (pre-registered, awaiting data)

All gated on the live recorder started 2026-08-01 00:13 UTC (restarted 00:38
with keyframes) and on the Kalshi settled pull.

| id | hypothesis | gated on |
|---|---|---|
| `A3` | cross-expiry consistency (4×15m constrain the hourly) | recorder duration |
| `A4` | cross-venue Kalshi↔Polymarket gap vs combined cost | recorder + oracle question resolved |
| `A5` | violation dwell time >30s with real depth | more violations to measure |
| `B1`–`B6` | model vs the venue's own mid, and where edge localises | settled pull + recorder |
| `C1`–`C10` | volatility: HAR/EWMA, seasonality, structural times, CME gaps, round-number pinning, fat tails, clustering | spot history |
| `D1`–`D5` | counterparty fingerprint, depth vs TTE, adverse selection | recorder duration |
| `E-A`–`E-I` | all nine strategy families incl. **`E-C` maker/market-making** (the priority) | recorder duration |
| `M1`–`M7` | the seven-model ladder, each must beat the previous OOS | settled pull |
| `L1`–`L4` | leak audit incl. the **synthetic-noise control** (`L4`, the gate) | pipeline built |

| `C8-v2` | round-number pinning, with a null that preserves the realised price path (block bootstrap / matched random walk), deduplicated series | rewrite of `C8` |

## Phase 2 — B1: does anything beat the Kalshi mid?

Panel: 250 events / 89,806 market-minutes / 1,968 markets / 10 ISO weeks.
Unit of observation = **event**. All CIs bootstrap-resample events, not rows.

| # | id | hypothesis | n | result | p | status |
|---|---|---|---|---|---|---|
| 11 | `B1-M1` | M1 driftless GBM beats the mid | 250 ev | diff +0.000261, CI [−0.00157, +0.00219] | 0.781 | **tie — no** |
| 12 | `B1-M2` | M2 settlement-aware beats the mid | 250 ev | diff **−0.000081**, CI [−0.00188, +0.00182] | 0.942 | **tie — no** |
| 13 | `B1-M3` | M3 empirical fat-tail beats the mid | 250 ev | diff +0.003703, CI [+0.00150, +0.00600] | 0.001 | **MID WINS** |
| 14 | `B1-M3t` | M3t Student-t ν=2.03 beats the mid | 250 ev | diff +0.022455, CI [+0.01865, +0.02637] | <1e-4 | **MID WINS** |
| 15 | `B1-ORD-a` | M2 beats M1 (settlement-average correction) | 250 ev | diff **−0.000342**, CI [−0.000436, −0.000242] | <1e-3 | **CONFIRMED** |
| 16 | `B1-ORD-b` | M3 beats M2 | 250 ev | diff +0.003784, CI [+0.00182, +0.00582] | <1e-3 | **REJECTED — M3 is worse** |
| 17 | `MIDCAL` | the mid's calibration gap is real and tradeable | 250 ev × 17 buckets | 3 of 17 nominally significant; **0 survive BH within the family**; best candidate p=0.029 vs BH threshold 0.0059 | — | **NOT SUPPORTED** |

Plus **21 localisation buckets** (time-to-expiry ×5, |ln(S/K)/σ√τ| ×5, mid price
×7, spread ×4), **6 two-period splits**, and **17 stability re-tests**.

### `B1` — the headline null, and it is a strong one

**No model beats the mid.** Two tie, two lose. Log loss agrees (mid 0.3766, best
model 0.3817). Per `docs/GO_NO_GO.md` this is a NO-GO on criterion 1 and **Task
5 was not run**.

**The null is not underpowered.** 250 events against a pre-registered 200-event
floor; the synthetic control showed the pipeline detects a 5% wing bias, and the
observed M2 effect (0.000081) is more than an order of magnitude *inside* the
250-event CI half-width (~0.0019). The test could have found an effect several
times larger than anything present.

### `B1-ORD-a` — the one confirmed model improvement

M2 beats M1 with a CI excluding zero. Kalshi settles on a **60-second average**,
so the terminal variable is less variable than a point sample and correct prices
sit further from 50¢. Pre-registered as expected "by construction" and confirmed.
It is real, measurable, and still not enough to catch the market.

### `B1-M3` — fat tails make the forecast WORSE

M3 loses to the mid *and* to M2, both CIs excluding zero. **This retires
`C9-econ` on evidence.** Kalshi's mid does not price its wings with a Gaussian;
feeding it a fatter tail than it already uses actively degrades the forecast. The
tails are fat (`C9`); the market already knows.

### `MIDCAL` — the fifth false positive, killed by clustering

Raw reliability showed the mid's empirical rate exceeding its implied probability
by up to **+4.2pp** — a large apparent edge against a ~1.3¢ cost bar. Under
event clustering the CIs widen ~**10×** (the pseudo-replication factor for ~360
correlated minutes per event) and 14 of 17 buckets become indistinguishable from
zero. The one nominally tradeable bucket (5–10¢, net +1.00¢ at the ask) has
p=0.029 against a BH threshold of 0.0059. Magnitudes roughly halve between the
two disjoint halves, and **no bucket is significant in both**.

**The same statistic had the opposite sign on the 13-event dry run.** It was not
reported then, precisely because 13 events cannot support it — and the sign
flipped with more data.

---

**Running count: 17 hypotheses across all phases**, comprising **101 individual
tests** (34 from Phases 0–1; 67 from Phase 2 — 4 model-vs-mid, 2 ordering, 21
localisation, 6 two-period, 17 calibration buckets, 17 stability).

**Facts surviving correction: 2** — `C9` (returns are fat-tailed) and
`B1-ORD-a` (the settlement-average correction improves the model). Both are
descriptive; neither is an edge.

**Tradeable edges surviving correction: 0.**

**Five** apparent positives arose across the session and **all five were
withdrawn**:

| claim | headline | why it died |
|---|---|---|
| bucket-sum arbitrage | 464 violations at 96–97¢ | partial ladder — 3 of 80 buckets |
| round-number pinning | 6/20 survive BH, p≈0 | invalid null + duplicated series |
| Polymarket taker cost parity | "identical to Kalshi" | trusted docs over the venue's own API; on-chain says 2.86× |
| fat-tail economic edge | 1.5–1.9¢ net at 2.5–3σ | benchmarked against a Gaussian strawman, not Kalshi's mid |
| **mid calibration gap** | **+4.2pp, net +1.00¢ at the ask** | **no event clustering; CIs widen 10×, fails BH, halves between periods, and had the opposite sign at n=13** |

Consistent with the project's base rate: every one of the 20 prior retractions
shrank the edge, and none ever revealed a larger effect. That now holds for
**25**.

Worth noting what the failure modes were, since they were all different:
partial data, an invalid null, documentation over API, an invented benchmark,
and pseudo-replication. There is no single check that would have caught all
five — which is the argument for running all of them every time.

---

## Data-quality corrections applied to this ledger

Two false positives were caught and killed before they reached the report. Both
are logged because a ledger that only records surviving claims understates how
easy it is to manufacture an edge.

1. **464 "profitable bucket-sum violations at 96–97¢."** The recorder writes on
   change, so a forward-filled snapshot early in the recording holds only the
   tickers seen so far — 3 of 80 buckets summing to 0.03 look like a 97¢
   risk-free profit. Buying 3 buckets does not pay $1; it pays $1 only if the
   outcome lands in those 3. Fixed by requiring the **complete** ticker
   universe of the event **and** a contiguous tiling of the strike line. All
   464 vanished.
2. **0 complete scans after that fix** — because a KXBTC bucket event is
   `less` + N × `between` + `greater`, and the type filter rejected `greater`,
   while KXBTCD events are *all* `greater` and must never be summed (nested, not
   a partition). Fixed by requiring ≥1 `between` to treat an event as a
   partition.

Both are the same shape as failure mode #3: plausible counts, wrong content.
Neither would have been caught by checking row counts.
