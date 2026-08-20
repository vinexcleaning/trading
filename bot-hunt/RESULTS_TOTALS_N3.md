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

## 3b. ⚠ THE OTHER TWO TOTALS FAMILIES, TESTED THE SAME HOUR — both dead too

§4 below listed first-five-innings and team totals as untested. **They are not
any more.** Same machinery, same day, `src/totals_family_n3.py`.

| | game totals | **first five innings** | **team totals** |
|---|---|---|---|
| Kalshi family | `KXMLBTOTAL` | `KXMLBF5TOTAL` | `KXMLBTEAMTOTAL` |
| rungs compared | 30 | **25** | **54** |
| **games** | 9 | **9** | **9** (18 team-games) |
| Pinnacle's margin | 3.96 | **3.98** | **5.44** |
| median disagreement | 0.43¢ | **0.73¢** | **1.20¢** |
| largest, any rung | 1.00¢ | **1.58¢** | **2.79¢** |
| median fee | 1.71¢ | 1.69¢ | 1.68¢ |
| **clearing the bar — buy** | **0 of 30** | **0 of 25** | **0 of 54** |
| **— sell** | **0 of 30** | **0 of 25** | **0 of 54** |

**109 rungs across three families, nine games, one hour. Not one clears.**

**Team totals look like the interesting row and they are not — and working out
why produced the best thing in this study.**

They carry Pinnacle's **fattest margin measured anywhere** (5.44 out of 100,
nearly three times its own moneyline) and the **largest apparent disagreement,
2.79¢** — comfortably above the 1.68¢ fee. A careless reading stops there and
reports a trade.

**⚠ It is not a disagreement. It is Kalshi's own spread, and I nearly wrote it up
as the former.** The biggest one in the study:

| Yankees team total, over 5.5 | |
|---|---|
| Kalshi bid / ask | **32¢ / 36¢** (a 4¢ spread) |
| sharp book's fair value for the over | **33.21¢** |
| buy the over at 36¢ | **−2.79¢** — you pay 2.79¢ over fair |
| so sell it? buying the under costs 100−32 = **68¢** | its fair is 66.79¢ → **−1.21¢** |

**Both sides are overpriced at once, and that is not a contradiction — it is what
a spread is.** The sharp price sits *between* Kalshi's bid and its ask, so you
cross the spread whichever way you go.

### The mechanism, measured across all three families

| | rungs | **sharp fair sits INSIDE Kalshi's bid–ask** | median Kalshi spread |
|---|---|---|---|
| game totals | 30 | 17 (**57%**) | 1.0¢ |
| first five | 25 | 17 (**68%**) | 2.0¢ |
| team totals | 54 | 42 (**78%**) | 3.0¢ |
| **all three** | **109** | **76 — 70 out of 100** | **2.0¢** |

> **On 70 out of every 100 rungs, the sharp book's fair value is inside Kalshi's
> spread.** There is no disagreement to trade; there is a spread to pay. And the
> share rises exactly with the spread — 57% at a 1¢ spread, 78% at 3¢ — so **the
> families that look like they disagree most are simply the ones with the widest
> spread.** The apparent gap is the half-spread wearing a disguise.

> **This is the fifth measured demonstration that a fat margin is not evidence of
> room, and the first that also explains the mechanism.** Widest margin in the
> study, widest apparent gap in the study — and the gap was Kalshi's own spread,
> pointing at a trade that does not exist in either direction.

**⚠ A caveat that belongs on the team-totals row specifically:** 54 rungs on 18
team-games is **not 54 observations and not even 18.** The two teams in one game
share a game state — a rain-shortened seven-inning game moves both — so the
conservative count is **nine**, and it is the one printed.

### And the coverage pattern is not a quirk of one family

| | referenced by a sharp book | **not referenced** | fee on the unreferenced |
|---|---|---|---|
| game totals | 30, at 37–68¢ | **69**, at 15–97¢ | min **0.20¢** |
| first five | 25, at 36–66¢ | **38**, at 23–98¢ | min **0.14¢** |
| team totals | 54, at 30–70¢ | **72**, at 10–89¢ | min 0.63¢ |

**Three families, same shape every time: the sharp book quotes only the middle
of the ladder, and every cheap-to-trade rung is unreferenced.** **179 rungs**
across the three have no free sharp price at all.

---

## 4. What this does NOT kill

`CLAUDE.md` §9c step 7 — the list, not a caveat.

- **69 of the 99 rungs, including every cheap one.** Untested here and
  **untestable by this route**, because the reference does not exist.
- **One reading, nine games, one hour of one day.** Totals move on weather,
  wind, and a late scratched pitcher. Nothing here sees any of that.
- ~~First-five-innings totals~~ and ~~team totals~~ — **both tested the same
  hour, see §3b. Both dead.** Struck through rather than deleted: a list of
  untested things is only useful if you can see what came off it.
- **Every non-baseball total.** `KXLIGAMXTOTAL` is on the recorder already.
- **Any model at all.** This is a price comparison. It says nothing about
  whether recent scoring rate conditioned on opponent quality predicts anything
   — which is a different question, and a much larger one.
- **Depth.** What size actually sits at those asks is recorded in the json and
  not analysed.

## 5. What would make me doubt this

- **Nine games is small.** For game totals it is decisive only because the gap is
  **4× under the bar at the median and still under it at the very worst**. ⚠ **I
  first wrote "1.7× under at its worst" and that was only true of the game-totals
  family** — team totals reach 2.79¢ against a 1.68¢ fee, *above* the bar, and
  are dead for a different reason (§3b: the sharp price is inside the spread).
  **A result landing at 1.5¢ against 1.7¢ would prove nothing at this sample** and
  I would not have written it up.
- **One hour of one day**, and an overnight hour at that. A getaway day, a
  doubleheader, or a scratched starter an hour before first pitch would not
  appear here.
- **The 30 matched rungs are the middle of the book by construction**, because
  that is where the sharp book quotes. They are not a random sample of Kalshi's
  ladder, and §3 is the whole reason that matters.
