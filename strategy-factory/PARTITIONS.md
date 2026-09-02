# WHICH KALSHI FAMILIES ACTUALLY PARTITION — a reference fact, not a result

**Measured 2026-09-02 from settlement outcomes on recorded tape.** Rebuilt by `strategy-factory/src/partitions_doc.py`; do not hand-edit.

## The question this answers in one lookup

> **Can I buy every outcome of this event and be guaranteed exactly one payout?**

If yes, sum-to-one arithmetic applies and a complete set costing under a dollar is real money. **If no, buying the whole set is a BET** — it can pay nothing, or pay several times over.

⚠ **This is the exact distinction that retracted LEDGER C014** — 464 claimed bucket-sum arbitrages, every one withdrawn, because the ladder was not a partition. It also caught a fake finding of mine on 2026-09-01: an *"8 cent edge on 6 legs"* of `KXEPLTOTAL`, which is a nested *Over 0.5 / Over 1.5 / Over 2.5* ladder where several legs are true at once.

## How it was decided — by measurement, never by product name

A family qualifies only if **every** settled event in it produced **exactly one** YES, over at least five events. **One lucky event cannot qualify a family:** a single 1-0 football match produces exactly one YES on a nested goals ladder and means nothing.

| | count |
|---|---:|
| families measured | 51 |
| **partitions** | **19** |
| not partitions | 32 |

## PARTITIONS — buying the whole set pays exactly once

| family | settled events measured |
|---|---:|
| `KXITFMATCH` | 1032 |
| `KXITFWMATCH` | 714 |
| `KXBTC` | 234 |
| `KXSOLE` | 234 |
| `KXATPMATCH` | 173 |
| `KXWTAMATCH` | 155 |
| `KXVALORANTGAME` | 55 |
| `KXMLSSCORE` | 31 |
| `KXUECLGAME` | 25 |
| `KXNFLGAME` | 16 |
| `KXLALIGAGAME` | 14 |
| `KXLALIGASCORE` | 14 |
| `KXUCLGAME` | 14 |
| `KXUELGAME` | 12 |
| `KXEPLGAME` | 10 |
| `KXHIGHCHI` | 10 |
| `KXHIGHNY` | 10 |
| `KXSERIEAGAME` | 10 |
| `KXLIGUE1GAME` | 9 |

## NOT PARTITIONS — buying the whole set is a bet

| family | settled events | YES per event |
|---|---:|---|
| `KXBTCD` | 234 | many |
| `KXETHD` | 234 | many |
| `KXSOLD` | 234 | many |
| `KXGOLDH` | 177 | many |
| `KXSILVERH` | 177 | many |
| `KXDJI` | 56 | many |
| `KXINXU` | 56 | many |
| `KXNASDAQ100U` | 56 | many |
| `KXARTISTSTREAMSY` | 44 | {1: 34, 2: 9, 3: 1} |
| `KXVOTEPRIMARY` | 29 | many |
| `KXUECLTOTAL` | 25 | {0: 5, 1: 3, 2: 7, 3: 1, 4: 7, 5: 1, 6: 1} |
| `KXNFLSPREAD` | 16 | {0: 1, 1: 1, 2: 2, 3: 1, 8: 1, 11: 3, 12: 7} |
| `KXNFLTOTAL` | 16 | many |
| `KXLALIGABTTS` | 14 | {0: 7, 1: 7} |
| `KXLALIGATEAMTOTAL` | 14 | {0: 2, 1: 3, 2: 4, 3: 1, 4: 2, 5: 2} |
| `KXLALIGATOTAL` | 14 | {0: 2, 1: 3, 2: 4, 3: 1, 4: 2, 5: 2} |
| `KXUCLBTTS` | 14 | {0: 4, 1: 10} |
| `KXUCLTOTAL` | 14 | {0: 1, 2: 3, 3: 4, 4: 4, 5: 2} |
| `KXUELTOTAL` | 12 | {0: 1, 1: 3, 2: 1, 3: 4, 4: 2, 7: 1} |
| `KXEPLBTTS` | 10 | {0: 6, 1: 4} |
| `KXEPLTOTAL` | 10 | {1: 1, 2: 2, 3: 4, 4: 2, 5: 1} |
| `KXRAIN` | 10 | {1: 1, 3: 2, 4: 5, 6: 2} |
| `KXSERIEABTTS` | 10 | {0: 6, 1: 4} |
| `KXSERIEATOTAL` | 10 | {1: 3, 2: 3, 3: 2, 4: 1, 5: 1} |
| `KXLIGUE1BTTS` | 9 | {0: 6, 1: 3} |
| `KXLIGUE1TOTAL` | 9 | {0: 2, 1: 1, 2: 2, 4: 3, 7: 1} |
| `KXWTI` | 7 | {6: 1, 12: 1, 16: 1, 21: 2, 22: 2} |
| `KXRT` | 5 | {1: 1, 5: 1, 6: 2, 14: 1} |
| `KXTRUMPSAY` | 2 | {15: 1, 19: 1} |
| `KXRAINWKND` | 1 | {8: 1} |
| `KXWTIMAX` | 1 | {4: 1} |
| `KXZECMAXY` | 1 | {7: 1} |

## What this does NOT say

- **Not that the second list is untradeable** — only that *sum-to-one* arithmetic does not apply to it. A nested ladder has its own identity (a higher strike must be worth less than a lower one), tested separately and also empty.
- **Not permanent.** Measured from families that settled inside the recording window. A family absent here was **not measured**, which `GUARDS.md` #15 and #25 both insist is different from being absent from the exchange.
- **Not a claim about size.** A partition can be real and still offer nothing tradeable; on this tape the whole structure offered about a dollar across 14 days.

