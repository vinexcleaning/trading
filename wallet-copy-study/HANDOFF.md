# HANDOFF — specialist wallet copy trading

Read-only public data, simulated fills only. No funded wallet, no order
placement, nothing live.

**Location:** `C:\Users\gianf\trading\wallet-copy-study` (moved — see R1)
**Interpreter:** `C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe`
**Prior sessions' handoff:** `HANDOFF_prior_sessions.md`

---

## 1. SPECIALIST vs GENERALIST — the session in one table

Ranked on period 1 only, measured on untouched period 2, within category only.
`F6_min20_all`, unweighted. Unit = **event**. `net` subtracts the 1.0pp spread
floor (a lower bound — the subgraph carries no book).

| Cut | Category | Copier gross | **Copier net** | Naive | **Excess vs naive** | CI95 | p | BH | n events | **n_eff** | Generalist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07-01 | **politics** | +3.387 | **+2.387** | −0.428 | **+1.180** | [0.37, 2.00] | 0.006 | **yes** | 3,360 | 2,337 | +0.937 |
| 2025-07-01 | other | +0.907 | −0.093 | −1.649 | +1.342 | [0.47, 2.26] | 0.005 | **yes** | 3,644 | 2,927 | +0.937 |
| 2025-07-01 | crypto | −2.352 | −3.352 | −2.360 | −0.970 | [−2.61, 0.70] | 0.256 | no | 744 | 636 | +0.937 |
| fee era | **politics** | +4.946 | **+3.946** | −0.299 | +1.154 | [−0.12, 2.57] | 0.073 | no | 1,190 | 1,076 | −0.135 |
| fee era | **soccer** | +3.582 | **+2.582** | −1.767 | **+3.464** | [1.66, 5.25] | 0.001 | **yes** | 928 | 743 | −0.135 |
| fee era | crypto | +1.433 | +0.433 | −2.222 | **+2.052** | [0.48, 3.60] | 0.010 | **yes** | 818 | **131** | −0.135 |
| fee era | other | −0.430 | −1.430 | −1.356 | +0.078 | [−3.12, 3.34] | 0.971 | no | 462 | 370 | −0.135 |
| fee era | nba | −4.113 | −5.113 | −1.385 | −2.428 | [−9.51, 4.47] | 0.483 | no | 134 | 95 | −0.135 |

**Pooled, volume-weighted:** 2025-07 copier +1.554pp / excess +2.788pp
(n=10,213, n_eff=5,900); fee era copier +1.645pp / excess +3.709pp (n=24,607,
n_eff=**2,415**).

### The answer

**Specialists beat the generalist; politics is the only category that does it
robustly.** Across the full 262-specification grid:

| Category | Cut | Specs | Positive | BH-sig | Median excess | Range |
|---|---|---|---|---|---|---|
| **politics** | 2025-07 | 21 | **21/21** | **21/21** | +1.271 | [+1.10, +1.53] |
| **politics** | fee era | 21 | **21/21** | 3/21 | +0.825 | [+0.28, +1.50] |
| other | 2025-07 | 21 | 21/21 | 16/21 | +1.182 | [+0.69, +1.52] |
| other | fee era | 21 | 5/21 | 0/21 | −1.114 | [−1.92, +2.44] |
| soccer | fee era | 21 | 21/21 | 11/21 | +2.205 | [+1.13, +3.56] |
| **soccer** | 2025-07 | 15 | **0/15** | 4/15 | **−3.336** | [−8.17, −0.95] |
| crypto | fee era | 21 | 16/21 | 8/21 | +1.507 | [−1.66, +4.03] |
| crypto | 2025-07 | 21 | 9/21 | 1/21 | −0.186 | [−3.67, +3.95] |
| nfl | fee era | 17 | 16/17 | 3/17 | +4.242 | [−1.95, +13.21] |

**Politics is positive in 42/42 specifications across both cuts, tight range.**
Nothing else is. **Soccer flips sign between cuts.** Crypto and `other` each work
at one cut and fail the other.

---

## 2. Which filters mattered, which were cosmetic

| Filter set | Specs | BH sig | Median excess | Median n_eff | Median wallets |
|---|---|---|---|---|---|
| F0 min10 | 48 | 12 | +0.646 | 483 | 387 |
| F1 min20 | 42 | 8 | +0.854 | 548 | 243 |
| F2 min50 | 39 | 9 | +0.955 | 569 | 135 |
| F3 min20+recent | 36 | 9 | +1.121 | 598 | 128 |
| **F4 min20+cadence** | 32 | 12 | **+1.345** | 392 | 61 |
| F5 min20+nonMM | 41 | 11 | +0.854 | 466 | 185 |
| F6 all | 24 | 10 | +1.268 | 743 | 76 |

- **Min trades/events MATTERED**, monotonic: +0.65 → +0.85 → +0.96pp
- **Recency + cadence MATTERED MOST**: +0.85 → +1.12 → +1.35pp
- **Non-MM filter COSMETIC** (identical to F1 without it)
- **Recency weighting COSMETIC**: hl30d +1.121 / hl90d +1.014 / unweighted
  +0.940 — ~0.2pp, inside grid noise. The brief expected this to matter. It does not.

**Tension:** ≥20 trades in a category selects the high-frequency wallets the MM
fingerprint then removes. Some of the "gain" from filtering is selection
intensity, not better wallets.

---

## 3. Whale exclusion: **immaterial, not wrong**

Impact does not scale with size — mean price move after a fill, 13.5M fills:

| Size ($) | d0 | d10 | d60 | d300 | d1800 | n |
|---|---|---|---|---|---|---|
| 0–100 | −0.371 | −0.195 | −0.133 | +0.123 | +0.448 | 12,170,124 |
| 100–1,000 | −0.346 | −0.056 | −0.044 | −0.033 | +0.176 | 1,159,982 |
| 1,000–10,000 | −0.378 | −0.056 | −0.035 | −0.010 | +0.089 | 189,817 |
| **10,000+** | **−0.297** | −0.138 | −0.103 | −0.029 | +0.049 | 14,213 |

The largest trades move price **less** than the smallest. Putting whales back
leaves politics/crypto/soccer/other **byte-identical**; only nba shifts. Only 41
such wallets exist and almost none clear the bar. **Keep it or drop it — it does
not matter.**

---

## 4. Which wallets survive a 30-minute delay? — **NONE. And the latency budget is ~10–60 seconds.**

*This was "unanswerable" last session at 0.9% coverage. A targeted pull was run:
**6,340 tokens, +11.27M fills**, bringing usable coverage to **11.2%** (3,741 of
33,522 survivor positions, **2,330 events, n_eff 1,470**). Balanced panel — a
position enters at every delay or none.*

### Pooled decay across all survivors

| Delay | n_ev | n_eff | Gross | **Net of spread** | CI95 gross | p |
|---|---|---|---|---|---|---|
| **0s** | 2,330 | 1,470 | **+4.651** | **+3.651** | [3.31, 5.91] | 0.0007 |
| **10s** | 2,330 | 1,470 | +2.014 | **+1.014** | [0.76, 3.28] | 0.0027 |
| **60s** | 2,330 | 1,470 | +1.357 | +0.357 | [0.16, 2.58] | 0.028 |
| 300s | 2,330 | 1,470 | +0.721 | **−0.279** | [−0.43, 1.89] | 0.229 |
| **1800s** | 2,330 | 1,470 | **−0.125** | **−1.125** | [−1.14, 0.90] | 0.804 |

### ⚠ THE 0-SECOND ROW IS NOT AN OPPORTUNITY — read this before quoting +4.65pp

**In 55.5% of positions the "price at 0s" IS the wallet's own trade** (median gap
between the wallet's entry and the 0s print: **0 seconds**). So the 0s row is
largely a restatement of the wallet's own edge, not a price any copier could
reach — that trade already happened, and it was theirs.

**The first row a copier could physically touch is 10s, and realistically 60s.**
Quoting the 0s figure as an opportunity is the same family of error as
backtesting over the selection window.

### Face value vs return on capital

`pp` is percentage points of the **$1 contract face value**, not a return on cash
deployed. Mean entry price is ~0.63, so:

| Delay | Mean px | Edge pp | Net pp | **Net return on capital** |
|---|---|---|---|---|
| 0s *(not reachable)* | 0.626 | +4.651 | +3.651 | **+5.83%** |
| **10s** | 0.654 | +2.014 | +1.014 | **+1.55%** |
| **60s** | 0.662 | +1.357 | +0.357 | **+0.54%** |
| 300s | 0.669 | +0.721 | −0.279 | −0.42% |
| 1800s | 0.682 | −0.125 | −1.125 | −1.65% |

*Caveat on a flattering statistic:* the per-position mean of `edge/price` reads
18–31%, but that average is dominated by cheap longshots where a small edge
divides by a small price. The portfolio figure above (total edge ÷ total capital)
is the honest one and is what should be quoted.

**57% of the edge is gone within 10 seconds. It is statistically dead by 300
seconds and economically dead by 30 minutes.**

**Latency budget: ~10s to keep a confident net edge, ~60s to keep any net edge
at all.** That is a bot requirement, not a phone-alert requirement.

### Per wallet — 17 of 30 reportable (≥30 events), **0 followable slowly**

| Wallet | Cats | n_ev | n_eff | d0 | d10 | d60 | d300 | d1800 | net1800 | loCI | Slow? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0x42157c2942.. | crypto | 109 | 66 | +12.94 | +11.13 | +12.46 | +11.95 | +6.08 | +5.08 | −0.42 | no |
| 0xed2c371514.. | other | 187 | 163 | +5.19 | +5.01 | +5.07 | +5.17 | +5.71 | +4.71 | −0.70 | no |
| 0x3c593aeb73.. | politics, other | 78 | 76 | +8.75 | +6.89 | +6.67 | +5.24 | +4.26 | +3.26 | −6.28 | no |
| 0x611a3c5951.. | other | 57 | 45 | +35.77 | +14.17 | +13.16 | +7.70 | +2.39 | +1.39 | −3.98 | no |
| 0xbd70eebd13.. | politics | 111 | 107 | +2.81 | +2.14 | +2.06 | +2.31 | +1.81 | +0.81 | −4.52 | no |
| 0x27db6ea905.. | politics | 260 | 243 | +2.43 | +1.70 | +1.92 | +1.84 | +0.99 | −0.01 | −4.07 | no |
| 0x15ac9d4fb9.. | soccer | **1,134** | 882 | +7.93 | +3.64 | +1.87 | +0.66 | +0.06 | −0.94 | −1.41 | no |
| 0xc468b3b856.. | politics, other | 100 | 98 | +4.24 | −3.93 | −2.37 | −2.29 | −1.70 | −2.70 | −11.26 | no |
| 0x77a395dd28.. | other | 86 | 76 | −17.11 | −16.82 | −17.05 | −17.23 | −15.69 | −16.69 | −24.65 | no |

*(9 of 17 shown; 8 further wallets all negative)*

**0 of 17 pass.** Two came close — `0x42157c2942..` (+5.08pp net at 30 min, lower
CI **−0.42**) and `0xed2c371514..` (+4.71pp net, lower CI **−0.70**) — and both
fail on the confidence bound, not the point estimate. **BH-FDR: 1 of 17
significant at d1800, and that one is significantly NEGATIVE** (−15.69pp).

The largest sample (`0x15ac9d4fb9..`, soccer, 1,134 events) shows the canonical
shape: **+7.93 → +0.06pp**. Edge is real at zero delay and gone by 30 minutes.

### Answer to the question as posed

**No wallet can be followed by hand from a phone alert.** The "no bot, no
custody" proposition does not survive contact with the data. A bot inside ~10
seconds is required, and even then the net edge is ~+1pp against a spread floor
that is a lower bound.

---

## RETRACTIONS AND DISPROVEN PREMISES

**R0 (NEW, this session). My own interim Task 5 reading was wrong and more data
killed it.** At 8.8% coverage the pooled 30-minute figure was **+0.98pp gross /
−0.02pp net** and **one** wallet passed the followable test
(`0xed2c371514..`, net +8.94pp, lower CI **+2.20**, n=133). After topping up to
11.2% coverage the same wallet reads net **+4.71pp, lower CI −0.70** (n=187) and
the pooled 30-minute figure is **−0.125pp gross / −1.125pp net**. **Followable
wallets went 1 → 0.** The direction of change matters: *more evidence made it
worse*, which is this project's pattern and a reason to treat the remaining
88.8% of uncovered positions as likely to make it worse still, not better.

**R1. The project moved** to `C:\Users\gianf\trading\wallet-copy-study`. Its
standalone git repo is gone — the folder now sits inside the `trading` repo, so
**16 commits of provenance are unreachable**. Data intact.

**R2. "Edge does not decay with latency, flat 0s–1800s" — FALSE**, and now
measured directly on the survivors: **+4.651 → −0.125pp**. The premise was true
only unconditionally, over all buys. The whale argument rested on it and reached
a defensible conclusion by luck.

**R3. "The earlier study may not have sized proportionally" — PARTLY FALSE.** It
already averaged a per-share return with equal weight per position, which *is* a
fixed fraction of bankroll per signal.

**R4. My synthetic control was wrong twice; its sanity check caught both.**
v1 per-token Bernoulli(vwap) → +3.94pp (YES/NO complementarity violated). v2
per-market weighted draw → +1.04pp (vwap is volume-weighted, positions are not).
v3 (used) permutes wallet labels within events, outcomes untouched.

**R5. My first registered hypothesis was wrong and it mattered.** Testing copier
return against **zero** gave **54 of 206 "significant"** in the null. The paired
copier-vs-naive test gave **0 of 249**. Same error that produced the original
+7.05pp finding.

**R6. A bug silently gutted the control.** `mm` is a per-position copy of a
per-wallet flag; under permutation it travelled with the position, so nearly
every wallet looked like a market maker. Fixed to read the wallet-level file.

**R7 (NEW). The windowed pull optimisation made things WORSE and was reverted.**
Adding a `timestamp` predicate to an `_in` query pushed the ETA from 235 min to
627 min — graph-node scans more, not less, with that combination. Recorded so it
is not retried. Full-book batched pulls at `BATCH=25` are the working method.

**R8. Unverifiable premises adopted as method, not fact.** "~47 corrections",
"8 dead positives", "1.81 effective series" have no artefact here. The methods
they imply are right and were applied; the numbers were not verified.

---

## CANARIES AND CONTROLS

| Control | Result |
|---|---|
| **Synthetic control (permuted wallet labels)** | **0 of 249 significant** vs **71 of 262** real. Median excess +0.052pp vs +1.014pp; 53% vs 66% positive. **PASS and discriminates.** |
| Look-ahead assertions | **PASS** both cuts, both modes; raises rather than warns |
| Selection-audit canary | **PASS** — pooled excess −0.0pp |
| Test suite | **32 passed** |
| Balanced panel (Task 5) | Enforced — n constant at 2,330 across all delays |
| Pull/analysis lookahead alignment | Pull window and `MAX_LOOKAHEAD` both 3600s, so no delay column is silently dropped |
| Fee-era restriction | One cut ranked **and** measured entirely post-2026-01-08 |
| Category coverage | 100% of 453,372 markets; **79.9% of volume** named; **0% unmapped** |

**Tests this session: 262 real + 249 synthetic + 10 whale + 17 per-wallet = 538**,
BH-FDR corrected within families.

---

## PROVENANCE

| Item | Value |
|---|---|
| Panel | 1,702,214 settled positions, 2,500 wallets, 677,721 tokens |
| Books pulled this session | **6,340 tokens, +11.27M fills** (~2.9 GB) |
| Books used for Task 5 | 24,808,505 fills over 14,256 tokens |
| Unit of observation | **event** (game, or recurring series-day) |
| Date range | 2022-11-21 → 2026-04-28 (subgraph stale ~3 months) |
| Selection A / B | before 2025-07-01 (223,315 rows) / before 2026-01-08 (685,088) |
| Task 5 coverage | **11.2%** of survivor positions; 17 of 30 wallets reportable |
| Seed | 20260801 throughout |

---

## NOW CLOSED

- Category ranking beats whole-portfolio ranking — **politics only**, both cuts,
  42/42 specifications.
- **Task 5 answered: latency budget ~10–60s; 0 of 17 wallets followable at 30
  minutes.** The phone-alert proposition is dead.
- Recency weighting cosmetic; min-trade and cadence filters real (~0.7pp).
- Whale exclusion immaterial; impact does not scale with size.
- Pipeline is not manufacturing edge (0/249 null vs 71/262 real).

## STILL OPEN

- **Task 5 coverage is 11.2%, not 100%.** The remaining 88.8% would take ~6h more
  at the working rate. Interim evidence says more coverage makes the answer
  *worse*, so this is a robustness question, not a hope.
- Politics' absolute net rests on a **1.0pp spread floor that is a lower bound**.
  At a true effective spread of 2pp+, politics is ~break-even.
- Politics at a third, earlier cut. Two cuts is the minimum.
- `other` is 20.1% of volume and is a bucket, not a category.

## NEXT THREE ACTIONS

1. **Measure the true effective spread** (record the CLOB book prospectively).
   Every net number in this session hangs off a lower bound. With a ~10s latency
   budget now established, the spread is the only remaining unknown that decides
   whether politics is tradeable at all.
2. **Finish Task 5 coverage** to ~40%+, prioritising politics wallets. Expect it
   to worsen the result.
3. **Politics at a third cut, and decompose `other`.**

---

## WHAT THE COORDINATING CHAT HAS WRONG — bluntly

1. **"If 30 minutes late costs nothing, price impact may not be eating the copier
   either."** Both halves now measured. 30 minutes late costs **everything**
   (+4.65 → −0.13pp). Impact indeed is not eating the copier — but that
   conclusion was reached *despite* the reasoning, not because of it.
2. **"A wallet whose edge survives 30 minutes can be followed by hand from a
   phone alert — a materially different proposition."** Correct in principle,
   and **there are no such wallets**. 0 of 17 with adequate samples. The
   proposition was worth testing and it failed.
3. **It implied the earlier study got sizing wrong.** It did not.
4. **It supplied unsourced numbers** alongside sourced ones. That makes the
   sourced ones harder to trust, not easier.
5. **"Specialists" is half-right and was worth doing** — politics is real and
   robust. But it is one category of eight, worth ~+1.2pp over benchmark, with a
   ~10-second latency budget and an unverified spread floor. The honest headline
   is: **the narrower question found one real thing, and it is harder to
   harvest than the broad question ever suggested.**
6. **Its framing of the look-ahead failure mode remains the most valuable thing
   it supplied.** That is exactly the error that made my first control report 54
   false positives. Keep it.
