# FAILURE_MODES.md — every instance of the five known patterns

Read-only audit, 2026-07-30. Instances are listed with file and line where a line exists.
A ✅ marks an instance the project **found and fixed itself** — those are recorded because
the pattern recurred, not as criticism. A ❌ marks one that is still live on disk.

---

## 1. Pseudo-replication — many observations from one underlying event treated as independent

**This is the dominant failure mode in this corpus. It has occurred at least nine times
across five independent codebases, and was caught seven times.**

| # | Where | The error | Status |
|---|---|---|---|
| 1.1 | P2 `scripts/copytrade_tests_v2.py:1-23` (docstring) | v1 treated each **fill** as independent. Top wallet: "+95.0pp over 21 bets — all 21 on ONE market". 12.3% of wallets with ≥20 fills traded <5 distinct markets. Manufactured 1,684 "significant" wallets | ✅ fixed — one row per (wallet, market), fills collapsed to VWAP |
| 1.2 | P2 `reports/vs_mid.json` | 2,543 book **snapshots** from 25 markets treated as independent; reported "MID BEATS US", CI [−0.0061, −0.0019] excluding zero. Clustering by market widened it ~5× to [−0.0168, +0.0100] and the significance evaporated | ✅ fixed in `vs_mid_clustered.json`. The unclustered file is still on disk but carries its own `caveat` field |
| 1.3 | P2 `reports/kalshi_longshot_bias.json` (v1) | 490,464 taker **fills** from 762 matches (644 per match) treated as independent → bucket edges of −20.9pp to +19.5pp with ±1pp CIs | ✅ fixed in v2 by clustering on match |
| 1.4 | P2 weather, `MORNING_REPORT.md` §7i | The model was scored on **8,090 test markets**, but ~10 strikes in one ladder resolve off a single temperature reading. Effective n ≈ 800 settlement hours; the CIs were "roughly 3× too tight" | ✅ fixed by bootstrapping over whole settlement hours — ❌ **but `docs/shortlist.md:113` still says "across 8,090 test markets in four cities, all surviving FDR"** |
| 1.5 | **P2 `reports/arb_log.parquet` — NOT caught** | `MORNING_REPORT.md` §6 headlines "**52 net-positive violations** found — so the detector does fire" and tabulates "`KXSOLD` 51 violations". The audit read the parquet: **55 `is_arb` rows but only 2 distinct violation ids.** 54 of the 55 are one `KXSOLD` monotone-ladder violation re-observed every 30 s for ~31 minutes. `arb_scan_meta.json` records `distinct_violations: 17` and nothing in the prose reflects it | ❌ **live**. The conclusion (0 at tradeable size) is unaffected; the count is inflated ~26× |
| 1.6 | **P2 `MORNING_REPORT.md` §7 — NOT caught** | "Buying everything priced 0.60–0.95 earns +7.05pp **± 0.22** on n = 98,766." Those 98,766 positions come from ~1,872 markets. A market settles once. A ±0.22pp interval on ~1,872 independent settlements is roughly 7× too tight | ❌ **live**, and it is the claim the whole copy-trading reframe rests on (see `LEDGER.md` C042) |
| 1.7 | P2 `reports/copytrade_tests_v2.json` — partially caught | The unit of observation is correctly (wallet, market), **but the bootstrap resamples wallets**, and 425 wallets share the same 1,872 markets. Their edges are cross-correlated through shared settlements, so CI [+4.61, +9.73] is narrower than the data supports | ❌ **live**, milder than 1.6 |
| 1.8 | P3 `HANDOFF.md` finding 9 | Ranking from raw tape produced a leader "98% over 57 bets" who had backed one player in **two matches**, with binomial p = 0.00000 | ✅ fixed — one match = one call, folded per (wallet, market, side) with a stake-weighted price. "Every apparent star vanished when the fold was applied" |
| 1.9 | P3 `HANDOFF.md` finding 11 | Three at once: raw trades as calls; a wallet's own later trades counted as the market moving in its favour; 20 trades by one wallet in one match watching the same subsequent move. Gave **t-statistics of 90 and 408** | ✅ fixed — "the giveaway, since no financial signal legitimately reaches those" |
| 1.10 | P5 `docs/PHASES.md` Phase 7 | Recognised in advance: "signals from the same weather event are correlated". The consensus-blend gate was evaluated with an **event-clustered bootstrap** keeping all brackets from one event together | ✅ correct by design — the only project that clustered *before* being burned |
| 1.11 | P1 `backtest/BACKTEST_RESULTS.md` | Per-trade means over 1,501 trades drawn from 995 matches; no CIs are reported anywhere in the document | ⚠ **latent** — the conclusion is an arithmetic gap (−9¢ vs a ~4¢ cost base) far larger than any plausible clustering correction, so it survives. But no interval in that file is trustworthy as stated |
| 1.12 | P1 `tennis_engine.py:32-39, 71-83` | Live-trading gates set from **125 settled markets** split into 5 price buckets, and **137 matches** split across 7 stop widths. Both are per-trade tallies over far fewer independent matches | ❌ **live and load-bearing** — these are the bot's entry floor and stop width |

**Rule this corpus has already paid to learn, three separate times:** the CI must be
bootstrapped over the thing that settles once — the match, the market, the settlement
hour — never over the fill, the snapshot, or the strike.

---

## 2. Look-ahead leakage — a feature whose knowability timestamp is at or after the decision

| # | Where | Status |
|---|---|---|
| 2.1 | **The known past instance: a price anchor set at or after settlement.** P2 addresses it explicitly — `MORNING_REPORT.md:107-109`: post-settlement `last_price_dollars` (0.001/0.999 on settled markets) "was **never** used as a price anchor — that is precisely the look-ahead leak that destroyed the tennis result" | ✅ excluded by construction. **The original leaking artifact is not on this machine** — no tennis script anywhere uses a settlement-time anchor, so the defect is known only from this reference. `PENDING (chat export)` for the primary evidence |
| 2.2 | P2 `src/kalshi_research/evaluate.py` + panel build | Knowability assertion `price anchor < decision < settlement` asserted in code on all 31,310 panel rows; anchor is the last **fully closed** 1-minute candle strictly before the decision | ✅ PASS |
| 2.3 | P2 `scripts/weather_model.py` | Leak assertion in code that every feature observation precedes its settlement; strict 60/40 time split with all parameters fit on train only | ✅ PASS |
| 2.4 | P5 `docs/PHASES.md` Phase 5 / `docs/DECISIONS.md` | NDFD forecasts selected with a **strict noon-UTC, day-before-event publication cutoff**, with issue/publication/validity/target timestamps all preserved. Explicitly "prevents outcome leakage" | ✅ PASS — the strongest anti-leak design in the corpus |
| 2.5 | P4 `tests/test_no_lookahead.py`; P7 `tests/test_no_lookahead.py` | Both Polymarket projects ship a dedicated no-lookahead test. PTIS backtests state that "outcomes are inaccessible to entry selection and used only for settlement" | ✅ PASS |
| 2.6 | P3 `scripts/follow_through.py` | A subtle near-leak, self-caught: letting a wallet's **own later trades** count as "the market moving its way". A 32,000-trade wallet simply *is* the later price in markets it touches | ✅ fixed |
| 2.7 | P2 `MORNING_REPORT.md` §7b / `scripts/weather_model.py` | Weather ground truth is reconstructed from `expiration_value` on **settled** markets. This is legitimate for building the historical temperature series, but it means the model can only ever be validated retrospectively — it cannot be run forward without an independent observation feed | ⚠ **structural, not a leak**, but worth stating: the training label and the settlement source are the same field |
| 2.8 | P1 `backtest/engine.py:13-14` | Same-candle stop/target ambiguity always resolves **stop first** — deliberately pessimistic, the opposite of leakage | ✅ correct |
| 2.9 | **P1 `backtest/high_sweep.py`, `phase` / `elapsed_*` parameters.** Recorded in project memory `kalshi-backtest-finding.md` | A "final third of match" filter showed **+1.68¢** — but which third a candle falls in is only knowable *after* the match ends. The tradeable restatement (`≥120 min elapsed`) gives **−0.09¢**. A 1.77¢ swing, entirely leakage | ✅ caught and restated. **No output file preserved** — this instance survives only in memory plus the parameters in code (`LEDGER.md` C005d) |
| 2.10 | P1 `backtest/high_sweep.py:85-90` | The maker fill loop deliberately starts at `i0+1`: "Inside the entry candle the low is below our limit by construction, so including it fills every order instantly and manufactures a profit that does not exist" | ✅ a same-bar fill leak, anticipated and excluded by construction |

**No live look-ahead leak was found.** This is the one failure mode the corpus has
genuinely solved, in all five codebases independently — though instances 2.9 and 2.10 are
preserved only as code comments and a memory file, so the *evidence* that 2.9 was caught is
one deletion away from being lost.

---

## 3. Silent data corruption — writers producing correct row counts with empty or malformed content

| # | Where | The error | Status |
|---|---|---|---|
| 3.1 | **P2 `scripts/record_kalshi.py`, the known instance.** `MORNING_REPORT.md` §8b | The orderbook response nests the book under **`orderbook_fp` at the top level**; the recorder unwrapped a non-existent `"orderbook"` key first, got `{}` on every call, and wrote an "empty book" marker with `n_levels: 0`. **Every book snapshot from 07:30 to 09:15 UTC was empty while row counts looked healthy.** "Row counts are not a data-quality check, and I should not have treated them as one" | ✅ fixed; 9 regression tests in `tests/test_book_parse.py` pin the verbatim live payload shape; ~1.8 h of empty files quarantined to `data/raw_empty_books_prefix/` rather than deleted |
| 3.2 | P2 writer, `PROGRESS.md:19` | The writer **early-returned on empty batches, so the time-based flush never fired** — a second silent-loss path in the same component, found the same hour | ✅ fixed |
| 3.3 | P2 panel build, `MORNING_REPORT.md` §9 | `close_time` parses as `datetime64[us]`, not `[ns]`, so `astype("int64") // 10**9` produced `1785393` instead of `1785393600`. Every price lookup silently missed and the panel came back **empty**. "If the assertion had not been there this would have looked like *no data available* rather than a unit error" | ✅ caught by an assertion; now converted resolution-independently with an explicit overlap check |
| 3.4 | P3 `backend/app/providers/polymarket.py` / `docs/DATA_LIMITATIONS.md` §4b | `data-api /activity` rejects offset > 5000 with HTTP 400 and **a naive paginator stops there without any error**. One wallet had **91,561 records and would have silently shown 2,000** | ✅ fixed by re-anchoring on the newest timestamp and walking forward; stalls warn (`provider.activity_window_stalled`) rather than looping |
| 3.5 | P3 `docs/DATA_LIMITATIONS.md` §3 | Gamma `?condition_id=` **silently ignores the filter and returns the default market list** — this would attach the wrong market metadata to a wallet's transactions, "a silent, total corruption of the tennis universe" | ✅ avoided; only `GET clob.polymarket.com/markets/{condition_id}` is used, which 404s on unknown ids |
| 3.6 | P3 `docs/FINDINGS.md` defect 3 | **Cluster ids were never written back to wallets**, leaving the consensus-independence rule inert — related wallets would have counted as separate confirmations | ✅ fixed |
| 3.7 | P4 `src/ptis/collectors.py:419-437`, `EXPERIMENT_LOG.md` Run 2 | The CLOB `base_fee` (an integer bps field) was converted into the **dynamic** fee-formula rate slot, which expects Gamma's `feeSchedule.rate`. Produced plausible numbers with the wrong fee | ✅ run invalidated and excluded from all performance calculations; record preserved |
| 3.8 | P2 `data/gaps_report.md` | ❌ **Stale on disk.** Generated at 09:23 UTC and reports coverage ending then; the recorder actually ran to **17:32 UTC** (see `data/recorder_kalshi.log`, 2,028,092 trades). The manifest and gaps report understate the dataset by ~8 hours | ❌ live — cosmetic, but a future session reading `gaps_report.md` will size the dataset wrong |
| 3.9 | P1 `kalshi/` root | ❌ **11 orphan `_*.json` data files** (~2 MB, 28 Jul) that **no script anywhere references**. Inputs preserved, method and conclusion lost. Not corruption, but the same end state: data that cannot be tied to a result | ❌ live |
| 3.10 | P3 `docs/DATA_LIMITATIONS.md` §12 | Upstream schema drift named as "the biggest silent risk" — "a field quietly renamed upstream would produce plausible, wrong numbers." Detection is implemented and surfaced on the System Health page | ⚠ **detector exists; no drift review is recorded**. If a drift event is pending, recent P3 numbers are unsafe |

---

## 4. Floating-point fee dust

`0.07 * 100 * 0.5 * 0.5 * 100` evaluates to `175.00000000000003`, so a naive `ceil()`
charges 1.76 instead of 1.75 — an overcharge of a cent on exactly the most common price.

**Nine independent implementations of the fee formula exist across five codebases. Two
are guarded. Six are not. One is a different venue's rule.**

| # | File:line | Expression | Guard |
|---|---|---|---|
| 4.1 | `kalshi\backtest\engine.py:101` | `math.ceil(round(0.07*contracts*p*(1.0-p)*100.0, 9))/100.0` | ✅ **YES** — `:96-98` names the exact `175.00000000000003` value |
| 4.2 | `kalshi markets\src\kalshi_research\fees.py:17-38` | `Decimal(str(rate))*Decimal(contracts)*… .quantize(Decimal(1), ROUND_CEILING)` | ✅ **YES** — `:20-22` names `1.7500000000000002`; "Money gets exact arithmetic" |
| 4.3 | **`kalshi\tennis_engine.py:240`** | `math.ceil(cfg.fee_rate*contracts*p*(1-p)*100)/100` | ❌ **NO — and this is the live trading engine** |
| 4.4 | **`kalshi\paper_bot.py:85`** | `math.ceil(0.07*n*p*(1-p)*100)/100` | ❌ **NO — the paper bot's P&L is systematically pessimistic vs the live engine's… which shares the same bug, so they agree with each other and both disagree with Kalshi** |
| 4.5 | `kalshi\backtest\longshot.py:31` | `math.ceil(0.07*contracts*p*(1-p)*100)/100.0` | ❌ NO |
| 4.6 | `kalshi\backtest\high_entry.py:28` | same | ❌ NO |
| 4.7 | `kalshi\backtest\high_sweep.py:37` | same | ❌ NO |
| 4.8 | `OneDrive\Desktop\kalshi\tennis_engine.py:123` | same | ❌ NO — stale duplicate of 4.3 |
| 4.9 | `PTIS\src\ptis\execution.py:33` | `shares * fee_rate_decimal * price * (1.0-price)` | n/a — Polymarket charges a continuous fee with **no ceil**, so there is no dust to round. Correct for that venue |

Plus a tenth cost model that is not a fee formula at all:
`weather-market-bot` never computes the Kalshi quadratic fee. It uses flat buffers —
`exit_policies.py:30-31` (`ENTRY_COST_BUFFER = 0.01`, `EXIT_COST_BUFFER = 0.03`) and
`market_structure.py:18` (`PER_LEG_COST_BUFFER = 0.03`). Its backtest P&L is therefore
not fee-accurate in either direction, and its basket-arbitrage screen uses a 3¢/leg
buffer where the true fee is price-dependent.

**Magnitude.** One cent per fill on the entry leg only. At P1's live sizing (8–10
contracts, ~$6 notional), the true fee at 65¢ on 9 contracts is
`ceil(7·9·0.65·0.35)/100 = ceil(14.33)/100 = $0.15` and the dust bug does not bite at
that size — it bites at the round numbers, most sharply at C=100, P=0.50. So this is
**material for the backtests' 100-contract cost curves and immaterial at current live
size**. It is listed as high priority anyway because 4.3 and 4.4 are in the money path
and the fix is one `round(..., 9)` per file, already written twice elsewhere in the same
repository.

**The deeper finding is not the dust — it is that nine implementations exist at all.**
`kalshi markets` has a correct, tested, importable `fees.py` (`tests/test_fees.py`,
including `test_fee_never_exceeds_notional` and an explicit rounding-rule guard) that no
other project uses.

---

## 5. Benchmark inflation — beating a weak benchmark reported as beating the market

| # | Where | The weak benchmark | Handling |
|---|---|---|---|
| 5.1 | P2 weather, `MORNING_REPORT.md` §7b | Persistence+hour-of-day beats **climatology** (Brier 0.058–0.093 vs 0.163–0.294) | ✅ **explicitly refused**: "this is not an edge. Beating climatology is table stakes — Kalshi's mid also knows last hour's temperature, and so does anyone who can read `api.weather.gov`." The `Kalshi mid Brier` column in the headline table reads *blocked* rather than being filled with the climatology number |
| 5.2 | P2 BTC, `HYPOTHESIS_LEDGER.md` row 3 | 35 fair-value hypotheses: **"25 beat a coinflip, 0 established edge over the market"** | ✅ the coinflip result is reported and immediately discounted; the ledger's Survivors column says "25 vs coinflip only" |
| 5.3 | P5 weather, `docs/PHASES.md` Phase 7 | Model Brier 0.204805 vs **market-ask** Brier 0.168963 | ✅ **the gate was defined against the market and the model failed it**, and "a positive thresholded simulation does not override the weaker probability comparison". The strongest example of benchmark discipline in the corpus |
| 5.4 | P2 `MORNING_REPORT.md` §7f | Kalshi sports "calibrated in aggregate" against **overround** | ⚠ **partially inflated.** The report itself catches the deeper version: "a favourite-longshot bias is a *redistribution* across buckets … so it nets to roughly zero in aggregate by construction. The beautifully calibrated 0.5152-vs-0.5168 overall figure … is **structurally incapable** of testing for this particular bias." Correctly caught — but `docs/GO_NO_GO.md:87-90` still quotes the bucket-level version as settled |
| 5.5 | **P2 §7 copy trading — ❌ live** | The +7.23pp top-decile edge and the +7.05pp price-band edge are both measured against **zero and a 2.4¢ cost bar**, never against *the Polymarket mid at the moment of entry*. The report acknowledges the adjacent problem ("these are filled prices, not posted quotes … a strategy must trade against what was available") but the headline number is still an edge-over-nothing, not an edge-over-the-market | ❌ live |
| 5.6 | **P1 §Honest read — ✅ the good version** | The v3 signal is compared against a **random-entry control (S5)** and against buy-and-hold (S2), and loses to both. "S1 −9.36¢ vs S5 random −8.28¢" | ✅ the correct benchmark was chosen and the strategy failed it |
| 5.7 | P4 `HISTORICAL_BACKTEST_REPORT.md:26` | Explicit **cash baseline: $0 P&L and 0% return**, and 0-second scenarios labelled "theoretical upper bounds" | ✅ correct |
| 5.8 | P3 `scripts/live_candidates.py` | The benchmark is a **luck bar** — the edge the luckiest wallet shows in a skill-free population of the same sample sizes — and `HANDOFF.md` finding 7 shows the bar must be computed over the volume-eligible pool, not the gate survivors, because shrinking the pool flipped a wallet from fail to pass without its record changing | ✅ **the single best benchmark construction in the corpus.** It benchmarks the *search*, not the strategy |
| 5.9 | P2 §7c, retracted | "Seven daily families clear the capacity bar by 7–49×, so weather is not capacity-limited" — passing a *depth* bar was reported as the weather thesis clearing its gate, when the binding gate was **recurrence** (66 settlements vs 481 needed) | ✅ retracted in §7i ("I was celebrating the wrong axis") — ❌ **still stated as a passing gate in `docs/shortlist.md:118-129` and `docs/GO_NO_GO.md:45`** |

---

## Summary count

| Pattern | Instances found | Self-caught | ❌ still live on disk |
|---|---|---|---|
| 1. Pseudo-replication | 12 | 7 | **5** (1.4 doc, 1.5, 1.6, 1.7, 1.12) |
| 2. Look-ahead leakage | 10 | 10 | 0 |
| 3. Silent data corruption | 10 | 7 | 3 (3.8, 3.9, 3.10) |
| 4. Fee dust | 9 implementations | 2 guarded | **6 unguarded, 2 in the live money path** |
| 5. Benchmark inflation | 9 | 7 | 2 (5.5, 5.9) |

The corpus is far better at catching these than at *propagating the correction into every
document*. **Every single one of the five ❌-live pseudo-replication and benchmark items is
a correction that was made in `MORNING_REPORT.md` and never carried into
`docs/GO_NO_GO.md` or `docs/shortlist.md`** — which are the shorter, more quotable files a
future session is more likely to read first.
