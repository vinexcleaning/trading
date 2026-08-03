# GO / NO-GO

> ## ⚠️ THIS FILE IS SHORTER AND MORE QUOTABLE THAN THE EVIDENCE BEHIND IT
>
> Four claims below were **retracted in [`../MORNING_REPORT.md`](../MORNING_REPORT.md)**
> and are marked inline where they appear. They are left in place, struck
> through, rather than deleted — deleting them is how they get re-derived.
> `MORNING_REPORT.md` is the corrected document; where the two disagree, it wins.
>
> | # | Claim as stated here | Status |
> |---|---|---|
> | 1 | depth at the touch collapses **40×** toward expiry, edge and liquidity anti-correlated | **RETRACTED** — one market, three minutes. Truth: 2.7×, and never thin |
> | 2 | ~5,200 settlements per weather family | **RETRACTED** — a ladder is one reading, not 10 markets. 512 hourly, 66 daily |
> | 3 | **seven** daily families clear the capacity bar | **RETRACTED framing** — they clear on depth but have 66 settlements, so depth is irrelevant |
> | 4 | Kalshi pre-match prices are calibrated **bucket by bucket** | **OVERSTATED** — failure to reject on n=19–52/bucket, CIs ±11–29pp |
>
> The **verdicts are unaffected** — every one of them was NO-GO already, and
> each still is on evidence that holds. What changed is the reasoning, and in
> two cases the direction of the argument.

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
| Trades / settlements available | 144 scans, **0 violations** | ~~~5,200 per family~~ **RETRACTED (2): 512 hourly / 66 daily** | 6,262 | 264,074 positions |
| Edge CI excludes cost bar | no events | **not measured** (needs mid) | **no** | **yes**, +7.23pp CI [+4.61, +9.73] |
| Two disjoint periods consistent | n/a | not measured | n/a (no edge) | **yes**, rho 0.351 |
| Time-of-day consistency | n/a | not measured | n/a | not measured |
| Calibration gap < 0.03 | n/a | not measured | borderline (0.026–0.035) | n/a |
| Depth ≥ 50 at touch | **not measured** | ~~**YES — 371–2,434 median, 7 families**~~ **RETRACTED framing (3)** — true on depth, but those 7 have 66 settlements each, so it decides nothing | yes, 21,942 | n/a (Polymarket) |
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
1¢ spread adds to the fee.

> ### ⚠️ RETRACTED (1) — the "40× depth collapse" was an artifact
>
> The sentence that stood here read: *"depth at the touch collapses 40× toward
> expiry (158 contracts at 10–15 min to 4 contracts inside 5 min) exactly as
> the model sharpens (Brier 0.224 at 780 s to 0.036 at 60 s) — so the edge and
> the liquidity are anti-correlated, which is an independent reason to stop
> regardless of the fee argument."*
>
> **It was measured from one market over three minutes.** Re-measured on 25
> markets over seven hours (`MORNING_REPORT.md` §7g), the truth is close to
> the opposite:
>
> | Time to expiry | Median spread | Median touch depth | Total breakeven |
> |---|---|---|---|
> | 10–15 min | 1.0¢ | **821** | 4.46¢ |
> | 5–10 min | 1.0¢ | **574** | 4.49¢ |
> | 2–5 min | 0.3¢ | **373** | 3.58¢ |
> | 60–120 s | 0.1¢ | **193** | 3.36¢ |
> | 0–60 s | 0.1¢ | **307** | **3.50¢** |
>
> Depth declines **2.7×, not 40×**, and never becomes thin — **307** contracts
> at the touch inside the final minute, not 4. The spread *tightens* 10×, from
> 1.0¢ to 0.1¢. So the total cost of trading **falls** toward expiry, 4.46¢ →
> 3.50¢: the contract is **cheaper** to trade late, not more expensive.
>
> The "anti-correlated edge and liquidity" argument is therefore **withdrawn
> entirely**. The NO-GO verdict is unchanged but no longer rests on it — it
> rests on the at-the-money fee structure, the direction effects below the
> bar, and the vs-mid null.

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
   −0.67pp against a 2.72% overround. Polymarket's +8.57pp at 0.6–0.7 becomes −2.12pp on
   Kalshi. **This breaks the Polymarket→Kalshi transfer the strategy depends on.**

   > **⚠️ OVERSTATED (4) — "calibrated bucket by bucket" is not established.**
   > The struck phrase was: *"and pre-match prices calibrated bucket by bucket
   > (0.846→0.846, 0.755→0.761; every binomial p ≥ 0.499)"*. Those buckets hold
   > **n = 19, 28, 46 and 52** markets. "Every binomial p ≥ 0.499" is a **failure
   > to reject**, not a demonstration of calibration — at that n the test cannot
   > reject anything, and a high p-value on a tiny sample is the weakest possible
   > evidence. The properly targeted re-run over 12 series and 2,258 markets
   > yielded only **726 usable pre-match observations**, with bucket CIs of
   > **±11–29pp** and **0 of 7 Polymarket values formally excluded** — i.e. the
   > Polymarket effect sizes sit *inside* the Kalshi confidence intervals. The
   > correct statement is that Kalshi shows **no detectable** favourite-longshot
   > bias at this sample size, which is not the same as being calibrated. The
   > aggregate −0.67pp on 762 matches is the part that carries weight.
   >
   > This does not rescue the strategy: the transfer needed a *positive* Kalshi
   > bias and there is no evidence of one. But the file must not be quoted as
   > having proven Kalshi calibrated.

   Sports simply are not traded much hours before the event, so historical mining
   cannot close this. Only forward recording can.
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
