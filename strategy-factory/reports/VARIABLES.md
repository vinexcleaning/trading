# WHAT COULD MOVE THIS PRICE — every category, written before the strategies

**Mailbox 001, and it is his own method (`CLAUDE.md` §9c step 2):** *"write down
ALL the parameters BEFORE looking at any result... including ones that probably
do not matter. A parameter thought of after seeing a result is a different thing
and must be labelled as such."*

So this file is written **first**, and it is deliberately generous — a variable
listed and then found irrelevant costs a line; a variable thought of after a
result is contamination.

**Anything added to this file after a result exists gets a dated `LATE:` tag.**
There are none yet.

---

## The variables that apply to EVERY family, whatever it is about

Listed once here rather than repeated fourteen times:

- **the spread**, and whether it is wide because the market is uncertain or
  because nobody is quoting
- **depth at the touch, and depth five cents in** — the second is what decides
  whether $500 fits
- **time to settlement**, and whether the family closes at a scheduled instant
  or when an event happens
- **the price itself** — the fee is quadratic, so a rule that loses money at
  50 cents can make money at 95, and this repo has quoted the 50-cent bar at
  extreme prices before
- **whether the series charges makers** (130 of 13,133 do)
- **how many markets the family lists at once**, because a 40-strike ladder is
  one event and not 40 observations
- **who publishes the settlement number, and when they publish it**
- **whether the family is one market or a mutually-exclusive SET** — the set
  case has an arithmetic constraint the single case does not

---

## Sports — 920 families, 25,282 two-sided markets, settles in hours to days

`bot-hunt` records baseball, tennis, esports and South American football. It
records **no American football at all**, and `KXNFLSPREAD` (793 two-sided) and
`KXNFLTOTAL` (608) are among the largest two-sided families on the exchange.

- the spread number itself, and whether it is a whole number or a half
- **the relationship between the spread ladder and the plain who-wins market** —
  a team favoured by 7 must win at least as often as it covers −7
- injury and lineup news, and what time of day it lands
- rest days, travel, whether a team is already eliminated or already through
- college versus professional — different quoting, different retail interest
- weather at outdoor venues
- the day of week and kickoff time, because the audience differs
- how long before kickoff the market opened

## Elections — 593 families, 9,995 two-sided, settles in months

The **largest** two-sided family on the whole exchange is `KXMIDTERMMOV`, margin
of victory, at 3,687.

- **the margin ladder against the winner market on the same race** — P(margin
  above zero) and P(win) are the same event described twice
- turnout markets against margin markets on the same race
- incumbency, and whether the seat is open
- primary results as they land
- redistricting
- how far out the market opened, and how much it moves per week
- national polling versus that specific district

## Financials — 486 families, 6,712 two-sided, settles in hours to days

- the underlying index level, which is public and free
- **the strike ladder's internal consistency**, which is arithmetic
- time of day: open, lunch, close, after-hours
- whether the day carries a scheduled release
- the previous close and the overnight gap
- how the ladder is spaced near the money versus in the wings

## Entertainment — 308 families, 4,422 two-sided, settles in weeks to months

- **whether the candidate list is CLOSED** — "who headlines Coachella" is a
  named short list, and a closed list of mutually exclusive outcomes must sum
  to a dollar
- whether an "anyone else" contract exists, because without one the sum can
  legitimately fall short
- for Rotten Tomatoes families: the number of reviews counted so far, and that
  the score is publicly visible before settlement
- release dates, and whether they move
- streaming-count families settle on a data vendor, not on the artist

## Economics — 240 families, 2,502 two-sided, settles in weeks to months

- the scheduled release instant, which is published far in advance
- the consensus forecast, and whether it is free to get
- revisions to the previous print
- **the settlement timer** — the market object carries
  `settlement_timer_seconds`, so the market stays open briefly after the number
  exists
- the ladder around the consensus, and how it is spaced

## Politics — 478 families, 1,967 two-sided, settles in weeks to months

- **whether the field is OPEN** — "who will Trump pardon" has no closed list, so
  the candidates should sum to LESS than a dollar, and a sum above one is a lock
- who the settlement source is: several of these settle on named news outlets
  rather than on an official record
- scheduled events (hearings, filings) versus unscheduled ones
- how many named candidates the family lists, and whether that changes

## Commodities — 37 families, 627 two-sided, settles in days to weeks

- **`KXGOLDH` and `KXSILVERH` settle HOURLY on Pyth** — a free public price feed,
  and among the fastest-settling families outside crypto
- the underlying spot, which is free
- the hour of day and whether the relevant market is open
- inventory and OPEC announcements for oil
- the strike ladder spacing relative to the hour's realised move

## Climate and Weather — 100 families, 541 two-sided, settles same day

The fastest settling category after crypto, and the model is public.

- the forecast, which is free from the same agency that settles the market
- the time of day the reading is taken
- how much the forecast has already moved today
- city, season, and whether the strike sits near the forecast or in the wings
- the ladder's completeness — these are bracket sets and must sum to a dollar

## Mentions — 30 families, 510 two-sided, settles in days to weeks

- **all of a family's risk resolves inside one short window** — a speech, a
  press conference — and nothing should move before it
- most words are never said, so most of these are longshots
- the words are **correlated**: one speech drives every market in the family,
  so they are one observation and not thirty
- whether a transcript is published, and how fast
- scheduled appearances versus unscheduled ones

## Companies — 36 families, 362 two-sided, settles in weeks to months

- the scheduled earnings date
- these settle on a data vendor (`Fiscal.ai`), not on the filing
- the ladder around the reported figure
- guidance from the previous quarter
- whether the metric is one the company reports directly or one derived

## Science and Technology — 127 families, 761 two-sided, settles in months

- award families are **closed candidate lists** and should sum to a dollar
- `KXH200MON` and `KXB200MAX` are GPU prices, settling on a vendor
- announcement calendars, which are public
- for outbreak families: which health agency settles it, and how fast they
  publish

## Unclassified — 2 families, 107 two-sided

`KXMLBWINS`, baseball season win totals, has no series row at all and 106
two-sided markets.

- **wins across all teams are CONSERVED** — every game produces exactly one win,
  so the expected wins implied by all thirty teams' ladders is pinned to a fixed
  total. That is an arithmetic constraint, not a forecast
- how far into the season it is
- trades and injuries
- whether a team is selling off

## World, Social — 5 families, 5 two-sided markets between them

**Nothing to test, and the reason is written rather than assumed:** five
two-sided markets in total across both categories. A forward test needs 100
settled units to be judged. These cannot produce an answer at any speed, so they
carry no quota and no spec. **They are re-measured on every rebuild and can come
back.**

## Exotics — 2 families, 701,056 markets, 16 two-sided

**Not tested, and the reason is the whole point:** 90% of the exchange's open
markets, and sixteen of them have a counterparty. Dropped from the recorder by
measurement and by name. `TIERS.md` names them with their counts.
