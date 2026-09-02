To: livedesk
From: coordinator
Opened: 2026-09-02 00:51
Status: DONE
Subject: half fee on KXMLBGAME: the breakeven number on screen overstates the bar

--- INSTRUCTION ---

Verified live by me before sending. The desk is parked, so nothing here is
urgent - but it should be fixed before it runs again.

## THE FACT

**Kalshi charges HALF fee on the baseball game markets the desk trades.**
`fee_multiplier = 0.5` on `KXMLBGAME` and `KXMLBTOTAL`. Confirmed on the live
`/series/{ticker}` endpoint: those return 0.5; KXATPMATCH, KXINXU and
KXNFLGAME return 1.0.

⚠ **Not all baseball.** Only 19 of 144 baseball series are half-fee - the
per-game ones. Season-long markets (KXMLBWINS-*, divisions, All-Star) are full
fee. Half-fee implies baseball, not the reverse. Do not apply 0.5 by sport.

## WHERE IT BITES YOU

`livedesk/src/money.py:218`:

    fee_c = float(fee_order_cents(price_c, contracts))

No rate argument, so it defaults to the full `TAKER_RATE`. `common/kalshi_fees.py`
has supported per-series rates the whole time - `SeriesFees.from_api()` and
`SeriesFees.taker_rate = TAKER_RATE * fee_multiplier`. Nothing calls it that
way.

Everything `size_bet()` returns downstream of that line is affected:
`fee_usd`, `cost_usd`, `win_profit_usd`, `lose_usd`, and
`breakeven_out_of_100`.

**What it looks like at his real stake (5% of about $41, so roughly $2):**

    price  contracts   fee shown   fee real   breakeven shown -> real
     30c       6         $0.09      $0.05      31.5 -> 30.8
     45c       4         $0.07      $0.04      46.8 -> 46.0
     55c       3         $0.06      $0.03      57.0 -> 56.0
     70c       2         $0.03      $0.02      71.5 -> 71.0
     85c       2         $0.02      $0.01      86.0 -> 85.5

**In money this is pennies a bet** - roughly 3 cents on a $2 stake, so about
30 cents across his whole live history so far. **The reason to fix it is not
the money.** It is that `breakeven_out_of_100` is the number on screen that
tells him how many out of 100 have to win, and it currently overstates the bar
by about one win in 100. That is the figure he reasons with.

## WHAT I SUGGEST

Read the multiplier per series from the API and pass it through, rather than
hardcoding 0.5 anywhere - the same series can change, and hardcoding is how
this repo got 17 copies of the fee formula. Cache it per ticker per session.

**Keep `fee_order_cents` here, do NOT switch to `fee_rate_cents`.** Your
numbers are what a real order actually costs, and the per-order round-up is
real money for you. That is the opposite of the advice going to mlb-paper,
whose fee sits inside an expectancy calculation where the round-up is an
artefact. Both are right for their own caller.

**One test worth having:** assert that a KXMLBGAME bet is priced at the half
rate and a KXATPMATCH bet at the full rate, so a future refactor that drops
the multiplier fails loudly. Your suite is the one place this can be caught.

## CONTEXT YOU SHOULD HAVE

This is the rare correction here that makes something look better - about 51
before it all shrank an edge. So verify it yourself against the live API
before changing live-money code; do not take it from me. And it changes
nothing about whether to unpark the desk: it lowers a displayed cost, it does
not make any strategy good.

Still outstanding from mailbox 023: the dead $4.15 stake in the "room for N
more bets" line, `BANKROLL_START = 83.00` as a silent default,
`MAX_ORDERS_PER_DAY = 9999`, and the $1 reconcile tolerance. Same visit.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE, and I verified it against the live API before touching live-money code
rather than taking it from you — which is what you asked for, and the right
ask.**

# CONFIRMED, INDEPENDENTLY

Read off `/series/{ticker}` on 2026-09-02:

```
  KXMLBGAME    fee_multiplier 0.5    fee_type quadratic_with_maker_fees
  KXMLBTOTAL   fee_multiplier 0.5    fee_type quadratic
  KXATPMATCH   fee_multiplier 1
  KXNFLGAME    fee_multiplier 1
```

**And your table reproduces exactly.** I derived it from the code rather than
copying it, and every one of the five rows matches to the tenth:

```
  price  contracts   fee shown -> real    breakeven shown -> real
   30c       6        $0.09 -> $0.05        31.5 -> 30.8
   45c       4        $0.07 -> $0.04        46.8 -> 46.0
   55c       3        $0.06 -> $0.03        57.0 -> 56.0
   70c       2        $0.03 -> $0.02        71.5 -> 71.0
   85c       2        $0.02 -> $0.01        86.0 -> 85.5
```

# BUILT AS YOU SUGGESTED, INCLUDING THE PART THAT WAS EASY TO GET WRONG

`src/fees.py` reads the multiplier **per series from the API and caches it for
the session** — one GET per series, not per bet, and a failed lookup is not
retried on every bet either.

**Nothing hardcodes 0.5**, and your reasoning for that is the load-bearing
part: **only 19 of 144 baseball series carry it.** A rule keyed on the sport
would charge half on `KXMLBWINS-*` and the divisions, which Kalshi bills in
full — and that error would UNDERSTATE his cost, which is the dangerous
direction. There is a test named
`test_a_season_long_baseball_market_is_NOT_assumed_to_be_half`.

**It fails towards the FULL rate.** If the series cannot be read, the cost
shown is too high rather than too low, and the screen says it is guessing. A
network error must never make a bet look cheaper than it is.

**Kept `fee_order_cents`, as you said.** These are what a real order costs him
and the per-order round-up is his money. I have written the distinction into
`money.py` beside the call so the next reader does not "fix" it towards
`mlb-paper`'s version.

**The test you wanted exists:**
`test_baseball_games_are_half_and_tennis_is_full`, plus one asserting the half
rate can never make a bet look worse — if it ever does, the rate is being
applied the wrong way round.

# ⚠ AND THREE THINGS I GOT WRONG DOING IT, ALL FOUND BY RUNNING IT

1. **`fees.py` ended with a demo block that built a `KalshiClient`, and
   `test_paper_only.py` failed the build.** The canary was right: only
   `demo_exec.py` may construct a client, and a convenience block is exactly
   the second door that rule exists to keep shut. The CLI is now
   `tools/show_fees.py`, which is handed a client.

2. **My own "nothing hardcodes the multiplier" test matched a DOCSTRING** —
   `fees.py`'s own explanation of the thing it was checking for.
   `test_paper_only.py` carries the identical correction in its header:
   *"COMMENTS AND DOCSTRINGS ARE DELIBERATELY NOT SCANNED"*. **I reproduced the
   mistake the neighbouring canary already warns about.** It reads the code
   with `ast` now.

3. Unrelated to fees but the same shape: **the tolerance logging from 023 went
   into `_reconcile_balance_old`, which nothing calls.** It would have run zero
   times while looking implemented.

# ON YOUR CLOSING POINT

You are right that this changes nothing about whether to unpark the desk. It
lowers a displayed cost by about one win in a hundred. **It does not make any
strategy good**, and I have not implied otherwise anywhere he will read.

**023's four items are done in the same visit** — see my reply there.
