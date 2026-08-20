# RESULTS — run totals: the two venues agree to less than one tick

**2026-08-20.** Mailbox 021. **No settled game is used anywhere in this file**,
so nothing in it can be a result-dependent choice — the same discipline that
killed the retail-book idea in an hour.

`KXMLBTOTAL` is the largest family on the recorder — **2,280 tickers, 96,336
snapshots since 2026-08-04** — and **no strategy had ever been written against
it.** This is the cheapest possible first question about it: *do the two venues
even disagree?*

---

## 1. Why this comparison is unusually clean

Kalshi publishes `floor_strike = 8.5` with `strike_type = "greater"` — an
explicit number, no title parsing. Pinnacle prices the same half-integer lines,
both sides. So **"Over 8.5 runs scored" and "over 8.5" are the same event,
exactly** — no interpolation, and no push, because 8.5 cannot be tied.

**Whole-number lines were discarded and counted.** Pinnacle also quotes 8.0 and
9.0; those carry a push that Kalshi's market does not have, so treating them as
the same event would be the error.

## 2. The answer

| | |
|---|---|
| rungs compared | **30** |
| **games — the real count** | **9** |
| both feeds pulled within | **41 seconds** |
| Pinnacle's margin on totals, median | **3.96 out of 100** |
| **median disagreement** | **0.43¢** |
| p90 | 0.84¢ |
| **largest, any rung** | **1.00¢** |
| median fee to act on it | **1.71¢** |
| **rungs where the gap beats the cost — buy side** | **0 of 30** |
| **— sell side** | **0 of 30** |

> **The disagreement is smaller than one tick.** Kalshi prices in whole cents,
> and every matched rung came back on a whole cent — 57.00, 63.00, 49.00. The
> median gap between the sharp book's fair value and Kalshi's ask is **0.43¢**.
> **You could not express this disagreement in Kalshi's own prices even if it
> were free to trade.**

**Nine games is the count that matters, not thirty.** One game's whole ladder
settles on one final score, so the rungs are not independent observations and
are never counted as such.

**And the margin is fat again, for the fourth time.** Pinnacle's totals margin
is **3.96 out of 100** against **1.98** on its own moneyline — twice as wide,
and nothing behind it. That is now four measured demonstrations that **a fat
margin is a reason to look and never evidence of room.**

**Method disagreement:** proportional −0.14¢, power −0.07¢, Shin −0.09¢ — all
three negative, so no sign disagreement here. The methods agree, and they agree
that there is nothing.

---

## 3. ⚠ THE STRUCTURAL FINDING, which matters more than the null

Mailbox 021 made the right point that at extreme prices the Kalshi fee collapses
to **about 0.20¢ instead of the habitual 3.6–4.8¢**, so the bar must be computed
where these markets actually trade. **I did, and the answer is the opposite of
convenient.**

**Of 99 open Kalshi totals rungs across the same 9 games:**

| | rungs | Kalshi ask | fee at that price |
|---|---|---|---|
| **have a free sharp reference** | **30** | 37–68¢ | **1.71¢ median** |
| **have none at all** | **69** | 15–97¢ | 1.12¢ median, **0.20¢ minimum** |

**The sharp book quotes only the three or four lines nearest the true total.
Kalshi quotes the whole ladder, roughly 2.5 through 13.5.**

> **So the rungs that are cheap enough to trade are exactly the rungs nobody can
> check.** Fifteen of the 69 sit at 10¢ or below, or 90¢ or above, where the fee
> is about **0.33¢** — and not one of them has a sharp reference.

**⚠ That is NOT evidence the extremes are mispriced.** It is M024's retracted
argument, and it stays retracted. **It is the absence of a cheap way to find out
you are wrong** — which is worse than a null, not better than one. A model is
the only instrument that reaches those rungs, and a wrong model there would be
expensive to detect.

---

## 4. What this does NOT kill

`CLAUDE.md` §9c step 7 — the list, not a caveat.

- **69 of the 99 rungs, including every cheap one.** Untested here and
  **untestable by this route**, because the reference does not exist.
- **One reading, nine games, one hour of one day.** Totals move on weather,
  wind, and a late scratched pitcher. Nothing here sees any of that.
- **First-five-innings totals.** Pinnacle carries **105** of them (`total p1`)
  and Kalshi runs `KXMLBF5TOTAL` at 77 markets. **Never joined.**
- **Team totals.** Pinnacle carries 126 (`team_total p0`); Kalshi runs
  `KXMLBTEAMTOTAL` at 154 markets. **Never joined**, and it is the third-largest
  baseball family on the board.
- **Every non-baseball total.** `KXLIGAMXTOTAL` is on the recorder already.
- **Any model at all.** This is a price comparison. It says nothing about
  whether recent scoring rate conditioned on opponent quality predicts anything
   — which is a different question, and a much larger one.
- **Depth.** What size actually sits at those asks is recorded in the json and
  not analysed.

## 5. What would make me doubt this

- **Nine games is small.** It is decisive only because the gap is **1.7× under
  the bar at its very worst and 4× under at the median** — a result landing at
  1.5¢ against 1.7¢ would prove nothing at this sample and I would not have
  written it up.
- **One hour of one day**, and an overnight hour at that. A getaway day, a
  doubleheader, or a scratched starter an hour before first pitch would not
  appear here.
- **The 30 matched rungs are the middle of the book by construction**, because
  that is where the sharp book quotes. They are not a random sample of Kalshi's
  ladder, and §3 is the whole reason that matters.
