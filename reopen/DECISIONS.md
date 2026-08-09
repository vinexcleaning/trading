# DECISIONS.md — reopen

Judgement calls taken without asking, per `CLAUDE.md` §2. Newest first.

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
