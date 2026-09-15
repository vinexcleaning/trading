# PRE-REGISTRATION — Kalshi combos (parlays)

**Written 2026-09-15, before any markup number existed.** Mailbox 013 §7 asked
for exactly this and asked for it first. Nothing in this file may be changed
once a result exists; changes go in a dated amendment section at the bottom
with the old wording struck through and visible.

**Sibling documents:** `PREREGISTRATION.md` (the factory's general rules) and
`PREREGISTRATION_HOLDON.md` still apply. This one is narrower and governs only
the combo work.

---

## 0. What a combo is, and the three facts that shape every test below

Kalshi's own help page, quoted rather than paraphrased
(help.kalshi.com/en/articles/13823820-combos, dated 2026-06-20):

> *"Combos allow you to trade custom combinations of events in a single
> position. Each combo is a unique market with its own dedicated order book.
> Combos resolve to the product of the underlying positions, paying out a
> maximum of $1.00 per contract."*

Verified against the live API on 2026-09-15, not taken on trust:

1. **There is no standing book.** Every settled combo read so far quotes
   `yes_bid 0.0000 / yes_ask 1.0000`. That is not a wide spread; it is the
   absence of a book. The only price that ever existed is `last_price_dollars`
   — what somebody actually paid.
2. **A filled combo cannot be sold.** Kalshi: *"Once a combo is placed and
   filled, it cannot be canceled or reversed."* On the settled rows read,
   `volume` and `open_interest` are the same number, which is what that implies.
3. **Legs are ordinary Kalshi markets.** `mve_selected_legs` names each leg's
   market ticker and side, so the price paid is directly comparable to what the
   legs themselves cost.

**Consequence taken as a rule, not re-derived later: no exit rule, no sizing
rule and no hold-versus-sell variant is in scope.** There is nothing to exit.

---

## 1. The hypothesis, stated so that it can fail

**H1 (the only primary hypothesis).** The price actually paid for a combo is
higher than the product of its legs' own asking prices at the same moment, by
a margin that is stable enough to state as a number.

    markup = price_paid / (product over legs of that leg's ask)

**H1 is a measurement of a cost, not a search for an edge.** The direction is
not in doubt — a dealer quoting into a request will not quote below fair — so
the test is not *"is the markup positive"*. It is **how big**, because that
number alone decides whether a combo can ever be worth taking.

**H2 (secondary, and it is the one that matters to him).** Stacking legs
multiplies whatever edge the legs already have; it does not create one. For
independent legs priced at the product,

    combo edge ratio = (p1/q1) x (p2/q2) x ... x (pn/qn)

so an edge compounds and so does a deficit. **This repo has already measured
its own legs as negative at the ask**, so the pre-registered expectation is
that combos are worse than legs, not better, and worse faster with more legs.

---

## 2. The unit of observation, and why the obvious one is wrong

**One observation is ONE DISTINCT SET OF GAMES, not one combo.**

Mailbox 013 put it plainly: *"six combos sharing five games are not six
observations."* Combos are built from a small pool of the day's games, so two
combos on the same evening will often share four of six legs and their
outcomes are almost the same event.

**So every result is reported twice:** once counting combos, and once counting
distinct leg-sets, and **the smaller number is the one any confidence statement
uses.** Where combos overlap partially rather than exactly, the effective count
is reported as the number of distinct *legs* covered, which is a floor.

**This is GUARDS territory and the repo has the scar:** 490,464 fills from 762
matches are 762 observations, not 490,464.

---

## 3. The sample, and the date range, and what will be missing from it

- **Sample:** every combo market the recorder captures, across every combo
  series the exchange lists. Series are discovered from
  `/multivariate_event_collections`, not typed in, so a new family is included
  automatically.
- **Date range:** starts 2026-09-15. Backwards coverage is whatever Kalshi's
  rolling window still holds on that date — **about 69 days, so roughly early
  July 2026 at best**, and it shrinks every day.
- **⚠ What will be permanently missing, stated now rather than discovered
  later:** every combo that settled before the window. It is not recoverable at
  any price. Any statement about combos therefore describes **mid-2026 onward**
  and may not describe the product at launch.
- **A combo whose legs are NOT on this project's own tape** can still be
  measured through Kalshi's candle API, but only while those legs are inside
  the same 69-day window. Where neither source has the leg, the combo is
  recorded and **excluded from the markup test with the reason stored**, never
  silently dropped.

---

## 4. The comparison price — and the assumption that most needs attacking

`last_price_dollars` says what was paid. **It does not say when.** The API gives
`created_time` for the combo market and `close_time` for its settlement, but no
timestamp on the trade itself.

**Pre-registered assumption:** because a combo market is created *by* a request
for a quote, the fill happens at or very near `created_time`. Leg prices are
therefore taken at `created_time`.

**Pre-registered sensitivity test, run before any headline number is quoted:**
recompute every markup using leg prices at `created_time` **minus one hour** and
**plus one hour**. **If the median markup moves by more than 1 percentage point
across that three-hour span, the timing assumption is doing the work and the
headline must be reported as a range rather than a number.**

**Leg price used is the ASK, never the middle price.** Buying legs separately
means paying the ask; comparing a paid price to a middle price would
manufacture a markup that is really just the leg spread.

---

## 5. What result would make me drop this — written before looking

**The kill condition, and it is mailbox 013's suggested number, adopted
unchanged:**

> **If the median markup is above 3 percent, the family is dead for TAKING.**

The arithmetic behind accepting that number rather than inventing one: on a
two-leg combo of 70-cent legs, the whole fee saving against buying the legs
separately is **1.19 cents on a 49-cent combo — about 2.4 percent of the
price.** A markup above 3 percent therefore eats the entire structural
advantage and more, and what remains is a worse version of buying the legs.

**Three further kill conditions:**

1. **Fewer than 100 combos, or fewer than 40 distinct leg-sets.** Below that,
   the honest answer is *"we could not tell"*, reported as **unmeasurable, not
   as negative** — `LEDGER` K012 is the standing warning that those are
   opposite sentences.
2. **Leg prices unavailable for more than half the captured combos.** Then the
   measured half is a biased sample of whichever families this project happens
   to record, and the number describes my tape rather than the exchange.
3. **The markup has no centre** — if it is spread so wide that the middle
   number carries no information (say, a quarter of combos below 1 percent and
   a quarter above 15), then "the median markup" is the wrong summary and the
   result must be reported as a distribution with the shape described, not as a
   single figure.

**And one anti-kill, because killing on a technicality is a recorded failure
here (§7 of CLAUDE.md):** a high markup kills **taking** combos. It does not
kill **quoting** into other people's requests, which is the opposite side of
the same trade and is a separate question with its own pre-registration if it
is ever asked. Nothing in this document licenses the sentence *"combos don't
work"*.

---

## 6. What is reported beside every number, without exception

- **The naive benchmark:** what buying the same legs separately, at their own
  asks, would have returned over the same games. A combo result with no leg
  comparison beside it is not a finding.
- **Both counts:** combos, and distinct leg-sets.
- **The scalar and did-not-play cases, separately.** A leg whose player does
  not appear settles to a fraction rather than to yes or no, and the combo pays
  the product including that fraction. **Folding those into a win rate would
  quietly bias it**, so they are counted and reported on their own line.
- **The placebo arm**, per CLAUDE.md §9c step 4: the same machinery run over
  combos whose legs have been re-paired at random from the same day's markets.
  If the pipeline finds a markup structure in randomly assembled legs, the
  pipeline is broken and every number it produced is void.
- **The fee, from `common/kalshi_fees.py` only**, at the combo's own price —
  never a fee computed leg by leg and added up, which is the mistake the whole
  fee advantage consists of avoiding.

---

## 7. What is explicitly NOT being tested, and why

Written now rather than at the end, because §7 of CLAUDE.md exists precisely
because a list written after a null result gets thinner.

| not tested | why |
|---|---|
| **exit rules of any kind** | combos cannot be sold. Kalshi says so and the open-interest figures agree |
| **covering both sides of a leg** | mailbox 009 killed it by arithmetic: two fees, and the leg cancels exactly |
| **his own three-or-four winning parlays** | at roughly even odds, three of four happens about **25 times in 100 by luck alone**. A sample of four cannot separate skill from that |
| **"the AI picked the legs"** | a real and testable claim, and **not** assumed here. It needs its own pre-registration with the picks recorded before the games, or it is unfalsifiable |
| **quoting into other people's RFQs** | the other side of the trade. Out of scope, explicitly not killed |
| **automating anything** | mailbox 013 §9: nothing gets automated until a markup exists and a leg with a real edge exists. Neither does yet |
| **combos on non-sports families** | weather and mentions collections exist and are being recorded, but the first measurement is on sports because that is where the settled rows are |

---

## 8. Amendments

*(none yet — amendments are appended here with a date, the old wording struck
through, and what forced the change)*
