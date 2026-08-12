# Hunting for things we have never tried

**As of 2026-08-11.** Written by the session that owns the social extractors,
on a change of emphasis from the user: *"You're using it right now mainly just
to test stuff that we already know. Use it to find huge strategies. Use it to
find more stuff. Don't only use it just to test or to confirm stuff we already
know."*

He is right about what had been happening. The two best things this reading had
produced — the stop-loss reconciliation and the between-candles hole — were both
**checks on things this repo already believed**. This pass went looking instead.

**Every candidate below was run through `coordinator/idea.py check` against the
638 recorded claims before it was written up.** Where something overlaps
existing work, the overlap is named with its claim ID and the difference is
spelled out. Where `idea.py` showed an idea was NOT new, it was cut — that
happened once and it is recorded at the bottom rather than quietly dropped.

---

## How the queue was built, and why not "find contradictions"

The previous instruction was to rank by *"could contradict a rule we hold"*. I
argued against that and the argument stands: **a queue that hunts for
disagreement will find disagreement whether or not it is there.** Our own stance
lexicon already cannot tell a claim from a quoted claim.

`src/hunt_new.py` ranks instead on four things a rigorous post has and a loud
one does not — **a count bound to a unit** ("4,604 markets", not "up 400%"), a
**cost side** (fees, spread, slippage), a **venue or instrument outside this
repo's recorded work**, and a **named data source** — minus selling language.

That produced **1,873 candidates out of 7,411 that passed the gate**, excluding
the 8 already read.

---

# 1. OUR OWN DATA SUPPLY IS UNDER A SHUTDOWN ORDER

**Rank 1 because it is the only item here with a deadline, and the deadline has
already partly passed.**

**What it claims.** The operator of PMXT posted, in his own name, on
**2026-07-31**: *"I run PMXT. We've been asked to shut down archive.pmxt.dev,
and we'll do so this week."*

**Why this is ours and not a stranger's problem.** `archive.pmxt.dev` is where
`src/pull_kalshi_archive.py` got the Kalshi orderbook data — the 312 hourly
files, 200,626,400 rows, 610 distinct tennis matches, 15–27 May 2026, that this
session rescued and cut from 34.5 GB to 1.21 GB. **Kalshi's own API is a ~69-day
window and closed markets 404 for good.** Anything on that host that we do not
copy is not "re-pullable later"; it is gone.

**Verified by fetching, on 2026-08-11, not by reading the post:**

| check | result |
|---|---|
| `r2kalshi.pmxt.dev` bucket root | 403 — expected, buckets do not list |
| a file we already hold, `2026-05-17T02` | **200, and the first four bytes are `PAR1`** — real parquet, still served |
| the index page `archive.pmxt.dev/Kalshi` | 200, 71 KB, **but it is the app shell** |
| dates outside our window (06-15, 07-01, 04-01, 07-30) | **404** |

**The index is paginated and does not show what we hold.** On 2026-08-11 it
listed **2026-06-09 to 06-11 — 50 hours we do not have**, and mentioned nothing
from the 15–27 May window we do. So neither listing is the inventory.
`src/archive_inventory.py` was written to ask the file host hour by hour with
HEAD requests instead, since that is the only answer that is not guesswork.

**A trap worth recording:** `archive.pmxt.dev` returns **HTTP 200 with a
400-byte body** for URLs that serve nothing. A 200 is not evidence here. This is
the second time on this host that a 200 has meant "no data" — the first cost an
hour and an 18,990-byte file with no magic bytes in it.

**What it would cost to act.** Nothing but disk and a few hours of paced
requests. The existing puller already filters to tennis and discards the raw
file. **This is the cheapest item on the list and the only one that expires.**

**Judgment call, and it is his to overturn, not mine to make quietly:** I have
inventoried but **not** bulk-downloaded beyond our window, because widening the
pull from tennis to everything is a storage decision (34.5 GB raw per 13 days)
and a scope decision, and neither is mine.

---

# 2. A NEW STRATEGY SHAPE: ODDS-SHOPPING OBSCURE SPORTS, PRE-MATCH ONLY

**What it claims.** €30,000 profit in 2022, hobby scale, target €50,000 the
next year. His method in his own words: *"I don't do any trading or live-
betting, I merely calculate pre-match probabilities very accurately and bet
where the odds exceed my calculated probability."* Singles only, **over 99.5% of
the time**, deliberately — because parlays would force him into one bookmaker
and cost him the best price.

**How many observations, over what dates.** A full year, 2022, at a stated
€30,000 net. He does not give a bet count, which is the main weakness. Posted
January 2023, so **the result is three and a half years old**.

**Do they show their working?** Partly. No numbers file, no code — but he
volunteers his losses, his operational mistakes (an extra zero turning a €30 bet
into €300), and the split he attributes success to: *"prediction algorithms are
50% and the rest is determining optimal risk."* No product, no course, nothing
for sale. That is the honest shape.

**Do we have anything on it? No — and this is the genuinely new one.** Every
element runs opposite to what this repo does:

| this repo | him |
|---|---|
| one venue (Kalshi), one price | many bookmakers, shopping for the best price |
| major sports, deep markets | **floorball, beach volleyball** |
| in-play or near-play | strictly pre-match |
| edge from market structure | edge from a better pre-match probability |

The mechanism is plausible and does not need him to be a genius: **a bookmaker
puts far less modelling effort into beach volleyball than into the Premier
League, so its errors there are larger.**

**On whether this is new — and this is an absence claim, so here is what was
actually consulted.** `coordinator/idea.py check` searches 638 recorded claims
across all 7 ledger files plus 58 write-up documents, and it is the thing that
would show a thinly-modelled-sport test if one existed. It returned nothing on
that shape. **Two honest limits on that:** it matches words, not meaning, so a
test written up in different words is invisible to it; and this repo has 23
project folders, of which 7 have no ledger rows at all. So the correct wording
is **"not found in the 638 recorded claims"**, not "never tested".

**What it would cost us to test.** The probability model is the cheap part. The
expensive part is odds history for obscure sports across multiple bookmakers,
and we do not have it.

**And here is the cost side he half-admits, which is probably fatal.** He writes
odds-shopping across many bookmakers *"or, at least I used to, more on this
later..."* — that is the sound of **account limiting**. Bookmakers restrict
winning accounts; that is the standard end of this strategy and it is why
exchanges exist. **This repo trades on an exchange precisely because an exchange
cannot limit you for winning.** So the honest read is: the mechanism is real and
new to us, and the delivery route he used is one we structurally cannot copy.
The version worth thinking about is **whether the same lazily-priced-sport
effect shows up on an exchange**, which is a different question and untested.

---

# 3. A 59,000-MARKET CALIBRATION STUDY WHOSE OWN CONTROL ARM FAILED

**What it claims.** That Polymarket binary contracts priced 30–60 cents are
overpriced by **12 to 24 cents**, and specifically that *"markets in the 40-50%
range resolve Yes only about 22% of the time."*

**How many observations, over what dates.** 59,000 resolved Polymarket binary
markets. No date range given — a real gap. Plus a second dataset of **7.68
million Kalshi markets**, which is far larger than anything this repo holds.

**Do they show their working?** More than most: a pre-registered kill gate, a
multiple-comparison correction across 537 cells, and a Simpson's-paradox check
that caught a composition artifact. **But he states plainly the backtest is
in-sample**, he withholds the tradeable cell map as commercial IP, and he is
weighing a course, data licensing and paid signals. Under our own rubric that is
an honesty deduction on the **results**, not on the tooling.

**Do we have anything on it?** Yes — **C106b**, status UNVERIFIED: *"Kalshi
tennis prices are calibrated to ±2.1¢ in every 5¢ bucket, and cheap underdogs
are slightly overpriced."* His version differs on venue (Polymarket, not
Kalshi), on market family (all categories, not tennis), and on size — he claims
**ten times** the mispricing C106b measured.

**Why I think the headline is an artifact, and the argument is checkable.** A
23-cent mispricing would be the largest ever recorded in any traded market
anywhere. That size alone is the tell, and there is a mechanism that produces it
for free with **no bias existing at all**:

> A single 10-candidate election is published as **10 separate binary markets**.
> Exactly **one** resolves YES. So across "all resolved binary markets" the YES
> rate is 1-in-10 **by construction** — and every one of those ten can sit in the
> 40–50 cent bucket at some point in its life, with nine resolving NO.

He controlled for **category** mix and caught a paradox there. He never says he
collapsed multi-outcome events to **one observation**. That is the same error
this repo already has a rule for — a 10-strike ladder is one temperature
reading, not ten markets.

**And his own control arm came back negative.** He expanded to Kalshi on 7.68
million markets and the gate **failed** — 2 of 10 required cells survived, and
*"a boundary sensitivity check revealed the apparent signal was a
bucket-assignment artifact at the 50-cent line."* He presents that as a kill
gate working, which it is. **It is also an independent stranger, on a dataset
far larger than ours, failing to find favourite-longshot bias on Kalshi.** That
is the part worth keeping: it agrees with C106b's small ±2.1 cents rather than
with his own 12–24 cent headline.

**What it would cost us to test.** Nothing, and it is the useful half. We hold
610 tennis matches of real Kalshi orderbook. Re-running C106b **with
multi-outcome events collapsed to one observation** would either confirm ±2.1
cents or find the artifact in our own numbers. **This upgrades C106b from
UNVERIFIED, which is worth doing regardless of what the stranger claims.**

---

# 4. BUYING NEAR-CERTAIN "NO" ON STRUCTURALLY IMPOSSIBLE MARKETS

**What it claims.** +15% in 60 days on about $4,000, **23 wins from 24 closed
positions**, average hold 17 days. Not forecasting — screening for events that
are *"constitutionally, historically, or institutionally impossible within the
contract window"*, then selling the 4–8 cent YES.

**Do they show their working?** The six-step filter is written out, and the
caveats are volunteered without being asked: 60 days is short, two positions are
underwater, and there is concentration risk. He is not selling anything. That is
a good-faith post.

**Do we have anything on it?** Yes — **SO041**, status SETTLED: *"The market
does not quote a near-certainty. Any strategy shaped 'buy the thing that is 97%
to happen, cheaply' fails on availability, not on price."* Measured on 699
matches of Kalshi soccer.

**How his differs, and this matters.** SO041 killed the shape on **availability
in Kalshi soccer** — the contracts simply were not quoted. He is on **Polymarket
political and institutional markets**, where they demonstrably are quoted: he
traded 24 of them. **So SO041 does not close this**, and saying "we tried that"
here would be exactly the failure mode this repo has a rule against. It is also
adjacent to **B024** and to the $25→$130 run — many small wins, one loss that
eats thirty.

**Why it still fails, on his own numbers rather than on our priors.** At his
stated 4–6% gross margin you are buying at roughly **95 cents**, so you must win
**about 95 times out of 100 just to break even**:

| his stated margin | you are buying at | you must win |
|---|---|---|
| 4% | 96.2 cents | 96.2 out of 100 |
| 5% | 95.2 cents | 95.2 out of 100 |
| 6% | 94.3 cents | 94.3 out of 100 |

He is at 23 out of 24, which is **95.8 out of 100**. But on 24 tries, the true
rate could honestly be anywhere from **79.8 to 99.3 out of 100** — and the
bottom of that range is nowhere near the 95.2 he needs. **The result does not
clear its own break-even bar at the sample size he has.**

The shape of the risk, on his own 24 positions:

| how it goes | result on the whole book |
|---|---|
| 23 win, 1 loses (what happened) | **+0.6%** |
| 22 win, 2 lose | **−3.8%** |
| 21 win, 3 lose | **−8.1%** |
| 20 win, 4 lose | **−12.5%** |

**One more loss and the whole 60 days is negative.** He reports +15% on deployed
capital; on the book it is under a percent, and it is a coin's width from
negative. He is not lying — he is one loss inside the noise.

**What it would cost us to test.** Nothing to check, since the arithmetic
already answers it. **Worth nobody's afternoon as a strategy.** Worth ten
minutes as a written-down example of the shape, because it is the third time
this shape has arrived under a new name.

---

# 5. CROSS-VENUE PRICING ON LONG-DATED SPORTS CONTRACTS

**What it claims.** Nothing yet — it is a methodology question, posted before
any result exists, which is the honest order. The strategy described is *"buy
contracts trading >15¢ below the fair value implied by a blended DK/FD/Pinnacle
book"* on **Kalshi playoff and series-winner markets with a 30–180 day life**.

**Do we have anything on it?** Related but not the same. **C097** is a
consensus-blend result (89% market / 11% weather) that failed its gate, and the
`bot-hunt` de-vig work is on short-dated markets.

**Not found in the 638 recorded claims: any test on contracts with a 30–180 day
life.** The source that would have shown it is `idea.py check` over all 7
ledgers, and it was run. **But this one has a second source that should be
consulted before anyone relies on it** — `bot-hunt` is the largest active
codebase in the repo and owns two pre-registrations, and I have read its ledger
rows, not its code. **A returning `devig` session should confirm this rather
than take my word for it.**

**The two ideas in it that are worth more than the strategy:**

1. **Report the liquidity tax as its own column.** Run the backtest twice —
   once at the midpoint, once replaying actual depth — and publish the gap
   rather than burying it in the headline. On his own numbers the spread is
   **8–12 cents on contracts trading at 25 cents**, which is enough to erase
   anything. This repo reports fills at the real price but does not report the
   *difference* as a number, and that difference is exactly what a hostile
   reader asks for first.
2. **Walk forward by days-to-settlement, not by calendar.** A contract 90 days
   from settlement and the same contract 10 days out are different regimes. Our
   tennis work is already event-time; the long-dated markets are not.

**What it would cost us to test.** The strategy needs sportsbook price history
we do not have. **Idea 1 costs an afternoon and applies to every backtest in the
repo.**

---

# 6. A STRANGER RAN OUR PLACEBO CONTROL, AND IT WORKED

Not a strategy — a method worth stealing, and confirmation that our Step 4 is
the right instinct.

Nine microstructure approaches on **12 months of L2 tick data** (about 648 GB,
Rust, 200+ unit tests). **Every single one came back between 47% and 50%.** The
line that matters: *"Ran a random entry baseline with identical exits → same
performance."*

That is the fake control CLAUDE.md asks for, run by someone with no stake in the
answer, and it did its job — it told him his entry signals were worth nothing
rather than letting him ship them. He also reports **ATR trailing stops
structurally losing at a 27% win rate, the same as random** — which is a third
independent data point on the stop-loss question, on the *uncapped* side of the
split.

**Cost to us: nothing.** It is already how we are told to work. Its value is as
the worked example that the placebo arm catches real failures.

---

# 7. A VENUE CLAIMING A SPREAD TWENTY TIMES TIGHTER THAN KALSHI

**What it claims.** On one NFL game (Bills vs Dolphins, −11.5), a side-by-side of
**SX Bet** against Kalshi: SX Bet's built-in cost **0.24%**, Kalshi's **5.14%**.
If that were general it would matter more than any strategy in this document,
because cost is the bar every result in this repo has to clear.

**How many observations.** **One game, one line, one moment.** He converts both
to a common basis and shows every number, which is more working than most posts
carry — but the sample is one.

**I re-did his arithmetic and it half-holds.** From his own figures, SX Bet's two
sides imply 49.0% and 51.3%, summing to **100.3%** — so about **0.3% built-in
cost**, close to his 0.24%. Kalshi's imply 49.6% and 53.9%, summing to
**103.5%** — about **3.5%**, not the 5.14% he states. **He is comparing Kalshi
after fees against SX Bet before them.** So the gap is real and large, but it is
roughly **12× not 20×**, and it is smaller than he says.

**Do we have anything on it? Nothing on SX Bet in the 640 recorded claims.** But
`idea.py` surfaced something better than a match — a warning.

**K006 is the precedent, and it is one of ours.** *"Depth at the touch collapses
40× toward expiry (158→4 contracts)"* — **status RETRACTED**. The data was **1
market, 3 minutes**. Re-run on 25 markets over 7 hours it was wrong in both
size and direction: depth declined 2.7× not 40×, and never went thin.

**That is exactly this post's shape.** A single snapshot of a single market,
stated as a property of the venue. Our own most instructive retraction came from
that shape, and it shrank on contact with a real sample — as all ~51 have.

**What it would cost to test, and the reason I did not.** A fair comparison
needs the same games sampled repeatedly at the same moments on both venues. What
a one-shot number cannot show is **whether you can get size at that price** — a
0.3% spread on a book two contracts deep is not a 0.3% spread. This repo has
already recorded that edge and liquidity move against each other.

**And there is a gate before any of it:** SX Bet is a crypto venue, and whether
it is lawfully accessible to this user is a question for him, not a thing to
assume from a Reddit post. **Logged, not pursued.**

---

# 8. THE "BEST OF 16 BOTS" POINT, MADE BY A STRANGER WITH BIGGER NUMBERS

Not new — it is CLAUDE.md's own sizing argument — but it is the clearest
statement of it I have seen and it is worth having in the user's own words'
neighbourhood.

His arithmetic: take **50,000 people placing 25 bets each, every one of them
completely clueless, all at a true 50-50**. Then by chance alone about **2,000
finish at 64 wins in 100**, about **500 at 72**, about **75 at 80**, and about
**10 people finish at 88 or better**. *"Those are the guys selling courses."*

**Why it belongs here.** This repo currently runs **16 tennis bots and 16
baseball bots**. The user has already been told, correctly, that the best of 16
will look good even if not one of them has any edge. This is the same point at a
scale that makes it undeniable, and it costs nothing to keep as the standard
answer when a screenshot arrives.

---

# WHAT I CUT, AND WHY

**On-chain Polymarket trade history.** I had this ranked second — a free,
permanent, unkillable trade-level feed from a public blockchain RPC, immune to
the shutdown in item 1. `idea.py check` returned **W017** in `wallet-copy-study`:
*"Polymarket charged no fee for 91% of on-chain history"*, measured **on
on-chain history**. So this repo already reads that chain and I would have
presented existing capability as a discovery. Cut. The tooling named in the
corpus may still be better than ours, but that is a tooling question, not a find.

---

# RANKED, AS ASKED — what I would spend an afternoon on first

| # | what | cost | why this order |
|---|---|---|---|
| 1 | **Finish the archive inventory and pull what we lack** | hours, free | The only item with a deadline. The operator has been asked to shut it down and the data cannot be re-obtained from Kalshi at any price. |
| 2 | **Re-run C106b with multi-outcome events collapsed to one observation** | an afternoon | Uses data we already hold, upgrades a claim from UNVERIFIED, and either finds or clears an artifact in our own numbers. |
| 3 | **Add a liquidity-tax column to backtests** | an afternoon | Applies to every result in the repo, not just this one. |
| 4 | **Thinly-modelled sports on an exchange** | days | Genuinely new to the 638 claims. Needs the exchange version of the question, since his bookmaker route ends in account limiting. |
| 5 | Structural-NO on Polymarket | ten minutes | Answered by arithmetic. Write it down so it is not re-derived a fourth time. |

---

# COUNTS

**Reading, since the count of "13 threads read" was given:** **16 threads read
closely**, out of **7,411 that passed the gate** — not 39,600; the gate discards
25,609 as too thin and 14,115 as off-topic before anything is read.

**What the eight new ones bought:** one live operational warning about our own
data supply, one strategy shape absent from all 640 claims, one artifact
argument against a stranger's headline that also upgrades one of our own claims,
two arithmetic kills, one venue worth a real comparison some day, and two
methods worth copying.

**Two of the eight were killed by our own ledger rather than by me** — the
structural-NO result by arithmetic, and the SX Bet spread claim by **K006**, a
retraction of ours built on the identical one-snapshot shape. That is the ledger
paying for itself, and it is the argument for keeping `idea.py` in the loop on
every candidate rather than only on the ones that feel familiar.

**The data-source sweep returned a null, and it is reported as one.** 73,679
posts and comments scanned for hosts named beside a word meaning *data*, minus
the ones we already use. Ranked by **distinct threads** rather than mentions —
mentions are dominated by spam, with one thread posting a single link 1,441
times. Nothing came back that is both free and new to us. `manifold.markets`
appeared in 6 threads and is the only prediction-market venue named that we do
not touch.

**The absence claim, stated at the strength it actually earns.** Not "there is
no hidden free feed" — **"two sweeps over this corpus did not surface one"**.
The sweeps were: every `http(s)` host appearing beside a data word (1,261
unknown hosts, 294 seen in 2+ threads), and a second pass for **86 data sources
named in prose without a link**, because "the Betfair historical files" has no
URL in it. That second pass is what found the PMXT shutdown in item 1, so it
works. **What would still hide a feed from both:** a source named only in an
image or screenshot, one in the 12,846 comments we hold but on threads we never
collected, and anything on the five platforms we cannot read at all. So the
finding is about **this corpus**, not about the world.
