# FAILURE_MODES_CHATS.md — Recurring failure modes in the chat archive

Audit date: 2026-07-31
Companion to `LEDGER_CHATS.md`. Claim IDs (`CH###`) refer to that file.

This document covers the five failure modes that were named for investigation. Each section gives
**every instance found in the chat exports**, the signature that identifies it, and the guard that
would have caught it.

One pattern runs through all five: **every time the methodology was tightened, the apparent edge got
smaller.** That happened at least seven times across three weeks and never once in the other
direction. That asymmetry is itself the most informative measurement in the archive.

---

## 1. Pseudo-replication — many observations from one event treated as independent

The most frequent and most expensive error in the archive. It appears in **four** distinct places,
was caught twice by accident and twice by a deliberate check, and in one case was caught only
*because the user asked for it in advance*.

### Confirmed instances

| # | Where | What happened | Effect on the number |
|---|---|---|---|
| 1.1 | **Polymarket longshot analysis** (CH007) | **644 fills per match treated as independent observations.** | Produced a headline **−20.9pp** figure that is fiction. n was inflated by ~600×, so the CI was ~25× too tight. |
| 1.2 | **Polymarket "best wallet"** (CH006) | A wallet showing **+95pp** turned out to have placed **21 bets on a single match**. | One match's outcome, counted 21 times, became a "top performer". This is what seeded the entire copy-trading thread. |
| 1.3 | **Kalshi tennis candlesticks** (CH049) | Kalshi lists **two mirrored markets per match** (one per player). Backtesting both double-counts every match. **14,162 markets = 7,081 matches.** | Would have made every confidence interval **√2 tighter than reality** and doubled the apparent significance of every result in the v3 backtest. |
| 1.4 | **Live-bot backtests on price observations** (CH038, CH039) | Results reported as **n=25,250 observations** and **n=996 observations** — but these are 60-second price candles drawn from only **171 matches** (342 markets). | The stated n overstates the independent evidence by roughly **two orders of magnitude**. The *direction* of these findings survives; the implied precision does not. |

### Near-miss worth recording

The **+7.05pp Polymarket favourite-longshot control** (CH092, n=98,766) was flagged in the same
breath that it was reported: *"confirm the ±0.22 CI is clustered at market level and not bet level.
If it's bet-level, that number is fiction too."* **This was never confirmed.** It is the one
positive-looking result left standing in the copy-trading thread, and it is standing on an
unchecked assumption of exactly the kind that already produced 1.1 and 1.2.

### Signature

- A confidence interval that looks impossibly tight for the underlying event count.
- n in the tens of thousands from a dataset that covers days, not years.
- The unit in the results table is "observations", "fills", "candles", or "rows" — never "matches",
  "markets", or "events".
- A single name, market, or day appearing many times in the top of a ranked list.

### Guard

1. **Report n in events, not rows.** Every results table gets two columns: `n_obs` and
   `n_independent_events`. If the second one isn't there, the result isn't finished.
2. **Cluster bootstrap at the event level**, never the row level. Resample matches, then take all
   their rows — not rows directly.
3. **Deduplicate mirrored markets before anything else.** For Kalshi tennis: dedupe to one market
   per match. Confirm the mirror relationship on **mids**, not on `bid(A)` vs `100−ask(B)` — that
   comparison differs by the spread by construction and produced a false "they're not inverses"
   result (CH019).
4. **Cap any single event's contribution** when ranking wallets or markets, or require a minimum
   number of *distinct* events before an entity is eligible for a leaderboard.

---

## 2. Look-ahead leakage

### The primary instance — CH002

**What happened.** The Kalshi "pre-match" price was anchored to the market's `occurrence_datetime`
field. For many tennis markets that field is **at or after the match end** — it equals
`expected_expiration_time`. Taking the last candlestick at or before it therefore returns a
**post-settlement price**.

**What it produced.** Kalshi appeared to beat the Betfair Exchange closing line by **0.022 Brier** —
a result that should have been immediately suspect, because Betfair and the bookmaker average agree
with *each other* at correlation **0.9985**.

**How it was caught.** Not by the headline number, but by a join-quality diagnostic:
> *every Kalshi price of 0.995 has y=1, and every 0.005 has y=0. That's not sharpness, it's look-ahead leakage.*

**The measurement that characterised it** (`reports/anchor_leak_test.txt`, CH070):

| Anchor | Quotes outside 2c–98c | Of those, % correct | Corr. with books | Kalshi − Betfair |
|---|---|---|---|---|
| −0h | 4.1% | **100.0%** | 0.824 | −0.0176 |
| −1h | 4.1% | 94.1% | 0.848 | −0.0082 |
| −2h | 1.0% | **100.0%** | 0.915 | −0.0092 |
| **−6h** | **0.1%** | — | **0.978** | **+0.0012** |
| −24h | 0.3% | — | 0.966 | +0.0009 |

The leak signature is unambiguous: a genuine pre-match market is rarely that confident, and when it
is, it is ~95% right, **not 100%**.

**Blast radius.** The leak contaminated the Stage 4 Kalshi benchmark and Stage 5 as well. It did
**not** touch the bookmaker benchmark (CH065), which contains no Kalshi data — which is why "the
model loses to Pinnacle/Betfair by +0.019 Brier" survived and remains the load-bearing negative result.

### Second instance — CH053

The backtest engine's forward walk **evaluated the entry candle's own high and low**, both of which
occurred before the simulated purchase. Caught during construction by an explicit look-ahead
assertion test, before any results were generated.

### Third instance, structural rather than temporal — CH055

The train/test split (oldest 60% / newest 40% of 2026-06-29 → 2026-07-27) **straddles the
grass-to-hardcourt transition**, landing the boundary at roughly July 16. Grass and hard courts have
materially different hold rates, hence different break frequencies, hence different structural-event
frequencies. The holdout therefore tests *surface transfer confounded with time*, not out-of-sample
performance. A config could fail for the wrong reason, or pass for one that won't hold in August.

### Signature

- Extreme quotes (outside 2c–98c) that are **100%** correct.
- A venue "beating" two other venues that agree with each other at r > 0.99.
- Any timestamp field used as a match-start proxy without empirical verification. **Kalshi publishes
  no match-start field.**
- A holdout boundary that coincides with a regime change in the underlying sport or asset.

### Guard

1. **Never trust a timestamp field's name.** Anchor sweeps (−0h, −1h, −2h, −6h, −24h) are cheap and
   decisive. Re-run the sweep any time the data source or market family changes.
2. **Make the extreme-quote test a standing assertion.** If >1% of quotes sit outside 2c–98c, or if
   the extreme bucket is >97% correct, fail the run loudly.
3. **Benchmark against two independent references** and check they agree with each other first. If
   your venue beats both by a wide margin, you are leaking, not sharp.
4. **Tag every match with surface/regime and report holdout results split by it.** Where surface is
   unavailable, tournament name is an acceptable proxy.
5. Keep the look-ahead assertion test in the engine's startup path, not in a test file someone
   remembers to run.

---

## 3. Silent data corruption

The dangerous class: no exception, no error log, plausible-looking output.

### 3.1 The score-staleness stamp — CH031

`score_from_item` set `fetched_at = time.time()` at the moment the score was read **from cache**,
not when it was fetched from the source. Consequence: `score_age_sec` always read ≈0, and the
`max_score_age_sec = 30` guard **never rejected anything, ever**.

This is the most consequential single bug in the archive. The guard existed specifically to prevent
adverse selection — buying a spike the market has already seen. Because it never fired:

> **Every trade in the project's live history was entered on score data of completely unknown age,
> by a bot that believed the data was fresh.**

It is the leading candidate mechanism for the central anomaly — paying an average of **69.5c** and
getting **40%** (CH024). And it means the 4-for-10 result is not a test of the entry logic; it is a
test of the entry logic running blind.

### 3.2 The orderbook parse bug — CH087

The exchange-wide recorder wrote **correct row counts with empty content** for **1 hour 45 minutes**,
and was discovered **by accident**. Any monitor watching row counts — the obvious thing to watch —
would have reported the recorder as healthy for the entire window.

The assessment at the time was correct and worth repeating: for a project whose only irreplaceable
asset is continuously accruing recorded data, this bug class is **existential**. Backtests can be
re-run; a lost recording window cannot be recovered.

### 3.3 The definition drift in copy trading — CH093

The field named `won` meant **market resolution**, not the wallet's own outcome. Only **31%** of
positions were held to settlement and **36%** were hedged. So a metric everyone read as "this
wallet's skill" was actually measuring "what a copy-and-hold follower would have got" — a different
quantity, on a population that mostly didn't do that.

No code was broken. The column name was simply wrong about what it contained, and it silently
reframed the entire copy-trading thesis.

### 3.4 The ITF series omission — CH004

Kalshi series were filtered by a hand-written regex on title and ticker
(`tennis|ATP|WTA|Open|…`). `"ITF Men's Match"` and ticker `KXITFMATCH` match none of those patterns,
while an authoritative `tags: Tennis` field existed and went unused. The audit silently excluded
**31,894 markets ≈ 76% of Kalshi's tennis book** — the exact tier the live bot was trading — and
reported 74.5% coverage for a universe that excluded most of the relevant markets.

It was caught only because **the user noticed the finding contradicted their own fill history.**

### Signature

- A guard, filter, or threshold that has never rejected anything.
- Health checks that count rows rather than inspect content.
- A regex or hand-written allowlist standing in for an authoritative field the API already provides.
- A boolean or outcome column whose definition nobody has read the code for.
- A finding that contradicts something the user knows first-hand.

### Guard

1. **Every guard needs a test that proves it fires.** Assert that a 45-second-old score is rejected
   *and* a 5-second-old one passes. Make it a startup check, not an optional test.
2. **Health checks must be content-level, not count-level.** Alert on schema drift, null rates, and
   value distributions — every 15 minutes, for anything recording continuously.
3. **Prefer authoritative fields over pattern matching.** If the API exposes `tags`, use `tags`. A
   regex over human-readable titles is a silent filter.
4. **Read the code behind any outcome column before building on it.** Especially anything named
   `won`, `result`, `success`, or `pnl`.
5. **Treat a contradiction with first-hand experience as a bug report, not a surprising finding.**
   The ITF omission was caught this way and nothing else would have caught it.

---

## 4. Floating-point fee-formula bugs

### The bug

```
0.07 * 100 * 0.5 * 0.5 * 100   ->   175.00000000000003
```

Kalshi's taker fee is `round_up(0.07 × C × P × (1−P))`, rounded up **to the next whole cent**. At
P = 0.50 the exact value is 1.75c. Floating-point representation returns a hair *above* 175 basis
units, so `ceil` promotes it to **1.76c → 2c**, adding a spurious cent to **every fee computation at
or near the peak of the curve**.

Because P(1−P) peaks at 0.50 and Kalshi's most-traded contracts cluster there — and because
**KXBTC15M markets are minted at-the-money by construction** (CH080) — the bug bites hardest exactly
where the volume is.

### Occurrences

| # | Session | Date | How caught |
|---|---|---|---|
| 4.1 | Tennis candlestick backtest engine | 2026-07-27 | An explicit unit test comparing the engine's fee against the spec's published reference points. |
| 4.2 | BTC / exchange-wide overnight session | 2026-07-30 (overnight) | Independently, in a separate codebase. |
| 4.3 | Tennis backtest session | 2026-07-30 | Independently again — noted at the time as *"the third occurrence."* |

Three separate codebases, three independent rediscoveries, zero shared implementation.

### The related ambiguity — CH034

The formula `0.07 × C × P × (1−P)` is **ambiguous about units** — dollars vs cents vs basis points —
and an agent correctly flagged this. The conclusion held (1.75c at 50c, ~3.5c round trip, measured
cost bar 4.1–4.5c once spread was included), but the notation did not. An ambiguous formula copied
by hand into three codebases is precisely how 4.1–4.3 happened.

### Unresolved and more expensive than the bug — CH034, CH035

The **maker-fee side has never been measured.** Sources conflict: one says maker is ~25% of taker,
another says roughly half, another says Kalshi applies the same formula with no structural maker
discount. The guidance given was correct — *"don't trust any of them — including me"* — and the test
was specified: pull every fill from the 125 settled markets, tag maker vs taker, and regress actual
fee against `0.07 × C × P × (1−P)`.

**That test was never run.** Given a **$57.52 fee bill against ~$47 of gross profit** (CH043), a
maker discount would be worth more than every strategy result in the archive combined. And **every
negative result in the project is a taker result** (CH035) — the cost bar that killed BTC, tennis,
and the exchange-wide scan has only ever been measured on one side of the book.

### Guard

1. **One shared, tested `fees.py`, imported everywhere.** This was the instruction issued on
   2026-07-30 and it is the whole fix. Stop reimplementing the formula.
2. **Compute in integer cents.** Do the multiplication in integer basis points and round once, at
   the end. No float ever touches a `ceil`.
3. **Unit-test against published reference points**, including exactly P = 0.50, and assert
   `fee(1, 0.50) == 2c` deliberately rather than discovering it.
4. **Fee rounds up on the order total, not per contract.** Nine 1-contract orders pay the ceiling
   nine times; one 9-contract order pays it once. Any bot legging into positions is donating.
5. **Measure your own fees empirically** rather than modelling them. The fills are already on disk.

---

## 5. Benchmark inflation — beating a weak reference reported as if it were beating the market

The most seductive mode, because the underlying measurement is usually *correct*. The error is in
what it is compared against.

### 5.1 The illiquid-market placeholder — CH003, CH067

**39.8%** of the held-out Kalshi tennis markets quoted wider than 10c, and a 1c/99c quote has a
"mid" of 50c. That 50c is **not a market opinion — it is the absence of one.** Including those
markets in the benchmark means any model better than a coin flip appears to beat "the market".

| Subset | n | Model Brier | Market Brier | Diff | Verdict |
|---|---|---|---|---|---|
| all joined | 502 | 0.21703 | 0.20989 | +0.00714 | *indistinguishable* |
| **spread ≤ 10c** | **302** | 0.22054 | **0.18343** | **+0.03711** | **market beats model** |
| spread ≤ 5c | 287 | 0.21926 | 0.18088 | +0.03838 | market beats model |
| spread ≤ 2c | 186 | 0.21383 | 0.17528 | +0.03855 | market beats model |

The illiquid tail moved the verdict from "we're competitive" to "we lose clearly" — and the liquid
subset is **also the only subset that could ever have been traded.**

### 5.2 Weather vs climatology — CH085

Weather forecasting scored **Brier 0.058–0.093 against climatology's 0.163–0.294** — the single
best-looking number produced anywhere in the exchange-wide scan. Climatology is a **weak benchmark**:
it is the long-run base rate with no knowledge of today's conditions. Beating it demonstrates that
the forecast reads a weather report.

This was flagged correctly and immediately: *"Beating climatology is not beating the mid. That's
still unmeasured."* The tradeable question — does the model beat the Kalshi price — has **n=31
settled markets with recorded books** (CH086) and remains undecided. Weather is currently the only
surviving candidate in the entire project, and its supporting number is a weak-benchmark number.

### 5.3 The `/tennis-live-predictor` skill's accuracy — CH014, CH075

The skill reported hit rates of **7/7**, then **7/8**, then — after the 76% Ma Yexin call went
visibly wrong — **"9/10 on the refresh calls if we count Ma's set 1 win."** That last recount adds a
*sub-outcome of a losing call* to preserve the headline. It is benchmark inflation and goalpost
movement in the same sentence.

But the deeper problem is what the accuracy was measured against at all:

> Six of eight picks were **the player who was already winning**. The two it declined to call were
> the close ones. Players up a set win about 80% of the time. So it isn't predicting — it's reading
> the scoreboard and reporting who's ahead.

And the conclusion that generalises to the whole project:

> **A model that is 100% accurate about what the market already knows is worth exactly zero at the
> point of trading. Accuracy and edge are different things.**

The skill's picks are *expensive favourites*. The user's actual winning trades — Yagan at 16c,
Chavez at 30c, Shibahara at 60c — were players the market had **underrated** (CH076). The tool with
the impressive accuracy pointed away from where the money was made.

### 5.4 Mid-price fills as a benchmark for executable P&L — CH001

The most expensive instance, because it produced a *positive* headline:

| Min edge | Fill | Bets | Mean P&L | 95% CI | ROI |
|---|---|---|---|---|---|
| 0.02 | **mid** | 465 | +0.0598 | [+0.019, +0.101] | **+14.4%** |
| 0.02 | ask/bid | 284 | −0.1174 | [−0.180, −0.055] | **−24.3%** |
| 0.05 | **mid** | 389 | +0.0757 | [+0.032, +0.120] | **+18.7%** |
| 0.05 | ask/bid | 229 | −0.1345 | [−0.204, −0.066] | **−28.3%** |
| 0.10 | **mid** | 294 | +0.0985 | [+0.046, +0.149] | **+24.6%** |
| 0.10 | ask/bid | 157 | −0.1490 | [−0.232, −0.063] | **−30.9%** |

The mid is not a price anyone can trade at. Buying YES lifts the **ask**; buying NO costs
**1 − bid**. Repricing at executable levels moved mean entry by **27–32 cents** and flipped a
+25% ROI into −31%, with every interval entirely below zero.

The rule that follows: **a result that only survives at mid-fill is not a result.**

### 5.5 Beating random entry — the benchmark that was missing, then wasn't

The archive contains a good version of this too. When the random-entry control was finally run, it
returned **−6.96c per trade**, almost exactly pure round-trip friction — which validated the cost
model. And against it, the deployed live rule measured **−6.69c** versus **−2.58c** for
buy-at-ask-and-hold (CH038, CH039): the entry filter was **2.6× worse than entering at random**.

That is the correct use of a benchmark, and it took three weeks to run.

### Signature

- The benchmark is a base rate, a coin flip, climatology, an unfilled quote, or a price nobody can trade at.
- The comparison excludes costs while the strategy includes them (or vice versa).
- A result that improves when you *add* untradeable data to the sample.
- Accuracy or win rate reported without the price paid.
- A record that gets re-scored after a call goes wrong.

### Guard

1. **The benchmark is always the executable market price at the moment of the decision.** Not the
   mid, not climatology, not a coin flip.
2. **Fill at ask/bid, never mid.** Report the spread distribution *before* the P&L, and exclude
   wide-quote markets from **both** the P&L and the market benchmark.
3. **Report win rate next to the price paid**, always. "49-7" is meaningless without the odds
   (CH099); so is "7/7".
4. **Pre-register the scoring rule before the calls are made**, so a record cannot be recounted
   after a miss.
5. **Always run a random-entry control**, and expect it to land near round-trip friction. If it
   doesn't, the cost model is wrong. Anything that can't clearly beat it is noise.
6. **State what the benchmark does not know.** "Beats climatology" means "reads a weather report".
   "Beats a coin flip" means "reads the scoreboard".

---

## Cross-cutting note: the retraction pattern

Twenty claims in `LEDGER_CHATS.md` are **RETRACTED**. Sorting them by how they were caught:

| Caught by | Count | Examples |
|---|---|---|
| A deliberate validation the project designed for itself | 7 | split-half killing the `serving` signal (CH020), the anchor sweep (CH002), the liquidity filter (CH003), BH correction (CH068) |
| A control run alongside the treatment | 3 | naive favourite-buying vs wallet selection (CH005), random entry (CH039) |
| Accident, or the user's own first-hand knowledge | 4 | the ITF omission (CH004), the orderbook parse bug (CH087), the reaction-count check (CH016) |
| An agent checking its own prior statement | 6 | the 404s (CH009), the fee multiplier (CH010), the arb scanner (CH011), the mirror comparison (CH019), the price-match rule (CH018), the Webb arithmetic (CH015) |

**Every retraction moved in the same direction: the edge got smaller or vanished.** Not one
correction in three weeks revealed a larger edge than first believed.

The one that should worry you most is **CH013**, because it did not come from any of these
mechanisms. A verbal recap ("no threshold was positive") replaced the actual finding ("not enough
data to evaluate thresholds") and was written into a verdict table that closed a project. It was
caught only because the user happened to remember it differently and said so. The user's own note
in memory is the right frame:

> *their verbal recaps of past sessions are approximate and may misstate what was found.*

That is the failure mode this ledger exists to fix: **a claim's status degrades every time it is
re-told without its artifact.** Roughly a third of the rows in `LEDGER_CHATS.md` reach the archive
only as text pasted back from Claude Code sessions that the exports do not contain (CH125). Those
rows are one retelling away from CH013.
