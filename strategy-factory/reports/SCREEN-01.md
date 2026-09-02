# SCREENING RUN 01 — and not one number here is money

**Run 2026-09-02 01:54 UTC by `strategy-factory/src/screen.py`.**

> **THE BACKTEST CHOOSES. ONLY THE FORWARD TEST COUNTS.** Nothing below is a result, none of it may be sized on, and none of it should be repeated to anyone as an amount of money. It exists to pick candidates.

**31 specs written, 27 LIVE, and 6 of them could actually be run.** That last number is the one that matters and it is small: most specs in this folder need data this project does not have. The list of what was NOT screened, and why, is section 4 - it is the honest half of this report.

## 1. THE PLACEBO ARM — read this before any other number

The same machinery, on the same tape, with **every outcome redrawn from the market's own implied probability**. Prices, spreads and fees stay exactly as recorded; only the thing under test is replaced - whether the outcome is related to anything other than the price.

> ⚠ **THE FIRST PLACEBO I BUILT WAS ALGEBRAICALLY A NO-OP, AND THIS RUN IS WHAT CAUGHT IT.** It shuffled settlement labels within each (family, day) group. Twenty seeds returned **-8.44% every single time, to the decimal.** The reason is one line of algebra: total net = 100 x (number of wins) - sum(ask) - sum(fee), a within-group permutation preserves the number of wins, and ask and fee never depended on the label. **The control could not move.** A placebo that cannot move is not a control, it is decoration, and it would have signed off on every run this engine ever does. Replaced with the null above.

**One note on the mid, because this repo has a hard rule against it.** GUARDS #7 forbids marking or filling at the mid, and nothing here does - every entry is the real recorded ask. The mid appears once, as the market's own estimate of the probability when drawing the null. That is what the null hypothesis literally asserts, and it is not an execution price.

| | return on cash |
|---|---:|
| **real arm** | **-5.11%** |
| placebo median (20 runs) | -6.10% |
| placebo range | -7.36% to -3.13% |
| **null drawn at the ASK** (matched to what we actually pay) | **-2.72%** |
| its range | -4.33% to +0.62% |

**TWO nulls, because one of them is unfair and it is the one that flatters nobody.** The mid null asks *"is the mid the truth?"* while our entries pay the **ask** - so it is advantaged by roughly half a spread before anything else happens, and the real arm should be below it even if the market is perfectly fair. The ask null asks the question that matters: *"given what we actually paid, did the outcomes beat it?"* Both are reported so neither can be quoted alone.

> ⚠ **THE REAL ARM DOES NOT BEAT ITS MATCHED NULL.** Buying indiscriminately at the recorded ask and holding to settlement did no better than the outcomes being drawn from the price we paid. **By the rule fixed in `PREREGISTRATION.md` §3 nothing this run produced may be promoted**, and it is reported that way rather than mined for a subset that looks better. This is also the expected answer: `CLAUDE.md` §9c step 3 says the general, all-markets version is normally flat or negative, and §7 of the pre-registration said so in advance.

## 2. What the tape can actually answer

| | |
|---|---:|
| settled markets with a recorded price | **299360** |
| of those, with a **two-sided quote 60 min before close** | **27691** |
| markets in the screened price and spread band | **7125** |
| distinct EVENTS behind them | **2346** |

> ⚠ **The second row is a finding on its own and it is not good news for trading.** Most settled markets had no two-sided quote an hour before they closed. That is `GUARDS.md` #24 - *the market does not quote a near-certainty* - showing up across the whole exchange rather than in one sport. **A strategy cannot trade what is not quoted**, and any backtest that assumes it can is measuring a market that does not exist.

**Markets and EVENTS are different numbers and both are shown**, because a ladder of strikes on one underlying is one observation, not twenty. LEDGER K003 was retracted for exactly that.

## 3. BREADTH — every category in the census gets a row

⚠ **`GUARDS.md` #24 requires the availability rate to be reported BESIDE the edge, always, and never used as a pass/fail gate** - *an edge measured on 5 out of 100 moments is a statement about those 5 moments*. The **quotable** column is that rate: of the settled markets we have a price for, how many had a two-sided quote when the rule wanted to enter. Read it next to every return on this table.

| category | in index | **quotable** | screened | net per contract | vs null | verdict |
|---|---:|---:|---:|---:|---|---|
| **Climate and Weather** | 288 | **270 (94 in 100)** | **65** (22 events) | -4.77c | -13.4% vs -9.1% | **too few events to say anything (22)** |
| **Commodities** | 12478 | **8093 (65 in 100)** | **330** (89 events) | +7.54c | +22.8% vs -5.6% | **too few events to say anything (89)** |
| **Crypto** | 253493 | **2045 (0.8 in 100)** | **1053** (134 events) | -2.98c | -9.7% vs -8.2% | **at or below its null** |
| **Elections** | 272 | **169 (62 in 100)** | **24** (14 events) | -2.36c | -8.6% vs -8.6% | **too few events to say anything (14)** |
| **Entertainment** | 73 | **22 (30 in 100)** | **3** (1 events) | -15.15c | -100.0% vs -100.0% | **too few events to say anything (1)** |
| **Financials** | 25770 | **10599 (41 in 100)** | **717** (45 events) | -7.05c | -26.1% vs -12.2% | **too few events to say anything (45)** |
| **Mentions** | 31 | **27 (87 in 100)** | **9** (1 events) | +39.18c | +64.4% vs -26.9% | **too few events to say anything (1)** |
| **Sports** | 6955 | **6466 (93 in 100)** | **4924** (2040 events) | -1.87c | -4.1% vs -4.6% | above its null - still not a result |

**A category with a small screened count cannot say anything**, and the count is shown rather than the number being quoted alone.

**2 categories clear the 100-event bar:** **Sports** 2040 events at -1.87c per contract; **Crypto** 134 events at -2.98c per contract.

Those are the only lines on this page with a sample behind them, and they say the dull version does not work.

Everything else is a few days of tape, reported so that nobody mistakes a 89-event number for a finding later.

> ⚠ **ONE LIMITATION THE CRYPTO ROW EXPOSES, AND IT IS MINE NOT THE MARKET'S.** Crypto has **253493 markets in the index and only 1053 that could be screened.** The entry rule takes the last two-sided quote at least 60 minutes before close - and a Kalshi crypto ladder is an HOURLY market, so 60 minutes before its close is at or before the moment it opens. **The fixed entry lead is simply wrong for fast families**, and the near-total absence of crypto here is an artefact of my parameter rather than a fact about crypto. Fixing it means an entry lead expressed as a FRACTION of each market's life, not a constant, and that is a change to make deliberately and re-run - not to tune until something looks good.

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

## 5. THE INVERT SCREEN — is a loser leaking fees, or picking the wrong side?

His idea, and it is computable: *"if we find a purely bad strategy that isn't just getting killed by the fees - pretty much what that's telling us is that this site is picking the wrong side. So we just pick the other side."*

**Two losers look identical on a profit line and are completely different things.** One pays more in costs than its edge is worth. The other is actively wrong, and the other side of it is a real hypothesis. The cost bar is what separates them.

⚠ **INVERTING IS NOT NEGATING**, and that is why this needs arithmetic rather than a minus sign. Buying the other side lifts the OTHER ask, so the inverted trade **pays the spread again and the fee again**. A strategy losing exactly its cost bar loses the same amount inverted.

**The bar is computed at the prices each row actually trades at, never at 50 cents** - the fee at 97c is 0.20c against 2.00c at 50c, and a constant bar would call every cheap strategy anti-predictive.

| category | net per contract | cost bar | gross (picking only) | inverted | invertible? |
|---|---:|---:|---:|---:|---|
| Climate and Weather | -4.77c | +2.48c | -2.29c | -0.11c | no (too few events to act on: 22) |
| Commodities | +7.54c | +3.87c | +11.40c | -15.06c | no (too few events to act on: 89) |
| Crypto | -2.98c | +2.42c | -0.56c | -1.75c | no |
| Elections | -2.36c | +2.54c | +0.19c | -2.56c | no (too few events to act on: 14) |
| Entertainment | -15.15c | +2.99c | -12.17c | +9.40c | **YES** (too few events to act on: 1) |
| Financials | -7.05c | +3.08c | -3.97c | +1.09c | **YES** (too few events to act on: 45) |
| Mentions | +39.18c | +2.82c | +42.00c | -44.85c | no (too few events to act on: 1) |
| Sports | -1.87c | +2.20c | +0.33c | -2.51c | no |

**Whole run:** net -2.10c, cost bar +2.41c, gross +0.30c, inverted -2.64c - **not invertible: it loses about what it costs to trade, which is the fee-leaking case and there is nothing underneath to flip**.

### ⚠ The trap, and it is the same size as the one that governs everything here

**Selecting the worst of N and inverting it is the best-of-N problem in a mirror. It is not a weaker version - it is the same size.** Measured on 16 baseball bots: a bot landing in the worst 2-in-100 tail happens to at least one of 16 with no skill anywhere **28 times in 100**.

So: **8 categories were screened to produce 2 invertible one(s)**, and an inverted strategy is a **NEW** strategy - it gets its own id, its own pre-registration and its own forward test before anything is believed about it. Nothing on this table is promotable.

### The placebo for this screen specifically

**Inverting a strategy that is merely fee-losing must NOT look good**, or the screen is finding noise. The null arm above is exactly that strategy: outcomes drawn from the price paid, so it loses its cost bar and nothing more, by construction.

| | inverted, per contract |
|---|---:|
| **the real arm** | **-2.64c** |
| a merely fee-losing arm, median of 12 | -3.71c |
| its range | -4.33c to -3.29c |

The real arm inverted beats the fee-losing arm inverted. **That is the minimum bar and not a result** - it says the screen can tell the two cases apart, which is a statement about the screen.

## 6. THE TWO STANDARD LENSES — fee curvature, and closing-line value

### Fee curvature: the same edge is worth far more at extreme prices

Kalshi's fee is `0.07 x contracts x p x (1-p)` — **maximised at 50 cents and collapsing at the extremes.** A 2-cent edge at 95c survives as **+1.67c**; the same 2-cent edge at 50c survives as **+0.25c**, nearly seven times less. **The price a strategy trades at is part of its value, not a detail**, and nothing in this engine knew that until now.

**Every row carries its event count**, because a per-contract edge is the number that gets quoted alone and one of these rows sits on a single event.

| category | events | avg price traded | fee at that price | gross edge | **edge after fee** |
|---|---:|---:|---:|---:|---:|
| Climate and Weather | 22 | 35c | 1.59c | -2.29c | -3.88c *(only 22 events - not readable)* |
| Commodities | 89 | 32c | 1.52c | +11.40c | +9.88c *(only 89 events - not readable)* |
| Crypto | 134 | 30c | 1.46c | -0.56c | **-2.03c** |
| Elections | 14 | 27c | 1.37c | +0.19c | -1.19c *(only 14 events - not readable)* |
| Entertainment | 1 | 14c | 0.86c | -12.17c | -13.03c *(only 1 events - not readable)* |
| Financials | 45 | 26c | 1.36c | -3.97c | -5.33c *(only 45 events - not readable)* |
| Mentions | 1 | 59c | 1.69c | +42.00c | +40.31c *(only 1 events - not readable)* |
| Sports | 2040 | 45c | 1.73c | +0.33c | **-1.40c** |

### Closing-line value — a signal that needs no outcomes

Did the entry buy cheaper than the market ended up pricing it? **It needs no settlement data at all**, so it gives a reading long before enough markets settle to measure profit.

| category | events | markets with a close | closing-line value per contract |
|---|---:|---:|---:|
| Climate and Weather | 22 | 13 | -8.19c *(only 22 events)* |
| Commodities | 89 | 141 | +6.50c *(only 89 events)* |
| Crypto | 134 | 630 | +1.68c |
| Elections | 14 | 1 | -1.50c *(only 14 events)* |
| Entertainment | 1 | 1 | -10.00c *(only 1 events)* |
| Financials | 45 | 117 | -3.94c *(only 45 events)* |
| Mentions | 1 | 1 | -2.00c *(only 1 events)* |
| Sports | 2040 | 3314 | -1.10c |

**Negative closing-line value means we bought dearer than the market settled into** — which is what paying the ask does, and is the expected sign for a rule that crosses the spread on every entry. It is reported as a lens, not as a result.

## 7. CAPACITY — what it would actually cost to fill

Walked on the recorded ladder rather than assumed from the touch. A market with no recorded ladder gets **no capacity claim at all**.

**Read the columns carefully: they are the money that ACTUALLY GOES IN, not whether the target was met.** Asking for $500 and getting $38 shows as $38, which is the whole point of walking the book.

| category | markets with a ladder | asking $50, got | asking $200, got | asking $500, got |
|---|---:|---|---|---|
| Climate and Weather | **0** | - | - | - |
| Commodities | **0** | - | - | - |
| Crypto | **0** | - | - | - |
| Elections | 1 | $50 | $200 | **$500** |
| Entertainment | 20 | $50 | $177 | **$376** |
| Financials | 25 | $45 | $45 | **$45** |
| Mentions | 21 | $50 | $200 | **$443** |
| Sports | **0** | - | - | - |

**Where the count is 0 the family has no full-depth ladder on tape** - it is recorded at top of book only, so the question cannot be answered and is not guessed at.

> ⚠ **The Financials row is the one to look at, and it is bad news for size.** Those books absorb about **$45** whether you ask for $50, $200 or $500 - the ladder simply runs out. **A strategy that only exists in the first $45 is a hobby**, which is the test `STRATEGY_FACTORY.md` stage 6 puts first, and it is answerable now rather than after a month of forward testing.

## 8. What this run does NOT establish

- **Nothing about whether any strategy works.** 8 days of tape, and the forward test has not started.
- **Nothing about the specs that could not be run** - their absence here is a statement about our data, not about their merit.
- **Nothing that survives being quoted without its screened count.** 31 specs were written to produce this page.
- **The entry rule is one fixed choice** - the last two-sided quote at least 60 minutes before close. It was fixed before the run and NOT swept. Sweeping the entry time and reporting the best is the best-of-N trap applied to a parameter instead of a strategy.

