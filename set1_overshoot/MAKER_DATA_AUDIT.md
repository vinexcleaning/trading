# JOB 0 — can we test the tennis fade as a MAKER? YES. And I first said no.

**2026-08-20.** Mailbox `tennis/017` made this a gate: settle the data question
in writing before running anything, and if the tape cannot support a fill model
read off the aggressor side, say so and stop.

**I wrote the "stop" version of this document first. It was wrong.** The
correction is the most useful thing here, so it goes at the top rather than in a
footnote.

---

## 0. The error, and what caught it

**What I concluded from two local data stores:**

- `bot-hunt/data/record.db` holds quotes only — no trades table, no aggressor
  field, sampled every ~731 seconds. **True.**
- `kalshi-market-scan`'s trades tape has the right columns but covers exactly
  one day, `date=2026-07-30`. **True.**
- Therefore the fade-as-maker test cannot be run. **FALSE, and it does not
  follow from the first two.**

**What I never did was ask the exchange.** Both of those are local *archives*.
Kalshi still serves per-market trade history and per-minute quote history for
anything inside its retention window, and nobody in this repo had queried it for
tennis.

**How it was caught.** `coordinator/reflect.py` flagged the phrase *"does not
exist"* as an ABSENCE CLAIM, with the note that three of the nine recorded
errors in `coordinator/REFLECT.md` were absence claims and **all three were
wrong**. Its instruction is the operative bit: *name the source that WOULD have
shown it if it existed, and say whether that source was actually consulted.* The
source was the API. It had not been consulted. Ten minutes of probing reversed
the answer.

**This is the eighth instance of the documented failure shape: read one source,
concluded, stated it confidently.** It was not a reasoning failure. Every step
after the wrong premise was sound, which is exactly why it reads as convincing.

---

## 1. What the exchange actually serves, measured 2026-08-20

| probe | result |
|---|---|
| settled tennis markets, `/markets?status=settled` | **35,994** across six series, 2026-06-14 → 08-20 |
| how far back | **2026-06-14 and no further.** 06-12 returns zero |
| `/markets/trades?ticker=X` | **works on settled markets**, 1,000 per page, cursored, with `taker_book_side` |
| `/series/{s}/markets/{t}/candlesticks?period_interval=1` | **one-minute bars carrying `yes_bid` and `yes_ask` separately** |

**The candlesticks are better than what the original study had.** It built a
mid-only tape. Separate bid and ask means the maker price and the taker price
are both *observed* rather than modelled — and the crypto maker work names the
fill model as *"the single easiest thing to fake in a maker backtest."*

### The universe, by tier

| series | matches | markets | maker fee |
|---|---|---|---|
| `KXITFMATCH` | 7,090 | 14,180 | **zero** |
| `KXITFWMATCH` | 6,190 | 12,380 | **zero** |
| `KXATPCHALLENGERMATCH` | 2,405 | 4,810 | **zero** |
| `KXWTAMATCH` | 930 | 1,860 | charged |
| `KXATPMATCH` | 923 | 1,846 | charged |
| `KXWTACHALLENGERMATCH` | 459 | 918 | **zero** |
| **total** | **17,997** | **35,994** | |

**Exactly two markets per match, with no exceptions** — checked, 17,997 events
and 35,994 markets once the window is extended to today. So **17,997 matches**,
against the 3,436 the study's headline `deep:30@38` was measured on. Of those,
**13,865 fall in the selection period and 4,132 in the untouched check
period.**

### ⏳ The window is closing at one day per day

**Nothing before 2026-06-14 is retrievable, and that boundary advances daily.**
A closed Kalshi market 404s forever once it ages out. Of the fade study's
2026-05-25 → 08-01 window, **48 of 68 days survive today**; three weeks are
already gone. **That is why the pull was started before this document was
finished** — pulling is free, read-only and reversible; waiting is not.

---

## 2. ⚠ The aggressor field means the OPPOSITE of what it looks like

`taker_book_side` and `taker_outcome_side` are **perfectly redundant** — in the
2026-07-30 tape, 303,558 rows read `yes` *and* `bid` and 97,954 read `no` *and*
`ask`, with no exceptions. There is a third field, `taker_side`, identical to
`taker_outcome_side`. **Three columns, one bit of information.**

The natural reading — "`bid` means the resting bid was hit" — is wrong. Resolved
empirically rather than from the name, by checking each trade's price against
the prevailing quote from the candles (ATP main tour, 6 markets, ~20,000
non-block trades):

| field says | trade actually printed at the ASK | at the BID |
|---|---|---|
| `taker_book_side = bid` | **4,485** | 1,589 |
| `taker_book_side = ask` | 909 | **2,246** |

**So `taker_book_side` is the side the TAKER's own order sat on, not the resting
side.** A marketable buy of YES is entered as a bid and lifts the ask.

**Which inverts the conclusion:**

> **75.6% of trades are takers BUYING. The resting order that gets filled is
> therefore an ASK about three times in four.**

An earlier draft stated the reverse and treated it as encouraging.

### ⚠ AND THEN I OVERCORRECTED. Second fix, same day.

I next wrote that this puts the fade's maker order on the hard side, because the
fade buys the underdog and buying means resting a **bid**. **That is also wrong,
and it was wrong because I had not noticed the position can be expressed two
ways.**

**Measured on 126 events with over 200 trades on each ticker:** takers buy on
**both** tickers of a match — 74% on average, and **126 of 126 events have both
sides above half**. Not a mirror artifact; people simply prefer buying a
contract to selling one, whichever side they have picked. And the two tickers
are **near-exact price mirrors** — `100 − bid` on one equals the other's ask,
median difference **0¢**, mean 0.81¢.

**So buying the underdog can be done two ways, and they are the same trade:**

| | what rests | filled by | side of the flow |
|---|---|---|---|
| **R1** | a YES **bid** on the underdog's ticker | takers selling the underdog | the ~26% side |
| **R2** | a YES **ask** on the favourite's ticker | takers buying the favourite | the ~74% side |

**Selling the favourite is being long the underdog.** R2 sits where the flow is.
Both are now measured for every arm (amendment A1), neither is chosen in
advance, and the correction denominator is unchanged because this is a reporting
split of one hypothesis, not a new one.

**The comfortable inference from R2 is not safe.** Easy to fill and good to fill
are different things — being filled by someone who turns out to be right is the
adverse selection that killed the crypto version at −1.226¢. **R2 filling well
and still losing is a completely plausible outcome.**

⚠ Caveats kept: one tier, six markets, one date range, and 53% of trades landed
between the quotes (minute-bar close versus trade timestamp), so the split is
directional, not exact. It is re-measured across the full pull before anything
is concluded.

---

## 3. Maker fees, read from the API and stored with the data

| series | `fee_type` | maker pays |
|---|---|---|
| `KXITFMATCH`, `KXITFWMATCH`, `KXATPCHALLENGERMATCH`, `KXWTACHALLENGERMATCH` | `quadratic` | **nothing** |
| `KXATPMATCH`, `KXWTAMATCH` | `quadratic_with_maker_fees` | charged |

**This is not new — it is ledger `S010`, settled.** Recorded here only because
the puller now stores the schedule in the same database as the prices, so a
future reader cannot pair the wrong fee with the wrong series.

**And `S025` is the necessary corrective to it.** S010's "91% of the book" is a
*count*. By volume the maker-fee series are **34.4%** on 5.8% of the markets,
and `KXATPMATCH` alone is **21.9%** of tennis volume. The 2026-07-30 tape shows
the same shape from the other side: **94.7% of tennis trades were in
taker-only families**, but far less of the contract volume. **ITF is where the
trade count is; main tour is where the money is.** For a maker that means ITF
offers many small fills, which is a different business from a few large ones and
must not be pooled with it.

---

## 4. His second question — the premise is wrong, and it matters

`017` asked whether the price-drop version had ever been run, since the existing
work "triggers on LOSING A SET".

**It does not. It never did.** `RESULTS.md:48` and `p2_calib.py:164`:

> `deep:12` — *the first minute the favourite's mid is **≥12¢ below its
> pre-match mid** and has not made a new low for 8 minutes, entered 3 minutes
> later. A stopping time.*

**The trigger was always a price drop.** The set score is not in the entry rule.
The whole grid was run — `deep:8/12/16/20/25/30`, with and without a minute
floor — with `deep:12` pre-committed as primary and `deep:30@38` the best
targeted, which is the **+2.42¢ headline this maker question exists to attack**.

**So his idea is `deep:40`: one row further along a grid that already exists.**

**His instinct matches the data** — the effect grows with the depth of the drop
(`deep:12` +1.13¢ → `deep:20@38` +2.06¢ → `deep:25` +2.41¢ → `deep:30@38`
+2.53¢, gross, over 2026-05-25 → 08-01).

**And GUARDS #10 says that exact shape is a warning, not a confirmation:**
*"monotone strengthening is evidence of contamination until proven otherwise."*
This repo's worst inference was arguing an effect was real *because* it
strengthened with detector precision, when precision and bias were the same
knob. **Every one of those rows is still negative after costs** — `deep:30@38`
nets −1.10¢, `deep:12` nets −2.86¢.

He should be told his instinct is right and the answer is still no — not offered
a "cheap addition" that has already been run.

---

## 5. What is now running

`set1_overshoot/src/p6_maker_pull.py`, read-only, no credentials, paced at 6
requests a second against a measured unauthenticated ceiling of 15 (`C018`) and
deliberately below it because the two forward recorders share this machine.

**Two passes, and the split is arithmetic.** Measured on a 2026-07-16 smoke run:
616 candle rows and **4,011 trade rows** per market. Over 27,730 markets that is
17M candles (~1 GB) against **111M trades (~28 GB)** — and the overwhelming
majority of those trades sit in markets where the entry rule never fires and can
never affect a result.

1. **Candles for all 27,730.** ~1 GB, ~80 minutes. Running now.
2. **Trades only for the markets that actually trigger.** Expected to be a few
   thousand markets, a few GB.

Two bugs were caught before launch and both were the silent-zero shape:
`count_fp` is the field name and there is **no `count` key at all** (`t["count"]`
would have written 0.0 for every trade), and `is_block_trade` must be kept
because a negotiated block is not a fill any resting order could have won.

---

## 6. What has NOT been tested — per CLAUDE.md §9c step 7

**Nothing has been run. This is a data report; there is no result here.**

1. **The fade as maker, on any sample.** Not run.
2. **Whether a resting order fills at a rate worth having.** The 75.6% is the
   share of aggressive volume, **not** the chance a given resting order fills.
   Different numbers; only the second one matters.
3. **Adverse selection**, which is what killed the crypto version (capture
   −1.226¢). Untouched.
4. **Whether tennis differs from crypto in the way the argument hopes** — hours
   of play with retail flow, against 15-minute ladders minted at-the-money
   against algorithms. Plausible, entirely untested.
5. **Anything before 2026-06-14.** Permanently gone; the study's first three
   weeks cannot be re-pulled. Whether the surviving 48 days behave like the full
   68 is unknown and unknowable.
6. **Queue position.** The candles give the touch, not where in the queue an
   order would sit. On ITF this may be the whole question.
7. **`deep:40`**, his actual suggestion, which is off the end of the existing
   grid.
8. **Set-1 outcomes for ITF and Challenger**, which no free source covers
   (`S018`) — so a set-conditioned variant stays main-tour-only.

---

## 7. Standing prediction, recorded before the result exists

**I expect this to fail, and I have already had to change my reason once.**

**Superseded (written earlier the same day):** *"it fails because the fade's
resting bid is on the hard-to-fill side."* Wrong — R2 exists and sits on the
easy side.

**Current prediction:** the zero maker fee on ITF and Challenger is a real
structural gain over crypto and larger than the time-structure argument. **I
expect R2 to fill well and to lose on adverse selection, and R1 to fill
poorly** — so the strategy fails, but not for want of fills. A thin ITF book is
where a stale quote is *most* exposed, not least.

**Recorded now so it cannot be adjusted after seeing a number. The superseded
version is kept above rather than deleted** — a prediction quietly rewritten is
not a prediction.
