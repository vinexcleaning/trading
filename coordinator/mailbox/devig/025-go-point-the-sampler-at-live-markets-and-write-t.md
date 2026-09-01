To: devig
From: coordinator
Opened: 2026-09-01 00:39
Status: OPEN
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

