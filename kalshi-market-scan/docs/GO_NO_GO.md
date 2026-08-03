# GO / NO-GO

## The bar, defined before looking at results

| Criterion | Threshold |
|---|---|
| Minimum out-of-sample trades | **784** for a coinflip-adjacent market (power calc below) |
| Minimum fee-inclusive per-trade edge | CI excluding the **round-trip cost**, not zero |
| Consistency across two disjoint periods | Edge positive in both halves, same sign |
| Consistency across time-of-day buckets | Positive in ≥3 of 4 six-hour buckets |
| Calibration stability | Weighted mean absolute reliability gap < 0.03 in both halves |
| Depth at the touch | Median ≥ 50 contracts at the price we would cross |
| All Phase 4 leak tests | Passed, including the synthetic-noise control |
| Mechanism | One sentence on why the counterparty is wrong and why it persists |

### Power calculation

For a binary contract at price *p*, per-trade P&L has standard deviation √(p(1−p));
at the money that is 0.5. To detect a true 5-percentage-point edge at α = 0.05 with
80% power:

```
n = ((1.96 + 0.84) x 0.5 / 0.05)^2  =  784 trades
```

Measured on the real tennis tape the per-market P&L standard deviation is 0.391, so:

- detecting a **5pp** edge needs **481** settlements
- clearing the **2.4¢** tennis cost bar needs **2,084** settlements

This is the number that kills most of the exchange. Twenty-two `KXFED` settlements
cannot support any claim at all.

---

## What actually happened

| Criterion | Arb scanner | Weather ladders | `KXBTC15M` | Copy trading |
|---|---|---|---|---|
| Trades / settlements available | 144 scans, **0 violations** | ~5,200 per family | 6,262 | 264,074 positions |
| Edge CI excludes cost bar | no events | **not measured** (needs mid) | **no** | **yes**, +7.23pp CI [+4.61, +9.73] |
| Two disjoint periods consistent | n/a | not measured | n/a (no edge) | **yes**, rho 0.351 |
| Time-of-day consistency | n/a | not measured | n/a | not measured |
| Calibration gap < 0.03 | n/a | not measured | borderline (0.026–0.035) | n/a |
| Depth ≥ 50 at touch | **not measured** | **YES — 371–2,434 median, 7 families** | yes, 21,942 | n/a (Polymarket) |
| Leak tests passed | n/a | n/a | **yes** | partial |
| Mechanism | needs none | plausible | **none found** | **yes** — favourite-longshot bias |
| **VERDICT** | **NO-GO — no evidence yet** | **NO-GO — only the mid comparison left** | **NO-GO — refuted** | **NO-GO — Kalshi transfer refuted** |

### `KXBTC15M` — NO-GO, and the reason is structural rather than statistical

The contract is minted at-the-money every 15 minutes (strike = previous window's
settle, confirmed on 99.86% of 6,261 markets), pinning entry to the maximum of the
quadratic fee curve: a **3.50¢ round trip**. Every direction effect found is smaller
than that.

| Effect | Magnitude | Significance | vs 3.50pp bar |
|---|---|---|---|
| 5-min reversal | 1.43pp | z = −4.08 | dead |
| 15-min reversal | 1.86pp | z = −3.08 | dead |
| 60-min reversal | 2.11pp | z = −1.74 | dead |
| ETH→BTC lead | 0.037 vs 0.845 contemporaneous | — | no lead exists |

**Measured from live books, the bar is worse than 3.50¢: 4.1–4.5¢**, because the
1¢ spread adds to the fee. And depth at the touch collapses 40× toward expiry (158
contracts at 10–15 min to 4 contracts inside 5 min) exactly as the model sharpens
(Brier 0.224 at 780 s to 0.036 at 60 s) — so the edge and the liquidity are
anti-correlated, which is an independent reason to stop regardless of the fee argument.

No further BTC direction work is justified until someone finds an effect above 4.2
points. The vol work stands on its own merits and is reported, but volatility is not
tradeable on this contract without a hedging instrument we cannot use.

### Copy trading — CONDITIONAL GO, where the condition does the real work

The edge is real and persistent, but **it is not wallet skill** (see
`MORNING_REPORT.md` §7). Conditions:

1. ~~Verify that `won` reflects the wallet's realised outcome.~~ **Done during the
   session. It does not** — only 31.0% of positions are held to resolution and 36.0% hold
   both outcomes. But `won − entry` is still exactly the return to a
   **copy-and-hold-to-resolution** strategy, so the +7.23pp estimate stands for that
   strategy; it simply cannot be called a measure of the whale's skill. Survivorship from
   the 61% unredeemed "open" positions was also bounded and is negligible for tennis
   (0.2% of tennis capital, bound [+17.00%, +17.16%]).
2. ~~Establish that the bias exists on Kalshi, not only Polymarket.~~ **DONE — it does
   not.** 490,464 taker fills across 762 settled Kalshi sports matches: aggregate edge
   −0.67pp against a 2.72% overround, and pre-match prices calibrated bucket by bucket
   (0.846→0.846, 0.755→0.761; every binomial p ≥ 0.499). Polymarket's +8.57pp at 0.6–0.7
   becomes −2.12pp on Kalshi. **This breaks the Polymarket→Kalshi transfer the strategy
   depends on.** Caveat, and it survived a dedicated attempt to remove it: a properly
   targeted re-run over 12 series and 2,258 markets still yielded only 726 usable
   pre-match observations, with bucket CIs of ±11–29pp and 0 of 7 Polymarket values
   formally excluded. Sports simply are not traded much hours before the event, so
   historical mining cannot close this. Only forward recording can.
3. **Measure it at posted prices, not filled prices.** The tape records fills that
   happened; a strategy must trade against quotes that were actually available.
4. **Filter to `behaviour = 'directional'`.** 36% of positions are hedges, so a third of
   the apparent signal may be hedge legs rather than views.

Note also that `best.db`'s 159 wallets are **selected on past performance**, so its
+17.18% tennis return is circular and must not be quoted as an expectation. The only
clean out-of-sample figure is the +7.23pp from the unfiltered 38,117-wallet tape.

**Revised verdict: NO-GO.** Condition (2) was the binding one and it failed. The
favourite-longshot premium that explains the Polymarket result does not exist on Kalshi,
so ranking Polymarket wallets to trade Kalshi contracts has no established basis. What
remains is a power question — the pre-match sample cannot exclude a *small* bias — and
that is the one test worth running before changing anything.

### Weather — the closest thing to a live candidate

After the 09:00 UTC reopen, weather cleared two of the three gates:

- **Model:** persistence + hour-of-day, Brier 0.0579–0.0931 out-of-sample vs climatology
  0.1628–0.2942, all four cities surviving FDR
- **Capacity:** depth is real where it exists — 371–2,434 contracts on the daily `KXHIGH*`
  families, 2,972 on `KXTEMPDCH`
- **Recurrence, correctly counted:** a ladder is ONE temperature reading, not 10 markets.
  So the hourly families have 512 independent settlements (not 5,200) and the daily
  families only **66** (not 396).
- **Cross-tabbing the two bars kills 10 of 11 families.** The daily families have depth but
  only 66 settlements — below the 481 needed to detect a 5pp edge, so their depth is
  irrelevant. Three of four hourly families have settlements but 1 contract of depth.
  **`KXTEMPDCH` alone clears both, and by only 512 vs 481 on recurrence.**
- **Edge vs the mid: still unmeasured.** The deciding gate. Needs books across many more
  settlement cycles.

## Overall verdict

**NO-GO for deploying capital on anything tonight.** One conditional lead (copy trading,
with a load-bearing caveat), one family that cleared two of three gates and is worth the
wait (weather), and two clean negative results (`KXBTC15M` direction, economics on
recurrence).
