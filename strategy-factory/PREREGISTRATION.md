# PREREGISTRATION — the Strategy Factory

**Written 2026-08-18, before the factory measured anything about any strategy.**

Amendments are numbered and dated at the bottom. Nothing above the amendment
line is ever edited after a result exists. A pre-registration that changes after
the fact is worthless, and that includes changing it quietly.

---

## 0. Honest note on ordering — two things were measured before this file existed

I am saying this here rather than leaving it to be discovered.

1. **The exchange census** (`src/census.py`) and **the shape measurement**
   (`src/shape.py`) ran before this file was written. They are counts of what
   the exchange lists and what carries a quote. They contain no strategy, no
   return, and no thing that could be selected on. Pre-registering "how many
   markets are there" would be theatre.
2. **The list-endpoint quote check** (`src/verify_list_quotes.py`) also ran
   first. It is a claim about an HTTP response, not about money, and it had a
   stated drop rule inside its own docstring before it ran: *below 90%
   agreement at one tick, or any series where the list side is systematically
   absent while the book has one.* It cleared both.

**No strategy has been screened, scored, or looked at as of this file.** That
is the line this document is guarding.

---

## 1. The question the factory exists to answer

> **Does any strategy, chosen by a backtest over Kalshi's recorded tape,
> continue to make money on games that did not exist when it was chosen?**

Everything else in this folder is machinery for asking that question at scale
without lying to ourselves.

### What number answers it

For each promoted strategy, the **forward paper-traded return per contract in
cents, net of real fees from `common/kalshi_fees.py`, entered at the real ask
and exited at the real bid**, over markets that opened after its
`PREREGISTRATION_<NAME>.md` was committed — placed beside the range that the
same number would fall in if the strategy had no skill at all.

**A forward result inside its no-skill range is not a result.** It is reported
as "not distinguishable from no skill", never as a small edge.

---

## 2. THE RULE THAT MAKES THE REST HONEST, and the number behind it

The factory will generate hundreds of strategies and report the best. That
process manufactures a large-looking edge out of nothing:

| strategies generated, **all with zero skill** | best one typically looks like | shows +30% or better |
|---|---|---:|
| 10 | +10.1% | never |
| 200 | +23.7% | 5 in 100 |
| **2,000** | **+29.5%** | **37 in 100** |

*(Source: `coordinator/STRATEGY_FACTORY.md` section 1, 20,000 simulated runs of
100 bets at 50 cents paying the real fee. I have not re-derived it here; it is
carried in as a stated prior, and section 6 below re-derives it inside this
folder before the first screen runs.)*

So:

1. **The backtest chooses. Only the forward test counts.**
2. **A backtest number is never reported to the user as money**, never sized
   on, and never called a result.
3. **Every report states how many strategies were screened** to produce the one
   being shown. Without that number the return is uninterpretable, and it is
   the number that always goes missing.

---

## 3. The screening stage — what it must clear to be believed at all

### The placebo arm, and it is a gate not a diagnostic

Every screening run carries a placebo arm: **the same machinery over the same
tape with the settlement labels shuffled.** Shuffled within market family and
within day, so the placebo keeps the real distribution of prices, spreads,
fees and market sizes and destroys only the link between the strategy's rule
and the outcome.

**What would make me throw the run away:** if the placebo arm's best strategy
scores at or above the real arm's best strategy, **every number that run
produced is void** — not "interesting", not "weaker than hoped". Void, and said
out loud in the report.

**The number I will report either way:** best-of-N in the real arm, best-of-N
in the placebo arm, and the gap between them, on every single run.

### What the screen is allowed to use

- **Real bid and real ask from the tape. Never the mid.** GUARDS #7.
- **Real fees from `common/kalshi_fees.py` and nothing else.** Guard #6 is
  enforced repo-wide by `common/tests/test_no_fee_reimplementation.py`.
- **Real depth.** Entry is priced by walking the recorded ladder, not by
  assuming the touch size is infinite.

### The naive benchmark, reported beside every screen

Three of them, because one is too easy to beat by accident:

1. **Buy the favourite and hold to settlement** in the same markets, same
   fees.
2. **Buy at random** in the same markets, same fees, same number of bets.
3. **Do nothing** — zero, which after fees is better than most strategies.

---

## 4. The forward stage — the only stage that produces a result

### Unit of observation

**One settled market.** Not one fill, not one snapshot, not one price change.
A market settles once. 490,464 fills from 762 matches are **762**
observations, and this repo has already paid for forgetting that.

Where a family lists a ladder of strikes on one underlying event (weather
highs, crypto levels, index closes), **the unit is the EVENT, not the strike.**
A 10-strike ladder on one day's New York temperature is one temperature
reading, not ten markets. Effective sample size is reported, not nominal.

### How many observations before a strategy can be judged

**A strategy is not judged before 100 settled units.** Below that, the
no-skill range is so wide that nothing outside it could be trusted and nothing
inside it means anything.

At 100 units, a strategy trading at around 50 cents can be distinguished from
no skill only if it makes roughly **4 cents or more per contract**. Anything
smaller than that, at this sample size, is undetectable — and saying so up
front is the point of writing it here.

**Families where 100 units will not arrive by 2026-09-18 are declared SLOW in
advance**, in `HANDOFF.md`, so that "no answer yet" in September is a
prediction that came true rather than a shrug.

### What makes us drop a strategy

Any one of these, and it is dropped and marked dropped, not quietly rested:

1. Forward result **inside** its no-skill range at 100 settled units.
2. Forward result **negative** at 50 settled units — half the sample, and the
   direction already wrong.
3. The rule fires on **fewer than 10 units in its first 30 days** — a strategy
   nobody can trade is not a strategy.
4. **Capacity below $25 per opportunity** when priced by walking the real
   recorded ladder. His bankroll is small but it is not $12, and an edge that
   only exists in the first two contracts is a hobby.

### What we will NOT do

We will not re-screen a dropped strategy against the same tape and promote it
on a second look. A strategy gets one forward test. A **variant** of it is a
new strategy with a new id, and it counts against the screened total.

---

## 5. The recorder — what "widened" has to mean to count

The urgent, irreversible stage. Its success criterion, fixed now:

- **Recorded families rise from 19 to at least 300** carrying a real quote,
  covering at minimum crypto, weather, economics, financial index levels and
  the non-sports categories that had nothing at all.
- **Zero reduction in the existing 19.** `bot-hunt`'s recorder is not touched,
  not restarted, and not competed with. The factory writes its own database
  file. Add, never replace.
- **Disk stays under 40 GB per 30 days** for the wide tape. If the first
  three days project past that, the long tail's interval is lengthened and
  the change is written into `DECISIONS.md` with the measured number that
  forced it — not a guess made now.
- **What was dropped is reported**, with the reason and the count, in
  `reports/SHAPE.md` and `HANDOFF.md`.

**What would make me revert the whole thing:** if the wide recorder's presence
measurably degrades `bot-hunt`'s recorder — a slower cycle, a missed cycle, a
`database is locked` — it is stopped that hour and the incident written up.
The 62 GB tape is the best asset in this repo and this project does not get to
risk it.

---

## 6. What has to be true before the first screen runs

These are gates, in order. None is skippable.

1. `tests/test_paper_only.py` passes. **Done, 2026-08-18.**
2. `common/tests/test_no_fee_reimplementation.py` passes with this folder in
   the tree.
3. The **best-of-N null is re-derived inside this folder** — my own code, my
   own numbers, on the real fee function — so the table in section 2 is a
   measurement here and not a quotation from elsewhere.
4. The **placebo arm exists and has been run once on real tape**, and its
   output is in the report before any real screen is read.

---

## 7. The benchmark I expect to lose to

Stated now so it cannot be forgotten later: **the honest expectation is that
the general, all-markets version of every strategy is flat or negative after
fees.** That is what the last eleven months of this repo say, it is what the
user himself predicted, and it is the correct prior.

The factory is not built because an edge is likely. It is built because
**finding out cheaply, at scale, on data that cannot be bought back later, is
worth doing even when the answer is usually no.**

---

## AMENDMENTS

*(numbered and dated; nothing above this line is edited)*

**A1 — 2026-08-18.** None yet. This line exists so that the first amendment is
visibly an amendment.
