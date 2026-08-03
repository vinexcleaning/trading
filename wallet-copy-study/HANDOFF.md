# HANDOFF — specialist wallet copy trading

Read-only public data, simulated fills only. No funded wallet, no order
placement, nothing live.

**Location:** `C:\Users\gianf\trading\wallet-copy-study` (moved — see R1)
**Interpreter:** `C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe`
**Prior sessions' handoff:** preserved as `HANDOFF_prior_sessions.md`

---

## 1. SPECIALIST vs GENERALIST — the session in one table

Ranked on period 1 only, measured on untouched period 2, within category only.
Filter set `F6_min20_all` (≥20 trades, ≥10 events, active in last 30d, no gap
>30d, market makers excluded), unweighted. Unit of observation is an **event** (a
game, or a recurring series-day). `net` subtracts the project's 1.0pp spread
floor — itself a lower bound, since the subgraph carries no book.

| Cut | Category | Copier gross | **Copier net** | Naive | **Excess vs naive** | CI95 | p | BH sig | n events | **n_eff** | Generalist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07-01 | **politics** | +3.387 | **+2.387** | −0.428 | **+1.180** | [0.37, 2.00] | 0.006 | **yes** | 3,360 | 2,337 | +0.937 |
| 2025-07-01 | other | +0.907 | −0.093 | −1.649 | +1.342 | [0.47, 2.26] | 0.005 | **yes** | 3,644 | 2,927 | +0.937 |
| 2025-07-01 | crypto | −2.352 | −3.352 | −2.360 | −0.970 | [−2.61, 0.70] | 0.256 | no | 744 | 636 | +0.937 |
| 2026-01-08 fee era | **politics** | +4.946 | **+3.946** | −0.299 | +1.154 | [−0.12, 2.57] | 0.073 | no | 1,190 | 1,076 | −0.135 |
| 2026-01-08 fee era | **soccer** | +3.582 | **+2.582** | −1.767 | **+3.464** | [1.66, 5.25] | 0.001 | **yes** | 928 | 743 | −0.135 |
| 2026-01-08 fee era | crypto | +1.433 | +0.433 | −2.222 | **+2.052** | [0.48, 3.60] | 0.010 | **yes** | 818 | **131** | −0.135 |
| 2026-01-08 fee era | other | −0.430 | −1.430 | −1.356 | +0.078 | [−3.12, 3.34] | 0.971 | no | 462 | 370 | −0.135 |
| 2026-01-08 fee era | nba | −4.113 | −5.113 | −1.385 | −2.428 | [−9.51, 4.47] | 0.483 | no | 134 | 95 | −0.135 |

**Pooled, volume-weighted:** 2025-07 cut copier +1.554pp / excess +2.788pp
(n=10,213, n_eff=5,900); fee era copier +1.645pp / excess +3.709pp (n=24,607,
n_eff=**2,415** — n_eff is a tenth of nominal n).

### The answer

**Specialists beat the generalist, and politics is the only category that does it
robustly.** Across the *entire* 262-specification grid:

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
| nba, esports, weather | both | small | mixed | 0–4 | unstable | wide |

**Politics is positive in 42 of 42 specifications across both cuts, in a tight
range.** Nothing else is. **Soccer flips sign between cuts** (−3.34 then +2.21pp)
and should not be believed. Crypto and `other` each work at one cut and fail at
the other.

So the earlier study did ask too broad a question — but the honest gain is
narrower than "specialists work". It is: **politics specialists carry roughly
+1.2pp of genuine excess over blind exposure, at both cuts, and +2.4 to +3.9pp
net of spread in absolute terms.** Materially better than the generalist's
+0.937pp / −0.135pp.

---

## 2. Which filters mattered, which were cosmetic

| Filter set | Specs | BH sig | Median excess | Median n_eff | Median wallets ranked |
|---|---|---|---|---|---|
| F0 min10 | 48 | 12 | +0.646 | 483 | 387 |
| F1 min20 | 42 | 8 | +0.854 | 548 | 243 |
| F2 min50 | 39 | 9 | +0.955 | 569 | 135 |
| F3 min20+recent | 36 | 9 | +1.121 | 598 | 128 |
| **F4 min20+cadence** | 32 | 12 | **+1.345** | 392 | 61 |
| F5 min20+nonMM | 41 | 11 | +0.854 | 466 | 185 |
| F6 all | 24 | 10 | +1.268 | 743 | 76 |

- **Minimum trades/events MATTERED**, monotonically: 10 → 20 → 50 lifts median
  excess +0.65 → +0.85 → +0.96pp.
- **Recency and cadence filters MATTERED most**: adding "active in last 30d" then
  "no gap >30d" takes +0.85 → +1.12 → +1.35pp. Largest single gain in the grid.
- **Non-MM filter was COSMETIC** (+0.854, identical to F1 without it).
- **Recency weighting was COSMETIC.** hl30d +1.121, hl90d +1.014, unweighted
  +0.940, with 23/26/22 significant — ~0.2pp, inside grid noise. The brief
  expected this to matter. It does not.

**Structural tension:** requiring ≥20 trades in one category selects precisely
the high-frequency wallets the MM fingerprint then removes. F6 ranks a median of
76 wallets vs F0's 387. Some of the gain from filtering is selection intensity,
not better wallets.

---

## 3. Was the whale exclusion right? — **Immaterial, not wrong**

**Price impact does not scale with size.** Mean price move after a fill, by trade
notional, over 13,534,136 fills:

| Size ($) | d0 | d10 | d60 | d300 | d1800 | n |
|---|---|---|---|---|---|---|
| 0–100 | −0.371 | −0.195 | −0.133 | +0.123 | +0.448 | 12,170,124 |
| 100–1,000 | −0.346 | −0.056 | −0.044 | −0.033 | +0.176 | 1,159,982 |
| 1,000–10,000 | −0.378 | −0.056 | −0.035 | −0.010 | +0.089 | 189,817 |
| **10,000+** | **−0.297** | −0.138 | −0.103 | −0.029 | +0.049 | 14,213 |

The largest trades move price **less** on impact than the smallest. The ~−0.3pp
at d0 common to every row is bid-ask bounce, and it reverts. **Size is not what
costs you.**

**Putting whales back changes essentially nothing.** politics, crypto, soccer and
`other` are byte-identical with and without them; only nba shifts (−4.113 →
−4.234pp, n_ev 134 → 211). Only 41 such wallets exist and almost none clear the
per-category bar.

**Verdict: the exclusion neither cost edge nor saved any. Keep it or drop it.**
The brief's *reasoning* for revisiting was wrong (R2); the conclusion happens to
hold on its own evidence.

---

## 4. Which wallets survive 30 minutes? — **UNANSWERABLE with current data**

**Book coverage of survivors' positions is 0.9%** (303 of 33,522). Only 6 of 30
survivors were measurable, on 8–137 events each.

| Wallet | Cats | n_ev | d0 | d10 | d60 | d300 | d1800 | Slow? |
|---|---|---|---|---|---|---|---|---|
| 0x3c593aeb73.. | politics, other | **8** | +28.72 | +27.75 | +27.56 | +27.80 | +23.26 | no |
| 0xc468b3b856.. | politics, other | 137 | +4.87 | −2.70 | −2.01 | −2.16 | −1.86 | no |
| 0xed2c371514.. | other | 10 | −2.44 | −2.73 | −2.95 | −0.08 | −2.19 | no |
| 0xe7f7e2d3d4.. | crypto | 10 | −5.98 | −6.59 | −6.51 | −6.69 | −5.86 | no |
| 0xe02c5438df.. | nba | 19 | −7.26 | −7.79 | −7.59 | −7.59 | −8.26 | no |
| 0x27db6ea905.. | politics | 13 | −7.57 | −8.06 | −8.91 | −8.99 | −9.00 | no |

**0 of 6 pass.** The spectacular one (+28.72pp) has **n_ev = 8** — exactly the
"+95pp genius wallet" failure mode, shown only to demonstrate why this table must
not be used.

**Do not read this as a result. It is a coverage failure.** Answering Task 5
needs a targeted book pull over ~33k survivor positions (≈6–10h at the observed
0.5 tokens/s), which was not run.

The one usable row (`0xc468b3b856..`, n_ev=137) shows **+4.87pp at 0s collapsing
to −2.70pp by 10s** — consistent with the established fast decay of
selected-wallet entries.

---

## RETRACTIONS AND DISPROVEN PREMISES

**R1. The project moved** to `C:\Users\gianf\trading\wallet-copy-study`. Its
standalone git repo is gone — the directory now sits inside the `trading` repo,
so **the 16 commits of provenance from earlier sessions are unreachable**. Data
intact (5.0 GB wallet fills, 1.2 GB positions, 2.1 GB universe).

**R2. "Edge does not decay with latency, flat 0s–1800s, so 30 minutes late costs
nothing" — FALSE AS STATED.** That was measured *unconditionally*. Conditioned on
selected wallets, buy-and-hold falls **+3.436pp at 0s to +0.427pp at 300s**. The
whale argument was built on this false premise and reached a defensible
conclusion by luck, not reasoning.

**R3. "The earlier study may not have sized proportionally" — PARTLY FALSE.** It
already averaged a **per-share** return with **equal weight per position**, which
*is* a fixed fraction of bankroll per signal, already scale-invariant. What it
does not do is mirror dollar sizes or conviction.

**R4. My own synthetic control was wrong twice; its sanity check caught both.**
v1 redrew each *token's* outcome ~Bernoulli(vwap) → pooled edge **+3.94pp**
(YES/NO are complementary; independent draws let both sides win). v2 drew one
winner per *market* weighted by vwap → **+1.04pp** (vwap is volume-weighted,
positions are equally weighted). v3 (used) **permutes wallet labels within each
event**, leaving outcomes untouched.

**R5. My first registered hypothesis was the wrong one, and it mattered.** I
initially tested whether copier return differed from **zero**. Under that test
the synthetic control reported **54 of 206 "significant"** — a copier can be
profitable purely by holding favourites. Switching to the **paired
copier-vs-naive** test took the control to **0 of 249**. Same error that produced
the original +7.05pp finding.

**R6. A bug silently gutted my control.** `mm` is stored per position as a copy
of a per-wallet attribute; under permutation it travelled with the *position*, so
nearly every wallet looked like a market maker and the F5/F6 control arms ranked
0–2 wallets. Fixed to read the wallet-level flags file; both runs redone.

**R7. Unverifiable premises, adopted as method not fact.** "~47 corrections, 8
dead positives" and "1.81 effective series out of 4" have no artefact in this
project — its own records document far fewer corrections, and 1.81 belongs to a
different project. The *methods* (treat positives as presumptively wrong; report
effective n) are right and were applied. The numbers were not verified.

---

## CANARIES AND CONTROLS

| Control | Result |
|---|---|
| **Synthetic control (permuted wallet labels)** | **0 of 249 significant** vs **71 of 262** real. Median excess +0.052pp synthetic vs +1.014pp real; 53% vs 66% positive. **PASS, and it discriminates.** |
| Look-ahead assertions | **PASS** both cuts, both modes; raises rather than warns |
| Selection-audit canary | **PASS** — pooled excess −0.0pp, random subsets straddle zero |
| Test suite | **32 passed** (3 recompute real positions from raw fills) |
| Fee-era restriction | One of the two cuts is ranked **and** measured entirely post-2026-01-08 |
| Category coverage | 100% of 453,372 traded markets; **79.9% of volume** named, 20.1% `other`, **0% unmapped** |

**Tests added this session: 262 real + 249 synthetic + 10 whale-variant = 521**,
BH-FDR corrected within families.

---

## RESULTS PROVENANCE

| Item | Value |
|---|---|
| Panel | 1,702,214 settled positions, 2,500 wallets, 677,721 tokens |
| Source | 14,082,296 wallet fills; 2,108,796-market universe |
| Unit of observation | **event** (game, or recurring series-day) |
| Date range | 2022-11-21 → 2026-04-28 (subgraph still stale ~3 months) |
| Selection A / B | before 2025-07-01 (223,315 rows) / before 2026-01-08 (685,088) |
| Measurement A / B | 1,478,899 / 1,017,126 rows, untouched |
| Specialists ≥50/70/90% | 1,799 / 1,224 / 723 wallets |
| Category volume | politics 30.9%, other 20.1%, crypto 19.7%, nba 12.9%, soccer 6.2%, nfl 4.9%, esports 3.6%, weather 1.7% |
| Seed | 20260801 throughout |

---

## NOW CLOSED

- Category ranking **does** beat whole-portfolio ranking — but only politics
  survives both cuts and all 42 specifications.
- Recency weighting is cosmetic (~0.2pp).
- Min-trade and cadence filters are real, worth ~0.7pp combined.
- The whale exclusion is immaterial; impact does not scale with size.
- The pipeline is not manufacturing edge: 0/249 synthetic vs 71/262 real.

## STILL OPEN

- **Task 5 unanswered** — 0.9% book coverage.
- Politics' *absolute* net (+2.4 to +3.9pp) rests on a 1.0pp spread floor that is
  a **lower bound**. At a true effective spread of 2pp+, politics is ~break-even.
- Whether politics survives a third, earlier cut. Two cuts is the minimum.
- `other` is 20.1% of volume and is a bucket, not a category. Decompose before
  trading it.

## NEXT THREE ACTIONS

1. **Targeted book pull for the 30 survivors' ~33k period-2 positions**, then
   re-run Task 5. Without it there is no latency answer, so no answer to "can
   this be followed by hand".
2. **Measure the true effective spread** by recording the CLOB book
   prospectively. Every net number hangs off a 1.0pp lower bound; this single
   measurement decides whether politics is +2.4pp or ~0.
3. **Re-run politics at a third cut, and decompose `other`.** Politics is the
   only candidate and deserves one more out-of-sample window before anyone acts.

---

## WHAT THE COORDINATING CHAT HAS WRONG — bluntly

1. **It asserted the latency curve is flat and reasoned from it.** Flat only
   unconditionally; for selected wallets the edge drops ~3pp in five minutes. The
   whale argument rested on a false premise and reached a defensible conclusion
   by luck.
2. **It implied the earlier study got sizing wrong.** It was already
   scale-invariant, equal-weight per signal. The critique targeted something that
   was not broken.
3. **It supplied numbers it could not source** — "~47 corrections", "8 dead
   positives", "1.81 effective series". None exists here. Mixing unsourced
   figures with sourced ones makes the sourced ones harder to trust.
4. **It framed the study as having asked "the wrong question".** Partly fair. But
   the win is one category of eight, worth ~+1.2pp over benchmark, resting on an
   unverified spread floor. The correct headline is "the earlier study asked too
   broad a question — **and the narrower question still mostly fails**".
5. **Its framing of the failure mode was right and is the most valuable thing it
   supplied.** The 7-day/7-day look-ahead example is exactly the error that made
   my first control report 54 false positives. Keep that. Repeat it.
