# STATUS.md — shared session status board

**This file did not exist before 2026-08-01 02:10. Nothing was overwritten.**
Append your session as a new `##` section; do not edit another session's block.

---

## tennis / set1_overshoot — 2026-08-01 02:10 (laptop, `gianf`)

**State: Phases 2–4 RETRACTED. Clean re-run blocked on a candle refetch, ~34 min.**

Full detail in `HANDOFF.md`, `SELECTION_AUDIT.md`, `PREREGISTRATION_PARTB.md`.

### Headline

The reported −2.53 pp set-1 "undershoot" was a selection artifact of my own
Phase 0 dedupe, which kept the **higher-volume** side of each mirrored market.
Volume is read after settlement and the winning side attracts more trading, so
the rule picked the winner **53.6%** of the time (z = +10.0, n = 19,759 pairs).
Orientation split: **+14.05 pp** where the favourite is the YES side, **−11.43 pp**
where it is the NO side — a 25.5 pp gap between halves that must agree.

**Void:** Phase 2 calibration, Phase 3 segments, Phase 4 holdout/walk-forward,
the "no overshoot" verdict, and the 90¢ cell.
**Standing:** detector accuracy 0.825 (n=2,787), t0 +5 min/MAD 6 (n=2,150),
mirror price identity (median 0.00¢), fee arithmetic, synthetic controls, and
the cost anatomy (3.636 ¢ = 1.197 spread + 1.000 slip + 1.439 fee).

### Cross-project warning — applies to every codebase here

Any selection, sort, dedupe, filter or join on a field knowable only at/after
settlement is a leak. Measured on 19,782 Kalshi tennis pairs:

| field used to pick a side | P(kept wins) | z |
|---|---|---|
| `last_price_dollars` | **0.9995** | **+140.4** |
| `open_interest_fp` | 0.5559 | +15.7 |
| `volume_fp` | 0.5357 | +10.0 |
| `volume_24h_fp` | — | UNTESTABLE (decides 3.9%) |
| `liquidity_dollars` | — | UNTESTABLE (decides 0.0%) |
| ticker alphabetical | 0.4969 | −0.88 (clean) |

`src/leakguard.py` is importable and generic. `docs/POST_SETTLEMENT_FIELDS.md`
lists the unsafe field set and the near-misses. 13 tests pass.

### Audited and CLEAN

- **Stage 0–5 player model** (`C:\Users\gianf\kalshi\src`): p1 assigned
  alphabetically, temporal split, side choice z = +1.44. Its headline (model
  loses to bookmakers, Brier 0.2249 vs 0.2057, n=2,645) stands.
- **crypto laptop copy** (`C:\Users\gianf\crypto\src`): no post-settlement field
  in any filter/sort/dedupe. All volume/OI/last reads are as-of a candle
  timestamp or a live recording.

### New leak found in the old tennis project

`stage4_kalshi_liquid.py` and `stage5_selective.py` filter on a spread taken
from `kalshi_prematch_prices.parquet.INVALID_LOOKAHEAD_LEAK` — a selection leak
on top of the known feature leak. Empirical test underpowered (n=502) and moot.

### Blocked on the desktop session (`C:\Users\vinig\kalshi`)

1. **v3 structural-event backtest** — deduped mirrored Kalshi markets, field
   unknown. **Presume void.** One grep decides it.
2. **Copy-trading / wallet ranking** — check the ranking field's timing and
   wallet survivorship; the favourite–longshot conclusion depends on it.
3. **Recorder `None`-price check** — legacy Kalshi price fields now return
   `None`; if the recorders read them the books are empty.

See `BLOCKED_ON_DESKTOP.md` for greps and run order.

### Running on this machine

| PID | What | Note |
|---|---|---|
| 12528 | my candle refetch → `data/candles_ohlc/` | **restart loses all progress** (script clears the output dir on start) |
| 22612 | `crypto/src/recorder.py` — **not mine**, untouched | sleep = permanent gap; Kalshi has no historical book endpoint |

---

## tennis / set1_overshoot — UPDATE 2026-08-01 07:00 (Part B complete)

**Clean re-run done. All gates passed. The undershoot is REAL but uncollectable.**

| item | value |
|---|---|
| θ, best-targeted `deep:30@38` | **−2.42 pp** [−3.93, −0.89], p=0.0009, n=3,436 matches, 25 May–1 Aug 2026 |
| Holdout (untouched, newest 40%) | −2.27 pp [−4.66, +0.17], n=1,374 — **replicates** |
| Cost bar to clear | **3.61 pp** (corrected 2026-08-01 from 3.70 — the 3.70 was the favourite-side breakeven, not the fade's). Fade loses in **0 of 6** configs (best −1.195¢) |
| Maker execution | **0 of 15 cells positive**, best −0.205¢/opportunity |
| Adverse selection | **−2.91¢** vs price improvement +0.69¢ — the binding constraint |
| Maker fill rate | 55–88% — **not** the constraint |
| Maker fee, tennis | **0¢ on Challenger/ITF (91% of book)**, verified via `fee_type`; ATP/WTA differ |
| Deflated Sharpe | 0.0000 |

**Partial un-retraction:** I voided Phases 2–4 wholesale; that was too broad. The
pooled headline moved only −2.53 → −2.42. The dedupe bug destroyed
orientation-**split** analysis (because `kept_is_fav` was outcome-correlated), not
the pooled estimate. My pre-registered prediction of +1.31 pp **failed** — outside
its [−1, +3] interval.

**Cross-session note for crypto:** your market-making result reproduces
qualitatively here. Tennis adverse selection is **1.45×** price improvement vs your
**4×** spread captured — milder counterparty, same verdict. But Kalshi maker fees
**do** exist on some series (`quadratic_with_maker_fees` on KXATPMATCH/KXWTAMATCH);
your "none crypto" finding is confirmed and is *not* universal across Kalshi.

**Recording overnight:** tennis order-book depth →
`data/depth/<date>/<hh>/depth.jsonl`, 118 markets, 0.55 s pacing, single-threaded.
Kalshi has no historical book endpoint, so an interruption is irrecoverable.

Artifacts: `HANDOFF.md`, `DECISIONS.md`, `SELECTION_AUDIT.md`,
`PREREGISTRATION_PARTB.md`, `docs/POST_SETTLEMENT_FIELDS.md`, `src/leakguard.py`.
