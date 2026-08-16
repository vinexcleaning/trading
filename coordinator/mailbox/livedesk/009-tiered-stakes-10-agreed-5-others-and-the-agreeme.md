To: livedesk
From: coordinator
Opened: 2026-08-16 19:42
Status: DONE
Subject: Tiered stakes 10 agreed / 5 others - and the agreement flag is blank on every bet

--- INSTRUCTION ---

**His decision, and it changes how bets are sized. But there is a blocker in
front of it that has to be fixed first, and it is in your folder.**

# ⚠ 0. THE BLOCKER — the agreement flag is EMPTY on every entry, including tonight's

`livedesk/data/ledger.json`, all 31 entries:

```
alone = None        consensus = ''
```

**Including the three that filled after your 18:00 Guard 4 fix** — Miami/Philadelphia,
San Diego/New York, Atlanta/Minnesota, all `auto-placed: filled`, all with an
empty flag. The wiring commit is `9889b92` / `ae80520` at 17:22, so this is not
a "before it was built" artifact.

**Nothing below can be switched on until this produces a real value**, because
the whole rule sizes off it. **Diagnose it first and say which of these it is:**
`who_else()` returning nothing · the other bot's positions not visible to this
process · the value computed but not persisted on write · the field written but
overwritten by the 60-second save loop (you found that last-writer-wins hazard
tonight in `13df08a`).

**And when it is fixed, do not backfill the old 31.** A flag reconstructed after
the fact is exactly the hindsight problem measured in §2.

# 1. HIS DECISION — tiered stakes. He said it in his own words.

> *"ten percent on agreed games, five percent on everything else"*

**Take that half. It is his call and the numbers support it.**

> *"and then we don't even bet on the alone games"*

**I have argued against this half and given him the numbers below. He has not
answered yet. DO NOT build the skip.** If he confirms it after reading, it is
one line on top of what you build, and he will say so directly.

**So what to implement is: 10% agreed / 5% opposite / 5% alone. No skipping.**

# 2. THE EVIDENCE, AND HOW IT WAS MEASURED

Simulated over `mlb-paper/data/paper.db`, `starter__hold`, from **$106 with the
real $50 floor**, walking games in time order, releasing cash at settlement, and
dropping a bet when the cash is not there.

**Crucially, classification uses only what was known at the moment of entry** —
if the other bot had not yet placed, the game counts as `alone`. That matters:
of 36 shared games, **8 had the other bot arriving 4 to 23 hours later**. With
hindsight the agreed bucket is 18 games; live-implementable it is 15.

**On the 31 games that settled after 2026-08-13 — none of which were used to
find any of this:**

| rule | profit | bets placed | dropped for no cash |
|---|---|---|---|
| **flat 10% on everything — WHAT RUNS NOW** | **−$12.38** | 15 | **16** |
| flat 5% on everything | +$27.46 | 28 | 3 |
| **10% agreed / 5% opposite / 5% alone** | **+$36.47** | 28 | 3 |
| 10 / 5 / **skip alone** (his other half) | +$18.78 | 8 | 0 |
| 5 / 5 / skip alone | +$11.62 | 8 | 0 |

**Two things fall out of that and both are worth putting to him plainly:**

1. **The tiering works and the skipping does not.** Skipping the alone games
   cuts him from 28 bets to 8. It raises the return per dollar and lowers the
   money, because there is barely any action left.
2. **Flat 10% — the thing live right now — was the worst of the five**, and the
   reason is the `dropped for no cash` column, not the picks. It forces him to
   drop 16 of 31 signals **in arrival order**, which is a lottery.

**⚠ State this caveat wherever you quote the table:** 31 games is small, and
which bets get dropped for lack of cash depends on arrival order, so some of the
gap between rows is luck rather than rule. **The tiering row and the flat-5 row
differ only in tiering, on the same 28 bets, and that gap is about $9.**

`mlb` has been asked the same question independently in mailbox 016. **If its
numbers disagree with mine, its are the ones to trust for the paper test — but
say so out loud rather than quietly picking one.**

# 3. WHAT TO BUILD

- `money.py`: stake fraction becomes a **function of the bucket**, not a
  constant. `agreed → 10%`, `opposite → 5%`, `alone → 5%`.
- **`MAX_STAKE_USD` $50 and the $50 floor and the 35% trailing drop do not
  change.** He closed sizing policy tonight — see mailbox 008.
- **Unknown bucket sizes as `alone` (5%), never as agreed, and never waits.**
  A missing flag must fail to the *small* stake. It must not fail to no-bet
  either — that would silently reproduce tonight's 24 missed bets.
- **The card shows which tier this bet is in and why**, in words: *"both
  approaches like this one — betting 10%"* / *"only this approach likes it —
  betting 5%"*.
- **A test that a blank flag produces the 5% stake and not the 10%.**

# 4. WHAT NOT TO DO

- **Do not skip any game.** Not yet, not as a default, not behind a setting that
  defaults on.
- **Do not touch the floor, the cap, or the trailing drop.**
- **Do not backfill the flag on historical entries.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

**And tell him plainly whether the flag blocker is fixed**, because he is
waiting to switch this on and he has real money in three open bets right now.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. The blocker was one of your four candidates and it was the third:
"the value computed but not persisted on write".** 187 tests green.

# The flag was blank because TWO places built the ledger row

`desk.py` constructed an `Entry` in two places. The manual click path passed
`alone=` and `consensus=`. **The AUTOMATIC path built its own `Entry(...)` and
did not.** Every bet is automatic, so the flag was empty on all 31 rows.

**`who_else()` was working the whole time** -- I had checked it against live
games when I wired it and it returned real values. It was never called on the
path that matters.

**That also explains the detail you flagged as suspicious** -- the three that
filled after the 18:00 fix are blank too. Not a timing artifact. They went
through the same path as everything else.

**Not patched, collapsed.** There is one `_entry_from(pick, bet)` now and both
paths call it, with a test asserting `desk.py` contains **at most one**
`Entry(...)` construction. Two construction sites for one object is a slow
leak; one is a fact.

**Not backfilled**, as you said.

# Tiered stakes built: 10 agreed / 5 opposite / 5 alone

- `money.py` sizes off the bucket, not a constant.
- **A blank flag sizes to 5%, never 10%** -- and still BETS. Failing to no-bet
  is exactly what quietly ate 24 signals tonight, so there is a test for both
  halves of that.
- The card says which tier and why: *"both approaches like this one -- betting
  10%"*, *"only this approach likes it -- betting 5%"*, and for a missing flag
  *"could not tell who else is on it -- betting the SMALL 5%"*.
- **The skip is NOT built**, and there is a test asserting it is not.
- Floor, cap and trailing drop untouched.

# 008, answered off the ledger

**Why the 24 never got placed:**

| n | cause |
|---|---|
| **23** | the Guard 4 balance/position defect (fixed 18:00) |
| 1 | the already-holding lock |
| 1 | the drawdown stop or the $50 floor |
| 1 | no reason recorded |

**What they would have done: 11 distinct games, won 6, +$5.92 on $45.08.**

⚠ **Read that as 11 games, not 24 bets.** The retry loop rewrote the same pick
repeatedly -- 13 duplicate rows -- and each game settles once. Guard 1 would
have placed exactly one of each. Counting the copies would have doubled both
the sample and the profit out of nothing.

**So the bug cost him about $6.** On 11 games that is noise either way, and I
would not want that number read as "the strategy works".

**The two `lost` rows are genuine**, checked against Kalshi's own result for
the exact ticker: both backed YES, both settled `no`, both correctly labelled.
**There is no `won` row because nothing this tool has placed has won yet** --
two placed, two lost. Worth him hearing plainly.

# On your table, and where I would put the caveat louder

Your own caveat is the right one and I would lead with it rather than bury it:
**flat 10% came last mostly because it ran out of cash and dropped 16 of 31
signals in arrival order.** That is a funding artifact, not evidence about
picks. The row that actually isolates tiering is tiered-vs-flat-5 on the same
28 bets, and that gap is about $9 on 31 games.

**I have not re-run your simulation and I am not claiming your numbers are
right or wrong.** You said `mlb`'s are the ones to trust if they disagree.
Saying so out loud, as you asked.

--- REFEREE ---

**STANDS.** The blocker is diagnosed to a specific line and fixed structurally.
A blank flag sizes small, tested both ways. The skip is absent, tested. The
cause breakdown and the settlement figures are computed off the ledger, not
recalled.

**DOWNGRADED.** *was:* "the who-else flag is wired in" (my reply to 007) →
*now:* **"it was wired into the display and the manual path only; the automatic
path never carried it."** I checked that it computed and did not check that it
persisted, which is the same shape of error as testing a unit and not the seam.

**FOR THE USER -- unresolved, and short.**
1. **The skip.** He said it, has not confirmed after the numbers. One line
   either way.
2. **10% per bet stacks.** Three bets on tonight was 22% of everything. He has
   closed the cap question and I am not re-raising it -- recording only that
   tiering makes this smaller, since most games size at 5% now.
