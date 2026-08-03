# Phase 1 — Shortlist and kill list

> ## ⚠️ TWO RETRACTED CLAIMS ARE MARKED INLINE BELOW
>
> Both were corrected in [`../MORNING_REPORT.md`](../MORNING_REPORT.md), which
> is the authoritative document. They are struck through here rather than
> deleted so nobody re-derives them from the raw counts.
>
> | Claim as stated here | Status |
> |---|---|
> | weather model validated across **8,090 test markets** | **RETRACTED** — a ladder is one reading; effective n ≈ 800 settlement hours, CIs were ~3× too tight. **Conclusion survives.** |
> | **seven** daily families clear the capacity bar by 7–49×, so weather is not capacity-limited | **RETRACTED framing** — they clear on depth, but have 66 settlements against the 481 needed. Depth without recurrence decides nothing. |
>
> Net effect: the weather model is **still real**, but the tradeable universe
> is **one family (`KXTEMPDCH`), not eight.**

Full scores: `docs/market_screen.csv` (3,133 series with ≥1 open market, 8 dimensions).
**1,112 killed on structure alone.** The screen is for elimination, so what follows
leads with the kill reasons.

## Kill reasons, by frequency

| n | Reason | What it means |
|---|---|---|
| 599 | Median spread exceeds any plausible edge (>8¢) | You would need a >8 point probability edge before fees to break even. Nothing on this exchange plausibly delivers that repeatably. |
| 569 | No liquidity — zero median volume, or quotes mostly absent | Cannot fill. A correct model is worthless without a counterparty. |
| 235 | No independent ground truth **and** no structural check | Pure opinion markets. There is nothing to compute and nothing to arbitrage against. |
| 92 | No two-sided quotes at all | Unpriceable and unfillable. |
| 3 | Fewer than 50 settlements available | Statistically unvalidatable, full stop. |
| 2 | Combo/multivariate only | The legs are priced elsewhere; the combo adds no independent information. |

## Whole categories killed, and why

**Politics (2,070 series) — killed.** Resolution depends on unmodellable human
events. Dimension 1 = 0. Some have bucket structure, which is why they are not *all*
killed by the compound rule, but none has a ground-truth channel we can compute
faster than the market reprices. Not modelled.

**Sports (3,043 series) — deprioritised, as instructed.** Not re-litigated: the
brief already establishes Kalshi tennis tracks Betfair at r = 0.9878, MAD 1.95¢
against a 2.4¢ round trip, and a player-level model lost to the bookmaker benchmark
(Brier 0.2249 vs 0.2057, n = 2,645). The one untested angle — correlated multi-leg
and set-score markets — is handled by the Phase 2 arb scanner, not by a new model.

**Economics releases — killed on recurrence, not on merit.** This is the clearest
kill of the night and it contradicts the brief's optimism:

| Series | Settlements available | Verdict |
|---|---|---|
| `KXCPI` | **23** | below the 50 minimum |
| `KXFED` | **22** | below the 50 minimum |
| `KXCPIYOY` | 48 | below the 50 minimum |
| `KXGDP` | 0 settled returned | unvalidatable |
| `KXJOBS`, `KXCLAIMS` | 0 open markets found | not listed |

The mechanism the brief proposes (professional forecasts are public and free, retail
may not use them) may well be true. It is untestable. Twenty-two Fed decisions cannot
distinguish a real edge from luck at any useful power — the Phase 6 power calculation
implies you need hundreds of settlements to establish a few points of edge. Jobless
claims were the one economics family with plausible sample size, and no open market
for them was found.

**Index range markets — downgraded, premise removed.** The brief's stated reason to
like these was the halved fee multiplier. The live API reports `fee_multiplier: 1`
for `KXINX`, `KXNASDAQ100` and all 48 variants (see `docs/contract_spec.md` §0.2,
`DECISIONS.md` D-002). Without the halving they are ordinary 0.07 series with no
structural advantage, and the ground truth (an index print) is the settlement source
itself rather than something we can compute independently.

---

## The shortlist

Three families survive with a stated mechanism. Nothing else does.

### 1. Internal no-arbitrage violations — highest quality, needs no model

**Mechanism:** none required. Mutually exclusive and exhaustive buckets must price to
100¢; nested thresholds must be monotone in strike. A violation net of fees is money
regardless of anyone's forecast.

**Status: built and running** (`scripts/arb_scanner.py`, 26 structural families
discovered, 55 unit tests). Result so far: **zero net-positive violations across 42
scans**, all during the trading halt, so this is not yet an informative sample.

The scanner's real contribution tonight was a correctness lesson: naively summing a
family produced a **phantom 1,298¢ "arb"** on `KXDJI`, which turned out to be a
60-rung nested `greater_or_equal` ladder rather than an exhaustive bucket set. Family
type is now derived from live `strike_type` data and bucket families must pass an
explicit tiling check before the sum-to-100 constraint is applied. Anyone building
this must do the same or they will find hundreds of arbs that do not exist.

### 2. Weather temperature ladders — best structure on the exchange, liquidity unproven

**Mechanism:** retail prices the forecast; we price the observation. The settlement is
a single number from a named NWS station, the ladder is monotone in strike, and the
observation is partially visible before settlement.

Everything about the structure checks out:

- `KXTEMPDCH`, `KXTEMPLAXH`, `KXTEMPCHIH`, `KXTEMPAUSH` — **hourly** nested
  thresholds at 1 °F steps, ~5,200 settled *markets* each — but only **512
  independent settlements**, because the ~10 strikes on one ladder are one
  temperature reading counted ten times. Never use the market count as n.
- `KXHIGH*` and `KXHIGHT*` daily families across ~15 cities
- Ground truth is free and immediate: `api.weather.gov` returned KDCA at **73.4 °F**
  against live strikes of 67.99–76.99 °F
- Settled markets carry `expiration_value` (e.g. `"75.00"`), so scoring is exact
- Tightest family `KXHIGHDEN` has a 1¢ median spread → **2.54¢ breakeven**

**Volume, measured properly across the full settled history** (an earlier draft of this
file quoted a five-market sample of 0/1/202/0/100, which was an unrepresentatively quiet
hour — corrected):

| Family | Median | p90 | Max | Zero-volume markets |
|---|---|---|---|---|
| `KXTEMPDCH` | 12 | 1,417 | 36,243 | 27.7% |
| `KXTEMPLAXH` | 147 | 2,897 | 44,333 | 23.2% |
| `KXTEMPCHIH` | 114 | 2,468 | 123,496 | 19.7% |
| `KXTEMPAUSH` | 24 | 1,872 | 52,445 | 25.7% |

The median market is thin and roughly a quarter never trade, but the p90 sits at
1,400–2,900 contracts, so genuinely liquid markets exist inside these families. Volume is
not depth at the touch, so capacity remains the open question — but the family should be
approached as "trade the liquid quarter", not written off.

**The model was built and works** (`scripts/weather_model.py`): persistence plus an
hour-of-day change profile reaches Brier **0.058–0.093** out-of-sample against
climatology's 0.163–0.294, ~~across 8,090 test markets in four cities~~, all surviving FDR.
The persistence error is 1.84–2.48 °F against a 6.95–7.00 °F climatological spread. But
beating climatology is table stakes — the market can read the same observation — so this
establishes model soundness, not edge.

> **⚠️ RETRACTED n — "8,090 test markets" is pseudo-replication.**
> Corrected in [`../MORNING_REPORT.md`](../MORNING_REPORT.md). A ladder is
> **one temperature reading**, not 10 independent markets: the 10 strikes on a
> single settlement are the same observation counted ten times. Effective n is
> **~800 settlement hours**, so the original CIs were roughly **3× too tight**.
>
> Re-scored with a bootstrap over whole settlement hours, **the conclusion
> survives comfortably** — this retraction costs the model nothing:
>
> | City | Settlements | Persistence Brier | Climatology Brier | Clustered diff CI |
> |---|---|---|---|---|
> | `KXTEMPDCH` | 204 | 0.1021 | 0.2357 | [+0.111, +0.156] |
> | `KXTEMPLAXH` | 204 | 0.0761 | 0.2162 | [+0.120, +0.160] |
> | `KXTEMPCHIH` | 204 | 0.0979 | 0.2543 | [+0.136, +0.176] |
> | `KXTEMPAUSH` | 200 | 0.1355 | 0.3146 | [+0.149, +0.207] |
>
> All four still beat climatology decisively. Quote the settlement counts, not
> the market counts. The same error inflates the "5,200 settlements per family"
> figure below to its true **512** (hourly) and **66** (daily).

**Capacity question: ANSWERED after the 09:00:42 UTC reopen.** Median depth at the touch,
from live recorded books:

| Family | Median touch depth | vs the 50-contract bar | Independent settlements |
|---|---|---|---|
| `KXHIGHLAX` | 2,434 | passes 49× | **66 — fails the power bar** |
| `KXHIGHNY` | 1,114 | passes 22× | **66 — fails** |
| `KXHIGHMIA` | 738 | passes 15× | **66 — fails** |
| `KXHIGHDEN` | 509 | passes 10× | **66 — fails** |
| `KXHIGHPHIL` | 490 | passes 10× | **66 — fails** |
| `KXHIGHAUS` | 487 | passes 10× | **66 — fails** |
| `KXHIGHCHI` | 371 | passes 7× | **66 — fails** |

> **⚠️ RETRACTED framing — "seven daily families clear the capacity bar by
> 7–49×, so weather is not capacity-limited."**
> Corrected in [`../MORNING_REPORT.md`](../MORNING_REPORT.md) §7g. The depth
> numbers are right. The **inference from them is not.** All seven daily
> families have **66 independent settlements** against the **481** needed to
> detect a 5pp edge at 80% power. They cannot validate an edge at any power,
> so **their depth is irrelevant** — capacity to trade a signal you cannot
> establish is worth nothing. The original framing celebrated the wrong axis.
>
> Cross-tabbing both bars — ≥481 settlements **and** ≥50 contracts at the
> touch — **kills 10 of 11 families.** `KXTEMPDCH` alone clears both, and by
> **512 vs 481**, a margin of 6%.

**Hourly ladders measured separately, and they split sharply:**

| Hourly family | Median touch depth | Verdict |
|---|---|---|
| `KXTEMPDCH` | 2,972 | tradeable |
| `KXTEMPLAXH` / `KXTEMPCHIH` / `KXTEMPAUSH` | 1 | untradeable |

> **Not killed, two of three gates cleared, but the family is narrower than it looked.**
> Recurrence and liquidity coincide only for `KXTEMPDCH`: the hourly families carry
> ~~5,200~~ **512** settlements each but three of four are one contract deep, while the
> daily `KXHIGH*` families have real depth and only ~~~396~~ **66** settlements.
> **Corrected conclusion:** the tradeable universe is `KXTEMPDCH` **alone** — not
> "`KXTEMPDCH` plus the daily families", because 66 settlements cannot validate an
> edge. One family of eleven.
>
> The remaining gate is whether the model beats the mid, which needs days of recorded
> books. Depth samples are 11-17 snapshots per family at one point in the session, and
> depth plausibly builds nearer settlement, so the thin readings may be pessimistic.

### 3. `KXBTC15M` — deepest liquidity, worst cost structure

**Mechanism:** honestly, none established. Included because it is by far the most
liquid recurring contract (median volume 973,904 per 15-minute market, 6,271
settlements in 66 days) and because the brief asks for depth here.

**The obstacle is structural and severe.** Each market's `floor_strike` equals the
previous window's `expiration_value` — confirmed on **99.86% of 6,261 markets**. So
this is not a strike ladder but a single "will BTC be ≥ its level 15 minutes ago"
contract, **minted exactly at-the-money every 15 minutes**. At P ≈ 0.50 the quadratic
fee is maximised, pinning the round trip to **3.50¢**. The cheap tails (1.26¢) are
structurally unreachable at entry.

So any directional edge must exceed **3.5 percentage points** on a driftless asset.
Measured direction effects (Phase 5):

| Horizon | Effect | Edge | vs 3.50pp bar |
|---|---|---|---|
| 5 min | reversal, z = −4.08 | 1.43pp | dead |
| 15 min | reversal, z = −3.08 | 1.86pp | dead |
| 60 min | reversal, z = −1.74 | 2.11pp | dead |

**Statistically real, economically dead.** All three are well-identified and all three
are under the cost bar. This is the cleanest negative result of the night.

---

## Rubric critique — the changes made, and why

The brief asked for the rubric to be critiqued rather than accepted.

**1. Dimension 5 (recurrence) should be a hard gate, not a score.** It is the only
dimension that cannot be compensated. A family scoring 5 on everything else with 22
settlements is unvalidatable, and averaging lets it survive. Implemented as a
disqualifier at <50 settlements — which is what killed the entire economics block.

**2. Dimension 2 (cost bar) must be computed at C≈100, not C=1.** Kalshi ceils the
fee to the whole cent per fill, so at one contract every price from 10¢ to 90¢ rounds
to 1¢ and the quadratic shape disappears entirely. A C=1 table makes the tails look no
cheaper than the middle and would misdirect the whole analysis (`DECISIONS.md` D-010).

**3. Dimension 1 conflates two different things.** "We can compute the answer from
free data" is not the same as "the data is independent of the settlement source." For
weather, NWS observations are genuinely independent of and faster than the market's
view. For `KXBTC15M` the CF Benchmarks index *is* the settlement source, so knowing it
confers no forecasting advantage, only a latency race. These deserve different scores;
weather gets 5, crypto/index get 3.

**4. Add a ninth dimension: capacity.** The rubric scores whether a market is *right*
but never whether it is *large enough to matter*. A 2.5¢ breakeven on a book two
contracts deep is not a strategy. Weather is exactly this case — best structure,
unknown capacity — and the existing rubric cannot express the distinction. Not scored
tonight because it requires recorded depth.

**5. Dimension 6 (counterparty fingerprint) is not scored — deliberately.** It needs
order-size distributions, quote-update frequency, cancel-to-trade ratios and
hour-of-day activity, all of which require recorded books during live trading. The
recorders started inside the daily halt, so there is no honest measurement yet. Left
as `NaN` in the CSV rather than guessed. This is the largest hole in tonight's screen
and the brief was right that it is one of the more interesting things available —
it just needs ~3 days of tape.
