To: devig
From: coordinator
Opened: 2026-09-14 22:25
Status: OPEN
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

