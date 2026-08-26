To: tennis
From: coordinator
Opened: 2026-08-26 14:04
Status: OPEN
Subject: His rebound hypothesis - run on 28k tennis tickers, real lift and every trade loses

--- INSTRUCTION ---

**His hypothesis, run tonight on `set1_overshoot/data/maker.db`. Adopt this into
your folder — the script is in a session scratchpad and will not survive.**

Script: `rebound2.py` (in the coordinator session's scratchpad — ask for it, or
rebuild from the method below, which is complete).
Outputs: `reb_tour.json`, `reb_itf.json` — 1,215 cells each.

# THE HYPOTHESIS

A player whose live price peaks high and then falls substantially rebounds more
often than baseline — and may ultimately win more often.

# METHOD

**Unit:** one ticker = one player's contract in one match. **One event per
ticker per parameter cell**, at its first qualifying dip, so an oscillating
match cannot contribute ten correlated events to the same number.

**Grid:** peak ∈ {70,75,80,85,90} × dip ∈ {destination 30/40/50/60, drawdown
10/20/30/40/50} × outcome ∈ {returns to peak level, trades above 50/60/70/80,
recovers +10/+20/+30, ultimately wins}.

**⚠ THE CONDITIONAL BASELINE IS THE WHOLE STUDY.** Every cell is compared with
ticker-minutes **in the same competition, the same third of the match, the same
10-cent price band, whose running peak had not yet reached P**. Same place,
different history. Without this, "80c player falls to 50c and recovers 55% of
the time" measures nothing but what 50c means.

**No look-ahead:** the trigger uses the running peak at or before the candle;
the outcome uses only candles strictly after it. Future max is a single
backward pass computed per path, never consulted by the trigger.

**Out of sample:** split on `close_time` at 2026-08-01. Everything reported is
the TEST half. Benjamini-Hochberg across all non-sparse test cells. Cells with
fewer than 30 events or 30 controls are marked sparse and excluded.

# RESULT 1 — THERE IS REAL PREDICTIVE LIFT, AND IT IS NOT WHERE HE EXPECTED

**Main tour (ATP + WTA, 3,576 settled tickers). Only SHALLOW dips survive:**

| peak | dip | n | wins | baseline | lift | p | BH |
|---|---|---|---|---|---|---|---|
| 75 | −10 pts | 471 | 70.5% | 62.8% | **+7.6** | 0.0006 | **yes** |
| 70 | −10 pts | 550 | 66.0% | 60.5% | +5.5 | 0.008 | no |
| 80/85 | fell to 30c | 136/91 | 25% | 24% | +1.1 | 0.76 | no |

**The deep-crash version — his actual hypothesis — is flat on the main tour.**

**ITF (24,296 settled tickers). Bigger, and it DOES extend to deep dips:**

| peak | dip | n | wins | baseline | lift | p | BH |
|---|---|---|---|---|---|---|---|
| 70 | −10 pts | 3,062 | 71.1% | 61.5% | **+9.6** | <0.00001 | **yes** |
| 75 | −10 pts | 2,743 | 74.2% | 66.7% | +7.4 | <0.00001 | **yes** |
| **90** | **fell to 30c** | **268** | **26.5%** | **20.2%** | **+6.3** | 0.010 | **yes** |
| 85 | fell to 30c | 470 | 26.0% | 20.4% | +5.6 | 0.003 | **yes** |
| 80 | fell to 30c | 667 | 25.6% | 20.2% | +5.5 | 0.0005 | **yes** |

**⚠ THE TWO POPULATIONS DISAGREE ON THE DEEP VERSION AND I CANNOT EXPLAIN IT.**
Either ITF is genuinely less efficient, or its wider spreads make the mid a
worse probability estimate and the lift is measurement error. **That is the
first thing to resolve and it is not resolved.**

# RESULT 2 — EVERY TRADABLE VERSION LOSES MONEY. ALL OF THEM.

Buying at the **ask** on the dip, selling at the **bid** on the rebound or
holding to settlement, fees from `common/kalshi_fees.py`:

```
  main tour : every cell   -5.3% to -33.0%
  ITF       : every cell   -5.7% to -20.2%
```

**Including the cells with the largest, most significant lift.** ITF `70/draw10`
carries a +9.6 point edge and returns **−7.4% to −10.4%** depending on exit.

**The mechanism, and it is the familiar one:** the lift lives where the price
barely moved, so there is little to capture, and the spread plus fee is larger
than the edge. **This is the clean separation his brief asked for — predictive
lift is real and is not a tradable edge — and it is now measured rather than
asserted.**

# ⚠ RESULT 3 — WHAT THIS IS PROBABLY MEASURING, AND IT IS NOT A REBOUND

The strongest, most robust cells are **10-point drawdowns**, not crashes. A
contract that touched 75 and slipped to 65 beats a contract that arrived at 65
having never touched 75.

**That is a peak-attainment effect, not a dip-recovery effect.** Reaching 75
is itself information about the player; the dip is incidental. **Do not write
this up as "buying the dip works" — the deep-dip version is flat on the main
tour, and the version that survives everywhere is barely a dip at all.**

# WHAT COULD NOT BE TESTED — the missing data, exactly

`maker.db` has **no score state at all**. So none of the following was possible:
set and game score · point score · sets remaining · best-of-3 vs 5 · who is
serving · break-point state · recent breaks · tiebreak status · up/down a break
· retirement and injury flags · ranking/Elo · surface.

**What exists instead:** competition (`series`), a crude match-phase third from
candle position, prematch price (`state.pre_bid/pre_ask`, loaded but unused),
tier, and the full bid/ask path at 60-second resolution.

**Smallest collection plan to close it:** a per-match score poller aligned to
Kalshi timestamps — set/game score, server, and point score if available,
written every 60 seconds into a table keyed on `(ticker, ts)` so it joins
straight onto `candles`. **Nothing else in the study changes.**

# OTHER LIMITATIONS, STATED NOT BURIED

1. **The control pool spans train and test.** More precise controls, but if the
   effect drifts over time this understates that. Re-run with segment-matched
   controls.
2. **One ticker can be treated for peak 75 and control for peak 90** at
   different minutes. Correct by construction — the running peak is frozen —
   but worth knowing.
3. **70 days, one northern summer.** No seasonal robustness is possible.
4. **`mid` as probability.** On ITF the spread is wide enough that this is a
   real assumption, and it is the leading candidate for the tour/ITF
   disagreement.

# RECOMMENDED NEXT EXPERIMENT

**Not more thresholds.** Resolve the tour-versus-ITF contradiction, because
every downstream conclusion depends on which one is telling the truth: re-run
the ITF deep-dip cells restricted to spreads of 3 cents or less. **If the lift
survives a tight-spread filter it is real and ITF is genuinely slower. If it
vanishes, it was the mid all along** — and that finding also retires a large
part of what makes ITF look attractive elsewhere.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

