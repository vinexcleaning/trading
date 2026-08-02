# EXPANSION_PLAN.md

Ranked by expected information gain per hour. Every proposal carries the
arithmetic that could kill it before it starts.

## The framing, restated

The study measured whether the price is wrong **on average across all dips**. It
never asked whether we can tell **which dips recover**. Those are different
questions and only the second needs match data.

## The arithmetic every proposal must beat

| quantity | value |
|---|---|
| fade edge, pooled | **+2.42 pp** |
| cost bar, fade | **3.61 pp** *(corrected from 3.70 — see AUDIT_FINAL)* |
| per-contract sd | ≈ 45 ¢ |
| n for a 2 ¢ edge at 80% power | **≈ 3,970 matches** |
| events available | **3,436** |

**The whole sample is already below the n needed to demonstrate a 2 ¢ edge.** Any
proposal that improves the effect but shrinks the sample must improve it *a lot*.
Required effect to clear at sample size n: `3.61 + 2.80×45/√n` pp.

| n | MDE (pp) | effect needed to clear |
|---|---|---|
| 3,436 | 2.15 | **5.76** |
| 1,500 | 3.25 | 6.86 |
| 479 | 5.76 | 9.37 |

---

## C1. Fix the detector with real scores — **recommended, but it does not clear on its own**

**Mechanism:** entry-rule precision is 0.793, so ~21% of entries were not set-1
losses. If those carry no effect they dilute the measured one toward zero.

**Measured today**, on the restored 2,887-match truth set (n doubled after the
dedupe fix remapped tickers):

| sample | n | effect pp | bar pp | net ¢ | MDE ¢ |
|---|---|---|---|---|---|
| all events | 3,436 | +2.42 | 3.61 | −1.195 | 2.16 |
| **label-verified** | **479** | **+5.75** | 3.61 | **+2.141** | **5.71** |
| label-verified, train | 287 | +7.21 | 3.84 | +3.365 | 7.42 |
| label-verified, **holdout** | 192 | +3.57 | 3.26 | **+0.311** | 8.93 |
| unlabelled remainder | 2,832 | +1.66 | 3.61 | **−1.948** | 2.38 |

**The dilution arithmetic, which is the decisive part.** If non-set-1-loss
entries carry zero effect, then `pooled = precision × true`, so
`true = 2.42 / 0.793 = **3.05 pp**`. Against a 3.61 pp bar that **still loses**,
even at perfect labelling and full sample. The observed +5.75 pp is **1.9× what
dilution can explain**, and the excess is unaccounted for.

**Warning signs on that excess:** the holdout falls from +7.21 to +3.57 pp
(net +3.365 → +0.311), which is the shape that killed the 90 ¢ cell. And the
labelled subsample is not random — it is 35.6% main tour vs 6.5% in the
unlabelled remainder. Reweighting to the unlabelled tier mix gives **+6.40 pp**,
so tier mix does *not* explain it — but within-tier the direction is
inconsistent (ATP labelled +3.52 vs unlabelled +10.40; ITF-M labelled +10.52 vs
unlabelled +0.74) at n ≈ 70–125 per cell. That is noise-shaped.

**Verdict: run it, because it is cheap and it is the only proposal that can
raise the effect without shrinking the sample** — Flashscore covers ITF and
Challenger, so labelling can go to ~100% of 3,436 rather than 14%. But
pre-register that dilution predicts **3.05 pp**, which loses, and that anything
above ~5.76 pp should be treated as presumptively noise until it survives a
holdout.

**Cost:** ≈ $3.44 (3,436 events at $0.001) or ≈ $20 for the full universe.
**Time:** ~2 h including the join, the selection canary on the join, and re-run.

---

## C2. Conditional recovery — the main event, and the only one that could change the answer

**Mechanism:** the market prices the average comeback. If set-1 detail (margin,
tiebreak, break points saved, serve %) predicts recovery *beyond* what the price
already reflects, the residual is tradeable. The error persists because
retail-facing in-play pricing is largely a function of score state, and the
counterparty may not condition on the finer detail.

**Benchmark is the market, not accuracy.** Report Brier for the model and for the
entry price on the same matches, exactly as the crypto B1 comparison did. A model
predicting recovery at 60% is worthless if the price already says 60%.

**Sample:** whatever C1 labels — up to 3,436 with Flashscore, of which ~2,700
would be genuine set-1 losses. MDE at n = 2,700 is 2.42 pp, so the model must add
**> 3.61 − 2.42 + 2.42 ≈ 3.6 pp** of *incremental* edge over the price. That is a
large ask for a feature set the market can also see.

**Doomed-by-arithmetic check:** not doomed, but tight. This is the only proposal
where the upside is not bounded by the pooled 2.42 pp, because selection can in
principle isolate a subset with a much larger error.
**Cost:** ≈ $258 for point-by-point on 3,436 matches, or free-ish if set-1 margin
and tiebreak flags from Flashscore suffice. **Time:** ~4 h.

---

## C3. Selection rather than prediction — **cheapest real test**

**Mechanism:** without any better probability, does match information mark a
subset where the existing 2.42 pp error is larger? Requires only set-1 margin and
tiebreak status, both in the Flashscore feed.

**Critical requirement, learned from the time-of-day segmentation:** compute the
cost bar **within** the selected subset. Selecting on anything liquidity-adjacent
moves the bar as well as the effect, and the pooled bar hides that.

**Doomed check:** partially. 0 of 25 pre-registered buckets cleared on the data we
already have, and the effect variation there was 0.73–4.63 pp — none of it enough.
For a subset to clear at n = 1,000 it needs **6.1 pp**. Possible only if set-1
margin is a far stronger conditioner than hour or tier were.
**Time:** ~1.5 h once C1 lands. **Run this before C2** — same data, tenth the cost.

---

## C4. Entry timing with real scores — **narrow, do it inside C1**

**Mechanism:** serve order in set 2 was pre-registered and abandoned as
unrecoverable from price. Point-by-point supplies it. Whether the favourite serves
first after losing set 1 is a genuine structural asymmetry.

**Doomed check:** it modifies *entry timing*, not the effect size, and the maker
work already showed timing is not the constraint — adverse selection is, and it is
stable at −4.58/−4.66 pp across halves. Expect it to move net by tenths of a cent.
**Cost:** requires the $0.075/match point-by-point tier. **Time:** ~1 h.

---

## C5. Pre-match strength conditional on the set-1 loss — **lowest priority**

**Mechanism:** a pre-match model already lost to the bookmaker benchmark
(Brier 0.2249 vs 0.2057, n = 2,645) and is not to be rebuilt. The narrower
question is whether pre-match features add anything *given* a set-1 loss.

**Doomed check:** largely, yes. The favourite-strength segmentation on clean data
found no monotone pattern, and the pre-match price is well calibrated
(unconditional residual **+0.24 pp**, n = 16,203). If the pre-match price is right
and the model already lost to it, conditioning is unlikely to rescue it.
**Time:** ~2 h. **Recommend skipping unless C2 finds structure.**

---

## Recommended order

1. **C1** — cheap, doubles-to-septuples the label coverage, and is a prerequisite
   for everything else. Pre-register the 3.05 pp dilution prediction first.
2. **C3** — reuses C1's data, tenth the cost of C2, and directly tests
   concentration with per-subset cost bars.
3. **C2** — only if C3 shows any concentration at all.
4. C4 inside C2. **C5 skip.**

## Guards that apply to all of them

Every external join is a new selection point: run `assert_selection_neutral` on
the joined-vs-unjoined split before reading any effect. The labelled subsample is
**already known to be non-random** (35.6% vs 6.5% main tour), so joins must be
reweighted or reported within tier. Everything into the ledger; BH-FDR across the
cumulative total; holdout gate on every candidate.
