# What the real scans found

Two scans against live Polymarket data, 29–30 July 2026. This is the record of
what was actually measured, so the conclusions survive a new session.

## Summary

**No wallet has a demonstrable copyable tennis edge.**

- Scan 1 — 40 arbitrary tennis participants. Population prior: **−5.6% copyable
  ROI**. Following the average visible tennis wallet loses money after a 15s delay.
- Scan 2 — deliberate search: 1,558 wallets ranked by tennis notional across 160
  markets, plus profit/volume leaderboards → 152 candidates → top 6
  deep-backfilled to 100% price coverage (1.2M price observations).

For all six finalists, removing the top 5% of trades collapses copyable ROI to
about zero or negative. The confidence interval spans zero for five of six.

| Wallet | Trades | Copyable ROI | Median trade | Excl. top 5% | Outlier dep. |
|---|---|---|---|---|---|
| `0xf8831548531d` | 27 | 24.9% | +28.8% | +18.4% | 26% |
| `0x4be1fa92e6ce` | 61 | 24.3% | −100% | −1.1% | 100% |
| `0x076daa87c4fe` | 481 | 11.3% | +15.2% | −7.1% | 100% |
| `0xf5fabdcdc6eb` | 24 | 10.5% | +29.6% | +2.9% | 72% |
| `0xf148f9acb3d2` | 58 | 5.4% | −100% | −4.5% | 100% |
| `0x99f0d31fdced` | 197 | 3.8% | −100% | −16.0% | 100% |

The closest thing to a real result is `0xf8831548531d`: robust to outlier
removal with a positive median. But n=27, its CI runs from −8.7% upward, and it
trades **$158,000 median positions** — uncopyable at any realistic size, and at
that size it is setting the price rather than taking it.

## Two traps found in live data

**1. Favourite-longshot (`tail_risk_asymmetry`).** A wallet buying at an average
of **$0.945** with a **98.9% win rate**: average win +$7.21, average loss
−$100.56, so one loss erased 13.9 wins. Its record contained **two losses in 181
trades** — far too few to estimate the loss rate that determines whether the
strategy is profitable at all. It looked excellent on win rate, profit factor
and drawdown simultaneously.

**2. Convexity bias in mean-of-ROI.** On a binary market a loss floors at −100%
regardless of the price paid, while a win at a cheap fill is unbounded. Random
variation in fill prices therefore biases the *average* ROI upward. A 481-trade
wallet reported 11.3% copyable ROI that fell to **0.54% excluding its ten best
trades**.

Both are now instrumented: `tail_risk_asymmetry` flag + penalty, and
`copyable_roi_median` / `copyable_roi_trimmed` / `copyable_outlier_dependence`.

## Defects the real data exposed

All three flattered results — the dangerous direction.

1. **Raw and copyable ROI were not comparable.** Raw was capital-weighted,
   copyable equal-weighted (a follower stakes flat per signal). Subtracting them
   conflated delay cost with the wallet's position sizing and could show *being
   late as profitable*. Fixed with `roi_equal_weighted`.
2. **History silently truncated at 5,000 records.** `/activity` rejects offsets
   past 5000; one wallet had 91,561 records. Fixed by re-anchoring on timestamps.
3. **Cluster ids never written back to wallets**, leaving the consensus
   independence rule inert — related wallets would have counted as separate
   confirmations.

## Why the next step is forward paper trading

Every number above is retrospective on wallets selected *because* they looked
good. That selection alone inflates the results, and no amount of further
backward analysis removes it. Paper trading fixes the rules now and evaluates
trades that have not happened yet, which is the only unbiased test available
without risking money.

## Reproducing

```bash
DATABASE_URL="sqlite:///./data/best.db" python scripts/find_best_tennis_wallets.py
DATABASE_URL="sqlite:///./data/best.db" python scripts/deep_backfill.py 0xADDR ...
```

Databases: `data/real.db` (scan 1), `data/best.db` (scan 2), `data/demo.db`
(synthetic demo).
