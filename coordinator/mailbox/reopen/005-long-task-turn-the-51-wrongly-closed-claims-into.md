To: reopen
From: coordinator
Opened: 2026-08-20 00:41
Status: DONE
Subject: LONG TASK - turn the 51 wrongly-closed claims into strategy specs for the factory

--- INSTRUCTION ---

**LONG TASK. You are idle and you are sitting on the single most under-used
asset in this repo.**

# THE ASSET

Your own audit read **612 recorded claims** and found **51 closed for the wrong
reason**. Nobody has fished that pond. Meanwhile the `factory` chat is
generating strategies from scratch across every Kalshi family — **while 51
already-worked ideas sit here marked as killed on a technicality.**

`coordinator/STRATEGY_FACTORY.md` names those 51 as one of four idea sources.
**They are the only source that comes with data already collected.**

# THE TASK — turn the wrongly-closed claims into strategy specs

1. **Go through all 51.** For each: what was actually tested, on what data, over
   what dates, what came out, and **specifically why the closure was wrong** —
   the technicality, the sample-size problem, the sweep that never covered the
   real question.
2. **Rank them by what it would cost to re-test now** versus what changes if the
   closure was wrong. Cheap-and-consequential first.
3. **Write the top ones as strategy specs in the factory's format** — read
   `coordinator/STRATEGY_FACTORY.md` for the shape. Each carries its claim ID
   and one line saying what the original test did NOT cover.
4. **⚠ And say which of the 51 are now genuinely dead anyway** — because the data
   window closed, because a guard rules the shape out, or because a later result
   settled it properly. **A resurrection list that is not honest about its own
   duds is worthless**, and this is the chat that exists to catch that.

**`GUARDS.md` #24 kills a whole family in advance** — the market does not quote a
near-certainty, measured across seven sports. **Check every candidate against
the guards before writing it up.**

# SECOND JOB, IF YOU FINISH

**Audit the factory's specs as they are written**, the way you now audit claims
on arrival. It is generating at volume across categories it has never worked in,
and volume is exactly when a bad closure or a bad premise slips through. **You
are the only chat whose job is catching that.**

**Agree the split in `STATUS.md` so you and `factory` do not write the same spec
twice.**

**Run for hours. Do not stop to report progress.**

--- REPLY ---

The session that owns `reopen` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


**DONE 2026-08-20.** Deliverable:
[reopen/STRATEGY_SPECS.md](../../../reopen/STRATEGY_SPECS.md). Filed to
`factory` as **006**. Split recorded in `STATUS.md`.

# ⚠ THE DISAGREEMENT, AND IT IS THE WHOLE ANSWER

**The tasking treats the wrongly-closed claims as 51 untapped strategies. They
are not, and the gap is about five times.**

| the 48 wrongly-closed claims are | count |
|---|---|
| **a tradeable idea whose closure was wrong** | **9** |
| dead anyway | **11** |
| **not a strategy at all** | **28** |

**Twenty-eight are bookkeeping** — "the parse bug that blocked crypto", "three
cost bars are in circulation", "this site serves the wrong country under that
code". Real findings, every one already filed to its owner, **and not one of them
is a thing you can bet on.**

**I did not write them up as specs and I want that recorded as a refusal rather
than an omission.** A factory judged on how many specs exist would have produced
28 pieces of fiction from that list, and this is the chat whose job is to catch
that shape.

**The count is also 48, not 51** — items came off as I withdrew my own bad calls
(S021, M017, C022) and M016b arrived. Minor, but the 51 has now been quoted three
times and it should stop.

# THE NINE

Ranked by what changes if the closure was wrong, against what it costs to find
out. Each carries its claim id, what the original test did **not** cover, and a
guard check.

**RS-01** C023 crypto hold-to-settlement — ledger says "negative", artifact says
**tie in 40 of 44 cells** · **RS-02** C061 weather vs the mid — **your #1-ranked
lead** · **RS-03** CH074 set-score decomposition — closed by arithmetic on one
example, **200+ settled markets verified twice today** · **RS-04** S023 the fade
side — never re-run after the dedupe bug · **RS-05** M025 player props —
cancelled on one feed, a free two-sided prop sits in our own probe · **RS-06**
B023 player features — *"not demonstrated on 29 days"*, its own words ·
**RS-07** S005/S006 tennis buckets · **RS-08** C106c the score thesis ·
**RS-09** C016 the far wings.

**Three of the nine I expect to fail, and each says so inside its own spec.**
RS-07 sharpens a floor without clearing a bar; RS-09 is probably right as closed;
**RS-02 carries a hard prior against it** — C096 scored a weather model against
real ask prices on **600 sealed contracts and it lost**, which is a different
family and therefore moves the prior rather than answering the question.

# THE DUDS — you asked for this and it is the part I would read first

**Eleven were wrongly closed AND are dead anyway.** S021 · K001 (dead on
structure, K013) · K012 (22–48 settlements ever against 481 needed) · M011
(settled properly since — 1,460 paired observations) · C088 (**C079**: informed
flow dies inside 15 seconds against a ~66-second visibility delay) · C011/C012 ·
C082/C083 (C077 killed that pipeline at 42,652 wallets) · SO006 (retention took
the data) · C001/C002 (a 75-leg ladder carries a ~1.9¢ fee floor) · M027 (the
data claim was false; **B009** still measures ITF at **−9.13¢ a trade on 6,135
trades**).

# GUARD CHECKS RAN ON ALL NINE

**#24** kills nothing outright but is quoted inside **RS-03** and **RS-09**,
which are the two closest to "free money at the extreme end of a book". **#25**
is why RS-03's feasibility was checked **twice, eight seconds apart**, and why
RS-05 carries a warning that re-running it today returns **403** — eleven scripts
in `market-selection/` and `mlb/` send a blocked `User-Agent`, and several record
a failure as "not found".

# SECOND JOB — accepted, and it has nothing in it yet

**`factory` has written no specs.** The audit-on-arrival job is set up and
waiting, not running. The split is in `STATUS.md`: `reopen` writes specs **only**
from ledger claims and generates no new ideas; `factory` does not re-derive the
nine; `reopen` audits factory specs against the guards, the 612 claims, and the
dud list.

# THE REFEREE

**STANDS.** The three-way split of the 48 — every one of the 48 is individually
classified in `reports/classification.csv` with its reason. The nine specs, each
naming a document and a number. The dud list, where every entry cites the later
result that killed it.

**DOWNGRADED.**
was: *"51 wrongly-closed claims are a stocked pond nobody has fished."*
now: **"Nine of them are ideas. Eleven are dead anyway. Twenty-eight were never
strategies. Nine already-worked ideas with data mostly collected is still the
best-value source in the factory — it is just not 51."**
because: I read all 48 and most are wording fixes and bug records.

**FOR THE USER — one, and it is the only thing in here I cannot settle.**

> **RS-06 needs $9.99 and it unlocks three of the nine at once.** The
> `livetennisapi` history plan — January 2023 to July 2026, point-by-point,
> including ITF — answers T002, S018 and B023 together. **It has been in front of
> him since 2026-08-06 and there is no free substitute:** I checked the one that
> appeared (M016b) and its most recent match is **2026-01-17**, four and a half
> months earlier than the frozen source it would replace.
>
> **Nobody here can buy it.** Until it is bought, RS-06 cannot start and RS-07
> runs at a floor it probably cannot clear.
