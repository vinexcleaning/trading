# Fix: a temporary refusal is permanently burning the signal

**For whoever is editing `livedesk/`.** Written 2026-08-14 by the dictator chat
from the evidence in `livedesk/data/ledger.json`. **Not a design opinion — the
notes in that file say what happened.**

---

## WHAT HAPPENED

Four picks are marked `void`. Every one carries this note:

```
auto-exec refused: THESE DO NOT AGREE by +$29.61. Your balance says $100.00;
this tool expects $70.39 (started $83.00, $12.61 out, $0.00 back). No profit
figure and no bets until this is sorted
```

| game | team | cost | status |
|---|---|---|---|
| 2026-08-14 BOS@PIT | Pittsburgh Pirates | $4.30 | void |
| 2026-08-14 NYY@TOR | New York Yankees | $4.25 | void |
| 2026-08-15 KC@LAA | Los Angeles Angels | $4.14 | void |
| 2026-08-15 COL@SF | Colorado Rockies | $4.07 | void |

**The reconciliation check refused to place them, and that was correct** — the
user's stored starting balance is $83.00 while his real balance had moved to
about $92 through his own trading, so the ledger and the account genuinely
disagreed by roughly $29. Refusing to trade on numbers that do not add up is
exactly what that guard is for.

**The bug is what happened next: each refused pick was written to the ledger
with `status = "void"`.**

Under Guard 1, a void closes that game for good. **So a temporary bookkeeping
mismatch has permanently destroyed four signals** that the strategy wanted and
that nothing was actually wrong with.

---

## THE DISTINCTION THAT IS MISSING

There are two completely different reasons a bet does not get placed, and the
code currently treats them the same:

**PERMANENT — the game should close for good:**
- the user clicked "I did NOT actually place this one";
- Guard 1: this exact signal has already been played;
- the game has started or finished.

**TEMPORARY — the game should stay available:**
- **reconciliation disagreement** (this case);
- the daily order or stake cap is reached;
- not enough cash right now;
- the kill switch is on;
- a network or API failure.

**A temporary block is a "not yet", not a "no". It must not consume the
signal.**

---

## THE FIX

1. **Add a `deferred` state**, distinct from `void`. A refused-for-a-temporary-
   reason pick becomes `deferred`, carrying the reason and a timestamp.
2. **A `deferred` pick does NOT count against Guard 1.** The game stays open.
3. **It re-enters the queue automatically once the blocking condition clears** —
   the balance is reconciled, cash frees up when a bet settles, the day rolls
   over.
4. **It expires when the game starts.** After first pitch the bet cannot be
   placed at all, so at that point mark it `expired` with the reason, and do not
   silently re-offer it.
5. **Re-price on retry.** The original price is stale. Rebuild the bet at the
   current quote and re-check it still clears its own cost bar — it may no
   longer qualify, and that is a legitimate outcome, not a failure.
6. **`void` keeps its current meaning** and is only reachable by the user's own
   click or a genuine duplicate.

**Do not implement this as "retry everything on a timer".** The point is that
the signal is not consumed; the retry is a consequence, not the feature.

---

## RECOVERY OF THE FOUR

**The two 2026-08-15 games have not started.** If `deferred` existed they would
still be available. **Worth reinstating those two manually** once the balance is
fixed — change their status so Guard 1 no longer sees them as played, and let
the strategy re-price them.

**The two 2026-08-14 games have very likely started.** Those are gone and should
be marked `expired`, not resurrected.

---

## THE BALANCE FIGURES, WHICH ARE THE ROOT CAUSE

He was reading his **portfolio** total and typing it into a box that is compared
against **cash**.

- **Cash: $92.13.** That is what should be typed in the balance box.
- **Money currently out: $8.31** — two open bets, St. Louis $4.25 and Miami $4.06.
- The check computes `start − out + back`, so for it to agree:
  **`account_start_usd` must be $100.44.**
- **`peak_total_usd` should move to $100.44 as well**, or the 35% trailing stop
  measures from a high point he passed days ago.

**Also label the box.** "What Kalshi says your balance is" is ambiguous when
Kalshi shows Cash and Portfolio side by side, and he read the wrong one. **Say
`CASH (not portfolio)`.** That one word caused all of this.
