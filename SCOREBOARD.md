# THE SCOREBOARD — every strategy ever tested, in plain English

**2026-08-06.** One page per market. No jargon. The defect list is in
[AUDIT_2026-08-06.md](AUDIT_2026-08-06.md).

---

## How to read this

**"Profit per contract"** — a contract pays $1.00 (100 cents) if you're right and
nothing if you're wrong. So a contract bought at 40 cents either becomes 100
cents or becomes zero. "Profit per contract" is the average cents you keep after
fees and after paying the real buy/sell prices. **Negative means it loses.**

**"Put $5 in every trade →"** — what $5 becomes on an average trade. It's worked
out from the profit per contract and the price the strategy actually buys at,
and that price is stated for each market. A cheap contract is more dangerous
than it looks: $5 buys twenty 25-cent contracts but only five $1-ish ones, so
the same loss per contract hurts four times as much.

**Verdict:**

| | |
|---|---|
| **WORKS** | makes money after every real cost, and it held up on data it had never seen |
| **DOESN'T** | loses money, and we're confident enough to stop |
| **NOT ENOUGH DATA** | the answer could be anything. Not a null — an unknown |
| 🔴 **FAKE** | positive **only** because the test let it buy at a price nobody could actually get |

**About 🔴 FAKE.** Three ways a test cheated, all found and all listed below:
buying at the "mid" (halfway between the buy and sell price — a price that does
not exist); assuming a resting order always gets filled; and reading a price
after the result was already known. Every FAKE row here has its honest twin
beside it.

---

## THE ONE-SCREEN SUMMARY

| Market | Strategies tested | WORKS | DOESN'T | NOT ENOUGH DATA |
|---|---|---|---|---|
| Tennis — in-play | 8 | **0** | 6 | 2 |
| Tennis — before the match | 6 | **0** | 4 | 2 |
| Crypto | 9 | **0** | 8 | 1 |
| Esports | 12 | **0** | 6 | 6 |
| Baseball (MLB) | 9 | **0** | 6 | 3 |
| Soccer | 2 | **0** | 1 | 1 |
| Weather | 2 | **0** | **2** | 0 |
| Copy trading | 9 | **0** | 7 | 2 |
| Arbitrage | 3 | **0** | 3 | 0 |
| **TOTAL** | **60** | **0** | **43** | **17** |

**Nothing works. Nothing has ever worked.** And the 17 "not enough data" rows
are not hidden winners — they are strategies whose result was so uncertain that
the honest answer is a shrug.

**⚠ UPDATED 2026-08-14. The three that were "genuinely unfinished" are now all
finished, and all three are negative:**

- **Weather, both rows.** The model was out-traded by thirty-year averages
  (**+1.37¢**) and by a model that says 50% to everything and knows nothing
  (**+1.01¢**), against its own **+0.43¢**. When a know-nothing clears your gate,
  the gate is picking cheap prices, not good forecasts. **93 out of every 100
  strikes on offer were priced 95–100 cents against a 46-in-100 win rate.**
- **Crypto market-making.** **−0.85¢ per contract**, and the range of what it
  could really be — **−1.63¢ to −0.19¢** — never touches zero. It loses money
  before adverse selection is even reached.
- **And one new row: the retail-bookmaker de-vig (page 5), dead on day one.**
  A loose bookmaker with **2.25× the margin** of the sharpest book in world
  sport agrees with it to **a fifth of a penny** once each one's margin is
  removed. **0 of 11 games, twice.**

---
---

# PAGE 1 — TENNIS, IN-PLAY

*Betting on a tennis match while it is being played.* Prices here are high —
usually 85 to 97 cents, because by then the favourite is usually winning. **$5
figures assume a 90-cent buy price.**

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Buy & hold** | Buy when the signal fires, then just wait for the match to end | **−2.29¢** | **$4.87** | 995 matches | **DOESN'T** |
| **Random entry** | Buy at random moments. This is the "do nothing clever" benchmark | **−8.28¢** | **$4.54** | 1,525 matches | **DOESN'T** |
| **The v3 bot's actual strategy** | Buy on a price ramp, then use a stop-loss and a profit ladder to exit | **−9.36¢** | **$4.48** | 995 matches | **DOESN'T** |
| **Best of 480 tuned versions** | Every combination of the bot's settings, swept | **−4.90¢** *(best)* | **$4.73** | 480 settings | **DOESN'T** |
| **The set-1 dip trade** | After the favourite's price drops in set one, bet it drops further | **−1.19¢** | **$4.88** | 3,436 matches | **DOESN'T** |
| **Resting orders (honest)** | Post an order and wait for someone to actually come to your price | **−1.30¢ to −2.42¢** | **$4.87 to $4.93** | 13,658 market views | **DOESN'T** |
| 🔴 **Resting orders (optimistic)** | Same, but the test **assumes you always get filled** | **+0.35¢ to +0.58¢** | **$5.02 to $5.03** | same | 🔴 **FAKE** |
| **The live bot, real money** | The actual bot, actually trading, for 39 hours | **−$0.064 per match** | **$4.95** | 108 matches | **NOT ENOUGH DATA** |

## The picture

```
 LOSS per contract          (each block = 1 cent, longer = worse)
   set-1 dip trade          █▎                         −1.19¢
   resting orders, honest   ██▍                        −2.42¢
   buy & hold               ██▎                        −2.29¢
   best of 480 tuned        ████▉                      −4.90¢
   random entry             ████████▎                  −8.28¢
   the v3 bot's strategy    █████████▍                 −9.36¢
   ─────────────────────────────────────────────────────────
   resting orders, FAKE     ▏ +0.58¢   🔴 only if fills are free
```

## The three things worth knowing

**1. The bot did worse than picking moments at random.** −9.36¢ against −8.28¢.
Its cleverness was actively costing money.

**2. The exit rules are what did it.** Buy-and-hold on the exact same signal
loses only 2.29¢. The stop-loss and profit ladder turn a −2.29¢ strategy into a
−9.36¢ one. The stop-loss alone is the single most expensive component — one
test showed the same trades going from **+0.62¢ to −3.77¢** purely by adding an
80-cent stop.

**3. The real money went up, and the bot is not why.** Over the account's life
the hand-placed trades made **+$98.94** and the bot lost **−$6.92**. The famous
"profitable night" turns out to be a cut taken at the highest point of the
equity curve — shuffle the same 108 results into a random order and you reach
that same peak about **85% of the time**. And the winning stretch was a
martingale: buy more as the price falls. It went 7-for-7, then the 8th one cost
more than all seven wins together.

## ⚠️ Never tested on this market

| | |
|---|---|
| **Which player** you're betting on, in-play | Never used. Every in-play strategy here is about the *price pattern*, not the people |
| **Does this specific player come back from a break?** | Tested once, on career-long data — **75% of "comeback ability" is just being a better player overall**. Never tested in-play |
| **Fatigue, time on court, travel** | Never tested |
| **Serve speed, aces, double faults, first-serve %** | **Not available in any free feed we have.** Not a choice — the data isn't there |
| **Surface (clay/hard/grass)** | **Never tested.** Kalshi's records don't say which tournament, so there's no way to look it up backwards |

---
---

# PAGE 2 — TENNIS, BEFORE THE MATCH

*Predicting the winner before play starts.* **$5 figures assume the buy price
stated in each row.**

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **The full player model** | 50 features, 1.5 million historical matches, predicts the winner | *no cents figure — it lost the accuracy contest* | — | 2,645 matches | **DOESN'T** |
| 🔴 **Selective betting (at the mid)** | Only bet where the model most disagrees with the market | **+14% to +25% return** | **$5.72 to $6.23** | 502 matches | 🔴 **FAKE** |
| **Selective betting (real prices)** | The identical trades, at prices you can actually get | **−24% to −31% return** | **$3.46 to $3.79** | 502 matches | **DOESN'T** |
| **Buy everything at the open** | No cleverness at all — buy every match at the opening price | **−4.14¢** *(50¢ buys)* | **$4.59** | 6,519 matches | **DOESN'T** |
| **Buy every longshot** | Buy every cheap contract at the open | **−5.42¢** *(25¢ buys)* | **$3.92** | 6,519 matches | **DOESN'T** |
| 🔴 **Buy the heavy favourite (at the mid)** | Buy anything priced 80¢ or more | **+3.12¢** | **$5.18** | 691 matches | 🔴 **FAKE** |
| **Buy the heavy favourite (real prices)** | Same, at prices you can get | **+0.96¢** then **−0.77¢** on fresh data | **$4.95** | 691 then 261 | **DOESN'T** |
| **Player form / recent results** | 2,008 different combinations of form, rest, workload, experience | *found less than random noise* | — | 6,519 matches | **NOT ENOUGH DATA** |

## The picture

```
 LOSS per contract          (each block = 1 cent)
   heavy favourite, real    ▊                          −0.77¢
   buy everything at open   ████▏                      −4.14¢
   buy every longshot       █████▍                     −5.42¢
   ─────────────────────────────────────────────────────────
   heavy favourite, FAKE    ███▏  +3.12¢   🔴 at a price nobody trades at
   selective betting, FAKE  ~+20% return   🔴 same reason, much bigger
```

## The three things worth knowing

**1. The model is genuinely good, and still loses.** Held-out accuracy is
respectable and it beats a coin flip comfortably. It just doesn't beat the
bookmakers, and the bookmakers are who you're betting against.

**2. "Buy the heavy favourite" looked like the one real edge — and it's an
illusion caused by wide prices.** Split it by how wide the buy/sell gap was:

| how wide the price gap was | apparent edge |
|---|---|
| **2 cents or less (you can actually trade)** | **+1.18 cents — and could easily be zero** |
| 2 to 4 cents | +4.87 cents |
| 4 to 8 cents | +3.50 cents |
| **more than 8 cents** | **+7.92 cents** |

The "edge" gets bigger exactly as the market gets harder to trade, and vanishes
where you could actually take it. **A price quoted in the middle of a 12-cent
gap isn't a price — it's the middle of nothing.**

**3. Where Kalshi tennis is liquid, its price is right across the whole range,
from 1 cent to 99 cents.** Zero of ten price bands showed any deviation.

## ⚠️ Never tested on this market

| | status |
|---|---|
| **Player form / recent results** | **TESTED — and this is the honest caveat.** It found nothing, but only **29 days** of history was available, so the average player appears about **three times**. The correlation between past win rate and result was **+0.006** — basically zero — because there wasn't enough history for form to mean anything. **This is "not shown on 29 days", not "doesn't work."** |
| **Head-to-head** | **BUILT BUT USELESS.** Only **79 of 6,519 matches (1.2%)** had the two players ever having met before, inside the window |
| **Surface — clay, hard, grass** | **NEVER TESTED.** Cannot be done backwards — no way to link Kalshi's records to a tournament. **But surface IS on every upcoming fixture.** Start recording fixtures and this becomes testable in about a month. Cheap |
| **Serve %, aces, double faults, break points** | **NEVER TESTED — not available.** The free feed carries scores only. In the historical archive, serve stats exist on only **4.6%** of lower-tier matches |
| **Rankings** | Available (30,951 players) but not modelled — and rankings are the most public information in tennis, so the price already knows |

> ### 💵 The one thing worth buying, and it's $9.99
> A tennis data provider sells **43 months of point-by-point history, January
> 2023 to July 2026, including the lower tiers**, for **$9.99**. That turns
> "form" and "head-to-head" from noise into real features and lets the whole
> 2,008-test study re-run on three years instead of four weeks. **It is the
> cheapest open question in the entire programme.**

---
---

# PAGE 3 — CRYPTO (Bitcoin / Ethereum price markets)

*Betting on where Bitcoin will be at a set time.* **$5 figures use each row's own
buy price**, which matters enormously here — these are cheap contracts.

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Buy at 5¢, sell at 10¢** | Buy cheap, sell on the bounce | **−2.18¢** | **$2.82** | 250 events | **DOESN'T** |
| **Buy at 10¢, sell at 15¢** | Same idea, less cheap | **−4.32¢** | **$2.84** | 250 events | **DOESN'T** |
| **Buy at 20¢, sell at 25¢** | Same idea again | **−6.03¢** | **$3.49** | 250 events | **DOESN'T** |
| **Buy at 25¢, sell at 30¢** | Same idea again | **−7.25¢** | **$3.55** | 250 events | **DOESN'T** |
| **Buy at 5¢, hold for a 10× move** | Lottery ticket | **+0.87¢** *but could be −0.91¢* | **$5.87** *or* **$4.09** | 250 events | **NOT ENOUGH DATA** |
| **Four forecasting models vs the market price** | Better maths for where Bitcoin lands | *none beat the market. Two tied, two lost* | — | 250 events | **DOESN'T** |
| **Streaks and price paths** | Bet on runs of up or down minutes | *nothing clears the cost* | — | multi-asset | **DOESN'T** |
| **Hold to settlement** | Buy and wait | *negative* | — | — | **DOESN'T** |
| **Market making** | Post buy and sell orders, earn the gap | **not measured** | **—** | **0** | **NOT ENOUGH DATA** |

## The picture

```
 LOSS per contract          (each block = 1 cent)
   buy 5¢ sell 10¢          ██▏                        −2.18¢
   buy 10¢ sell 15¢         ████▎                      −4.32¢
   buy 20¢ sell 25¢         ██████                     −6.03¢
   buy 25¢ sell 30¢         ███████▎                   −7.25¢

 Same losses as a share of YOUR $5 — this is the number that hurts
   buy 5¢ sell 10¢          ███████████████████████████████████████████  −44%
   buy 10¢ sell 15¢         ███████████████████████████████████████████  −43%
   buy 20¢ sell 25¢         ██████████████████████████████               −30%
   buy 25¢ sell 30¢         █████████████████████████████                −29%
```

## The three things worth knowing

**1. The spikes are completely real, and they still lose.** A 10-cent contract
does touch 15 cents within about 7 minutes, **43.8% of the time**. You still
lose money, because the other 56% of the time you're holding something that
expires worthless. That's what a fair price means.

**2. Cheap contracts are a trap, and the numbers above are why.** A 2.18-cent
loss on a 5-cent contract is a **44% loss of your stake**. The fee is largest,
relative to the ticket, exactly where the ticket is cheapest.

**3. The 15-minute Bitcoin markets are structurally dead, not statistically
dead.** On **99.86% of 6,261 markets** the target price is set to exactly where
the last window finished — so every contract is born at a coin flip, which is
the single most expensive point on the fee curve. The round trip is pinned at
about 3.5 cents before you do anything at all.

## ⚠️ Never tested — and one of these is a live open lead

| | status |
|---|---|
| **🟡 Market making — posting orders instead of taking them** | **THE UNFINISHED TEST.** The test rig was built and validated (it correctly reports zero profit on a market designed to have exactly zero). The gap you'd earn is a **full 1.00 cent**, and fees no longer eat it. **The deciding measurement — whether informed traders pick you off faster than 373 milliseconds — was never run.** The project's own verdict section opens with the words "Not yet reached", while the top-level status file lists crypto as closed. **These disagree.** |
| **"0 of 4 series are unprofitable for market making"** | This claim circulates in the handoffs. **Only ONE series was ever actually tested** (58 markets). Three of the four have nothing behind them |
| Order-flow / microstructure | **Impossible with what was recorded** — the recorder saved prices every ~120 seconds, and this lives in the gaps |
| Options-market reference prices | **Ruled out.** The shortest usable option expiry is 54 hours; these markets last 1 hour |

---
---

# PAGE 4 — ESPORTS (Counter-Strike, League of Legends, Valorant)

*Betting on professional video-game matches.* **$5 figures assume a 50-cent buy
price** unless the row says otherwise.

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Random side** | Pick a side at random. The "no cleverness" benchmark | **−6.83¢** | **$4.32** | 2,779 matches | **DOESN'T** |
| **Buy one side of everything** | No selection at all | **−8.68¢** | **$4.13** | 2,779 matches | **DOESN'T** |
| **Buy the heavy favourite (90–95¢)** | Bet on the near-certainties | **−31.63¢** | **$3.28** | 32 matches | **DOESN'T** |
| **Buy the longshot** | Bet on the underdogs | *negative* | — | 2,779 matches | **DOESN'T** |
| **Buy the wider-priced side** | Bet where fewer people are looking | *negative* | — | 2,779 matches | **DOESN'T** |
| **Buy the quieter side** | Bet where volume is lowest | *negative* | — | 2,779 matches | **DOESN'T** |
| **Calibration, 40–50¢ band** | The one price band that came out positive | **+0.13¢** *but could be −7.65¢* | **$5.01** *or* **$4.24** | 152 matches | **NOT ENOUGH DATA** |
| **Follow the price move** | Buy whatever's been rising | **+7.78¢** *but could be −2.02¢* | **$5.78** *or* **$4.80** | 83 matches | **NOT ENOUGH DATA** |
| **Buy the stalest price** | Buy whichever side hasn't moved in 6 hours | **+7.96¢** *but could be −1.25¢* | **$5.80** *or* **$4.88** | 70 matches | **NOT ENOUGH DATA** |
| **Resting orders (passive quoting)** | Post an order 1 cent inside the market and wait | **−1.48¢ to +2.55¢ — the sign flips** | **$4.85 to $5.26** | 81 matches | **NOT ENOUGH DATA** |
| **Copy the sharp bookmaker's price** | Strip the bookmaker's margin, compare, trade the gap | *no profit figure — see below* | — | 13 matches | **NOT ENOUGH DATA** |
| 🔴 **Resting orders (touch counts as a fill)** | Same, but assume you're filled whenever the price merely reaches you | *not reported as a result* | — | 81 matches | 🔴 **FAKE** *(run deliberately, as a check)* |

## The picture

```
 LOSS per contract          (each block = 2 cents)
   random side              ███▍                       −6.83¢
   buy one side of all      ████▎                      −8.68¢
   heavy favourite 90-95¢   ███████████████▊           −31.63¢
   ─────────────────────────────────────────────────────────
 Positive-looking, but the uncertainty range crosses zero on all three:
   stalest price            +7.96¢   ← could be −1.25¢, only 70 matches
   follow the move          +7.78¢   ← could be −2.02¢, only 83 matches
   40-50¢ band              +0.13¢   ← could be −7.65¢, isolated fluke
```

## The three things worth knowing

**1. 260 different versions were tested and none survived.** Of those, 120
looked statistically interesting — **every single one was significantly
negative**. Not one positive result survived.

**2. The cost of trading esports before a match is 3 to 6 times higher than the
number the whole plan was built on.** The original shortlist ranked esports #1
partly on a 1-cent trading cost. That was measured at the busiest moment of the
busiest market. Measured across *all* markets a day before the match, the worst
10% of Counter-Strike markets cost **69 cents** to trade, and the average
tripled. **A strategy that must trade every qualifying match pays the average,
not the best case.**

**3. The one real number that came out of the passive-quoting test is the fill
rate: about 30%** (or 63–69% if you're generous about what counts as a fill).
That's a genuine measurement, corroborated three ways, and it kills a common
assumption — resting orders *do* get filled. They just don't make money.

## ⚠️ Never tested on this market

Everything about the *teams*. Every strategy above is about price behaviour.

| | |
|---|---|
| Team form, recent results, win streaks | **NEVER TESTED** |
| Roster changes — who actually played | **NEVER TESTED**, and esports rosters change constantly |
| Map pool / map veto | **NEVER TESTED** |
| Game patch version | **NEVER TESTED** — a balance patch can invert which team is favoured |
| Head-to-head history | **NEVER TESTED** |
| Whether the match even started on time | Not tracked |

---
---

# PAGE 5 — BASEBALL (MLB)

*Betting on which team wins.* MLB was used as the **control** — the market
believed to be efficient, included so that if a strategy "worked" here we'd know
the machinery was broken. **$5 figures assume a 50-cent buy price.**

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Random side** | Pick a side at random | **−5.75¢** | **$4.43** | 909 games | **DOESN'T** |
| **Buy one side of everything** | No selection | **−2.43¢** *but could be +1.31¢* | **$4.76** *or* **$5.13** | 909 games | **NOT ENOUGH DATA** |
| **148 price-pattern strategies** | Every combination of price band, timing and cost | **0 came out positive** | — | 909 games | **DOESN'T** |
| **Copy the sharp bookmaker's price** | Strip Pinnacle's margin, compare to Kalshi, trade only when the gap beats cost | **no trades ever qualified** | **—** | 17 games so far | **NOT ENOUGH DATA** |

## The picture

```
 LOSS per contract          (each block = 1 cent)
   random side              █████▊                     −5.75¢
   buy one side of all      ██▍                        −2.43¢  (could be +1.31¢)
   148 price strategies     ─── 0 of 148 came out positive ───
```

## The three things worth knowing — and this is today's work

**1. The bookmaker-copying idea has never actually been run to a profit figure —
anywhere, on any market.** It's the idea ranked #1: take Pinnacle's price, strip
out their margin, treat that as the true probability, and buy when Kalshi is
cheaper by more than it costs to trade. Three earlier things look like this test
and none of them is it — they either used Kalshi's own price with no bookmaker
at all, or measured how far apart the two prices sit **without ever checking who
was right**.

**2. It is now pre-registered and measured. ⚠ The line below is CORRECTED —
my original wording was wrong, in the direction of sounding too decisive.**

> ### ⚠ Retracted 2026-08-07: "the cost is bigger than the whole margin"
>
> That sentence is **not a valid argument** and I should not have written it.
> The bookmaker's margin is what you *strip off* to work out the true price. It
> does **not** cap how far Kalshi's price can be wrong. If Kalshi were 8 cents
> off, the edge would be 8 cents, on a market with a 2-cent margin.
>
> **What actually settles it is a measurement, not the arithmetic.** Across
> **1,460 price comparisons on 30 games**, the two venues never disagreed by more
> than **2.77 cents** — and it costs **2.75 cents** to act. For money to be
> there, they would have to disagree by roughly **four times the largest gap ever
> observed.** That is decisive, and it is decisive *because it was measured*.
> See [bot-hunt/RESULTS_DEVIG_WHERE.md](bot-hunt/RESULTS_DEVIG_WHERE.md).

| | |
|---|---|
| Pinnacle's total margin on baseball | **2.01 cents** — that's the *entire* thing being stripped out |
| What it costs to trade one Kalshi contract | **2.75 cents** (1.75 fee + 1.0 slippage) |

**The cost of trading is bigger than the whole margin you're trying to
exploit.** Out of 17 games with matched prices, the gate fired **zero times**.
Taking each game's single best moment across its entire 24 hours before first
pitch — cherry-picking with hindsight — **the best any game ever got was −0.91
cents.** Not one game was ever positive at any moment.

**3. How long until it's properly testable:** to prove a 5-cent edge you'd need
about **4,356 qualifying games — roughly 1.8 full baseball seasons.** A 3-cent
edge needs 5 seasons. The rest of this season could only detect an 11.6-cent
edge, which is absurd. **There's a cheaper version that IS reachable** — instead
of trading, just ask whether the bookmaker's price *predicts* better than
Kalshi's. That needs about **440 games ≈ 30 days ≈ early September.**

## ⚠️ Never tested on this market

**Everything about baseball.** Every strategy above is price-versus-price.

| | |
|---|---|
| **Starting pitcher** | **NEVER TESTED** — and it is the single biggest driver of a baseball line |
| **Lineups, rest, bullpen usage** | **NEVER TESTED** |
| **Ballpark, weather, wind** | **NEVER TESTED** |
| **Team form, home/away splits** | **NEVER TESTED** |
| **Run-scored-in-the-first-inning markets** | **NEVER TESTED.** 71 of these are being recorded. The reason for wanting them is described in the repo as *"an assertion about how the counterparty prices, with no evidence"* |
| **Over/under total runs** | **NEVER TESTED.** 249 markets recorded and never looked at — and Pinnacle prices these too, so the bookmaker comparison could run on them |

---
---

# PAGE 6 — SOCCER

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Three-way price baskets** | Home/draw/away should add to 100¢ — buy when they don't | **0 of 93 baskets profitable** | **—** | 93 baskets | **DOESN'T** |
| **Anything else** | — | **never run** | **—** | **152 games available vs 481 needed** | **NOT ENOUGH DATA** |

## The two things worth knowing

**1. Soccer was ranked #1 and then killed on counting.** It was ranked top on
"40–101 settled matches per week" — a *rate*. The actual number of finished
matches you can still get data for, across all five South American leagues, is
**152**. You need **481** to detect even a large edge. It was ranked on the
wrong number.

**2. There is a defect sitting under the whole soccer dataset.** A basic safety
check — does the third of matches with a bookmaker price differ from the two
thirds without one? — came back **"can't tell"** and was never resolved. The
project's own note says: *"Until this is done we do not know whether the 33% of
matches carrying a closing line differ systematically from the 67% that do
not."* The fix is described as **about 30 minutes** of work.

## ⚠️ Never tested on this market

| | |
|---|---|
| **Head-to-head, league position, last-five form, rest days** | **NEVER TESTED — and the data is already downloaded.** It was fetched and never joined onto the rows |
| **Expected goals (xG)** | **NOT AVAILABLE.** No free source covers these leagues |
| **Injuries and suspensions** | **NOT AVAILABLE** — the feed returns zero for soccer |
| **Ten years of history** | **NEVER FETCHED.** The dataset is 152 games because that's Kalshi's window, not the sport's. About **10 years per league** is reachable for free |

---
---

# PAGE 7 — WEATHER 🟡

*Betting on tomorrow's temperature.* **This page is different from every other
page: nothing here says DOESN'T.**

## What was tested

| Strategy | What it does | How good | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Temperature model vs. long-run averages** | Predict the day's high from yesterday's and the time of day | **Beats the historical average comfortably in all four cities** | **—** | 812 settlements | **NOT ENOUGH DATA** *(never priced)* |
| **Temperature model vs. the market price** | The only comparison that decides whether there's money in it | **NEVER MEASURED** | **—** | **0** | **NOT ENOUGH DATA** |

## The three things worth knowing

**1. This is the only market in the whole programme where a model genuinely
predicts better than the obvious benchmark**, in all four cities, with the
uncertainty ranges clearly on the right side.

**2. And the deciding test was never run.** Beating the *historical average* is
not the same as beating *the price on the screen*. The project's own document
says, in these words: **"Edge vs the mid: still unmeasured."** That is the gate,
and it is empty.

**3. It's also the only family that passes both practical filters at once, and
only just.** Of eleven weather families:

| | |
|---|---|
| Enough separate settlements to prove an edge (need 481) | **`KXTEMPDCH` has 512** — a 6% margin |
| Enough size available to actually trade | Yes — 2,972 contracts |
| **All eleven other families** | fail one or the other. Several have plenty of depth and only **66** settlements; several have settlements and **1 contract** of depth |

> **This is the biggest genuinely-open question in the repo.** A model that
> works, on the one market that clears both practical bars, with the deciding
> comparison never made. It could go either way — and a 6% margin means a
> recount could kill it too.

## ⚠️ Never tested

Everything except "yesterday's temperature plus time of day". No forecast data,
no multiple weather sources, no other cities, and — crucially — **no comparison
to the price.**

---
---

# PAGE 8 — COPY TRADING (following other people's bets)

*Watching successful traders and copying their positions.* **$5 figures assume a
50-cent buy price.**

## What was tested

| Strategy | What it does | Profit per contract | Put $5 in every trade → | Events tested | Verdict |
|---|---|---|---|---|---|
| **Is skill real at all?** | Do good traders stay good? | **YES — this part is genuinely true** | — | 31,703 trader-markets | *(a fact, not a trade)* |
| **The traders' own edge** | What the good traders themselves earn | **+2.57¢** | **$5.26** | 31,703 | *(not available to you)* |
| **What a copier actually gets** | Buy the same things, hold to the end | **+0.94¢** | **$5.09** | 31,703 | **DOESN'T** *(see below)* |
| **…after the buy/sell gap** | The same, minus what it costs to get in | **−0.06¢** | **$4.99** | 31,703 | **DOESN'T** |
| **Copying their exits too** | Also sell when they sell | **−0.51¢** | **$4.95** | 8,600 positions | **DOESN'T** |
| **Copy tennis traders on Polymarket** | Follow the visible tennis wallets | **−5.6% return** | **$4.72** | 40 wallets | **DOESN'T** |
| **The best tennis wallet found** | The single best of 1,558 searched | **+24.9% return** *but could be −8.7%* | **$6.25** *or* **$4.57** | **27 trades** | **NOT ENOUGH DATA** |
| **"Several experts agree" consensus** | Only bet when 3+ top traders buy the same thing | **no trades ever qualified** | — | **0 accepted** | **NOT ENOUGH DATA** |
| **Transfer the idea to Kalshi** | The same price-band trade, on Kalshi | **−0.67¢** | **$4.93** | 762 matches | **DOESN'T** |

## The picture

```
 PROFIT / LOSS per contract    (each block = 0.5 cents)
   the traders' own edge     █████ +2.57¢   ← theirs, not yours
   what a copier gets        █▉    +0.94¢
   ─── minus the buy/sell gap of at least 1.0¢ ───────────
   copier, after that gap    ▏     −0.06¢   ← this is the real number
   copying their exits       █     −0.51¢
   same idea on Kalshi       █▎    −0.67¢
   average tennis wallet     ─────────── −5.6% of stake
```

## The three things worth knowing

**1. The skill is real. The copyable part isn't.** Good traders genuinely stay
good — that's measured properly and it holds up. But by the time you've paid the
gap between the buy and sell price, what's left is **−0.06 cents**. The edge is
smaller than the door charge.

**2. And it's shrinking.** Measured at three points in time: **+1.98¢ → +0.94¢ →
−0.14¢**. Polymarket introduced fees on 8 January 2026 and the whole ranking of
who's good changed — only **7 of 36** top traders stayed on the list.

**3. The famous "+7.05 cents" number was wrong, and it took two projects to
notice.** The same claim sat in two different project files with **two different
verdicts** — one said "unverified", the other had already recomputed it from
scratch at **+2.09¢ before costs and −0.29¢ after**. Neither knew the other
existed. It was found only when both were put in the same file.

## ⚠️ Never tested

| | |
|---|---|
| **Position sizing, portfolio construction, forward testing** | **DELIBERATELY NOT RUN** — and that was the right call. The gate required both real skill *and* a window where you could act on it. The window doesn't exist |
| **Faster copying** (under 1 second) | Not tested — but the copier's return is flat from 1 second to 30 minutes, so speed isn't the problem |
| **Copying on Kalshi rather than Polymarket** | Tested and refuted — the price-band effect the whole idea rested on **does not exist on Kalshi** |

---
---

# PAGE 9 — ARBITRAGE (free money from prices that don't add up)

## What was tested

| Strategy | What it does | Result | Events tested | Verdict |
|---|---|---|---|---|
| **Ladder ordering** | "Above $100k" must cost more than "above $110k". Buy when it doesn't | **0 violations found** | 3,187 scans | **DOESN'T** |
| **Basket sums** | A full set of price buckets must add to 100¢. Buy when it doesn't | **1 violation, worth less than the fees** | 1,135 scans | **DOESN'T** |
| **Exchange-wide scan** | The same, across 26 market families | **52 real violations, 0 with enough size to trade** | 1,083 scans | **DOESN'T** |

## The two things worth knowing

**1. The violations are real and there are more than first reported.** One
project cited another as finding "zero violations". It had actually found
**52** — none tradeable. Same conclusion, wrong number, corrected.

**2. Why it can't work here:** a basket has many legs, and you pay a fee on every
one. On the crypto ladders the fee floor alone is about **1.93 cents** on a
75-leg basket. The mispricings are worth about 1 cent. **The maths never gets
close.**

---
---

# THE PATTERN, IN ONE PARAGRAPH

Fifty-five strategies across nine markets. **Zero work.** Every closed thread
died the same way and it is worth saying once, plainly: **the effect was real
and smaller than the cost of reaching it.** Tennis: a genuine 2.4-cent
mispricing against a 3.6-cent cost. Copy trading: a genuine 0.94-cent edge
against a 1.0-cent spread. Player form on favourites: a genuine 1.18-cent
signal, too small to measure. Baseball: a 2.75-cent cost against a 2.01-cent
total margin. Crypto: real 43%-frequency price spikes that still lose money.
**Nine times, the same shape.**

Forty-five times a number in this repo has been corrected. **Every single
correction made the edge smaller. Not one has ever made it bigger.** That
asymmetry is what "there is no edge here" looks like from the inside — a real
edge survives being checked, and usually grows.

## The three things that are genuinely unfinished

Not failures — **never run**:

1. **🟡 Weather vs. the market price.** A model that beats its benchmark, on the
   only market clearing both practical bars, with the deciding comparison never
   made.
2. **🟡 Crypto market making.** A validated test rig, a full 1-cent gap to earn,
   fees no longer in the way, and the one measurement that decides it never
   taken. The project's own verdict section opens with "Not yet reached" while
   the status file calls the thread closed.
3. **🟡 Tennis player form, on more than 29 days.** The null result stands, but
   on a window so short the average player appears three times. **$9.99** buys
   three years.
