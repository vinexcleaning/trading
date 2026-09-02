# STRUCTURAL ARBITRAGE — two identities checked, and both come back empty

**Run 2026-09-02 02:00 UTC by `strategy-factory/src/structural.py`.** Neither test needs a view on any game: both are arithmetic identities, so a violation would be money that does not depend on who wins.

**Every number below is measured on the tape recorded 2026-08-18 to 2026-09-01 — 14 days, 3,438 Kalshi families, 22.2 million price rows.** Nothing here is a fact about the exchange in general; it is a fact about those 14 days.

> **THE HEADLINE IS A NULL, AND IT IS THE EXPECTED ONE.** Both structures were untested on this exchange. Neither produced tradeable money. That is worth as much as a positive would have been, because both are now closed with a number rather than left open as a maybe.

## TEST A — sum-to-one on multi-outcome events

An event whose outcomes are mutually exclusive and exhaustive must cost at least a dollar to buy completely.

### The partition is PROVED, not assumed — this is the C014 fix

LEDGER **C014** claimed **464** bucket-sum arbitrages and retracted every one: the ladder was **partial**, 3 of 80 buckets, and buying 3 of 80 pays a dollar only if the answer lands in those 3. **That is a bet, not an arbitrage.**

So an event qualifies here only if **every one of its markets settled AND exactly one resolved YES** — a measurement of the partition on that occasion, not an inference from the product name.

> ⚠ **MY FIRST VERSION OF THIS TEST WAS WRONG AND WOULD HAVE REPORTED A FAKE ARBITRAGE.** It qualified an EVENT when exactly one of its markets resolved YES. `KXEPLTOTAL` legs are *Over 0.5, Over 1.5, Over 2.5* - **nested thresholds**, where several are true at once. Across ten settled events its yes-counts were **{1:1, 2:2, 3:4, 4:2, 5:1}** - exactly one of the ten produced a single YES, because that game finished 1-0. My test caught that one lucky game, called the family a partition, and flagged an **"8 cent edge on 6 legs"**. Buying all six legs of a nested ladder pays **once per true leg** - 300c on three goals, 0c on none. **That is a bet, not an arbitrage**, and it is C014 arriving in a new costume in my own code.

**The test is now at the SERIES level:** a family qualifies only if **every** settled event in it produced exactly one YES, over at least five events. One lucky event can no longer qualify a family.

| | count |
|---|---:|
| events with settlements | 4328 |
| not all legs settled — excluded | 35 |
| **families that ARE partitions** | **19** |
| families rejected as not partitions | 32 |
| **usable partition events (2+ legs)** | **2772** |

**Which families passed, and which did not, is a finding on its own** - nothing in this repo previously knew which Kalshi events partition:

| family | settled events | yes-count per event |
|---|---:|---|
| `KXITFMATCH` | 1032 | always exactly 1 — **partition** |
| `KXITFWMATCH` | 714 | always exactly 1 — **partition** |
| `KXBTC` | 234 | always exactly 1 — **partition** |
| `KXSOLE` | 234 | always exactly 1 — **partition** |
| `KXATPMATCH` | 173 | always exactly 1 — **partition** |
| `KXWTAMATCH` | 155 | always exactly 1 — **partition** |
| `KXVALORANTGAME` | 55 | always exactly 1 — **partition** |
| `KXMLSSCORE` | 31 | always exactly 1 — **partition** |
| `KXUECLGAME` | 25 | always exactly 1 — **partition** |
| `KXNFLGAME` | 16 | always exactly 1 — **partition** |
| `KXBTCD` | 234 | many — not a partition |
| `KXETHD` | 234 | many — not a partition |
| `KXSOLD` | 234 | many — not a partition |
| `KXGOLDH` | 177 | many — not a partition |
| `KXSILVERH` | 177 | many — not a partition |
| `KXDJI` | 56 | many — not a partition |
| `KXINXU` | 56 | many — not a partition |
| `KXNASDAQ100U` | 56 | many — not a partition |

### Result

| | |
|---|---:|
| event-instants examined | 92093 |
| instants with **every leg quoted** | 72027 |
| sets costing under a dollar after fees | **32** |
| **...with any size offered** | **18** |

| event | legs | sum of asks | fees | edge | contracts offered |
|---|---:|---:|---:|---:|---:|
| `KXATPMATCH-26AUG24GEANAG` | 2 | 97.0c | 2.3c | **0.7c** | 10 |
| `KXITFMATCH-26AUG23SENBAR` | 2 | 96.0c | 3.3c | **0.7c** | 3 |
| `KXITFMATCH-26AUG24GARGOL` | 2 | 98.0c | 1.4c | **0.6c** | 38 |
| `KXITFWMATCH-26AUG24STAVEL` | 2 | 97.0c | 2.5c | **0.5c** | 2 |
| `KXITFMATCH-26AUG18KOKWER` | 2 | 99.0c | 0.7c | **0.3c** | 3.02 |
| `KXITFWMATCH-26AUG23BOJRAD` | 2 | 97.0c | 2.8c | **0.2c** | 11 |
| `KXITFMATCH-26AUG23ALVCER` | 2 | 97.0c | 2.8c | **0.2c** | 11 |
| `KXITFWMATCH-26AUG23BOJRAD` | 2 | 97.0c | 2.8c | **0.2c** | 11 |
| `KXITFMATCH-26AUG19ENAGAR` | 2 | 99.0c | 0.9c | **0.1c** | 225 |
| `KXITFWMATCH-26AUG23BOJRAD` | 2 | 97.0c | 2.9c | **0.1c** | 21 |
| `KXITFMATCH-26AUG19MARBIO` | 2 | 99.0c | 1.0c | **0.0c** | 322 |
| `KXITFMATCH-26AUG18PANHAI` | 2 | 99.0c | 1.0c | **0.0c** | 564 |
| `KXITFMATCH-26AUG20MICBER` | 2 | 99.0c | 1.0c | **0.0c** | 127 |
| `KXITFMATCH-26AUG22LOGVAN` | 2 | 97.0c | 3.0c | **0.0c** | 87 |
| `KXITFMATCH-26AUG18PANHAI` | 2 | 99.0c | 1.0c | **0.0c** | 92.03 |

**Total money available in every violation on this tape, added up: $1.13.**

**That is the answer, and it is a null with a number on it.** Over 72027 fully-quoted event-instants in 14 days, the whole sum-to-one structure offered **$1.13 in total**, across 18 moments, in KXITFMATCH (13), KXITFWMATCH (4), KXATPMATCH (1). The largest single opportunity was 564 contracts.

**Every one is a TWO-LEG market** - one player or the other. Buying both sides of a two-way market is the *cover both sides* hedge that mailbox 009 already kills by arithmetic: it costs two fees and cancels the leg exactly. These clear it only because the pair happened to be quoted below par for a cycle, and the amounts are what they are.

⚠ **A violation with size is still not money until the size is real.** `BH024` produced **1,292 fake cross-venue arbitrages** from stale quotes, and `K007` found 52 genuine ladder violations with **0 tradeable size**. Anything above needs a live re-probe before it is believed.

## TEST B — a spread implies its moneyline

Winning by more than 7.5 points implies winning, so `ask(spread) + fee` must never sit below `bid(moneyline) − fee` for the same team in the same game. Kalshi lists the two in **separate families** and nobody has crossed them before.

The violation is the **narrow** event priced ABOVE the **wide** one - sell the spread, buy the moneyline, and whenever the spread pays the moneyline pays too.

> ⚠ **I HAD THIS INEQUALITY BACKWARDS AND THE FIRST RUN "FOUND" 105,322 ARBITRAGES IN 122,658 INSTANTS - 86 out of 100.** An 86% hit rate on an arithmetic identity is never a market finding; it is the test measuring itself, and **the size of the number is the tell.** v1 fired when the moneyline bid was above the spread ask - but winning by more than 7.5 is a subset of winning, so the moneyline *should* be dearer. That condition is the identity HOLDING. Corrected below.

| pairing | games shared | market pairs | instants checked | violations |
|---|---:|---:|---:|---:|
| `KXNFLSPREAD` → moneyline | 48 | 350 | 131186 | **0** |
| `KXEPLSPREAD` → moneyline | 30 | 138 | 17446 | **0** |
| `KXUCLSPREAD` → moneyline | 11 | 56 | 2680 | **0** |
| `KXLALIGASPREAD` → moneyline | 36 | 166 | 19243 | **0** |
| `KXSERIEASPREAD` → moneyline | 30 | 135 | 13650 | **0** |

**184205 price instants checked across five competitions, 0 violations.**

**Whole-number lines were skipped, and that is not a detail.** A line of exactly 7 can PUSH, which breaks the implication entirely. 2,826 spread strikes were read off this tape on 2026-08-20 and **not one is a whole number** — every line is a half point — so the skip removed nothing here, and the check stays in so it fires if Kalshi ever changes.

## What this does NOT establish

- **Not that these structures are impossible** — only that they did not occur, with size, on this tape. `GUARDS.md` #15 and #25: an absence is not a proof.
- **Nothing about markets we do not record.** The recorder covers 3,438 families of about 13,000.
- **Nothing about latency.** Even a real violation has to be hit before it moves, and this repo has measured that wall before: 97.4 out of 100 of a price move was already done by the time a bot saw the news.
- **Test A depends on settlement data**, so it can only judge events that have already settled. A partition that never settled in this window is invisible to it.

