# PARLAYS ON KALSHI — what they are, and what is established

**Opened 2026-09-14 at his request.** He asked to go deep on parlays and said
he would be away, checking one chat a day. This page is the standing reference
so nothing below gets re-derived or re-argued. **Everything here was verified
against Kalshi on 2026-09-14, not recalled.**

---

## 1. They exist, and they are called COMBOS

`help.kalshi.com/en/articles/13823820-combos`, dated 2026-06-20:

> "Combos allow you to trade custom combinations of events in a single
> position. Each combo is a unique market with its own dedicated order book.
> Combos resolve to the product of the underlying positions, paying out a
> maximum of $1.00 per contract."

**Three properties that decide most questions before they are asked:**

| property | consequence |
|---|---|
| **Priced by Request For Quote**, not from a book — *"the platform sends out a quote request … other participants can respond with a price"* | the price is a dealer's quote. There is no market price to compare against, only what somebody paid |
| ***"Fills are not guaranteed."*** If nobody answers the RFQ, nothing happens | a strategy can be correct and still never trade |
| ***"Once a combo is placed and filled, it cannot be canceled or reversed."*** | **there is no exit, ever.** Every combo is hold-to-settlement by construction. Every exit-rule variant is dead before it starts |

A leg whose player does not play settles **scalar** — it resolves to its last
traded price and the combo pays the product including that fraction. So a combo
is **not** strictly all-or-nothing, and DNP cases must be analysed separately.

## 2. The fee — same rate, charged once instead of many times

`kalshi.com/fee-schedule`, read 2026-09-14, lists **"Combos (excluding
uncorrelated NFL)" at fee multiplier 1** — identical to a normal market — plus
**maker fees at 50% of taker**.

> ⚠ **The PDF at `kalshi.com/docs/kalshi-fee-schedule.pdf` extracts as a
> mangled table and appears to show a multiplier of 2 for combos. That is a
> column misalignment, not a different fee.** The live HTML page is correct.
> Recorded so nobody re-derives the wrong number from the PDF.

Because the fee is quadratic and collapses at the extremes, paying it once on a
low combo price beats paying it on every leg. Computed with
`common/kalshi_fees.py`:

| legs | each | combo price | fee on combo | fee buying legs | saving |
|---|---|---|---|---|---|
| 2 | 70¢ | 49.0¢ | 1.75¢ | 2.94¢ | **1.19¢** |
| 3 | 70¢ | 34.3¢ | 1.58¢ | 4.41¢ | **2.83¢** |
| 4 | 70¢ | 24.0¢ | 1.28¢ | 5.88¢ | **4.60¢** |
| 6 | 70¢ | 11.8¢ | 0.73¢ | 8.82¢ | **8.09¢** |
| 6 | 80¢ | 26.2¢ | 1.35¢ | 6.72¢ | **5.37¢** |
| 6 | 90¢ | 53.1¢ | 1.74¢ | 3.78¢ | **2.04¢** |

**This is the first structural advantage found in this project that is real and
in his favour.** It is also small in absolute terms — see §4.

## 3. ⚠ Stacking MULTIPLIES an edge. It does not remove one.

**His own reading was that the edge "kind of goes away" once you stack. It is
the opposite, and this is the single most important line on this page.**

For an independent combo priced at the product of its legs, the edge ratios
multiply:

| each leg | 2 legs | 4 legs | 6 legs |
|---|---|---|---|
| 2% underpriced | 4.0% | 8.2% | **12.6%** |
| 3% **over**priced | 5.9% | 11.5% | **16.7%** |

**A parlay is a lever, not a strategy.** It magnifies whatever you already
have, in both directions. **This repo's own measurement is that its legs are
negative at the ask**, so on today's evidence stacking makes the loss bigger,
faster. Ledger `CH074` states the same thing and is `SUGGESTIVE` on **n=1
example** — it has never been measured.

## 4. The number that decides the whole family

The fee saving is wiped out by a very small markup on the quote:

| quoted against a fair 49¢ | you lose |
|---|---|
| 50¢ | 5.5 per 100 risked |
| 51¢ | 7.4 per 100 risked |
| 52¢ | 9.1 per 100 risked |
| 54¢ | 12.5 per 100 risked |

**One cent of markup erases the entire fee advantage of a two-leg combo.** So
the open question is exactly one measurement: **how far above the product of
its legs does the RFQ quote sit?** Never taken here.

## 5. It is measurable offline, free, with no account

Verified 2026-09-14 — `GET /multivariate_event_collections` returns **200
without authentication**, 500+ collections. Settled combos carry their legs,
the price paid, and the result:

```
KXMVESPORTSMULTIGAMEEXTENDED-S20264E1F9411A8E-CAA582F97BC
  6 legs: KXMLBGAME-26AUG171840MIAPHI, KXMLBGAME-26AUG171910SDNYM,
          KXMLBGAME-26AUG172005CWSCHC, KXMLBTOTAL-… +2
  last traded 0.0440   bid 0.0000 / ask 1.0000   result 'no'
```

**`bid 0.00 / ask 1.00` is the normal state for a combo, not a broken quote** —
nothing rests on the book until an RFQ is answered. A recorder that filters for
two-sided quotes will store nothing.

Combo series: `KXMVESPORTSMULTIGAMEEXTENDED` (cross-game — the ones he means) ·
`KXMVECROSSCATEGORY` and `-SHARD1` · `KXMVENFLSINGLEGAME` ·
`KXMVENBASINGLEGAME` (same-game).

**⚠ Kalshi's window is ~69 days. Settled combos expire and cannot be recovered.**
Capture was routed to `devig` (mailbox 032) on that basis; analysis to
`factory` (mailbox 013).

## 6. What is already settled, so it is not re-run

- **Covering both sides of a leg** — dead by arithmetic: costs two fees and
  cancels the leg exactly (factory mailbox 009).
- **Exit rules on combos** — impossible; Kalshi does not allow a combo to be
  sold.
- **Kalshi's combinatorial families are enormous and mostly unquotable** —
  `F003` and `M020`: ~9 of 10 open markets belong to two parlay families with
  almost no counterparty. **That is about the standing families, NOT about the
  RFQ combo product**, and does not settle anything here.

## 7. His own evidence, stated honestly

He has placed three or four parlays and three hit. At roughly even odds per
parlay, **three of four happens about 25 times in 100 by luck alone.** He
suspected this himself and said so. It is not evidence either way.
