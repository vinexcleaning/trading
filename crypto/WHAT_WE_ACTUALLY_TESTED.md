# WHAT WE ACTUALLY TESTED

A plain-language accounting of the whole crypto research effort.
Written 2026-08-01. **No new tests were run to produce this document** — it is a
report on work already done.

Every number below has its sample size and date range next to it. Where a number
came from a sample, the way the sample was drawn is stated, because this project
has produced false positives from badly-drawn samples more than once.

---

## 1. The one-paragraph version

**The question:** on Kalshi's crypto markets — contracts that pay $1 if Bitcoin
is above some price at some hour and $0 otherwise — can we predict the outcome
better than the market's own price does? **The data:** 250 randomly-spaced hours
of real Bitcoin contract prices, minute by minute, over 68 days (25 May to 30
July 2026), covering 1,968 individual contracts and 89,806 price observations,
matched against what Bitcoin actually did. **The answer: no.** We built four
increasingly sophisticated forecasting models. The best one matched the market's
accuracy almost exactly and could not beat it; two were clearly worse. **What
this covers:** buying or selling Bitcoin hourly contracts on Kalshi at prices
between roughly 5¢ and 95¢, one hour or less before they expire, based on
forecasting where Bitcoin will end up. **What it does not cover:** making money
by *quoting* prices rather than predicting them (market making), anything faster
than one minute, any asset other than Bitcoin and Ethereum, most of Kalshi's 272
crypto markets, and any lead-lag relationship between assets — that last one was
never tested at all. Section 5 lists the boundary precisely.

---

## 2. Every hypothesis tested

"Survived correction?" means: after accounting for the fact that we ran 101
separate tests, and some will look significant by pure luck, did this one still
stand up? (The method is Benjamini–Hochberg — the more tests you run, the higher
the bar each one must clear.)

### Phase 0–1: structure, costs, and the underlying data

| # | Plain-English question | Data source & dates | Sample size & unit | Result in plain numbers | Survived correction? | Verdict |
|---|---|---|---|---|---|---|
| 1 `A2` | Are Kalshi's price ladders internally contradictory in a way we could arbitrage? (If "BTC above $60k" is cheaper than "BTC above $61k", that's free money.) | Live Kalshi recorder, 2026-08-01, 10.5 min | 3,187 ladder snapshots / **26 events** | **0 contradictions found**, ever | n/a (nothing to correct) | No free money. The ladders are internally consistent. |
| 2 `A1` | Do the price buckets in one hour add up to more or less than 100¢? (If all buckets cost 97¢ total, buy them all and collect $1.) | Live Kalshi recorder, 2026-08-01, 10.5 min | 1,135 complete ladder snapshots / **26 events** | **1 violation** worth +1.00¢ gross. Trading it costs **1.93¢ in fees** across 75 contracts → **loses 0.93¢** | n/a | Real but unprofitable. The ladder is so wide that fees eat any gap. |
| 3 `C8` | Does Bitcoin "stick" to round numbers like $60,000 more than chance? | Kalshi settled data, 25 May – 1 Aug 2026 | 1,593 hourly settlements / **event** | 6 of 20 tests looked significant, **all were artifacts** | **No — retracted** | ❌ **RETRACTED.** Not supported. See §7. |
| 4 `F1` | Is Polymarket's trading fee what its documentation says? | Polygon blockchain records, 20–27 Apr 2026 | 4,310 actual fee payments | Documentation says 1.75¢ per contract at 50¢. **Reality is 5.00¢** — 2.86× more. Formula matched to 6 decimal places on 100% of fills | n/a (exact match, not a statistical test) | ❌ Documentation was **wrong**. Polymarket is far more expensive than published. |
| 5 `C9` | Are hourly Bitcoin moves more extreme than a normal bell curve predicts? | Kalshi settled data, 25 May – 1 Aug 2026 | 1,582 hourly returns / **event** | Moves beyond 3 standard deviations happen **7× more often** than a bell curve says; beyond 4 sd, **140× more often** | ✅ **Yes** (overwhelmingly) | ✅ **TRUE.** Crypto has fat tails. This is a fact about the world, not an edge. |
| 6 `C9-econ` | Can we make money from those fat tails? | — | — | Claimed 1.5–1.9¢ profit per contract | **No — withdrawn** | ❌ **WITHDRAWN.** We compared against a bell curve we invented, not against the market. See §7. |
| 7 `L4-A` | If we feed the whole system fake data with **no edge in it**, does it correctly find nothing? | Simulated | 1,500 fake events | Found nothing. Difference −0.000028, confidence range includes zero | ✅ Pass | ✅ The system doesn't hallucinate edges. |
| 8 `L4-B` | If we plant a **15% mispricing** in fake data, does the system find it? | Simulated | 1,500 fake events | Found it clearly | ✅ Pass | ✅ The system has real detection power. |
| 9 `L4-B5` | Same, with a smaller **5% mispricing**? | Simulated | 1,500 fake events | Found it | ✅ Pass | ✅ Sensitive down to 5% under clean conditions. |
| 10 `L4-C` | If we secretly leak the answer into the model, does the system catch the cheating? | Simulated | 1,500 fake events | Caught it immediately | ✅ Pass | ✅ The leak detector works. |

### Phase 2: the headline test — can any model beat the market's price?

Panel: **250 events, 89,806 minute-by-minute observations, 1,968 contracts,
10 calendar weeks, 25 May – 30 July 2026.**

**How the sample was drawn** (this matters — read it): of 1,593 settled hourly
events, 1,525 had usable data. We sorted them by date and took **every 6th one**,
giving 250 events spread evenly across all 10 weeks. Within each event we took
the **8 contracts closest to where Bitcoin was when the hour opened** — *not* the
8 closest to where it ended, which would have been cheating by using the answer
to pick the sample. Weekly coverage was even: 4,650–10,572 observations per week.

| # | Plain-English question | Sample size & unit | Result in plain numbers | Survived correction? | Verdict |
|---|---|---|---|---|---|
| 11 `B1-M1` | Does a standard textbook option model beat the market price? | **250 events** | Model's error 0.120431 vs market's 0.119733. **Market slightly better.** Statistically a tie (p=0.78) | No | ❌ No. |
| 12 `B1-M2` | Does that model, corrected for how Kalshi actually settles, beat the market? | **250 events** | Model 0.120091 vs market 0.119733. **Dead heat** (p=0.94) | No | ❌ No — matches the market, cannot beat it. |
| 13 `B1-M3` | Does a fat-tailed model beat the market? | **250 events** | Model 0.123043 vs market 0.119733. **Market clearly better** (p=0.001) | Market wins | ❌ No — actively worse. |
| 14 `B1-M3t` | Same with a different fat-tail formula? | **250 events** | Model 0.143255 vs market 0.119733. **Much worse** | Market wins | ❌ No — far worse. |
| 15 `B1-ORD-a` | Does correcting for Kalshi's 60-second averaging settlement genuinely improve a model? | **250 events** | Yes: improvement 0.000342, confidence range [0.000242, 0.000436], excludes zero | ✅ **Yes** | ✅ **TRUE.** A real, measurable modelling improvement — just not enough to catch the market. |
| 16 `B1-ORD-b` | Does adding fat tails improve on the corrected model? | **250 events** | No — makes it **worse** by 0.003784 | Rejected | ❌ Kalshi already prices tails properly. |
| 17 `MIDCAL` | Is the market's own price systematically biased in a way we could trade? | **250 events × 17 price buckets** | Raw numbers suggested the market underprices by up to **4.2 percentage points**. After correcting for double-counting, 14 of 17 buckets became noise; best survivor p=0.029 against a required 0.0059 | **No** | ❌ **WITHDRAWN.** The apparent bias was a counting error. See §7. |

Plus **21 localisation sub-tests** (by time-to-expiry, distance-from-strike,
price level, spread width), **6 two-period stability tests**, and **17 stability
re-tests**.

### Tests that were pre-registered but never run

Listed for honesty — these are gaps, not results.

| Test | Why it wasn't run |
|---|---|
| `X1` Polymarket historical order books | **Impossible.** Those records were never public — Polymarket matches trades off-exchange and only publishes completed trades. |
| `X2` Polymarket historical short-dated backtest | **Impossible.** Settled short-term markets disappear from Polymarket's public data (1 of 21 days retrievable). |
| `X3` Kalshi order-book replay | **Impossible here.** Kalshi has no historical order-book endpoint; the recordings live on the desktop machine. |
| `X4` Deribit-vs-Kalshi price comparison | **Impossible.** Deribit's shortest usable option expires in 54 hours; Kalshi's contracts last 1 hour. No overlap for 99.9% of contracts. |
| `A3`, `A4`, `A5` cross-expiry / cross-venue arbitrage | **Ran out of time** — needs more recording. |
| `C1`–`C7`, `C10` volatility forecasting, time-of-day, CME gaps | **Ran out of time.** |
| `D1`–`D5` who we're trading against, adverse selection | **Ran out of time** — needs recorded order books. |
| `E-A`–`E-I` all nine strategy families | **Deliberately gated off.** See §5. |
| `M4`–`M6` seasonal, blended and machine-learning models | **Ran out of time.** M1–M3 already tied or lost; see §5 for whether this matters. |
| Hour-of-day and volatility-regime breakdowns | **Written into the code but not executed** — the base result was null, so breaking a zero into buckets was moot. An honest gap. |

**Totals: 17 hypotheses, 101 individual tests. 2 facts survived correction
(`C9` fat tails, `B1-ORD-a` settlement correction). Zero tradeable edges
survived. Five apparent positives were withdrawn.**

---

## 3. Every data source used

All free. **No paid data was used. No money was ever at risk** — no
order-placement code exists anywhere in this project, and no wallet was connected.

### Used

| Source | What it is | Cost | Date range pulled | Rows | Used for |
|---|---|---|---|---|---|
| **Kalshi settled markets** (`/markets`) | Final results of expired contracts: strike, outcome, and the official settlement price | Free, no login | 25 May – 1 Aug 2026 | **1,483,451 rows** across 12 series (KXBTC 291,840; KXBTCD 292,160; KXETH/KXETHD 186,945 each; KXSOLD 188,975; KXXRP/KXXRPD 117,120 each; KXDOGED 83,030; four 15-min series 6,429 each) | Outcomes, strikes, the official BTC/ETH price series |
| **Kalshi candlesticks** | Minute-by-minute bid and ask history for expired contracts | Free, no login | 25 May – 30 July 2026 | **118,233 candles → 89,819 usable rows** | **The headline test.** This was the unlock — it's the only source of what the market was actually charging at decision time |
| **Coinbase spot candles** | Minute-by-minute Bitcoin price | Free, no login | 24 May – 1 Aug 2026 | **99,402 minutes** (99.98% coverage) | Model inputs — where Bitcoin was at each decision minute |
| **Deribit options** | Full Bitcoin/Ethereum option chain and the DVOL volatility index | Free, no login | Live snapshot, 1 Aug 2026 | 870 BTC + 742 ETH instruments, 13 expiries each | Built a working "correct price" calculator — then found it unusable at Kalshi's horizons (see §5) |
| **Polygon blockchain** (Goldsky) | Every Polymarket trade ever settled on-chain | Free | Indexed 21 Nov 2022 – 28 Apr 2026 | 4,310 fee-bearing trades sampled | **Proved Polymarket's published fees are wrong** |
| **Polymarket Gamma / CLOB / data-api** | Market definitions, live order books, recent trades | Free | Live | 57,470 book snapshots, 13,748 trades | Establishing what's tradeable and what history exists |
| **Live recorder (ours)** | Our own recording of Kalshi quotes and Polymarket books | Free | 1 Aug 2026 onward, ~4 hours | **228,530 Kalshi quotes, 57,470 Polymarket books, 13,748 trades** | The ladder-arbitrage tests; future market-making work |

### Probed and rejected

| Source | Why rejected |
|---|---|
| **Binance API** | Geo-blocked from this machine (HTTP 451). |
| **Bybit API** | Geo-blocked (HTTP 403). |
| `data.binance.vision` | **Works** — free historical data going back years. Never used; we ran out of time before needing it. |
| **Polygon public RPC** | API key disabled. Worked around via the Goldsky index. |
| **LMAX public data** | Endpoint returns 404. |
| **CF Benchmarks API** | Returns an empty payload on the index list. Worked around: Kalshi's settled records contain the official settlement price directly. |
| **The desktop machine's data** | ~6,271 prior BTC markets, 102,716 candles, 1.77M recorded trades, and all recorded order books — **not on this laptop.** Different machine. Documented in `BLOCKED_ON_DESKTOP.md`. |

---

## 4. The correlations that were actually measured

**Read this section carefully, because the honest answer is uncomfortable.**

You said you believe things like "BTC and ETH are related" must be exploitable.
Here is exactly what was measured and what was not.

| Relationship | Measured value | Sample & dates | Simultaneous or predictive? | Measured lead |
|---|---|---|---|---|
| **BTC vs ETH hourly returns** | **correlation = 0.891** | 1,582 hourly returns, 25 May – 1 Aug 2026 | **SIMULTANEOUS** — both measured in the *same hour* | **Zero. No lead was measured.** |
| **BTC vs ETH extreme hours** | **62%** of BTC's biggest hours were also ETH's (20 of 32 shared) | 1,582 hours, same dates | **SIMULTANEOUS** | **Zero.** |
| **Kalshi's official price (BRTI) vs Coinbase spot** | Differ by **+1.48 basis points** on average (about $9 on a $62,900 Bitcoin), scatter 3.02bp | 758 hourly boundaries, first half of the sample | **SIMULTANEOUS** by construction — both at the same instant | **Zero.** |
| **Contract price vs eventual outcome** | The market's price error (Brier) was **0.1197**; our best model's **0.1201** | 250 events / 89,806 minutes | **Predictive** — this *is* the headline test | Market prices already contain the prediction |
| **Deribit DVOL volatility index** | BTC 35.53, ETH 50.17 | Live snapshot, 1 Aug 2026 | Captured only | Never correlated with anything |

### The thing you specifically asked about: is there a tradeable lead?

**No lead-lag test was run in this entire project. Not one.** The 0.891 figure is
BTC and ETH moving **in the same hour** — it says nothing about whether one
moves *first*.

This is the exact distinction you were asking me to show you, so let me be
blunt about it:

- **A correlation of 0.891 measured in the same hour is the textbook case of
  "real relationship, not tradeable."** It tells you BTC and ETH go up and down
  together. It does *not* tell you that you can watch one and trade the other,
  because by the time you've observed BTC's hourly move, ETH's hourly move has
  already happened too.
- **Worse, the data we have could not answer the question even if we ran the
  test.** Our BTC/ETH series is sampled **once per hour**. Lead-lag between major
  crypto assets, where it exists at all, operates on timescales of
  **milliseconds to a few seconds** — it is arbitraged away long before an hour
  passes. Testing for a lead with hourly data is like trying to photograph a
  bullet with a sundial.
- The one dataset that *could* address it (`data.binance.vision`, which offers
  free 1-second data going back years) was confirmed reachable and **never
  pulled.**

**So: the honest status of "BTC leads ETH" is UNTESTED, not disproven.** It is
the single largest genuine gap in this work. Section 8 returns to it.

---

## 5. What the headline test does NOT cover

The vs-mid result closed one specific question: *can we forecast Kalshi's hourly
Bitcoin contracts better than Kalshi's own price, buying and selling at market?*
Everything below is outside that boundary.

| Not tested | Why | Status |
|---|---|---|
| **Market making** — quoting prices and collecting the spread rather than forecasting | **Ran out of time**, and Kalshi's recorded order books live on the desktop machine | 🟡 **Genuinely open.** This is a *different question*: a market maker doesn't need to forecast better, only to avoid being picked off. Our null does not speak to it. **But note the honest prior: we showed the mid is an excellent forecast, which means a maker earns spread minus adverse selection and nothing more.** |
| **Sub-minute horizons** (seconds, milliseconds) | **Untestable with what we pulled** — Kalshi candlesticks are 1-minute minimum | 🟡 **Open**, but would need a live recorder and probably co-location to exploit |
| **Other assets** — SOL, XRP, DOGE, ADA, BCH, BNB, HYPE, NEAR, TON, ZEC | **Ran out of time.** We pulled settled data for SOL/XRP/DOGE (389,125 rows) but never ran the headline test on them | 🟡 **Open.** Weaker assets are less efficiently priced in most markets — a reasonable place to look |
| **Most of Kalshi's 272 crypto series** — we tested 1 (KXBTCD) | **Ran out of time** | 🟡 **Open** |
| **Range/bucket markets** (as opposed to above/below) | Only tested for internal arbitrage (`A1`), not for forecastability | 🟡 **Open** |
| **The 15-minute series** | **Ran out of time.** We pulled the data (6,429 rows each for BTC/ETH/SOL/XRP) | 🟡 **Open**, though prior work found this series structurally hostile |
| **Non-crypto Kalshi markets** | Out of scope for this project | ⚪ Not attempted |
| **Polymarket** | **Effectively ruled out on cost** — we proved its taker fee is 2.86× Kalshi's | 🔴 **Ruled out for taking.** Its *maker* fee is unverified |
| **Other venues entirely** | Not attempted | ⚪ Open |
| **Entry and exit timing rules** — stop-losses, profit targets, hold-to-settlement | **Deliberately gated off.** See below | 🔴 **Correctly skipped, not an omission** |
| **Deribit-relative pricing** | **Ruled out — structurally impossible.** Deribit's shortest usable option expires in 54 hours; Kalshi's contracts last 1 hour | 🔴 **Closed** |
| **Lead-lag between assets** | **Never tested.** See §4 | 🟡 **Wide open** |
| **Volatility forecasting** (HAR, EWMA, seasonality) | **Ran out of time** | 🟡 Open |
| **Time-of-day effects** (Friday expiry, funding resets, CME hours) | **Ran out of time.** Pre-registered, never run | 🟡 Open |
| **Machine-learning models (M6)** | **Ran out of time** | 🟡 Open — but see the caveat below |

### Why the exit-rule sweep was deliberately skipped

This was a judgement call and you should know it was made on purpose. Exit rules
(stop-losses, profit targets) **do not create an edge — they reshape one.** If
your entry signal has zero expected value, no exit rule makes it positive; you
are just choosing the shape of your losses. Sweeping hundreds of exit
combinations over a zero-edge signal reliably produces something that looks
profitable in a backtest and dies live. **That has already happened at least
once in this project.** Running it was pre-registered as conditional on a model
beating the mid. No model did, so it was not run.

### An honest caveat on the untested models (M4–M6)

Three of the six planned models were never built. It would be overclaiming to
say "no model can beat the mid" — we tested four. But the pattern is
informative: the models got *worse*, not better, as they got more elaborate
(M3 and M3t both lost decisively). And the one improvement that did work
(M2's settlement correction) moved the needle by 0.000342 against a gap of
0.0019 needed to matter. A machine-learning model might do better; the evidence
so far points the other way.

---

## 6. Why you should believe the null

### What the synthetic control was

Before trusting any result, we built a **fake market** where we knew the right
answer, and ran the *exact same code* on it.

We generated 1,500 fake hours of Bitcoin prices from a known mathematical
formula, then created fake contract prices from that *same* formula. By
construction there is **no edge** — the "market" and the "model" are drawing
from the identical process. Then we ran three versions:

| Arm | What we planted | What the system should say | What it said |
|---|---|---|---|
| **A — Null** | Nothing. No edge exists. | "I find nothing" | ✅ Found nothing (p=0.59) |
| **B — Positive** | A deliberate 15% mispricing in the tails | "I found it" | ✅ Found it clearly |
| **B5 — Small positive** | A smaller 5% mispricing | "I found it" | ✅ Found it |
| **C — Leak** | Secretly fed the model the answer | "Something is badly wrong" | ✅ Caught it instantly |

**Why this matters:** a system that finds nothing is only meaningful if it
*would have* found something. Arm A proves it doesn't hallucinate. Arms B and B5
prove it isn't blind. Arm C proves it catches cheating. Without arms B and C, "we
found no edge" would be indistinguishable from "our code is broken."

### What "an order of magnitude smaller than the detectable floor" means

Precision matters here, and my earlier phrasing in `MORNING_REPORT.md` was
slightly too generous — let me correct it.

The synthetic control detected a **5% mispricing**, but that was under clean
laboratory conditions with **1,500** events. The real panel has **250** events
and far more messiness (varying volatility, different strikes, real spreads). In
the real panel, the smallest difference we could reliably distinguish from zero
was about **0.0019** in Brier units.

Translating: the 15%-mispricing arm produced a Brier difference of **0.002655**.
So the real-panel detection floor is roughly a **10–15% systematic mispricing**,
not 5%.

**The measured difference between our best model and the market was 0.000081.**

That is about **23 times smaller** than the smallest thing we could reliably
detect. The needle didn't move a little — it didn't move at all.

### How big would an edge have had to be for us to see it?

In practical terms: **the market's prices in the tails would have to be wrong by
about 10–15% of their distance from 50¢.**

Concretely: a contract that *should* trade at 10¢ would have to be trading at
roughly **16¢** — consistently, across 68 days — for this test to reliably catch
it. Errors smaller than that could be hiding in the data and we would not know.

**This is the honest limit of the result.** We can say with confidence there is
no *large* forecasting edge. We cannot rule out a small one — but a small one
also has to survive a 1.75¢ fee and a ~0.5¢ half-spread, which is roughly 2.3¢
of cost on a contract worth between 5¢ and 95¢.

---

## 7. The five withdrawn positives

Every one of these looked real at first. This is the most important section in
the document.

### 1. "464 risk-free arbitrages worth 96–97¢ each"

- **What it looked like:** buying every price bucket in an hour for 3¢ total,
  then collecting $1. Apparently free money, 464 times over.
- **What killed it:** our recorder only saves prices *when they change*. Dead
  contracts in the far wings never change, so they were never saved. We were
  adding up **3 of 80 buckets** and comparing to $1. Buying 3 buckets doesn't
  pay $1 — it pays $1 only if the answer lands in those 3.
- **What you'd have lost:** everything staked. It was never a trade; the
  positions didn't cover the outcomes.
- **Genuine phenomenon or measurement error?** **Pure measurement error.** There
  was never anything there.

### 2. "Bitcoin sticks to round numbers"

- **What it looked like:** 6 of 20 tests significant with p≈0.
- **What killed it:** three things. The effects ran the **wrong way** (Bitcoin
  *avoided* round numbers, the opposite of the hypothesis). The statistical test
  was invalid at exactly the levels where it "worked" — Bitcoin only spanned
  about 4 multiples of $5,000 in 68 days, far too few for the test's assumptions.
  And half the tests were **duplicates** of each other.
- **What you'd have lost:** unclear, since no trading rule was ever derived. The
  danger was building one.
- **Genuine or error?** **Measurement error.** The test was broken, not the market.

### 3. "Polymarket has the same fees as Kalshi"

- **What it looked like:** Polymarket's documentation, corroborated by two
  independent sources, matched Kalshi's fee formula exactly.
- **What killed it:** the actual blockchain records. 4,310 real fee payments
  match a completely different formula — **2.86× more expensive at 50¢**. I had
  seen Polymarket's own API contradict its documentation, flagged it, and then
  **reasoned around it instead of treating it as blocking.**
- **What you'd have lost:** on a 100-contract round trip at 50¢, you'd have
  budgeted $3.50 in fees and paid **$10.00**. Every strategy sized on the
  documented number would have been unprofitable by construction.
- **Genuine or error?** **Measurement error — mine.** The real fee was always
  there on-chain. I trusted a document over a machine.

### 4. "Fat tails are worth 1.5–1.9¢ per contract"

- **What it looked like:** Bitcoin's real tail moves happen 7× more often than a
  bell curve predicts, and the gap looked worth 1.5–1.9¢ after fees.
- **What killed it:** we measured the gap between reality and **a bell curve we
  invented ourselves**. Nobody ever showed Kalshi uses a bell curve. Later, the
  headline test proved it **doesn't** — feeding the model fatter tails made it
  measurably *worse* than the market.
- **What you'd have lost:** you'd have systematically bought tail contracts
  believing they were underpriced. They weren't. Losses would have been the fee
  and spread on every trade, roughly 1–2¢ per contract, indefinitely.
- **Genuine or error?** **The fat tails are 100% genuine** — that finding stands.
  **The edge was a measurement error:** we compared the market to a strawman
  instead of to the market.

### 5. "The market underprices by 4.2 percentage points"

- **What it looked like:** in the 5–65¢ range, contracts won more often than
  their price implied — by up to 4.2 points, against a ~1.3¢ cost. Apparently
  the largest and cleanest edge of the whole project.
- **What killed it:** **double-counting.** We had 89,806 price observations but
  only **250 independent events** — roughly 360 consecutive minutes of the same
  contract, which are nearly the same observation repeated. Counting them as
  independent made the result look ~10× more certain than it was. Corrected, 14
  of 17 buckets became indistinguishable from noise. The best survivor needed
  p ≤ 0.0059 and had p = 0.029. It also **halved between the first and second
  half** of the data, and **had the opposite sign** when we first looked at it
  with only 13 events.
- **What you'd have lost:** this is the dangerous one. It would have looked
  profitable in a backtest and you'd have traded it at real size. Expected
  outcome: roughly break-even minus costs, so a slow bleed of ~1–2¢ per
  contract, with the losses arriving as noise you'd rationalise as variance.
- **Genuine or error?** **Measurement error** — specifically, the single most
  common error in this entire project, made for the fifth time.

### The pattern

Each of the five failed a **different** way: partial data, an invalid test,
documentation over reality, an invented benchmark, and double-counting. There is
no one check that catches all five. That is the argument for running all of them
every time — and for the directional prior that any positive result in this
domain is presumptively overstated.

---

## 8. My honest read

### Is the conclusion "there is no edge in crypto prediction markets"?

**No. That would be overstating it.** The defensible conclusion is narrower:

> **On Kalshi's hourly Bitcoin above/below contracts, in the price range 5¢–95¢,
> within one hour of expiry, you cannot forecast the outcome better than the
> market's own price — and any remaining forecasting edge is smaller than roughly
> a 10–15% mispricing, which would not survive the ~2.3¢ round-trip cost anyway.**

That is a real, well-evidenced result with adequate statistical power, a
validated pipeline, and 68 days of data. It is not a small claim. But note what
it is bounded by: **one venue, one asset, one contract type, one time horizon,
and one *kind* of strategy** (forecasting, as a taker).

What is genuinely closed:
- Forecasting Kalshi's hourly BTC contracts as a taker. **Closed.**
- Deribit-relative pricing at these horizons. **Closed** — structurally impossible.
- Ladder arbitrage on Kalshi. **Closed** — fees exceed any gap by construction.
- Polymarket as a taker. **Closed on cost** — 2.86× Kalshi.

What remains genuinely open is in §5, and it is more than nothing.

### The single most likely place a real edge still exists

**Cross-asset lead-lag at sub-second timescales — specifically, whether BTC
moves lead the smaller crypto assets (SOL, XRP, DOGE) by enough to trade their
Kalshi contracts.**

Why this one:

1. **It was never tested.** Unlike everything else in this report, there is no
   evidence against it. Our only measurement (correlation 0.891) was
   contemporaneous and at hourly granularity — structurally incapable of
   detecting a lead.
2. **The mechanism is plausible and specific.** Bitcoin is the deepest,
   fastest-priced crypto asset. Smaller assets demonstrably follow it. Kalshi's
   SOL/XRP/DOGE contracts are far thinner than its BTC contracts — we saw
   0.005 flow-imbalance on liquid series versus much higher on thin ones. A
   market maker on a thin XRP contract may simply be slower to reprice on a BTC
   move than one on the BTC contract.
3. **It's a different *kind* of edge from everything we ruled out.** We tested
   whether we can forecast *better* than the market. This asks whether we can
   react *faster* on a market that is watching a different screen. Our null says
   nothing about it.
4. **The data to test it is free and confirmed reachable** —
   `data.binance.vision` offers 1-second klines going back years, and we already
   hold 389,125 rows of settled SOL/XRP/DOGE contracts.

**My honest estimate that it survives testing: 15–25%.**

I want to be clear that this is *not* a high number, and I am not recommending it
with enthusiasm. The reasons for pessimism are strong:

- Cross-asset lead-lag in crypto is **one of the most heavily mined signals in
  the entire industry.** Any lead that exists is measured in milliseconds and is
  contested by firms with co-located hardware. We would be arriving late to a
  crowded trade with a laptop.
- Even if a lead exists in *spot*, it must survive translation into a **Kalshi
  contract price**, then a **1¢ minimum tick**, then a **~1.3¢ fee**, then a
  **~1¢ spread**. That is a very high bar for a signal that decays in seconds.
- The thin contracts where the edge is most likely are also the ones with the
  least depth — you would be right and unable to size.
- And this project's base rate is unforgiving: **25 corrections, every one
  shrank the edge, none ever revealed a larger one.**

If I had to bet, I would bet it fails. But it is the only remaining hypothesis I
can name where the *mechanism* is plausible, the *data* is free, and the
*evidence against it is genuinely zero* rather than merely untested-by-accident.

**The second-most-likely candidate — and the cheaper one to check — is market
making on Kalshi**, because it asks a fundamentally different question (capture
spread vs. forecast better) and the recorder is already collecting the data. I'd
put that at similar odds but far lower cost to test, and it does not require
being fast. If you want one thing to do next, that is the one I'd pick on
expected-value-per-hour, even though lead-lag is the more interesting question.
