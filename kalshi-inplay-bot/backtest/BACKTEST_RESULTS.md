# Kalshi tennis backtest — results
Offline replay of the v3 strategy rules against 4 weeks of Kalshi 1-minute candlestick history. No live trading, no credentials loaded, read-only public market data.
## Bottom line
**No configuration of any strategy tested was profitable — including the best of 480 parameter combinations, and including a random-entry control.** The v3 entry signal does contain a small real edge (+1.9c per contract), but round-trip trading costs are 4.1c. The edge is less than half the cost of harvesting it.
The v3 exit ladder makes this worse, not better: it turns a +1.9c raw edge into −1.3c *before* any costs are applied.
## 1. Data
| | |
|---|---|
| Source | Kalshi public candlestick API (`api.elections.kalshi.com`) |
| Interval | 1 minute (finest Kalshi offers; 1/60/1440 are the only valid values) |
| Window | 2026-06-29 → 2026-07-27 (28 days) |
| Markets | 14,162 settled (7,081 matches × 2 mirrored sides) |
| Candle rows | 4,971,350 raw → 4,931,103 after cleaning |
| Live candles | 2,941,821 (59.7%) after pre-match/dormancy/spread filters |
| Market views | 13,658 |
| Train / holdout | oldest 60% = 8,218 markets / newest 40% = 5,440 markets |
### Execution assumptions
- Signals on the **bid/ask midpoint**; execution on the **real ask** (buys) and **real bid** (sells), plus **1c** extra slippage each side
- Fees: taker both sides, `ceil(0.07 × C × P × (1−P))`, verified against the spec's reference points (1.75c/contract at 50c, 0.63c at 90c/10c)
- Same-candle stop/target ambiguity always resolves **stop first**
- Candles with spread > 15c dropped as untradeable
- Fixed $6 notional per trade
- One open position per match at a time (the two sides of a match are near-perfect mid-price inverses — median difference 0.00c)
## 2. Step 5 — five strategies, training set
| strategy | trades | matches | win_rate | avg_win_c | avg_loss_c | gross | fees | net | net_c/trade | net_$/trade | max_dd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S2 buy&hold | 996 | 995 | 64.50 | 32.70 | -65.70 | -62.73 | 150.57 | -213.30 | -2.29 | -0.21 | 238.39 |
| S5 random | 2885 | 1525 | 13.20 | 8.40 | -10.80 | -1,699.74 | 1,126.46 | -2,826.20 | -8.28 | -0.98 | 2,825.58 |
| S1 V3 ramp | 1501 | 995 | 45.40 | 12.20 | -27.20 | -869.32 | 430.07 | -1,299.39 | -9.36 | -0.87 | 1,300.39 |
| S3 fade drop | 3530 | 1478 | 39.50 | 7.40 | -20.80 | -3,048.97 | 1,461.50 | -4,510.47 | -9.67 | -1.28 | 4,512.34 |
| S4 ride rise | 3349 | 1454 | 38.00 | 7.30 | -21.30 | -2,816.45 | 1,268.72 | -4,085.17 | -10.40 | -1.22 | 4,082.16 |

Sorted by net cents per trade. Every strategy loses. **S1 — the v3 strategy — performs worse than random entry (S5).**
### Signal funnel
| strategy | live candles | structural events | pass vol filter | pass hold | pass price band | traded (after dedup) |
|---|---|---|---|---|---|---|
| S1 V3 ramp | 1,695,733 | 8,214 | 6,498 | 4,681 | 1,603 | 1,501 |
| S2 buy&hold | 1,695,733 | 8,214 | 6,498 | 4,681 | 1,603 | 996 |
| S3 fade drop | 1,695,733 | 7,724 | 7,724 | 7,724 | 4,123 | 3,530 |
| S4 ride rise | 1,695,733 | 8,214 | 8,214 | 8,214 | 3,896 | 3,349 |
| S5 random | 1,687,650 | 6,715 | 6,715 | 6,715 | 3,053 | 2,885 |

### Where the money actually goes (cents per contract)
| strategy | trades | edge_c | spread_slip_c | fees_c | net_c |
|---|---|---|---|---|---|
| S2 buy&hold | 996 | 1.86 | 2.52 | 1.62 | -2.29 |
| S5 random | 2885 | -0.65 | 4.33 | 3.29 | -8.28 |
| S1 V3 ramp | 1501 | -1.31 | 4.98 | 3.07 | -9.36 |
| S3 fade drop | 3530 | -1.41 | 5.06 | 3.20 | -9.67 |
| S4 ride rise | 3349 | -2.11 | 5.04 | 3.25 | -10.40 |

`edge_c` is the raw price move before any trading cost. This is the single most important table in the document:

- **S2 (buy & hold) is the only strategy with a positive raw edge: +1.86c.** The v3 entry trigger genuinely predicts a small upward drift.
- That edge is destroyed by 2.52c of spread+slippage and 1.62c of fees → net −2.29c.
- **S1's raw edge is −1.31c.** The exit ladder does not merely fail to add value; it converts a positive edge into a negative one before costs.
- S3, S4 and S5 all have raw edges at or below zero — there is no path edge to harvest.
### Slippage sensitivity (net c/trade)
| strategy | 0.0 | 1.0 | 2.0 |
|---|---|---|---|
| S1 V3 ramp | -7.66 | -9.36 | -11.32 |
| S2 buy&hold | -1.31 | -2.29 | -3.31 |
| S3 fade drop | -7.80 | -9.67 | -11.50 |
| S4 ride rise | -8.52 | -10.40 | -12.22 |
| S5 random | -6.28 | -8.28 | -10.23 |

Nothing flips sign between 0c and 2c. The losses are not an artifact of the slippage assumption — at **zero** extra slippage every strategy still loses.
### By spread bucket

**S1 V3 ramp**
| spread_bucket | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| 0-2c | 857 | 651 | 52.20 | -522.30 | -6.61 |
| 3-5c | 387 | 344 | 40.80 | -398.05 | -11.12 |
| 6-10c | 213 | 193 | 31.90 | -297.82 | -14.96 |
| 10c+ | 44 | 43 | 18.20 | -81.23 | -20.29 |

**S3 fade drop**
| spread_bucket | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| 0-2c | 2114 | 1067 | 42.60 | -2,434.22 | -8.69 |
| 3-5c | 772 | 580 | 38.50 | -986.61 | -9.77 |
| 6-10c | 476 | 401 | 30.90 | -770.81 | -12.31 |
| 10c+ | 168 | 146 | 29.80 | -318.83 | -14.11 |

**S5 random**
| spread_bucket | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| 0-2c | 1944 | 1050 | 13.10 | -1,697.00 | -7.32 |
| 3-5c | 715 | 582 | 14.70 | -745.20 | -8.97 |
| 6-10c | 198 | 189 | 10.10 | -320.78 | -13.81 |
| 10c+ | 28 | 27 | 7.10 | -63.22 | -17.74 |

Performance degrades monotonically with spread in every strategy — the honest bid/ask execution model is doing its job. But note the tightest bucket (0–2c) still loses 6.6–8.7c per trade. **There is no spread regime in which this is profitable**, so 'trade only liquid markets' does not rescue it.
### By series

**S1 V3 ramp**
| tournament | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| WTA | 80 | 52 | 55.00 | -38.44 | -5.27 |
| Challenger | 303 | 193 | 49.80 | -217.56 | -7.81 |
| ATP | 75 | 47 | 48.00 | -61.72 | -8.83 |
| ITF-W | 489 | 319 | 43.60 | -445.23 | -9.77 |
| ITF-M | 554 | 384 | 42.80 | -536.44 | -10.50 |

**S2 buy&hold**
| tournament | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| ITF-M | 384 | 384 | 66.40 | -38.73 | -0.81 |
| Challenger | 193 | 193 | 64.20 | -37.55 | -1.95 |
| ITF-W | 320 | 319 | 64.10 | -63.75 | -2.40 |
| WTA | 52 | 52 | 61.50 | -27.00 | -5.54 |
| ATP | 47 | 47 | 55.30 | -46.28 | -11.45 |

**S3 fade drop**
| tournament | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| ATP | 190 | 68 | 45.30 | -176.49 | -7.07 |
| WTA | 198 | 67 | 43.90 | -222.55 | -8.59 |
| Challenger | 744 | 289 | 40.20 | -899.00 | -9.33 |
| ITF-W | 1108 | 470 | 39.80 | -1,390.61 | -9.64 |
| ITF-M | 1290 | 584 | 37.40 | -1,821.81 | -10.44 |

**S4 ride rise**
| tournament | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| Challenger | 719 | 282 | 42.40 | -720.44 | -8.41 |
| WTA | 189 | 66 | 40.20 | -234.42 | -10.07 |
| ITF-W | 996 | 453 | 39.20 | -1,185.77 | -10.33 |
| ATP | 179 | 69 | 33.50 | -234.73 | -11.18 |
| ITF-M | 1266 | 584 | 35.00 | -1,709.82 | -11.52 |

**S5 random**
| tournament | trades | matches | win_rate | net | net_c_per_trade |
|---|---|---|---|---|---|
| WTA | 362 | 104 | 5.00 | -299.62 | -7.10 |
| ATP | 479 | 124 | 1.70 | -410.79 | -7.29 |
| Challenger | 693 | 354 | 12.70 | -613.36 | -7.41 |
| ITF-M | 748 | 508 | 19.50 | -820.84 | -9.26 |
| ITF-W | 603 | 435 | 20.20 | -681.60 | -9.54 |

Every series loses in every strategy. The edge does not live in one segment and get averaged away — there is no segment.
## 3. Step 6 — parameter sweep (S1, best of S1/S3/S4)
### One knob at a time
| dim | value | trades | matches | win_rate | net | net_c_per_trade | max_dd |
|---|---|---|---|---|---|---|---|
| max_price | 65 | 800 | 621 | 46.80 | -703.41 | -8.83 | 700.62 |
| max_price | 70 | 1169 | 822 | 45.30 | -1,046.55 | -9.37 | 1,046.40 |
| max_price | 75 | 1501 | 995 | 45.40 | -1,299.39 | -9.36 | 1,300.39 |
| max_price | 80 | 1828 | 1173 | 45.40 | -1,523.65 | -9.28 | 1,524.28 |
| max_price | 85 | 2160 | 1360 | 46.00 | -1,712.68 | -9.07 | 1,714.10 |
| max_price | 99 | 2828 | 1722 | 48.10 | -2,087.96 | -8.95 | 2,089.43 |
| thresh | 8 | 4695 | 2027 | 39.80 | -4,333.23 | -9.86 | 4,337.62 |
| thresh | 10 | 2725 | 1489 | 43.40 | -2,420.72 | -9.54 | 2,424.61 |
| thresh | 12 | 1501 | 995 | 45.40 | -1,299.39 | -9.36 | 1,300.39 |
| thresh | 15 | 571 | 462 | 47.10 | -474.28 | -9.21 | 473.95 |
| thresh | 20 | 125 | 117 | 47.20 | -94.18 | -8.63 | 94.31 |
| stop | 15 | 1540 | 995 | 32.70 | -1,286.48 | -9.01 | 1,284.56 |
| stop | 20 | 1516 | 995 | 41.30 | -1,258.92 | -9.00 | 1,256.52 |
| stop | 25 | 1497 | 995 | 46.20 | -1,307.06 | -9.44 | 1,307.87 |
| stop | 30 | 1475 | 995 | 50.40 | -1,307.65 | -9.59 | 1,307.45 |
| target | 10 | 1519 | 995 | 51.20 | -1,388.47 | -9.86 | 1,388.21 |
| target | 15 | 1501 | 995 | 45.40 | -1,299.39 | -9.36 | 1,300.39 |
| target | 20 | 1499 | 995 | 40.10 | -1,292.39 | -9.34 | 1,291.55 |
| target | 25 | 1496 | 995 | 35.80 | -1,306.79 | -9.47 | 1,309.40 |

The entire response surface spans −8.6c to −9.9c. No single parameter moves the result more than ~1.2c, and none approaches zero.
### Full grid — 480 configurations
**Configurations with positive net P&L per trade: 0 of 480.**

Top 10 with at least 100 trades:
| max_price | thresh | stop | target | trades | matches | win_rate | net | net_c_per_trade | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| 75.00 | 20.00 | 15.00 | 15.00 | 125.00 | 117.00 | 38.40 | -72.57 | -6.71 | 73.53 |
| 65.00 | 15.00 | 20.00 | 15.00 | 268.00 | 236.00 | 47.80 | -184.04 | -6.96 | 185.58 |
| 75.00 | 20.00 | 15.00 | 20.00 | 125.00 | 117.00 | 32.80 | -75.98 | -7.04 | 75.26 |
| 65.00 | 15.00 | 20.00 | 25.00 | 268.00 | 236.00 | 37.70 | -188.37 | -7.09 | 186.24 |
| 75.00 | 20.00 | 15.00 | 25.00 | 125.00 | 117.00 | 28.80 | -77.66 | -7.13 | 77.22 |
| 75.00 | 20.00 | 15.00 | 10.00 | 125.00 | 117.00 | 43.20 | -78.01 | -7.18 | 78.48 |
| 65.00 | 15.00 | 25.00 | 25.00 | 267.00 | 236.00 | 43.10 | -191.36 | -7.24 | 188.47 |
| 65.00 | 15.00 | 25.00 | 15.00 | 267.00 | 236.00 | 52.80 | -193.45 | -7.36 | 192.18 |
| 65.00 | 15.00 | 15.00 | 25.00 | 268.00 | 236.00 | 29.90 | -196.28 | -7.39 | 194.35 |
| 65.00 | 15.00 | 15.00 | 15.00 | 268.00 | 236.00 | 38.10 | -197.28 | -7.45 | 195.67 |

Best overall ignoring sample size: -4.90 c/trade (47 trades). Range across all 480: -11.43 to -4.90, std 0.95.
### Sensitivity of the best configuration
| dim | from | to | net_c | delta | trades |
|---|---|---|---|---|---|
| max_price | 75.00 | 70 | -4.94 | 1.77 | 86.00 |
| max_price | 75.00 | 80 | -8.31 | -1.60 | 162.00 |
| thresh | 20.00 | 15 | -8.47 | -1.76 | 574.00 |
| stop | 15.00 | 20 | -8.88 | -2.17 | 125.00 |
| target | 15.00 | 10 | -7.18 | -0.48 | 125.00 |
| target | 15.00 | 20 | -7.04 | -0.34 | 125.00 |

Moving **one** knob **one** notch shifts the result by up to 2.17c — roughly a third of the best config's own value. A result that moves that much under a one-notch change is not a stable optimum; it is noise-fitting. The holdout confirms this.
## 4. Step 7 — holdout (newest 40%, touched once)
| config | train_trades | train_net_c | train_net | hold_trades | hold_matches | hold_win | hold_avg_win_c | hold_avg_loss_c | hold_gross | hold_fees | hold_net | hold_net_c | hold_dd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| max75/th20/sl15/tg15 | 125 | -6.71 | -72.57 | 102 | 96 | 26.50 | 12.20 | -19.40 | -72.24 | 30.49 | -102.73 | -11.03 | 102.16 |
| max65/th15/sl20/tg15 | 268 | -6.96 | -184.04 | 224 | 199 | 38.40 | 11.60 | -24.30 | -161.39 | 73.12 | -234.51 | -10.53 | 237.72 |
| max75/th20/sl15/tg20 | 125 | -7.04 | -75.98 | 102 | 96 | 24.50 | 16.90 | -19.40 | -66.96 | 30.17 | -97.13 | -10.49 | 99.01 |
| max75/th12/sl24/tg15 | 1501 | -9.36 | -1,299.39 | 1115 | 732 | 44.70 | 11.60 | -27.10 | -695.88 | 318.84 | -1,014.72 | -9.82 | 1,014.75 |

**Every configuration degraded on the holdout, and the tuned ones degraded most:**

| Config | Train | Holdout | Change |
|---|---|---|---|
| max75/th20/sl15/tg15 | -6.71 | -11.03 | -4.33 |
| max65/th15/sl20/tg15 | -6.96 | -10.53 | -3.57 |
| max75/th20/sl15/tg20 | -7.04 | -10.49 | -3.45 |
| max75/th12/sl24/tg15 | -9.36 | -9.82 | -0.46 |

The three tuned configurations gave back 3.5–4.3c on unseen data. The **untuned v3 default** gave back only 0.5c — because there was nothing fitted to give back. After the holdout, all three tuned configs are *worse* than the baseline they were tuned to beat. That is the cleanest possible demonstration that the Step 6 gains were fitted noise.

**Which survived: none.**
## 5. Honest read
**This is noise, not edge.** Six independent lines of evidence:

1. Zero of 480 parameter configurations was profitable.
2. The v3 strategy (−9.36c) performed worse than random entry (−8.28c).
3. All three tuned configs collapsed on the holdout, ending up worse than the untuned baseline.
4. The one-notch sensitivity is ~⅓ of the best config's value.
5. Losses persist at zero slippage, in the tightest spread bucket, and in every series.
6. The only positive raw edge found (+1.86c) is less than half the 4.14c cost of trading it.

### What is actually true about the v3 signal
The structural-event trigger is **not** worthless. Buying an upward 12c/60s step at 55–75c and holding to settlement produces a genuine +1.86c per-contract drift, and the classifier fires on real tennis events (verified by eye on ATP matches: clean 54→62→74→78 break-of-serve ramps). The problem is arithmetic, not signal quality:

```
  raw edge                      +1.86c
  spread + slippage             -2.52c
  fees                          -1.62c
  ------------------------------------
  net                           -2.29c
```

To make this work you would need the edge to roughly triple, or costs to fall by ~60%. ~~Maker-only entries (the spec's §4 resting limit, at 25% of taker fees) recover ~1.2c of the 1.62c fee.~~ **Corrected 2026-08-03: ~1.58c, not ~1.2c.** The 25%-of-taker maker rate applies only on series whose `fee_type` is `quadratic_with_maker_fees` — that is **ATP and WTA only**. Challenger and ITF are plain `quadratic` and pay **no maker fee at all**, and they are **90.3%** of this dataset (12,339 of 13,658 markets). So maker entries recover the *full* fee on 90.3% of markets and 75% of it on the rest: `0.903 x 1.62 + 0.097 x 1.215 = 1.58c`. **That closes about a sixth of the gap and still leaves the strategy negative** — the strategy loses 9.36c/trade, so an extra 0.38c of recovered fee changes nothing about the verdict.

### On the exits specifically
Your Step 5 framing was: *"If Strategy 1 can't beat this, its exits are destroying value."* Answer: **S1 −9.36c vs S2 −2.29c. The exits destroy 7.07c per trade.** The scale-out, the structural stop and the −24c floor together take a signal with a small positive drift and produce a raw edge of −1.31c before costs, plus an extra 2.5c of round-trip friction that holding to settlement never pays.

This also settles the six-trade observation from 27 Jul that stops were 'selling local lows'. Across 1,501 trades the stops are not the problem in the way that reading suggested — but the exit machinery as a whole is worse than having no exits at all.

### What this does not say
- It does not say tennis markets are unbeatable. It says *this family of momentum-continuation rules, at these costs*, is not.
- The window is 4 weeks of summer ITF/Challenger-heavy calendar.
- Intra-candle path is invisible at 1-minute resolution; the stop-first tie rule is deliberately pessimistic and costs S1 some wins it might have had. It does not change the conclusion — S1 loses by 9c against a ~4c total cost base.
- Untested and cheap to test next: the spec's §6 serve-timing filter (enter at the start of a service game), which is a genuinely different hypothesis rather than a re-parameterisation of this one.

### Measurement window, for the live bot
Structural events were measured as **mid-price change over 1 candle (60 seconds)**, not the spec's 45s. If any of this is ever revisited, the live bot must use a 60s window to match.
