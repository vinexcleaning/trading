# MORNING_REPORT.md

## ★ HEADLINE (Phase 2, 2026-08-01) — the Kalshi mid wins. Crypto pricing is closed.

**No model beats Kalshi's own mid price. Two tie with it, two lose to it. The
crypto ladder is efficiently priced at the horizons and strikes where it is
quotable, and this line of inquiry is retired.**

Panel: **250 events, 89,806 market-minutes, 1,968 markets, 10 ISO weeks,
2026-05-25 → 2026-07-30.** Unit of observation is the **event**; every CI below
resamples events, never rows.

| model | Brier | mid's Brier | diff | 95% CI (event-clustered) | p | verdict |
|---|---|---|---|---|---|---|
| M1 driftless GBM | 0.120431 | 0.119733 | +0.000261 | [−0.00157, +0.00219] | 0.781 | tie |
| **M2 settlement-aware** | 0.120091 | 0.119733 | **−0.000081** | [−0.00188, +0.00182] | 0.942 | **tie** |
| M3 empirical fat-tail | 0.123043 | 0.119733 | +0.003703 | [+0.00150, +0.00600] | 0.001 | **MID** |
| M3t Student-t ν=2.03 | 0.143255 | 0.119733 | +0.022455 | [+0.01865, +0.02637] | <0.0001 | **MID** |

*(diff = Brier_model − Brier_mid; negative = model beats mid)*

Log loss agrees: **mid 0.3766**, best model (M2) 0.3817. The mid wins on both
scoring rules.

**The best model in the project ties the market to four decimal places and
cannot beat it.** Per `docs/GO_NO_GO.md`, this is a NO-GO, and **Task 5 (the
strategy sweep) was not run** — sweeping exit rules over a signal with no edge is
how this project has previously produced strategies that die live.

### Two secondary results that are worth as much as the headline

**1. M2 beats M1 — the settlement-average physics is real and measurable.**
diff −0.000342, CI **[−0.000436, −0.000242]**, excluding zero. Kalshi settles on
a 60-second *average*, so the terminal variable is less variable than a point
sample and correct prices sit further from 50¢. Predicted by construction in the
pre-registration, and confirmed. This is the one place a model demonstrably
improved on another — it just isn't enough to catch the market.

**2. M3 (fat tails) makes things WORSE**, not better: +0.003703 against the mid,
and −0.003784 against M2, both CIs excluding zero. **This retires `C9-econ` on
evidence rather than on my earlier benchmark-inflation argument alone.** Kalshi's
mid is *not* pricing the wings with a Gaussian; feeding it a fatter tail than it
already uses actively degrades the forecast. The fat tails are real (`C9`); the
market already knows.

### The one candidate that appeared, and why it died

The raw reliability table showed the mid's empirical rate exceeding its implied
probability by up to **+4.2pp** in the 5–65% band — which at face value is a
large, tradeable edge against a ~1.3¢ cost bar.

**It does not survive event clustering.** Re-tested with the bootstrap
resampling events rather than rows, the CIs widen by roughly **10×** — exactly
the pseudo-replication factor implied by ~360 correlated minutes per event — and
14 of 17 buckets become indistinguishable from zero:

| mid bucket | raw gap | event-clustered 95% CI | p | buy-at-ask NET of fee |
|---|---|---|---|---|
| 0.00–0.05 | +0.0287 | [+0.0031, +0.0580] | 0.027 | **−0.0035** |
| 0.05–0.10 | +0.0357 | [+0.0034, +0.0712] | 0.029 | +0.0100 |
| 0.30–0.35 | +0.0388 | [−0.0162, +0.0936] | 0.146 | — |
| 0.90–1.00 | −0.0389 | [−0.0696, −0.0104] | 0.004 | −0.0004 |

Only **one** bucket (5–10¢) is both nominally significant and net-positive after
the fee. Across the 17 buckets tested, Benjamini–Hochberg requires p ≤ 0.0059 at
its rank; the observed p is **0.029**. **Nothing survives correction**, even
within its own family, let alone across the cumulative ledger.

Stability confirms it: signs agree across the two disjoint halves in 16 of 17
buckets, but **no bucket has a CI excluding zero in both halves**, and the
magnitudes roughly halve from the first half to the second (5–10¢: +0.052 →
+0.020) — the signature of a statistic decaying toward zero as n grows.

**And the same statistic had the opposite sign on the 13-event dry run**
(longshots *over*priced). I declined to report it then specifically because 13
events cannot support it. That call was correct: the sign flipped with more
data.

### Localisation — inconsistent, and it fails the pre-registered criterion

M2 beats the mid in two buckets (time-to-expiry 0–10 min, diff −0.005179; and
near-money |ln(S/K)/σ√τ| < 0.5, diff −0.005522), but the mid beats M2 at 20–30
min, and the two-period split **flips sign between halves** for both M1 and M2
(first half −0.0014, second half +0.0009). That fails GO_NO_GO criterion 4
(consistency across two disjoint periods). Per pre-registration a diffuse,
sign-flipping advantage is treated as a leak, not an edge.

---

Session start: 2026-07-31 ~19:30 ET. Machine: **laptop** (`C:\Users\gianf`).
Project root: `C:\Users\gianf\crypto\`. Status: **Phase 0 complete on the two
decisive questions.** No strategy results yet — do not read a verdict into this
file until §2 is filled in.

---

## 0000. PHASE 2 STRUCTURAL FINDING — the "cheap wings" are not quotable

The brief reasons that "wing asks run 1–22¢, so fees there are roughly a third
of their at-the-money value — if any advantage exists, the wings are where it
survives costs." That is true about the *fee* and false about the *market*.

Measured on a full 60-strike `KXBTCD` ladder, per-minute over the final hour:

| \|K − settle\| | strikes | minutes with a two-sided quote |
|---|---|---|
| $107 | 1 | 56 of 61 |
| $393 | 1 | 40 of 61 |
| $607 | 1 | 39 of 61 |
| **≥ $893** | **11** | **0 of 61, every one** |

The wings have an **ask but no bid**. They are not cheap — they are *one-sided*.
Three consequences, and the first is fatal to the intended test:

1. **Where there is no two-sided quote there is no mid**, so the pre-registered
   benchmark does not exist there. Those rows cannot be scored against the mid
   at all, and back-filling a synthetic mid would be benchmark inflation by
   construction.
2. **You cannot exit a wing position by selling** — there is no bid to hit. A
   wing trade is structurally hold-to-settlement, which changes the fee
   arithmetic (one fee, not two) but removes all optionality.
3. The `C9` fat-tail result therefore **cannot be monetised in the wings the way
   the brief anticipated**, independent of whether the tails are fat. This is
   the same conclusion the `C9-econ` withdrawal reached, arrived at from
   market structure rather than from the benchmark error.

**Refinement, so this is not overstated.** The figure above describes the *whole*
ladder. Selecting the 8 strikes nearest the **anchor** (the previous event's
settlement, knowable at open) lands on the liquid core and retains **~78%** of
candles as two-sided. So the tradeable band is dense and testable; it is the far
wings that are unquotable. The B1 panel is built on that band.

---

## 000. PREMISE DISPROVED — the Deribit-vs-Kalshi comparison cannot be run on the crypto ladders

The Phase 1 brief states the comparison "gives a market price and a
theoretically correct price for the same event, over a real sample, with no live
recording needed." **The reference-price half of that is not available at
Kalshi's horizons.** Checked before building, not after.

### The binding constraint: a 54× horizon gap

| | value |
|---|---|
| Deribit's **shortest usable** expiry after quality filtering | **54.2 h** |
| Kalshi `KXBTC`/`KXBTCD` contract lifetime, median | **1.0 h** |
| Kalshi contracts with lifetime ≥ 54 h | **0.1%** |

Deribit *lists* 6.17 h and 30.17 h expiries, but both are dropped by the chain
filters — 12 one-sided quotes and 9 uninvertible at 6 h, leaving 1 usable strike
against a minimum of 8. They exist but are too illiquid to define a curve. The
same holds for ETH.

So pricing a 1-hour Kalshi contract off Deribit means extrapolating a 54-hour
surface down by a factor of ~54. At that ratio the answer is dominated by
intraday volatility seasonality, which a 54-hour surface cannot see. The brief
anticipated this risk ("interpolating down to a 1-hour horizon is an
extrapolation, not an interpolation") and directed using the daily series as the
primary test — but `KXBTCD` is **hourly**, not daily, despite the name: its
events close every hour and its median contract lifetime is also 1.0 h.

**Verdict: the headline Deribit-vs-Kalshi test is not executable on the hourly
ladders, and no amount of recording changes that.** It is a property of Deribit's
listed expiries, not of our data.

### A second premise failed, then recovered

Settled Kalshi records do **not** retain a decision-time quote: across 60,000
settled `KXBTC` markets, **100%** of `yes_bid` and `yes_ask` sit at the 0/1
extremes, and only 0.0–0.4% of any price field falls between 5¢ and 95¢. They
are post-settlement degenerate quotes (bid 0, ask 1), not prices anyone traded
at. The 291,840-market settled history alone cannot support a vs-mid comparison.

**But this one is recoverable.** Kalshi exposes
`/series/{s}/markets/{ticker}/candlesticks`, which returns per-minute
`yes_bid`/`yes_ask` OHLC for settled markets over the full 68-day history. The
market-price side of any vs-mid test is therefore available; it just is not in
the `/markets` records. This is now the path for `B1`.

### Reprioritisation

1. **Task 3 (Deribit comparison) is cancelled for the hourly ladders** and
   logged as `X4` in the ledger. The only viable remnant: `KXBTC` weekly events
   (lifetime up to 169 h, the 0.1%) do overlap Deribit's usable range. That is a
   real but small test and it needs candlestick quotes, not settled records.
2. **Task 4 (fat tails) is promoted** — it needs only `expiration_value` and is
   fully executable on the 68-day sample now.
3. `B1` (vs-mid) is unblocked by the candlesticks endpoint and no longer depends
   on days of recording.

**Nothing below was built on the disproved premise.** The Deribit pricer itself
(Task 2) is complete and validated, and remains correct and useful — it is the
*joining* of it to hourly Kalshi contracts that fails.

---

## 00. RETRACTION (2026-08-01, Phase 1 Task 1) — Polymarket is ~2.9× MORE expensive than Kalshi for takers

**This reverses §0.1 below and the headline of `docs/venue_comparison.md`.** Both
are corrected in place; this section records what was wrong and why.

**What I reported in Phase 0:** Polymarket's crypto taker fee is
`0.07 × p × (1−p)` — identical to Kalshi. Source: published documentation,
corroborated by two independent secondary sources. I flagged the API's
`taker_base_fee: 1000` as unreconciled and marked it the top open item.

**What the on-chain fills actually show.** The documented formula is wrong in
both **rate and shape**:

```
economic fee per share ($) = (feeRateBps / 10000) × min(p, 1 − p)
                           = 0.10 × min(p, 1 − p)      [feeRateBps = 1000]
```

Verified against **4,310 fee-bearing fills** (2026-04-20 → 27): **median
relative error 0.000000, 100% within 1%**, on both the BUY branch (n=3,774) and
the SELL branch (n=536). That is verification to machine precision, not a fit.

The raw on-chain amount is side-dependent because the fee is taken in whichever
asset the taker receives — `BUY: rate·min(p,1−p)·shares / p` in tokens,
`SELL: rate·min(p,1−p)·shares` in USDC. The BUY branch divides by `p`, so below
50¢ it collapses to a **flat `0.10 × shares`** — which is exactly the flat
`0.100000` fee-per-share observed across every price bin under 50¢, and the
signature that identified the formula.

### The corrected comparison

| price | Kalshi taker | Polymarket taker | ratio |
|---:|---:|---:|---:|
| 5¢ | 0.333¢ | 0.500¢ | 1.50× |
| 10¢ | 0.630¢ | 1.000¢ | 1.59× |
| 25¢ | 1.313¢ | 2.500¢ | 1.90× |
| **50¢** | **1.750¢** | **5.000¢** | **2.86×** |
| 75¢ | 1.313¢ | 2.500¢ | 1.90× |
| 90¢ | 0.630¢ | 1.000¢ | 1.59× |

Published docs claim $1.75 per 100 shares at 50¢. On-chain says **$5.00**.

**Why the error was made and what it should have taken to avoid it.** I trusted
documentation for a number I had already flagged as contradicted by the venue's
own API, and I let the documented figure into a headline table with a `conf B`
rating instead of blocking on it. The `1000` was visible in Phase 0 and was the
correct signal; I noted it and then reasoned around it. **A venue's API disagreeing
with its own documentation should have been treated as blocking, not as a
footnote.**

### Two things this does NOT establish

1. **Whether makers are exempt.** `maker_base_fee` also reads `1000`, but that
   field is the market *maximum*, not the signed rate — an operator may sign a
   maker order at 0. The on-chain data that could settle it ends 2026-04-28.
   **The entire maker-side case for Polymarket is now UNVERIFIED**, and every
   number resting on it is marked provisional.
2. **Whether this rate is still current.** The sample is 2026-04-20→27, the end
   of subgraph coverage — **3 months stale**. Live markets still report
   `taker_base_fee: 1000`, which corroborates it, but does not prove the signed
   rate.

### Reprioritisation

`E-C` (maker/market-making on Polymarket) was the session's designated priority
*because* the maker fee was zero. That premise is now unverified and the taker
case is actively bad. **`E-C` is demoted from "the priority" to "conditional on
verifying the maker exemption on live fills"** — which needs a current data
source the subgraph cannot provide. Kalshi is now the better venue on cost at
every price point for takers, and the only venue with verified costs on both
sides.

---

## 0. PREMISE CORRECTIONS — read before anything else

Four premises of the master prompt are wrong. Three of them change what is worth
doing; one changes it a lot.

### 0.1 ❌ "Polymarket has historically charged no trading fee" — FALSE for crypto

This was the decisive economic question of the session, and the answer is the
opposite of the one the prompt anticipated.

**Polymarket charges a taker fee on crypto markets of `0.07 × p × (1−p)` per
share** — the *same functional form and the same rate as Kalshi*.

| price | Kalshi taker | Polymarket crypto taker |
|---|---|---|
| 50¢ | 1.75¢ | 1.75¢ |
| 90¢ / 10¢ | 0.63¢ | 0.63¢ |
| 5¢ | 0.3325¢ | 0.3325¢ |

Verified two ways: the published schedule (crypto rate 0.07, formula
`fee = C × rate × p × (1−p)`), and `tests/test_fees.py` reproducing all three
reference points the prompt fixes (1.75¢ / 0.63¢ / 0.63¢) in exact decimal.
15/15 tests pass.

**Consequence:** the cost bar on Polymarket is *not* ~3× lower. For a **taker**
it is identical to Kalshi. Every prior Kalshi taker negative result therefore
carries over to Polymarket unchanged, and item 3 of the report spec ("is
Polymarket structurally better?") does **not** have the expected answer.

**How the earlier probe got this wrong, and why it matters.** My first fee pull
returned `maker_base_fee: 0, taker_base_fee: 0` across 1000 markets and looked
like clean confirmation of zero fees. It was garbage: `/markets` returns oldest
first, so those were 987/1000 **closed 2023 sports** markets. Re-querying only
live, order-book-enabled *crypto* markets returned `1000/1000` on both fields.
This is failure mode #3 (plausible row counts, wrong content) and it would have
inverted the session's headline conclusion. Row counts are not a data check.

### 0.2 ✅ …but Polymarket **makers pay zero**, and that is the real edge

- **Polymarket maker fee: 0%.** Flat, all categories.
- **Kalshi maker fee: ~0.25× taker** (≈0.44¢ at 50¢).
- Polymarket additionally **rebates 15–25% of collected taker fees to makers**
  daily via its Maker Rebates Program — a maker can be *paid* to quote.

So the venue comparison inverts by side:

| | Kalshi | Polymarket |
|---|---|---|
| **Taker** | 1.75¢ @50¢ | 1.75¢ @50¢ — **identical** |
| **Maker** | ~0.44¢ @50¢ | **0¢, plus rebate** |

**This makes Strategy Family C (maker / market-making) the single highest-value
thread in the session, and Polymarket the venue to run it on.** That was already
flagged as "the largest untested gap"; it is now also the only axis on which the
two venues materially differ. Reprioritised accordingly.

### 0.3 ❌ "Kalshi crypto = the 15-minute series" — the universe is 272 series

`/series?category=Crypto` returns **272 series**, not one. The recurring
short-dated families alone:

- **14 fifteen-minute series** — BTC, ETH, SOL, XRP, DOGE, ADA, BCH, BNB, HYPE,
  NEAR, TON, ZEC, plus `KXCRYPTOCOMP15M` and `KXCRYPTOLEAD15M`.
- **~25 hourly series** — BTC/ETH/SOL/XRP/DOGE/BNB/HYPE/NEAR/TON/ZEC, each in a
  `range` (bucket) and a `D` (above/below) variant.
- **~19 daily series** — BTC, BTCD, ETHD, AVAX, BCH, DOT, LINK, LTC, SHIBA, XLM…

Prior work covered 1 of 272.

### 0.4 ✅✅ **Kalshi's hourly and daily series use FIXED ROUND-NUMBER STRIKES**

This was named "the single most important question in Phase 0". Answer:
**confirmed — they do not inherit the 15-minute series' at-the-money defect.**

- `KXBTC15M`: **1 market per event**, `floor_strike = 62926.4` — an unrounded
  number equal to the previous window's 60-second average. Born at-the-money,
  exactly as prior work described.
- `KXBTC` / `KXBTCD` (hourly): **80–188 markets per event**, strikes on a fixed
  **$250 ladder** — 53750, 54000, 54250 … 73250 — with spot at $62,926. Round
  numbers, fixed in advance, spanning ±16% of spot.

Live asks on the 2026-08-01 17:00 event ranged from **1¢ in the wings to 22¢ at
the mode**. So these contracts do trade across the full price range, including
the cheap tails where the quadratic fee is at its lowest.

**Consequence: the prompt's narrower restatement is right, and Families B, D and
the term-structure work all have a real venue to run on.** `KXBTC`/`KXBTCD` are
`between`/`greater` ladders over one expiry, so bucket families must sum to 100
and nested thresholds must be monotone — arbitrage checks that need no model.

### 0.5 ❌ "Polymarket's fill history is permanently public, so you can backtest against real historical order books immediately" — FALSE, twice over

This was the stated reason to lead with Polymarket. Both halves fail.

**(a) Order books were never public.** Polymarket matches orders in a centralised
off-chain CLOB and settles only *fills* on-chain. The Goldsky orderbook subgraph
exposes exactly four entity families — `orderFilledEvent`, `ordersMatchedEvent`,
`orderbook` (aggregate volume counters), `marketData`. There is **no `orders`
entity**; `orders(first:2){id}` returns `Type 'Query' has no field 'orders'`.
Order placement and cancellation are never indexed. **Historical Polymarket order
books cannot be reconstructed by anyone.**

**(b) The fill history that *is* public is stale and hard to join.** Measured:

| source | coverage | limit |
|---|---|---|
| Goldsky orderbook subgraph | **2022-11-21 → 2026-04-28**, complete fills with `fee`, `maker`, `taker`, `orderHash` | **~3 months stale** as of today |
| `data-api /trades` | current | **~10-minute rolling window** — `offset` 400s above ~20k; 10k trades reaches back only 8 minutes |
| Gamma `/markets?slug=` | **current window only** | settled short-dated markets stop resolving entirely |

The last row is the killer. Walking `bitcoin-up-or-down-<date>-7pm-et` backwards:
**1 of 21 days resolvable** — only today's. Same for the unix-stamped series
(`btc-updown-5m-<ts>`: today HIT, every prior probe from −1d to −365d miss) and
for the dated threshold ladders (`bitcoin-above-{58..66}k-on-<date>`: 0 of 60
probes across 12 days). Settled short-dated Polymarket markets vanish from the
public metadata API, so even the subgraph's on-chain fills cannot be joined back
to a market definition for those series.

**Consequence — this reverses the session's data strategy.** Polymarket does *not*
give an immediate backtest. Like Kalshi, its short-dated crypto series must be
**recorded live**. The one real advantage remains: Polymarket's live `/book`
returns genuine deep books (113 bid levels on a 5-minute market), so a recorder
started here produces true Tier B data.

**Therefore the single highest-value action is to start recording now**, so data
accumulates while the rest of the session proceeds. Done — see §1.

### 0.6 ❌ "Reuse the desktop's data" — none of it is on this machine

The prompt directs reuse of ~6,271 settled `KXBTC15M` markets, 102,716 1-minute
candles, and live recorders "on the desktop". **This is the laptop.** There is no
`C:\Users\vinig`; the only user profile is `gianf`. `C:\Users\gianf\kalshi` is a
*different project* (the tennis pre-match player model) that merely shares a
folder name — zero filename overlap, confirmed against the prior audit.

Kalshi order-book history is not retrievable from the API, so the recorded books
**cannot be recreated here at all**. See `BLOCKED_ON_DESKTOP.md`.

---

## 1. What is established so far

### Venue facts (detail in `docs/venue_spec.md`)

**Settlement — resolved definitively, both venues sampled from live contracts.**
Kalshi crypto settles on the **simple average of the sixty seconds** of the
relevant CF Benchmarks real-time index before the close — *not* a point sample.
Quoted verbatim from `rules_primary` on a live market:

> "If the simple average of the sixty seconds of CF Benchmarks' BRTI before
> 7:45 PM EDT on Jul 31, 2026 is at least the simple average of the sixty
> seconds of CF Benchmarks' [BRTI before 7:30 PM]…"

Both the **strike and the settle** are 60-second averages. An average has lower
variance than a point sample, so a point-sample model will systematically
overprice the tails of late-window contracts. Phase 4 model 2
(settlement-aware) is therefore not optional — it is a correctness fix, and it
should beat model 1 by construction.

**Tick structure — a finding prior work is unlikely to have had.** Kalshi tick
size is *not* a flat cent:

| series | `price_level_structure` | tick |
|---|---|---|
| `KXBTC15M`, `KXETH15M`, `KXSOL15M`, `KXXRP15M`, `KXDOGE15M` | `tapered_deci_cent` | **0.1¢ below 10¢ and above 90¢**, 1¢ in between |
| `KXBTC`, `KXBTCD`, `KXETH`, `KXETHD`, `KXSOLD`, `KXXRP` | `linear_cent` | flat 1¢ |

The 10× finer tick sits on the 15-minute series (minted ATM, so rarely in the
tails) and *not* on the hourly ladders (which live in the tails). That is the
wrong way round for Family D and needs to be priced in, not assumed away.

Kalshi also now quotes **fractional contracts** (`yes_bid_size_fp`,
`open_interest_fp`) and dollar-denominated prices (`yes_ask_dollars`).

**Polymarket short-dated crypto universe** — discovered from the public trade
stream (6,000 recent trades, 479 distinct markets), because Gamma's `tag_slug`
filter is silently ignored (see §3):

| family | recent trades |
|---|---|
| `btc-updown-5m-<ts>` | 1,623 |
| `eth-updown-5m-<ts>` | 363 |
| `btc-updown-15m-<ts>` | 272 |
| `sol-updown-5m-<ts>` | 202 |
| `eth-updown-15m-<ts>` | 140 |
| `sol-updown-15m-<ts>` | 135 |
| `xrp-updown-5m`, `hype-updown-5m`, `doge-updown-5m`, `bnb-updown-5m` | 95 / 94 / 65 / 63 |
| `btc-updown-4h`, `eth-updown-4h` | 44 / 51 |

**Polymarket runs 5-minute crypto binaries** — shorter-dated than anything on
Kalshi — plus 15-minute and 4-hour, plus dated ladders
(`bitcoin-above-{60k,62k,64k}-on-august-1-2026`) and bucket markets
(`will-the-price-of-bitcoin-be-between-60000-62000-…`). Tick is 1¢ on the
up/down series and **0.1¢ on the dated ladders**; minimum order size $5;
`seconds_delay: 0`.

### Cost bar, both venues, exact decimal (`src/fees.py`, 15 tests passing)

| | 50¢ | 25¢ / 75¢ | 10¢ / 90¢ | 5¢ |
|---|---|---|---|---|
| per-contract taker fee (both venues) | 1.75¢ | 1.3125¢ | 0.63¢ | 0.3325¢ |
| Kalshi taker round trip @ same price | 3.50¢ | 2.63¢ | 1.26¢ | 0.67¢ |
| Kalshi hold-to-settlement (one fee) | 1.75¢ | 1.32¢ | 0.63¢ | 0.34¢ |
| **Polymarket maker** | **0¢** | **0¢** | **0¢** | **0¢** |

Two rounding subtleties, both verified in tests:
- Kalshi **rounds fees UP to the cent per order**. A 1-lot at 50¢ pays **2.00¢**,
  not 1.75¢ (+14%). At 5¢ a 1-lot pays 1.00¢ on a raw 0.33¢ fee — **3× the
  headline rate**. This partly offsets the "tails are cheap" argument *for small
  orders only*; it vanishes at size (1000 lots at 5¢ → 0.333¢/contract).
- Polymarket rounds to 5 dp, min 0.00001 USDC — no material penalty.

---

## 1.5 Phase 1 results (2026-08-01)

### Does Deribit's implied probability beat Kalshi's mid?

**Not answerable, and not because of anything in our data.** Deribit's shortest
usable expiry is 54.2 h; Kalshi's crypto ladder contracts have a median lifetime
of 1.0 h. The horizon ranges do not overlap for 99.9% of contracts. See §000.
The pricer is built and validated (`docs/deribit_method.md`); the join is what
fails. Logged as `X4` — cancelled, not tested.

### Fat tails in the wings (`C9`) — supported, and it is the session's one surviving positive

1,582 consecutive hourly returns from 1,593 settled events, 2026-05-25 →
2026-08-01, from `expiration_value`.

| | BTC | ETH |
|---|---|---|
| annualised vol (hourly sampling) | 43.5% | 56.6% |
| skew | −0.596 | −0.462 |
| **excess kurtosis** | **13.08** | **12.85** |
| Student-t ν | **2.03** | **2.02** |
| Hill tail index α | 2.55 | 2.69 |
| Jarque–Bera p | ≈0 | ≈0 |

Empirical vs Gaussian tail mass: **2.5σ → 2.5×**, **3σ → 7.0×**, **4σ → 140×**.

Outliers verified as genuine: the largest BTC hour (−5.05%, 2026-06-25
13:00→14:00) coincides with ETH −6.27% in the same hour. Real market event, not
a bad settlement value.

**Two caveats that shrink this to one finding, not two.** corr(BTC, ETH hourly
returns) = **0.891** and 62% of extreme hours are shared, so the assets are not
independent confirmations. And ν ≈ 2.03 sits on the infinite-variance boundary,
so the σ defining "3σ" is itself unstable — the direction is robust, the exact
multipliers are not.

**No tradeable claim is made — see the withdrawal in §4.**

### Polymarket fee resolution

Resolved empirically and it **reverses the Phase 0 headline**. See §00.

## 2. Headline results

**No strategy has been backtested yet** — the vs-mid comparison, which is the
headline the session exists to produce, is gated on recorded data (see §9).

What *is* established is the model-free arbitrage result, which needs no
forecasting and no recording depth to be meaningful.

### 2.1 Term structure — Kalshi ladders are internally consistent (`A1`, `A2`)

| test | series | scans | events | gross violations | **profitable net of fees** |
|---|---|---|---|---|---|
| `A2` monotonicity of nested thresholds | KXBTCD, KXETHD, KXSOLD, KXXRPD | **3,187** | 26 | **0** | **0** |
| `A1` bucket families sum to 100¢ | KXBTC, KXETH, KXXRP | **1,135** complete | 26 | **1** | **0** |

The single `A1` violation: a `KXXRP` snapshot with bids summing to **1.0100** —
a 1.00¢ gross edge across a **75-leg** ladder. Crossing 75 legs costs **1.93¢ in
fees alone**, before any spread. Net: **−0.93¢**. Not tradeable.

**Mechanism for the null — and why it should persist.** The constraint is
enforced by the *width of the ladder*, not by arbitrageurs racing to it. A KXBTC
hourly event has 80–188 legs, a KXXRP event 75. Fee cost grows linearly in the
number of legs while the mispricing does not, so a bucket-sum violation must
exceed ~2¢ merely to break even at 75 legs. **The ladder is wide enough that
legging it is self-defeating.** This is structural, not a small-sample artifact.

**Sample caveat, stated plainly: 10.5 minutes, 26 events.** This is a
*preliminary* null. It extends prior work's "zero violations in 1,083 scans" in
kind — adding fee-inclusive accounting, the monotonicity constraint, and a
dwell-time measurement — but not yet in duration.

### 2.2 Two false positives caught and killed

Logged because a report that only records surviving claims understates how
easily an edge is manufactured.

1. **"464 profitable bucket-sum violations at 96–97¢."** The recorder writes on
   change, so an early forward-filled snapshot holds only the tickers seen so
   far: **3 of 80 buckets** summing to 0.03, which looks like a 97¢ risk-free
   profit. Buying 3 buckets does not pay $1 — it pays $1 only if the outcome
   lands in those 3. Fixed by requiring the complete ticker universe of the
   event *and* a contiguous tiling of the strike line. **All 464 vanished.**
2. **Then 0 complete scans** — a KXBTC bucket event is `less` + N × `between` +
   `greater`, and the type filter rejected `greater`; meanwhile KXBTCD events
   are *all* `greater` and must never be summed (nested thresholds, not a
   partition). Fixed by requiring ≥1 `between` to treat an event as a partition.

Both are failure mode #3 — plausible counts, wrong content. Neither would have
been caught by a row-count check. This is also a live example of the project's
own base rate: **the first "positive" result of the session was worth 0¢, and
correcting it shrank the edge to nothing**, consistent with all 20 prior
retractions.

### 2.3 A recorder design flaw the arbitrage test exposed

Write-on-change is correct for information content but makes `A1` **untestable**:
dead wing strikes never change, so a complete ladder is never captured. Fixed by
emitting an unconditional **keyframe** every 24 cycles (2 min), flagged
`keyframe: true` in the row. Complete-ladder scans went 0 → 1,135.

---

## 3. Data-quality incidents this session

Logged as they happen, per the project's failure-mode discipline.

1. **Polymarket fee sample was closed 2023 sports markets** (§0.1). Would have
   inverted the session's headline conclusion. Caught by checking
   `accepting_orders` / `enable_order_book`, not row count.
2. **Gamma `tag_slug` filter is silently ignored.** Querying `tag_slug=crypto`,
   `bitcoin`, `ethereum`, `solana`, `xrp` returned five **identical** 100-row
   sets, topped by `will-jesus-christ-return-before-2027` and a run of 2028 US
   election markets. Plausible row counts, wrong content — failure mode #3
   again. Worked around by discovering markets from the trade stream instead.
3. **Kalshi legacy integer price fields now return `None`.** `yes_bid`,
   `yes_ask`, `last_price`, `volume`, `open_interest` are all `None`; the live
   values are in `*_dollars` / `*_fp`. Any code carried over from prior work that
   reads `yes_bid` gets `None` silently — the exact shape of the orderbook-parser
   corruption already in this project's history. Flagged for the desktop merge.
4. **My own test expectation was wrong**, not the code: 0.0175 ceilings to 0.02.
   Corrected, and turned into the round-up findings above.

---

## 4. Hypotheses tested and surviving

**6 hypotheses evaluated** (`A1`, `A2`, `C8`, `F1`, `C9`, `C9-econ`), comprising
**34 individual tests**.

**Surviving correction: 1** — `C9` (fat tails), a distributional fact.
**Tradeable edges surviving: 0.**

Four apparent positives arose and **all four were withdrawn**:

| apparent positive | headline number | why it died |
|---|---|---|
| bucket-sum arbitrage | 464 violations at 96–97¢ | partial ladder — 3 of 80 buckets |
| round-number pinning | 6/20 survive BH, p≈0, R=0.244 | invalid null + duplicated series |
| **Polymarket taker-cost parity** | "identical to Kalshi" | trusted docs over the venue's own API; on-chain says **2.86×** |
| **fat-tail economic edge** | 1.5–1.9¢ net at 2.5–3σ | **benchmark inflation** — measured against a Gaussian strawman, not Kalshi's mid |

The last one deserves emphasis because it is the exact failure the brief warns
about. `fat_tails.py` printed an "edge − fee / tradeable? YES" column showing
1.5–1.9¢ apparently free at 2.5–3σ, where the fee is only 0.13–0.21¢. That
number is meaningless: it is the gap between reality and **a Gaussian I invented**,
and nothing in this session has shown Kalshi prices its wings with a Gaussian. A
venue already pricing fat tails correctly offers zero edge no matter how fat the
tails are. The real test needs Kalshi's own mid from the candlesticks endpoint
and has not been run.

Base rate now holds for **24 corrections**: every one shrank the edge, none ever
revealed a larger effect.

## 5. Structural-time hypotheses

| id | hypothesis | status |
|---|---|---|
| `C8` | round-number pinning | **NOT SUPPORTED** — see §4 and the ledger. Apparent effects are repulsion, not attraction, and appear only where the null is invalid. A valid retest (`C8-v2`) needs a path-preserving null. |
| `C3` Friday 08:00 UTC Deribit expiry | | PENDING — Deribit chain captured (870 BTC / 742 ETH instruments, 13 expiries); needs spot history |
| `C4` funding resets 00/08/16 UTC | | PENDING |
| `C5` 13:30 / 14:00 UTC US data | | PENDING |
| `C6` 21:00–22:00 UTC CME settle | | PENDING |
| `C7` CME weekend gap fill | | PENDING |

Deribit reference captured this session: **BTC DVOL 35.53** (7d range
34.91–38.78), **ETH DVOL 50.17** (48.69–53.32). The digital-price extraction
`P(S>K) = −dC/dK` works and produces a clean monotone curve (1.0000 → 0.0000
across strikes 57k–70k at the T+7.7h expiry, spot 62,898), so Phase 4 model `M6`
is ready to run as soon as there is quoted data to price against.

## 6. Maker vs taker

**Not yet measurable** — gated on recorded data. But Phase 0 established the
structural fact that makes this the session's priority: on Polymarket the maker
fee is **0** against Kalshi's ~0.44¢ at 50¢, plus a 15–25% taker-fee rebate to
makers. For a taker the two venues are **identical**. See §0.1–0.2 and
`docs/venue_comparison.md`.

## 7. Term-structure and cross-venue violations

Covered in §2.1. Kalshi ladders are internally consistent: **0 monotonicity
violations in 3,187 scans**; **1 bucket-sum violation in 1,135 complete scans,
worth −0.93¢ after the 75-leg fee**. Cross-venue (`A4`) is blocked on resolving
Polymarket's oracle — see §10.

## 8. Leak tests

**Not yet run.** No model has been fitted, so there is nothing to leak-test yet.
`L1`–`L4` are pre-registered, and **`L4` (the synthetic-noise control) is the
gate**: if the pipeline finds edge on a matched random walk with random
outcomes, everything else in the session is void.

The two false positives in §4 are not leak-test failures — both were caught by
data-completeness and null-validity checks, upstream of any model.

## 9. What is blocked, and how much data is needed

| blocked item | blocked on | ETA |
|---|---|---|
| Kalshi Tier B (order-book replay) | recorded books; **no historical endpoint exists** | recorder running since 00:13 UTC |
| Polymarket Tier B | same — books were never public anywhere | same recorder |
| `B1`–`B6` vs-mid comparison | recorder depth + settled pull | settled pull ~70% done |
| `E-C` maker strategies | recorder depth | needs ≥1 full session |
| `D1`–`D5` microstructure | recorder depth | needs ≥1 full session |
| desktop recordings, 1.77M trades | different machine | `BLOCKED_ON_DESKTOP.md` |

**Data in hand at time of writing:**

| dataset | size |
|---|---|
| Kalshi settled hourly ladders `KXBTC`/`KXBTCD` | **291,840 / 292,160 markets, 1,593 events, 2026-05-25 → 2026-08-01 (68 days)** |
| …`KXETH`/`KXETHD` | 186,945 each, 1,593 events, same span |
| …validation | 8/8 files clean: 0 parse errors, 0 duplicate tickers, 0 bad results, `expiration_value` on 99.99% |
| Deribit snapshot | 1.58 MB, 870 BTC + 742 ETH option instruments, DVOL 7d hourly |
| live recorder | ~7,000 Kalshi quote rows, ~1,900 Polymarket books, ~900 trades and growing |

The settled ladders are the session's most valuable asset: `expiration_value`
gives the realised CF Benchmarks 60-second average at **1,593 hourly boundaries**
— a free, high-quality spot series sampled exactly at settlement, requiring no
candle reconstruction.

⚠️ **A duplicate-writer incident was caught and resolved.** Two instances of the
settled pull ran concurrently against the same files (a `nohup` launch I believed
had failed had in fact started; only its `tail` failed). Both opened the same
`.jsonl` in `"w"` mode. One was killed and every file was re-validated
line-by-line — all 8 clean. Had this gone unnoticed, a truncated file would have
presented with a plausible row count.

## 10c. Top three next actions (updated 2026-08-01, post-Phase 2)

The crypto pricing question is **closed**. These are the only threads left that
are not variations on a question already answered.

1. **Verify whether Polymarket makers are actually exempt from fees.** The one
   remaining structural asymmetry between the venues, and it is *unverified*:
   `maker_base_fee` reads `1000` (a market maximum, not a signed rate) and the
   on-chain record ends 2026-04-28. Needs a current fill source. If makers do
   pay 0.10·min(p,1−p) like takers, Polymarket has no advantage at all and the
   whole venue can be dropped. **Highest information gain per hour by a wide
   margin** — it is a single decisive fact that closes or opens a venue.
2. **Test the maker side on Kalshi with the recorded books.** Every negative
   result in this project — including this one — is a *taker* result against the
   mid. Kalshi's maker fee is a quarter of taker, and a market-maker's question
   is not "can I forecast better than the mid" but "can I capture spread without
   being adversely selected". That is a genuinely different question and the
   recorder now has the data to ask it. **Note the honest prior: `B1` shows the
   mid is unbeatable as a forecast, which means a maker there earns spread minus
   adverse selection and nothing else.**
3. **Stop, and write up.** Two phases have produced a well-evidenced null on the
   central question and five withdrawn positives. The marginal value of a third
   phase on crypto pricing is low, and the project's own history says the next
   "edge" is most likely to be a sixth retraction.

Explicitly **not** recommended: more models, more parameters, shorter horizons,
or other venues' crypto ladders. Per `GO_NO_GO.md` §4 those are the moves that
generated the 25 prior retractions.

## 10b. Top three next actions (updated 2026-08-01, post-Phase 1 — superseded)

1. **Run `B1` (model vs Kalshi's own mid) using the candlesticks endpoint.**
   `/series/{s}/markets/{ticker}/candlesticks` returns per-minute `yes_bid` /
   `yes_ask` OHLC for settled markets across the full 68-day history — verified
   working. This unblocks the headline vs-mid comparison **without waiting for
   recording**, and it is the only benchmark that counts. It is also what turns
   the `C9` fat-tail fact into either a real edge or a null: price the wings
   with the fitted Student-t (ν≈2.03) against Kalshi's realised wing quotes,
   net of the 0.13–0.33¢ fee and the 1¢ tick.
2. **Verify whether Polymarket makers are actually exempt.** The entire
   maker-side case rests on `maker_base_fee: 1000` being a market maximum
   rather than a signed rate, and the on-chain record ends 2026-04-28. Needs a
   current fill source. Until then every Polymarket maker number is provisional
   and `E-C` cannot be prioritised.
3. **Run the `L4` synthetic-noise control before any further modelling.** Four
   false positives have now been caught by hand in two phases. The pipeline
   gate should be automated before it is trusted with a real result.

Demoted: the Deribit comparison (`X4`, cancelled for hourly ladders — viable
only on `KXBTC` weekly events, the 0.1%).

## 10. Top three next actions by information gain per hour (Phase 0, superseded)

1. **Resolve the Polymarket fee discrepancy** (`1000` in the API vs the
   documented `0.07·p·(1−p)`). One focused pass over on-chain `orderFilledEvent`
   fees, which are populated and non-zero on 192/200 recent fills. **Every
   number in `venue_comparison.md` depends on it**, and if the true taker rate is
   10% the taker comparison flips hard against Polymarket. Highest value per
   hour in the session by a wide margin.
2. **Let the recorder run, then execute `B1` (vs-mid) and `E-C` (maker) on the
   hourly ladders.** These are the headline result and the priority strategy;
   both are purely time-gated now, and the structural case for `E-C` is already
   established.
3. **Confirm Polymarket's resolution oracle.** Gates all cross-venue work
   (`A4`, `E-G`). If it is not CF Benchmarks, then near a strike the two venues
   can legitimately resolve differently — a settlement risk, not an arbitrage,
   and any gap-based strategy would be mispriced from the start.

Runner-up: rerun `C8` with a path-preserving null (`C8-v2`).

---

## Priority order for the rest of the session

Reordered by the user for this machine, and consistent with the findings above:

1. **Polymarket** — enumerate crypto markets ✅, confirm fees ✅, **reconstruct
   historical order books** from the CLOB API + Goldsky orderbook subgraph
   (both confirmed reachable). Fully public, no live recording needed.
2. **Kalshi settled history** for the hourly/daily ladder series — re-pullable
   here, and now known to have fixed round-number strikes.
3. **Deribit** option chain + DVOL — live, free, no auth.
4. Deferred to a desktop session: `BLOCKED_ON_DESKTOP.md`.
