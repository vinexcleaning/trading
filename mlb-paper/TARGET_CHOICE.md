# Do over/under and first-inning beat moneyline as the target?

**Short answer: no — and the 249 number is not what it looks like.**

`SCOREBOARD.md` page 5 flags **249 over/under markets and 71 first-inning
markets recorded and never examined**. Both are now examined. Measured
2026-08-07 01:05–01:15 UTC against the live Kalshi and Pinnacle books.
`reports/market_census.json`, `reports/target_choice_multiplicative.json`.

---

## 1. The 249 is ~23 games, not 249 events

`KXMLBTOTAL` is a **ladder**. Kalshi lists one contract per half-run threshold —
"Over 1.5 runs", "Over 2.5 runs", … out to "Over 13.5 runs".

| series | open markets | distinct games | **strikes per game** |
|---|---|---|---|
| `KXMLBGAME` | 98 | 49 | **2** (the two sides of one game) |
| `KXMLBTOTAL` | 134 | 12 | **11** (max 13) |
| `KXMLBRFI` | 46 | 46 | **1** |
| `KXMLBSPREAD` | 77 | 12 | 6 |
| `KXMLBF5TOTAL` | 84 | 12 | 7 |

Eleven rungs on one game are eleven views of **one** run total. GUARDS says it
plainly: *a 10-strike ladder is one temperature reading, not ten markets.*

> **249 `KXMLBTOTAL` tickers ≈ 23 games. 71 `KXMLBRFI` tickers = 71 games.**
> The first-inning number is honest; the over/under number is inflated about
> elevenfold. Neither adds events faster than moneyline, because all three come
> off the same ~12–15 games a day.

## 2. First-inning is killed on cost and on capacity, twice over

| | `KXMLBGAME` | `KXMLBTOTAL` | **`KXMLBRFI`** |
|---|---|---|---|
| median quoted spread | 2.0¢ | 2.0¢ | **9.0¢** |
| p90 spread | 4.0¢ | 3.0¢ | **18.0¢** |
| cost to enter and hold to settle | 3.0¢ | 3.0¢ | **6.5¢** |
| round trip | 6.0¢ | 6.0¢ | **13.0¢** |
| **median size at the touch** (min side) | 68.5 | **1,029** | **2** |
| free sharp reference price | Pinnacle ML | Pinnacle totals | **NONE** |

`KXMLBRFI` costs **2.2× more to trade** than either alternative and has **two
contracts** at the touch. `market-selection/SHORTLIST.md` called it *"the
deepest book on the list"* at **301,578 contracts**; `mlb/PROGRESS.md` already
re-measured that as an **08:00 UTC snapshot** which read 19 contracts and an
8¢ spread by game time. This measurement is a third reading and agrees with the
second. **The 301,578 figure should not be used again.**

And there is the thing that made it attractive in the first place, which is the
same thing that kills it: it has **no free reference price anywhere** — checked
across ESPN, every odds provider, 9,802 prop entries, Action Network, Covers,
ScoresAndOdds and RotoWire. That was sold as *nobody is watching*. It is also
*you cannot check yourself*, and the one honest published model of it
(`lucasreydman/sharprfi`, 1,344 games) beats the base rate by **0.003 Brier** —
0.2447 against 0.2475. A near-coin-flip, modelled at the edge of measurement,
against a 6.5¢ cost bar.

**`KXMLBRFI` is dropped.**

## 3. Over/under ties moneyline on cost and beats it 15× on depth

`KXMLBTOTAL` has the **same 2.0¢ spread and 3.0¢ entry cost** as the moneyline
and **1,029 contracts at the touch against 68.5** — fifteen times the size. On
the two axes a paper test cares about most, totals are at least as good.

Two further points genuinely favour totals, and they are the reason it is kept:

- **Pinnacle is less sure about runs than about winners.** Measured on the same
  games at the same moment: overround **4.01 pp on totals** against **2.55 pp on
  the moneyline**, and a maximum stake of **$1,875 against $2,500**. A sharp
  book's vig and its limit are its own statement of confidence.
- **Everything in the pre-match brief is about runs.** Park, elevation, wind
  direction, temperature, bullpen fatigue, a tired lineup — these change *how
  many runs score* far more directly than they change *who wins*. Pointing
  run-shaped information at a winner market throws most of it away.

## 4. But the deciding test comes back zero on both

The feasibility statistic `bot-hunt` measured as **q = 0 of 17** on the
moneyline, extended to totals for the first time. Buy YES at the ask or NO at
(100 − bid); fair value is the de-vigged Pinnacle price; cost is the Kalshi
taker fee plus 1¢ slippage.

| | joined | games | median vig | **qualifying** | best net edge |
|---|---|---|---|---|---|
| `KXMLBGAME` vs de-vigged Pinnacle | 20 | 10 | 2.55 pp | **0 (0.0%)** | **−1.82¢** |
| `KXMLBTOTAL` vs de-vigged Pinnacle | 38 | 10 | 4.01 pp | **0 (0.0%)** | **−1.63¢** |

Not one market on either family is positive, and the **best** case — chosen with
hindsight across every rung of every game — is still negative. Kalshi's MLB
price is the de-vigged sharp line to within about a cent, on runs as well as on
winners. That is now the fifth independent confirmation in this repo.

### The placebo, which is the part that makes the zero mean something

The same code, run with each Kalshi game deliberately joined to a **different**
Pinnacle game:

| | qualifying | best net edge |
|---|---|---|
| `KXMLBGAME` **placebo** | **8 of 18 (44%)** | **+24.76¢** |
| `KXMLBTOTAL` **placebo** | **28 of 34 (82%)** | **+20.49¢** |

A wrong join manufactures a large, confident, entirely fake edge. **Any future
MLB result that does not clear its own mismatched-pair placebo is a join error,
not a finding.** This is not hypothetical — the first version of
`target_choice.py` reported an 80% qualifying rate and a 57¢ best edge because
it matched on the club pair without the start time, and baseball teams play each
other three days running. It was reporting Tuesday's Kalshi price against
Thursday's Pinnacle line.

## 5. Verdict, and what actually gets run

**Neither beats moneyline outright. First-inning is dropped. Over/under is kept
as a co-target, assigned by mentality rather than run in parallel.**

| mentality | target | why that target |
|---|---|---|
| M1 starting pitcher | `KXMLBGAME` | the starter is what the winner line is built on |
| M2 park and air | `KXMLBTOTAL` | wind and elevation move runs, not winners |
| M3 bullpen fatigue | `KXMLBTOTAL` | a spent bullpen concedes runs |
| M4 the early window | `KXMLBGAME` | the widest, least-anchored quote |
| M5 the lineup drop | `KXMLBGAME` | a discrete, timestamped repricing event |

Each mentality trades **one** pre-registered market on the **same shared pool of
games**, so the game pool is common and the multiplicity count does not double.
Assigning the target by mechanism is a pre-registration decision made **before
any return exists** and recorded in `PREREGISTRATION.md`.

> **The bar all five now face, stated once.** §4 is not a side note. It says the
> executable Kalshi price already equals the de-vigged sharp consensus. So a
> mentality does not have to beat *Kalshi* — it has to beat **Pinnacle**, using
> only free public information, by more than 3.0¢. Nothing in this programme has
> ever cleared a bar that shape. The honest prior is that none of these will
> either, and the test is built to detect that quickly rather than to flatter it.
