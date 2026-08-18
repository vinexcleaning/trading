# THE STRATEGY FACTORY — the constant strategy creation plan

**His idea, 2026-08-18:** use the extractors, use Claude's reasoning, come up
with strategies, backtest them, then forward paper-trade them — so that a month
from now there are hundreds of strategies, dozens per market, across everything
Kalshi lists rather than sports alone, running constantly.

**Status: PLAN ONLY. Nothing built. Awaiting his go.**

---

## 0. WHAT THE AUDIT FOUND, BECAUSE IT CHANGES THE PLAN

### 0a. WE RECORD 19 OF KALSHI'S 12,396 MARKET FAMILIES. That is the bottleneck.

`bot-hunt/data/record.db` is **62 GB** and is the best asset in this repo:
Kalshi bid/ask **with depth**, Polymarket bid/ask, and Pinnacle prices, on one
clock.

| | |
|---|---|
| recording since | **2026-08-04**, 1,369 cycles, still alive |
| Kalshi tickers captured | **9,610** |
| Kalshi **series** captured | **19** |
| Kalshi series that **exist** | **12,396** (census 2026-08-03, `common/kalshi_fees.py`) |

**About one market family in every 650.** And it cannot be fixed later: Kalshi's
history window is roughly 69 days and rolling, and a closed market 404s forever.

> **Widening the recorder is the highest-value free action available today. It
> outranks every extractor upgrade, because the strategy work a month from now
> is limited by what gets captured this week.**

The 19 are a decent spread — baseball games/totals/first-inning, tennis (ITF
men and women, ATP, WTA), esports (CS2, League, Valorant), soccer (Argentine,
Mexican, Colombian, Champions League, Premier League), weather (NY and Chicago
high temperature). **No crypto. Nothing economic, political or entertainment.**

### 0b. The chats are mostly idle. That is capacity.

| chat | state | free for factory work? |
|---|---|---|
| **devig** | queue empty, owns `bot-hunt` — the recorder | **yes, and owns the urgent job** |
| **signal** | extractors fixed, two candidates untested | **yes** |
| **reopen** | audit finished, audits on arrival now | **yes** |
| **extractors** | blocked on one free signup | partly |
| **soccer** | closed 2026-08-11 | **dormant, reusable** |
| tennis | 587 of 2,500 matches | no, running |
| mlb | re-pulling 12,059 markets at minute resolution | no — it is the data engine |
| livedesk | live money, open instructions | **no, and must stay out** |

### 0c. Free extractor upgrades, ranked by value to the factory

1. **Widen the recorder** (`devig`) — not an extractor, still the answer. Free,
   and the only irreversible one.
2. **Bright Data** — 5,000 records a month, free, no card, stops rather than
   billing. Covers X, TikTok and Instagram. Blocked only on a signup.
3. **Bluesky needs no account** — proven on seven clients, two addresses.
4. **The two `signal` fixes are already in** — its tools now say out loud when
   they were refused instead of reporting "found nothing".

**Nothing here costs money.** Apify (40c per thousand X posts) stays on the
shelf until something specific needs it, and he gets the arithmetic first.

---

## 1. THE ONE THING THAT WILL KILL THIS PLAN — and he is right that it is not coin-flipping

**He said:** *"If something comes up with a thirty percent edge on multiple
trades, then I'm almost sure we're not flipping a coin."*

**Measured, 20,000 runs.** One strategy, 100 bets at 50 cents, **no skill at
all**, paying the real fee:

- lands between **-18.8% and +12.1%** 90 times in 100
- reaches **+30%**: **1 time in 10,000**

> **He is right. A single strategy showing +30% over 100 trades is not luck.**

**But the factory tests thousands and looks at the best. That is a different
question, and it is the only real danger here:**

| strategies generated, **all with zero skill** | best one typically looks like | shows +30% or better |
|---|---|---|
| 10 | +10.1% | never |
| 50 | +17.9% | never |
| 200 | +23.7% | 5 in 100 |
| 500 | +25.6% | 9 in 100 |
| **2,000** | **+29.5%** | **37 in 100** |

**At the scale he wants, the winner looks like a +30% edge even if nothing has
any edge.** That is the specification, not an objection.

### The cure is already in his own design

He described backtesting **and then forward paper trading**. That second step is
exactly the fix:

> **A strategy chosen out of 2,000 is worth nothing. The same strategy run
> forward on games that did not exist when it was chosen is worth everything.**

**Rule one: the backtest chooses; only the forward test counts.** Backtest
numbers are never reported as money, never sized on, never shown as a result.

---

## 2. THE FACTORY — six stages, running continuously

```
  [1] WIDEN      record more of Kalshi, every day, forever
  [2] GENERATE   Claude + extractors -> strategy specs in a fixed format
  [3] SCREEN     cheap backtest on recorded tape. Kills most. Reports nothing.
  [4] REGISTER   survivors written down and SEALED before going forward
  [5] FORWARD    paper trade live on unseen data. THIS is the result.
  [6] PROMOTE    only a forward survivor is ever discussed as real
```

### Stage 1 — WIDEN THE RECORDER (`devig`) — start now, free

- Enumerate every Kalshi series currently listed and open.
- Rank by whether a strategy could ever trade it: two-sided, has depth, settles
  on something knowable.
- **Record everything that passes** — crypto, weather, economics, politics,
  entertainment. His explicit ask.
- Keep the existing 19 untouched. **Add, never replace.**
- **Report what was dropped and why.**

**Constraint: disk.** 62 GB in 14 days on 19 families. Widening 100-fold naively
eats the machine. **Tiered rate** — full depth on families a strategy is live
on, slower heartbeat on the long tail. Write the numbers down before turning it
on.

### Stage 2 — GENERATE (`signal` plus whoever owns the market)

**A strategy is a written spec, before any data is touched.** Fixed format so
hundreds can be handled mechanically: id · market family · what it bets on ·
entry rule · exit rule · size rule · what would make it wrong · who suggested
it · date.

**Four sources, all four run:**

1. **The extractors** — GitHub repos that really trade, YouTube methods with
   timestamps, Reddit and Discord claims.
2. **Claude's own reasoning** — mechanisms in market structure: how a ladder is
   priced, when a family opens, what a settlement source actually measures,
   where a market maker is forced to quote.
3. **The dead ideas** — `reopen` found **51 of 612 claims closed for the wrong
   reason**. A stocked pond nobody has fished.
4. **His own domain knowledge** — the one input this repo cannot generate.

**His dimensions are part of the spec, not afterthoughts:** hold to settlement ·
sell at a level · buy more at a level · which level · one mentality or two ·
what happens when two disagree.

### Stage 3 — SCREEN, and it reports nothing to him

- **Real bid and ask** from `k_book`. Never the mid.
- **Real fees from `common/kalshi_fees.py` only** — Guard #6, enforced by a test.
- **Capacity — his low-liquidity question.** `k_book` carries `bid_size`,
  `ask_size`, `depth5_yes`, `depth5_no`. So *"what if I put $500 into this thin
  market"* is directly answerable: walk the book, report what it actually costs
  to fill.
- **A placebo arm in every run** — same machinery, shuffled labels. If it finds
  an edge in noise, everything that run produced is void.

### Stage 4 — REGISTER, the stage that makes the rest honest

`PREREGISTRATION_<NAME>.md`, committed **before** the forward test starts: the
rule in full · unit of observation · how many observations before it can be
judged · start date · **what result makes us drop it.**

**Also recorded: how many strategies were screened to produce this one.** That
number turns "+30%" into either a finding or a coincidence, and it is the number
that always goes missing.

### Stage 5 — FORWARD PAPER TRADE — the only stage that produces a result

- Live markets, **no money, no keys**, enforced by a copied
  `test_paper_only.py`.
- Every strategy carries its **no-skill range** printed beside its result, the
  way `tennis` now does for all 17 bots.
- **Not "working" until the forward result sits outside that range**, however
  good the backtest was.

### Stage 6 — PROMOTE

Only a forward survivor is discussed as real, and the first question is
capacity: at his actual bankroll, in that market's actual depth, how much can it
hold? **A great edge in a market that takes $12 is a hobby.**

---

## 3. THE RULES, SHORT ENOUGH TO HOLD

1. **The backtest chooses. Only the forward test counts.**
2. **Report how many strategies were screened, every time.**
3. **A placebo arm in every run, or the run is void.**
4. **Real bid and ask, real fees, real depth. Never the mid.**
5. **Add to the recorder, never narrow it, and say what was dropped.**
6. **No money, no keys, anywhere in the factory. Enforced by a test.**
7. **Every dead idea ends with a list of what it did NOT test.**

---

## 4. WHAT HE HAS TO DO

1. **Say go.**
2. **One free Bright Data signup** — no card, no payment method.

**That is the whole list.** If a paid tier ever becomes the blocker he gets the
arithmetic — what free allows, what paid costs, what it would have to be worth —
and he decides.

---

## 5. WHAT COULD GO WRONG — written before starting

- **Disk.** The most likely thing to actually break. Tiered rates or bust.
- **Best-of-N** is handled by stage 5 and nothing else. If anyone reports a
  backtest number as money, the factory is worthless that day.
- **Generation is cheap, screening is not.** Thousands of specs against 62 GB
  needs the tape indexed first.
- **The forward test is slow by nature.** A month gives real answers on
  fast-settling families and nothing on slow ones. Say which is which up front.
- **Kalshi's 69-day window** is a permanent horizon on every backtest. Design
  around it; it is not a bug to fix.
