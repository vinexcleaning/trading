# PREREGISTRATION_TOTALSMODEL.md — predict the run total, score it against settlement

**2026-08-21. Written before the model exists and before any backtest has been
run.** Everything already measured is in §2 and it is all apparatus: how much
settled data exists, whether historical prices are retrievable, and whether the
outcome can be recovered at all.

**His condition, which is the right one and is not negotiable:** *"as long as we
don't actually integrate it until we actually backtest it on some sort of data."*
**Nothing here is traded, integrated, or connected to anything.**

---

## 1. Why this is a different question from everything in `RESULTS_TOTALS_N3.md`

That study asked *do two venues disagree on the price*. Answer: no — **109 rungs,
nine games, none clearing, and the sharp book's fair value sits inside Kalshi's
own spread on 70 out of 100 rungs (BH020).**

**This asks something the price comparison cannot reach.** A de-vig test needs
someone else's opinion to compare against, and **179 of the totals rungs have no
free sharp price at all — and they are the cheap ones**, where the fee is
0.14–0.63¢ instead of 1.7¢ (BH018).

> **The coordinator argued a model there would be unverifiable, then withdrew it,
> and the withdrawal is the important part: the check for a forecast is
> SETTLEMENT, not a bookmaker.** You do not need anyone's opinion of the
> probability when you can observe what actually happened. A price comparison is
> a shortcut to the truth; the outcome *is* the truth.

## 2. Everything measured before this file existed

| measured 2026-08-21 | result |
|---|---|
| settled `KXMLBTOTAL` rungs retrievable from the API | **10,431** |
| **settled GAMES** | **854** |
| distinct game-days covered | **66** |
| rungs per game | 12.1 |
| historical prices retrievable for a settled rung | **yes** — candlesticks return `yes_ask.close_dollars` per minute; 13 hourly candles over the 13 h before one first pitch |
| **can the final total be recovered without any external data?** | **yes — 104 of 104 ladders, zero inconsistent** |

### ⚠ 2a. I have to correct the number this whole plan was scoped on

**Mailbox 022 states 160 settled games and concludes the sample "reaches the easy
bar in about three weeks".** That count came from `record.db`, which only began
on 2026-08-06 and only holds what the recorder saw.

**Kalshi's API still serves settled markets back to 2026-06-30: 854 games, not
160.** Against `K014`'s bar — **481 settlements to detect a large edge, 2,084 for
a small one** — that is **already past the first** and 41% of the way to the
second.

> **So the three-week wait does not exist. The data is here now.** I would rather
> say that than inherit a timeline that would have parked this until mid-September
> for no reason.

**What has NOT changed:** the small-edge bar still needs 2,084 games and the
recorder adds about **15 a day**, so **a small edge remains undetectable this
season.** That belongs in the report, up front, whichever way the result lands.

### 2b. The dataset needs no external source, which was not obvious

**The settlement ladder is self-describing.** "Over 10.5 = yes" and
"over 11.5 = no" means the game finished on exactly 11 runs. Checked on 104
consecutive ladders: **every one crosses exactly once, none contradicts itself.**

**So one free endpoint yields the outcome, and a second yields the price we would
have paid.** No scraper, no paid feed, no login.

## 3. The hypothesis — T1

**His words, and they are already a usable rule:** *recent scoring rate,
conditioned on opponent quality.*

Concretely: for each game, from **information available before first pitch only**,
predict a distribution over the final total, and price every rung of the ladder
from it. Enter where the model's probability beats Kalshi's ask by more than the
cost.

```
p_hat(total >= k)  = model, fitted on games BEFORE this one only
edge_c             = 100 * p_hat − kalshi_ask_c        # ask from candlesticks
cost_c             = fee(ask) + slippage               # common/kalshi_fees.py ONLY
ENTER iff edge_c > cost_c
```

**The first model is deliberately dull:** each team's runs scored and runs allowed
over its last N games, combined into an expected total, spread over a count
distribution. **A dull model that is honestly scored is worth more than a clever
one that is not**, and the machinery is what is being tested first.

## 4. The rules, fixed now

**4a. Unit of observation is ONE GAME.** A game's twelve rungs settle on one final
score. **Every number reported is per game**, effective count printed beside
nominal, and the rung count is never used as a sample size. This is the rule that
turned 490,464 fills from 762 matches into 762.

**4b. The holdout is sealed before any fitting.** The **newest 30% of game-days**
— not games, days, so a single day cannot straddle the split — are held out and
**touched once, by survivors only.** The split is by date and is written into the
code as a constant before the first fit.

**4c. Nothing outside the past.** Every feature is computed from games that
finished **strictly before** the game being predicted, and the price is the ask
**before first pitch**. Any feature that cannot be computed at that moment is
excluded, and the check is mechanical rather than a promise.

**4d. Cost at the real price.** `fee(ask) + slippage`, per trade, no half-spread
term — buying at the ask *is* crossing. ⚠ **The fee is quadratic and near its
minimum at extremes: ~0.20¢ at 97¢, not the habitual 3.6–4.8¢.** The cheap rungs
are the point of this exercise, so the bar is computed per rung and its
distribution is reported, never a single number.

**4e. Capacity, not just edge.** These are the thin rungs. **Depth at the entry
price is reported for anything that survives.** Cheap to trade and impossible to
fill is still nothing.

## 5. Controls

| | |
|---|---|
| **P1 — shuffled outcomes** | refit and rescore with the final totals randomly permuted across games. **Anything the model "finds" there is the machinery, and a positive voids the run.** |
| **P2 — the market's own price as the forecast** | score Kalshi's implied probability against settlement, on the same games. **This is the benchmark that must be beaten, and it is the one that usually wins.** |
| **P3 — a constant** | league-average total, ignoring both teams. If it trades as well as the model, the model is not what is doing the work. **Weather died on exactly this**: climatology beat the real model, +1.37¢ to +0.43¢, and a know-nothing 50% model cleared the gate at +1.01¢. |
| **P4 — sell side** | run the gate on the under too. **Both sides positive on one population is arithmetically impossible** and means the join or the cost model is wrong. |

**P3 is the one I expect to bite**, and it is the reason a dull model goes first:
if league average trades as well as team form, then team form is decoration.

## 6. What makes me drop it

**Any one of these and T1 stops:**

- **P1 fires** — the shuffled-outcome placebo finds anything;
- **P3 ties or wins** — a constant trades as well as the model;
- **P2 is not beaten on the holdout** — the market's own price forecasts better;
- the qualifying rate **inside the tradeable set is not higher than outside it** —
  that is selection, not edge;
- **fewer than 481 usable games** after joining prices to outcomes;
- the result **strengthens monotonically as the sample grows**, which is
  contamination rather than evidence.

## 7. What I expect, and what would make me distrust a win

**I expect T1 to fail**, and the base rate is the honest reason: **59 strategies
tested in this repo, 0 that work, and 51 recorded retractions of which every
single one shrank an edge.**

**The specific way I expect it to fail is P3** — the market price already contains
the starting pitchers, the weather and the park, and a team's last-N runs contains
much less than that.

**What would make me distrust a positive, written now so it cannot be assembled
later:**

- a win that lives **only in the cheap outer rungs**, where the fee is smallest
  and the model is furthest from the data it was fitted on;
- a win that **does not survive P3**;
- a win whose **capacity is a handful of contracts**, which is a backtest
  artefact rather than a strategy;
- a win that appears **only after the holdout is opened more than once.** It is
  opened once. If it fails, it fails.

## 8. What is NOT being built

**Not integrated. Not traded. Not connected to any credential.** No order code
enters this project — `bot-hunt` has no paper-only canary of its own yet, and
**if T1 ever survives to the point of wanting one, that test gets written before
the feature does**, copying `tennis-paper-forward/tests/test_paper_only.py`
rather than inventing a third style.
