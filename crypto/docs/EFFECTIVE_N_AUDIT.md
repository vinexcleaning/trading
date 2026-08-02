# EFFECTIVE_N_AUDIT.md

Audit of every cross-asset / pooled claim under the independence finding
(**1.81 effective independent series out of 4**). Read against the actual
artifacts in `reports/`, not against session summaries.

Verdicts: **UNAFFECTED** / **WEAKENED** / **VOID** / **UNSUPPORTED**.

`UNSUPPORTED` is a category the brief did not anticipate and it was needed —
one claim circulating in the handoffs has no artifact behind it at all.

---

## Summary

| claim | artifact | verdict | note |
|---|---|---|---|
| lead-lag ETH→XRP +0.1544 | `leadlag.json` | **UNAFFECTED** | measures cross-asset correlation by design; the conclusion was economic, not statistical |
| **"MM scan: 0 of 4 series profitable"** | `mm_latency_fixed.json` | **UNSUPPORTED** | **only KXBTCD (58 markets) was ever P&L-tested** |
| cross-asset streaks (this session) | `streaks_multiasset.json` | **WEAKENED** (already stated) | 3-of-4 ≈ 1.8 observations; 0/136 survive FDR regardless |
| fat tails BTC + ETH (`C9`) | `fat_tails.json` | **UNAFFECTED** | already reported as one finding, not two |
| round-number pinning (`C8`) | `pinning_test.json` | **VOID** (already retracted) | invalid null + duplicated series |
| B1 vs-mid / touch matrix / path-streak | `b1_KXBTCD.json`, `path_streak.json` | **UNAFFECTED** | single-asset; effective-n applies between assets only |

---

## 1. Lead-lag ETH→XRP — UNAFFECTED

The independence finding says the four assets' **settlement signs** are
correlated (phi 0.59–0.70). The lead-lag test *measures* cross-asset correlation
— it is the object of study, not a confound. Correlated assets are the
precondition for the test, not a threat to it.

**One genuine caveat on the CI:** SE was taken as `1/√n`, which assumes
independent observations. One-second returns are mildly autocorrelated, so the
true SE is larger than reported. The effect was ~40 SE, so even a 10× understated
SE leaves it at ~4 SE.

**It does not matter, because the decision was economic, not statistical:**
0.38¢ of edge against a **1.00¢ minimum tick**, requiring a correlation of
0.575–1.113 against 0.1544 observed. Widening a confidence interval does not
lift a sub-tick signal above one tick. **Verdict unchanged: not tradeable.**

## 2. "MM scan: 0 of 4 series profitable" — UNSUPPORTED

**There is no artifact behind this claim.** `mm_latency_fixed.json` contains
`n_markets = 58` in every row and four rows — those four are **latencies**
(0/100/373/1000 ms), not four series. `data/mm/universe.json` scored 12 series,
but **scoring makeability is not a P&L test**.

**I wrote "0 of 4 series profitable" into `STATUS.md` myself.** It conflated the
four latency points with four series. Corrected statement:

> Market making was P&L-tested on **one** series, `KXBTCD`, **58 markets / 20
> events**, 25 May – 1 Aug 2026: **−1.86¢/contract, CI [−2.73, −1.53]**, losing
> at every latency from 0 ms to 1000 ms.

The *conclusion* (market making loses) is unchanged and rests on a real
artifact. Only the **breadth** claim was inflated. Three other crypto series and
the entire non-crypto exchange remain **untested for market-making
profitability**.

## 3. Cross-asset streaks — WEAKENED (already stated)

Reported with the effective-n caveat when first produced. 0 of 136 tests survive
BH-FDR regardless, so the weakening does not change any verdict.

## 4. Fat tails (`C9`) — UNAFFECTED

Reported as **one** finding, not two, at the time, on the grounds that
corr(BTC, ETH hourly returns) = 0.891 and 62% of extreme hours are shared. The
1.81 result corroborates that call.

## 5. Pinning (`C8`) — VOID (already retracted)

Retracted for an invalid null *and* for duplicate series (`KXBTC`/`KXBTCD` share
settlements exactly). The independence finding is a stronger form of the same
objection.

## 6. Single-asset claims — UNAFFECTED

`B1` vs-mid (250 events), the touch matrix (250 events), path/streak on
`KXBTC15M` (6,429 windows) are all within one series. Their unit is the event
and their CIs bootstrap events inside that series. A **between**-asset
correlation finding does not touch them.

---

## Rule adopted going forward

**Every cross-asset claim states nominal n and effective n.** Four crypto assets
agreeing ≈ **1.8 observations**. XRP carries more weight than its nominal share,
being least correlated with the rest — and it is the asset that fails to show
mean reversion.
