# venue_spec.md

Every row has a source and a confidence rating. Confidence:

- **A** — read directly off a live API response this session (reproducible now)
- **B** — published venue documentation, corroborated by ≥2 independent sources
- **C** — inferred from observed data, not directly stated
- **?** — open question, explicitly not resolved

Captured 2026-07-31 ~20:00 ET / 2026-08-01 00:00 UTC.

---

## 1. Kalshi

### 1.1 Universe

| item | value | conf | source |
|---|---|---|---|
| crypto series count | **272** | A | `GET /series?category=Crypto` |
| 15-minute series | 14 (BTC, ETH, SOL, XRP, DOGE, ADA, BCH, BNB, HYPE, NEAR, TON, ZEC + `KXCRYPTOCOMP15M`, `KXCRYPTOLEAD15M`) | A | same |
| hourly series | ~25, each asset in a `range` (bucket) and `D` (above/below) variant | A | same |
| daily series | ~19 (BTC, BTCD, ETHD, AVAX, BCH, DOT, LINK, LTC, SHIBA, XLM…) | A | same |
| API host | `api.elections.kalshi.com/trade-api/v2` | A | probe; `trading-api.kalshi.com` returns 401 "API has been moved" |
| auth needed for market data | **no** | A | all pulls this session unauthenticated |
| historical order book | **not retrievable** | A | no endpoint exists |

### 1.2 Strike convention — the decisive Phase 0 question

| series class | convention | conf |
|---|---|---|
| `KXBTC15M` and the other `*15M` | **1 market per event**, strike = the previous window's 60-second average. Born at-the-money. `floor_strike` e.g. `62926.4` (unrounded) | A |
| `KXBTC` / `KXBTCD` (hourly) | **80–188 markets per event** on a **fixed $250 ladder** (53750, 54000, … 73250) with spot at 62,898. `KXBTCD` uses `…99.99` offsets on a $100 ladder | A |
| `KXETH`, `KXXRP`, `KXSOLD` (hourly) | same ladder structure, asset-appropriate spacing | A |

**Consequence:** the at-the-money defect that killed `KXBTC15M` taker round trips
is specific to the `*15M` series. The hourly ladders trade the full 1¢–99¢ range
including cheap tails, where the quadratic fee is at its lowest.

> ⚠️ Do **not** test "is the strike a round number" by integer-roundness.
> `KXBTCD` strikes are `54599.99` and XRP strikes are `1.062`; both score 0 on
> roundness while being perfectly regular ladders. Test **spacing regularity
> within an event** instead.

### 1.3 Settlement — resolved definitively

| item | value | conf |
|---|---|---|
| source | **CF Benchmarks real-time index** (BRTI for BTC, ETHUSD_RTI, SOLUSDRTI, …) | A |
| mechanic | **simple average of the sixty seconds before the close** — *not* a point sample | A |
| 15m strike | also a 60-second average (of the 60s before the window opened) | A |
| `settlement_timer_seconds` | `1` on `*15M`; `60` on hourly ladders; `1800` on some daily | A |
| settled record carries | `expiration_value` (the realised settlement, e.g. `"62893.21"`) and `result` (`yes`/`no`) | A |

Quoted verbatim from a live `rules_primary`:

> "If the simple average of the sixty seconds of CF Benchmarks' BRTI before
> 7:45 PM EDT on Jul 31, 2026 is at least the simple average of the sixty
> seconds of CF Benchmarks' [BRTI before 7:30 PM]…"

**Modelling consequence:** the terminal variable is a 60-second *mean*, whose
variance is strictly below a point sample's. A point-sample model overprices the
tails of late-window contracts. Phase 4 model `M2` is a correctness fix, not an
optional refinement.

### 1.4 Fees

| item | value | conf |
|---|---|---|
| `fee_type` | `quadratic` | A (per-series API field) |
| `fee_multiplier` | `1` on the series inspected | A |
| taker fee | `ceil_to_cent(0.07 × C × p × (1−p))` | B |
| reference points | 1.75¢ @50¢, 0.63¢ @90¢ and @10¢, 0.3325¢ @5¢ | A (`tests/test_fees.py`, 15 passing) |
| maker fee | ~0.25× taker (≈0.44¢ @50¢) | B — **not yet verified empirically** |
| rounding | **UP, per order** | B |

**Rounding matters more than it looks.** A 1-lot at 50¢ pays **2.00¢**, not
1.75¢ (+14%). A 1-lot at 5¢ pays **1.00¢** on a raw 0.3325¢ fee — **3× the
headline rate**. The penalty vanishes at size (1000 lots @5¢ → 0.333¢/contract).
This partially offsets the Family D "tails are cheap" argument *for small orders
only*.

### 1.5 Tick structure — non-uniform, and the wrong way round

| series | `price_level_structure` | tick | conf |
|---|---|---|---|
| `KXBTC15M`, `KXETH15M`, `KXSOL15M`, `KXXRP15M`, `KXDOGE15M` | `tapered_deci_cent` | **0.1¢ below 10¢ and above 90¢**, 1¢ between | A |
| `KXBTC`, `KXBTCD`, `KXETH`, `KXETHD`, `KXSOLD`, `KXXRP` | `linear_cent` | flat 1¢ everywhere | A |

The 10× finer tick sits on the series minted at-the-money (which rarely reach the
tails) and **not** on the hourly ladders (which live there). For Family D on the
hourly ladders the minimum spread is a full cent — comparable to the entire fee
at 10¢. This must be priced in, not assumed away.

### 1.6 Other

| item | value | conf |
|---|---|---|
| fractional contracts | **yes** — `yes_bid_size_fp`, `open_interest_fp` are decimals | A |
| price fields | `*_dollars` as **strings** (`"0.9900"`) — parse as Decimal, no float dust | A |
| ⚠️ legacy fields | `yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest` now return **`None`** | A |
| rate limits | not hit at 10 series × 200 markets every 5s, sustained | C — measured, not documented |
| settled history depth | ≥400 pages × 1000 for `KXBTC` (pull ongoing) | A |

> ⚠️ The legacy-field change is a live instance of this project's known
> orderbook-parser corruption mode: code reading `yes_bid` gets `None` with
> correct row counts. See `BLOCKED_ON_DESKTOP.md` §C.2.

---

## 2. Polymarket

### 2.1 Universe

| item | value | conf |
|---|---|---|
| short-dated crypto series | `{btc,eth,sol,xrp,doge,bnb,hype}-updown-{5m,15m,4h}-<unix_ts>` | A |
| **5-minute binaries** | yes — shorter-dated than anything on Kalshi | A |
| dated ladders | `bitcoin-above-{60,62,64}k-on-<date>` | A |
| bucket markets | `will-the-price-of-bitcoin-be-between-60000-62000-…` | A |
| one-touch | `what-price-will-bitcoin-hit-in-<month>` | A |
| busiest series (recent tape) | `btc-updown-5m` 1,623 trades of 6,000 sampled | A |

### 2.2 Fees — the decisive Phase 0 question

| item | value | conf |
|---|---|---|
| formula | `fee = C × rate × p × (1−p)` | B |
| **crypto taker rate** | **0.07** | B — 2 independent sources + venue docs |
| **maker rate** | **0** — makers are never charged, all categories | B |
| maker rebates | 15–25% of collected taker fees redistributed daily to makers | B |
| rounding | 5 dp, min 0.00001 USDC | B |
| other categories | sports/econ 0.05; politics/finance/tech 0.04; geopolitics 0% | B |
| API `maker_base_fee` / `taker_base_fee` | **`1000`** on live crypto markets | A |
| on-chain `fee` field | populated and non-zero on 192/200 recent fills | A |
| ⁇ reconciliation of `1000` vs `0.07` | **unresolved** | ? |

**The `1000` is not reconciled with the documented 0.07 and must not be treated
as settled.** 1000 bps = 10%, which is not 0.07. Most likely `*_base_fee` is a
per-market *maximum* the operator may sign, not the rate actually charged — one
observed fill had `fee / takerAmountFilled` = exactly 0.10. The documented 0.07
formula reproduces the venue's own published per-100-share table and matches
Kalshi's three reference points exactly, so it is used for now. **Verifying this
empirically against on-chain fills is a required Phase 1 work item** — the on-chain
`fee` field makes it possible, and the whole cross-venue cost comparison rests on
it.

> ⚠️ An earlier probe returned `maker_base_fee: 0, taker_base_fee: 0` across
> 1000 markets and looked like clean confirmation of zero fees. Those were
> 987/1000 **closed 2023 sports** markets — `/markets` returns oldest first.
> Row counts are not a data-quality check.

### 2.3 Market mechanics

| item | value | conf |
|---|---|---|
| tick size | **1¢** on `*-updown-*`; **0.1¢** on dated ladders / bucket markets | A |
| minimum order size | **$5** | A |
| `seconds_delay` | `0` | A |
| outcomes | binary `["Up","Down"]` | A |
| live book depth | genuine — 113 bid levels on a 5-minute market | A |
| book endpoint | `GET /book?token_id=` with `hash` + `timestamp` | A |
| resolution oracle | UMA optimistic oracle; underlying price feed **not yet confirmed** | ? |

**The oracle source is an open question and it matters.** The prompt asks
whether Kalshi and Polymarket resolve on *different* sources, because near a
strike boundary they could legitimately disagree — a structural risk, not an
arbitrage. Kalshi's source is confirmed CF Benchmarks. Polymarket's is not yet
confirmed and **must be resolved before any cross-venue (`E-G`) result is
believed**.

### 2.4 Data availability — the session's biggest constraint

| source | coverage | conf |
|---|---|---|
| Goldsky orderbook subgraph | **2022-11-21 → 2026-04-28** complete on-chain fills, with `fee`, `maker`, `taker`, `orderHash` | A |
| …staleness | **~3 months behind** | A |
| `data-api /trades` | current, but a **~10-minute rolling window** (`offset` 400s above ~20k) | A |
| Gamma `/markets?slug=` | **current window only** — settled short-dated markets stop resolving (1/21 days) | A |
| live `/book` | full depth, recordable | A |
| **historical order books** | **do not exist publicly** — no `orders` entity in the subgraph; matching is off-chain | A |

⚠️ **Three Gamma filters are silently ignored** rather than erroring:
`tag_slug`, `slug_contains`, and repeated `slug` params. Querying
`tag_slug=crypto|bitcoin|ethereum|solana|xrp` returns five **identical** 100-row
sets topped by `will-jesus-christ-return-before-2027`. Discovery must go through
the trade tape instead.

---

## 3. Open questions (`?` rows above)

1. **Polymarket `*_base_fee: 1000` vs documented `0.07`** — resolve against
   on-chain fills. Gates the entire cross-venue cost comparison.
2. **Polymarket's crypto oracle / price feed** — gates `E-G`.
3. **Kalshi maker fee multiplier** — documented as ~0.25× taker, not yet
   verified against an observed fill. Gates `E-C` on Kalshi.
4. **Kalshi rate limits** — measured as sufficient, never documented; a harder
   recorder cadence may hit an undocumented ceiling.
