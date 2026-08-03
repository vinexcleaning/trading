# Known data limitations

Read this before trusting any number in the dashboard. Everything below is a
real constraint discovered by probing the live APIs, not a hypothetical.

---

## 1. Price history cannot resolve sub-minute delays

`clob.polymarket.com/prices-history` has a minimum fidelity of **1 minute**.
Finer requests are silently coarsened, and the interval form (`interval=1d`)
clamps coarser still. Passing explicit `startTs`/`endTs` with `fidelity=1`
bypasses the interval minimum and returns true 1-minute bars.

**Effect:** short follower delays (2s, 5s, 15s) can only be answered from the
second-level trade tape. Where the tape is sparse, the system says so rather
than interpolating. This is the single largest source of `n/a` values.

## 2. The trade tape is sparse in thin markets

`data-api /trades` returns genuine second-resolution prints, but a busy market
yielded 1,000 prints while an illiquid ITF market yielded **zero**. Copyability
for thin markets therefore rests on minute bars or modelled prices, and is
labelled accordingly.

## 3. Gamma cannot look up a market by condition id

Verified: `?condition_ids=` returns an empty list, and `?condition_id=`
**silently ignores the filter and returns the default market list**. Using
either would attach the wrong market metadata to a wallet's transactions —
a silent, total corruption of the tennis universe.

The correct lookup is `GET clob.polymarket.com/markets/{condition_id}`, which
resolves properly, 404s on unknown ids, and exposes `tokens[].winner` for
resolution. This is the only lookup path used.

## 4. Per-id market lookups are expensive

Because there is no verified batch-by-condition-id endpoint, each unknown market
costs one request. Wallets trade far more non-tennis than tennis, so backfill is
capped per sync cycle and prioritised. A high count of transactions unmatched to
a market is **expected**, not a fault — only the tennis universe is fully synced.

## 4b. Wallet activity history is capped at 5,000 records by offset

`data-api /activity` rejects offsets beyond 5000 with HTTP 400 (`max historical
activity offset of 5000 exceeded`). A wallet with more history than that cannot
be fully read by paging, and a naive paginator stops there **without any error** —
silently truncating history and biasing every metric derived from it.

The provider works around this by re-anchoring on the newest timestamp seen and
restarting the offset, walking forward through time in windows. It stops and
warns (`provider.activity_window_stalled`) rather than looping if a single
timestamp fills an entire window.

## 4c. `resolved_at` is not when the match ended

It is a metadata/UMA finalisation timestamp, observed 6–15 days after matches
that lasted a few hours. Consequently `holding_seconds` for a position closed by
redemption measures *entry → settlement bookkeeping*, not how long risk was held.

In the real-wallet sample, positions that were actually sold averaged **0.9
hours**, while settlement-closed positions averaged **160 hours**. Averaging the
two together produces a meaningless number, so hold time must always be read
split by close type. Note that for copyability this cuts the right way anyway: a
wallet that never sells early cannot strand a follower.

## 5. Order-book depth is a point-in-time snapshot

Books are captured when the price-backfill job runs, not continuously. For
historical trades, depth at the moment of the wallet's entry usually does not
exist. The backtester therefore **cannot apply its minimum-liquidity gate** to
those candidates and says so explicitly in the run warnings, rather than letting
them pass a test that was never run.

## 6. Total depth flatters thin markets

$14.55 available within one cent of touch versus $2,178 across the whole ladder
was observed on a single real market. Any "liquidity" number that sums the book
is close to meaningless for execution. Depth is measured near the touch.

## 7. Wallet bankroll is not observable

Drawdown percentages need a capital base that on-chain data does not provide.
An explicit modelled bankroll is used (see [SCORING.md](SCORING.md)). It is an
assumption applied uniformly, not a measurement.

## 8. Off-platform and cross-market hedges are invisible

A position that looks directional may be one leg of a hedge held elsewhere.
Behaviour is therefore reported as **flags** (`possible_hedge`,
`likely_market_making`, `possible_arbitrage`) rather than as a verdict.

## 9. Wallet clustering suggests, it does not prove

Shared markets, timing correlation and size similarity can indicate one operator
behind several addresses — or simply two people reading the same information.
Labels are graded (`likely_independent`, `possibly_related`,
`highly_correlated`, `insufficient_evidence`) and never assert ownership.

## 10. Survivorship bias is not corrected

Wallets become visible because they did something noticeable, and leaderboards
list winners. Wallets that blew up quietly are absent. Every ranking carries a
caveat, and `survivorship_risk` exists as a flag, but the bias itself cannot be
removed from the population.

## 11. Resolution timing is approximate

`resolved_at` comes from market metadata, not from settlement on-chain. Holding
periods that span resolution can be slightly off.

## 12. Upstream schema changes are the biggest silent risk

A field quietly renamed upstream would produce plausible, wrong numbers. Schema
drift is detected and recorded as a first-class alertable event, surfaced on the
System Health page. **If drift is reported, do not trust recent results until it
is reviewed.**

---

## How limitations surface in the UI

| Signal | Meaning |
|---|---|
| `n/a` copyable ROI | Not enough price evidence to measure honestly |
| Coverage < 50% (amber) | The copyable figure rests on a minority of trades |
| `thin_data` flag | Sparse price evidence around this trade |
| Evidence badge (`modeled`) | The number is an assumption, not an observation |
| Backtest warning about depth | The liquidity gate could not be applied |
| "P(positive edge): withheld" | Sample too small for the statistic to mean anything |
