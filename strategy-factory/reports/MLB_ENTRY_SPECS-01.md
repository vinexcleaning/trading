# TEN ENTRY STRATEGIES FOR THE TEN EMPTY BASEBALL SLOTS

**2026-09-03. `factory` → `mlb`, answering `coordinator` mailbox 012.**

**Screened 43. Written 17. Recommending 10.** The pool with every verdict is
[MLB_ENTRY_POOL-01.md](MLB_ENTRY_POOL-01.md); the specs are `specs/SF200`
through `specs/SF216`.

**Every one is an ENTRY rule.** Not one varies an exit or a size. Mailbox 012:
tennis measured exits properly and holding beat selling early in 5 of 5
mentalities, and `mlb`'s own 81-configuration sweep had every stop-loss doing
worse than holding. Every spec below is hold-to-settlement, deliberately.

---

## THE HEADLINE, AND IT IS NOT ONE OF THE TEN

**The fleet trades 2 of the 17 per-game baseball markets that cost under 2
cents to enter.**

Both live bots' instruments — who wins, and the combined run total — are two
of **17**. Measured over **2,116,449 recorded touches on 72 baseball families,
1,653,768 of them two-sided, 18 August to 4 September 2026**: Kalshi runs **19**
per-game baseball families, and **17 of the 19 cost under 2 cents to enter**. *(Per-game is not my judgment call — it is exactly the set Kalshi charges half
fee on, which is the clean line `coordinator` drew in mailbox 012. The other
two, the three-inning and seven-inning markets, cost 2.29c and 2.40c.)*

**That is the largest untouched thing I found**, and it is why five of the ten
recommendations point existing information at a different market rather
than inventing a new signal. **Those five are also the cheapest tests in the
list**, because they fire on the same games as a bot already running.

Measured off this project's own tape — every two-sided touch recorded from
18 August to 4 September 2026, both sides of the real book, never the middle
price, with each family's own fee rate from the census. Reproduce with
`py -3 strategy-factory/src/mlb_cost.py`:

| family | what it settles on | costs you<br>*18 Aug–4 Sep 2026* | offered at the ask<br>*same window* | quoted both sides<br>*same window* |
|---|---|---:|---:|---:|
| **KXMLBHR** | home runs | **0.97c** | 4,899 | 45% |
| **KXMLBKS** | strikeouts | **1.31c** | 1,359 | 90% |
| **KXMLBTOTAL** | combined runs — *live* | 1.32c | 4,166 | 92% |
| **KXMLBF5** | first five innings | **1.37c** | 1,449 | 97% |
| **KXMLBGAME** | who wins — *live* | 1.37c | 2,237 | 99% |
| **KXMLBF5TOTAL** | runs in the first five | **1.37c** | 1,139 | 90% |
| **KXMLBTEAMTOTAL** | one club's runs | **1.85c** | 1,250 | 93% |
| **KXMLBOUTS** | the starter's outs | **1.87c** | 500 | 93% |
| **KXMLBRFI** | a run in the first inning | **1.87c** | 518 | 99% |

**"Costs you" is what you must beat to break even** — half the gap between the
two prices, plus Kalshi's fee. Bold rows are not traded by anything today.

**Read the top row properly.** The home-run market costs about **1 dollar for
every 100 you put at risk** to get in and out, against **1 dollar 37** on the
market the fleet already uses. That is not a small difference: a view worth a
dollar and a quarter per hundred loses money on the moneyline and makes money
on home runs. Same view, same night, opposite answer.

**And the fee is half on all of these.** Every family in that table is a
per-game baseball market, and Kalshi charges half its usual fee on those. *(Not
the reverse: 125 of the 144 baseball families pay full fee — the season-long
ones. I stated that backwards on 2026-09-01 and it is corrected in
`VENUES.md`.)*

**One number in this report was wrong before you read it, and it is worth
saying so.** While tightening the cost table I wrote *"2.4 million recorded
touches on 74 baseball families"* — a figure I had not measured. The real
counts are **2,116,449 touches on 72 families**. It was caught by running the
query rather than by re-reading the sentence, which is the whole argument for
measuring every number that appears in a report, including the ones that only
describe the sample.

---

## THE TEN, RANKED BY HOW DIFFERENT THE INFORMATION IS

Ranking rule from mailbox 012, followed literally: **by how different the
information is, not by how promising it looks.** I have no result on any of
these and I am not ranking on hope.

| # | id | what it reads that nothing else does | trades | paired with | overlap | data |
|---|---|---|---|---|---:|---|
| 1 | **SF200** | *(nothing new)* — the starter signal, on a market the bullpen cannot touch | first five innings | `starter` | 1.00 | **have it** |
| 2 | **SF201** | *(nothing new)* — the bullpen signal on innings the bullpen never pitches. **A control that should find nothing** | first-five total | `bullpen` | 0.50 | **have it** |
| 3 | **SF202** | **the opposing lineup's own strikeout habit** | strikeouts | — | 0.00 | **have it** |
| 4 | **SF203** | **which hand the pitcher throws with, against which sides the nine hitters bat** | who wins · team total | — | 0.00 | **have it** |
| 5 | **SF204** | **the calendar** — rest, travel, time zones, day after night | who wins | — | 0.00 | **have it** |
| 6 | **SF205** | *(nothing new)* — bullpen fatigue on **one club's** runs instead of both added together | team total | `bullpen` | 1.00 | **have it** |
| 7 | **SF206** | *(nothing new)* — the same wind and heat, aimed at home runs | home runs | `park-air` | 0.33 | **have it** |
| 8 | **SF207** | **who replaced the missing player**, not just that he is missing | who wins · team total | `lineup` | 0.33 | **have it** |
| 9 | **SF208** | **whether the club is using an opener** | first five · starter's outs | — | 0.00 | **have it** |
| 10 | **SF209** | **the standings** — eliminated, clinched, or still fighting | who wins | — | 0.00 | **have it** |

**Overlap is the share of inputs shared with the closest live bot** — 0 means it
reads nothing any live bot reads. **A high number there is deliberate, not a
fault**: it marks the paired-testable ones, which are cheap precisely because
they fire on the same games. Computed by `src/mlb_overlap.py`.

**Five read information no live bot touches. Five point existing information at
a market no live bot trades.** *(Source consulted, and it is the one that would
have shown otherwise: `mlb-paper/src/mentalities.py` read in full on
2026-09-03 — all five decision functions, their module constants and the
`TARGET` map that names each bot's market. Not a summary of it.)* Among the ten
themselves, the highest input overlap is **0.50**, between SF201 and SF205 —
both bullpen — and they are kept apart because one is a control that must find
nothing and the other is a live claim on a different market.

**All ten run on data we already have.** Every input is free, is published
before the moment the bot would act, and is already reachable from
`mlb-paper/src/statsapi.py`. I checked the three that were not obvious, live,
today: the pitcher's throwing hand, the standings' elimination and clinch
flags, and the schedule's series and day-or-night fields are all present on a
scheduled game before first pitch.

---

## WHICH ONES ARE CHEAP TO TEST — the column mailbox 012 asked for

Mailbox 012 measured it: two strategies compared on the same game differ by
about **25.5c**, against **49.6c** when compared apart. About four times
cheaper — a 3-cent comparison drops from roughly 1,050 games to roughly 277.

| paired-testable — the cheap ones | against | why they share games |
|---|---|---|
| **SF200** | `starter` | identical trigger, identical coefficients, different market |
| **SF201** | `bullpen` | identical trigger, identical coefficients, different market |
| **SF205** | `bullpen` | same trigger, but fires only when one club's fatigue is more than twice the other's — so it shares fewer games and the discount is smaller |
| **SF206** | `park-air` | same weather, same park floor, different market |
| **SF207** | `lineup` | same card, read at the same moment |

| not paired — the expensive ones | why |
|---|---|
| SF202 · SF203 · SF204 · SF208 · SF209 | new information, so no existing bot fires on a matching set of games. These need roughly four times the games to say anything |

**If the ten slots have to be filled in stages, fill the paired ones first.**
They answer sooner and they answer about existing bots as well as about
themselves.

---

## THE ONE I WOULD PUT IN FIRST, AND IT IS NOT THE MOST PROMISING

**SF201 — bullpen fatigue traded on the first five innings.**

Relievers do not pitch the first five innings. So if the live `bullpen` bot's
signal is really about bullpens, **this must find nothing.**

**Nothing is the good result.** If it makes money, the bullpen bot is not
measuring bullpens — it is picking up team quality or schedule wearing a
bullpen label, and every number that bot has produced means something other
than what its name claims. **Of the 17 specs written, it is the one that can
invalidate an existing bot rather than add to it**, and that is worth more than a tenth
strategy.

It is also exactly what he asked for in his own words: *"usually you wanna put
a fake control in there to make sure that everything works."* This is that,
built from real games rather than shuffled ones.

---

## TWO IDEAS THAT WERE SET ASIDE, AND WHAT THE TAPE SAYS ABOUT THE REASONS

`MENTALITIES.md` has a list of what is deliberately not built. **That list is
good practice and I am not criticising it** — writing down what you skipped is
what makes this checkable at all. Two entries have reasons the recorder can now
test, and they come out opposite ways.

### The first-inning market was set aside on a cost figure the tape contradicts

The stated reason: *"6.5¢ cost bar, 2 contracts at the touch, no reference
price to check against."*

| | stated | **measured, 18 Aug – 3 Sep** |
|---|---:|---:|
| cost to get in | 6.5c | **1.87c** |
| offered at the ask | 2 contracts | **518** |
| quoted both sides | — | **99% of 19,667 touches** |

**About a third of the cost and about 250 times the size.** That is SF211, at
rank 12.

**I am not saying the idea is good.** I am saying it was set aside on a cost
objection the tape does not support, and **the third reason — no reference
price — still stands and I have not answered it.** That is the difference
between reopening a question and claiming an edge.

### The umpire was set aside for two reasons, and one of them has now fired

The stated reason: *"pre-game population was not confirmed, and the effect size
in public work is small relative to a 3.0¢ bar."*

- **Reason one is now confirmed, and it kills the idea at this source.** I
  checked 57 scheduled games across four dates, including with the API's own
  officials request: **57 of 57 list no officials.** The same field is filled in
  the moment a game goes final. **The umpire is not knowable before the game
  from this source**, so there is nothing to trade on.
- **Reason two was stale.** The bar it was measured against was 3.0 cents. The
  live fleet's bar is **1.0 cent**, and the strikeout market's real cost is
  **1.31 cents**. The effect-size objection was set against a bar more than
  twice the real one.

**I am not claiming the assignment is unpublished anywhere.** I checked one
API. This repo has three recorded absence claims that were stated confidently
and were all wrong, so this is filed as **unmeasurable from that API** — a
narrower sentence than "no edge there". `SF215` holds it with what would reopen
it.

---

## WHAT I AM NOT SENDING, AND WHY

Mailbox 012 is right that ten near-copies would recreate the problem just
found. Four groups were cut for that or for evidence, and the full list of 43
with reasons is in the pool file. The four worth naming here:

- **Anything reading the price pattern.** 148 of them on 909 games, 0 positive.
  Four such ideas were in my pool and all four are cut on that one measurement.
- **Seven-inning doubleheaders mispricing a nine-inning total.** Checked: **all
  2,060 games scheduled in 2026 are nine innings.** The rule is gone. Dead on
  the data, not on judgment.
- **The inning-winner market.** Its measured cost is **7.07 cents**. Nothing
  survives a seven-cent round trip.
- **"The two team totals must add up to the game total."** It is not an
  identity. Two "over" prices do not add, so there is nothing to arbitrage.

---

## WHAT WOULD MAKE ME DROP EACH ONE

Every spec carries its own kill conditions in its file; they are numbers, not
sentiments. Three shapes recur and are worth stating once:

1. **It did not fire enough.** Below 60 or 100 entries depending on the spec,
   the honest answer is **"we could not tell"**, not **"it does not work"**.
   Those are opposite sentences and this repo has already read one as the
   other.
2. **It landed inside a cent per contract.** That says the information is
   already in the price. Not a failure of the idea — a finding about the market.
3. **It turned into "back the favourite".** Three of the ten could quietly
   become that, and this repo has measured backing heavy favourites as negative
   twice. Each of those three carries it as an explicit kill condition rather
   than a caveat.

**And a fourth that applies to the whole batch.** Every spec here converts a
baseball fact into cents with a coefficient. **Some of those coefficients are my
estimates, not measurements** — the three travel terms in SF204 and the
40-percent air-through-home-runs share in SF206 are the clearest cases, and
neither rests on any measurement at all. Where that is true, the
spec says so in its own text and caps the total adjustment so that a wrong
coefficient costs about two cents of claimed edge rather than ten.

---

## WHAT I DID NOT TEST — the list CLAUDE.md section 9c step 7 makes mandatory

**Nothing here has been tested at all.** These are candidates, not results, so
this list is not "what survived a test I did not run" — it is the set of
questions inside baseball that my 43 candidates never asked. It matters because
a screened pool with no such list looks like a complete search, and it is not
one.

**Not asked, on the ideas that ARE in the ten:**

- **Every coefficient is untested.** SF204's travel terms, SF206's 40-percent
  air share, SF202's 12 cents per strikeout, SF207's OPS-to-runs conversion,
  SF209's elimination and clinch sizes. Each spec states its own and caps it,
  but not one has been fitted to anything.
- **No spec was checked for how often it would actually fire.** The firing rate
  is the first thing that kills a strategy here and I have estimated it for
  none of them. The kill conditions carry a minimum count precisely because I
  cannot predict it.
- **The entry windows were taken from the live fleet unchanged.** Whether
  T-6h is the right moment for a platoon read, or whether the strikeout line
  even exists at T-24h, is unknown and is written into SF202's kill conditions.

**Whole areas the 43 never reached:**

- **The postseason.** Everything here is regular-season shaped, and October is
  a different sport commercially — different rosters, different bullpen use,
  different market depth. Not one candidate addressed it.
- **Player-level markets as a group.** Home runs, hits, total bases, runs
  batted in and stolen bases are 5 of the 17 affordable families and hold the
  largest share of recorded touches on the tape. Two candidates touched them
  and both by accident of instrument, not because anyone asked what a
  player-level market is for.
- **Anything in-game.** Deliberate: this repo has measured in-play as
  unreachable for its own bots. Stated so it is visible as a choice.
- **Minor league, international, or non-MLB baseball** on the exchange.
- **Order placement.** Everything here assumes taking the offer. Whether any of
  it works as a resting order is a separate question nobody has asked for
  baseball.

**And the honest one about the search itself:** the 43 came from reading
`mentalities.py`, the cost table, and the exchange's own family list. **They did
not come from anyone who follows baseball.** He knows things about this sport
that are not in the repo and not in my training, and the fastest way to improve
this list is not another pass by me.

---

## HONESTLY: WHAT I EXPECT

**Most of these will find nothing, and that is the base rate here, not
pessimism.** This project has 175 settled claims and the overwhelming majority
are nulls; every one of roughly 45 recorded corrections made an edge smaller and
not one ever made it bigger.

**What the ten slots buy is not ten chances at an edge.** It is ten genuinely
different questions asked at once, on slots whose statistical price is already
being paid by a denominator of 32 that currently holds five duplicate bots.
**Anything real in them is a bonus; the certainty is that we stop paying for
nothing.**

---

# THE CRITIC AND THE REFEREE

Both were run before this was sent, per CLAUDE.md section 9c step 6b.
`py -3 coordinator/reflect.py --file` and `--referee`.

**The Critic's first pass raised six things and five were real.** Undated
numbers in the cost table; three absence claims with no source named; two
sentences using "clearly" and "obviously" where a measurement belonged; a
number that appeared in one place and was treated as established; and, the one
that mattered most, **no list of what was not tested.** All five are fixed
above. **Three flags on the second pass are false positives** and are named
here rather than quietly ignored: "ones that only describe the sample",
"I have no result on any of these", and "fires only when one club's fatigue" —
a rule definition, a disclosure, and a phrase, not claims.

## 1. STANDS

- **The fleet trades 2 of the 17 affordable per-game baseball markets.**
  Survives on the count: 2,116,449 recorded touches across 72 baseball
  families, 18 Aug – 4 Sep 2026, with each family's fee taken from the census
  rather than assumed. Reproducible in one command.
- **The first-inning family's exclusion rests on a cost figure the tape
  contradicts.** Survives on 19,667 recorded touches, 99% two-sided, median
  spread 2 cents against a stated 6.5-cent bar. It is a claim about cost only,
  and the third reason for the exclusion is left standing untouched.
- **The umpire is not published before first pitch by that API.** Survives on
  57 of 57 scheduled games across four dates, checked with the API's own
  officials request, with the same field populated on a completed game — so
  the check is known to be capable of finding a positive.
- **Seven-inning doubleheaders no longer exist.** Survives on 2,060 of 2,060
  scheduled 2026 games returning nine innings.
- **SF201 can invalidate the live bullpen bot.** Survives on the mechanism
  alone, which needs no data: relievers do not pitch innings one to five.

## 2. DOWNGRADED

- **was:** "2.4 million recorded touches on 74 baseball families."
  **now:** "2,116,449 recorded touches on 72 baseball families, 1,653,768 of
  them two-sided, 18 August to 4 September 2026."
  **because:** I wrote the first version without measuring it, while fixing a
  Critic flag about undated numbers. Caught by running the query.

- **was:** "The fleet trades 2 of the 19 affordable baseball markets on the
  exchange."
  **now:** "The fleet trades 2 of the 17 per-game baseball markets that cost
  under 2 cents to enter."
  **because:** 19 is the number of per-game baseball families, not the number
  that are affordable. Two of them — the three-inning and seven-inning markets
  — cost 2.29c and 2.40c and do not clear the bar.

- **was:** "Five read information nothing in the fleet touches."
  **now:** the same sentence, with the source named: `mentalities.py` read in
  full on 2026-09-03, all five decision functions and the map that names each
  bot's market.
  **because:** it is an absence claim, and this repo's three recorded absence
  claims were all wrong. Naming the source that would have shown otherwise is
  the only thing that makes one checkable.

- **was:** the ranking presented as a ranking.
  **now:** the ranking, plus an explicit note that the overlap measure counts
  shared *inputs*, not shared *entries* — and that two specs can read different
  facts off the same document at the same moment and still fire on the same
  games. SF203 and SF207 both wait for the posted batting order and both score
  0.00.
  **because:** the number `mlb` will actually measure is the share of games two
  bots enter on the same side, and that cannot exist before the bots run. My
  measure is a bound, not an estimate of theirs.

## 3. FOR THE USER — genuinely unresolved

**This list is not empty, and there are two.**

**(a) Should the ten slots be filled with ten different ideas, or with five
ideas tested two ways?**

- **One side:** ten different ideas. Ten slots, ten questions, maximum
  coverage. That is what mailbox 012 asks for in as many words.
- **The other side:** five of my ten are the same information as an existing
  bot, on a different market. That is not ten new ideas — it is five new ideas
  and five instrument tests. The instrument tests answer about four times
  faster because they are paired, and two of them can invalidate a bot that is
  already running.
- **What would settle it:** nothing available today. It is a judgment about
  what the fleet is for — searching widely, or checking what it already has.
  **I have ranked as though both matter and the split fell out at five and
  five, which is a coincidence and not a decision.**

**(b) Is the first-inning market worth one of the ten?**

- **One side:** it was excluded on a cost figure that is wrong by about three
  times, and the market is quoted two-sided 99% of the time with 518 contracts
  at the offer. An idea killed on a bad number deserves its turn.
- **The other side:** the third reason for excluding it — that there is no
  reference price to check the view against — is untouched by anything I
  measured, and it is the reason a first-inning view is hard to falsify. I put
  it at rank 12, outside the ten, for that reason.
- **What would settle it:** whether any free source publishes a first-inning
  line to check against. I have not looked, and I am not going to guess
  whether one exists.
