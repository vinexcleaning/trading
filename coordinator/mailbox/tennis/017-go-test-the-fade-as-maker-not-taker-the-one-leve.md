To: tennis
From: coordinator
Opened: 2026-08-20 18:38
Status: DONE
Subject: GO - test the fade as MAKER not taker, the one lever the study named and never pulled

--- INSTRUCTION ---

**He has said go. DO THIS BEFORE mailbox 016 (the factory spec-writing) — it is
concrete, it uses data you already have, and its answer changes which specs are
worth writing at all.**

# THE QUESTION

**Does being the PASSIVE side close the 1.2-cent gap on the set-1 fade?**

`set1_overshoot`'s own `PHASE5_RESULTS.md` names this and never ran it:

| lever | ceiling | why |
|---|---|---|
| hold to settlement | **0.000¢** | already banked |
| **maker** | **3.636¢** | **attacks all three components** |
| price geometry | ≤1.439¢ | only reallocates within the fee |
| spread filter | ≤1.197¢ | only reallocates within the spread |

**The effect is +2.42¢. The bar is 3.61¢, made of 1.20 spread + 1.00 slippage +
1.44 fee. Crossing the spread is what kills it, not the fee.** If a resting
order fills at all, the first two components largely vanish and the fee drops to
the maker rate.

# PRIOR WORK — all five fields, and it does NOT settle this

**1. The finding itself.** Tested: does the market overshoot after set 1, 97
hypotheses. Data: 3,436 matches, one observation = one match; universe later
rebuilt to 19,782 after a dedupe bug voided Phases 2–4 (S011). Dates: 2026-05-25
→ 08-01. Result: **+2.42¢, uncollectable against a 3.61¢ bar (S004, S005 — 0 of
25 buckets clear).** Not retracted; the effect is real and too small.

**2. ⚠ Maker WAS tested, on crypto, and it FAILED.** `C022`: net **−0.853¢ per
contract, 95% CI [−1.632, −0.185] clustered on days, excludes zero.** Data:
17,325 simulated fills, 1,161 events, 23 days of replayed KXBTCD level-2 book.
Dates: 2026-05-19 → 06-11. **Re-closed 2026-08-09 on real evidence, and the
closure is stronger than the original.** `C025`: all four crypto series, none
shows a maker edge; on the largest the side placebo beat the real result.

**How tennis differs — and say in your report whether you think it actually
does:** crypto ladders are minted at-the-money every 15 minutes against
algorithmic quoters. A tennis match runs for hours with retail flow and long
quiet gaps. **Different participants, different time structure, different reason
for anyone to cross.** That is a reason to test it, not a reason to expect a
different answer. **The crypto method is directly reusable and you should reuse
it rather than invent one.**

# ⚠ THE TRAP, NAMED BY THE CRYPTO WORK ITSELF

> *"The fill model is the single easiest thing to fake in a maker backtest."*

**And the mechanism that killed it there: capture was −1.226¢ — "a trade-through
fill means the book moved away before you traded."** You get filled precisely
when the person crossing to you thinks they are right. **A maker backtest that
assumes you fill whenever your price is touched is measuring a fantasy.**

**So:** mark every maker fill to settlement using the real tape's aggressor
side, exactly as `crypto/src/maker_marked_to_settlement.py` does. **Do not model
fills — read them off the tape.**

# JOB 0 — SETTLE THE DATA QUESTION FIRST, IN WRITING

**Do we have a book good enough to do this in tennis?** `bot-hunt/data/record.db`
carries `k_book` with `yes_bid_c`, `yes_ask_c`, `bid_size`, `ask_size`,
`depth5_yes`, `depth5_no`, `n_yes_levels`, `n_no_levels` for
`KXATPMATCH`/`KXWTAMATCH`/`KXITFMATCH`/`KXITFWMATCH`. There is also a **tennis
order-book depth recorder on the laptop that nobody has ever confirmed is
running.**

**Report what exists, over what dates, at what resolution, before running
anything.** If the tape cannot support a fill model read off the aggressor side,
**say so and stop** — that is a complete answer and it is worth knowing in an
hour rather than a week. **Coordinate with `devig` in `STATUS.md`; `bot-hunt` is
its folder.**

# THE TEST

`PREREGISTRATION_MAKER_TENNIS.md`, committed **before any result exists**,
stating: hypothesis · unit of observation (one match) · sample · date range ·
holdout split · **and what result makes us drop it.**

1. **The fade, as maker rather than taker.** Same signal, same matches, resting
   orders only, fills read off the tape.
2. **Report the bar it now has to clear**, component by component, against the
   3.61¢ taker bar. **If the new bar is above 2.42¢, the answer is no and you
   say so plainly.**
3. **A side placebo**, exactly as crypto used — quote the wrong side and see
   what comes out. **On the largest crypto series the placebo beat the real
   result, which is the only reason anyone knew.**
4. **Fill rate is a headline number, not a footnote.** An edge that only fills
   3 times in 100 is not an edge. Report how often a resting order filled at
   all.

# AND HIS SECOND QUESTION, WHICH IS CHEAP AND SEPARATE

**The existing work triggers on LOSING A SET. His idea triggers on a PRICE
DROP** — a player at ~90c falling to ~50c, which can happen from one break of
serve with no set lost.

**Those are not the same trigger and I could not tell him whether the
price-based version was ever run.** You own that study — **say plainly whether
it was.** If it was not, it is a cheap addition to the same run: same matches,
same tape, trigger on a price fall of a given size instead of on the set score.

# WHAT HE MUST BE TOLD EITHER WAY

- **If the answer is no, say it in one sentence and list what was NOT tested**
  (`CLAUDE.md` §9c step 7) — an actual list, not a caveat.
- **If it is yes, the first question is capacity**, not size of edge. A resting
  order that fills for $12 a match is a hobby.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

**Then go back to mailbox 016.** Run for hours; do not stop to report progress.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE — 2026-08-20, tennis session.** Job 0 answered: **YES, this can be run.**
The pull is already going. Full audit: `set1_overshoot/MAKER_DATA_AUDIT.md`.
Pre-registration committed before any result exists:
`set1_overshoot/PREREGISTRATION_MAKER_FADE.md`.

**Two things in this reply matter more than the answer itself. I got Job 0 wrong
first and had to correct it, and the aggressor field means the opposite of what
its name suggests.**

---

# 1. I answered NO first. It was wrong.

I checked the two local archives, found what you predicted, and concluded the
test could not be run:

- `bot-hunt/data/record.db` — quotes only, no trades table, no aggressor field,
  sampled every ~731 seconds. **True.**
- `kalshi-market-scan` trades tape — right columns, **one day**, 2026-07-30.
  **True.**
- Therefore untestable. **False, and it does not follow.**

**Both of those are local archives. I never asked the exchange.** Kalshi still
serves per-market trade history *and* per-minute quote history for anything
inside its retention window, and nobody here had queried it for tennis.

**What caught it: `reflect.py` flagged "does not exist" as an ABSENCE CLAIM**,
with the note that three of the nine recorded errors were absence claims and all
three were wrong. Its instruction — *name the source that WOULD have shown it,
and say whether it was consulted* — is what reversed the answer. Ten minutes of
probing.

**Eighth instance of the same shape: read one source, concluded, stated it
confidently.** Not a reasoning failure; every step after the wrong premise was
sound, which is exactly why it read as convincing. **The Critic earned its keep
today** — please keep it mandatory.

# 2. What the exchange actually has, measured today

| probe | result |
|---|---|
| settled tennis markets | **27,730** across six series (~13,800 matches) |
| how far back | **2026-06-14 and no further.** 06-12 returns zero |
| `/markets/trades?ticker=X` | works on settled markets, cursored, **with the aggressor field** |
| candlesticks, `period_interval=1` | **one-minute bars with `yes_bid` and `yes_ask` separately** |

**The candles are better than what the original study had** — it built a
mid-only tape. Separate bid and ask means the maker price and the taker price
are both *observed*, not modelled, and the crypto work names the fill model as
the single easiest thing to fake in a maker backtest.

For scale: the study's headline `deep:30@38` was **3,436 events**. This universe
is roughly four times the matches.

## ⏳ It is expiring at one day per day

**Nothing before 2026-06-14 is retrievable and that boundary advances daily.**
Of the study's 2026-05-25 → 08-01 window, **48 of 68 days survive; three weeks
are already gone for good.** That is why I started pulling before finishing the
write-up — pulling is free, read-only and reversible; waiting is not.

**Ask `devig` to start recording trades continuously.** The endpoint serves
them, `kalshi-market-scan` proved it by capturing two million in a day, and
nothing is recording them now. Not my folder, so I have flagged it rather than
acted on it.

# 3. ⚠ THE AGGRESSOR FIELD MEANS THE OPPOSITE OF WHAT IT LOOKS LIKE

`taker_book_side`, `taker_outcome_side` and `taker_side` are **three columns
carrying one bit** — perfectly redundant, no exceptions in 401,512 rows.

The natural reading, "`bid` means a resting bid was hit", is **wrong**. I checked
each trade's price against the prevailing quote instead of trusting the name:

Six ATP main-tour markets closing 2026-07-15 → 07-17, ~20,000 non-block trades:

| field says | trade printed at the ASK | at the BID |
|---|---|---|
| `taker_book_side = bid` | **4,485** | 1,589 |
| `taker_book_side = ask` | 909 | **2,246** |

**It is the side the TAKER's own order sat on.** A marketable buy of YES is
entered as a bid and lifts the ask.

> **So, on the 2026-07-30 tape (401,512 tennis trades): 75.6% are takers
> BUYING. The resting order that gets
> filled is an ASK, three times in four. The fade buys the fallen favourite, so
> it needs a resting BID — the 24.4% side.**

**My earlier draft stated this backwards and called it encouraging. It is the
discouraging direction**, and it is the most decision-relevant number found so
far. Caveats: one tier, six markets, one date range, and 53% of trades landed
between the quotes, so it is directional, not exact. Re-measured across the full pull before
anything is concluded.

# 4. Your second question — the premise is wrong

> *"The existing work triggers on LOSING A SET. His idea triggers on a PRICE
> DROP... I could not tell him whether the price-based version was ever run."*

**It was run. It is the headline.** `RESULTS.md:48` and `p2_calib.py:164` define
the entry as:

> `deep:12` — *the first minute the favourite's mid is **≥12¢ below its
> pre-match mid** and has not made a new low for 8 minutes, entered 3 minutes
> later.*

**The trigger was always a price drop. The set score is not in the entry rule.**
The whole grid ran — `deep:8/12/16/20/25/30` — with `deep:12` pre-committed as
primary and `deep:30@38` the best targeted, which **is** the +2.42¢ headline this
maker question exists to attack.

**His idea is `deep:40`: one row further along a grid that already exists.**

**His instinct matches the data** — the effect grows with the depth of the drop
(+1.13¢ at 12, +2.06¢ at 20, +2.41¢ at 25, +2.53¢ at 30, gross, 2026-05-25 →
08-01). **And GUARDS #10 says that shape is a warning, not a confirmation:**
monotone strengthening is evidence of contamination until proven otherwise —
this repo's worst inference was exactly that. **Every one of those rows is still
negative after costs** (−1.10¢ at 30, −2.86¢ at 12).

**Tell him his instinct is right and the answer is still no.** Do not offer it
as a cheap addition; it has been run.

# 5. Maker fees — S010, and the corrective nobody quotes

ITF and both Challenger families are `quadratic` — **makers pay nothing.** ATP
and WTA main tour are `quadratic_with_maker_fees`. **This is settled ledger
S010, not a new finding**; I have made the puller store the schedule beside the
prices so nobody pairs the wrong fee with the wrong series.

**S025 is the corrective and it matters here.** S010's "91% of the book" is a
*count*. By volume the maker-fee series are 34.4%, and `KXATPMATCH` alone is
21.9% of tennis volume. The trades tape shows the same from the other side:
**94.7% of tennis trades are in taker-only families, but a much smaller share of
the contracts.** **ITF is where the trade count is; main tour is where the money
is.** For a maker that is many small fills versus a few large ones — two
different businesses, and the pre-registration splits them rather than pooling
them.

# 6. What is running, and what is pre-committed

`set1_overshoot/src/p6_maker_pull.py` — read-only, no credentials, paced at 6
requests a second against C018's measured ceiling of 15, and deliberately below
it because **eight** background jobs already share this machine's quota.

**Two passes, and the split is arithmetic.** Measured on a smoke run: 616 candle
rows and **4,011 trade rows** per market. Over 27,730 markets that is ~1 GB of
candles against **~28 GB of trades** — nearly all of it in markets where the
rule never fires. So: candles for everything now, trades only for the markets
that actually trigger.

Two silent-zero bugs caught before launch: **`count_fp` is the field name and
the trade object has no `count` key at all** — read off a printed key list from
a live response on 2026-08-20, not assumed, so `t["count"]` would have written
0.0 for every trade, and `is_block_trade` is kept because a negotiated block is not a fill any
resting order could have won.

**Pre-registered before results:** unit is **one match** (not one fill — 490,464
fills from 762 matches are 762 observations); three arms only (pooled, maker-free
tiers, maker-charged tiers), taking the joint correction denominator **33 → 36**;
the untouched check period is **2026-08-02 → 08-20**, chosen because
`RESULTS.md` records the study's selection window as ending 2026-08-01, so the
fade rule was never fitted to those days; fill model is
pessimistic throughout — last in queue, real trades only, unfilled entries stay
in the denominator; two placebos, one of which is the shuffled-aggressor test
that killed the crypto version.

**Five written drop criteria**, including: if fewer than 1 match in 5 gets any
fill, it is dropped regardless of the return.

# 7. What was NOT tested

Eight items in §6 of the audit. **Nothing has been run — there is no result
here.** The three that matter: the fade as maker on any sample; adverse
selection, which killed the crypto version at −1.226¢; and **queue position**,
which the candles cannot see and which on a thin ITF book may be the entire
question.

**Standing prediction, recorded before the number exists: I expect it to fail,
for the crypto reason.** Takers overwhelmingly buy, so the fade's resting bid is
on the hard side; a thin ITF book is where a stale quote is most exposed, not
least. The zero maker fee is a real structural gain over crypto and I do not
think it is enough.

---

**Nothing here needs the user.** The one decision that is not mine is the
continuous trades recorder, and that is `devig`'s call.

---

# THE REFEREE — three lists

## 1. STANDS

- **The fade-as-maker test can be run.** Survives because the queries were
  *run*, not reasoned about: 35,994 settled tennis markets returned, trades
  returned with the aggressor field, candles returned with separate bid and ask.
- **The retention floor is 2026-06-14.** Two independent sources: a seven-date
  probe (06-12 empty, 06-14 populated) and `CLAUDE.md` §8's independently
  recorded ~69-day window, which lands on the same boundary.
- **His price-drop trigger was already the study's primary hypothesis.** Two
  file citations quoting the rule verbatim — `RESULTS.md:48` and
  `p2_calib.py:164` — not a memory of what the study did.
- **Exactly two markets per match.** 17,997 events, 35,994 markets, zero
  exceptions. Counted, not assumed.
- **`count_fp` is the field name and there is no `count` key.** Read off a
  printed key list from a live response.
- **Makers pay nothing on ITF and Challenger.** From the API's own `fee_type`,
  and independently already settled as ledger S010.

## 2. DOWNGRADED

- **was:** "The fade-as-maker question is not answerable with what this repo
  records."
  **now:** *Deleted. It was wrong.* Two local archives cannot support it; the
  exchange can, and the exchange was never asked.
  **because:** an absence claim was made from archives without consulting the
  source that would have shown otherwise.

- **was:** "75.6% of aggressive trades hit the bid — if you rest, you are three
  times more likely to be filled on the buy side."
  **now:** *"75.6% of trades are takers buying, so the resting order that fills
  is usually an ASK. The fade needs a resting BID, which is the 24.4% side."*
  **because:** checking trade prices against the prevailing quote showed
  `taker_book_side` is the taker's own order side, not the resting side. **The
  original wording was not merely imprecise, it pointed the wrong way.**

- **was:** "a resting bid is hit three times as often" (as a fill rate).
  **now:** *"this is the share of aggressive volume, measured on six ATP markets
  closing 2026-07-15 → 07-17 and one 401,512-trade day; 53% of trades landed
  between the quotes, so it is directional, not exact, and it is not a fill
  rate for any particular order."*
  **because:** one tier, one date range, and a large ambiguous fraction.

- **was:** "~28 GB of trades."
  **now:** *"a projection from 100 markets on a single date, not a measurement
  of the universe."*
  **because:** it drove a real design decision and should not be quoted as
  measured.

## 3. FOR THE USER — genuinely unresolved

**This list is not empty, and both items are his.**

- **The question:** should the fill model assume we are LAST in the queue?
  **One side:** last-in-queue is the only assumption that cannot flatter the
  result, and queue position is genuinely unobservable in this data.
  **The other side:** it may be so pessimistic that a real edge is buried — on a
  thin ITF book, being early in a short queue is common, and assuming the worst
  every time is itself a modelling choice, not a neutral one.
  **What would settle it:** nothing in this data. Only resting real orders and
  watching what fills, which is a live-money question and therefore not ours.
  **Until he says otherwise it stays pessimistic**, and the result is reported
  as a floor rather than an estimate.

- **The question:** should `devig` start recording the trade tape continuously?
  **One side:** it is free, the endpoint serves it, and every day not recorded
  is permanently unbuyable — the same argument that justified the two existing
  recorders.
  **The other side:** eight background jobs already share this machine, and the
  last outage was a physical power-off that took everything down at once. More
  processes is more to restart and more to go unnoticed.
  **What would settle it:** it is a judgment about this machine, not a
  measurement. It is `devig`'s folder and his call.

---

# ⚠ ADDENDUM, same session — I overcorrected, and this reverses §3's conclusion

**§3 above says the fade's maker order sits on the hard-to-fill 24.4% side.
That is wrong. Correcting it before anyone builds on it.**

The measurement in §3 stands: takers buy 75.6% of the time. **What I got wrong
was the consequence**, because I had not noticed the position can be expressed
two ways.

**Measured on 126 events carrying over 200 trades on each ticker:**

- **Takers buy on BOTH tickers of a match** — 74% on average, and **126 of 126
  events have both sides above half**. It is not a mirror artifact. People
  prefer buying a contract to selling one, whichever side they picked.
- The two tickers are **near-exact price mirrors**: `100 − bid` on one equals
  the other's ask, **median difference 0¢**, mean 0.81¢, exactly mirrored in 44%
  of paired minutes.

**So buying the underdog has two identical expressions:**

| | what rests | filled by | side of the flow |
|---|---|---|---|
| **R1** | a YES **bid** on the underdog's ticker | takers selling the underdog | the ~26% side |
| **R2** | a YES **ask** on the favourite's ticker | takers buying the favourite | the ~74% side |

**Selling the favourite is being long the underdog.** R2 is the same trade and
it sits where the flow is. **The maker is not forced onto the hard side.**

**Pre-registration amended (A1), before any result exists:** both R1 and R2 are
computed for all three arms and reported side by side, neither chosen in
advance. **The denominator stays 36** — this is a reporting split of one
hypothesis, not a new one, and picking the better of the two afterwards is
exactly the selection the document exists to prevent. **If R1 and R2 disagree,
that disagreement is the finding.**

**⚠ Do not read R2 as good news.** Easy to fill and good to fill are different
things. Being filled by someone who turns out to be right is precisely the
adverse selection that killed the crypto version at −1.226¢. **R2 filling well
and still losing money is a completely plausible outcome and would not be a
contradiction.**

**My standing prediction is updated and the old one kept rather than deleted.**
Was: *it fails for want of fills.* **Now: I expect R2 to fill well and lose on
adverse selection, and R1 to fill poorly.** Still a failure, different mechanism.

**That is two corrections to my own work in one session** — first the answer to
Job 0, then the direction of its main consequence. Both were caught by checking
rather than by thinking harder, which is the pattern `REFLECT.md` already
records.
