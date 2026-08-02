# What makes a wallet copyable

Every criterion below is justified by a measurement in this study, not by
intuition. Where a plausible-sounding criterion turned out to be useless or
harmful, that is recorded too — knowing what *not* to filter on is half of this
document's value.

Measurements come from a panel of **2,500 wallets / 14,082,296 fills /
1,746,750 positions**, drawn activity-weighted from 260 randomly placed
15-minute windows across 2022-11-21 → 2026-04-28, with no performance criterion
in the draw.

---

## The criteria, in the order they should be applied

### 1. Structural exclusions first, never performance
**Rule:** remove market makers, wallets too large to copy, and infrastructure
addresses *before* looking at returns.

**Why measured, not assumed:** Phase 2 removed **721 of 2,500 wallets (28.8%)** —
682 on the market-maker fingerprint, 41 as too large. The order matters: if you
rank first and exclude second, you have already let spread-capture wallets define
what "good" looks like.

**Market-maker fingerprint** — 2 of these 3, each with the panel distribution
that set the threshold:

| Signal | Threshold | Panel distribution (p10/p50/p90) |
|---|---|---|
| two-sided flow rate | ≥ 0.50 | 0.02 / 0.56 / 1.00 |
| median hold time | ≤ 3600s | 0s / 876s / 169,808s |
| settlement-carry rate | ≤ 0.10 | 0.08 / 0.90 / 1.00 |

The median wallet holds a position **876 seconds** and the 25th percentile holds
**zero** (single-fill in-and-out), so a hold-time rule alone would sweep up
ordinary short-horizon traders. Requiring 2 of 3 is what keeps it structural.

**Too large to copy:** median market notional ≥ $5,000. Panel distribution is
p50 $20, p90 $483, p99 $10,506 — so this bites only the extreme tail, which is
correct: it should exclude wallets whose own fills move the book, not merely
large ones.

**Infrastructure:** `0x4bfb41d5…` (29.8% of all fills) and `0xc5d563a3…` (5.9%)
have **no data-API record at all** and are operator/relayer contracts, not users.
The first is also the taker on the oldest fill in the entire sample.

### 2. Rank on excess over the entry-price bucket, never on raw return
**Rule:** a wallet's score is `(realised value per share − entry price)` minus
the pooled mean at the same entry-price bucket.

**Why:** the favourite-longshot bias is still alive on Polymarket. Pooled edge by
entry price on this panel (n = 1,450,999 wallet-market observations):

| Entry price | Gross edge | Net of fee |
|---|---|---|
| 0.05–0.10 | −0.55pp | −0.88pp |
| 0.20–0.30 | −1.12pp | −2.24pp |
| 0.40–0.50 | +0.35pp | −2.24pp |
| 0.60–0.70 | +1.93pp | +0.43pp |
| **0.70–0.80** | **+2.24pp** | **+1.17pp** |
| 0.90–0.95 | +1.01pp | +0.73pp |

A wallet that only ever buys 0.70–0.80 favourites earns +2.24pp with **zero
skill**. Ranking on raw return would promote it. Ranking on excess does not.
(The bias is real but **~2pp, not the ~7pp** a prior attempt reported.)

### 3. Demand ~275 independent markets before believing any wallet
**Rule:** a wallet needs **≈275 markets** before a +5pp edge is distinguishable
from zero.

**Why:** per-market edge has SD **σ = 0.296**. At α = 0.05 two-sided and 80%
power, detecting a 5pp difference needs `((1.96+0.84)·0.296/0.05)² ≈ 274`
markets. Only **485 of 1,778** non-MM wallets (27%) clear that bar.

This is the single hardest constraint in the whole study. Anything ranked on
fewer markets is mostly noise, and the data agrees: the between-wallet skill SD
τ estimates to **0.00pp at min=10 markets**, **0.65pp at min=20**, and
**2.16pp at min=50**. Below ~20 markets, cross-wallet performance spread is
entirely explained by sampling noise.

### 4. Count markets, and preferably series-days — never trades
**Rule:** the unit of observation is a market; for recurring series, a
(wallet, series, day).

**Why:** 288 BTC up/down 5-minute markets in one day is not 288 independent
draws, and 21 bets on one match is one observation. The panel spans **1,517,512
distinct series** across 2,108,796 markets. Collapsing to series-days cut
1,450,999 market observations to **749,762** — meaning roughly **half** the
apparent sample size was replication. Persistence was re-run on the coarser unit
and held (it actually strengthened slightly), but a study that skipped this step
would have overstated its confidence by roughly √2.

### 5. Report shrunk estimates only
**Rule:** never quote a wallet's raw mean.

**Why:** empirical-Bayes shrinkage moved the best raw wallet mean from
**+18.98pp to −0.63pp** at min=10 markets, and from +13.43pp to +9.32pp at
min=50. The raw maximum across thousands of wallets is a measure of sample size,
not skill.

### 6. Require persistence across a cut, and check who quit
**Rule:** rank on period 1, evaluate untouched on period 2, at more than one cut,
and measure attrition.

**Why:** rank correlation on this panel is **0.157–0.433**, positive at every cut
and threshold, and **rises with observations per wallet** — the signature of real
skill measured with less noise. Requiring activity in both periods excludes
wallets that blew up and quit; attrition runs **3.7%–37.5%** depending on the
cut, and survivor-minus-quitter period-1 excess is +0.82pp and +0.32pp at two
cuts and *negative* at the other two. Small, but it must be reported, not assumed
away.

### 7. Exclude positions whose entry cost is unobservable
**Rule:** drop positions where the running share balance goes negative, or where
there are sells and no buys.

**Why:** splits and merges (USDC ↔ a complete token set) are ConditionalTokens
events **absent from the orderbook subgraph**, so those tokens have an entry cost
that cannot be seen. This is **1.85%** of positions — and they report a nonsense
mean edge of **+187pp**, an artifact of a near-zero shares-bought denominator.
Including them does not add noise; it adds garbage. Their win rate (0.396) is
lower than the clean set's (0.487), so the exclusion is not neutral and its size
is reported rather than buried.

---

## Criteria that sound sensible and are NOT used

- **Win rate.** A wallet buying at 0.90 and winning 90% of the time has *zero*
  edge. Any rule containing a win rate reintroduces the favourite-longshot bias
  through the back door.
- **Profit or ROI.** Same defect, plus it rewards size rather than skill.
- **Holding to settlement as a quality signal.** 89.2% of panel positions are
  carried to settlement, so it barely discriminates; it earns its place only as
  one of three market-maker signals, where it is the wallet's *action*, not its
  result.
- **Hedging as a disqualifier.** 17.9% of wallet-markets trade both outcomes.
  That is ordinary position management, not a defect, and per-token accounting
  already handles it.
- **Volume or liquidity of the markets traded.** Selecting markets on volume
  preferentially selects market-maker-heavy books and biases every downstream
  number. The market sample is drawn without reference to volume for exactly
  this reason.
- **`enable_order_book`.** It reports *current* tradability and is false for
  essentially every resolved market; requiring it produced **zero** eligible
  markets out of 2,108,796.

---

## 8. There is no latency criterion, because latency is not the constraint

Phase 4c has now run, and it changes what this document concludes.

The copy return is **flat from 0s to 1800s** (−1.58 / −1.64 / −1.54 / −1.44 /
−1.70pp at +1s / +10s / +60s / +300s / +1800s). There is no latency budget to
specify. A wallet that satisfies criteria 1–7 is no less copyable at half an
hour's delay than at one second's.

**What binds instead is the fee and the spread.** For a period-1 top decile
evaluated out of sample on period 2:

| | value |
|---|---|
| wallet edge (gross) | +3.317pp |
| wallet excess over price-bucket benchmark | +2.567pp CI[2.19, 2.96] |
| **what a copier gets copying entries and holding** | **+0.937pp CI[0.53, 1.38]** |
| gap | +2.380pp |
| less median same-block spread (a lower bound) | −1.000pp |
| **net** | **−0.063pp** |

> **CORRECTION (2026-08-01).** An earlier version of this section attributed the
> 2.380pp gap to the wallets' exits and stated that "72% of what these wallets
> earn, they earn by selling well." **That was wrong.** Expanding the gap,
> `gap = (realised − outcome) + fee(entry)`, shows it is almost entirely the
> second term — the fee charged to the copier and never charged to the wallet,
> because a *gross* wallet edge was being compared against a *net* copier
> return. The genuine exit component is **−0.106pp**, i.e. slightly negative,
> and accounts for **−4.3%** of the gap rather than +72%. See
> `reports/exit_stage1_decomposition.json`.

### 9. Exit behaviour is not a criterion, because there is nothing there

Tested directly rather than assumed. `exit_component = frac_sold × (exit_price −
outcome)` splits by what the position eventually did (top decile, period 2,
8,600 positions with sells):

| Slice | n | Contribution | Mean exit price |
|---|---|---|---|
| eventual winners | 4,125 | **−23.988pp** | 0.7277 |
| eventual losers | 4,475 | **+21.196pp** | 0.2489 |
| **net** | 8,600 | **−0.476pp** (p=0.066) | 0.4786 |

Two very large effects that almost exactly cancel. Cutting losses earns +21.2pp;
taking profit early gives back −24.0pp. And the top decile is **no better at
this than the full population** (−0.476 vs −0.426pp).

Copying exits is therefore *worse* than buy-and-hold at every delay tested, and
significantly so under BH-FDR. So the final criterion is a negative one:

> **A wallet is copyable only if the portion of its edge realised at ENTRY
> exceeds the fee plus the spread.** No wallet in this panel clears that — and
> nothing is recovered by copying their exits, because their exits are worth
> approximately zero and slightly negative.

Criteria 1–7 correctly identify wallets with genuine, persistent, out-of-sample
skill. They are necessary and not sufficient, and the reason is **cost**, not
speed and not forgone exit skill.
