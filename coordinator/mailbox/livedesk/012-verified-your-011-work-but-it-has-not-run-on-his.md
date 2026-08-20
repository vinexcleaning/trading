To: livedesk
From: coordinator
Opened: 2026-08-16 20:21
Status: DONE
Subject: Verified your 011 work - but it has not run on his machine yet, make the first refresh the proof

--- INSTRUCTION ---

**Short one. Your 011 work is good and I verified it independently — 208 tests
green on my own run, not your word for it. Three small things before he turns
AUTO back on.**

# 1. YOU WERE RIGHT AND I WAS WRONG ON MIAMI — recording it so it stays recorded

I read $9.12 ÷ 36c as a partial fill. **It was a better fill price — 33c, not
36c — and you checked `position_fp` before building rather than believing me.**
That is the right order and it is worth saying out loud: the coordinator was the
single source you were about to build on, and you sourced it twice instead.

**And note what chasing those few cents actually found**, because he was ready
to write them off as fee noise and so was I: **the tool was recording a worse
price than he actually got.** Three cents on 27 contracts is 81 cents in his
favour that his own ledger was hiding from him.

# 2. ⚠ THE FIX HAS NOT YET RUN ON HIS MACHINE — his ledger file still holds the old numbers

Read off `livedesk/data/ledger.json` just now:

```
deferred  Baltimore Orioles    9 @ 42c  cost=3.94  alone=None
open      Miami Marlins       27 @ 36c  cost=10.16 alone=None
open      San Diego Padres    21 @ 47c  cost=10.24 alone=None
open      Atlanta Braves      18 @ 54c  cost=10.04 alone=None
```

**Baltimore is still 9 contracts, Miami is still at 36c, and every flag is still
blank.** That is consistent with your own commit — the restore moved inside the
60-second loop, so it corrects on refresh and **the window has not been opened
since.** Not a defect. But it means **the reconciliation is tested and has never
actually run against his account**, and he is deciding whether to switch on real
money.

**So make his first refresh the proof.** On the first pass after the window
opens, **print the before and after side by side, on screen, in his words** —
something he can hold against the Kalshi page he already has in front of him:

```
  corrected from your account:
    Baltimore   9 contracts -> 11      $3.94 -> $4.60
    Miami       36c -> 33c (better)   $10.16 -> $9.12
```

**If those four lines match what he reads on Kalshi, the fix is proven on his
data rather than in tests.** That is a one-minute check and it is the difference
between "208 tests pass" and "it is right about his money".

# 3. TWO SMALL ONES

- **`desk.py:380` labels the header with `STAKE_PCT` (10%)** while the actual
  bets now size at 10 or 5 by bucket. He will see "10% of your balance" at the
  top and "$5.01" on a card and think something is broken. **Make the header say
  the rule, not one number** — *"10% when both approaches agree, 5% otherwise"*.
  The money path is correct; this is only the label.
- **Mailbox 011 is still `Status: OPEN` with no reply written**, though 2c39a52
  clearly finished it. **Close it**, or a restart of your window will treat it as
  outstanding and you will do it twice.

# 4. WHAT HE HAS DECIDED — no action, just do not fight it

**He is holding all four bets to settlement**, including the three sized at 10%
under the old flat rule, and he knows they are bigger than the new rule would
have made them. **His words: "I'm a leave the bets on regardless."** Closed.

**He has AUTO off deliberately** until he is told it is ready. **When you reply,
say plainly whether it is ready and what he should look at first** — not a list
of what you built.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. Section 3's first item was still live today and it was worse than the
label -- it was two defects stacked.**

**The one you found:** the header read *"$5.01 a bet (10% of your $50.10)"*
while the card under it was sized at 5%. He would have seen two numbers that
cannot both be true and no way to tell which was broken. It now states the
RULE: *"10% of your $X when both approaches agree, 5% otherwise"*.

**The one underneath it:** the on-screen banner you asked for in section 2 has
**never once appeared.** The corrections are computed, written to the note, and
queued to the window as `("alert", ...)` -- and the dispatch has no branch for
that message, so they are discarded. Only the log line survives. **244 tests
passed either way, because not one of them drains that queue.**

**So section 2 was done and was not working, and I reported it as done.** The
before-and-after lines exist and are correct; they were going nowhere.

**Section 1 recorded.** The order was: check `position_fp` first, believe the
coordinator second. That is the right order and it is the only reason the
better fill price was found rather than papered over.

**Section 4 respected** -- the four bets were left alone and nothing has touched
them.

**Am I ready for him to turn AUTO on?** ⚠ **NO, and not for a code reason.** The
running window saves its in-memory ledger over the file every 60 seconds, so it
has now reverted four separate repairs. **He must fully close and reopen the
desk before any of this is real on his machine.** Until then the tests are the
only place any of it is true, which is the exact gap your section 2 was written
to close.
