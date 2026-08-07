# PREREGISTRATION — does a resting order capture enough spread to cover the pick-off?

**2026-08-07.** Written **before any spread-capture number, any fill count, and
any P&L exists** for this design. What had been measured when this file was
committed is in §1.2 and it is all apparatus. Git history is the evidence for
that ordering, which is why this file is committed alone.

---

## 1. The question, and why it is the only one left alive

### 1.1 What is known and what is missing

[MM_RESULTS_MAKER.md](MM_RESULTS_MAKER.md) §6b measured one half:

> **Adverse selection on real Kalshi crypto flow is ~0.5¢ per contract, negative
> on 8 of 8 days** (day-clustered −1.256¢, 95% CI [−2.788, −0.344]; −0.526¢ and
> 7 of 7 excluding a one-event stub day). It **grew** as data was added,
> −0.387¢ at 432 events → −0.532¢ at 658.

**The other half has never been measured: what a resting order actually
captures.** MM_RESULTS §10 states the gross margin at the touch is a full
**1.00¢**, but that is a *quoted spread*, not a captured one. A maker only earns
it on the fills they actually get, at the queue position they actually hold.

**0.5¢ of cost against an unmeasured income is not a verdict.** That is the gap.

### 1.2 Everything measured before this file was written

| measured | value | where |
|---|---|---|
| adverse selection, settlement-marked | **−0.526¢**, 7 of 7 days | MM_RESULTS_MAKER §6b |
| ⚠ **the recorder does NOT cover crypto** | `record.py`'s `KALSHI_SERIES` has **zero** `KXBTC`/`KXETH` entries — soccer, tennis, esports, MLB, weather only | §1.3 |
| **the L2 archive DOES cover crypto** | `KXBTCD` **22,691 rows/hour (1.264%)**, `KXBTC` 22,132, `KXETHD` 8,730, `KXETH` 8,780; **16,449 distinct crypto tickers in one hour** | `src/probe_l2_crypto.py` |
| archive window | 2026-05-19T06 → 2026-06-11T03, **frozen, not rolling** (M003) | `pull_l2.py` |
| fill model, already written and validated | trade-through only, last in queue | `bot-hunt/src/engine.py::maker_fills` |
| book replay, already written | snapshot + delta → point-in-time book | `bot-hunt/src/replay.py` |

**Not measured, and deliberately not:** any spread capture, any fill rate on
crypto, any maker P&L from the book.

### 1.3 ⚠ A correction to something I told the user

I said the order book was *"free and already recording."* **It is free. It is not
recording for crypto.** The recorder covers five families and crypto is not one
of them. That mattered: it is the difference between "this runs now" and "this
needs weeks", and I had the wrong answer until I checked.

**What rescues the timeline is the archive, not the recorder** — ~24 days of full
L2 already on a public server. **Route A, decided by measurement.**

---

## 2. The test

### 2.1 Design — **M1**

Replay `KXBTCD` L2 from the archive into a point-in-time book. At pre-registered
sample instants, place a simulated resting order; follow it forward; decompose
what it earns.

```
capture_c      = |mid_at_fill − fill_price|          # what resting paid us
adverse_c(Δ)   = signed mid move against us, fill → fill+Δ
fee_c          = maker fee, from common/kalshi_fees.py with a SeriesFees
                 fetched from the API (KXBTCD is `quadratic` ⇒ 0, verified)
net_c(Δ)       = capture_c − adverse_c(Δ) − fee_c
```

| | |
|---|---|
| **arms** | `join` (rest at the touch) · `improve` (rest 1¢ inside) · both sides |
| **fill model** | **trade-through only, last in queue** — `engine.py::maker_fills`, unchanged |
| **Δ (horizons)** | **60 s PRIMARY**; 1 s, 10 s, 300 s, and hold-to-settlement as secondary |
| **unit of observation** | **THE DAY**, ~24 of them |

### 2.2 ⚠ Why 60 seconds is the primary and settlement is not

**This is the single most important choice in the file, and §6b is why.**

Marking to settlement makes every fill in a day share one BTC trajectory. That is
what made the tape measurement unresolvable: the day-clustered CI was **7.78¢
wide against an event-clustered 1.36¢ — 5.7× too narrow** — and one 15-minute
market moved the eight-day mean by 2.5¢.

**A 60-second horizon does not have that problem.** A day-long directional drift
contributes almost nothing to a 60-second post-fill move, so the estimator is not
swamped by the thing that is hardest to sample.

It also answers the question that was actually asked. *"Does the spread cover the
pick-off?"* is a microstructure question about the moments around a fill — not a
bet on where Bitcoin closes.

> **Stated against my own convenience:** the 60 s number is **not** a P&L. A maker
> who cannot flatten in 60 s bears the rest, and the settlement-marked arm is
> reported beside it precisely so the gap between them is visible. **If the two
> disagree in sign, that disagreement is the finding**, and it means inventory —
> not adverse selection — is what kills this.

### 2.3 Clustering, and the correction it encodes

**Every CI is bootstrapped over DAYS.** Event-clustered figures are reported
beside them **with the ratio of the two interval widths printed**, so that if I
ever again quote the narrow one it is visible on the same line. Effective n is
printed next to nominal n (C019, C026, K003).

### 2.4 Capacity is part of the result, not a footnote

Every surviving cell reports **depth at the resting level** and **queue ahead**.
An edge available for 3 contracts is recorded as an edge available for 3
contracts. This repo's recurring shape is *a real effect smaller than the cost of
reaching it*, and the esports arb author with the only reconciled live P&L lost
**38% of gross** to adverse selection.

---

## 3. Controls — four, and two of them gate the run

| | control | what a failure means |
|---|---|---|
| **N1** | **Side placebo.** Randomly reassign which side of each fill we were on. | This is what killed the tape version. **N1 positive ⇒ nothing is reportable.** |
| **N2** | **Positive control.** Inject a known 0.5¢ capture into synthetic flow; the pipeline must recover it within its CI. | If it cannot find a planted effect, a null means nothing (C008 is why this exists). |
| **N3** | **Touch-counts-as-fill**, run **only** as a declared leak diagnostic. | It must produce a *materially better* number. If it does not, the conservative fill model is not biting and the whole engine is suspect. |
| **N4** | **Never-filled orders contribute exactly zero.** | A silent non-zero means the accounting is wrong before any strategy question is asked. |

**N1 and N2 gate. N3 and N4 are asserted in code and the run refuses to print if
either fails.**

---

## 4. Decision rules, fixed now

1. **BH-FDR at q = 0.10** across the whole grid — 2 arms × 2 sides × 5 horizons ×
   4 slippage = **80 cells**, one denominator. Empty cells stay in it.
2. **Two-sided.** A significantly *negative* capture is a finding: it would be a
   fifth confirmation that passive quoting loses on this exchange.
3. **The cost bar is recomputed per fill** from `common/kalshi_fees.py` with a
   `SeriesFees` fetched from the API. Never hardcoded, never assumed zero.
4. **MDE beside every null.** Effective n beside nominal n.
5. **Surface, not peak** — each surviving cell labelled PEAK or PLATEAU.
6. **Monotone strengthening with sample size is CONTAMINATION** (GUARDS #10) —
   and note that adverse selection *already did this* in §6b, growing 37% when
   52% more events were added. **If capture does the same, treat it as a warning,
   not a discovery.**
7. **The holdout is the newest 30% of DAYS**, sealed, touched once, by survivors
   only. Frozen to `reports/maker_viability_holdout.json` at the first run.

## 5. What I expect, written down so a null is a measurement

**I expect M1 to fail**, and the reasons are all already on record:

- **S008/S009** — all 15 maker configurations on tennis net-negative, with
  adverse selection exceeding price improvement at every window.
- **H10** — passive quoting on esports: fill rate is real (29–36% strict) and
  the P&L **sign-flips** across nested prefixes.
- The esports arb author with the only reconciled live P&L: **adverse selection
  cost 38% of gross**, and he switched the strategy off.
- A 20-year professional in this repo's own corpus: **"be a market TAKER, not a
  market maker"** — you are filled only in the states where you were wrong.
- **~49 corrections in this repo and every one shrank the edge.**

**The one thing that would make it interesting:** capture at 60 s exceeding
0.5¢ *while* the settlement-marked arm is negative. That combination would mean
the spread does cover the pick-off and **inventory** is the killer — a different
problem, and unlike adverse selection, a hedgeable one.

## 6. What would make me revise

A cell clearing BH-FDR **and** exceeding the measured ~0.5¢ adverse-selection
cost **and** clean on N1 **and** a PLATEAU **and** surviving the sealed holdout
**and** with reportable depth at the resting level. **Fewer than six and it is a
lead, not a finding.**

## 6b. AMENDMENT A1 — the hour sample. Declared BEFORE the pull, 2026-08-07.

**No number from this design existed when this was written.** The trial pull that
forced it produced only transfer statistics.

**What fired.** §7 says "~24 days is what exists" and did not say how much of each
day. Measured on one trial hour (`2026-05-30T17`, `KXBTCD`):

| | |
|---|---|
| rows kept | **570,699** for one hour, one series |
| **transfer** | **92.5 MB of a 127 MB file — 73%** |

Parquet stores columns contiguously, but the book columns (`yes_bids`,
`no_bids`) *are* most of the file, so range requests save far less here than
they did on the esports pull. **The full window is 550 files ≈ 51 GB.**

`pull_l2.py`'s own docstring says it: *"This is somebody else's volunteer-run
archive … taking 37 GB to answer one question would be rude and unnecessary."*
That applies to me.

**The rule, fixed now and applied identically to every day:**

> **Three hours of every day — 08:00, 14:00 and 20:00 UTC.** 24 days × 3 =
> **72 files ≈ 6.7 GB**, giving **72 events across 24 day-clusters**.

**Why three, and why those.** The binding constraint on this design is the number
of **days** (§2.3 clusters on the day), not hours within a day — extra hours buy
within-day precision the day-clustered interval barely uses. Three spread across
the active session samples different liquidity regimes rather than one; a single
fixed hour would confound the result with whatever is special about that hour.

**What this costs, stated rather than hidden:** ~87% of the archive's book events
are not read. If a maker edge exists **only** in the hours not sampled, this will
miss it. The three hours are fixed in advance and identical across days, so the
sample is uniform — but it is a sample, and any result carries that.

**One consequence for §4.7's holdout:** the holdout is still the newest 30% of
**days**, unchanged. Sampling hours does not touch it.

---

## 7. Scope, and what is deliberately NOT in it

- **One series, `KXBTCD`.** `KXBTC`, `KXETHD`, `KXETH` are a **replication arm**,
  run only if `KXBTCD` survives. C026 measured the crypto assets at **~1.81
  effective independent series of four** — they are not four confirmations.
- **~24 days is what exists.** The archive is **frozen** (M003), so this cannot
  be extended by waiting. Extending it means adding crypto to a recorder and
  accruing forward — **not done here**, because it would lengthen every cycle of
  the shared recorder that four other threads depend on. Logged in `DECISIONS.md`.
- **No order placement. No money.** Simulated fills against recorded books only.
