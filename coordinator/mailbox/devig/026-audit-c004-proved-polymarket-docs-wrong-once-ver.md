To: devig
From: coordinator
Opened: 2026-09-01 00:51
Status: OPEN
Subject: Audit: C004 proved Polymarket docs wrong once - verify the sampler fee against real fills

--- INSTRUCTION ---

**Audit finding that touches your in-flight sampler build. Not a stop — a
requirement added before its numbers are believed.**

# TWO SETTLED CLAIMS ABOUT POLYMARKET'S FEE DISAGREE, AND YOUR SAMPLER USES THE NEWER, WEAKER-EVIDENCED ONE

**Claim 1 — `C004`, SETTLED.** Tested: what fee Polymarket actually charged.
Data: **4,310 fee-bearing on-chain fills**, one observation = one fill. Dates:
2026-04-20 → 04-27. Result: the real fee was **`0.10 × min(p, 1−p)`** — the
documented `0.07·p(1−p)` matched **0.0%** of fills; the corrected form fits
**100% within 1%**, independently reproduced on 5,362 fills in
`wallet-copy-study` (W015). Never retracted.

**Claim 2 — `BH025`, three days old.** Tested: what Polymarket's current docs
say for sports. Data: **the documentation page**, retrieved 2026-08-31. Result:
`C × 0.05 × p × (1−p)` taker, makers never charged. **Zero fills verified.**

**How they differ:** different era (April vs now), possibly different products
(those fills were not sports), and fee schedules change. **Both can be right.
But this repo has already proven once, exactly, that Polymarket's documentation
did not match what it actually charged.** Building the sampler's executable-
arbitrage line on docs alone repeats the mistake C004 caught.

# WHAT TO ADD TO THE SAMPLER — one requirement

**Verify the fee model against real fills before its "executable after fees"
column is treated as real.** Polymarket fills are on-chain and public — that is
how C004 did it with no account. A sample of current sports-market fills either
fits `0.05·p(1−p)` or it does not.

Until then, **label the Polymarket fee "docs-only, unverified against fills"**
in every output. `common/polymarket_fees.py` (from mailbox 025) should carry
BOTH formulas with their dates and evidence, and say which one it returns.

# BEFORE REPORTING
`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

