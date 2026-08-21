# SCREENING RUN 01 — and not one number here is money

**Run 2026-08-21 04:25 UTC by `strategy-factory/src/screen.py`.**

> **THE BACKTEST CHOOSES. ONLY THE FORWARD TEST COUNTS.** Nothing below is a result, none of it may be sized on, and none of it should be repeated to anyone as an amount of money. It exists to pick candidates.

**31 specs written, 27 LIVE, and 6 of them could actually be run.** That last number is the one that matters and it is small: most specs in this folder need data this project does not have. The list of what was NOT screened, and why, is section 4 - it is the honest half of this report.

## 1. THE PLACEBO ARM — read this before any other number

The same machinery, on the same tape, with **every outcome redrawn from the market's own implied probability**. Prices, spreads and fees stay exactly as recorded; only the thing under test is replaced - whether the outcome is related to anything other than the price.

> ⚠ **THE FIRST PLACEBO I BUILT WAS ALGEBRAICALLY A NO-OP, AND THIS RUN IS WHAT CAUGHT IT.** It shuffled settlement labels within each (family, day) group. Twenty seeds returned **-8.44% every single time, to the decimal.** The reason is one line of algebra: total net = 100 x (number of wins) - sum(ask) - sum(fee), a within-group permutation preserves the number of wins, and ask and fee never depended on the label. **The control could not move.** A placebo that cannot move is not a control, it is decoration, and it would have signed off on every run this engine ever does. Replaced with the null above.

**One note on the mid, because this repo has a hard rule against it.** GUARDS #7 forbids marking or filling at the mid, and nothing here does - every entry is the real recorded ask. The mid appears once, as the market's own estimate of the probability when drawing the null. That is what the null hypothesis literally asserts, and it is not an execution price.

| | return on cash |
|---|---:|
| **real arm** | **-8.55%** |
| placebo median (40 runs) | -7.33% |
| placebo range | -10.39% to -3.34% |
| **null drawn at the ASK** (matched to what we actually pay) | **-3.80%** |
| its range | -6.56% to -0.13% |

**TWO nulls, because one of them is unfair and it is the one that flatters nobody.** The mid null asks *"is the mid the truth?"* while our entries pay the **ask** - so it is advantaged by roughly half a spread before anything else happens, and the real arm should be below it even if the market is perfectly fair. The ask null asks the question that matters: *"given what we actually paid, did the outcomes beat it?"* Both are reported so neither can be quoted alone.

> ⚠ **THE REAL ARM DOES NOT BEAT ITS MATCHED NULL.** Buying indiscriminately at the recorded ask and holding to settlement did no better than the outcomes being drawn from the price we paid. **By the rule fixed in `PREREGISTRATION.md` §3 nothing this run produced may be promoted**, and it is reported that way rather than mined for a subset that looks better. This is also the expected answer: `CLAUDE.md` §9c step 3 says the general, all-markets version is normally flat or negative, and §7 of the pre-registration said so in advance.

## 2. What the tape can actually answer

| | |
|---|---:|
| settled markets with a recorded price | **72495** |
| of those, with a **two-sided quote 60 min before close** | **7645** |
| markets in the screened price and spread band | **1595** |
| distinct EVENTS behind them | **612** |

> ⚠ **The second row is a finding on its own and it is not good news for trading.** Most settled markets had no two-sided quote an hour before they closed. That is `GUARDS.md` #24 - *the market does not quote a near-certainty* - showing up across the whole exchange rather than in one sport. **A strategy cannot trade what is not quoted**, and any backtest that assumes it can is measuring a market that does not exist.

**Markets and EVENTS are different numbers and both are shown**, because a ladder of strikes on one underlying is one observation, not twenty. LEDGER K003 was retracted for exactly that.

## 3. BREADTH — every category in the census gets a row

⚠ **`GUARDS.md` #24 requires the availability rate to be reported BESIDE the edge, always, and never used as a pass/fail gate** - *an edge measured on 5 out of 100 moments is a statement about those 5 moments*. The **quotable** column is that rate: of the settled markets we have a price for, how many had a two-sided quote when the rule wanted to enter. Read it next to every return on this table.

| category | in index | **quotable** | screened | net per contract | vs null | verdict |
|---|---:|---:|---:|---:|---|---|
| **Climate and Weather** | 44 | **28 (64 in 100)** | **6** (3 events) | +1.67c | +3.4% vs -31.0% | **too few events to say anything (3)** |
| **Commodities** | 3975 | **3004 (76 in 100)** | **130** (37 events) | +5.85c | +20.9% vs -17.6% | **too few events to say anything (37)** |
| **Crypto** | 59401 | **286 (0.5 in 100)** | **130** (34 events) | -5.02c | -15.0% vs -8.1% | **too few events to say anything (34)** |
| **Elections** | 40 | **5 (12 in 100)** | **1** (1 events) | +5.00c | +5.3% vs +5.3% | **too few events to say anything (1)** |
| Entertainment | 20 | 0 (0.0 in 100) | 0 | - | - | nothing in the price/spread band |
| **Financials** | 7320 | **2770 (38 in 100)** | **187** (9 events) | -12.30c | -48.9% vs -12.8% | **too few events to say anything (9)** |
| **Sports** | 1695 | **1552 (92 in 100)** | **1141** (528 events) | -2.99c | -6.5% vs -6.5% | **at or below its null** |

**A category with a small screened count cannot say anything**, and the count is shown rather than the number being quoted alone.

**The only category with a real sample is Sports: 528 events, -2.99c per contract.** That is the one line on this page with anything behind it, and it says the dull version does not work.

Everything else is a few days of tape, reported so that nobody mistakes a 37-event number for a finding later.

> ⚠ **ONE LIMITATION THE CRYPTO ROW EXPOSES, AND IT IS MINE NOT THE MARKET'S.** Crypto has **59401 markets in the index and only 130 that could be screened.** The entry rule takes the last two-sided quote at least 60 minutes before close - and a Kalshi crypto ladder is an HOURLY market, so 60 minutes before its close is at or before the moment it opens. **The fixed entry lead is simply wrong for fast families**, and the near-total absence of crypto here is an artefact of my parameter rather than a fact about crypto. Fixing it means an entry lead expressed as a FRACTION of each market's life, not a constant, and that is a change to make deliberately and re-run - not to tune until something looks good.

## 4. WHAT WAS NOT SCREENED, AND WHY — the honest half

**21 of 27 LIVE specs could not be run.** Every one still counts toward the screened total; what it does not do is produce a number nobody could defend.

| spec | why not |
|---|---|
| `SF001` | needs strikes GROUPED into ladders per event, plus tier A depth on both legs at the same instant. The grouping code does not exist yet. |
| `SF002` | same as SF001, and additionally needs a proven-complete tiling - the exact check whose absence retracted LEDGER C014. |
| `SF003` | needs a fill model for a RESTING order. The tape records the book, not whether our hypothetical quote would have been hit, and inventing that model is how a maker strategy flatters itself. |
| `SF004` | same resting-order fill model as SF003. |
| `SF007` | needs the publication instant of each settlement source. Not on tape and not in the Kalshi metadata. |
| `SF008` | already run as a canary rather than a trade - 85,498 snapshots, 0 crossed books (reports/RECORDER_LIVE.md). Nothing to screen. |
| `SF009` | needs spread and win markets PAIRED per game. The join is proven (32 of 32 NFL events) but the pairing code does not exist yet. |
| `SF010` | needs a margin ladder summed per race and paired to a winner market. Same missing grouping code as SF001. |
| `SF014` | unit is the SPEECH, and the tape has no speech calendar. Grouping word markets by event is possible; dating the speech is not. |
| `SF017` | needs all 30 MLB team ladders quoted at one instant plus games played to date. Neither is derivable from this tape alone. |
| `SF018` | needs GOAL TIMES and per-club behaviour history. No goal data in this project at all. |
| `SF019` | needs a fixture list to count games in the last 10 days. |
| `SF020` | needs line-up publication times. |
| `SF021` | needs goals scored per club and an opponent-quality table. |
| `SF022` | needs the same per-competition goal data as SF021. |
| `SF100` | tennis chat's spec - needs match-state data this project has not got. Left for the chat that wrote it. |
| `SF101` | tennis chat's spec - same. |
| `SF102` | tennis chat's spec - complement pairing, needs both player markets grouped per match. |
| `SF103` | tennis chat's spec - needs player history. |
| `SF110` | tennis chat's spec - needs an exit simulation. |
| `SF111` | tennis chat's spec, and it is already a FORWARD result rather than a candidate: 17 bots, 1,037 settled matches, every one inside its own no-skill range. |

**The pattern is one thing, and it is worth naming: almost every unscreenable spec needs data ABOUT THE WORLD rather than about the book** - goal times, club identities, fixture lists, speech calendars, line-up announcements. The recorder captures prices beautifully and captures none of that. **That is the single biggest constraint on this project and it was not visible until screening was attempted.**

## 5. CAPACITY — what it would actually cost to fill

Walked on the recorded ladder rather than assumed from the touch. A market with no recorded ladder gets **no capacity claim at all**.

**Read the columns carefully: they are the money that ACTUALLY GOES IN, not whether the target was met.** Asking for $500 and getting $38 shows as $38, which is the whole point of walking the book.

| category | markets with a ladder | asking $50, got | asking $200, got | asking $500, got |
|---|---:|---|---|---|
| Climate and Weather | 17 | $50 | $192 | **$393** |
| Commodities | **0** | - | - | - |
| Crypto | 2 | $50 | $125 | **$275** |
| Elections | **0** | - | - | - |
| Financials | 155 | $38 | $38 | **$38** |
| Sports | **0** | - | - | - |

**Where the count is 0 the family has no full-depth ladder on tape** - it is recorded at top of book only, so the question cannot be answered and is not guessed at.

> ⚠ **The Financials row is the one to look at, and it is bad news for size.** Those books absorb about **$38** whether you ask for $50, $200 or $500 - the ladder simply runs out. **A strategy that only exists in the first thirty-eight dollars is a hobby**, which is the test `STRATEGY_FACTORY.md` stage 6 puts first, and it is answerable now rather than after a month of forward testing.

## 6. What this run does NOT establish

- **Nothing about whether any strategy works.** Two days of tape, no category near 100 settled units, and the forward test has not started.
- **Nothing about the specs that could not be run** - their absence here is a statement about our data, not about their merit.
- **Nothing that survives being quoted without its screened count.** 31 specs were written to produce this page.
- **The entry rule is one fixed choice** - the last two-sided quote at least 60 minutes before close. It was fixed before the run and NOT swept. Sweeping the entry time and reporting the best is the best-of-N trap applied to a parameter instead of a strategy.

