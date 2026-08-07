# PREREGISTRATION — tennis paper-only forward test

**Written 2026-08-06, before the runner accumulated a single settled match.**
Nothing below was chosen after seeing an outcome. Amendments go in §10 with
their date and their reason, and the original text is never edited.

Related: [GUARDS.md](../GUARDS.md) · [LEDGER.md](../LEDGER.md) ·
[SCOREBOARD.md](../SCOREBOARD.md) · [DECISIONS.md](DECISIONS.md)

---

## 1. What is being tested

Sixteen bots trade the same pool of Kalshi singles tennis matches on paper.
Five mentalities × three exit modes, plus one no-trade control.

| | hold to settle | exit once | exit and re-enter |
|---|---|---|---|
| **favourite** (80c+) | `favourite__hold` | `favourite__exit-once` | `favourite__free` |
| **underdog** (5–35c) | `underdog__hold` | `underdog__exit-once` | `underdog__free` |
| **brief-led** | `brief-led__hold` | `brief-led__exit-once` | `brief-led__free` |
| **momentum** | `momentum__hold` | `momentum__exit-once` | `momentum__free` |
| **unconstrained** | `unconstrained__hold` | `unconstrained__exit-once` | `unconstrained__free` |
| **control** | `control__no-trade` — logs intended trades, takes none | | |

Every bot also chooses its own **stake** per trade from its own confidence,
inside a $500 paper bankroll it never tops up. Selection and sizing are scored
separately (§5).

**No money is involved and none can be.** The package has no credentials, no
order endpoint, and a GET-only host allowlist. `tests/test_paper_only.py`
enforces it at source level and fails the build if order-shaped code appears.

---

## 2. The unit of observation

**A settled match.** Not a fill, not a tick, not a market row.

Kalshi lists one market per player, so each match has two mirrored markets.
They are folded into one on **first ticker alphabetically** — the rule measured
clean at P(kept side wins) = 0.4969, z = −0.88. Deduping on `volume_fp` reads
0.5356, z = +10.0, and voided three phases of earlier work. GUARDS #1.

**Target: 50 settled matches**, expected in about a week at the observed rate
of 120–125 open matches at any moment.

---

## 3. ⚠ THE HONEST POWER CALCULATION, STATED BEFORE THE RUN

**Fifty matches cannot decide whether any of these bots makes money.** This is
arithmetic, not pessimism, and it is written here so that the result cannot
later be read as though it were a verdict.

Per-match profit per contract has a standard deviation of about **45c** (from
`set1_overshoot`, 3,436 events). With a Benjamini–Hochberg correction at
q = 0.10 across all sixteen bots:

| matches per bot | MDE at α=.05 | **MDE under BH across 16** |
|---|---|---|
| 20 | 28.2c | **36.0c** |
| **50** | 17.8c | **22.8c** |
| 120 | 11.5c | 14.7c |
| 500 | 5.6c | 7.2c |
| 2,000 | 2.8c | **3.6c** |

The cost bar on Kalshi tennis is about **3.6c**. So:

> **To resolve an edge the size of the cost bar, at q = 0.10 across sixteen
> bots, needs about 2,000 settled matches PER BOT.** Fifty is 2.5% of that. At
> fifty matches this test can only detect a 22.8c edge — roughly six times the
> entire cost of trading, and larger than anything in the archive by an order
> of magnitude.

Worse: no bot enters every match. A bot entering 40% of the pool has n ≈ 20 and
an MDE of **36c**.

**Therefore the P&L result is pre-registered as UNTESTABLE at n = 50.** It will
be reported with its interval and its MDE beside it, and the word "works" will
not be used. GUARDS #21: UNTESTABLE is a verdict about the test, never about
the effect.

---

## 4. What IS decidable at fifty matches — the primary endpoints

These are the gates. They are measurable because their variance is small, and
they are the questions this run actually exists to answer.

### T1 — Does the machinery survive a week unattended?
**Gate:** ≥ 95% of expected ticks completed, zero double-runner incidents, the
state file resumes cleanly across at least one deliberate restart, and the two
recorders already on the laptop are untouched.
**Pre-registered prediction:** pass.

### T2 — Is the brief actually available for the matches Kalshi lists?
**Gate:** report, do not threshold — % of matches where both players resolve in
the archive, % where surface is known, % with point-by-point coverage, split by
tier (ATP/WTA vs Challenger vs ITF).
**Pre-registered prediction:** ATP/WTA resolution above 90%; **ITF below 60%**;
point-by-point coverage **below 20% outside the main tour**. If ITF resolution
comes in above 80% I should suspect the name matcher of accepting loose
matches, not celebrate.

### T3 — What does it actually cost to trade this market?
**Metric:** realised round-trip cost per contract = entry fee + exit fee +
spread paid + measured slippage between decision and fill.
**Power:** sd ≈ 2.5c, so at n = 50 the MDE is **0.99c**. This is measurable.
**Pre-registered prediction:** **3.5c to 4.5c**, consistent with the archive's
3.61c bar. A number below 2.5c means the fill model has gone optimistic and
should be treated as a bug until proven otherwise.

### T4 — Do the mentalities actually differ, or is this one bot in five hats?
**Metric:** pairwise Jaccard overlap of the sets of matches each mentality
entered, and the correlation of their conviction scores.
**Gate:** report. Median pairwise Jaccard **below 0.5** would mean they are
genuinely different instruments; **above 0.8** would mean the labels are
decoration and the sixteen-way correction is measuring one thing sixteen times.
**Pre-registered prediction:** favourite and underdog near-disjoint (they trade
different price bands by construction); unconstrained overlapping everything.

### T5 — What does execution take out?
**Metric:** control P&L (mid price, zero fees, hold to settle) minus each
traded bot's P&L, on the matches both took.
**Note:** the control's own number is **FAKE BY CONSTRUCTION** and is labelled
as such everywhere. It is not a strategy. It exists so the execution cost can
be read off directly, which is the same trick that turned a +14.4% to +24.6%
tennis result into −24.3% to −30.9% once fills were made executable.
**Pre-registered prediction:** the gap is **larger than every bot's edge**.

---

## 5. Separating sizing skill from selection skill

A single P&L number confounds two abilities. They are scored apart:

| | metric | what it answers |
|---|---|---|
| **selection** | mean profit per **contract**, every settled match weighted equally | did it pick well? |
| **sizing** | stake-weighted mean minus equally-weighted mean | did betting more on its better ideas help? |
| **sizing, direct** | corr(stake fraction, realised per-contract P&L), clustered by match | is confidence informative at all? |

**Power on the correlation:** at n = 50 only |r| ≥ **0.39** is detectable at 80%
power. At n = 20, |r| ≥ 0.59. **Sizing skill is therefore also UNTESTABLE at
this sample size** unless it is enormous, and will be reported as an estimate
with its interval.

**Pre-registered prediction:** the sizing term is indistinguishable from zero,
and its sign is a coin flip. If stake-weighting beats equal-weighting by more
than 3c per contract, the first thing to check is whether the bankroll cap
correlated stake with entry ORDER rather than with confidence.

---

## 6. Secondary endpoint — the P&L, reported but not believed

For each of the sixteen bots:

- mean profit per contract, with a **match-clustered** bootstrap 95% interval
- the same, stake-weighted
- n (settled matches entered), and the MDE at that n
- the naive benchmark beside it: **buy the favourite side of every match in the
  pool and hold** — the archive's own "buy everything at the open" comparator
- the round-trip cost bar for that bot's own average entry price

**One BH-FDR denominator of 16**, at q = 0.10, over all sixteen bots including
the control and including `unconstrained`. Cancelled or zero-n bots stay in the
denominator as `CANCELLED` rows so it cannot quietly shrink (crypto's
convention, GUARDS #11).

Three-valued verdict per bot, never two:

| verdict | condition |
|---|---|
| **SURVIVES** | BH-adjusted interval excludes zero AND the point estimate clears that bot's own cost bar |
| **UNDERPOWERED** | interval includes zero but the point estimate is largely retained |
| **COLLAPSES** | the point estimate itself goes away |

**Pre-registered prediction, stated as a number so it can be wrong:** every bot
lands between **−12c and +2c** per contract, no bot survives BH, and the modal
verdict is UNDERPOWERED. The archive is 55 strategies, 0 that work, and 45
corrections of which every single one shrank the edge. That is the prior.

**Pre-registered prediction on the exit modes specifically:** `hold` beats
`exit-once` beats `free`, because the archive measured the same signal at
−2.29c held and −9.36c with a stop-loss and profit ladder attached, and the
stop-loss alone moved one test from +0.62c to −3.77c. If `free` wins, that is
the most interesting result this run could produce and it should be attacked,
not published.

---

## 7. Guards that must pass, or the run is void

| # | guard | how it is enforced |
|---|---|---|
| 1 | selection canary | dedupe is on ticker order only; `test_selection.py` asserts no outcome-bearing field is read |
| 2 | within-match leak | any market carrying a `result` is filtered out of the pool before any bot sees it; the count is logged every tick |
| 6 | exact-decimal fees | `common/kalshi_fees.py` only; `test_no_fee_reimplementation.py` fails on a copy |
| 7 | fill at the ask, never the mid | there is no mid in the engine; the brief's field is named `mid_DIAGNOSTIC_ONLY` |
| 8 | effective sample size | every interval is clustered on **match** |
| 9 | guard rot | the paper-only detector is run against a planted violation |
| 11 | one BH denominator | 16, fixed here, before any result |
| 12 | content-level health | % of markets carrying an ask, zero-ask count, stale-book count, asserted every tick |
| 13 | assert content not the call | every CSV's header is checked against the columns about to be read |
| 18 | structural invariant | bid sum > 100c on a complementary pair is impossible and is alerted |
| 20 | placebo/matched control | the after-break statistic is measured against the after-a-hold control in the same matches |

**If the result-leak filter ever fires on a market a bot had already traded,
the run is void and is restarted.**

---

## 8. What would make me doubt a positive result

Written now, so it cannot be rationalised later:

1. **Any bot beating its cost bar at n < 100.** The MDE says that cannot be
   resolved, so a "significant" result at that n is a fluke or a leak.
2. **A result that strengthens as the filter gets more precise.** GUARDS #10 —
   monotone strengthening is evidence of contamination until proven otherwise.
3. **`free` beating `hold`.** It contradicts the archive's own measurement of
   the same mechanism twice over.
4. **Any bot whose edge lives in wide quotes.** The heavy-favourite "edge" was
   +1.18c where the spread was ≤2c and +7.92c where it was >8c. That shape is
   the spread, not an edge. Every result will be split by spread bucket.
5. **The control looking tradeable.** It buys at a price that does not exist and
   pays no fees. If it looks good, that is the measurement working.
6. **A number landing exactly where the archive's numbers landed.** GUARDS #16 —
   when a new measurement agrees suspiciously well with the old ones, go and
   look for the line of code that put it there.

---

## 9. Fixed parameters, declared before the run

| parameter | value | why this one |
|---|---|---|
| poll interval | 60 s | a tennis game lasts minutes; faster buys nothing and costs politeness |
| fill timing | the **next** tick's book | the latency model; a decision cannot fill at the price that triggered it |
| pending order max age | 300 s | across a restart, an old intention must not fill against a moved book |
| depth cap | 25% of shown top-of-book size | never consume size the book did not show |
| bankroll | $500 per bot, never topped up | fixed, so a losing run shrinks its own sizing |
| stake fraction | 0.5% to 6% of bankroll | |
| Kelly | quarter | |
| **model weight in sizing** | **0.35** | the archive measured a far better tennis model losing to the bookmakers by +0.01922 Brier on n=2,645; a crude elo does not deserve to outvote the market. **Sizing only — selection uses the raw model gap, so the two stay separable.** |
| take profit / stop | ±12c | symmetric, so the exit modes are not secretly directional |
| re-entry cooldown | 900 s | the live bot re-entered a falling market after 24 s, three times |
| max entries per event | 2 (`free` only) | |
| **re-entry size cap** | **never larger than the first entry** | this alone refuses the 12 → 20 → 32 martingale that cost −$7.56 in 50 minutes |
| entry conviction bars | favourite 2.0 · underdog 2.0 · brief-led 2.5 · momentum 2.5 · unconstrained 3.5 | set from the FIRST live tick's conviction distribution so that every bot can fire at all. Calibrated on entry FREQUENCY with zero outcome data available — see DECISIONS.md D6 |

---

## 10. Amendments

### A1 — 2026-08-06. T2's prediction was WRONG, and the code was right.

**What §4/T2 predicted:** "ITF [player resolution] **below 60%**", and "if ITF
resolution comes in above 80% I should suspect the name matcher of accepting
loose matches, not celebrate."

**What was measured on the first 123 matches:** ATP 90%, WTA 100%, Challenger
100%, **ITF 88.9%**.

**So the check fired, and it was run.** Of 172 ITF player resolutions, **168
were exact normalised-name matches** — no fuzziness involved at all. Only 4 used
the surname fallback, and all four are correct:

| Kalshi | archive | archive n |
|---|---|---|
| Tsung-Hao Huang | Tsung Hao Huang | 300 |
| Sasikumar Mukund | Sasi Kumar Mukund | 685 |
| Giorgia Pedone | Georgia Pedone | 274 |
| Jodie Anna Burrage | Jodie Burrage | 424 |

Zero false matches. **The prediction was simply wrong**, for a good reason:
Sackmann's `atp_matches_futures_*` and `wta_matches_qual_itf_*` files cover the
ITF circuit thoroughly, and ITF is not the coverage desert I assumed.

**Nothing in the design changed.** This amendment exists because a
pre-registered prediction failed, and the failure is the record.

### A2 — 2026-08-06. Surface coverage: 17.8% → 100% on ITF. A build change, not a gate change.

The first surface lookup was a hand-written table of tournament names. It
resolved 100% of ATP/WTA and **17.8% of ITF**, which is **73% of everything
Kalshi lists**. Replaced with a lookup derived from the archive's own
`tourney_name` → `surface` record, keyed on venue with the prize-money prefix
stripped (4,845 venues). ITF surface coverage is now 100%, Challenger 84.6%.

A venue that has hosted more than one surface resolves only at ≥80% agreement
over ≥2 events, and otherwise reports **unknown** with the reason. See
DECISIONS.md D5.

**No gate, threshold, prediction or bar was changed.** This made a brief field
available that was previously missing on three quarters of the sample; it did
not alter what any of them is measured against.

### A3 — 2026-08-07. The BH denominator RISES from 16 to 32. §6 is superseded. **Agreed.**

**What §6 declared:** "One BH-FDR denominator of 16, at q = 0.10, over all
sixteen bots."

**What supersedes it:** [../JOINT_MULTIPLICITY.md](../JOINT_MULTIPLICITY.md),
written by the concurrent `mlb-paper` session before either test had a settled
result. A second sixteen-bot forward test — same five-mentality × three-exit
structure, same exchange, same repo, same fortnight — is running alongside this
one. Correcting each test inside itself and then reading the two side by side is
**a 32-way search reported as two 16-way searches**.

**This session has checked the arithmetic and agrees.** Verified independently:

| n matches | MDE at m=16 | MDE at m=32 | widening |
|---|---|---|---|
| 20 | 35.98c | 38.20c | +6.2% |
| **50** | **22.76c** | **24.16c** | **+6.2%** |
| 2,000 | 3.60c | 3.82c | +6.2% |

and their power constant `k = 3.797` at α = 0.10/32 reproduces exactly. Their
prose says "about 8%"; it is **6.2%** — noted, immaterial, and not worth an
amendment of its own.

**The cost to this test:** resolving a 3.6c edge moves from **~1,998 to ~2,252
settled matches per bot**. §3's conclusion is unchanged and slightly
strengthened: the P&L endpoint remains UNTESTABLE at n = 50, now at 24.2c
rather than 22.8c.

**Why this amendment is legitimate and a downward revision would not be:** a
multiplicity correction may only ever be made **stricter** after a run begins.
Raising it costs power, which is a price paid against oneself. Lowering it —
including by dropping a test from the family after seeing its results — is how
a search gets reported as smaller than it was, and is the error
`wallet-copy-study` R5 already priced: **54 of 206 "significant" in a pure
null** against 0 of 249 done correctly.

**Accepted in full, including the rules that come with it:**

1. cancelled, zero-entry and control bots stay in the denominator
2. **the two tests are reported together, or neither is reported** — a tennis
   result published alone under a 16-way correction is published at the wrong
   bar
3. the denominator stays 32 even if one test stops early
4. it never falls; if either test adds a bot it rises, and every previously
   reported p-value is recomputed

**Changed in code:** `src/analyse.py` `N_HYPOTHESES = 32`, with `N_OWN_BOTS =
16` retained so each bot's report shows the MDE both jointly and alone. Every
output field is renamed (`bh_pass_q10_of_joint32`, `mde_at_this_n_bh_joint32`)
so a stale reader cannot mistake one for the other. `analyse.py` now prints the
reporting rule at the top of its own output.

**Not changed:** §3's table and §6's text stay as originally written, per the
rule that the text above §10 is never edited. A reader arriving at §6 sees 16;
this amendment is what tells them it is 32.

---

*Each entry gets a date, a reason, and what it changed. The text above §10 is
never edited.*
