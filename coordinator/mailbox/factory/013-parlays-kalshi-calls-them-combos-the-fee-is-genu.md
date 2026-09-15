To: factory
From: coordinator
Opened: 2026-09-14 22:25
Status: OPEN
Subject: PARLAYS: Kalshi calls them combos, the fee is genuinely lower, and stacking MULTIPLIES the edge rather than removing it

--- INSTRUCTION ---

He is back after a week and this is the one thing he asked for. **He will not
be around** - he can read one chat a day and run a command elsewhere. So this
is a long background program, and it is yours.

**Everything below I verified myself today against Kalshi, not from memory.**

# 1. THE PRODUCT EXISTS AND IT IS CALLED A COMBO

Kalshi's own help page (help.kalshi.com/en/articles/13823820-combos, dated
2026-06-20), quoted:

> "Combos allow you to trade custom combinations of events in a single
> position. Each combo is a unique market with its own dedicated order book.
> Combos resolve to the product of the underlying positions, paying out a
> maximum of $1.00 per contract."

**Three facts from that page that shape everything:**

1. **Price comes from an RFQ, not from a book.** *"When you request a combo,
   the platform sends out a quote request to the market and other participants
   can respond with a price."* So the price is a dealer's quote, not a market.
2. **"Fills are not guaranteed. If no market participant responds to the RFQ
   with a quote, the combo order will not fill."**
3. **"Once a combo is placed and filled, it cannot be canceled or reversed."**
   **There is no exit. Ever.** Every combo is hold-to-settlement by
   construction, which kills every exit-rule variant before it starts.

Also: a player who does not play settles **scalar** - the leg resolves to its
last traded price and the combo pays the product including that fraction. So a
combo is not strictly all-or-nothing.

# 2. THE FEE ANSWER, WHICH HE ASKED FOR DIRECTLY - AND IT IS GOOD NEWS

**The live fee page (kalshi.com/fee-schedule, read 2026-09-14) lists
"Combos (excluding uncorrelated NFL)" at fee multiplier 1** - the same rate as
any normal market - **plus maker fees at 50% of taker.**

⚠ **The PDF at kalshi.com/docs/kalshi-fee-schedule.pdf extracts as a mangled
table and appears to show a multiplier of 2 for combos. It is a column
misalignment. The live HTML page is the one to trust; I checked both and am
recording the discrepancy so nobody re-derives the wrong number.**

**So the rate is the same. What changes is the PRICE the rate is charged on** -
one combo price instead of several leg prices - and because the fee is
quadratic and collapses at the extremes, that is a real saving. Computed with
`common/kalshi_fees.py`:

    legs  each   combo   fee on combo   fee buying legs   saving
      2    70c   49.0c       1.75c           2.94c        1.19c
      3    70c   34.3c       1.58c           4.41c        2.83c
      4    70c   24.0c       1.28c           5.88c        4.60c
      6    70c   11.8c       0.73c           8.82c        8.09c
      6    80c   26.2c       1.35c           6.72c        5.37c
      6    90c   53.1c       1.74c           3.78c        2.04c

**A six-leg parlay of 70-cent games pays 0.73 cents of fee where doing it leg
by leg pays 8.82.** That is the first structural advantage this project has
found that is real, is in his favour, and nobody here knew about.

# 3. AND THE REASON IT PROBABLY STILL LOSES - THE NUMBER THAT DECIDES IT

The fee saving is small in absolute terms and the RFQ markup is unmeasured.

    quoted 50c against a fair 49c  ->  lose  5.5 per 100 risked
    quoted 51c against a fair 49c  ->  lose  7.4 per 100 risked
    quoted 52c against a fair 49c  ->  lose  9.1 per 100 risked
    quoted 54c against a fair 49c  ->  lose 12.5 per 100 risked

**One cent of markup wipes out the entire fee saving on a two-leg combo.** So
the whole question is: **how far above the product of its legs does the RFQ
quote sit?** That is a measurement, it has never been taken, and taking it is
this project.

# 4. ⚠ THE THING HE HAS BACKWARDS, AND IT MATTERS MOST

He wrote: *"it's kind of like an edge... but once you stack two games on it,
the edge kind of goes away."*

**It is the opposite. Stacking MULTIPLIES the edge.** If a leg's true chance is
`p` and you pay `q`, the edge ratio is `p/q`. For an independent combo priced
at the product of its legs, the parlay's ratio is `(p1/q1) x (p2/q2) x ...`

    each leg 2% underpriced ->  2 legs = 4.0% underpriced,  6 legs = 12.6%
    each leg 3% OVERpriced  ->  2 legs = 5.9% overpriced,   6 legs = 16.7%

**A parlay is a lever, not a strategy.** It magnifies whatever you already
have. And this repo's own measurement is that its legs are **negative at the
ask** - so on today's evidence, stacking makes it worse, faster. **That is the
honest headline and it should lead the report to him.**

`CH074` says the same thing and was never properly tested: *"a parlay's edge is
the product of its legs' edges"*, SUGGESTIVE, **n=1 example**. Your job is to
turn that one example into a measurement.

# 5. IT IS ALL MEASURABLE OFFLINE, FREE, WITH NO ACCOUNT - I CHECKED

`GET /multivariate_event_collections` returns **200 with no authentication**.
500+ collections. `GET /markets?series_ticker=<combo series>&status=settled`
returns **real settled combos** with their legs and the price someone paid:

    KXMVESPORTSMULTIGAMEEXTENDED-S20264E1F9411A8E-CAA582F97BC
      6 legs: KXMLBGAME-26AUG171840MIAPHI, KXMLBGAME-26AUG171910SDNYM,
              KXMLBGAME-26AUG172005CWSCHC, KXMLBTOTAL-... and 2 more
      last traded 0.0440   bid/ask 0.0000 / 1.0000   result 'no'

    KXMVECROSSCATEGORY-S2026CEDC0FF79EB-D84C5CD337B
      5 legs, last traded 0.0760, result 'no'

**Note bid 0.00 / ask 1.00 on every one.** There is no standing book at all,
exactly as the RFQ design implies. The only price that exists is what somebody
actually paid.

The combo series to sweep: `KXMVESPORTSMULTIGAMEEXTENDED` (cross-game),
`KXMVECROSSCATEGORY` and `-SHARD1` (mixed categories), `KXMVENFLSINGLEGAME`,
`KXMVENBASINGLEGAME` (same-game).

# 6. ⚠ THE URGENT PART: KALSHI'S WINDOW IS ~69 DAYS

**Every settled combo older than about 69 days is gone for good**, like every
other closed market here. **Start capturing before anything else** - a daily
sweep of all combo series, storing ticker, legs, last price, volume, open
interest, result, close time. That is a small recorder and it is the only part
of this that cannot be done later.

**Register it in BOTH `runners/runners.json` and `coordinator/runners.json`**
per CLAUDE.md §10, and give it an explicit connect AND read timeout - the
cross-venue recorder just lost 9 hours to a request that hung instead of
failing (devig mailbox 029-031).

# 7. THE MEASUREMENT, PRE-REGISTERED BEFORE ANY NUMBER

Write `PREREGISTRATION_COMBOS.md` before you compute anything. The core test:

**For every settled combo, compare the price actually paid against the product
of its legs' own prices at that moment.**

    markup = price_paid / (product of the legs' asks at that time)

Legs are ordinary Kalshi markets, so their prices come from the candle API
(~69 days) or from this repo's own tape where the family is recorded.

**State before looking:** what markup would make combos worth trading, and what
would kill them. My suggestion, yours to change: **if the median markup is
above about 3% the family is dead for taking, and the only live question left
is whether QUOTING into other people's RFQs is worth it.**

**Report, beside every number:**
- **the naive benchmark** - what buying the legs separately would have returned
  over the same games
- **how many combos you looked at, and how many distinct games they cover** -
  six combos sharing five games are not six observations
- **the DNP/scalar cases separately** - they are not all-or-nothing and will
  otherwise quietly bias the win rate

# 8. FOUR THINGS NOT TO DO

1. **Do not test exit rules.** Combos cannot be sold. Kalshi says so.
2. **Do not re-test covering both sides of a leg.** Mailbox 009 killed it by
   arithmetic: it costs two fees and cancels the leg exactly.
3. **Do not conclude from his four bets.** He has placed three or four parlays
   and three hit. At roughly even odds per parlay, three of four happens about
   **25 times in 100 by luck alone.** Tell him that plainly - he already
   suspects it and said so himself.
4. **Do not let "the AI picked the games" become the strategy.** If ChatGPT
   picking legs is the edge, that is a testable claim with a pre-registration
   of its own, not an assumption to build on.

# 9. WHAT HE SAID HE WANTS

Automated. The API supports it end to end - `POST /communications/rfqs` creates
an RFQ, `/multivariate_event_collections/.../markets` creates the combo market,
and there are quote endpoints. **Do not build any of that yet.** Nothing gets
automated until the markup is measured and a leg with a real edge exists.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both. Money or out of 100, no statistics words - he is reading
this on a phone once a day.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

