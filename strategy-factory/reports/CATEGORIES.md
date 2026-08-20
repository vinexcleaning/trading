# EVERY CATEGORY ON KALSHI — and whether a strategy could be tested there

**Built by `strategy-factory/src/categories.py` from the exchange census of 2026-08-18 and the tape recorded since.** Rebuilt, never hand-edited.

This file exists because of one sentence of his, quoted in mailbox 001: *"I tell the factory chat to find me a bunch of strategies. Instead we'll end up doing it to find me one really good market and find all the strategies within that market. But I wanted to do that with ALL the markets."*

> **A category dismissed without a written reason is a category that was skipped.** So every category gets a row and a verdict, including the ones that are obviously hopeless, and the reason is written out.

## The table

| category | families | markets | two-sided | on tape | full depth | new/day | charge makers | settles in | VERDICT |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| **Sports** | 920 | 42106 | 25282 | 875 | 9 | 11310 | 66 | hours to days | **YES** |
| **Elections** | 593 | 11387 | 9995 | 588 | 4 | 45 | 0 | months | **SLOW — testable, not inside a month** |
| **Financials** | 486 | 10050 | 6712 | 481 | 4 | 4215 | 3 | hours to days | **YES** |
| **Entertainment** | 308 | 6609 | 4422 | 296 | 4 | 397 | 7 | weeks to months | **YES** |
| **Economics** | 240 | 3183 | 2502 | 237 | 4 | 75 | 10 | weeks to months | **YES** |
| **Politics** | 478 | 2107 | 1967 | 474 | 4 | 10 | 0 | weeks to months | **YES** |
| **Science and Technology** | 127 | 917 | 761 | 127 | 3 | 3 | 1 | months | **SLOW — testable, not inside a month** |
| **Commodities** | 37 | 1288 | 627 | 35 | 3 | 5343 | 0 | days to weeks | **YES** |
| **Climate and Weather** | 100 | 967 | 541 | 99 | 3 | 1700 | 0 | same day | **YES** |
| **Mentions** | 30 | 533 | 510 | 30 | 3 | 10 | 0 | days to weeks | **YES** |
| **Crypto** | 78 | 4010 | 460 | 73 | 4 | 49584 | 1 | minutes to hours | **YES** |
| **Companies** | 36 | 394 | 362 | 35 | 3 | 0 | 0 | weeks to months | **UNMEASURABLE - nothing new is minted** |
| **?** | 2 | 202 | 107 | 2 | 2 | 0 | 0 | unknown | **UNMEASURABLE - nothing new is minted** |
| **Exotics** | 2 | 701056 | 16 | 0 | 0 | 0 | 0 | unknown | **NO — not recorded** |
| **World** | 3 | 3 | 3 | 3 | 3 | 0 | 0 | months | **WEAK — too few two-sided markets** |
| **Social** | 2 | 2 | 2 | 2 | 2 | 0 | 0 | months | **WEAK — too few two-sided markets** |

## The written reason for every verdict — including the obvious ones

### Sports — YES

25282 two-sided markets across 920 families, settling in hours to days, and recorded on tape.

Biggest families by two-sided markets: `KXNFLSPREAD`, `KXNFLTOTAL`, `KXNFLWINSWEEK`.

45 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Elections — SLOW — testable, not inside a month

real two-sided markets (9995), but they settle in months. Specs here are written and queued, and saying so now is a prediction rather than an excuse offered in September.

Biggest families by two-sided markets: `KXMIDTERMMOV`, `KXMIDTERMVOTETURN`, `KXHOUSERACE`.

5 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Financials — YES

6712 two-sided markets across 486 families, settling in hours to days, and recorded on tape.

Biggest families by two-sided markets: `KXNASDAQ100U`, `KXDJI`, `KXDDR5MS`.

5 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Entertainment — YES

4422 two-sided markets across 308 families, settling in weeks to months, and recorded on tape.

Biggest families by two-sided markets: `KXARTISTSTREAMSY`, `KXRT`, `KXPERFORMVS`.

12 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Economics — YES

2502 two-sided markets across 240 families, settling in weeks to months, and recorded on tape.

Biggest families by two-sided markets: `KXFEDFUNDSYEAR`, `KXNOMGDPGROWTH`, `KXUSCPIYEAR`.

3 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Politics — YES

1967 two-sided markets across 478 families, settling in weeks to months, and recorded on tape.

Biggest families by two-sided markets: `KXFUNDRAISING`, `KXNYCSTAT`, `KXTRUMPPARDONS`.

4 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Science and Technology — SLOW — testable, not inside a month

real two-sided markets (761), but they settle in months. Specs here are written and queued, and saying so now is a prediction rather than an excuse offered in September.

Biggest families by two-sided markets: `KXH200MON`, `KXEBOLACOUNTRY`, `KXNOBELPHYSICS`.

### Commodities — YES

627 two-sided markets across 37 families, settling in days to weeks, and recorded on tape.

Biggest families by two-sided markets: `KXWTI`, `KXSILVERH`, `KXGOLDH`.

2 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Climate and Weather — YES

541 two-sided markets across 100 families, settling in same day, and recorded on tape.

Biggest families by two-sided markets: `KXHURRICANE`, `KXRAINWKND`, `KXRAIN`.

1 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Mentions — YES

510 two-sided markets across 30 families, settling in days to weeks, and recorded on tape.

Biggest families by two-sided markets: `KXFEDMENTION`, `KXSECPRESSMENTION`, `KXTRUMPSAY`.

### Crypto — YES

460 two-sided markets across 78 families, settling in minutes to hours, and recorded on tape.

Biggest families by two-sided markets: `KXBTCD`, `KXBTCY`, `KXBTC`.

5 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### Companies — UNMEASURABLE - nothing new is minted

MEASURED ON THE TAPE, not read off the metadata: **0 new markets in 2.0 days of recording, 0.0 a day**. At that rate the 100 settled units a forward test needs would take over a year, and that is before any of them settles. Two independent methods agree here - 36 of 36 quoted families also carry a non-recurring `frequency` on Kalshi's own metadata. ⚠ This says we CANNOT FIND OUT, not that the markets are efficient. LEDGER K012 is the warning: 'economics markets are killed on recurrence' was read as 'there is no edge there', and those are opposite sentences.

Biggest families by two-sided markets: `KXHOODA`, `KXTSLAA`, `KXSPOTA`.

1 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### ? — UNMEASURABLE - nothing new is minted

MEASURED ON THE TAPE, not read off the metadata: **0 new markets in 2.0 days of recording, 0.0 a day**. At that rate the 100 settled units a forward test needs would take over a year, and that is before any of them settles. Two independent methods agree here - 2 of 2 quoted families also carry a non-recurring `frequency` on Kalshi's own metadata. ⚠ This says we CANNOT FIND OUT, not that the markets are efficient. LEDGER K012 is the warning: 'economics markets are killed on recurrence' was read as 'there is no edge there', and those are opposite sentences.

Biggest families by two-sided markets: `KXMLBWINS`, `KXNEWOUTBREAK`.

### Exotics — NO — not recorded

no family cleared the recorder's bar, so no tape accrues.

Biggest families by two-sided markets: `KXMVECROSSCATEGORY`, `KXMVESPORTSMULTIGAMEEXTENDED`.

2 family/families in this category were dropped from the recorder. The reason and the counts are in `TIERS.md`; a drop is a recording priority, never a verdict on the family (GUARDS #15).

### World — WEAK — too few two-sided markets

only 3 two-sided markets across the whole category. A forward test needs 100 settled units to be judged, so this cannot produce an answer at any speed.

Biggest families by two-sided markets: `KXBANTRANS`, `EUEXPANSION`, `EUEXIT`.

### Social — WEAK — too few two-sided markets

only 2 two-sided markets across the whole category. A forward test needs 100 settled units to be judged, so this cannot produce an answer at any speed.

Biggest families by two-sided markets: `KXMICHELINNYC3`, `KXBANDANTES`.

## What is on tape, by category, right now

| category | price rows recorded |
|---|---:|
| Sports | 1,607,860 |
| Financials | 303,735 |
| Crypto | 257,630 |
| Elections | 181,884 |
| Entertainment | 134,731 |
| Commodities | 77,202 |
| Economics | 70,715 |
| Climate and Weather | 47,102 |
| Politics | 44,793 |
| (unclassified) | 29,596 |
| Mentions | 24,513 |
| Science and Technology | 23,388 |
| Companies | 6,193 |
| World | 54 |
| Social | 51 |

## The categories a strategy CAN be tested in

- **Testable inside a month (9):** Climate and Weather, Commodities, Crypto, Economics, Entertainment, Financials, Mentions, Politics, Sports
- **Testable, but not inside a month (2):** Elections, Science and Technology
- **Not testable, with the reason above (5):** ?, Companies, Exotics, Social, World

**The quota follows from this list.** Every category in the first two groups needs at least one strategy spec before a second one is written for any category. `py -3 strategy-factory/src/spec.py --coverage` checks it and names what is missing.

