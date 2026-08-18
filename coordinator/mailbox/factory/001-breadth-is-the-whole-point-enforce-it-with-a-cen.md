To: factory
From: coordinator
Opened: 2026-08-18 00:33
Status: OPEN
Subject: Breadth is the whole point - enforce it with a census and a per-category quota, not with intent

--- INSTRUCTION ---

**⚠ READ THIS BEFORE YOU START GENERATING. He has named a specific failure mode
and he is right about it. This message exists to make it structurally
impossible rather than merely discouraged.**

# 1. THE FAILURE MODE, IN HIS WORDS

> *"Claude has this... we get really focused. So for example, I tell the factory
> chat to find me a bunch of strategies. Instead we'll end up doing it to find
> me one really good market and find all the strategies within that market. But
> I wanted to do that with ALL the markets."*

**He is describing narrowing, and it is real.** Told to be broad, a session
picks the most tractable corner and goes deep, then reports depth as if it were
breadth. **Every instinct you have will pull you toward baseball, because
baseball is where the data already is. Resist it structurally, not by
willpower.**

# 2. BREADTH IS ENFORCED BY A LIST, NOT BY INTENT

**"Be creative and broad" is not an instruction anyone can follow or check.
This is:**

### a) CENSUS FIRST. Nothing is generated until the list exists.

**Enumerate every Kalshi series that is currently listed and open, and write it
to a file before you think about a single strategy.** You cannot silently skip
what is on a list you already committed. Group it into categories and put a
count against each:

sports · esports · weather and climate · economics and rates · politics and
elections · entertainment and awards · crypto and financial · companies and
tech · science and space · health · anything that does not fit

**He named some himself and they are examples, not the scope:** WNBA, NBA,
soccer. **The point of his message is the categories he did NOT name.**

### b) A QUOTA PER CATEGORY, NOT A TOTAL

**A total is how narrowing hides.** 200 strategies all on baseball satisfies
"200 strategies" and fails him completely.

**So: a minimum number of strategy specs for EVERY category in the census before
a second one is written for any category.** Breadth pass first, depth pass
second, and the breadth pass is not optional.

**If a category genuinely cannot support a strategy, that is a finding — write
down why, in one line, and move on.** *"No two-sided quotes"*, *"settles on a
source we cannot get"*, *"one market a year"*. **A category dismissed without a
written reason is a category you skipped.**

### c) VARIABLES PER MARKET, ALSO AS A LIST

For each family, before strategies: **what could possibly move this price?**
Write them out — including ones that probably do not matter. **His method,
§9c step 2: write down ALL the parameters BEFORE looking at any result.** A
parameter thought of after seeing a result is a different thing and must be
labelled as such.

### d) A COMPLETENESS PASS AT THE END OF EVERY CYCLE

Ask, in writing: **what did I not cover? What category got one strategy while
another got twenty? What data did I assume was unavailable without checking?**
**What that pass finds becomes the next cycle's work.** This is the single
mechanism that turns one deep dive back into a broad sweep.

# 3. ⚠ THE HONEST CONSTRAINT — SAY IT TO HIM, DO NOT PRETEND AROUND IT

**Generating strategies is unbounded. Screening them is not.**

We hold recorded tape on **19 Kalshi series**. The exchange has **12,396**. So
you can write specs for every family tonight and **you can only backtest the 19
we happen to have recorded.**

**That is not a reason to narrow the generation. It is the reason the recorder
is job one** — every family added starts accumulating history immediately, and
history cannot be bought back later.

**So the shape of the work is:**

- **generate broadly NOW**, because specs cost nothing and they are what tells
  the recorder what is worth recording
- **the census feeds the recorder's priority list** — that is the connection,
  and it is why the census comes first
- **screen what we can, and keep a visible queue of "written, waiting on tape"**

**Do not quietly restrict generation to what is testable today.** That is the
narrowing, wearing a respectable disguise.

# 4. SOURCES OF IDEAS — use all four, and the second is the one that gets skipped

1. **The extractors** — GitHub repos that really trade, YouTube methods with
   timestamps, Reddit and Discord claims. `signal` owns these and they are
   already built.
2. **Your own reasoning about market mechanics** — and this is the one that gets
   dropped in favour of searching, because searching feels like progress. How is
   a ladder priced. When does a family open and who quotes it first. What does
   the settlement source actually measure, and does it differ from what people
   think it measures. Where is a market maker structurally forced to quote. What
   happens at a family's first and last hour. Where does a fee curve make a
   trade impossible at one price and fine at another.
3. **The 51 claims out of 612 that `reopen` found were closed for the wrong
   reason.** A stocked pond nobody has fished.
4. **His own domain knowledge** — ask him specific questions when you have them,
   batched, never one at a time.

# 5. HOW LONG TO RUN — his explicit instruction

> *"It shouldn't cut off in ten minutes because this is a very deep prompt that
> should take hours."*

**Work through the whole census. Do not end a turn to report progress**
(`CLAUDE.md` §2). Do not ask whether to continue. Take the conservative option
on any judgement call, log it in your `DECISIONS.md`, and keep going.

**When he comes back, one consolidated report:** what the census found, the
per-category counts, what was generated, what was screened, what is queued
waiting on tape, and what the completeness pass says is still missing.

# 6. ⚠ WHAT "DONE" HONESTLY LOOKS LIKE TOMORROW MORNING — do not oversell it

He hopes it will be *"done thinking of everything"*. **Set the expectation
truthfully in your first report:**

- **realistic overnight:** the full census, every category ranked for whether it
  is tradeable at all, variables listed per promising family, and a first broad
  sweep of strategy specs with the per-category counts visible
- **not realistic overnight:** meaningful strategies for all 12,396 series, or
  backtests of anything outside the 19 recorded families

**Say which is which up front.** An honest smaller number beats a claim that
collapses when he reads the counts.

# 7. UNCHANGED AND NON-NEGOTIABLE

The backtest chooses, only the forward test counts. Placebo arm in every run.
Real bid and ask, real fees from `common/kalshi_fees.py` only. Paper only, no
keys, enforced by a copied test. Say how many strategies were screened to
produce anything you show him. **Coordinate with `devig` in `STATUS.md` before
touching `bot-hunt`. Stay away from `livedesk` — it is trading his real money.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

