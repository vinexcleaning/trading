# HANDOFF — kalshi-tennis / data audit

Last updated 2026-08-03. Session working dir was `C:\Users\gianf\kalshi`
(NOT in the repo); the files this session produced live here, in
`trading/kalshi-tennis/audit/`, and are tracked.

## What this session was asked to do

The user pasted a four-phase "Kalshi research rig" plan (build a data lake →
build a backtest engine → test favourite-longshot bias → optional Homerun live
execution). Before building anything, they asked to establish whether a
clean-room rebuild would actually get better data than what was already on disk.

Answer: **no. A rebuild would get strictly less, and the difference is gone
forever.** Full write-up in `audit/AUDIT.md`. Nothing from the four-phase plan
was built. No collector was started.

## The finding that governs everything

**Kalshi's public API is a rolling ~69-day window, not an archive.**

- Diffing the 2026-07-29 pull against 2026-08-01: **1,066 markets aged off in
  3 days**, all closing 2026-05-24, all `finalized`. 1,004 new ones appeared.
- Those tickers now return **404 on `/markets/{ticker}`, 404 on
  `/candlesticks`, 0 rows on `/trades`**. Deleted, not archived.
- Full crawl of `/markets` to exhaustion: **28,621,377 markets, 28,622 pages,
  2 h 17 m**, unauthenticated, no rate limiting at 0.05 s pacing.
- By close year: 2023=59, 2024=561, 2025=6,149, **2026=28,580,313**. The
  pre-2026 rows are long-dated contracts still listed. There is no history.
- **88% of the universe is junk**: `KXMVESPORTSMULTIGAMEEXTENDED` (20.4M) +
  `KXMVECROSSCATEGORY` (4.9M) are auto-generated parlays with zero volume, zero
  OI, zero liquidity, ~3-minute lifetimes. Real tradeable universe ≈ 3.3M.
  Exclude `KXMVE*` at collection or the database is unusable.

The plan's premise — "Kalshi goes back to July 2021, I want ALL of it" — is not
achievable from the free API at any effort level.

## Quality of the data already held — it holds up

`data/` here is gitignored (correctly). Contents measured, not assumed:

- `candles_ohlc/`: **6,308,170** 1-min candles, 19,781 markets, 2026-05-21 →
  08-01. **19,781 of 19,782** markets have candles.
- Candle span covers **1.00×** each market's listed open→close life.
- **0.00%** absent bid/ask. **0.0000%** crossed books. Median spread **2¢**,
  mean 11.95¢, p90 46¢. 47 markets (0.2%) never traded.
- Integer cents throughout; no float path.

Two caveats:

- **Sparse minutes.** Median market has a candle for only **28%** of the minutes
  in its span. Kalshi emits one only on activity — anything assuming a quote per
  minute is interpolating.
- **The "40% of markets quote 1¢/99¢" note is conditional**, not general. Across
  all 6.3M candle rows it is **0.63% of rows** and **29 of 19,781 markets**. The
  40% describes a pre-match anchor on a 502-match main-tour holdout. Both are
  true; do not generalise the 40%.

## One real bug, unfixed

`set1_overshoot/src/p0_markets.py` lists **5** series. The older
`download_kalshi.py` pulled **6**. The newer pull silently drops
**KXWTACHALLENGERMATCH — 1,256 markets (606 yes / 606 no)**, a whole tour tier.
It survives only in `data/kalshi/tennis_markets.json` (gitignored, 111 MB), and
Kalshi has since deleted most of it. Add the series before any future pull.

Also: not every series prices in whole cents. Tennis is `linear_cent`; the MVE
series are **`deci_cent`**. The integer-cent assumption in `p0_candles.py` and
the exact-Decimal fee arithmetic is safe for tennis and **not** safe for an
all-category rig.

## New data source found — free, no login, unclaimed

`https://archive.pmxt.dev/Kalshi` — CC-BY-4.0. Direct files at
`https://r2kalshi.pmxt.dev/kalshi_orderbook_YYYY-MM-DDTHH.parquet`.

Verified by downloading `2026-06-01T12` (kept at `audit/pmxt_sample.parquet`,
57 MB, gitignored):

| | |
|---|---|
| what | raw Kalshi **websocket capture** — `orderbook_snapshot` + `orderbook_delta` |
| schema | `timestamp_received`, `timestamp`, `market_ticker`, `market_id`, `event_type`, `yes_bids`, `no_bids`, `price`, `delta`, `side` |
| resolution | **millisecond**, per price level, per side |
| breadth | **73,786 tickers in one hour**, all categories |
| volume | **11,839,385 rows/hour**; 3.6M tennis across 579 markets |
| coverage | **2026-05-15 00:00 → 2026-06-10 23:00 UTC**, all 24 h daily, 648 files |
| size | ~60 MB/file, **≈39 GB** total |

Kalshi publishes no historical order book, so this is the only way to replace
optimistic trade-print fills with a real book walk. It overlaps the local candle
archive by three weeks and precedes it by six days — days Kalshi has deleted.
**It stopped updating on 2026-06-10** and may be abandoned; mirror before
trusting. Data is deltas — reconstruct by replaying snapshot + deltas.

## State: nothing is running, and that is the problem

No collector, no recorder, no daily job for this project. Every day that holds,
one more day ages off Kalshi permanently. This is the only irreversible item on
the board.

## Next actions — both were waiting on user approval, still unstarted

1. **Append-only daily collector.** Drive it off `/series`, exclude `KXMVE*`,
   include `KXWTACHALLENGERMATCH`, collect trades (never collected here before).
   Append only — never re-pull to "replace" an existing archive.
2. **Mirror the 39 GB pmxt archive** while it is still up.
3. Rebuild the *schema* (SQLite/Postgres, indices, `settlement_status`) as the
   plan asks, but **load the existing files into it**. Rebuild the container,
   never the contents.
4. Pre-2026 history: only lead is `lycheedata.com` (paid, pricing not public,
   claims 7.68M markets / 72.1M trades since July 2021). Needs the user.
5. `kalshibacktest.com` free tier is weaker than the plan assumes — free is the
   newest 50 markets per type; 31 days of history is paid Pro.

## Reproduce any of this

```
python kalshi-tennis/audit/inventory_local.py    # what is on disk
python kalshi-tennis/audit/probe_api.py          # what the free API gives (~2h17m)
python kalshi-tennis/audit/quality_candles.py    # does the candle archive survive checks
```

`python` on PATH is a Store stub — use
`C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe`.
Paths inside these scripts still point at `C:\Users\gianf\kalshi\...` and need
updating for the move into the repo.
