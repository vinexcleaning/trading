# FINDINGS.md — what this project established

Written 2026-08-03. Seven independent tests, seven nulls. This file is the
answer to the question the project was set up to ask.

## The question

Is there a tradeable edge on Kalshi — a way to know something the price does
not?

## The answer

**No, in every market tested, by every mechanism tested.** Kalshi is
efficiently priced wherever a counterparty exists.

| # | Market | Mechanism | Result |
|---|---|---|---|
| 1 | Tennis (prior work) | pre-match model vs bookmakers | model worse, **+0.01922 Brier** [+0.01438,+0.02417], n=2,645 |
| 2 | Crypto ladders (prior work) | model vs the mid | **no model beats the mid**, n=250 events, positive control passed |
| 3 | Polymarket copy trading (prior work) | follow skilled wallets | copyable edge **+0.937pp < the 1.0pp spread**, and decaying |
| 4 | Soccer (5 leagues) | model vs closing line | model worse, **+0.02170** [+0.01626,+0.02750], n=2,875 |
| 5 | MLB first innings | model vs Kalshi's own price | does not beat, **+0.00237** [−0.00072,+0.00553], n=771 |
| 6 | MLB in-play | react to news faster than the market | market reprices in **2.2s**. Unreachable. |
| 7 | MLB first innings + Statcast | 846,343 pitches of real pitch quality | does not beat, **+0.00212** [−0.00099,+0.00520], n=771 |

## The decisive diagnostic

Test 7 was designed to answer *why* test 5 failed, not just to repeat it.

Test 5's model could barely tell games apart — its probabilities varied by
**1.89pp** while Kalshi's varied by **~6.5pp**. The hypothesis was that better
pitcher data would close that.

Adding a decade of Statcast — expected wOBA on contact, hard-hit rate,
strikeout and walk rates, on 846,343 first-inning pitches — moved the spread
from **1.89pp to 2.89pp**. Still under half the market's. And the improvement
over simply guessing the base rate barely moved at all: **+0.00033 → +0.00034**.

**So the market's advantage is not pitch quality.** The best free measurement
of how good a pitcher is, applied properly and leak-free, closes almost none of
the gap. Whatever Kalshi knows is something else — late scratches, weather at
first pitch, order flow, or simply that a single inning is mostly irreducible
noise and the market has correctly priced that.

That is the cleanest available signal to stop. Further feature work on this
market is not warranted.

## Corroboration: Kalshi matches sharp references in three sports

| Sport | Reference | Agreement |
|---|---|---|
| Tennis | Betfair close | r = 0.9878, MAD 1.95¢ vs a 2.44¢ cost |
| MLB | DraftKings moneyline | median **0.37¢**, 0 of 26 beyond the cost bar |
| Soccer | market-average close | r = 0.9593, median **1.12¢** vs a ~2.0¢ cost |

## What was learned that IS durable

- **Kalshi order-book depth is free** — 20 levels a side via
  `orderbook_fp.{yes,no}_dollars`. Two prior sessions concluded otherwise;
  both read a key that does not exist.
- The exchange's tape retains **exactly 69 days**, and there is a **weekly
  Thursday maintenance window ~07:00–09:00 UTC**.
- **`tick_size` does not exist**; the tick is `price_level_structure`.
- The pmxt L2 archive's `delta` is an **absolute size**, not a change — but the
  replay is only accurate to **2–3¢ on 15–20% of trades**, which is the size of
  the entire edge being sought, so it cannot support fill simulation.
- ESPN's free API is unexpectedly rich: UTC wallclock per event, lineups,
  formations, referee, odds, a decade of history.
- **No free xG exists** for Liga MX, Argentina, Colombia or MLS.
- **Pinnacle vanished from football-data's 2026 data** — the second time a
  Pinnacle feed has disappeared mid-project (LEDGER T014 was the first).

## The methodological finding, which may matter most

**Ten corrections were made across this work. Every one shrank or removed a
claim. Not one revealed a larger effect.**

Four occurred in a single day, and all four initially looked like discoveries:

1. a **+17.25¢ edge** on first-inning markets — created by a filter that
   discarded quotes when the ask hit 100, which selected on the outcome
2. **301,578 contracts of depth** — a single snapshot; the same market showed
   19 contracts twelve hours later
3. a **+51-second trading window** after a run scored — the median at-bat lasts
   72 seconds; I had started the clock before the event happened
4. a **crossed order book** — bid 99¢ against an ask of 22¢, from assuming
   `delta` meant a change in size

Each was caught by a consistency check, not by inspection. **That asymmetry —
every promising number dissolving, none surviving — is what an efficient market
looks like from the inside.**

## Recommendation

Stop looking for an edge on this exchange with these methods. The evidence is
consistent across four sports, three mechanisms (prediction, latency,
cross-venue) and two venues.

The durable output is not a strategy. It is `GUARDS.md`, `common/costbar.py`,
`common/backtest.py`, `common/leakguard.py` and `common/bookreplay.py` — the
apparatus that kept catching the errors. If this work resumes, it should resume
somewhere the apparatus can be pointed at a genuinely different question, not
at a fifth sport.
