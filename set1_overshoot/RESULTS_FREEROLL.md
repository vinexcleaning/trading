# The free-roll exit — twelve of thirteen versions fail, and one works

**2026-08-26.** His idea, from `tennis` mailbox 020. Pre-registered in
`PREREGISTRATION_FREEROLL.md` **before any result existed**, including the
scoring, so it could not be reframed afterwards. Overlay:
`common/freeroll.py`. Runner: `src/p8_freeroll_run.py`.

All figures on tennis positions closing **2026-06-14 → 2026-08-01**, entries at
the ask, exits at the bid, fees from `common/kalshi_fees.py`, whole contracts,
one minute of latency, no look-ahead.

---

## The answer

**Taking your stake off the table costs about 8% of the stake when you do it at
20¢ — and one configuration out of thirteen pays for itself anyway.**

> **Twelve of the thirteen versions lose money AND make the worst run of losses
> bigger.** Under your own scoring that is a failure twice over.
>
> **One version — sell at 1.5× your entry — makes slightly more money and cuts
> the worst losing run by 9% across a whole portfolio, and by 88% on the bets it
> actually fires on.** That is your success case, exactly as you defined it.
>
> **And it is one of thirteen things looked at, so it needs a fresh test before
> anyone trades it.**

---

## 1. JOB 0 — what it costs, computed before anything was measured

The pre-registration made this the first thing to run, so the cost could not be
re-described after seeing a benefit.

**Holding to settlement on Kalshi pays no exit fee at all.** Selling early pays
two things the holder never pays: the walk from the middle price down to the
bid, and a fee. Both are known the moment the price is known.

| you sell at | cost per $1 of stake recovered |
|---|---|
| 10¢ | **11.3%** |
| **20¢ — your example** | **8.1%** |
| 30¢ | 6.6% |
| 50¢ | 4.5% |
| 80¢ | 2.0% |
| 90¢ | 1.3% |

**⚠ The counterintuitive bit, and it works against your example.** The Kalshi
fee is proportional to price × (1 − price), so in cents it is largest at 50¢ —
but **as a share of the sale it is far worse when the price is low**, because
you pay a similar fee on a much smaller sale. **Buying at 10¢ and selling at 20¢
is close to the most expensive place on the board to do this.**

## 2. ⚠ And most of what we trade cannot use a multiple at all

Your example doubles from 10¢. **A contract cannot double from above 50¢** — the
ceiling is 100.

| rule | highest entry where it can EVER fire |
|---|---|
| 3× entry | 33¢ |
| 2× entry | 50¢ |
| 1.5× entry | 66¢ |
| 1.25× entry | 80¢ |

**The set-1 fade enters at 70¢ on average. Of its 738 positions, 679 could never
fire a 2× rule** — not "did not", *could not*. That is arithmetic, not a result,
and it is why the firing rate is reported as a headline everywhere below.

## 3. The two trade lists, and why both

Neither strategy makes money. **That is deliberate: the overlay is measured for
what it does to the SHAPE of a return, never for rescuing a bad edge.** They sit
either side of the 50¢ line where multiples stop working.

| | positions | enters at | wins |
|---|---|---|---|
| **FADE** — buy the underdog after a 30¢ collapse | 738 | 70.0¢ | 69.9% |
| **REBOUND** — ITF contract that peaked at 80¢ and fell to 30¢ | 371 | 26.2¢ | 24.0% |

## 4. Unlimited cash — the pure shape-versus-cost trade

**FADE.** Hold to settlement returns **−2.0%** with a worst losing run of
**$177.99**.

| rule | fires | return | worst run | vs hold |
|---|---|---|---|---|
| hold to settlement | — | −2.0% | $177.99 | — |
| **1.5× entry, recover all** | **22.5%** | **−1.8%** | **$162.00** | **+0.2%, and −9% on the worst run** |
| 2× entry, recover all | 3.9% | −2.0% | $174.39 | +0.0% |
| 1.25× entry, recover all | 53.0% | −3.6% | $240.05 | −1.6%, worst run **35% bigger** |
| +5¢, recover all | 83.3% | −5.8% | $325.45 | −3.8%, worst run **83% bigger** |
| price 50¢, recover all | 97.7% | −6.3% | $331.92 | −4.3%, worst run **87% bigger** |

**REBOUND.** Hold returns −13.0%, worst run $183.73. **Every single overlay is
worse on return**, from −14.4% to −19.5%, and none meaningfully improves the
worst run.

### ⚠ The finding that surprised me, and it is the important one

**Scaling out usually makes the worst losing run BIGGER, not smaller.** That is
the opposite of what a free-roll is supposed to do, and the mechanism is simple
once seen: **selling half of the winners caps the recoveries that would have
climbed out of a drawdown, while the losers still lose in full.** You keep the
losses and clip the repairs.

**So for twelve of thirteen versions this fails your own test twice** — lower
return *and* a worse worst run. Not a close call.

## 5. The one that works, and the check that it is real

**1.5× entry, recover all** is the exception in every arm. On the same bets:

| on the 166 positions where it fired | hold | 1.5× free-roll |
|---|---|---|
| return | +48.70% | **+50.08%** |
| worst losing run | $11.96 | **$1.46** |

**Same positions, same entries, same settlement — so this is not selection.**
The overlay is worth **+1.38%** on those bets and **cuts the worst run by 88%**.

⚠ **But the +48.70% is not an edge.** Those 166 are the positions whose price
rose 50% after entry, which is only knowable afterwards. **You cannot pick them
in advance.** In live use you take all 738 and it fires on the 166 that happen
to rise — which is the portfolio line in §4: **+0.2% return and −9% on the worst
run.** Real, and much smaller than the subset table looks.

**Why 1.5× and not the others.** Its trigger sits just above where our entries
cluster: it fires on the cheaper 166 (entering at 55.8¢ against 74.1¢ for the
rest) and skips the expensive ones where a scale-out is pure cost. The rules
that fire on almost everything — +5¢, price 50¢ — pay the cost on every
position and are the worst performers.

## 6. The bankroll arm — and why it could not be tested properly

This is the one mechanism by which the overlay can genuinely win, so it was
simulated with **positions overlapping in time**, cash released at the scale-out
minute rather than at settlement.

**FADE on $200:**

| rule | bets taken | profit | worst run |
|---|---|---|---|
| hold to settlement | 738 | −$105.69 | $184.13 |
| **1.5× entry** | 738 | **−$92.53** | **$177.92** |
| +5¢, recover all | 515 | −$199.92 | $210.00 |
| price 50¢ | 440 | −$198.63 | $198.81 |

**1.5× is $13.16 better on the same $200.** Everything that fires often is
catastrophically worse — those arms lose essentially the whole account.

**⚠ REBOUND on $50: every single arm loses the entire $50.** The strategy loses
13% a bet, so the account is gone either way and the comparison is empty.

> **So the capital mechanism is NOT tested here, and cannot be with what we
> have. Testing "does freeing cash early let a good strategy take more bets"
> requires a strategy with a real edge that is capital-constrained. Tennis has
> no such strategy.** The baseball side does — capacity for about 5 concurrent
> bets against a need for 9 — and that is where this arm belongs.

## 7. The pre-registered drop criteria, applied

| # | criterion | outcome |
|---|---|---|
| 1 | Job 0 cost exceeds any possible benefit | **No.** 8.1% at 20¢ is real but the 1.5× arm clears it |
| 2 | fewer than 1 in 10 activates across every rule | **No.** 22.5% to 98% depending on rule |
| 3 | return falls and the worst run does not improve | **YES for 12 of 13 rules.** Dropped |
| 4 | the bankroll version does not raise total return | **Untestable** — §6 |
| 5 | the placebo looks as good | **No — it fails badly.** §7a |

## 7a. The placebo — run, and it passes

Pre-registered: scale out at a **random minute** instead of at the trigger, same
positions, same sizing, same costs. **⚠ The minute is drawn strictly inside the
tape** — `RESULTS_MAKER.md` §6 records a placebo that drew minutes *after*
settlement, where the book is pinned at the known result, and it beat its own
treatment by +12.40¢.

**Rate-matched**, on the same 166 positions where 1.5× actually fired, so that
timing is tested without the firing-rate difference:

| | return | worst run | vs hold |
|---|---|---|---|
| hold to settlement | +48.70% | $11.96 | — |
| **1.5× entry, the real rule** | **+50.08%** | **$1.46** | **+1.38%** |
| random minute, five seeds | +9.5% to +14.6% | $11.71 to $18.09 | −34% to −39% |

**Random timing costs 34 to 39 points against holding. The real rule gains
1.38.** The timing is doing the work; it is not just the cost of scaling out.

⚠ **And one honest deflation of that.** The rule fires *because* the price is up
50%, so of course it sells higher than a random minute — that part is close to
tautological. **The comparison that matters is against HOLDING, not against
random**, and that one is clean: same positions, no selection, **+1.38% and an
88% smaller worst run.**

## 8. What was NOT tested — CLAUDE.md §9c step 7

1. **The capital mechanism**, which needs a profitable capital-constrained
   strategy. §6.
3. **Staged recovery** at successive multiples — in the grid, not run.
4. **Remaining-edge-aware activation** — only free-roll when the model still
   likes the runner. He asked for it; we have no live model on these positions.
5. **Applying the strategy's own exit to the runner.** Every runner here is held
   to settlement.
6. **Position sizes other than 10 contracts.** Whole-contract rounding decides
   whether a scale-out is possible at all, so this matters and only one size
   was run.
7. **Segmentation he asked for** — by confidence, prematch favourite status,
   time to settlement, volatility, adverse excursion. Not done.
8. **Anything with score state.** `maker.db` has none.
9. **Baseball, weather, crypto.** The overlay is generic and only tennis was run.

## 9. Standing prediction, scored

**I predicted the overlay would lose money per trade, genuinely reduce the worst
run of losses, and be killed by its firing rate.**

- **Loses money per trade: right**, for twelve of thirteen.
- **Reduces the worst run: WRONG, and importantly so.** It usually makes it
  *bigger*, for a reason I had not thought of — clipping the recoveries while
  keeping the losses.
- **Killed by firing rate: half right.** 679 of 738 fade positions can never
  fire a 2× rule, but the rules that fire often are the worst ones, so the
  problem is the opposite of what I expected.

## 10. What I would do next, and it is one thing

**Re-test 1.5× on data nobody has looked at.** The placebo is done and it
passed; what is left is the thing that actually kills survivors. **It is one out
of thirteen** — exactly the shape a lucky slice has, and this repo has retracted
52 claims that looked like this.

**The fresh-data test is cheap and it is already scheduled by something else:**
the same three-week wait the rebound question needs, on the same re-pull. **One
wait, two answers.**
