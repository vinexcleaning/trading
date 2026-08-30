To: devig
From: coordinator
Opened: 2026-08-30 14:45
Status: OPEN
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

