# GAPS.md — what was never tested

Read-only audit, 2026-07-30. Each item in the audit prompt is **confirmed** (never tested)
or **refuted** (it was tested — here is where). Additional gaps found during the sweep
follow.

---

## The six items the prompt named

### 1. Does the trading server owner's posted calls have any edge? — **CONFIRMED. Never measured, never attempted.**

The evidence exists and nothing has touched it.

- `OneDrive\Desktop\kalshi\RICH0FFTENN1S - TRADES - 🐳rot-trades [1519487140231123144].json`
  — 1.5 MB, **176 messages, 174 of them by the server owner, 2026-06-30 → 2026-07-29**,
  exported 2026-07-30 11:30 with `Downloads\DiscordChatExporter.win-x64`.
- A search for `discord`, `rich0ff` and `rot-trades` across every in-scope project returns
  **only outbound notification plumbing in P3** (`backend/app/services/notifications.py`).
  Nothing reads the export.
- None of the four sub-questions — persistence, shrinkage for sample size, edge decay after
  the call, adverse selection — has any artifact anywhere.

**This is the largest untested item in the corpus and the cheapest to close.** Every method
needed already exists and is validated: P3's `scripts/rank_tape.py` (one call = one
observation), `scripts/live_candidates.py` (luck bar over the *search-wide* pool),
`scripts/split_sample_test.py` (selection null), `scripts/follow_through.py` (edge decay
after the call at a realistic follower delay). 174 calls over 30 days is a *small* sample —
at P2's measured tennis P&L sd of 0.391 it takes 481 settlements to detect a 5pp edge — so
the honest expected outcome is "underpowered", and that itself is worth knowing before any
capital follows a call.

**One caution the corpus has already earned:** a single poster's 174 calls will contain
correlated bets (several calls on one match, several legs of one position). Fold to one
observation per match before computing anything, or this will reproduce failure mode 1.8
exactly.

### 2. Does any strategy work as a **maker** rather than a taker? — **PARTIALLY REFUTED. It was tested once, carefully, for one strategy — and the result exists only in a memory file and in code, with no preserved output.**

**Correction to the prompt's premise, and to this audit's first pass.**
`kalshi\backtest\high_sweep.py` implements a genuinely careful maker model, and its module
docstring (`:5-15`) states the trap directly: "modelling maker fills as *always get bid+1*
is the single easiest way to fake a profitable backtest, because in reality you fill exactly
when the price is coming toward you, which is disproportionately when it's about to keep
going." The implementation (`:82-104`) rests at bid+1, **starts scanning at `i0+1` so the
entry candle cannot fill the order by construction**, gives up after `patience` minutes with
**no trade** if the market runs away, and offers a `strict` mode requiring the *ask* to come
down — "the pessimistic bound, and it captures adverse selection."

The result is recorded in the project memory file
`.claude\projects\C--Users-vinig-kalshi\memory\kalshi-backtest-finding.md`:

> *Maker fills*: modelling "always fill at bid+1" showed **+0.24¢**. Requiring a real seller
> (ask comes down to us) → **33% of trades never fill**, win rate drops 1.8 points from
> adverse selection, result returns to **−1.57¢**. The apparent maker profit was entirely an
> artifact of the fill assumption.

**Status: `UNVERIFIED` — but with strong corroboration.** The code that would produce
exactly these numbers exists and matches the description in detail; the numbers themselves
have **no preserved output file** (`high_sweep.py`, `high_entry.py` and `longshot.py` all
write no results, and `BACKTEST_RESULTS.md` documents only S1–S5). Re-running
`high_sweep.py` against the candles already on disk would settle it in minutes. See
`LEDGER.md` C005/C106.

**What that leaves genuinely untested:**

- The maker test covers the **buy-high / longshot** family only. The **v3 momentum**
  strategy — the one the live bot runs — has never been simulated as a maker. Its 480-config
  sweep is taker throughout.
- **No maker test anywhere accounts for `fee_type`.** All of them assume the maker fee is ¼
  of taker. On this exchange it is usually **zero** (see below), which makes the maker case
  meaningfully better than any figure quoted above.
- No maker analysis exists for anything outside P1 — not `KXBTC15M`, not weather, not the
  arb scanner, none of which would clear their bars on a taker basis.

Every other cost-bar conclusion in the corpus assumes crossing the spread:

- P1 `backtest/engine.py:10-12` — "execution uses the REAL ask to buy and the REAL bid to
  sell, plus `extra_slip` cents"; "fees are taker on both sides". All 480 sweep
  configurations are taker.
- P2 `src/kalshi_research/fees.py:53` — `round_trip_taker_cents`; `breakeven_edge_cents`
  "assume exit also crosses". The entire 3.50¢/4.1–4.5¢ `KXBTC15M` bar is a taker bar.
- P2's arb scanner nets fees at the taker rate.
- P3/P4 model a *follower* who takes.

P1 `BACKTEST_RESULTS.md:238` reasons about it in one sentence — "Maker-only entries … at 25%
of taker fees recover ~1.2¢ of the 1.62¢ fee. That closes less than a third of the gap" —
without reference to the `high_sweep.py` maker simulation that already exists in the same
folder. No queue-position model exists anywhere.

**The prompt says the maker fee is a quarter of taker. On this exchange it is usually
zero.** P2's own Phase 0, `docs/contract_spec.md:51,66-68`, read `fee_type` on all 7,493
series: `quadratic` on **7,369** and `quadratic_with_maker_fees` on only **124**. Maker fees
are ¼ of taker *on those 124 series only*; **every other series charges makers nothing.**

So the untested question is not "does a quarter-fee help" but "does a **zero**-fee resting
entry help", and for P1's tennis strategy that would remove the entire 1.62¢ fee component,
not 1.2¢ of it. Against S2 buy-and-hold's arithmetic (+1.86¢ raw, −2.52¢ spread+slippage,
−1.62¢ fees, = −2.29¢ net) a maker entry that also avoids crossing the spread on entry is
the only configuration in the whole backtest that has not been ruled out.

**Which series carry `quadratic_with_maker_fees` is recorded nowhere** — the 124 are
counted but not listed, and whether the tennis families are among them is unknown. That is
a single API call. It is the cheapest unanswered question in the corpus and it gates the
one remaining live-bot hypothesis.

The honest counterweight is the one `high_sweep.py` already measured: a resting bid fills
preferentially when the signal is wrong. Requiring a real seller cost 33% of trades and 1.8
points of win rate, which erased the entire apparent maker gain. P1's live spec agrees from
the other direction — it cancels unfilled buys after 60 s because "a buy left resting … can
fill long after the score that justified it has changed" (`tennis_engine.py:86-89`). Any
maker study must model non-fills, not just cheaper fills. The open question is whether a
**zero** maker fee is enough to survive that 33% non-fill rate — which nobody has computed,
because every existing maker run assumed the fee was ¼ of taker rather than nil.

### 3. Does any model beat the Kalshi **mid** at adequate n? — **CONFIRMED. Never achieved, for anything.**

| Family | vs mid? | n | Verdict |
|---|---|---|---|
| `KXBTC15M` | **yes, measured** | **16–25 markets** per offset | 0 of 7 offsets beat the mid, 0 of 7 lose. A null at n=25 markets is low power, not a demonstration of no edge (`LEDGER.md` C027) |
| Weather (`KXTEMP*H`, `KXHIGH*`) | **no** | — | P2's headline table says *blocked*; the model was only ever scored against **climatology** (C056, C061) |
| Kalshi sports/tennis | **no** | — | Scored against realised outcomes and overround, never against a contemporaneous quote (C046, C049) |
| Kalshi flow following | n/a | 1,376 markets | Scored as a residual against price — the closest thing to a mid comparison in the corpus, and a well-powered null (C052) |
| Index ranges, economics, politics | **no model built** | — | Killed on structure or recurrence |

**The nearest thing to an answer came from a project P2 never saw.** P5
(`weather-market-bot`, 2026-07-23) scored a weather model against contemporaneous **market
asks** on a 600-contract validation sample: model Brier **0.204805** vs market-ask Brier
**0.168963** — the market won by a wide margin. A fitted consensus blend put **89% weight on
the market and 11% on weather**, improving the market's Brier by 0.000628 with an
event-clustered 95% CI of **[−0.000839, +0.002153]**, only 77.4% of resamples positive
(`LEDGER.md` C096, C097).

That is a different family (daily `KXHIGH*` via NDFD forecasts) and a different benchmark
(ask, not mid), so it does not formally settle P2's question — but it is direct evidence,
already on disk, that the answer is likely "no", obtained with correct event clustering, a
week before P2 declared the question blocked.

**And the recorders were not collecting the data needed to close it.** P2's stated only fix
for the #1 open question is "recording forward — capturing quotes on sports markets across
many events, which the recorders can now do." They cannot, as configured:
`scripts/record_kalshi.py:32-47` defines tier1 as nine crypto/index series plus five
weather families, and `data/watchlist_tier2.json` contains **19 families, all crypto,
index or weather, and zero sports**. Roughly 8.5 hours of book recording captured no
tennis, no baseball, no sports of any kind.

### 4. Is the tennis structural-event signal inverted — does fade-the-drop beat ride-the-rise? — **REFUTED. This was tested, on 14,162 markets.**

P1 `backtest/BACKTEST_RESULTS.md` §2 ran both as explicit strategies against the same tape:

| Strategy | Trades | Raw edge before costs | Net ¢/trade |
|---|---|---|---|
| S2 buy & hold (buy the up-step, hold to settlement) | 996 | **+1.86¢** | −2.29¢ |
| S3 **fade the drop** | 3,530 | **−1.41¢** | −9.67¢ |
| S4 **ride the rise** | 3,349 | **−2.11¢** | −10.40¢ |
| S5 random control | 2,885 | −0.65¢ | −8.28¢ |

**Answer: fade-the-drop is 0.73¢/trade less bad than ride-the-rise, but neither has a
positive raw edge, and both are worse than random entry.** The signal is not inverted. The
only positive raw edge in the whole family is buying the *upward* step and holding to
settlement — the un-inverted direction — and it is +1.86¢ against a 4.14¢ cost base.

What remains genuinely untested in this area is P1's own suggestion at
`BACKTEST_RESULTS.md:249`: **the spec's §6 serve-timing filter (enter at the start of a
service game)**, described as "a genuinely different hypothesis rather than a
re-parameterisation of this one". No artifact exists for it.

### 5. Set-score and multi-leg/parlay tennis markets, where correlated legs may be priced as independent — **CONFIRMED. Never tested.**

P2 `docs/shortlist.md:28-29` explicitly assigns this question away: "The one untested angle
— correlated multi-leg and set-score markets — is handled by the Phase 2 arb scanner, not by
a new model."

**The arb scanner never scanned them.** The audit read `reports/arb_log.parquet`: across
1,084 scans the only series that ever produced a row are `KXDJI`, `KXFED`, `KXINXU`,
`KXSOLD` and `KXTEMPAUSH`, and `family_kind` takes exactly one value — **`ladder`**. Not one
bucket-family row and not one sports row was ever logged. So the handoff went to a
component that was pointed at crypto, index, rates and weather ladders.

Nothing anywhere else touches it either:

- P2 `DECISIONS.md` D-004 **drops every combo before aggregating** (`mve_collection_ticker`
  non-null, 87.0% of open markets) in all flow and volume analysis. Combos are filtered out
  of the analysis, not analysed.
- A correlated-legs mispricing is not an arbitrage — it needs a joint model of set outcomes
  against the priced legs, which no project has.
- P5 ran the analogous test on weather baskets and found all 74 visible events exhaustive
  with no arbitrage after costs (`LEDGER.md` C038) — the method exists, it was simply never
  applied to tennis.

This remains the most concrete unexplored *structural* idea in the corpus, and it is the
one that does not need a forecasting edge.

### 6. Anything else proposed and never executed

| Proposed in | Item | Status |
|---|---|---|
| P2 `MORNING_REPORT.md` §11 action 3 | Re-run copy-trading persistence filtered to `behaviour = 'directional'` — 36% of positions hold both outcomes, so a third of the signal may be hedge legs. Explicitly "cuts both ways, which makes it a good test" | **Never run.** No artifact. P3's finding 8 independently showed the largest wallets hedge 72–86% of the time, which makes this test more urgent, not less |
| P2 `MORNING_REPORT.md` §7 caveat 3 / `GO_NO_GO.md` condition 3 | Measure the copy-trading edge at **posted quotes** rather than filled prices | **Never run.** Every copy-trading number in the corpus is measured on fills that happened, not on quotes a follower could have hit |
| P2 `PROGRESS.md` Phase 1 | **Rubric dimension 6 — counterparty fingerprint** (order-size distributions, quote-update frequency, cancel-to-trade ratio, hour-of-day activity). Left as `NaN` in `docs/market_screen.csv` rather than guessed | **Never run**, blocked on ~3 days of books spanning all 24 hours. Books stopped after ~8.5 h |
| P2 `PROGRESS.md` Phase 7 / Phase 8 | Strategy sweep and paper trader | **Deliberately not run** — correctly. Nothing cleared Phase 1 with a mechanism *and* fillable liquidity |
| P2 `MORNING_REPORT.md` §4 | Macro/tariff effects on BTC vol | **Never run.** No scheduled release fell in the recording window; needs ~30 days |
| P2 `MORNING_REPORT.md` §10 | Deribit implied-vol blend (846 instruments/snapshot captured) | **Never run.** ~2 days of chains needed; ~1.7 h collected |
| P2 `evaluate.py` | Feature-shift and label-shuffle leak tests are **implemented but never exercised** — "no fitted model reached the stage of needing them" | Latent capability, unused |
| P2 `evaluate.py` | `deflated_sharpe_ratio()` shipped, never called | Correctly unused — no strategy sweep to deflate |
| P3 `data/follow-list.json` | **The forward record.** 4 wallets frozen 2026-07-30 06:01 UTC, to be scored with `scripts/forward_record.py` against a pass mark of **+13.2p** (search-wide luck bar) | **Not yet scored.** This is the only ungameable test in the corpus and it is waiting on wall-clock time. **Blocked by defect C082** — `0x39f6236ccd16` is in the list with 33.7% of its follower outcomes contaminated, and the verdict is *pooled*, so one bad wallet in four corrupts it |
| P4 `HISTORICAL_BACKTEST_REPORT.md:129-141` | Pre-declared promotion rule: 100 resolved strategy-eligible paper trades, ≥30 outside the dominant wallet, ≥3 categories, 4–12 weeks minimum | **Never reached.** 9 paper positions exist, 0 resolved, $0 realised |
| P5 `docs/PHASES.md` Phase 8 | Forecast-revision latency — the surviving weather hypothesis | **Deferred to forward collection**, never run. Collector last wrote 2026-07-23 |
| P5 `docs/PHASES.md` Phase 9 | The final sealed 20% test split | **Correctly still sealed.** Do not open it |
| P1 `BACKTEST_RESULTS.md:249` | Serve-timing filter (enter at the start of a service game) | **Never run** — "untested and cheap to test next" |

---

## Additional gaps this audit found

**G-A. No forward-looking test of anything has ever been scored.** Four projects
independently concluded that only forward evidence can settle their central question — P3's
frozen list, P4's 100-trade promotion rule, P5's forward collector, P2's "only fix is
recording forward". **Not one of these has produced a single scored forward result.** Every
number in the corpus is retrospective. Meanwhile the live bot is the only thing that has
been generating genuine forward evidence, and its results were used to *tune parameters*
(`tennis_engine.py:32-39`, `:71-83`) rather than to score a frozen hypothesis.

**G-B. The live bot's actual configuration has never been backtested.** The 14,162-market
backtest evaluated the v3 defaults and 480 variants. The bot now runs
`min_entry_price=60 / max_favorite_price=75 / favorite_exit_drop=38 / favorite_target_price=95 /
max_spread=3 / max_concurrent=4`, every one of which was changed on 27–28 July on the basis
of 125–137 live observations. That configuration appears nowhere in the sweep. Running the
existing `backtest/high_sweep.py` machinery over the *current* parameter set is a few hours
of work against data already on disk.

**G-C. Nobody has reconciled the two tennis cost bars.** P2 uses 2.4¢ throughout
(`copytrade_tests_v2.py:42`); P1 measured 4.14¢. The difference is P1's 2¢ modelled
slippage. Conclusions phrased as "the CI excludes the 2.4¢ round trip" do not survive at
4.14¢ — the price-matched persistence result (+5.09pp, CI [+2.83, +7.35]) clears 2.4
comfortably and 4.14 only barely.

**G-D. The Polymarket→Kalshi price mapping was never validated.** The whole cross-venue
thesis assumes a Polymarket tennis market and its Kalshi twin are the same contract at
comparable prices. The only cited evidence is the Betfair correlation (C009), which has **no
artifact on this machine**. No script anywhere joins a Polymarket condition id to a Kalshi
ticker.

**G-E. Kalshi tennis has never been tested for favourite-longshot bias directly.** P2 tested
Kalshi *sports* aggregate (762 matches, 8 series including ATP/WTA/ITF) and pre-match
buckets at 19–52 matches — underpowered, and the bucket claim was later walked back
(`LEDGER.md` C049). Meanwhile P1's orphan `_calib.json` in `kalshi\` is a
(ticker, price, outcome, volume) table over ~28 July tennis markets that looks purpose-built
for exactly this test, with **no script and no written result** (C017). Somebody may have
already run this and lost the answer.

**G-F. Nine fee implementations, one shared library, zero reuse.** `kalshi markets` has a
correct, `Decimal`-based, unit-tested `fees.py` that no other project imports. See
`FAILURE_MODES.md` §4.

**G-G. Three of five projects have no version control at all** — including the one that
places real orders. No past live result can be attributed to a known code state.

**G-H. `PENDING (chat export)`.** These could not be assessed without the conversation
history: whether any claim in the ledger was contradicted in chat and never written down;
the origin of the Betfair correlation (C009) and the player-model Brier figures (C010); what
the 28 July `_*.json` pull was for (C017); and whether the "price anchor at or after
settlement" leak that P2 refers to as having "destroyed the tennis result" has any surviving
artifact — no such code exists on disk today.
