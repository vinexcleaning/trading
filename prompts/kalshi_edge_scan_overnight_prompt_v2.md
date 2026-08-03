# MASTER PROMPT v2 — Kalshi Exchange-Wide Edge Scan

Supersedes the BTC-only prompt. Paste into a fresh Claude Code session in an empty project directory. The BTC work is still here in full — it's now Phase 5 — but it no longer runs alone.

---

You are building a research stack that scans the whole Kalshi exchange for tradeable edge, plus a deep-dive on 15-minute Bitcoin (`KXBTC15M`), plus a copy/flow-trading research track. This is a 6–8 hour autonomous overnight job. Do not stop to ask questions. When a decision is ambiguous, take the more conservative option, log it in `DECISIONS.md`, continue.

## Absolute rules

1. **No real money, ever.** No order-placement endpoint may be imported anywhere in this codebase. Read-only data and simulated fills only. Any credential handler must refuse a key with trade permissions.
2. **No paid data.** Free tiers and public endpoints only. Anything that needs a card goes in `PAID_OPTIONS.md` with cost, what it buys, and an estimate of whether it's worth it. Then move on.
3. **No martingale, no doubling after losses, no averaging down.** Sizing is quarter-Kelly, hard-capped.
4. **Assume every market is efficient until proven otherwise.** A rigorously evidenced "there is no edge here, and here is the proof" is a successful night. Say so plainly if that's the finding.
5. **Never fit and evaluate on the same data.** Every reported number is out-of-sample.

## The rule that governs this entire project

Widening from one market to hundreds multiplies the multiple-comparisons problem enormously. If you test 150 markets × 40 parameter combinations, you have run 6,000 experiments and roughly 300 of them will look "profitable at p < 0.05" **on pure noise**. A naive breadth-first search is therefore not just weak, it's actively dangerous: it manufactures false confidence at scale.

So, non-negotiable:

- **Pre-register before you search.** Write `docs/PREREGISTRATION.md` *before* running any strategy sweep: the hypothesis per market family, the features allowed, the parameter grid, the evaluation metric, and the significance threshold. Then don't deviate. If you deviate, log it as a new hypothesis and count it.
- **Count every hypothesis.** Maintain `docs/HYPOTHESIS_LEDGER.md` with an incrementing count of every distinct model/parameter/market combination evaluated. The final report must state the total.
- **Apply Benjamini–Hochberg FDR control across the entire ledger**, not per market. Report both raw and corrected results.
- **Compute a deflated Sharpe ratio** that accounts for the number of trials.
- **Every surviving candidate must have a mechanism.** If you cannot write one sentence explaining *why* the counterparty is wrong and why that mistake persists, the result is noise no matter how good the p-value. Put that sentence in the report or discard the candidate.

## Reframe: the scan is for elimination, not discovery

Do not think of the wide scan as "search many markets for a winner." Think of it as **cheap triage**: spend a few minutes per market family killing everything that structurally cannot work, so that the expensive modelling work lands on the two or three families that have a real reason to be inefficient. The output of the scan should be a short list with reasons, not a ranking of backtest returns.

This also fixes the ordering. Your instinct was scan → parameter sweep → historical validation. That wastes compute: parameter-sweeping a market with a 3¢ spread and four settlements a month tells you nothing regardless of the result. Screen on structure first, and only ever sweep parameters on markets that could clear the cost bar even if the model were perfect.

## The universal cost bar — compute this first, for every market family

Kalshi's taker fee is `ceil(0.07 × C × P × (1-P))` cents per contract; maker is one quarter of that on series where it applies; **S&P 500 and Nasdaq-100 series reportedly use a halved multiplier (0.035)**. Verify all of this against Kalshi's live fee schedule in Phase 0 — do not trust these numbers from me.

For every market family, compute and tabulate:

```
breakeven_edge = round_trip_fee(P) + spread_cost(P) + slippage_estimate
```

at P = 10¢, 25¢, 50¢, 75¢, 90¢. At 50¢ with the standard multiplier a round trip is ~3.5¢, meaning **a 3.5 percentage point probability edge just to break even.** Any family where the median spread alone exceeds the plausible edge is dead on arrival — kill it in Phase 1 and never model it. Note that because the fee scales with `P(1-P)`, trading at 10¢/90¢ costs about a fifth as much as at 50¢; check whether the viable space lives at the tails.

---

# PHASE 0 — Ground truth (~45 min, do first)

Do not write strategy code until this is written up in `docs/contract_spec.md`, with a source link and a confidence rating per row.

1. Enumerate all Kalshi series via the public API. Count active series and markets per category.
2. Full fee schedule: taker multiplier, maker multiplier, per-category exceptions, rounding, which series carry maker fees.
3. `KXBTC15M` specifics: settlement mechanics (**public sources contradict each other — some say a single captured price, others a 60-second average of the CF Benchmarks real-time index sampled once per second over the final minute; resolve it definitively, it changes the pricing model materially**), `floor_strike` / `strike_threshold` / `expiration_value` availability post-settlement, strike banding, tie handling.
4. API surface: REST endpoints, WebSocket channels, what needs auth, and — critically — **the exact rate limits**. Compute how many markets we can realistically maintain live order books for simultaneously. This number determines the whole recorder architecture, so get it before you build.
5. Whether any historical order book is retrievable (expect no — which is why recorders start tonight).
6. Whether settled-market history is walkable backwards, and how far.
7. The public trades endpoint: is it anonymous, does it require auth, and **does it include auto-generated legs from multi-leg Combo contracts?** (Reportedly yes, and they dominate raw volume. If so, you must filter them or every flow signal will be garbage.)
8. Kalshi's leaderboard: opt-in or default? What is publicly exposed per trader without a paid scraper?

---

# PHASE 1 — Universe enumeration and structural screen (no strategy code)

## 1a. The market quality rubric

I asked you to define what makes a market worth trading. Here is the starting rubric — **critique it, improve it, and justify any changes.** Score every Kalshi series 0–5 on each dimension and write the table to `docs/market_screen.csv`.

| # | Dimension | What a 5 looks like | What a 0 looks like |
|---|---|---|---|
| 1 | **Independent ground truth** | We can compute the answer from free data that updates faster than the market reprices (weather station observations, released economic components) | Resolution depends on unmodellable human events (politics, awards) |
| 2 | **Cost bar** | Halved fee multiplier, tight spread, trades at the tails | Standard fee, 3¢+ spread, trades near 50¢ |
| 3 | **Liquidity** | Deep book at the touch, continuous volume, many distinct trades | Two-sided quotes only sporadically, one market maker |
| 4 | **Structural redundancy** | Family contains internal constraints checkable *without any forecast* — mutually exclusive buckets that must sum to 100, nested thresholds that must be monotone, Combo legs vs. their standalone markets, term structure across expiries, an identical contract on another venue | Single isolated binary with no relatives |
| 5 | **Recurrence** | Dozens or hundreds of independent settlements per week, so results are statistically testable | A handful of settlements per year — unvalidatable, full stop |
| 6 | **Counterparty composition** | Retail-heavy: round order sizes, slow quote updates, wide unstable spreads, activity tracking waking hours | Bot-dominated: sub-second quote updates, tight stable spreads, flat 24h activity |
| 7 | **Settlement clarity** | Machine-readable, unambiguous, single named source | Discretionary or ambiguous resolution language |
| 8 | **Data cost** | Fully free and unlimited | Licence-gated (e.g. CF Benchmarks BRRNY for hourly BTC) |

**Hard disqualifiers — kill immediately, do not model:**
- Zero on dimension 1 **and** zero on dimension 4 (no ground truth and no structural check = pure opinion market)
- Median spread greater than the plausible edge
- Fewer than ~50 settlements available for validation
- Resolution requires human judgment
- Requires paid data

Dimension 6 needs actual measurement, not a guess. Build a **counterparty fingerprint** per series from the public order book and trade feed: order size distribution (round numbers vs. odd lots), quote update frequency, spread stability, cancel-to-trade ratio, and activity by hour-of-day. Rank all series from most retail-like to most bot-like. This is directly your time-of-day hypothesis generalised across the exchange, and it's one of the more interesting things you'll produce tonight.

## 1b. Where edge plausibly lives — start here rather than rediscovering it

Investigate these in roughly this order. For each, the mechanism is stated; verify or refute it.

1. **Weather markets.** Highest-prior candidate on the exchange. Physical ground truth (NWS/METAR observations, TAF, HRRR/GFS/GEFS ensembles — all free), machine-readable settlement at a named station, high recurrence, retail-heavy counterparty, and the intraday high is *partially observable before settlement*, which is a genuine structural asymmetry. Mechanism: retail prices the forecast, we price the observation. I already have working tooling for airport station data — assume it exists and build a clean model rather than a scraper.
2. **Internal no-arbitrage violations.** Bucket families (temperature ranges, CPI ranges, index ranges) are mutually exclusive and exhaustive, so the buckets must price to 100. If the sum of asks is under 100, or the sum of bids over 100, that is a locked position requiring **zero forecasting skill**. Same for nested thresholds that must be monotone in strike. Also check Combo (parlay) contracts against the product of their standalone legs. Mechanism for the last one is strong: parlays are frequently priced as if legs were independent when the legs are correlated, which systematically misprices them in a predictable direction. **This whole category is the highest-quality thing in the project because it needs no model, only monitoring and speed.** Build the scanner in Phase 2.
3. **Crypto term structure and options-implied distributions.** Four 15-minute markets must be consistent with the hourly market; the hourly with the daily. Deribit's public API gives a full free risk-neutral distribution for BTC — compare Kalshi's implied probabilities against it directly.
4. **Index range markets vs. equity options.** Same trick as Deribit but for S&P/Nasdaq: back out the implied distribution from a free option chain and compare. Structurally attractive because of the reportedly halved fee multiplier, which lowers the edge bar by half.
5. **Economics releases.** CPI/PPI nowcasting from published components, jobless claims (weekly, so decent sample size), Fed decisions against CME FedWatch and SOFR futures pricing. Mechanism: the professional forecast is public and free, and retail may not be using it.
6. **Cross-venue: Kalshi vs. Polymarket.** Match identical contracts and measure the price gap distribution against combined round-trip costs. Be warned: commercial scanners for exactly this already exist, so expect the gap to be mostly closed. Measure it anyway — the *distribution* of gaps is informative even if the mean is unexploitable. Note also that I have already established Kalshi tennis prices track Betfair at r = 0.9878 with a mean absolute difference of 1.95¢ against a 2.4¢ round trip, i.e. no edge; assume similar efficiency until shown otherwise.
7. **Sports — deprioritise, with one exception.** I spent weeks proving there is no pricing edge in Kalshi tennis versus the bookmaker consensus, and a player-level model lost to the bookmaker benchmark (Brier 0.2249 vs 0.2057, n = 2,645). Do not repeat that work. The one untested angle is correlated multi-leg and set-score markets, which belongs to category 2 above.

Write the shortlist to `docs/shortlist.md` with the score table, the mechanism sentence, and the kill reason for everything eliminated. **I want to read the kill reasons.**

---

# PHASE 2 — No-arbitrage scanner (build early, it can pay off immediately)

This is the one component that needs no forecasting, no backtest, and no history. Build it right after the screen.

- Poll every bucket family, nested-threshold family, and Combo/leg relationship on a loop.
- Check: buckets sum to 100 within fee tolerance; thresholds monotone in strike; Combo price versus the joint probability of its legs under both an independence assumption and an estimated correlation; the same contract's price across correlated series.
- Report violations **net of round-trip fees on every leg and net of the spread you would actually cross.** A 1¢ violation is not an arb when the round trip costs 3.5¢ per leg. Most apparent violations die here — that's the expected result and it's fine.
- Log every violation with timestamp, size available at the violating prices, and **how long it persisted.** Persistence is the whole question: a violation that survives 200ms is a data artifact; one that survives 30 seconds with real depth is a genuine edge, and its frequency and size tell us whether the strategy is worth anything.
- Output `reports/arb_log.parquet` and a summary of violations per hour, by series, by time of day.

---

# PHASE 3 — Recorders (time-critical, start before any analysis)

Recorded data accrues in wall-clock time and cannot be recovered later. Get these running, then do analysis while they collect.

Tier the recording by the rate limits measured in Phase 0:

- **Tier 1 (full order book + all trades):** the top ~10–20 shortlisted markets, including all live `KXBTC15M` markets.
- **Tier 2 (top-of-book snapshots at a slower interval + all trades):** the next ~100.
- **Tier 3 (trades and settlement outcomes only):** everything else on the exchange. Cheap and comprehensive.
- **The public trade feed, exchange-wide, continuously** — with Combo-generated legs tagged and separated. This is the raw material for Phase 6 and it's free.
- **External:** BTC/ETH spot from three or more exchanges plus Binance perps (funding, open interest, liquidations); Deribit DVOL and option chain; NWS/METAR observations for every weather settlement station; free option chains for index markets.

Timestamp discipline, non-negotiable: three timestamps per row (exchange event time, our receipt time, our write time), UTC integer nanoseconds, NTP-synced with the offset logged at startup and drift re-checked hourly, one monotonic clock for sequencing, measured wire latency logged per source. Parquet partitioned by `source/date/hour`, queried with DuckDB. A `manifest.json` with row counts, first/last timestamps, gaps and checksums, plus a gap-detection pass writing `data/gaps_report.md`. All downloads idempotent.

---

# PHASE 4 — Ground-truth models for surviving families

For each shortlisted family, build the smallest model that produces a calibrated probability, and score it the same way everywhere so results are comparable:

- Brier score and log loss, walk-forward, strictly time-ordered splits. **No shuffled cross-validation, ever.**
- Reliability curves in 5% buckets with counts.
- **The decisive comparison, identical for every family: our probability versus Kalshi's mid-price, both scored against the realised outcome.** If the mid beats us, we have no edge in that family. Report this as a single table across all families — it's the headline result of the night.
- Where we do beat the mid, localise it: by time-to-expiry, by distance from strike, by hour of day, by liquidity regime. A real edge is concentrated and explainable; a diffuse edge spread evenly is almost always a leak.

## Leak audit — mandatory, run it early, not last

I have been burned by exactly this: an apparent edge in my tennis work turned out to be a look-ahead leak where the price anchor timestamp sat at or after settlement, and the edge vanished at a clean pre-event anchor. So, for every family:

- Assert in code, per feature, that its knowability timestamp precedes the decision timestamp.
- Shift all features forward one period and confirm the edge disappears.
- Shuffle labels and confirm the edge goes to zero.
- **Run the entire pipeline end-to-end on synthetic data with no signal in it** (random walks matched to each family's volatility, random outcomes for discrete families). If the pipeline finds an edge on synthetic noise, the pipeline is broken and every other result tonight is void. This is the single most important test in the project.

---

# PHASE 5 — BTC deep dive (full depth, unchanged in ambition)

Everything in this phase is BTC-specific and should reach the depth of a standalone project.

**Volatility work (highest value here):** realized vol at 1m/5m/15m/1h/1d via close-to-close, Parkinson, Garman-Klass, Rogers-Satchell and bipower variation; EWMA and HAR-RV forecasts at a 15-minute horizon scored out-of-sample on RMSE and QLIKE; the **intraday vol seasonality curve** by minute-of-day UTC and day-of-week with confidence bands, plus vol by minute-within-the-quarter-hour to see whether anything systematic happens around the :00/:15/:30/:45 boundaries where these markets open and close; jump detection and the unconditional probability of a jump inside a 15-minute window; the empirical distribution of 15-minute log returns with a Student-t fit and tail index, quantifying how badly a Gaussian misprices the tails; vol clustering by previous-window decile.

**Direction work (expect null, document it anyway):** autocorrelation of returns and of return signs at lags 1–20; sign persistence and reversal at 1s/10s/1m/5m/15m; order-flow imbalance and cumulative volume delta; book imbalance and depth asymmetry; **ETH→BTC lead-lag** via cross-correlation from −60s to +60s and a Hayashi-Yoshida estimator for asynchronous data, reporting whether any lead survives transaction costs; funding rate and open-interest change as direction predictors; liquidation-cascade conditional response.

**Perps specifically, since I asked about them:** treat funding rate, basis (perp minus spot), open interest change and the liquidation stream as **volatility and regime inputs**, not direction inputs. Test three concrete things: (a) does funding or basis predict realized vol over the next 15 minutes, (b) do liquidation clusters predict a vol spike that the 15-minute market has not yet priced, (c) does the perp order book lead the spot order book at sub-second scale by enough to matter after costs. Also note for the record what a perp *would* give us if we ever traded real money — a hedging instrument, which changes the strategy space entirely — but we cannot use it now and should not design around it.

**Macro and news:** for each scheduled release (CPI, PPI, NFP, FOMC, claims), measure the change in realized vol and absolute return in the following 15/30/60 minutes. Report macro as a **vol** result. Separately test direction and expect nothing. For unscheduled news like tariff announcements, be honest that we have no clean free timestamped dataset, and state what building one would take.

**Fair value model:** build `p_up = P(settle > strike | spot, strike, seconds_remaining, vol_state)`. Start with driftless GBM, `Φ(ln(S/K)/(σ√τ))`, as the benchmark everything must beat. Then: a settlement-aware version (if Phase 0 confirms a 60-second average settle, the terminal distribution is the distribution of that average, which has lower variance and means late-window contracts should price *further* from 50¢ than a point-sample model implies); fat-tailed; seasonal-σ from the minute-of-day curve; a blend of realized, forecast and Deribit implied vol with weights fit out-of-sample; and only then a gradient-boosted classifier, which must clearly beat the blended model out-of-sample or be discarded.

---

# PHASE 6 — Copy trading and flow following

Do the research here honestly, because the reality is asymmetric between venues and most of what's sold as "copy trading" is survivorship bias with a leaderboard next to it.

**What's actually available:**
- **Kalshi's public trade feed is anonymous.** You see that a large trade happened, not who did it. So on Kalshi this cannot be identity-based copying — only **flow following**. Build it: aggregate fills into per-market per-side notional and VWAP, **filter out the auto-generated Combo legs that dominate raw volume**, and treat large accumulating one-sided positions in single markets as the signal. Free to compute, no auth needed.
- **Kalshi's leaderboard is opt-in**, so anyone on it is self-selected, and per-trader positions need a paid scraper. Log that in `PAID_OPTIONS.md` with a cost estimate; do not build on it.
- **Polymarket is the opposite:** wallets are fully public on-chain, so complete position and P&L history is free via the Polymarket data API and Polygon indexers. This is the only venue where genuine identity-level copy trading is possible for free. Build the wallet ranker there **even though I trade Kalshi**, because a skilled wallet's position in a Polymarket contract is a readable signal for the twin Kalshi contract.

**The tests that decide whether any of this is real — run all four, they are the point of this phase:**
1. **Persistence.** Rank traders/flows on period 1, evaluate on a strictly later period 2. Does past performance predict future performance at all? For most leaderboards it doesn't. If rank correlation across periods is near zero, copy trading is dead and say so.
2. **Skill versus luck.** Apply Bayesian shrinkage to win rates against sample size. A 70% win rate over 20 trades is noise. Report shrunk estimates only, and the number of trades needed to distinguish a genuinely 55% trader from a 50% one at your significance level.
3. **Edge decay and capacity.** Measure the price path at +1s, +10s, +60s, +5m after a whale print or a followed trade. If the price has already moved past the entry by the time we could act, the signal is unexploitable regardless of how good the trader is. Also model the reflexive problem: a popular signal moves the price before followers fill, so the more copyable it looks, the worse the fill.
4. **Adverse selection.** Are we systematically filled by the informed side? Check whether our simulated entries cluster just before adverse moves.

**Also, apply exactly these four tests to my own live tennis copy trading.** I'm doing that now on real money and I have never measured whether the source has persistent skill or whether I've been getting lucky. That's arguably the most immediately valuable analysis in this whole phase, so do it properly and tell me the answer even if I won't like it.

---

# PHASE 7 — Strategy search with FDR control

Only after `docs/PREREGISTRATION.md` exists. For each shortlisted family, sweep the pre-registered grid with:

- Fee-inclusive P&L using the verified formula and correct rounding, always. No gross numbers anywhere.
- An explicit fill model: crossing fills at the touch with slippage; resting orders fill only when the book trades through, assuming we are last in the queue at our price.
- Replay at measured latency — decisions see only data that had arrived.
- Purged walk-forward with an embargo between train and test.
- Bootstrapped P&L confidence intervals, not point estimates.
- **Report the full parameter surface, not the peak.** A sharp isolated peak is overfitting; a broad plateau might be real. State explicitly which one each candidate has.
- Every result compared against the fee-adjusted-coinflip null.
- Every result carried into the hypothesis ledger and FDR-corrected across the whole project.

---

# PHASE 8 — Paper trader

Live data, entirely simulated fills, no order endpoints in the codebase. Same fill model as Phase 7 so paper and backtest results are directly comparable — **log any divergence between them, that divergence is the most informative number we'll get.** Quarter-Kelly sizing, hard-capped at 2% of notional bankroll per position and 10% total exposure, hard-coded. Kill switch on daily loss limit, consecutive losses, stale feed, or calibration drift. Restart-safe with state on disk. Log every decision including the no-trades, with the full feature vector.

# PHASE 9 — Verdict

Write `docs/GO_NO_GO.md` defining the bar **before** looking at results: minimum out-of-sample trades (justify with a power calculation — for coinflip-adjacent markets expect to need many hundreds), minimum fee-inclusive per-trade edge with a CI excluding zero, consistency across two disjoint periods and across time-of-day buckets, calibration stability, and all Phase 4 leak tests passed. Then fill in what actually happened.

---

# MORNING_REPORT.md — what I read when I wake up

Update it incrementally as you go, not at the end, so it's useful even if you're interrupted.

1. **The verdict in three sentences.** Any evidence of edge anywhere, yes or no. Lead with it.
2. **The single headline table:** every market family × our Brier score × Kalshi's mid Brier score × fee-inclusive edge with CI × survives FDR. One row per family. This is the whole night in one table.
3. **Total hypotheses tested**, and how many survived correction.
4. **What I got wrong.** Which of my hypotheses — macro/tariffs, ETH lead-lag, time-of-day regimes, perps tying into the 15-minute market, copy trading, profit-take/stop-loss optimisation — survived contact with data and which didn't. Be blunt. I'd rather be corrected tonight than pay for it later.
5. The kill list from Phase 1 with reasons.
6. Arb scanner results: violations per hour, size, persistence distribution, net of fees.
7. My tennis copy-trading verdict from Phase 6.
8. BTC intraday vol seasonality chart and what it implies about when to trade.
9. Leak test results including the synthetic-noise control.
10. What's blocked on more recorded data, and how many days of recording each blocked item needs.
11. Top three next actions, ranked by expected information gain per hour of work.

Also produce `docs/contract_spec.md`, `docs/market_screen.csv`, `docs/shortlist.md`, `docs/PREREGISTRATION.md`, `docs/HYPOTHESIS_LEDGER.md`, `docs/GO_NO_GO.md`, `DECISIONS.md`, `PAID_OPTIONS.md`, `data/gaps_report.md`, and charts as PNGs in `notebooks/`.

# Working discipline

Git repo, commit after every working unit, never leave the tree broken. `PROGRESS.md` as a timestamped running log with a checkbox per sub-phase so I can see exactly where you stopped. Small boring tested code over clever code; `pytest` coverage on the fee calculation, the probability models, and the arb detector especially.

**Priority ladder if you run out of time, context, or rate limit:**

1. Phase 0 ground truth, including rate limits
2. Phase 3 recorders live and writing (unrecoverable if skipped)
3. Phase 1 screen and shortlist
4. Phase 4 synthetic-noise control (everything else is void without it)
5. Phase 2 arb scanner
6. Phase 6 test 1 and 2 on my tennis copy trading
7. Phase 5 BTC vol seasonality and fair value baseline
8. Everything else

If you discover something that invalidates a premise of this prompt, stop that thread, write it prominently at the top of `MORNING_REPORT.md`, and reprioritise. Do not build on a premise you've already disproved.

Begin with Phase 0.
