To: tennis
From: coordinator
Opened: 2026-08-26 17:39
Status: OPEN
Subject: Principal Recovery / Free-Roll Exit - build it as a reusable overlay, not a strategy variant

--- INSTRUCTION ---

**His idea. He asked for it to be run here rather than in the dictator window,
because you own the tennis strategy work. Nothing about live trading changes and
nothing deploys without him approving it separately.**

# THE IDEA, IN HIS WORDS

> **Principal Recovery / Free-Roll Exit.** Buy 10 YES at 10c for $1. If price
> reaches 20c, sell 5 for $1 — the original stake is back. Let the other 5 ride.
> If it then loses, the principal was already recovered; if it wins, the
> remaining 5 settle for $5.

**The general rule:**

```
contracts to sell = target principal recovery / executable exit price
```

subject to whole-contract rounding, real fills, fees, and spread.

# ⚠ THE THING TO BE HONEST ABOUT BEFORE YOU START

**A free-roll exit cannot raise expected value, and he already knows this** —
his own brief says *"determine when taking principal off the table improves
risk-adjusted returns even if it reduces raw expected value."* Selling half at a
fair price is EV-neutral before costs and **EV-negative after fees and spread**.

**So the honest hypothesis is not "does this make more money". It is "does this
change the SHAPE of the returns enough to be worth the cost".** Report it that
way. A result showing lower EV and much lower drawdown is a *success* under his
framing, and a result showing lower EV and unchanged drawdown is a failure.

**AND THERE IS ONE MECHANISM BY WHICH IT CAN GENUINELY WIN, WHICH HE DID NOT
NAME — test it explicitly.** If capital is the binding constraint, recovering
principal early frees it for the next bet, and the strategy gets more shots per
unit of bankroll. **This was measured as real on the baseball side: capacity for
about 5 concurrent bets against a need for 9, so roughly 4 in 9 signals went
untaken purely for lack of cash.** Under that constraint an EV-negative overlay
can still raise total return by raising turnover. **Simulate with a bankroll
constraint as well as without it — the answer may differ in sign.**

# PRIOR WORK — five fields each, and none of it settles this

**1. `mlb-paper` exit grid, 2026-08-23.** Tested: take-profit × stop-loss over 81
cells. Data: 84 settled `starter__hold` games, minute tape on 72, one
observation per game. Dates: 2026-08-08 → 08-19. Result: **every one of the 72
cells containing a stop-loss lost money; holding beat all but one cell, and the
best cell failed all three pre-registered kill conditions.** Not retracted.
**How his differs: those are FULL exits at a threshold. His is a PARTIAL exit
sized to a dollar target, with a runner left on. Nothing there tested a
scale-out.**

**2. `tennis` mailbox 017, the maker test.** Tested: resting an order instead of
crossing. Result: **UNDECIDABLE** — the lever removes ~3.2c of a 3.61c cost bar
and there is no edge underneath. **How his differs: that is about entry cost.
This is about exit management on a position already held.**

**3. `set1_overshoot` cost bar, S004.** 3.6104pp = 1.170 spread + 1.000 slip +
1.441 fee, on 3,436 matches, 2026-05-25 → 08-01. **Directly relevant and it is
the thing that will most likely kill this:** a free-roll exit pays that bar an
EXTRA time, on the sold half. **Compute what the overlay costs before measuring
what it saves.**

**4. `coordinator/studies/rebound2.py`, tonight.** 28,000 tennis tickers, 1,215
cells. Every tradable exit rule tested came out between −5% and −33%. **How his
differs: those were all-or-nothing exits at price thresholds.**

# THE COMPARISON MATRIX HE ASKED FOR

**Baseline arms:** existing exit logic · full hold to settlement.

**Recovery targets:** 50% · 75% · 100% of original principal.

**Activation rules:** price multiples 1.25× · 1.5× · 2× · 3× entry · absolute
profit thresholds · absolute price thresholds · **remaining-edge-aware
activation** (only free-roll when the model still likes the runner).

**Sizing:** exactly enough contracts to hit the target · fixed-fraction
scale-outs (sell a quarter, a third, a half).

**The remainder:** hold to settlement · apply the existing exit logic to it.

**Timing:** one-time recovery · staged recovery at successive multiples.

**⚠ And the cases he specifically listed, which are the ones that quietly get
dropped:** positions with too few contracts to recover anything (a 3-contract
position cannot sell 1.5), and positions where the price never rises enough to
activate. **Those are not "excluded" — they are part of the result, and their
count is a headline number.** An overlay that only fires on 8% of positions
cannot move a portfolio however good it looks on those 8%.

# EXECUTION REALISM — non-negotiable

Entries at the **original ask or recorded fill**. Exits at the **executable
bid**, never the mid (`GUARDS.md` #7). Fees from `common/kalshi_fees.py` and
nothing else — a repo-wide test enforces that it is the only implementation.
Whole-contract rounding. Partial fills and available size from the book where
depth exists. **No look-ahead: the activation decision uses only the tape at or
before that minute.**

**`set1_overshoot/data/maker.db` has 13.2M 60-second candles with real bid AND
ask across 35,990 tennis tickers, 2026-06-12 → 08-20, with settled results.**
That is the dataset. It has **no score state**, so live match-state segmentation
is not available — say so rather than approximating it.

# WHAT TO REPORT

Net P&L · ROI · EV per trade · hit rate · profit factor · max drawdown ·
volatility of returns · **capital turnover** · **recovery-trigger rate** ·
**remaining-runner win rate** · opportunity cost versus holding.

**Segment by:** entry price · market type · confidence or estimated edge ·
prematch favourite status · time to settlement · volatility · spread and
liquidity · adverse and favourable excursion before activation.

# ⚠ THE MOST IMPORTANT INSTRUCTION, AND IT IS NOT THE TEST

> **He wants this as a REUSABLE EXIT OVERLAY, kept in mind for every current and
> future tennis strategy, with a standard with-and-without comparison added as a
> permanent column.**

**So build it as an overlay applied to a strategy's trade list, not as a variant
of one strategy.** Any strategy that produces (entry price, size, exit tape,
settlement) should be able to be run through it unchanged. **That is the
deliverable that outlives tonight's answer**, and if the answer is no it is
still worth having, because the next strategy gets tested with and without for
free.

**And keep the two effects apart in every table: predictive edge is what the
strategy picks; exit management is what the overlay does to the same picks.**
Mixing them is how an exit rule takes credit for a signal.

# HOUSEKEEPING

Pre-register before you look — `PREREGISTRATION_FREEROLL.md`, stating what
result makes us drop it. Preserve existing work; change no live behaviour.
Reproducible artifacts in your own folder. **`coordinator/studies/rebound2.py`
is tonight's tennis study and is yours to adopt** — its conditional-baseline and
no-look-ahead structure is directly reusable here.

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

