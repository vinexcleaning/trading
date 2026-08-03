# Phase 0 — Ground truth

All rows verified **2026-07-30** unless stated. Confidence: **H** = verified directly
against the live Kalshi API from this host, **M** = official docs/help-centre text,
**L** = secondary source or inference.

Where a claim in the master prompt turned out to be wrong, it is marked
**PREMISE CORRECTED** and repeated at the top of `MORNING_REPORT.md`.

---

## 0.1 Exchange scale

| Fact | Value | Conf | Source |
|---|---|---|---|
| Distinct series enumerated | **7,493** | H | `GET /series?category=…` across 12 categories |
| Open markets (all types) | **551,366** | H | `GET /markets?status=open` full walk, 2,796 pages |
| Open markets excl. combos | **71,781** (13.0%) | H | filter `mve_collection_ticker is null` |
| Combo / multivariate markets | **479,585** (87.0%) | H | same |
| Distinct series with ≥1 open single market | **3,131** | H | derived |

Series per category (from `/series`):

| Category | Series | Category | Series |
|---|---|---|---|
| Sports | 3,043 | Companies | 173 |
| Politics | 2,070 | World | 141 |
| Financials | 710 | Health | 96 |
| Economics | 606 | Transportation | 39 |
| Science and Technology | 283 | Entertainment | 38 |
| Crypto | 269 | Elections | 11 |
| Climate and Weather | **6** | Commodities | 8 |

> **PREMISE CORRECTED — "Climate and Weather" is not where the weather markets are.**
> The category holds only 6 series (EV market share, eclipse cloud cover). The real
> temperature markets live under other categories with `KXTEMP*` / `KXHIGH*` tickers
> and are **not returned by any `/series?category=` query** — see 0.7.

## 0.2 Fees — the formula, and a corrected premise

The **series object itself carries the fee terms**, which is more authoritative than
any published PDF (`kalshi.com/fee-schedule` and the fee PDF both returned HTTP 429
throughout; they were never successfully read):

```
GET /series/{ticker} -> { "fee_type": ..., "fee_multiplier": ... }
```

| Field | Observed values (n=7,493 series) | Conf |
|---|---|---|
| `fee_type` | `quadratic` (7,369) · `quadratic_with_maker_fees` (124) | H |
| `fee_multiplier` | `1` (7,484) · `0` (9) | H |

Verified taker formula (units corrected from the prompt):

```
fee_dollars = ceil(0.07 * C * P * (1-P) * 100) / 100      # P in dollars 0..1
fee_cents   = ceil(7 * C * P * (1-P))
```

The prompt's `ceil(0.07 × C × P × (1-P))` is right in shape but **off by 100×** — that
expression is dollars, not cents. Cross-check: 100 contracts at 50¢ → 0.07·100·0.25 =
**$1.75**, the widely-reported figure. Conf **H** on shape and multiplier (blog post
"halving" figure of 0.875¢ at midpoint back-solves to exactly 0.035·0.25·100).

Maker fee = **¼ of taker** (`0.0175`), and **only on the 124 series** whose `fee_type`
is `quadratic_with_maker_fees`. Every other series charges makers nothing. Conf **M**
on the ¼ ratio, **H** on which series it applies to.

> **PREMISE CORRECTED — there is no halved fee multiplier for S&P 500 / Nasdaq-100.**
> The prompt (and a 2022 Kalshi blog post announcing a halving) says these use 0.035.
> Live API says otherwise: **`KXINX` and `KXNASDAQ100` both report `fee_multiplier: 1`**,
> as do all 48 `KXINX*`/`KXNASDAQ100*` variants. Either the 2022 promo lapsed or it is
> not expressed through this field. **Conservative decision (`DECISIONS.md` D-002): assume
> the standard 0.07 everywhere.** This removes the entire stated structural
> reason to prefer index range markets (Phase 1b item 4).

The 9 series with `fee_multiplier: 0` (genuinely zero fees) are:
`KXDOED`, `KXPAHLAVIHEAD`, `KXEXPAND`, `KXGAMBLINGREPEAL`, `KXGREENLAND`,
`KXETHY`, `KXBTCY`, `KXGDPYEAR`, `KXLAYOFFSYINFO`.
All are one-off/annual — **recurrence ≈ 0, so zero fees buys nothing testable.**

### Round-trip taker cost (the cost bar)

Per contract, at C=100 so the per-fill ceiling doesn't dominate:

| P | Fee/leg (¢/contract) | **Round trip (¢)** | Round trip if 0.035 existed |
|---|---|---|---|
| 0.10 | 0.63 | **1.26** | 0.63 |
| 0.25 | 1.32 | **2.63** | 1.32 |
| 0.50 | 1.75 | **3.50** | 1.75 |
| 0.75 | 1.32 | **2.63** | 1.32 |
| 0.90 | 0.63 | **1.26** | 0.63 |

The prompt's ~3.5¢ round trip at 50¢ is **confirmed**. Trading the tails costs ~36% of
trading the middle (1.26 vs 3.50), so the viable space does live at the tails — but see
0.5: the flagship BTC contract is structurally pinned to the *most expensive* point.

## 0.3 API surface and auth

| Endpoint | Purpose | Auth | Conf |
|---|---|---|---|
| `GET /series?category=` | list series | **none** | H |
| `GET /series/{t}` | series terms incl. fee fields | **none** | H |
| `GET /markets` | markets, `status`/`series_ticker` filters, cursor | **none** | H |
| `GET /markets/{t}/orderbook` | full depth both sides | **none** | H |
| `GET /markets/trades` | exchange-wide trades, `min_ts`, `ticker` | **none** | H |
| `GET /events` | events, nested markets | **none** | H |
| `GET /exchange/status` | `trading_active` flag | **none** | H |
| `GET /exchange/schedule` | standard hours, maintenance windows | **none** | H |
| WebSocket `wss://…/trade-api/ws/v2` | deltas | **RSA-signed key required even for public channels** | M |

The entire read-only surface needed for this project is **anonymous**. No credentials
exist anywhere in this repo. WebSocket needs a signed handshake, so all recorders are
REST-poll based — the cost is that we get snapshots, not true deltas, and no exchange
event timestamp on book rows (`event_ns` is null for books by necessity).

### Rate limits — measured, not documented

Docs describe token buckets for *authenticated* tiers (Basic ≈ 20 read req/s) and say
nothing about anonymous access. Measured directly against uncacheable
per-market orderbook URLs from this host:

| Offered rate | Result | Conf |
|---|---|---|
| 15 req/s paced, 12 s | **180/180 OK, 0 × 429** | H |
| 17.5 req/s sequential, 200 reqs | **200/200 OK, 0 × 429** | H |
| 25 req/s paced | 131 OK / **169 × 429 (56%)** | H |
| 4 threads unpaced (≈62 req/s) | 133 OK / **107 × 429** | H |
| 16 threads unpaced (≈232 req/s) | 67 OK / **173 × 429** | H |

**Conclusion: the anonymous sustained ceiling is ~15–18 req/s and it is a hard wall,
not a soft throttle.** Recorders run at **8 req/s** (observed 640 requests, 0 × 429).

Caution for anyone re-measuring: `GET /series` responses carry
`Cache-Control: public, max-age=15` and are served by CloudFront, so repeated identical
requests return `X-Cache: Hit` and appear to sustain 69 req/s. That number is fake.
Only distinct URLs (`X-Cache: Miss`) measure the real limiter.

**How many books can we maintain?** At 8 req/s with one request per book snapshot:
24 markets at 3 s resolution, or 140 markets at ~18 s, or ~480 markets at 60 s. The
recorder splits this as tier1 = 24 near-money markets at 4 req/s (6 s full rotation)
and tier2 = 140 at 2 req/s (70 s rotation).

## 0.4 History availability

| Question | Answer | Conf |
|---|---|---|
| Historical order book / depth retrievable? | **No.** Only current book state. This is why recorders start immediately. | H |
| Settled markets walkable backwards? | **Yes**, cursor pagination, no observed hard stop | H |
| Depth demonstrated | **2,400 settled `KXBTC15M` markets** walked back to 2026-07-05, more pages remained | H |
| Settlement fields post-settlement | **Populated** — see 0.5 | H |
| Live/historical split | docs describe a ~3-month live tier and `/historical/*` beyond a cutoff | M |

2,400 settled 15-minute markets ≈ 25 days at 96/day. **This is enough history to do
real out-of-sample work on BTC tonight without waiting for recorded data.**

## 0.5 `KXBTC15M` — settlement resolved, and the structure matters more

**Settlement mechanics — resolved definitively, the prompt's second option is right.**
Straight from the live series object (`product_metadata.important_info`):

> "The price used to determine this market is based on CF Benchmarks' corresponding
> Real Time Index (RTI). At the last minute before expiration, 60 RTI prices are
> collected. The official and final value is the average of these prices."

Conf **H** (live API, not a third-party summary). Settlement source: **CF Benchmarks**,
`settlement_sources[0]`. So the terminal variable is a **60-second arithmetic mean of
1 Hz samples**, not a point sample. This is the pricing-model-relevant answer: the
variance of a mean over the final minute is lower than a point sample, so a correct
model prices late-window contracts **further from 50¢** than point-sample GBM does.

Fields on a settled market — all populated (`status` becomes `finalized`):

| Field | Example | Note |
|---|---|---|
| `expiration_value` | `"63928.89"` | the 60 s average. **Is a real field** — the prompt's `strike_threshold` is not. |
| `floor_strike` | `63983.17` | the threshold |
| `cap_strike` | `null` | used by `between` markets |
| `strike_type` | `"greater_or_equal"` | **resolves tie handling: exactly on strike ⇒ YES** |
| `result` | `"yes"` / `"no"` | outcome |

> **STRUCTURAL FINDING — the strike is the previous window's settlement value.**
> Consecutive markets chain exactly:
>
> | Market (close) | `floor_strike` | `expiration_value` |
> |---|---|---|
> | 02:15 | 63951.04 | 63934.93 |
> | 02:30 | **63934.93** | 63983.17 |
> | 02:45 | **63983.17** | 63928.89 |
>
> Each window's strike **is** the prior window's settle. So `KXBTC15M` is not a strike
> ladder — it is a single **"will BTC be ≥ where it was 15 minutes ago"** contract,
> minted exactly at-the-money every 15 minutes.
>
> **Consequence for the cost bar, and it is severe.** An at-the-money contract sits at
> P ≈ 0.50, precisely where `P(1-P)` — and therefore the fee — is *maximised*. The
> flagship BTC market is permanently parked at the **3.50¢ round trip**, the worst point
> on the curve, and the tail discount (1.26¢) is structurally unreachable at entry.
> A directional edge on a driftless asset must therefore exceed **3.5 percentage points**
> to break even. That is a very high bar for 15-minute BTC direction, and it should be
> stated as the headline obstacle for Phase 5 rather than discovered at backtest time.

Strike banding: `KXBTC` (hourly) uses ~$250-wide `between` buckets plus `greater`/`less`
tails (e.g. `B73625` = floor 73500 / cap 73749.99), so **hourly is a genuine
mutually-exclusive bucket family** and is arb-checkable. `KXBTC15M` is a single binary.

## 0.6 Trades feed — anonymous, and combos ARE filterable

| Question | Answer | Conf |
|---|---|---|
| Requires auth? | **No** | H |
| Anonymous? | **Yes.** Fields: `trade_id, ticker, count_fp, yes_price_dollars, no_price_dollars, taker_outcome_side, taker_book_side, created_time, is_block_trade`. **No account identifier of any kind.** | H |
| Combo legs present? | Combos trade under **their own tickers**, and those markets are flagged | H |
| Filterable? | **Yes** — `mve_collection_ticker` and `mve_selected_legs` on the market object | H |

> **PREMISE PARTLY CORRECTED.** The prompt warns combo legs are auto-generated into the
> feed and must be filtered or "every flow signal will be garbage". The mechanism is
> different but the warning is directionally right and the fix is clean: a combo is a
> distinct market carrying `mve_collection_ticker` (e.g.
> `KXMVESPORTSMULTIGAMEEXTENDED-R`) plus `mve_selected_legs` naming each underlying
> leg. **87% of all open markets are combos**, so filtering them is not optional —
> but it is a single non-null check, not a heuristic. Flow analysis joins trades to
> markets on `ticker` and drops non-null `mve_collection_ticker`.

`min_ts` (unix seconds) works and is the correct way to poll forward. Ordering is
**newest-first**, and the cursor walks *backwards* in time.

## 0.7 Weather markets — they exist, under tickers the series list hides

`/series?category=` never returns them, and `/series/KXTEMPDCH` is not resolvable, yet
**`/markets?series_ticker=KXTEMPDCH` returns markets**. So the series index is
incomplete and the market index is authoritative. Found this way:

| Family | Cadence | Structure | Open now |
|---|---|---|---|
| `KXTEMPDCH`, `KXTEMPLAXH`, `KXTEMPCHIH`, `KXTEMPAUSH` | **hourly** | nested `greater` thresholds at 1 °F steps | 10 each |
| `KXHIGHNY/CHI/MIA/AUS/LAX/DEN/PHIL` | daily | daily-high buckets | 6–12 each |

Example: `KXTEMPDCH-26JUL3004-T76.99` — "temp in Washington DC above 76.99 °F at
4am EDT". Settled examples carry `expiration_value: "75.00"` with `floor_strike`
76.99 / 75.99 / … — i.e. **a monotone nested-threshold ladder settling off a single
observed number.** Ground truth is free and directly comparable: NWS
`api.weather.gov/stations/KDCA/observations/latest` returned **73.4 °F** against those
same strikes at the time of writing.

**Volume is the problem, not the structure.** Settled DC thresholds showed
`volume_fp` of 0, 1, 202, 0, 100 — near-nothing. Provisionally a liquidity kill, to be
confirmed against recorded books once trading reopens (see `docs/shortlist.md`).

## 0.8 Leaderboard

Opt-in, not default-on; only opted-in aggregate stats are public; no API endpoint
exposes per-trader positions. Identity-level copy trading on Kalshi is therefore
impossible for free — **flow following is the only option**. Conf **M** (help centre).
Logged in `PAID_OPTIONS.md`.

## 0.9 Trading hours — the thing that explains every empty feed

```
GET /exchange/status
-> { "exchange_active": true, "trading_active": false, ... }
```

At 07:39 UTC on Thursday 2026-07-30 **trading was halted**. `/exchange/schedule` gives
Thursday as two sessions — `open 00:00 close 03:00` and `open 05:00 close 00:00` — in
ET, i.e. a **07:00–09:00 UTC halt**. This exactly explains three things that otherwise
look like bugs or dead markets:

1. Zero trades exchange-wide after `07:00:00.762685Z` (`min_ts` sweep confirms genuine
   absence, not a stale cache).
2. `KXBTC15M` having no `active` market — settled through 06:45, next batch
   `initialized` for 03:45 the following day.
3. `updated_time` on `KXBTCD` markets stuck at the previous 20:00 UTC.

**Operational consequence:** any recorder started in this window sees nothing and must
not be mistaken for broken. `trading_active` is now recorded every 30 s
(`source=kalshi_status`) so every gap in `data/gaps_report.md` is attributable.
Recorders were live before the 09:00 UTC reopen, which was the goal.

---

## Open questions

- Whether the anonymous ~15 req/s ceiling is per-IP, per-host or global. Only measured
  from one host.
- Whether the 2022 S&P/Nasdaq fee halving lapsed or is applied outside `fee_multiplier`.
  Blocked on `kalshi.com/fee-schedule` (persistent 429).
- Whether `/series` omits `KXTEMP*` by design or by defect. Material because a
  category-driven screen silently misses the highest-prior family on the exchange.
- Exact maker-fee series list beyond the 124 flagged `quadratic_with_maker_fees`.
