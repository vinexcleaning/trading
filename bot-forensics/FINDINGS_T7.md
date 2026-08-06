# Player features vs. the Kalshi opening price — 2,008 cells, and a clean null

Run 2026-08-06. Design fixed in advance in
[PREREGISTRATION_T6.md](PREREGISTRATION_T6.md), committed before any number
existed. Code: `src/t6_features.py`, `src/t7_sweep.py`. Output: `out/t6_*`,
`out/t7_*`.

---

## The short version

**The market's opening price already contains everything these features know.**
2,008 pre-registered cells; **2 survived BH-FDR at 5%**; the same machinery run
on *shuffled* data produces **4.1 on average**. The real data found **fewer
"discoveries" than its own null**, and a lower maximum t-statistic (4.17 against
a null average of 4.40).

The two survivors were both "buy the heavy favourite". They held their sign on
holdout — and then died on execution, because the entire effect lives in markets
whose opening book is too wide to trade.

---

## What was actually built

`markets.parquet` carries `player` for all 14,162 markets, which is what made
this possible without any external data. From it:

| | |
|---|---|
| events with a clean mirrored pair | **6,519** (4,563 train / 1,956 holdout) |
| features | recent form (last 3 / last 5), prior win rate, days rest, 7-day workload, experience, head-to-head, round, tier, opening price |
| leak rule | every feature uses **only matches whose `close_ts` < this match's `open_ts`** — enforced by a chronological pass that reads history *before* writing the current result into it |
| dedupe | **ticker order**, never volume (that is S011, which voided four phases) |
| target | **calibration residual** `outcome − implied`, not the win rate |

### The guards passed

| guard | reading |
|---|---|
| selection canary, P(kept side wins) | **0.5005**, n = 6,519, z = **+0.09** → PASS |
| market calibration at the open | **+0.0031** overall; every tier \|t\| < 1.2 |
| leak sanity, corr(prior winrate, residual) | **−0.0029** |

> **corr(prior win rate, *outcome*) is +0.0058 — essentially zero.** Over a
> 29-day window most players appear only a handful of times, so "recent form"
> here is mostly noise. That is a limitation of the window, not a finding about
> tennis, and it caps what any form-based feature could have shown.

---

## The sweep

**2,008 cells** = 7 tier groupings × 4 price bands × 10 features × 2 directions
× 4–5 thresholds, every cell with n ≥ 40, one BH-FDR denominator over all of it.

### BH-FDR at 5%: 2 discoveries, and the null produces more

| | BH discoveries | max \|t\| |
|---|---|---|
| **real data** | **2** | **4.17** |
| shuffled, 10 runs | mean **4.1**, max 16 | mean **4.40**, max 6.03 |

The permutation shuffles the outcome within **(tier × 5-cent price bin)**, so
calibration survives and only the feature link is destroyed. **A sweep that finds
less than its own null has found nothing.**

### The two survivors, and how they died

Both were `open_price >= 80` — buy the heavy favourite.

| | train | holdout |
|---|---|---|
| residual | **+4.31pp**, t = 4.17 | **+3.28pp**, t = 1.79 (same sign) |
| net at the **mid** | +3.12c | +2.04c |
| **net at the ask** | **+0.96c** | **−0.77c** |
| mean opening spread | 4.60c | **6.06c** |

### Why it is a quoting artifact, not an edge

Split the ≥80c cell by the width of its own opening book:

| opening spread | n | residual | t |
|---|---|---|---|
| **≤ 2c (tradeable)** | 255 | **+1.18pp** | **+0.64** |
| 2–4c | 292 | +4.87pp | +3.21 |
| 4–8c | 248 | +3.50pp | +1.87 |
| > 8c | 157 | **+7.92pp** | +3.92 |

**The effect is monotonic in spread width and vanishes on tight books.** A mid
quoted inside an 11.8-cent spread is not a price, it is the midpoint of an
absence of prices. The "mispricing" is the market not having formed an opinion
yet — and you cannot collect it, because crossing that spread costs more than
the residual is worth.

> Stated honestly: the tight-book cell has n = 255, residual +1.18pp, se 1.84pp,
> **95% CI [−2.42pp, +4.79pp]**, and a **minimum detectable effect of 5.15pp at
> 80% power**. It does not *exclude* a real effect — it is not powered to. It
> shows no evidence of one at a spread where one would be collectable, and an
> effect it could have detected would have had to be larger than the whole
> apparent edge in the wide-book cells.

### The naive benchmarks, which every cell must beat

Buy at the open, hold to settlement, exact Decimal fees:

| | at the mid | **at the ask** |
|---|---|---|
| all 6,519 events | −1.45c | **−4.14c** |
| favourites ≥50c | −0.23c | **−2.90c** |
| longshots <50c | −2.70c | **−5.42c** |

---

## ⚠ Two bugs in my own code, found and fixed mid-analysis

Both would have produced a false positive. Recorded because the repo's rule is
that catching your own error is worth more than the result.

**1. The first permutation null was broken and useless.** It shuffled outcomes
within *tier only*. Favourites genuinely win ~92%, so handing them the tier
average (~50%) manufactured a **−38pp** residual in every high-price cell that
had nothing to do with any feature. That null returned **1,010 "discoveries" out
of 2,008** and max \|t\| = 22. **The tell was that the null was wildly worse than
the real data** — a null should bracket it, not dwarf it. Fixed by stratifying on
price as well as tier.

**2. Entries were priced at the mid.** You cannot buy at the mid; a taker lifts
the ask. On these books that is 2–3c per contract — **larger than every effect in
the table**. Fixed; both columns are now reported side by side, and the gap
between them is exactly the size of the thing that looked like an edge.

---

## What could not be tested, and is not worked around

| the user asked about | status |
|---|---|
| **surface / "the floor"** | **NOT TESTABLE.** Kalshi's market records carry tier but no tournament name, so there is no join key to any surface source. `livetennisapi` has surface per tournament and it cannot be attached to these 6,519 events. |
| **serve %, double faults, aces** | **NOT AVAILABLE.** The free feed carries scores only — no match statistics. Would need the paid history plan, and the point-by-point tape may still not carry them. |
| **head-to-head** | **BUILT BUT USELESS.** Only **79 of 6,519 events (1.2%)** had a prior meeting inside the window. 29 days is not long enough for rematches. |
| **top-5 Challenger players' form** | The feature exists but rests on ~3 matches per player. See the +0.0058 correlation above. |

---

## Where this leaves the question

The user's premise — *aggregate efficiency does not imply efficiency in every
sub-population* — is correct, and it is the right question to have asked. It has
now been tested on the strongest pre-match feature set that this data supports,
with the analysis fixed in advance.

**The answer is that the opening price already knows.** Every apparent exception
traced back to the book being wide rather than the price being wrong.

This is the same shape as every other thread in this repo: **a real effect
smaller than the cost of reaching it.** It is now the ninth apparent positive to
die, and the 46th correction that shrank rather than grew an edge.

### One tension to flag rather than bury

`kalshi-market-scan` K009 says **the favourite-longshot bias does not exist on
Kalshi** (aggregate −0.67pp, 762 settled matches). This study finds **+4.31pp at
≥80c** on 691 train events. Those are not obviously compatible.

The reconciliation offered here — and it is a hypothesis, not a settled result —
is that **K009 measured traded prices while this measures the opening mid**, and
the spread table above shows the discrepancy is concentrated in the widest books,
where a mid is least meaningful. **On tight books this study reads +1.18pp,
t = 0.64, which is consistent with K009.** Recorded as an open item, with K009
treated as the better-supported number because it is measured where trades
actually happen.
