# THE RECORDER'S TIER LIST - and everything it drops

**Built 2026-08-18T05:08:40Z by `strategy-factory/src/tiers.py`** from a census of every Kalshi series and a full sweep measuring which markets carry a real quote. Not hand-written, and rebuilt rather than edited.

## What gets recorded

| tier | what is stored | series | cost per cycle |
|---|---|---:|---|
| **A** | the whole orderbook ladder, both sides | **36** | 900 requests |
| **B** | top of book, written only when it changes | **3357** | 3357 requests |

Tier A is expensive because a ladder costs one request per MARKET. Tier B is cheap because a listing costs one request per SERIES no matter how many markets are in it. That asymmetry is the entire reason the tiers exist.

`bot-hunt`'s 19 families are **not touched and not competed with**. 16 of them appear in tier B so the factory has its own top-of-book copy on one clock with everything else, and none of them consume tier A - they are already on tape at full depth.

## What was DROPPED, and why

A drop is a recording priority, never a verdict on the family. GUARDS #15: a single absent reading never establishes that something is dead. The list is re-measured on every rebuild and a family can come back.

| reason | series dropped | open markets in them |
|---|---:|---:|
| combinatorial parlay product | 2 | 701056 |
| no quote on either side when measured | 0 | 0 |
| quoted on one side only, never two-sided | 83 | 2490 |

### The parlay families, named

- `KXMVECROSSCATEGORY` - Exotics - **568219 open markets**, 10 two-sided. MVE Cross Category
- `KXMVESPORTSMULTIGAMEEXTENDED` - Exotics - **132837 open markets**, 6 two-sided. MVE Sport Mutli Game

These two families alone are the great majority of the open markets on the exchange. Recording them would have consumed the entire disk budget on products that almost never have a counterparty.

### The biggest families with no quote at all

| series | category | open markets |
|---|---|---:|

## Tier A, in the order it was chosen

| # | series | category | two-sided markets | frequency | charges makers |
|---:|---|---|---:|---|---|
| 1 | `KXMIDTERMMOV` | Elections | 3687 | one_off | no |
| 2 | `KXMIDTERMVOTETURN` | Elections | 2463 | one_off | no |
| 3 | `KXNASDAQ100U` | Financials | 581 | hourly | no |
| 4 | `KXHOUSERACE` | Elections | 704 | one_off | no |
| 5 | `KXDJI` | Financials | 420 | one_off | no |
| 6 | `KXARTISTSTREAMSY` | Entertainment | 842 | annual | no |
| 7 | `KXDDR5MS` | Financials | 390 | monthly | no |
| 8 | `KXDDR5EMS` | Financials | 373 | monthly | no |
| 9 | `KXFEDFUNDSYEAR` | Economics | 210 | annual | no |
| 10 | `KXINXU` | Financials | 227 | hourly | no |
| 11 | `KXNFLSPREAD` | Sports | 793 | custom | yes |
| 12 | `KXNOMGDPGROWTH` | Economics | 143 | annual | no |
| 13 | `KXUSCPIYEAR` | Economics | 130 | annual | no |
| 14 | `KXVOTEPRIMARY` | Elections | 259 | one_off | no |
| 15 | `KXNFLTOTAL` | Sports | 608 | custom | yes |
| 16 | `KXGDPYEAR` | Economics | 118 | custom | no |
| 17 | `KXNFLWINSWEEK` | Sports | 582 | custom | no |
| 18 | `KXH200MS` | Financials | 136 | one_off | no |
| 19 | `KXGDPNOM` | Economics | 107 | one_off | no |
| 20 | `KXNCAAFWINS` | Sports | 528 | annual | no |
| 21 | `KXB200MS` | Financials | 118 | monthly | no |
| 22 | `KXH100MS` | Financials | 115 | one_off | no |
| 23 | `KXWTI` | Commodities | 114 | daily | no |
| 24 | `KXRTX5090MS` | Financials | 103 | monthly | no |
| 25 | `KXNFLWINS` | Sports | 404 | custom | no |
| 26 | `KXUE` | Economics | 76 | monthly | no |
| 27 | `KXA100MS` | Financials | 89 | one_off | no |
| 28 | `KXRT` | Entertainment | 180 | custom | no |
| 29 | `KXFED` | Economics | 72 | custom | yes |
| 30 | `KXRTX5090WS` | Financials | 79 | weekly | no |
| 31 | `KXMLSSCORE` | Sports | 329 | custom | no |
| 32 | `KXB200WS` | Financials | 74 | weekly | no |
| 33 | `KXNFLTSPEC` | Sports | 304 | custom | no |
| 34 | `KXFEDDECISION` | Economics | 58 | custom | yes |
| 35 | `KXLOLMAP` | Sports | 282 | custom | no |
| 36 | `KXSTATEBALLOTMEASURE` | Elections | 110 | one_off | no |

The ranking is two-sided market count multiplied by a boost for categories `bot-hunt` records **nothing** in - crypto, economics, financials, commodities. Those are the families where this recorder is the only thing that will ever have tape, which was his explicit ask: *crypto, weather, economics, anything*, not sports alone.

## Tier B by category

| category | series in tier B |
|---|---:|
| Sports | 875 |
| Elections | 588 |
| Financials | 481 |
| Politics | 474 |
| Entertainment | 296 |
| Economics | 237 |
| Science and Technology | 127 |
| Climate and Weather | 99 |
| Crypto | 73 |
| Companies | 35 |
| Commodities | 35 |
| Mentions | 30 |
| World | 3 |
| Social | 2 |
| ? | 2 |

