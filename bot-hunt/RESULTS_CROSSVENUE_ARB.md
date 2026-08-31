# RESULTS — cross-venue arbitrage: the tape cannot answer this, and I can prove why

**2026-08-31.** Mailbox 023 job 1. A query over `bot-hunt/data/record.db`, no
live connection and no execution.

> ## ⚠ THE HEADLINE, BEFORE ANY NUMBERS
>
> **My first run said 1,292 executable arbitrages, median 3.47¢, best 92¢.**
> **It was wrong, and the correct answer is that this tape cannot measure
> cross-venue arbitrage at all** — because it never recorded the two venues at
> the same instant. **94 out of every 100 apparent crossings are the clock.**

---

## 1. The gate — how many genuinely equivalent pairs exist? (this part passed)

The instruction was right to demand this first. **Run totals dodge most of the
settlement-rule trap because both venues put the line in the identifier:**

| | |
|---|---|
| Kalshi | `KXMLBTOTAL-26AUG061805WSHPHI-9` → *"Over 8.5 runs scored"* |
| Polymarket | `mlb-wsh-phi-2026-08-06-total-8pt5`, outcomes Over / Under |

A pair matches only on **same two clubs + same date + same numeric line** —
three independent agreements, and a mismatch on any one drops the pair.

| | |
|---|---|
| Kalshi run-total rungs keyed | 4,261 |
| Polymarket run-total markets keyed | 1,079 |
| **matched pairs** | **969** |
| **distinct games** | **202** |
| dates covered | **27** (2026-08-05 → 2026-08-31) |
| pairs never quoted in the same cycle | 158 |

**Checked, not assumed: no doubleheaders.** All 365 date/club-pair combinations
have a single start time, so the key cannot silently collapse two games.

**And the two venues do track each other** — correlation **0.871** on paired
mid-prices, median difference **2.5¢**. The match is real.

## 2. ⚠ Why the answer is still "cannot measure"

**`cycle_id` is not one clock.** The recorder writes Kalshi first and Polymarket
later in the same cycle:

> **Median gap between the two venues inside one `cycle_id`: 6.5 minutes.
> p90 8.0. Maximum 23.8.**

Every "crossing" therefore compares a Kalshi price with a Polymarket price taken
**six and a half minutes later**.

### The placebo that settles it

Deliberately mis-align the two venues further and recount. **If crossings rise
with the offset, what is being measured is elapsed time, not disagreement.**

| Polymarket shifted by | approx gap | crossings |
|---|---|---|
| 0 cycles | **~6.5 min** | **125** |
| 1 cycle | ~19 min | 274 |
| 2 cycles | ~32 min | 451 |
| 4 cycles | ~58 min | 875 |

> **Crossings scale almost perfectly linearly with the time gap — correlation
> 0.9975, about 14.7 extra "arbitrages" per minute of skew.** Comparing prices an
> hour apart manufactures **seven times** as much free money as comparing them
> six minutes apart.
>
> **Extrapolated to a zero time gap: 7 crossings, against the 125 the tape
> shows. So at least 94 out of every 100 is the clock.**

**That is not a small correction. It is the whole result.**

## 3. What the corrected numbers look like, for completeness

**In-play observations were discarded** — 94% of the original hits. The biggest
were markets already decided: *"Over 20.5 runs"* with Kalshi bid 50 / ask 84
while **both** venues priced the over near 99. That 34-cent spread is a stale
limit order on a settled question, and the ask is **gone by the next cycle**.

*(`CLAUDE.md` §9b independently forbids in-play here: this repo's own bot was
measured reading scores after **97.4%** of the price move had already happened,
on 4,398 score-change events.)*

| pre-game only | |
|---|---|
| theoretical crossings | **125** on 75 pairs |
| gross margin, median / max | 1.00¢ / 25.00¢ |
| **fee to cross both venues, median** | **2.96¢** |
| after fees still positive | 44 of 125 |
| "executable" (net > 0, ≥10 contracts both legs) | **40** |
| **longest unbroken run, median** | **1 cycle** |
| **crossings gone after a single snapshot** | **37 of 44 — 84 out of 100** |

**Even taken at face value, 84 out of 100 existed in exactly one snapshot** —
and one snapshot is a comparison of two prices 6.5 minutes apart. **There is
nothing here to hit two legs against.**

## 4. ⚠ The fee finding, which stands on its own and corrects this repo

The instruction said establish the fees from primary sources rather than assume.
**Doing so overturned an assumption already in use here.**

| venue | taker fee | source |
|---|---|---|
| **Kalshi** | `roundup(0.07 × C × P × (1−P))` | `common/kalshi_fees.py`; schedule effective 2026-07-07 |
| **Polymarket** | **`C × 0.05 × p × (1−p)` on SPORTS** | [docs.polymarket.com/trading/fees](https://docs.polymarket.com/trading/fees), retrieved 2026-08-31 |

Polymarket's own words: *"Makers are never charged fees. Only takers pay fees."*
Their worked example: 100 shares at $0.50 costs **$1.25**.

> **This repo has treated Polymarket as free to trade. On sports it is not.**
> Both venues charge the *same quadratic shape* and differ only in the
> coefficient — 7% against 5% — so **a two-legged taker arbitrage pays
> 0.12 × p × (1−p), about 3 cents at a 50¢ price.** That is why a 1-cent
> theoretical crossing was never a trade, and it is the median crossing here.

## 5. What would have to change to answer the question properly

**This is the actionable part, and it belongs to whoever next touches the
recorder** (`factory` is widening it now — flagged to them in `STATUS.md`):

> **Sample Kalshi and Polymarket for the same market within seconds of each
> other, not within a cycle.** The current recorder walks venue by venue, so the
> two legs of any pair are minutes apart by construction. **No amount of
> additional recording at the current cadence can fix this** — it is the order of
> operations, not the volume.

A paired sampler over the ~200 games a day that both venues quote would cost a
few hundred requests a day against a recorded ceiling of 15 a second.

## 6. What this does NOT establish

`CLAUDE.md` §9c step 7.

- **Not that cross-venue arbitrage does not exist.** It says this tape cannot
  see it. The residual after removing the clock is ~7 crossings over 202 games,
  which is *consistent with zero* and equally consistent with a small real
  effect the instrument cannot resolve.
- **Settlement rules were never verified.** Neither tape records them. A
  suspended, shortened or rain-called game could resolve differently on the two
  venues, and **that risk is unpriced here.** Every candidate is reported as a
  price crossing, never as free money.
- **Only run totals, only MLB.** Game winners, tennis, esports and soccer all
  have recorded pairs and none was joined.
- **Pinnacle was not included** at all, though `pin_market` holds `max_risk` and
  would support a third leg.
- **Depth was read from the top of book plus the recorded size**, not by walking
  the full ladder. The size columns exist; `depth5` was not used per level.
