# THE RECORDER'S TIER LIST - and everything it drops

**Built 2026-08-18T23:43:35Z by `strategy-factory/src/tiers.py`** from a census of every Kalshi series and a full sweep measuring which markets carry a real quote. Not hand-written, and rebuilt rather than edited.

## What gets recorded

| tier | what is stored | series | cost per cycle |
|---|---|---:|---|
| **A** | the whole orderbook ladder, both sides | **55** | 1200 requests |
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
| 2 | `KXMIDTERMMOV` | Elections | 3687 | one_off | no |
| 17 | `KXMIDTERMVOTETURN` | Elections | 2463 | one_off | no |
| 3 | `KXNASDAQ100U` | Financials | 581 | hourly | no |
| 32 | `KXHOUSERACE` | Elections | 704 | one_off | no |
| 18 | `KXDJI` | Financials | 420 | one_off | no |
| 5 | `KXARTISTSTREAMSY` | Entertainment | 842 | annual | no |
| 33 | `KXDDR5MS` | Financials | 390 | monthly | no |
| 46 | `KXDDR5EMS` | Financials | 373 | monthly | no |
| 6 | `KXFEDFUNDSYEAR` | Economics | 210 | annual | no |
| 1 | `KXNFLSPREAD` | Sports | 793 | custom | yes |
| 21 | `KXNOMGDPGROWTH` | Economics | 143 | annual | no |
| 36 | `KXUSCPIYEAR` | Economics | 130 | annual | no |
| 45 | `KXVOTEPRIMARY` | Elections | 259 | one_off | no |
| 16 | `KXNFLTOTAL` | Sports | 608 | custom | yes |
| 49 | `KXGDPYEAR` | Economics | 118 | custom | no |
| 31 | `KXNFLWINSWEEK` | Sports | 582 | custom | no |
| 44 | `KXNCAAFWINS` | Sports | 528 | annual | no |
| 10 | `KXWTI` | Commodities | 114 | daily | no |
| 20 | `KXRT` | Entertainment | 180 | custom | no |
| 35 | `KXPERFORMVS` | Entertainment | 126 | one_off | no |
| 48 | `KXROLEATEVENTCOACHELLA` | Entertainment | 114 | one_off | no |
| 4 | `KXFUNDRAISING` | Politics | 84 | one_off | no |
| 14 | `KXMLBWINS` | ? | 106 | ? | no |
| 9 | `KXBTCD` | Crypto | 33 | hourly | no |
| 25 | `KXSILVERH` | Commodities | 38 | hourly | no |
| 24 | `KXBTCY` | Crypto | 28 | annual | no |
| 19 | `KXNYCSTAT` | Politics | 53 | one_off | no |
| 34 | `KXTRUMPPARDONS` | Politics | 52 | one_off | no |
| 39 | `KXBTC` | Crypto | 26 | hourly | no |
| 40 | `KXGOLDH` | Commodities | 31 | hourly | no |
| 53 | `KXWTIMAX` | Commodities | 30 | annual | no |
| 47 | `KXFEDERALCHARGE` | Politics | 40 | annual | no |
| 52 | `KXSOLD` | Crypto | 18 | hourly | no |
| 11 | `KXHOODA` | Companies | 35 | one_off | no |
| 8 | `KXHURRICANE` | Climate and Weather | 23 | custom | no |
| 12 | `KXFEDMENTION` | Mentions | 44 | custom | no |
| 23 | `KXRAINWKND` | Climate and Weather | 20 | weekly | no |
| 38 | `KXRAIN` | Climate and Weather | 18 | daily | no |
| 51 | `KXHURRICANENAMES` | Climate and Weather | 18 | custom | no |
| 26 | `KXTSLAA` | Companies | 23 | one_off | no |
| 41 | `KXSPOTA` | Companies | 23 | one_off | no |
| 7 | `KXH200MON` | Science and Technology | 28 | monthly | no |
| 54 | `KXSBUXA` | Companies | 22 | one_off | no |
| 27 | `KXSECPRESSMENTION` | Mentions | 30 | custom | no |
| 22 | `KXEBOLACOUNTRY` | Science and Technology | 25 | one_off | no |
| 37 | `KXNOBELPHYSICS` | Science and Technology | 24 | annual | no |
| 50 | `KXB200MAX` | Science and Technology | 23 | annual | no |
| 42 | `KXTRUMPSAY` | Mentions | 27 | one_off | no |
| 55 | `KXSOLMINY` | Crypto | 8 | annual | no |
| 29 | `KXNEWOUTBREAK` | ? | 1 | ? | no |
| 15 | `KXMICHELINNYC3` | Social | 1 | annual | no |
| 13 | `KXBANTRANS` | World | 1 | one_off | no |
| 30 | `KXBANDANTES` | Social | 1 | one_off | no |
| 28 | `EUEXPANSION` | World | 1 | custom | no |
| 43 | `EUEXIT` | World | 1 | custom | no |

**54 of the 55 tier A families were allocated by CATEGORY QUOTA** - 4 slots to every category with any two-sided market, handed out before any category got a second helping. The remaining 1 were filled by score. Without the quota the first allocation put 12 of 36 slots in Financials and 8 in Sports and gave **zero** to crypto, weather, politics, companies, science and mentions - and crypto settles in minutes while weather settles same-day, which makes them the two fastest categories to get a real forward answer from.

The score used for the leftover slots is two-sided market count categories `bot-hunt` records **nothing** in - crypto, economics, financials, commodities. Those are the families where this recorder is the only thing that will ever have tape, which was his explicit ask: *crypto, weather, economics, anything*, not sports alone.

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

