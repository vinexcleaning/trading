# SELECTION_AUDIT.md

Audit of every selection, filter, sort, dedupe, join and sample that reads a
field only knowable at or after settlement. Written 2026-08-01 after the
volume-dedupe bug voided Phase 2.

**Scope audited on this machine:** `kalshi\set1_overshoot` (this project),
`kalshi\src` (Stage 0–5 player model), `crypto\src`, `Desktop\kalshi_backup\src`
(identical copy of the second). 315 occurrences of post-settlement fields found
across 4 codebases and classified.

**Not on this machine:** the v3 structural-event backtest and the
copy-trading / wallet work. See [BLOCKED_ON_DESKTOP.md](BLOCKED_ON_DESKTOP.md).

---

## 1. Verdict table — every finding in the project

| # | Finding | Verdict | Basis |
|---|---|---|---|
| **Tennis — set1_overshoot (Phases 2–5)** ||||
| 1 | Set-1 undershoot, −2.53 pp, p=0.0007 | **VOID** | dedupe read `volume_fp`; the two orientations disagree by 25.5 pp |
| 2 | "No overshoot" verdict; true sign of the effect | **VOID — unknown** | direction was set by the artifact |
| 3 | Monotone strengthening with detector precision | **VOID — and backwards** | deeper rules push the kept/favourite split further from 50/50, amplifying the bias |
| 4 | Phase 3 segments (strength bands, drop size, tier, exits, 3d, 3g) | **VOID** | same event set |
| 5 | Phase 4 holdout, walk-forward, deflated Sharpe | **VOID** | same event set |
| 6 | 90¢+ favourites, +7.93 pp | **VOID** (was already dead on holdout) | same event set |
| 7 | Fade side loses in all 6 configurations | **NEEDS RE-RUN** | conclusion likely survives (cost arithmetic dominates) but the edge term is void |
| 8 | Detector direction accuracy 0.825 | **CLEAN** | validated against 2,787 external scorelines, not against outcomes |
| 9 | `t0` tuning: +5 min median, MAD 6 | **CLEAN** | validated against Sackmann playing minutes |
| 10 | Mirror equivalence, median 0.00¢ | **CLEAN** | price identity, no selection |
| 11 | Fee arithmetic (1.75/0.63/0.63¢) | **CLEAN** | exact Decimal, unit-tested |
| 12 | Synthetic controls: null +0.06 pp, planted 5 pp → +4.54 pp | **CLEAN** | generated data, no selection |
| 13 | Leak canary +6.75 pp vs honest rules | **CLEAN** | diagnostic behaves correctly |
| 14 | Cost anatomy: spread **1.170**¢ / slip 1.000¢ / fee **1.441**¢ = **3.61 pp** | **CORRECTED 2026-08-01** | the 1.197/3.70 figures were a contaminated-universe half-spread and a favourite-side breakeven; recomputed on clean data. No calculation ever used them as inputs, so no verdict changed |
| 15 | Task 1a: Phase 2 fade was already hold-to-settlement | **CLEAN** | code fact |
| 16 | Retirement add-back costs −0.004¢ | **NEEDS RE-RUN** | small and unlikely to move, but computed on the void event set |
| **Tennis — Stage 0–5 player model (`kalshi\src`)** ||||
| 17 | Model loses to bookmakers, Brier 0.2249 vs 0.2057, n=2,645 | **CLEAN** | p1 assigned alphabetically; temporal split; no Kalshi data |
| 18 | Kalshi beats Betfair by 0.022 Brier | **VOID** (already retracted) | anchor at/after settlement |
| 19 | Stage 4 "market beats model once wide quotes excluded" | **VOID** | feature leak **and** a new selection leak — the spread filter read the leaking anchor |
| 20 | Stage 5: mid-fill +14–25% ROI vs ask-fill −24–31% | **NEEDS RE-RUN**; the *lesson* stands | prices from the leaking anchor, but the mid-vs-ask gap is a cost identity |
| 21 | Kalshi vs Betfair r=0.9878, MAD 1.95¢ (h6 anchor) | **CLEAN** | h6 anchor; side chosen by API listing order, tested at z=+1.44 |
| 22 | Stage 2 shrinkage constants, Stage 3 traits | **CLEAN** | Sackmann only, no Kalshi selection |
| 23 | ITF ≈ 76% of Kalshi's tennis book | **CLEAN** | a count |
| **Crypto (`crypto\src`, laptop copy)** ||||
| 24 | Panel build filters (null / one-sided / wide spread / τ≤0 / after close) | **CLEAN** | all evaluated per market-minute from candles, as-of that minute |
| 25 | Mid calibration (`result` as label) | **CLEAN** | label use, not selection |
| 26 | Ladder arbitrage replay | **CLEAN** | replays recorded snapshots in time order |
| 27 | Recorders writing `volume_fp` / `open_interest_fp` / `last_price` | **CLEAN** | recorded with a timestamp, so as-of; unsafe only if later read off a settled record |
| 28 | Everything requiring desktop recordings (Tier B, microstructure) | **BLOCKED** | not on this machine |
| **Not auditable here** ||||
| 29 | v3 structural-event backtest (14,162-market pull) | **UNKNOWN — presume VOID** | it deduped mirrored markets; field unknown |
| 30 | Copy-trading / wallet ranking, favourite–longshot conclusion | **UNKNOWN** | ranking field and its timing unknown |

---

## 2. SELECTION usages, classified

Full occurrence list: `reports/audit_occurrences.txt` (315 lines, file:line).
Only usages that decide *which rows exist* are reproduced here.

### set1_overshoot

| file:line | field | class | verdict |
|---|---|---|---|
| `p0_universe.py` (was) | `volume_fp` | **SELECTION** | **UNSAFE — the bug.** Fixed to lexicographic ticker |
| `p0_universe.py:62` | `status` | SELECTION | safe — "is it decided", not "which outcome" |
| `p0_universe.py:64` | `result` | SELECTION | unsafe in principle, unavoidable, measured (§3) |
| `p1_state.py:300` | derived duration | **SELECTION** | borderline — see §3 |
| `p1_state.py` (play window) | derived activity | **SELECTION** | 14.4% dropped; untestable by residual, bounded in §3 |
| `p2_calib.py:238` | `dur_min` | SELECTION | safe — at entry time you know the match is live |
| `p0_scores.py` | outcome agreement | SELECTION | validation only, not the main analysis |
| `p4_validate.py:67` | `close_time` | ordering | safe as a coordinate; noted caveat in §3 |

### Stage 0–5 player model

| file:line | field | class | verdict |
|---|---|---|---|
| `stage4_model.py:43-47` | player order | SELECTION | **CLEAN** — `swap = w > l`, alphabetical, target ~50/50 |
| `stage4_model.py:36,150` | date | split | **CLEAN** — temporal |
| `tennis_data.py:196-198` | API listing order | SELECTION | **CLEAN** — tested, z = +1.44 |
| `stage0_audit.py:88-89` | `volume_fp` from a **candle** | FEATURE | **CLEAN** — as-of the anchor timestamp. The correct pattern |
| `stage4_kalshi_liquid.py:24` | spread from the leaking anchor | **SELECTION** | **UNSAFE** — see §3 |
| `stage5_selective.py:131` | same spread | **SELECTION** | **UNSAFE**, same source |
| `stage5_selective.py:255` | `sort_values("mean_pnl")` | SELECTION | not post-settlement, but selects the best variant on the full sample with no holdout — an overfitting hazard, separate class |
| `stage5_selective.py:99` | `drop_duplicates(keep="first")` | SELECTION | order-dependent and non-deterministic; not outcome-correlated, but should be given an explicit sort |

### Crypto

No post-settlement field appears in any filter, sort or dedupe. All `volume_fp`
/ `open_interest_fp` / `last_price` reads are either per-minute candle features
or live recordings, both of which are as-of a timestamp. `result` appears once,
as a label.

---

## 3. A3 — empirical tests

Every selection point, tested the way the dedupe bug was caught. Full output:
`reports/audit_a3.txt`, `reports/audit_a4.txt`.

### Side-choice rules. Null: P(kept side wins) = 0.5000, n = 19,782

| rule | observed | z | verdict |
|---|---|---|---|
| higher `last_price_dollars` | **0.9989** | **+140.3** | catastrophic — it *is* the answer |
| higher `open_interest_fp` | **0.5558** | **+15.7** | unsafe |
| higher `volume_fp` — **the Phase 0 bug** | **0.5356** | **+10.0** | unsafe |
| higher `liquidity_dollars` | 0.5031 | +0.88 | clean *on this data only* — the field is 0 on most settled tennis markets, so this is innocence by emptiness, not a property to rely on |
| **first ticker alphabetically — the fix** | **0.4969** | **−0.88** | clean |
| API listing order (old project) | 0.5050 | +1.44 | clean |

### Filters. Null: the filter may change who is sampled, not how well they are priced

| filter | kept residual | dropped residual | z | verdict |
|---|---|---|---|---|
| `plausible` duration 25–330 min | +0.0029 (n=16,258) | +0.0294 (n=682) | **−2.59** | **borderline.** Below the |z|=4 threshold but not nothing. 4% of rows, and the dropped ones are better-calibrated. Measured on the *contaminated* universe, so it must be re-tested on the clean one |
| leaking-anchor spread ≤ 10¢ / 5¢ / 2¢ | — | — | +0.11 / 0.00 / +0.14 | **inconclusive, and moot.** Only 502 joined rows survive, far too few to clear a filter this important; and the file it reads is void for the separate feature leak regardless |

### Filters that cannot be tested this way

The play-window filter drops 14.4% of markets (2,841 of 19,781: 2,825 with no
detectable activity, 16 with no usable quote at all). Those rows have no
pre-match price, so their calibration residual is undefined and the residual
test cannot run. **This is not a leak**: a market that never traded and never
moved could not have been traded by any strategy either, so excluding it defines
the tradeable universe rather than biasing within it. Stated rather than tested,
which is weaker, and flagged as such.

---

## 4. Permanent guards

`src/leakguard.py`, importable, two assertions:

```python
assert_side_choice_neutral(kept_won, name)          # null exactly 0.50
assert_selection_neutral(mask, outcome, implied)    # residual must not shift
```

Both raise `SelectionLeak` above |z| = 4.

**Enforced, not merely present:**

- `p0_universe.py` asserts the canary at build time and refuses to write a
  universe that fails. Verified: current build reads 0.4969, z = −0.88.
- `tests/test_leakguard.py` — 9 tests, all passing. Includes:
  - a live regression on the real universe;
  - a *guard-rot* test that the known-bad rules (`volume`, `open_interest`)
    still trip the assertion on real data, so the guard cannot silently stop
    working;
  - a source-level test that the canary is asserted and that the dedupe sort
    does not reference any post-settlement field.

**Why the existing canary missed this.** The leak canary watches for look-ahead
*within* a match — a price read from after the decision. This leak was
*between* two markets: every price was correctly timestamped, and the wrong rows
were chosen. Feature-level tests are structurally blind to it. That is why the
new guard tests row membership instead.

---

## 5. What I got wrong, stated plainly

1. **The bug was mine and it was in the first script I wrote.** "Keep the
   higher-volume side" looked like a tie-break. It was a coin weighted by the
   answer.
2. **I argued the effect was real because it strengthened with precision.**
   The opposite was true: precision and bias were the same knob. This is the
   single worst inference in the project, because it converted evidence of
   contamination into evidence of signal.
3. **I ran a mirror check in Phase 0 and it passed.** It compared *prices*
   between sibling markets, which were fine. It never compared *outcomes* by
   orientation. A correct check existed and was pointed at the wrong quantity.
4. **`liquidity_dollars` passes only because it is empty.** I nearly recorded it
   as a safe alternative rule; it is not, it is untested.

Directional prior, updated: **28 corrections, every one shrank the edge.**
