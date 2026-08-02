# AUDIT.md — is the data we have any good, and is a clean-room rebuild worth it?

Run 2026-08-01. Every number below came from a script in this folder, not from
any project's own claims. Re-runnable:

```
python audit/inventory_local.py    # what is on disk
python audit/probe_api.py          # what the free API will give
python audit/quality_candles.py    # does the candle archive survive checks
```

---

## VERDICT

**Do not clean-room. A rebuild started today would come back with strictly less
data than we already hold, and the difference is permanently unrecoverable.**

Kalshi's public API is a **rolling ~69-day window, not an archive**. Markets that
close outside that window are deleted outright — not archived, not paginated
deeper, just gone. Verified three ways on the same tickers:

| ticker (closed 2026-05-24) | `/markets/{t}` | `/candlesticks` | `/trades` |
|---|---|---|---|
| `KXATPMATCH-26MAY25BLOWON-WON` | **404** | **404** | 0 rows |
| `KXATPMATCH-26MAY25SONHER-SON` | **404** | **404** | 0 rows |
| `KXATPMATCH-26MAY25FONPAV-FON` | **404** | **404** | 0 rows |
| *(control, still listed)* `…26AUG01FAROCO-FAR` | 200 | 200 | 10 rows |

Those six markets **were** in the 2026-07-29 pull. Between 07-29 and 08-01 —
three days — **1,066 markets aged off**, every one of them closing 2026-05-24,
every one `finalized`. 1,004 new ones appeared at the other end. The window
slides forward about one day per day.

So the local archive is not a suspect copy of something re-downloadable. It is
the only copy. `set1_overshoot/data/candles_ohlc/` holds **2026-05-21 → 08-01**;
the first three days of that no longer exist on Kalshi's servers.

The plan's premise — *"Kalshi markets go back to July 2021, I want ALL of it"* —
is not achievable from the free API at any effort level. Nothing before
**2026-05-24** is retrievable, for any category.

---

## 1. What is already on disk

| Store | Size | Coverage | State |
|---|---|---|---|
| `set1_overshoot/data/markets_raw.json` | 107 MB | 40,526 tennis markets, 5 series | pulled 08-01 |
| `data/kalshi/tennis_markets.json` | 111 MB | 41,844 tennis markets, **6 series** | pulled 07-29 |
| `set1_overshoot/data/candles_ohlc/` | 55 MB | **6,308,170** 1-min candles, 19,781 markets, 05-21 → 08-01 | the asset |
| `set1_overshoot/data/depth/` | 85 MB | live L2 book, 08-01 only, 118 markets | self-recorded |
| `data/cache/*.parquet` | ~1.05 GB | Sackmann tennis model features (1.75M matches) | separate project |

### Candle quality — it holds up

- **19,781 of 19,782** markets have candles. One missing (0.01%).
- Candle span covers **1.00×** each market's listed open→close life. No truncation.
- **0.00%** rows with an absent bid or ask. **0.0000%** crossed books (bid > ask).
- Median spread **2¢**, mean 11.95¢, p90 46¢.
- Zero-volume markets: 47 (0.2%). Median final volume 6,291 contracts.
- Prices stored as integer cents, no float path — `p0_candles.py` converts via
  `Decimal`, and `fees.py` is exact `Decimal` throughout.

Two caveats, both real:

- **Sparse minutes.** Median market has a candle for only **28%** of the minutes
  in its span (p25 21%, p95 60%). Kalshi emits a candle only when something
  happens. Any strategy that assumes a quote every minute is interpolating.
- **The 1¢/99¢ trap is much smaller here than the note in memory says.** Only
  **0.63%** of candle rows quote 0-1/99-100, and only **29 of 19,781** markets
  (0.1%) spend over half their life there. The "40% of tennis markets" figure
  does not describe this dataset — it likely came from an entry-time snapshot of
  a different universe. Worth re-deriving before relying on it either way.

### One real bug found

`set1_overshoot/src/p0_markets.py` lists five series. The earlier
`download_kalshi.py` pulled **six**. The newer, more careful pull silently drops
**KXWTACHALLENGERMATCH — 1,256 markets, 606 yes / 606 no**, a whole tour tier.
That data survives only in the older `tennis_markets.json`, and Kalshi has since
deleted most of it. Add the series before the next pull.

---

## 2. What the free API actually gives (ceiling, measured)

Full crawl of `/markets` to exhaustion: **28,621,377 markets, 28,622 pages,
2 h 17 m**, unauthenticated, no rate-limit hit at 0.05 s pacing.

- **No auth needed** for `/markets`, `/markets/trades`, `/series`,
  `/candlesticks`. Confirmed live, 200s.
- **12,369 series** across 18 categories: Sports 3,065 · Entertainment 2,490 ·
  Politics 2,127 · Elections 1,525 · Financials 715 · Economics 614 ·
  Mentions 398 · Climate/Weather 291 · Sci/Tech 283 · Crypto 271 · Companies 173 ·
  World 143 · Health 96 · Commodities 77 · Social 52 · Transportation 38 ·
  Exotics 10 · Education 1.

### 88% of that 28.6M is auto-generated parlay junk

| series root | markets |
|---|---|
| `KXMVESPORTSMULTIGAMEEXTENDED` | **20,363,716** |
| `KXMVECROSSCATEGORY` | **4,924,738** |
| everything else (4,526 roots) | ~3.33M |

Sampling settled markets returns these almost exclusively, and they carry
`volume_fp 0.00`, `open_interest_fp 0.00`, `liquidity_dollars 0.0000`, all prices
`0.0000`, `rules_primary` empty, and lifetimes of minutes (`open_time`
00:40:35 → `settlement_ts` 00:43:14). They are combinatorial multi-leg
constructions, not traded markets. **A naive "collect every market" pull is 88%
noise**; the real tradeable universe is ~3.3M. Filter `KXMVE*` at collection or
the database is unusable.

### There is still no history

| close year | markets |
|---|---|
| 2023 | 59 |
| 2024 | 561 |
| 2025 | 6,149 |
| **2026** | **28,580,313** |
| 2027+ (long-dated) | 34,295 |

6,769 markets across 2023–2025 — those are long-dated contracts still listed, not
an archive. The 2021–2022 era the plan assumes returns **nothing**. Trades agree:
`/markets/trades` with `max_ts` before 2026-01-01 returns **0 rows** at every year
tested.

### Other measured facts

- **Trades are public and per-market**: `taker_side`, `taker_book_side`,
  `count_fp`, `yes_price_dollars`, `created_time`, `is_block_trade`. Real taker
  flow, never collected by this project, and it ages off with the market.
- **Candlesticks**: 1-minute minimum, capped at 5,000 periods per request. No
  sub-minute data — intra-minute adverse selection is not measurable from Kalshi.
- **Not every series prices in whole cents.** Tennis is `linear_cent`; the MVE
  series are **`deci_cent`**. The integer-cent assumption in `p0_candles.py` and
  the fee arithmetic is safe for tennis and **not** safe for an all-category rig.
- **Price/volume fields are alive.** The 0.0% sample above is a property of the
  junk markets drawn, not of the API — the tennis pull has all 46 fields
  populated with real distinct values (`volume_fp` 36,731 distinct).
- **No historical order book.** Kalshi publishes none. (But see §3.)

---

## 3. New data that is actually new — and free

### pmxt archive — the find. `https://archive.pmxt.dev/Kalshi`

Free, CC-BY-4.0, **no signup, no key**. Direct files at
`https://r2kalshi.pmxt.dev/kalshi_orderbook_YYYY-MM-DDTHH.parquet`.

Verified by downloading `2026-06-01T12`:

| | |
|---|---|
| What it is | raw Kalshi **websocket capture** — `orderbook_snapshot` + `orderbook_delta` |
| Resolution | **millisecond**, per price level, per side (`timestamp`, `price`, `delta`, `side`) |
| Breadth | **73,786 distinct tickers in a single hour**, all categories |
| Volume | **11,839,385 rows per hour** |
| Coverage | **2026-05-15 00:00 → 2026-06-10 23:00 UTC**, all 24 h every day, 648 files |
| Size | ~60 MB/file, **≈ 39 GB** total |
| Tennis content | 3.6M rows/hour, 579 tennis markets in that hour alone |

Why this matters more than anything else here: it is **true L2 depth for the
window our candles already cover** (05-21 → 06-10 overlaps by 3 weeks). That is
the difference between "fills marked OPTIMISTIC because we only had trade
prints" and walking a real book. It also covers **05-15 → 05-21**, which predates
our own archive and which Kalshi has already deleted.

Two warnings: the archive **stopped on 2026-06-10** — nothing since, so it is not
a live feed and may be abandoned; and being deltas, the book must be
reconstructed from snapshot + replay, not read off directly.

### Sources that need you (see below)

| Source | Cost | Needs |
|---|---|---|
| kalshibacktest.com free tier | free | signup. **Weaker than the plan assumes** — free = newest 50 markets per type; 31 days of history is the paid Pro tier |
| lycheedata.com | paid, unpriced publicly | claims 36 GB, 7.68M markets, 72.1M trades **since July 2021** — the only thing found that covers the pre-2026 era |
| Apify `flashscore-tennis-matches` | $0.001/result (~$20 for the full tennis universe) | your Apify account |

---

## 4. What to do instead of a clean room

1. **Start an append-only daily collector today.** Every day it does not run, one
   day falls off the far end forever. This is the only irreversible item.
2. **Add `KXWTACHALLENGERMATCH`** and, if the scope is now all-category, drive the
   collector off `/series` rather than a hardcoded list — while excluding
   `KXMVE*`, which is 88% of the row count and 0% of the tradeable universe.
3. **Mirror the pmxt archive now** — 39 GB, free, and it is already two months
   stale with no guarantee it stays up.
4. **Collect trades**, which nothing here has done, while the markets are still alive.
5. Rebuild the *schema* (SQLite/Postgres, indices, `settlement_status`) as the
   plan asks — but **load the existing files into it**. Rebuild the container, not
   the contents.
