# PROGRESS.md

Timestamped log. All times UTC. Session started 2026-07-31 ~23:35 UTC.

## Phase 0 — Universe and specification

- [x] `23:38` Environment survey. **Machine is the laptop; desktop crypto data absent.** Only user profile is `gianf`; `C:\Users\gianf\kalshi` is the unrelated tennis project.
- [x] `23:40` Connectivity probe, 23 endpoints. **18/23 reachable.** `data.binance.vision` works despite `api.binance.com` being geo-blocked (451). Bybit blocked (403). `polygon-rpc.com` disabled; Goldsky subgraph works.
- [x] `23:45` Kalshi crypto series enumeration — **272 series**, not 1.
- [x] `23:52` **Strike convention resolved.** Hourly/daily use fixed round-number ladders ($250 grid, 80–188 legs); only `*15M` is minted ATM.
- [x] `23:52` **Settlement resolved.** 60-second average of CF Benchmarks, for both strike and settle. Not a point sample.
- [x] `23:55` Tick structure: `tapered_deci_cent` (0.1¢ tails) on `*15M`; flat `linear_cent` on hourly ladders.
- [x] `00:02` Polymarket fee probe #1 — **wrong** (closed 2023 sports markets).
- [x] `00:05` ~~**Polymarket fees resolved.** Crypto taker `0.07·p·(1−p)` — identical to Kalshi.~~ **RETRACTED (LEDGER C015)** — this was read from published documentation, which matched **0.0% of 4,310 real on-chain fills**. The true fee is a different *shape* and a higher rate: **`0.10 · min(p, 1−p)`**, verified at median relative error 0.000000 and reproduced independently on 5,362 fills (W015). Polymarket is **2.86× Kalshi at 50¢**, not at parity. Corrected in `MORNING_REPORT.md` §00. **Maker 0**, plus rebate — maker exemption remains UNVERIFIED.
- [x] `00:08` `src/fees.py` + 15 passing tests; all three reference points reproduced in exact decimal.
- [x] `00:30` `docs/venue_spec.md`, `docs/venue_comparison.md`.
- [x] `00:45` `PREREGISTRATION.md`, `HYPOTHESIS_LEDGER.md`.

## Phase 1 — Data

- [x] `00:10` **Polymarket history assessed.** No `orders` entity → books never public. Subgraph 2022-11-21 → **2026-04-28 (3mo stale)**. Tape = ~10-min rolling window. Settled short-dated markets stop resolving (1/21 days).
- [x] `00:13` **Live recorder launched** (Kalshi 10 series + Polymarket books/trades). Write-on-change: 91% row reduction.
- [x] `00:38` Recorder restarted with **keyframes** every 24 cycles — write-on-change alone never captures a complete ladder, making `A1` untestable.
- [x] `00:20` Kalshi settled pull launched.
- [x] `01:05` **Duplicate-writer incident** caught and resolved; all 8 files re-validated clean.
- [x] `01:05` Settled data: **`KXBTC`/`KXBTCD` 291,840/292,160 markets, 1,593 events, 68 days.** `KXETH`/`KXETHD` 186,945 each.
- [x] `00:25` Deribit chain + DVOL captured. BTC DVOL 35.53, ETH 50.17. Digital extraction `−dC/dK` verified monotone.
- [ ] Spot history from CF Benchmarks constituents + `data.binance.vision` — **not started**
- [ ] Derivatives (funding, OI, basis, liquidations) via OKX/Deribit — **not started**

## Phase 2 — Microstructure

- [ ] Blocked on recorder depth. Counterparty fingerprint, depth-vs-TTE, adverse selection all pending.

## Phase 3 — Volatility

- [ ] Not started. Gated on spot history.

## Phase 4 — Fair value

- [x] `01:10` **`C8` round-number pinning — run and retracted.** 6/20 tests survived BH but all are artifacts (repulsion not attraction; invalid null where few periods span the range; half the tests duplicated).
- [ ] `M1`–`M7` not started.
- [ ] `L1`–`L4` leak audit not started — **`L4` is the gate**.

## Phase 5 — Strategies

- [x] `01:00` **`A2` monotonicity: 0 violations / 3,187 scans.**
- [x] `01:00` **`A1` bucket sum: 1 violation / 1,135 complete scans, −0.93¢ net.**
- [ ] `E-A`–`E-I` pending. **`E-C` (maker) is the priority.**

## Phase 1 (2026-08-01) — Deribit-relative pricing test

- [x] `01:20` **TASK 1 — Polymarket fee RESOLVED empirically.** On-chain form is
  `0.10 × min(p, 1−p)` per share, **not** the documented `0.07·p·(1−p)`.
  Verified on 4,310 fee-bearing fills (2026-04-20→27): median rel. err
  **0.000000**, 100% within 1%, both branches. **Polymarket is 2.86× Kalshi at
  50¢**, 1.5× in the wings. `fees.py` corrected, 19 tests passing.
  `venue_comparison.md` headline reversed.
- [x] `01:22` Fees were **zero before ~2026-02**: 0 fee-bearing fills in the
  2023-06 / 2024-06 / 2025-06 / 2026-01 windows, 81% in 2026-03, 95% in 2026-04.
  Dates the fee introduction.
- [x] `01:25` Maker exemption **UNVERIFIED** — `maker_base_fee` is a market
  maximum, not a signed rate; on-chain record ends 2026-04-28. `E-C` demoted.
- [x] `01:35` **TASK 2 — Deribit pricer built and validated.** Bisection IV
  inversion from bid/ask prices, per-expiry forward, total-variance × log-moneyness
  fit, no-arb checks, bid/ask confidence band, term interpolation with
  extrapolation flags, settlement-averaging adjustment. Calendar arbitrage
  **0 violations / 50 pairs** both assets.
- [x] `01:33` Caught a field trap: `get_book_summary_by_currency` returns **no
  `bid_iv`/`ask_iv`** (null on all 870) — the first build silently discarded the
  entire chain. Also switched to the per-expiry **forward** (63,964 vs 62,910
  spot, 1.7% carry).
- [x] `01:40` **TASK 3 — PREMISE DISPROVED, thread stopped.** Deribit's shortest
  usable expiry **54.2 h** vs Kalshi ladder median lifetime **1.0 h**; only 0.1%
  overlap. Logged `X4`, cancelled not tested.
- [x] `01:38` Settled Kalshi records carry **no decision-time quote** (100% of
  bid/ask at 0/1 extremes) — but **recovered**: the candlesticks endpoint
  returns per-minute bid/ask OHLC over the full 68 days. `B1` unblocked.
- [x] `01:50` **TASK 4 — fat tails CONFIRMED** (`C9`). Excess kurtosis 13.08/12.85,
  Student-t ν≈2.03, Hill α 2.55/2.69, 3σ ratio **7.0×**, 4σ **140×**. Outliers
  verified genuine. BTC/ETH not independent (r=0.891) → one finding, not two.
- [x] `01:52` **`C9-econ` WITHDRAWN** — the "1.5–1.9¢ tradeable" column
  benchmarked a Gaussian strawman, not Kalshi's mid. Benchmark inflation.
- [x] `01:55` **TASK 5 — recorders healthy throughout.** 1 process (no
  duplicates), 76,407 Kalshi quotes, 18,343 Polymarket books, 5,245 trades,
  **54,936 keyframes** landing.
- [ ] `B1` vs-mid via candlesticks — **next**
- [ ] `L1`–`L4` leak audit incl. synthetic control — not run

## Phase 2 (2026-08-01) — B1: does anything beat the Kalshi mid?

- [x] `02:10` Recorders verified healthy and left running throughout.
- [x] `02:12` Candlestick endpoint characterised. Serves the **full 68 days**
  (oldest event 2026-05-25 returns candles). Latency ~427 ms. `period_interval`
  1 / 60 / 1440 all supported.
- [x] `02:14` **Across the FULL 60-strike ladder, only ~3 strikes carry a
  two-sided quote.** |K−settle| ≥ $893 had **zero** two-sided minutes across all
  61 candles. The wings have an ask but **no bid** — so no mid exists there, and
  the "cheap wings" premise needs re-examination (see MORNING_REPORT).
- [x] `03:05` **Refinement:** that figure describes the *whole* ladder. Selecting
  the 8 strikes nearest the **anchor** lands on the liquid core and retains
  **78%** of candles as two-sided (1,861 usable rows from 2,382 candles over the
  first 5 events). So the panel is dense where quotes exist; it is the far wings
  that are unquotable, not the tradeable band.
- [x] `03:05` Confirmed **HTTP 429s** are occurring (3 of 8 probe calls) from
  contention with the other session's 9-worker Kalshi pull. Build still runs at
  5.4 events/min via retry/backoff; single-threaded by design.
- [x] `02:15` **TASK 4 SYNTHETIC CONTROL — GATE PASSED, all three arms.**
  A NULL: diff −0.000028, CI [−0.00013, +0.00008] contains zero, p=0.593.
  B POWER: detects 15% wing bias (p<1e-4) **and** 5% (sensitivity floor).
  C LEAK: catches outcome-in-feature (Brier 0.0004 vs 0.1032).
  Pipeline neither hallucinates nor is blind.
- [x] `02:20` `PREREGISTRATION.md` Phase 2 addendum written **before** any
  model was scored. Pre-committed direction: **the mid wins every one.**
- [x] `02:30` Look-ahead discipline fixed in the panel design: strikes are
  selected by distance from the **previous event's settlement** (the anchor,
  knowable at this event's open), **never** from this event's settlement.
  Asserted in code.
- [x] `02:40` **Spot pulled and VALIDATED against BRTI.** Coinbase BTC-USD 1m,
  **99,402 minutes, 99.98% coverage**, 11 small gaps. Basis vs the 1,593
  `expiration_value` boundaries: mean **+1.25 bp**, median |diff| 1.65 bp
  (**$10.35**), p99 9.96 bp ($62.65), max 22.56 bp. Mean basis corrected out,
  fitted on the first half only; residual sd 2.76 bp carried as noise.
- [x] `02:45` `docs/GO_NO_GO.md` written **before** any Task 5 result, with a
  power calculation derived from the synthetic control's measured sensitivity
  (**≥200 events minimum**).
- [ ] `02:50` Panel build running (250 events × 8 strikes, single-threaded to
  avoid contention with another session's 9-worker Kalshi pull on this machine).
- [x] `03:15` Analysis pipeline **dry-run on the first 13 panel events** — a
  rehearsal, not a result. Caught a real defect: the BRTI basis estimator
  iterated *markets* not *settlement boundaries* (n=5,908 vs 1,593 real events),
  over-weighting events by strike count. Fixed by deduping on close timestamp.
- [x] `03:30` **TASK 6 recorder health — PASS.**
  1 recorder instance (no duplicate writers). Kalshi content validation: prices
  in [0,1], 6/4000 rows with `event_after_recv` (≈0.15%, server-clock skew,
  logged). Polymarket books: **zero** issues, median depth **70 levels**.
  Keyframes **3,507/4,000** landing. Gaps: kalshi_quotes 0 >60s, poly_books 1,
  poly_trades 29 (expected — trades are sparse). Written to
  `data/gaps_report.md`.
- [x] `04:05` **TASK 1 panel complete.** 2,000 calls → 118,233 candles →
  **89,819 rows / 250 events / 1,968 markets / 10 ISO weeks**
  (2026-05-25 → 2026-07-30). Dropped: 28,401 one-sided (24%), 6 spread >10¢,
  7 non-positive τ, 4 HTTP errors. 0 malformed rows.
- [x] `04:10` **TASK 3 HEADLINE — THE MID WINS. No model beats it.**
  M1 +0.000261 (tie), **M2 −0.000081 (tie, p=0.942)**, M3 +0.003703 (MID),
  M3t +0.022455 (MID). Log loss: mid 0.3766 vs best model 0.3817.
- [x] `04:10` **M2 beats M1** (−0.000342, CI [−0.000436, −0.000242]) — the
  60-second-average settlement correction is real and measurable.
- [x] `04:10` **M3 is WORSE than M2** — Kalshi does not price its wings with a
  Gaussian. Retires `C9-econ` on evidence, not just on the benchmark argument.
- [x] `04:15` **`MIDCAL` — fifth false positive caught.** Raw reliability showed
  a +4.2pp gap (apparently tradeable at +1.00¢ net). Event clustering widens
  CIs ~10×; 14/17 buckets go to noise; best p=0.029 vs BH threshold 0.0059;
  magnitudes halve across periods; **opposite sign at n=13 in the dry run.**
- [x] `04:20` **`docs/GO_NO_GO.md` outcome filled: NO-GO.** Criterion 1 fails.
  Power confirmed adequate (250 ev vs 200 floor; observed effect an order of
  magnitude inside the detectable range).
- [x] `04:20` **TASK 5 NOT RUN — correctly gated.** No model beats the mid, so
  there is no signal for exit rules to extract. Recorded as a decision.

**Phase 2 verdict: Kalshi's crypto ladder is efficiently priced where it is
quotable. The pricing question is closed.**

## Phase 6/7 — Backtest and verdict

- [ ] Not started. `docs/GO_NO_GO.md` not yet written.

---

## Running state

- **Recorder** pid 22612, 8h run from 00:38 UTC, keyframes on.
- **Settled pull** pid 9212, working through the series list.
- **Money:** none at risk. No order-placement endpoint imported anywhere; no wallet; every pull read-only and unauthenticated.
