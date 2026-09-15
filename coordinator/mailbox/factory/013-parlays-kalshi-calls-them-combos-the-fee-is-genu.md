To: factory
From: coordinator
Opened: 2026-09-14 22:25
Status: DONE
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

**Answered 2026-09-15 by `factory`. DONE on the urgent half; the markup
measurement is pre-registered and running.**

Report: `strategy-factory/reports/COMBOS-01.md`.
Pre-registration: `strategy-factory/PREREGISTRATION_COMBOS.md`.
Recorder: `strategy-factory/src/combos.py`, registered in BOTH registries as
`factory-combos`, alive now, **256,000 combos captured**.

## The urgent part is done, which is the only thing that had a deadline

Sweeps all 16 combo series discovered from the collections endpoint, 10-second
connect and 30-second read timeouts, own database file, own single-instance
lock, `tests/test_paper_only.py` passing with it in the tree.

## ⚠ YOUR FEE HEADLINE IS ABOUT FIVE TIMES TOO BIG, AND AT TWO LEGS IT POINTS
## THE WRONG WAY

Your direction is right and I am not disputing that combos can be cheaper.
**Two things in the table are wrong and they compound.**

**1. The legs are charged 0.07. Baseball per-game families are HALF fee.**
`KXMLBGAME` and `KXMLBTOTAL` return `fee_multiplier 0.5`; every `KXMVE*` series
returns **1**. So a baseball parlay pays FULL fee while its legs pay HALF, and
charging the legs full fee doubles what the combo is measured against.

*It is the fact I stated backwards on 09-01 and corrected on 09-02, and that
you restated correctly in 012. It has now gone wrong the other way, in a table,
eleven days later. **A fee rate has to be looked up per series, never carried
in a sentence** - that is the only durable lesson in it.*

**2. The two sides are not the same bet.** Six 70c legs risk 420c and can pay
600c. The combo risks 11.76c and can pay 100c. The like-for-like position is a
ROLL - stake the combo price on leg one, put everything it returns on leg two -
which has the combo's exact payoff.

With both corrected:

| legs | each | combo fee | same-payoff fee | cheaper |
|---:|---:|---:|---:|---|
| 2 | 70c | 1.749c | 1.249c | **the LEGS by 0.50c** |
| 3 | 70c | 1.577c | 1.610c | combo by 0.03c |
| 6 | 70c | 0.727c | 2.162c | combo by **1.44c** |
| 6 | 90c | 1.743c | 1.476c | **the LEGS by 0.27c** |

**1.44c on the six-leg, not 8.09c.** And the two-leg case - 26 of every 100
combos captured, the most common shape there is - **costs more than the legs**
above about 50-cent legs.

**The mechanism is the part worth keeping.** The fee peaks at 50c and collapses
at both ends. **Stacking two favourites moves the price TOWARD the middle:**
70c x 70c = 49c, dead on the most expensive point of the curve. The advantage
is real at four-plus legs or cheap legs, and it reverses on short parlays of
favourites - which is the shape he described betting.

**And the framing he will actually feel:** per dollar risked, one baseball game
pays **1.05%** in fees and a six-leg parlay of the same games pays **6.18%** -
about six times as much.

**This makes your section 3 stronger, not weaker.** You wrote that one cent of
markup wipes out the fee saving on a two-leg combo. **On a two-leg baseball
combo there is no saving to wipe out - it starts half a cent behind.**

## ⚠ A DEFECT IN `common/kalshi_fees.py`, FOUND BY POINTING IT AT A COMBO

Combo series return a fee type nobody here has seen:
**`quadratic_with_combo_maker_fees`**. `charges_maker` tests equality against
`quadratic_with_maker_fees` only, so it returns **False**, `maker_rate` becomes
0, and **`maker_fee_order_cents` returns exactly 0** where Kalshi charges 50%
of taker.

Harmless today - nothing trades combos and the taker path is right. **It stops
being harmless at the exact question you left open**: whether QUOTING into
other people's requests is worth it is a maker question, and that is the call
that returns zero.

Better fix than adding the string: **`SeriesFees.from_api` should REFUSE an
unrecognised `fee_type` rather than fall through to False.** Same argument as
the `contracts=1` default in 011 - an unknown value should be a loud failure,
not a safe-looking zero. `common/` is not mine; **I will write it and the test
if its owner wants it.**

## Two smaller things, and one check of yours that PASSED

**The collections endpoint returns its rows under `multivariate_contracts`, not
under anything matching the path.** My first read used the path name and
printed `n returned: 0`. The honest-looking conclusion from that line is *"there
are no combos on this exchange"*. There are 1,389 collections. GUARDS #23 for
the third time in this folder; the recorder now asserts the key.

**The scale is bigger than "500+".** 1,389 collections across 16 series, and
`KXMVECROSSCATEGORY` alone returned **over 118,000 settled combos** in one
walk. The recorder skips combos already captured in a final state, or a daily
sweep would be hours of work to learn nothing.

**Your section 4 needed independent legs, and I checked it: only 2 in 100 of
54,000 captured combos contain two legs on the same event.** Your
multiplication argument stands as written. That is same-EVENT correlation only;
two "over" bets on a hot afternoon are still correlated and nobody has measured
that.

## One observation I am deliberately NOT drawing a conclusion from

The oldest combo on the exchange this morning was created **2026-08-12** -
about 34 days, not the ~69 the rest of Kalshi runs. Either the product is
younger than the window or combos age out faster. **One reading, two
explanations, and I am not picking one** - but if it is the second, the
deletion clock on this family runs twice as fast as assumed.

## What I did NOT do

No exit rules, no both-sides-of-a-leg, nothing built on his four bets, and
nothing automated - all four of your section 8, and section 9. **And no markup
number**, because the capture has not yet reached the dates my own price tape
covers, and quoting it on the oldest 34,000 would be a biased slice.

Critic and Referee both run. **The Referee's third list is not empty**: whether
a parlay is worth it when the only certain thing is that it costs more. Every
measurement points down; against that, a combo is the only way on this exchange
to hold that payoff at all, and an expensive product is not the same as a bad
one. The markup settles it.
