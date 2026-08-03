## Corrections

Claims this project published and later found to be wrong. Hand-written and
tracked in git, unlike `GITHUB_KNOWLEDGE.md`, which is generated — a correction
kept only in the generated file is reinstated by the next regeneration.
`build_knowledge.py` splices this section in verbatim.

---

### C1 — Kalshi does **not** charge makers and takers the same rate

*Raised 2026-08-03 by the user's own measurement. Verified here two ways.*

**What this project published (wrong):**

> Kalshi: `ceil_to_cent(0.07 × qty × p × (1−p))`, **same rate for makers and
> takers** (source: `evan-kolberg/prediction-market-backtesting` →
> `adapters/kalshi/fee_model.py:908`, modified 2026-03-11).

**What Kalshi actually charges**, from its own fee schedule —
`https://kalshi.com/docs/kalshi-fee-schedule.pdf`, *"Last updated and effective:
July 7, 2026"*, retrieved 2026-08-03:

| side | formula | default multiplier `M` |
|---|---|---|
| taker | `roundup(M × 0.07 × C × P × (1−P))` | **1** |
| maker | `roundup(M × 0.0175 × C × P × (1−P))` | **0** |

The maker rate is **0.0175 — exactly one quarter of the taker rate** — and its
multiplier defaults to **zero**, so on an ordinary series a resting order pays
nothing. The schedule says so in words as well as arithmetic: trading fees are
*"not charged for orders placed that are not immediately matched and are instead
left as resting orders on the orderbook unless they are included in our 'Maker
Fees' section."*

**Second, independent confirmation — the live API.** `/trade-api/v2/series`,
full pagination, 12,396 series, 2026-08-03:

| `fee_type` | series |
|---|---|
| `quadratic` — taker only | **12,266** |
| `quadratic_with_maker_fees` | **130** |
| *(of the 12,266)* `fee_multiplier == 0` — no fee at all | 14 |

The two sources agree, and both disagree with the third-party fee model that was
this project's only prior source.

**Where the 130 are:** Sports 107 · Economics 10 · Entertainment 7 ·
Financials 3 · **Crypto 2** · Science and Technology 1.

**One refinement to the correction as it was given to me.** The claim came with
"none of them crypto". Two of the 130 are: **`KXBTCMAX150`** and
**`KXBTCMAX125`** — both long-dated "will bitcoin reach $X" series, not the
15-minute or hourly BTC markets. The PDF's Non-Standard Fees table lists
`KXBTCMAX150` at Maker 1 / Taker 1 independently of the API. 269 of the 271
`Crypto` series are taker-only, so the substantive point — that the crypto
markets you would actually trade charge makers nothing — stands; the literal
"zero" does not.

**The part that matters most for this repo's own trading.** `KXATPMATCH` and
`KXWTAMATCH` — the ATP and WTA match series behind `kalshi-inplay-bot` and
`set1_overshoot` — are both in the 130, at Maker multiplier 1. So are the NFL,
NBA, MLB, NHL and college series. Kalshi charges makers on the sports series,
which are its flagship product: **107 of the 130 are Sports.**

**And they hold the liquidity — measured, not argued.** This is the question
that decides the strategy, so it was measured rather than left as an inference
from "Sports is the flagship product". All 130 maker-fee series plus a random
sample of 300 taker-only series, queried per series
(`src/kalshi_liquidity_survey.py`, seed 20260803):

| per series, open markets | maker-fee (n=130) | taker-only (n=300 sampled) |
|---|---|---|
| mean open volume | **1,812,418** | 16,627 |
| median open volume | 17,038 | 0 |
| mean open interest | **1,399,160** | 8,919 |
| series with any open volume | 78 of 130 (60%) | 86 of 300 (29%) |

Mann-Whitney on per-series open volume: **U = 28,065, z = 8.28, p ≈ 2e-16**
(tie-corrected; the zero-volume ties are numerous and shrink the standard
deviation to 1,034). The same test on open interest agrees: U = 28,207,
z = 8.42. Ratio of means 109× on volume, **157× on open interest**.

The rank statistic is the one to remember. Of the 430 surveyed series ordered by
open volume — a pool that is 30% maker-fee by construction, and 1.0% maker-fee in
the population — the **top 25 are all maker-fee**, and 45 of the top 50 are.
`KXSB` (53.0M), `KXMLB` (43.4M), `KXNBA` (19.7M) and **`KXATPMATCH` (13.4M)** head
the list.

Two caveats, stated because they are the ones that could overturn it. `volume` is
cumulative since a market opened, so long-dated season futures accumulate more
purely by age — but `open_interest` is a stock rather than a flow, is not
age-biased in the same way, and shows the same 157× gap. And the taker-only side
is a 300-series sample; the rank result does not depend on projecting it, which
is why it is reported instead of an extrapolated share of total volume.

**So: Kalshi charges makers on 1.0% of series and on essentially all of the
liquid ones.** "Makers pay nothing on 98.9% of series" is true and close to
useless.

**Consequence for the venue recommendation.** The report concluded that
maker-only two-sided quoting on Polymarket was *"the one strategy whose income is
not required to overcome a fee first"*. That rested on Kalshi charging makers the
full 0.07. It does not — Kalshi makers pay nothing on 98.9% of series by count —
so Kalshi is **not** excluded on fee grounds the way the report said — the
premise was wrong. But the conclusion survives the correction, for a reason the
report never gave: the Kalshi series that charge makers nothing are the ones with
no liquidity. Fee-free maker quoting on Kalshi is available and mostly
unquotable. **The rule that survives is: pick a series whose maker multiplier is
zero *and* which has a book.** On Kalshi those two conditions are close to
mutually exclusive.

**Canonical implementation:** `common/kalshi_fees.py`. It takes a `SeriesFees`
read from the API and refuses to guess — `maker_fee_order_cents()` has no default
argument for the series, because a caller that does not know the series' fee_type
does not know its maker fee. Do not reintroduce a hardcoded maker rate.

**Also recovered from the same document, and new to this project:** Kalshi
publishes a **perpetual futures** fee schedule — taker 12.0 bps at tier 0 falling
to 2.6 bps at ≥ $3,000M 30-day volume; maker 5.0 bps falling to 0.6 bps. A
separate product from event contracts and not otherwise covered here.

**Method note, which is the transferable part.** The wrong number came from a
1,094-star repo that scores well on every computed component of this project's
own rubric. It was a *secondary* source for a fact the exchange publishes
directly. A repo being rigorous about its own strategy says nothing about whether
it copied a venue constant correctly. Prefer the venue's own document; this one
was reachable all along.

> Shelf life: **fees expire in 3 months.** Re-verify after **2026-11-03**.
> Reproduce with `src/kalshi_fees_census.py`.

**Also closes part of HANDOFF §5.1.** That section recorded that `kalshi.com`
returned HTTP 429 to every request including its own fee-schedule PDF, so the fee
schedule was never read. It is reachable with a browser User-Agent and a retry —
the 429 is intermittent, not a block; it succeeded on the first attempt of a
patient retry loop. **The fee schedule has now been read.** The Kalshi *member
agreement* and the Polymarket *terms of use* still have not been, and the
automation claims still rest on developer documentation.
