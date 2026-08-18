# PREREGISTRATION_PROPS.md — de-vig a SHARP book on PLAYER PROPS, not the game winner

**2026-08-18. Written before any gap, edge or settled outcome exists for this
design.** Everything already measured is in §2 and it is all apparatus: which
feeds carry what, when, and whether the two venues are asking the same question.

---

## 1. Why this is a different test and not a repeat

**Every de-vig result in this repo — all of them null — was measured on the GAME
WINNER.**

| | |
|---|---|
| `RESULTS_DEVIG_WHERE.md` | 1,460 paired readings, 30 MLB games, largest gap **2.77¢** against a 2.75¢ cost |
| `RESULTS_RETAIL_N3.md` | Bovada vs Pinnacle, 11 games twice, largest gap **0.48¢** against 1.61¢ |
| **T012** (tennis) | correlation 0.9878, mean absolute gap **1.95¢** against a 2.44¢ bar |
| `mlb-paper` | **0 of 58** markets worth trading, best case −1.63¢ |

**The game winner is the most-arbitraged line on the board.** Two books agreeing
there is nearly a definition rather than a discovery. **Nobody here has ever
compared the two venues on anything else**, because until 2026-08-14 we had no
free two-sided sharp reference for anything else. Now we do — §2.

> ### ⚠ THE INFERENCE THIS TEST MUST NOT REST ON, STATED FIRST
>
> **A fat margin is a reason to look. It is never evidence of room.** Two chats
> made that inference and both withdrew it, and `RESULTS_RETAIL_N3.md` is now the
> **third measured demonstration**: Bovada's margin was **2.25×** Pinnacle's and
> after stripping there was **0.18¢** behind it.
>
> So Pinnacle's prop margin running 2–3× its moneyline margin is **not a reason
> to expect anything**. The reason to run this is narrower and it is the only
> one: **this market has never been looked at.**

## 2. Everything measured before this file existed

| measured | when | result |
|---|---|---|
| Pinnacle's free feed carries two-sided **player props** | 2026-08-14 06:20Z | **12 parents → 62 priced markets** (`Total Strikeouts`, `Total Home Runs`) |
| join to Kalshi by player name — strikeouts | same | **10 of Kalshi's 20** pitchers |
| join to Kalshi by player name — home runs | same | **13 of Kalshi's 21** hitters |
| Kalshi's strikeout board | 2026-08-18 04:30Z | `KXMLBKS`, **149 markets, 16 pitchers**, each a **LADDER** — e.g. Robbie Ray at 3+, 4+, 5+, 6+, 7+, 8+, 9+ |
| Kalshi baseball markets with **no** free sharp reference at all | 2026-08-14 | **3,686 of 4,291 — 86 out of 100** |
| **⚠ Pinnacle player props, re-read** | **2026-08-18 04:30Z** | **ZERO. Not one.** Control passed on the same call: 1.13 MB, 290 matchups, 23 MLB games, Exact Scores 228 / Next Run 12 / Double Result 12 |

**Not measured, and deliberately not:** any de-vigged fair value, any gap to
Kalshi, any settled outcome, any qualifying rate.

## 3. ⚠ Two problems that could kill this before any pricing, and both are apparatus

### 3a. The reference is INTERMITTENT, and that may be fatal on its own

**Present 2026-08-14, absent 2026-08-18, same endpoint, control passing** (GUARDS
#27 — an empty payload is only an empty board once a control returns a full one,
and here it did). The likeliest explanation is that Pinnacle posts pitcher props
only close to first pitch, and 04:30 UTC is the middle of the American night.

**This is measured before anything else is built.** `src/prop_watch.py` samples
the feed every 20 minutes and records, per hour, whether player props exist and
how many.

> **The kill condition, written now:** if the props are live for **fewer than two
> hours before first pitch**, then Kalshi's ladder — quoted days ahead — and
> Pinnacle's line barely coexist, and **there is no window in which a
> disagreement could be acted on.** That ends this idea on apparatus, for free,
> before a single price is compared.

### 3b. The two venues may not be asking the same question

**Kalshi quotes a LADDER** — *"Robbie Ray: 3+ strikeouts?"* through *"9+"*, seven
separate yes/no markets on one pitcher. **Pinnacle prices ONE line**, over/under
a number like 5.5.

**They are comparable, but only through a step that can itself invent an edge.**
The ladder implies a whole distribution; the line implies one point on one.
Comparing them means reading Kalshi's implied probability **at Pinnacle's line**,
and when the line falls between rungs, interpolating.

> **The rule, fixed now rather than after seeing results:** **only lines that sit
> between two rungs that both exist as real Kalshi markets are used** — no
> extrapolation past either end of the ladder — and the method is declared here
> as **linear in the implied probability between the two adjacent rungs**. **If
> the answer changes materially under a monotone-spline interpolation instead,
> that is the finding and there is no edge**, exactly as
> `PREREGISTRATION_RETAIL.md` §3a treats method disagreement.

**And the ladder carries its own check:** a Kalshi ladder that is not monotone
(5+ priced above 4+) is arbitrage against itself and marks a bad read, not an
opportunity. **Any pitcher whose ladder is non-monotone at the touch is
discarded, and the number discarded is reported.**

## 4. The test — P1

For each pitcher where both venues quote, at each observation:

```
p_over, p_under = american_to_prob(Pinnacle's two prices)
fair            = devig(p_over, p_under)[method]     # three methods, below
k_implied       = Kalshi's ladder interpolated to Pinnacle's line
edge_c          = 100 * fair − kalshi_ask_c          # on whichever side qualifies
cost_c          = fee(ask) + slippage                # common/kalshi_fees.py ONLY
ENTER iff edge_c > cost_c
```

**Three margin-removal methods** — proportional, power/logarithmic, and Shin
solved **numerically** rather than from a remembered closed form. **If they
disagree in sign, that is the finding and the edge is not real.** Worst-case is
primary, for the reason `PREREGISTRATION_DEVIG.md` §2.2 gives: the one author
with a reconciled live profit-and-loss reported his Shin implementation *"ran hot
on favourites"*, and a method that manufactures the tail under test is not a
neutral instrument.

**Cost:** `fee(ask) + slippage`, recomputed per trade, **no half-spread term** —
buying at the ask *is* crossing. ⚠ **The fee is quadratic and near its MINIMUM at
extreme prices — about 0.20¢ at 97¢, not the 3.6–4.8¢ this repo habitually
quotes.** A strikeout ladder's outer rungs live exactly there, so quoting the
habitual figure would be an error of 20×.

**Unit of observation: the PITCHER-START**, never the rung. One pitcher's seven
rungs settle on one performance — treating them as seven is the same mistake as
counting 490,464 fills from 762 matches as 490,464 observations. **Effective
count printed beside nominal count, every time.**

**Holdout: the newest 30% of pitcher-starts, sealed**, touched once, by survivors
only.

## 5. Controls

| | |
|---|---|
| **N1** | **Mismatched pitcher** — de-vig from a different pitcher the same day, deterministic rotation. **Positive here voids the run.** |
| **N2** | **Two-sided coherence** — run the gate on the sell side too. Both sides positive on one population is arithmetically impossible. |
| **N3** | **The moneyline arm on the same games** — the known null. If props show an edge where the game winner does not, the difference is the market type. **If both show one, suspect the join or the cost model, not the books.** |
| **N4** | **Ladder-internal placebo** — interpolate between Kalshi's own adjacent rungs and compare to Kalshi itself, a venue that cannot disagree with itself. **Whatever this finds is instrument, not signal.** |

**N4 is new, and it exists because of §3b.** The interpolation is the one step
here capable of manufacturing an edge out of nothing, so it gets its own control
rather than a caveat.

## 6. What makes me drop it

**Any one of these and P1 stops:**

- **props live for under two hours before first pitch** (§3a) — no tradeable
  window, and this is checked first because it is free;
- the three de-vig methods **disagree in sign**;
- **N1 or N4 fires**;
- the answer **moves materially between the two interpolation methods**;
- fewer than **40 pitcher-starts** joinable after two weeks — not a sample, and
  saying so early is cheaper than a wide interval later.

## 7. What I expect

**I expect P1 to fail, and the reason belongs on record before the number
exists.** But the honest form of my expectation is narrower than that:
**I have no measurement either way for props** — which is the entire point of
running it — **and the base rate in this repo is 56 strategies tested and 0 that
work.**

**What would genuinely surprise me:** the props being quoted by a *different*
part of Pinnacle's book than the moneyline — thinner, posted later, less
arbitraged — and therefore disagreeing with Kalshi by more than the cost bar.
**That is measurable on the first day both feeds are up, before any pitcher
throws**, and it is the arm to run first, for the same reason it was the right
first arm on the retail test: it can only cost hours and it can end the idea.

**What would make me distrust a positive, listed now so it cannot be assembled
later:** one that appears **only at the outer rungs**, where the fee is smallest
and the interpolation is furthest from real data; one that **strengthens as the
sample grows**, which is contamination rather than evidence; or one that
**survives N1 but not N4**, which would mean the interpolation built it.
