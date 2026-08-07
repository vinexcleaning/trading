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

## 6. IN FLIGHT (2026-08-07) — the multi-day tape pull. Do not kill it.

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
