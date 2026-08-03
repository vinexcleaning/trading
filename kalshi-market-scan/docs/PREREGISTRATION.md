# Pre-registration

**Written before any strategy sweep. Honest status: no Phase 7 sweep was run**, because
nothing cleared the Phase 1 structural screen with a mechanism *and* demonstrated
fillable liquidity. This document therefore serves its second purpose — it fixes the
rules in advance so that the next session cannot tune them after seeing results.

## Standing rules

1. Every reported number is out-of-sample. Splits are strictly time-ordered. No
   shuffled cross-validation, ever.
2. All P&L is fee-inclusive, using the verified formula
   `fee_cents = ceil(7 * C * P * (1-P))` with per-fill ceiling (`src/.../fees.py`,
   23 tests).
3. The null is never zero — it is the **fee-adjusted coinflip**. A model must beat
   the round-trip cost, not merely beat 50/50.
4. FDR control (Benjamini–Hochberg, α = 0.05) across the entire
   `docs/HYPOTHESIS_LEDGER.md`, not per family.
5. Any surviving candidate must come with a one-sentence mechanism explaining why the
   counterparty is wrong and why the mistake persists. No mechanism → discarded
   regardless of p-value.

## Per-family hypotheses, features, and grids

### A. No-arbitrage violations (`KXBTC`, `KXINX*`, `KXTEMP*`, bucket and ladder families)
- **Hypothesis:** violations net of round-trip fees on every leg occur, and persist
  long enough with enough depth to be captured.
- **Features allowed:** live top-of-book prices and sizes only. No forecast of any kind.
- **Grid:** persistence threshold ∈ {1, 5, 15, 30, 60} s; minimum net edge ∈
  {0.5, 1, 2, 3} ¢; minimum depth ∈ {10, 50, 200} contracts. 60 combinations.
- **Metric:** count and total net-of-fee value of violations that persisted ≥ threshold
  with ≥ depth available.
- **Threshold:** a family is interesting if ≥ 20 such events occur per week.
- **Pre-committed kill:** if zero violations survive fees over 7 days of scanning,
  the category is closed and not revisited.

### B. Weather temperature ladders (`KXTEMP*H`, `KXHIGH*`)
- **Hypothesis:** a model built on NWS observations plus persistence beats the Kalshi
  mid, concentrated in the final hours before settlement when the observation is
  partially known.
- **Features allowed, with knowability timestamps asserted in code:** latest NWS
  station observation (temp, dewpoint, wind) strictly prior to the decision; hours
  elapsed in the settlement window; climatological hour-of-day mean; the strike.
  **Forbidden:** any observation timestamped at or after the decision instant, and the
  settlement value itself.
- **Grid:** blend weight on observation-vs-climatology ∈ {0.5, 0.6, 0.7, 0.8, 0.9,
  1.0}; sigma estimate ∈ {trailing 7-day, trailing 30-day}; entry threshold on
  model-minus-mid ∈ {3, 4, 5, 7} ¢. 48 combinations per city family.
- **Metric:** Brier and log loss vs the Kalshi mid on the same settlements, plus
  fee-inclusive per-trade edge with a bootstrap CI.
- **Threshold:** CI on per-trade edge excludes the round-trip cost, and the effect is
  concentrated in an explainable region (late window), not diffuse.

### C. `KXBTC15M` fair value
- **Hypothesis:** a settlement-aware fat-tailed model with a vol blend beats the
  Kalshi mid by more than 3.5 percentage points at the money.
- **Features allowed:** spot from ≥3 venues at the last fully-closed 1-minute candle
  before the decision; EWMA and trailing realized vol; Deribit DVOL and implied vol;
  perp funding, basis and open-interest change **as vol inputs only, never direction**;
  seconds remaining; the strike (= previous window's settle, known at open).
- **Grid:** vol estimator ∈ {EWMA λ=0.94, EWMA λ=0.97, RV60, HAR-RV}; blend weight on
  implied vol ∈ {0, 0.25, 0.5}; Student-t dof ∈ {4, 6, ∞}; decision offset ∈
  {780, 600, 300, 120, 60} s. 180 combinations.
- **Metric:** Brier vs the mid; then fee-inclusive P&L with the fill model below.
- **Threshold:** per-trade edge CI must exclude **3.5¢**, not zero.
- **Pre-committed prior:** expected to fail. Recorded here so that failure is not
  reinterpreted as success.

## Fill model (identical in backtest and paper trading)

- Crossing orders fill at the touch, plus slippage = half the observed spread, capped
  at the depth available at that level.
- Resting orders fill **only** when the book trades through our price, and we assume
  we are last in the queue at that price.
- Replay at measured latency: a decision may only read data that had already arrived,
  using recorded `recv_ns`.
- Purged walk-forward with a one-period embargo between train and test.

## Sizing (hard-coded, not a parameter)

Quarter-Kelly, capped at 2% of notional bankroll per position and 10% total exposure.
No martingale, no doubling after losses, no averaging down. These are not swept.

## What would make me abandon a family

Stated in advance so it cannot be softened later:
- Median depth at the touch below 50 contracts → capacity kill, regardless of edge.
- Edge diffuse across time-to-expiry and hour-of-day rather than concentrated → treated
  as a leak, not an edge.
- Any Phase 4 leak test failing → the family's results are void, not caveated.
