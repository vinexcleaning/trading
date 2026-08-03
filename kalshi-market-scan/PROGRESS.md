# PROGRESS

Timestamped log. Session start 2026-07-30 ~07:00 UTC.

## Phase 0 — Ground truth ✅
- [x] 07:04 Enumerated series/markets: 7,493 series, 551,366 open markets, 87% combos
- [x] 07:10 Fee schedule verified from live series objects (fee_type, fee_multiplier)
- [x] 07:12 **Premise corrected:** no halved multiplier for KXINX/KXNASDAQ100
- [x] 07:20 **Rate limits measured:** 15 req/s = 0% 429, 25 req/s = 56% 429
- [x] 07:22 KXBTC15M settlement resolved: 60s mean of CF Benchmarks RTI (live API)
- [x] 07:25 **Structural finding:** strike = previous window's settle (99.86% of 6,261)
- [x] 07:30 Trades feed: anonymous, min_ts polls forward, combos filterable
- [x] 07:40 **Trading halt discovered:** trading_active=false 07:00-09:00 UTC
- [x] 03:41 docs/contract_spec.md written

## Phase 3 — Recorders ✅ (running)
- [x] 07:30 Kalshi tiered recorder live (tier1=24 @4rps, tier2=140 @2rps, trades, status)
- [x] 07:34 External recorder live (3 spot venues, OKX+Deribit perps, DVOL, chain, NWS)
- [x] 07:40 Fixed flush bug: writer early-returned on empty batches so time-flush never fired
- [x] 07:40 Added exchange-status worker so gaps are attributable
- [x] 03:54 Historical BTC/ETH 1-min candles: 102,716 each, 100% coverage
- [x] 03:43 Settled history: 6,271 KXBTC15M, ~5,200/weather family, 60k caps elsewhere

## Phase 1 — Screen ✅
- [x] 03:55 3,133 series scored, 1,112 killed
- [x] **Premise corrected:** weather is KXTEMP*/KXHIGH*, absent from /series entirely
- [x] 04:11 docs/shortlist.md with kill reasons and rubric critique
- [ ] Dimension 6 counterparty fingerprint — **blocked on ~3 days of recorded books**

## Phase 4 — Leak audit and synthetic control ✅
- [x] 03:35 First control design was mis-specified (mid = truth + noise); caught and fixed
- [x] 03:38 **Control PASSES:** 0/18 negative-control false positives, 3/6 positive detections
- [x] Added a positive control the brief did not ask for — negative-only suites pass trivially

## Phase 2 — Arb scanner ✅ (running)
- [x] 07:47 **Caught phantom 1,298c arb** on KXDJI (nested ladder, not bucket family)
- [x] 07:48 classify_family() + verify_bucket_coverage() + regression test
- [x] 42 scans, 0 violations — all during the halt, so not yet informative

## Phase 5 — BTC deep dive ✅
- [x] 03:58 Vol estimators, seasonality, jumps, tails on 102,716 candles
- [x] **Bug caught by assertion:** datetime64[us] vs [ns] made every price lookup miss
- [x] 03:58 31,310-row decision panel, leak assertions passing
- [x] 04:00 Settlement-aware correction confirmed: +7.5% Brier at 60s, decaying
- [x] 04:00 **Refuted:** seasonal-sigma correction does not improve forecasts
- [x] 04:00 **Refuted:** ETH does not lead BTC
- [x] 04:00 5 charts written

## Phase 6 — Copy trading ✅
- [x] 04:05 v1 run invalid: pseudo-replication (one +95pp wallet = 21 bets on 1 market)
- [x] 04:07 v2 at market level: **persistence confirmed**, rho=0.351, top decile +7.23pp
- [x] 04:08 Tests 3 and 4: mild edge decay, no adverse selection
- [x] 04:09 **Key finding:** edge is favourite-longshot bias, not wallet skill
- [ ] Kalshi flow following — **blocked on ~2 days of trade feed**
- [ ] `won` semantics unverified — **the #1 next action**

## Phase 7 — Strategy search ⬜ not run
Deliberately. Nothing cleared Phase 1 with a mechanism AND fillable liquidity, so there
was no candidate to sweep. Sweeping anyway is the 6,000-experiment trap.

## Phase 8 — Paper trader ⬜ not built
Correctly blocked: a paper trader needs a strategy, and no strategy passed Phase 9's bar.

## Phase 9 — Verdict ✅
- [x] 04:13 docs/GO_NO_GO.md — bar defined first, then filled in
- [x] 04:15 MORNING_REPORT.md

## Where I stopped
Recorders and arb scanner still running. The exchange reopens at 09:00 UTC; the scanner
and recorders will capture the first live session automatically. Everything else is
blocked on wall-clock recording time, not on work.
