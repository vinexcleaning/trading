# THE SCREENED POOL — every baseball entry idea considered, and what happened to it

**2026-09-03, for `mlb` via `coordinator` mailbox 012.**

Mailbox 012 asks for "the count of how many you screened to produce them, per
the best-of-N rule". **That count is 43, and this file is the count** — not a
number asserted in a summary, but the list itself, so the denominator can be
audited rather than believed.

**43 considered → 17 written as specs → 10 recommended to fill the 10 slots.**

## Why the count matters, in his terms

If you look at 43 ideas and keep the best 10, the best 10 will look good **even
if not one of them is any good** — because they are the best of 43. That is not
a reason to look at fewer ideas; looking at more is how you find things. It is a
reason to write the 43 down, so that when one of the ten looks promising later,
the honest question — *"best of how many?"* — has an answer on file.

---

## The screen, stated before the verdicts

Five filters, in order. A candidate had to pass all five.

1. **Shape.** It must state a signed adjustment in cents to the market's own
   price, from baseball inputs, the way all five live mentalities do. A rival
   win-probability model is a different project and is excluded by
   `MENTALITIES.md` on measured grounds.
2. **No price pattern.** 148 price-pattern strategies over 909 baseball games
   returned 0 positive (`LEDGER` BH002). Anything reading price history, drift,
   staleness or volume shape is cut without further thought.
3. **Free data, reachable at the decision moment.** Not "exists somewhere" —
   published before the window the bot would act in.
4. **The market can be afforded.** Measured from this project's own tape by
   `src/mlb_cost.py`, never assumed.
5. **Not a near-copy.** Either the inputs differ from every live bot, or the
   inputs are the same and the **instrument** differs — which is a feature, not
   a fault, because it buys the paired-test discount.

---

## The 43

`LIVE` = written as a spec. `DUP` = already running in the fleet.
`FOLD` = merged into another spec rather than given its own slot.
`CUT` = screened out, with the reason.

### Starting pitcher — 10 considered

| # | idea | verdict | why |
|---|---|---|---|
| 1 | recent-form divergence → who wins | `DUP` | this is the live `starter` bot |
| 2 | recent-form divergence → **first five innings** | **`SF200`** | same signal, bullpen removed from the payout |
| 3 | recent-form divergence → **starter's outs** | **`SF212`** | same signal, third instrument, thinner book |
| 4 | his strikeout rate **× the opponent's** → strikeouts | **`SF202`** | no live bot reads the opponent at all |
| 5 | his throwing hand vs the lineup's batting sides | **`SF203`** | free from the API, read by nobody |
| 6 | announced opener / bullpen game | **`SF208`** | the named starter is misleading by design |
| 7 | his career record against this specific club | `CUT` | 20-odd plate appearances is noise, and it is the exact trap M1's amendment A3 was written to close |
| 8 | pitch-velocity trend from Statcast | `CUT` | `MENTALITIES.md`: a modelling project, not a mentality. Also the only idea here needing a data source we do not have |
| 9 | short rest | `DUP` | already a term inside `starter` |
| 10 | debut starter | `DUP` | already a term inside `starter` |

### Bullpen — 5 considered

| # | idea | verdict | why |
|---|---|---|---|
| 11 | fatigue → combined total | `DUP` | this is the live `bullpen` bot |
| 12 | fatigue → **first-five total, as a control** | **`SF201`** | relievers do not pitch innings 1–5, so this must find nothing |
| 13 | fatigue → **one club's team total** | **`SF205`** | the combined market cancels one side against the other |
| 14 | closer unavailable → inning winner | `CUT` | measured cost bar **7.07c**. Nothing survives a 7-cent round trip |
| 15 | fatigue → the sixth and seventh innings, as a two-leg trade | `CUT` | two legs, two spreads, and a derived market. Too clever for a first pass |

### Park and weather — 5 considered

| # | idea | verdict | why |
|---|---|---|---|
| 16 | wind and heat → runs | `DUP` | this is the live `park-air` bot |
| 17 | wind and heat → **home runs** | **`SF206`** | carry is a home-run effect first; and it is the cheapest family on the board at **0.97c** |
| 18 | rain and shortened games | **`SF210`** | a different mechanism entirely — innings played, not carry |
| 19 | humidity and air density as their own term | `CUT` | near-copy of the temperature term already inside `park-air` |
| 20 | roof open or closed | `FOLD` | folded into `SF210` as a required condition rather than given a slot |

### Batting and the lineup card — 6 considered

| # | idea | verdict | why |
|---|---|---|---|
| 21 | two or more of the top five missing → who wins | `DUP` | this is the live `lineup` bot |
| 22 | **whole card, absentee minus replacement** → who wins | **`SF207`** | the cost is the gap, not the absence |
| 23 | the same, on the affected club's team total | `FOLD` | folded into `SF207` as a second family |
| 24 | top-of-order quality → **run in the first inning** | **`SF211`** | reopens a family set aside on a cost figure the tape contradicts |
| 25 | a missing slugger → **home runs** | **`SF214`** | reserve — most at risk of being a near-copy of `SF207` |
| 26 | batter-versus-pitcher career history | `CUT` | tiny samples, and known noise in public work |

### The calendar — 4 considered

| # | idea | verdict | why |
|---|---|---|---|
| 27 | travel, rest days, time zones, day-after-night | **`SF204`** | nothing in the fleet reads the calendar |
| 28 | series game number | `FOLD` | into `SF204` |
| 29 | doubleheaders | `FOLD` | into `SF204` — 40 of 2,060 games this season |
| 30 | seven-inning doubleheaders mispricing a nine-inning total | **`CUT`, measured dead** | **all 2,060 games scheduled in 2026 are 9 innings.** The seven-inning rule is gone. Checked against the schedule API today, not assumed |

### The standings — 3 considered

| # | idea | verdict | why |
|---|---|---|---|
| 31 | eliminated vs clinched vs contending, in September | **`SF209`** | free from the standings, read by nobody |
| 32 | a clinched club resting regulars | `FOLD` | into `SF209` as its larger of two coefficients |
| 33 | September roster expansion | `CUT` | cannot be separated from 31 or from bullpen depth |

### Officials — 1 considered

| # | idea | verdict | why |
|---|---|---|---|
| 34 | home-plate umpire's strike zone | **`SF215`, `UNMEASURABLE`** | **checked live: 57 of 57 scheduled games list no officials, including with the API's own `hydrate=officials`. The same field is filled once the game is final.** So the input does not exist at any window the fleet decides in |

### Defence — 1 considered

| # | idea | verdict | why |
|---|---|---|---|
| 35 | catcher framing | **`SF216`**, reserve | **fails on arithmetic before it is run:** 0.08 runs is about 0.7c against a measured 1.32c bar. Written down anyway rather than dropped silently |

### Arithmetic identities, no view on the game — 4 considered

| # | idea | verdict | why |
|---|---|---|---|
| 36 | first five plus innings six-to-nine equals the game | `CUT` | there is no innings-six-to-nine market to pair against |
| 37 | winning by more than X implies winning | `CUT` | already measured: **0 violations in 172,684 instants** (`STRUCTURAL-01.md`) |
| 38 | the two team totals must add to the game total | `CUT` | **not an identity.** Two "over" prices do not add — the game total depends on how the two clubs' runs combine, not on their sum of thresholds |
| 39 | over X in the first five implies over X in the game | **`SF213`**, bonus | a genuine containment, never tested, runs on tape already on disk |

### Price patterns — 4 considered, 4 cut on the same evidence

| # | idea | verdict |
|---|---|---|
| 40 | enter when the spread narrows | `CUT` |
| 41 | enter on a stale quote | `CUT` |
| 42 | enter on a volume spike | `CUT` |
| 43 | enter on drift from the opening price | `CUT` |

All four are cut by the same measurement, quoted rather than paraphrased:
`MENTALITIES.md`, *"anything about the price pattern — 148 of them on 909
games, 0 positive. Rebuilding one would be the single most predictable waste in
this repo."*

---

## The tally

| | |
|---|---:|
| considered | **43** |
| already running in the fleet | 5 |
| folded into another spec | 4 |
| cut by the screen | 17 |
| **written as specs** | **17** |
| of those, recommended for the ten slots | **10** |
| next in line if one fails to build | 2 |
| reserve | 3 |
| unmeasurable, no slot | 1 |
| structural bonus, needs no slot | 1 |

**Four of the 17 cuts are backed by a measurement made today rather than by a
judgment:** the seven-inning doubleheader (2,060 of 2,060 games are nine
innings), the inning-winner market (7.07c cost bar), the umpire (57 of 57 games
with no officials listed), and the two-team-totals identity (it is not one).
