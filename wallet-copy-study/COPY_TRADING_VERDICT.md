# COPY TRADING VERDICT

# EDGE, SLOW DECAY — but the copyable part is smaller than the spread

**Do not build the bot.** Not because the edge is fake, and not because it is
too fast to catch. Because latency was never the binding constraint, and the
part of the edge you can actually copy is worth less than the spread you must
cross to take it.

The three findings that produce that verdict:

1. **Wallet skill is real and it persists out of sample.** Rank correlation
   between periods is 0.157–0.433, positive at every cut point and every
   sample-size threshold, and it *rises* with observations per wallet. A
   period-1 top decile keeps **+2.567pp of excess** over the price-bucket
   benchmark into an untouched period 2, CI95 **[2.19, 2.96]**.
2. **The edge does not decay with latency.** The copy return is flat from 0s to
   1800s. A bot buys you essentially nothing over a human refreshing a page.
3. ~~**But 72% of the edge lives in exits**~~ **— RETRACTED, see the amendment
   immediately below (LEDGER W006). It was a fee artifact; the genuine exit
   component is −0.106pp, i.e. −4.3%, not +72%.** The rest of this point stands
   and is what carries the verdict: **the copyable edge is eaten by the
   spread.** Copying entries and holding to settlement returns **+0.937pp** net
   of fee (CI95 [0.53, 1.38]). The median same-block trade-price dispersion —
   itself a *lower bound* on the quoted spread — is **1.0pp**. That leaves
   **−0.06pp**: break-even at best, before any slippage, before any reflexivity,
   and at a delay of zero that is not physically achievable.

---

> ## ⚠ AMENDED 2026-08-01 — the exit study
>
> This verdict originally said **72% of the edge lives in exits**, and named
> "test copying exits" as the highest-value follow-up. That follow-up has now
> run, and **the 72% claim is retracted.**
>
> `gap = (realised_per_share − outcome) + fee(entry_px)`. The second term exists
> only because a **gross** wallet edge was compared against a **net** copier
> return. For the ~80% of positions held to settlement `realised == outcome`, so
> on those the entire gap is that fee. Measured: the genuine exit component is
> **−0.106pp**, or **−4.3%** of the gap — not +72%.
>
> **Copying exits does not recover anything; it destroys value.** Top-decile
> delta versus buy-and-hold is **−0.505pp** CI[−0.643, −0.373] at zero delay
> (p=0.0005), worsening to −0.698pp at a 1.0pp-per-leg spread. 18 of 20 tests
> significant under BH-FDR at 5%.
>
> **The verdict itself is unchanged** — `EDGE, SLOW DECAY, do not build` — but
> the *reason* is now cleaner. The copier captures only +0.937pp of a +2.567pp
> wallet edge because of **the fee**, not because of forgone exit skill. Full
> detail in the section "Exit study" below and in
> `reports/exit_stage1_decomposition.json`, `reports/exit_anatomy.json`,
> `reports/exit_fee_era_ranking.json`.

---

## What was retracted during this session

Recorded as prominently as anything found, per the brief.

**1. An intermediate reading that copying the selected wallets loses 5.9pp was
wrong, and I corrected it.** Measured on the market panel, the period-1 top
decile's period-2 signals gave a copy return of −5.90pp, CI95 [−12.06, −1.13].
That rested on the overlap between 47 selected wallets and a 2,529-market
sample: **1,944 signals in 140 markets**. Re-measured on the wallet panel, where
every fill of every selected wallet is present, the same quantity is
**+0.937pp** on **31,703 wallet-markets**. The wide interval on the small slice
was the warning; the small slice was not representative. The full-sample number
is the one that stands.

**2. The fee formula check initially reported median relative error 0.96.** Cause
was an inverted maker side: `makerAssetId == 0` means the maker *paid* USDC, i.e.
bought, and the fee is denominated in the asset the maker *receives*. Corrected,
the formula fits **100.0% of 5,362 fills within 1%**. A silent sign error there
would have poisoned every cost number in the study, so it is guarded by a test
that asserts inverting the side is off by exactly 100% at 50¢.

**3. `enable_order_book` as an eligibility criterion produced zero eligible
markets** out of 2,108,796. It reports *current* tradability and is false for
essentially every resolved market — it was excluding markets precisely for
having finished. Removed; eligibility is now 874,943 markets.

**4. The prior study's +7.05pp naive benchmark could not be audited and was
treated as void.** A recursive search of `C:\Users\gianf` found no copy-trading
study and no wallet dataset. The benchmark was recomputed from scratch and comes
out at **+2.09pp gross with CI95 [−1.37, +5.35]** — not reliably different from
zero, and **−0.29pp net of fees**.

---

## The naive benchmark, by price bucket

Buy everything in the bucket, no wallet selection, hold to settlement.
Market panel: 2,234,479 buys across 2,271 markets. CIs are **market-clustered**
bootstrap — a market is one draw regardless of how many trades it contains.

| Bucket | n trades | n markets | Gross pp | Net pp | Gross CI95 |
|---|---|---|---|---|---|
| 0.00–0.05 | 209,035 | 2,144 | +0.31 | +0.15 | [−0.73, +1.79] |
| 0.05–0.10 | 85,278 | 1,368 | −1.44 | −2.13 | [−3.60, +1.32] |
| 0.10–0.20 | 143,992 | 1,332 | −3.33 | −4.77 | [−6.35, +0.08] |
| 0.20–0.30 | 162,492 | 1,241 | +0.84 | −1.62 | [−4.31, +5.66] |
| 0.30–0.40 | 192,844 | 1,220 | −2.44 | −5.92 | [−6.87, +2.02] |
| 0.40–0.50 | 315,419 | 1,262 | −0.70 | −5.21 | [−4.54, +3.83] |
| 0.50–0.60 | 324,775 | 1,278 | +0.65 | −3.98 | [−3.85, +4.28] |
| 0.60–0.70 | 194,319 | 1,222 | +2.36 | −1.21 | [−2.05, +7.04] |
| 0.70–0.80 | 159,704 | 1,219 | −0.11 | −2.67 | [−4.99, +5.00] |
| **0.80–0.90** | 143,463 | 1,311 | **+4.16** | **+2.62** | **[+1.03, +7.05]** |
| 0.90–0.95 | 85,580 | 1,308 | +2.11 | +1.33 | [−0.69, +4.42] |
| 0.95–1.00 | 217,578 | 2,171 | −0.02 | −0.20 | [−1.55, +1.05] |

**Favourite band 0.60–0.95: +2.09pp gross, CI95 [−1.37, +5.35], −0.29pp net.**

**Does favourite-longshot bias still exist?** Directionally yes — longshots lose,
favourites win, and 0.80–0.90 is the one bucket whose interval excludes zero. But
once intervals are clustered by market, the effect is **not reliably positive**,
and **it is negative after fees**. It is nothing like the +7.05pp the prior
attempt reported on n=98,766. That number was almost certainly a trade-clustered
interval on a market-clustered phenomenon.

---

## Persistence, at every split point

Unit of observation is a **market** (and, in scenarios C/D, a **(wallet, series,
day)** — so 288 BTC up/down 5-minute markets in one day stop counting as 288
independent draws). Metric is **excess over the entry-price-bucket benchmark**,
so favourite exposure is netted out before anything is ranked.

Spearman ρ, period 1 → period 2:

| Scenario | 2025-01-01 | 2025-07-01 | 2026-01-08 (fee regime) |
|---|---|---|---|
| A: all wallets, unit=market | 0.162 / 0.177 / 0.315 | 0.174 / 0.261 / 0.353 | 0.234 / 0.339 / 0.347 |
| B: market makers removed | 0.144 / 0.144 / 0.284 | 0.185 / 0.250 / 0.349 | 0.202 / 0.317 / 0.316 |
| C: unit = series-day | 0.174 / 0.193 / 0.316 | 0.181 / 0.273 / 0.371 | 0.263 / 0.377 / 0.437 |
| **D: both corrections** | 0.157 / 0.159 / 0.299 | 0.193 / 0.264 / **0.361** | 0.254 / 0.384 / **0.433** |

*(three values are min ≥10 / ≥20 / ≥50 markets per wallet per period)*

**ρ is positive in all 36 cells.** It rises with the market-count threshold,
which is the signature of a real signal measured with less noise rather than a
leaderboard artifact.

Top decile selected on period 1, evaluated on untouched period 2 (scenario D):

| Cut | n wallets | P1 excess | **P2 excess** | P2 CI95 | Bottom decile P2 |
|---|---|---|---|---|---|
| 2025-01-01, min 50 | 112 | +6.88 | +2.030 | [−0.56, +4.36] | −2.74 |
| **2025-07-01, min 50** | 176 | +6.21 | **+3.549** | **[+2.00, +5.08]** | −2.64 |
| 2026-01-08, min 50 | 191 | +5.25 | +1.711 | [−0.84, +3.97] | −3.09 |

**The pattern is symmetric.** Bad wallets stay bad (−2.6 to −3.8pp). Pure noise
regresses both deciles toward the same mean; this does not.

**Survivorship audit.** Requiring activity in both periods excludes wallets that
blew up and quit. Attrition runs 3.7%–37.5% by cut. Survivor-minus-quitter
period-1 excess is +0.82pp and +0.32pp at two cuts and **negative** at the other
two. Real, small, and not driving the result.

---

## The decay curve

Market panel, unconditional over 2,234,479 buy signals. Copy return = outcome −
price at delay − fee, held to settlement.

| Delay | n obs | Copy return | Signal return | Mean price move | Median actual lag |
|---|---|---|---|---|---|
| 0s | 2,234,479 | −2.41pp | −2.41pp | 0.00pp | 0s |
| 1s | 2,205,538 | −1.58pp | −2.43pp | −0.83pp | 2s |
| 10s | 2,199,548 | −1.64pp | −2.42pp | −0.71pp | 10s |
| 60s | 2,164,493 | −1.54pp | −2.32pp | −0.46pp | 60s |
| 300s | 1,750,550 | −1.44pp | −1.61pp | +0.68pp | 306s |
| 1800s | 976,438 | −1.70pp | −1.28pp | +0.97pp | 1932s |

**The curve is flat.** Between +1s and +1800s the copy return moves by ~0.3pp.
The negative price move at short horizons is bid-ask bounce, not information —
a buy lifts the ask and the next print is nearer the bid.

**This is the finding that decides "do we need a bot": no.** Edge that survives
30 minutes unchanged does not reward engineering. The 373ms round trip is
irrelevant, because 1800 seconds is also irrelevant.

The signal *does* carry information — correlation between the post-signal price
move and the eventual outcome is **+0.338** — but the information is priced in
slowly enough that latency is not the constraint.

---

## Where the edge actually lives, and what a copier gets

Period 2, out of sample, full wallet panel. Selection used period-1 data only.

| Group | n wallet-markets | Wallet edge | Wallet excess | Excess CI95 | **Copier (buy & hold)** | Copier CI95 | Gap |
|---|---|---|---|---|---|---|---|
| Top decile | 31,703 | +3.317 | +2.567 | [2.19, 2.96] | **+0.937** | [0.53, 1.38] | **+2.380** |
| Bottom decile | 6,266 | −2.089 | −2.739 | [−3.58, −1.87] | −4.738 | [−5.71, −3.77] | +2.649 |
| All eligible | 135,379 | +0.976 | +0.389 | [0.39, 1.10] | −1.288 | [−1.32, −0.53] | +2.264 |
| Everyone | 1,256,235 | +0.434 | −0.000 | [−0.12, 0.36] | −1.739 | [−1.82, −1.29] | +2.173 |

The **gap** column is the study's central economic finding: `wallet edge −
copier return` is **+2.38pp for the top decile**, i.e. **72% of the wallet's edge
lives in its exits, not its entries.** These wallets carry 79.8% of a position to
settlement and sell out of 23.6% of positions, and it is that selling that
generates most of the measured edge.

A copier cannot have it. Their exits arrive with the same delay as their entries,
and by then the price has moved — which is precisely what the +0.338
move/outcome correlation says.

### Consistency across split points — and a trend that matters

The headline copier number was re-computed at all three cut points, selection
always on period 1 only:

| Cut | n eligible | Top-decile excess | **Copier (buy & hold)** | Gap (edge in exits) | Frac held | Frac sold |
|---|---|---|---|---|---|---|
| 2025-01-01 | 211 | +3.953 [3.47, 4.42] | **+1.981 [1.45, 2.52]** | 2.330 | 0.604 | 0.537 |
| 2025-07-01 | 479 | +2.567 [2.19, 2.96] | **+0.937 [0.53, 1.38]** | 2.380 | 0.798 | 0.236 |
| 2026-01-08 (fee regime) | 822 | +2.068 [1.30, 2.82] | **−0.135 [−0.93, 0.63]** | 2.614 | 0.885 | 0.143 |

Three things to take from this:

1. **The gap is the study's most stable finding: 2.33 / 2.38 / 2.61pp.** ~~The
   claim that roughly 72% of a good wallet's edge lives in its exits holds at
   every split point tested.~~
   > **⚠ RETRACTED (LEDGER W006).** The *gap* is stable — that part is right.
   > What is wrong is reading the gap as exit skill. `gap` compared a **gross**
   > wallet edge against a **net** copier return, and ~80% of positions settle,
   > so the whole gap is the **fee**. Stability across split points is exactly
   > what a fee would produce. The genuine exit component is **−0.106pp =
   > −4.3%**, measured in the exit study below. A number being reproducible is
   > not evidence it measures what you named it.
2. **Wallet excess is positive with a zero-excluding interval at all three
   cuts.** Persistence is not an artifact of where the split was drawn.
3. **The copier return declines monotonically: +1.98 → +0.94 → −0.14.** At the
   most recent cut — the one whose period 2 lies entirely in the fee-bearing era
   — copying entries is **negative before any spread is charged at all**, with an
   interval spanning zero.

That trend is the verdict in miniature. Whatever was copyable is getting less so,
and the era that matters for a decision made today is the one where it is
already gone.

### The arithmetic that kills it

```
copier return, entries copied at the wallet's own price, held to settlement
                                              +0.937 pp   CI [0.53, 1.38]
less spread (median same-block trade dispersion, a LOWER bound)
                                              −1.000 pp
                                              ----------
                                              −0.063 pp
```

And that is the *optimistic* case, because every measurement above flatters the
copier:

- `p_d` is a **trade price, not an ask**. A real copier pays the ask.
- The spread estimate is same-block trade-price *dispersion*, which is a lower
  bound on the quoted spread. Mean dispersion is 2.10pp and p90 is 4.07pp.
- Delay is **zero**, which is not achievable.
- **Reflexivity is not in the number at all.** A signal that looks copyable moves
  the price because people copy it. The more copyable it looks, the worse the
  fill.

---

## Adverse selection and capacity

**Adverse selection: not present in the way expected.** 96.9% of signals are
copyable at +60s. The copyable subset returns −1.54pp against −5.32pp for the
uncopyable subset — copyable fills are *better*, not worse. The uncopyable ones
are in illiquid markets with no next trade, and those are the bad ones. There is
no evidence that being able to copy selects the trades about to move against you.

**Capacity is not the binding constraint.** Signed price impact by trade size:

| Trade size (USD) | n | Signed move | Absolute move |
|---|---|---|---|
| 0–10 | 1,592,669 | +0.021pp | 0.544pp |
| 10–50 | 406,379 | −0.007pp | 0.709pp |
| 50–250 | 163,910 | −0.023pp | 0.795pp |
| 250–1,000 | 48,550 | −0.049pp | 0.810pp |
| 1,000–5,000 | 16,743 | −0.033pp | 0.773pp |
| 5,000–25,000 | 2,785 | −0.109pp | 0.577pp |
| 25,000+ | 456 | −0.049pp | 0.411pp |

Impact does **not** scale with size across four orders of magnitude. Absolute
move sits at 0.41–0.81pp everywhere, which is the spread, not impact. The
constraint on this strategy is the cost of crossing, not the size you can push.
Note this measures sizes that *did* trade, so it understates what a copier adds
on top.

---

## How many wallets clear the sample-size bar

Per-market edge has SD **σ = 0.296**. Detecting a +5pp wallet against a 0pp one
at α=0.05 two-sided with 80% power needs

```
n = ((1.96 + 0.84) × 0.296 / 0.05)² ≈ 274 markets
```

**485 of 1,778** non-market-maker wallets (27%) clear it.

Between-wallet skill dispersion τ, by minimum market count:

| Min markets | n wallets | τ | Skill detected? | Best raw mean → shrunk |
|---|---|---|---|---|
| 10 | 1,630 | 0.000pp | **No** | +18.98pp → −0.63pp |
| 20 | 1,448 | 0.648pp | Yes | +14.48pp → +5.74pp |
| 50 | 1,028 | 2.160pp | Yes | +13.43pp → +9.32pp |
| 100 | 706 | 2.183pp | Yes | +13.43pp → +9.47pp |

**Below ~20 markets, the entire spread in wallet performance is sampling noise.**
The best raw wallet mean at min=10 shrinks from +18.98pp to *below zero*. Any
leaderboard that ranks on fewer than ~20 markets is ranking luck, and this is
the specific mechanism that turned a coinflip into a "+95pp genius" previously.

---

## Structural exclusions

721 of 2,500 wallets removed (28.8%), none on performance:

| Reason | n |
|---|---|
| Market-maker fingerprint (2 of 3) | 682 |
| Too large to copy (median market notional ≥ $5,000) | 41 |
| Infrastructure addresses | 2 (in list; both also caught above) |

Removing them **barely moved ρ** (scenario A → B), so market making is *not* the
explanation for the persistence result.

---

## The cost bar this had to clear

Fee verified empirically as `0.10 × min(p, 1−p)` per share — median relative
error 7.71e-08, **100.0% of 5,362 fills within 1%**, modal implied rate 1000 bps.
The published `0.07 × p × (1−p)` matches **0.0%**.

| Price | Polymarket one-way | Round trip | Kalshi | Poly ÷ Kalshi |
|---|---|---|---|---|
| 10¢ / 90¢ | 1.00¢ | 2.00¢ | 0.63¢ | 1.59× |
| 25¢ / 75¢ | 2.50¢ | 5.00¢ | 1.31¢ | 1.90× |
| 50¢ | **5.00¢** | 10.00¢ | 1.75¢ | **2.86×** |

**A regime break not anticipated by the brief:** Polymarket charged **no fee for
91% of on-chain history**, switching on **2026-01-08** (bisected to the day).
Every wallet ranked on pre-break data earned its record without paying the fee a
copier now faces. Only ~16 weeks of fee-bearing history exists inside subgraph
coverage. Persistence was therefore tested at the regime cut as well as calendar
cuts; ρ is positive there too (0.254–0.433), so the result is not an artifact of
the cost change.

---

## What would change this verdict

- **A better spread estimate.** The 1.0pp haircut is a lower bound derived from
  trade prices, because the subgraph carries no book. If the true effective
  spread for a patient limit order is materially below 1.0pp, +0.937pp becomes
  a real if thin edge. This is the single highest-value follow-up: record the
  CLOB book prospectively and measure the actual ask.
- ~~**Copying exits as well as entries.** 72% of the edge is in exits and this
  study only tested copying entries. Exits arrive with the same delay, so the
  prior is poor — but it is untested, and it is where the money is.~~
  > **⚠ DONE, AND IT FAILED (LEDGER W006/W007).** This was named the
  > highest-value follow-up on the strength of the 72% figure. The follow-up
  > ran: the 72% was a fee artifact, and copying exits **destroys** value at
  > every delay — −0.505pp [−0.643, −0.373], p=0.0005, with 18 of 20 tests
  > surviving BH-FDR. It is not "where the money is"; it is where more of it
  > goes. Do not re-propose this.
- **Restricting to a price band or market type.** All figures here pool across
  market types that behave very differently (30% of eligible markets are
  5-minute crypto up/down). A band-restricted strategy was not tested.

## What would not

- **A faster bot.** The decay curve is flat to 1800 seconds. There is no latency
  budget to hit because latency is not what is taking the money.

---

## Exit study

Run after the main study, because "72% of the edge lives in exits" made copying
exits the obvious next step. It turned out the premise was false.

### 1. The gap was a fee artifact, not exit skill

| Group | Gap | **Exit component** | Fee artifact | Exit share |
|---|---|---|---|---|
| Top decile | 2.484 | **−0.106** | 2.590 | **−4.3%** |
| Bottom decile | 2.669 | −0.070 | 2.739 | −2.6% |
| All eligible | 2.329 | −0.167 | 2.496 | −7.2% |
| Everyone | 2.270 | −0.134 | 2.404 | −5.9% |

### 2. Copying exits loses money at every delay

Top decile, period 2, versus buy-and-hold:

| Spread | Delta | CI95 | p |
|---|---|---|---|
| none | −0.505pp | [−0.643, −0.373] | 0.0005 |
| 0.5pp/leg | −0.602pp | [−0.739, −0.469] | 0.0005 |
| 1.0pp/leg | −0.698pp | [−0.837, −0.565] | 0.0005 |

**18 of 20 tests significant under BH-FDR at 5%.**

### 3. It is neither timing skill nor tail-risk avoidance

`exit_component = frac_sold × (exit_price − outcome)`, split by eventual outcome
(top decile, 8,600 positions with sells):

| Slice | n | Contribution | CI95 | Mean exit price |
|---|---|---|---|---|
| eventual winners | 4,125 (48%) | **−23.988pp** | [−24.73, −23.20] | 0.7277 |
| eventual losers | 4,475 (52%) | **+21.196pp** | [+20.56, +21.86] | 0.2489 |
| net | 8,600 | **−0.476pp** | [−1.02, +0.04] | 0.4786 |

Two enormous effects that almost exactly cancel: they sell winners at 0.73 that
settle at 1.00, and sell losers at 0.25 that settle at 0.00. **The top decile is
no better at this than the full population** (−0.476 vs −0.426pp).

By entry price: **+1.63pp** CI[0.82, 2.40] on longshots, **−2.85pp**
CI[−3.90, −1.76] at mid-price, where selling early forgoes most. 10 of 20 tests
significant under BH-FDR.

### 4. Exit decay is flat, and the mechanical benchmark loses too

Complete books for 3,200 tokens (10,755,763 fills). **Balanced panel — n
constant at 2,879 across every delay**, so none of this is composition drift.

| Delay | Buy & hold | Copy exits | **Delta** | CI95 | p |
|---|---|---|---|---|---|
| 0s | +3.436 | +1.201 | **−2.235** | [−3.36, −1.23] | 0.0005 |
| 10s | +0.781 | −1.333 | −2.114 | [−3.21, −1.08] | 0.0005 |
| 60s | +0.686 | −1.351 | −2.037 | [−3.14, −1.01] | 0.0005 |
| 300s | +0.427 | −1.567 | −1.995 | [−3.10, −0.97] | 0.0005 |

**Exits show no latency decay either** — a flat ~−2pp drag at every delay. With
spread at 60s: −2.537pp (half) and −3.037pp (full). **12 of 13 tests significant
under BH-FDR at 5%.**

**Mechanical hold rule** (sell H after entry, no wallet selection), the exit
benchmark in the way the favourite band was the entry benchmark:

| Hold | Return | vs buy & hold | CI95 |
|---|---|---|---|
| 60s | −0.311 | **−3.548** | [−4.74, −2.34] |
| 300s | −0.209 | −3.446 | [−4.61, −2.20] |
| 1800s | +0.118 | −3.120 | [−4.31, −1.89] |
| 7200s | +0.254 | −2.983 | [−4.14, −1.83] |
| 86400s | +1.714 | −1.523 | [−2.43, −0.62] |

**Shorter holding is strictly worse, monotonically.** Tail-risk avoidance is
refuted: exiting early is a cost, growing the earlier you exit.

**Duration-matched** (mechanical exit at the wallet's own holding period —
identical exposure, different instant): wallet minus mechanical =
**−0.401pp** CI[−1.03, +0.24], **p=0.224**. **No timing skill.**

### 5. REFINEMENT — entries do decay for selected wallets

The buy-and-hold column above falls **+3.436 → +0.427pp** from 0s to 300s: ~3pp
of entry decay in five minutes, on a constant panel, most of it in the first ten
seconds.

The main study reported entry decay as flat to 1800s and concluded latency was
irrelevant. That was **unconditional**, over all 2.23M market-panel buys.
Conditioned on selected wallets' signals, entries **do** decay.

*Limitation:* this subsample is positions with sells in tokens where a top-decile
wallet sold — not a random sample of their entries. Suggestive, not a clean
replacement for the unconditional curve. **It does not change the verdict**
(+0.686pp at 60s is already below the ≥1.0pp spread), but *"latency is
irrelevant"* was too strong. The accurate statement: **latency is irrelevant to
the unconditional population and costs roughly 2.7pp in the first ten seconds for
selected-wallet signals — and even at zero latency the edge is below cost.**

### 6. Ranking inside the fee era gives a nearly disjoint top decile

P1 = 2026-01-08→03-01, P2 = 2026-03-01→04-28, both with fees live:

| | value |
|---|---|
| Top-decile overlap with the fee-free-history ranking | **7 of 36** |
| Jaccard | **0.092** |
| Fee-era top-decile wallets not even *eligible* before | **23 of 36** |
| Persistence within fee era (ρ) | 0.2565 |
| Top decile P1 → P2 excess | +6.441 → **+0.513pp** |

Persistence survives inside the fee era, but it identifies **different wallets**
and what they retain collapses from +3.549pp to +0.513pp. *Caveat:* eight weeks
per sub-period — the composition result is the robust part, the point estimate is
soft. 6 of 7 tests significant under BH-FDR.

---

## Phase 5 was not run, deliberately

The brief gates Phase 5 (portfolio construction, sizing, exit policy, forward
test) on "Phase 4a shows persistence **and** 4c shows an actionable window".
Persistence holds. An actionable window does not exist: the copyable component is
+0.937pp at the middle cut and **−0.135pp at the most recent one**, against a
spread whose lower bound is 1.0pp. Sizing a position against a negative expected
edge is not a modelling exercise, so Phase 5 was skipped rather than run for
completeness. Nothing in Phase 5 could change the verdict; it would only decorate
it.

---

## Reproduction

| Artifact | Path |
|---|---|
| Data availability, Phase 0 | `docs/data_availability.md` |
| Copyable-wallet definition | `docs/wallet_criteria.md` |
| Method decisions | `DECISIONS.md` |
| Naive benchmark | `reports/phase3_benchmark.json` |
| Persistence (4 cuts × 3 thresholds) | `reports/phase4a_persistence.json` |
| Persistence under both corrections | `reports/phase4a_persistence_clean.json` |
| Skill vs luck | `reports/phase4b_shrinkage.json` |
| Decay curve | `reports/phase4c_decay.json` |
| Selected-wallet decay | `reports/phase4c_decay_selected.json` |
| Edge decomposition / copyability | `reports/phase4c_copyability.json` |
| Adverse selection and capacity | `reports/phase4d_capacity.json` |
| Selection audit and canary | `reports/selection_audit.json` |
| Structural exclusions | `reports/phase2_exclusions.json` |

**Sample:** 2,500 wallets · 14,082,296 wallet-panel fills · 1,746,750 positions ·
2,529 sampled markets · 2,778,373 market-panel fills · universe of 2,108,796
markets, 874,943 eligible. Seed 20260801 throughout.

**Validation:** 32 tests pass, including three that recompute real positions from
raw fills and assert the pipeline agrees, and a canary confirming the excess
metric scores a null strategy at −0.0pp with random subsets straddling zero.
