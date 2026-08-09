# What reading the Reddit corpus actually found

Thirteen threads read in full out of a 39,600-post corpus. Permalinks only — no
usernames, because this repo is public and the posters are private individuals.
Every claim below is theirs, not this project's; where it touches a result this
repo already has, that is said explicitly.

Sorted by how much it should change what happens next.

**Read §0 and §0b first.** Between them they contain 4,604 resolved Polymarket
windows and a 1,700-trade rebuild of a viral YouTube strategy, and they arrive
independently at two results this programme spent months reaching.

---

## 0. Seven months and 4,604 resolved windows on Polymarket's 5-minute crypto markets

`/r/Polymarket/comments/1un85mg/` · 9 points · 16 comments

**The most directly relevant document found on any platform in this programme,
and it has 9 points.** Someone tested every angle on Polymarket's 5-minute
Up/Down crypto markets — ~1.7M candles and **4,604 real resolved windows from
live-recorded order books** — and published the autopsy. It reaches this repo's
KXBTC15M structural kill and its ladder-arbitrage null independently, **on the
other venue**, with denominators on every claim.

It is a MIDDLE-bucket source: it ends with a soft pitch for the author's own
trading terminal, undisclosed as an interest. The rubric's answer is the right
one — **keep the method, discount nothing here because there are no profit
claims to discount, and note the incentive.**

### The results, each with its n

| test | n | result |
|---|---|---|
| **Chainlink-vs-Binance lag arbitrage** | 5,826 entries | momentum side resolved **74.8%**; the Poly ask you would pay was **75.3%**. **Gap −0.4pp. Zero fillable lag.** |
| a "+$456 profit" version of the same signal | — | **a measurement artifact**: ETH carries a structural ~0.12% Binance-to-Chainlink offset, larger than the 0.10% entry gate, so the signal always fired "Up". Corrected → gone. |
| momentum continuation | 346,094 windows | ~49%, and **it gets worse the bigger the move** — 48.0% at ≥0.10%, **46.5% at ≥0.40%**. Mildly mean-reverting. |
| sustained-trend continuation | 17,856–168,815 per bucket | **monotonically inverts**: run≥2 48.4% · run≥3 47.6% · run≥4 46.4% · run≥5 46.1% · run≥4 **and** ≥0.8% **44.8%**. |
| **buy the favoured side at its real ask, hold to resolution** | **4,569 decisions over 4,604 windows** | **every band loses against price+fee**: −4.5pp at 0.50–0.55, −2.1 at 0.55–0.60, −3.7 at 0.60–0.65, **−6.5 at 0.65–0.70**, −1.6 at 0.70–0.80, −3.6 at 0.80–0.95. |
| "in a bleed, buy the trend side cheap" | 1,262 | **exactly backwards**: 0.00–0.45 wins **30.8%**, 0.70–1.00 wins 84.2%. The price is never a discount; it is the probability, even inside a trend. |

> **"There is no band where paying for direction beats the fee."** The book is
> calibrated: a side priced 0.65 wins ~60–63%. The strong-favourite band is the
> *worst*, because by the time a side is bid that high the move is exhausted.

### The exit study, which lands directly on the live bot's martingale

- **58% of eventual *winners* dip to −10% before recovering.** Any stop at a
  −10%-ish tier kills more winners than losers.
- Winners' first pullback averaged **~22pp with 97% recovering**; losers'
  averaged **~38pp with ~32% recovering**. They look identical for the first few
  seconds, so no stop rule separates them cleanly.
- **"Break-even arming (move stop to entry after +5%): net negative — the single
  biggest source of loss in one exit study."**

`STATUS.md`'s 2026-08-03 diagnosis of the live bot's 28 July martingale found
the same mechanism from the other side: `rearm_above = stop_price + 2` meant a
2¢ bounce off your own stop re-armed entry, which in a falling market is
ordinary noise. **An unrelated researcher, different venue, 4,604 windows,
independently names break-even arming as the largest single loss source.** That
is the strongest external support any fix in this repo has received.

### Adverse selection, explained mechanically — and it is the ladder-arb null

> *"you rest a bid to buy Up at 0.50. That only gets hit when someone is willing
> to sell you Up at 0.50 — and a rational seller only does that when Up is
> becoming less likely … **Being filled is itself bad news.**"*

And the two-legged version, which is precisely why this repo's ladder arbitrage
was *"unprofitable net"* despite a real gross violation: rest both legs of a
split as maker, and **they do not fill at the same instant**. The leg in demand
fills; the leg that is now worthless hangs. *"You just sold the winning leg
cheap and got left holding the losing leg, naked."* To rescue it you cross the
spread as a taker and pay the fee you were trying to earn.

**This repo found the null. This post supplies the mechanism.**

### And it lands on the venue recommendation

`signal-github` concluded **Polymarket for maker-only quoting**. This post
describes what that business actually is at the top of the book, and it is not
quoting for a spread:

- **split** $1 → 1 Up + 1 Down, **sell both as maker** for ~$1.02. Zero
  directional opinion, zero taker fee.
- **buy both and merge** when Up + Down sum below $1.00.
- **Polymarket's liquidity-rewards programme pays for resting size near mid** —
  *"a stable, directional-risk-free paycheck that arrives on top of everything
  else."*

The whales *"are wrong constantly — pages of total losses"*; the losses are a
cost of inventory for a business earning spread + rebates + merge profit on
volume. **"Their PnL curve is a straight line up not because they predict well,
but because they're the casino, not the gambler."**

**Why retail cannot run it, in his words:** the spread income does not cover
your time at small size, the rewards programme favours size and uptime, and the
merge windows are taken by bots in milliseconds. Same shape as this repo's
recurring finding — *a real effect smaller than the cost of reaching it* — and
it is a **second, independent reason** to be sceptical of maker-only quoting,
alongside §7's underwriting claim.

### The one thing that showed a pulse, and he refuses to call it a strategy

**Fading** extended moves. After a strong 20-minute run the reversal hits
**~54–55%**, stable across four years — 2023 53.8%, 2024 51.6%, 2025 54.5%,
2026 54.6%. As a maker (50% break-even) that is a ~4-point paper edge. He then
says it wobbled to break-even in 2024, it means buying against the obvious move,
and **he has not proven it survives real maker fills plus adverse selection**:
*"Treat it as a hypothesis, not a strategy."*

That is the honesty signal the rubric weights highest, and it is the one number
in this post worth a real test here.

### ⚠ A conflict with a primary measurement in this repo

He states the Polymarket 5-minute taker fee as

> `fee = shares × 0.072 × price × (1 − price)`, makers zero

— a **quadratic** form, the same shape as Kalshi's `0.07 × C × P × (1−P)`.
`signal-github`'s correction **C2**, measured from the Gamma API over 2,100
markets, records Polymarket taker fees as **flat rates of 0.04 / 0.05 / 0.07 by
category**. Both agree makers pay zero and both agree on roughly 7% somewhere;
**they disagree about the functional form**, and the functional form is the
whole reason cheap contracts are penalised differently from coin-flips.

**Not resolved here.** C2 is a primary measurement over 2,100 markets and this
is one researcher's write-up — but he has 4,604 resolved windows of real book
data behind his version, and the break-even numbers he quotes (51.8% at 0.50)
are only consistent with the quadratic. **Re-run `polymarket_fees_census.py` and
settle it; this is the highest-value single check on the list.**

---

## 0b. The cross-platform contradiction, in its purest form

`/r/algotrading/comments/1r92wxr/` · **321 points** · 106 comments
and the sequel `/r/algotrading/comments/1reh4pa/` · 133 points

This is the thing this whole project was built to find, and it arrived intact.

Someone rebuilt a **400,000-view YouTube trading strategy** rule by rule and
backtested it properly.

| | the YouTube video | the 16-year rebuild |
|---|---|---|
| trades | **100** | **1,700+** |
| win rate | 56% | **39%** |
| risk/reward | 1.5 | 1.5 |
| return | **+40%** | **−23% total, −1.6% annualised** |
| max drawdown | not shown | **−36%** |

Negative expectancy, negative Sharpe, profit factor below 1.

> **"What's wild is that the exact 100 trades shown in the video do appear in
> the backtest… but they're just a short lucky stretch inside a much longer
> downtrend."**

That sentence is the entire thesis of this programme, demonstrated by someone
else with the receipts. The video was not fabricated. Every trade in it is real.
**The denominator was 100 and the truth needed 1,700**, and the brief's own
framing — *"small numbers stated confidently, usually sincerely"* — is exactly
what happened. The rebuilder says so too: *"I'm not saying the YouTuber was
lying on purpose."*

### The sequel kills the obvious rescue

The top comment on the first post was *"if it's that consistently bad, why not
do the exact opposite?"* He tested it: same rules, every signal flipped, same 16
years, **1,731 trades**.

Win rate jumps to **61%** and the equity curve stops looking like a slide to
zero. **Expectancy is still −0.01.** He traded a low win rate with good R:R for
a high win rate with terrible R:R, and:

> **"When you reverse a strategy, you aren't reversing the costs. You're still
> paying the house."**
> **"We often assume a losing strategy has a negative edge, but usually it just
> has no edge at all."**

**Why that belongs in `GUARDS.md`.** This repo's best-supported result is 480
configurations, 0 profitable, S1 at −9.36¢ against a random-entry control S5 at
−8.28¢. *"No edge"* and *"negative edge"* look identical on a P&L curve and are
completely different objects, and the difference is decided by whether the cost
term explains the gap. That is a one-line check this programme already has the
data to run and has never framed that way.

---

## 0c. Five independent arrivals at this repo's KXBTC15M kill

`STATUS.md` closed the BTC 15-minute thread **structurally**: *"`floor_strike`
equals the prior window's settlement in 99.86% of 6,261 markets, so every
contract is minted at-the-money on the peak of the fee curve."* That was derived
here, from the venue's own data.

Reading the corpus turns up **four unrelated people who got to the same place by
building the thing**, on both venues:

| source | what they did | where they landed |
|---|---|---|
| `/r/Polymarket/1un85mg` (§0) | 4,604 resolved 5-min windows, real recorded books | **every price band loses against price + fee**, −1.6 to −6.5pp |
| `/r/algotrading/1u0cz4n` | 4 weeks, full apparatus — scanners, paper trading, latency monitoring, hundreds of finalised paper trades | killed it: *"It was failing because the economics weren't there"* |
| a commenter on that thread | XGB implied-probability model, **Rust** execution, a month of **1-second order-book snapshots** | profitable on paper **with fees included**, **lost several hundred dollars live** — *"the fees were eating any potential profit"* |
| `artyomderkach-bit/kalshi-15m-market-maker` (via `signal-github`) | built the full engine and backtest harness, ships in paper mode | *"almost every edge that looked real in-sample decayed out-of-sample"* |

The line worth keeping, from the second one:

> **"The closer I got to production realism, the less attractive the strategy
> became."**

That is this programme's own asymmetry stated by a stranger — **~41 recorded
corrections here, every one of which shrank the edge, not one of which ever
revealed a larger effect.** Four outsiders, two venues, four toolchains, one
conclusion.

**And the one dissent points the same way as everything else.** A commenter:
*"next 5/15 mins up down is a literal coin toss, therefore the edge is trading
both sides and managing inventory."* That is not a counter-argument — it is
§0's split-sell finding restated. The money is on the **supply** side, and §0
already established why retail cannot reach it: the rebate programme favours
size and uptime, and the merge windows go to bots in milliseconds.

> **What this does NOT do:** none of it is independent in the strict sense —
> they are all people who read the same venues and hit the same fee curve. Five
> people finding the same wall is weaker evidence than one properly powered
> test. It is, however, exactly what a wall looks like from five directions.

---

## 0d. A candidate 13th guard: **a mispricing filter is an illiquidity filter**

`/r/algotrading/comments/1rsj22d/` · 60 points · 53 comments

The post is an LLM-versus-Polymarket divergence strategy — enter when the
model's probability differs from the market by ≥15%, exit next day, €10,000 per
agent, 60 days, paper only. The value is entirely in one 9-point reply, which
takes it apart three ways and produces a mechanism this repo does not have
written down anywhere:

> **"the 15% divergence threshold is likely doing more work than the LLM
> rationality thesis — it's essentially filtering for the most mispriced, least
> liquid markets where paper fills are most unrealistic."**

**Screening for the biggest mispricing selects for the thinnest book, every
time.** The filter and the thesis are confounded by construction: whatever
explanatory story sits on top, the trades you actually take are the ones nobody
else wanted. That is the same shape as the `youtube-signal` finding — a
demonstrated mispriced prop with **~$60 of liquidity** — and as this repo's own
recurring conclusion that the edge is real *because* nobody is looking, which is
precisely why nobody can size into it. It has never been stated as a *test* you
can run before trusting a screen.

**The candidate guard:** for any strategy selected by a threshold on
mispricing, divergence or edge, report the **liquidity distribution of the
selected set against the unselected set**. If the selected markets are
systematically thinner, the threshold is doing the work and the thesis is
unfalsified rather than supported.

*Not added to `GUARDS.md` unilaterally — that file is a curated, numbered,
repo-wide asset and this session does not own it. Flagged here and in
`STATUS.md` for whoever does.*

### And a number that dwarfs the fee work

> **"a 1¢ bid/ask spread on a 3¢ market is 33% round-trip cost"**

This programme has carefully established that fees hurt cheap contracts
disproportionately — about **2% on a 69¢ contract against ~6% on an 18¢ one**.
At **3¢ the spread alone is 33%**, which is five times the worst fee figure and
an order of magnitude above the typical one. **On penny contracts the fee curve
is the small term.** Any cost bar built from fees alone will be wildly optimistic
exactly where a mispricing screen sends you — which is the previous point,
arriving from the other direction.

Third objection from the same reply, worth keeping as a reading habit: the
equity curve is **flat noise for ~50 of the 60 days** with the whole return
arriving in the last 7–10, on correlated events. That is the shape the
"delete the top five trades" stress test exists to catch.

---

## 0e. Three sources disagree about stop losses, and the disagreement is the finding

This repo's position is settled and stated in `CLAUDE.md` §9b: **stops make it
worse.** Measured on the user's own bot in `bot-forensics`, stop-and-re-enter
turned **−2.29¢ into −9.36¢** per contract, and *"selling a 90-cent contract at
40 cents locks in the loss the strategy was relying on recovering."*

Reading turned up a second source agreeing and a third flatly contradicting it:

| source | what it measured | verdict on stops |
|---|---|---|
| **this repo** (`bot-forensics`) | a real bot's real trades, buying favourites | **harmful** — −2.29¢ → −9.36¢ |
| Hyperliquid copy bot (`/r/algotrading/1v56b7h`) | every stopout re-scored against its max adverse excursion | **harmful** — **8 of 9 would have recovered** |
| SPY short-vol grid (`/r/options/1sy0plj`) | 96 cells, 7 years of 1-minute chains, **16,024 trades** | **the stop IS the strategy** — same cell, same fills, same period: **+5,439% with, −100% without** |

### They are all right, and the reconciliation is worth more than any of them

**It turns on whether the left tail is bounded.**

- **Buying a contract** — the tennis bot, copy-trading a holder — has a floor.
  It can only go to zero, and drawdowns mean-revert because the thing you bought
  is still the thing you bought. A stop **realises** a loss the position was
  going to recover, and then you pay the spread again to get back in. This is
  exactly what `bot-forensics` measured, and exactly the 8-of-9 result.
- **Selling premium** — short vol, credit spreads — has **no floor**. One tail
  event takes the account to zero. The stop is not a tuning parameter, it is the
  only thing standing between the strategy and ruin. Hence −100% without it.

**So "do stop losses help?" has no general answer, and this repo has been
carrying one.** §9b's rule is right *for the strategies this repo trades* and
would be actively dangerous if lifted to a premium-selling strategy. The
sentence that needs adding is not a correction, it is a **scope**: *stops hurt
when your downside is bounded and your drawdowns mean-revert; stops are survival
when your downside is not.*

### The same post also puts a denominator on something the repo asserts

`kalshi-inplay-bot/backtest/HIGH_SWEEP_RERUN.md` calls the optimistic fill model
*"the single easiest way to fake a profitable backtest"*. That is now measured:
**mid-fill backtests overstate returns by 30–60%**, and switching to
post-a-limit-and-wait flipped **half the winning cells negative** across a
96-cell grid. Their honest fill model — post at `combo_ask + $0.04`, 20–25% fill
rate, ~12 minute average wait — lands **4–7 cents worse than mid, every trade.**

---

## 0f. A stop that fires between candles is invisible to the backtest

`/r/algotrading/comments/1qcp07r/` — a catalogue of five backtest biases from
someone running **16,000 backtests a day**. One of them lands on this repo's
in-play work:

> **"I originally evaluated stops on 1-hour bars. That turned out to be a big
> mistake. One hour is a long time, and trades could have hit stops mid-bar
> without being detected. When I switched to evaluating stops on 1-minute bars,
> trade counts went up significantly."**

**This repo runs its in-play analysis on one-minute candles**, and
`soccer/src/analyse_inplay.py` already notes that one-minute candles cannot
resolve sub-minute reaction. Those are the same problem one scale down: **a stop
that triggers between two candles never appears in the backtest at all.** The
in-play bot's headline is −9¢ per trade against a ~4¢ cost base, and that number
is computed from candles. If mid-candle stop hits are being missed, the true
count of stop events is higher than the backtest thinks — and given
`bot-forensics` measured stop-and-re-enter turning −2.29¢ into −9.36¢, missed
stop events push the estimate in the **worse** direction, not the better one.

**Checkable with data already on disk:** the pmxt L2 archive rescued earlier
this session is tick-level for 15–27 May, and `set1_overshoot`'s depth recorder
samples at 0.55 s. Either can say how often price crossed a stop level *between*
one-minute candles. Nobody has asked.

### The other four, worth having as a checklist

| bias | the symptom that reveals it |
|---|---|
| **survivorship** | using today's symbol list and walking backwards silently filters for survivors — rebuild the universe from data available *at the trade date* |
| **corporate actions** | *"a $5,000 bet would suddenly show a $45k gain in a day"* — an implausible single-day gain is the tell for an unadjusted reverse split |
| **liquidity concentration** | run the strategy per liquidity decile, not pooled: *"some strategies held up across multiple buckets. Many did not."* |
| **execution optimism** | he moved from next-bar-open to the next 1-minute bar taking the **worse** side — close-or-high for buys, close-or-low for sells — and still says it may be optimistic |

**And one he does not flag, which is the biggest.** He selects the
best-performing strategies on a recent window, then tests those on a 22-year
history that **contains that window**. That is not an out-of-sample check.
`CLAUDE.md` §6 states the rule he is breaking: *selecting on past performance is
fine; measuring returns over the same window you selected on is not.*

> Worth holding next to this repo's own scale. `CLAUDE.md` §9c warns that with
> **16 tennis bots** running, the best of 16 looks good even if none has an
> edge. **He runs 16,000 a day.**

`/r/algotrading/comments/1v56b7h/` · 43 points · 24 comments

Ten lessons from building a Hyperliquid copy-trading bot, opening with *"Do not
ask for the bot. I am not selling anything."* Every lesson carries a number and
most of them are failures. **This is the best single document found on any
platform this session, and it has 43 points.**

It reaches this repo's own closed copy-trading verdict independently, from a
different venue — and then goes past it:

> **"copying a profitable trader loses money by default. i matched every copy to
> the source wallet's outcome on the same trades: they made +0.5% per trade at
> 69% winrate, my copies made half that at much lower winrate. the gap is exit
> timing."**

and

> **"entry latency is a red herring. my median detection lag was under a minute
> and simulating zero lag barely moved the numbers. all the leak was on the exit
> side."**

### Why that matters here specifically

`wallet-copy-study` and `polymarket-tennis-copy` both model the follower's loss
as an **entry delay** — `TradeCopyability.delay_seconds`, follower ROI measured
at +1s/+10s/+60s, and `follow_through.py`'s whole design is "what the market
traded at AFTER the delay". If this poster is right, that instrument is
measuring the wrong side of the trade, and the thread's conclusion (the copyable
part is smaller than the spread) would be **right for a reason the model does
not contain**.

That is a cheap thing to check and it has not been checked. It does not reopen
the thread — the verdict was NO-GO and this makes the copyable portion smaller,
not larger — but it changes what the number means.

### Six more from the same post, each with its own use here

| lesson | where it lands in this repo |
|---|---|
| **"position fragmentation"** — a wallet scales in over several fills and each fill can read as its own position; closing the copy when one fragment closes took an 84% win-rate wallet to 12% copies. Fixing it took that strategy from 21% to 82%. | This is a concrete, named bug class for any position reconstruction. `ReconstructedPosition` does exactly this reconstruction. |
| **"a normal stop loss cancels the copied edge"** — the source holds through drawdowns; your stop realises their drawdown and misses their recovery. Re-scored against max adverse excursion, **8 of 9 stopouts would have recovered**. | The tennis in-play bot's stop-and-re-arm behaviour is the same shape, and its 28 Jul martingale was three stopouts in 50 minutes. |
| **"polled stops make paper trading lie about your losses"** — an illiquid coin gapped 66% through a stop that live would have filled near the trigger, because live uses resting exchange orders and the sim checked price in a loop. | Corroborates the backtest-realism rules already in `KNOWLEDGE.md`, from the loss side rather than the fill side. |
| **"winrate comparisons under a few hundred trades are noise; detecting a 5-point winrate edge takes roughly 1500 trades per arm"** | Same order as this programme's own ~481-settlement bar, and larger. Nothing here disagrees with it. |
| **"checking your experiment daily and stopping when it looks good inflates false positives to 20-30% … e-values (always-valid sequential tests) let you look every day"** | **A tool this programme does not have.** Every recorder here is watched daily and every analysis is re-run as data accrues. Holm-Bonferroni fixes the multiple-outcome problem; it does not fix repeated peeking. Worth adding to `GUARDS.md`. |
| **"a weak benchmark validates whatever you want to believe. my random-entry control traded too rarely at a different size, so 'beats random' was statistically meaningless."** | The 480-config backtest's headline is S1 −9.36¢ **against random-entry S5 −8.28¢**. Whether S5 trades at the same rate and size as S1 is exactly the question this raises, and it decides whether that comparison means anything. |

Its own tl;dr: *"most of what looked like edge was measurement error."*

---

## 2. Kalshi settlement mechanics, from 750+ tracked settlements

`/r/Kalshi/comments/1v9snr3/` · 9 points · 16 comments

Three mechanics, with a stated denominator, which is rare enough on its own:

1. **"Closed" is not "settled."** A market sits in `closed` or `determined` for
   minutes to hours — weather markets sometimes about a day — before
   `finalized`. **Count only `finalized`; anything earlier can still move.**
2. **Tennis series can settle before the match starts.** Series resolve on who
   *advances*, so a withdrawal or walkover pays out with zero play. *"It reads
   like a glitch the first time; it's the rulebook."*
3. **The last few cents are not free.** In the 0.90+ band their sample resolves
   favourite-side ~96–97%, so the "safe" last cents lose almost exactly as often
   as they pay, and the 7% × p(1−p) fee eats a real share of thin edges.

**Point 2 is the one to act on.** `kalshi-inplay-bot` and `set1_overshoot` trade
`KXATPMATCH` / `KXWTAMATCH`, and a walkover settling with zero play is a
settlement path that an in-play strategy has no model for at all. Point 3 is an
independent, ticket-side arrival at the same fee-curve shape this repo found
structurally in KXBTC15M and in the 3.61pp tennis cost bar.

Unverified: this is a Reddit poster's own paper-tracked research, and it says so
(*"Research only — not financial advice. Paper-tracked"*). The claims are
checkable against Kalshi's API and have not been checked here.

---

## 3. A free Polymarket historical order-book archive, and it is live

`/r/algotrading/comments/1rdhw2n/` · 556 points · 60 comments

**`pmxt`** — *"CCXT for prediction markets"*, a unified API over Polymarket and
Kalshi. Verified live by fetching, 2026-08-04:

| | |
|---|---|
| `github.com/pmxt-dev/pmxt` | **2,055★**, not archived, last push 2026-07-18 |
| `github.com/qoery-com/pmxt` | same repo — the org was renamed; both return identical API data |
| `archive.pmxt.dev/Polymarket` | **HTTP 200** — free Polymarket order-book dumps |
| `pmxt.dev` | HTTP 200 |

The archive announcement's framing is *"charging devs for raw market data is
basically a scam at this point"* and it is stated as **part 1 of 3**, order books
only, with trade-level and other exchanges promised.

> ## ⛔ RETRACTED — "hourly snapshots". It is a TICK-LEVEL DELTA FEED.
>
> **Everything below this box that calls the archive "hourly" is wrong**, and the
> error was load-bearing: it is why the Kalshi half was written off as
> substituting "for nothing here". Left in place rather than deleted, because
> deleting a wrong number is how somebody re-derives it.
>
> One file was finally **downloaded and opened** (2026-08-04) instead of being
> judged from its filename. `kalshi_orderbook_2026-05-17T02.parquet`:
>
> | | |
> |---|---|
> | size | **128,739,737 bytes** for ONE hour |
> | rows | **20,723,041** |
> | `event_type` | **18,937,521 `orderbook_delta`** + 1,785,520 `orderbook_snapshot` |
> | columns | `timestamp_received` (ms), `timestamp` (µs), `market_ticker`, `market_id`, `event_type`, `yes_bids`, `no_bids` (full price/size ladders), `price`, `delta`, `side` |
> | distinct tickers in the hour | **642,054** |
> | **tennis** | **126,704 rows across 97 distinct `KXATPMATCH`/`KXWTAMATCH` tickers — in one hour** |
>
> The hourly cadence is how the files are **batched**, not the resolution of
> what is inside them. This is a full order-book delta stream at microsecond
> stamps — **finer than this repo's own 0.55 s depth recorder**, and it covers
> the exact tennis series `kalshi-inplay-bot` and `set1_overshoot` trade.
>
> **What that does to the earlier conclusion:** the ~12-day window Kalshi's own
> API has already dropped is not a coarse consolation prize. It is tick-level
> depth on 642k markets that cannot be obtained anywhere else at any price.
> Cost to take it: ~128 MB/hour × ~288 hours ≈ **37 GB of a volunteer archive's
> bandwidth**, which is a real ask and is why it has not been done unilaterally
> — see `DECISIONS.md` D14.
>
> **The lesson, and it is one this repo already had:** *verify by fetching, not
> by finding a link.* I enumerated the index and believed I had verified the
> archive. I had verified that the **files exist**. I had not opened one.

### What the archive actually contains — enumerated, not assumed

The landing page is a claim; the directory index is a fact. Fetched 2026-08-04:

| | |
|---|---|
| format | **hourly Parquet order-book snapshots**, CC BY 4.0 |
| venues listed | Polymarket, **Kalshi**, Limitless, Opinion |
| `/data/Polymarket/v2/` | **21 Apr – 4 Aug 2026**, ~105 days, 412–534 MB **per hour** |
| `/data/Polymarket/v1/` | separate feed, newest **16 Apr 2026** |
| `/data/Kalshi/` | **15 May – 11 June 2026**, ~28 days, 8–90 MB per hour |

Ranges established by walking the paginated index (≈3 days per page) until it
returned empty: Kalshi page 13 held 15–17 May and page 15 was empty; Polymarket
v2 page 50 held 21–24 Apr and page 60 was empty.

**A detail that corroborates something already in this repo:** the archive's
Polymarket **v1** feed stops on 16 April and its **v2** feed starts on 21 April.
Polymarket's CLOB **V2 went live 28 April 2026** — `youtube-signal`'s own
`tool_reputation.py` finding. An unrelated third party's data pipeline brackets
the cutover independently.

**Two very different situations, and the difference matters.**

**Polymarket is live and current** at roughly **12 GB/day**. That is the same
order as the *"top-of-book ~5 GB per 3–4 months, full book ~150 GB"* figure the
`youtube-signal` corpus recorded for a paid vendor — free, hourly, and under a
licence that permits commercial use with attribution.

**The Kalshi feed stopped on 11 June** and covers only ~28 days. It is not a
substitute for this repo's own tennis depth recorder, which started 1 August and
samples at 0.55 s rather than hourly.

**But there is a real, narrow prize in it.** `STATUS.md` records Kalshi's API as
a ~69-day window in which *"closed markets 404 and are gone"*, and recorded
order books as *"not re-pullable at any price"*. On 4 August that window reaches
back to about **27 May**. This archive holds hourly Kalshi books from **15 May**.

> **That is roughly twelve days of Kalshi order-book data — 15 to 27 May 2026 —
> that Kalshi's own API no longer serves and that this programme does not have.**
> Hourly, not sub-minute, and it will keep shrinking as the 69-day window rolls
> forward. If it is worth anything, it is worth pulling **now**.

For Polymarket the "not re-pullable at any price" line is simply false: 105 days
of hourly books, free, CC BY 4.0.

This is the data source the `youtube-signal` corpus recorded as `r2v2.pmxt.dev`
— which this project's live check returned 404 for, correctly classified as
`API_ROOT_404` (a REST base URL with no document at `/`) rather than as a death.

`pmxt-dev/pmxt` was already in `signal-github`'s corpus at 2,053★ — the 11th
most-starred repo it holds — and nobody had joined it to anything. Reddit is
where it is promoted; GitHub is where it was already sitting.

Caveat worth keeping: **9 of the posts mentioning `pmxt` read as coordinated
promotion**, and being posted nine times is not nine recommendations. The repo
and the archive were verified by fetching, not by counting posts.

---

## 4. Two named counterparty risks on Kalshi

- `/r/PredictionMarkets/comments/1qjjgfm/` — a settlement dispute where the
  poster argues the resolution contradicted the contract's own stated primary
  source, and says they are filing with the **CFTC Reparations Program** on the
  grounds that Kalshi is a Designated Contract Market legally required to follow
  its filed rulebook. **The existence of that route is the useful part**; the
  merits of the dispute are not assessed here.
- `/r/Kalshi/comments/1v5po6r/` — an account banned with $4,100 inside and
  withdrawal blocked. One report, no corroboration, and recorded as one report.

Both are the class of risk that never appears in a backtest.

---

## 4b. The one finding here that could stop money being lost this week

**`predictionhunt.com`** — a live prediction-market site — carries **8
scam-flavoured mention windows out of 17** in the Reddit corpus, against 4
neutral and 2 positive. That ratio is why it clears the stated floor while
`arxiv.org`'s two-in-309 does not.

The windows are specific and consistent, and they are **users' allegations, not
this project's finding**:

> *"Predictionhunt is a complete pile of crap. They took my money, the site
> crashed, and [they] won't respond to my emails."*
> *"I would stay away from predictionhunt.com at all costs."*

A separate thread describes the same shape from the operator's side — support
saying *"there was some sort of exploit and their wallets got drained"*, then
asking the user to email a deposit transaction hash and going quiet.

**What is verified here and what is not.** Verified: the domain resolves and
returns HTTP 200 (so "the site is gone" is not the complaint), and the mention
counts are reproducible from `data/social.db`. **Not verified:** whether any
individual account was actually withheld. These are user reports on a public
forum and nothing here adjudicates them.

**The practical rule needs no adjudication:** this is a site holding customer
deposits whose users say withdrawals stopped and support went silent. That is
the one class of risk that never appears in any backtest, and it is the reason
a reputation table is worth building at all.

---

## 5. A Polymarket credential-phishing site, described but not named

`/r/Polymarket/comments/1tpu8za/` · 4 points

A site claiming to be a Polymarket trading bot, promoted by **seeded comments
from brand-new accounts on Polymarket markets themselves**, with a fake login
page. The poster entered their Polymarket login and *"it drained my account"*.
Two `.xyz` domains were taken down and it moved to a `.com`; Cloudflare acts,
the Swiss hosting provider does not. They deliberately do not name the site.

**The transferable rule, which needs no name: no third-party "bot" ever needs
your venue login.** Every legitimate integration in either sibling corpus uses
an API key or a wallet signature. A login form on a bot site is the attack.

---

## 6. The satire that scores well, and what it says about the instrument

`/r/algotrading/comments/1skauaj/` · 332 points — the top-scoring post in the
whole corpus — is a **parody**: two weeks of 5-minute candles, parameters tuned
until the equity curve turns green, no fees or slippage *"but I'm sure that
won't make much difference"*, leverage to compensate, and the strategy withheld
so JP Morgan cannot steal it.

It is worth reading precisely because the community's most-upvoted contribution
is a checklist of this repo's own GUARDS, written as a joke. It also breaks this
project's proxy scorer — see `reports/T2_rubric_audit.md`.

---

## 7. The claim that would reframe this repo's most promising strategy

`/r/quant/comments/1rodanx/` · 137 points · 40 comments
(cross-posted to `/r/PredictionMarkets/comments/1roaqkl/`)

> **"I pulled 5GB of Kalshi trade data and the liquidity provider economics
> don't look like market making — they look like underwriting."**

Kalshi's full 2025 NFL moneyline trade data, passive LP exposure reconstructed
game by game. The poster's summary: *"LPs aren't neutralizing inventory and
capturing spread. They're accumulating directional outcome exposure that
persists through settlement, and profitability correlates with managing flow
imbalance rather than eliminating it. That's not a market making return
profile — it's closer to how a sportsbook or insurer makes money."*

**Why this is the most consequential unverified claim in the corpus.** This
programme's single most promising strategy is **maker-only two-sided quoting**,
and `signal-github` has already narrowed the venue answer twice — first to
"quote where the maker fee is zero", then to "Polymarket, because Kalshi charges
makers precisely where the liquidity is and its member agreement says designated
market makers get fee discounts, rebates, revenue share, cancel-on-disconnect
and greater throughput."

Every one of those arguments is about **costs and privileges**. This claim is
about the **return profile itself**: that passive quoting in event contracts
does not pay you a spread for neutral inventory, it pays you for warehousing
directional risk to settlement. If that is right, then the strategy is not a
cheaper or more expensive version of market making — **it is a different
business**, and it needs to be sized and hedged as underwriting rather than as
inventory turnover.

> ### ⚠ Unverified, and it stays that way here
> The poster cites SSRN abstract **6325658**, *"A Microstructure Perspective on
> Prediction Markets"*. Fetched 2026-08-04: `papers.ssrn.com` returns
> **HTTP 403 with a Cloudflare "Just a moment..." interstitial** to a
> non-browser client. **This project does not solve bot challenges**, so the
> paper's existence, authorship and methodology are all unconfirmed. It is
> recorded as a claim with a citation, not as a source that was read.

### Two supporting observations from the same subreddit, both first-hand

`/r/quant/comments/1ul6e62/` (50 points) — from someone who says they have made
markets on both venues:

- *"millions of shares are often parked right at the bid, so if you want the bid
  price it's time to get in line."* **Queue depth, not fee level, is what stops
  a retail maker getting filled** — an obstacle neither sibling project has
  measured and which no fee schedule reveals.
- *"if your market is 50/50 the fee curve on Kalshi taxes these a lot more than
  say 80/20 markets."* Independent, first-hand arrival at the `p(1−p)` peak this
  repo found structurally in KXBTC15M.

### And one claim that conflicts with a measured result here

`/r/PredictionMarkets/comments/1q64dd9/` — *"Fees only apply to 15-minute crypto
markets rn"* and *"Fees go to the market makers, not to polymarket"*.

`signal-github`'s correction **C2** measured Polymarket's Gamma API over 2,100
markets and found taker fees of 0.04 / 0.05 / 0.07 **by category**, with makers
at zero on 100% of markets carrying a schedule. The "makers are paid" half
agrees. The "only 15-minute crypto" half does not, and the post carries no date
context in its text.

**Recorded as a conflict to re-measure, not as a correction.** C2 is a primary
measurement over 2,100 markets; this is one person's write-up for a friend. The
useful part is that it is cheap to re-run `polymarket_fees_census.py` and settle
it, and fee claims expire in 3 months anyway.

---

## 8. Wallet persistence, measured by someone else

`/r/Polymarket/comments/1tn51bp/` — six months of Polymarket wallet data:
*"Most 'top wallets' from any 3-month window revert toward average in the next
3 months. But there's a small subset (~3–5% of active wallets) that maintains
edge persistently."*

That is `wallet-copy-study`'s split-sample result reached independently: **wallet
skill is real and persists in a small minority, and the screen that finds them
mostly finds noise.** This repo went one step further and asked whether the
persistent part is *copyable* after costs — it is not, at +0.937pp falling to
−0.135pp in the fee era against a ≥1.0pp spread. The poster's own open question
is the same one: *"how to distinguish genuine information edge from structural
advantages."*

Nothing here changes that verdict. It does mean an unrelated analyst, on
different data, found the same shape — which is the closest thing to replication
this programme has for that thread.

---

## 8b. Multi-leg fill drag, quantified — 180 round trips, 45,000 spread observations

`/r/algotrading/comments/1rvk302/` · 26 points

Someone logged, for every order, their own model's theoretical mid, the NBBO mid
at submission, and the actual fill. 90 days, ~180 round trips, ~45,000 bid-ask
width observations. The gap between fill and theoretical mid, **by number of
legs**:

| structure | legs | fill vs theoretical mid |
|---|---|---|
| single | 1 | **2–4%** |
| vertical | 2 | **8–12%** |
| iron condor | 4 | **15–22%** |

> *"Four legs, four independent fictions stacked together."*

That drag **was the entire gap** between their backtested and realised returns —
they had spent weeks tuning the model looking for it.

`youtube-signal`'s corpus already carries the qualitative version — *multi-leg
partial fills turn a risk-neutral position directional*. This is the same
statement with a denominator, and it is superlinear in leg count. It is directly
relevant to any two-legged prediction-market structure: the split-sell in §0, the
Kalshi↔Polymarket synthetic arbitrage in §3, and this repo's own bucket-sum
ladder check, which found **1 gross violation in 1,135 scans and unprofitable
net.**

---

## 9. On the Kalshi automation question — weak evidence, honestly labelled

`signal-github`'s single open item is the **KalshiEX Rulebook**: the member
agreement is silent on automation and says the Rulebook governs, and the
Rulebook defeats HTTP and a real browser. Reddit cannot answer that, and this
section exists to say what it *can* answer and how little that is worth.

Searching the whole corpus for Kalshi plus automation, bots, bans and API keys
returns **no report of anyone being restricted for running a bot**, alongside
openly published Kalshi automation — a **281-point r/algotrading post shipping
the source of a Kalshi↔Polymarket arbitrage bot**, an r/Kalshi thread
recommending a free open-source native client you plug your own API key into,
and a general "best API stack" thread naming Kalshi's V2 API for *"automated
prediction market bets"*.

**That is evidence about enforcement, not about permission**, and it is the weak
kind: absence of complaints in a sample that was never designed to find them.
It does not move the Rulebook question at all. Recorded so the next session does
not re-run the same search hoping for more.

Two account-level restrictions **were** found (§4) and neither mentions
automation.

---

## What this section is not

None of the above has been verified against an exchange, a chain or a
statement, except the four URLs in §3 which were fetched. Reddit is a source of
**hypotheses and of criticism**, and the criticism is the part that is hard to
get anywhere else. Treat every number above as a claim carrying its poster's
name, not as a measurement carrying this repo's.
