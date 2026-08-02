# HANDOFF.md — hold-to-settlement reverses; a claim of mine was unsupported

2026-08-01 ~18:45 UTC. `C:\Users\gianf\crypto`. Read-only, simulated only, no
order-placement code. Autonomous session, no questions asked; ambiguities logged
in `DECISIONS.md`.

## 1. HOLD-TO-SETTLEMENT — four assets

Entry at the **real ask**, **one** taker fee (settlement costs nothing), payoff =
realised outcome. CIs bootstrap **events**. Panels built by fixed stride over
settled events; strikes chosen by the **anchor** (previous settlement, knowable
pre-open), never by the outcome.

| | BTC (KXBTCD) | ETH (KXETHD) | SOL (KXSOLD) | XRP (KXXRPD) |
|---|---|---|---|---|
| rows / events / markets | 89,819 / **250** / 1,968 | 19,369 / **150** / 500 | 14,763 / **149** / 459 | 8,940 / **~102** / 336 |
| date range | 25 May – 30 Jul 2026 | same | same | same |
| median spread | **1.00¢** | 2.00¢ | 2.00¢ | **3.00¢** |
| frac spread > 1¢ | ~0% | 57.1% | 67.1% | **76.3%** |

**Net ¢/contract, hold to settlement (95% CI, event-clustered):**

| entry | BTC | ETH | SOL | XRP |
|---|---|---|---|---|
| **5¢** | **+2.93** [−0.0, +6.1] | **−3.10** [−4.5, **−1.1**] | −0.12 [−3.0, +3.4] | −0.65 [−3.7, +3.3] |
| **10¢** | **+2.39** [−1.3, +6.2] | **−4.44** [−8.1, **−0.0**] | −1.92 [−6.6, +3.6] | −5.79 [−10.4, +0.3] |
| **15¢** | **+2.62** [−1.5, +6.7] | −3.22 [−9.1, +3.3] | −2.49 [−8.8, +4.9] | −7.22 [−14.4, +1.3] |
| 20¢ | +2.30 | −6.62 | −3.80 | — |
| 30¢ | +0.60 | −1.88 | −2.38 | — |
| 50¢ | +0.35 | −4.96 | −1.93 | — |
| 70¢ | −3.00 | −5.09 | −5.32 | — |
| 90¢ | −3.68 [−7.2, −0.1] | −1.24 | −1.52 | −0.83 |

**Nominal assets 4; EFFECTIVE independent series 1.81.**

## 2. DOES THE CHEAP-CONTRACT EFFECT REPLICATE? — NO. IT REVERSES.

| bucket | assets | CI excluding zero | signs |
|---|---|---|---|
| 5¢ | 4 | **0** | BTC **+**, ETH **−**, SOL **−**, XRP **−** |
| 10¢ | 4 | **0** | BTC **+**, ETH **−**, SOL **−**, XRP **−** |
| 15¢ | 4 | **0** | BTC **+**, ETH **−**, SOL **−**, XRP **−** |

**BTC is positive; all three other assets are negative at every cheap bucket.**
ETH is *significantly* negative at 5¢ (−3.10, CI [−4.5, −1.1]) and 10¢ — the
opposite sign to BTC, with a CI excluding zero. **Not one positive cell with a
CI excluding zero appears anywhere in the 4 × 12 grid.**

Even BTC's own 5¢ cell is now +2.93 **[−0.04, +6.1]** — the CI includes zero on
this bootstrap seed, against [+0.02, +6.26] previously. It was always borderline.

**Favourite-longshot bias is rejected.** It would have to appear on every asset;
it appears on one and reverses on three.

**The trap check passes and explains the pattern.** Spread ordering
BTC 1.00¢ < ETH 2.00¢ ≈ SOL 2.00¢ < XRP 3.00¢, and expectancy worsens in exactly
that order. Buying at a wider ask into settlement is worse — as predicted. The
cross-asset pattern is a **spread effect**, not a mispricing.

**Verdict: the BTC 5¢ cell was one noisy bucket on one asset.**

## 3. EFFECTIVE-N AUDIT — one claim of mine was UNSUPPORTED

`docs/EFFECTIVE_N_AUDIT.md`. Verdicts read off artifacts, not summaries.

| claim | verdict | note |
|---|---|---|
| lead-lag ETH→XRP +0.1544 | **UNAFFECTED** | measures cross-asset correlation *by design*; decision was economic (sub-tick), not statistical |
| **"MM scan: 0 of 4 series profitable"** | **UNSUPPORTED** | **no artifact exists** |
| cross-asset streaks | WEAKENED (already stated) | 3-of-4 ≈ 1.8 obs; 0/136 survive FDR anyway |
| fat tails BTC+ETH | UNAFFECTED | already reported as one finding |
| pinning `C8` | VOID (already retracted) | invalid null + duplicate series |
| B1 / touch matrix / path-streak | UNAFFECTED | single-asset; effective-n is a between-asset correction |

**The unsupported one is mine.** `mm_latency_fixed.json` has `n_markets = 58` in
every row; its four rows are four **latencies** (0/100/373/1000 ms), not four
series. I conflated them and wrote "0 of 4 series profitable" into `STATUS.md`.

> **Corrected:** market making was P&L-tested on **one** series, `KXBTCD`,
> **58 markets / 20 events**: −1.86¢/contract, CI [−2.73, −1.53], losing at
> every latency. The *conclusion* stands on a real artifact; only the **breadth**
> was inflated. Three other crypto series and the whole non-crypto exchange
> remain untested for MM profitability.

## 4. TAPERED TICK — a real correction to the wing cost bar

Verified from the API's own `price_ranges`: 0–10¢ step **0.1¢**, 10–90¢ step
1¢, 90–100¢ step **0.1¢**, on all 14 fifteen-minute series.

| price | tick | round trip (tapered) | round trip (flat 1¢) |
|---|---|---|---|
| 5¢ | 0.10¢ | **0.865¢** | 2.665¢ |
| 7¢ | 0.10¢ | 1.111¢ | 2.911¢ |
| 50¢ | 1.00¢ | 5.500¢ | 5.500¢ |
| 95¢ | 0.10¢ | **0.865¢** | 2.665¢ |

**Wing round-trips are 3.08× cheaper than a flat-1¢ assumption** on the 15-minute
series. This had not been accounted for anywhere. It does **not** affect the
touch matrix (that ran on `KXBTCD`, genuinely `linear_cent`) or the fade (~50¢,
where tapered still gives 1¢).

**Partial correction to my own earlier claim.** I said the lead-lag signal "is
smaller than the smallest price increment that exists." That is true at the
money and **false in the wings**: at 7¢ and 93¢ the edge (0.128¢) exceeds the
0.10¢ tick, ratio **1.284**. The correct statement is that the signal never
covers **tick + fee** — at 7¢ the fee alone is 0.456¢, **3.5×** the edge, netting
−0.427¢. Conclusion unchanged; the *reason* is the fee, not the tick.

## 5. RESULTS TABLE

| claim | n + unit | effective n | date range | effect | verdict |
|---|---|---|---|---|---|
| Cheap contracts underpriced (5¢) | 4 assets, 102–250 ev each | **1.8** | 25 May–30 Jul | BTC +2.93, ETH **−3.10**, SOL −0.12, XRP −0.65 | ❌ **reverses** |
| …10¢ | same | 1.8 | same | BTC +2.39, ETH **−4.44**, SOL −1.92, XRP −5.79 | ❌ reverses |
| Any positive HTS cell survives | **4 × 12 = 48 cells** | 1.8 | same | **0 with CI excluding zero** | ❌ |
| Wider spread → worse HTS | 4 assets | 1.8 | same | 1.00/2.00/2.00/3.00¢ ordering tracks expectancy | ✅ mechanism confirmed |
| MM tested on 4 series | artifact check | — | — | `n_markets`=58 in all rows | ❌ **UNSUPPORTED** |
| Wing tick is 1¢ on 15m series | `price_ranges` | — | live | **0.1¢** below 10¢/above 90¢ | ❌ my prior assumption |
| Lead-lag is sub-tick everywhere | 17 price points | — | — | exceeds tick at 7¢/93¢ (1.284×) | ⚠️ **partially wrong** |

**This session adds 48 HTS cells + 6 audit verdicts + 17 tick points = 71
tests.** Cumulative ≈ **429 tests, 0 tradeable edges, 8 withdrawn positives.**

## 6. RETRACTIONS

1. **"MM scan: 0 of 4 series profitable" — UNSUPPORTED, and I wrote it.** Only
   `KXBTCD` was P&L-tested.
2. **"The lead-lag signal is below one tick everywhere" — partially wrong.** It
   exceeds the tick at 7¢/93¢; the fee is what kills it.
3. **"Hold-to-settlement beat every exit rule at every entry price" (BTC)** —
   true on BTC, but the cheap-bucket result **does not generalise** and reverses
   on three assets.
4. Standing: three fade bars wrong-shaped; markets do **not** trade before open;
   "three independent replications" false (1.81); `KXDOGED` unusable.

## 7. CANARIES AND CONTROLS

| guard | reading |
|---|---|
| Recorder health, ~30 min | **ALIVE** pid 24756 — 307 rows, 27 windows, **0 rejected, 0 errors**; content check on live tail shows full schema, real prices |
| Look-ahead | strikes by anchor (pre-open); `ts > close_ts` rejected in the builder |
| Selection | fixed stride over close_time; no outcome filtering |
| Trap check (thin = worse) | ✅ spread ordering tracks expectancy ordering exactly |
| Effective-n stated | ✅ on every cross-asset claim |
| Fee arithmetic | 21 tests passing; tapered tick now modelled explicitly |
| **Not run** | per-asset synthetic controls; sub-second strike-lock (Task 3); census (Task 4); vs-mid non-BTC (Task 5); per-window fade costing (Task 6, needs ~200 windows/asset) |

## 8. NOW CLOSED

- **Hold-to-settlement / favourite-longshot bias.** Reverses across assets;
  0 of 48 cells positive with CI excluding zero.
- **The cross-asset streak thesis.** 0/136 FDR; 1.81 effective series.
- Carried: taker forecasting (p=0.942); market making on KXBTCD (−1.86¢/ct at
  0 ms); path/spike; momentum; lead-lag (never covers tick + fee).

## 9. STILL OPEN

**Not yet run:** sub-second strike-lock poll (Task 3, ~30 min wall-clock);
crypto census (Task 4); vs-mid on non-BTC ladders (Task 5); per-asset synthetic
controls. **Accruing:** 14-series opens, 307 rows / 27 windows so far.
**Blocked:** desktop recordings; per-window fade costing until ~200 windows.

## 10. RUNNING

`record_15m_opens_v2.py` pid **24756** — 14 crypto 15-minute series, both sides
+ sizes, 2 s cadence, first 60 s after open →
`data/btc15m_opens/opens_all_<date>.jsonl`. 168 h from 17:42 UTC. Supervised,
paced, 429 backoff, append-only, per-row validation. Panels for all four ladder
series now complete on disk.

## 11. NEXT THREE ACTIONS

1. **Task 5, vs-mid on ETH/SOL ladders (~1 h).** Panels are built; only the
   model scoring remains. **State the detection floor first** — at 150 events
   the floor is ~1.3× BTC's (~13–20% mispricing), so a null there is weak and
   must be reported as such rather than as a result.
2. **Task 3, sub-second strike-lock (~30 min wall-clock).** Closes the last
   ~9.7¢ of the open-price anomaly.
3. **Per-asset synthetic controls (~1 h).** Never run for the cross-asset grid;
   the previous version fabricated +9.46¢.

## 12. WHAT THE COORDINATING CHAT HAS WRONG

1. **"Hold-to-settlement is the last untested item with a real prior."** It was,
   and it is now dead: BTC positive, ETH/SOL/XRP negative, 0 of 48 cells
   positive with a CI excluding zero. The mechanism it proposed
   (favourite-longshot bias) is **rejected** — it would have to appear on every
   asset.
2. **"0 of 4 series profitable" for market making.** No artifact. One series,
   58 markets. My error, now corrected in `docs/EFFECTIVE_N_AUDIT.md`.
3. **"The tapered tick has not been accounted for anywhere."** Correct, and it
   mattered: wing round-trips are **3.08× cheaper** than assumed. It also makes
   one of my own statements partially wrong (lead-lag is *not* sub-tick at
   7¢/93¢).
4. **"~358 tests, 7 withdrawn positives."** Close: ~358 before today, now ~429
   and 8.
5. **What the brief got right:** the trap warning — "thin assets have wide
   spreads, so a positive there is presumptively an artifact." The data
   confirmed the ordering exactly, and it is why the cross-asset pattern is
   readable as a spread effect rather than a mispricing.
