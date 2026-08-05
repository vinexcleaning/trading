# REPRODUCTION — an independent re-run of this project's own numbers

Second session, 2026-08-05. Read-only. The bot was not started, no order
endpoint was touched, `TRADING_DISABLED` is untouched, and **nothing in
`kalshi-inplay-bot/` was modified except one row in its `audit/LEDGER.md`.**

The point of this file is narrow: [FINDINGS.md](FINDINGS.md) and
[VERDICT.md](VERDICT.md) were written by the session that produced the numbers.
Nobody had re-run them. This is that re-run.

---

## 1. Everything reproduced

| script | what it produces | result |
|---|---|---|
| `src/t2_master.py` | the ledger, bursts, the peak, the stress test | **reproduced** |
| `src/t2b_nightday.py` | argmax null, clock buckets, BH-FDR | **reproduced** |
| `src/t2c_costbar.py` | permutation p-values, cost bar per bucket | **reproduced** |
| `src/t2d_martingale.py` | multi-leg entries, the score-lag test | **reproduced** |
| `src/t3b_proxy.py` | **the decisive backtest replay** | **byte-identical to `out/t3b_proxy.txt`** |
| `backtest/high_entry.py` | the one positive cell in the file | **reproduced** |
| `backtest/high_sweep.py` | maker/taker bands | **identical apart from a UTF-8 BOM** |
| `backtest/longshot.py` | buy-the-collapsed-favourite | **identical apart from a UTF-8 BOM** |

Spot checks against the written-up figures, all matching: **−$6.92** over 108
matches; **74** bursts; 95% CI **[−$0.967, +$0.780]**; peak **+$32.19** after 60
matches at 13:32 UTC; argmax **p = 0.052**; twelve averaging-down sequences at
**−$16.43** against **+$9.63** on the other 94; **97.4%** of repricing already
done (+4.677c before / +0.169c after, placebo +0.178c, n = 4,398); and the
decisive ITF arm at **−9.13c/trade on 6,135 trades / 2,599 matches**, holdout
**−8.77c** on 1,045 matches.

`high_entry`'s single positive cell also reproduced exactly: **96–97c, opened
≥60c favourite, no stop, n = 95, +0.62c** — becoming **−3.77c** when an 80c stop
is added to the identical trades.

---

## 2. ⚠ The one correction: a reporting selection, not a wrong number

**`t2b_nightday.py` prints `buckets tested: 21   BH discoveries at FDR 5%: 3`,
and it always did — the line is in the committed `out/t2b_nightday.txt` at line
93. [FINDINGS.md](FINDINGS.md), [VERDICT.md](VERDICT.md) and
[HANDOFF.md](HANDOFF.md) all state "0 of 13" without naming which arm.**

They are two different tests over two different families:

| | family | test | result |
|---|---|---|---|
| quoted everywhere | **13** buckets (tier, 4h block, night/day) | **label permutation**, 200,000 shuffles | **0 discoveries** |
| never mentioned | **21** buckets (adds tier×night cells) | **parametric t-test** | **3 discoveries** |

**The 0 is the right answer and the 3 is the broken test.** Three reasons, each
checkable from `out/`:

1. The three "discoveries" are at **n = 4, 5 and 6**. A t-test there divides by a
   realised standard error that is itself barely estimated. For the 04–07 UTC
   bucket the parametric p is **0.0002** and the permutation p **on the same five
   matches** is **0.0477 — 240× larger.**
2. **One of the three is a loss bucket.** WTA|day, n = 4, mean **−$2.89**, all
   four losers. It "clears" because four consistent losses have low variance.
3. The other two — 04–07 UTC and Challenger|night — are **the same six trades**,
   which `FINDINGS.md` already says elsewhere.

Recorded and marked inline in all three files rather than quietly corrected,
because a reader who runs the script sees the 3. Ledgered as
**[B005a](../LEDGER.md#section-7--bot-forensics-the-night-the-live-tennis-bot-made-money)**.

> This is the shape the repo keeps producing: the *arm that was reported* was the
> correct one, and it was reported without saying it was an arm. Nothing is
> overturned; the audit trail was incomplete.

---

## 3. Look-ahead audit of the decisive test

The whole verdict's strongest claim — **D is refuted** — rests on
`src/t3b_proxy.py`. This repo has already had one result family voided by exactly
this class of bug (`S011`, where a dedupe kept the higher-`volume_fp` side and
took four phases down with it), so the decisive test was audited line by line.

**It is causally clean.**

| step | where | uses |
|---|---|---|
| signal | `t3b_proxy.py:60-67` | `v.mid[0]` (the open), `v.live`, `v.spread`, `v.ask_close`, `v.mid` — **all at index `i` or earlier** |
| fill | `t3b_proxy.py:90` → `engine._enter(v, i+1, SLIP)` | the **next** candle's closing ask **+1c**. No same-bar fill |
| exits | `t3b_proxy.py:103` → `engine._walk(v, i+1, …)` | evaluation begins at `start+1`; the entry candle's own high/low are never scanned |
| ties | `engine._walk` | **stop-before-target on same-candle ambiguity, always** — the conservative side |
| ordering | `t3b_proxy.py:73` | `cand.sort(key=lambda x: x[0])` — **entry timestamp only**, stable, ties fall back to views order. This is the same dedupe the 2026-08-03 audit examined and found clean |

`engine._walk`'s own docstring states the rule explicitly: *"We bought at candle
`start`'s closing ask, so that candle's own high and low already happened —
scanning them would be look-ahead. Evaluation begins at start+1."*

### The two soft spots, stated rather than buried

Line 54 filters on `np.isnan(v.settlement)` and `v.live.sum() < 10`. Both touch
information not available at decision time:

- **`settlement`** is a post-outcome field, but it is used only to decide whether
  a market can have a P&L computed at all, never as a signal. Every market in the
  corpus is settled by construction.
- **`v.live.sum() >= 10`** requires the market to have ≥10 live candles *in
  total*, which at candle `i` you do not yet know. This is a data-quality filter
  applied uniformly across all configurations and all tiers.

Neither enters the entry rule. Both would have to correlate with the *direction*
of outcome to bias the estimate, and no mechanism for that is apparent.

### The property that makes this argument robust anyway

**Look-ahead bias inflates backtest results. This result is strongly negative.**

A leak makes a strategy look better than it is, so a test with residual
look-ahead risk that still returns **−9.13c per trade at t = −26** is reporting a
*ceiling*, not a floor. The true figure would be the same or worse. That is why
the negative verdict survives an imperfect audit in a way a positive one never
could — and it is the reason this project's decisive claim is the refutation of D
rather than any of the affirmative findings.

> Corollary worth keeping: **this asymmetry is only available to negative
> results.** Had the replay come back positive, none of the above would have been
> reassuring and the two soft spots would have had to be closed before the number
> could be quoted.

---

## 4. What did not change

The verdict is unchanged: **A and B jointly, C contributing, D refuted.** Every
number in [FINDINGS.md](FINDINGS.md) and [VERDICT.md](VERDICT.md) stands as
written, with the single arm-labelling caveat in §2 above now marked inline where
each claim appears.

The project is now in the root [LEDGER.md](../LEDGER.md) as **Section 7, rows
B001–B020**, which it was not before — and ledgering it corrected two stale rows
in Section 5 (`CH031` had no magnitude; `CH044` said "never diagnosed, never
fixed" and was wrong on both counts).
