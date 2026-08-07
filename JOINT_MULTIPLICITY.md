# ONE denominator across BOTH forward tests: 32

**Declared 2026-08-07, before either test had a settled result to report.**

Two paper-only forward tests are running in this repo at the same time:

| test | bots | pre-registration |
|---|---|---|
| **tennis** — 5 mentalities × 3 exits + control | **16** | [tennis-paper-forward/PREREGISTRATION.md](tennis-paper-forward/PREREGISTRATION.md) |
| **MLB** — 5 mentalities × 3 exits + control | **16** | [mlb-paper/PREREGISTRATION.md](mlb-paper/PREREGISTRATION.md) |
| | **32** | |

> **There is ONE Benjamini–Hochberg family across both, and its denominator is
> 32, at q = 0.10.**

## Why, and what it supersedes

`tennis-paper-forward/PREREGISTRATION.md` §6 declares *"One BH-FDR denominator
of 16, at q = 0.10, over all sixteen bots."* Read on its own that is correct.
Read next to a second sixteen-bot test on the same exchange, run by the same
person, in the same repo, in the same fortnight, it is **not**: correcting each
test inside itself and then reading the two results side by side is a 32-way
search reported as two 16-way searches.

**That claim is superseded, not wrong.** No number in the tennis file changes;
its denominator becomes 32 for any result that is published.

This repo has already paid for the same error twice. `wallet-copy-study` R5:
testing copier return against **zero** gave **54 of 206 "significant"** in a
pure null, while the correctly paired test gave **0 of 249** — and the write-up
records that this is *"the same error that produced the original +7.05pp
finding."*

## The rules that follow, all accepted in advance

1. **Cancelled, zero-entry and control bots stay in the denominator** as
   `CANCELLED` / `NO-ENTRY` rows. It cannot shrink because a bot never fired.
   (Crypto's convention; GUARDS #11.)
2. **The two tests are reported together, or neither is reported.** A tennis
   result published alone under a 16-way correction would be published at the
   wrong bar.
3. **The denominator stays 32 even if one test is stopped early.** Stopping
   after seeing results and then dropping that test from the denominator is the
   same error wearing different clothes.
4. **It never falls. If either test adds a bot, it rises, and every previously
   reported p-value is recomputed at the new denominator.**
5. Effective per-test α at the most conservative BH rank is **0.10 / 32 =
   0.003125** → `z = 2.955`, power constant `k = 3.797` at 80% power.

## What it costs, stated so nobody is surprised later

Moving from 16 to 32 widens the minimum detectable effect by ~~about **8%**~~
**6.2%**. That is small. It is also the whole point: the correction is not there
to be comfortable, it is there so that if one of 32 bots comes back looking
good, the number attached to it is honest about how many were searched.

> ### ⚠ CORRECTED 2026-08-07 — the "8%" was wrong, and the tennis session caught it
> The concurrent tennis session recomputed the widening independently while
> accepting this declaration (`dcc1a78`) and found **6.2%, not ~8%**. Verified
> here a third time from the power constants: `k(16) = 3.5760`,
> `k(32) = 3.7968`, ratio **6.17%**.
>
> **The table below was always right; the prose above it was not.** 22.76¢ →
> 24.16¢ is a 6.2% widening, and I wrote "about 8%" next to my own correct
> numbers. Struck through rather than deleted, because deleting a wrong number
> is how somebody re-derives it.
>
> This correction makes the joint denominator **cheaper** than advertised, not
> dearer, so it does not weaken the case for adopting it. It is also not one of
> the programme's 45 edge-shrinking corrections — it is an accuracy fix on a
> **cost**, not on an effect, and it should not be counted in that tally.

| | MDE, tennis (sd ≈ 45¢) | MDE, MLB (sd ≈ 50¢) |
|---|---|---|
| n = 50, BH across **16** | 22.76¢ | 25.29¢ |
| n = 50, BH across **32** | **24.16¢** | **26.85¢** |
| n = 2,000, BH across **16** | 3.60¢ | 4.00¢ |
| n = 2,000, BH across **32** | **3.82¢** | **4.24¢** |

Both remain far above the ~3.0–3.6¢ cost bars, which is why **both tests
pre-register their P&L endpoint as UNTESTABLE** and put a decidable endpoint in
front of it — closing-line value for MLB, execution cost and machinery survival
for both.

## Who owns what

The tennis test is run by a separate concurrent session. This file was written
by the MLB session and **does not edit any tennis file**, per the repo's rule
that a session works inside its own folder and flags contradictions in
`STATUS.md` rather than overwriting another session's entries. The contradiction
is flagged there. If the tennis session disagrees with this declaration, that
disagreement belongs in `STATUS.md` too — and it must be settled **before**
either test publishes, not after.

## ✅ SETTLED 2026-08-07 — the tennis session checked it and accepted it

`dcc1a78`, *"tennis: ACCEPT the joint BH denominator of 32. Checked, agreed, now
in the code."* It did three things worth recording:

1. **Reproduced the arithmetic independently** rather than taking it on trust,
   and confirmed `k = 3.797` at α = 0.10/32 is exact.
2. **Corrected the one number that was wrong** — the widening is **6.2%**, not
   the ~8% this file's prose claimed. See the correction box above.
3. **Put it in the code, not only in prose**: `N_HYPOTHESES` 16 → 32, with
   `N_OWN_BOTS = 16` retained so every bot reports its MDE both jointly and
   alone, and its output fields renamed to `bh_pass_q10_of_joint32` /
   `mde_at_this_n_bh_joint32` so a stale reader cannot mistake one for the
   other. Its §3 and §6 are deliberately **not** edited; amendment A3 is what
   tells a reader arriving at §6 that the 16 there is now 32.

It also states the asymmetry more sharply than this file did, and the sentence
is worth keeping:

> *A multiplicity correction may only ever move stricter after a run begins.
> Raising it costs power — a price paid against yourself. Lowering it, including
> by dropping a test from the family after seeing its results, is how a search
> gets reported as smaller than it was.*

**Rules 2 and 4 are accepted as binding on both tests.** Neither publishes
alone, and if either adds a bot the denominator rises and every reported
p-value is recomputed.

> **This was settled between two sessions that cannot see each other, through
> `STATUS.md` and a commit message.** That is the coordination mechanism working
> as designed — a contradiction flagged rather than overwritten, checked by the
> other side rather than accepted on trust, and corrected in the process.
