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
| **net at the ask** | **+0.96c** | **~~−0.77c~~ −0.374c** | ⚠ **CORRECTED 2026-09-01 to −0.374c** — the −0.770c charged `fee_order_cents(px, 1)`, the per-ORDER round-up, to orders of ONE contract in expectancy arithmetic; `common/kalshi_fees.py` names `fee_rate_cents` for exactly this case. Reproduced (n=261) then recomputed. **+0.396c of the old number was the rounding assumption, not economics.** The old figure is left visible per house rules. **B024 is unchanged** — still negative, and the cell's 6.06c mean spread is the killer, not the fee. Found by the `reopen` audit.
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

### ✅ The tension with K009 — RESOLVED, and K009 was right

Run after the above, as `src/t8_calibration.py`. The full calibration curve,
split by whether the opening book was tradeable:

| | price bands whose 95% CI excludes zero | pooled residual |
|---|---|---|
| **tradeable books (spread ≤ 2c)** | **0 of 10** | **+0.03pp**, se 1.09pp, t = **+0.03** |
| wide books (spread > 4c) | **2 of 10** | +0.60pp, se 0.75pp |
| all books | 2 of 10 | +0.31pp, se 0.53pp |

The two wide-book deviations are 40–50c at **−4.96pp** and 80–90c at
**+5.16pp** — the same heavy-favourite cell t7 flagged, and it is present *only*
where the book is wide.

> **Where Kalshi tennis is liquid, its opening price is calibrated across the
> entire price range from 1c to 99c.** K009's "the favourite-longshot bias does
> not exist on Kalshi" is confirmed on independent data by a different method,
> and t7's +4.31pp is fully explained as a wide-book quoting artifact.

Power caveat, stated plainly: each tight-book band holds only 114–208 events, so
a single band could hide a 5–12pp effect. The **pooled** tight-book number is the
well-powered one, and it is +0.03pp.

### The original tension, kept for the record

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

---

## Postscript — what the live feed adds, and the one thing worth buying

Run as `src/t9_upcoming.py`. Cached to `data/`, so re-runs cost 0 API calls.

**437 upcoming fixtures**, and — importantly — **`surface` is present on every
one**. Surface is unavailable *retrospectively* (no join key to Kalshi's market
records) but is available *prospectively*. **If fixtures are recorded from now
on, surface-conditioned analysis becomes possible in about a month.** That is a
recorder job, not an analysis job, and it is cheap.

| | |
|---|---|
| fixtures | 437 — ITF-M 98 · ITF-W 97 · Challenger 31 · ATP 25 · WTA 20 · rest doubles/teams |
| surfaces | hard 254 · clay 163 · grass 12 |
| both players inside the top 2,000 by ranking | 161 of 437 |
| player database | **30,951 ranked players**, 200 per call |

**The sheet is descriptive and is labelled as such in the script's own output.**
`p1_win_rank` is an unfitted logistic on the log-ranking gap, printed to make the
gap readable. It is not a price. Ranking is the most public information in
tennis; if computed form adds nothing to Kalshi's price (B023) and the price is
calibrated wherever it is liquid (B027), a ranking model adds less.

### The single highest-value unlock, and it costs $9.99

**Everything weak in this study traces to one cause: the corpus is 29 days
long.** Head-to-head reached only **1.2%** coverage. `corr(prior win rate,
outcome)` was **+0.0058** — indistinguishable from zero — because the median
player appears about three times.

`livetennisapi`'s history plan is **$9.99** and covers **43 monthly periods,
January 2023 to July 2026, point-by-point, including ITF.** That turns form and
head-to-head from noise into real features and would let this exact study be
re-run with 3 years of history instead of 4 weeks.

> **Stated against my own interest in a tidy conclusion:** this study is a null,
> and a null on a 29-day window is much weaker evidence than a null on three
> years. **B023 should be read as "not demonstrated on 29 days of form data",
> not as "player features cannot work."** The $9.99 would settle it properly.
>
> What it would *not* change is B027 — the calibration result stands on its own
> and does not depend on the window length.
