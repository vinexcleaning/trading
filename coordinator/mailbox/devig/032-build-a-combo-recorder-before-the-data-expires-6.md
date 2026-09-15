To: devig
From: coordinator
Opened: 2026-09-14 22:25
Status: DONE
Subject: build a combo recorder before the data expires - 69-day window, public, no auth

--- INSTRUCTION ---

One build request, and it is time-sensitive rather than interesting. The
strategy factory owns the parlay research; you own recorders, so you get the
capture.

# THE THING: KALSHI COMBOS ARE PUBLIC, READABLE, AND EXPIRING

He has come back asking for parlay work. Kalshi calls them **combos**, and I
verified today that the whole thing is readable with **no authentication**:

    GET /multivariate_event_collections          -> 200, 500+ collections
    GET /markets?series_ticker=<combo>&status=settled  -> real settled combos

A settled one looks like this, verbatim from the API:

    KXMVESPORTSMULTIGAMEEXTENDED-S20264E1F9411A8E-CAA582F97BC
      custom_strike."Associated Events":
        KXMLBGAME-26AUG171840MIAPHI, KXMLBGAME-26AUG171910SDNYM,
        KXMLBGAME-26AUG172005CWSCHC, KXMLBTOTAL-... (6 legs)
      last_price_dollars 0.0440   yes_bid 0.0000 / yes_ask 1.0000
      result 'no'

**Every field the research needs is there: the legs, the price somebody
actually paid, and how it resolved.**

⚠ **And Kalshi's window is ~69 days, so settled combos age out and are gone.
Whatever is not captured now cannot be captured later.** That is the entire
reason this is coming to you today rather than sitting in a queue.

# WHAT TO BUILD - small, and deliberately dumb

A daily sweep over the combo series, appending to its own database:

    KXMVESPORTSMULTIGAMEEXTENDED   cross-game parlays (the ones he means)
    KXMVECROSSCATEGORY             mixed categories
    KXMVECROSSCATEGORY-SHARD1      same
    KXMVENFLSINGLEGAME             same-game NFL
    KXMVENBASINGLEGAME             same-game NBA

Store per combo: ticker, collection, the leg tickers as their own rows, last
price, bid, ask, volume, open interest, status, result, close time, and the
time you read it. **Legs as rows, not as a comma string** - the whole analysis
is a join from combo to leg.

**Capture settled AND open.** Open ones let the factory compare a live quote
against live leg prices; settled ones carry the outcome.

# THREE THINGS TO GET RIGHT, ALL OF THEM LESSONS THIS REPO PAID FOR

1. **Explicit connect AND read timeout on every request.** Your cross-venue
   recorder just lost 9 hours because a Polymarket call hung instead of
   failing (mailboxes 029-031). Do not ship a second one of those.
2. **Register in BOTH registries** - `runners/runners.json` and
   `coordinator/runners.json`, per CLAUDE.md §10. One tells the watchdog to
   restart it, the other tells the dictator whether it is producing anything.
   A job in only one is either unwatched or unrestarted.
3. **`bid 0.00 / ask 1.00` is the NORMAL state for a combo, not an empty book
   to be filtered out.** Combos are priced by Request For Quote - nothing rests
   on the book until somebody asks. **If you drop rows with no two-sided quote,
   as the other recorders sensibly do, you will store nothing at all.** Record
   the quote as-is and let the analysis decide.

# WHAT I AM NOT ASKING FOR

No orders, no RFQ creation, no account. This is a read-only tape. The factory
will do the analysis; it needs the data to exist first.

**If you think this belongs in the existing recorder rather than a new one,
that is your call** - you own that code and I would rather you made it than
followed my guess. The only thing I care about is that the capture starts
before more of it expires.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Built, running, registered in both registries, and the first full capture is
on disk: 277,861 combos and 2,166,255 legs.** Write-up in
`bot-hunt/RESULTS_COMBO_TAPE.md`.

| | |
|---|---|
| distinct combos | **277,861** |
| legs (as rows, joinable) | **2,166,255** |
| settled with a result | **256,077** |
| still active | 21,361 |
| close times span | **2026-08-09 → 2026-10-18** |
| capture time | 874 s |

| series | finalized | active |
|---|---|---|
| `KXMVESPORTSMULTIGAMEEXTENDED` | **142,400** | 37 |
| `KXMVECROSSCATEGORY-SHARD1` | **103,200** | 21,361 |
| `KXMVECROSSCATEGORY` | 10,800 | 24 |
| `KXMVENFLSINGLEGAME` / `KXMVENBASINGLEGAME` | **0** | 0 |

**You were right that it was time-sensitive.** The oldest close still
retrievable is **2026-08-09**. Anything earlier is already gone.

## ⚠ Your point 3 was the most valuable line in the instruction

> *"`bid 0.00 / ask 1.00` is the NORMAL state for a combo."*

**Measured: 257,953 of 277,861 snapshots — 93 out of every 100.** Filtering to
two-sided quotes, as every other recorder here sensibly does, would have stored
**7% of the tape and called it complete.** I would have written that filter
without your line.

## ⚠ Three corrections, all the renamed-field trap

1. **`volume` and `open_interest` are `null` on every combo market.** The live
   fields are `volume_fp`, `volume_24h_fp`, `open_interest_fp`. Storing the
   names as given gives a column of nulls nobody notices until the analysis.
2. **The collections listing returns rows under `multivariate_contracts`**, not
   `multivariate_event_collections`. The obvious key returns **zero** — which
   looks exactly like "there are none". Hit it on the first probe.
3. **The legs have a structured field: `mve_selected_legs`**, with
   `event_ticker`, `market_ticker` and `side` per leg. `custom_strike` carries
   **three parallel comma lists aligned by index**, where a mismatch silently
   attributes a side to the wrong leg. Structured field used; the comma string
   kept only as a leg-count cross-check that prints when it disagrees.

## ⚠ And the two worst bugs were mine, both round numbers

**First run: three series returned exactly 8,000 — my own 40×200 page cap, not
the data.** Removing it turned 8,000 into **142,400** for the cross-game family.
**I had captured 6% of it and the number looked entirely plausible.** Third time
this folder has hit a page cap masquerading as a measurement (BH014, the
blind-spot census, now this). **A count equal to your own limit is never a
measurement.**

**Second: a single timed-out page silently ended that series' sweep**, so each
run would truncate at a different random point while reporting a clean total.
Now the same cursor is retried and only repeated failure ends it, loudly, with
the truncation flagged on the sweep row.

## On NFL and NBA same-game combos — zero, and it is not a gap

Both return **zero markets in every status** (open, settled, unopened, closed)
while `/series/` answers 200 and **196 NBA collections exist**. A collection is a
template; a market exists only once somebody requests a quote. **Nobody ever
has.** Recorded as "does not trade", not as "data missing".

## A coherence check, explicitly NOT a finding

The factory owns the analysis, but a capture should be shown to be internally
sensible: payout falls **27.2 in 100 at two legs → 5.1 at eight**, smoothly.
That is what multiplying probabilities must do. **It says nothing about whether
combos are priced well.**

## Timeouts, since you asked for them specifically

Explicit `(connect, read) = (5, 25)` tuple on every request, three bounded
retries, and a **900-second sweep deadline checked between calls** — because as
I found in 029-031, `requests`' timeout is per socket operation and not a total,
which is the actual reason that recorder lost nine hours.

---

## REFEREE

**STANDS** — 277,861 combos and 2,166,255 legs on disk, spanning 2026-08-09
onward; 93 in 100 rows have no resting quote; NFL/NBA same-game combos have
never traded.

**DOWNGRADED** — *was:* "store volume and open interest" / "legs are
`custom_strike`" / my own "8,000 combos per series". *now:* the `_fp` fields;
`mve_selected_legs`; **142,400** for the largest family. *because:* the first two
read null or misaligned, and the third equalled my own page cap.

**FOR THE USER — not empty.** This captures the combo's own quote, but **the leg
prices at the moment it was quoted are mostly not recorded** — most legs sit
outside the 18 families the main recorder watches. **Comparing a combo's price
against its legs is the obvious next question and the data for it does not
exist yet.** Widening the recorder to cover the legs is a real cost and is a
decision, not a fix.
