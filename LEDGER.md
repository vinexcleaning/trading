# LEDGER.md — every claim ever made across all trading projects

Built 2026-08-02 by inventory. **Nothing here was recomputed.** Every row was
read off an artifact on disk, a git log, or a project document. Where a document
asserts a number and no artifact backs it, the row says `NONE` and the status is
`UNVERIFIED` — regardless of how confident the prose was.

## Status key

| Status | Meaning |
|---|---|
| **SETTLED** | Reproducible artifact, adequate n, validated out of sample (or true by arithmetic / API fact). Safe to build on. |
| **SUGGESTIVE** | Real artifact, but underpowered, no CI, or never validated out of sample. Directional only. |
| **UNVERIFIED** | Asserted somewhere, no artifact findable. Machinery may exist; it was never run at real n. |
| **BROKEN** | Artifact exists but carries a defect that invalidates the number. |
| **RETRACTED** | Stated confidently, corrected later. **Read these first.** |

## Tally

| Status | Count |
|---|---|
| **RETRACTED** | **51** |
| SETTLED | 175 |
| SUGGESTIVE | 36 |
| UNVERIFIED | 30 |
| BROKEN | 11 |
| CANCELLED | 1 |
| **Total** | **304** |

**Updated 2026-08-06 (second entry)**: **+43 rows** from the full-programme
audit — **Section 8**, which merges `market-selection`'s 29 rows (they sat in an
unmerged `LEDGER_ADDITIONS.md` for four days, invisible to every cross-check) and
adds `bot-hunt`'s 14. **It paid immediately, for the third time out of three:**
**[M011](#m011)** is a **SUGGESTIVE** row on **13 games against a retail book**
that is quoted as established fact in **eight** places, including as the
justification for making MLB a negative control and as one of "four independent
measurements" in a pre-registration written the same morning; and **M001** — the
retraction of *"Kalshi order-book depth is not public"* — is **still stated as a
live blocker in `crypto/MM_RESULTS.md`**, which is part of why the crypto
market-making thread stalled. Depth is public, free, 20 levels a side, re-verified
live on 2026-08-06.

**Updated 2026-08-03**: +16 rows from **Section 6 — kalshi-market-scan**, which
had no rows in this ledger until then. Three of its retractions (K003, K005,
K006) and one overstatement (K010) were live in `docs/GO_NO_GO.md` and
`docs/shortlist.md` and were invisible to any ledger-based check.

**Updated 2026-08-05**: +21 rows from **Section 7 — bot-forensics**, which also
had no rows here until now, and which is the project whose conclusions are most
likely to be acted on because it is the only one about **money that actually
moved**. Ledgering it immediately corrected **two stale rows in Section 5**
(CH031 gained a magnitude after months without one; CH044 said *"never
diagnosed, never fixed"* and was wrong on both counts) and surfaced **B005a**, a
reporting selection in which three of that project's own documents state "0 of
13" while its own committed output prints "3" from a different, broken arm.

**Updated 2026-08-06**: +7 rows (**B021–B027**), tally 254 → **261**. The ITF
question is **settled affirmatively** — a free source exists and the thread was
closed on a false premise (B021) — and the user's player-feature hypothesis was
tested over **2,008 pre-registered cells** and returned a clean null (B023).
B016 moves UNVERIFIED → SETTLED. **RETRACTED still 45.**

> **The ninth apparent positive died, and the directional prior held for the
> 46th time.** "Buy the heavy favourite" showed +4.31pp on train and kept its
> sign on holdout — then turned out to be **monotonic in spread width and absent
> on tradeable books** (B024). Two bugs in this session's own code (B025) both
> pushed toward a false positive and were caught before publication.

> **RETRACTED stays at 45 — no B-row is itself a retraction — but the
> directional prior held again.** Every correction bot-forensics produced shrank
> the apparent edge: **B002** moved $99 of gains from the bot to the hand,
> **B019** removed a $14.51 winner that a bad classifier had credited to the bot
> (roughly half its apparent total), and **B003** dissolved the profitable night
> into the argmax of its own equity curve. **Still not one correction anywhere in
> this repo has ever revealed a larger effect.**

## The directional prior, and it is the single most informative number here

**Across all projects, 45 corrections. Every one shrank the edge. Not one ever
revealed a larger effect.** set1_overshoot logged this explicitly at 28 and
crypto at 25 within their own scopes. That asymmetry is what no-edge looks like
from the inside; a real edge survives scrutiny and often grows under it.

> This sentence read "~41" until 2026-08-03 and was stale by four. **The Tally
> table above is the source of truth** — quote the `RETRACTED` row, not this
> prose, and update both together. `CLAUDE.md` §6 points here for exactly this
> reason.

## ⚠ RETRACTED — loudly, first

These were stated as findings and are wrong. Anything built on them is void.

| ID | Retracted claim | Project | Why it died |
|---|---|---|---|
| **S011** | Set-1 undershoot −2.53pp, p=0.0007, and everything in Phases 2–5 built on it | set1_overshoot | Dedupe kept the higher-`volume_fp` side. P(kept side wins) = **0.5356, z=+10.0**. The two orientations disagreed by **25.5pp**. Voided Phases 2, 3, 4 and the 90¢+ result in one stroke. |
| **S003** | Label-verified subsample −5.75pp [−9.71,−1.79], p=0.0062 | set1_overshoot | 1.9× its own mechanism ceiling; decays **+3.365¢ → +0.311¢** on holdout; join canary **UNTESTABLE** (z=+2.15). Presumed artifact. |
| **S012** | "ATP is the thinnest book — median 30 lots, 3¢ spread" | set1_overshoot | A single 68-minute window at market open. Full day: **1.0¢ spread, 312 lots**. |
| **S013** | "Median 106 contracts at the touch" | set1_overshoot | Same 68-minute artifact. Full day: **564**. |
| **C003** | Round-number settlement pinning, 6/20 survive BH at p≈0 | crypto | Three disqualifiers: effects run the **wrong way** (repulsion, not attraction); the uniform null is invalid at exactly the levels that "worked" (BTC spans ~4 periods of 5000); and **10 of 20 tests were duplicate series** (KXBTC/KXBTCD share settlements). |
| **C006** | Fat-tail edge worth 1.5–1.9¢ net at 2.5–3σ | crypto | Benchmarked against a **Gaussian strawman**, not Kalshi's mid. Later retired on evidence: M3 fat-tail model *loses* to the mid (+0.003703, CI excludes zero). |
| **C013** | Mid calibration gap +4.2pp, net +1.00¢ at the ask | crypto | No event clustering. CIs widen **~10×**; 14 of 17 buckets go to zero; best p=0.029 vs BH threshold 0.0059; magnitudes halve between disjoint halves; **opposite sign at n=13**. |
| **C014** | 464 profitable bucket-sum arbitrage violations at 96–97¢ | crypto | Forward-filled partial ladder — 3 of 80 buckets. Buying 3 buckets pays $1 only if the outcome lands in those 3. All 464 vanished on the fix. |
| **C015** | Polymarket taker cost is identical to Kalshi | crypto | Trusted docs over the venue's own API. On-chain says **2.86× Kalshi at 50¢**. |
| **W006** | **"72% of the edge lives in exits"** | wallet-copy-study | A **fee artifact**. `gap` compared a *gross* wallet edge against a *net* copier return; ~80% of positions settle so the whole gap is the fee. Genuine exit component: **−0.106pp = −4.3%**, not +72%. Named the highest-value follow-up in the original verdict — it was a mirage. |
| **W011** | Prior study's naive favourite benchmark +7.05pp on n=98,766 | wallet-copy-study | Unauditable (no dataset found anywhere on disk); recomputed from scratch at **+2.09pp, CI [−1.37,+5.35]**, and **−0.29pp net**. Almost certainly a trade-clustered interval on a market-clustered phenomenon. |
| **W012** | Copying selected wallets loses −5.90pp | wallet-copy-study | Measured on a 140-market overlap. Re-measured on the full wallet panel (31,703 wallet-markets): **+0.937pp**. The wide interval was the warning. |
| **W015** | Polymarket fee formula fits at median relative error 0.96 | wallet-copy-study | Inverted maker side. Corrected: **100.0% of 5,362 fills within 1%**. |
| **W016** | `enable_order_book` is a valid eligibility criterion | wallet-copy-study | Returns *current* tradability — false for essentially every resolved market. Gave **0 eligible of 2,108,796**. |
| **T008** | Stage 5 selective betting returns **+14.4% to +24.6% ROI** | kalshi-tennis | Priced at the mid. Re-priced at executable fills (buy YES lifts the **ask**; buy NO costs **1−bid**): **−24.3% to −30.9%**, every CI entirely below zero. Mean entry moved 27–32¢. |
| **T010** | Kalshi beats the Betfair closing line by 0.022 Brier | kalshi-tennis | **Look-ahead leak.** `occurrence_datetime` is at/after match end; 4.1% of quotes sat outside 2c–98c and were **100% correct**. At a clean −6h anchor the advantage vanishes (+0.00122). |
| **T007** | Market beats model once wide quotes are excluded (+0.03711) | kalshi-tennis | The spread filter **read the leaking anchor**. Feature leak *and* a selection leak. The *direction* is separately confirmed by T012; this particular number is void. |
| **T017** | Stage 0 coverage is 74.5%; there is no ITF tier on Kalshi | kalshi-tennis | Hand-written regex missed "ITF Men's Match". ITF is **31,894 markets ≈ 76% of Kalshi's tennis book**. Corrected coverage **36.9%**. Caught by the user from their own fill history. |
| CH001–CH020 | 20 further retractions from the chat archive | various | Full detail in [kalshi-chat-audit/LEDGER_CHATS.md](kalshi-chat-audit/LEDGER_CHATS.md). Carried below. |
| **K006** | **Depth at the touch collapses 40× toward expiry**, so edge and liquidity are anti-correlated | kalshi-market-scan | Measured from **one market over three minutes**. On 25 markets: depth falls **2.7×** and never goes thin (**307** contracts in the final minute, not 4), the spread *tightens* 10×, and total cost **falls** 4.46¢→3.50¢. The argument is withdrawn entirely. |
| **K003** | The weather model was validated on **8,090 test markets** | kalshi-market-scan | A ladder is **one** temperature reading, not 10 markets. Effective n ≈ **800 settlement hours**; the CIs were ~**3× too tight**. The model itself survives re-scoring. |
| **K005** | "**Seven daily families clear the capacity bar**, so weather is not capacity-limited" | kalshi-market-scan | Depth right, inference wrong. All seven have **66** settlements against the **481** needed, so their depth decides nothing. Cross-tabbing both bars kills **10 of 11** families. |
| **K015** | "Buying everything priced 0.60–0.95 earns **+7.05pp ± 0.22** on n=98,766" — named the finding that reframes the whole copy-trading block | kalshi-market-scan | **Is the same claim as W011**, which had already recomputed it from scratch at **+2.09pp [−1.37,+5.35] gross, −0.29pp net**. Two projects, two rows, two different statuses, one dead number. See "the duplicate-claim trap" in Section 6. |

---

# SECTION 1 — set1_overshoot (Kalshi tennis, in-play set-1 study)

Artifacts: `C:\Users\gianf\kalshi\set1_overshoot\` (original, **recorder live**) and
`trading/set1_overshoot/` (code copy). Full 97-hypothesis grid with BH-FDR:
`reports/hypothesis_ledger.csv`.

Unit of observation is **the match**. Kalshi data **2026-05-25 → 2026-08-01**,
19,782 matches, 5 series.

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| S001 | The market **undershoots** after a set-1 dip — it does not overshoot. The effect is real. | set1_overshoot | `src/p2_calib.py` → `reports/p2_base.txt`, `hypothesis_ledger.csv#2` | 3,436 matches | 05-25→08-01 | −2.4153pp [−3.90,−0.93], p=0.0019 | **yes** (BH q=0.1, thr 0.0374) | train −2.51 / holdout −2.27, p=0.062 — **decays below significance** | **SETTLED** (effect) |
| S002 | The **pre-committed primary** entry rule (`deep:12`) shows no effect at all. | set1_overshoot | same, `hypothesis_ledger.csv#1` | 5,390 matches | 05-25→08-01 | −0.84pp [−2.10,+0.42], p=0.2058 | no | — | **SETTLED** (null) |
| S003 | Fixing the labels rescues the trade: −5.75pp on the label-verified subsample. | set1_overshoot | `reports/p6_task2_margin.md`, `ledger#85` | 479 matches | 05-25→07-26 | −5.75pp [−9.71,−1.79], p=0.0067 | yes | **NO — +3.365¢ → +0.311¢** | **RETRACTED** |
| S004 | The cost bar to beat is **3.6104pp** = 1.170 spread + 1.000 slip + 1.441 fee. | set1_overshoot | `src/fees.py` (exact `Decimal`) → `reports/audit_rerun.txt` | 3,436 matches | 05-25→08-01 | 3.6104pp, recomputed from data every run | n/a | n/a | **SETTLED** |
| S005 | **No time or tier bucket clears the bar.** 0 of 25. | set1_overshoot | `src/p5_segment.py` → `reports/p5_segment_time.md`, `ledger#59–84` | 25 buckets / 3,436 matches | 05-25→08-01 | 0 of 25 clear; median MDE 3.7–9.0¢ vs ~2¢ target | 4 nominal survive BH, none clears the cost bar | — | **SETTLED** (null) |
| S006 | **No set-1 margin bucket clears the bar.** 0 of 10 (0.25 expected by chance). | set1_overshoot | `src/p6_margin.py` → `reports/p6_task2_margin.md`, `ledger#85–96` | 10 buckets / 479 matches | 05-25→07-26 | 0 of 10; median MDE **9.9¢** vs ~2¢ target | 6 nominal survive BH, none clears the bar | no bucket qualified | **SETTLED** (null) |
| S007 | Effect strengthens monotonically as set 1 gets shorter/more lopsided (10.86→5.58→2.77pp; 8.15→4.12→1.84pp). | set1_overshoot | `reports/p6_task2_margin.md` | 99–223 matches/cell | 05-25→07-26 | monotone gradient, every cell inside its noise band | — | untested | **SUGGESTIVE** |
| S008 | **Maker/resting orders do not fix it.** All 15 fill configurations are net-negative per opportunity. | set1_overshoot | `src/p5_maker.py` → `reports/p5_task1b.md`, `ledger#40–54` | 1,889–3,029 opportunities | 05-25→08-01 | net −0.205¢ to −1.220¢; fill rates 0.550–0.882 | n/a (no positive to correct) | — | **SETTLED** |
| S009 | Maker price improvement is already exceeded by adverse selection. | set1_overshoot | `src/p5_maker.py` → `reports/p5_task1b.md` | per-opportunity decomposition | 05-25→08-01 | adverse selection > price improvement at every window | — | — | **SETTLED** |
| S010 | Maker fee is **zero on Challenger/ITF (91% of the book)**, applies only on ATP/WTA. | set1_overshoot | resolved empirically from series `fee_type`; git `0c96a40` | full series list | 2026-08 | structural fact | n/a | n/a | **SETTLED** |
| S011 | Set-1 undershoot −2.53pp p=0.0007 (**the original Phase 2 headline**). | set1_overshoot | `SELECTION_AUDIT.md` row 1; `reports/p5_dedupe_bias.txt` | 19,782 matches | 05-25→07-xx | **VOID** — orientations disagree by 25.5pp | — | — | **RETRACTED** |
| S012 | ATP is the thinnest book (30 lots, 3¢ spread). | set1_overshoot | `reports/p6_queue_atp.md` | 1,857 → 22,395 snapshots | 08-01 | full day: **1.0¢ / 312 lots** | — | — | **RETRACTED** |
| S013 | Median 106 contracts at the touch. | set1_overshoot | `reports/depth_analysis.md` | 64,898 snapshots | 08-01 06:58–18:15 | full day median **564** lots | — | — | **RETRACTED** |
| S014 | The set-1 detector calls direction correctly 82.5% of the time. | set1_overshoot | `src/p0_scores.py` → `PHASE1_DETECTOR_ACCURACY.md` | 2,787 external scorelines | 05-25→07-26 | 0.825 accuracy, validated against **external** labels not outcomes | n/a | n/a | **SETTLED** |
| S015 | `t0` (set-1 end) is estimated +5 min median, MAD 6, against real playing minutes. | set1_overshoot | `src/p1_state.py` → `reports/p1_t0_tuning.csv` | tuned vs Sackmann durations | — | +5 min, MAD 6 | n/a | n/a | **SETTLED** |
| S016 | Mirrored Kalshi markets are exact inverses (median mid difference 0.00¢). | set1_overshoot | `src/p0_mirror.py` → `reports/p0_mirror.txt` | sampled markets | 05-25→08-01 | median 0.00¢ | n/a | n/a | **SETTLED** |
| S017 | The P&L decomposition is an exact identity. | set1_overshoot | `src/p5_maker.py` → `reports/p5_task1b.md` | per-opportunity | — | **+0.0000¢** residual | n/a | n/a | **SETTLED** |
| S018 | Label coverage cannot be raised. Apify hard-capped; Flashscore `dayOffsets` is −7..+7 against a −68 need. | set1_overshoot | Apify error payload; actor schema | — | 08-01 | structural blocker; true cost ~$20 not $3.44 | n/a | n/a | **SETTLED** |
| S019 | Trade-through is not a generous fill assumption — best bid rises in only 6.1% of minutes. | set1_overshoot | `reports/depth_analysis.md` | 150 markets | 08-01 | median 6.1% of minutes | n/a | n/a | **SETTLED** |
| S020 | 15 headline numbers recomputed independently; **14 confirmed**, 1 baseline updated. | set1_overshoot | `src/audit_final.py` → `reports/audit_final_stdout.txt`, `AUDIT_FINAL.md` | 15 numbers | 08-01 | 14/15 CONFIRMED | n/a | n/a | **SETTLED** |
| S021 | The tennis strategy line cannot be resolved with the sample available. | set1_overshoot | power calc in `HANDOFF.md` §9 | 3,436 events, sd 45¢ | — | needs n≈3,970 for a 2¢ edge; accrues ~1,900 matches/week | n/a | n/a | **SETTLED** |
| S022 | Retirement add-back costs −0.004¢. | set1_overshoot | `reports/p2_scalar.txt` | scalar settlements | 05-25→07-xx | −0.004¢ | — | — | **BROKEN** (computed on the void event set; needs re-run) |
| S023 | The fade side loses in all 6 configurations. | set1_overshoot | `reports/p2_fade.md` | 6 configs | 05-25→07-xx | all negative | — | — | **BROKEN** (edge term void; cost arithmetic likely carries the conclusion — needs re-run) |
| S025 | **The two maker-fee tennis series hold 34.4% of tennis volume on 5.8% of the markets** — 5.9× concentration. S010's "91% of the book" is a *count*; by volume the taker-only series are 65.6%. | set1_overshoot | `common/measure_tennis_maker_liquidity.py` → `common/TENNIS_MAKER_LIQUIDITY.md` | 42 series, 66,694 markets, 9.63bn volume | 2026-08-03 | maker-fee 3,864 mkts / 3.31bn vol; taker-only 62,830 / 6.32bn. `KXATPMATCH` alone is **21.9%** of volume | n/a | n/a | **SETTLED** (structural fact from the API) — answers the question `signal-github` `e3b87d7` left open. Does **not** revive the maker case: S008/S009 and the 08-03 `high_sweep` re-run all stand |
| S024 | `plausible` duration filter (25–330 min) is immaterial to θ. | set1_overshoot | `src/audit_plausible.py` → `reports/audit_plausible.md` | 16,258 kept / 682 dropped | 05-25→08-01 | +0.02pp; residual z=−2.59 (borderline, below \|z\|=4) | n/a | n/a | **SUGGESTIVE** (measured on the contaminated universe; re-test pending) |

---

# SECTION 2 — crypto (BTC/ETH/SOL/XRP prediction markets)

Artifacts: `C:\Users\gianf\crypto\` (original, **recorder live**) and
`trading/crypto/`. Ledger: `HYPOTHESIS_LEDGER.md`, headline `MORNING_REPORT.md`.

**17 hypotheses / 101 individual tests. Facts surviving correction: 2. Tradeable
edges surviving correction: 0.**

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| C010 | **No model beats Kalshi's own mid.** Two tie, two lose. The crypto ladder is efficiently priced. | crypto | `src/analyze_panel.py` → `reports/b1_output.txt`, `b1_KXBTCD.json` | **250 events**, 89,806 market-minutes, 1,968 markets | 05-25→07-30 | M1 +0.000261 [−0.00157,+0.00219]; **M2 −0.000081 [−0.00188,+0.00182]**; M3 +0.003703 [+0.0015,+0.006]; M3t +0.022455 | n/a (null) | event-clustered CIs; 2 disjoint periods | **SETTLED** |
| C011 | The settlement-average correction genuinely improves the model (M2 beats M1). | crypto | same | 250 events | 05-25→07-30 | **−0.000342 [−0.000436,−0.000242]**, p<1e-3 | **yes** | consistent | **SETTLED** |
| C012 | Feeding the model **fatter** tails than the market uses makes the forecast worse. | crypto | same | 250 events | 05-25→07-30 | M3 vs M2 +0.003784 [+0.00182,+0.00582] | **yes** | — | **SETTLED** |
| C005 | Hourly BTC/ETH returns are severely fat-tailed. | crypto | `src/fat_tails.py` → `reports/fat_tails.json` | 1,582 returns / 1,593 events, 68 days | 68-day window | excess kurtosis **13.08 / 12.85**; ν≈2.03/2.02; Hill α 2.55/2.69; 4σ tail **140×** Gaussian | **yes**, p<1e-300 | — | **SETTLED** (descriptive; BTC/ETH corr 0.891 ⇒ **one** finding not two) |
| C001 | ⚠ **WORDING NARROWED 2026-08-09.** "No arbitrage" rests on **10.5 minutes** of scanning. The sentence to quote is **K007's 9 hours** (52 real violations, 0 with tradeable size) — same conclusion, honest sample. Original: Kalshi `greater` ladders are monotone in strike — no arbitrage. | crypto | `src/ladder_arb.py` → `reports/ladder_arb.json` | 3,187 scans / 26 events / 10.5 min | 08-01 | **0 violations**, gross or net | n/a | — | **SUGGESTIVE** (clean null but only 10.5 min). ⚠ The "prior 1,083-scan null" this row cited is **[K007](#section-6--kalshi-market-scan-exchange-wide-screen-weather-flow-sports)**, which found **52 violations, not zero** — citation corrected in `crypto/` 2026-08-03 |
| C002 | ⚠ **WORDING NARROWED 2026-08-09.** Same 10.5-minute window as C001; quote **K007** instead. The *mechanism* (a 75-leg fee floor of ~1.93¢ against ~1¢ of mispricing) is what carries this, not the sample. Original: `between` bucket families sum to 100¢ — no arbitrage net of fees. | crypto | same | 1,135 complete scans / 26 events | 08-01 | 1 gross violation (+1.00¢), **0 profitable net** (75-leg fee floor ≈1.93¢) | n/a | — | **SUGGESTIVE** (same duration caveat; structural mechanism given) |
| C004 | Polymarket's fee is **`0.10 × min(p,1−p)`**, not the documented `0.07·p(1−p)`. | crypto | `src/poly_fee.py` → `reports/poly_fee_resolution.json`, `poly_fee_verify.json` | 4,310 fee-bearing on-chain fills | 04-20→04-27 | median relative error 0.000000; **100% within 1%** | n/a (exact) | independently reproduced in wallet-copy-study on 5,362 fills | **SETTLED** |
| C016 | The "cheap wings" are not tradeable — they have an ask but **no bid**. | crypto | `reports/b1_KXBTCD.json`, `MORNING_REPORT.md` §0000 | 60-strike ladder, per-minute over final hour | 08-01 | at \|K−settle\| ≥ $893: **0 of 61 minutes** two-sided, all 11 strikes | n/a | n/a | **SETTLED** |
| C017 | Deribit cannot serve as a reference price for the hourly ladders. | crypto | `docs/deribit_method.md`, `docs/venue_comparison.md` | — | 08-01 | shortest usable expiry **54.2h** vs ladder median lifetime **1.0h**; only 0.1% reach 54h | n/a | n/a | **SETTLED** (cancels hypothesis X4) |
| C018 | Kalshi unauthenticated rate limit is 15 req/s sustained; 25 req/s ⇒ 56% rejection. | crypto | paced probe, `docs/connectivity.json` | — | 07-30 | 15 r/s = 0% reject | n/a | n/a | **SETTLED** |
| C007 | The pipeline finds **no** edge in synthetic data containing no edge. | crypto | `src/synthetic_control.py` → `reports/synthetic_control.json` | 1,500 synthetic events × 9 strikes | — | diff −0.000028 [−0.00013,+0.00008], **contains zero**, p=0.593 | n/a | n/a | **SETTLED** (control) |
| C008 | The pipeline **detects** an injected 15% wing bias, and a 5% one. | crypto | same | 1,500 events each | — | −0.002655 [−0.00310,−0.00217]; 5%: −0.000334 [−0.00050,−0.00014] | p<0.0001 | n/a | **SETTLED** (control — this is what makes C010's null credible) |
| C009 | The pipeline **detects** outcome leaked into a feature. | crypto | same | 1,500 events | — | Brier 0.0004 vs 0.1032 | p<0.0001 | n/a | **SETTLED** (control) |
| C003 | BTC/ETH settlements pin near round numbers. | crypto | `src/pinning_test.py` → `reports/pinning_test.json` | 1,593 events, 68 days | 68-day window | 6/20 survived BH at p≈0, Rayleigh R≤0.244 | initially yes — **invalid** | — | **RETRACTED** |
| C006 | The fat-tail mispricing is economically tradeable (1.5–1.9¢ at 2.5–3σ). | crypto | `reports/fat_tails.json` | — | — | benchmark was a Gaussian, not Kalshi's mid | — | — | **RETRACTED** |
| C013 | The mid's calibration gap is real and tradeable (+4.2pp, net +1.00¢). | crypto | `src/mid_calibration.py` → `reports/mid_calibration.json` | 250 events × 17 buckets | 05-25→07-30 | best p=0.029 vs BH threshold **0.0059** | **no** | **no** — no bucket significant in both halves | **RETRACTED** |
| C014 | 464 profitable bucket-sum violations at 96–97¢. | crypto | `reports/ladder_arb.json` (pre-fix) | 464 "violations" | 08-01 | all 464 vanished on requiring a complete contiguous tiling | — | — | **RETRACTED** |
| C015 | Polymarket taker cost is identical to Kalshi's. | crypto | `reports/poly_fee_resolution.json` | — | — | **2.86× Kalshi at 50¢** | — | — | **RETRACTED** |
| C019 | Effective sample size is far below row count — ~360 correlated minutes per event. | crypto | `src/effective_n.py` → `reports/effective_n_audit.json`, `.txt`, `docs/EFFECTIVE_N_AUDIT.md` | 89,806 market-minutes → 250 events | 05-25→07-30 | pseudo-replication factor ~10× on CI width | n/a | n/a | **SETTLED** |
| C020 | ETH does not lead BTC. | crypto | `src/leadlag.py` → `reports/leadlag.json`, `leadlag_tradeable.json` | recorded tick data | 07-30 | contemporaneous corr **0.845** vs **0.037** at best lead | n/a | — | **SETTLED** |
| C021 | Path/streak structure in 15m opens is tradeable. | crypto | `src/path_streak.py` → `reports/path_streak.json`, `streak_fade.json`, `streaks_multiasset.json`, `PATH_STREAK_RESULTS.md` | multi-asset | — | see `PATH_STREAK_RESULTS.md` — no edge clears the cost bar | no | — | **SETTLED** (null) |
| C022 | Market-making on the ladders is viable. | crypto | ~~`MM_RESULTS.md`~~ → **`crypto/RESULTS_MAKER_VIABILITY.md`** (`src/maker_viability.py`) | **17,325 simulated fills, 1,161 events, 23 days** of replayed KXBTCD L2 | 2026-05-19 → 06-11 | **net −0.853¢/contract, 95% CI [−1.632, −0.185] clustered on DAYS — excludes zero.** Capture is **−1.226¢**: a trade-through fill means the book moved *away* before you traded. Side placebo **−0.004¢** | n/a | holdout sealed, nothing qualified | **SETTLED (null) — RE-CLOSED 2026-08-09 ON REAL EVIDENCE.** ⚠ The `reopen` chat is right that the old row was wrong: it cited `MM_RESULTS.md`, whose §10 is titled *Verdict* and opens **"Not yet reached"**. It is now closed on a measurement that did not exist then, and the closure is *stronger*, not weaker |
| C023 | Hold-to-settlement on the ladders is profitable. | crypto | `src/hold_settle.py` → `reports/hold_settle.txt` | **250 events, 89,819 rows, 1,968 markets** (BTC arm) | **2026-05-25 → 07-30** | ⚠ **THE ROW SAID ONLY "negative" AND THE ARTIFACT DOES NOT.** It reads **`tie` in 40 of 44 price cells**; only the 90¢ cell is `negative` (−3.677 [−7.23, −0.05]). Intervals run **±5 to 15¢ against a 1–2¢ cost**, so the test cannot see anything under ~5¢. BTC at 5¢ reads **+2.929 [−0.01, +6.13]** — upper cells *positive* with the lower edge a hundredth below zero | no | — | **UNDERPOWERED, not demonstrated negative. Reopened 2026-08-09.** ⚠ **Do NOT chase the 5¢ cell**: the artifact shows the other three assets going the *other* way there, and C026 puts the four at **~1.8 independent series**, so it does not replicate |
| C024 | A silent orderbook parse bug wrote **real row counts with empty content** for 1h45m. | crypto | recorder output inspection; `reports/data_audit.txt` | 1h45m of recording | 07-30 | caught **by accident** | n/a | n/a | **SETTLED** (bug) / fix status **UNVERIFIED** |
| C025 | "MM scan: **0 of 4 series profitable**." | crypto | ~~`mm_latency_fixed.json`~~ → **`crypto/MM_RESULTS_MAKER.md`** (`src/maker_multiday.py`) | **all four series now tested**: KXBTCD, KXBTC15M, KXETHD, KXETH15M | 2026-07-24 → 07-31 | the original claim covered **1 series, 58 markets**, and three of four had no artifact at all. All four are now measured. **None shows a maker edge**; on the largest (KXBTC15M, 658 events) the **side placebo BEATS the real result** | n/a | n/a | ~~UNVERIFIED~~ → **SETTLED 2026-08-09.** The sentence happened to be right and the evidence for it did not exist when it was written |
| C026 | The four crypto assets are **not four independent series** — there are ~1.81. | crypto | `src/effective_n_audit.py` → `reports/effective_n_audit.json`, `docs/EFFECTIVE_N_AUDIT.md` | 4 assets, settlement signs | 68-day window | **1.81 effective independent series of 4**; settlement-sign phi **0.59–0.70** | n/a | n/a | **SETTLED** — every pooled cross-asset claim re-verdicted against it |
| C027 | Lead-lag ETH→XRP (+0.1544) is tradeable. | crypto | `reports/leadlag.json`, `leadlag_tradeable.json` | 1-second returns | 07-30 | **0.38¢ of edge against a 1.00¢ minimum tick**; needs corr 0.575–1.113 vs 0.1544 observed | n/a | n/a | **SETTLED** (null) — killed economically, so the understated SE (1/√n on autocorrelated data) does not matter |

---

# SECTION 3 — wallet-copy-study (Polymarket copy trading)

Artifacts: `trading/wallet-copy-study/` (moved; 17 GB of data stays local and
gitignored). Verdict: `COPY_TRADING_VERDICT.md`. Seed 20260801 throughout.

**Sample:** 2,500 wallets · 14,082,296 wallet-panel fills · 1,746,750 positions ·
2,529 sampled markets · 2,778,373 market-panel fills · 2,108,796 market universe,
874,943 eligible. 32 validation tests pass.

**Verdict: EDGE, SLOW DECAY — do not build the bot.**

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| W001 | **Wallet skill is real and persists out of sample.** | wallet-copy-study | `src/phase4a_persistence.py` → `reports/phase4a_persistence.json`, `phase4a_persistence_clean.json` | 1,028–1,778 wallets; unit = market and (wallet,series,day) | 2025-01-01 → 2026-04-28 | Spearman ρ **0.157–0.433, positive in all 36 cells**; rises with markets-per-wallet | n/a | **yes** — 3 independent split points | **SETTLED** |
| W002 | A period-1 top decile keeps **+2.567pp of excess** into an untouched period 2. | wallet-copy-study | `reports/phase4c_copyability.json` | 31,703 wallet-markets / 479 wallets | P2 = 2025-07-01→ | **+2.567pp [2.19, 2.96]** | n/a | **yes** — selection on P1 only | **SETTLED** |
| W003 | But a **copier** who buys the same entries and holds gets only **+0.937pp**. | wallet-copy-study | same | 31,703 wallet-markets | P2 | **+0.937pp [0.53, 1.38]** | n/a | yes | **SETTLED** |
| W004 | And that is **less than the spread**, so the strategy is break-even at best. | wallet-copy-study | `reports/phase4d_capacity.json` + arithmetic in `COPY_TRADING_VERDICT.md` | median same-block trade dispersion | P2 | +0.937 − 1.000 = **−0.063pp**, and 1.0pp is a **lower bound** (mean 2.10, p90 4.07) | n/a | n/a | **SETTLED** |
| W005 | The copier return **declines monotonically** across split points: +1.98 → +0.94 → **−0.14**. | wallet-copy-study | `reports/phase4c_copyability_1735689600.json`, `_1767830400.json` | 211 / 479 / 822 eligible wallets | 3 cuts to 2026-04-28 | +1.981 [1.45,2.52] → +0.937 [0.53,1.38] → **−0.135 [−0.93,+0.63]** | n/a | yes, at each cut | **SETTLED** |
| W006 | **72% of the edge lives in exits.** | wallet-copy-study | `reports/exit_stage1_decomposition.json` | top decile | P2 | genuine exit component **−0.106pp = −4.3%**; the rest was the fee | — | — | **RETRACTED** |
| W007 | Copying exits **destroys** value at every delay. | wallet-copy-study | `src/exit_study.py` → `reports/exit_anatomy.json`, `exit_stage2_decay.json` | 8,600 positions with sells; balanced panel n=2,879/delay | P2 | −0.505pp [−0.643,−0.373] p=0.0005; −0.698pp at 1.0pp/leg spread | **yes — 18 of 20 under BH-FDR 5%** | yes | **SETTLED** |
| W008 | It is **not timing skill** — duration-matched, the wallets add nothing. | wallet-copy-study | `reports/exit_anatomy.json` | 8,600 positions | P2 | wallet − mechanical = **−0.401pp [−1.03,+0.24], p=0.224** | n/a | yes | **SETTLED** |
| W009 | It is **not tail-risk avoidance** — shorter holding is strictly worse, monotonically. | wallet-copy-study | `reports/exit_stage2_decay.json` | 3,200 tokens / 10,755,763 fills | P2 | 60s −3.548 [−4.74,−2.34] … 86400s −1.523 [−2.43,−0.62] vs buy-and-hold | **yes — 12 of 13 under BH** | yes | **SETTLED** |
| W010 | Selling winners early and losers early are **two enormous effects that cancel**. | wallet-copy-study | `reports/exit_anatomy.json` | 8,600 positions (4,125 win / 4,475 lose) | P2 | winners **−23.988pp**, losers **+21.196pp**, net −0.476 [−1.02,+0.04] | 10 of 20 under BH | yes | **SETTLED** |
| W011 | Naive favourite-band buying earns +7.05pp (the prior study's benchmark). | wallet-copy-study | none findable — recursive search of `C:\Users\gianf` found no dataset | claimed n=98,766 | — | recomputed: **+2.09pp [−1.37,+5.35] gross, −0.29pp net** | n/a | n/a | **RETRACTED** |
| W012 | Copying selected wallets loses −5.90pp. | wallet-copy-study | `reports/phase4c_copyability.json` (intermediate) | 1,944 signals / 140 markets | P2 | re-measured on full panel: **+0.937pp** | — | — | **RETRACTED** |
| W013 | **Entries do decay** for selected wallets: +3.436 → +0.427pp over 5 minutes. | wallet-copy-study | `reports/exit_stage2_decay.json` | balanced panel, n=2,879 | P2 | ~3pp in 5 min, most in the first 10s | n/a | **not a clean holdout** — subsample is positions with sells, not random entries | **SUGGESTIVE** |
| W014 | The **unconditional** decay curve is flat from 0s to 1800s — a bot buys nothing. | wallet-copy-study | `reports/phase4c_decay.json`, `phase4c_decay_selected.json` | 2,234,479 buy signals | full history | copy return moves ~0.3pp between +1s and +1800s | n/a | yes | **SETTLED** (but W013 shows the *conditional* statement was too strong) |
| W015 | Below ~20 markets per wallet, the **entire** spread in wallet performance is sampling noise. | wallet-copy-study | `src/phase4b_shrinkage.py` → `reports/phase4b_shrinkage.json` | 1,630 wallets at min=10 | full history | τ = **0.000pp** at min 10; best raw +18.98pp shrinks to **−0.63pp** | n/a | n/a | **SETTLED** (this is the exact mechanism that made a coinflip a "+95pp genius") |
| W016 | Only **27%** of wallets have enough markets to detect a +5pp edge at 80% power. | wallet-copy-study | same | 485 of 1,778 non-MM wallets | full history | σ=0.296 ⇒ n≈**274 markets** needed | n/a | n/a | **SETTLED** |
| W017 | Polymarket charged **no fee for 91% of on-chain history**, switching on **2026-01-08**. | wallet-copy-study | bisected to the day; `reports/exit_fee_era_ranking.json` | on-chain history | to 2026-04-28 | regime break confirmed | n/a | n/a | **SETTLED** |
| W018 | Ranking inside the fee era finds an **almost entirely different** top decile. | wallet-copy-study | `reports/exit_fee_era_ranking.json` | 36 wallets | 2026-01-08→04-28 | overlap **7 of 36**, Jaccard **0.092**; 23 of 36 not previously eligible; retained excess collapses +6.441 → **+0.513pp** | 6 of 7 under BH | yes | **SETTLED** (composition) / **SUGGESTIVE** (point estimate — 8 weeks/sub-period) |
| W019 | **Capacity is not the constraint** — price impact does not scale with trade size. | wallet-copy-study | `reports/phase4d_capacity.json` | 2,231,492 trades across 7 size buckets | full history | absolute move 0.41–0.81pp across **four orders of magnitude** — that is the spread, not impact | n/a | n/a | **SETTLED** |
| W020 | **Adverse selection is not present** — copyable fills are *better*, not worse. | wallet-copy-study | same | 96.9% of signals copyable at +60s | full history | copyable −1.54pp vs uncopyable −5.32pp | n/a | n/a | **SETTLED** |
| W021 | Market making is **not** the explanation for persistence. | wallet-copy-study | `src/phase2_exclusions.py` → `reports/phase2_exclusions.json` | 721 of 2,500 wallets excluded (28.8%), none on performance | full history | removing them barely moved ρ (scenario A→B) | n/a | n/a | **SETTLED** |
| W022 | Survivorship is not driving the result. | wallet-copy-study | `reports/phase4a_persistence_clean.json` | attrition 3.7%–37.5% by cut | full history | survivor-minus-quitter P1 excess +0.82 / +0.32pp at two cuts, **negative** at the other two | n/a | n/a | **SETTLED** |
| W023 | The excess metric scores a null strategy at zero. | wallet-copy-study | `reports/selection_audit.json` | random subsets | — | **−0.0pp**, random subsets straddle zero | n/a | n/a | **SETTLED** (canary) |
| W024 | Phase 5 (sizing, portfolio, forward test) was **deliberately not run**. | wallet-copy-study | `COPY_TRADING_VERDICT.md` | — | — | gate requires persistence **and** an actionable window; the window does not exist | n/a | n/a | **SETTLED** (a decision, not a result) |

---

# SECTION 4 — kalshi-tennis (Stage 0–5 pre-match player model)

Artifacts: `trading/kalshi-tennis/reports/` — eight `.txt` files, all present.
This folder is the **only** copy of the Stage 0–5 work and was unversioned until
this repo. See `reports/README_DEFECTS.md`.

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Only **36.9%** of Kalshi tennis markets clear all three modelling thresholds. | kalshi-tennis | `src/stage0_audit.py` → `reports/stage0_coverage.txt` | 20,922 markets / 9,262 players | to 2026-07 | 86.6% have both players in Sackmann; 36.9% usable; ATP-ITF 20.9% | n/a | n/a | **SETTLED** |
| T002 | The binding constraint: Sackmann features end **2026-06-02**, and 85.0% of markets are after that. | kalshi-tennis | same | 20,922 markets | to 2026-07 | only **3,145** markets are both settled and inside the window | n/a | n/a | **SETTLED** |
| T003 | Sackmann's upstream repos are **gone (404)**; the project runs on a frozen mirror. | kalshi-tennis | `src/verify_data.py` (4 known finals reproduced) | — | mirror last commit 2026-06-25 | verified 404 + schema check | n/a | n/a | **SETTLED** |
| T004 | **"Comeback ability" is ~75% just overall skill.** | kalshi-tennis | `src/stage3_traits.py` → `reports/stage3_traits.txt` | **3,446,840 player-match rows; 15,812 players** | full history | split-half r **+0.439** raw → **+0.125** residualised; tiebreak r +0.091→+0.049; **positive control** (match win rate) r=+0.633 | n/a | split-half **with** a positive control and a null | **SETTLED** |
| T005 | The model itself is good: held-out Brier 0.19884, AUC 0.75984. | kalshi-tennis | `src/stage4_model.py` → `reports/stage4_model.txt` | test n=**80,657** (2025+), 1,530,252 rows, 50 features | train <2023 / val 2023-24 / test 2025+ | Brier 0.19884, LogLoss 0.58007, AUC 0.75984, Acc 0.68707; calibration within ~0.021 | 6 variants declared | **yes** — chronological split | **SETTLED** |
| T006 | **But the model loses to the bookmakers.** This is the Stage 4 gate, and it failed. | kalshi-tennis | same | n=**2,645** matches (avg close), n=1,774 (Pinnacle-labelled) | 2025+ | **+0.01922 [+0.01438, +0.02417]**; Pinnacle row +0.01816 [+0.01216,+0.02425] | n/a | yes; **contains no Kalshi data so the leak never touched it** | **SETTLED** |
| T007 | The market beats the model on tradeable Kalshi quotes (+0.03711). | kalshi-tennis | `src/stage4_kalshi_liquid.py` → `reports/stage4_kalshi_liquid.txt` | n=302 / 287 / 186 matches | 2026 | +0.03711 [+0.0165,+0.0569]; monotone across 3 liquidity filters | n/a | — | **RETRACTED** — the spread filter read the leaking anchor (`SELECTION_AUDIT.md` row 19). Direction survives via T012. |
| T008 | Selective betting returns **+14.4% to +24.6% ROI**. | kalshi-tennis | `src/stage5_selective.py` → `reports/stage5_selective.txt` | 465/389/294 bets over 502 held-out matches | 2026 | at executable fills: **−24.3% to −30.9%**, every CI below zero | — | had a holdout; the **fill model** was the defect | **RETRACTED** |
| T009 | 43 selective segments tested with Benjamini-Hochberg; **19 survive and every one is negative**. | kalshi-tennis | same | 43 segments / 502 matches | 2026 | 19 survive at α=0.05, all negative | **yes** | held-out matches | **SETTLED** |
| T010 | Kalshi beats the Betfair closing line by 0.022 Brier. | kalshi-tennis | `src/pinnacle_vs_kalshi.py` → `reports/pinnacle_vs_kalshi.txt` | n≈844 joined matches | 2026 | at a clean −6h anchor the advantage vanishes (+0.00122) | — | — | **RETRACTED** |
| T011 | The anchor sweep proves **which** Kalshi anchor is leak-free. | kalshi-tennis | `src/anchor_leak_test.py` → `reports/anchor_leak_test.txt` | n=575–877 per anchor | 2026 | −0h: 4.1% of quotes outside 2c–98c and **100% correct**; −6h: 0.1% extreme, corr **0.9775** | n/a | n/a | **SETTLED** — the two independent books agree at corr 0.9985, so any anchor where Kalshi beats both is leaking |
| T012 | **Kalshi is the sharp line** — indistinguishable from Betfair at a clean anchor. | kalshi-tennis | `reports/pinnacle_vs_kalshi.txt` | n=**809** matches | 2026, −6h anchor | r=**0.9878**, MAD **1.95¢** vs a 2.44¢ round-trip cost; Brier diff −0.00053 **[−0.00312,+0.00157]** | n/a | 4,000-sample bootstrap; **no model fitted ⇒ no holdout needed** | **SETTLED** |
| T013 | Where the two venues disagree by more than it costs to act, **Kalshi is closer 49.1% of the time** — a coin flip measured precisely. | kalshi-tennis | same | 230 of 809 disagreements (28.4%); 14 segments | 2026 | **49.1% [42.7%, 55.6%]**; **all 14 segments cross zero** | n/a | segments span tour, surface, favourite band, time-to-start, period | **SETTLED** |
| T014 | tennis-data.co.uk **stopped carrying Pinnacle in 2026**; the real benchmark is the Betfair Exchange close. | kalshi-tennis | `reports/pinnacle_vs_kalshi.txt` (`with a real Pinnacle price: 0`) | 844 joined matches | 2026 | Pinnacle coverage collapsed to **5.1%**; Betfair 93.6% | n/a | n/a | **SETTLED** — ⚠ **naming trap**: the script, the report and a Stage 4 row are all still labelled "Pinnacle" |
| T015 | **39.8%** of held-out Kalshi markets quote wider than 10¢ — a 1c/99c quote has a 50c "mid" nobody trades at. | kalshi-tennis | `reports/stage5_selective.txt` | n=502 markets | 2026 | median spread 3.0¢, 39.8% > 10¢ | n/a | n/a | **SETTLED** — this is the mechanism behind both T008 and T007 |
| T016 | Shrinkage behaves correctly across all 8 statistics × 2 buckets. | kalshi-tennis | `src/stage2_shrinkage.py` → `reports/stage2_shrinkage.txt` | 16 statistic×bucket cells | full history | raw sd collapses toward population sd everywhere | n/a | n/a | **SETTLED** (sanity check) |
| T017 | Stage 0 coverage is 74.5% and there is no ITF tier on Kalshi. | kalshi-tennis | `src/stage0_audit.py` (pre-fix) | 20,922 markets | — | ITF is **31,894 markets ≈ 76%** of the book | — | — | **RETRACTED** |
| T018 | The ITF tier **cannot** be modelled from Sackmann — serve stats on only 4.6% of futures rows. | kalshi-tennis | `reports/stage0_coverage.txt` | futures rows | full history | 4.6% | n/a | n/a | **SETTLED** — with T001 this is the "where the data exists the market is hard; where the market is soft the data doesn't exist" constraint |
| T019 | Player order is assigned cleanly (alphabetical), not by outcome. | kalshi-tennis | `src/stage4_model.py:43-47`; `SELECTION_AUDIT.md` row 80 | — | — | `swap = w > l`, target ~50/50 | n/a | n/a | **SETTLED** (guard) |
| T020 | The API-listing-order side choice is clean. | kalshi-tennis | `src/tennis_data.py:196-198` | 19,782-market canary | — | **z = +1.44** | n/a | n/a | **SETTLED** (guard) |
| T021 | `stage5_selective.py` sorts variants on `mean_pnl` over the **full sample with no holdout**. | kalshi-tennis | `SELECTION_AUDIT.md` row 86; re-read 2026-08-06 | — | — | ⚠ **SEVERITY CORRECTED DOWN 2026-08-06.** The wording reads like a selection step and it is not one: the sort decides only the **order of the printed table**, and Benjamini-Hochberg is applied across **every** segment, not the 25 displayed. Nothing downstream consumes the ordering. **What remains is a reading hazard** — printing the 25 best realised P&Ls invites a reader to quote one. Commented in place | n/a | **no** | **SUGGESTIVE hazard**, not BROKEN |
| T022 | `stage5_selective.py` dedupes with `keep="first"` — order-dependent and non-deterministic. | kalshi-tennis | `SELECTION_AUDIT.md` row 87 | — | — | **FIXED 2026-08-06.** An explicit `sort_values(list(p.columns), kind="mergesort")` now precedes the drop. Every sort column is a pre-match feature or identifier — date, player names, elo/rank gaps, sample counts — and **none is outcome-derived**, which is the condition GUARDS #1 exists for (S011 deduped on `volume_fp`, P(kept wins) = 0.5356, z = +10.0, and it voided four phases). **A fixed arbitrary rule is not ideal; a non-deterministic one is strictly worse, because it cannot be reproduced to be audited.** ⚠ Not executed — `kalshi-tennis/data/` is **laptop-only** and empty on the desktop. Verified by AST parse and an isolated determinism test | n/a | n/a | **FIXED, unrun** |

---

# SECTION 5 — claims from the chat archive (CH001–CH128)

Full text, per-claim validation and source conversation codes:
**[kalshi-chat-audit/LEDGER_CHATS.md](kalshi-chat-audit/LEDGER_CHATS.md)**
(129 rows) and **[kalshi-chat-audit/FAILURE_MODES_CHATS.md](kalshi-chat-audit/FAILURE_MODES_CHATS.md)**.

These come from 21 Claude Pro conversations + 1 Max conversation, 2026-07-25 →
07-31. They are **not** duplicated row-by-row here because that file already
carries them in this exact schema. What matters for this ledger:

| Group | Count | Where the artifacts live |
|---|---|---|
| CH001–CH020 | 20 **RETRACTED** | mostly the tennis bot and copy-trading threads |
| CH021–CH046 | Tennis live-trading bot | **desktop machine** (`C:\Users\vinig\kalshi`) — not in this repo |
| CH047–CH058 | v3 candlestick backtest | **desktop machine** |
| CH059–CH074 | Stage 0–5 player model | **in this repo** — superseded by Section 4 above, which applies the selection audit on top |
| CH075–CH077 | `/tennis-live-predictor` skill accuracy | chat only, no artifact |
| CH078–CH091 | BTC 15-min + exchange-wide scan | partly superseded by Section 2 |
| CH092–CH097 | Polymarket copy trading | superseded by Section 3, which recomputed the benchmark from scratch |
| CH098–CH111 | Discord signal bot ("rot") | chat + export only |
| CH112–CH123 | Manual discretionary trading | screenshots only |
| CH124–CH128 | Process and infrastructure | derived |

### The five CH rows that still gate decisions

| ID | Claim | STATUS | Why it matters |
|---|---|---|---|
| **CH057** | "4 weeks / 14k markets / 0 of 480 configs profitable" | ~~UNVERIFIED~~ → **SETTLED 2026-08-06** | ⚠ **This row was STALE and the audit found it so.** It was still labelled *"never checked, still open"* after **three independent verifications had landed**: (1) the v3 dedupe field was traced end to end on 2026-08-03 and is ordered on **entry timestamp** with ticker as tie-break — `strategies.py` contains **zero** references to `volume`, `open_interest`, `last_price` or `settlement`, so the ~100× evidence base is **usable**; (2) `kalshi-inplay-bot/backtest/BACKTEST_RESULTS.md` prints **"Configurations with positive net P&L per trade: 0 of 480"**; (3) **B010** independently replayed the sweep at **481 configurations, 0 profitable**, and **B009** replayed the live config over **13,658 market views** at −8.08¢/trade. **The single highest-value verification in the archive was completed and nobody updated the row.** |
| **CH031** | The score-staleness guard never fired — `fetched_at` was stamped at cache read | **SETTLED** (bug), **magnitude measured 2026-08-05** | **No live entry result anywhere in the archive is a valid test of the entry logic.** The 4-for-10 included. **[B008](#section-7--bot-forensics-the-night-the-live-tennis-bot-made-money) puts a size on it, which this row lacked for months:** on 4,398 score-change events, **97.4% of the repricing had already happened** by the time the bot's snapshot showed the new score (+4.68c before, +0.17c after, placebo +0.18c). The bot was systematically buying **after** the news. |
| **CH022** | Three irreconcilable P&L figures for one session (+$0.60 / +$2.51 / −$3.55) | **BROKEN** | The fee ceiling proves −$3.55 is impossible; true net is in **[−$0.68, +$2.51]**. CH021 and CH029 are unusable until this is resolved. |
| **CH035** | Every negative result in the project is a **taker** result | **UNVERIFIED** | No resting-order strategy was ever tested on any market — until S008 above, which tested it on tennis and found all 15 configurations negative. |
| **CH044** | A position-sizing blowout produced 64 contracts against an intended 9 | **SETTLED** (bug) / cause **SETTLED 2026-08-03** | ~~Never diagnosed, never fixed.~~ **Both halves of that are now wrong.** Diagnosed 08-03: **not a sizing bug but a martingale** — `qty = int(stake/price)` is arithmetically correct, and sizing by *fixed dollars* buys *more* contracts as price falls, so 64 = 12+20+32 across three re-entries. Fixed the same day (`max_contracts`, `reentry_cooldown_sec = 900`, `max_reentries_per_event = 1`, `max_daily_loss_pct` 0 → 15). **[B007](#section-7--bot-forensics-the-night-the-live-tennis-bot-made-money) then showed it was never confined to one match: twelve averaging-down sequences, −$16.43, and the other 94 matches were +$9.63.** See also **B017** — the legs were 749 s apart, not 24 s. |

---

# SECTION 6 — kalshi-market-scan (exchange-wide screen, weather, flow, sports)

**Added 2026-08-03.** This project had **no rows in this ledger at all** until
now — its claims were invisible to every ledger-based cross-check, which is
exactly why four retracted results survived in `docs/GO_NO_GO.md` and
`docs/shortlist.md` and were caught only because a brief named them.

Artifacts: `kalshi-market-scan/`. Corrected headline: `MORNING_REPORT.md`.
Own hypothesis count: `docs/HYPOTHESIS_LEDGER.md` — **116 hypotheses across 13
blocks**, BH-FDR corrected within block. The shorter files (`GO_NO_GO.md`,
`shortlist.md`) are more quotable than the evidence behind them; where they
disagree with `MORNING_REPORT.md`, **the morning report wins**.

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| K001 | ⚠ **WORDING NARROWED 2026-08-09.** Reads as a general claim; it is **25 markets**. Correct sentence: *"on the 25 KXBTC15M markets with recorded books, no model beat the mid and every interval spans zero."* The family is dead on **structure** anyway (K013), which is the load-bearing kill. Original: **No model beats the Kalshi mid on `KXBTC15M` direction.** | kalshi-market-scan | `reports/vs_mid_clustered.csv`, `MORNING_REPORT.md` §7g | **25 markets** with recorded books, 7 offsets | 08-02→08-03 | 0 of 7 offsets beat the mid; **all CIs span 0**; ours 0.0020@60s vs mid 0.0075@60s | market-clustered bootstrap | measured forward, not back-filled | **SETTLED** (null) |
| K002 | **The weather model genuinely beats climatology** in all four cities. | kalshi-market-scan | `scripts/weather_model.py` → `reports/weather_model.csv` | **812 independent settlements** (~204/city) | to 08-03 | persistence Brier 0.076–0.136 vs climatology 0.216–0.315; clustered diff CIs all exclude 0 | **yes**, across 4 cities jointly | bootstrap over whole settlement hours | **SETTLED** |
| K003 | The weather model was validated on **8,090 test markets**. | kalshi-market-scan | `docs/shortlist.md` (pre-correction) | claimed 8,090 markets | — | a ladder is **one** temperature reading, not 10 markets; effective n ≈ **800 settlement hours**, CIs ~**3× too tight** | — | — | **RETRACTED** — pseudo-replication. K002 is the corrected version and **survives** |
| K004 | **Only `KXTEMPDCH` clears both the power bar and the capacity bar.** 1 of 11 families. | kalshi-market-scan | `MORNING_REPORT.md` §7g cross-tab | 11 families | 08-03 | requires ≥481 settlements **and** ≥50 contracts at the touch; `KXTEMPDCH` clears at **512 vs 481** — a 6% margin | n/a | n/a | **SETTLED** |
| K005 | "**Seven daily families clear the capacity bar by 7–49×**, so weather is not capacity-limited." | kalshi-market-scan | `docs/shortlist.md`, `docs/GO_NO_GO.md` (pre-correction) | 7 families, 371–2,434 median depth | 08-03 | depth figures are **correct**; the inference is not. All seven have **66** independent settlements against the **481** needed, so their depth decides nothing | — | — | **RETRACTED** (framing) — "celebrating the wrong axis" |
| K006 | **Depth at the touch collapses 40× toward expiry** (158→4 contracts) as the model sharpens, so edge and liquidity are anti-correlated. | kalshi-market-scan | `docs/GO_NO_GO.md` (pre-correction) | **1 market, 3 minutes** | — | on 25 markets over 7 h: depth declines **2.7×**, never thin (**307** contracts inside the final minute, not 4); spread **tightens 10×**; total cost **falls** 4.46¢→3.50¢ | — | — | **RETRACTED** — the argument is **withdrawn entirely**; the contract is *cheaper* to trade late |
| K007 | **No-arb violations are real but the size is dust.** | kalshi-market-scan | 1,083 scans, `MORNING_REPORT.md` | 1,083 scans / 26 families / ~9 h | 08-02→08-03 | **52 genuine violations, 0 with tradeable size** | n/a | n/a | **SETTLED** (null) — corroborates C001/C002 **on the conclusion, not the count**: `crypto/` cited this study twice as "zero violations in 1,083 scans" when it found **52** (none tradeable). Corrected 2026-08-03 |
| K008 | Copying Polymarket tennis wallets earns **+7.23pp**. | kalshi-market-scan | `reports/copytrade_tests_v2.json` | 264,074 positions | — | +7.23pp CI [+4.61, +9.73] against a 2.4¢ bar | **yes** | price-matched | **SETTLED** (the number) — but **not skill**; the edge lives in the price band, §7 |
| K009 | **The favourite-longshot bias does not exist on Kalshi**, so the Polymarket→Kalshi transfer fails. | kalshi-market-scan | `reports/kalshi_longshot_v3.json` | **762 settled matches**, 490,464 fills; re-run 12 series / 2,258 markets | to 08-03 | aggregate **−0.67pp** against a 2.72% overround; Polymarket's +8.57pp at 0.6–0.7 becomes **−2.12pp** | binomial per bucket | n/a | **SETTLED** (aggregate) — this is the load-bearing kill for the copy-trading thread |
| K010 | Kalshi pre-match prices are **calibrated bucket by bucket** ("every binomial p ≥ 0.499"). | kalshi-market-scan | same | buckets of **n=19–52**; re-run gave only **726** usable pre-match observations | to 08-03 | a **failure to reject**, not a demonstration. Bucket CIs **±11–29pp**; **0 of 7** Polymarket values formally excluded — they sit *inside* the intervals | 0 of 30 survive | n/a | **UNVERIFIED / OVERSTATED** — correct statement is "no *detectable* bias at this n". K009's aggregate is the part that carries weight |
| K011 | **Flow following on Kalshi has no signal** — price absorbs the flow. | kalshi-market-scan | `reports/flow_predicts_outcome.json` | **1,376 settled markets**, 1.77M trades | to 08-03 | corr(flow, outcome−price) = **−0.052, p=0.053**; the residual, not the raw direction, is the right test | no survivors | n/a | **SETTLED** (null) |
| K012 | ⚠ **WORDING NARROWED 2026-08-09.** "Killed" reads as *no edge*; it means **can never be measured** — 22–48 settlements against the 481 needed. An unmeasurable family is not a refuted one. Original: **Economics series are killed on recurrence**, not on edge. | kalshi-market-scan | `docs/market_screen.csv`, `MORNING_REPORT.md` | `KXCPI`/`KXFED`/`KXGDP`: **22–48 settlements** | — | against **481** needed to detect a 5pp edge at 80% power | n/a | n/a | **SETTLED** (structural) |
| K013 | `KXBTC15M` is minted **at-the-money every 15 minutes**, pinning entry to the peak of the fee curve. | kalshi-market-scan | `docs/contract_spec.md` | `floor_strike` = prior window's `expiration_value` on **99.86% of 6,261 markets** | — | round trip pinned at **3.50¢**; measured from live books **4.1–4.5¢** | n/a | n/a | **SETTLED** — structural kill, matches the crypto section |
| K014 | The power bar is **481 settlements** for a 5pp edge, **2,084** to clear the 2.4¢ tennis cost bar. | kalshi-market-scan | `docs/GO_NO_GO.md` power calc | per-market P&L sd **0.391** measured on the real tape | — | this single number kills most of the exchange | n/a | n/a | **SETTLED** (arithmetic) |
| K015 | "Buying everything priced 0.60–0.95 with no wallet selection earns **+7.05pp ± 0.22** on n=98,766." | kalshi-market-scan | **none findable** — `docs/HYPOTHESIS_LEDGER.md` records the location as literally `inline` | claimed 98,766 positions from ~1,872 markets | — | **recomputed from scratch at +2.09pp, CI [−1.37,+5.35] gross, −0.29pp NET** | — | — | **RETRACTED — this is the same claim as [W011](#section-3--wallet-copy-study-polymarket-copy-trading)**, which already recomputed and killed it. Same effect, same n, same price band, two projects, two rows, and until 2026-08-03 two different statuses. See "the duplicate-claim trap" below |
| K016 | Deflated Sharpe was **deliberately not computed**. | kalshi-market-scan | `docs/HYPOTHESIS_LEDGER.md` | — | — | no Phase 7 sweep ran because nothing cleared Phase 1 + Phase 4, so there was no candidate. Computing it on a null "would be theatre" | n/a | n/a | **SETTLED** (a decision, and the right one) |

### What this section changes

**No verdict was overturned by ledgering it** — every verdict in the project was
already NO-GO and still is. What it buys is that K003, K005, K006 and K010 are
now visible to the same cross-check that governs every other project, instead
of living only in whichever document happened to be read.

### ⚠ The duplicate-claim trap — K015 is W011

Ledgering the project immediately produced a result that ledgering it was
supposed to produce, and it is worth stating on its own.

**K015 and [W011](#section-3--wallet-copy-study-polymarket-copy-trading) are the
same claim.** Same effect (**+7.05pp**), same sample (**n=98,766**), same price
band, described in two projects' documents in slightly different words:

| | K015, as written in `kalshi-market-scan` | W011, as written in `wallet-copy-study` |
|---|---|---|
| Claim | "buying everything priced 0.60–0.95 … +7.05pp ± 0.22" | "naive favourite-band buying earns +7.05pp" |
| n | 98,766 positions | 98,766 |
| Status **before** 08-03 | **UNVERIFIED** — "no artifact anywhere" | **RETRACTED** — recomputed at **+2.09pp [−1.37,+5.35] gross, −0.29pp net** |

`wallet-copy-study` had **already recomputed it from scratch and killed it.**
`kalshi-market-scan` went on describing it as the finding that reframes its
whole copy-trading block, and `kalshi-inplay-bot/audit/LEDGER.md` C042/R2
flagged it as the corpus's least-supported claim — none of them aware the
answer already existed one section away.

**The lesson is about the ledger, not the number.** A claim that travels between
projects gets a fresh row and a fresh status each time, and the weakest status
is the one that survives in whichever document a reader happens to open. Cross-
reference by *number and n*, not by project. It was found here only because the
two rows finally sat in the same file.

---

# SECTION 7 — bot-forensics (the night the live tennis bot made money)

**Added 2026-08-05.** Like Section 6 before it, this project had **no rows in
this ledger at all** until now, and it is the project whose conclusions the user
is most likely to act on — it is the only one about *money that actually moved*.

Artifacts: `bot-forensics/` — `FINDINGS.md` (Tasks 1–2), `VERDICT.md` (Tasks
3–5), `DECISIONS.md`, every run's stdout and CSVs committed under
`bot-forensics/out/`. Source records are the live account's own exchange files in
`kalshi-inplay-bot/`. **Every number below was independently re-run on
2026-08-05 and reproduced bit-identically** against the committed output.

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| **B001** | **The bot lost money over its whole life.** −$6.92 across 108 matches. | bot-forensics | `src/t2_master.py` → `out/t2_master.txt`, `out/master_match.csv` | **108 matches → 74 entry bursts** (the scanner fires everything qualifying in one pass, so same-burst matches share one feed state) | 07-27 05:58 → 07-28 21:00 UTC | mean **−$0.064/match**; burst-clustered mean −$0.094, **95% CI [−$0.97, +$0.78]**, t = −0.21 | n/a | n/a | **SETTLED** (null) — effective n is **74**, not 108 and not 1,237 fills |
| **B002** | **The hand-trading made the money; the bot did not.** Manual +$98.94, bot −$6.92. | bot-forensics | `src/t1c_classify.py` → `out/ticker_class.csv`; `src/t2_master.py` | bot 108 matches / manual 31 / mixed 1 | 07-25 → 07-28 | manual **+$98.94** on 31 matches vs bot **−$6.92** on 108; most of the manual gain predates the bot's first order | n/a | n/a | **SETTLED** — **the single most load-bearing correction in the project.** The account did go up; the bot is not why |
| **B003** | **The "profitable night" is a cut at the maximum of the equity curve, and the argmax is not a finding.** | bot-forensics | `src/t2b_nightday.py` → `out/t2b_nightday.txt`, `out/perm_buckets.csv` | 108 match P&Ls, 200,000 random reorderings | 07-27 → 07-28 | peak **+$32.19** after 60 matches; random reorder reaches it **p = 0.052**; before/after gap **p = 0.272**; a zero-drift process shows the same shape **85%** of the time | permutation | order-destroying null retains the true total and dispersion | **SETTLED** (null) — generalised into **[GUARDS.md](GUARDS.md) #17** |
| **B004** | Splitting on the clock instead of the curve: night beats day in **sign only**. | bot-forensics | `src/t2b_nightday.py` | night **n = 19 matches**, day n = 89 | 07-27 → 07-28 | night +$0.799/match vs day −$0.248; **Welch t = 1.54, p = 0.133** | see B005 | n/a | **SUGGESTIVE at best** — the direction the user remembers, at an n that cannot resolve it |
| **B005** | **0 of 13 permutation-tested buckets clear BH-FDR at 5%.** | bot-forensics | `src/t2c_costbar.py` → `out/t2c_costbar.txt` | 13 buckets (tier, 4h block, night/day), **200,000 shuffles each** | 07-27 → 07-28 | smallest p = **0.0477** (04–07 UTC, n = 5); **0 discoveries**; 12 of 21 buckets positive against a chance expectation of 10.5 (binomial p = 0.66) | **BH-FDR 5%** | n/a | **SETTLED** (null) — ⚠ **see B005a; this number is arm-dependent and the reports quote only this arm** |
| **B005a** | ⚠ **The parametric arm of the same test reports 3 discoveries, not 0, and it propagated to only one of four documents.** | bot-forensics | `src/t2b_nightday.py` → `out/t2b_nightday.txt` line 93; recorded in [GUARDS.md](GUARDS.md) #17 | **21** t-tested buckets (adds the tier×night interaction cells) | 07-27 → 07-28 | BH-FDR 5% gives **3 "discoveries"**: WTA\|day (n=4, **−$2.89**, t=−6.4), 04–07 (n=5, p=0.0002), Challenger\|night (n=6, p=0.0004). The permutation p for that same 04–07 bucket is **0.0477 — 240× larger** | BH-FDR 5% | n/a | **BROKEN as a test, and the 0 is the right answer** — a t-test on n=4–6 with small realised variance is wildly anti-conservative, one "discovery" is a *loss* bucket, and the other two are the same six trades seen twice. **The permutation arm supersedes it.** ⚠ **`GUARDS.md` #17 states this correctly** ("three buckets cleared on t-statistics and none survived label permutation"); **`FINDINGS.md`, `VERDICT.md` and `HANDOFF.md` all state "0 of 13" without naming the arm.** So this is a **propagation gap, not a suppressed result** — the reusable guard carried the caveat and the project's own three write-ups dropped it |
| **B006** | **The night/day comparison is confounded against the night at source.** | bot-forensics | `src/t2c_costbar.py` → `out/costbar_tier.csv`, `out/costbar_night.csv` | **27,083 recorder rows**, 342 markets | 07-27 23:01 → 07-28 13:49 UTC | mean spread ATP **1.17c** · WTA 1.24c · Challenger 1.57c · ITF-M 2.80c (night **5.26c**) · ITF-W 4.48c (**night 7.16c**) | n/a | n/a | **SETTLED** — overnight ITF books are **2–6× wider**. The bucket that looked better is the one with the worse book |
| **B007** | **The martingale is present in the profitable stretch, and it went 7 for 7.** | bot-forensics | `src/t2d_martingale.py` → `out/t2d_martingale.txt`, `out/multileg.csv` | 14 of 101 traded markets had >1 filled entry; **12 averaged down** | 07-27 → 07-28 | averaging-down 12 matches **−$16.43**; single-entry 94 matches **+$9.63**; **before the peak, 7 sequences, 7 winners, +$6.63**; after it ~−$23, SAGLEV alone −$8.79 | n/a | n/a | **SETTLED** — **the bot's entire loss is the twelve averaging-down sequences.** A run of small wins ended by one loss bigger than all of them is the martingale signature, and while running it is indistinguishable from skill |
| **B008** | **The score feed arrived after the market had already repriced.** Puts a magnitude on CH031. | bot-forensics | `src/t2d_martingale.py` → `out/lag_events.csv` | **4,398 score-change events**, 305 markets, 60 s polling | 07-27 → 07-28 | mean oriented move: placebo (−8→−6) **+0.18c** · (−6→−3) +1.39c · **(−3→0) +4.68c** · **(0→+3) +0.17c**. Only **2.6%** of repricing falls after the bot could see the score | n/a | placebo control at ~5 min | **SETTLED** — the placebo rules out ordinary momentum. Cannot separate feed lag from honest market anticipation at 60 s resolution, **and does not need to**: the entry signal arrived after the event it was meant to predict |
| **B009** | **The night's actual configuration, replayed over the backtest corpus, loses on every tier — worst on ITF, where it actually traded.** | bot-forensics | `src/t3b_proxy.py` → `out/t3b_proxy.txt`, `out/t3b_proxy.csv` | **13,658 market views**; ITF arm **6,135 trades / 2,599 matches** | 06-29 → 07-27 | ITF **−9.13c/trade, −$1.98/match, t = −26.0**; ITF holdout −8.77c on 1,045 matches, t = −16.0; all tiers −8.08c. No proxy threshold turns it (0c → 30c all −8.6 to −9.7) | n/a | **yes — train/holdout split** | **SETTLED** — **the decisive test, and it refutes verdict D.** Not an underpowered null: a large, precisely measured loss |
| **B010** | The night's config was **not badly chosen — it is just in a losing family.** | bot-forensics | `src/t3_replay.py` + `src/t3b_proxy.py`; sweep from `kalshi-inplay-bot/backtest/` | 481 configurations | 06-29 → 07-27 | ranks ~**55th of 481** on the tight-book tiers (−5.64c) and **between random entry (−8.28c) and S1 (−9.36c) on ITF**. **0 of 481 profitable** | n/a | yes | **SETTLED** — corroborates CH001/R5: tuning was never the problem |
| **B011** | The live 39 hours are **consistent with the backtest, not in tension with it.** | bot-forensics | `VERDICT.md` §"the live 39 hours" | live n = 108 matches vs backtest n = 1,616 matches | 07-27 → 07-28 | live −$0.064/match (se 0.284) vs backtest −$0.755 (se 0.077); difference $0.69, se 0.294, **t = 2.35** | n/a | n/a | **SETTLED** — the live window ran ~2σ better than its own backtest predicts. **That is what a good run looks like**, and the large sample is the one to believe |
| **B012** | **The stop loss is the single most expensive component**, and four independent files now agree. | bot-forensics | `out/rerun_high_sweep.txt`, `out/rerun_high_entry.txt`, `out/rerun_longshot.txt` + Arm A | `high_entry` cell n = 95; 480-config sweep; 13,658-view replay | 06-29 → 07-27 | `high_entry` **+0.62c → −3.77c** on identical trades when an 80c stop is added; S2 buy-and-hold (−2.29c) beats S1's exit ladder (−9.36c) by **7.07c**; removing the stop is the best single change in Arm A (−6.47c → −4.59c) | n/a | partial | **SETTLED** (direction) — **contradicts the live bot's design.** The bot stopped out of **77%** of backtested and 30 of 71 live trades. Closes `kalshi-inplay-bot/audit/LEDGER.md` **R6** — those outputs are now on disk |
| **B013** | Kalshi tennis settles **strictly binary**; a retirement does *not* settle "at the number". | bot-forensics | `kalshi-inplay-bot/_settled_all.json` scan in `src/t4b_verify.py` → `out/t4b_verify.txt` | **9,352 settled tennis markets** | to 07-28 | **4,676 `yes` / 4,676 `no`, exactly mirrored, zero non-binary settlements.** A 43c holder at retirement is paid **100** | n/a | n/a | **SETTLED** (structural) — **refutes a YouTube claim in this repo's own corpus** (`ELpX7I0sPtc`). Cuts toward holding: the windfall is invisible to a stop. Another entry against B012's stop |
| **B014** | **Roughly thirty people independently built this same bot in six months and none publishes a settled P&L.** | bot-forensics | `src/t4_github.py` → `out/t4_github.txt` (repo-level detail gitignored — this repo is public) | **32 distinct Kalshi/Polymarket tennis repos** | retrieved 08-05 | **30 of 32 created in the last 180 days**; 135 stars total, **129 of them on one repo**; every repo stating a mode states **paper**; 0 settled P&L | n/a | n/a | **SETTLED** (observational) — the finding is **the crowd, not any repo.** Consistent with the adverse-selection result already in STATUS.md |
| **B015** | **Nobody documents the overnight-vs-daytime pattern in prediction-market sports books.** | bot-forensics | `src/t4_github.py`, `src/t4c_youtube.py` → `out/t4c_youtube.txt` | 2 YouTube corpora (**1,135 videos, 39.8M chars**) + 4 targeted GitHub queries | searched 08-05 | "overnight" appears **142 times across 75 videos** and **every hit is equity/futures session language**; 4 GitHub queries returned 1 result between them | n/a | n/a | **SETTLED** (null search) — a canary term asserts the scan is alive, after a first pass read the wrong column and cleanly reported a fake 0 |
| **B016** | ⚠ **A free ITF data source may exist, reopening a thread closed on data availability.** | bot-forensics | `src/t4_github.py`, `src/t4b_verify.py` → `out/t4b_verify.txt` | 11 official client libraries, all pushed within 2 days of 08-05 | checked 08-05 | `api.livetennisapi.com/api/public/v1/health` returns **200, no key**; all data endpoints **401**. Free tier *advertises* ATP+WTA+Challenger+**ITF** live scores | n/a | n/a | **SETTLED 2026-08-06 by [B021](#added-2026-08-06--the-itf-answer-and-the-player-feature-sweep) — the free tier DOES return ITF (7,786 tournaments).** ~~UNVERIFIED — vendor ADVOCACY.~~ Settling it needed an account, which is the user's to create. **Reopens data availability only** — B009 says ITF economics are the worst of any tier. **2026-08-05: endpoint paths verified by 401-not-404 on 5 routes, and the test is written and tested** — `src/t5_itf_probe.py` + [`ITF_CHECK.md`](bot-forensics/ITF_CHECK.md). Sharpened reading: the free tier's stated limits are **capability- and rate-based with no tour restriction stated anywhere**, so free ITF is plausible — but the site never affirms it either, so it stays an inference the vendor wrote |
| **B017** | The SAGLEV re-entry legs were **749 s apart, not 24 s**. | bot-forensics | `src/t2d_martingale.py` → `out/multileg.csv` | 3 legs, 1 match | 07-28 | entry-to-entry gap **12–13 min**; **no re-entry anywhere in the record was under 60 s** from the prior entry. The 24 s/23 s figures are stop-fill→re-entry gaps | n/a | n/a | **SETTLED** — and a **correction to STATUS.md** and to `tennis_engine.py`'s post-mortem comment. The shipped fix (`reentry_cooldown_sec = 900`) still blocks all twelve, so **no patch changes** — but "24 seconds later" overstates how frantic it looked |
| **B018** | **The bankroll was stepped up by hand during the winning run.** | bot-forensics | `src/t2_master.py`, order sizes in `out/master_ticker.csv` | 113 orders on 07-28 | 07-27 → 07-28 | implied stake ~$5.1 → ~$5.9 → **exactly $6.25** from 07:44; `$6.25 = 125 × 5%` reproduces **113 of 113** sizes | n/a | n/a | **SETTLED** — a **discretionary size-up on a winning run**, layered on the strategy. The profitable early trades were sized **smaller** than the later losing ones |
| **B019** | A notional-only bot/manual classifier **misclassified the single largest winner.** | bot-forensics | `src/t0c_botsig.py` (kept as evidence) vs `src/t1c_classify.py` | 1 order of 389 fills | 07-27 | a hand-placed 15.5-contract **NO** longshot at 6c cost $0.93 — bot-sized — and returned **+$14.51**, roughly half the apparent bot total | n/a | n/a | **BROKEN classifier, caught and replaced.** The rule has to be **structural** (`side == yes` ∧ 10–90c ∧ $4.60–6.30 notional). **A classifier that misfires on the largest winner is not a classifier** |
| **B020** | **"Sackmann upstream is 404" is too strong** — a live mirror exists. | bot-forensics | GitHub API check in `src/t4b_verify.py` → `out/t4b_verify.txt` | 5 repos checked | checked 08-05 | `tennis_atp`, `tennis_wta`, `tennis_slam_pointbypoint` **are** 404 — but **`JeffSackmann/tennis_MatchChartingProject` is live, 399★**, and `Aneeshers/tennis-sackmann-archive` mirrors the point-by-point data, pushed 2026-06-25 | n/a | n/a | **SETTLED** — and a **correction to STATUS.md**. The data is **not unrecoverable**; `kalshi-tennis/data` is not the only copy |

### Added 2026-08-06 — the ITF answer, and the player-feature sweep

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| **B021** | **A free ITF data source DOES exist. The thread that was closed on "no free ITF source" was closed on a false premise.** | bot-forensics | `src/t5_itf_probe.py`; live API call with the user's free key | **7,786 ITF tournaments** of 10,172 total | checked 08-06 | `GET /tournaments?tour=itf` on a **free** key returns `total: 7786`. Surface and tour are populated per tournament | n/a | n/a | **SETTLED — supersedes B016, which was UNVERIFIED.** Reopens **data availability only**; B009 says ITF economics are the worst of any tier |
| **B022** | ⚠ **The vendor's advertised free-tier rate limit is wrong by 10×.** | bot-forensics | `/usage` response | 1 account | 08-06 | site says **1,000/day**; the API's own `/usage` returns `limits: {per_day: 100, per_minute: 30}` | n/a | n/a | **SETTLED** — a primary-source contradiction of the vendor's own marketing. Anything planned against a 1,000/day budget is planned wrong |
| **B023** | **Pre-match player features add nothing to Kalshi's opening price.** | bot-forensics | `src/t6_features.py`, `src/t7_sweep.py` → `out/t7_sweep_*.csv`, [FINDINGS_T7.md](bot-forensics/FINDINGS_T7.md) | **6,519 events** (4,563 train / 1,956 holdout), **2,008 cells** | 06-29 → 07-27 | **2 BH discoveries; the same machinery on shuffled data yields 4.1 on average.** Real max\|t\| **4.17** vs null mean **4.40** | **BH-FDR 5%, one denominator over all 2,008** | **yes, time-ordered 70/30** | **SETTLED** (null) — pre-registered before running. **A sweep that finds less than its own null has found nothing** |
| **B024** | The one surviving signal — "buy the heavy favourite" — **is a wide-book quoting artifact, not a mispricing.** | bot-forensics | `src/t7_sweep.py`; spread-stratified table in FINDINGS_T7 | 952 events ≥80c | 06-29 → 07-27 | residual by opening spread: **≤2c → +1.18pp (t=0.64)** · 2–4c +4.87pp · 4–8c +3.50pp · **>8c +7.92pp**. Monotonic in spread; gone where tradeable | within B023's family | holdout same sign, **net at ask −0.77c** | **SETTLED** — a mid quoted inside an 11.8c spread is not a price. Tight-book MDE **5.15pp**, so a real effect is not excluded, only unevidenced |
| **B025** | ⚠ **Two bugs in this session's own analysis code, caught before publication.** | bot-forensics | `src/t7_sweep.py` docstrings + FINDINGS_T7 | — | 08-06 | (a) the first permutation null shuffled within **tier only**, manufacturing a −38pp residual in every high-price cell → **1,010 false discoveries of 2,008, max\|t\| 22**; (b) entries priced at the **mid**, worth 2–3c/contract — **larger than every effect measured** | n/a | n/a | **BROKEN, fixed, and recorded.** The tell on (a) was that the null was *worse* than the real data. Both bugs pushed toward a false positive |
| **B026** | ⚠ **Possible tension with K009**, unresolved. | bot-forensics | FINDINGS_T7 §"one tension" | 691 train events ≥80c vs K009's 762 matches | — | K009: favourite-longshot bias **does not exist** on Kalshi (−0.67pp). This study: **+4.31pp at ≥80c** at the open | — | — | **RESOLVED 2026-08-06 by [B027](#b027) — the two agree, and K009 is right.** ~~UNVERIFIED, an open contradiction.~~ The full calibration curve on **tradeable books shows 0 of 10 price bands deviating**, mean residual **+0.03pp**. t7's +4.31pp was a wide-book quoting artifact, exactly as the offered reconciliation proposed. **SETTLED** |

<a id="b027"></a>

| ID | Claim in plain English | Project | Artifact (script + output) | n + unit | Date range | Effect + CI | FDR? | Holdout? | STATUS |
|---|---|---|---|---|---|---|---|---|---|
| **B027** | **Where Kalshi tennis is liquid, its opening price is calibrated across the entire price range. Where it is wide, it is not — and that is where every apparent edge in this repo has come from.** | bot-forensics | `src/t8_calibration.py` → `out/t8_calibration.txt`, `out/t8_calibration.csv` | **6,519 events**; 1,531 tradeable (spread ≤2c), 3,332 wide (>4c) | 06-29 → 07-27 | **tradeable books: 0 of 10 price bands have a Wilson CI excluding zero**, pooled residual **+0.03pp, se 1.09pp, t=+0.03**. Wide books: **2 of 10** deviate (40–50c **−4.96pp**, 80–90c **+5.16pp**) | Wilson CI per band | n/a — full sample, both arms pre-declared | **SETTLED.** Resolves B026 in K009's favour. Per-band tight-book n is 114–208 so each band alone is weak (±5–12pp); the **pooled** tight-book figure is the well-powered one |

### The verdict these rows add up to

**A and B jointly** — variance plus a martingale that happened to win. **C** (the
stale-score bug) is real and measured (B008) but explains why the strategy has no
edge, not why one run went up. **D is refuted by B009**, and that is the
strongest statement in the project: the exact condition proposed — ITF,
overnight — is the *worst* cell in the whole test.

### What ledgering this project immediately paid for

Exactly as in Section 6, putting the rows in one file produced findings that
could not be seen from inside the project:

1. **CH044 was stale in two directions.** It read *"never diagnosed, never
   fixed"*. It was diagnosed on 08-03 (a martingale, not a sizing bug) and
   **B007 then showed it was never confined to one match** — twelve sequences,
   not one. Row corrected inline.
2. **CH031 had no magnitude.** It recorded the staleness bug as a fact for
   months; **B008 measures it** at 97.4% of repricing already complete. Row
   corrected inline.
3. **B005a is a reporting selection nobody would have caught from the prose.**
   Three of this project's own documents state "0 of 13" while its own committed
   output prints "3" from a different arm. The 0 is correct and the 3 is the
   broken test — but a reader running the script sees the 3.

> **The pattern to notice across B001, B002 and B009.** The user's memory was
> accurate about the *account* and wrong about the *cause*. The account went up
> ~$99; the bot lost $6.92 while it did. **"It worked and then it stopped
> working" was, on measurement, the shape of a fair coin** — which is why it
> became GUARDS #17 rather than a strategy note.

---

# SECTION 8 — market-selection (merged 2026-08-06) and bot-hunt

**Added 2026-08-06 by the full-programme audit.** Both projects had **zero rows
in this ledger**. `market-selection` kept its claims in
[market-selection/LEDGER_ADDITIONS.md](market-selection/LEDGER_ADDITIONS.md),
whose own header says *"Merge into LEDGER.md at the next inventory"* — **it was
never merged.** `bot-hunt` has four results documents and had no rows at all.

> ### ⚠ It paid on the first pass, for the third time out of three
>
> Section 6 found **K015 = W011**. Section 7 found **B005a** and two stale CH
> rows. This section found **two live defects, and one of them is load-bearing
> in a pre-registration written the same morning.**

### ⚠⚠ M011 is SUGGESTIVE and is quoted as established fact in eight places

<a id="m011"></a>

| ID | Claim | STATUS |
|---|---|---|
| **M011** | **"Kalshi's MLB moneyline already tracks the free DraftKings line."** median \|Kalshi mid − de-vigged DK\| **0.37¢**, p90 0.75¢, max 1.94¢, **0 of 26 exceed the cost bar** | **SUGGESTIVE** |

The row's own author wrote the caveat and it is exact:

> *"**SUGGESTIVE** — one snapshot, not a closing line, DK is retail not Pinnacle."*

**n = 26 game sides = 13 games. One snapshot. Against a retail book.** And it is
the corrected form of **M002**, a retraction which at n = 4 games said the
*opposite* ("6 of 8 game sides exceed the cost bar").

It is now cited as a settled fact in **eight** places across `bot-hunt`:

| where | what it is doing there |
|---|---|
| `PREREGISTRATION.md` §0 | **the justification for making MLB the negative control** — *"MLB moneyline is known efficient"* |
| `PREREGISTRATION.md` §4 | one of three measurements grounding "I expect every strategy to fail" |
| **`PREREGISTRATION_DEVIG.md` §4.2** | **one of "four independent measurements" said to establish MLB is efficient — used to set an ASYMMETRIC decision bar against the test. Written 2026-08-06, hours before this audit found the row.** |
| `PREREGISTRATION_DEVIG.md` §7 | listed under "what I expect" |
| `RESULTS_CROSSVENUE.md` §2 | part of the "fourth independent confirmation that Kalshi is the sharp line" chain |
| `PRIOR_ART.md`, `SHORTLIST.md` ×2, `FINDINGS.md` | family ranking and mechanism selection |

**What actually changes, stated precisely.** The *direction* is corroborated
independently — T012 on tennis (r 0.9878, n=809), B027 on tennis calibration
(0 of 10 tradeable bands), and `bot-hunt`'s own **RESULTS_DEVIG** on MLB itself
(a 2.75¢ cost bar against a 2.01pp Pinnacle overround, q = 0 of 17). So no
verdict flips. **What was wrong is the word "known", and the count "four
independent measurements" — one of the four is a 13-game snapshot against a
retail book, and it should have been named as such in a document whose whole
purpose is to fix the standard of evidence in advance.**

### ⚠⚠ M001 is RETRACTED and `crypto/MM_RESULTS.md` still states it as a blocker

| ID | Retracted claim | Why it died |
|---|---|---|
| **M001** | *"Kalshi's `/orderbook` returns empty; order-book depth is not public."* Held by a prior session and **independently reproduced on 85 markets**. | Both readings parsed a key that does not exist. The response has exactly one top-level key, **`orderbook_fp`**, holding `yes_dollars`/`no_dollars`. Depth is **public, free, unauthenticated, 20 levels a side.** |

**`crypto/MM_RESULTS.md` §0.2 still states the retracted version as a headline
finding**, in bold, as one of two reasons the market-making study could not
proceed:

> *"❌ Kalshi does not expose order-book depth publicly at all … So this is not a
> gap in our recording — the depth is not public. … Full-depth Kalshi book
> reconstruction is not available to us, now or historically."*

**Re-verified live 2026-08-06 on `KXBTCD-26AUG0620-T73299.99`:** the response
carries `orderbook_fp` with `no_dollars` at **16 price levels**. `bot-hunt`'s
recorder has been reading it correctly this whole time
(`bot-hunt/src/venues.py::k_orderbook`).

> **This is why the crypto market-making thread stalled, and the premise was
> false.** It does not by itself prove market making works — the decisive
> adverse-selection measurement is still unrun (C025, and the audit's D2) — but
> *"the data does not exist"* was never true. See the audit's ranked item #2.

### The remaining market-selection rows, merged by reference

**M001–M027** are carried in full at
[market-selection/LEDGER_ADDITIONS.md](market-selection/LEDGER_ADDITIONS.md) and
are now part of this ledger's denominator. Six retractions (**M001–M004, M005r,
M006r**), 17 SETTLED, 4 SUGGESTIVE (**M011, M019, M022, M026**), 1 UNVERIFIED
(M016), 1 CANCELLED (M025).

Three that matter beyond their own project:

- **M009 / M010** — *"the Kalshi trade tape retains **exactly 69 days and rolls
  daily**"*, bisected at 13 ages. ⚠ **RESOLVED THE SAME DAY, AGAINST M009. See
  BH009 below.** A third bisection on 2026-08-06 put the boundary at
  **2026-05-25 on both the listing and the tape — 73 days old, and unmoved
  across three measurements four days apart while the "window" grew 69 → 71 →
  73.** A rolling 69-day window would sit at 2026-05-29. **M009's 69 was the age
  of a fixed date on the day it was measured**, and M010's arithmetic
  consequence — *"the whole overlap is gone by 2026-08-19"* — **does not
  follow.** M009 → **RETRACTED**, M010 → **RETRACTED (its premise)**.
  > **Caveat, stated because it cuts against the convenient reading:** a fixed
  > boundary is not a promise. Three points over four days establish that it is
  > not rolling *now*; the mechanism is unknown (it looks like a data-migration
  > cutover), and a fixed boundary can vanish in one step rather than sliding.
  > **It removes a deadline; it does not create a guarantee.**
  >
  > **A trap in the probe itself, recorded because a naive read is nonsense:**
  > `KXBTCD` and `KXITFMATCH` returned "earliest = 1 day / 41 days". Both hit the
  > **8,000-market pagination cap**, so their "earliest" is where the page ran
  > out, not where the data ends. **Only the six families that did *not* hit the
  > cap carry information — and all six read exactly `2026-05-25`.**
- **M005** — order-book depth is public, 20 levels a side, 92.2% of snapshots
  carry depth. The positive form of M001.
- **M017** — `football-data.co.uk` serves a **wrong-country file at HTTP 200**:
  `COL` ≡ `POL` ≡ `BOL` are byte-identical (Poland). A naive probe "confirms"
  Colombian odds that do not exist. This is GUARDS #13 in the wild.

### bot-hunt — BH001–BH014

| ID | Claim in plain English | Artifact | n + unit | Effect | STATUS |
|---|---|---|---|---|---|
| **BH001** | Pinnacle's guest API returns live priced markets **unauthenticated and free** — 27,582 soccer, 3,728 tennis, 1,920 baseball, 643 esports, each with `maxRiskStake`. | `src/probe_pinnacle.py` → `reports/pinnacle_probe.json` | 6 sports | only **3 of 3,195** archived repos reference it | **SETTLED** (API fact) |
| **BH002** | **Nothing survives the structural grid on esports, and nothing survives on the MLB control.** | `src/run_grid.py` → `reports/grid_train.json`, [RESULTS.md](bot-hunt/RESULTS.md) | **2,779 esports events** / 909 MLB, 260 + 148 cells | **0 cells with a CI above zero**; 120 survive BH-FDR and **every one is negative** | **SETTLED** (null) |
| **BH003** | **`close_time` is when the market SETTLES, not when play starts** — the pre-registered −60 min anchor was VOID at 13.96% extreme quotes, 99.7% correct. | Amendment A1, `src/anchor_sweep.py` | 2,779 events × 10 leads × 4 series | anchor moved to a uniform **−24 h**, monotone-clean | **SETTLED** — the gate fired before any return printed |
| **BH004** | **Esports' real pre-match cost is 3–6× the figure the shortlist ranked it on.** | `src/spread_vs_lead.py` → `reports/spread_vs_lead.json` | all settled markets, 4 series | CS2 p90 spread **12¢ → 69¢** from 15 min to 24 h; mean triples. MLB is 1.0¢ at every lead *(⚠ see BH013)* | **SETTLED** — the most useful thing the grid produced |
| **BH005** | **Resting orders do get filled: 29–36% strict (trade-through), 63–69% permissive.** | `src/h10_passive.py`, `h10_stability.py` → [RESULTS_H10.md](bot-hunt/RESULTS_H10.md) | 12,959 simulated orders, **81 events**, ~13M L2 rows | stable across nested prefixes; the pre-registered <20% falsification **fails** | **SETTLED** — the one number H10 produced |
| **BH006** | H10's net P&L and adverse selection. | same | 81 events | net P&L **sign-flips −1.48 … +2.55¢** across nested prefixes; adverse selection **decays −14.04 → −4.03pp** as data is added | **BROKEN as evidence** — decay toward zero is the artifact signature; GUARDS #10 flags the one strengthening quantity as contamination, not a finding |
| **BH007** | De-vigged Pinnacle vs the Kalshi ask on esports: **the median buy edge is negative under every method.** | `src/crossvenue_join.py` → [RESULTS_CROSSVENUE.md](bot-hunt/RESULTS_CROSSVENUE.md) | 5,334 paired observations, **13 events**, median 7 s alignment | multiplicative −0.72¢ · power −0.75¢ · worst-case −1.64¢; Pinnacle overround 4.82pp | **SUGGESTIVE** — 13 events, **no settlement joined**, so it measures price agreement and not P&L. Its own §4.3 says so |
| **BH008** | **Polymarket esports is ~96% derivative markets.** | `src/poly_crossvenue.py` | 436 recorded (slug, outcome) pairs | maps/game-N **247** · props 111 · handicaps 62 · **plausible moneylines 16** | **SETTLED** — pairing a moneyline to a handicap is the classic phantom |
| **BH009** | Kalshi's retention is a **fixed calendar boundary at 2026-05-25**, not a rolling window — **and it is the same boundary on the market listing AND the trade tape.** | `src/probe_historical.py`, **`src/retention_rebisect.py` → `reports/retention_rebisect.json`** | 8 unrelated families + 11 tape ages, probed at one minute | **third bisection: 08-02 → 69 d, 08-04 → 71 d, 08-06 → 73 d, boundary unmoved at 2026-05-25 throughout.** Tape has trades at 73 d and **zero at 74 d**; 6 of 8 families read exactly `2026-05-25` | **SETTLED 2026-08-06** — ⚠ **this REFUTES M009/M010's "exactly 69 days, rolls daily".** The 69 was the *age of a fixed date on the day it was measured*. **The 2026-08-19 deadline does not exist** |
| **BH010** | ⚠ **WORDING NARROWED 2026-08-09.** This measures **what Kalshi's retrievable tape holds**, not how much soccer exists or how good it is. The 152-event count killed the S. American families *as a backtest target on this exchange's history*. It is **not** a statement about soccer — the 2026-08-09 census found **606 soccer series, 88,526 markets, 15.3bn contracts**. Original: Retrievable settled **events** by family, against LEDGER **K014**'s 481-event bar. | `src/dimension_e.py` → `reports/dimension_e.json` | 5 families | ITF 8,000/7,636 (16.6×) · CS2 1,648 (3.4×) · WTA/ATP 974/942 (2.0×) · MLB 907 (1.9×) · **all five S. American soccer series 152 (0.32×)** | **SETTLED** — kills the prior #1 entry on an axis it was never ranked on |
| **BH011** | **The de-vig test's cost bar is larger than the entire vig it removes.** | `src/devig_power.py` → `reports/devig_power.json`, [RESULTS_DEVIG.md](bot-hunt/RESULTS_DEVIG.md) | **17 joined MLB games**, 21 joined events | Pinnacle MLB overround **2.01pp**; Kalshi cost bar **2.75¢** at 50¢; qualifying rate **q = 0 of 17**; best per-event net gap **choosing entry with hindsight −0.91¢** | **SETTLED** (structural) — a 5¢ edge needs 4,356 events ≈ **1.8 MLB seasons**; no settlement was joined |
| **BH012** | **`close_time` on a LIVE Kalshi MLB market is the game start plus exactly 72 h.** On settled markets Kalshi rewrites it to the true settlement instant (2.4–3.2 h after start). | `src/mlb_scope.py`, `devig_power.py` | **94 of 94** active markets at 72.00 h; 1,830 finalized at 2.4–3.2 h | start derived from the ticker instead, **exact against Pinnacle's `starts_utc` on 22 of 22** | **SETTLED** — third Kalshi time field to mislead this repo, after BH003 and T010 |
| **BH013** | ⚠ **`RESULTS.md` §3's "`KXMLBGAME` is 1.0¢ at every lead" is a CANDLE measurement.** | `src/mlb_scope.py` → `reports/mlb_scope.json` | 12,720 recorded book snapshots, 120 tickers, 100% two-sided | recorded live touch is **median 2.0¢, p90 7.0¢**. The strategy pays the touch | **SETTLED** — correction to BH004's MLB row, marked inline rather than deleted |
| **BH014** | `record.py` probed `mkts[:60]` in Kalshi's **undocumented** listing order. | `src/record.py` diff, `reports/mlb_scope.json` | 214 cycles, 122 MLB tickers | `KXMLBGAME` lists 85–104 against a cap of 60; snapshots per ticker ran **min 1, p25 25, median 94** — the server decided which ~40 got no book | **BROKEN, fixed 2026-08-06** — now sorted by `close_time` ascending |

### Tally after this section

| Status | was | **now** |
|---|---|---|
| **RETRACTED** | 45 | **51** (+6, all `market-selection`: M001–M004, M005r, M006r) |
| SETTLED | 148 | **175** (+17 M, +10 BH) |
| SUGGESTIVE | 31 | **36** (+4 M, +1 BH) |
| UNVERIFIED | 28 | **30** (+1 M, +1 BH) |
| BROKEN | 9 | **11** (+2 BH) |
| CANCELLED | — | **1** (M025) |
| **Total** | 261 | **304** |

> **The directional prior held for the 47th time.** All six newly-merged
> retractions shrank the edge or removed a premise: **M002** took MLB from "6 of
> 8 sides beat the cost bar" to **0 of 26**; **M005r** removed the entire stated
> mechanism of what had been the top-ranked shortlist entry; **M006r** turned a
> 79%-exceed reading into an uninterpretable one. **Still not one correction
> anywhere in this repo has ever revealed a larger effect.**

---

## What is SETTLED enough to build on

Only these. Everything else is either negative, underpowered, or void.

1. **Kalshi is a sharp line on tennis** (T012, T013) and **efficiently priced on
   crypto ladders** (C010). Both measured against clean benchmarks, both with
   adequate n, neither dependent on any leaking anchor.
2. **Cost arithmetic** — Kalshi's fee formula (CH034 taker side), Polymarket's
   true fee `0.10·min(p,1−p)` (C004, independently reproduced), and the 3.61pp
   tennis cost bar (S004). Exact-decimal, unit-tested, reproduced across projects.
3. **Wallet skill on Polymarket persists out of sample** (W001, W002) — but the
   copyable fraction is smaller than the spread (W003, W004) and shrinking (W005).
4. **Trait statistics collapse when residualised against overall skill** (T004),
   on 3.4M rows with a positive control and a null. This settles the belief the
   entire player-model direction rested on.
5. **The guards themselves** — see [GUARDS.md](GUARDS.md). These are the most
   reusable output of all four projects.

## What is negative and should stop

- Tennis set-1 overshoot: real undershoot, **uncollectable** against the cost bar
  (S001, S004, S005, S006), and the sample cannot resolve it (S021).
- Crypto ladder modelling: **no model beats the mid** (C010), with a validated
  positive control proving the test could have found an effect (C008).
- Polymarket copy trading: **do not build the bot** (W003–W005).
- Stage 0–5 player model: **the model loses to the bookmakers** (T006). Gate failed.
