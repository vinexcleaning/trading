# PREREGISTRATION — does the weather model beat the MARKET, not just climatology?

**2026-08-06.** Written **before any model score, any edge, and any settled
outcome was joined to any price.** What had been measured when this file was
committed is listed exhaustively in §1.2, and it is all apparatus. Git history is
the evidence for that ordering, which is why this file is committed alone.

---

## 1. Why this exists

### 1.1 The gate that was never run

[`docs/GO_NO_GO.md`](GO_NO_GO.md) says of weather, in its own words:

> **"Edge vs the mid: still unmeasured. The deciding gate."**

The [2026-08-06 audit](../../AUDIT_2026-08-06.md) ranked this **#1 of sixteen
defects**, because weather is the only place in the programme where all of the
following are true at once:

| | |
|---|---|
| a model genuinely beats its benchmark | **K002 SETTLED** — persistence + hour-of-day beats climatology in all four cities, clustered CIs excluding zero, 812 independent settlements |
| the family clears the **power** bar | `KXTEMPDCH` has **512** settlements against the **481** needed (K004) |
| the family clears the **capacity** bar | 2,972 contracts of depth |
| **and the deciding comparison was never made** | this file |

**Beating climatology is not beating the price.** `scripts/weather_model.py`
imports a helper called `compare_to_mid` and then passes it
`base = models["climatology"]` — so despite the name, **no market price has ever
entered the weather work.** That is the whole gap.

### 1.2 Everything measured before this file was written

| measured | value |
|---|---|
| `KXTEMPDCH` settled markets | **5,186** over **512** settlement hours, 2026-07-08 → 07-30 |
| **market lifetime, open → close** | **exactly 1.00 h on 5,162 of 5,186** |
| candles retrievable for settled markets | **yes** — 248 of 250 sampled returned candles |
| candles available **before** the final hour | **ZERO.** A 24-hour request returns 2 candles: the hour ending at close, and one after |
| two-sided book at the **start** of the market's only hour | **0 of 248** |
| ask present but **no bid** at the start | **122 of 248 (49%)** |
| no book at all at the start | 126 of 248 |
| markets trading during the hour | 177 of 248 had volume |

**Not measured, and deliberately not:** any model probability, any settled
outcome joined to any price, any edge, any Brier score against the market.

### 1.3 ⚠ The structural fact that shapes the whole design

**A `KXTEMPDCH` market exists for one hour and settles on a temperature observed
at the end of that hour.** There is no multi-day pre-match window; the market is
born, trades for sixty minutes, and resolves.

And at the moment it is born, **not one market in the sample has a bid.**

Two consequences, and the first nearly caused me to kill this on the wrong axis:

1. **Selling is impossible and a "mid" does not exist.** Any test framed as
   *model vs the mid* is unrunnable here — there is nothing to average. Marking
   to a mid would be inventing a price, which is **T008**, the retraction that
   turned +24.6% ROI into −30.9%.
2. **Buying is still possible, and needs only an ask.** A hold-to-settlement buy
   lifts the offer and never sells. **49% of markets have an offer at the open.**
   So the honest version of this gate is *model vs the ASK*, not *model vs the
   mid* — and it is a strictly harder test than the one `GO_NO_GO.md` asked for,
   because the ask is above any mid.

**This design tests the ask. The phrase "edge vs the mid" is retired here as
unrunnable, and the reason is recorded rather than the words being reused.**

---

## 2. The test

### 2.1 The strategy — **W1**

For every settled `KXTEMPDCH` market:

```
anchor        = the market's OPEN, i.e. the start of its only hour of life
p_model       = P(temp_at_close >= strike), from persist_hod, using ONLY
                temperatures observed at hours strictly BEFORE the anchor
ask_c         = yes_ask_open of the candle whose end_period_ts == close_ts
edge_c        = 100 * p_model - ask_c
cost_c        = fee(ask_c)                      # common/kalshi_fees.py, taker
ENTER  iff  edge_c > cost_c + slippage
```

Buy one contract at the ask, hold to settlement, realise `100 - ask_c` if the
temperature reaches the strike and `-ask_c` if it does not, minus the fee.
**Kalshi charges no settlement fee, so there is exactly one fee per trade.**

### 2.2 The model, unchanged

`persist_hod` exactly as in `scripts/weather_model.py`: last observed temperature
plus the hour-of-day change profile, with the persistence error standard
deviation as the spread. **Parameters are fit on the first 60% of settlement
hours and never refit** — identical to K002's split, so this is not a new model
and cannot be tuned to the price.

### 2.3 The leak rule, and it is stricter than K002's

K002 required features from hours strictly earlier than the settlement hour.
**That is not sufficient here**, because the market opens one hour before close
and the previous hour's temperature is published at the top of that hour. So:

> **Every feature must come from a temperature observation at an hour strictly
> earlier than the market's OPEN time**, not merely earlier than its close. The
> build asserts it and refuses to write a panel that violates it.

Asserted, plus two canaries that run before any return prints:

1. **Extreme-quote canary (T010/T011).** If more than 1% of entry asks are ≤2¢
   or ≥98¢ **and** ≥99% of those are correct, the anchor is **VOID**.
2. **Ask-provenance canary.** `yes_ask_open` must come from the candle whose
   `end_period_ts == close_ts` and no other. Any market contributing a candle
   with `end_period_ts > close_ts` — a post-settlement candle, which exists on
   every market and reads 0 bid / 100 ask — is **dropped and counted.**

### 2.4 Unit of observation, and the trap K003 already fell into

> **K003 is the retraction that matters most here.** It claimed the weather model
> was validated on **8,090 test markets**. A ten-strike ladder is **one
> temperature reading, not ten markets** — effective n was ~800 settlement hours
> and the intervals were **~3× too tight.**

So:

| | |
|---|---|
| **unit of observation** | **the SETTLEMENT HOUR**, never the market. All ~10 strikes of one hour resolve off one temperature |
| **every CI** | bootstrap resamples **settlement hours**, not markets |
| **reported beside every n** | nominal markets **and** effective hours |
| **one trade per hour** | at most one entry per settlement hour, taken at the **largest** qualifying edge. If two strikes qualify, taking both is one bet counted twice |

### 2.5 The cost bar

`cost = fee(ask) + slippage`, recomputed per trade from
`common/kalshi_fees.py` and nothing else (GUARDS #6, enforced repo-wide by
`common/tests/test_no_fee_reimplementation.py`). Slippage swept at
**0.0 / 0.5 / 1.0 / 2.0¢, primary 1.0¢**.

**No half-spread term** — buying at the ask *is* crossing, and there is no bid to
half anyway.

> ⚠ **Depth is not in a candle, and this design cannot measure it.** A qualifying
> ask may be for one contract. Every surviving cell must be reported with the
> caveat that **size is unverified**, and `data/raw/source=kalshi_book_tier2`
> (one day, 2026-07-30) is the only depth evidence that exists for this family.

---

## 3. Controls, because the family is now the test family

### 3.1 The three that gate the run

| | control | what a failure means |
|---|---|---|
| **N1** | **Climatology instead of `persist_hod`**, everything else identical. Climatology is the benchmark K002 already showed is *worse*. | If climatology trades as well as the real model, the "edge" is the cost gate selecting cheap asks, not the forecast. **N1 positive ⇒ nothing is reportable.** |
| **N2** | **Shuffled outcomes** within (hour-of-day × 5¢ ask bucket), 200 draws. | Gives the noise floor of the whole pipeline. Any real result must exceed it. **This is B023's method, which found 2 real discoveries against a null average of 4.1 and correctly reported nothing.** |
| **N3** | **The always-50 model.** | A model that knows nothing must not clear the gate. |

### 3.2 The naive benchmarks, reported beside every result

- **B0-ALLASK** — buy every market with any ask, no model.
- **B0-CHEAP** — buy every ask below 20¢ (the "lottery ticket" shape that has
  lost money on every market in this programme).

### 3.3 The holdout

**The newest 30% of settlement hours is SEALED** and touched **once**, by a
design that has already cleared everything else. `KXTEMPDCH` covers 2026-07-08 →
07-30, so the holdout is roughly 07-23 onward. Written to
`reports/weather_holdout_hours.json` at the first run and frozen.

**The other three cities (`KXTEMPLAXH`, `KXTEMPCHIH`, `KXTEMPAUSH`) are a
REPLICATION arm, not extra sample.** They are run only if `KXTEMPDCH` survives,
and disagreement between cities is a finding, not something to pool away.

---

## 4. Decision rules, fixed now

1. **BH-FDR at q = 0.10** across the whole grid — 4 slippage values × 3 model
   arms × 2 anchors = **24 cells**, one denominator.
2. **Two-sided p-values.** A systematic *loss* is a finding: it would be the
   fifth confirmation that Kalshi is the sharp line, on a market type nothing
   else in this repo has tested.
3. **Every CI clustered on the settlement hour**, effective n printed beside
   nominal n, **MDE beside every null**.
4. **The surface, not the peak** — each surviving cell labelled PEAK or PLATEAU.
5. **Monotone strengthening with sample size is CONTAMINATION**, not evidence
   (GUARDS #10, and the error H10 already tripped).
6. **N1 gates the run.** A positive result on the climatology arm voids it.
7. **Capacity is reported, never assumed** — §2.5's depth caveat accompanies
   every surviving cell, and a cell whose median qualifying ask is under 5¢ is
   additionally flagged, because **every cheap-contract strategy in this
   programme has lost** (crypto's 5¢ entries lose 44% of stake; tennis longshots
   −5.42¢).

## 5. What I expect, written down so a null is a measurement

**I expect W1 to fail, and the specific mechanism I expect is the one already
visible in §1.2: the gate will fire almost only on strikes with no bid and a
cheap ask** — that is, precisely where the market has declined to make a price.
A 3¢ offer on a strike nobody will bid for is not a mispricing; it is an absence
of a market, and **B024/B027 is exactly this** — an apparent edge that is
monotonic in book width and vanishes wherever the book is tradeable.

Against that, the honest case for running it: **K002 is a real, well-controlled
result.** The model does beat climatology on 812 independent settlements with a
positive control and clustered intervals. If a genuinely better forecast cannot
be monetised even here, that is worth knowing precisely, and it is the last
untested corner of the exchange this programme identified.

**45 corrections in this repo and every one shrank the edge.**

## 6. What would make me revise

A cell clearing BH-FDR **and** the cost bar **and** the sealed holdout **and**
showing a plateau **and** clean on N1/N2/N3 **and** with a median qualifying ask
above 5¢. **Fewer than six and it is recorded as a lead, not a finding.**
