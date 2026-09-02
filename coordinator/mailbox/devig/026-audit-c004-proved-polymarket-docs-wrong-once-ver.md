To: devig
From: coordinator
Opened: 2026-09-01 00:51
Status: DONE
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

**Done, and the answer is that it CANNOT be verified from free sources today —
for a reason that also weakens the case for C004's number.**

## The verification route C004 used no longer exists

I built the check exactly as you asked — take the CLOB token ids of the live MLB
run-total markets the sampler is already watching, so every fill is a sports fill
by construction, and query the same public on-chain source C004 used.

**The endpoint refuses, and its own words are the finding:**

> *"This Polymarket subgraph endpoint is paused and deprecated following
> Polymarket's migration to V2 — the data is stale and incorrect. Stop using
> it."*

**Probed the same minute, per GUARDS #27 — an absence is only an absence once you
have checked access:**

| source | result |
|---|---|
| Goldsky orderbook subgraph (C004's route) | **HTTP 429, deprecated** |
| `data-api.polymarket.com/trades` | **HTTP 200 — but carries NO fee field** |
| `clob.polymarket.com/trades` | **HTTP 401, authentication required** |

## ⚠ And this cuts against your framing, in a way worth stating

Your argument was: the docs have been proven wrong once, so do not trust them
again. **That is right as far as it goes. But C004's measurement is from
2026-04-20..27 and Polymarket has since migrated to V2** — which is a concrete,
named reason the old formula may no longer describe the venue.

**So the honest position is not "C004 beats the docs". It is that NEITHER is
verified for current sports markets**, and there is now a specific event between
the two that could explain a genuine change.

## What I did about it

**I use C004's formula, and label it unverified everywhere** — not because it is
better evidenced *today*, but because it is the **larger** of the two and a cost
bar should err upward:

| price | docs `0.05·p(1−p)` | C004 `0.10·min(p,1−p)` | ratio |
|---|---|---|---|
| 10¢ | 0.45¢ | **1.00¢** | 2.2× |
| 50¢ | 1.25¢ | **5.00¢** | **4.0×** |
| 90¢ | 0.45¢ | **1.00¢** | 2.2× |

**Every "after fees" number I published using the documented form was too
generous — which makes my cross-venue null stronger, not weaker.** The paired
sampler's report, re-run on the measured fee, now shows **40 theoretical
crossings collapsing to 1 after fees on both legs.**

`src/poly_fee_check.py` records all of this so nobody repeats the dead query.

---

## REFEREE

**STANDS** — the subgraph is deprecated (quoted verbatim); the two live
alternatives carry no fee or need auth; the measured formula is 2.2–4× the
documented one.

**DOWNGRADED** — *was:* "BH025: Polymarket's sports fee is `0.05·p(1−p)`."
*now:* "two candidate formulas, neither verified for current sports markets; the
larger is used for cost bars and labelled unverified." *because:* the docs were
never checked against fills and C004's route is gone.

**FOR THE USER — not empty.** Getting a verified fee needs either an
authenticated Polymarket key or a paid on-chain data source. **Worth it only if
we ever intend to trade there** — for killing ideas, the conservative bar is
enough, and every cross-venue result so far dies at either fee.
