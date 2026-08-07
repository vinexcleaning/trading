# Crypto market making — the measurement was RUN. It does not survive its placebo.

**2026-08-07.** `src/maker_marked_to_settlement.py` →
`reports/maker_marked_to_settlement.json`.

[MM_RESULTS.md](MM_RESULTS.md) §10 is titled **"Verdict"** and opens **"Not yet
reached"**. The 2026-08-06 audit ranked it **#2 of sixteen** open items. This
closes the gap between "never run" and "run", and the answer is a null with a
control that earns it.

---

## 1. First — the premise that blocked it was false

MM_RESULTS gave two reasons the study could not proceed. The second was:

> *"❌ Kalshi does not expose order-book depth publicly at all … full-depth
> Kalshi book reconstruction is not available to us, now or historically."*

**That is claim [M001](../LEDGER.md#section-8--market-selection-merged-2026-08-06-and-bot-hunt),
retracted on 2026-08-02.** The response carries exactly one top-level key,
`orderbook_fp`; reading a non-existent `orderbook` key returns an empty book from
an **HTTP 200 on every market**, which is why it "reproduced" on 85 markets
including one with $1.6 M of 24 h volume. **Re-verified live 2026-08-06: 16 price
levels on a KXBTCD market.** Marked inline in MM_RESULTS §0.2.

**But this measurement does not need the book at all**, which is the more useful
point. MM_RESULTS itself flags the one excellent thing on disk — the **trade
tape, carrying the aggressor side**. Every trade has a taker and a maker on the
opposite side, so **a passive quoter is the maker side of the tape**. Mark every
maker fill to settlement and you have the bottom line — spread, adverse
selection and inventory all included — with **no book reconstruction and no fill
model.** The fill model is the single easiest thing to fake in a maker backtest;
here there is nothing to fake, because every fill really happened.

## 2. The raw result — positive on all four series

**2,034,720 trades**, 2026-07-30. Maker fee confirmed **zero** by fetching each
series' `fee_type` from the API rather than assuming it (all four are plain
`quadratic`, `charges_maker=False`) — the shared module *refuses* to guess.

| series | trades | **events** | maker ¢/contract | 95% CI (clustered on events) | fills profitable |
|---|---|---|---|---|---|
| KXBTCD | 123,615 | **11** | **+1.062¢** | [−3.461, +5.875] | 54.1% |
| KXBTC15M | 463,483 | **29** | **+0.873¢** | [−0.596, +2.670] | 52.3% |
| KXETHD | 12,327 | **11** | **+1.933¢** | [−0.049, +3.967] | 52.0% |
| KXETH15M | 82,387 | **29** | **+0.704¢** | [−1.237, +2.593] | 48.7% |

Every CI crosses zero. But four positive point estimates, on 2 million real
fills, against a stated 1.00¢ gross margin — this is the most promising-looking
table this programme has produced, and it is exactly the kind of thing
[LEDGER.md](../LEDGER.md)'s directional prior exists to kill.

## 3. ⚠ The placebo kills it, and on the bigger sample it kills it outright

Shuffle **which side was the aggressor**, within each event, 200 times. The
prices, the outcomes, the sizes and the clustering are all untouched — only the
maker/taker labelling is destroyed. If the edge is about being the maker, it
must not survive.

| series | events | real | **placebo mean** | placebo sd | **p** |
|---|---|---|---|---|---|
| **KXBTC15M** | **29** | +0.873¢ | **+1.351¢** | 0.216 | **0.995** |
| KXBTCD | 11 | +1.062¢ | +0.144¢ | 0.685 | 0.125 |

> **On the series with the most events, the placebo BEATS the real result.**
> Shuffling away the entire maker/taker distinction *raises* the number from
> +0.873¢ to +1.351¢. There is nothing about being the maker in it.

**And the second control names the mechanism.** "Always buy YES, ignore the
aggressor entirely" returns **+3.874¢** on KXBTC15M and **−2.269¢** on KXBTCD.
Those are one-day directional moves: on 2026-07-30, YES settled more often than
the average traded price implied on the 15-minute ladders, and less often on the
daily ones. **Any strategy that happened to be net-long YES that day looks
profitable, and any that was net-short looks terrible.** That is what the
"maker edge" is made of.

`KXBTCD`'s p = 0.125 is not a pass either — it is **11 correlated hourly windows
on a single day**, which cannot resolve anything. And C026 already measured that
the four crypto assets are **~1.81 effective independent series, not four**, so
the four rows above are not four confirmations.

## 4. Verdict

**NOT REPORTABLE as an edge, and the reason is data volume rather than method.**

| | |
|---|---|
| the premise that blocked it | **false, corrected** — depth is public |
| the method | **built and validated by its own placebo** |
| the fee treatment | **fetched per series, not assumed** |
| the binding constraint | **one day of tape → 11–29 correlated events, on a day with a large directional move** |

**What makes this different from "underpowered" in the usual sense:** the placebo
is *not* underpowered — it has the same n and it returns a *larger* number. So
this is not "we could not tell". On KXBTC15M we can tell, and the answer is that
the aggressor label carries no information at this sample.

## 5. The single next thing, and it is now cheap

**Pull the trade tape across many days.** The tape is re-pullable and the
retention boundary turned out to be a **fixed calendar date (2026-05-25)**, not
the 69-day rolling window M009 claimed — re-bisected 2026-08-06, unmoved across
three measurements while its apparent age went 69 → 71 → 73 days. So roughly
**73 days of tape are retrievable, against the one day used here.**

That converts 29 events into ~2,000, and it is the difference between a placebo
that wins and a test that can decide. Estimated cost: a few thousand paced
requests, sequenced **after** the recorder's needs, never beside a second heavy
puller (C018 puts the unauthenticated ceiling at 15 req/s).

> **Stated plainly so it is not mis-cited:** this file does **not** show that
> market making on Kalshi crypto loses. It shows that the one day of evidence
> available says nothing, that the apparent +0.87 to +1.93¢ is a one-day
> directional artifact, and that the question is now genuinely runnable for the
> first time.

---

## 6b. ⚠⚠ FINAL, at 658 events — and it corrects §6 twice. Read this, not §6.

**§6 below was written at 415/664 markets and clustered on the wrong unit. Two
errors, both mine, both found within minutes of each other.**

### Error 1 — I clustered on the event. The events are not independent.

All ~96 fifteen-minute BTC windows in a day share **one BTC trajectory**. They
are nowhere near 96 independent observations. Clustering on the day instead:

| | mean | 95% CI | **CI width** |
|---|---|---|---|
| event-clustered (§6, wrong) | +0.321¢ | [−0.368, +0.997] | **1.36¢** |
| **day-clustered (right)** | — see error 2 | — | **7.78¢** |

**5.7× too narrow.** This is C019/C026's lesson and K003's exactly — *a
ten-strike ladder is one temperature reading, not ten markets*. Here **a day of
15-minute BTC markets is far closer to one observation than to 97**, and I made
the same mistake the ledger already records twice.

### Error 2 — the day-clustered number was itself contaminated, by ONE market

The day-clustered mean came out **−2.206¢** and I nearly reported that. Per day:

| day | maker P&L | events |
|---|---|---|
| 07-24 … 07-30 | +0.624 · +0.595 · +0.975 · −0.497 · +0.351 · +0.370 · −0.619¢ | 96, 96, 96, 96, 96, 96, 81 |
| **07-31** | **−19.444¢** | **1** |

**2026-07-31 is not a day — it is the pull's exclusive end boundary, and exactly
one 15-minute market landed on it.** A single market was dragging the whole
eight-day mean from +0.257¢ to −2.206¢. Dropping it:

| | 7 full days |
|---|---|
| maker absolute P&L | **+0.257¢/day**, positive on **5 of 7**, day sd ≈ 0.55¢ |
| **adverse selection (real − placebo)** | **−0.526¢**, negative on **7 of 7** |

### What actually survives

| | |
|---|---|
| **Adverse selection is REAL and CONSISTENT** | **negative on 8 of 8 days**, day-clustered mean **−1.256¢, 95% CI [−2.788, −0.344]** — excludes zero. Excluding the stub day it is **−0.526¢** and still 7 of 7. |
| **It GREW as data was added** | −0.387¢ at 432 events → **−0.532¢** at 658. Every step of this analysis moved against the maker. |
| **Total maker P&L is NOT resolvable** | +0.257¢/day against a day sd of 0.55¢ on 7 days. The honest statement is *unknown*, not *positive*. |

> **Retracting my own framing from two messages ago.** I wrote that adverse
> selection at 0.387¢ against a ~1.00¢ spread was *"the first encouraging sign in
> this programme."* At full sample the cost is **0.532¢**, it grew 37% when I
> added 52% more events, the absolute P&L fell from +0.504¢ to +0.321¢, and the
> correct clustering leaves the total unmeasurable. **Every one of those moves is
> in the discouraging direction. That is the directional prior holding for the
> 49th time, and I got ahead of the data.**

**What is genuinely new and stands:** adverse selection on real Kalshi crypto
flow is **~0.5¢ per contract, consistent on every day measured**. That is the
number `MM_RESULTS.md` §10 asked for. It is **below** the ~1.00¢ gross margin —
so the question is not settled against market making, it is *unresolved*, and
resolving it needs **weeks of days, not hundreds of correlated 15-minute
windows**, plus the other half: what a resting order actually captures, which
needs the order book this project already records.

---

## 6. Superseded — the 415-market run (kept; §6b corrects it)

**2026-08-07.** `src/maker_multiday.py` → `reports/maker_multiday.json`.
**432 KXBTC15M events, 3,263,999 trades, 5 days, 0 rows dropped, 0 markets
page-capped.** Against the 29 events §3 had.

`MM_RESULTS.md` §10 named exactly one open question: *"does adverse selection on
real flow exceed 1.00¢ per round trip?"* **It now has an answer.**

| | KXBTC15M, 432 events |
|---|---|
| **REAL** maker P&L, marked to settlement | **+0.5044¢** · 95% CI **[−0.3101, +1.2872]** |
| **PLACEBO** — passive side reassigned at random within each event | **+0.8911¢** · sd 0.0681 |
| **REAL − PLACEBO** | **−0.3867¢** · permutation **p = 0.0000** |
| D1 always-long-yes / always-short-yes | **+0.6263¢ / −0.6263¢** |
| D2 per day | 5 days, mean +0.414¢, **positive on 80%** |
| D3 stability at 25 / 50 / 75 / 100% of events | **+0.526 · +0.555 · +0.535 · +0.504¢** |

### What changed from the one-day run, and it is the whole point

At 29 events the placebo beat the real result at **p = 0.995** — indistinguishable
noise. At **432** events the placebo still beats it, but now by
**−0.3867¢ with p = 0.0000.** The placebo's own sd tightened **0.216 → 0.068**, a
3.2× narrowing against the 3.9× that √(432/29) predicts.

> **That is adverse selection, measured.** Being the passive side is
> **significantly worse than having the passive side assigned at random** — which
> is only possible if takers systematically hit at prices that turn out to
> favour them. **It costs the maker 0.387¢ per contract.**

### Three things this does NOT say

1. **It does not say the maker lost money.** The maker side earned **+0.504¢** in
   absolute terms. That figure's CI crosses zero and it is contaminated: D1 shows
   this window had a real directional drift (**always-long-yes +0.626¢**), so any
   participant net-long YES looked good regardless of who was passive.
2. **It does not say adverse selection exceeds the spread.** 0.387¢ against
   MM_RESULTS' stated **1.00¢** gross margin at the touch. **On this measurement
   it does not** — which is the first result in this programme pointing toward a
   strategy rather than away from one, and is exactly why it needs the caveats
   below rather than a headline.
3. **The two statistics answer different questions and must not be merged.** The
   permutation test is **within**-event (valid for adverse selection); the
   bootstrap CI is **between**-event (valid for total P&L). The total is not
   distinguishable from zero; the adverse-selection term is, decisively.

### Limitations, stated rather than buried

- **5 days, one series, and only the first 5 minutes of each market's life.**
  That slice was chosen before any P&L was computed, and for a stated reason
  (§below), but it is a slice.
- **This is the maker side of ALL flow** — a quoter permanently at the touch on
  both sides. A real maker chooses when and where to quote, so this is a lower
  bound on skill and an upper bound on volume.
- **It measures fills that happened, not a fill model.** That is the design's
  strength and also its ceiling: it cannot tell you what a *different* quote
  would have earned.
- **The pull was still running at 415/664 markets** when this ran. D3's stability
  curve is flat to ±0.05¢ across quartiles, so more events are expected to move
  the point estimate very little — but the run should be repeated at completion.

### The honest next step

**Do not build anything on +0.504¢.** The one number that is solid is the
**−0.387¢ adverse-selection cost**. To know whether quoting is viable you need
the other half — what a resting order actually captures — and that needs the
**order book**, which is public and free (§1) and which the recorder has been
storing all along. That is the measurement `bot-hunt`'s H10 machinery already
does, pointed at crypto instead of esports.

---

## 7. IN FLIGHT (2026-08-07) — the multi-day tape pull. Do not kill it.

`src/pull_trade_tape.py`, **PID 28028**, writing `crypto/data/trade_tape.db`.
**Resumable per ticker** — if it dies, re-run the same command and it skips what
it has.

```bash
C:/Users/vinig/trading/bot-hunt/.venv/Scripts/python.exe src/pull_trade_tape.py --series KXBTC15M --start 2026-07-24 --end 2026-08-07 --pace 0.2 --slice-min 5
```

| | |
|---|---|
| target | **1,327 settled KXBTC15M markets = 1,327 events**, against the **29** the one-day run had |
| what is kept | the **first 5 minutes of every market's life**, uniformly |
| rate | ~7.8 s/market, ~10,350 trades per slice, **0 markets hitting the page cap** |
| analysis, ready to run | `src/maker_multiday.py` |

**The test statistic is `real − placebo`, not `real`.** That is the lesson of §3:
the raw number was positive and meaningless.

### Three defects in my own tooling, found by running it

1. **`/markets/trades` silently ignores `series_ticker`** — it returns KXABNB,
   KXALIENS, KXASEANGAME. A filter that is accepted and ignored is worse than
   one that errors.
2. **Committing every 100 tickers did not finish.** Each market carries
   20,000–30,000 trades, so the transaction held ~2M uncommitted rows and every
   `insert or ignore` re-checked the primary key against the growing set.
   **45 minutes, a 325 MB WAL, 2,580 s of kernel time, zero rows visible.**
3. **The cursor is NEWEST-FIRST**, so a page cap keeps the trades nearest
   settlement and discards early price discovery — the worst direction to
   truncate in, and adjacent to the leak that voided T010. Replaced with a
   uniform time slice.
