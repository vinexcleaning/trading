# venue_comparison.md

Side-by-side Kalshi vs Polymarket for short-dated crypto binaries.
Confidence ratings as in `venue_spec.md`. Captured 2026-08-01 00:00 UTC.

> ### ⚠️ CORRECTED 2026-08-01 — the original headline was wrong
>
> This file previously stated that taker costs are identical across the two
> venues. **They are not.** On-chain fills show Polymarket's economic taker fee
> is `0.10 × min(p, 1−p)` per share — **2.86× Kalshi at 50¢** — not the
> documented `0.07 × p × (1−p)`. Verified against 4,310 fills to machine
> precision (median relative error 0.000000). See `MORNING_REPORT.md` §00.
>
> The maker-side claim below is **UNVERIFIED and provisional**: `maker_base_fee`
> reads `1000`, which is a market maximum rather than a signed rate, and the
> on-chain record ends 2026-04-28.

**Headline: Kalshi is cheaper than Polymarket for takers at every price point,
by 1.5×–2.9×. The maker comparison is unresolved.**

---

## 1. Cost at every price point, 5¢ → 95¢

Per-contract cost in **cents**. Fee from `src/fees.py` (exact decimal, 15 tests
passing). Spread = one tick, the minimum possible; real spreads are wider.

| price | Kalshi taker `0.07·p(1−p)` | **Poly taker `0.10·min(p,1−p)`** | **ratio** | Kalshi maker (0.25×) | Poly maker (unverified) |
|---:|---:|---:|---:|---:|---:|
| 5¢ | 0.333 | **0.500** | 1.50× | 0.083 | ? |
| 10¢ | 0.630 | **1.000** | 1.59× | 0.158 | ? |
| 15¢ | 0.893 | **1.500** | 1.68× | 0.223 | ? |
| 20¢ | 1.120 | **2.000** | 1.79× | 0.280 | ? |
| 25¢ | 1.313 | **2.500** | 1.90× | 0.328 | ? |
| 30¢ | 1.470 | **3.000** | 2.04× | 0.368 | ? |
| 40¢ | 1.680 | **4.000** | 2.38× | 0.420 | ? |
| **50¢** | **1.750** | **5.000** | **2.86×** | **0.438** | **?** |
| 60¢ | 1.680 | **4.000** | 2.38× | 0.420 | ? |
| 70¢ | 1.470 | **3.000** | 2.04× | 0.368 | ? |
| 75¢ | 1.313 | **2.500** | 1.90× | 0.328 | ? |
| 80¢ | 1.120 | **2.000** | 1.79× | 0.280 | ? |
| 85¢ | 0.893 | **1.500** | 1.68× | 0.223 | ? |
| 90¢ | 0.630 | **1.000** | 1.59× | 0.158 | ? |
| 95¢ | 0.333 | **0.500** | 1.50× | 0.083 | ? |

Kalshi is cheaper at **every** price point. The gap is worst at the money
(2.86×) and narrowest in the wings (1.50×) — because the two fee curves have
different *shapes*: Kalshi's is quadratic `p(1−p)`, Polymarket's is the
piecewise-linear `min(p, 1−p)`.

Ticks are unchanged: Kalshi 0.1¢ on `*15M` / 1¢ on hourly ladders; Polymarket
1¢ on updown / 0.1¢ on dated ladders.

Kalshi maker column assumes the documented 0.25× multiplier (**conf B, not
verified against an observed fill**). Polymarket maker is **`?`** — see the
correction box above.

### Cost bars that actually matter

| strategy shape | Kalshi @50¢ | Polymarket @50¢ | ratio |
|---|---:|---:|---:|
| taker round trip (2 fees) | 3.50¢ | 3.50¢ | 1.00× |
| taker hold-to-settlement (1 fee) | 1.75¢ | 1.75¢ | 1.00× |
| maker round trip (2 fees) | 0.88¢ | **0¢** | **∞** |
| maker in / hold to settlement | 0.44¢ | **0¢** | **∞** |
| taker round trip @10¢ (tails) | 1.26¢ | 1.26¢ | 1.00× |
| maker round trip @10¢ | 0.32¢ | **0¢** | **∞** |

Plus Polymarket **rebates 15–25% of collected taker fees to makers daily** — a
maker can be *paid* to quote, which no cost table can express as a positive
number.

---

## 2. Everything else

| dimension | Kalshi | Polymarket | better |
|---|---|---|---|
| **taker fee** | 0.07·p·(1−p) | 0.07·p·(1−p) | **tie** |
| **maker fee** | ~0.25× taker | **0, plus rebate** | **Polymarket, decisively** |
| fee rounding | **UP to the cent, per order** (1-lot @50¢ pays 2.00¢, +14%; @5¢ pays 3× headline) | 5 dp, min 0.00001 USDC | **Polymarket** |
| min order size | fractional contracts (`*_fp` decimals) | **$5** | **Kalshi** |
| tick in the tails | 0.1¢ on `*15M`, **1¢ on the hourly ladders** | 1¢ on updown, **0.1¢ on ladders** | **mixed — see below** |
| shortest series | 15 min | **5 min** | Polymarket (more windows/day) |
| strike ladders | **80–188 legs**, fixed $250 grid, ±16% of spot | 11-leg dated ladders | **Kalshi, by far** |
| settlement source | **CF Benchmarks BRTI, 60-second average** (confirmed) | UMA oracle, feed **unconfirmed** | **Kalshi** |
| settled-record detail | `expiration_value` + `result` per market | resolution only | **Kalshi** |
| **historical order books** | none | **none** | tie (both nil) |
| historical fills | none | **2022-11-21 → 2026-04-28** on-chain, w/ `fee`/`maker`/`taker` | **Polymarket** |
| …but current fills | none | **~10-min rolling window** only | tie (both need recording) |
| settled market history | **deep** (400+ pages × 1000 per series) | settled markets **stop resolving** | **Kalshi, decisively** |
| live book depth | top-of-book via `/markets` | **113 levels** via `/book` | **Polymarket** |
| API filter reliability | good | **3 filters silently ignored** (`tag_slug`, `slug_contains`, repeated `slug`) | **Kalshi** |
| counterparty identity | none | **maker/taker wallet on every on-chain fill** | **Polymarket** |
| universe breadth | **272 crypto series** | ~7 assets × 3 horizons + ladders | **Kalshi** |

### The tick note

The 10× finer tick is on the **wrong series** on Kalshi: `tapered_deci_cent`
(0.1¢ in the tails) applies to the `*15M` series, which are minted at-the-money
and therefore rarely trade in the tails. The hourly ladders — which *do* live in
the tails and are where Family D would operate — are flat `linear_cent`. So on
Kalshi's tail contracts the minimum spread is a full cent, **comparable to the
entire fee at 10¢ (0.63¢) and larger than it at 5¢ (0.33¢)**.

Polymarket is the reverse: 1¢ on the up/down series, 0.1¢ on the dated ladders.

**For tail strategies specifically, Polymarket's ladders have the better tick and
the zero maker fee.** This is the strongest single argument in the comparison.

---

## 3. Verdict — is Polymarket structurally better for this?

**For a taker: no. They are the same venue with different labels.** Identical fee
function, identical rate, no material difference at any price point. Every prior
Kalshi taker negative result transfers to Polymarket unchanged, and there is no
reason to expect a different answer.

**For a maker: yes, decisively, and it is the only axis that differs.** Zero fee
versus ~0.44¢ at 50¢, plus a rebate that can make quoting net-positive before any
edge. Combined with a 0.1¢ tick on the ladders, the cost bar for a Polymarket
maker is *spread capture minus adverse selection* with **no fee term at all**.

**For research infrastructure: Kalshi, clearly.** Deep settled history with
`expiration_value`, a confirmed settlement source, 272 series, 80–188-leg
ladders, and reliable API filters. Polymarket's settled short-dated markets
vanish from its own metadata API, three of its filters lie, and its oracle is
unconfirmed.

**The synthesis that follows:** develop and validate on **Kalshi's** data because
that is where the history and the ground truth are, then run **maker** strategies
on **Polymarket** because that is where the cost bar is zero. Neither venue
supports a historical order-book backtest, so both require live recording, which
is now running.

### What would change this verdict

1. **The unresolved `1000` vs `0.07` fee discrepancy.** If Polymarket's crypto
   taker fee is really 10% and not 7%·p·(1−p), the taker comparison flips hard
   *against* Polymarket. This gates everything in §1 and is the top open item.
2. **Polymarket's oracle.** If it differs from CF Benchmarks, cross-venue gaps
   near a strike are a settlement risk, not an arbitrage.
3. **Kalshi's maker multiplier**, unverified against an observed fill.
