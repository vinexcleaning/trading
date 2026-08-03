# Copyability: could a follower actually have taken this trade?

The central question of the system. A wallet's printed entry price is what *it*
paid. It is not what you would have paid, arriving seconds later.

Copyability is scored 0–100 from **execution realism only**. It deliberately
does not consider whether the trade won.

---

## The hard constraint: price history bottoms out at one minute

Verified directly against the CLOB API: `/prices-history` accepts a `fidelity`
parameter, and the finest available value is **1 minute**. Requests for finer
resolution are silently coarsened.

That matters enormously, because it means the platform's own price history
**cannot answer "what was the price 15 seconds later"**. Any system that reports
a precise 15-second follower price purely from `/prices-history` is inventing it.

So prices are resolved through a tiered fallback, and every reconstructed price
carries the tier that produced it:

| Tier | Confidence | Source |
|---|---|---|
| `observed_trade` | 100 | A real trade print within tolerance of the target time |
| `interpolated_trade` | 80 | Between two real prints |
| `minute_bar` | 60 | A `/prices-history` point — the platform's floor |
| `nearest_trade` | 40 | The closest print, outside the tolerance window |
| `modeled` | 20 | Heuristic fallback |
| `unavailable` | 0 | No usable evidence |

Confidence decays further with distance in time: a full minute away costs a
fifth of the tier's value, so stale evidence cannot masquerade as fresh.

Sub-minute delays are answered from the **second-level trade tape**
(`data-api /trades`), which is genuinely second-resolution but sparse — busy
markets have hundreds of prints, thin markets have none. Where the tape is
silent, the answer degrades honestly rather than being interpolated into
existence.

### Consequences you will see in the UI

- Copyable ROI reads **`n/a`** rather than a number when evidence is too weak.
- Every copyable figure is accompanied by **coverage**: the share of trades with
  evidence good enough to measure. Coverage below 50% is highlighted.
- Trades scored from `modeled` or `nearest_trade` evidence are **capped at 55**
  copyability, so an assumption can never clear a strict alert gate.
- `MIN_COPYABLE_DATA_CONFIDENCE` (default 55) excludes weak-evidence trades from
  the headline copyable ROI entirely. Averaging assumptions in would manufacture
  an edge — or erase a real one — out of nothing.

---

## The score

Six weighted execution factors:

| Factor | Weight | Meaning |
|---|---|---|
| Price persistence | 30% | How much of the wallet's price survived in the market |
| Liquidity | 25% | Was the follower's stake actually fillable |
| Spread | 15% | Cost of crossing |
| Timing pressure | 10% | Longer delays score worse; live markets worse still |
| Hold duration | 10% | Did the wallet hold long enough to be followed |
| Market stability | 10% | Was the market repricing rapidly during the delay |

```
execution_score  = Σ (factor × weight)
data_quality     = price_confidence × 0.7 + classification_confidence × 0.3
quality_multiplier = FLOOR + (1 − FLOOR) × data_quality/100
final_score      = execution_score × quality_multiplier
```

**Data quality is a multiplier, never a bonus.** An earlier version added it as a
positive factor, which meant high confidence in a measurement *raised* the score
of a plainly uncopyable trade. Confidence in a measurement should scale what was
measured, never improve it.

### Liquidity is measured near the touch

Total ladder depth is misleading. A live probe on one market showed **$14.55**
available within a cent of the best ask against **$2,178** across the whole
book — a 150× difference. Depth is therefore measured within a band of the
touch, and fills are estimated by walking the real ladder when a book snapshot
exists. A partial fill from a real book walk overrides any quoted liquidity
figure.

---

## The canonical uncopyable trade

From the bundled demo data, the "Fast mover" wallet:

- Buys at **$0.55**
- Within 10 seconds the market is at **$0.64**
- A follower at the 15-second benchmark pays ~**$0.65** after spread and slippage
- Price deterioration **$0.105** against a $0.03 alert limit

Result: raw ROI **37.6%**, copyable ROI **19.7%** — roughly half the edge gone —
and the live signal is **rejected** with `price_moved_too_far` and
`low_copyability`. The wallet is genuinely skilled. It is not followable.

Compare the "Steady grinder": raw 32.9% → copyable 19.2%, price barely moving
after entry, and its signals qualify.

---

## Follower delays

Every trade is scored at every configured delay: 0, 2, 5, 10, 15, 30, 60, 120,
300 seconds. The wallet page plots the resulting decay curve.

**0 seconds is retained only as a theoretical reference.** It is labelled as
unachievable everywhere it appears, and startup validation refuses a benchmark
delay of 0 outright — no follower detects, decides and executes instantly.

---

## What is not modelled

- **Market impact of the follower's own order** beyond walking the visible
  ladder. Hidden liquidity and queue position are not observable.
- **Latency variance.** A single configured delay stands in for a distribution.
- **Partial-fill timing.** A fill is modelled as instantaneous at the delay.
- **Off-platform hedges**, which are invisible by construction.
