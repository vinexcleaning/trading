# deribit_method.md

The Deribit-implied risk-neutral pricer (`src/deribit_pricer.py`). Confidence
ratings as elsewhere: **A** = measured live this session, **B** = documented +
corroborated, **C** = inferred, **?** = open.

> **Read this first.** The pricer is complete and validated, but the comparison
> it was built for — Deribit vs Kalshi's **hourly** crypto ladders — **cannot be
> run**. Deribit's shortest usable expiry is 54.2 h; Kalshi's ladder contracts
> have a median lifetime of 1.0 h and only 0.1% reach 54 h. See §6.

---

## 1. Chain retrieval and hygiene (conf A)

Source: `get_book_summary_by_currency`, `get_instruments`, `get_index_price`,
`get_volatility_index_data`. Public, unauthenticated.

### A field trap that silently emptied the first build

`get_book_summary_by_currency` returns **no `bid_iv` / `ask_iv`** — verified
null on all 870 BTC instruments. A filter requiring two-sided *IV* therefore
discarded the entire chain and produced an empty, silently "clean" result. The
endpoint does return `bid_price` / `ask_price` (quoted in units of the
underlying), which are inverted to IV here instead.

### The forward, not the spot

Each row carries a per-expiry **`underlying_price`**, which is the *forward* for
that expiry — **63,964 against a 62,910 spot index on the Dec-26 contract, 1.7%
carry**. Using the spot index as the forward would bias every digital,
increasingly so at longer expiries. `F = underlying_price` per expiry.

### Filters, with thresholds and justification

| filter | threshold | justification |
|---|---|---|
| two-sided quote | `bid_price > 0 and ask_price > 0 and ask ≥ bid` | a one-sided quote carries no bracketing information |
| staleness | quote age ≤ **600 s** | Deribit marks refresh continuously; older than this and the quote predates recent spot moves. Measured: 0 of 870 exceeded it, so this filter is currently non-binding |
| invertibility | price strictly between intrinsic and forward | outside those bounds no Black-76 vol exists; the price is stale or crossed |
| IV sanity | 0.01 < σ < 5.0 | excludes degenerate inversions |
| **thin expiry** | ≥ **8 strikes** | below this, `−∂C/∂K` interpolates a curve rather than measuring one. Chosen because the differencing needs interior nodes on both wings plus the money |

Retained vs discarded is reported per expiry on every run.

**Measured result (2026-08-01 ~01:30 UTC):** BTC 11 of 13 expiries usable, ETH
11 of 13. The two dropped are in both cases the **6.17 h and 30.17 h** expiries —
they exist and are listed, but fail on one-sided quotes and uninvertible prices,
leaving 1 and 5 usable strikes against the minimum of 8.

## 2. Surface fit (conf A)

Interpolation is in **total variance `w = σ²τ` against log-moneyness
`k = ln(K/F)`**, linear in `k`, flat extrapolation beyond the quoted range.
Prices are then rebuilt via Black-76 and differentiated.

Fitting in `(k, w)` rather than `(K, σ)` matters because differentiating a raw
noisy price curve amplifies noise badly; total variance in log-moneyness is the
parameterisation in which the surface is closest to smooth and in which
no-arbitrage conditions are naturally expressed.

Implied vol is recovered by **bisection**, not Newton — `bs_call` is strictly
increasing in `w`, so bisection is unconditionally stable, including in the
wings where Newton diverges and where we most need the values.

## 3. Extraction (conf A)

`P(S_T > K) = −∂C/∂K`, central difference with `h = 10⁻³·K` on the **fitted**
curve.

The numerical digital deliberately differs from the closed-form
`Φ(d₂)`: at the money on the nearest BTC expiry the numerical value is **0.5324**
against a closed-form **0.4965**. The gap is the volatility-skew term
`−∂C/∂σ · ∂σ/∂K`, which the closed-form omits. **The numerical value is the
correct one**; the closed form is retained only as a cross-check that the two
agree away from the skew.

## 4. No-arbitrage checks — reported, never smoothed (conf A)

Checked on the fitted surface at 60 nodes per expiry:

- calls **monotone decreasing** in `K`
- calls **convex** in `K`
- extracted digital **monotone decreasing** in `K`
- **total variance monotone non-decreasing in τ** at fixed `k` (calendar)

**Measured:** calendar arbitrage **0 violations across 50 adjacent pairs** for
both BTC and ETH — the term structure is clean. Butterfly/convexity violations
are concentrated in the **long-dated, thinly-quoted** expiries (13 convexity
violations at both 654 h and 1,326 h for BTC) and are near-zero at short dates.
These are reported per expiry rather than smoothed away, because a violation is
either a data problem or a real signal and the distinction matters. Short-dated
expiries — the ones relevant to any Kalshi comparison — are clean.

## 5. Confidence band (conf A)

`P(S>K)` is re-extracted on the **bid-IV** and **ask-IV** surfaces to bracket it.

This is not decoration. Measured band widths on the nearest expiry: BTC
**0.001–0.080**; ETH up to **0.498** (at K=1850 the band is [0.249, 0.747]).
**A Kalshi–Deribit disagreement inside this band is not evidence of anything**,
and on ETH at some strikes the band is wide enough to admit almost any Kalshi
price. Any comparison must be filtered on band width first.

## 6. Term interpolation — and its hard limit (conf A)

Interpolation is linear in total variance along `τ` at fixed `k`. Every call
returns a mode flag: `interp`, `EXTRAPOLATE_SHORT`, or `EXTRAPOLATE_LONG`, plus
the extrapolation ratio, so no caller can silently consume an extrapolated
number.

### The limit that blocks the intended comparison

| | |
|---|---|
| Deribit shortest **usable** expiry | **54.2 h** |
| Kalshi `KXBTC`/`KXBTCD` contract lifetime (median) | **1.0 h** |
| Kalshi contracts with lifetime ≥ 54 h | **0.1%** |

Pricing a 1-hour Kalshi contract off this surface is a **~54× extrapolation**.
At that ratio the result is dominated by intraday volatility seasonality, which
a 54-hour surface cannot resolve. The brief anticipated an extrapolation problem
and directed treating the daily series as primary — but `KXBTCD` is **hourly**
despite the name, with the same 1.0 h median lifetime.

**Conclusion: not a defensible reference price at Kalshi's crypto horizons.**
The one viable remnant is `KXBTC` **weekly** events (lifetime to 169 h, the
0.1%), which genuinely overlap Deribit's usable range.

## 7. Settlement alignment (conf A / conf ? )

Kalshi settles on the **mean of the final 60 seconds** of the CF Benchmarks
index; Deribit settles on its own index at a point in time. Two consequences:

**(a) Variance adjustment — implemented.** For driftless Brownian motion the
variance of the mean over the final window, relative to a point sample, is

```
factor = 1 − a + a²/3,      a = averaging_window / total_horizon
```

always ≤ 1. An average is less variable than a point sample, so **a correct
Kalshi price sits further from 50¢ than a point-sample model implies**. For a
60 s average on a 1 h contract, `a = 1/60` and the factor is 0.9836 — a ~1.6%
variance reduction, small but systematic and always in the same direction. On a
5-minute contract `a = 0.2` and the factor is 0.8133, which is not small.

**(b) Index divergence — NOT yet quantified (conf ?).** How often the CF
Benchmarks and Deribit indices differ by enough to flip a contract near a strike
is unmeasured. It is a floor on how tight any cross-venue comparison can be, and
it remains open. It does not currently block anything, because §6 blocks the
comparison first.

## 8. Reference values captured

BTC **DVOL 35.53** (7-day range 34.91–38.78); ETH **DVOL 50.17** (48.69–53.32),
2026-08-01 00:25 UTC. BTC 870 option instruments across 13 expiries; ETH 742
across 13.
