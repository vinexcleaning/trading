# THE SHAPE OF THE EXCHANGE - measured before any recorder was widened

**Measured 2026-08-18 05:08 UTC by `strategy-factory/src/shape.py`.** One full sweep of every open Kalshi market, then a second sweep 300 seconds later to measure how much actually moves. Nothing was recorded; this is the arithmetic that decides the recorder's shape.

## 1. One sweep of the whole exchange

| | |
|---|---|
| open markets | **784814** |
| HTTP requests to get them all | 785 |
| seconds for one sweep | **626** |
| markets with a two-sided quote | **54269** (6.9%) |
| markets with one side only | 639956 (81.5%) |
| markets with no quote at all | 90589 (11.5%) |

A sweep is one HTTP request per 1,000 markets, not one per market. That is the finding in `RESULT_LIST_QUOTES.md` and it is what makes recording the whole exchange possible at all: the per-market orderbook route would be 76.3 hours for one pass.

## 2. Where the markets actually are

| category | series | markets | quoted | two-sided |
|---|---:|---:|---:|---:|
| Exotics | 2 | 701056 | 610489 | 16 |
| Sports | 920 | 42106 | 42101 | 25282 |
| Elections | 593 | 11387 | 11387 | 9995 |
| Financials | 486 | 10050 | 10050 | 6712 |
| Entertainment | 308 | 6609 | 6609 | 4422 |
| Crypto | 78 | 4010 | 3993 | 460 |
| Economics | 240 | 3183 | 3183 | 2502 |
| Politics | 478 | 2107 | 2107 | 1967 |
| Commodities | 37 | 1288 | 1288 | 627 |
| Climate and Weather | 100 | 967 | 967 | 541 |
| Science and Technology | 127 | 917 | 917 | 761 |
| Mentions | 30 | 533 | 533 | 510 |
| Companies | 36 | 394 | 394 | 362 |
| (unknown) | 2 | 202 | 202 | 107 |
| World | 3 | 3 | 3 | 3 |
| Social | 2 | 2 | 2 | 2 |

## 3. The 20 biggest series, and how much of each is dead air

| series | category | markets | two-sided | share two-sided |
|---|---|---:|---:|---:|
| `KXMVECROSSCATEGORY` | Exotics | 568219 | 10 | 0.0% |
| `KXMVESPORTSMULTIGAMEEXTENDED` | Exotics | 132837 | 6 | 0.0% |
| `KXMIDTERMMOV` | Elections | 3939 | 3687 | 93.6% |
| `KXNASDAQ100U` | Financials | 2800 | 581 | 20.8% |
| `KXMIDTERMVOTETURN` | Elections | 2756 | 2463 | 89.4% |
| `KXARTISTSTREAMSY` | Entertainment | 1097 | 842 | 76.8% |
| `KXNEXTTEAMNBA` | Sports | 823 | 80 | 9.7% |
| `KXNFLSPREAD` | Sports | 793 | 793 | 100.0% |
| `KXNFLWINSWEEK` | Sports | 728 | 582 | 79.9% |
| `KXHOUSERACE` | Elections | 705 | 704 | 99.9% |
| `KXNCAAFCONFMATCHUP` | Sports | 620 | 3 | 0.5% |
| `KXNFLTOTAL` | Sports | 608 | 608 | 100.0% |
| `KXNCAAFSEED` | Sports | 600 | 31 | 5.2% |
| `KXNCAAFWINS` | Sports | 583 | 528 | 90.6% |
| `KXNFLFFLEADERTOP` | Sports | 575 | 57 | 9.9% |
| `KXMARMADROUND` | Sports | 560 | 163 | 29.1% |
| `KXNFLWINS` | Sports | 547 | 404 | 73.9% |
| `KXNFLMATCHUP` | Sports | 496 | 46 | 9.3% |
| `KXMLSSCORE` | Sports | 450 | 329 | 73.1% |
| `KXMARMADSEED` | Sports | 444 | 0 | 0.0% |

## 4. The 25 series with the most two-sided markets - the ones worth tape

| series | category | markets | two-sided | share |
|---|---|---:|---:|---:|
| `KXMIDTERMMOV` | Elections | 3939 | 3687 | 93.6% |
| `KXMIDTERMVOTETURN` | Elections | 2756 | 2463 | 89.4% |
| `KXARTISTSTREAMSY` | Entertainment | 1097 | 842 | 76.8% |
| `KXNFLSPREAD` | Sports | 793 | 793 | 100.0% |
| `KXHOUSERACE` | Elections | 705 | 704 | 99.9% |
| `KXNFLTOTAL` | Sports | 608 | 608 | 100.0% |
| `KXNFLWINSWEEK` | Sports | 728 | 582 | 79.9% |
| `KXNASDAQ100U` | Financials | 2800 | 581 | 20.8% |
| `KXNCAAFWINS` | Sports | 583 | 528 | 90.6% |
| `KXDJI` | Financials | 420 | 420 | 100.0% |
| `KXNFLWINS` | Sports | 547 | 404 | 73.9% |
| `KXDDR5MS` | Financials | 400 | 390 | 97.5% |
| `KXDDR5EMS` | Financials | 400 | 373 | 93.2% |
| `KXMLSSCORE` | Sports | 450 | 329 | 73.1% |
| `KXNFLTSPEC` | Sports | 304 | 304 | 100.0% |
| `KXITFMATCH` | Sports | 282 | 282 | 100.0% |
| `KXLOLMAP` | Sports | 282 | 282 | 100.0% |
| `KXVOTEPRIMARY` | Elections | 386 | 259 | 67.1% |
| `KXNBAWINS` | Sports | 312 | 249 | 79.8% |
| `KXINXU` | Financials | 420 | 227 | 54.0% |
| `KXNCAAFSPREAD` | Sports | 219 | 219 | 100.0% |
| `KXMLBTEAMTOTAL` | Sports | 210 | 210 | 100.0% |
| `KXFEDFUNDSYEAR` | Economics | 210 | 210 | 100.0% |
| `KXCS2MAP` | Sports | 208 | 208 | 100.0% |
| `KXITFWMATCH` | Sports | 188 | 186 | 98.9% |

## 5. How much moves in 300 seconds - the change-only saving

| | |
|---|---|
| markets in both sweeps | 768262 |
| quote CHANGED | **19354 (2.5%)** |
| quote identical | 748908 (97.5%) |
| markets that appeared between sweeps | 23081 |

Writing only the rows that changed therefore costs about **2.5%** of writing all of them. That is measured on two real sweeps 300 seconds apart, not assumed - and it is the single decision that makes recording the whole exchange fit on disk.

| interval | full rows/day | change-only rows/day | GB/day at 110 B/row |
|---|---:|---:|---:|
| 300 s | 226026432 | 5694041 | **0.6** |
| 600 s | 113013216 | 2847021 | **0.3** |
| 1800 s | 37671072 | 949007 | **0.1** |
| 3600 s | 18835536 | 474503 | **0.0** |

The change rate is measured at 300 s. At a longer interval more will have moved between snapshots, so the rows/day column above is a FLOOR for the long intervals, not a promise. The recorder reports its real rows/day in `w_cycle` from the first day, and that number replaces this one.

## 6. What this rules out

- **Recording every open market at full orderbook depth.** 784814 markets at ~0.35 s each is 76.3 hours for one pass. Not a tiering choice, an impossibility.
- **Recording the Exotics families at all.** They are the great majority of open markets and almost none of them carry a quote. See the table in section 3.

