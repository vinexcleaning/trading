# GUARDS.md — the reusable part

Every canary, control and check that exists in any project, where it lives, and
which projects have it. **This is the most transferable output of all four
projects.** The strategies all died; the guards are what caught them dying, and
several caught errors that would otherwise have shipped.

Each guard below is listed with: what it tests, the null, the artifact, and the
coverage table.

## Coverage at a glance

| Guard | set1_overshoot | crypto | wallet-copy-study | kalshi-tennis | desktop bot / v3 |
|---|---|---|---|---|---|
| 1. Selection canary (3-valued) | ✅ enforced at build | ➖ audited clean, not enforced | ✅ equivalent | ⚠️ retro-audited, 2 UNSAFE found | ❌ **presume void** |
| 2. Within-match leak canary | ✅ | ✅ | ✅ | ✅ (found the leak) | ❌ |
| 3. Synthetic null | ✅ | ✅ | ✅ | ❌ | ❌ |
| 4. Positive control (planted effect) | ✅ | ✅ (15% and 5%) | ➖ implicit | ✅ (Stage 3 traits) | ❌ |
| 5. Deliberate-leak diagnostic | ✅ | ✅ | ❌ | ✅ (anchor sweep) | ❌ |
| 6. Exact-decimal fee arithmetic | ✅ | ✅ | ✅ (empirical) | ✅ **fixed 08-03** | ✅ **fixed 08-03** |
| 6b. **Anti-reimplementation guard** (repo-wide) | ✅ enforced repo-wide by [`common/tests/test_no_fee_reimplementation.py`](common/tests/test_no_fee_reimplementation.py) — one test covers every project | | | | |
| 7. Per-market P&L decomposition | ✅ exact identity | ✅ | ✅ | ❌ | ❌ |
| 8. Effective sample size | ✅ (day-clustered) | ✅ (event-clustered) | ✅ (market/series-day) | ➖ partial | ❌ |
| 9. Guard-rot test | ✅ | ❌ | ❌ | ❌ | ❌ |
| 10. Pre-registration before seeing numbers | ✅ | ✅ | ✅ | ❌ | ❌ |
| 11. BH-FDR across the whole ledger | ✅ 97 rows | ✅ 101 tests | ✅ per family | ✅ 43 segments | ❌ |
| 13. Content-assert, not call-assert (a 200/exit-0 is not a result) | ✅ `frames.is_flat` | | | | |
| 14. `robots.txt` `Allow:` implemented (longest match wins) | ✅ `find_sources.robots_allows` | | | | |
| 15. A 404 never establishes death | ✅ `unify_currency._dead` | | | | |
| 16. Membership table, so dedup cannot decide an overlap statistic | ✅ `hn.membership` | | | | |
| 12. Content-level recorder health check | ✅ | ⚠️ specified, status unknown | n/a | n/a | ❌ **check first** |

✅ present and enforced ➖ present but weaker ⚠️ partial or unverified ❌ absent

---

## 1. The selection canary — P(kept side wins) = 0.50

**The single most valuable guard in the repo.** It is the one that caught the
bug that voided three phases of work.

**Source:** [`set1_overshoot/src/leakguard.py`](set1_overshoot/src/leakguard.py)
**Tests:** [`set1_overshoot/tests/test_leakguard.py`](set1_overshoot/tests/test_leakguard.py) — 9 tests, all passing
**Audit:** [`set1_overshoot/SELECTION_AUDIT.md`](set1_overshoot/SELECTION_AUDIT.md) — 315 occurrences across 4 codebases

### What it tests

When a market lists two mirrored sides (Kalshi lists one market per player), you
must dedupe to one. **Whichever field orders that choice must not know the
answer.** The null is exact: over mirrored pairs, P(the kept side wins) = 0.5000.

### Why it exists

`p0_universe.py` deduped by keeping the higher-`volume_fp` side. That looks like
a tie-break. It is a coin weighted by the outcome — the winning side attracts
more volume. Measured:

| Rule | P(kept wins) | z | Verdict |
|---|---|---|---|
| higher `last_price_dollars` | **0.9989** | **+140.3** | catastrophic — it *is* the answer |
| higher `open_interest_fp` | **0.5558** | **+15.7** | unsafe |
| higher `volume_fp` — **the bug** | **0.5356** | **+10.0** | unsafe |
| higher `liquidity_dollars` | 0.5031 | +0.88 | **UNTESTABLE** — see below |
| **first ticker alphabetically — the fix** | **0.4969** | **−0.88** | clean |
| API listing order (kalshi-tennis) | 0.5050 | +1.44 | clean |

The two orientations disagreed by **25.5pp**. Everything downstream was void.

### The three-valued verdict — PASS / FAIL / UNTESTABLE

This is the part most implementations get wrong, and v1 of this file got it
wrong too.

`liquidity_dollars` scored z = +0.88 and was **recorded as a clean alternative
rule**. It is not clean. The field reads 0 on almost every settled tennis
market, so the rule almost never actually chooses anything — the tie-break does
the work. **Any mostly-null field passes a correlation test for free.**

So the guard returns three values, and **UNTESTABLE is never rendered as a
pass**:

```python
Z_MAX        = 4.0    # ~1 in 16,000 two-sided
MDE_MAX_PP   = 2.0    # a rule that cannot see a 2pp bias is untestable
MIN_DISCRIM  = 0.10   # a rule that decides <10% of cases is not the rule
```

| Verdict | Condition | Meaning |
|---|---|---|
| **UNTESTABLE** | `frac_discriminated < 0.10` | *"Innocence by emptiness is not innocence."* |
| **UNTESTABLE** | `MDE > 2.0 pp` | too few decided pairs to detect a bias that would matter |
| **FAIL** | `\|z\| > 4` | the rule reads the outcome |
| **PASS** | otherwise | |

### The variation check

`check_side_choice(kept_won, discriminated=...)` takes a second array: **True
where the rule's field actually differed between the two sides.** Where it did
not, the choice fell through to the tie-break and tells you nothing about the
rule. `n_eff` is computed on the discriminating subset only, and the reported
statistic is `P(kept wins | the rule actually decided)`.

Omit `discriminated` only when the rule discriminates by construction (ticker
order always does).

### The filter form

Same module, `check_selection(mask, outcome, implied)`. Different null:

> **A filter may change *who* is in the sample. It may not change *how well the
> market prices them*.**

The statistic is the **calibration residual** `outcome − implied`, not the raw
outcome rate — because the residual is what every downstream result actually
rests on. A filter that selects strong favourites shifts the outcome rate
legitimately; it must not shift the residual.

Both arms must be large enough to resolve a 2pp shift, or the result is
UNTESTABLE. Readings from the audit:

| Filter | Kept residual | Dropped residual | z | Verdict |
|---|---|---|---|---|
| `plausible` duration 25–330 min | +0.0029 (n=16,258) | +0.0294 (n=682) | −2.59 | borderline, below \|z\|=4 |
| leaking-anchor spread ≤10¢/5¢/2¢ | — | — | +0.11 / 0.00 / +0.14 | **inconclusive and moot** — only 502 joined rows |
| label join (set1) | +0.0597 (n=604) | +0.0166 (n=2,832) | **+2.15** | **UNTESTABLE**, MDE 5.60pp |
| spread > 15¢ mask | — | — | **−6.34** | **FAIL** — real composition effect |
| play-window (drops 14.4%) | undefined | undefined | — | **structurally justified, not tested** |

### Enforcement, not mere presence

- `p0_universe.py` **asserts the canary at build time and refuses to write a
  universe that fails.** Current build: 0.4969, z = −0.88.
- A **source-level test** asserts that the canary is called and that the dedupe
  sort references no post-settlement field.

### Where it is not enforced

| Project | State |
|---|---|
| crypto | Audited clean — no post-settlement field appears in any filter, sort or dedupe. Not wired in as an assertion. |
| wallet-copy-study | Equivalent guard: `reports/selection_audit.json` scores a null strategy at −0.0pp with random subsets straddling zero. |
| kalshi-tennis | Retro-audited. **Two UNSAFE sites found and still live**: `stage4_kalshi_liquid.py:24` and `stage5_selective.py:131` both filter on a spread read from the leaking anchor. |
| **v3 backtest (desktop)** | **PRESUME VOID.** It deduped 14,162 mirrored Kalshi markets — the same operation, same exchange, same sport. **One grep answers it.** |
| **copy-trading wallet ranking (desktop)** | Unknown ranking field and timing. |

---

## 2. The within-match leak canary — look-ahead inside one market

**Different failure, different guard.** The selection canary watches *which rows
exist*. This one watches *whether a price was read from after the decision*.

**Source:** `kalshi-tennis/src/anchor_leak_test.py` → `reports/anchor_leak_test.txt`

### The test

Sweep the price anchor backwards from settlement and watch two diagnostics:

| Anchor | Quotes outside 2¢–98¢ | Of those, % correct | corr with books |
|---|---|---|---|
| **−0h** | **4.1%** | **100%** | 0.824 |
| −6h | 0.1% | — | **0.9775** |

**A real pre-match market cannot produce quotes that are 100% correct at the
extremes.** That is the signature.

### The independent-books trick

Two independent bookmakers agree with each other at **corr 0.9985, MAD 0.015**.
So any anchor at which Kalshi appears to *beat both* is leaking, not sharp. This
turns "is my anchor clean?" into a falsifiable measurement rather than a
judgement call.

### Why it is not sufficient on its own

Stated plainly in `SELECTION_AUDIT.md` §4:

> The leak canary watches for look-ahead **within** a match. The volume-dedupe
> leak was **between** two markets: every price was correctly timestamped, and
> the wrong rows were chosen. **Feature-level tests are structurally blind to
> it.**

**You need both. Neither substitutes for the other.**

---

## 3. Synthetic null control

**Feed the pipeline data with no edge in it. It must find no edge.**

| Project | Artifact | Result |
|---|---|---|
| set1_overshoot | `reports/p2_synth_null.txt`, `p2_synth_null_clean.txt` | **−0.59pp** (also reported −0.06pp on an earlier build) — PASS |
| crypto | `src/synthetic_control.py` → `reports/synthetic_control.json` (`L4-A`) | diff **−0.000028, CI [−0.00013, +0.00008] contains zero**, p=0.593 — PASS |
| wallet-copy-study | `reports/selection_audit.json` | null strategy scores **−0.0pp**; random subsets straddle zero — PASS |

---

## 4. Positive control — a planted effect the pipeline must find

A null control alone proves nothing: a pipeline that always reports zero passes
it. **You need the pipeline to detect an effect you put there.**

| Project | Artifact | Planted | Detected |
|---|---|---|---|
| set1_overshoot | `reports/p2_synth_boost.txt` | 5pp | **+4.54pp** (also +4.04pp on the later build) — PASS |
| crypto `L4-B` | `reports/synthetic_control.json` | 15% wing bias | **−0.002655 [−0.00310,−0.00217]**, p<0.0001 — PASS |
| crypto `L4-B5` | same | **5% wing bias (sensitivity floor)** | **−0.000334 [−0.00050,−0.00014]**, p<0.0001 — PASS |
| crypto `L4-C` | same | outcome leaked into a feature | Brier **0.0004 vs 0.1032** — PASS |
| kalshi-tennis | `reports/stage3_traits.txt` | match win rate (known-real trait) | split-half r **+0.633** — PASS |

**This is what makes crypto's headline null credible.** `C010` says no model
beats the mid. `L4-B5` proves the same pipeline would have found a 5% bias. The
test could have found an effect several times larger than anything present, so
the null is a measurement, not a failure to look.

---

## 5. Deliberate-leak diagnostic — prove the detector still bites

Distinct from the positive control: here you plant a *leak* rather than an
*effect*, and the pipeline must light up.

| Project | Artifact | Result |
|---|---|---|
| set1_overshoot | `hypothesis_ledger.csv#32,33` (`cpleak-10`, `cpleak+0`) | **+6.96pp** and **−2.67pp** vs honest rules — marked `DELIBERATE LEAK, diagnostic only` in the ledger itself |
| kalshi-tennis | the −0h anchor in the sweep | 100%-correct extremes — the leak, measured |

---

## 6. Exact-decimal fee arithmetic

**Source:** [`common/kalshi_fees.py`](common/kalshi_fees.py) — **the single
implementation**. Tests in [`common/tests/`](common/tests/). Every other module
in the repo imports it; none reimplements it.

### The bug this exists to prevent

```
0.07 * 100 * 0.5 * 0.5 * 100  ->  175.00000000000003
```

`ceil` then adds a spurious cent, inflating every fee. **This recurred in three
separate codebases.** The instruction issued was: one shared, tested `fees.py`.

### What actually happened, and the lesson (2026-08-03)

The instruction was not enough. By 08-03 the formula existed **seventeen times
across five projects.** Nine copies carried the bug; **two of those were in the
live-money path** (`tennis_engine.py`, `paper_bot.py`). Measured against exact
Decimal over the integer-cent × order-size grid, each unguarded copy
overcharged on **115 of 1,881 cells (6.1%)**, always by exactly 1¢.

> **Telling people to share a module does not make them share it.** The count
> went from 3 to 17 *after* the instruction was issued. What stops the 18th
> copy is a test that fails when one appears — not a convention.

### The guard that enforces it

[`common/tests/test_no_fee_reimplementation.py`](common/tests/test_no_fee_reimplementation.py)
walks every `.py` file in the repo and flags anything carrying a fee
fingerprint (a `0.07`/`0.0175` literal together with a quadratic term or a
`ceil`). Each hit must **either** import the shared module **or** appear in an
explicit `ALLOWED` map with a written reason.

The allowlist is the mechanism, not an escape hatch. Three sub-tests keep it
honest:

- **dead entries fail.** An allowlisted file that stops matching must be
  removed, so the list cannot silently become a blanket exemption. *(This fired
  on its first run and caught a stale entry.)*
- **empty reasons fail.** Every entry states why.
- **the detector is proven to bite** on the canonical bug — guard-rot
  protection, GUARDS #9. A check that cannot fail is not a check.

Legitimate allowlist entries are Polymarket code (where `0.07` is the
*documented* rate retained specifically to prove it wrong — it matched 0.0% of
4,310 real fills), prose inside generated reports, and the sibling project's
audit of published fee claims.

### The implementation

Nothing touches float. `Decimal` throughout, `ROUND_CEILING` per order.

```python
RATE = Decimal("0.07")
fee = roundup( 0.07 * C * P * (1 - P) )   # dollars, rounded UP per order
```

Two functions with a deliberate distinction:

- `fee_rate_cents(price)` — **unrounded**, for expectancy arithmetic, where
  per-order round-up is an artefact of order size rather than an economic cost.
- `fee_order_cents(price, contracts)` — what an actual order is **charged**.

Verified against hard-coded reference points, asserted at import:

| Price | Per-contract fee |
|---|---|
| 50¢ | **1.75¢** (peak) |
| 90¢ / 10¢ | **0.63¢** |
| 55¢ | 1.7325¢ |
| 1¢ / 99¢ | 0.0693¢ |

Plus order-level round-up: `fee_order_cents(50, 1) == 2`, `(50, 100) == 175`.

### Settlement semantics

**There is no separate settlement fee.** Holding to settlement pays the entry fee
only; an early exit pays entry + exit. Getting this wrong doubles the cost bar on
every hold-to-settle strategy.

### Fees resolved empirically, not from documentation

Two cases where the docs were **wrong** and only the venue's own data revealed it:

| Venue | Documented | Actual | Evidence |
|---|---|---|---|
| **Polymarket** | `0.07 · p(1−p)` — matches **0.0%** of fills | **`0.10 · min(p, 1−p)`** | 4,310 on-chain fills, median relative error 0.000000, **100% within 1%** (`crypto/reports/poly_fee_resolution.json`); independently reproduced on 5,362 fills in wallet-copy-study |
| **Kalshi maker** | "25% of taker" | **zero on Challenger/ITF (91% of the book)**, applies on ATP/WTA only | resolved from the series `fee_type` field |

Consequence: Polymarket costs **2.86× Kalshi at 50¢**, which retired the claimed
cost parity.

**Guard the sign.** wallet-copy-study's fee check initially reported median
relative error 0.96 — an inverted maker side. It is now protected by a test that
asserts **inverting the side is off by exactly 100% at 50¢**. A silent sign error
there would have poisoned every cost number in the study.

---

## 7. Per-market P&L decomposition, marked at actual settlement

**Source:** `set1_overshoot/src/p5_maker.py` → `reports/p5_task1b.md`;
tests in `set1_overshoot/tests/test_pnl.py`

### The rule

Every opportunity's P&L decomposes into named components that **sum to the total
exactly**, and the position is marked at **actual settlement**, never at a
model price, never at the mid.

Measured residual: **+0.0000¢**. It is an identity, and it is asserted.

### Why it matters

It is what makes the maker result interpretable. The four-way decomposition
showed **adverse selection already exceeds price improvement** — so a maker
strategy is not "the taker result plus a fee saving", and no amount of fee
optimisation rescues it. Without the decomposition you get a single negative
number and no idea which term killed it.

### The mid-price trap this enforces

`kalshi-tennis` Stage 5 reported **+14.4% to +24.6% ROI** marked at the mid. At
executable fills — buy YES lifts the **ask**, buy NO costs **1 − bid** — the same
strategy returns **−24.3% to −30.9%**, every CI below zero. Mean entry moved
**27–32¢**.

The mechanism: **39.8% of held-out markets quote wider than 10¢.** A 1¢/99¢
quote has a 50¢ "mid" that nobody will ever trade at.

> **Never mark at the mid. Fill at the ask when buying and the bid when selling.**

### Where it is absent

`kalshi-tennis` has no decomposition and no execution model — that is precisely
how T008 survived as a headline.

---

## 8. Effective sample size

**Row count is not evidence count.** This is failure mode #1 across the whole
archive, and it is responsible for more retracted claims than any other error.

**Sources:** `crypto/src/effective_n_audit.py` →
`reports/effective_n_audit.json`, `.txt`, and
[`crypto/docs/EFFECTIVE_N_AUDIT.md`](crypto/docs/EFFECTIVE_N_AUDIT.md)

### The unit of observation, per project

| Project | Naive n | **Correct unit** | Correct n | Inflation |
|---|---|---|---|---|
| crypto | 89,806 market-minutes | **event** | **250** | ~360 correlated minutes/event ⇒ **CIs widen ~10×** |
| set1_overshoot | 19,782 markets | **match** (day-clustered bootstrap) | 3,436 events | mirrored pairs ⇒ √2 |
| wallet-copy-study | 2,234,479 trades | **market**, and **(wallet, series, day)** | 2,271 markets | 288 BTC 5-min markets in a day ≠ 288 draws |
| tennis bot (chat) | 25,250 "observations" | **match** | ~171 matches | **~2 orders of magnitude** |
| copy trading (chat) | 644 fills | **match** | 1 | **644×** |

### What it killed

- **crypto `MIDCAL`**: raw reliability showed a **+4.2pp** gap against a ~1.3¢
  cost bar. Under event clustering the CIs widened ~10× and 14 of 17 buckets went
  to zero. It failed BH, halved between disjoint halves, and had had the
  **opposite sign at n=13**.
- **The "+95pp genius wallet"**: 21 bets on **one match**.
- **The "+7.05pp" copy-trading benchmark**: a trade-clustered interval on a
  market-clustered phenomenon. Recomputed with market clustering: **+2.09pp,
  CI [−1.37,+5.35]**, and **−0.29pp net**.

### Cross-asset independence

crypto measured it directly: **1.81 effective independent series out of 4**
(settlement-sign phi 0.59–0.70 between assets). BTC/ETH hourly return correlation
is **0.891**, and 62% of BTC's extreme hours are also ETH's — so the fat-tail
result is **one** finding, not two.

The audit re-checked every pooled claim against this and produced a four-valued
verdict — including one the brief did not anticipate:

> **`UNSUPPORTED`** — *"MM scan: 0 of 4 series profitable"* had **no artifact
> behind it at all**. Only KXBTCD (58 markets) was ever P&L-tested.

### The power calculation that follows

- Distinguishing a real 3% edge from zero needs **~1,000+ trades**; separating
  55% from 50% needs ~400. The account cannot fund that sample.
- set1_overshoot: 3,436 events, sd 45¢ ⇒ **n ≈ 3,970** needed for a 2¢ edge.
- wallet-copy-study: σ = 0.296 ⇒ **n ≈ 274 markets** per wallet; only **27%**
  of wallets clear it.

> **"You've been trying to solve a sample-size problem with effort."**

### MDE reported next to every null

Every segment table in set1_overshoot reports its minimum detectable effect
beside the point estimate — so `0 of 25` reads honestly as *"0 of 25, median MDE
3.7–9.0¢ against a ~2¢ target"* rather than as evidence of absence.

---

## 9. Guard-rot test

**A guard that silently stops working is worse than no guard.**

`set1_overshoot/tests/test_leakguard.py` includes a test asserting that the
**known-bad** rules still trip the assertion on real data:

| Known-bad rule | Must still read | Current |
|---|---|---|
| `last_price` | catastrophic | **+140.4** ✅ |
| `open_interest` | fail | **+15.7** ✅ |
| `volume` | fail | **+10.0** ✅ |

If any of these ever passes, the guard has broken, not the data.

Also present: a **live regression** on the real universe, and a **source-level**
test that the canary is actually invoked.

**This exists in set1_overshoot only.** It should be copied to every project.

---

## 10. Pre-registration before seeing any number

| Project | Artifact |
|---|---|
| set1_overshoot | `PREREGISTRATION.md`, `PREREGISTRATION_PARTB.md` — point prediction **+1.3pp**, interval **[−1,+3]**, gates fixed in advance; amendments A1/A2 recorded **with provenance** |
| crypto | `PREREGISTRATION.md`, `docs/GO_NO_GO.md` |
| wallet-copy-study | `DECISIONS.md`, `docs/wallet_criteria.md` |

### Gates enforced in code, not by hand

`set1_overshoot` Part B **exits before printing any calibration number** if the
two orientations disagree (the `3e` gate). crypto's `GO_NO_GO.md` criterion 1
stopped Task 5 from running at all once B1 came back null.

> *"Sweeping exit rules over a signal with no edge is how this project has
> previously produced strategies that die live."*

### Monotone strengthening reclassified as a **warning sign**

The single worst inference in the archive was arguing an effect was real
*because it strengthened with detector precision*. It was the opposite:
precision and bias were the same knob. Deeper rules pushed the kept/favourite
split further from 50/50, amplifying the leak.

**Pre-registered afterwards: monotone strengthening is evidence of
contamination until proven otherwise.**

---

## 11. Benjamini-Hochberg across the whole ledger

Not per phase, not per family — **across every hypothesis the project ever
evaluated**, so the denominator stays honest.

| Project | Ledger | Tests | Survive |
|---|---|---|---|
| set1_overshoot | `HYPOTHESIS_LEDGER.md` + `reports/hypothesis_ledger.csv` | **97** hypotheses, 80 with a computable p | **30** at q=0.1 (threshold p ≤ 0.03740) |
| crypto | `HYPOTHESIS_LEDGER.md` | **17** hypotheses / **101** individual tests | **2 facts, 0 tradeable edges** |
| kalshi-tennis | `reports/stage5_selective.txt` | 43 segments | 19 survive at α=0.05 — **all negative** |
| wallet-copy-study | per family | 20 / 13 / 7-test families | 18/20, 12/13, 6/7 |

Two conventions worth copying:

1. **Two-sided p-values**, "because an undershoot is a finding here and a
   one-sided overshoot test would hide it."
2. **Cancelled hypotheses stay in the table** (crypto's `CANCELLED` status) —
   pre-registered but unanswerable, kept so the denominator does not quietly
   shrink.

---

## 12. Content-level recorder health check

**Not a row-count check.** Row counts were right in both incidents.

### The incidents

| Project | What happened |
|---|---|
| crypto | An orderbook parse bug wrote **real row counts with empty content for 1h45m**, caught **by accident**. *"For a project whose only irreplaceable asset is continuously accruing recorded data, that bug class is existential."* |
| crypto | Kalshi's legacy price fields (`yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest`) now return **`None`** — values moved to `*_dollars` / `*_fp`. Any recorder still reading the old names is silently writing nulls. |

### The check that is actually implemented

`set1_overshoot`'s depth recorder, run **×5 per day**, asserts on content:

| Assertion | Reading |
|---|---|
| non-empty snapshots | **98.8%** |
| levels per side | **20** |
| prices in (0,1) | ✅ |
| staleness | **3 s old** |

### Still open

- crypto's fix was **specified** (content-level check every 15 min alerting on
  schema drift) — **implementation status unknown**.
- **The desktop recorders have never been checked for the `None` bug.** One grep
  of `kalshi_client.py` and `record_data.py`. If they have been writing `None`,
  every recorded book on that machine is worthless, and it gates all Tier B work.

---

---

## 13. A 200 is not a correct file, and a 0 exit code is not a rendered artifact

*Contributed by `extractor-upgrade`, 2026-08-05. Four independent instances in
two days, in three different projects.*

Every one of these returned **success** and **wrong**:

| what returned success | what was actually true |
|---|---|
| `football-data.co.uk` HTTP **200** | `COL.csv` is byte-identical to `POL.csv`; its own League column reads *Ekstraklasa*. `KOR.csv` ≡ `NOR.csv`. |
| `ffmpeg` exit **0**, empty stderr | a **blank frame**. `%` in `drawtext` renders the whole caption as nothing. Bisected: `"Total 18%"` → 1,002-byte blank, `"Total 18 pct"` → 3,007 bytes with text. `\%` does not help; `textfile=` does not help; `expansion=none` does. |
| a collector that **printed a running total for every query** | it wrote **zero rows** — the write sat inside an `if already-have: skip` branch. |
| an earlier repo scorer | *"reported 358 repos scored when 92 had real data."* |

**The check is always the same shape: assert something about the CONTENT, not
about the call.** Hash the file and read its own identifying column. Measure the
image's pixel standard deviation (`extractor-upgrade/src/frames.py::is_flat`).
Assert the row count went **up**, not that the function returned.

> **A silent no-op that reports progress is worse than a crash.** A crash is
> free to diagnose. This costs a session and then a retraction.

---

## 14. A `robots.txt` check that does not implement `Allow:` is not a check

*Contributed by `extractor-upgrade`, 2026-08-05.*

```
# hacker-news.firebaseio.com/robots.txt
User-agent: *
Allow: /*.json$        <- the API is EXPLICITLY permitted
Allow: /*.json?*$
Disallow: /               only the HTML is not
```

A parser that reads the `Disallow` and ignores the `Allow` calls a **documented,
explicitly-permitted public API off-limits.** The standard is **longest match
wins**, with `*` and `$` wildcards. Implementing it flipped two hosts in
*opposite* directions — Hacker News forbidden → **permitted**, Apple Podcasts
permitted → **forbidden** (`Disallow: /search*`, which the naive parser had
missed the other way).

Two corollaries, both learned the expensive way:

- **A host that serves NO `robots.txt` is UNDECIDABLE, not permitted.** Keep the
  two states apart in the data, not just in your head.
- **Read the whole file before concluding a host is closed.** `i.ytimg.com`
  disallows `/sb/` and nothing else. Reading that line, correctly concluding
  storyboards were forbidden, and stopping there cost a day and produced a
  published retraction — `/vi/<id>/maxres{1,2,3}.jpg` are permitted 1280×720
  video frames.

**Refusing something you are permitted to use costs exactly as much as using
something you are not.**

---

## 15. A 404 never establishes that something is dead

*Contributed by `extractor-upgrade`, 2026-08-05, after getting it wrong twice in
the same script.*

- **v1** counted every 404 as death and killed `api.elections.kalshi.com`,
  `api.exchange.coinbase.com` and `r2v2.pmxt.dev` — all live hosts whose **base
  URL has no handler**.
- **v2** patched that with a path-segment heuristic and immediately killed
  `https://api.elections.kalshi.com/trade-api/v2` — a **versioned API base this
  repo is recording against right now.** A heuristic written to fix a false kill
  produced another one on its first run.

Only four states establish death, and none of them is an inference:

| state | why it is conclusive |
|---|---|
| **NO_DNS** | the name does not resolve; nothing is there to serve anything |
| **ARCHIVED** | the **owner's own flag**, not a judgment |
| **HTTP 410 Gone** | the one status that explicitly means permanently removed |
| **COLD** | no push in >1 year — reported as its own state, never as death |

`401` / `403` / `429` are a door **held shut**, not a door that is **gone**.
`guest.api.arcadia.pinnacle.com/0.1/sports` returns **401**, while
`/0.1/sports/29/matchups` returns **200 and 1.7 MB with no header at all.**

> This is the same family as the repo's existing kills-from-bad-probes:
> `market-selection`'s stale tickers produced **19 wrong kills**, and
> `bot-hunt`'s `tag_slug=esports` killed its own best lead. **A probe that
> samples the wrong thing fails silently, and always toward a kill.**

---

## 16. Never let your own dedup decide your headline number

*Contributed by `extractor-upgrade`, 2026-08-05. The near-miss worth reading
even if you skip the rest.*

A retrieval design here rests on the finding that **beginner-phrasing and
insider-vocabulary queries return near-disjoint sets** — Jaccard 0.037 on video,
0.032 / 0.033 / 0.036 on repositories.

A fourth corpus was built to test it. The collector skipped any id it already
held, so an item found by **both** families was filed under whichever family
reached it first. **That makes the overlap structurally zero regardless of what
the corpus contains.**

It returned **Jaccard 0.000**, and was one commit from being published as *the
fourth independent corroboration*.

> **A self-inflicted number that AGREES with three prior measurements is the
> least likely number in the world to be questioned.** Nothing about it looks
> wrong. It has the right sign, the right magnitude, and a story.

**The guard:** for any set-overlap, set-difference or novelty statistic, record
membership in a table that permits multiple memberships, and compute the
statistic from *that* — never from a deduplicated collection whose insertion
order silently defines the answer. And when a new measurement lands **exactly**
where the old ones did, that is the moment to go looking for the line of your
own code that put it there.

---

## The one-page version

If you carry nothing else into the next project:

1. **Two leak canaries, not one.** Row membership *and* within-row look-ahead.
   Each is structurally blind to the other's failure.
2. **Three-valued verdicts.** UNTESTABLE is not PASS. Report the MDE next to
   every null.
3. **A null control and a positive control.** The null alone is passed by a
   pipeline that always reports zero.
4. **Guard-rot tests.** Assert the known-bad inputs still fail.
5. **Decimal fees, resolved from the venue's own data, never the docs.**
6. **Fill at the ask, never the mid.** Decompose P&L and mark at real settlement.
7. **Count events, not rows.** Then compute the power before running anything.
8. **Pre-register, and put the gate in code** so it fires before you see a number.
9. **One FDR denominator for the whole project.** Cancelled hypotheses stay in it.
10. **Every correction so far has shrunk the edge.** Update on that.
11. **Assert content, not the call.** A 200 is not a correct file and a 0
    exit code is not a rendered artifact. A silent no-op that reports
    progress is worse than a crash.
12. **A 404 never establishes death, and no-`robots.txt` is not permission.**
    A probe that samples the wrong thing fails silently, and always toward
    the conservative answer - a kill, or a refusal.
13. **Never let your own dedup decide your headline number**, and treat a
    result that lands exactly on your prior ones as a reason to go looking
    for the line of code that put it there.
