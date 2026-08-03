# HANDOFF — fee consolidation and stale-claim sweep

**Session:** 2026-08-03, desktop `C:\Users\vinig`.
**Scope:** repo admin across five projects. Three tasks, three commits, all pushed.

| Commit | What |
|---|---|
| `214ad96` | Consolidate the Kalshi fee formula to one module; fix the live-money path |
| `a92ef01` | Mark four retracted results inline in `GO_NO_GO.md` and `shortlist.md` |
| `aeb26b9` | Sweep: mark four more retracted claims still stated as fact |
| *(pending)* | Maker rate resolved from Kalshi's schedule; supersedes the flat-0.25¢ arm |

---

## 1. The fee formula — the count was 15, not 9

The brief said nine implementations. **There are fifteen.** The inventory
undercounted by six, all in `kalshi-inplay-bot/backtest/`.

| # | Location | Arithmetic | Dust-safe? |
|---|---|---|---|
| 1 | `common/kalshi_fees.py` | Decimal | ✔ |
| 2 | `common/costbar.py` | Decimal | ✔ |
| 3 | `set1_overshoot/src/fees.py` | Decimal — **byte-identical** to #1 | ✔ |
| 4 | `crypto/src/fees.py` | Decimal | ✔ |
| 5 | `kalshi-market-scan/src/kalshi_research/fees.py` | Decimal | ✔ |
| 6 | `kalshi-inplay-bot/backtest/engine.py` | float + `round(...,9)` guard | ✔ |
| 7 | **`kalshi-inplay-bot/tennis_engine.py`** | float | ✘ **LIVE MONEY** |
| 8 | **`kalshi-inplay-bot/paper_bot.py`** | float | ✘ |
| 9 | `kalshi-inplay-bot/backtest/high_entry.py` | float | ✘ |
| 10 | `kalshi-inplay-bot/backtest/longshot.py` | float | ✘ |
| 11 | `kalshi-inplay-bot/backtest/high_sweep.py` | float | ✘ |
| 12 | `kalshi-inplay-bot/backtest/venue_compare.py` | float | ✘ |
| 13 | `kalshi-tennis/src/stage5_selective.py` | float (`np.ceil`) | ✘ |
| 14 | `kalshi-tennis/src/pinnacle_vs_kalshi.py` | float (`np.ceil`) | ✘ |
| 15 | `kalshi-tennis/src/diag_stage5.py` | float (`np.ceil`) | ✘ |

So **six guard the dust, nine do not** — the brief's "only two guard it" was
also low. `crypto/src/path_streak.py` looked like a sixteenth but already
imported from #4.

### The bug is real and I measured it rather than asserting it

Each unguarded copy was replayed against exact Decimal over the integer-cent ×
order-size grid: **115 disagreements in 1,881 cells (6.1%)**, every one an
**overcharge of exactly 1¢**, never an undercharge.

```
0.07 * 100 * 0.5 * 0.5 * 100  ==  175.00000000000003   ->  ceil -> 176c
```

### Now: one module

`common/kalshi_fees.py`, exact Decimal, **47 tests** in `common/tests/`. Pins
the three reference points (1.75¢ at 50¢, 0.63¢ at 90¢, 0.63¢ at 10¢), the
float-dust regression, a whole-grid disagreement check, and the per-series
maker schedule. All 14 other sites now delegate to it.

Two things worth knowing about the module:

- It **self-verifies at import** and raises if a reference point moves. The
  live bot therefore refuses to load rather than trade on unverified fee
  arithmetic. This is deliberate.
- The vectorised helpers are **dollar-native on purpose**. Converting a dollar
  price back to cents in float is lossy for 8 prices (7, 14, 28, 29, 55–58¢ —
  `0.07*100 == 7.000000000000001`) and changes the billed fee on 8 cells. The
  helpers coerce with `Decimal(str(x))` and never do that multiplication.

### The live bot — fee call only, and verified

Diff is in the task report: two import lines, and the body of `fee()` replaced
by one call. `math` stays (still used by `target_for_profit`).

- **49,500 price/size cells compared.** 189 changed. **All 189 strictly
  cheaper by exactly 1¢. Zero more expensive.**
- **760 `evaluate()` snapshots.** Entry, size, target and exit **identical in
  every one**. A sub-cent fee change does not move any threshold.

⚠ **One caveat on the sizes that were being overcharged.** They cluster near
the 50¢ peak of the fee curve. The three legs of the 28 Jul martingale
(12@49¢, 20@31¢, 32@19¢) do **not** hit the dust bug. The bug was live and is
worth fixing, but it is **not** what made that day expensive — that was the
martingale, already fixed on 08-03.

---

## 2. `fee_type` per series — verified against the live API

Full pagination of `/trade-api/v2/series`, 2026-08-03:

| | Count |
|---|---|
| **Total series** | **12,396** (was 12,368 on 08-01) |
| `quadratic` (taker only) | 12,266 — of which 14 have `fee_multiplier` 0 |
| `quadratic_with_maker_fees` | **130** |

**The 130 reproduces exactly.** The taker-only count grew 12,224 → 12,252 by
the same 28 as the total, so the brief's numbers were right and merely stale.

Independently reproduced by the sibling `signal-github` session (`e3b87d7`) to
the same three figures.

### Three hardcoded maker fees found — all were bugs

1. **`crypto/src/fees.py`** asserted *"**ZERO are crypto** ⇒ on every crypto
   series the MAKER FEE IS ZERO"* and set `KALSHI_MAKER_RATE = 0` on it.
   **False.** `KXBTCMAX150` and `KXBTCMAX125` are category Crypto and
   `quadratic_with_maker_fees`. The maker-fee 130 breaks down Sports 107,
   Economics 10, Entertainment 7, Financials 3, **Crypto 2**, Sci/Tech 1.
   *The ladder series this project actually trades are all `quadratic`, so the
   ladder results stand — the generalisation was the defect, not the numbers.*
2. **`backtest/high_sweep.py`** applied a flat `fee_mult = 0.25` to **every**
   market, including ITF and Challenger — verified taker-only and **90.4%** of
   that dataset (12,800 of 14,162). Now reads per series.
3. **`backtest/venue_compare.py`** applied `0.0175` unconditionally. Now
   **raises** rather than guess.

### The maker RATE — flagged as unresolvable, then resolved mid-session

I first recorded it as not API-verifiable: the series object carries only
`fee_type` and `fee_multiplier`, no maker rate (checked on `KXATPMATCH`,
`KXNBA`, `KXBTCMAX150`). Two incompatible readings existed in the repo:

- **(a)** 25% of taker, quadratic → `0.0175 × C × P × (1−P)`
- **(b)** a **flat 0.25¢/contract** → `0.25 × C` (`set1_overshoot/src/p5_task1b.py`)

They cross, so the choice matters in a price-dependent direction.

**The sibling `signal-github` session then retrieved Kalshi's own fee schedule
(effective 7 Jul 2026) and it settles it:**

```
taker  roundup(M × 0.07   × C × P × (1−P))    M defaults to 1
maker  roundup(M × 0.0175 × C × P × (1−P))    M defaults to 0
```

**(a) is correct; (b) is superseded.** `common/kalshi_fees.py` now carries
`MAKER_RATE_IS_VERIFIED = True` with the source, and `p5_task1b.py` is marked.

> **S008 survives either way** — all 15 maker configurations were net-negative
> under both arms, and the arm that turned out to be correct is the harsher one
> in the middle of the curve. Only the constant was wrong, never the verdict.

⚠ **The finding with the most forward consequence, from the sibling session:**
**107 of the 130 maker-fee series are Sports, and `KXATPMATCH` / `KXWTAMATCH`
are among them.** Kalshi charges makers precisely on the tennis series this
repo trades. Whether those series also hold most of the liquidity is
**explicitly unmeasured**.

---

## 3. Retracted results still stated as fact

### `kalshi-market-scan` — the four from the brief

Marked inline where each claim appears, plus a summary table at the top of each
file. Nothing deleted — deleting is how a retracted number gets re-derived.

| # | Claim | Correction |
|---|---|---|
| 1 | depth collapses **40×** toward expiry; edge and liquidity anti-correlated | One market, three minutes. On 25 markets/7 h: **2.7×**, never thin (**307** contracts inside the final minute, not 4), spread **tightens 10×**, so total cost **falls** 4.46¢→3.50¢. Argument **withdrawn entirely** |
| 2 | **8,090** weather test markets | A ladder is one reading. Effective n **≈800 settlement hours**; CIs were **~3× too tight**. **Model survives** re-scoring comfortably |
| 3 | **seven** daily families clear the capacity bar 7–49× | Depth right, inference wrong. All seven have **66** settlements against the **481** needed. Cross-tab kills **10 of 11**; `KXTEMPDCH` alone clears, by 512 vs 481 |
| 4 | Kalshi pre-match calibrated **bucket by bucket** | Marked **OVERSTATED**, not retracted. n=19–52/bucket; "every binomial p ≥ 0.499" is a **failure to reject**. Re-run: CIs **±11–29pp**, **0 of 7** Polymarket values excluded — they sit *inside* the intervals |

**Every verdict was NO-GO and still is.** What changed is the reasoning, and in
two cases its direction.

### Sweep — four more, outside the brief

| File | Claim | Why it matters |
|---|---|---|
| `set1_overshoot/reports/depth_analysis.md` | "median 106 contracts at the touch" (S013), ATP 30 lots/3¢ (S012) | 65-minute window **at market open**, so every median is at its daily minimum. Full day: **564**; ATP **1.0¢/312 lots**. *Conclusion strengthens* — "the touch is not thin" holds a fortiori |
| `set1_overshoot/PREREGISTRATION_PARTB.md` | same S012 figures | **Load-bearing** — the stated justification for **lifting the Phase 3 anti-slicing gate**. A retracted fact warranting a methodological decision. Outcome unaffected (S005: 0 of 25 buckets clear), but the reasoning must not be reused |
| `wallet-copy-study/COPY_TRADING_VERDICT.md` | "72% of the edge lives in exits" (W006), **3 unmarked places** | File has an AMENDED block but still asserts it in the headline, in *"the most stable finding … holds at every split point"*, and in future work as *"where the money is"*. **The gap IS stable — because a fee is stable.** Reproducibility is not evidence a number measures what you named it |
| `crypto/PROGRESS.md` | "Polymarket taker identical to Kalshi" (C015), as a ticked item | Documentation matched **0.0%** of 4,310 on-chain fills. True: `0.10·min(p,1−p)`, **2.86× Kalshi at 50¢** |

Plus, fixed under Task 1, same class: **`venue_compare.py` priced Polymarket at
a documented `0.05·p·(1−p)`.** Its entire conclusion — *"would these strategies
do better on Polymarket?"* — **reversed sign** once corrected. Marked RETRACTED
inline, not deleted.

### ⚠ Cross-check result worth acting on

**`kalshi-market-scan` has no rows in `LEDGER.md` at all.** The ledger covers
`set1_overshoot`, `crypto`, `wallet-copy-study`, `kalshi-tennis` and the chat
archive. The four claims in the brief were therefore **invisible to any
ledger-based check** — they were found only because the brief named them.
`kalshi-market-scan` has its own `docs/HYPOTHESIS_LEDGER.md`, unlinked from the
top-level one.

---

## What I did NOT do

- **Did not touch `signal-github/`.** It had uncommitted work from a concurrent
  session throughout. Staged explicit paths every time; never `git add -A`.
- **Did not re-run any backtest.** The fee correction is ≤1¢ and strictly in
  the trader's favour, so every stored result is now marginally conservative,
  not wrong. Re-running `stage5_selective`, `high_sweep` and the v3 sweep would
  shift numbers by <1¢/trade — worth doing, not urgent.
- **Did not measure** whether the maker-fee tennis series hold most of the
  liquidity. That is the open question the sibling session flagged.

## Next actions, in order

1. **Decide whether the live bot trades at all.** Unchanged by this work and
   still the biggest open item: its own 14,162-market backtest says −9¢/trade.
2. **Re-run `high_sweep.py`.** Its maker arm previously charged a fee on 90.4%
   of markets that do not pay one, so every maker result it produced was
   pessimistic. This is the one stored result the fee fixes actually move.
3. **Ledger `kalshi-market-scan`,** or link its `HYPOTHESIS_LEDGER.md` from
   `LEDGER.md`. Right now a whole project's claims escape the cross-check.
4. **Measure liquidity on the 130 maker-fee series**, tennis first.
