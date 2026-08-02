# archive.pmxt.dev — what it actually is

Measured 2026-08-02 by fetching, not by reading the site. Every number below
came off an HTTP response or a parquet file on disk.

## ⚠ The premise in the request is wrong

> *"free L2 orderbook archive with rolling 30-day retention, so it deletes
> itself continuously"*

**It is not on rolling retention and it is not deleting itself.** It is frozen.

| Probe | Result |
|---|---|
| `kalshi_orderbook_2026-05-16T12.parquet` | **HTTP 200**, 55,380,433 bytes, `Last-Modified: Sat, 16 May 2026 13:05:34 GMT` |
| Age of that file | **78 days** — it would have been deleted 48 days ago under 30-day retention |
| Every hour after `2026-06-11T03` | **HTTP 404** |
| `2026-07-xx`, `2026-08-xx` (10 dates probed) | **404, all of them** |

Under rolling 30-day retention on 2026-08-02 the archive would hold
2026-07-03 → 2026-08-02 and nothing earlier. The observed pattern is the exact
inverse: everything before 06-11 is present, everything after is absent. This
is a **capture that stopped**, with its back catalogue left in place.

**Consequence for prioritisation:** mirroring is insurance against an abandoned
R2 bucket being switched off by its owner. That is a real risk and worth the
40 GB. It is *not* time-critical in the stated sense, and nothing was lost by
the ~1 h spent verifying before downloading. No live recording gap is accruing
against this source, because the source stopped accruing 52 days ago.

## Actual coverage

Probed every hour at the boundaries, not interpolated:

```
2026-05-14  ..............XXXXXXXXXX   first file 14:00 UTC
2026-05-15  XXXXXXXXXXXXXXXXXXXXXXXX
   ... 27 complete days, all 24 h ...
2026-06-10  XXXXXXXXXXXXXXXXXXXXXXXX
2026-06-11  XXXX....................   last file 03:00 UTC
2026-06-12  ........................
```

| | |
|---|---|
| Span | **2026-05-14T14:00 → 2026-06-11T03:00 UTC**, contiguous |
| Files | **662** hourly parquet files, no gaps found |
| Size | ~40 GB total, 40–85 MB/file |
| Licence | CC-BY-4.0, no signup, no API key |
| Direct URL | `https://r2kalshi.pmxt.dev/kalshi_orderbook_YYYY-MM-DDTHH.parquet` |

A prior memory recorded this as `2026-05-15 00:00 → 2026-06-10 23:00, 648
files`. That is **10 hours short at the front and 4 at the back**; the true
range is 662 files. Corrected.

## It is a websocket capture, not a book series

This is the part that decides how it can be used. Verified on
`2026-06-01T12`, 11,839,385 rows:

| Column | Type |
|---|---|
| `timestamp_received` | `timestamp[ms, UTC]`, **never null** |
| `timestamp` | `timestamp[us, UTC]`, **null on 100% of snapshot rows** |
| `market_ticker`, `market_id`, `event_type`, `side` | string, never null |
| `yes_bids`, `no_bids` | `list<struct<"1": decimal(9,4), "2": decimal(18,6)>>` = (price, size) |
| `price`, `delta` | decimal, non-null on delta rows only |

| Event type | Rows | Share |
|---|---|---|
| `orderbook_delta` | 11,807,343 | **99.73%** |
| `orderbook_snapshot` | 32,042 | **0.27%** |

**The book is not readable off any single row.** A snapshot is sent once when
the capture subscribes to a market; everything after it is a per-price-level
delta. Reconstructing depth means replaying snapshot + deltas in order, per
ticker. Any analysis that reads `yes_bids` directly and averages it will get
the empty list 99.98% of the time and silently report no depth.

### Two parsing traps, both hit during verification

1. **`frac_empty = 0.9998` is not a finding.** That was computed over the
   first 20,000 rows, which are nearly all deltas. Delta rows carry empty
   level arrays *by construction*. Restricted to snapshot rows the figure is
   25.30% with depth on at least one side, 4.99% two-sided — and even that
   describes the moment of subscription, not the market.
2. **The struct children are literally named `"1"` and `"2"`.** Iterating the
   converted dict yields its *keys*, so `[(float(a), float(b)) for a, b in
   levels]` produces a perfectly plausible ladder of `(1.0, 2.0)` repeated at
   every level, on every market. It looks like data. It is the column names.
   Read by key explicitly. This is GUARDS #12's failure mode arriving in a new
   costume, and it fooled the first pass of this session's own check.

Parsed correctly, the ladders are real:

| | |
|---|---|
| Levels parsed (two-sided snapshots, 1 h) | 25,301 |
| Price range | 0.0010 – 0.9980, **100%** inside (0,1) |
| Size | min 0, median **200**, p90 4,450, max 15,556,807 |
| Distinct prices / sizes | 479 / 5,307 |
| Max levels seen on one side | **102** |

## Breadth — this is why it matters for market selection

In the single hour `2026-06-01T12`:

| | |
|---|---|
| Distinct tickers with any event | **73,786** |
| Distinct tickers receiving a snapshot | 30,160 |

Top series by row count in that hour:

| Series | Rows |
|---|---|
| KXBTCD | 1,851,820 |
| KXATPCHALLENGERMATCH | 1,678,511 |
| KXITFWMATCH | 845,829 |
| KXINTLFRIENDLYGAME | 710,250 |
| KXWTACHALLENGERMATCH | 408,042 |
| KXBTC15M | 383,455 |
| KXMVESPORTSMULTIGAMEEXTENDED | 341,090 |
| KXWTAMATCH | 282,652 |
| KXITFMATCH | 245,500 |
| KXMLBGAME | 240,749 |
| KXCS2GAME | 202,887 |
| KXETH15M | 198,536 |
| KXWTASETWINNER | 196,242 |
| KXBTC | 193,034 |
| KXETHD | 180,265 |

Tennis across its five series is ~3.66 M rows in the hour — consistent with the
earlier note of "3.6 M tennis rows".

## Status of the mirror

Running as a detached process, 3 workers, resumable, **content-validated per
file** (parquet footer parses, row count > 0, schema field names match the
expected 10 exactly, `price` row-group statistics inside (0,1), and
`orderbook_delta` present in row group 0). A file failing any check is renamed
`.BAD` and retried. Row counts alone are never accepted as evidence.

- Destination `market-selection/data/pmxt/` (gitignored: `data/` and `*.parquet`)
- Log `market-selection/data/pmxt/_mirror_log.jsonl`, one record per file
- Observed rate ≈ 41 GB/h ⇒ ~1 h for 662 files
