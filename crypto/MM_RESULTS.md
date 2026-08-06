# MM_RESULTS.md — market-making feasibility study

Started 2026-08-01 ~06:00 UTC. Read-only, simulated fills only, no
order-placement code anywhere in this repo.

---

## 0. PREMISE CORRECTIONS — read first

### 0.1 ❌ This machine does **not** hold recorded order books

The brief says to run "on the machine holding the recorded order books." It
isn't. What this laptop's recorder actually captured, verified field-by-field:

| | |
|---|---|
| Kalshi depth fields present | **NONE — top of book only** (`yes_bid`, `yes_ask`, `yes_bid_size`, `yes_ask_size`, `no_bid`, `no_ask`) |
| Effective per-ticker resample interval | **p50 = 120 s** (p10 24.5 s, p90 134 s) — not 5 s |
| Total Kalshi recording | 265,242 rows over **~6 hours** |
| Polymarket books | full depth (median 70 levels) — but Polymarket is already ruled out on cost |

The 120-second figure is the important one and it is my own design's fault: the
recorder writes **on change**, with unconditional keyframes only every 24 cycles
(120 s). For a market that barely moves, an unchanged quote is re-written only
at the keyframe. That is correct for information content and **useless for
market-making microstructure**, which lives between those samples.

**Consequence: queue position, cancel-to-trade ratios, and depth-at-touch
dynamics cannot be measured from our recording.** Anything claiming to measure
them from this data would be invented.

### 0.2 ❌ Kalshi does not expose order-book depth publicly at all

> # ⚠⚠ THIS SECTION IS WRONG. RETRACTED 2026-08-06. Read this box first.
>
> **Kalshi order-book depth IS public, free, unauthenticated, 20 levels a side.**
> This section, and the sentence below that *"full-depth Kalshi book
> reconstruction is not available to us, now or historically"*, are the claim
> **[M001](../LEDGER.md#section-8--market-selection-merged-2026-08-06-and-bot-hunt)**,
> which `market-selection` retracted on 2026-08-02.
>
> **The cause was a parse, not the API.** The response has exactly **one**
> top-level key, **`orderbook_fp`**, holding `yes_dollars` / `no_dollars`. There
> is no `orderbook` key and no `yes`/`no` key — so reading those yields an empty
> book from an **HTTP 200 on every market**, liquid or dead. That is why it
> reproduced on 85 markets including one with $1.6 M of 24 h volume: the failure
> is deterministic and independent of the market.
>
> **Re-verified live 2026-08-06** on `KXBTCD-26AUG0620-T73299.99` — `orderbook_fp`
> returned **16 price levels**. `bot-hunt/src/venues.py::k_orderbook` has been
> reading it correctly the whole time, and its recorder stores 5¢ depth per side.
>
> **What this changes:** the two stated reasons this study could not proceed were
> (a) the laptop recorded only top-of-book at 120 s, and (b) depth is not public.
> **(b) is false.** (a) remains true of that recording, but a fresh recorder gets
> full depth for free, and `archive.pmxt.dev` carries historical L2 with
> microsecond timestamps.
>
> **What this does NOT change:** §10's verdict is still *"Not yet reached"*. The
> decisive measurement — adverse selection on real `KXBTCD` flow at 373 ms — is
> still unrun, and **C025** ("0 of 4 series profitable") still has an artifact for
> only one series. See `AUDIT_2026-08-06.md` item **D2**, ranked #2 of sixteen.
>
> Nothing below is deleted. Deleting a wrong number is how someone re-derives it.

`GET /markets/{ticker}/orderbook?depth=50` returns **HTTP 200 with an empty
body** (`keys: []`, `yes: None`, `no: None`) on a live, actively-quoted market.
So this is not a gap in our recording — **the depth is not public**. No amount of
recording from this machine fixes it. Full-depth Kalshi book reconstruction is
not available to us, now or historically.

### 0.3 ✅ But there **is** a historical trade tape, and it is very good

`GET /markets/trades` works, unauthenticated, with cursor pagination, and
crucially carries the **aggressor side**:

```
count_fp, created_time (microsecond), ticker, trade_id,
yes_price_dollars, no_price_dollars,
taker_side, taker_book_side, taker_outcome_side, is_block_trade
```

Verified reaching back across the full settled window — sampled at
**2026-07-04, 2026-07-18 and 2026-08-01**, 100 trades returned on each.

**This is the unlock, and it is the analogue of the candlesticks unlock in Phase
2.** Knowing *when a trade happened, at what price, and which side was the
aggressor* is exactly what a fill model needs: a resting order fills when the
book trades through its price with the taker on the opposite side. Combined with
the per-minute bid/ask from candlesticks, a conservative fill model is buildable
over **68 days** rather than 6 hours.

### 0.4 ✅ The 373 ms latency premise is confirmed

Measured fresh from this machine, this session:

| endpoint | n | min | **p50** | p90 | max |
|---|---|---|---|---|---|
| `/exchange/status` | 12 | 359 ms | **389 ms** | 436 ms | 532 ms |
| `/markets` (200 rows) | 8 | 341 ms | **375 ms** | — | 386 ms |

So ~373 ms is right. (Our recorder logs ~47 ms `latency_ns`, but that measures
only the socket read on a warm keep-alive connection, not a full round trip —
it should not be quoted as latency.)

### 0.5 ⚠️ Some figures in the brief come from a different project

The brief cites "27 corrections", "seven apparent positives died", weather depth
of "371–2,434 contracts", and a "within-match look-ahead canary". None of these
are from the crypto work. This project's ledger records **25 corrections and 5
withdrawn positives**, and has no match-based canaries — "within-match" is tennis
terminology. I have carried over the *discipline* those canaries encode (a
look-ahead assertion and a selection check) but implemented them for this domain
rather than pretending the tennis ones exist here.

### 0.6 Revised plan

The study is still worth running, on a different foundation:

| brief assumed | actual basis |
|---|---|
| recorded order books | **candlestick quotes (68 days) + trade tape (68 days)** |
| queue position from depth | **not measurable** — replaced with an explicit assumed-queue-ahead parameter, swept for sensitivity |
| cancel-to-trade ratio | **not measurable** — dropped, stated as a gap |
| adverse selection at +1 s | **not measurable at 1 s** — quotes are per-minute. Measured at +1 min, +5 min, and settlement |

**The +1 s and +10 s adverse-selection horizons the brief asks for are not
obtainable.** Our finest quote resolution is one minute. This is a real
limitation on the headline question, because adverse selection against a fast
counterparty happens well inside a minute, and is stated as such rather than
approximated.

---

## 0.7 ✅✅ CORRECTION THAT MAKES THINGS **BETTER** — Kalshi charges **no maker fee on crypto**

Flagged prominently because it runs *against* this project's base rate, where
every one of 25 corrections shrank the edge. This one grows it, which is
precisely why I verified it two independent ways before using it.

Kalshi exposes `fee_type` per series. Across **all 12,368 Kalshi series**:

| `fee_type` | count | categories |
|---|---|---|
| `quadratic` (taker only) | **12,224** | everything, incl. **all crypto** |
| `quadratic_with_maker_fees` | **130** | Sports, Entertainment, Economics, Financials — **zero crypto** |
| `quadratic`, `fee_multiplier: 0` | 14 | fee-free |

The 130 maker-fee series are championships, awards shows, and unemployment
prints. Kalshi's own docs corroborate: maker fees apply to "**some** markets …
often due to special events (such as the election, awards ceremony, or a large
sporting championship)."

**So on every crypto series the maker fee is ZERO — not 0.25× taker.**
`venue_spec.md` recorded 0.25× at confidence B from documentation alone; that
figure is the rate *where a maker fee exists*, and it does not exist here.
Corrected in `fees.py`, with tests (21 passing).

**Why this matters more than it sounds.** The crypto ladders have a **1¢ minimum
tick**, so a maker capturing the touch earns 1.00¢ gross:

| assumption | maker round trip | margin left to meet adverse selection |
|---|---|---|
| old (0.25× taker, wrong) | 0.875¢ | **0.125¢** |
| **verified (zero)** | **0.000¢** | **1.000¢** |

An **8× difference** in the margin available. Under the old figure market making
was arithmetically hopeless before any measurement; under the correct one the
question is genuinely open and rests entirely on adverse selection — exactly as
the brief framed it.

---

## 1. Headline

**Not yet measured on real data.** The pipeline is built and validated but the
real-data adverse-selection run has not completed. No claim is made.

## 1b. What IS established

| finding | status |
|---|---|
| Kalshi crypto maker fee = **0** | ✅ verified, API + docs, 21 tests |
| Gross margin at the touch = **1.00¢** | ✅ arithmetic on a verified 1¢ tick |
| Measured round-trip latency = **375–389 ms p50** | ✅ measured this session |
| Kalshi order-book depth | ❌ **not public** — `/orderbook` returns empty |
| Historical trade tape with aggressor side | ✅ available, 68 days |
| MM pipeline synthetic control | ✅ **PASSES** after two defects found and fixed |

## 2. Latency curve

*Pending Task 3.*

## 3. P&L decomposition

*Pending Task 3.*

## 4. Fill rates

*Pending Task 2.*

## 5. Makeable universe (Task 1, partial — scan still running)

**Sampling rule:** 6 events per series drawn on a fixed stride through all
settled events sorted by close_time, so every calendar week is represented; 4
strikes per event nearest the **anchor** (previous event's settlement, knowable
before the event opens) — never nearest the settlement, which would select on
the outcome. Final 60 minutes before close. Trades windowed to that same hour.

| series | two-sided uptime | median spread | p90 | trades/mkt/hr | median trade size | events/wk | verdict |
|---|---|---|---|---|---|---|---|
| **KXBTCD** (BTC above/below) | **86.8%** | **1.00¢** | 2.00¢ | **1,652** | 25 | 164 | ✅ **best candidate** |
| KXBTC (BTC buckets) | 81.8% | 3.00¢ | 6.00¢ | 57 | 10 | 164 | 🟡 wide spread, thin flow |
| KXETHD (ETH above/below) | 64.2% | 2.00¢ | 4.00¢ | 110 | 15 | 164 | 🟡 uptime marginal |

**The revenue trade-off is decisive and not obvious from spread alone.** KXBTC
offers 3× the gross spread but 1/29th the flow. Expected gross revenue scales as
spread × fills:

- KXBTCD: 1.00¢ × 1,652 = **1,652** units/market-hour
- KXETHD: 2.00¢ × 110 = 220
- KXBTC: 3.00¢ × 57 = 171

**KXBTCD is ~10× the opportunity of either alternative** despite having the
narrowest spread. Wide spreads on illiquid ladders are not an opportunity; they
are the market telling you nobody trades there.

**Disqualifiers as pre-registered:** D1 (spread ≤ maker round-trip) **cannot
bind**, because the maker fee is zero. D2 (uptime < 50%) — none breached yet;
KXETHD at 64.2% is the closest. D3 (< 2 trades/hr) — none breached.

⚠️ **A metric bug was caught and fixed mid-scan.** The first run reported 2,188
trades/market/hour for KXBTCD. `/markets/trades` returns a market's **entire
life** (up to 33 h for these ladders), which I was dividing by a 1-hour window —
overstating frequency by ~30×. Fixed by windowing the tape to the same
[start, close] the quotes cover, and the scan restarted. The corrected 1,652 is
still high but is consistent with a market that traded 540,644 contracts and
concentrates activity near expiry.

## 6. Capacity

*Pending.*

## 7. Cumulative hypotheses and FDR

Carried forward: **17 hypotheses / 101 individual tests / 0 tradeable edges
surviving** across Phases 0–2. MM configurations are added to
`HYPOTHESIS_LEDGER.md` as they are run.

## 8. Synthetic control — FAILED TWICE, then passed after two real fixes

Run before any real-data measurement, per the priority ladder. It earned its
place: **it caught two genuine defects that would have produced a fake profit.**

### Final result (passing)

120 synthetic markets per arm, 60 min each, 400 trades each, 373 ms latency.
Flow informativeness is a controlled multiple of the half-spread, so the correct
answer for each arm is known in advance.

| arm | drift | fill % | spread | adverse | inventory | **NET ¢/contract** | expected | ✓ |
|---|---|---|---|---|---|---|---|---|
| BENIGN | 0.3× | 92.1% | +0.5000 | −0.1386 | +0.3463 | **+0.3463** | NET > 0 | ✅ |
| **NULL** | 1.0× | 92.2% | +0.5000 | −0.4739 | +0.0037 | **+0.0037** | **NET ≈ 0** | ✅ |
| TOXIC | 2.0× | 92.2% | +0.5000 | −0.9542 | −0.4867 | **−0.4867** | NET < 0 | ✅ |

**Ordering TOXIC < NULL < BENIGN: ✅. Overall gate: PASS.**

The NULL arm landing at **+0.0037¢** against a theoretical exact zero is the
strongest single validation here: where informed flow exactly compensates the
spread, the pipeline correctly reports that a maker earns nothing. Adverse
selection also scales proportionally with the injected drift (−0.14 / −0.47 /
−0.95), which is what it should do.

### Defect 1 — inventory carry was missing from the P&L decomposition

The first gate run reported **+0.4987¢ profit on structureless flow**. Cause:
`decompose()` measured spread, adverse selection and fees but **never marked the
residual position.** Every fill is a position until it is closed; a maker who
buys 1,000 contracts and never sells has an unrealised P&L that was simply
absent from the accounting. Fixed by tracking cash and inventory per market and
marking the residual at that market's terminal mid. **This is the exact defect
the brief warned about** in asking for four components rather than three.

### Defect 2 — the control's own flow was mis-specified, twice

First attempt: trade sides drawn independently of price. That is not a null — it
is a world with *zero* informed flow, where earning the full spread is the
correct answer.

Second attempt: informed flow, but sides drawn independently **within each
minute**. Buys and sells offset, the maker filled both sides (99.79% fill rate),
and was therefore perfectly hedged. **A hedged maker cannot be adversely
selected**, so adverse selection measured ≈0 (−0.02¢) regardless of arm.

Fix: real toxic flow is **one-sided**. All trades within a minute now take the
side that profits from that minute's move. Fill rate fell to 92.1% — only one
side fills — and adverse selection immediately began behaving correctly.

**Had I skipped the control and run straight on real data, the missing inventory
term alone would have manufactured roughly +0.5¢/contract of pure fiction — on a
1.00¢ gross margin, that is a fabricated 50% edge.**

## 9. Retractions and corrections this session

| item | direction | status |
|---|---|---|
| Kalshi crypto maker fee 0.25× taker → **zero** | **grows** the margin 8× | ✅ corrected, verified 2 ways |
| "This machine holds recorded order books" | — | ❌ premise false; top-of-book only, 120 s resolution |
| Kalshi `/orderbook` gives depth | — | ❌ returns empty; depth is not public at all |
| trades/market/hour metric | shrinks by ~30× | ✅ fixed mid-scan |
| MM P&L missing inventory carry | removes a **fake +0.5¢** | ✅ fixed, gate now passes |
| Brief's "27 corrections / 7 positives / weather depth / within-match canary" | — | ⚠️ from a different project; this ledger says 25 and 5 |

## 10. Verdict

**Not yet reached.** The decisive measurement — adverse selection on real
KXBTCD flow at 373 ms — has not been run. What can be said:

- The economics are **not** foreclosed by fees, which was the live possibility
  before the maker-fee correction. Gross margin at the touch is a full 1.00¢.
- **KXBTCD is the only clearly makeable series found so far** (86.8% two-sided
  uptime, 1,652 trades/market-hour, 164 events/week).
- The pipeline is validated and would detect both a real profit and real
  toxicity.
- **The whole question now reduces to one number:** does adverse selection on
  real flow exceed 1.00¢ per round trip at 373 ms latency? The synthetic control
  shows that at drift 1.0× — where informed flow exactly compensates the
  spread — a maker nets zero. Real markets are generally *worse* than that for
  slow participants.

**My honest prior remains that this fails at 373 ms**, for the reason the B1
result already established: the Kalshi mid is an excellent forecast, which means
the flow hitting it is well-informed, which is precisely the condition under
which a slow maker is picked off. But it is now an open empirical question
rather than a foregone arithmetic one, which it was not before today.
