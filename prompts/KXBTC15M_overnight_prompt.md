# MASTER PROMPT — Kalshi KXBTC15M Research Stack

Paste everything below into a fresh Claude Code session at the root of a new empty project directory.

---

You are building a research stack for Kalshi's 15-minute Bitcoin up/down market (series `KXBTC15M`). This is a multi-phase overnight job. Work autonomously. Do not stop to ask me questions — if a decision is ambiguous, pick the more conservative option, log the decision in `DECISIONS.md`, and keep going.

## Absolute rules

1. **No real money. Ever.** Do not write, import, or call any Kalshi order-placement endpoint. Read-only market data and simulated fills only. If you create a Kalshi API key handler, it must reject any credential with trade permissions and refuse to run.
2. **No paid data.** Free tiers and public endpoints only. If something requires a card, log it in `PAID_OPTIONS.md` with the cost and what it would buy us, and move on.
3. **No martingale, no doubling after losses, no averaging down.** If you test these at all, test them only to produce a ruin-probability table proving they're bad. Sizing is fractional-Kelly capped, described in Phase 5.
4. **Assume there is no edge until the data proves otherwise at a stated significance level.** Your job tonight is honest measurement, not finding a strategy. A well-evidenced "this market is efficient, here's the proof" is a **successful** outcome and I want you to say so plainly if that's what you find.
5. **Never fit and evaluate on the same data.** Every number that gets reported to me must come from data the model has not seen.

## Framing — read this before you design anything

The naive question is "will BTC be up or down in 15 minutes?" That question is a dead end. At a 15-minute horizon BTC returns are approximately a driftless martingale; directional prediction is close to impossible and any signal you find will almost certainly be a multiple-testing artifact.

The real question is: **is Kalshi's quoted price a mispriced estimate of P(settle above strike)?** A contract at 40¢ is a claim that the probability is 40%. That probability is mostly a function of four things — spot price, distance to the strike, time remaining in the window, and volatility. So the plausible sources of edge, in rough order of likelihood, are:

- **Volatility mispricing.** The market may use a lazy or stale vol estimate. If we estimate σ better (intraday seasonality, EWMA/HAR realized vol, Deribit implied vol), our probability is better than theirs.
- **Latency.** Our spot feed vs. their quote updates. Small, and possibly negative for us on a home connection — measure it, don't assume it.
- **Structural pricing biases.** Favorite-longshot bias, round-number strike stickiness, over/under-reaction to spot ticks, systematic misvaluation in the final 60–90 seconds when the outcome becomes near-deterministic.
- **Spread capture.** Being the maker rather than the taker.

Everything else — macro news, tariffs, ETH lead-lag, funding rates — belongs in Phase 2 as a **volatility regime** input, not a direction input. Test them, but expect direction results to be null.

## The fee math — carry this number through everything

Kalshi's taker fee is `ceil(0.07 × C × P × (1-P))` cents per contract, and the maker fee is one quarter of that (`0.0175` multiplier) on series where it applies. **Verify both against Kalshi's current fee schedule in Phase 0 — do not trust these numbers from me.**

If that formula holds, at 50¢ the taker fee is 1.75¢ per contract, so a round trip is ~3.5¢ on a $1 contract. **That means a taker strategy near 50¢ needs roughly a 3.5-percentage-point probability edge just to break even.** For a 15-minute coinflip that is an enormous bar.

Consequences you must build in from the start:
- Every strategy is evaluated on **fee-inclusive** P&L. No exceptions, no "gross" headline numbers.
- Prefer resting limit orders (maker) over crossing. Model fill probability honestly rather than assuming resting orders fill.
- Because fees scale with `P(1-P)`, cheap and expensive contracts are far cheaper to trade than 50¢ ones. Trades at 10¢/90¢ cost ~0.63¢. Check whether the viable strategy space lives at the tails.
- Hold to settlement pays the fee once; exiting early pays it twice.

---

# PHASE 0 — Ground truth (do this first, ~30–45 min)

Do not write a single line of strategy code until this is done and written up.

Establish from **Kalshi's own documentation and live API responses**, not from blog posts:

1. Exact series ticker(s) and market ticker format for the 15-minute BTC market. Confirm whether ETH and other assets have equivalents.
2. **Settlement mechanics, precisely.** Public sources contradict each other on this — some say the settle is a single captured price, others say it's a 60-second average of the CF Benchmarks real-time index sampled once per second over the final minute. This distinction materially changes the pricing model (an average over the last minute has lower variance than a point sample, so late-window contracts should be priced *further* from 50¢ than a point-sample model implies). Resolve it definitively and document the source.
3. `floor_strike` vs `strike_threshold` vs `expiration_value` on the market record. Confirm whether both the strike and the realised settle value are retrievable from the public API after settlement — if so, historical settlement replay is self-contained and needs no external index licence.
4. Strike banding: is the strike a round number near spot at open, or exactly spot at open? How much does it drift from spot at open?
5. Tie handling when `expiration_value` exactly equals the threshold.
6. Fee schedule: taker multiplier, maker multiplier, whether `KXBTC15M` is on the maker-fee list, rounding direction.
7. Tick size, min/max order size, position limits, and whether there is a pre-close trading halt.
8. Rate limits on REST and WebSocket, and which endpoints need authentication.
9. Whether Kalshi exposes any **historical order book**. (Expect: no. If not, note explicitly that the only way to get it is to record it live — which is why Phase 1 starts tonight and runs continuously.)

Write all of it to `docs/contract_spec.md` with a "confidence" column and a source link per row. Flag anything you could not confirm.

---

# PHASE 1 — Data capture (build this second, start it running immediately)

This phase is time-critical: recorded data accrues in wall-clock time, so get the recorder live before doing any research. Run it as a background process and let it collect while you work on Phases 2–4.

## 1a. Live recorder (`recorder/`)

Two independent processes, each with its own supervisor, auto-reconnect with exponential backoff, and crash-safe append-only writes.

**Kalshi recorder** — for every open `KXBTC15M` market:
- Full order book snapshot + deltas (use the WebSocket if available; poll REST at the fastest rate the limits allow if not)
- Every public trade with price, size, taker side, timestamp
- Market metadata at open: strike, open time, close time
- Market record at settlement: `expiration_value`, result
- Log our own request→response latency on every call

**Spot recorder** — from at least three of the exchanges in the CF Benchmarks basket (Coinbase, Kraken, Bitstamp, LMAX, Gemini, itBit) plus Binance for depth:
- Best bid/ask top-of-book at every update
- All trades (aggregated trades are fine)
- L2 depth snapshots at 100ms–1s where free
- Perp funding rate, open interest, and the liquidation stream from Binance futures
- ETH spot on the same schema, for the lead-lag test in Phase 2

## 1b. Timestamp discipline — this is the part that kills projects

- Every row carries **three** timestamps: exchange event time, our receipt time, and our write time. All UTC, nanosecond integers, never local time, never naive datetimes.
- Sync the clock (NTP) at startup and log the offset. Re-check hourly and log drift.
- Record the measured wire latency per source so Phase 4 can replay with realistic delays.
- A single monotonic clock for all sequencing. Never sort by exchange timestamp across venues.

## 1c. Historical bulk download (`data/historical/`)

Free, no API key, years of depth:
- **`data.binance.vision`** — BTCUSDT and ETHUSDT: 1-second klines, `aggTrades`, `bookTicker`, plus the `metrics` directory (open interest, long/short account ratios) and funding-rate history. Download as much as bandwidth allows, minimum 2 years of 1s klines. This is the single most valuable free dataset available to us.
- **Kraken / Bitstamp / Coinbase** public OHLC and trade history endpoints for cross-venue comparison.
- **Deribit public API** (no auth required for market data): the DVOL index history and the current option chain with implied vols. Deribit is our only forward-looking vol source and it's free — do not skip it.
- **Kalshi** `KXBTC15M` settled-market history: walk the markets endpoint backwards as far as it will go, storing strike, settle value, result, open/close times, and candlesticks. This gives us settlement outcomes for a long history even though it gives us no order book.
- An economic-calendar scrape (CPI, PPI, FOMC, NFP release timestamps) purely for tagging vol regimes.

## 1d. Storage and hygiene

- Parquet, partitioned by `source/date/hour`. DuckDB for querying — do not build a database server.
- A `data/manifest.json` recording, per source per day: row count, first/last timestamp, detected gaps, and a checksum.
- A gap-detection pass that runs after every download and writes `data/gaps_report.md`. Silent gaps are worse than missing data.
- Everything is idempotent: re-running a download must not duplicate rows.

---

# PHASE 2 — What the underlying actually does

All of this on historical Binance/Kraken data. Every test reports effect size, a bootstrapped confidence interval, and the number of hypotheses tested alongside a Benjamini–Hochberg FDR correction. **State the number of hypotheses you tested in the final report.** An uncorrected p-value in this phase is worthless.

## 2a. Volatility (the highest-value work in this phase)

- Realized vol over 1m/5m/15m/1h/1d windows: close-to-close, Parkinson, Garman-Klass, Rogers-Satchell, bipower variation.
- EWMA and HAR-RV vol forecasts at a 15-minute horizon. Score them against realised vol out-of-sample (RMSE and QLIKE).
- **The intraday vol seasonality curve**: mean and median realized vol by minute-of-day (UTC) and by day-of-week, over the full history, with confidence bands. This directly addresses my time-of-day question and is probably the most useful single output of the night. Also check vol by minute-within-the-quarter-hour — is there a systematic pattern around the :00/:15/:30/:45 boundaries where these markets open and close?
- Jump detection (Lee-Mykland or bipower) and the unconditional frequency of a jump inside a 15-minute window.
- The empirical distribution of 15-minute log returns: fit a Student-t and a normal, report the tail index, and quantify how badly a Gaussian assumption misprices tail probabilities. This matters enormously for far-from-strike contracts.
- Vol clustering: given the last 15 minutes' realized vol decile, what's the distribution of the next 15 minutes'?

## 2b. Direction (expect null results — document them anyway)

- Autocorrelation of 15-minute returns and of return signs, at lags 1–20.
- Sign-persistence and reversal at 1s/10s/1m/5m/15m.
- Order-flow imbalance and cumulative volume delta as predictors of the next 15 minutes' sign.
- Book imbalance and depth asymmetry at the top 5–10 levels.
- **ETH→BTC lead-lag**: cross-correlation at lags from −60s to +60s and a Hayashi-Yoshida estimator for asynchronous data. Report whether any lead survives transaction costs. (My prior from watching videos is that these two are related — I want to know whether that relationship is *exploitable at 15 minutes* or just a long-horizon co-movement.)
- Funding rate and open-interest change as direction predictors.
- Liquidation cascades: conditional on a large liquidation print, what happens over the next 15 minutes?
- Macro events: for each scheduled release, measure the change in realized vol and the absolute return in the following 15/30/60 minutes. **Report macro effects as a vol result, and separately test whether direction is predictable — I expect it isn't.** For unscheduled news (tariff announcements and similar), note honestly that we don't have a clean timestamped dataset for free, and say what it would take to build one.

## 2c. Regimes

Cluster 15-minute windows by realized vol, trend strength, and hour-of-day. Report how many distinct regimes there are and how persistent they are. Check whether any Phase 2b result holds in one regime but not others — and treat that as a red flag for overfitting unless the subsample is large.

---

# PHASE 3 — Fair value model

This is the core deliverable. Build a function:

```
p_up = P(settle_value > strike | spot, strike, seconds_remaining, vol_state, ...)
```

## 3a. Models, in increasing sophistication

1. **Baseline (driftless GBM):** `p_up = Φ( ln(S/K) / (σ√τ) )` where σ is annualised vol scaled to τ. Get this working first; it is the benchmark everything else must beat.
2. **Settlement-aware:** if Phase 0 confirms the settle is a 60-second average, replace the terminal-value distribution with the distribution of the average over the final minute. This lowers effective variance late in the window.
3. **Fat-tailed:** Student-t or the empirical return distribution instead of Gaussian.
4. **Seasonal vol:** feed σ from the Phase 2a minute-of-day curve rather than a flat estimate.
5. **Blended vol:** combine trailing realized vol, an EWMA/HAR forecast, and Deribit short-dated implied vol. Fit the blend weights out-of-sample.
6. **Empirical/ML:** a gradient-boosted classifier on features `(ln(S/K)/√τ, τ, vol state, hour, order-flow features)` trained on historical windows with known outcomes. This must beat model 5 out-of-sample by a clear margin to justify its complexity — if it doesn't, say so and discard it.

## 3b. Scoring — do this rigorously

- Brier score and log loss on held-out windows, walk-forward, with a strict time-ordered split. No shuffled cross-validation, ever.
- Reliability/calibration curves in 5% probability buckets with counts per bucket.
- **The decisive comparison:** for every historical window where we have both, plot our model's probability against Kalshi's mid-price and score both against the realised outcome. If Kalshi's mid has a lower Brier score than our best model, we have no edge and the honest answer is to stop. Report this as the headline number.
- If our model beats the mid, find *where*: bucket the difference by seconds-remaining, by |ln(S/K)/√τ|, by hour-of-day, by vol regime. A real edge should be concentrated and explainable. A diffuse edge spread evenly across all buckets is almost always a bug or a look-ahead leak.

## 3c. Leak audit (mandatory, not optional)

I have been burned by exactly this before: an apparent edge in a previous project turned out to be a look-ahead leak where the anchor timestamp was at or after settlement. So:

- For every feature, write down the exact timestamp at which it becomes knowable and assert in code that it precedes the decision timestamp.
- Add a deliberate test that shifts every feature forward by one window and confirms the edge disappears.
- Add a shuffled-label test and confirm the edge goes to zero.
- Run the full pipeline on synthetic random-walk data with the same vol as BTC. **If the pipeline finds an edge on synthetic random data, the pipeline is broken.** This is the single most important test in the project. Do it early, not last.

---

# PHASE 4 — Backtest

Build two clearly separated tiers and never mix their results.

**Tier A — settlement replay (weak but available now).** Uses Kalshi's historical settled markets: strike, settle value, outcome, plus candlestick prices. Good enough to test "would we have been on the right side" and to compute calibration. Cannot model fills or spread. Every Tier A number must be labelled as an upper bound.

**Tier B — order-book replay (the only trustworthy tier).** Uses the Phase 1a recording. Not much data will exist tonight — that's expected. Build the engine now so it's ready as data accumulates.

Tier B realism requirements:
- Fee-inclusive P&L using the verified formula, with correct rounding.
- Explicit fill model: crossing the spread fills at the touch with slippage; resting orders fill only when the book trades through our price, with a conservative queue-position assumption (assume we are last in the queue at our price level).
- Replay with the measured latency from Phase 1b — decisions use only data that had arrived by the decision time.
- Adverse selection: track whether our resting orders fill disproportionately when the market is about to move against us. If they do, that's the whole story and the strategy is dead.
- No partial-fill optimism. Model partial fills.

Strategy sweep — implement each as a plug-in with declared parameters:
- Fair-value divergence: enter when |model p − market p| > threshold. Sweep the threshold.
- Late-window certainty: in the last 60–120 seconds, is the market slow to price a nearly-determined outcome?
- Mean reversion after a spot spike moves the contract price sharply.
- Maker/market-making: quote both sides around fair value, capture spread, manage inventory.
- Time-of-day-restricted versions of each (this tests my overnight-vs-daytime hypothesis directly).
- Fixed profit-take / stop-loss grids on top of the best entry rule — sweep the grid and report the full surface, not just the peak. **A sharp isolated peak in the parameter surface is overfitting; a broad plateau is a possible real effect.** Say which one we have.

Validation:
- Purged walk-forward with an embargo period between train and test.
- Bootstrap the P&L distribution; report the CI, not just the mean.
- Deflated Sharpe ratio accounting for the number of strategy variants tried.
- Report the fee-adjusted-coinflip null alongside every result.

---

# PHASE 5 — Paper trader

Only after Phase 4 exists. Live Kalshi market data, entirely simulated fills, no order endpoints imported anywhere in the codebase.

- Runs continuously, restart-safe, resumes state from disk.
- Uses the same fill model as Tier B so paper results and backtest results are directly comparable. Log any divergence between them — that divergence is the most informative signal we'll get.
- Fractional Kelly sizing: `f = edge / odds`, multiplied by a safety factor of 0.25, hard-capped at 2% of notional bankroll per position and 10% total exposure. Hard-coded, not configurable to anything higher.
- A kill switch that halts on: daily loss limit, N consecutive losses, a data feed going stale beyond a threshold, or model calibration drifting past a set bound.
- Logs every decision including the ones where it chose not to trade, with the full feature vector, so we can audit the reasoning later.

---

# PHASE 6 — Verdict gates

Write `docs/GO_NO_GO.md` defining, **before seeing the results**, the bar that would have to be cleared before real money is even discussed:

- Minimum number of independent out-of-sample trades (I suggest ≥ 500 for a coinflip-adjacent market — justify whatever number you pick with a power calculation).
- Minimum fee-inclusive edge per trade with a confidence interval excluding zero.
- Consistency across at least two disjoint time periods and across time-of-day buckets.
- Calibration stability over the whole paper-trading run.
- Passing all Phase 3c leak tests.

Then fill in the actual results against those gates.

---

# Deliverables — what I read in the morning

Write `MORNING_REPORT.md` at the top level, and update it incrementally as you go rather than at the end, so it's useful even if you're interrupted. Structure it as:

1. **The verdict, in three sentences.** Is there any evidence of an edge in this market, yes or no? Lead with the answer.
2. **What I got wrong.** Which of my stated hypotheses (macro/tariffs mattering, ETH lead-lag, time-of-day regimes, profit-take/stop-loss optimisation) survived contact with data and which didn't. Be blunt about it — I would rather be corrected tonight than lose money later.
3. The headline table: our model's Brier score vs. Kalshi's mid-price Brier score, out-of-sample.
4. The intraday volatility seasonality chart and what it implies about when to trade.
5. Strategy sweep results, fee-inclusive, with CIs and the number of variants tested.
6. Leak-test results, including the synthetic random-walk control.
7. What's blocked on more recorded data, and how many days of recording we need before Tier B says anything meaningful.
8. The top three things to do next, ranked by expected information gain per hour of work.

Also produce: `docs/contract_spec.md`, `DECISIONS.md`, `PAID_OPTIONS.md`, `data/gaps_report.md`, `docs/GO_NO_GO.md`, and a `notebooks/` directory with the charts as PNGs.

# Working discipline for the overnight run

- Git repo, commit after every working unit with a descriptive message. Never leave the tree broken.
- Maintain `PROGRESS.md` as a running log with timestamps and a checkbox per sub-phase. I need to be able to see exactly where you stopped.
- Priority order if you run out of time or context: **Phase 0 → Phase 1a recorder running → Phase 1c bulk download → Phase 3c synthetic control → Phase 2a vol seasonality → everything else.** The recorder and the bulk download are the things that can't be recovered later; analysis can always be redone tomorrow.
- Prefer small, tested, boring code over clever code. Type hints, docstrings, `pytest` tests for every non-trivial function, especially the fee calculation and the probability model.
- If you discover something that invalidates a premise of this prompt, stop that thread, write it prominently in `MORNING_REPORT.md`, and reprioritise. Do not build on a premise you've disproved.

Begin with Phase 0.
