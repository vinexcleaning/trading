# bot-forensics — what actually happened on the night the bot made money

Reconstructed 2026-08-05 from the live account's own exchange records in
`kalshi-inplay-bot/`. Read-only throughout. No order endpoint was touched, the
bot was not started, and `TRADING_DISABLED` was left in place.

---

## The headline, in one paragraph

**There was no profitable night. There was a profitable *first sixty matches*,
and the split between "profitable" and "not" was found by cutting the record at
the maximum of its own equity curve — which is the most selection-biased cut
available.** The bot's realised P&L over its entire life is **−$6.92 across 108
matches**, mean **−$0.064 per match** (se $0.284, t = −0.23). Its running total
did peak at **+$32.19**, at 13:32 UTC on 28 Jul, after 60 matches. It then lost
$39.12 over the remaining 48. Reordering those same 108 results at random
produces a peak of $32.19 or better **5.2%** of the time and a before/after gap
at least as large as the observed one **27%** of the time. A zero-edge process
shows the same rising-then-falling shape **85%** of the time.

---

## Task 1 — the reconstruction

### What the records are, and which one is authoritative

| file | what it is | used for |
|---|---|---|
| `_fills.json` (389) | every execution, with the fee Kalshi actually charged | timing, entry price, sequence |
| `_orders.json` (428) | every order incl. 98 cancelled | **sizing** — the bot's intent survives even when a fill does not |
| `_settlements.json` + `_settle.json` (142) | Kalshi's own settlement report | **P&L. This is the authority.** |
| `_trades.json`, `_18h.json` | the bot's own reconstructions | treated as claims, checked, not relied on |

**How Kalshi books a sale had to be established before any P&L could be
computed**, because it flips the sign of most of the record. There are 204
`buy/yes` fills, 177 `sell/no`, and only one `sell/yes`. If `sell/no` opened a
new short the account would carry enormous unclosed positions. It does not:
Kalshi books "sell a YES you own" as "buy the NO". Holding one YES and one NO
pays exactly $1.00 whatever happens, so the pair is a closed round trip:

```
payout = yes_ct * v + no_ct * (1 - v)          v = value/100, in {0, 1}
pnl    = payout - yes_cost - no_cost - fee
```

Three independent confirmations: `yes_price + no_price = 1.0000` on all 389
fills; the settlement record's `revenue` field equals `(yes_ct − no_ct) × value`
in cents on every row, which is the residual rebuilt from the fills; and the
formula reproduces the bot's own `_trades.json` P&L to the cent.

**`fee_cost` on a settlement row is the cumulative TRADING fee for that ticker,
not an extra settlement charge** — verified equal to the sum of that ticker's
fill fees. It is not double counted.

Eight markets were traded after the last settlement pull. Six are closed round
trips and need no outcome; two carried an open residual and were resolved from
Kalshi's public market endpoint (`out/late_outcomes.json`).

### Separating the bot from the hand

**The account was also traded by hand, and pooling the two makes the whole
question meaningless.** `_trades.json` contains BTC 15-minute crypto, three
soccer markets and an esports market at 100–2,326 contracts, against the bot's
7–25.

The classifier is structural and cannot see the outcome. A BUY order is the
bot's iff

1. `side == yes` — the engine never buys NO; all four `buy/no` are manual;
2. `10c ≤ price ≤ 90c` — manual buys are marketable limits typed at **99c**, or
   1–6c longshots;
3. `$4.60 ≤ qty × price ≤ $6.30` — the engine sizes `qty = int(stake/price)`.

> **The first version of this split used notional alone and got it wrong in the
> most expensive possible place.** A hand-placed 15.5-contract NO longshot at 6c
> on `SHIDON` cost $0.93 — bot-sized — and returned **+$14.51**, which is half
> the apparent bot total. Rule 1 removes it. A classifier that misfires on the
> single largest winner is not a classifier.

### The configuration that was running

`kalshi-inplay-bot` had **no version control at all** until 2026-08-03, so git
does not reach the night. But `tennis_engine.py` is commented as a dated
changelog, and the order record measures the rest.

| parameter | value on 27–28 Jul | evidence |
|---|---|---|
| `bankroll` | **stepped ~$102 → ~$118 → $125** during 27 Jul | order sizes; see below |
| `stake_pct` | 5 | `$6.25 = 125 × 5%` reproduces **113 of 113** sizes on 28 Jul |
| `min_entry_price` | **none** | "Floor added 28 Jul"; 25c and 34c entries exist in the record |
| `max_favorite_price` | **85** | "75c, not 85c … changed 28 Jul"; entries up to 84c exist |
| `favorite_exit_drop` | **22c** | "38c, widened from 22c on 28 Jul" |
| `max_open_positions` | **10** | "Cut 10 → 4 on 28 Jul"; 5 simultaneous entries observed |
| `favorite_target_price` | 95 | 35 resting sells at exactly 95c |
| `max_daily_loss_pct` | **0 (off)** | STATUS.md; nothing stopped the 3-leg martingale |
| `max_contracts`, `reentry_cooldown_sec`, `max_reentries_per_event` | **did not exist** | added 3 Aug |
| `max_spread` | 3 | unchanged |

> **The bankroll stepped up, and that is itself a finding.** `gui.py` takes
> `--bankroll` as a command-line argument and nothing updates it while running.
> Order sizes on 27 Jul imply a stake of ~$5.1 at 05:36–06:01, ~$5.9 at
> 06:19–06:24, and exactly $6.25 from 07:44 onward. **The user was restarting
> the bot with a bigger bankroll as the account grew** — which is a discretionary
> size-up on a winning run, layered on top of the strategy. It means the
> profitable early trades were sized smaller than the later losing ones.

### The result

| | matches | P&L | contracts | capital | fees |
|---|---|---|---|---|---|
| **bot** | **108** | **−$6.92** | 1,237 | $1,209.51 | $24.41 |
| manual | 31 | +$98.94 | 1,814 | $1,371.54 | $30.66 |
| mixed | 1 | +$5.19 | 20 | $14.70 | $0.28 |

**The hand-trading made the money. The bot did not.** That is the single most
load-bearing correction here: the user remembers the account going up, and it
did — by about $99 on 25–26 July, before the bot placed its first order at
**05:58 UTC on 27 July**.

Bot distribution, one observation per match:

```
n 108   mean -$0.0641   median +$0.2602   sd $2.9526   se $0.2841   t -0.23
winners 54/108 (50.0%)        -0.56c per contract
worst -$8.79 (SAGLEV)         best +$6.01 (MAJPAU)
```

Clustering at **entry burst** rather than match (the scanner fires everything
that qualifies in one pass, so matches entered seconds apart share one feed
state and one score snapshot) gives 74 bursts from 108 matches, mean −$0.094,
95% CI **[−$0.97, +$0.78]**. **Effective n is 74, not 108, and not 1,237.**

Stress test — this is a distribution held up by its tails in both directions:

| | total |
|---|---|
| all 108 | −$6.92 |
| drop 1 worst | **+$1.87** |
| drop 1 best | −$12.94 |
| drop 5 each end | +$5.89 |

---

## Task 2 — night versus day

### The argmax null: the split is not a finding

The "it worked overnight and stopped when the daytime tournaments began" story
maps onto a cut at the peak of the cumulative curve. **The argmax is by
construction the point that maximises the before-minus-after gap.** Testing it
against the same 108 numbers in random order:

| | observed | null median | null 95th | p |
|---|---|---|---|---|
| peak of the equity curve | **+$32.19** | +$13.40 | +$32.39 | **0.052** |
| mean(before) − mean(after) | **+$1.3515** | +$0.9971 | +$2.3292 | **0.272** |

**A zero-drift process with this dispersion shows a positive argmax gap 85% of
the time.** The null used here already contains the true total and the true
dispersion — it destroys only the order. The night/day story rests on the order
the matches happened to arrive in.

### Splitting on the clock instead

Night = 20:00–07:59 UTC, day = 08:00–19:59, fixed before looking.

| | n | total | mean | c/contract | permutation p |
|---|---|---|---|---|---|
| night | 19 | +$15.18 | +$0.799 | +7.16c | 0.157 |
| day | 89 | −$22.11 | −$0.248 | −2.16c | 0.156 |

Welch t = +1.54, p = 0.133. **The sign is in the direction the user remembers.
The magnitude is not distinguishable from noise at n = 19 night matches.**

### All buckets, with a cost bar per bucket

Cost bar measured from the recorder tapes (27,083 usable rows, 27–28 Jul, 342
markets), restricted to the 40–80c band the bot actually traded, as
`spread + entry fee + exit fee` from `common/kalshi_fees.py`. It is **≈5c per
contract round trip in every bucket** — median spread is 1c almost everywhere;
the fee is 2c in and 2c out at a ~62c median ask.

**But the mean spread is not the median, and this is where the tiers separate:**

| tier | mean spread | night mean spread |
|---|---|---|
| ATP | 1.17c | — |
| WTA | 1.24c | 1.24c |
| Challenger | 1.57c | 1.48c |
| ITF-M | 2.80c | **5.26c** |
| ITF-W | 4.48c | **7.16c** |

**Overnight ITF books are two to six times wider than daytime ATP/Challenger
books.** The night/day comparison is confounded at source, exactly as the brief
warned, and it is confounded *against* the night: the bucket that looks better
is the one with the worse book.

**13 buckets tested by label permutation (200,000 shuffles each).
BH-FDR at 5%: 0 discoveries.** 12 of 21 t-tested buckets had a positive mean
against a chance expectation of 10.5 (binomial p = 0.66).

> ### ⚠ Which arm this "0" comes from — added 2026-08-05 on re-run
>
> **`t2b_nightday.py` prints "buckets tested: 21 · BH discoveries at FDR 5%: 3"
> to screen, and it always did — the figure is in the committed
> `out/t2b_nightday.txt` at line 93.** The "0 of 13" quoted above is the
> *permutation* arm (`t2c_costbar.py`); the "3" is the *parametric* arm over a
> larger family that adds the tier×night interaction cells. Both are real
> outputs of this project and only one was ever written up.
>
> **The 0 is the right answer and the 3 is the broken test**, for three reasons
> that should be checked rather than taken on trust:
>
> 1. The three "discoveries" are **n = 4, 5 and 6**. A t-test there divides by a
>    realised standard error that is itself almost unmeasured, and is wildly
>    anti-conservative. For the 04–07 bucket the parametric p is **0.0002** and
>    the permutation p on the same five matches is **0.0477 — 240× larger.**
> 2. **One of the three is a *loss* bucket** — WTA\|day, n = 4, mean −$2.89, all
>    four losers. It "clears" only because four consistent losses have small
>    variance. Nobody would call that a discovery.
> 3. The other two — 04–07 UTC and Challenger\|night — are **the same six trades
>    seen twice**, as this file already notes.
>
> Recorded rather than quietly fixed because a reader who runs the script sees
> the 3. Ledgered as **[B005a](../LEDGER.md#section-7--bot-forensics-the-night-the-live-tennis-bot-made-money)**.

The only bucket under p = 0.05 on permutation is **04:00–07:00 UTC: n = 5,
+$11.63, all five winners, p = 0.048** — and it does not survive BH. Those five
matches are the first five the bot ever placed, on the morning of 27 July, and
they reappear inside "Challenger" and inside "night", so the three apparently
independent signals are three views of the same six trades.

> The prior tennis study in this repo found **0 of 25 time/tier buckets
> clearing**, with 7 positive where 12.5 were expected. This one finds **0 of 13
> clearing**, with 12 of 21 positive where 10.5 were expected. Same answer,
> reached on completely different data.

---

---

## The martingale DID appear in the profitable stretch, and it went 7 for 7

The brief asked whether the winning nights contain the same re-entry pattern as
the SAGLEV disaster, "because a martingale that happens to win looks identical
to skill". **They do, and it did.**

14 of 101 traded markets had more than one filled entry. **Twelve of the
fourteen averaged DOWN** — each leg cheaper than the last, and because the stake
is a fixed number of dollars, each leg therefore *larger* than the last.

| | matches | total P&L | mean |
|---|---|---|---|
| averaged DOWN (martingale) | 12 | **−$16.43** | −$1.369 |
| averaged UP | 2 | −$0.13 | −$0.064 |
| single entry | 94 | **+$9.63** | +$0.102 |

**The bot's entire loss is the twelve averaging-down sequences.** Strip them out
and the other 94 matches made $9.63 — still nothing, but not a loss.

And before the equity peak:

| ticker | legs | sizes | P&L |
|---|---|---|---|
| KASFER | 66c → 37c | 9 → 16 | +$0.52 |
| JIXKOX | 83c → 59c | 6 → 10 | +$0.56 |
| HUDPED | 68c → 42c | 9 → 14 | +$0.68 |
| ZHUSHE | 69c → 49c | 9 → 12 | +$1.09 |
| KRUBOU | 69c → 39c | 9 → 16 | +$1.15 |
| CEXSHA | 38c → 24c | 16 → 26 | +$1.29 |
| FUNSHA | 46c → 29c | 13 → 21 | +$1.33 |

**Seven averaging-down sequences before the peak, seven winners, +$6.63.** Then
five after it, for roughly −$23. The mechanism did not change. The market did.

That is the textbook martingale signature: a run of small wins that look like
the strategy working, terminated by one loss larger than all of them. SAGLEV
alone (−$8.79) is bigger than all seven early wins combined.

One correction to the existing record: **the SAGLEV legs were 749s and later
apart, not 24s.** The 24s and 23s figures in `STATUS.md` and in
`tennis_engine.py`'s post-mortem comment are the gaps between the *stop-out
fill* and the *re-entry*, which is the right number for the re-arm question.
The gap between one *entry* and the next was 12–13 minutes. No re-entry anywhere
in the record was under 60 seconds from the previous entry. The fix that shipped
(`reentry_cooldown_sec = 900`) still blocks all twelve, so nothing about the
patch changes — but the "24 seconds later" framing overstates how frantic it
looked.

---

## The score feed was arriving after the market had already moved

`STATUS.md` records the staleness bug as a fact but nobody had measured its
size. It can be measured from the recorder tape, with no new data.

**The test.** If the score feed is late, then on the tick where our recorded
score finally changes, the market will *already* have repriced — because
everyone watching the actual match repriced first. So take every game/set change
in the tape and measure the price move in the mid, oriented so that positive
means "in the direction the score change implies".

4,398 score-change events, 305 markets, recorder polling every **60 seconds**:

| window | mean move |
|---|---|
| ticks −8 → −6 (placebo, ~5 min before) | **+0.18c** |
| ticks −6 → −3 (placebo, ~3 min before) | +1.39c |
| **ticks −3 → 0 (our feed catches up)** | **+4.68c** |
| ticks 0 → +3 (after) | **+0.17c** |

**Only 2.6% of the repricing happened after our snapshot showed the new score.**
The placebo windows confirm this is not ordinary momentum: five minutes earlier
the drift is +0.18c, essentially nothing. The move is sharply localised to the
three minutes immediately before the feed updated, and then it stops.

By tier — mean cents before / after:
ATP 6.62 / 0.86 · WTA 6.66 / −0.12 · Challenger 5.93 / 0.49 · ITF-W 4.97 / −0.34 ·
ITF-M 3.02 / 0.02.

> **What this does and does not prove.** Part of that move is legitimate market
> anticipation — a market prices a game as it is being won, not when it is
> logged. So "+4.68c before" is a mixture of feed lag and honest anticipation,
> and this measurement cannot separate them at 60-second resolution.
> **It does not need to.** The operative fact for a bot that trades on the
> snapshot is the last row: **by the time the bot could see the score change,
> the price move it was supposed to trade had finished.** Whatever the cause,
> the entry signal arrived after the event it was meant to predict.

This is the mechanism behind Verdict C, and it makes the direction of the
staleness bias predictable rather than unknown: the bot was systematically
buying *after* the news, i.e. paying the informed side.

---

## Caveats that apply to every number above

1. **The score-staleness bug was live for this entire window.** `fetched_at` was
   stamped at cache read, so the 30-second freshness guard never rejected
   anything. **No live entry result here is a valid test of the entry logic.**
   The direction of that bias is not obvious and is examined separately.
2. **n = 108 matches, effective n = 74 bursts, over 39 hours.** Nothing in this
   file is powered to detect an effect smaller than about $1 per match.
3. **The martingale is present and it is not confined to SAGLEV** — see "The
   martingale DID appear in the profitable stretch" above, and `out/multileg.csv`
   for the twelve sequences. (This pointed at a `MARTINGALE.md` that was never
   written; the analysis is in this file. Ledgered as
   [B007](../LEDGER.md#section-7--bot-forensics-the-night-the-live-tennis-bot-made-money).)
4. The manual/bot split, though structural, is a judgement. Every number is
   reproducible from `out/` and the classifier is one function.
