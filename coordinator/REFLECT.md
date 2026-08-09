# REFLECT.md — the two checkers, and the pattern they exist to catch

**Asked for by the user on 2026-08-09, in his words:**

> *"Claude makes easy mistakes sometimes because it narrows in too much… you
> were so focused on the 97/3 instead of looking at the big picture, you might
> have completely gone past other stuff that might have worked. There needs to
> be a version of Claude that is actively looking for what is wrong… and then
> the other one is gonna act as a medium between the two, and then I will also
> come in as another medium."*

Three roles, in order. **He is the last word and the only one who resolves a
genuine disagreement.**

| Role | Job |
|---|---|
| **The Worker** | Does the work and writes the report. |
| **The Critic** | Attacks it. Hunts only for what is wrong, missing, or narrowed. Never balances. |
| **The Referee** | Takes both and says what actually stands, what is downgraded, what is genuinely unresolved. |
| **The user** | Decides the unresolved ones. Nothing pretends to resolve them for him. |

**The Critic is not allowed to be fair.** A critic that says "on balance this is
reasonable" has done nothing. Its output is a list of specific attacks or the
sentence *"I could not find anything wrong, and here is where I looked."*

---

## The evidence base: nine errors in one session, and eight share a cause

Recorded 2026-08-08/09. **Not one was caught by being careful. Every one was
caught by a second source.**

| # | What was claimed | What was true | Caught by |
|---|---|---|---|
| 1 | The bet is 97c to make 3c | One price at one instant. Games are 85/15 and 90/10 too | **the user** |
| 2 | `runners\install.ps1` needs no administrator | Access denied | running it |
| 3 | Kalshi has no Premier League or Champions League | 231 Champions League markets, 51.7m contracts | `devig` |
| 4 | Kalshi soccer is mostly international friendlies | That window was the international break before the World Cup | `soccer` |
| 5 | The cost bar is 4.8c | 0.20c at 97c — the fee is near its minimum at the edges | computing it |
| 6 | Any table keyed on the displayed minute is fiction | True for the price join, false for the comeback table | `soccer` |
| 7 | The coin-flip analogy | Oversells randomness; the luck is in which slice you picked | **the user** |
| 8 | This is survivorship bias | It is not. It is selection among strategies | **the user** |
| 9 | The baseball admin job may already be done | The task exists, but registering one needs elevation | running it |

### The pattern, and it is the Critic's first question

**Eight of nine: read ONE source, concluded, stated it confidently.** Not one
was a reasoning error. Every one was a *sourcing* error.

- #3 and #4: one recording window, treated as a census.
- #2 and #9: read a script for a flag, never ran it.
- #1: an illustration in a handoff note, treated as a measurement.
- #5: a number that was true elsewhere, applied where it was not.

**Absence is the sharpest case.** "There is no X" is almost never supportable
from one place — it needs a source that would have shown X if X existed. Three
of the nine were absence claims and all three were wrong.

---

## The Critic's checklist

Work down it. Each item is a question with a wrong answer, not a topic.

### 1. Sourcing — where eight of nine died

- **For every claim: how many independent places did this come from?** If one,
  say so out loud in the report.
- **Any sentence containing "no", "never", "none", "only", "not available"** —
  what would have shown the opposite, and was that consulted?
- **Was a script READ where it should have been RUN?** Reading is not evidence
  about behaviour.
- **Is a number being carried from another context?** Fees, cost bars, sample
  thresholds. A number true at one price or one sport is not a number.
- **Does the window cover the thing being claimed absent?** A 69-day window in
  one sport's off-season shows that sport as absent.

### 2. Narrowing — the failure the user named

- **What versions of this idea were NOT tested?** List them. `CLAUDE.md` §9c
  step 7 makes this mandatory on any negative result.
- **Has one number become the whole frame?** The 97c case: a single
  illustrative price silently became the definition of the strategy, and the
  question *"what about 85c"* was never asked until the user asked it.
- **Is a parameter fixed that should be a column?** If the answer could differ
  across it, it is a column.
- **Would a different-but-reasonable choice change the conclusion?**

### 3. The number itself

- **Does every number carry the dates it was measured over?**
- **Is it the right unit?** A match settles once.
- **Was the naive benchmark reported next to it?**
- **Gross or net?** Middle price or the price you would really pay?
- **Is the sample big enough to see the effect being claimed**, and if not, is
  that said?

### 4. Selection

- **How many things were tried before this one looked good?**
- **Was the winner checked on data not used to find it?**
- **Was a control run** — the same machinery on scrambled data?

### 5. Writing

- **Any jargon at all?** `CLAUDE.md` §1 banned list. Money, or out of 100.
- **Does every number say bigger-is-better or bigger-is-worse?**
- **Is a guess presented as a fact?**

---

## The Referee's job

Take the work and the attacks. Produce three lists and nothing else:

1. **STANDS** — survived, and why.
2. **DOWNGRADED** — still true but weaker than stated, with the weaker wording.
3. **FOR THE USER** — genuine disagreements, and the two positions stated
   fairly enough that he can pick without reading either in full.

**The Referee never resolves a real disagreement.** If the Worker and Critic
disagree on something that matters, it goes to the user with both cases. That
is what he asked for and it is the one thing that cannot be delegated.

---

## When it runs

**Before any report that reaches the user**, and before any result is written
into `BRIEF.md` or `LEDGER.md`.

`py -3 coordinator\reflect.py --file <draft>` does the mechanical part — it
finds absence claims, undated numbers, jargon and single-source language. **It
catches wording, not reasoning.** The checklist above is the part that matters
and it needs a mind, not a script.
