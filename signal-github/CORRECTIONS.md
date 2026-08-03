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

Whether the maker-fee series also hold most of Kalshi's *liquidity* is the
question that decides the strategy, and it is **not measured here**. A first
attempt aborted — paginating `/markets?status=open` spends its first 16,200 rows
inside a single 12,160-market exotics series (`KXMVESPORTSMULTIGAMEEXTENDED`), so
a capped scan reaches 7 series and answers nothing. Stated as the open question
it is rather than guessed at.

**Consequence for the venue recommendation.** The report concluded that
maker-only two-sided quoting on Polymarket was *"the one strategy whose income is
not required to overcome a fee first"*. That rested on Kalshi charging makers the
full 0.07. It does not — Kalshi makers pay nothing on 98.9% of series by count —
so Kalshi is **not** excluded on fee grounds the way the report said. The honest
version is narrower and more useful: **on either venue, pick a series whose maker
multiplier is zero.** On Kalshi that is 12,266 of 12,396 series, but it excludes
almost every liquid sports market.

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
