# HANDOFF — specialist wallet copy trading

Read-only public data, simulated fills only. No funded wallet, no order placement, nothing live.

**Location:** `C:\Users\gianf\trading\wallet-copy-study`
**Interpreter:** `C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe`
**Earlier sessions:** `HANDOFF_prior_sessions.md`

---

# 1. THE ANSWER

The edge and the money are two different questions, and they have two different answers.

**16 rolling 60-day out-of-sample windows.** Rank on everything prior, measure on the next 60 days, never overlapping.

| | Does the edge EXIST? | Can you HARVEST it? |
|---|---|---|
| Metric | per-position excess vs naive | bankroll return, 1% stake |
| Mean | **+2.117pp** | +5.1% |
| **Median** | **+1.711pp** | **−3.0%** |
| SD | 1.484 | 22.8 |
| Range | [−0.22, +5.32] | [−22.6%, +62.7%] |
| **Positive in** | **94% of windows (15/16)** | **31% of windows (5/16)** |
| Significant p<0.05 | 8 of 16 | — |

*Return column uses the **corrected** measured cost of 1.000pp (see §5 retraction). Excess is a relative measure and is unaffected by the cost assumption.*

> **Update (R11):** the harvest side is now worse than this table shows. The
> +0.300pp 10-second edge that made a bot arguable has been retracted as a
> liquidity-selection artifact — at 47.3% coverage it is **−1.957pp, p=0.0027**.
> **No latency budget works.** See §4.

**The edge is present in 94% of windows. The bankroll return is positive in 31%.**

Not a contradiction — it *is* the finding. The return distribution is severely right-skewed: a handful of windows (best +62.7%) carry the entire mean while most bleed slightly, and the worst loses 22.6%. You would lose money in roughly **two of every three 60-day periods**, punctuated by occasional large wins.

**This is a positive-expectation lottery, not an income stream.**

---

# 2. IS IT REAL? — controlled three ways, and yes

### Control A: the null (wallet labels permuted within each event)

| Category | Real mean | **Real % positive** | Real sig | Null mean | **Null % positive** | Null sig |
|---|---|---|---|---|---|---|
| **politics** | +2.117 | **94%** | **8** | −0.696 | **50%** | **0** |
| other | +0.899 | 75% | 0 | +0.239 | 44% | 0 |
| crypto | +1.020 | 73% | 4 | +2.461 | 46% | 2 |
| nba | +0.738 | 73% | 5 | +2.070 | 50% | 1 |
| soccer | +1.243 | 67% | 3 | −6.852 | 50% | 0 |

**The null lands at 44–50% positive in every category** — a coin flip, exactly as it must. The method does not manufacture edge. Politics at **94% against a 50% null** is the strongest result in this project.

*Read % positive, not the mean:* null means for crypto/nba are dragged positive by outlier windows; % positive is the robust statistic.

### Control B: the full specification grid (482 tests, BH-FDR)

Synthetic **0 of 249** significant vs real **71 of 262**. Politics positive in **36/36 specifications across three cuts** (medians +1.99 / +1.29 / +1.08).

### Control C: leave-one-out

| Dropped | 2025-01 | 2025-07 | fee era |
|---|---|---|---|
| *(base)* | +1.989 | +1.180 | +1.154 |
| largest **event** | +1.990 (+0.001) | +1.176 (−0.004) | +1.153 (−0.001) |
| **top-5 events** | +1.991 | +1.177 | +1.157 |
| largest **wallet** | +2.049 | +1.148 | +1.212 |
| largest **month** | +1.771 (−0.218) | +1.123 | +0.840 (−0.314) |
| largest **price band** | +2.162 | **+0.545 (−0.635)** | +1.278 |

**Not one election night** (dropping the biggest event moves it 0.001pp). **Not one wallet** (≤0.06pp, despite the top wallet being 48–86% of *notional* — the paired test weights events, not dollars).

### Control D: self-audit of my own ranking benchmark — CLEAN

Found by re-reading my code, not by a test failing: `rank_within_category` scores
wallets against a price-band benchmark **pooled across all categories**. If
politics at 0.80 behaves differently from crypto at 0.80, that would favour
wallets trading the divergent bands — a selection artifact dressed as skill.
(The *measurement* side was never at risk; the paired test compares within the
same events.)

Re-ranked using a **politics-only** benchmark across all 16 windows:

| | Mean | Median | % positive | SD |
|---|---|---|---|---|
| pooled benchmark | +2.117 | +1.711 | 93.8% | 1.484 |
| within-category | +2.066 | +1.621 | 93.8% | 1.523 |

**Identical in 14 of 16 windows**, top-decile overlap near-perfect (11/11, 8/8, 7/7…). Mean moves −0.051pp; % positive unchanged. **The concern was real and the answer is no.**

### Control E: is the edge concentrated in one price band? — NO

The 2025-07 cut collapsed when its top band was dropped. Across all 16 windows, split by band:

| Band | Windows | Mean | Median | % positive |
|---|---|---|---|---|
| 0.00–0.10 | 16 | +0.216 | +0.096 | 62% |
| 0.10–0.25 | 16 | +0.331 | +0.432 | 69% |
| 0.25–0.40 | 16 | +1.050 | +1.239 | 69% |
| 0.40–0.60 | 16 | +0.666 | +0.499 | 62% |
| 0.60–0.75 | 15 | +1.347 | +1.823 | 73% |
| **0.75–0.90** | 14 | +0.998 | +0.700 | **93%** |
| 0.90–1.00 | 13 | +0.891 | +0.722 | 77% |

**Positive in every one of seven bands**, 62–93% of windows each. No band is load-bearing — the single-cut fragility was noise. This also rules out the edge being favourite-longshot bias in disguise: it is present at longshot prices too.

---

# 3. SPECIALIST vs GENERALIST

`F6_min20_all`, unweighted. Unit = **event**. Net uses the **corrected measured**
cost of 1.000pp at $200 (§5) — an earlier version of this table used 0.675pp and
was 0.325pp too generous throughout.

| Cut | Category | Copier gross | Net | Naive | **Excess** | CI95 | p | BH | n_ev | n_eff | Generalist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07 | **politics** | +3.387 | **+2.39** | −0.428 | **+1.180** | [0.37, 2.00] | 0.006 | **yes** | 3,360 | 2,337 | +0.937 |
| 2025-07 | other | +0.907 | **−0.09** | −1.649 | +1.342 | [0.47, 2.26] | 0.005 | **yes** | 3,644 | 2,927 | +0.937 |
| fee era | **politics** | +4.946 | **+3.95** | −0.299 | +1.154 | [−0.12, 2.57] | 0.073 | no | 1,190 | 1,076 | −0.135 |
| fee era | **soccer** | +3.582 | **+2.58** | −1.767 | **+3.464** | [1.66, 5.25] | 0.001 | **yes** | 928 | 743 | −0.135 |
| fee era | crypto | +1.433 | **+0.43** | −2.222 | **+2.052** | [0.48, 3.60] | 0.010 | **yes** | 818 | **131** | −0.135 |
| fee era | nba | −4.113 | −5.11 | −1.385 | −2.428 | [−9.51, 4.47] | 0.483 | no | 134 | 95 | −0.135 |

*These are the wallets' own entry prices net of cost — i.e. an upper bound. What a
copier gets at a reachable latency is §4, and it is much smaller.*

**Specialists beat the generalist (+0.937 / −0.135pp), and politics is the only category robust across all three cuts.** Soccer flips sign between cuts; crypto and `other` work at one cut and fail the other.

### Filters: what mattered

| Filter | Specs | BH sig | Median excess | Median wallets |
|---|---|---|---|---|
| F0 min10 | 48 | 12 | +0.646 | 387 |
| F2 min50 | 39 | 9 | +0.955 | 135 |
| **F4 min20+cadence** | 32 | 12 | **+1.345** | 61 |
| F6 all | 24 | 10 | +1.268 | 76 |

- **Min trades/events MATTERED**, monotonically (+0.65 → +0.85 → +0.96).
- **Recency + cadence MATTERED MOST** (+0.85 → +1.12 → +1.35). Largest gain in the grid.
- **Non-MM filter COSMETIC.** **Recency weighting COSMETIC** (hl30d +1.121 / hl90d +1.014 / unweighted +0.940 — inside noise). *The brief expected this to matter. It does not.*
- **Tension:** ≥20 trades/category selects the high-frequency wallets the MM fingerprint then removes.

---

# 4. LATENCY — **NO WORKABLE BUDGET EXISTS.** The +0.300pp was a liquidity artifact.

**RETRACTED (R11).** The +0.300pp at 10 seconds — the last surviving positive in
this project — does not survive higher coverage. It came from a **balanced panel
selected on liquidity**.

### The control that killed it

The balanced panel required a print at *every* delay including **1800s**.
Requiring a trade to exist half an hour later selects for liquid tokens. Tested
directly, at a fixed 10-second delay:

| 10s delay, split by whether a 1800s print exists | Gross | CI95 | Events |
|---|---|---|---|
| **WITH** a 1800s print (i.e. kept by the old panel) | **+1.265pp** | [0.194, 2.347] | 3,345 |
| **WITHOUT** (i.e. discarded) | **−2.318pp** | [−3.117, −1.580] | 1,455 |
| **Difference** | **3.583pp** | **CIs disjoint** | |

**The old panel kept the liquid half, where the edge is, and threw away the
illiquid half, which is strongly negative.**

### What happens as coverage rises

| Panel | Coverage | **10s net** | p | 60s net | 300s net |
|---|---|---|---|---|---|
| balanced incl. 1800s *(old headline)* | 16.1% | **+0.300** | 0.029 | −0.214 | −0.670 |
| balanced through 300s | **31.1%** | **−1.165** | 0.676 | −1.653 | −1.947 |
| per-delay, max coverage | **47.3%** | **−1.957** | **0.0027** | **−2.299** | **−1.932** |

At 47.3% coverage the 10-second net return is **−1.957pp, significantly
negative** (p=0.0027). So are 60s (−2.299pp, p=0.0007) and 300s (−1.932pp,
p=0.0053).

**Third time more coverage has killed a Task 5 number (0.9% → 11.2% → 16.1% →
47.3%), third time in the same direction. I predicted this in the last handoff.**

*Caveat that cuts both ways:* effective sample size collapses in the wider panels
— n_eff 2,079 at 16.1%, but **268** at 31.1% and **196** at 47.3%, because the
added positions cluster into few events. The wider panels rest on ~200 effective
observations, not 15,857 independent draws. The direction is consistent and
significant; the precision is weaker than the nominal n suggests.

### Per-wallet, at the wider panel

**22 wallets** now clear the 30-event floor (was 9). Net-positive at 10s:
**9 of 22**. At 300s: **5 of 22**. Under half, at the shortest reachable delay.

**A pull of the 16,033 entirely-missing token books is running now** and will
take coverage toward its 69.7% ceiling. Given three consistent moves in the same
direction, I expect it to confirm this, not reverse it.

---

# 4b. The superseded version, retained for the record

Two targeted pulls this session: **11,645 tokens, +24.5M fills**. Coverage
0.9% → 11.2% → **16.1%** (5,405 positions, **3,322 events, n_eff 2,079**,
balanced panel).

**I predicted on the record that more coverage would make this worse. It did.**

| Delay | Gross @11.2% | **Gross @16.1%** | **Net (1.000pp)** | CI95 gross | p |
|---|---|---|---|---|---|
| **0s** *(not reachable)* | +4.651 | **+3.935** | +2.935 | [2.72, 5.09] | 0.0007 |
| **10s** | +2.014 | **+1.300** | **+0.300** | [0.10, 2.38] | **0.029** |
| **60s** | +1.357 | **+0.785** | **−0.215** | [−0.41, 1.88] | 0.188 |
| 300s | +0.721 | +0.330 | −0.670 | [−0.83, 1.37] | 0.589 |
| 1800s | −0.125 | **−0.423** | −1.423 | [−1.41, 0.51] | 0.349 |

**At 60 seconds the net edge is now NEGATIVE (−0.215pp) and not significant.**
The usable latency budget has collapsed from ~60s to **~10 seconds**, and even
there it is only +0.300pp net.

**⚠ The 0s row is not an opportunity.** In **55.5%** of positions the "price at
0s" *is the wallet's own trade* (median gap: 0 seconds). It restates their edge;
it is not a price you can reach.

**0 of 17 reportable wallets survive 30 minutes. BH-FDR: 0 of 17 significant.**

A clean illustration of why coverage mattered — one wallet across three coverage
levels:

| `0xed2c371514..` | 8.8% cov (n=133) | 11.2% (n=187) | **16.1% (n=438)** |
|---|---|---|---|
| d1800 gross | +9.94 | +5.71 | **−1.65** |
| verdict | "followable" | near-miss | **negative** |

It inverted entirely as evidence accumulated. At 8.8% coverage I would have
reported it as the one wallet you could follow by hand.

**No wallet can be followed by hand from a phone alert.**

*Units:* `pp` is percentage points of $1 face value, not return on cash. At a mean entry of ~0.65, the **+0.300pp at 10s is ~+0.46% on capital deployed**, per position, with cash locked until the market resolves. That is the honest headline number for a copier — not the +4% the 0s row appears to offer.

---

# 5. THE SPREAD — measured, converged, and SETTLED

**The recorder completed its full run: 420 cycles, 7.0 hours, 4,600 tokens,
1,797,426 two-sided snapshots at 10 levels/side, 0 malformed, 834 MB.**

### The measurement has converged

| Politics cost | 1 hour (231k snaps) | **7 hours (1.80M snaps)** |
|---|---|---|
| $50 | 0.600 | **0.600** |
| **$200** | 1.000 | **1.000** |
| $500 | 1.163 | **1.163** |
| $1,000 | 1.573 | **1.577** |
| $5,000 | 2.149 | **2.160** |
| $500 unfillable | 17.6% | **17.4%** |

**Eight times the data moved every figure by less than 0.01pp.** This number is
settled: a copier buying $200 of a politics market pays **1.000pp above mid**.
The project's original 1.0pp assumption — carried for weeks as a guess — was
exactly right.

This closes the question the whole session was built around. **No further
revision to the net figures is required.**

### ⚠ RETRACTION — "the spread is better than assumed" was depth survivorship

I first measured with **3 levels** and reported politics at **0.675pp for a $200
order**, concluding the project's 1.0pp haircut had been too harsh and the net
edge roughly doubled. **Wrong.** With only 3 levels, orders that could not fill
were *excluded* — and the excluded ones were the thin, expensive books (45.5%
unfillable at $500). At **10 levels** those fill, at higher cost:

| Size | 3 levels (wrong) | **10 levels (correct)** |
|---|---|---|
| $50 | 0.500 | **0.600** |
| **$200** | 0.675 | **1.000** |
| $500 | 0.892 | **1.163** |
| $1,000 | 0.936 | **1.573** |
| $5,000 | 1.173 | **2.149** |

**The original 1.0pp assumption was almost exactly right at $200, and too
generous above it.** Same pattern as every other correction in this project:
more data, worse answer.

### Final effective cost by category (7h, 10 levels, pp above mid)

| Category | Snapshots | Full spread | Half | $50 | $200 | $500 | $1,000 | $5,000 | $500 unfillable |
|---|---|---|---|---|---|---|---|---|---|
| **politics** | 586,760 | **1.000** | **0.500** | 0.600 | **1.000** | 1.163 | 1.577 | 2.160 | 17.4% |
| nfl | 123,260 | 2.000 | 1.000 | 1.000 | 1.261 | 1.627 | 2.094 | 2.624 | 14.6% |
| other | 289,758 | 2.000 | 1.000 | 1.332 | 1.763 | 1.747 | 1.634 | 2.304 | 34.3% |
| crypto | 292,928 | 2.300 | 1.150 | 1.871 | 2.500 | 2.861 | 3.117 | 4.607 | 32.6% |
| nba | 133,010 | 5.000 | 2.500 | 2.490 | 2.500 | 2.808 | 2.926 | 4.795 | 29.6% |
| soccer | 191,744 | 27.700 | 13.850 | 7.784 | 3.000 | 1.490 | 1.200 | 1.222 | 55.8% |
| esports | 96,090 | 8.000 | 4.000 | 4.410 | 4.216 | 2.437 | 2.193 | 2.103 | 69.3% |
| weather | 83,876 | 5.000 | 2.500 | 4.500 | 7.318 | 3.962 | 3.467 | 1.888 | 51.1% |

**Politics is the tightest book on the venue** — 1 tick, and 2.5× cheaper than
crypto at $200. That is the one genuinely favourable structural fact this project
found, and it is why politics is the only category where a ~1pp edge is even
arguable.

**Even at 10 levels, 17.4% of $500 politics orders don't fill**, so the $500+
column remains optimistic. Size above ~$200 is not supported by this book.

### Consequence for sizing

Re-running the sweep with the corrected 1.000pp cost: **only 1 of 12
configurations is positive in all three windows** (down from 5 of 12), and that
one takes just 135 trades across three windows — noise. **At honest costs,
essentially no sizing configuration reliably harvests the edge.**

---

# 6. SIZING — capital scheduling, not edge, is what kills you

12 configurations × 3 windows. **8 of 36 window-runs lose money; the worst loses 82%.**

At the **corrected** 1.000pp cost:

| Stake | Cap | 2025-01 | 2025-07 | fee era | Worst | All + ? |
|---|---|---|---|---|---|---|
| 0.5% | 50% | +40.7% | −1.9% | +39.3% | −1.9% | no |
| 1.0% | 100% | +81.5% | −3.7% | +78.5% | −3.7% | no |
| 1.0% | 50% | +81.3% | **−38.8%** | +17.2% | −38.8% | no |
| 2.0% | 100% | +155.8% | **−58.9%** | +34.4% | −58.9% | no |
| 5.0% | 25% | +22.3% | +113.1% | +7.7% | +7.7% | *yes (135 trades)* |
| 5.0% | 100% | **−75.0%** | −17.1% | +20.7% | −75.0% | no |

**11 of 12 configurations fail.** The single survivor takes 135 trades across
three windows and is noise. At the earlier (wrong) 0.675pp cost, 5 of 12 passed —
that apparent robustness was an artifact of understating the spread.

**I am not recommending any configuration.** Moving the stake 1%→2% at the same
cap flips a window from −3.7% to −58.9%. An outcome that sensitive to a parameter
is not driven by the edge — and picking whichever config was positive on the
three windows I measured is selecting a parameter on the evaluation data, the
same error one level up.

**The sweep's real finding is its own instability.** With a 2% stake, peak
exposure hit **$22,000 against a $10,000 bankroll**.

---

# 7. WHALE EXCLUSION — immaterial, not wrong

Price impact does **not** scale with size across 13.5M fills: the **$10,000+** bin moves price **less** (−0.297pp) than the $0–100 bin (−0.371pp). The ~−0.3pp common to every row is bid-ask bounce, and it reverts. Putting whales back leaves politics/crypto/soccer/other **byte-identical**; only nba shifts. **Keep it or drop it — it does not matter.**

---

# 8. RETRACTIONS

**R11. The +0.300pp 10-second edge — the project's last surviving positive.**
Killed by a liquidity-selection control. The balanced panel required a print at
1800s, which kept liquid tokens (**+1.265pp** at 10s) and discarded illiquid ones
(**−2.318pp**); CIs disjoint, difference 3.583pp. At 47.3% coverage the
10-second net return is **−1.957pp, p=0.0027**. **There is no latency at which
copying these wallets is profitable.** Predicted in the previous handoff.

**R0. My own interim Task 5 reading, killed twice by more data — as predicted.**
At 8.8% coverage: +0.98pp gross at 30 min, **1 followable wallet**. At 11.2%:
**−0.125pp**, 0 followable. At **16.1%: −0.423pp**, and the 60-second net edge
turned **negative**. I put the prediction on the record before running the
top-up; it was confirmed both times. **83.9% of positions remain uncovered and
the trend has been monotonic — assume the true numbers are worse still.**

**R0b. "The spread is better than assumed" — retracted, it was depth
survivorship.** Measured with 3 book levels I reported politics at **0.675pp for
$200** and said the net edge roughly doubled. With 10 levels it is **1.000pp** —
because 3 levels silently *excluded* the 45.5% of orders that could not fill, and
those were the thin, expensive books. The original 1.0pp assumption was right.
Knock-on: the sizing sweep went from **5 of 12 configurations viable to 1 of 12**,
and that survivor has 135 trades. **The apparent robustness was an artifact of
understating the spread.**

**R1. My "untradeable P&L" claim, corrected an hour later.** I read a −60% simulation as the edge failing. Wrong: the same signals **without** the capital constraint gave **+36.3%**. It was cash scheduling, not edge.

**R2. "`other_residual` is a second winner" — withdrawn.** Inspection shows it is `will-zelenskyy-wear-a-suit`, `will-elon-tweet` (4,137 markets), Mike Tyson/Jake Paul novelty markets. A **grab bag of novelty markets**, not a category. *(Also: that slug listing characterises the original `other` bucket, not the post-decomposition residual — my script's label was wrong.)*

**R3. "Edge doesn't decay with latency" — FALSE**, now measured directly on survivors: **+4.651 → −0.125pp**. True only unconditionally.

**R4. My synthetic control was wrong twice**; its sanity check caught both. v1 per-token Bernoulli → +3.94pp (YES/NO complementarity violated). v2 per-market weighted → +1.04pp (vwap is volume-weighted, positions are not). v3 (used): permute wallet labels within events.

**R5. My first registered hypothesis was wrong and it mattered.** Testing copier return against **zero** gave **54 of 206 "significant"** in the null. The paired copier-vs-naive test gave **0 of 249**. Same error that produced the original +7.05pp finding.

**R6. A bug gutted the control.** `mm` is a per-position copy of a per-wallet flag; under permutation it travelled with the position. Fixed to read the wallet-level file; both runs redone.

**R7. The windowed-pull "optimisation" made things worse** (235 → 627 min ETA) — timestamp predicates on `_in` queries make graph-node scan more. Reverted.

**R8. "Sizing wasn't proportional" — PARTLY FALSE.** Already per-share, equal-weight per position = a fixed fraction of bankroll per signal.

**R9. Repo provenance lost.** The project moved into the `trading` repo; **16 commits of history are unreachable.** Data intact.

**R10. Unsourced premises** ("~47 corrections", "1.81 effective series") have no artefact here. Methods adopted; numbers not verified.

---

# 9. CONTROLS

| Control | Result |
|---|---|
| Null, rolling windows | **44–50% positive in every category** (chance) vs 94% politics |
| Null, specification grid | **0 of 249** vs **71 of 262** real |
| Look-ahead assertions | **PASS** every cut, every mode; raises rather than warns |
| Selection-audit canary | **PASS** — pooled excess −0.0pp |
| Test suite | **32 passed** |
| Balanced panel | Enforced — n constant across all delays |
| Pull/analysis alignment | Window and `MAX_LOOKAHEAD` both 3600s |
| Category coverage | 100% of 453,372 markets; **79.9% of volume** named; **0% unmapped** |

**Tests this session: 262 + 249 + 220 + 17 + 10 + rolling = 750+**, BH-FDR within families.

---

# 10. STILL OPEN → NEXT THREE

**~~1. Measure the spread.~~ DONE and CLOSED.** 7h / 1.8M snapshots, converged.
Politics = 1.000pp at $200. This was the #1 open item for the entire project and
it is now settled.

1. **Task 5 coverage is 16.1%.** The trend across 8.8% → 11.2% → 16.1% has been
   monotonically worse and the 60-second net edge has already gone negative.
   Pushing toward ~40% is the cheapest way to find out whether even the
   10-second budget (+0.300pp) survives. **My expectation: it does not.**
2. **Month-sensitivity** is the last untested crack. Price-band fragility is
   closed (Control E) and the ranking-benchmark concern is closed (Control D).
   Dropping the largest month still costs up to 0.31pp at a single cut and has
   not been re-tested at rolling scale.
3. **Decide whether to stop.** Every measurement this session moved the answer
   the same direction: down. The edge is real and controlled five ways; the
   harvestable remainder is ~+0.30pp net at a 10-second latency that requires a
   bot, in one category, profitable in 31% of 60-day windows. A further round of
   work is more likely to close this than open it.

**Nothing is running.** All background jobs complete: recorder (420 cycles, 7.0h,
1.8M snapshots, 834 MB in `data/book_recording_deep/`) and the Task 5 top-up
(+13.27M fills).

---

# 11. WHAT THE COORDINATING CHAT HAS WRONG

1. **"If 30 minutes late costs nothing, impact may not be eating the copier."** 30 minutes late costs **everything** (+4.65 → −0.13pp). Impact indeed isn't eating the copier — reached *despite* the reasoning, not because of it.
2. **"A wallet surviving 30 minutes could be followed by phone."** Right in principle; **there are none.**
3. **Unsourced numbers** mixed with sourced ones corrode both.
4. **"Specialists" was worth doing** — politics is real, 94% of windows, against a 50% null. But it is one category of eight, ~+1.2pp, with a ~10-second latency budget, and **profitable in only 31% of 60-day windows**.
5. **The honest headline:** *the narrower question found something real, and it is harder to harvest than any headline number suggests.*
6. **Its look-ahead framing remains the most valuable thing it supplied** — exactly the error that made my first control report 54 false positives.
