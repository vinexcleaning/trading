# RESULTS — the combo tape is captured, and it was bigger than anyone thought

**2026-09-15.** Mailbox 032. **Read-only capture. No orders, no Request For
Quote creation, no account, no credential.** The strategy factory owns the
parlay research; this is the data existing so that research is possible.

---

## 1. What is now on disk

| | |
|---|---|
| **distinct combos** | **277,861** |
| **legs** | **2,166,255** |
| settled with a result | **256,077** |
| still active | 21,361 |
| close times span | **2026-08-09 → 2026-10-18** |
| capture time | 874 seconds |

**By family:**

| series | finalized | active |
|---|---|---|
| `KXMVESPORTSMULTIGAMEEXTENDED` (cross-game) | **142,400** | 37 |
| `KXMVECROSSCATEGORY-SHARD1` | **103,200** | 21,361 |
| `KXMVECROSSCATEGORY` | 10,800 | 24 |
| `KXMVENFLSINGLEGAME` | **0** | 0 |
| `KXMVENBASINGLEGAME` | **0** | 0 |

**It was time-sensitive and the instruction was right about that.** The oldest
close still retrievable is **2026-08-09** — everything that closed before that is
already gone, permanently. A week's delay would have cost a week of the record.

## 2. ⚠ Three corrections to the instruction, all the same shape

**Every one is the renamed-field trap, and every one would have produced a
confident wrong answer rather than an error.**

**1. `volume` and `open_interest` are `null` on every combo market.** The live
fields are `volume_fp`, `volume_24h_fp`, `open_interest_fp`. Storing the names
as given would have written a column of nulls that nobody notices until the
analysis.

**2. The collections listing returns its rows under `multivariate_contracts`,
not `multivariate_event_collections`.** Reading the obvious key returns **zero
collections** — indistinguishable from "there are none". I hit this on the first
probe.

**3. The legs are available as a structured field, not only as a comma string.**
The instruction pointed at `custom_strike."Associated Events"`. There is also
**`mve_selected_legs`**, an array of objects with `event_ticker`,
`market_ticker` and `side`. The comma strings are **three parallel lists aligned
by index** — events, sides, markets — and any mismatch between them is a silent
mis-attribution of a side to the wrong leg. The structured field is used; the
comma string is kept only as a cross-check on the leg count, and the check is
printed when it disagrees.

## 3. ⚠ And the worst bug was mine, twice, and both were round numbers

**First run: three series returned exactly 8,000 combos each.** That is 40 pages
× 200 — **my own page cap, not the data.** Removing it turned 8,000 into
**142,400** for the cross-game family alone: I had captured **6% of it** and the
number looked plausible.

> **A count that exactly equals your own limit is never a measurement.** Same
> failure as BH014 (the recorder probed `mkts[:60]` in an undocumented order) and
> the blind-spot census that returned zero baseball. Third time in this folder.

**Second run: three "HTTP None" lines, each silently ending a series wherever it
happened to be.** A single timed-out page abandoned the rest of that family, so
the sweep would have truncated at a different random point every run while
reporting a clean-looking total. **Now a dropped page retries the same cursor,
and only repeated failure ends the series — loudly, and flagged on the sweep
row.**

## 4. The instruction's point 3 was the most valuable thing in it

> *"`bid 0.00 / ask 1.00` is the NORMAL state for a combo, not an empty book to
> be filtered out."*

**Measured: 257,953 of 277,861 snapshots — 93 out of every 100 — have bid 0 and
ask 100.**

Combos are priced by Request For Quote: nothing rests on the book until somebody
asks. **Every other recorder in this folder sensibly drops rows with no
two-sided quote. Doing that here would have stored 7% of the tape and called it
complete.**

## 5. A coherence check, which is NOT a finding

The factory owns the analysis. But a capture should be shown to be internally
sensible before anyone builds on it, so:

| legs | settled | paid out | rate |
|---|---|---|---|
| 2 | 22,827 | 6,200 | **27.2 in 100** |
| 3 | 31,664 | 6,236 | 19.7 |
| 4 | 32,316 | 4,720 | 14.6 |
| 5 | 28,176 | 3,076 | 10.9 |
| 6 | 24,239 | 1,992 | 8.2 |
| 7 | 19,465 | 1,284 | 6.6 |
| 8 | 17,339 | 888 | **5.1 in 100** |

**The payout rate falls smoothly as legs are added, which is what multiplying
probabilities together must do.** That is a sanity check on the capture, not
evidence about whether combos are priced well. **Nothing here says anything
about whether they are worth trading.**

## 6. What this does NOT capture

- **Any price anybody was actually offered.** 93 in 100 rows have no resting
  quote. `last_price_dollars` is the last trade, which for most combos is
  nothing at all.
- **The leg prices at the moment the combo was quoted.** The join from combo to
  leg exists; the leg's own price history is in `record.db` only for the 18
  families that recorder watches. **Most legs here are outside them.**
- **NFL and NBA same-game combos.** Both series return **zero markets in every
  status**, while 196 NBA *collections* exist. A collection is a template; a
  market only exists once somebody requests a quote. **Nobody ever has.** ⚠ That
  is not "the data is missing" — it is that the thing does not trade.
- **Anything that closed before 2026-08-09.** Gone, and not recoverable.
- **Whether the two venues' combos are comparable.** Not looked at.
