# GUARDS.md â€” the reusable part

Every canary, control and check that exists in any project, where it lives, and
which projects have it. **This is the most transferable output of all four
projects.** The strategies all died; the guards are what caught them dying, and
several caught errors that would otherwise have shipped.

Each guard below is listed with: what it tests, the null, the artifact, and the
coverage table.

## Coverage at a glance

| Guard | set1_overshoot | crypto | wallet-copy-study | kalshi-tennis | desktop bot / v3 |
|---|---|---|---|---|---|
| 1. Selection canary (3-valued) | âœ… enforced at build | âž– audited clean, not enforced | âœ… equivalent | âš ï¸ retro-audited, 2 UNSAFE found | âŒ **presume void** |
| 2. Within-match leak canary | âœ… | âœ… | âœ… | âœ… (found the leak) | âŒ |
| 3. Synthetic null | âœ… | âœ… | âœ… | âŒ | âŒ |
| 4. Positive control (planted effect) | âœ… | âœ… (15% and 5%) | âž– implicit | âœ… (Stage 3 traits) | âŒ |
| 5. Deliberate-leak diagnostic | âœ… | âœ… | âŒ | âœ… (anchor sweep) | âŒ |
| 6. Exact-decimal fee arithmetic | âœ… | âœ… | âœ… (empirical) | âœ… **fixed 08-03** | âœ… **fixed 08-03** |
| 6b. **Anti-reimplementation guard** (repo-wide) | âœ… enforced repo-wide by [`common/tests/test_no_fee_reimplementation.py`](common/tests/test_no_fee_reimplementation.py) â€” one test covers every project | | | | |
| 7. Per-market P&L decomposition | âœ… exact identity | âœ… | âœ… | âŒ | âŒ |
| 8. Effective sample size | âœ… (day-clustered) | âœ… (event-clustered) | âœ… (market/series-day) | âž– partial | âŒ |
| 9. Guard-rot test | âœ… | âŒ | âŒ | âŒ | âŒ |
| 10. Pre-registration before seeing numbers | âœ… | âœ… | âœ… | âŒ | âŒ |
| 11. BH-FDR across the whole ledger | âœ… 97 rows | âœ… 101 tests | âœ… per family | âœ… 43 segments | âŒ |
| 13. Content-assert, not call-assert (a 200/exit-0 is not a result) | âœ… `frames.is_flat` | | | | |
| 14. `robots.txt` `Allow:` implemented (longest match wins) | âœ… `find_sources.robots_allows` | | | | |
| 15. A 404 never establishes death | âœ… `unify_currency._dead` | | | | |
| 16. Membership table, so dedup cannot decide an overlap statistic | âœ… `hn.membership` | | | | |
| 12. Content-level recorder health check | âœ… | âš ï¸ specified, status unknown | n/a | n/a | âŒ **check first** |
| 23. **Renamed-field trap** (venue schema drift) | ✅ enforced repo-wide by [`common/kalshi_fields.py`](common/kalshi_fields.py) + [`test_no_legacy_kalshi_fields.py`](common/tests/test_no_legacy_kalshi_fields.py) — found **2 live bugs** the day it was written | | | | |

âœ… present and enforced âž– present but weaker âš ï¸ partial or unverified âŒ absent

---

## 1. The selection canary â€” P(kept side wins) = 0.50

**The single most valuable guard in the repo.** It is the one that caught the
bug that voided three phases of work.

**Source:** [`set1_overshoot/src/leakguard.py`](set1_overshoot/src/leakguard.py)
**Tests:** [`set1_overshoot/tests/test_leakguard.py`](set1_overshoot/tests/test_leakguard.py) â€” 9 tests, all passing
**Audit:** [`set1_overshoot/SELECTION_AUDIT.md`](set1_overshoot/SELECTION_AUDIT.md) â€” 315 occurrences across 4 codebases

### What it tests

When a market lists two mirrored sides (Kalshi lists one market per player), you
must dedupe to one. **Whichever field orders that choice must not know the
answer.** The null is exact: over mirrored pairs, P(the kept side wins) = 0.5000.

### Why it exists

`p0_universe.py` deduped by keeping the higher-`volume_fp` side. That looks like
a tie-break. It is a coin weighted by the outcome â€” the winning side attracts
more volume. Measured:

| Rule | P(kept wins) | z | Verdict |
|---|---|---|---|
| higher `last_price_dollars` | **0.9989** | **+140.3** | catastrophic â€” it *is* the answer |
| higher `open_interest_fp` | **0.5558** | **+15.7** | unsafe |
| higher `volume_fp` â€” **the bug** | **0.5356** | **+10.0** | unsafe |
| higher `liquidity_dollars` | 0.5031 | +0.88 | **UNTESTABLE** â€” see below |
| **first ticker alphabetically â€” the fix** | **0.4969** | **âˆ’0.88** | clean |
| API listing order (kalshi-tennis) | 0.5050 | +1.44 | clean |

The two orientations disagreed by **25.5pp**. Everything downstream was void.

### The three-valued verdict â€” PASS / FAIL / UNTESTABLE

This is the part most implementations get wrong, and v1 of this file got it
wrong too.

`liquidity_dollars` scored z = +0.88 and was **recorded as a clean alternative
rule**. It is not clean. The field reads 0 on almost every settled tennis
market, so the rule almost never actually chooses anything â€” the tie-break does
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

The statistic is the **calibration residual** `outcome âˆ’ implied`, not the raw
outcome rate â€” because the residual is what every downstream result actually
rests on. A filter that selects strong favourites shifts the outcome rate
legitimately; it must not shift the residual.

Both arms must be large enough to resolve a 2pp shift, or the result is
UNTESTABLE. Readings from the audit:

| Filter | Kept residual | Dropped residual | z | Verdict |
|---|---|---|---|---|
| `plausible` duration 25â€“330 min | +0.0029 (n=16,258) | +0.0294 (n=682) | âˆ’2.59 | borderline, below \|z\|=4 |
| leaking-anchor spread â‰¤10Â¢/5Â¢/2Â¢ | â€” | â€” | +0.11 / 0.00 / +0.14 | **inconclusive and moot** â€” only 502 joined rows |
| label join (set1) | +0.0597 (n=604) | +0.0166 (n=2,832) | **+2.15** | **UNTESTABLE**, MDE 5.60pp |
| spread > 15Â¢ mask | â€” | â€” | **âˆ’6.34** | **FAIL** â€” real composition effect |
| play-window (drops 14.4%) | undefined | undefined | â€” | **structurally justified, not tested** |

### Enforcement, not mere presence

- `p0_universe.py` **asserts the canary at build time and refuses to write a
  universe that fails.** Current build: 0.4969, z = âˆ’0.88.
- A **source-level test** asserts that the canary is called and that the dedupe
  sort references no post-settlement field.

### Where it is not enforced

| Project | State |
|---|---|
| crypto | Audited clean â€” no post-settlement field appears in any filter, sort or dedupe. Not wired in as an assertion. |
| wallet-copy-study | Equivalent guard: `reports/selection_audit.json` scores a null strategy at âˆ’0.0pp with random subsets straddling zero. |
| kalshi-tennis | Retro-audited. **Two UNSAFE sites found and still live**: `stage4_kalshi_liquid.py:24` and `stage5_selective.py:131` both filter on a spread read from the leaking anchor. |
| **v3 backtest (desktop)** | **PRESUME VOID.** It deduped 14,162 mirrored Kalshi markets â€” the same operation, same exchange, same sport. **One grep answers it.** |
| **copy-trading wallet ranking (desktop)** | Unknown ranking field and timing. |

---

## 2. The within-match leak canary â€” look-ahead inside one market

**Different failure, different guard.** The selection canary watches *which rows
exist*. This one watches *whether a price was read from after the decision*.

**Source:** `kalshi-tennis/src/anchor_leak_test.py` â†’ `reports/anchor_leak_test.txt`

### The test

Sweep the price anchor backwards from settlement and watch two diagnostics:

| Anchor | Quotes outside 2Â¢â€“98Â¢ | Of those, % correct | corr with books |
|---|---|---|---|
| **âˆ’0h** | **4.1%** | **100%** | 0.824 |
| âˆ’6h | 0.1% | â€” | **0.9775** |

**A real pre-match market cannot produce quotes that are 100% correct at the
extremes.** That is the signature.

### The independent-books trick

Two independent bookmakers agree with each other at **corr 0.9985, MAD 0.015**.
So any anchor at which Kalshi appears to *beat both* is leaking, not sharp. This
turns "is my anchor clean?" into a falsifiable measurement rather than a
judgement call.

### Why it is not sufficient on its own

Stated plainly in `SELECTION_AUDIT.md` Â§4:

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
| set1_overshoot | `reports/p2_synth_null.txt`, `p2_synth_null_clean.txt` | **âˆ’0.59pp** (also reported âˆ’0.06pp on an earlier build) â€” PASS |
| crypto | `src/synthetic_control.py` â†’ `reports/synthetic_control.json` (`L4-A`) | diff **âˆ’0.000028, CI [âˆ’0.00013, +0.00008] contains zero**, p=0.593 â€” PASS |
| wallet-copy-study | `reports/selection_audit.json` | null strategy scores **âˆ’0.0pp**; random subsets straddle zero â€” PASS |

---

## 4. Positive control â€” a planted effect the pipeline must find

A null control alone proves nothing: a pipeline that always reports zero passes
it. **You need the pipeline to detect an effect you put there.**

| Project | Artifact | Planted | Detected |
|---|---|---|---|
| set1_overshoot | `reports/p2_synth_boost.txt` | 5pp | **+4.54pp** (also +4.04pp on the later build) â€” PASS |
| crypto `L4-B` | `reports/synthetic_control.json` | 15% wing bias | **âˆ’0.002655 [âˆ’0.00310,âˆ’0.00217]**, p<0.0001 â€” PASS |
| crypto `L4-B5` | same | **5% wing bias (sensitivity floor)** | **âˆ’0.000334 [âˆ’0.00050,âˆ’0.00014]**, p<0.0001 â€” PASS |
| crypto `L4-C` | same | outcome leaked into a feature | Brier **0.0004 vs 0.1032** â€” PASS |
| kalshi-tennis | `reports/stage3_traits.txt` | match win rate (known-real trait) | split-half r **+0.633** â€” PASS |

**This is what makes crypto's headline null credible.** `C010` says no model
beats the mid. `L4-B5` proves the same pipeline would have found a 5% bias. The
test could have found an effect several times larger than anything present, so
the null is a measurement, not a failure to look.

---

## 5. Deliberate-leak diagnostic â€” prove the detector still bites

Distinct from the positive control: here you plant a *leak* rather than an
*effect*, and the pipeline must light up.

| Project | Artifact | Result |
|---|---|---|
| set1_overshoot | `hypothesis_ledger.csv#32,33` (`cpleak-10`, `cpleak+0`) | **+6.96pp** and **âˆ’2.67pp** vs honest rules â€” marked `DELIBERATE LEAK, diagnostic only` in the ledger itself |
| kalshi-tennis | the âˆ’0h anchor in the sweep | 100%-correct extremes â€” the leak, measured |

---

## 6. Exact-decimal fee arithmetic

**Source:** [`common/kalshi_fees.py`](common/kalshi_fees.py) â€” **the single
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
Decimal over the integer-cent Ã— order-size grid, each unguarded copy
overcharged on **115 of 1,881 cells (6.1%)**, always by exactly 1Â¢.

> **Telling people to share a module does not make them share it.** The count
> went from 3 to 17 *after* the instruction was issued. What stops the 18th
> copy is a test that fails when one appears â€” not a convention.

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
- **the detector is proven to bite** on the canonical bug â€” guard-rot
  protection, GUARDS #9. A check that cannot fail is not a check.

Legitimate allowlist entries are Polymarket code (where `0.07` is the
*documented* rate retained specifically to prove it wrong â€” it matched 0.0% of
4,310 real fills), prose inside generated reports, and the sibling project's
audit of published fee claims.

### The implementation

Nothing touches float. `Decimal` throughout, `ROUND_CEILING` per order.

```python
RATE = Decimal("0.07")
fee = roundup( 0.07 * C * P * (1 - P) )   # dollars, rounded UP per order
```

Two functions with a deliberate distinction:

- `fee_rate_cents(price)` â€” **unrounded**, for expectancy arithmetic, where
  per-order round-up is an artefact of order size rather than an economic cost.
- `fee_order_cents(price, contracts)` â€” what an actual order is **charged**.

Verified against hard-coded reference points, asserted at import:

| Price | Per-contract fee |
|---|---|
| 50Â¢ | **1.75Â¢** (peak) |
| 90Â¢ / 10Â¢ | **0.63Â¢** |
| 55Â¢ | 1.7325Â¢ |
| 1Â¢ / 99Â¢ | 0.0693Â¢ |

Plus order-level round-up: `fee_order_cents(50, 1) == 2`, `(50, 100) == 175`.

### Settlement semantics

**There is no separate settlement fee.** Holding to settlement pays the entry fee
only; an early exit pays entry + exit. Getting this wrong doubles the cost bar on
every hold-to-settle strategy.

### Fees resolved empirically, not from documentation

Two cases where the docs were **wrong** and only the venue's own data revealed it:

| Venue | Documented | Actual | Evidence |
|---|---|---|---|
| **Polymarket** | `0.07 Â· p(1âˆ’p)` â€” matches **0.0%** of fills | **`0.10 Â· min(p, 1âˆ’p)`** | 4,310 on-chain fills, median relative error 0.000000, **100% within 1%** (`crypto/reports/poly_fee_resolution.json`); independently reproduced on 5,362 fills in wallet-copy-study |
| **Kalshi maker** | "25% of taker" | **zero on Challenger/ITF (91% of the book)**, applies on ATP/WTA only | resolved from the series `fee_type` field |

Consequence: Polymarket costs **2.86Ã— Kalshi at 50Â¢**, which retired the claimed
cost parity.

**Guard the sign.** wallet-copy-study's fee check initially reported median
relative error 0.96 â€” an inverted maker side. It is now protected by a test that
asserts **inverting the side is off by exactly 100% at 50Â¢**. A silent sign error
there would have poisoned every cost number in the study.

---

## 7. Per-market P&L decomposition, marked at actual settlement

**Source:** `set1_overshoot/src/p5_maker.py` â†’ `reports/p5_task1b.md`;
tests in `set1_overshoot/tests/test_pnl.py`

### The rule

Every opportunity's P&L decomposes into named components that **sum to the total
exactly**, and the position is marked at **actual settlement**, never at a
model price, never at the mid.

Measured residual: **+0.0000Â¢**. It is an identity, and it is asserted.

### Why it matters

It is what makes the maker result interpretable. The four-way decomposition
showed **adverse selection already exceeds price improvement** â€” so a maker
strategy is not "the taker result plus a fee saving", and no amount of fee
optimisation rescues it. Without the decomposition you get a single negative
number and no idea which term killed it.

### The mid-price trap this enforces

`kalshi-tennis` Stage 5 reported **+14.4% to +24.6% ROI** marked at the mid. At
executable fills â€” buy YES lifts the **ask**, buy NO costs **1 âˆ’ bid** â€” the same
strategy returns **âˆ’24.3% to âˆ’30.9%**, every CI below zero. Mean entry moved
**27â€“32Â¢**.

The mechanism: **39.8% of held-out markets quote wider than 10Â¢.** A 1Â¢/99Â¢
quote has a 50Â¢ "mid" that nobody will ever trade at.

> **Never mark at the mid. Fill at the ask when buying and the bid when selling.**

### Where it is absent

`kalshi-tennis` has no decomposition and no execution model â€” that is precisely
how T008 survived as a headline.

---

## 8. Effective sample size

**Row count is not evidence count.** This is failure mode #1 across the whole
archive, and it is responsible for more retracted claims than any other error.

**Sources:** `crypto/src/effective_n_audit.py` â†’
`reports/effective_n_audit.json`, `.txt`, and
[`crypto/docs/EFFECTIVE_N_AUDIT.md`](crypto/docs/EFFECTIVE_N_AUDIT.md)

### The unit of observation, per project

| Project | Naive n | **Correct unit** | Correct n | Inflation |
|---|---|---|---|---|
| crypto | 89,806 market-minutes | **event** | **250** | ~360 correlated minutes/event â‡’ **CIs widen ~10Ã—** |
| set1_overshoot | 19,782 markets | **match** (day-clustered bootstrap) | 3,436 events | mirrored pairs â‡’ âˆš2 |
| wallet-copy-study | 2,234,479 trades | **market**, and **(wallet, series, day)** | 2,271 markets | 288 BTC 5-min markets in a day â‰  288 draws |
| tennis bot (chat) | 25,250 "observations" | **match** | ~171 matches | **~2 orders of magnitude** |
| copy trading (chat) | 644 fills | **match** | 1 | **644Ã—** |

### What it killed

- **crypto `MIDCAL`**: raw reliability showed a **+4.2pp** gap against a ~1.3Â¢
  cost bar. Under event clustering the CIs widened ~10Ã— and 14 of 17 buckets went
  to zero. It failed BH, halved between disjoint halves, and had had the
  **opposite sign at n=13**.
- **The "+95pp genius wallet"**: 21 bets on **one match**.
- **The "+7.05pp" copy-trading benchmark**: a trade-clustered interval on a
  market-clustered phenomenon. Recomputed with market clustering: **+2.09pp,
  CI [âˆ’1.37,+5.35]**, and **âˆ’0.29pp net**.

### Cross-asset independence

crypto measured it directly: **1.81 effective independent series out of 4**
(settlement-sign phi 0.59â€“0.70 between assets). BTC/ETH hourly return correlation
is **0.891**, and 62% of BTC's extreme hours are also ETH's â€” so the fat-tail
result is **one** finding, not two.

The audit re-checked every pooled claim against this and produced a four-valued
verdict â€” including one the brief did not anticipate:

> **`UNSUPPORTED`** â€” *"MM scan: 0 of 4 series profitable"* had **no artifact
> behind it at all**. Only KXBTCD (58 markets) was ever P&L-tested.

### The power calculation that follows

- Distinguishing a real 3% edge from zero needs **~1,000+ trades**; separating
  55% from 50% needs ~400. The account cannot fund that sample.
- set1_overshoot: 3,436 events, sd 45Â¢ â‡’ **n â‰ˆ 3,970** needed for a 2Â¢ edge.
- wallet-copy-study: Ïƒ = 0.296 â‡’ **n â‰ˆ 274 markets** per wallet; only **27%**
  of wallets clear it.

> **"You've been trying to solve a sample-size problem with effort."**

### MDE reported next to every null

Every segment table in set1_overshoot reports its minimum detectable effect
beside the point estimate â€” so `0 of 25` reads honestly as *"0 of 25, median MDE
3.7â€“9.0Â¢ against a ~2Â¢ target"* rather than as evidence of absence.

### The floor is set by the PRICE, and you do not get to choose it

**Added 2026-09-02 by `soccer`, verified independently by the coordinator.**
This is the sharpest form of #8 and it removes the guesswork: for a bet held
to settlement the payout is 0 or 100, so **the spread is not something you
measure — it is fixed by the price you paid:**

> **sd = 100 Ã— âˆš(P Ã— (1âˆ’P)) cents**

Predicted **45.8Â¢** at a 70Â¢ price; `soccer` measured **41.9Â¢** on 73 real
matches. The theory holds. Bets needed before the 95% range stops touching
zero:

| edge | at 50Â¢ | at 70Â¢ | at 90Â¢ | at 97Â¢ |
|---|---:|---:|---:|---:|
| 1Â¢ | 9,604 | 8,067 | 3,457 | 1,118 |
| 2Â¢ | 2,401 | 2,017 | 864 | 279 |
| 3Â¢ | 1,067 | 896 | 384 | 124 |
| 5Â¢ | 384 | 323 | 138 | 45 |

**âš  THE TRAP: the exchange offers liquidity exactly where measurement is most
expensive.** At 97Â¢ an edge needs 47 bets to see and nobody quotes it. At 50Â¢
you can always trade and need 400 for the same edge. *"I can trade it"* and
*"I can measure it"* pull in opposite directions, and a project that follows
liquidity walks straight into the expensive corner.

**The worked case, which is live:** the 16-bot baseball fleet has **254
settled bets at a median 50Â¢**. Smallest edge it can see is **6.1Â¢ pooled and
about 25Â¢ per individual bot** â€” against a repo record whose largest real
effect is **under 3Â¢**. So *"all 16 came back flat"* was never able to say
anything else. **That is not evidence of no edge; it is a test that cannot
resolve one**, and it must be reported as `UNTESTABLE` per #21, never as a
null.

**The way out, because the wall has a door:** this floor applies to an
**unpaired** test. **Two arms on the same game cancels the outcome and escapes
it** â€” and the paired question (*does A beat B on the same match*) is usually
the one actually being asked. Prefer the paired design before spending months
buying sample size.

**Cost of not knowing this:** it invalidated a pre-registered threshold by a
factor of six â€” 216 matches claimed, 1,755 actually required for 2Â¢ â€” because
the spread was carried over from a study of expected-value differences
(7.35Â¢) into one of realised outcomes (41.9Â¢).

**Confirmed independently on a second sport, 2026-09-02.** The baseball fleet's
own settled positions: **n = 1,081 per contract, sd 49.6Â¢** against the
formula's **50.0Â¢** at a 50Â¢ price. And the paired escape was measured, not
assumed â€” on 32 games where two strategies bet the same side, the spread of
the **difference** was **25.5Â¢ against 49.6Â¢ unpaired**, cutting the games
needed for a 3Â¢ comparison from ~1,050 to ~277.

> **âš  But count the arms, not the names, before quoting either number.** The
> same check found the fleet's 15 bots are **5 strategies Ã— 3 exit rules**, and
> the exit rules had fired **3 times in 1,504 positions** â€” so ten bots were
> bit-for-bit duplicates and 1,081 rows were really **327 distinct bets**.
> Counting duplicated arms as sample inflates resolution from an honest 5.4Â¢ to
> a false 2.95Â¢. Same error as counting a 10-strike ladder as ten markets (#8,
> above); it just wears a different costume when the duplication is a
> *configuration* that never triggers.

---

## 9. Guard-rot test

**A guard that silently stops working is worse than no guard.**

`set1_overshoot/tests/test_leakguard.py` includes a test asserting that the
**known-bad** rules still trip the assertion on real data:

| Known-bad rule | Must still read | Current |
|---|---|---|
| `last_price` | catastrophic | **+140.4** âœ… |
| `open_interest` | fail | **+15.7** âœ… |
| `volume` | fail | **+10.0** âœ… |

If any of these ever passes, the guard has broken, not the data.

Also present: a **live regression** on the real universe, and a **source-level**
test that the canary is actually invoked.

**This exists in set1_overshoot only.** It should be copied to every project.

---

## 10. Pre-registration before seeing any number

| Project | Artifact |
|---|---|
| set1_overshoot | `PREREGISTRATION.md`, `PREREGISTRATION_PARTB.md` â€” point prediction **+1.3pp**, interval **[âˆ’1,+3]**, gates fixed in advance; amendments A1/A2 recorded **with provenance** |
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

Not per phase, not per family â€” **across every hypothesis the project ever
evaluated**, so the denominator stays honest.

| Project | Ledger | Tests | Survive |
|---|---|---|---|
| set1_overshoot | `HYPOTHESIS_LEDGER.md` + `reports/hypothesis_ledger.csv` | **97** hypotheses, 80 with a computable p | **30** at q=0.1 (threshold p â‰¤ 0.03740) |
| crypto | `HYPOTHESIS_LEDGER.md` | **17** hypotheses / **101** individual tests | **2 facts, 0 tradeable edges** |
| kalshi-tennis | `reports/stage5_selective.txt` | 43 segments | 19 survive at Î±=0.05 â€” **all negative** |
| wallet-copy-study | per family | 20 / 13 / 7-test families | 18/20, 12/13, 6/7 |

Two conventions worth copying:

1. **Two-sided p-values**, "because an undershoot is a finding here and a
   one-sided overshoot test would hide it."
2. **Cancelled hypotheses stay in the table** (crypto's `CANCELLED` status) â€”
   pre-registered but unanswerable, kept so the denominator does not quietly
   shrink.

---

## 12. Content-level recorder health check

**Not a row-count check.** Row counts were right in both incidents.

### The incidents

| Project | What happened |
|---|---|
| crypto | An orderbook parse bug wrote **real row counts with empty content for 1h45m**, caught **by accident**. *"For a project whose only irreplaceable asset is continuously accruing recorded data, that bug class is existential."* |
| crypto | Kalshi's legacy price fields (`yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest`) now return **`None`** â€” values moved to `*_dollars` / `*_fp`. Any recorder still reading the old names is silently writing nulls. |

### The check that is actually implemented

`set1_overshoot`'s depth recorder, run **Ã—5 per day**, asserts on content:

| Assertion | Reading |
|---|---|
| non-empty snapshots | **98.8%** |
| levels per side | **20** |
| prices in (0,1) | âœ… |
| staleness | **3 s old** |

### Still open

- crypto's fix was **specified** (content-level check every 15 min alerting on
  schema drift) â€” **implementation status unknown**.
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
| `football-data.co.uk` HTTP **200** | `COL.csv` is byte-identical to `POL.csv`; its own League column reads *Ekstraklasa*. `KOR.csv` â‰¡ `NOR.csv`. |
| `ffmpeg` exit **0**, empty stderr | a **blank frame**. `%` in `drawtext` renders the whole caption as nothing. Bisected: `"Total 18%"` â†’ 1,002-byte blank, `"Total 18 pct"` â†’ 3,007 bytes with text. `\%` does not help; `textfile=` does not help; `expansion=none` does. |
| a collector that **printed a running total for every query** | it wrote **zero rows** â€” the write sat inside an `if already-have: skip` branch. |
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
*opposite* directions â€” Hacker News forbidden â†’ **permitted**, Apple Podcasts
permitted â†’ **forbidden** (`Disallow: /search*`, which the naive parser had
missed the other way).

Two corollaries, both learned the expensive way:

- **A host that serves NO `robots.txt` is UNDECIDABLE, not permitted.** Keep the
  two states apart in the data, not just in your head.
- **Read the whole file before concluding a host is closed.** `i.ytimg.com`
  disallows `/sb/` and nothing else. Reading that line, correctly concluding
  storyboards were forbidden, and stopping there cost a day and produced a
  published retraction â€” `/vi/<id>/maxres{1,2,3}.jpg` are permitted 1280Ã—720
  video frames.

**Refusing something you are permitted to use costs exactly as much as using
something you are not.**

---

## 15. A 404 never establishes that something is dead

*Contributed by `extractor-upgrade`, 2026-08-05, after getting it wrong twice in
the same script.*

- **v1** counted every 404 as death and killed `api.elections.kalshi.com`,
  `api.exchange.coinbase.com` and `r2v2.pmxt.dev` â€” all live hosts whose **base
  URL has no handler**.
- **v2** patched that with a path-segment heuristic and immediately killed
  `https://api.elections.kalshi.com/trade-api/v2` â€” a **versioned API base this
  repo is recording against right now.** A heuristic written to fix a false kill
  produced another one on its first run.

Only four states establish death, and none of them is an inference:

| state | why it is conclusive |
|---|---|
| **NO_DNS** | the name does not resolve; nothing is there to serve anything |
| **ARCHIVED** | the **owner's own flag**, not a judgment |
| **HTTP 410 Gone** | the one status that explicitly means permanently removed |
| **COLD** | no push in >1 year â€” reported as its own state, never as death |

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
insider-vocabulary queries return near-disjoint sets** â€” Jaccard 0.037 on video,
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
statistic from *that* â€” never from a deduplicated collection whose insertion
order silently defines the answer. And when a new measurement lands **exactly**
where the old ones did, that is the moment to go looking for the line of your
own code that put it there.

---

## 17. The argmax null â€” "it worked, then it stopped working" is the shape of noise

**Source:** [`bot-forensics/src/t2b_nightday.py`](bot-forensics/src/t2b_nightday.py)
**Found by:** the live tennis bot's "profitable night", 2026-08-05

### What it tests

Whenever a record is split into a good period and a bad one, ask **how the split
point was chosen**. If it was chosen by looking at the results â€” the peak of the
equity curve, the day the drawdown started, "when the daytime tournaments began"
â€” then the difference across it is not evidence, because **the argmax of a
cumulative sum is by construction the point that maximises
`mean(before) âˆ’ mean(after)`.**

### The null, and why it is the right one

Permute the same observations into a random order, recompute the same statistic,
and compare. This null is unusually strong because it **preserves everything
except the ordering**: the true total, the true dispersion, every outlier. If
the observed split is not extreme against it, the story rests entirely on the
sequence the observations happened to arrive in.

```python
def argmax_stat(v):
    c = np.cumsum(v)
    k = int(np.argmax(c)) + 1
    return v[:k].mean(), v[k:].mean(), k

pre, post, k = argmax_stat(x)
gaps = [np.subtract(*argmax_stat(rng.permutation(x))[:2]) for _ in range(200_000)]
p = np.mean(np.array(gaps) >= pre - post)
```

### The reading that made it worth writing down

| statistic | observed | null median | null 95th | p |
|---|---|---|---|---|
| peak of the equity curve | **+$32.19** | +$13.40 | +$32.39 | 0.052 |
| mean(before) âˆ’ mean(after) | **+$1.3515** | +$0.9971 | +$2.3292 | **0.272** |

**A zero-drift process with the same dispersion shows a positive argmax gap 85%
of the time.** The "it worked overnight and stopped in the daytime" story was
one of 108 orderings that all produce a rising-then-falling curve.

### The companion rule

Once the argmax split is disqualified, **re-split on something fixed in advance**
â€” the clock, the tier, the calendar â€” and report every bucket with n, the cost
bar for that bucket, the MDE, and one BH-FDR denominator over the whole family.
Here: night vs day on a pre-fixed 20:00â€“07:59 UTC boundary gave Welch p = 0.133,
and **0 of 13 permutation-tested buckets survived BH at 5%**.

### Two traps inside the companion rule

1. **A t-test on n = 5 with a 100% win rate is not evidence.** Three buckets
   "cleared" on t-statistics and none survived label permutation.
2. **Overlapping buckets are not independent tests.** The same five matches
   appeared in "04â€“07 UTC", in "Challenger" and in "night", so three apparently
   separate signals were three views of one run. Say so; BH does not fix it.

### Where it belongs

Anywhere a strategy is described as having "stopped working", "worked until X",
or "worked in regime R" where R was noticed after the fact. It is the sequential
form of Guard #1: **the thing that chooses your sample must not be able to see
your outcome**, and a cumulative curve can see all of it.

---

## 18. The structural-invariant canary â€” conservation can pass while the book rots

**Source:** [`bot-hunt/src/replay.py`](bot-hunt/src/replay.py)
**Contributed by `bot-hunt`, 2026-08-05,** replaying 13M rows of Kalshi L2.

Reconstructing an order book from `snapshot + deltas` has an obvious check:
**no price level may go negative**, because you cannot remove size that was
never there. It ran at **0.047% violations and PASSED throughout.**

The replay was still wrong. It ended with books like **bid 99 / ask 16 â€”
crossed by 83Â¢**, which is free money and cannot exist. The cause was that a
snapshot was *skipped* whenever the ticker already had carried-forward state, so
the book **never re-synced** and levels the feed expects a snapshot to clear
accumulated all day.

> **Stale levels are not negative levels.** Conservation is a check on the
> *arithmetic*; it says nothing about whether the state is *real*.

**The guard: assert an invariant the real object must satisfy, not just one your
update rule must satisfy.** For a two-sided book that is
`best_bid + best_opposing_bid â‰¤ 100`. Adding it turned an invisible failure into
a 75% violation rate on the first run.

It also settled two questions the conservation check could not:

| | crossed rate |
|---|---|
| pre-event observations | **5.60%** |
| post-event observations | **83.65%** |
| under the alternative price-space reading | **~100%** â€” refuted |

So the price convention was confirmed correct, and **settled books are simply
not maintained** â€” any L2 study must restrict to pre-event data. One invariant,
three answers.

---

## 19. The stability curve â€” a statistic that wanders was never a measurement

**Source:** [`bot-hunt/src/h10_stability.py`](bot-hunt/src/h10_stability.py)
**Contributed by `bot-hunt`, 2026-08-05,** after publishing a headline that
flipped sign 40 minutes later.

Re-run the whole analysis over **nested prefixes** of the same corpus and plot
each statistic against n. This is the method that killed this repo's own
stars-vs-substance false positive (**Ï +0.241 at n=105 â†’ âˆ’0.007 at n=3,165**);
it generalises to every number a study reports.

Four trajectory shapes, and only one of them is a result:

| shape | verdict | example from the run that motivated this |
|---|---|---|
| **flat** | âœ… a measurement | fill rate **30.8 â†’ 31.2%**, last-3 drift **0.01** |
| **sign-flips** | âŒ noise, not a small effect | net P&L **âˆ’1.71 â€¦ +2.55Â¢** |
| **decays toward zero** | âš ï¸ small-sample artifact | adverse selection **âˆ’14.04 â†’ âˆ’4.03pp** |
| **strengthens with n** | âš ï¸ contamination â€” see **#10** | thin-book edge **+2.05 â†’ +8.83pp** |

> **I published "you set out to earn +1.50Â¢ and you get âˆ’1.50Â¢" on 21 hourly
> files. Seven more hours made it +0.38Â¢.** The CI contained zero at both sizes,
> so nothing was ever significant â€” the point estimate was simply a point on a
> random walk, and I led with it.

**Run this before quoting any number, not after being embarrassed by one.** It
is cheap: replay once and slice the results by timestamp. (v1 re-ran the full
pipeline per prefix â€” O(nÂ²) â€” and produced nothing in 15 minutes.)

---

## 20. The placebo split â€” measure your estimator's noise floor before believing it

**Source:** [`bot-hunt/src/contamination_check.py`](bot-hunt/src/contamination_check.py)
**Contributed by `bot-hunt`, 2026-08-05.**

Before believing that a split on some variable produced an effect, **split the
same data on a variable that cannot possibly matter** and see what the estimator
reports. On a real dataset, splitting filled orders by the **parity of the
placement minute** produced **âˆ’3.7pp â€” 45% of the claimed effect.**

That is not a bug. It is the estimator's noise floor on this sample, and it is
the number a claimed effect has to be judged against:

> An effect that is **2.2Ã— a meaningless split** is not the same object as one
> that is 20Ã—, even if both have the same p-value.

This is the sibling of the synthetic null (#3). The synthetic null asks *"does
the pipeline invent an effect in data with none?"*; the placebo asks *"how big
an effect does this pipeline invent on THIS data from a split that means
nothing?"* **Real data has structure that synthetic data does not**, so the
placebo is the tighter bound and the one to report.

Related, from the same run: a permutation null that shuffles the outcome across
clusters exposed that the estimator was **biased by âˆ’2pp under the null** â€” so a
bootstrap CI centred on the raw difference was **anti-conservative** and excluded
zero when the permutation test gave p = 0.135. **When a bootstrap and a
permutation test disagree, believe the permutation test**: it absorbs the
estimator's own bias automatically.

---

## 21. UNTESTABLE is a verdict about the TEST, never about the effect

**Contributed by `bot-hunt`, 2026-08-05.** GUARDS #1 established three-valued
verdicts for the selection canary. **The principle is general and it is easy to
lose the moment a different test is written.**

A within-event stratification returned **+6.08pp with a CI of [âˆ’6.13, +20.13]**
against a **+8.19pp** baseline. The rule as first written printed:

> *"DOES NOT SURVIVE â€” the effect is BETWEEN events, not within them."*

**That is a claim about the world, and it was wrong.** A point estimate keeping
**74%** of its size has not collapsed; the *interval* widened, because the
within-event comparison had 75 events instead of the full sample's leverage.
"The effect is between-events" and "this test cannot resolve it" are opposite
findings and the code conflated them.

**The guard: any verdict function that can emit a conclusion must be able to
emit "I could not tell."** Three states, always:

| verdict | condition |
|---|---|
| **SURVIVES** | interval excludes zero |
| **UNDERPOWERED** | interval includes zero **but the point estimate is largely retained** |
| **COLLAPSES** | the point estimate itself goes away |

The same shape as *"innocence by emptiness is not innocence"* â€” and the same
shape as a control family that **did not run** being read as a control that
**passed**, which is how a `.get(key, 0)` default let `bot-hunt` print
*"control clean â†’ results are reportable"* over a family with no data at all.

---

## 22. Cross-venue joins: name similarity is RECALL; the second side is PRECISION

**Source:** [`bot-hunt/src/poly_crossvenue.py`](bot-hunt/src/poly_crossvenue.py),
[`crossvenue_join.py`](bot-hunt/src/crossvenue_join.py)
**Contributed by `bot-hunt`, 2026-08-06.** Three phantom classes in one session.

Matching a contract across venues on names alone fails in ways that are
invisible in aggregate:

| phantom | what happened |
|---|---|
| **wrong sport entirely** | a `KXCS2GAME` market paired to a **Mobile Legends** matchup. The join never checked the league. |
| **a degenerate short name** | Pinnacle's **"A Team"** normalises to **`"a"`** once the stopword *team* is stripped â€” and `"a" in name` is true for almost everything. **Four of twelve matches** collapsed onto the same matchup. |
| **the organisation's second roster** | "CYBERSHOKE Esports" â‰  "CYBERSHOKE Prospects"; "Vitality" â‰  "Vitality Academy". |

Four filters, in order of how much they buy:

1. **Category consistency** â€” the game, league or sport must agree. Cheapest and
   catches the worst phantom.
2. **A length floor on BOTH strings** before any substring match is allowed.
   Exact match otherwise. One-character names are not a hypothetical.
3. **Roster-suffix AGREEMENT, not detection.** Both venues legitimately say
   "Academy" when the match really is between academies. The test is whether
   they *agree*, not whether the token is present. *(A first version flagged 6
   of 10 correct pairs as suspect â€” a detector that fires on the correct case is
   not a detector.)*
4. **Verify the OTHER side.** A pair is two contracts; matching one name is half
   a match. Where only one side's name is recorded, the opponent can usually be
   recovered from the slug or ticker.

> The corpora reached this independently and put it best: **the dangerous
> phantoms have HIGH token overlap, not low** â€” *"who will **run** for the
> nomination"* versus *"will X **win** the nomination"* share almost every word.
> **Token overlap is a recall net; resolution-equivalence is the filter.**

**And record what the join drops.** In one case the phantoms happened to
contribute no observations, so the numbers were unaffected â€” *that was luck, not
design*, and the only way to know which you have is to look.


## 23. The renamed-field trap — a missing key reads `None` and becomes a silent zero

**Three sessions have now shipped this bug, and the third had the warning
already written down in front of it.** That is what makes it a guard, not a note.

**Source:** [`common/kalshi_fields.py`](common/kalshi_fields.py) — the field map
plus `assert_priced()`
**Triage:** [`common/scan_legacy_kalshi_fields.py`](common/scan_legacy_kalshi_fields.py)
→ [`common/LEGACY_FIELD_SCAN.md`](common/LEGACY_FIELD_SCAN.md)
**Tests:** [`common/tests/test_no_legacy_kalshi_fields.py`](common/tests/test_no_legacy_kalshi_fields.py) — 6 tests
**Contributed by `mlb-paper`, 2026-08-07**, after `crypto` hit it the same day.

### What it tests

Kalshi renamed its price and size fields to `*_dollars` and `*_fp`. **The legacy
names are not `None` — they are ABSENT.** So `obj.get("yes_bid")` returns `None`,
`float(x or 0)` turns that into `0`, and the run completes with clean-looking
numbers that are wrong in the flattering direction.

Verified against the live API on 2026-08-07, not recited from documentation:

| object | dead (absent) | live |
|---|---|---|
| market | `yes_bid` `yes_ask` `no_bid` `no_ask` `last_price` `volume` `volume_24h` `open_interest` `yes_bid_size` `yes_ask_size` | `*_dollars`, `*_fp` |
| trade | `yes_price` `no_price` `count` | `yes_price_dollars` `no_price_dollars` `count_fp` |
| orderbook | `orderbook` → `.yes` / `.no` | **`orderbook_fp` → `.yes_dollars` / `.no_dollars`** |
| candlestick | `volume` `open_interest` | `volume_fp` `open_interest_fp` |

### ⚠ The half-truth that makes a blanket ban wrong

On a **candlestick**, `yes_bid` / `yes_ask` / `price` are **live** — as
*containers* whose leaves are `*_dollars`. On the **same object**, `volume` and
`open_interest` are **dead**. `STATUS.md` records only the first half
("candlesticks are a different schema — do not fix them"), which would let
somebody read `candle["volume"]` believing candlesticks are exempt. They are not.

### The three incidents

| where | what | cost |
|---|---|---|
| `set1_overshoot` (C024) | `volume` → `volume_fp` | a dedupe summed to **zero**; the first run reported a clean fake result |
| `mlb-paper` 2026-08-07 | `orderbook.yes` → `orderbook_fp.yes_dollars` | every depth read 0 |
| `crypto` 2026-08-07 | `yes_price`/`no_price`/`count` on the trade object | **3,979,927 rows stored with a null price**, across two 50-minute pulls |

The crypto session's own account is the most useful sentence here: its recorder
docstring warned about exactly this, *in those words*, and it wrote a new puller
and did the documented thing anyway. **Prose does not hold.** GUARDS #6 records
the same lesson — the fee formula went 3 copies → 17 while the rule was only a
convention, and stopped at 17 the day it became a failing test.

### The enforcement is a RUNTIME assert, not a static ban

`assert_priced(obj, kind)` on the **first object of a pull**. Exact, cannot be
fooled by where the dict came from, and costs ten seconds instead of two
fifty-minute pulls. GUARDS #13 applied to a schema: *a 200 and a row count are
not a result.*

### Why the static half is a REPORT and not a failing test

Recorded because the mistake is instructive. The first version asserted
repo-wide that no dead name is read anywhere. **It fired on 25 files across 10
projects, and the first four sampled were all correct code** — two reading
candlesticks, two reading their own stored JSON under their own key names.

A static checker cannot see whether a dict came off the wire or out of your own
database. **A guard that fires on correct code in ten projects gets
wholesale-allowlisted and then deleted — guard rot arriving on day one.** So the
scan classifies into `WIRE` / `CANDLE` / `OWN`, only `WIRE` needs a human, and
the test defends the boundary rather than the whole repo.

### What it found on the day it was written — 44 files, 7 WIRE, 2 real bugs

Both the same mistake, and **neither is in this session's folder, so both are
flagged rather than fixed** (CLAUDE.md §5):

- **`market-selection/src/probe_orderbook.py:73`** — reads
  `r.json().get("orderbook")`, which is always absent, so `yes_levels` and
  `no_levels` are **0 for every market**. The file's entire purpose is probing
  book depth.
- **`crypto/src/mm_capability_probe.py:61`** — the same read. It prints
  `keys: []` and finds no levels, i.e. **it reports the orderbook endpoint as
  returning nothing.**

> ### ⚠ This may explain a contradiction this repo has recorded twice
> `CLAUDE.md` §5 names two cross-session disagreements that have already
> happened: the Kalshi maker-fee question, and **"whether the orderbook endpoint
> returns data."** A capability probe that reads the wrong key reports exactly
> that symptom.
>
> **Stated as a mechanism, not a verdict.** I have shown the probe *would*
> report an empty book; I have not shown this is what produced the recorded
> disagreement. The owning sessions should check.

### The one file to copy

`common/measure_tennis_maker_liquidity.py` already does the right thing: it
**asserts `volume_fp` is present and raises if the schema moved**, then reads
its own accumulator. It is the model.

---

## 24. The market does not quote a near-certainty — availability, not price

**Contributed by `soccer`, 2026-08-11**, on the closure of the late-comeback
idea. **Measured on SEVEN sports, not one** — see the cross-sport table below,
which is why this is no longer only a soccer finding.

### The shape it catches

> **Any strategy of the form "buy the thing that is 97% to happen, cheaply".**

Late-match favourites. Heavy pre-match favourites held to settlement. "Free
money" ladders at the extreme ends of a book. They all reduce to the same
sentence and they all fail the same way.

### What was measured

Kalshi soccer, 699 matches priced at **every displayed minute** (not only after
goals), inside the ~69-day candle window ending 2026-08-09. For each match, one
reading per minute, and the question: was anyone bidding on the losing side at
all?

| minute | trailing team came back, where a bet WAS possible | where it was NOT |
|---|---|---|
| 60 | **7.1 per 100** | 0.0 |
| 70 | 5.7 | 0.0 |
| 80 | 4.0 | 0.4 |
| 85 | 2.6 | 0.0 |

One reading per match, so the unit is the match. `GUARDS #1 check_selection` on
a *has-a-market* mask returns **FAIL**.

### The guard

**A quote is not a constant of nature. It is a decision by a market maker who
declines to quote when there is nothing left to be uncertain about.** So:

1. **Before pricing a strategy at an extreme probability, measure how often a
   tradeable quote exists there at all.** Not the spread — the existence. On
   Kalshi soccer at the 89th minute it was **16 in 100**, and **1 in 100** at 97
   cents or better.
2. **If you only measure where a quote exists, you have conditioned your sample
   on the event still being uncertain.** Every price you collected is a price on
   an unsettled outcome, which is a different population from the one the
   strategy was aimed at. That is a selection effect and it is invisible in the
   output.
3. **Report the availability rate next to the edge, always.** An edge measured
   on 5% of moments is a statement about that 5%.

### It is market-maker behaviour, not one sport's quirk

Measured 2026-08-11 on **284 settled Kalshi markets**, using only the price so
that no sport knowledge is needed. *Near-certain* = somebody bidding 95c+.
*Buyable* = an offer below 100 exists. The middling band is the control.

| sport | buyable when NEARLY SURE | buyable when IN DOUBT |
|---|---|---|
| soccer | **29 in 100** | 100 in 100 |
| basketball (women) | 31 in 100 | 100 in 100 |
| basketball | 37 in 100 | 100 in 100 |
| hockey | 51 in 100 | 100 in 100 |
| baseball | 53 in 100 | 100 in 100 |
| tennis (men) | 56 in 100 | 100 in 100 |
| tennis (women) | 67 in 100 | 100 in 100 |

**Every sport is buyable on all 33,802 of its middling minutes** — that perfect
control is what makes the left column mean something, and it rules out "thin
book". The soccer-specific explanation (a three-way market with a draw leg to
lay off against) is dead: six of these sports have no draw leg and show the same
shape. `soccer/reports/other_sports_probe.txt`.

**Availability is necessary, not sufficient.** Soccer's book was a clean 100 in
100 early in a match and the price was still bad. This guard says a trade may
not exist; it never says one is good.

### Why it is not the same as a wide spread

A wide spread is a cost and can be beaten by patience or by a limit order.
**Absence cannot.** There is no price at which the trade happens, so no amount
of sizing, patience or fee optimisation reaches it. **A strategy killed this way
does not get better with a deeper book** — a deeper book improves prices on
matches still in doubt, which are the ones you did not want.

### The cheap check

```python
# mask = "a tradeable quote existed at this moment"
# y    = the realised outcome the strategy depends on
leakguard.check_selection(mask, y, name="a market existed")
```

If that FAILs, the edge is conditional on quotability and must be stated that
way. **Soccer's `−0.40c per contract` became `−0.40c in the games and minutes
where a trade was actually available`, which is a materially different claim.**

### Where it belongs

Anywhere a strategy leans on extreme probabilities: `bot-hunt`'s de-vig work at
the tails, `crypto`'s ladders at 1c and 99c, `mlb-paper` and
`tennis-paper-forward` on heavy favourites, and any future revival of
**B024** — "buy the heavy favourite", which died on a spread artifact and would
meet this wall next.

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
14. **"It worked, then it stopped working" is the shape of noise.** If the
    split point was found by looking at the results, permute the same
    observations into a random order and see how often the null beats you.
    A zero-drift process rises then falls 85% of the time.
15. **A missing key is not a zero.** When a venue renames a field the old name
    goes ABSENT, `.get()` hands you `None`, and `float(x or 0)` turns that into
    a clean, plausible, wrong number. Assert the schema on the FIRST object of
    every pull. Three sessions here have shipped this, and the third had the
    warning written down in front of it.


---

## 25. Before recording that something does not exist, ask twice

**Contributed by `reopen`, 2026-08-11**, from auditing 611 claims across seven
ledgers. Asked for by the coordinator after this chat caught itself.

### The shape it catches

> **Any sentence of the form "there is no X", written from a probe that ran
> once.**

This repo has now produced **five** of them and every one was wrong: "Kalshi has
no Champions League", "Kalshi soccer is mostly friendlies", "no free ITF data
source exists", "the price sample contains no European league", and — from this
chat — "the set-score market has been minted zero times".

### What was measured

Three hosts, same URL, same minute, four different `User-Agent` headers:

| header | ESPN | Sofascore | ATP archive |
|---|---|---|---|
| `Mozilla/5.0 (…-research/1.0)` | **403** | 403 | 200 → **403** |
| bare product token | **403** | 403 | 403 |
| `curl/8.4.0` | **200** | 403 | 403 |
| none sent | **200** | 403 | 403 |

**Three hosts, three different policies.** ESPN blocks browser-shaped agents and
accepts curl. Sofascore blocks everything. **ATP returned 200 and then 403 to
the identical request one minute apart** — it rations, and a single probe of it
returns a number that is not a property of the host at all.

### The guard

1. **Run the probe twice, separated in time.** A rate limit, a warm cache and a
   real absence are indistinguishable in one call. Ten seconds of patience
   separates them.
2. **Vary the one thing you did not think was a variable.** One header across
   six hosts is one experiment, not six — and whichever header you pick, it will
   be wrong for at least one of them.
3. **A failure is not a finding.** Record the status code, never "not found".
   `market-selection/src/check_tennis_live.py` probed six sources with one
   header and wrote *"No free data source covering ITF tennis was found"*; that
   became **M027**, recorded SETTLED, and **B021** refuted it four days later.
4. **A dead fetcher does not look dead — it looks like the data is gone.**
   Eleven scripts in two folders were returning nothing at all while reporting
   normally. Assert content on the first object of every pull (GUARDS #15), and
   assert it on the *probe* too, not only on the pipeline.

### Why it earns a number of its own

**GUARDS #12 already says a 404 never establishes death.** This is the weaker
and commoner case: **a 200 that is really a 403, and a 403 that is really a
queue.** #12 is about interpreting the answer. #25 is about not trusting a
single ask.

### The cheapest version

```python
a = probe(url); time.sleep(10); b = probe(url)
if a != b:
    raise AssertionError(f"{url} is not stable: {a} then {b}")
```

**This chat found the ATP behaviour only because it ran the script a second
time to fix an unrelated crash.** Nothing about being careful would have caught
it.

---

## 26. A count of rows is not a count of people

**Added 2026-08-13 by `signal`, on the coordinator's instruction to generalise
it beyond Reddit.** Every corpus in this repo counts rows and reports them as if
each row were an independent voice. **They are not, and the failure is silent.**

**The case that produced it.** A finding about the gap between the displayed
price and the price you actually get arrived as post `1rvk0d1`. It had already
been read and recorded as `1rvk302` — **the same author, the same 90-day
experiment, posted to two subreddits with different titles and partly different
text.** The second copy even carried a detail the first did not, which is what
made it look like corroboration.

**Why this is not bookkeeping.** The Critic's standing first question is *"how
many independent sources?"*, and the entire argument for reading strangers is
that two of them agreeing is worth more than one asserting. **Cross-posting
manufactures the second stranger for free.** So does a tipster account posting
the same format daily, and so does a repo that is a fork of another repo.

**The guard.** Before any count of a corpus reaches a report:

1. **Say what one row is** — a post, a person, a claim, a repo — in the same
   sentence as the number. The unit-of-observation rule this repo already
   applies to markets applies to text.
2. **Near-duplicate sweep before counting**, not after. Same author plus
   overlapping text is one observation. Fork of the same upstream is one
   observation.
3. **When it has not been done, say so and downgrade the wording** to "N posts",
   never "N people" or "N independent sources".

**This is unfixed in `social-signal` right now.** 60,833 posts across Reddit and
Mastodon with no near-duplicate check, and every count reported so far treats
each row as one voice. Recorded as a known gap rather than quietly left.

**Related:** Guard #8 (effective sample size) is the same idea for correlated
observations; Guard #16 is the same idea for dedup deciding a headline.

---

## 27. HTTP 200 with an empty body — absence of data and absence of access are the same bytes

**Added 2026-08-14, measured, and it is Guard #25's sibling.** Guard #25 says
*before recording that something does not exist, ask twice*. This is the specific
network shape that makes asking once feel completely safe.

### The shape it catches

You request a feed. It answers **HTTP 200**. No error, no `429`, no
`Retry-After`, no redirect. The body is **`[]`** — two bytes. Every check a
careful person runs has passed: the host resolved, the connection succeeded, the
status is success, the JSON parses. **The only honest reading of that response
looks like "there is nothing there."**

It is often false, and the false version is indistinguishable from the true one
**at that endpoint**.

### What was measured

**2026-08-14, 05:39–06:00 UTC.** Bovada's baseball coupon returned 200 and a
two-byte body for twenty minutes. Pinnacle's free feed, read in the same second,
listed **twelve baseball games**, eleven of them starting later that day. So
"Bovada lists no baseball" was **wrong**, and it was one sentence from becoming
*"the retail-bookmaker route is dead"* — an idea that had already been blocked
for six days on a different false absence.

**The discriminator is a CONTROL ENDPOINT on the same host, in the same second:**

| Bovada coupon | bytes | events |
|---|---|---|
| `baseball/mlb` | **2** | **0** |
| `football/nfl` | 625,438 | 17 |
| `tennis` | 1,926,596 | 160 |

That is what tells the two apart, and nothing at the original endpoint can.

**Then the same probe measured the other half.** After roughly fifteen fetches in
a few minutes the **control** stopped answering too — so at that point the
correct verdict flipped from "empty board" to "**we are the problem**". A checker
without a control cannot see that flip either.

### The guard

**Never record an empty payload as an empty board until a control endpoint on
the same host has returned a full one in the same pass.** Three states, not two:

| control | subject | verdict |
|---|---|---|
| full | full | data |
| **full** | **empty** | **genuinely empty — record it** |
| **empty** | **empty** | **NO ACCESS — record nothing about the subject** |

The third row is the whole point. It must **fail closed**: an unknown is not an
absence, and "we could not tell" is a legitimate and much more useful entry in a
ledger than a confident zero.

Pick a control that is **on the same host, needs no credential, and is expected
to be non-empty for reasons independent of the thing under test** — a different
sport, a different region, a static index. A control that can plausibly be empty
at the same time as the subject is not a control.

### Why it earns a number of its own

`reopen`'s audit found **13 of 156 closures were "the data was not available" and
the data was.** Guard #23 covers the same error caused by reading a renamed
field; Guard #25 covers it as a habit of mind. **Neither would have caught this
one**, because nothing was misread and nothing was assumed — the feed really did
say `[]`, and believing it was correct behaviour given the information at hand.
The fix is not more care. It is **one more request**.

### The other two shapes of the same failure, from the same afternoon

1. **A permission check that fails OPEN.** The first robots-checker returned
   "no robots file" on a non-200 and then **fetched anyway** — labelling a site
   unrestricted when that site names our crawler and disallows everything, its
   robots file merely 403ing to us as well. **A permission check that cannot read
   the permission must never conclude permission.**
2. **The wrong field name, for the third time in a week** (C024, M024, and a
   retail census that read `competitors[].description` where the field is
   `competitors[].name`). Every team came back empty and the join matched
   nothing. **It was caught by arithmetic refusing to add up** — nine events with
   two competitors each cannot also be one event with two named clubs — **not by
   care.** So: put a cheap consistency identity next to any join, and let it be
   the thing that fails.

**Related:** Guard #23 (renamed fields), Guard #25 (ask twice before recording an
absence), Guard #12 (the legacy-field trap).

---

## 28. The coin sets the sample size, and it is bigger than anyone plans for

**Contributed by `soccer`, 2026-09-02**, from the reverse-trade run. **This is
arithmetic, not a method preference.** It cost this folder a pre-registered
threshold that was wrong by a factor of six, and it applies to every
paper-trading project in the repo.

### The rule

A settled bet pays 0 or 100. Nothing else. So the spread of its result is fixed
by the price alone:

    spread = 100 x sqrt(P x (1-P))

and **no estimator, model or cleverness reduces it** for the question *"did this
actually make money"*. To see an edge of E cents you need about
`(2 x spread / E)^2` settled bets:

| price paid | spread | to see 1c | to see 2c | to see 5c |
|---|---|---|---|---|
| 50c | 50.0c | 10,000 | 2,500 | **400** |
| 70c | 45.8c | 8,400 | 2,100 | 336 |
| 90c | 30.0c | 3,600 | 900 | 144 |
| 97c | 17.1c | 1,164 | 291 | **47** |

**Measured against reality:** the soccer reverse trade had a median price of 70c
and a realised spread of **41.9c** on 73 matches, against a predicted 45.8c. The
arithmetic holds.

### ⚠ The trap this creates, and it is the reason to file it

**The market gives you liquidity exactly where measurement is most expensive.**

- At **97c** an edge is cheap to measure — 47 bets to see 5 cents — but
  **GUARDS #24** says nobody quotes it, so you cannot trade there.
- At **50c** you can always trade — soccer measured 100 in 100 — but it takes
  **400** bets to see the same 5 cents, and **2,500** to see 2.

**So "I can trade it" and "I can measure it" pull in opposite directions**, and
a project that only checks the first will run for months without being able to
see the effect it is looking for.

### What to do about it, because the wall has a door

**The floor above is for an UNPAIRED test** — "is this strategy's result
different from zero". **A PAIRED test escapes it**, because the thing that
creates the variance is the match outcome, and pairing cancels it:

- **Two arms on the same game.** Bot A versus bot B on the identical event: the
  outcome is shared, so it drops out and what remains is the difference in their
  decisions.
- **The same arm against the market's own price** on the same event.
- **Any design where the coin appears on both sides of the subtraction.**

**Before running a fleet for months, work out which of the two you are doing.**
The unpaired version needs thousands of settled bets; the paired one needs far
fewer, and it is usually the question actually being asked ("is my rule better
than the obvious alternative") rather than the one being measured.

### Where it belongs

Any project counting settled bets. **Read this off your own data before the
season, not after:** median fill price, count of settled positions, then the
table above.

---

