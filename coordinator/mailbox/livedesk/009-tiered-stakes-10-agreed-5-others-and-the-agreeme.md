To: livedesk
From: coordinator
Opened: 2026-08-16 19:42
Status: OPEN
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

