# The Adjusted Tennis Skill Score

A single number, 0–100, answering one question: **how much confidence does the
evidence support that this wallet has a repeatable, copyable tennis edge?**

It is deliberately *not* a measure of profit. A wallet can be enormously
profitable and score badly here, and that is the intended behaviour.

Every component is stored and surfaced on the wallet page, so a ranking is
always explainable rather than asserted.

---

## The formula

```
base_score   = Σ (component_score × weight)
final_score  = base_score × Π penalties
```

Components are each normalised to 0–100 before weighting.

| Component | Weight | What it measures |
|---|---|---|
| Copyable ROI | 25% | Return achievable by a delayed follower, after shrinkage |
| Profit factor | 15% | Gross profit ÷ gross loss, on copyable results |
| Sample confidence | 15% | How much the record can be trusted at this sample size |
| Consistency | 10% | Stability across time periods and market types |
| Drawdown | 10% | Peak-to-trough decline |
| Recency | 10% | Weighting toward recent performance |
| Liquidity fit | 5% | Whether it trades markets deep enough to copy |
| Concentration | 5% | Independence from one or two outlier trades |
| Data quality | 5% | Strength of the price evidence behind the copyable figures |

Weights are set in configuration (`SCORE_WEIGHT_*`) and validated at startup to
sum to 1.0. They live in the environment rather than the runtime settings API
because changing them invalidates every stored score.

### Normalisation ranges

| Component | Worst (0) | Best (100) |
|---|---|---|
| Copyable ROI | −20% | +30% |
| Profit factor | 0.5 | 3.0 |
| Drawdown | 60% | 0% |
| Concentration | 60% from one trade | 0% |

Values outside a range clamp rather than extrapolate, so one spectacular
quarter cannot buy an unbounded score.

---

## Why copyable ROI, and why shrunk

The headline input is **not** the wallet's raw ROI. It is:

1. **Copyable ROI** — recomputed at the benchmark follower delay (default 15s)
   using the price a follower could actually have obtained, after spread and
   modelled slippage. See [COPYABILITY.md](COPYABILITY.md).
2. **Shrunk toward the population mean** by sample size (Bayesian shrinkage,
   strength `BAYESIAN_SHRINKAGE_STRENGTH`, default 30):

   ```
   shrunk = (n × observed + k × population_mean) / (n + k)
   ```

With `k = 30`, a wallet with 8 trades keeps roughly 21% of its observed edge;
one with 300 keeps 91%. This is what stops eight lucky wins from topping the
table — the mechanism is arithmetic, not a disclaimer.

Worked example from the bundled demo data:

| Wallet | Trades | Raw ROI | Copyable ROI | Shrunk | Score |
|---|---|---|---|---|---|
| Eight lucky wins | 8 | 147% | 149% | 42% | **51.4** |
| Steady grinder | 121 | 32.9% | 19.2% | 18.3% | **80.4** |

The lucky wallet has 7× the raw ROI and scores 29 points lower.

---

## Penalties

Applied multiplicatively after the weighted sum, so they compound:

| Penalty | Multiplier | Trigger |
|---|---|---|
| Below minimum trades | ×0.60 | Fewer than 20 completed tennis trades |
| High concentration | ×0.80 | One trade dominates total profit |
| Severe drawdown | ×0.80 | Drawdown beyond the configured limit |
| Negative 30-day trend | ×0.85 | Recent performance materially worse |
| Negative copyable ROI | ×0.55 | A delayed follower would have lost money |
| Market-making behaviour | ×0.65 | Two-sided quoting rather than directional views |
| Low liquidity | ×0.90 | Trades markets too thin to copy at size |
| Ambiguous reconstruction | ×0.85 | Position history could not be rebuilt confidently |

Every applied penalty is stored with its multiplier and shown in the UI.

---

## Statistical safeguards

- **Confidence intervals** on ROI and copyable ROI (bootstrap, 2,000 iterations).
- **P(positive edge)** — bootstrap probability the copyable edge is genuinely
  above zero. **Withheld entirely below the sample floor**: on eight trades a
  bootstrap cannot distinguish skill from luck, and printing "100%" next to
  "insufficient confidence" invites exactly the misreading this system exists to
  prevent.
- **Sample confidence** reaches 100 only at `MIN_TRADES_FOR_FULL_CONFIDENCE`
  (default 100 completed trades).
- **Recency weighting** with a 90-day half-life.
- **Stability** measured across time periods and market types.

---

## The drawdown base

True bankroll is not visible on-chain, so drawdown percentage needs an assumed
capital base. It is the larger of the biggest single stake and a bankroll of
`ASSUMED_BANKROLL_MULTIPLE` × median stake.

- Using the largest stake alone understates capital, making a 300-trade wallet
  betting $100 a time look catastrophic against $100 of capital.
- Using cumulative volume overstates it, flattering high-turnover wallets.

This is an explicit modelling assumption applied identically to every wallet, so
comparisons stay fair. The reported percentage is **capped at 100%**: exceeding
the assumed bankroll reads as "lost more than everything", which is an artifact
of the assumption rather than a fact. The absolute drawdown figure is uncapped.

---

## Qualification

A wallet is *qualified* — eligible to generate alerts — only when it clears
every hard gate simultaneously (all configurable):

- ≥ 30 completed tennis trades
- Skill score ≥ 75
- Copyable ROI > 0 at the benchmark delay
- Data confidence ≥ 80
- Max drawdown ≤ 40%
- No severe risk flags

Disqualification reasons are stored individually, so "why isn't this wallet
alerting?" always has a specific answer.

---

## What this score cannot do

- It cannot see off-platform hedges, so an apparent directional bet may be one
  leg of a position this system cannot observe.
- It measures only wallets that were added. Publicly visible wallets skew toward
  winners, and survivorship bias is not corrected — it is flagged.
- It is descriptive of the past. Nothing here forecasts.
