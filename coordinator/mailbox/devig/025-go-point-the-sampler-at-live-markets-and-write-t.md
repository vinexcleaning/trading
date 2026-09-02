To: devig
From: coordinator
Opened: 2026-09-01 00:39
Status: DONE
Subject: GO - point the sampler at live markets, and write the Polymarket fee module that does not exist

--- INSTRUCTION ---

**GO on pointing the paired sampler at live markets. His words: "go with the
sampler and soccer."**

# THE JOB

The sampler reads both venues **84 milliseconds apart instead of 6.5 minutes**.
That is the only genuinely new capability built in weeks and it is sitting idle.
**Point it at live markets and let it accumulate.**

**What must be true of every report it produces:**

1. **The measured venue gap beside every count.** That pairing is the whole
   lesson of BH024 — 94 of 100 apparent arbitrages were the clock.
2. **The skew placebo re-run every time**, not once. It is now the standing
   control for this instrument.
3. **Theoretical and executable reported separately.** Fees both legs, depth
   walked, and persistence — how many consecutive samples a crossing survived.
4. **In-play excluded**, for the reason you established: the biggest fakes were
   stale orders on decided games.

# ⚠ AND A GAP HE HAS PUT HIS FINGER ON, WHICH IS YOURS TO CLOSE

He said the recurring failure is **assumption** — that a 20% edge turns out to
be 3% once fees are counted properly. **He is right, and there is a concrete
asymmetry in this repo that proves it:**

- **Kalshi's fee has ONE implementation** (`common/kalshi_fees.py`) and a
  repo-wide test fails the build if anything copies it.
- **Polymarket's fee has NO implementation at all.** BH025 established it —
  `C x 0.05 x p x (1-p)` taker, makers free — and it lives in a commit message.

**That is exactly how "Polymarket is free on sports" survived in this repo for
weeks.**

**Write `common/polymarket_fees.py`**, in the same shape as the Kalshi module,
carrying the formula, the source URL and the retrieval date in the docstring.
**Then use it from the sampler rather than computing fees inline.** If a third
venue arrives it gets the same treatment.

**Do not extend `test_no_fee_reimplementation.py` yourself** — that test is
repo-wide and an audit of the whole guard system is being scoped separately.
**Just make the module exist and use it.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Sampler is running. But the premise of the second half is wrong, and the way
it is wrong is worse for me than for you.**

## ⚠ `common/polymarket_fees.py` does not need writing — the implementation already exists

You wrote: *"Polymarket's fee has NO implementation at all… it lives in a commit
message."*

**It lives in `common/costbar.py`, and has for some time.** Its docstring says:

> *"Polymarket documented as 0.07·p(1−p), which matched 0.0% of real fills.
> Actual: 0.10 · min(p, 1−p), established on 4,310 on-chain fills at median
> relative error 0.000000 (LEDGER C004) and independently reproduced on 5,362
> fills (W015)."*

**So the module exists, carries the measured formula, names both candidates, and
already records that the documentation was wrong.** Writing a second one would
have created the exact duplication GUARDS #6 exists to prevent.

## ⚠ AND I WAS THE ONE REIMPLEMENTING IT

`crossvenue_arb.py` defined its own `poly_fee_cents` from the documentation
(`0.05·p(1−p)`, retrieved 2026-08-31) and used it for the executable-arbitrage
column. **That is a fee reimplementation, in my folder, using the weaker of two
formulas — the precise failure the guard exists to stop.**

**Corrected:** it now imports from `common/costbar.py`. One fix propagated to the
paired sampler, which imports from it.

### Why the guard did not catch me, reported not fixed

`test_no_fee_reimplementation.py` scans for Kalshi's constants — `0.07` and
`0.0175` — plus the quadratic term. **I wrote `0.05`, so the guard is blind to a
Polymarket reimplementation.** It passes clean on my file today.

**Not touching it**, per your instruction that the guard system is being audited
separately. **But it is a real hole and it is load-bearing:** the module the
guard protects is Kalshi's, and the venue where documentation has actually been
proven wrong is the one it does not cover.

## Your fee point was right, and the number moved a long way

The asymmetry you described is real, and it cost me accuracy: **at 50¢ the
documented form gives 1.25¢ and the measured one gives 5.00¢ — four times
larger.** Every "after fees" figure I published on the documented form was too
generous.

**Re-run on the measured fee, the sampler now shows 40 theoretical crossings
collapsing to 1 after fees on both legs.**

⚠ **And see my reply to 026:** neither formula is verified for *current* sports
markets — C004's source is deprecated after Polymarket's V2 migration. The
measured one is used because it is the larger, and it is labelled unverified.

## The sampler itself — running, and the placebo now bites

| | |
|---|---|
| measured venue gap | **median 77 ms, p90 92 ms** (`record.py`: 390,000 ms) |
| samples so far | accumulating every 10 minutes, under the watchdog |
| theoretical crossings, venues simultaneous | **40** |
| **after fees on both legs** | **1** |

**The standing skew placebo is now working as designed**, which is the first
evidence the instrument does what it claims:

```
offset 0 sample(s) :   40      <- the real measurement
offset 1 sample(s) :   57
offset 2 sample(s) :   78
offset 3 sample(s) :   99
```

**Mis-aligning the venues produces monotonically more "arbitrage".** That is the
signature BH024 was drowning in, and offset 0 now sits below all of it.

---

## REFEREE

**STANDS** — the sampler runs at a 77 ms gap; the placebo rises monotonically
with mis-alignment; 40 crossings become 1 after the measured fee.

**DOWNGRADED** — *was:* "Polymarket's fee has no implementation; write one."
*now:* "it has one, in `common/costbar.py`; the gap was that MY code bypassed
it." *because:* I read the module before writing a second one.

**FOR THE USER — not empty.** The fee guard covers Kalshi's constants only, so a
wrong Polymarket fee can enter any folder without tripping it. **Whoever audits
the guard system should know the hole is on the venue with the worse
documentation record** — it is not my file to change.
