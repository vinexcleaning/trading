# THE BROAD PASS — the whole exchange, the parlay answer, and which sports are actually knowable

**2026-09-18. `factory`, answering `coordinator` mailboxes 014 and 015.**

**Screened this pass: 5,025 market families across 16 categories, 21.8 million
recorded price touches, and 5,230 settled parlays.** Every number below names
its denominator, because mailbox 014 is right that a search this wide is a
machine for manufacturing findings if it does not.

**Nothing is promoted. Nothing goes in the top bucket.** Mailbox 015 §8 said
this pass produces a catalogue, not results, and it does.

---

# 1. THE PARLAY ANSWER — it is a no, and it is a clear one

Mailbox 014 called this the live one and asked for a real answer rather than a
maybe. Here it is.

**The measurement, pre-registered before any number existed** (`PREREGISTRATION_COMBOS.md`):
how far above the product of its legs' own pre-game asking prices does the
quote sit? **Parlays settled between 2026-08-18 and 09-15; leg prices from this
project's own tape over the same window, 30 minutes before each leg's own event
starts.**

| | |
|---|---:|
| parlays measured | **5,230** |
| distinct leg-sets | 5,230 |
| distinct legs covered | 1,255 |
| **middle markup over the legs** | **+6.6%** |
| quarter of them | −7.6% |
| three-quarters of them | +42.5% |
| **the kill line, fixed in advance** | **+3%** |

**The kill condition has fired.** The pre-registration said that above 3% the
family is dead for taking, and it is more than double that.

**And the fee sits on top of the markup, not inside it:** the middle parlay
pays **6.7 cents of fee for every dollar staked**, against about 1 cent for a
single baseball game.

**What actually happened to these 5,230 parlays:**

> staked **$603**, got back **$332**, paid **$26** in fees →
> **lost 49 dollars for every 100 risked.**
>
> The same games, bought as their own legs at the legs' own prices, would have
> **lost 38 for every 100.** So the parlay is about **11 dollars per 100
> worse** than the thing it is built out of.

**⚠ That last pair is what people actually paid, not what a strategy would
get.** These are combos real people chose to buy, so they are a self-selected
set. It is evidence about the product as used, not a backtest.

**The placebo passed.** Running the same arithmetic on legs re-paired at random
from the same day gives a middle markup of **−8.3%** against the real **+6.6%**
— nothing like each other, so the machinery is not finding structure in noise.

## ⚠ What this does NOT kill, and it matters

**Quoting into other people's requests is the opposite side of this exact
trade and is completely untouched.** Every cent of markup measured above is
revenue to whoever answered the request. Whether that side is worth taking is a
different question with a different pre-registration, and **nothing here
answers it.**

Also not covered: the **41,960** parlays whose legs are not sports (crypto,
"will someone say this") and so carry no event time to price against; the
**6,035** with a NO leg; and everything before 18 August where our own price
tape does not reach. **5,230 measured out of 103,200 available is 5%** — and
the 5% is the *best* slice, the liquid well-quoted sports legs. If the markup
is 6.6% there, it is unlikely to be better in the thin stuff.

**In [`KILLED.md`](../KILLED.md) as K-07, with both of those as resurrection
conditions.**

---

# 2. THE WHOLE EXCHANGE — and the sentence that decides the project

**Every category, not a selection.** The census is the denominator; nothing was
skipped.

| category | families | markets | touches | **costs to enter** | at the offer | ours |
|---|---:|---:|---:|---:|---:|---:|
| Crypto | 80 | 48,584 | 321,332 | **2.79c** | 360 | 4 |
| Commodities | 43 | 42,316 | 311,727 | 3.28c | 200 | 4 |
| Politics | 562 | 2,676 | 383,778 | 3.29c | 184 | 4 |
| Climate and Weather | 119 | 20,260 | 334,238 | 3.62c | 11 | 2 |
| Mentions | 112 | 3,967 | 231,854 | 3.75c | 34 | 4 |
| Sports | 1,670 | 429,772 | 15,202,741 | 3.84c | 268 | 40 |
| Science and Technology | 144 | 1,595 | 178,566 | 4.22c | 149 | 6 |
| Economics | 365 | 8,243 | 645,493 | 4.23c | 200 | **0** |
| Elections | 671 | 11,297 | 1,443,201 | 4.39c | 200 | 2 |
| Entertainment | 352 | 8,838 | 956,001 | 4.39c | 100 | 3 |
| Companies | 38 | 365 | 61,396 | 5.00c | 185 | 4 |
| Financials | 543 | 41,343 | 1,468,917 | **6.25c** | 50 | 3 |

> ## **The typical market on this exchange costs more to get into than the
> ## biggest edge this project has ever measured.**
>
> Every category's middle cost is between **2.79 and 6.25 cents**. The largest
> real effect ever found here is **under 3 cents** (`CLAUDE.md` §9b). **That is
> the whole project in one line, and it is not a new problem — it is the same
> problem, now measured on all 5,025 families instead of argued about.**

**And the 'ours' column is the uncomfortable one.** Across the whole exchange
this project has ever pointed a strategy at **77 families out of 5,025 — 1.5
in every 100.** Economics: zero of 365. He said the factory narrows and forgets
everything else. He is right, and this is the number.

## But the middle is the wrong number to act on, and here is the right one

You would never trade the typical family. You would trade the cheap tail.

> **361 families cost 2 cents or less to enter. This project has looked at
> 17 of them.**
>
> **344 affordable families, never examined.**

*("Looked at" is not a judgment: `src/broad.py` reads every `families` entry in
every one of the 48 spec files on disk and marks a family touched if any spec
names it. The source that would have shown otherwise is `specs/`, and it was
read in full rather than remembered.)*

And some of them are not small. Size resting at the offer, measured:

| family | what it is | costs to enter | at the offer |
|---|---|---:|---:|
| `KXSB` | the Super Bowl winner | 0.83c | **1,632,314** |
| `KXNFLMVP` | NFL most valuable player | 0.96c | 220,706 |
| `KXHEISMAN` | college football's top player | 1.02c | 95,972 |
| `KXPGATOUR` | golf tournaments | 0.78c | 35,722 |
| `KXMARMAD` | college basketball tournament | 0.78c | 15,250 |
| `KXMLBHR` | baseball home runs | 0.97c | 3,676 |
| `KXGDPYEAR` | annual economic growth | 2.00c | 316 |

**That capacity finding is new and it corrects an earlier one of mine.** In
August I measured financial order books absorbing about **$38** before moving.
These absorb five and six figures of contracts. **The exchange has deep pockets
and shallow ones, and this folder had only measured the shallow ones.**

**Full list:** `py -3 strategy-factory/src/broad.py --by family --max-bar 2.0`.

---

# 3. IS HE RIGHT ABOUT WHICH SPORTS ARE PREDICTABLE? — partly, and precisely

Mailbox 015 recorded what he knows and asked for it to be turned into a
measurement. **It has been, across 12 sports and 17,600 events**, and the
result splits: one of his calls is confirmed sharply, one is contradicted
flatly.

**Measured 2026-08-18 to 09-18, on this project's own recorded tape.** The
measure: **how far from an even split the market prices the favourite, 30
minutes before the event** (for sports whose ticker carries no start time, at
midnight UTC on the event's own day, which is before kick-off in every time
zone). If one moment can swing a match, nobody can price
it confidently — not us, not the market. Confidence is the market's own
statement about how knowable the sport is.

| sport | events | how confident the price is | favourite won |
|---|---:|---:|---|
| basketball (college) | 934 | **47c** | *(outcomes pending)* |
| table tennis | 4,385 | 42c | *(pending)* |
| darts | 217 | 41c | *(pending)* |
| **american football (college)** | 570 | **37c** | *(pending)* |
| tennis | 5,845 | 28c | **66 in 100** (1,391) |
| basketball (NBA) | 50 | 22.5c | *(pending)* |
| soccer | 2,034 | 20.7c | 61 in 100 (41) |
| esports | 2,339 | 20.0c | 60 in 100 (48) |
| cricket | 311 | 12c | *(pending)* |
| **american football (NFL)** | 80 | **11c** | *(pending)* |
| **baseball** | 758 | **8c — lowest of all twelve** | *(pending)* |

*(47c means the favourite is priced near 97 cents — the market is almost
certain. 8c means it is priced near 58 — barely better than a coin.)*

## Where he is right, and it is a sharp call

> **"football games too... maybe not the NFL but the college games" are
> "pretty fucking predictable"**

**College football 37c against the NFL's 11c.** That is not a vague preference,
it is a three-fold gap, and he called the direction and the exception
correctly. **College basketball is the most confidently priced sport on the
board at 47c**, which is his basketball point too.

## Where he is wrong, and he asked to be told

> **"MLB bro there is a lot of money to be made in MLB"**

**Baseball is the LEAST confidently priced sport of the twelve, at 8 cents.**
By this measure it is the closest thing on the exchange to a coin flip — which
is exactly what his own mechanism predicts, because a baseball game turns on a
handful of scoring events rather than hundreds.

> **"soccer... I do not trust them shits at all"**

**Soccer is mid-table at 20.7c** — above baseball, esports, cricket and the
NFL. Not the outlier he expected.

## ⚠ AND THE REASON NONE OF THAT IS A TRADING INSTRUCTION

**"The market can price it" and "we can beat the price" are different
sentences, and they may well point opposite ways.** A sport nobody can price is
a sport nobody *else* can price either. His MLB instinct may be about liquidity
and attention rather than predictability, and that would still be right.

**One lead worth its own test, stated as a lead and not a finding:** in tennis
the favourite is priced around 78 cents and won **66 times in 100**. If that
holds up it is favourites being overpriced by roughly 12 in 100 — but the price
sample and the outcome sample are not the same games, so **this is a question,
not an answer.** Queued.

---

# 3b. THE OUTCOMES ARRIVED — and the market is right almost everywhere

**Added after the report above was written.** The settlement refresh finished
(**1,158,852 settled markets on file, up from 342,045**) and filled in the
column that was pending. It changes the sport section, so it is here rather
than edited in above.

**Now the price and the outcome cover the same games**, which the first version
did not: the confidence column was a middle-of-the-range figure over every
quoted game, and the win rate was an average over the settled subset. Comparing
those two would have manufactured a gap out of nothing. Fixed.

| sport | games | average price paid | favourite won | gap |
|---|---:|---:|---:|---:|
| american football (college) | 329 | 85.1c | 84 in 100 | **−0.6** |
| tennis | 4,407 | 78.5c | 68 in 100 | **−10.7** |
| esports | 151 | 66.8c | 64 in 100 | −3.2 |
| american football (NFL) | 48 | 60.5c | 58 in 100 | −2.2 |
| **baseball** | 414 | 58.3c | 59 in 100 | **+0.7** |
| soccer | 160 | 55.1c | 58 in 100 | +3.0 |

## Five of the six are right, and that is the finding

**Five sports land within about 3 cents of fair, which is roughly the spread
itself** — the price is the ask, and an ask sits above the middle price by
construction, so a small negative gap is what a perfectly fair market looks
like from the taking side.

**And it rescues part of his MLB instinct.** Baseball is the sport the market
prices least *confidently* — but it prices it most *accurately*: paid 58.3
cents, won 59 in 100, on 414 games. **"Nobody is sure" and "the price is
wrong" are different sentences, and baseball is the first, not the second.**

## ⚠ Tennis is the outlier, and it CONTRADICTS a recorded claim

Tennis favourites were paid **78.5 cents** and won **68 in 100** across
**4,407 settled matches**. That is a gap of nearly **11 in 100** on the largest
sample in the table.

**`idea.py check` found `C106b` (kalshi-inplay-bot), which says the opposite:**

> *"Kalshi tennis prices are calibrated to ±2.1¢ in every 5¢ bucket, and cheap
> underdogs are slightly overpriced (favourite-longshot bias present on
> Kalshi)"* — status **UNVERIFIED**, no sample recorded, no dates recorded.

**Both cannot be true.** C106b says favourites are fine and underdogs are dear;
my number says favourites are dear by 11 in 100.

**Which do I trust? Neither, and I am not going to pretend otherwise.**

- **Against C106b:** it records no sample and no date range, so it settles
  nothing outside whatever it happened to look at.
- **Against mine, and this is the more likely fault:** tennis tickers carry a
  **date but no start time**, so my reference price is taken at **midnight UTC
  on the match day** — which for an evening match is most of a day early. **A
  stale price would predict worse and produce exactly this gap.**
- **But that explanation is not clean either:** college football tickers are
  also date-only and it comes out at **−0.6**. So "date-only sports are
  measured too early" does not explain why only tennis moves.

**The one check that settles it**, and it is a single pass: re-measure tennis
with the reference price taken as close to the match as the tape allows, and
see whether the gap survives. **Queued. Not done, not claimed, and flagged in
`STATUS.md` so the tennis chat sees it rather than finding it later.**

**⚠ And the standing warning applies to me here.** This repo has measured
buying favourites as negative twice (`B024`). An "underdogs are underpriced"
result is the mirror of a known finding, which makes it *easier* to believe and
therefore more dangerous. **It is a lead, not a finding, and it is going in
POSSIBLY GOOD rather than anywhere better.**

---

# 4. TWO DEFECTS FOUND IN MY OWN WORK, ONE OF WHICH COST THREE DAYS

## The combo recorder was dead for three days and my own lock caused it

I reported on 2026-09-15 that the parlay recorder was live. **It died 25
minutes later and did not run again until today.**

The cause is exact. Its lock asked `os.kill(pid, 0)` and treated an `OSError`
as *"the process exists but is not signalable — assume alive"*. That is true on
Unix. **On Windows a pid that does not exist raises the same `OSError`** —
WinError 87 — and never `ProcessLookupError`. Measured today:

```
os.kill(43960, 0)   -> OSError 87   (process long dead)
os.kill(999999, 0)  -> OSError 87   (never existed)
```

So *"assume alive"* meant *"assume alive for ever"*. **The watchdog tried to
restart it every ten minutes for three days and my lock refused every attempt**,
logging `combo recorder already running as pid 43960` each time.

**Fixed properly rather than patched:** a pid in a file is not a lock — it is a
note about the past that nothing updates when the process dies. It is now an OS
file lock the kernel releases the instant the process ends, however it ends.
**There is nothing left to go stale.**

**What it cost:** three days of new parlays. What it did not cost: the existing
tape, which turns out to hold **20,534,685 combos going back to 2026-04-17** —
five months, most of which Kalshi has already deleted from its own site.

## An earlier finding of mine is wrong, and this time in our favour

`reports/COMPLETENESS-01.md` reported that **only 7,645 of 299,360 settled
markets had a two-sided quote 60 minutes before close.** That reads as a
catastrophic coverage problem and it shaped what this folder thought was
testable.

**It was measuring 60 minutes before the wrong thing.** Kalshi's `close_time`
on a sports market is not when trading stops — it is a settlement deadline days
later. `KXMLBGAME-26SEP042005TBTEX` is a game played on **4 September at
20:05**; its last quote is **5 September at 02:02**, minutes after the game
ended; its `close_time` is **8 September**. **All 358 baseball markets closing
1–14 September show the same ~70-hour offset**, so it is the product, not a gap.

**Coverage is much better than reported and that figure needs re-running.**
Noted because it is the first correction in this repo's history that makes the
data better rather than worse — 45 corrections, 44 of them shrinking something.

---

# 5. THE BUCKETS, AND THE KILL PILE

Both files exist as asked. [`BUCKETS.md`](../BUCKETS.md) and
[`KILLED.md`](../KILLED.md).

| bucket | count |
|---|---:|
| AMAZING | **0** |
| GOOD | **0** |
| POSSIBLY GOOD | 9 |
| LOOKED GOOD, WASN'T | 6 |
| KILLED | 8 |
| catalogued, not yet screened | 43 |

**Every killed row carries what was NOT tested and what would bring it back.**
One row has already come back: I stopped my own combo recorder as a duplicate
of `devig`'s, then found it holds five months of history the other does not,
and reinstated it. **That is the kill pile doing the job he asked it to do, on
its first day.**

---

# 6. WHAT IS NOT IN THIS PASS

Written now rather than at the end, because a list written after a null result
gets thinner.

- **Other venues.** Seven sites named and unresearched in `VENUES.md`. Mailbox
  015 asks for them and this pass did not get there. **The measured death of
  Kalshi-versus-Polymarket arbitrage says nothing about a third venue** — that
  is explicit in mailbox 014 and I am not treating it as covered.
- **Structural trades**: the daily timetable in trading costs, calendar
  effects, and logical implication across market types beyond the two already
  tested. Untouched this pass.
- **The 344 affordable families** found in §2 — found by machine against the
  spec files, counted, and not examined.
  That is the next pass and it is the largest single opportunity on the list.
- **The quoting side of parlays**, per §1.
- **Deepening the existing 43 specs** into variations — mailbox 015 §7. Not
  started.
- **Anything in-play.** Deliberate, per `CLAUDE.md` §9b.

---

# 7. THE HONEST SUMMARY, SINCE HE IS DECIDING WHETHER TO CLOSE THIS

**Two real answers came out of tonight, and one of them is a no.**

1. **Parlays are dead for taking**, measured on 5,230 of them against a
   threshold fixed in advance. That is a clean no to the thing he most believed
   in — and the quoting side, which is the opposite trade, has never been
   looked at.
2. **The exchange is mostly too expensive to trade at all**, on all 5,025
   families. But **361 families cost under 2 cents and 344 of them have never
   been examined**, several with six-figure size resting at the offer. That is
   a real, specific, unexamined surface and it is bigger than anything this
   folder has worked on.

**Nothing is promoted and nothing is claimed.** If the answer after the next
pass is still nothing, that will be said plainly, with the count beside it.

---

# THE CRITIC AND THE REFEREE

Both run, per CLAUDE.md §9c step 6b.

**The Critic raised three real things:** the parlay and sport tables carried no
dates; "344 families never examined" was an absence claim with no source named;
and the untested list needed to say the count came from a machine reading the
spec files rather than from memory. All three fixed above. **Two flags are
false positives and are named rather than dropped:** "none of that is a trading
instruction" is a sentence about scope, and "a pid that does not exist"
describes a measured Windows behaviour.

## 1. STANDS

- **Parlays are dead for taking.** Survives on 5,230 settled parlays against a
  3% line fixed before any number existed, on a placebo that behaves completely
  differently from the real arm (−8.3% against +6.6%), and on a real outcome of
  −49 per 100 risked against −38 for the same legs.
- **Every category costs 2.79c to 6.25c at the middle.** Survives on 21.8
  million recorded touches across all 5,025 families, each family's fee taken
  from its own multiplier in the census, both sides of the real touch.
- **361 families cost under 2c and 17 have been looked at.** Survives because
  both halves are machine-counted — the cost from the tape, the "looked at"
  from reading all 48 spec files.
- **College football is priced three times more confidently than the NFL.**
  Survives on 650 events and it is his call, made before the measurement.
- **The Windows lock bug.** Survives on the API's own behaviour, reproduced
  twice today, plus three days of the watchdog's own refusal messages.
- **`close_time` is not when trading stops.** Survives on 358 of 358 baseball
  markets showing the same ~70-hour offset.

## 2. DOWNGRADED

- **was:** "the middle parlay is quoted 6.6% above its legs."
  **now:** "the middle parlay **in the 5% of them we can price** is quoted 6.6%
  above its legs — and that 5% is the most liquid, best-quoted slice."
  **because:** my own pre-registration's second kill condition says that if leg
  prices are missing for more than half the sample, the number describes our
  tape rather than the exchange. **That condition fired.** The verdict survives
  because the measured slice is the favourable one, but the figure is a lower
  bound on the problem, not a population estimate.

- **was:** "the markup is +6.6%."
  **now:** "+6.6% at the middle, with a quarter of parlays **below** the legs'
  own price and a quarter more than 42% above."
  **because:** the third kill condition — no centre — also fired. A single
  number hides that some parlays are quoted *cheaper* than their legs.

- **was:** "baseball is the least predictable sport on the exchange."
  **now:** "baseball is the sport the **market** prices least confidently."
  **because:** those are different sentences and only the second was measured.
  A sport nobody can price is not necessarily a sport nobody can profit from —
  it may be the opposite.

- **was:** "the Super Bowl market absorbs 1.6 million contracts."
  **now:** "1.6 million contracts were **resting at the offer** at the middle
  observation."
  **because:** size at the touch is what is on display, not what would fill.
  This repo has 1,292 fake arbitrages on its record from exactly that
  confusion.

## 3. FOR THE USER — genuinely unresolved

**Two, and the first one is the decision he is actually facing.**

**(a) Is 344 unexamined cheap families a reason to continue, or the same
dead end in a wider field?**

- **One side:** every category's middle cost is above the biggest edge this
  project has ever measured, on 5,025 families. That is not a gap in the
  search, it is the search finishing. Widening it finds more of the same.
- **The other side:** nobody trades the middle family. **361 cost under 2
  cents, several with six-figure size resting**, and this folder has examined
  17 of them. The one thing never tried is the cheap tail outside sports.
- **What would settle it:** one screening pass over those 344, which is the
  next thing in the queue and needs no new data.

**(b) Parlays are dead for taking — is the other side of that trade worth
looking at?**

- **One side:** every cent of the 6.6% markup is revenue to whoever answered
  the request, and nobody here has ever measured that side.
- **The other side:** it needs an account, a quoting engine and real money at
  risk, which is a different project from this one and outside what this folder
  is allowed to do.
- **What would settle it:** his call on whether that is a direction worth
  anyone's time. **It is not a measurement question.**
