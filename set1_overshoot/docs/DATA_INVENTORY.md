# DATA_INVENTORY.md

Verified 2026-08-01. Every availability claim below was tested with a live
request, not assumed.

## B1. What is currently used

| Field / dataset | Source | Coverage | Role |
|---|---|---|---|
| `event_ticker`, `ticker`, `series` | Kalshi `/markets` | 19,782 matches | **decision** — universe and dedupe key |
| `result` (yes/no) | Kalshi | 19,782 | **label** only |
| `open_time`, `close_time` | Kalshi | 19,782 | time coordinate; `close_time` for the temporal split |
| `yes_bid`/`yes_ask` OHLC, 1-min | Kalshi candlesticks | 6,308,170 rows, 19,781 markets | **decision** — every price, entry, exit |
| `bid_h` / `ask_l` | Kalshi candlesticks | same | **decision** — maker trade-through test |
| `vol`, `oi` per candle | Kalshi candlesticks | same | **not used** (as-of safe, but unused) |
| `rules_primary` | Kalshi | 19,782 | tournament + round parsed; **not yet used as a feature** |
| Inferred `t0`, `dur_min` | derived | 16,921 ok | **decision** — play window, entry timing |
| Inferred set-1 changepoint | derived | 16,921 | **decision** — entry rule |
| Scoreline truth set | Sackmann mirror + tennis-data | **2,887 matches (14.6%)** | **validation only — never a feature** |
| Order-book depth, 20 levels | Kalshi `/orderbook`, recorded live | 63,409 snapshots, 08-01 only | **validation only** — fill realism |
| `volume_fp`, `open_interest_fp`, `last_price` on settled records | Kalshi | — | **BANNED** — post-settlement, see `POST_SETTLEMENT_FIELDS.md` |

The scoreline set is the important line: it exists, it is clean (settlement
agreement **1.0000**, n=2,887), and it has only ever been used to check the
detector. It has never entered a model.

## B2. Available and unused

### Sackmann GitHub — **GONE. Verified 404 today.**

| URL | status |
|---|---|
| `github.com/JeffSackmann/tennis_atp` | **404** |
| `github.com/JeffSackmann/tennis_wta` | **404** |
| `github.com/JeffSackmann/tennis_slam_pointbypoint` | **404** |
| raw `atp_matches_2026.csv` | **404** |
| raw `atp_matches_futures_2026.csv` | **404** |

The repos are not reachable. What exists is the **frozen local mirror ending
2026-06-02**, which covers only the first 9 days of the Kalshi window. It cannot
be extended. Any plan that assumes Sackmann can be re-pulled is dead on arrival.

Serve-stat coverage in the mirror, for the record: the prior claim of 4.6% on ITF
futures could not be re-verified per tier at usable n because the mirror stops
before most of the Kalshi window.

### tennis-data.co.uk — **LIVE (HTTP 200, 278 KB)**

Contains results plus closing odds (B365, Pinnacle, Betfair) and **set-by-set
scores** (`W1/L1/…`). Free. Well timestamped by match date — safe.
**Coverage limit: ATP/WTA main tour only ≈ 1,724 of 19,782 matches (8.7%).**
Already used; local copy runs to 2026-07-26 and can be refreshed.

### SofaScore — **BLOCKED. HTTP 403 on the public API today.**

Would provide point-by-point and momentum. Not accessible without circumventing
the block, and I have not checked whether their terms permit programmatic
access. **Reporting it as unavailable rather than working around it.**

### Apify actors — available, paid, and this is the real gap-filler

Verified in the Store today. There is no `tennis-live-predictor` skill in this
session's skill list, so the claim that one is "already set up" **could not be
confirmed from here**; the actors below were found by direct search.

| Actor | Covers | Price | Backfill? |
|---|---|---|---|
| `extractify-labs/flashscore-tennis-matches` | **ATP, WTA, ITF *and* Challenger**, set-by-set scores, live + historical by date offset | **$0.001/result** | yes, by date |
| `sian.agency/tennis-point-by-point-scraper` | every serve/rally/break point + match and set stats | $0.075/match | yes, by player |
| `crawlstone/tennis-scraper` | SofaScore + Tennis Abstract, point-by-point | $0.008/result | yes |
| `parseforge/tennisexplorer-scraper` | results + closing odds by date | $0.0075/result | yes |
| `parseforge/tennis-abstract-scraper` | player stats, H2H splits | $0.021/result | yes |

**Flashscore is the one that matters**: it is the only verified source covering
ITF and Challenger — 91% of the Kalshi book — for the period Sackmann cannot.
Cost to label the 3,436 events is about **$3.44**; the whole 19,782-match
universe about **$20**.

### Derivable from data already held — free, no new joins

Match duration; number and size of price changepoints; realised volatility of
the price path; pre-match mid as a strength proxy; drop depth and speed;
entry-time spread; time since each player's previous match in the dataset
(fatigue); matches played so far in the same tournament; tournament and round
from `rules_primary` (parses on **19,782/19,782**).

### Live-only — record now or lose it

Order-book depth and queue position. Kalshi publishes **no** historical
order-book endpoint. Already recording since 06:58 (63,409 snapshots). Anything
needing depth for the May–July backtest window is permanently unavailable.

## B3. Cannot be obtained

- **Serve order in set 2** for the historical window. Not recoverable from price
  and no free source publishes it. Flashscore point-by-point could supply it
  *going forward and for backfill at $0.075/match*, but not free.
- **Historical order-book depth** for 25 May – 1 Aug. Gone.
- **Sackmann data after 2026-06-02.** Repos deleted.
- **Sub-minute price movement.** Kalshi candles are 1-minute; adverse selection
  inside a minute cannot be measured from them.
- **Counterparty identity / order flow.** Not published.
