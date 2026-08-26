# The tour-versus-ITF contradiction is not demonstrated, so there is nothing to explain

**2026-08-26. All figures below are out-of-sample, on matches closing 2026-08-01 to 08-20, from a study window of 2026-06-14 to 08-20.** Answers the recommended next experiment in `tennis` mailbox 019.
Script: `src/p7_rebound.py`, adopted from `coordinator/studies/rebound2.py` with
a spread gate added.

---

## The answer

019 found that the deep-dip version of the rebound hypothesis is **flat on the
main tour** and **clears Benjamini–Hochberg on ITF**, could not explain it, and
proposed a tight-spread re-run with two possible outcomes: the lift survives and
ITF is genuinely slower, or it vanishes and it was the mid all along.

> **Neither. The main tour's deep-dip cells are measured on 56 to 136 events and
> their confidence ranges are ±7 to ±11 points wide — they overlap ITF's almost
> entirely. "Flat on the main tour" was a wide interval being read as a zero.
> There was never a demonstrated disagreement.**

| peak, fell to 30¢ | main tour | ITF |
|---|---|---|
| 80 | +1.1pp **[−6.2, +8.4]** on 136 events | +5.4pp [+2.1, +8.8] on 667 |
| 85 | +1.4pp **[−7.5, +10.4]** on 91 events | +5.6pp [+1.6, +9.5] on 470 |
| 90 | +0.1pp **[−11.0, +11.2]** on 56 events | +6.3pp [+1.0, +11.6] on 268 |

**A test that cannot tell +1 from +6 has not found a flat result. It has found
nothing.**

### And this is tested directly, not argued from overlapping ranges

Overlapping intervals are a weak way to claim two things agree, so the
difference itself was tested — each population's lift against its own control,
then one minus the other:

| peak, fell to 30¢ | ITF | main tour | difference | |
|---|---|---|---|---|
| 80 | +5.4pp | +1.1pp | **+4.3pp [−3.7, +12.3]** | p=0.29 |
| 85 | +5.6pp | +1.4pp | **+4.1pp [−5.6, +13.9]** | p=0.41 |
| 90 | +6.3pp | +0.1pp | **+6.2pp [−6.0, +18.5]** | p=0.32 |

**Not distinguishable at any peak.** The gap between the two populations might
be six points and might be zero, and 019's own data cannot say which.

Both populations reproduce 019 exactly first — main tour 75/draw10 **+7.6pp,
p=0.0006**; ITF 70/draw10 **+9.6pp**, 90/dest30 **+6.3pp, p=0.010** — so this is
a reading of the same numbers, not a different run.

---

## 1. What the spread gate did, and what it did not

019's proposal was to restrict the ITF cells to spreads of 3¢ or less. Two
things had to be got right before that means anything.

**It must gate WHERE A MEASUREMENT IS TAKEN, not which candles exist.** Deleting
wide candles would change the running peak and the future maximum — that changes
what the price *did*, not where we looked at it. And it is applied identically
to treated events and control minutes; gating only the treatment swaps one
confound for a worse one.

**⚠ And the obvious version of the gate is far weaker than it looks.** Skipping a
wide minute does not drop the event — it relocates it to the next tight minute.
The event count fell only **268 → 259 (3%)**, even though **half of ITF minutes
near 30¢ are wider than 3¢**. Same events, later timestamps.

So `--strict` was added: if a dip first qualifies while the book is wide, the
cell is burned for that ticker and can never fire later. That is the question
019 was actually asking.

## 2. What happened as the gate tightened

**Deep dips (peak 90, fell to 30¢), ultimate win, out of sample:**

| gate | events | lift | 95% range | clears BH |
|---|---|---|---|---|
| none | 268 | +6.3pp | [+1.0, +11.6] | **yes** |
| ≤3¢ | 259 | +5.9pp | [+0.6, +11.2] | **yes** |
| ≤3¢ strict | 224 | +5.9pp | [+0.2, +11.7] | **yes** |
| **≤1¢ strict** | **162** | **+2.8pp** | **[−3.7, +9.3]** | **no** |

**Shallow drawdowns (peak 70, −10 points) — the robust one:**

| gate | events | lift | 95% range | clears BH |
|---|---|---|---|---|
| none | 3,062 | +9.6pp | [+8.0, +11.2] | **yes** |
| ≤3¢ | 2,854 | +9.2pp | [+7.5, +10.9] | **yes** |
| ≤3¢ strict | 1,954 | +7.8pp | [+5.8, +9.8] | **yes** |
| **≤1¢ strict** | **1,339** | **+6.8pp** | **[+4.4, +9.3]** | **yes** |

**The shallow effect survives every gate with its range never touching zero. The
deep effect drifts down and its range crosses zero at the harshest gate — but
every gate's range overlaps every other's, so the decline is not established
either.** The sample falls 40% across those rows and that alone widens the
interval enough to explain the lost significance.

## 3. The structural fact that makes the spread story plausible

Near 30¢, the fraction of minutes quoted 1¢ wide or tighter:

| | ≤1¢ | ≤3¢ |
|---|---|---|
| **main tour** | **77.6%** | 93.7% |
| **ITF** | **20.9%** | 50.2% |

**The main tour naturally trades at the tightness the 1¢ gate forces on ITF.**
So "ITF forced to main-tour conditions" moves its deep-dip estimate from +6.3 to
+2.8 — toward the main tour's +0.1. **That is the shape a spread artifact would
have.** It is suggestive and it is not proof, because of §2's overlapping ranges.

## 4. ⚠ This one IS resolvable, and quickly — unlike the maker question

Deep-dip events available at the harshest gate, in the ~20-day out-of-sample
half:

| peak, dest30 | events | per day |
|---|---|---|
| 70 | 663 | 33.1 |
| 80 | 408 | 20.4 |
| 90 | 162 | 8.1 |
| **pooled** | **2,034** | **101.7** |

**The individual cells are underpowered; the flow is not.** At ~100 tight
deep-dip events a day, three weeks of fresh data gives about 2,000 — enough for
a range of roughly ±2 points, which separates +1 from +5 comfortably.

**And no recorder is needed.** The exchange serves this history retrospectively
inside its retention window, so the whole thing is: **wait about three weeks,
re-pull, re-run.** It costs nothing but the waiting.

> **Contrast with the maker question, which needed ~8,000 matches against 902
> that will ever exist — about two and a half years. This one is three weeks.
> That difference is the reason to do this one and not that one.**

⚠ **It must be run on FRESH data with the pooled definition pre-registered
first.** Pooling the peak thresholds after seeing the per-cell results, on the
same data, is precisely the selection that produced this repo's retractions.

## 5. What was NOT tested

1. **Whether the shallow effect is tradable.** 019 already measured every
   tradable version at **−5% to −33%**, and nothing here changes that. **A real
   predictive lift that is not a tradable edge is still the finding.**
2. **The pooled deep-dip cell**, deliberately — see §4.
3. **Anything involving score state.** `maker.db` has none: no set or game
   score, no server, no break points, no retirements, no ranking, no surface.
4. **Gates between 1¢ and 3¢**, and gates on depth rather than spread.
5. **Whether the main tour's deep cells would firm up with more data** — they
   would need roughly 10× their current 56–136 events.
6. **Challenger**, which sits between the two populations in book quality and
   was not run.

## 6. One correction to 019's own framing, in its favour

019 wrote: *"Either ITF is genuinely less efficient, or its wider spreads make
the mid a worse probability estimate and the lift is measurement error. That is
the first thing to resolve and it is not resolved."*

**Both branches assume the main tour's flatness is a measurement. It is not — it
is an absence of measurement.** The third possibility, which turns out to be the
live one, is that the two populations agree as well as 56 events can agree with
667, and the whole contradiction was an artifact of reporting a wide interval as
a point.
