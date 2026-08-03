# `high_sweep.py` re-run after the maker-fee correction

**2026-08-03.** Re-run requested after `high_sweep.py` was found charging a
maker fee on every market. It should charge one only on ATP and WTA
(`fee_type = quadratic_with_maker_fees`); Challenger and ITF are plain
`quadratic` and pay **no maker fee at all**.

**That is 90.3% of this dataset:**

| Tour | Markets | Share | Maker multiplier |
|---|---|---|---|
| ITF-M | 5,359 | 39.2% | **0** |
| ITF-W | 4,902 | 35.9% | **0** |
| Challenger | 2,078 | 15.2% | **0** |
| ATP | 662 | 4.8% | 0.25 |
| WTA | 657 | 4.8% | 0.25 |

So every maker number this file produced was **too pessimistic**.

## Result — cents per contract

Both arms run on the same 13,658 cached market views.

| Band | Mode | Trades | Old | Corrected | Change |
|---|---|---|---|---|---|
| 85–89 | taker | 6,289 | −1.8230 | −1.8230 | 0.0000 |
| 85–89 | **maker** | 6,281 | +0.3849 | **+0.5785** | **+0.1936** |
| 85–89 | maker-strict | 4,262 | −2.5120 | −2.3198 | +0.1922 |
| 90–92 | taker | 5,579 | −2.2092 | −2.2092 | 0.0000 |
| 90–92 | **maker** | 5,573 | −0.2570 | **−0.1092** | +0.1477 |
| 90–92 | maker-strict | 3,779 | −2.5593 | −2.4151 | +0.1442 |
| 93–95 | taker | 5,676 | −1.5029 | −1.5029 | 0.0000 |
| 93–95 | **maker** | 5,667 | +0.2390 | **+0.3457** | +0.1068 |
| 93–95 | maker-strict | 3,821 | −1.5918 | −1.4867 | +0.1050 |
| 96–97 | taker | 4,759 | −1.8388 | −1.8388 | 0.0000 |
| 96–97 | **maker** | 4,746 | −0.2125 | **−0.1459** | +0.0666 |
| 96–97 | maker-strict | 3,260 | −1.3608 | −1.2970 | +0.0638 |

- **All 8 maker rows improved. None worsened.** Mean **+0.1275¢/contract**,
  largest +0.1936¢.
- **All 4 taker rows are byte-identical**, which is the control: the change
  touched the maker path only, as intended.

## What it changes: nothing that matters

**No configuration flipped sign. Two of twelve rows were positive before and
two are positive after.** The improvement is ~0.13¢ against a cost base of
roughly 4¢ — real, measurable, and an order of magnitude too small to matter.

The two positive rows are both **`maker` (optimistic fill)**, and this file's
own header names that model as *"the single easiest way to fake a profitable
backtest"*, because it assumes you always get filled at bid+1. The honest
version of the same bands is **`maker-strict`**, which requires a seller to
actually come to your price — and every strict row is still firmly negative:
**−2.32, −2.42, −1.49, −1.30 ¢/contract**.

So the corrected reading is unchanged from the original:

> Resting orders look profitable only under a fill model that gives you the
> fill for free. Require the fill to be real and the strategy is negative in
> every band. Removing a fee that was never owed does not change that — it
> moves the honest rows from about −2.5¢ to about −2.4¢.

This matches S008 in `LEDGER.md` (all 15 maker configurations net-negative on
the set-1 study) and S009 (adverse selection already exceeds maker price
improvement). The maker-fee correction does not disturb either.

## Also corrected

`BACKTEST_RESULTS.md` stated *"maker-only entries … recover ~1.2c of the 1.62c
fee"*. That assumed 25%-of-taker everywhere. Blended correctly it is
**~1.58¢** (`0.903 × 1.62 + 0.097 × 1.215`). The strategy loses 9.36¢/trade,
so the extra 0.38¢ closes about a sixth of the gap rather than a third — and
the verdict is unaffected either way.

## Reproduce

```bash
C:/Users/vinig/trading/kalshi-market-scan/.venv/Scripts/python.exe run_backtest.py prep
C:/Users/vinig/trading/kalshi-market-scan/.venv/Scripts/python.exe high_sweep.py
```
