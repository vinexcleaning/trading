# Task 1a — hold to settlement vs round trip

## The premise is false, and it changes this phase's priorities

The Phase 2 fade was **already hold-to-settlement**. From `src/p2_fade.py`:

```python
fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
net = 100.0 * dog_won - fill - fee      # one fee, no exit leg
```

`net` pays the settlement value `100 * dog_won` against a single entry fill and a
single fee. There is no target, no stop and no exit trade anywhere in it. The
−1.10¢ headline already banks the whole hold-to-settlement saving.

The round-trip figures the brief is thinking of are the **Phase 3 exit surface**,
which was a separate experiment on the *favourite* side, not the fade. There, all
25 target/stop cells lost more than hold-to-settlement, which is the same lesson
pointing the same way — but that saving is spent, not available.

### What a round trip would have cost, for completeness

| entry rule | n | hold-to-settlement net ¢ | forced round-trip net ¢ | cost of the second leg |
|---|---|---|---|---|
| deep:12 | 5,396 | -2.861 | -2.861 | +0.000 |
| deep:30@38 | 3,427 | -1.101 | -1.101 | +0.000 |
| deep:20@38 | 4,190 | -1.739 | -1.739 | +0.000 |
| deep:25 | 4,045 | -1.405 | -1.405 | +0.000 |
| cp | 3,518 | -3.434 | -3.434 | +0.000 |
| fixed | 3,341 | -1.641 | -1.641 | +0.000 |

The second leg is cheap here only because a settled position exits at 0 or 100,
where the fee formula bottoms out. An early exit at a mid price would cost the
full ~1.7¢, which is what the Phase 3 surface measured.

## Anatomy of the cost bar — where the 3.6¢ actually is

Best-targeted rule `deep:30@38`, the one carrying the −2.53 pp undershoot.

| component | ¢/contract | avoidable? |
|---|---|---|
| fair value at entry (underdog mid) | 63.567 |  |
| half-spread paid to cross | 1.197 | avoidable as a maker |
| assumed slippage | 1.000 | avoidable as a maker; an assumption, not measured |
| exchange fee (taker) | 1.439 | up to 3/4 avoidable as a maker |
| **total cost above fair value** | **3.636** | |

- observed underdog win rate: **66.09%**
- fair value implies: **63.57%**
- **gross edge: +2.53 pp**
- **net after cost: -1.101 ¢/contract**

So the fee is **40%** of the cost bar, not all of it. Spread and
slippage together are **60%**. That reorders the phase:

| lever | ceiling ¢ | note |
|---|---|---|
| 1a hold to settlement | **0.000** | already banked |
| 1b maker, fee only (÷4) | 1.079 | if Kalshi charges 1/4 taker |
| 1b maker, fee to zero | 1.439 | if tennis has no maker fee |
| 1b maker, no crossing + no slippage | 2.197 | the larger half of the prize |
| **1b maker, everything** | **3.636** | vs a 1.101¢ gap to close |
| 1c price geometry | ≤1.439 | reallocates within the fee |
| 1d spread filter | ≤1.197 | reallocates within the spread |

**1b is the whole phase.** 1c and 1d can only redistribute components 1b already
targets, and 1a is spent. The maker line also has the one failure mode that could
kill it outright — a resting order that fades a favourite fills precisely when the
favourite is ticking up, which is adverse selection by construction. That is tested
next and is the pivot of this phase.

## The distribution behind the mean, and drawdown

Hold-to-settlement has no stop, so the mean hides a binary payoff. Per contract:

- n = 3,427 positions, mean **-1.101¢**, sd 45.1¢
- wins 66.1% of the time, averaging +29.8¢
- loses 33.9% of the time, averaging -61.4¢
- worst single position **-98.1¢**, best **+74.7¢**

Worst peak-to-trough, cumulative ¢ per 1 contract per match:
- in the realised chronological order: **4,792¢**
- median over 200 shuffles: 5,029¢, 95th percentile 6,508¢

At one contract per match that is a **$48** peak-to-trough on a strategy whose mean is negative — the drawdown figure is included because it is the honest companion to any expectancy number, not because this configuration is worth trading.