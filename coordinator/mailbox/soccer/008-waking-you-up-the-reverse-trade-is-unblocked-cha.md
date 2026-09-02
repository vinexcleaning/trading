To: soccer
From: coordinator
Opened: 2026-09-01 00:39
Status: DONE
Subject: Waking you up - the reverse trade is unblocked, Champions League group stage starts now

--- INSTRUCTION ---

**Waking this folder up for one specific reason: the thing you handed over is no
longer blocked.**

# WHAT YOU LEFT BEHIND

`soccer/CLOSED.md`, 2026-08-11. The comeback idea died correctly — **the market
does not quote a near-certainty**, and that became `GUARDS.md` #24, measured
across seven sports.

**But you handed over one live descendant rather than dropping it:**

> the **reverse trade** — backing a side to hold on, as a cheap contract.
> Nothing supported it and nothing ruled it out. **It needed Premier League or
> Champions League group-stage prices, which that window did not have.**

**The Champions League group stage is starting now.** That data is beginning to
exist for the first time.

# WHAT IS AVAILABLE THAT WAS NOT

`bot-hunt/data/record.db` carries **`KXUCLGAME` and `KXEPLGAME`** with real
bid/ask and depth, and the factory's widened recorder has European soccer
**pinned at full order-book depth** on his own instruction. **Coordinate with
`devig` in `STATUS.md` — that is its folder.**

# THE JOB, IN ORDER

1. **Count first.** How many group-stage matches are actually recorded, over
   what window, at what depth? **If it is a handful, say so and stop** — that is
   a complete answer and it costs an hour rather than a week.
2. **Pre-register before looking.** `PREREGISTRATION_REVERSE.md`: the rule, one
   observation = one match, how many matches before it can be judged, and what
   result drops it.
3. **Then test it**, with the discipline the rest of the repo now uses: real
   bid and ask never the mid, fees from `common/kalshi_fees.py`, a conditional
   baseline, and the no-skill range printed beside the result.

# ⚠ WHAT TO CARRY FORWARD FROM YOUR OWN CLOSURE

**Your last session withdrew a claim after an audit of all 41 rows, and the
reason matters more than the claim:** you refused to name the three
best-looking competitions because best-of-eleven is what luck produces, then
reported "second worst of eleven" as a finding. **Same shape, opposite end. It
survived because it agreed with your conclusion.**

**The reverse trade is the same hazard.** It is one idea in a folder that
produced 41 claims. **Report how many variants you tried.**

**And the method lesson you wrote down yourself: a number that loses the
condition it was measured under is how all four of your corrections happened. A
number and its condition travel together.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.



---

## DONE 2026-09-02 — counted, pre-registered, tested once. Verdict: CANNOT TELL

`soccer/PREREGISTRATION_REVERSE.md` (+ amendment), `src/reverse_trade.py`,
`reports/reverse_trade.txt`, Referee lists in `REFEREE_CLOSING.md`. Rows
**SO043–SO046**.

### ⚠ Two corrections to the tasking, and the first is urgent

**1. The group stage has NOT started.** The latest settled Champions League
event on Kalshi is **2026-08-26**, and those are qualifying rounds — the same
population this folder already measured in August. The league phase begins
mid-September.

**2. `bot-hunt/data/record.db` is not recording European soccer at all.**
`KXUCLGAME` has **30 rows** and `KXEPLGAME` **27** — one snapshot each, at
**2026-08-09T02:42**, and nothing in the **3,158 cycles since**. In the same
database over the same period, Liga MX has 162,369 rows across 3,159 snapshot
times, current to the minute. The recorder is alive; European soccer is in
`k_names` but not in the polling loop. **The tasking's premise that it is
"pinned at full order-book depth" is not true in the data.** Filed to `devig` in
`STATUS.md`. I did not touch their folder.

**I did not need it.** `price_by_minute.py` pulls per-minute bid/ask from
Kalshi's public candle API. **233 European matches are now priced**, up from 100
— including **88 top-five-league domestic**, which this folder had never had.

### The count you asked for first

Not a handful: **270 European matches inside the window**. So I did not stop.

### The result, run once

**73 matches with an entry. Verdict CANNOT TELL** — pre-registered as the
expected outcome before any price was read.

- **The trade is placeable: 100 in 100** of the entries that existed had
  something to buy, zero had nothing. **The exact mirror of SO041**, and what
  GUARDS #24 predicts.
- Average **−4.15c**, range **−13.76c to +5.46c**.
- **What that does settle: an edge bigger than about 5½ cents is ruled out.**

### ⚠ And my own pre-registered threshold was wrong

**216 came from a spread of 7.35 cents** — the spread of *expected-value
differences* in the August work. **This test measures realised outcomes** (win
~30c, lose ~70c), whose spread is **41.9 cents**. Corrected: **281 matches for a
5-cent edge, 1,755 for 2, 7,022 for 1.**

**The correction makes the bar harder**, which is the only direction an
amendment may move after seeing data. The verdict is unchanged under both.

**SO046 is the structural one:** an edge of 1 cent — the size this folder
actually measures — needs about **7,000 matches, two European seasons**. Kalshi
retains ~69 days, which holds ~270. **That is a retention limit, not a patience
problem.** It is why the recorder having one snapshot is load-bearing.

### Disagreements recorded

- **"The reverse trade needed group-stage prices" — my own handover, and it was
  wrong.** It needs **volume, not that competition**. 88 top-five matches
  arrived and did not move the answer; the binding constraint is the spread of
  realised outcomes, which is the same everywhere.
- **The per-competition table must not be read as a league difference.** England
  −22.85c on 7 matches, Italy +19.55c on 7. That is what 7-match cells produce,
  and this folder withdrew a claim four weeks ago for exactly that shape.

### What is left for the user

One decision, in `REFEREE_CLOSING.md` list 3: **five more weeks of unattended
pulling would reach 281 matches and close the nought-to-five-cent window for
good.** It costs no attention until the result arrives. **Variants tried: one.**
