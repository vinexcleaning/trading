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

## Next actions — ALL FOUR NOW DONE (2026-08-03, later session)

1. ~~Decide whether the live bot trades at all.~~ **DONE — it is OFF.**
2. ~~Re-run `high_sweep.py`.~~ **DONE — no conclusion changed.**
3. ~~Ledger `kalshi-market-scan`.~~ **DONE — 16 rows, and it immediately paid.**
4. ~~Measure liquidity on the maker-fee series.~~ **DONE — 34.4% of volume.**

---

# PART 2 — autonomous continuation (2026-08-03)

| Commit | What |
|---|---|
| `a1f5df8` | Re-run `high_sweep` after the maker-fee fix: no conclusion changes |
| `005f9a7` | Turn the live bot off: fail-closed kill switch |
| `69a52de` | Guard against a future fee reimplementation; repoint two more copies |
| `f49aa0a` | Ledger `kalshi-market-scan`: 16 rows, closing the cross-check gap |
| `4710163` | Measure whether the maker-fee tennis series hold the liquidity |

## 4. The live bot is OFF

`kalshi-inplay-bot/TRADING_DISABLED` blocks all order placement. The check sits
in `_check_writable()` **before** the `read_only` flag, so it fails closed and
cannot be bypassed by constructing the client differently. Verified: bid and
ask both blocked with `read_only=False`; guard releases when the file is
removed. **To trade again, delete that one file.**

It was **already off** before anything changed — no process, no autostart
shortcut, no scheduled task, and `bot_state.json` six days stale listing five
positions on matches that settled ~6 days earlier. No open exposure. The commit
made "off" durable rather than incidental.

## 5. `high_sweep` re-run — the fee fix changed nothing that matters

All 8 maker rows improved (mean **+0.13¢/contract**), all 4 taker rows came
back **byte-identical** as the control. **No configuration flipped sign.** The
two positive rows are both the optimistic fill model the file's own header
calls "the single easiest way to fake a profitable backtest"; the honest
`maker-strict` arm stays at **−1.30 to −2.42¢**. Fees were never the binding
constraint. Full table: `kalshi-inplay-bot/backtest/HIGH_SWEEP_RERUN.md`.

## 6. The guard that stops a 16th copy — and found a 16th and 17th

`common/tests/test_no_fee_reimplementation.py` walks every `.py` in the repo
and flags a fee fingerprint. Each hit must import the shared module or sit in
an `ALLOWED` map **with a written reason**.

> GUARDS #6 already said "one shared, tested `fees.py`". The count went from 3
> to 17 *after* that instruction. **Telling people to share a module does not
> make them share it.** A test that fails is what stops the next one.

Three sub-tests keep the allowlist honest: dead entries fail (this fired on
first run and caught a stale entry of mine), empty reasons fail, and the
detector is proven to bite on the canonical bug and *not* on an unrelated
`0.07`. A fifth test imports each shim from a neutral cwd.

It immediately found two copies the manual sweep missed —
`probe_01_depth.py:238` and `probe_02_fees.py:175`, both computing the Kalshi
side of the Polymarket cost ratio. Neither used `ceil`, so neither carried the
dust bug. Repointed; outputs byte-identical at all five price points.

**True count: 17, not 15.**

## 7. `kalshi-market-scan` is ledgered — and it paid immediately

16 rows, K001–K016, in `LEDGER.md` Section 6. Tally 216 → 233, RETRACTED
41 → 45.

### ⚠ The finding: K015 *is* W011

**The same claim had two rows in two projects with two different statuses.**

| | K015 (`kalshi-market-scan`) | W011 (`wallet-copy-study`) |
|---|---|---|
| Claim | "0.60–0.95 … **+7.05pp ± 0.22**" | "naive favourite-band … **+7.05pp**" |
| n | **98,766** | **98,766** |
| Status before 08-03 | **UNVERIFIED** | **RETRACTED** — recomputed **+2.09pp [−1.37,+5.35] gross, −0.29pp net** |

`wallet-copy-study` had **already killed it**. `kalshi-market-scan` went on
calling it the finding that reframes its whole copy-trading block, and
`kalshi-inplay-bot/audit/LEDGER.md` C042/R2 called it the corpus's
least-supported claim — none of them aware the answer sat one section away.

**A claim that travels between projects gets a fresh row and a fresh status
each time, and the weakest status is the one a reader happens to find.**
Cross-reference by number and n, not by project name. K015 is now RETRACTED.

## 8. Do the maker-fee tennis series hold the liquidity? No — but 6×

Answers the question `signal-github` `e3b87d7` left explicitly open.

| | Series | Markets | % count | Volume | % volume |
|---|---|---|---|---|---|
| **Charges makers** | 2 | 3,864 | **5.8%** | 3.31bn | **34.4%** |
| Taker-only | 40 | 62,830 | 94.2% | 6.32bn | 65.6% |

**5.9× more traded per market.** `KXATPMATCH` alone is **21.9%** of tennis
volume on 2.8% of markets. S010's "91% of the book" is a *count* and is right
(measured 94.2%); by *volume* the taker-only series are 65.6%.

Two thirds of tennis volume sits where makers pay nothing — but the single
deepest series charges, so choosing on fee alone pushes you toward the thinner
book. It does **not** revive the maker case (S008, S009, and the `high_sweep`
re-run all stand).

**Two method traps hit and fixed, both already recorded in this repo:**

- **Volume is `volume_fp`, not `volume`.** The old name returns `None` and sums
  silently to **zero** — the first run reported a clean, completely fake result
  across all 42 series. That is C024's renamed-field trap. The script now
  raises if the field is absent and aborts if the total is zero.
- **Series selection is by prefix, not substring.** `ATP|WTA|ITF` as a
  substring pulls in twelve non-tennis series — `KXNEWTAYLOR` ("Taylor Swift
  album"), `WTAX` ("Wealth tax"), `KXLOWTAUS` ("Lowest temperature in Austin").
  **T017 is a retraction caused by exactly this.** Headline robust either way.

## What remains

1. **Rotate `kalshi_private_key.pem`** — still in the bot folder *and* a
   OneDrive-synced Desktop folder. User's call, unaffected by trading being off.
2. **`high_sweep.py` maker rows are still optimistic-fill.** The corrected
   numbers are honest about fees but not about fills. Nothing depends on them
   now that the bot is off.
3. **Sweep the other three projects for duplicate claims** the way K015/W011
   was found — by number and n across sections, not by project.
