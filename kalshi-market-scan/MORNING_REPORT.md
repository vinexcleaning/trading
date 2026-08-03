# MORNING REPORT — Kalshi exchange-wide edge scan

Session: 2026-07-30, 07:00–17:30 UTC — spanning the daily trading halt, the 09:00:42
reopen, and ~8.5 hours of live recording. Recorders still running.
Repo: 20 commits, 64 passing tests, 6.4M rows recorded (1.8M trades, 4.4M book).

---

## ⚠️ Read this first — five premises in the brief turned out to be wrong

These are corrected in place throughout, but they change what is worth doing next, so
they lead.

**1. There is no halved fee multiplier for S&P 500 / Nasdaq-100.** The live API reports
`fee_multiplier: 1` for `KXINX`, `KXNASDAQ100` and all 48 `KXINX*`/`KXNASDAQ100*`
variants. A 2022 Kalshi blog post did announce a halving; either it lapsed or it is not
expressed through this field, and `kalshi.com/fee-schedule` returned HTTP 429 on every
attempt so the authoritative document was never read. **This removes the entire stated
reason to prefer index range markets** (brief §1b item 4). Conservative decision: assume
0.07 everywhere (`DECISIONS.md` D-002).

**2. The fee formula in the brief is off by 100×.** `ceil(0.07 × C × P × (1−P))` evaluates
in *dollars*, not cents. Correct: `fee_cents = ceil(7 × C × P × (1−P))`. The anchor is
100 contracts at 50¢ → $1.75. Your 3.5¢ round-trip figure is right; the formula as
written would have produced fees 100× too small.

**3. `KXBTC15M` is not a strike ladder — it is an at-the-money coin flip, and that is
the whole problem.** Each market's `floor_strike` equals the *previous* window's
`expiration_value`. Confirmed on **99.86% of 6,261 consecutive markets**. So the contract
is "will BTC be ≥ where it was 15 minutes ago", minted exactly at-the-money every 15
minutes. Because the fee is quadratic in price, entry is permanently pinned to P ≈ 0.50
where the fee is **maximised**: a 3.50¢ round trip, and the cheap tails (1.26¢) are
structurally unreachable at entry. Phase 5 is therefore not "find a directional edge"
but "find a directional edge worth more than 3.5 percentage points on a driftless
asset." Nothing found comes close.

**4. Weather markets are not in the "Climate and Weather" category, and `/series` does
not list them at all.** That category holds 6 series (EV market share, eclipse cloud
cover). The real temperature families are `KXTEMP{CITY}H` (hourly, 1 °F nested
thresholds) and `KXHIGH*`/`KXHIGHT*` (daily, ~15 cities) — and `/series/KXTEMPDCH` does
not even resolve, while `/markets?series_ticker=KXTEMPDCH` returns markets. **Any screen
driven off the category listing silently misses the highest-prior family on the
exchange.** All universe work now enumerates markets and derives series from ticker
prefixes (`DECISIONS.md` D-006).

**5. Combo legs dominate market *count*, not trade count — the "garbage flow signal" risk
is ~33× smaller than stated.** The brief warns that auto-generated combo legs dominate raw
volume and must be filtered or every flow signal is garbage. Combos are indeed **87.0% of
open markets** (479,585 of 551,366), but across **1,771,977 recorded trades** they are only
**2.6%** (46,830). Filtering is still correct and is implemented as an exact non-null check
on `mve_collection_ticker` rather than a heuristic — but combos are simply not the
contamination problem the brief expects. (Successive estimates as the tape grew: 9.5% of
200 trades during the halt, 3.6% of 17k early in the session, 2.6% of 1.77M — the final
figure is definitive.)

A sixth, operational: **Kalshi halts trading daily.** `trading_active: false` from
07:00–09:00 UTC on Thursday. This explains an empty exchange-wide trade feed, absent
active `KXBTC15M` markets, and stale `updated_time` fields — all of which look like bugs
or dead markets. It is now recorded every 30 s so gaps are attributable rather than
mysterious.

---

## 1. The verdict in three sentences

**No tradeable edge was found anywhere on Kalshi, and after a full day of live recording
three of those nulls are measured rather than inferred: `KXBTC15M` ties the mid at all
seven horizons on recorded books, the arb scanner found 52 genuine violations across 1,083
scans with zero of tradeable size, and flow following adds nothing over price across 1,376
settled markets.** The one real, cost-bar-clearing edge found anywhere was in the
**Polymarket** tennis tape — but it is **favourite-longshot bias rather than wallet skill**,
and on Kalshi the same test found no such bias in its point estimates, so **the
Polymarket→Kalshi transfer your live strategy depends on has no positive evidence behind
it** (though in fairness the bucket-level sample is too thin to formally exclude a bias,
and mining more history cannot fix that — only forward recording can). The one candidate
still standing is weather, which narrowed sharply once I counted independent settlements
rather than markets: of eleven temperature families **exactly one, `KXTEMPDCH`, has both
enough settlements to validate an edge and enough depth to trade one**, and whether it
beats the mid is still unmeasured.

## 2. The headline table

One row per family. "Our Brier vs mid Brier" is the decisive comparison the brief asks
for; where it says *blocked*, the reason is that Kalshi exposes **no historical order
book**, so mid-quotes during a market's life must be recorded going forward and cannot be
back-filled.

| Family | n | Our Brier | Kalshi mid Brier | Fee-inclusive edge (CI) | Survives FDR | Verdict |
|---|---|---|---|---|---|---|
| `KXBTC15M` direction | **25 markets, recorded books** | 0.0020 @60s · 0.2309 @720s | **0.0075 @60s · 0.2337 @720s** | **0/7 offsets beat the mid, all CIs span 0** | n/a | **NO EDGE — measured, not inferred** |
| Weather ladders (`KXTEMP*H`) | **812 independent settlements** (not 8,090 markets) | **0.076–0.136** | **blocked** — climatology 0.216–0.315 | — | **yes**, clustered, all 4 cities | **Model real. Only `KXTEMPDCH` viable (1 of 11 families). vs-mid unmeasured** |
| No-arb violations (26 families) | **1,083 scans, ~9 h** | n/a — needs no model | n/a | 52 violations, **0 with tradeable size** | n/a | **NO EDGE — violations real, size is dust** |
| Index ranges (`KXINX*`, `KXNASDAQ100*`) | — | not built | — | — | — | **Downgraded** — fee premise false |
| Economics (`KXCPI`, `KXFED`, `KXGDP`) | **22–48 settlements** | not built | — | — | — | **Killed on recurrence** (need 481) |
| Politics (2,070 series) | — | — | — | — | — | **Killed** — no ground truth, no structure |
| Copy trading (Polymarket tennis) | 264,074 positions | n/a | n/a | **+7.23pp, CI [+4.61, +9.73]** vs 2.4¢ bar | **yes** | **Real — but not skill, and does not transfer to Kalshi.** §7, §7f |
| Flow following (Kalshi) | **1,376 settled markets** | n/a | n/a | corr(flow, outcome−price) = **−0.052, p=0.053** | no | **NO SIGNAL — price absorbs the flow** |
| Sports pricing (Kalshi, 12 series) | **2,258 markets, 490k fills** | n/a | aggregate calibrated (p=0.96) | aggregate **−0.67pp** vs 2.72% overround | no | **Efficient in aggregate. Bucket-level bias NOT excludable — see §7f** |

**On the one remaining "blocked" cell.** Scoring against Kalshi's mid needs the mid *at
the decision instant*, and Kalshi has no historical order-book endpoint — so it must be
recorded forward. For `KXBTC15M` that is now **done**: 25 markets settled with recorded
books, and the answer is a clean null (§7g). Weather is still blocked only because its
markets settle hourly or daily rather than every 15 minutes, so a comparable sample needs
days rather than hours. The recorders are collecting it.

Throughout, the post-settlement `last_price_dollars` (0.001 or 0.999) was **never** used
as a price anchor — that is precisely the look-ahead leak that destroyed the tennis
result.

## 3. Hypotheses tested

**116 total** (`docs/HYPOTHESIS_LEDGER.md`), BH-FDR corrected across the whole ledger.

- 18 negative-control hypotheses: **0 survived** (required — a survivor would void the night)
- 6 positive-control hypotheses: 3 survived (required — proves the pipeline can see a real 6¢ mispricing)
- 35 BTC fair-value hypotheses: 25 beat a coinflip, **0 established edge over the market**
- 5 seasonal-sigma hypotheses: **0 survived**
- 4+1 BTC direction hypotheses: 3 statistically significant, **0 above the cost bar**
- 2 copy-trading persistence, 1 skill (2,579 wallets internally), 4 price-band strategies: all positive
- 16 weather hypotheses (4 cities × 4 models): 10 beat climatology, **0 established edge vs market**
- 7 `KXBTC15M` vs-mid hypotheses (market-clustered): **0 beat the mid, 0 lost to it**
- 7 Kalshi flow-following hypotheses: **0 survived**
- 30 Kalshi sports-calibration hypotheses: **0 significant** (but underpowered per bucket)

**Across 116 hypotheses, the number that produced a tradeable edge on Kalshi is zero.**

No Phase 7 strategy sweep was run, so no deflated Sharpe is reported — there was no
candidate that cleared Phase 1 with a mechanism *and* demonstrated fillable liquidity.
Computing a deflated Sharpe on a null result would be theatre.

## 4. What you got wrong — bluntly

| Your hypothesis | Verdict | Evidence |
|---|---|---|
| **ETH leads BTC** | **Refuted** | Contemporaneous correlation 0.845; best positive lead (1 min) only 0.037. There is no lead to trade. |
| **Perps tie into the 15-minute market** | **Not supported, and the framing is now moot** | Funding/basis/OI are being recorded as vol inputs, but since no direction effect clears 3.5pp there is nothing for a regime input to improve. Also: Binance (451) and Bybit (403) are geo-blocked from your host — OKX and Deribit substituted. |
| **Time-of-day regimes** | **Confirmed as a vol fact, useless as a direction edge** | Vol peaks 14:00 UTC at 1.58× and troughs 10:00 at 0.75× — a clean 2.10× swing tracking the US equity open. Real and well-powered. But it forecasts *magnitude*, and this contract pays on *direction*. |
| **Profit-take / stop-loss optimisation** | **Not tested, and deliberately so** | Sweeping exit rules on a family with no established entry edge is exactly the 6,000-experiment trap the brief warns about. Would have manufactured false confidence. |
| **Macro/tariffs move BTC vol** | **Not tested** | Recording started at 07:30 UTC with no scheduled release in the window. Blocked on calendar coverage, not on method. |
| **Copy trading works** | **Right conclusion, wrong reason** | It works (+7.23pp persistent, CI excludes the cost bar) but not because you picked skilled traders. See §7. |
| **Weather is the highest-prior candidate** | **Structurally vindicated, economically unproven** | Best structure on the exchange by a wide margin. Volume is the open question: settled DC hourly thresholds showed volumes of 0, 1, 202, 0, 100. |
| **Internal no-arbitrage is the highest-quality category** | **Agreed, and still the best thing to build** | Needs no model, no history, no forecast. Zero violations so far, but every scan was during the trading halt. |

## 5. Kill list

Full detail with reasons in `docs/shortlist.md`. **1,112 of 3,133 series killed on
structure alone:**

| n | Reason |
|---|---|
| 599 | Median spread >8¢ — exceeds any plausible edge |
| 569 | No liquidity: zero median volume or quotes mostly absent |
| 235 | No independent ground truth **and** no structural check (pure opinion) |
| 92 | No two-sided quotes at all |
| 3 | Fewer than 50 settlements available |
| 2 | Combo/multivariate only |

The kill that will annoy you most: **the entire economics block dies on sample size, not
on merit.** `KXCPI` 23 settlements, `KXFED` 22, `KXCPIYOY` 48, against a measured
requirement of 481 settlements to detect a 5pp edge at 80% power. Your proposed mechanism
(public professional forecasts, retail ignoring them) may be entirely correct and is
simply untestable. `KXJOBS`/`KXCLAIMS` — the one family with plausible recurrence — had
no open markets at all.

## 6. Arb scanner results

**Now a real sample: 1,083 scans across ~9 hours, most of it live trading.**

- 26 structural families monitored at 30 s intervals
- **52 net-positive violations found** — so the detector does fire
- **0 of them had tradeable size**

| Series | Violations | Median net edge | **Median size available** | Median persistence |
|---|---|---|---|---|
| `KXSOLD` | 51 | 0.59¢ | **0.01 contracts** | 960 s |
| `KXTEMPAUSH` | 1 | 0.32¢ | 1.00 contract | 0 s |

| Filter | Count |
|---|---|
| net-positive after fees | 52 |
| …and size ≥ 10 contracts | **0** |
| …and size ≥ 10 **and** persisted ≥ 30 s | **0** |

The `KXSOLD` monotone-ladder violation is genuinely persistent — it survived **29+
minutes**, which rules out a data artifact — and it is worth 0.59¢ on **one hundredth of
a contract**. That is 0.006¢ of profit. Market makers leave sub-contract crumbs on the
book and nothing else.

**Verdict for the whole no-arbitrage category: real violations exist, none are tradeable.**
This was the highest-prior candidate in the brief because it needs no model. It needed no
model and it found no money. That is a clean negative result rather than an absence of
evidence — 1,083 scans is a genuine sample.

The scanner's actual contribution tonight was a correctness lesson worth more than the
null result. Naively summing each family produced a **phantom 1,298¢ "arb"** on `KXDJI`
with size 1 — a 13-dollar edge on a 1-dollar contract. `KXDJI` is a **60-rung nested
`greater_or_equal` ladder**, not an exhaustive bucket set; summing it is meaningless.
`KXBTC` by contrast is `less` + 78 `between` + `greater`, which genuinely tiles the line.
Family type is now derived from live `strike_type` data, bucket families must pass an
explicit tiling check (contiguity, no gaps, exactly two tails) before the sum-to-100
constraint applies, and a regression test guards the case. **Anyone building this without
that check will find hundreds of arbitrages that do not exist.**

## 7. Your tennis copy trading — the answer, and you won't like it

I ran all four tests on your live source (`tape_scan.db`, 1.64M fills → **264,074
wallet×market positions**, 38,117 wallets, 1,872 markets, Jul 2025 – Jul 2026).

### First, a methodological correction that reversed my own conclusion

My initial run treated each fill as an independent observation and reported *NOT
PERSISTENT* on test 1 and *SKILL PRESENT* on test 2 — two tests contradicting each other,
which is a reliable sign one of them is wrong. Both were. The top-ranked "skilled" wallet
had:

> **edge = +95.0 percentage points over 21 bets — all 21 on ONE market**, average price
> 0.05, and it won.

That is a single coin flip counted 21 times. Across the tape, 12.3% of wallets with ≥20
fills traded fewer than 5 distinct markets. Pseudo-replication of that kind understates
every standard error, which manufactured 1,684 "significant" wallets *and* simultaneously
diluted the persistence correlation with noise-dominated wallets. Corrected to **one
observation per (wallet, market)**, with fills collapsed to a size-weighted entry price.

### Test 1 — Persistence: **YES, it persists**

Rank on the first half (to 2026-06-09), evaluate on the strictly later half:

| | Period 1 | Period 2 |
|---|---|---|
| Top decile (42 wallets) | +16.17pp | **+7.23pp** |
| All qualifying wallets (425) | — | +1.37pp |

- Spearman rho = **0.351** (p = 8.9 × 10⁻¹⁴), Pearson r = 0.396
- Top decile vs the rest in period 2: **p = 0.0001**
- Bootstrap 95% CI on the top decile's period-2 edge: **[+4.61, +9.73] pp** — excludes
  both zero and the 2.4¢ round trip
- 34 of 42 stayed positive; 30 of 42 beat the cost bar
- 55% shrinkage from period 1 to period 2 — substantial regression to the mean, but the
  survivor is real

### Test 2 — Skill vs luck: real signal, but far less than it appears

- True skill variance τ² = 0.0027 → **only 40% of the observed spread in wallet edge is
  skill**; 60% is noise. Median shrinkage weight 0.44, so halve any raw edge you see.
- 516 of 2,579 wallets significant at raw p<0.05 against ~129 expected by chance;
  **274 survive BH-FDR**. So a real subpopulation exists.
- Best raw edge +72pp shrinks to +21.7pp — still implausibly high, so some contamination
  probably remains.
- **The number that matters: you need 481 settlements to detect a 5pp edge, and 2,084 to
  establish that it clears the 2.4¢ cost bar. Only 20 of 2,579 wallets have ≥481
  markets.** For virtually every *individual* wallet, you cannot establish skill. The
  top-decile *portfolio* result is far stronger than any single wallet's.

### Test 3 — Edge decay and capacity: mild, and not the binding constraint

From the project's own `trade_copyability` table (n = 5,013 per delay):

| Delay | Median deterioration | Moved against you |
|---|---|---|
| 0 s | 0.69¢ | 78.5% |
| 10 s | 0.81¢ | 78.8% |
| 30 s | 0.97¢ | 80.8% |
| 300 s | 0.85¢ | 69.3% |

Price moves against a follower ~78% of the time, but only by ~0.7–1.0¢ against a 0.1¢
spread. Costly, not fatal — a +7pp edge survives a 1¢ haircut comfortably.

### Test 4 — Adverse selection: none detected

Edge by trade-size quintile is flat (+0.16pp smallest, +0.17pp largest). No evidence that
large followed trades are systematically worse.

### The finding that reframes everything

The tape has an enormous **favourite-longshot bias**:

| Entry price | n | Win rate | Edge |
|---|---|---|---|
| 0.10–0.20 | 17,435 | 0.090 | **−6.39pp** |
| 0.20–0.30 | 20,911 | 0.175 | **−8.03pp** |
| 0.40–0.50 | 37,206 | 0.432 | −2.34pp |
| 0.50–0.60 | 35,861 | 0.601 | **+5.09pp** |
| 0.60–0.70 | 28,482 | 0.737 | **+8.57pp** |
| 0.70–0.80 | 24,655 | 0.848 | **+9.63pp** |
| 0.90–1.00 | 33,646 | 0.966 | +2.16pp |

So I re-ran persistence against a **price-matched benchmark** (each position scored
against the population win rate of its own price ventile), which strips out
favourite-longshot exposure and leaves only genuine wallet skill:

| Ranking on | Persistence rho | Top decile P1 → P2 | 95% CI on P2 |
|---|---|---|---|
| Raw edge | 0.351 | +16.17 → **+7.23pp** | [+4.61, +9.73] |
| **Price-matched excess** | 0.189 | +13.20 → **+5.09pp** | [+2.83, +7.35] |

Wallet skill does survive price-matching — but barely clears 2.4¢. And then:

> **Buying everything priced 0.60–0.95, with no wallet selection whatsoever, earns
> +7.05pp ± 0.22 on n = 98,766.**

That is the same edge as copying the top decile of wallets (+7.23pp), with a confidence
interval **twenty times tighter**, no wallet-selection risk, no ranking to maintain, and
no reflexivity problem. **The edge you are capturing is the price band, not the trader.**

### I then verified the load-bearing assumption. It is false — but not fatally

I flagged "does `won` mean the wallet's realised outcome?" as the #1 next action, then
ran it against `reconstructed_positions` in `best.db` (98,548 positions with full exit
and P&L accounting). **`won` is market resolution, not the wallet's outcome:**

| Check | Result |
|---|---|
| Positions held to resolution | **31.0%** — so for **69%**, `won` ≠ what the wallet realised |
| Positions that held **both** outcomes (hedged) | **36.0%** — per-leg `won` is meaningless as P&L |
| Purely directional | 71.6% |
| Positions with a partial exit | 48.8% |

**Why this does not collapse the result, and what it does change.** The tape metric
`won − entry` is not the whale's P&L. But it *is* exactly the return to a
**copy-and-hold-to-resolution** strategy: buy what they bought, at their price, hold to
settlement. That is the simplest implementable copy strategy, so the +7.23pp number
remains the right estimate **for that strategy** — it just cannot be described as
measuring the whale's skill. Reframing, not refutation.

**A separate survivorship trap, checked and largely cleared for tennis.** 60,543 of
98,548 positions are still `open`, with a **median age of 40.8 days** and 26.2% over 90
days — but tennis resolves in hours, so those are abandoned worthless positions never
redeemed (no reason to pay gas to redeem a zero), not live ones. Excluding them would
bias returns upward. Bounding it:

| | Closed-only | Open all break even | Open all total losses |
|---|---|---|---|
| All markets | +25.08% | +21.04% | **+4.96%** |
| **Tennis only** | **+17.18%** | +17.16% | **+17.00%** |

Tennis is nearly immune: only **0.2%** of tennis capital sits in open positions, so the
bound is tight at **[+17.00%, +17.16%]** capital-weighted. The survivorship problem is
real for the non-tennis book and negligible for tennis.

### The caveats that remain

1. **`best.db`'s 159 wallets are curated — selected on past performance.** So its
   +17.18% tennis return is circular and is *not* an out-of-sample estimate. The only
   clean number is the persistence test, which used the unfiltered 38,117-wallet tape and
   gave +7.23pp out of sample. Do not quote the 17%.
2. **A 6–9pp favourite-longshot bias is implausibly large for a liquid market**, and your
   own work shows Kalshi tennis tracks Betfair at r = 0.9878 with 1.95¢ MAD — consistent
   with the bias being absent or already arbitraged **on Kalshi**. This result is
   Polymarket. This is now the #1 open question.
3. **These are filled prices, not posted quotes.** A strategy must trade against what was
   available, not what happened to trade.
4. **36% hedging means the signal itself is ambiguous** — a large buy may be one leg of a
   hedge, not a directional view. Filtering to `behaviour = 'directional'` before
   following flow is likely necessary.

## 7b. Weather — model built and it is sharp, but that is not the same as edge

I found a way to test this tonight without waiting for recorded books: **the settled
markets encode their own ground truth.** `expiration_value` on a settled
`KXTEMPDCH-…-T76.99` market *is* the observed temperature at that hour, so 500–512
hourly settlements per city reconstruct the temperature series with no external archive
needed. (NWS historical observation queries returned empty over these dates, so this was
the only route.)

Strict 60/40 time split, all parameters fit on train only, leak assertion in code that
every feature observation precedes the settlement:

| City | Climatology Brier | Persistence | **Persistence + hour-of-day** | Test markets |
|---|---|---|---|---|
| `KXTEMPLAXH` | 0.1628 | 0.0752 | **0.0579** | 2,022 |
| `KXTEMPDCH` | 0.2209 | 0.1012 | **0.0797** | 2,033 |
| `KXTEMPCHIH` | 0.2942 | 0.0979 | **0.0744** | 2,039 |
| `KXTEMPAUSH` | 0.2725 | 0.1351 | **0.0931** | 1,996 |

All four beat climatology with q = 0.000. The reason is simple and physical: the
persistence error is only **1.84–2.48 °F** against a climatological spread of
**6.95–7.00 °F**, so last hour's reading is overwhelmingly informative about this hour's.

**Now the honest part: this is not an edge.** Beating climatology is table stakes —
Kalshi's mid also knows last hour's temperature, and so does anyone who can read
`api.weather.gov`. A Brier of 0.058 proves the model is sound and the pipeline works
end-to-end on a real family; it says nothing about whether the market is mispriced.
That comparison needs mid-quotes during each market's life, which is blocked on recorded
books.

**A correction to my own earlier claim.** In the shortlist I called weather volume
"near-nothing" based on a five-market sample (0, 1, 202, 0, 100). Across the full settled
history that was an unrepresentatively quiet hour:

| Family | Median volume | p90 | Max | Markets with zero volume |
|---|---|---|---|---|
| `KXTEMPDCH` | 12 | 1,417 | 36,243 | 27.7% |
| `KXTEMPLAXH` | 147 | 2,897 | 44,333 | 23.2% |
| `KXTEMPCHIH` | 114 | 2,468 | 123,496 | 19.7% |
| `KXTEMPAUSH` | 24 | 1,872 | 52,445 | 25.7% |

The median market is thin and a quarter never trade at all, but the p90 is **1,400–2,900
contracts** — so liquid markets do exist within these families.

### 7c. Then the exchange reopened and the capacity question got answered

Trading resumed at **09:00:42 UTC** and the recorders captured live books. Depth at the
touch — size available at the best price, which is what actually determines fillability:

| Family | Median touch depth | Mean | Max | vs my pre-registered 50-contract bar |
|---|---|---|---|---|
| `KXHIGHLAX` | **2,434** | 3,057 | 7,733 | **passes, 49×** |
| `KXHIGHNY` | **1,114** | 1,178 | 3,321 | **passes, 22×** |
| `KXHIGHMIA` | **738** | 919 | 1,727 | **passes, 15×** |
| `KXHIGHDEN` | **509** | 686 | 1,904 | **passes, 10×** |
| `KXHIGHPHIL` | **490** | 561 | 2,123 | **passes, 10×** |
| `KXHIGHAUS` | **487** | 601 | 1,012 | **passes, 10×** |
| `KXHIGHCHI` | **371** | 487 | 978 | **passes, 7×** |
| *`KXBTC15M`, for scale* | *21,942* | *25,501* | — | — |

**The daily weather ladders are not capacity-limited.** Every one of seven independent
families clears the bar by 7–49×. This was the single question I said blocked the whole
weather thesis, and the answer is favourable.

**Then I measured the hourly ladders too, and they do not behave like the daily ones.**
I refreshed the watchlist during live trading to pick them up:

| Hourly family | Median touch depth | Verdict |
|---|---|---|
| `KXTEMPDCH` | **2,972** | tradeable |
| `KXTEMPLAXH` | **1** | untradeable |
| `KXTEMPCHIH` | **1** | untradeable |
| `KXTEMPAUSH` | **1** | untradeable |

**This is the most important qualification in the weather story.** The hourly families are
the ones with 5,200 settlements each — the high-recurrence, statistically-testable ones
where my model was sharpest. Three of the four are effectively empty at the touch: one
contract. Only Washington DC has real depth, and it has a lot of it.

So recurrence and liquidity **do not coincide** except for `KXTEMPDCH`. The daily `KXHIGH*`
families have depth but only ~396 settlements each; the hourly families have 5,200
settlements but only one of four is fillable. Any weather strategy is therefore either
`KXTEMPDCH` specifically, or the daily families with a much smaller sample to validate on.

**Caveats.** Depth samples are small — 11–17 snapshots per hourly family, ~12 per daily
family, all at one point in the session. Depth plausibly builds as a market approaches its
settlement hour, which would make these numbers pessimistic for the thin families. This
needs days of tape to settle, and the recorders are collecting it.

**What this does and does not change.** Weather now has: a working model (Brier
0.058–0.093), a real mechanism, high recurrence, and demonstrated depth. What it still
lacks is the only thing that constitutes edge — **evidence the model beats the mid**. That
comparison needs the books recording across full settlement cycles, which is now happening
but needs days. So weather moves from "blocked on two unknowns" to "blocked on the decisive
one", which is real progress.

## 8. BTC intraday vol seasonality, and what it implies

Charts: `notebooks/btc_vol_seasonality_minute_of_day.png`,
`notebooks/btc_vol_seasonality_intraweek.png`. 102,716 one-minute candles, 100% coverage,
2026-05-20 → 07-30.

- **Hour of day:** peak **14:00 UTC at 1.58×**, trough **10:00 UTC at 0.75×** — a
  **2.10× swing**, tracking the US equity open (14:00 UTC = 10:00 ET).
- **Day of week:** Thu 1.18× and Fri 1.17× vs Sat 0.70× and Sun 0.79× — **1.69× ratio**.
- **Within the quarter-hour — the :00/:15/:30/:45 question you asked:** vol decays
  **monotonically** from **1.17× at minute 0 to 0.87× at minute 14**, a 35% spread with
  n = 6,847 per bucket. Something systematic does happen at the boundaries where these
  markets open and close.
- Distribution: excess kurtosis **12.19**, fitted Student-t **dof ≈ 2.0** (at the
  variance-finiteness boundary), and the 0.1% tail is realised **7.2× more often than
  Gaussian**. A Gaussian model badly misprices the tails.
- **A jump occurs in 22.2% of 15-minute windows** (realized variance > 1.5× bipower).

**What it implies about when to trade:** if you ever do trade this contract, the vol
information says sell premium into the 14:00 UTC peak and avoid the 10:00 trough — but
that requires selling volatility, and this contract pays on direction. Combined with the
minute-within-window decay, a constant-sigma model systematically over-states remaining
vol late in the window.

**The falsifiable prediction that followed, and failed.** Those three facts imply a
trailing sigma over-states the vol remaining, making the model under-confident — which is
exactly what the calibration curve shows (at 5 minutes to expiry, the 0.7–0.8 bucket
realises 0.85). So I fit the intra-window seasonal on the first 60% and rescaled sigma on
the last 40%. **It did not improve the forecast: all five paired CIs include zero.** The
seasonality is real; correcting for it does not help. The calibration bias comes from
somewhere else.

**One prompt hypothesis confirmed cleanly.** The brief predicted that if settlement is a
60-second average, late-window contracts should price *further* from 50¢ than a
point-sample model implies. Settlement **is** a 60-second mean of the CF Benchmarks RTI
(confirmed verbatim from the live API, not a third-party summary), and the
settlement-aware correction improves Brier by **+7.51% at 60 s** to expiry, decaying to
+0.01% at 780 s. Exactly the predicted shape: it matters only when the averaging window
is comparable to the time remaining.

## 7i. Weather, finally resolved: **exactly one viable family out of eleven**

Recording weather books all day surfaced a structural point I had missed, and it cuts the
weather thesis down hard.

**A temperature ladder is not 10 independent markets — it is one temperature reading.**
All ~10 strikes in `KXTEMPDCH-26JUL3006-*` resolve off the same 78.00 °F observation. So
the unit of independent observation is the **(city, settlement hour)**, not the market:

| Family | Markets | **Independent settlements** | Strikes each |
|---|---|---|---|
| `KXTEMPDCH` | 5,186 | **512** | 10.1 |
| `KXTEMPLAXH` | 5,192 | **514** | 10.1 |
| `KXHIGHNY` | 396 | **66** | 6.0 |
| `KXHIGHLAX` | 396 | **66** | 6.0 |

**This is a correction to my own earlier weather result.** I reported the model on "8,090
test markets"; the effective n was ~800 settlement hours, so those CIs were roughly 3×
too tight. Re-scored with a bootstrap over whole settlement hours, the conclusion
survives comfortably:

| City | Settlements | Persistence Brier | Climatology Brier | Clustered diff CI |
|---|---|---|---|---|
| `KXTEMPDCH` | 204 | 0.1021 | 0.2357 | [+0.111, +0.156] |
| `KXTEMPLAXH` | 204 | 0.0761 | 0.2162 | [+0.120, +0.160] |
| `KXTEMPCHIH` | 204 | 0.0979 | 0.2543 | [+0.136, +0.176] |
| `KXTEMPAUSH` | 200 | 0.1355 | 0.3146 | [+0.149, +0.207] |

All four still beat climatology decisively. The model is real.

### But cross-tabbing recurrence against depth kills almost everything

Requiring **both** ≥481 independent settlements (the power bar) **and** ≥50 contracts at
the touch (the capacity bar):

| Family | Independent settlements | Median touch depth | Verdict |
|---|---|---|---|
| **`KXTEMPDCH`** | **512** | **2,972** | **VIABLE** |
| `KXTEMPLAXH` | 514 | 1 | no depth |
| `KXTEMPCHIH` | 512 | 1 | no depth |
| `KXTEMPAUSH` | 512 | 1 | no depth |
| `KXHIGHLAX` | 66 | 2,434 | too few settlements |
| `KXHIGHNY` | 66 | 1,114 | too few settlements |
| `KXHIGHMIA` | 66 | 738 | too few settlements |
| `KXHIGHDEN` | 66 | 509 | too few settlements |
| `KXHIGHPHIL` | 66 | 490 | too few settlements |
| `KXHIGHAUS` | 66 | 487 | too few settlements |
| `KXHIGHCHI` | 66 | 371 | too few settlements |

**One family out of eleven clears both bars: `KXTEMPDCH`, Washington DC hourly
temperature.** And it clears the recurrence bar by 512 vs 481 — margin of 6%, which is
thin.

This also retracts my earlier framing that "seven daily families clear the capacity bar
by 7–49×, so weather is not capacity-limited." They do clear it on depth — but with 66
independent settlements they cannot validate a 5-point edge at any power, so their depth
is irrelevant. I was celebrating the wrong axis.

**Net position on weather:** the model works, the mechanism is sound, and the tradeable
universe is a single city's hourly temperature ladder. That is a much smaller prize than
the structural screen implied, and whether even it beats the mid is still unmeasured.

## 7h. Flow following on Kalshi: **no signal**, on 1,376 settled markets

The brief's Kalshi copy-trading hypothesis was flow following — since the feed is
anonymous, large accumulating one-sided positions are the only available signal. With
1.77M recorded trades and 1,376 settled markets this is now properly testable.

**The test that matters is not "does the flow side win"** — of course it does, flow moves
price and price predicts outcome. It is whether flow adds information **over and above the
price it has already moved to**. So the residual `outcome − price_at_cutoff` is regressed
on flow imbalance, measured strictly ≥120 s before close.

| Flow imbalance | Markets | Mean price | Win rate | Residual |
|---|---|---|---|---|
| strong NO (< −0.5) | 65 | 0.501 | 0.508 | +0.69pp ± 5.20 |
| mild NO | 166 | 0.549 | 0.572 | +2.32pp ± 2.80 |
| balanced | 199 | 0.533 | 0.538 | +0.50pp ± 2.94 |
| mild YES | 414 | 0.517 | 0.531 | +1.45pp ± 1.57 |
| strong YES (> +0.5) | 532 | 0.516 | 0.508 | **−0.89pp ± 1.07** |

- **flow side won just 51.24%** overall — and only **50.59%** when imbalance exceeded 0.5,
  i.e. *stronger* flow was *not* more predictive
- **corr(flow imbalance, outcome − price) = −0.0522, p = 0.053** — indistinguishable from
  zero, and if anything negative
- **whale prints** (top-decile notional, n=138): corr −0.064, p = 0.454. Nothing.

**Verdict: flow following on Kalshi has no signal.** The price absorbs the flow before it
is observable in the public feed. Note the faint negative tilt — heavy one-sided flow
slightly *underperforms* its price — which is what adverse selection would look like, but
at p = 0.053 I am not claiming it.

This closes the last untested hypothesis in the brief.

## 7g. THE HEADLINE TEST IS ANSWERED — and I have to retract an earlier finding

Seven hours of recording later, **25 `KXBTC15M` markets have both recorded books and
final settlements**, so the comparison I had been calling blocked is now measurable.

### Our model vs Kalshi's mid, clustered by market

164 observations at 7 decision offsets, CI bootstrapped over **markets** (not snapshots,
which share a settlement):

| Offset | Markets | Our Brier | Mid Brier | Diff | 95% CI (clustered) | Verdict |
|---|---|---|---|---|---|---|
| 60 s | 16 | 0.00196 | 0.00746 | +0.00550 | [−0.0032, +0.0208] | no difference |
| 120 s | 24 | 0.03417 | 0.03369 | −0.00048 | [−0.0141, +0.0139] | no difference |
| 180 s | 25 | 0.08448 | 0.09058 | +0.00610 | [−0.0113, +0.0265] | no difference |
| 300 s | 25 | 0.12683 | 0.12423 | −0.00260 | [−0.0168, +0.0100] | no difference |
| 480 s | 25 | 0.20832 | 0.19426 | −0.01406 | [−0.0373, +0.0070] | no difference |
| 600 s | 25 | 0.23855 | 0.22374 | −0.01481 | [−0.0366, +0.0063] | no difference |
| 720 s | 24 | 0.23087 | 0.23372 | +0.00285 | [−0.0208, +0.0263] | no difference |

**0 of 7 offsets beat the mid. 0 of 7 lose to it.** Every CI includes zero.

**No evidence of edge in `KXBTC15M`.** The market's mid is at least as good as our model
at every horizon. This is the decisive comparison the brief asked for, and for the crypto
family the answer is a clean null.

*Pseudo-replication, a third time.* The unclustered version of this same comparison
reported "MID BEATS US" with a CI of [−0.0061, −0.0019] excluding zero. Clustering by
market widens that to [−0.0168, +0.0100] — roughly **5× wider**, and the significance
evaporates. Snapshot-level CIs on market-level outcomes are wrong every time.

### RETRACTION: the "liquidity vanishes as the model sharpens" finding was an artifact

Earlier I reported, as a headline, that depth at the touch collapses 40× toward expiry
(158 → 4 contracts) while the model sharpens, and called the edge and liquidity
"anti-correlated". **That was measured from one market over three minutes and it is
wrong.** With 25 markets over seven hours:

| Time to expiry | Median spread | Median touch depth | Total breakeven |
|---|---|---|---|
| 10–15 min | 1.0¢ | **821** | 4.46¢ |
| 5–10 min | 1.0¢ | **574** | 4.49¢ |
| 2–5 min | 0.3¢ | **373** | 3.58¢ |
| 60–120 s | 0.1¢ | **193** | 3.36¢ |
| 0–60 s | 0.1¢ | **307** | **3.50¢** |

The truth is close to the opposite of what I claimed:

- depth declines **2.7×**, not 40×, and never becomes thin — 307 contracts at the touch
  inside the final minute, not 4
- the **spread tightens 10×** toward expiry, from 1.0¢ to 0.1¢
- so the **total cost of trading falls** as expiry approaches, from 4.46¢ to 3.50¢

I over-read a three-minute sample and presented it with more confidence than one market
could support. The corrected picture removes that particular argument against
`KXBTC15M` — the contract is *cheaper* to trade late, not more expensive. The verdict is
unchanged, but it now rests on the evidence that actually holds: the at-the-money fee
structure, direction effects far below the bar, and the vs-mid null above.

## 7f. THE DECISIVE TEST: does the favourite-longshot bias exist on Kalshi? **No.**

This was the #1 open question and it is now answered. Method: pull settled sports markets
and their **full public trade history** — a Phase 0 capability I understated, since
historical *books* are unavailable but historical *trades per market* are retrievable —
then score every taker fill from the buyer's perspective and bucket by price paid.

**490,464 fills across 762 matches** in 8 series (ATP, WTA, ITF ×2, MLB, NBA, NHL, WNBA).

### The aggregate, which is the well-powered number

| | Paid | Won | Edge |
|---|---|---|---|
| YES takers (n=297,643) | 0.4704 | 0.4508 | **−1.96pp** |
| NO takers (n=192,821) | 0.4123 | 0.4254 | **+1.31pp** |
| **Overall** | | | **−0.67pp** (−0.29pp size-weighted) |

Overround **2.72%**. Takers lose roughly the overround — what an efficient market with a
spread looks like.

### Pre-match calibration by price bucket

Fills ≥120 min before the event ends, clustered by match, tested with a **binomial test**
(the correct test for binary outcomes):

| Bucket | Matches | Fair price | Observed | Binomial p |
|---|---|---|---|---|
| 0.1–0.2 | 40 | 0.158 | 0.125 | 0.827 |
| 0.2–0.3 | 32 | 0.243 | 0.219 | 0.840 |
| 0.3–0.4 | 25 | 0.363 | 0.280 | 0.533 |
| 0.4–0.5 | 21 | 0.450 | 0.476 | 0.830 |
| 0.5–0.6 | 19 | 0.553 | 0.474 | 0.499 |
| 0.6–0.7 | 28 | 0.664 | 0.643 | 0.842 |
| 0.7–0.8 | 46 | 0.755 | 0.761 | **1.000** |
| 0.8–0.9 | 52 | 0.846 | 0.846 | **1.000** |

**Not one bucket deviates.** 0.846 → 0.846 exactly; 0.755 → 0.761. Against Polymarket's
+8.57pp at 0.6–0.7 and +9.63pp at 0.7–0.8, Kalshi gives **−2.12pp and +0.57pp**.

### Two false positives caught in my own test

**v1 reported edges of −20.9pp to +19.5pp with ±1pp CIs.** Nonsense: 490,464 fills came
from 762 matches (644 each) and a match settles *once* — the same pseudo-replication error
as the Polymarket run. The sane aggregate (−0.67pp) should have been the tell.

**After clustering, two buckets still flagged significant** — (0.9,1.0] at +6.03pp ±1.02
and (0.0,0.1] at −7.32pp ±0.88. Both are **degenerate-variance artifacts**: all 14 and all
17 matches respectively had identical outcomes, so P&L variance collapsed to ~0 and the CI
with it. Under fair prices, P(all identical) = 0.42 and 0.28 — unremarkable. Proper
binomial p-values: **1.000 and 0.631**.

### What this means for the strategy — the most actionable finding of the session

The setup ranks **Polymarket** wallets and trades the twin **Kalshi** contract. But the
Phase 6 edge lives **in the Polymarket price**, not in the wallets' insight — and Kalshi
prices are calibrated. **The transfer fails at exactly the step it depends on.** Copying a
Polymarket wallet into a Kalshi contract cannot capture a favourite-longshot premium that
does not exist on Kalshi.

### The power fix I proposed — and why it failed

I said the pre-match sample was too small (19–52 matches per bucket) and that the fix was
targeting early trades directly. `max_ts` does work: one request returns the fills
immediately preceding any cutoff, replacing ~20 pages of pagination. So I re-ran it across
**12 series and 2,258 settled markets at three horizons**.

**It did not deliver the power I predicted.** 487,003 fills collapsed to only **726
market-horizon observations across 663 markets**:

| Horizon | Markets | Overall calibration | Binomial p |
|---|---|---|---|
| 60 min pre-event | 77 | 0.4156 vs fair 0.4323 | 0.819 |
| **240 min pre-event** | **427** | **0.5152 vs fair 0.5168** | **0.961** |
| 1440 min pre-event | 222 | 0.4685 vs fair 0.4988 | 0.383 |

Bucket-level CIs are still **±11 to ±29pp**, and **0 of 7 Polymarket values are excluded**:

| Bucket | Kalshi | 95% CI | Polymarket | |
|---|---|---|---|---|
| 0.2–0.3 | −5.70pp | [−14.37, +6.01] | −8.03pp | cannot exclude |
| 0.6–0.7 | −2.59pp | [−18.86, +11.93] | +8.57pp | cannot exclude |
| 0.7–0.8 | −0.43pp | [−13.61, +10.18] | +9.63pp | cannot exclude |

**Why it failed, and it is not a fixable method problem.** Sports markets simply are not
traded much four-plus hours before the event — the volume is concentrated near and during
play. So pre-match n is limited by *trader behaviour*, not by my pagination. Mining deeper
history cannot fix it.

**And the aggregate cannot rescue it.** A favourite-longshot bias is a *redistribution*
across buckets — longshots lose what favourites gain — so it nets to roughly zero in
aggregate by construction. The beautifully calibrated 0.5152-vs-0.5168 overall figure is
reassuring about general efficiency but is **structurally incapable** of testing for this
particular bias.

### So what is actually established

- **Well established:** Kalshi sports markets are efficient in aggregate — takers lose
  −0.67pp against a 2.72% overround across 490k fills.
- **Point estimates:** every pre-match bucket sits near fair, with no longshot pattern.
- **Not established:** that a Polymarket-sized (6–9pp) bucket-level bias is absent. The
  CIs are too wide, and historical mining cannot narrow them.
- **The only fix is recording forward** — capturing quotes on sports markets across many
  events, which the recorders can now do. That is days-to-weeks of tape, not an analysis
  task.

I flagged this as the run that would make the conclusion decisive. It did not. The
direction of evidence is unchanged and still points to no bias, but I over-promised what
the test could deliver.

## 7d. Flow following on the live session — and an efficiency signal worth noting

17,101 trades recorded after the reopen, 16,487 organic after dropping combos, 179 whale
prints ≥ $500. Top markets by traded notional:

| Market | Trades | Notional | One-sidedness | Side |
|---|---|---|---|---|
| `KXBTC15M-26JUL300515-15` | 3,854 | $83,307 | **0.071** | — |
| `KXITFWMATCH-…-SHO` (tennis) | 230 | $49,848 | 0.922 | yes |
| `KXITFWMATCH-…-DYU` (tennis) | 317 | $24,377 | 0.852 | yes |
| `KXETH15M-26JUL300515-15` | 728 | $10,455 | **0.005** | — |

**The crypto 15-minute markets are almost perfectly two-sided** — one-sidedness of 0.071
for BTC and 0.005 for ETH, against 0.85–0.92 for the tennis markets. That is an
independent signal of exactly the efficiency the cost-bar analysis predicted: the most
liquid contract on the exchange has essentially balanced taker flow, so there is no
accumulating one-sided position to follow. Flow following, if it works anywhere, will work
in the thin one-sided sports markets — which are precisely the ones where the spread eats
the edge.

## 7e. The measured cost bar — and liquidity that vanishes exactly when the model sharpens

With real books recording I could finally measure the `KXBTC15M` cost bar instead of
estimating it. 123 top-of-book snapshots across one market's full 15-minute life:

| Time to expiry | Median spread | **Median depth at touch** | Median mid | Fee at mid | **Total breakeven** |
|---|---|---|---|---|---|
| 10–15 min | 1.0¢ | **158** | 0.50 | 3.50¢ | **4.50¢** |
| 5–10 min | 1.0¢ | **54** | 0.64 | 3.22¢ | **4.22¢** |
| 2–5 min | 1.0¢ | **4** | 0.66 | 3.12¢ | **4.12¢** |
| 60–120 s | 1.0¢ | **4** | 0.66 | 3.12¢ | **4.12¢** |
| 0–60 s | 1.0¢ | **4** | 0.66 | 3.12¢ | **4.12¢** |

Two things fall out, and the second is the more damaging.

**First, the real bar is 4.1–4.5¢, not 3.5¢.** My earlier figure assumed a zero spread;
the measured 1¢ spread adds directly to it. So a directional edge needs to exceed roughly
**4.2 points**, making the already-dead direction effects (1.43–2.11pp) even further out
of reach.

**Second — and this is the finding I did not anticipate — depth at the touch collapses
40× as expiry approaches, from 158 contracts to 4.** Put that beside the Phase 5 result
that the model gets sharpest near expiry (Brier 0.036 at 60 s vs 0.224 at 780 s) and the
two facts are in direct opposition: **the informational edge and the available liquidity
are anti-correlated.** Precisely when you know most, there is essentially nothing to trade
against. A strategy built on late-window confidence cannot be executed in any size, and
one built on early-window liquidity is trading close to a coin flip at a 4.5¢ bar.

This is an independent reason for the `KXBTC15M` NO-GO that has nothing to do with the
at-the-money fee argument, and I would not have found it without recorded books.

**Caveat: n = 1 market**, 9–44 snapshots per bucket. The depth gradient is large and
monotone, which makes it unlikely to be noise, but it needs many markets to be solid.
`scripts/score_vs_mid.py` re-runs this and the vs-mid comparison as the tape grows.

## 8b. A recorder bug found after the reopen — and why it is in this report

At 09:15 UTC I checked whether live `KXBTC15M` books were being captured and found
**zero rows for it**, with `n_levels: 0` on every ticker. The cause: the orderbook
response nests the book under **`orderbook_fp` at the top level**, and the recorder
unwrapped a non-existent `"orderbook"` key first. That returned `{}` on every call, so
`_ob_rows` emitted nothing and the worker wrote an "empty book" marker instead.

**Every book snapshot from 07:30 to 09:15 was an empty marker.** I had reported the
recorders as healthy on row counts alone — the counts were real, the content was not.
Row counts are not a data-quality check, and I should not have treated them as one.

Fixed, 9 regression tests added pinning the verbatim live payload shape, the ~1.8 hours of
empty book files quarantined to `data/raw_empty_books_prefix/` rather than deleted, and the
recorder restarted. Post-fix, within three minutes: **12,031 real tier1 book rows across
20 markets with up to 97 price levels**, including 3,487 `KXBTC15M` rows, plus 8,813 tier2
rows across 94 markets. Those numbers are what let §7c answer the capacity question.

Little was lost — the halt meant books were genuinely empty for most of that window — but
the bug would have silently destroyed days of the one dataset that cannot be recovered
retroactively.

## 9. Leak test results

| Test | Result |
|---|---|
| **Synthetic-noise control** | **PASS** — 0 of 18 negative-control hypotheses detected an edge in signal-free data |
| **Positive control** | **PASS** — 3 of 6 detected a deliberately-injected 6¢ mispricing |
| Knowability assertions | **PASS** — asserted in code: `price anchor < decision < settlement`, on all 31,310 panel rows |
| Price-anchor discipline | **PASS** — anchor is the last **fully closed** 1-minute candle strictly before the decision |
| Post-settlement fields | **Excluded by construction** — `last_price_dollars` on settled markets is 0.001/0.999 and was never used as a price anchor |
| Feature-shift and label-shuffle | Implemented in `evaluate.py`; **not exercised** — no fitted model reached the stage of needing them |

**The synthetic control caught a real error in my own test design, which is the point of
having it.** My first version set the synthetic "market mid" to the true probability
*plus* noise. Every near-optimal model then beat it and the control reported FAIL — but
that was arithmetic, not leakage: adding zero-mean noise to a probability forecast
strictly raises its Brier score, so anything closer to the truth wins. Corrected to pin
the mid at the exact true probability.

I also added a **positive control**, which the brief did not ask for and which I think it
needs: a suite of only negative controls is passed trivially by a pipeline that never
detects anything. Requiring detection of a known 6¢ mispricing distinguishes a correct
pipeline from a broken-and-silent one.

**One genuine bug was caught and fixed by an assertion:** `close_time` parses as
`datetime64[us]`, not `[ns]`, so `astype("int64") // 10**9` produced 1785393 instead of
1785393600 — every price lookup silently missed and the panel came back empty. If the
assertion had not been there this would have looked like "no data available" rather than
a unit error. Now converted resolution-independently with an explicit overlap check.

## 10. What is blocked on more recorded data

| Blocked item | Needs | Why |
|---|---|---|
| **Our Brier vs Kalshi's mid — the headline comparison** | **~3–7 days** of tier1/tier2 books | No historical order book exists. This is the single biggest hole in tonight's work and it is unrecoverable retroactively. |
| **Weather ladder capacity — the one question that decides the shortlist** | **~3 days** of tier2 books | Settled volumes look thin (0–202 contracts) but volume ≠ depth at the touch. |
| **Counterparty fingerprint (rubric dimension 6)** | **~3 days** spanning all 24 hours | Needs order-size distributions, quote-update frequency, cancel-to-trade ratio, hour-of-day activity. Left as `NaN` in the CSV rather than guessed. |
| **Arb violation frequency and persistence** | **~7 days** including live sessions | All 42 scans ran during the trading halt. |
| **Flow following (Phase 6 Kalshi side)** | **~2 days** of the exchange-wide trade feed | Feed is anonymous but combo legs are filterable via `mve_collection_ticker` — 87% of markets. |
| **Macro release vol response** | **~30 days** to cover CPI/PPI/NFP/FOMC/claims | No release fell in tonight's window. |
| **Deribit implied-vol blend** | **~2 days** of option chains | 846 instruments captured per snapshot at 5-min intervals. |

## 11. Top three next actions, by information gain per hour

*(The original #1 — verify `won` semantics — was completed during the session; see §7.
These are the three that remain.)*

**1. Test the favourite-longshot bias on Kalshi rather than Polymarket (≈2 hours).**
Now the highest-information item. If a 6–9pp bias exists on Kalshi tennis at posted
prices, that beats copy trading outright: simpler, a 20× tighter CI, no wallet ranking to
maintain, no reflexivity. Your own Betfair r = 0.9878 result suggests it will **not** be
there — which is exactly why the test is cheap and decisive either way. Pull settled
Kalshi tennis markets with their pre-close quotes and bucket realised outcomes by entry
price. If the bias is absent on Kalshi, the whole Phase 6 result becomes a Polymarket
fact with no bearing on your Kalshi trading, and you should know that before adding size.

**2. Let the recorders run three days, then answer the weather capacity question (≈1 hour
of work after the wait).** Weather has the best structure on the exchange — free physical
ground truth, monotone nested ladders, hourly recurrence, machine-readable settlement,
`KXHIGHDEN` at a 2.54¢ breakeven. It is blocked on one measurement: is there depth at the
touch? Nothing else should be built until that is known — building a weather model first
risks weeks on a market that cannot be filled.

**3. Re-run the copy-trading persistence test filtered to `behaviour = 'directional'`
(≈1 hour).** 36% of positions held both outcomes, so a third of the "signal" is hedging
noise rather than a view. Filtering to directional positions should *sharpen* the
persistence result if it is real — and if it weakens it instead, that is strong evidence
the apparent edge is an artifact of hedge legs. Cheap, and it cuts both ways, which makes
it a good test.

**Explicitly not recommended:** more `KXBTC15M` direction work. The 3.5¢ at-the-money
cost bar is structural, not a modelling failure, and every effect found is under half of
it.

---

## Deliverables

| File | Contents |
|---|---|
| `docs/contract_spec.md` | Phase 0 ground truth, per-row source and confidence |
| `docs/market_screen.csv` | 3,133 series × 8 rubric dimensions |
| `docs/shortlist.md` | Shortlist, kill reasons, rubric critique |
| `docs/PREREGISTRATION.md` | Hypotheses, grids, fill model, abandonment criteria |
| `docs/HYPOTHESIS_LEDGER.md` | 76 hypotheses, FDR accounting |
| `docs/GO_NO_GO.md` | Bar defined in advance, then what happened |
| `DECISIONS.md` | 10 logged decisions |
| `PAID_OPTIONS.md` | 6 options costed and declined |
| `data/gaps_report.md` | Coverage, gaps, dataset limitations |
| `data/manifest.json` | 158 files, row counts, checksums |
| `notebooks/*.png` | 5 charts |
| `reports/*` | Analysis outputs |

**Still running:** Kalshi tiered recorder, external recorder (spot/perp/Deribit/NWS), arb
scanner. Restart any of them with:

```bash
cd "C:/Users/vinig/kalshi markets" && ./.venv/Scripts/python.exe scripts/record_kalshi.py
```
