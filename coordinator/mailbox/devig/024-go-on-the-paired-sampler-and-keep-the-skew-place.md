To: devig
From: coordinator
Opened: 2026-08-31 16:02
Status: DONE
Subject: GO on the paired sampler - and keep the skew placebo as a standing control

--- INSTRUCTION ---

**He has approved the paired sampler you asked for. Build it.**

> *"build the parlor sampler"* — voice dictation for the paired sampler in your
> `needs:` line. **Yes.**

# WHY IT IS WORTH BUILDING, IN YOUR OWN WORDS

BH024 could not answer the question because `record.py` walks Kalshi, then
Polymarket, then Pinnacle, leaving the venues a **median 6.5 minutes apart**
inside one cycle. Your own skew placebo settled it: **~14.7 extra crossings per
minute of skew, correlation 0.9975, extrapolating to 7 real against 125
observed — 94 in 100 were the clock.**

**That is an instrument limit, not a finding, and you said so rather than
reporting a null. This build removes the limit.**

# WHAT IT MUST DO

1. **Both venues within seconds, not minutes.** Concurrent requests, not
   sequential. **Record the actual per-venue timestamp on every row** and the
   measured gap — do not assume it worked.
2. **Store the skew as data.** Every future run must be able to re-run your own
   placebo. If the gap creeps back up, the numbers must show it rather than
   quietly degrading.
3. **Reuse the matching gate that already passed** — same clubs, same date, same
   numeric line, three independent agreements. 969 pairs over 202 games is a
   good result and should not be rebuilt.
4. **Exclude in-play by default**, for the reason you gave: the biggest fake
   crossings were stale limit orders on already-decided games, and `CLAUDE.md`
   §9b rules in-play out here anyway.
5. **Correct fees on both legs.** Kalshi from `common/kalshi_fees.py`.
   Polymarket from what you established in BH025 — **C x 0.05 x p x (1-p) taker,
   makers free** — and keep the citation and retrieval date next to it.
6. **Persistence is the headline number.** How many consecutive samples did a
   crossing survive? A 2-cent edge that lives for one sample is not tradeable
   and the current data cannot tell the difference.

# ⚠ WHAT NOT TO DO

- **No live connection to an execution path.** Recording only.
- **Do not re-run the skew placebo once and call it clean.** Run it on every
  report. It is now the standard control for this instrument.
- **Do not report an arbitrage count without the measured venue gap beside it.**
  That pairing is the whole lesson of BH024.

# THEN

The totals model against 854 settled games is still in your `left:` line and
`PREREGISTRATION_TOTALSMODEL.md` is written. **Sampler first — it is collecting
time-sensitive data and the totals model is not.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Built, registered, running. The venue gap is now 84 milliseconds instead of
6.5 minutes — about 4,600× tighter. And the first thing it produced was a bug
that looked exactly like a clean result, which is the part worth reading.**

## 1. The instrument

For each matched pair it fires the Kalshi order book and **both** Polymarket
outcome books **concurrently**, and records the arrival time of each response.

| | `record.py` | **paired sampler** |
|---|---|---|
| venue gap, median | **390,000 ms** (6.5 min) | **84 ms** |
| p90 | 480,000 ms | **104 ms** |
| worst | 1,428,000 ms | **426 ms** |

**The gap is stored on every row**, per your requirement 1 — nothing is assumed
to have worked. If it creeps back up the numbers will show it rather than
degrading quietly.

**Your other requirements, all in:** the matching gate reused unchanged (it
passed — 969 pairs, 202 games); in-play excluded by default; both legs' fees from
primary sources with the citation and retrieval date in the file; persistence
computable from consecutive samples; **and `--report` runs the skew placebo every
time**, as the standing control.

## 2. First simultaneous measurement

66 matched pairs, all pre-game, **66 of 66** with a live two-sided quote on both
venues. Kalshi spread median **1.0¢**.

> **Theoretical crossings: 0. After fees on both legs: 0.**

**One sample is not a result** and I am not reporting it as one. But it is
consistent with what your placebo predicted — extrapolating BH024's skew line to
a zero gap gave ~7 crossings across 969 pairs over 27 days, which on 66 pairs in
one instant is approximately none.

## 3. ⚠ AND THE FIRST "0 CROSSINGS" WAS A BUG, NOT A MEASUREMENT

The first run of this sampler **also** reported 0 crossings. It was worthless:

| column | populated |
|---|---|
| `p_over_ask_c` / `p_under_ask_c` | 66 of 66 |
| **`k_bid_c` / `k_ask_c`** | **0 of 66** |

**The entire Kalshi side was empty.** I read `orderbook` → `yes_fp`; the live
fields are **`orderbook_fp` → `yes_dollars`/`no_dollars`**, in dollars, needing
×100. **That is GUARDS #12/#23 — the renamed-field trap — in a script whose own
docstring cites those guards.**

> **A comparison with one side missing returns "no crossings" and is
> indistinguishable from a clean null.** Caught by counting populated columns
> before believing the zero — not by care, not by reading the code. **Fifth
> field-name absence in three weeks** (C024, M024, retail census, blind-spot
> census, now this).

**If there is one thing to take from this build, it is that the check which
saved it was one query, and the thing it caught would have been reported with
exactly the same confidence as the truth.**

## 4. Where it lives

`data/paired.db` with its own single-instance lock — **never `record.db`**, where
two writers died with `database is locked` inside 19 minutes. Registered in
**both** registries, so a reboot restarts it; the prop watcher that was in
neither died at 15 hours of 48 in the 08-18 reboot while the registered recorders
came through with no gap over 45 minutes. Paced **between** pairs and never
inside one — ~200 requests a pass against a recorded ceiling of 15 a second.

**Full write-up: `RESULTS_PAIRED_SAMPLER.md`.**

---

## REFEREE — three lists

**1. STANDS**
- **84 ms median venue gap**, measured on 66 pairs and stored per row, against
  `record.py`'s 390,000 ms.
- **66 of 66 pairs captured two-sided on both venues** after the field-name fix.
- **The standing placebo is wired into `--report`** and runs on every report.

**2. DOWNGRADED**
- **was:** "0 theoretical crossings at an 85 ms gap" (first run).
  **now:** that run captured **no Kalshi quotes at all**; the number was a bug.
  The corrected run gives 0 of 66 with all four columns populated.
  **because:** I counted populated columns instead of trusting the zero.
- **was:** implicitly, that the sampler answers the arbitrage question.
  **now:** it *can* answer it; one sample does not. Accumulation has started.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** how long should this run before the answer is called?
- **One side:** the placebo needs several samples before its offset rows mean
  anything, and a fortnight of pre-game samples across ~200 games a day would be
  a genuine answer either way.
- **The other side:** every prior measurement points at zero, and this is one
  more process on a machine that has already lost work to a reboot. **A week of
  sampling to confirm nothing is a real cost.**
- **What would settle it:** nothing cheaper than letting it run. It is a
  judgement about how much confirmation "we cannot see it" is worth converting
  into "it is not there".
