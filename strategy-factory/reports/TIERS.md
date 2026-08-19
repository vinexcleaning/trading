# THE RECORDER'S TIER LIST - and everything it drops

**Built 2026-08-19T04:27:19Z by `strategy-factory/src/tiers.py`** from a census of every Kalshi series and a full sweep measuring which markets carry a real quote. Not hand-written, and rebuilt rather than edited.

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
| 5 | `KXMIDTERMMOV` | Elections | 3687 | one_off | no |
| 20 | `KXMIDTERMVOTETURN` | Elections | 2463 | one_off | no |
| 6 | `KXNASDAQ100U` | Financials | 581 | hourly | no |
| 35 | `KXHOUSERACE` | Elections | 704 | one_off | no |
| 21 | `KXDJI` | Financials | 420 | one_off | no |
| 8 | `KXARTISTSTREAMSY` | Entertainment | 842 | annual | no |
| 36 | `KXDDR5MS` | Financials | 390 | monthly | no |
| 49 | `KXDDR5EMS` | Financials | 373 | monthly | no |
| 9 | `KXFEDFUNDSYEAR` | Economics | 210 | annual | no |
| 4 | `KXNFLSPREAD` | Sports | 793 | custom | yes |
| 24 | `KXNOMGDPGROWTH` | Economics | 143 | annual | no |
| 39 | `KXUSCPIYEAR` | Economics | 130 | annual | no |
| 48 | `KXVOTEPRIMARY` | Elections | 259 | one_off | no |
| 19 | `KXNFLTOTAL` | Sports | 608 | custom | yes |
| 52 | `KXGDPYEAR` | Economics | 118 | custom | no |
| 34 | `KXNFLWINSWEEK` | Sports | 582 | custom | no |
| 47 | `KXNCAAFWINS` | Sports | 528 | annual | no |
| 13 | `KXWTI` | Commodities | 114 | daily | no |
| 23 | `KXRT` | Entertainment | 180 | custom | no |
| 38 | `KXPERFORMVS` | Entertainment | 126 | one_off | no |
| 51 | `KXROLEATEVENTCOACHELLA` | Entertainment | 114 | one_off | no |
| 7 | `KXFUNDRAISING` | Politics | 84 | one_off | no |
| 17 | `KXMLBWINS` | ? | 106 | ? | no |
| 12 | `KXBTCD` | Crypto | 33 | hourly | no |
| 28 | `KXSILVERH` | Commodities | 38 | hourly | no |
| 27 | `KXBTCY` | Crypto | 28 | annual | no |
| 22 | `KXNYCSTAT` | Politics | 53 | one_off | no |
| 37 | `KXTRUMPPARDONS` | Politics | 52 | one_off | no |
| 42 | `KXBTC` | Crypto | 26 | hourly | no |
| 43 | `KXGOLDH` | Commodities | 31 | hourly | no |
| 50 | `KXFEDERALCHARGE` | Politics | 40 | annual | no |
| 14 | `KXHOODA` | Companies | 35 | one_off | no |
| 11 | `KXHURRICANE` | Climate and Weather | 23 | custom | no |
| 15 | `KXFEDMENTION` | Mentions | 44 | custom | no |
| 26 | `KXRAINWKND` | Climate and Weather | 20 | weekly | no |
| 41 | `KXRAIN` | Climate and Weather | 18 | daily | no |
| 54 | `KXHURRICANENAMES` | Climate and Weather | 18 | custom | no |
| 1 | `KXEPLGAME` | Sports | 60 | custom | yes |
| 29 | `KXTSLAA` | Companies | 23 | one_off | no |
| 44 | `KXSPOTA` | Companies | 23 | one_off | no |
| 10 | `KXH200MON` | Science and Technology | 28 | monthly | no |
| 30 | `KXSECPRESSMENTION` | Mentions | 30 | custom | no |
| 25 | `KXEBOLACOUNTRY` | Science and Technology | 25 | one_off | no |
| 40 | `KXNOBELPHYSICS` | Science and Technology | 24 | annual | no |
| 53 | `KXB200MAX` | Science and Technology | 23 | annual | no |
| 55 | `KXUSRETAIL` | Economics | 9 | monthly | no |
| 45 | `KXTRUMPSAY` | Mentions | 27 | one_off | no |
| 2 | `KXUCLGAME` | Sports | 21 | custom | yes |
| 32 | `KXNEWOUTBREAK` | ? | 1 | ? | no |
| 18 | `KXMICHELINNYC3` | Social | 1 | annual | no |
| 16 | `KXBANTRANS` | World | 1 | one_off | no |
| 33 | `KXBANDANTES` | Social | 1 | one_off | no |
| 31 | `EUEXPANSION` | World | 1 | custom | no |
| 46 | `EUEXIT` | World | 1 | custom | no |
| 3 | `KXVALORANTGAME` | Sports | 40 | custom | no |

### The 3 PINNED families, and what they displaced

| series | category | why it is pinned |
|---|---|---|
| `KXEPLGAME` | Sports | Premier League - same argument, named in the same sentence |
| `KXUCLGAME` | Sports | Champions League - his strongest sport, and the group stage starting in September is the specific data soccer/CLOSED.md says its one live descendant was waiting for |
| `KXVALORANTGAME` | Sports | his only esport, and the only one he can sanity-check |

**A pin overrides a measurement, so it costs something and the cost is named.** These 3 families consume 71 of the 1200 request budget. What they displaced is the 3 lowest-scoring families that would otherwise have been filled by score - listed at the bottom of the tier A table below as the ones just outside the line. **Nothing allocated by the category quota was touched**, because pins are taken before the quota rather than after it: a pin can push out a score-filled family and can never push out a category's guaranteed share.

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

