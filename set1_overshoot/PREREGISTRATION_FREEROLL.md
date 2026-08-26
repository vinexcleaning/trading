# PREREGISTRATION — the Principal Recovery / Free-Roll Exit overlay

**Written 2026-08-26, before any result exists.** Origin: `tennis` mailbox 020,
his own idea. Prior work assessed in §2. What had already been looked at is
declared in §9.

---

## 1. The idea, and the honest form of the question

**His words:** *buy 10 YES at 10¢ for $1; if the price reaches 20¢, sell 5 for
$1 — the original stake is back — and let the other 5 ride.*

**The general rule:** `contracts to sell = principal to recover ÷ executable
exit price`, subject to whole contracts, real fills, fees and spread.

**A free-roll exit cannot raise expected value, and he already knows it** — his
brief asks whether taking principal off the table *"improves risk-adjusted
returns even if it reduces raw expected value."* Selling half at a fair price is
break-even before costs and **loses money after fees and spread**.

> **So the question is not "does this make more money". It is: does it change
> the SHAPE of the outcome enough to be worth what it costs — and is there a
> setting in which it genuinely wins?**

**Scoring, fixed now:**

| outcome | verdict |
|---|---|
| lower total return, much smaller worst run of losses | **success** under his framing |
| lower total return, worst run of losses unchanged | **failure** |
| higher total return once cash is limited | **success, and the interesting one** |

## 2. Prior work — and I agree with 020 that none of it settles this

| what was tested | why it does not answer this |
|---|---|
| `mlb-paper` exit grid, 81 cells, 84 games, 2026-08-08→08-19: **every one of the 72 cells containing a stop-loss lost money** | those are **full** exits at a threshold. This is a **partial** exit sized to a dollar target with a runner left on. Nothing there tested a scale-out |
| `tennis` 017 maker test: **UNDECIDABLE**, lever removes ~3.2¢ of a 3.61¢ bar | that is about the cost of **entering**. This is about managing an exit on a position already held |
| `set1_overshoot` S004: cost bar **3.6104pp** = 1.170 spread + 1.000 slippage + 1.441 fee, 3,436 matches, 2026-05-25→08-01 | **directly relevant and the most likely killer** — a free-roll pays that bar an **extra time**, on the half it sells |
| `rebound2` 2026-08-26: every tradable exit rule between **−5% and −33%** | all-or-nothing exits at price thresholds, not scale-outs |

**Recorded in `DECISIONS.md`: this is a different question from all four.**

## 3. ⚠ JOB 0 — compute what the overlay COSTS before measuring what it saves

**Cheap, decisive, and done first.** The cost is close to deterministic: selling
`m` contracts at the bid and paying the fee is a known amount the moment the
activation price is known.

**If the cost per position exceeds any plausible benefit, that is the answer and
the rest of the study is a formality.** This is written down now so the result
cannot be reframed after the fact.

## 4. ⚠ AND A STRUCTURAL PROBLEM WITH HIS EXAMPLE, STATED BEFORE ANY RESULT

**His example is a 10¢ contract doubling to 20¢. Every tennis strategy in this
repo enters between about 60¢ and 70¢**, where a contract cannot double —
100¢ is the ceiling.

| activation rule | highest entry price where it is possible |
|---|---|
| 3× entry | 33¢ |
| 2× entry | 50¢ |
| 1.5× entry | 66¢ |
| 1.25× entry | 80¢ |

**So a multiple-based free-roll is arithmetically unavailable to most of what we
trade**, and this is a fact about the ceiling, not a finding. It is why §5
includes absolute-profit and absolute-price activations, which have no such
limit, and why **the activation rate is a headline number rather than a
footnote.**

## 5. The grid, fixed now

| dimension | values |
|---|---|
| **baseline arms** | hold to settlement · the strategy's existing exit |
| **recovery target** | 50% · 75% · 100% of principal |
| **activation** | 1.25× · 1.5× · 2× · 3× entry · absolute profit +5¢/+10¢/+20¢ · absolute price 50/60/70/80¢ |
| **sizing** | exactly enough to hit the target · sell ¼ · sell ⅓ · sell ½ |
| **the runner** | hold to settlement · apply the strategy's existing exit |
| **timing** | one-time recovery · staged at successive multiples |

**Nothing is added to this grid later.** Anything that looks interesting and is
not on it goes in the not-tested list for a future registration.

## 6. Execution realism — non-negotiable

1. **Entry at the ask** (or the recorded fill), **exit at the bid, never the
   mid** — `GUARDS.md` #7.
2. **Fees only from `common/kalshi_fees.py`**, which a repo-wide test enforces
   as the single implementation.
3. **Whole contracts.** A position of 3 cannot sell 1.5.
4. **No look-ahead**: the activation decision uses only the tape at or before
   that minute; the runner's outcome uses only minutes strictly after it.
5. **Latency of one whole minute-bar**, matching the existing convention here.
6. **`set1_overshoot/data/maker.db` is the dataset** — 13.2M sixty-second
   candles with real bid *and* ask, 35,990 tennis tickers, settled results.
   **It has no score state**, so no live match-state segmentation is possible
   and none will be approximated.

## 7. The cases that quietly get dropped are part of the RESULT

Three counts are reported as headlines, not as caveats:

1. **positions too small to recover anything** — cannot sell a fraction of a
   contract;
2. **positions that never activate** — the price never rose enough;
3. **positions where the sale would be for less than a whole cent of use.**

> **An overlay that fires on 8 positions in 100 cannot move a portfolio, however
> good it looks on those 8.**

## 8. Two simulations, because the answer may differ in sign

**(a) Unconstrained.** Every signal taken, unlimited cash. Isolates the pure
shape-versus-cost trade.

**(b) Bankroll-constrained**, and **this is the one mechanism by which the
overlay can genuinely win**, which he did not name and 020 did:
recovering principal early frees cash for the next bet, so the same bankroll
gets more shots. **Measured as real on the baseball side — capacity for about
5 concurrent bets against a need for 9, so roughly 4 signals in 9 went untaken
purely for lack of cash.** Under that constraint an overlay that loses money per
trade can still raise total return by raising turnover.

**Reported: fixed bankroll, positions sized as a fixed fraction, signals skipped
when cash is short, and the count of skipped signals with and without the
overlay.**

## 9. What has already been looked at

- The **cost bar** and the fee curve, from prior work in this folder.
- **Entry prices of the existing tennis strategies** (~60–70¢), which is what
  §4 is built on.
- **No free-roll rule has been evaluated against any outcome.** Nothing in §5
  has been run.

## 10. The placebo

**Apply the overlay at a RANDOM minute** rather than at its activation trigger,
same position, same sizing, same costs. **If random-timing scale-out looks as
good as triggered scale-out, the rule is doing nothing and only the costs are
real.**

⚠ **And the trap from `RESULTS_MAKER.md` §6 applies directly here:** a random
minute must be drawn **inside the match**, never after settlement, where the
book is pinned at the known result. That mistake made a placebo beat its own
treatment by +12.40¢ and took three rounds to find.

## 11. WHAT WOULD MAKE ME DROP THIS

**Any one of these ends it.**

1. **Job 0 shows the overlay's cost exceeds the largest drawdown improvement it
   could possibly buy.** Dropped on arithmetic, before the grid runs.
2. **Fewer than 1 position in 10 activates** across every activation rule.
   Immaterial to a portfolio regardless of how it looks on those that do.
3. **Total return falls and the worst run of losses does not improve** —
   failure by his own stated framing.
4. **The bankroll-constrained version does not raise total return either.** Then
   the one mechanism that could genuinely win does not.
5. **The placebo looks as good as the real rule.** Void, not a finding.

**And one thing that is NOT a drop:** a smaller worst-run-of-losses bought at a
small cost in return is a **success**, and reporting it as a failure because
"expected value went down" would be misreading what he asked for.

## 12. Standing prediction, recorded before any number exists

**I expect the overlay to lose money per trade and to genuinely reduce the worst
run of losses, and I expect the activation rate to be the thing that kills it**
— because our entries sit at 60–70¢ where the multiple-based rules cannot fire
at all.

**I also expect the bankroll-constrained version to be the closest call**, and I
would not be surprised to be wrong about its sign.
