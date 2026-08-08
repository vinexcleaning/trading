# RESULTS — M1. A resting order does NOT capture enough spread. It captures negative spread.

**2026-08-08.** Runs [PREREGISTRATION_MAKER_VIABILITY.md](PREREGISTRATION_MAKER_VIABILITY.md)
+ Amendment A1, both committed before any number from this design existed.
Code `src/maker_viability.py`; raw `reports/maker_viability.json`.

**This was the last live money question in this workstream.** De-vig closed,
weather closed. The remaining one was: adverse selection costs ~0.5¢ per
contract — does a resting order earn enough spread to cover it?

**The answer is no, and it fails one step earlier than expected.**

---

## 1. The result

`KXBTCD`, 24 days of replayed L2, **17,325 fills across 1,161 events and 23 days**.

| JOIN — rest at the touch | |
|---|---|
| **capture** (mid at fill − our price) | **−1.226¢** |
| adverse selection @60 s | **−0.460¢** *(negative = the price moved back in our favour)* |
| **NET @60 s** | **−0.766¢** |
| **DAY-clustered** *(primary)* | **−0.853¢**, 95% CI **[−1.632, −0.185]** — **excludes zero** |
| event-clustered | −0.370¢ [−0.660, −0.093] — **width ratio 2.56×** |
| **N1 side placebo** | **−0.004¢** (sd 0.068) → **real − placebo = −0.849¢** |

**The strategy does not fail on adverse selection. It fails on capture.**

The framing everyone starts with — *earn the spread, lose some of it to being
picked off* — is **backwards here**. With an honest fill model:

1. **You pay 1.23¢ to get filled.** A trade-through fill means the book moved
   *away* from your resting price before you traded. You are buying at a price
   the market has already left.
2. **Then it drifts 0.46¢ back in your favour** — genuine mean reversion after
   the sweep.
3. **Net −0.77¢, and the day-clustered interval never touches zero.**

> **So the 0.5¢ pick-off cost measured in `MM_RESULTS_MAKER.md` §6b turns out not
> to be the binding constraint.** Even if adverse selection were zero, capture at
> −1.23¢ would sink it. The question "does the spread cover the pick-off" has a
> harder answer than no: **there is no spread being captured to begin with.**

**N1 lands at −0.004¢**, which is what a correct estimator must return when the
side label is randomised. The real result sits 0.849¢ below it.

## 2. ⚠ The IMPROVE arm is VOID, and it is the reason to distrust anyone's maker backtest

Quoting *inside* the touch reports **+1.606¢ day-clustered, CI [+1.192, +2.090]**,
on 21,244 fills. **It is not a result and it is not reported as one.**

**The archive feed carries exactly two event types — `orderbook_delta` (822,213
rows in a sampled hour) and `orderbook_snapshot` (700). There is no trade event
type.** A negative delta is a price level shrinking, which is **either a trade or
a cancellation**, and nothing separates them.

For JOIN, trade-through is a real filter: the best bid must move below our price.
For IMPROVE no such filter exists — once you improve on the touch, the market's
best bid is *by construction* below you (H10 documented this) — so the fill test
collapses to "did anything at our price disappear", and **every cancellation
counts as a fill.**

A maker who "fills" whenever a neighbour cancels is handed exactly the moments
when the book is thinnest and the mid is furthest from their price. That is where
**+1.28¢ of capture** comes from, against the honest arm's **−1.23¢**. **The two
arms differ by 2.5¢ purely on how a fill is defined.**

> This is the touch-counts-as-fill fake wearing a new costume.
> `kalshi-inplay-bot/backtest`'s own header calls that *"the single easiest way
> to fake a profitable backtest"*, and the two positive rows in its 12-row sweep
> were both that model. **The pre-registration's N3 control exists for exactly
> this and it fired.**

## 3. What this does not settle

1. **JOIN's fill model is imperfect too, in the same direction.** A mass
   cancellation of the whole best-bid level also pushes the best bid below our
   price and can register as a trade-through. So **the JOIN number is itself
   contaminated by cancellations** — but note the contamination flatters (it is
   what makes IMPROVE look good), so the true JOIN result is **no better than
   −0.85¢ and plausibly worse.** The verdict direction is safe.
2. **The capture/adverse split is boundary-dependent.** Marking at the mid *at*
   the fill instant puts the informativeness of the filling trade into
   "capture" rather than "adverse". A different boundary moves cents between the
   two columns. **The total — `mid(fill+Δ) − price − fee` — is the robust
   quantity and it is what §1 concludes on.**
3. **Three hours of each day** (Amendment A1), one series, 24 days.
4. **A real maker chooses when and where to quote.** This is a quoter permanently
   at the touch. It is a lower bound on skill.

## 4. Verdict

**NO.** Against the pre-registration's §6, which required **six** conditions to
revise: a cell clearing BH-FDR, exceeding the 0.5¢ adverse-selection cost, clean
on N1, a plateau, surviving the holdout, and with reportable depth. **Zero are
met** — the primary arm is negative with a day-clustered interval entirely below
zero, so the holdout stays sealed and untouched.

**The pre-registration expected this and said why** (S008/S009: all 15 maker
configurations on tennis net-negative; H10: esports P&L sign-flips; the esports
arb author losing 38% of gross to adverse selection; a 20-year professional
saying *"be a taker"*). **It is the ~50th correction in this repo pointing the
same way.**

**What is genuinely new:** the mechanism. Every previous maker null in this repo
died on adverse selection. **This one dies before adverse selection is reached** —
an honest fill model gives negative capture, because the event that fills you is
the event that tells you the price was wrong.

## 5. What would still be worth doing, and what would not

**Worth doing:** join a **trade tape** to the book. That is the only thing that
separates a fill from a cancellation, and it would (a) make IMPROVE measurable
instead of void and (b) remove the flattering contamination from JOIN. The tape
is re-pullable per ticker and `crypto/src/pull_trade_tape.py` already does it.
**Until that exists, no maker backtest on this data can be trusted in the
positive direction — including this one's IMPROVE arm.**

**Not worth doing:** more days of the same thing. The day-clustered interval
already excludes zero at 23 days, and the failure is structural rather than
statistical.
