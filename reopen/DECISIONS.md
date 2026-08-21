# DECISIONS.md — reopen

Judgement calls taken without asking, per `CLAUDE.md` §2. Newest first.

---

## 2026-08-20 — HIS DECISION: no paid tennis history. CLOSED, do not raise again.

**His words, 2026-08-20:** *"I don't wanna pay any money for tennis history."*

**This is the second time he has declined it** — once through `tennis`, once
through this chat. **It is closed.** `CLAUDE.md` §1: a request is raised once,
clearly, then recorded and dropped. Re-raising it spends the credibility needed
for the next thing that actually matters.

**Not a judgement call I took — his call, recorded here so nobody re-derives the
request in a month and asks him a third time.**

### What it blocks, marked rather than left looking live

| item | status now |
|---|---|
| **RS-06** (player features on three years) | **BLOCKED — not testable.** A spec that cannot be run is not a pending spec. |
| **RS-07** (the tennis buckets) | **WEAKENED, still partly runnable** — see below |
| **T002** (features stop 2026-06-02) | **open and unanswerable from free sources**, reason recorded |
| **S018** (label coverage) | partly answered free; **the ITF half is not** |
| **B023** (features add nothing, on 29 days) | **stays a 29-day null and cannot be improved** |

### RS-07, by how much

`tennis` already found a **free** substitute for the main-tour half: per-season
workbooks carrying games won by each player in every set, reaching back years.
That took the label count from **479 to 1,062** and the smallest visible effect
from about **9.9 to about 6.6**.

**Against a cost bar of 3.61 it still does not clear.** So RS-07 can still be
re-run and will still produce a floor, and **the honest expectation is that it
sharpens a number without answering the question.** That is worth doing once and
not worth doing twice.

### What a free substitute would have to look like

**Stated as a specification rather than "none exists", so the question is
answerable if one ever appears.** The gap is narrower than it sounds — most of
it is already solved free.

| requirement | why | current best free source |
|---|---|---|
| **Challenger and ITF matches** | the Kalshi pool is **73–87% ITF**; a main-tour-only source measures the wrong 15% | ⚠ **THE ONLY REAL GAP.** `tennis-data.co.uk` is main tour only |
| **games won per set** (W1/L1 style) | this is the set-1 margin S006 buckets on | ✅ solved — `tennis-data.co.uk` per-season workbooks |
| **history from 2023 or earlier** | so form and head-to-head are not noise; on 29 days the median player appears **~3 times** and head-to-head reached **1.2%** | ✅ solved for main tour, back years |
| **updated within days, not frozen** | a frozen archive recreates T002 exactly. The one free ATP database that appeared (**M016b**) stops at **2026-01-17** | ⚠ partly — must be checked on arrival, not trusted from a description |
| **serve stats on ITF rows** | only needed for a serve-based model, not for set margins | ❌ Sackmann carries futures rows but serve stats on **4.6%** of them (T018) |

**So the precise ask, if a source is ever found:** *Challenger and ITF match
results with per-set games won, from 2023 to within a week of today, updated
weekly.* **Not "tennis data" — that specific thing.** Everything else on the list
is already covered free.

> **And the check that must be run on any candidate**, because it has now caught
> two: **open the file and read the last date.** M016b described itself as *"a
> complete and live updated Database"* and its most recent match was seven months
> old. GUARDS #25.

---

## 2026-08-08 — the denominator: what counts as "a closure"

**Decision.** Of 313 distinct claims, **231 were classified as not closures at
all** — API facts, cost arithmetic, safety canaries, positive findings,
corrections, and items openly marked unfinished. Only the remaining **82** were
sorted into *closed properly* versus *closed for some other reason*.

**Why.** The tasking asks for the count that closed correctly, prominently. That
number is meaningless without saying what the denominator is, and the
denominator is the single biggest lever in the whole report. Counting "Kalshi's
fee formula is `0.07·C·P·(1−P)`" as a correctly-closed thread would have turned
53-of-82 into 284-of-313 and flattered the audit by three times.

**The risk, stated.** The line between *a fact* and *a closure* is a judgement.
Both framings are printed in `REOPENED.md` so a reader can take the other one.

---

## 2026-08-08 — split the 29 into REOPEN and RELABEL

**Decision.** The claims not closed on evidence were split into **13 REOPEN**
(there is a test to run) and **16 RELABEL** (the measurement is fine or cannot
be improved; the row's wording is what will mislead the next reader).

**Why.** "29 threads should be reopened" is an unusable instruction and would
have been fair to attack as a chat justifying its own existence. Most of these
cost minutes and no compute. Naming which is which is the difference between a
report and a demand.

---

## 2026-08-08 — did not report `crypto/MM_RESULTS.md` as still carrying M001

**Decision.** `LEDGER.md` says, in bold, that `crypto/MM_RESULTS.md` still
states the retracted "depth is not public" claim as a live blocker. **A plain
search reproduces that** — the sentence is there in four places. I opened the
file and it is under a retraction box added 2026-08-06 that corrects it in place
and says explicitly that nothing below is deleted, per the house convention.

**So the finding is stale and I did not report it.** Reporting it would have
been this chat's own recorded failure mode — searching for a string, finding it,
and concluding without opening the file.

**What I did report instead:** the ledger row for that thread (`C022`) says
*settled, no edge* while the project's own later document says the question is
**unresolved**. That is a real live contradiction and it is the top crypto item.

---

## 2026-08-08 — used `coordinator/ledger.py` rather than writing a parser

**Decision.** The dump imports the coordinator's existing ledger parser
read-only instead of parsing the Markdown tables again.

**Why.** `CLAUDE.md` §6 and the fee-formula history: a rule that is only a
convention drifts, and the fee formula reached 17 copies that way. A second
ledger parser would drift from the first, and the two would then disagree about
how many claims exist — which is precisely the number this report turns on.

**Cost of the decision:** the parser reads three ledger files. It does not read
`kalshi-inplay-bot/audit/LEDGER.md`, and it finds zero rows in
`crypto/HYPOTHESIS_LEDGER.md` and `set1_overshoot/HYPOTHESIS_LEDGER.md` (their
tables are not in the shared schema). **That hole is stated in `REOPENED.md`
rather than quietly patched**, because patching it here would create exactly the
second parser this decision avoids. The right fix is in `coordinator/ledger.py`
and belongs to the coordinator chat.

---

## 2026-08-08 — made the coverage check a hard failure

**Decision.** `classify_closures.py` exits non-zero if any claim has no
classification, if any classification points at a claim that does not exist, or
if anything not closed on evidence has no stated action.

**Why.** This chat's whole subject is people concluding without covering
everything. A silent omission in the audit of silent omissions would be the
obvious way to fail, and a warning printed at the bottom of a long run is a
silent omission.
