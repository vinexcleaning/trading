# RESULTS — player props: P1 stops on its own pre-registered drop condition

**2026-08-21.** `PREREGISTRATION_PROPS.md`, the day-one arm. **No settled game is
used anywhere in this file**, so nothing in it can be a result-dependent choice.

**This was the first free sharp reference this repo has ever had on anything that
is not who-wins-the-game.** It took three days of waiting to catch the board open.

---

## 1. The answer

**14 props, 14 distinct players, both feeds pulled 12 seconds apart.**

| | |
|---|---|
| Pinnacle's margin on props, median | **6.97 out of 100** |
| median disagreement, sharp fair vs Kalshi ask | **1.35¢** |
| p90 / largest | 2.94¢ / **3.57¢** |
| Kalshi ask, median (range) | 24.5¢ (12–60¢) |
| **fee at those prices**, median (range) | **1.29¢ (0.74–1.75¢)** |
| **buy side clearing the bar** | **0 of 14** |
| sell side flagging | 4 of 14 |

> ### ⚠ AND P1 STOPS, on a condition written before any number existed
>
> `PREREGISTRATION_PROPS.md` §6: *"the three de-vig methods disagree in sign"* is
> an explicit drop condition. **They disagree on 8 of the 14.**
>
> | method | mean | share positive |
> |---|---|---|
> | proportional | **+0.47¢** | 57% |
> | power / logarithmic | **−1.50¢** | **0%** |
> | Shin | −0.72¢ | 21% |
>
> **Proportional says there is an edge on more than half of them. Power says
> there is one on none of them.** The pre-registration named this outcome as the
> finding itself, and it is.

## 2. ⚠ The pattern behind the disagreement is perfectly clean, and it was predicted

| prop type | methods disagreeing in sign | Kalshi ask |
|---|---|---|
| **Home runs** | **8 of 8** | **12–28¢** |
| **Strikeouts** | **0 of 6** | 43–60¢ |

**Every single disagreement is a home-run prop. Not one strikeout prop
disagrees.** Home-run props are "1+ home run" — long odds, priced 12–28¢.
Strikeout props sit mid-book at 43–60¢.

**`PREREGISTRATION_RETAIL.md` §3a said this in advance:** *"proportional is the
default and is known to be wrong at long odds, and the margin is fattest exactly
where it is worst."* **Pinnacle's prop margin is 6.97 out of 100 — the fattest
measured anywhere in this repo, three and a half times its own moneyline.** At
long odds with a margin that fat, *how* you remove the margin dominates the
answer.

## 3. ⚠ The finding worth keeping, which is not the null

Mailbox 021 made the right point that the Kalshi fee collapses at extreme prices
and the bar must be computed where these markets actually trade. **It does, and
props are the first family where it matters:**

| | fee at the prices actually traded |
|---|---|
| run totals (all three families) | 1.68–1.71¢ |
| **player props** | **0.74–1.75¢, median 1.29¢** |

**The cheap rungs are real here — a home-run prop at 12¢ costs 0.74¢ to trade,
less than half what a total costs.** That is the first time the fee argument has
actually bitten.

> **But the cheap rungs are cheap *because* they are long odds — and long odds
> are exactly where removing the bookmaker's margin stops having a single
> answer.** The fee saving and the measurement ambiguity are not two facts. They
> are the same fact, seen from two sides.
>
> **So "go where the fee is small" is self-defeating on this route.** Every step
> toward a cheaper trade is a step toward not being able to tell what the fair
> value is.

## 4. The four sell-side flags, and why none of them is a trade

| player | kind | bid/ask | proportional | power | Shin |
|---|---|---|---|---|---|
| Mookie Betts | Home Runs | 12/14 | **+0.61** | **−3.57** | −1.86 |
| Alex Bregman | Home Runs | 10/12 | **+1.35** | **−3.02** | −1.20 |
| Randy Arozarena | Home Runs | 15/16 | **+1.31** | **−2.46** | −0.97 |
| **Yoshinobu Yamamoto** | Strikeouts | 59/60 | −3.33 | −2.73 | −2.94 |

**Three of the four are home-run props where the methods contradict each
other** — the drop condition, not a signal.

**The fourth is the only one where all three methods agree.** Buying the under
means paying 100 − 59 = **41¢** against a sharp fair of **42.73¢**. Edge
**+1.73¢** against a **1.69¢** bar.

> **It clears by 0.03 cents.** On one prop, on one day. That is not a finding; it
> is the width of a rounding error, and reporting it as anything else would be
> the exact failure this repo has recorded 51 times.

## 5. ⚠ How this nearly did not happen at all

**The first capture ran, fetched 32 sharp props and 225 Kalshi rungs, and then
died on a print statement.**

Launched by hand, these scripts inherit `PYTHONIOENCODING=utf-8`. **Launched by
the watchdog they inherit the Windows cp1252 console default**, and the first
`print` containing a `⚠` raised `UnicodeEncodeError` and killed the process —
**after the data was already in memory**, three days into waiting for a board
that is open only some of the time.

**Fixed at the source, in all six scripts**, by reconfiguring the streams at
import rather than by setting an environment variable in one launcher — because
the next launcher would not have had it either.

> **A cosmetic character in a log line destroyed a measurement that had cost
> three days of waiting.** The lesson is not "avoid unicode"; it is that **a
> long-running capture must not be able to die on its own output.**

## 6. What this does NOT kill

`CLAUDE.md` §9c step 7.

- **The strikeout props themselves are not refuted.** 6 of 6 had all three
  methods agreeing, and all six came back negative on the buy side — but **six
  props on one day is not a sample**, it is a look.
- **The availability question is still open** and is the bigger obstacle:
  `RESULTS_PROPS_WINDOW.md` records the board live 15 hours on one day and absent
  on two others. **This capture is one open board out of four days watched.**
- **Only strikeouts and home runs.** Pinnacle carried no other player prop type
  on the day it opened.
- **No other sport.** Basketball and football props were never looked at.
- **Depth.** Recorded in the json, not analysed. These are thin markets and
  capacity could kill anything that survived.
- **A model.** This is a price comparison. It says nothing about whether a
  forecast could beat these prices — which is `PREREGISTRATION_TOTALSMODEL.md`'s
  question, on a different family.

---

## 7. ⚠ CORRECTION 2026-09-02 — the bar in §1 and §4 was fee-only, and too permissive

An audit pass caught that this run set `bar = fee_rate_cents(ask)` — **the fee
alone, with no spread** — while the shared engine's cost bar is half-spread +
slippage + fee. **Buying at the ask is crossing the spread, and this file did not
charge for it.**

**The verdict does not change, but the evidence for it gets cleaner.** Re-costed
with the half-spread included (`src/costbar_local.py`):

| sell-side flag | edge | old bar | **new bar** | |
|---|---|---|---|---|
| Yoshinobu Yamamoto | +1.73¢ | 1.69¢ | **2.19¢** | **gone** |
| Mookie Betts | +1.57¢ | 0.74¢ | **1.74¢** | **gone** |
| Alex Bregman | +1.02¢ | 0.63¢ | **1.63¢** | **gone** |
| Randy Arozarena | +1.46¢ | 0.89¢ | **1.39¢** | still flags |

> **Four flags become one.** The Yamamoto case §4 described as clearing "by 0.03
> cents" now **fails by 0.46¢** — it was never a candidate, and the fee-only bar
> was manufacturing candidates I then had to argue away one at a time.
>
> **The survivor is a home-run prop, which sits inside the 8-of-8 method
> disagreement that §2 reports.** So P1 still stops on its pre-registered drop
> condition, now with one arguable case instead of four.

**A permissive bar makes a null harder to reach, so §1's `0 of 14` on the buy
side was never at risk.** But it was generating false positives on the sell side,
and that is worth fixing rather than explaining away.
