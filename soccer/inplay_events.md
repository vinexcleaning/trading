# inplay_events.md — what the Kalshi price does after a goal

**Descriptive only.** No entry rules, no P&L, no edge claim. This is a
description of market behaviour.

Measured 2026-08-02. Artifacts: `data/inplay_events.json`,
`reports/inplay_analysis.txt`, scripts `src/inplay.py`, `src/analyse_inplay.py`.

| | |
|---|---|
| Fixtures | **130** completed, matched Kalshi↔ESPN |
| Events | **255** — 229 goals, 26 red cards |
| Leagues | Liga MX, Argentina Primera, Copa do Brasil, Colombia, MLS |
| Window | 2026-05-24 → 2026-08-02 (Kalshi's ~69-day retention) |
| Unit of observation | **one event × the scoring team's own contract** |
| Price | mid of `yes_bid`/`yes_ask` close, 1-minute candles |
| Fixtures with no ESPN summary | **0** |
| Fixtures with no Kalshi candles | **0** |

---

## ⚠ First: the clock problem is real, large, and already solved

The tasking asks me to measure the alignment error rather than assume it is
zero. Measured, on 362 events carrying both a displayed minute and a wallclock:

| minute-implied timestamp − true wallclock | |
|---|---|
| median | **−17.52 min** |
| p10 / p90 | −21.80 / +0.78 min |
| min / max | −29.52 / +0.98 min |
| \|error\| > 1 min | **58.0%** of events |
| \|error\| > 5 min | **55.2%** of events |

A join built on `kickoff + displayed_minute` would be wrong by **a quarter of
an hour at the median** and by nearly half an hour at worst — because halftime
and stoppage are real elapsed time that the displayed minute does not count.

**But no such join was needed.** ESPN publishes `wallclock`, an absolute UTC
instant, on every keyEvent, and `wallclockAvailable` is `true`. That field was
used throughout, so **the alignment error in this study is zero, not
estimated.** The premise that the mapping must be approximated is false; the
premise that a minute-based mapping would be badly wrong is correct and is
quantified above.

---

## Goals — the scoring team's own contract

Median mid price, in cents, at each offset from the goal:

| Offset (min) | n | median | mean | median spread |
|---|---|---|---|---|
| −5 | 229 | 32.50 | 38.06 | 1.00 |
| −1 | 229 | 36.50 | 40.01 | 1.00 |
| **0** | 229 | **60.50** | 55.36 | **2.00** |
| +1 | 229 | 71.50 | 61.76 | 1.00 |
| +3 | 227 | 72.50 | 62.82 | 1.00 |
| +5 | 223 | 73.50 | 63.42 | 1.00 |
| +10 | 216 | 75.50 | 63.26 | 1.00 |

**The move, T−1 → T+1:** mean **+21.75¢**, median **+19.00¢**, sd 19.08.
94% of goals move the scorer's price up.

### The distribution matters more than the mean

| T−1 → T+1 | p10 | p25 | median | p75 | p90 | min | max |
|---|---|---|---|---|---|---|---|
| cents | +1.50 | +9.00 | **+19.00** | +26.50 | +43.00 | −3.00 | +94.00 |

The spread of outcomes is enormous — a goal is worth anywhere from ~0 to ~94¢
depending on scoreline, time remaining and starting price. **A single "goals
are worth 20¢" number would be actively misleading.** By T+10 the p10/p90 range
is +0.50 / +54.00.

### Favourite vs underdog

| | n | median px at −1 | median move −1→+1 | median move −1→+10 |
|---|---|---|---|---|
| **Favourite scores** | 128 | 45.00 | **+19.75¢** | +21.25¢ |
| **Underdog scores** | 101 | 20.50 | **+17.50¢** | +18.00¢ |

The two are close. The favourite's goal moves its price slightly more in
absolute cents, which is unsurprising given it starts higher and a goal pushes
it further toward a region where the remaining uncertainty is small. **The
difference (≈2¢ at the median) is well inside the dispersion (sd ≈19¢) and
should not be treated as an established asymmetry** on n=128 vs n=101.

---

## Red cards — the offending team's own contract

| Offset | n | median | mean |
|---|---|---|---|
| −5 | 26 | 13.25 | 25.54 |
| −1 | 26 | 9.75 | 23.48 |
| 0 | 26 | 7.25 | 24.29 |
| +1 | 26 | 7.75 | 22.50 |
| +3 | 24 | 4.50 | 19.60 |
| +10 | 22 | 4.50 | 18.07 |

| move | mean | median | frac positive |
|---|---|---|---|
| −1 → +1 | −0.98¢ | −0.75¢ | 0.19 |
| −1 → +10 | −4.18¢ | −2.00¢ | 0.18 |
| −5 → +10 | −7.11¢ | −4.00¢ | 0.14 |

**Red cards are much smaller than goals in this sample, not larger.** The
tasking anticipated "rarer and larger"; they are certainly rarer (26 vs 229) but
the median move is **−2¢ over ten minutes** against a goal's +20¢.

Two honest reasons to distrust that as a general fact:
1. **n=26, and only 22 survive to T+10.** The mean (−4.18¢) and median (−2.00¢)
   diverge sharply, so the distribution is skewed and badly under-sampled.
2. **The offending team is usually already losing** — median price 9.75¢ at
   T−1. A contract at 10¢ has little room to fall, so the measured move is
   compressed by where it starts, not necessarily by how little the red card
   matters.

---

## How fast does the price stabilise?

Fraction of the eventual T−1 → T+10 move already realised, over events that
moved at least 1¢:

| | by T+0 | by T+1 | by T+3 | by T+5 |
|---|---|---|---|---|
| **Goals** (n=199) | **71.7%** | 91.3% | 95.9% | 98.3% |
| **Red cards** (n=17) | 36.4% | 45.5% | 90.0% | 100.0% |

**Goals: ~72% of the move is already in the price within the same minute the
goal is scored, and ~91% within one minute.** The market is fast. Red cards
resolve more slowly — under half the move at T+1, most of it by T+3 — which is
consistent with a red card's consequence being ambiguous until play resumes,
though n=17 makes this weak.

The spread widens from 1.00¢ to **2.00¢ in the minute of the goal** and returns
to 1.00¢ by T+1. So the moment of maximum price movement is also the moment of
maximum cost, and any move measured on the mid overstates what was executable
precisely then.

---

## ⚠ A selection effect in the pre-event prices, named

The scoring team's median price rises from **32.50¢ at T−5 to 36.50¢ at T−1** —
before the goal. This is **not** evidence that the market anticipates goals.
The sample is conditioned on *having scored*, so the pre-event prices are drawn
from team-minutes that ended in a goal. Teams pressing hard both score more
often and drift up in price. The T−5→T−1 drift is a property of the selection,
not a forecast.

A neutral version of this question needs a control sample of team-minutes with
no goal, which was not built here. **Do not read the +4¢ pre-drift as a
signal.**

---

## Coverage

| League | goals | red cards |
|---|---|---|
| arg.1 | 68 | 12 |
| bra.copa_do_brazil | 22 | 1 |
| col.1 | 41 | 6 |
| mex.1 | 46 | 3 |
| usa.1 | 52 | 4 |

130 fixtures processed, median 2 captured events per fixture.

## What this does NOT say

- It says nothing about whether any of this is tradeable. The 2¢ spread at the
  moment of the goal, the 1¢ spread either side, and Kalshi's `quadratic` fee
  are all costs a strategy would pay; none has been netted here.
- It says nothing about *reaction latency* in seconds. One-minute candles
  cannot resolve whether the price moved in 2 seconds or 50.
- It measures the scoring team's own leg only. The tie leg and the opponent's
  leg move too and were not analysed.
- 216 of 229 goals have a T+10 price; the 13 missing are goals late enough that
  the market closed. Late goals are therefore slightly under-represented at the
  longer offsets.
