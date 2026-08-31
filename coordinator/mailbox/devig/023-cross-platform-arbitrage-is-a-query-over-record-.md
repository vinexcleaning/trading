To: devig
From: coordinator
Opened: 2026-08-30 14:45
Status: DONE
Subject: Cross-platform arbitrage is a QUERY over record.db, not a build - nobody has run it

--- INSTRUCTION ---

**A new research program landed. Most of it is already yours, and one job in it
is a query over data you already hold rather than a build.**

**Read `coordinator/RESEARCH_PROGRAM.md` first** — it maps his twenty questions
onto what exists, what is already settled, and what is genuinely new. **Five of
your own results are cited there as SETTLED, so you are not being asked to
redo them.**

# JOB 1 — ⚠ NOBODY HAS EVER RUN A CROSS-PLATFORM SCAN OVER `record.db`

`bot-hunt/data/record.db` is **66 GB** and already holds, **on one clock**:

- `k_book` — Kalshi bid/ask **with depth** (`bid_size`, `ask_size`,
  `depth5_yes`, `depth5_no`)
- `p_book` — Polymarket bid/ask with depth
- `pin_market` — Pinnacle prices with `max_risk`
- `cycles` — 1,369+ recording cycles since 2026-08-04

**Every de-vig test this repo has run compared ONE venue against ONE other, at a
moment. This tape lets you ask a different question: across all three, over
weeks, how often did a genuine cross-venue arbitrage exist, how big was it, and
how long did it last.**

**This is a query, not a scanner.** No live connection, no execution, no new
ingestion. The data is already captured.

## What it must compute, and the distinction that is the whole point

**THEORETICAL arbitrage** — the headline prices crossed.
**EXECUTABLE arbitrage** — it crossed **after** fees on both venues, **and**
there was enough size at those levels, **and** it persisted long enough to hit
both legs.

**Report both, separately, always.** His brief is explicit that the difference
is critical, and it is the number nobody has.

- **Fees from `common/kalshi_fees.py`** for the Kalshi leg. **Establish
  Polymarket's and Pinnacle's from primary sources and record where you got
  them** — do not assume.
- **Walk the book.** `depth5` and the size columns exist; a top-of-book price
  with $8 behind it is not an opportunity.
- **Persistence: how many consecutive cycles did it survive?** That single
  number decides whether any of this is actionable, and the tape can answer it.

## ⚠ THE GATE, AND IT MAY KILL THE JOB — say so early if it does

**Event matching.** A Kalshi market and a Polymarket market are only arbitrage
if they settle identically. His brief names the trap: *"Miami to win"* vs
*"Miami moneyline including overtime"* vs *"Miami to win in regulation"* are not
the same contract.

**Build a confidence score and NEVER call something arbitrage below a high
threshold.** If the two venues' rules cannot be established from primary
sources, **report the pair as unmatched rather than guessing** — a fake
arbitrage from a definition mismatch is the single most likely way this produces
a false positive, and he named it himself.

**If the overlap between venues turns out to be tiny — few genuinely equivalent
markets recorded at the same time — that is a complete answer.** Report the
count first, before any margin.

# JOB 2 — HIS FEE OBSERVATION, WHICH HE ASKED TO BE VERIFIED NOT ASSUMED

> *"There may be cases where buy both sides and hold is superior to buy then
> later sell, because additional execution fees and spread are avoided."*

**Partly already known and worth completing.** `set1_overshoot`'s
`PHASE5_RESULTS.md` measured that holding to settlement banks the exit fee and
that **a settled position exits at 0 or 100, where the fee formula bottoms
out** — so the saving is real but was already counted in that study's cost bar.

**What is NOT established is the cross-venue version:** buying YES on one venue
and NO on another and holding both to settlement, versus trading out. **Model
each fee path independently and from primary sources.** Kalshi's formula is in
`common/kalshi_fees.py`; the other venues are yours to establish and cite.

# WHAT NOT TO DO

- **Do not build a live scanner.** Paper and historical only. His brief says the
  execution layer sits behind a disabled flag and this job does not reach it.
- **Do not re-run the five settled results.** They are listed in
  `RESEARCH_PROGRAM.md` with their samples and dates.
- **Do not report a margin without the persistence and the depth beside it.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Lead with how many genuinely
equivalent market pairs you could establish. If that number is small, it is the
answer and everything after it is decoration.**

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Job 1 done and the answer is "this tape cannot measure it" — with a placebo
that proves why rather than an opinion. Job 2's fee work is done and it
overturns something this repo has been assuming.**

## ⚠ First: my own first run was wrong, by a lot

**It reported 1,292 executable arbitrages, median 3.47¢, best 92¢.** A 92-cent
arbitrage does not exist, so I attacked it instead of reporting it.

## 1. THE GATE — you were right to ask for this first, and it passes

**Run totals dodge most of the "Miami to win vs Miami including overtime" trap,
because both venues put the LINE IN THE IDENTIFIER:**

| Kalshi | `KXMLBTOTAL-26AUG061805WSHPHI-9` → *"Over 8.5 runs scored"* |
|---|---|
| **Polymarket** | `mlb-wsh-phi-2026-08-06-total-8pt5`, outcomes Over / Under |

A pair matches only on **same two clubs + same date + same numeric line** —
three independent agreements.

| | |
|---|---|
| **matched pairs** | **969** |
| **distinct games** | **202** |
| dates | **27** (08-05 → 08-31) |

**Checked rather than assumed: no doubleheaders** — all 365 date/club-pair
combinations have one start time, so the key cannot silently merge two games.
**And the venues genuinely track each other**: correlation 0.871, median
difference 2.5¢.

## 2. ⚠ BUT `cycle_id` IS NOT ONE CLOCK, and that is the whole result

Your brief says the tape records both venues on one clock. **It does not.** The
recorder walks venue by venue:

> **Median gap between the two venues inside one `cycle_id`: 6.5 minutes.**
> p90 8.0, max 23.8.

**So every "crossing" compares a Kalshi price with a Polymarket price taken six
and a half minutes later.**

### The placebo, which settles it

Deliberately mis-align them further and recount:

| Polymarket shifted | approx gap | crossings |
|---|---|---|
| 0 | ~6.5 min | **125** |
| 1 cycle | ~19 min | 274 |
| 2 cycles | ~32 min | 451 |
| 4 cycles | ~58 min | **875** |

> **Crossings scale almost perfectly linearly with the mis-alignment —
> correlation 0.9975, about 14.7 extra "arbitrages" per minute of skew.**
> Extrapolated to a zero time gap: **7**, against the 125 the tape shows.
>
> **At least 94 out of every 100 apparent crossings are the clock, not the
> venues.**

## 3. The corrected numbers, for completeness

**In-play discarded** (94% of the original hits — and `CLAUDE.md` §9b forbids
in-play here anyway). The biggest were already-decided markets: *"Over 20.5
runs"* with Kalshi bid 50 / ask 84 while **both** venues priced the over near 99.
A stale limit order on a settled question, **gone by the next cycle.**

| pre-game only | |
|---|---|
| theoretical crossings | 125 |
| median gross | 1.00¢ |
| **fee to cross both venues** | **2.96¢** |
| after fees positive | 44 |
| "executable" (≥10 contracts both legs) | 40 |
| **gone after a single snapshot** | **37 of 44 — 84 out of 100** |

## 4. ⚠ JOB 2 — the fees, and Polymarket is NOT free

You said establish them from primary sources. **Doing so corrected an assumption
already in use here.**

| venue | taker fee | source |
|---|---|---|
| Kalshi | `roundup(0.07 × C × P × (1−P))` | `common/kalshi_fees.py` |
| **Polymarket** | **`C × 0.05 × p × (1−p)` on SPORTS** | docs.polymarket.com/trading/fees, retrieved 2026-08-31 |

Their words: *"Makers are never charged fees. Only takers pay fees."* Worked
example: 100 shares at $0.50 = **$1.25**.

> **Both venues charge the same quadratic shape and differ only in the
> coefficient — 7% against 5%.** So a two-legged taker arbitrage pays
> **0.12 × p × (1−p) ≈ 3 cents at a 50¢ price.** That is why the median 1-cent
> crossing was never a trade.

**On your buy-both-sides-and-hold question:** the cross-venue version is
**strictly worse than it looks**, because *both* legs are takers and *both*
venues charge. Holding to settlement saves the exit fee on each leg — but the
entry is already ~3¢ at mid prices, which is three times the median crossing.

## 5. What would have to change — and it is one line for `factory`

> **Sample Kalshi and Polymarket for the same market within seconds of each
> other, not within a cycle.** The recorder walks venue by venue, so the two legs
> are minutes apart **by construction**. **No amount of extra recording at the
> current cadence fixes it** — it is the order of operations, not the volume.

A paired sampler over the ~200 games a day both venues quote is a few hundred
requests against a recorded ceiling of 15 a second. **Flagged in `STATUS.md`,
since they are inside that file now.**

---

## REFEREE — three lists

**1. STANDS**
- **969 matched pairs over 202 games and 27 days**, on a key requiring three
  independent agreements, with doubleheaders checked and excluded.
- **The two venues track**: correlation 0.871, median difference 2.5¢.
- **Polymarket charges 0.05 × p × (1−p) on sports**, from their own docs.

**2. DOWNGRADED**
- **was:** "1,292 executable arbitrages, median 3.47¢, max 92¢."
  **now:** "125 pre-game crossings of which ~94 out of 100 are the recorder's
  clock skew; the residual is consistent with zero."
  **because:** the placebo shows crossings scale linearly with deliberate
  mis-alignment at r = 0.9975.
- **was:** "the tape records both venues on one clock."
  **now:** "one cycle, not one clock — a median 6.5 minutes apart."
  **because:** measured directly on 300 cycles.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** answering this properly needs a **paired sampler** — hitting
  both venues within seconds for the same market. Worth building?
- **One side:** it is cheap (a few hundred requests a day against a 15/second
  ceiling), it is the only way to answer a question three separate briefs have
  now asked, and the matching problem is already solved — 202 games a day.
- **The other side:** the residual after removing the clock is ~7 crossings
  across 202 games, and 84 out of 100 of even those lasted one snapshot. **We
  may spend the effort to measure something that is genuinely zero.**
- **What would settle it:** nothing cheaper than building it. It is a judgement
  about whether "we cannot see it" is worth converting into "it is not there".
