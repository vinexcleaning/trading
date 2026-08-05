# RESULTS.md — Step 6

**Run 2026-08-05** on the amended design ([PREREGISTRATION.md](PREREGISTRATION.md)
+ **Amendment A1**, both committed before this run). Raw:
`reports/grid_train.json`, `anchor_sweep.json`, `spread_vs_lead.json`.

**Headline: nothing survives, on either family, at any anchor. And the most
useful thing the run produced is not a strategy result — it is that the cost
bar every entry in [SHORTLIST.md](SHORTLIST.md) was ranked on is measured at a
moment a pre-match strategy cannot trade.**

---

## 1. The guards, first — two of them changed the run

| guard | test family | control (`KXMLBGAME`) |
|---|---|---|
| selection canary, P(kept wins) = 0.5 | **PASS** 0.4894, z = −1.12, n = 2,779 | **UNTESTABLE** 0.5248, z = +1.49, MDE 3.25 pp > 2.0 pp |
| leak canary at the pre-registered −60 min | **VOID** — 13.96% extreme, 99.7% correct | 5.17% extreme, 95.7% correct |
| leak canary at the amended −24 h | **PASS** — 0.65% extreme, 90.0% correct | **PASS** — 0.00% extreme |
| negative-control gate | — | **PASS**, 0 positive survivors of 148 cells |

The control's selection canary is **UNTESTABLE, not PASS** — n = 909 cannot
resolve a 2 pp bias. Reported as such rather than rendered as a pass.

## 2. The result

| | test (CS2 + LoL + Valorant) | control (MLB moneyline) |
|---|---|---|
| events with a usable panel | 2,779 | 909 |
| train / sealed holdout | 1,945 / 834 | 636 / 273 |
| cells swept | **260** | 148 |
| BH-FDR q = 0.10 threshold | p ≤ 0.04579 | p ≤ 0.00318 |
| cells surviving BH | 120 | 8 |
| **cells surviving BH with CI > 0** | **0** | **0** |

**Every surviving cell is significantly NEGATIVE.** The holdout has not been
touched: nothing qualified to face it. Per §3.8 of the pre-registration it stays
sealed.

### The naive benchmarks, reported beside everything

At the primary anchor and slippage (−24 h, 1.0¢):

| benchmark | test family | control |
|---|---|---|
| **H0-RANDOM** — random side, no view | **−6.826¢** [−9.490, −4.259] | −5.747¢ [−9.167, −2.077] |
| **H0-ALLYES** — buy the kept side of every event | **−8.680¢** [−12.305, −5.335] | −2.426¢ [−6.257, +1.311] |

n_trades 979, **n_days 59, n_eff 718–1,258**, design effect 0.8–1.4×.

> **No strategy in the grid beat the random-side benchmark with a CI above
> zero.** The best-looking cells (H9 stale-quote +7.96¢, H6 momentum +7.78¢)
> have CIs of [−1.25, +17.30] and [−2.02, +16.20] on 70 and 83 trades. They are
> what 260 cells produce by chance.

### The parameter surface — the shape is the finding

H1 calibration by price band, −24 h, slippage 1.0¢, test family:

| band | n_trades | n_eff | mean | CI |
|---|---|---|---|---|
| 10–20¢ | 39 | 31 | −1.41¢ | [−11.97, +13.06] |
| 20–30¢ | 69 | 71 | −9.06¢ | [−18.12, +0.69] |
| 30–40¢ | 109 | 176 | −7.73¢ | [−14.46, **−0.44**] |
| **40–50¢** | 152 | 151 | **+0.13¢** | [−7.65, +8.22] |
| 50–60¢ | 149 | 107 | −6.13¢ | [−15.47, +3.01] |
| 60–70¢ | 144 | 168 | −8.38¢ | [−15.81, **−0.77**] |
| 70–80¢ | 139 | 116 | −9.60¢ | [−18.02, **−1.14**] |
| 80–90¢ | 98 | 76 | −10.55¢ | [−20.20, **−1.67**] |
| **90–95¢** | 32 | 30 | **−31.63¢** | [−47.77, **−12.92**] |

The single positive band, 40–50¢ at +0.13¢, has a **nearest-neighbour gap of
+6.25¢** → labelled **PEAK (isolated — treat as overfitting)** by the
pre-registered rule, and its CI contains zero anyway.

**The real signal in this table is the monotone decline with price.** Buying the
favourite a day out loses more the bigger the favourite, reaching **−31.6¢ per
contract at 90–95¢ with a CI entirely below zero**. That is not a tradeable
inversion — the mirror trade is buying longshots, and 10–20¢ is −1.41¢ with a
CI spanning 25 points. It is a **cost** result: the wings are where the spread
is widest, and §3 is why.

## 3. ⚠ THE FINDING THAT OUTLIVES THE NULL

**Dimension C — the cost bar — has been measured at the touch, on the busiest
markets, at a moment a pre-match strategy cannot trade.**

Median spread by lead time (`src/spread_vs_lead.py`, over **all** settled
markets, not the busiest):

| series | 15 min | −6 h | **−24 h** | p90 @15min → **p90 @−24h** | mean @15min → **@−24h** |
|---|---|---|---|---|---|
| KXCS2GAME | 3.0¢ | 2.0¢ | **4.0¢** | 12¢ → **69¢** | 6.44¢ → **18.33¢** |
| KXLOLGAME | 1.0¢ | 1.0¢ | **3.0¢** | 4¢ → **62¢** | 3.19¢ → **12.46¢** |
| KXVALORANTGAME | 2.0¢ | 2.0¢ | **3.0¢** | 7¢ → **10¢** | 3.73¢ → **6.16¢** |
| **KXMLBGAME** | **1.0¢** | **1.0¢** | **1.0¢** | 1¢ → **1¢** | 1.12¢ → **1.08¢** |

Three things follow, and each is more useful than any cell in the grid:

1. **The median barely moves; the tail explodes.** CS2's p90 goes 12¢ → 69¢ and
   its *mean* triples. **A strategy that must trade every qualifying event pays
   the mean, not the median.** That is precisely why the naive benchmarks land
   at −6.8¢ to −8.7¢ against a "2.2¢ cost bar" — the bar was a median of the
   best case.

2. **`market-selection` reported a 1.0¢ median spread and 21,236 contracts at
   the touch on KXCS2GAME. I measure 3.0¢ even at 15 minutes.** Both are right
   and they measure different things: its stated convention was *"the busiest
   markets inside the busiest tags, i.e. each family's BEST case"*. Mine is the
   population of settled markets. **The strategy pays the population number.**
   Neither file was wrong; the two were never comparable, and nothing said so.

3. **MLB moneyline is genuinely 1.0¢ at every lead from 15 minutes to 24 hours,
   p90 included.** The contrast is the point: a deep continuously-quoted market
   looks completely different from esports, and the control family is the only
   one in this project whose quoted cost is stable enough that a pre-match
   strategy could rely on it.

> **Consequence for SHORTLIST.md.** Every entry's dimension-C figure is a
> best-case touch measurement. For esports — shortlist **#1** — the cost a
> real pre-match strategy pays is **3–6× larger** than the figure it was ranked
> on. That does not kill the entry, because the reference-price mechanism has
> never been tested. It does mean the edge required is several times bigger than
> the shortlist implies.

## 4. Why each strategy failed

Reported for losers too, per the brief — the failure reasons are where the next
idea comes from.

| ID | outcome | why |
|---|---|---|
| H1 calibration | no band clears | prices are calibrated to within the (large) cost; the monotone decline with price is a spread effect, not a mispricing |
| H2 longshot / H3 favourite | negative | the racetrack bias is absent, matching the Polymarket ten-strategy study (longshots ≤0.20 implied 0.73%, actual 1.15%) |
| H4 60–95¢ band | negative | the band that was **K015 = W011** on Polymarket is negative here too, on a third venue-sport |
| H5 fade / H6 momentum | CI spans zero | best cell +7.78¢ [−2.02, +16.20] on 83 trades. The pre-registered rule that momentum must be measured on *early* prices is what kept this honest |
| H7 wide spread | negative | buying the wide side buys the cost |
| H8 low volume | negative | "nobody is watching" is also "nobody will fill you" |
| H9 stale quote | CI spans zero | best cell +7.96¢ [−1.25, +17.30] on 70 trades, n_eff 94 |
| **H10 passive quoting** | **NOT RUN** | needs the order book, not candles. See §5 — it is now runnable and it is the most informative cell in the grid |

## 5. What changed underneath this run

**The premise the brief was written on is refuted.** A sibling session
established that `archive.pmxt.dev` carries Kalshi **full L2** — microsecond
timestamps, `yes_bids`/`no_bids` ladders, delta + snapshot. I confirmed it
carries the families here, by opening one file (2026-05-30T17, 19,310,089 rows):

| family | rows in that hour | % of hour | distinct tickers |
|---|---|---|---|
| tennis | 2,092,158 | 10.835% | 186 |
| **esports** | **498,434** | **2.581%** | **74** |
| MLB | 70,629 | 0.366% | 117 |
| **S. American soccer** | **0** | **0.000%** | **0** |

550 hourly files, **2026-05-19T06 → 2026-06-11T03**.

- **H10 is now runnable**, and it is the cell that matters: the maker-vs-taker
  tension is unresolved and the one number anyone has put on it is the **38% of
  gross** that adverse selection cost the esports arb author.
- **Zero soccer rows is a third independent confirmation** that the prior #1
  entry has no history — after the 152-event count and the listing boundary.
- ⚠ **Correction for the sibling:** their disk estimate assumed tennis is ~0.6%
  of rows, measured on `2026-05-17T02` — an overnight hour. At `2026-05-30T17`
  it is **10.8%**, an 18× difference. Their ~230 MB projection is low; mine is
  ~4 GB for tennis across the window, ~1 GB for esports.

## 6. Status against the pre-registration

| rule | honoured? |
|---|---|
| holdout sealed until survivors face it once | ✅ untouched — nothing qualified |
| one BH-FDR denominator across the whole grid | ✅ 260 cells, including the sensitivity arm |
| naive benchmark reported beside every result | ✅ two of them |
| effective n, not nominal | ✅ n_eff and design effect on every cell |
| parameter surface, not the peak | ✅ §2, with the PEAK/PLATEAU label fired |
| MDE beside every null | ✅ |
| negative control gates the run | ✅ PASS |
| **expected outcome: all of H1–H10 fail** | ✅ **as pre-registered** |

**This is the 46th correction-shaped result in this programme and it points the
same way as the other 45: the edge shrank.** The pre-registration said all ten
would fail and gave the reasons; they did, for those reasons.

---

## 7. Step 6's mandated prior-art check â€” has anyone tested this and failed?

Asked of the corpora *before* writing this file up, per the brief.

### 7a. Order-book mechanics in the repo corpus (3,201 archives scanned)

| signal | repos | % |
|---|---|---|
| latency model | 1,011 | 31.6% |
| L2 / MBO vocabulary | 994 | 31.1% |
| replay | 626 | 19.6% |
| partial fill | 605 | 18.9% |
| delta apply | 325 | 10.2% |
| **queue position** | **166** | **5.2%** |
| **trade-through** | **96** | **3.0%** |
| pmxt | 151 | 4.7% |

**135 repos carry â‰¥2 core book mechanics AND import Kalshi.** But the two
signals that decide whether a maker backtest is honest â€” **queue position
(5.2%)** and **trade-through (3.0%)** â€” are the two rarest. Most "backtests" fill
on a touch. `tfrmma/prediction-market-maker` (4â˜…) is the only repo carrying all
six signals; `eshan327/kalshi-arb` (0â˜…) carries six of seven.

**So H10 does not have an off-the-shelf implementation to adopt**, and the ones
that exist mostly encode the fill assumption this repo's own `high_sweep` header
calls *"the single easiest way to fake a profitable backtest."*

### 7b. Esports on a prediction market â€” 121 repos, 25 Reddit threads

The single most decision-relevant document is a third-party breakdown of a
public Polymarket wallet: **211 days, $65M closed volume, 5,187 resolved
positions, ~$1M realised** (`1u1j8mq`).

| segment | positions | win rate | PnL |
|---|---|---|---|
| **League of Legends** | 1,819 | **49.0%** | **+$1.47M** |
| Counter-Strike | 393 | 46.8% | +$132K |
| NFL | 467 | **89.5%** | +$73K |
| **"Other"** | 1,705 | **69.8%** | **âˆ’$506K** |

Three things it establishes, and one caution:

1. **The largest esports profit in the corpus comes from a sub-50% win rate.**
   LoL at 49.0% earns +$1.47M while NFL at 89.5% earns +$73K. That is the shape
   of a *value* strategy â€” you are wrong more often than right and paid on entry
   price â€” which is what a reference-price mechanism looks like from the
   outside. It is the closest thing to independent support the shortlist's #1
   entry has.
2. **"Other" at a 69.8% win rate loses $506K.** The high-win-rate segment is the
   losing one, exactly the pattern `1uo6uhz` measured: records farmed by buying
   near-decided outcomes are unfollowable and roughly zero-edge.
3. **ROI on closed volume is 1.6%; profit factor 1.09.** A thin edge on enormous
   volume. Against the spread numbers in Â§3 â€” a **mean** of 6â€“18Â¢ on esports
   pre-match â€” 1.6% is not obviously survivable for anyone trading less often or
   later.

> **Caution, and it is the same one as everywhere else in PRIOR_ART.md:** this
> is a third party analysing a wallet they found *because* it ranks #128 on a
> public leaderboard. Selection on outcome. **W015** applies â€” below ~20 markets
> per wallet the entire spread in wallet performance is sampling noise, and this
> is one wallet out of a leaderboard. It is a lead, not a result.

### 7c. The mechanism is being commoditised

`1szk1id`: someone shipped a single API where
`bookmakers=polymarket,pinnacle,kalshi` returns all three in one call, with
Polymarket's implied probabilities converted to American odds. Their own
measurement: **"Polymarket and Kalshi agree within 1 to 2 cents on most
game-level NBA / NFL / NHL markets where both have liquidity."**

Two consequences. The cross-venue leg is independently confirmed efficient for a
fourth time. And the *build* cost of the reference-price mechanism â€” which
Â§4a of PRIOR_ART.md noted only 3 of 3,195 repos had paid, via Pinnacle's free
endpoint â€” is now available as a hosted API to anyone. **Whatever edge existed
in being one of three people wiring Pinnacle to a prediction market has a
shorter remaining life than it did.**

