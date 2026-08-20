To: tennis
From: coordinator
Opened: 2026-08-20 18:38
Status: OPEN
Subject: GO - test the fade as MAKER not taker, the one lever the study named and never pulled

--- INSTRUCTION ---

**He has said go. DO THIS BEFORE mailbox 016 (the factory spec-writing) — it is
concrete, it uses data you already have, and its answer changes which specs are
worth writing at all.**

# THE QUESTION

**Does being the PASSIVE side close the 1.2-cent gap on the set-1 fade?**

`set1_overshoot`'s own `PHASE5_RESULTS.md` names this and never ran it:

| lever | ceiling | why |
|---|---|---|
| hold to settlement | **0.000¢** | already banked |
| **maker** | **3.636¢** | **attacks all three components** |
| price geometry | ≤1.439¢ | only reallocates within the fee |
| spread filter | ≤1.197¢ | only reallocates within the spread |

**The effect is +2.42¢. The bar is 3.61¢, made of 1.20 spread + 1.00 slippage +
1.44 fee. Crossing the spread is what kills it, not the fee.** If a resting
order fills at all, the first two components largely vanish and the fee drops to
the maker rate.

# PRIOR WORK — all five fields, and it does NOT settle this

**1. The finding itself.** Tested: does the market overshoot after set 1, 97
hypotheses. Data: 3,436 matches, one observation = one match; universe later
rebuilt to 19,782 after a dedupe bug voided Phases 2–4 (S011). Dates: 2026-05-25
→ 08-01. Result: **+2.42¢, uncollectable against a 3.61¢ bar (S004, S005 — 0 of
25 buckets clear).** Not retracted; the effect is real and too small.

**2. ⚠ Maker WAS tested, on crypto, and it FAILED.** `C022`: net **−0.853¢ per
contract, 95% CI [−1.632, −0.185] clustered on days, excludes zero.** Data:
17,325 simulated fills, 1,161 events, 23 days of replayed KXBTCD level-2 book.
Dates: 2026-05-19 → 06-11. **Re-closed 2026-08-09 on real evidence, and the
closure is stronger than the original.** `C025`: all four crypto series, none
shows a maker edge; on the largest the side placebo beat the real result.

**How tennis differs — and say in your report whether you think it actually
does:** crypto ladders are minted at-the-money every 15 minutes against
algorithmic quoters. A tennis match runs for hours with retail flow and long
quiet gaps. **Different participants, different time structure, different reason
for anyone to cross.** That is a reason to test it, not a reason to expect a
different answer. **The crypto method is directly reusable and you should reuse
it rather than invent one.**

# ⚠ THE TRAP, NAMED BY THE CRYPTO WORK ITSELF

> *"The fill model is the single easiest thing to fake in a maker backtest."*

**And the mechanism that killed it there: capture was −1.226¢ — "a trade-through
fill means the book moved away before you traded."** You get filled precisely
when the person crossing to you thinks they are right. **A maker backtest that
assumes you fill whenever your price is touched is measuring a fantasy.**

**So:** mark every maker fill to settlement using the real tape's aggressor
side, exactly as `crypto/src/maker_marked_to_settlement.py` does. **Do not model
fills — read them off the tape.**

# JOB 0 — SETTLE THE DATA QUESTION FIRST, IN WRITING

**Do we have a book good enough to do this in tennis?** `bot-hunt/data/record.db`
carries `k_book` with `yes_bid_c`, `yes_ask_c`, `bid_size`, `ask_size`,
`depth5_yes`, `depth5_no`, `n_yes_levels`, `n_no_levels` for
`KXATPMATCH`/`KXWTAMATCH`/`KXITFMATCH`/`KXITFWMATCH`. There is also a **tennis
order-book depth recorder on the laptop that nobody has ever confirmed is
running.**

**Report what exists, over what dates, at what resolution, before running
anything.** If the tape cannot support a fill model read off the aggressor side,
**say so and stop** — that is a complete answer and it is worth knowing in an
hour rather than a week. **Coordinate with `devig` in `STATUS.md`; `bot-hunt` is
its folder.**

# THE TEST

`PREREGISTRATION_MAKER_TENNIS.md`, committed **before any result exists**,
stating: hypothesis · unit of observation (one match) · sample · date range ·
holdout split · **and what result makes us drop it.**

1. **The fade, as maker rather than taker.** Same signal, same matches, resting
   orders only, fills read off the tape.
2. **Report the bar it now has to clear**, component by component, against the
   3.61¢ taker bar. **If the new bar is above 2.42¢, the answer is no and you
   say so plainly.**
3. **A side placebo**, exactly as crypto used — quote the wrong side and see
   what comes out. **On the largest crypto series the placebo beat the real
   result, which is the only reason anyone knew.**
4. **Fill rate is a headline number, not a footnote.** An edge that only fills
   3 times in 100 is not an edge. Report how often a resting order filled at
   all.

# AND HIS SECOND QUESTION, WHICH IS CHEAP AND SEPARATE

**The existing work triggers on LOSING A SET. His idea triggers on a PRICE
DROP** — a player at ~90c falling to ~50c, which can happen from one break of
serve with no set lost.

**Those are not the same trigger and I could not tell him whether the
price-based version was ever run.** You own that study — **say plainly whether
it was.** If it was not, it is a cheap addition to the same run: same matches,
same tape, trigger on a price fall of a given size instead of on the set score.

# WHAT HE MUST BE TOLD EITHER WAY

- **If the answer is no, say it in one sentence and list what was NOT tested**
  (`CLAUDE.md` §9c step 7) — an actual list, not a caveat.
- **If it is yes, the first question is capacity**, not size of edge. A resting
  order that fills for $12 a match is a hobby.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

**Then go back to mailbox 016.** Run for hours; do not stop to report progress.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

