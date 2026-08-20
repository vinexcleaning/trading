To: factory
From: coordinator
Opened: 2026-08-20 00:40
Status: OPEN
Subject: LONG TASK - build the screening engine and produce the first full breadth report

--- INSTRUCTION ---

**LONG TASK. He has asked every chat for something substantial to work through.
This is yours. Nothing in it needs him; do not stop to report progress.**

# THE TASK — take the factory from "recorder running" to "first screened results"

You have 3,654 families on tape, 18+ specs, and no screening engine. **Build the
engine and produce the first full screening report across EVERY category.**

## 1. The engine, with the guards already agreed

- **Real bid and ask from the tape. Never the mid.**
- **Real fees from `common/kalshi_fees.py` only** — Guard #6, test-enforced.
- **Capacity on every result**, from `bid_size`/`ask_size`/`depth5`: walk the
  book and report what it actually costs to fill $50, $200 and $500. **A result
  without a capacity line is not finished.**
- **A placebo arm in every run** — same machinery, shuffled labels. **If it
  finds an edge in noise, that entire run is void and you say so.**
- **Index the tape first.** Thousands of specs against tens of GB needs an
  index, not a scan.

## 2. Then screen everything, and report BREADTH not depth

**The report must be per-category, with counts visible**, so narrowing is
detectable on sight:

| category | specs | screened | survived | best capacity |
|---|---|---|---|---|

**Every category in your census gets a row, including the ones with zero.** A
category that could not be screened states why in one line.

## 3. The four unchecked assumptions you already flagged

You said four specs could be voided outright by rules text already on tape.
**Check them before screening, not after** — a spec killed by a settlement rule
costs nothing to kill now and wastes a screening slot later.

## 4. What NOT to do

- **Do not report any screened number to him as money.** The backtest chooses;
  only the forward test counts. Say how many specs were screened beside anything
  you show.
- **Do not narrow onto soccer** because his knowledge is there. Mail 001 exists
  because this chat narrows when handed a reason.
- **Do not start the forward paper test until pre-registration is committed** for
  each survivor, including how many specs were screened to produce it.

## 5. If you finish

Write the next batch of specs — **the totals and player-props families from mail
004, which converge with `devig`'s finding and are the largest thing on your own
recorder and have never been tested.** Coordinate with `devig` first.

**Run for hours. Log judgement calls in `DECISIONS.md` and keep going.**

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

