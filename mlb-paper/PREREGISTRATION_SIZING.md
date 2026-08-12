# PREREGISTRATION — the sizing arms

**Written 2026-08-12, before the harness existed and before any arm had a
balance.** Nothing below was chosen after seeing a result. Amendments go in §8.

His idea, in his words (relayed via mailbox 010):

> *"We'll give them all a $250 balance, and they have different mentalities so
> they can place however much money they want. We could put one bot that
> literally gambles half their portfolio, one that only gambles five percent."*

---

## 1. ⚠ THE ANSWER IS PARTLY KNOWN IN ADVANCE, AND IT IS WRITTEN HERE SO NOBODY CAN CLAIM IT LATER

**Sizing cannot create an edge. It cannot change the average result. Betting
half the pot and betting 5% of it have exactly the same expected outcome.**

What sizing changes is **the chance of going broke**, and the shape of the ride.
That is arithmetic, not a hypothesis, and this test is not run to discover it.

**So why run it at all?** Because he has already been shown the table and it did
not land, and watching a half-the-pot bot destroy a $250 paper balance on his
own picks will. **The purpose of this test is to make a known fact visible on
his own data.** That is a legitimate reason to build something, and pretending
otherwise afterwards would be dishonest.

> **Therefore: no arm winning is a discovery.** If `all-in` finishes first, that
> is not evidence that betting everything is good. §5 is what decides.

## 2. What is fixed, and what varies

**Every arm sees the identical picks, at the identical entry prices, on the
identical games, in the identical order.** They are replays of the `starter`
and `early` entries already recorded in `data/paper.db` — **no new signal, no
new data, nothing collected.**

**Only the stake rule differs.**

| arm | stake on each bet |
|---|---|
| `flat-5` | 5% of the **starting** $250, fixed forever — $12.50 every time |
| `flat-5-comp` | 5% of the **current** balance |
| `flat-20` | 20% of current |
| `half` | 50% of current |
| `all-in` | 100% of current |
| `kelly` | the mathematically optimal fraction for the edge the bot claims |
| `kelly-half` | half of that, which is what people actually use |

Starting balance **$250** each. Fees and the real entry price apply exactly as
in the live test — `common/kalshi_fees.py`, never a mid.

**An arm that cannot afford one contract is BUST and stops.** It is not topped
up, not reset, and not quietly skipped. Going broke is the outcome being
measured, so hiding it would remove the point.

## 3. The unit of observation, and the reordering

**A settled game.** Contracts are integers, so a stake buys
`floor(stake / price)` contracts and the remainder stays in the balance.

**Order matters enormously for compounding arms, and one ordering is one
anecdote.** So each arm is run over **2,000 random shuffles** of the same
settled games. The games and their outcomes are fixed; only the sequence moves.

> This is legitimate because **the outcomes are already known and unchanged** —
> shuffling re-asks "what if these same results had arrived in a different
> order", which is exactly the question sizing is about. It is **not** a
> resample of outcomes and it invents no games. The single real-world ordering
> is reported alongside, labelled as one draw.

## 4. What is reported, per arm

- final balance: **median**, worst 5%, best 5%, and the single real ordering
- **how many of the 2,000 runs went below $50**
- **how many went to zero**
- biggest fall from a peak, median across runs
- worst single game

## 5. ⚠ THE TRAP, AND THE RULE THAT DECIDES A WINNER — FIXED BEFORE ANY NUMBER EXISTS

**After a week one arm will be ahead, and it will probably be an aggressive
one.** That is what aggressive sizing does over short runs: it wins bigger when
it wins. Judging on final balance alone would therefore "discover" that betting
everything is best, on data that cannot support it.

**An arm counts as better only if ALL THREE hold:**

1. its **median** final balance across 2,000 orderings is higher, **and**
2. **zero** of the 2,000 orderings went below $50, **and**
3. its biggest fall from a peak is **smaller than its final gain**.

**Pre-registered prediction, as a number so it can be wrong:** `flat-5` and
`kelly-half` clear all three. `half` and `all-in` fail condition 2 in **more
than half** of the 2,000 orderings. `all-in` reaches zero in **over 90%** of
them, because on a near-coin-flip market a single loss ends it.

**And the arithmetic that says so in advance:** the picks average about a 52-cent
buy price and win about 63 times in 100 so far. An `all-in` arm survives *n*
bets only if it wins all *n*. At 63 in 100 that is 63% after one bet, 25% after
three, **1% after ten**.

## 6. What this test CANNOT show

- **Whether any pick is good.** It replays picks whose value is already in doubt
  — `starter` is buying behind the closing sharp line. **If the edge is
  negative, every arm loses and the aggressive ones lose faster.** That is a
  result about sizing, not a rescue of the signal.
- **Anything about a different win rate.** Every number here inherits the 63-in-100
  observed so far, which rests on 30 games and is not established.
- **Real fills.** These are replays at recorded prices; a bigger stake in real
  life would move the price and the book may not hold it. **`flat-20`, `half`
  and `all-in` would frequently exceed the size actually shown at the touch.**

## 7. Guards

| guard | how |
|---|---|
| paper only | replays a database; no venue call, no order path. `tests/test_paper_only.py` covers the whole package |
| exact fees | `common/kalshi_fees.py`, never re-implemented |
| never the mid | replays the recorded executable entry price |
| no look-ahead | the stake is computed from the balance **before** the outcome is applied |
| bust is real | an arm below one contract stops and is reported as bust |
| the known result is stated first | §1, above the numbers |

## 8. Amendments

*Each entry gets a date, a reason, and what it changed. The text above is never
edited.*

### A1 — 2026-08-12. First run. Two of §5's predictions were WRONG and are recorded here.

73 settled picks from `starter__hold` + `early__hold`, 42 won (58 out of 100),
average buy price 50.5¢, 2,000 orderings per arm.

| arm | median final | <$50 | to zero | biggest fall | rule |
|---|---|---|---|---|---|
| `flat-5` | **$405.59** | 0.0% | 0.0% | $74 | **PASS** |
| `flat-5-comp` | **$419.67** | 0.0% | 0.0% | $103 | **PASS** |
| `flat-20` | **$572.04** | 7.0% | 0.0% | $755 | fail |
| `half` | **$1.92** | 100% | 0.0% | $688 | fail |
| `all-in` | **$0.24** | 100% | 2.2% | $439 | fail |
| `kelly` | $293.82 | 6.3% | 0.0% | $449 | fail |
| `kelly-half` | $364.11 | 0.0% | 0.0% | $196 | fail |

**WRONG PREDICTION 1.** §5 said *"`flat-5` and `kelly-half` clear all three."*
`flat-5` did. **`kelly-half` did NOT** — it fails condition 3, because its
biggest fall ($196) exceeds its final gain ($114). The prediction was right
about it being safe (0% below $50) and wrong about it clearing the bar.

**WRONG PREDICTION 2, and badly.** §5 said *"`all-in` reaches zero in over 90%
of orderings."* Measured: **2.2%.**

> **Why, and it is a real mechanism rather than a bug.** Contracts are integers.
> `all-in` stakes the whole balance but can only buy `floor(balance / price)`
> contracts, so **the remainder always stays behind.** After a loss the arm is
> not at zero, it is at the change. It therefore *decays* rather than dying —
> median **$0.24 from $250, a 99.9% loss** — and only reaches literal zero when
> the change itself cannot buy one contract.
>
> **The prediction was wrong and the conclusion it was serving is unchanged, in
> fact strengthened.** "Reaches zero 2.2% of the time" sounds survivable;
> "ends with 24 cents of a $250 stake" is not. I would rather have this
> recorded than quietly restated.

**The one that matters for him.** `flat-20` finishes **highest of all seven** at
$572 and **fails the rule** — 7% of orderings dipped under $50 and its worst
fall was $755, more than twice its gain. **This is exactly the trap §5 was
written to catch, and it fired on the first run.** Judging on final balance
alone would have crowned it.

**No gate, threshold, bar or rule was changed by this amendment.** §5's
three-condition test was fixed before any number existed and is applied here
unmodified, including where it fails an arm I predicted would pass.
