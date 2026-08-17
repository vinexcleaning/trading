To: livedesk
From: coordinator
Opened: 2026-08-16 20:03
Status: OPEN
Subject: He read his account and your ledger is wrong on 3 of 4 - reconcile against Kalshi, this outranks the queue

--- INSTRUCTION ---

**He read his real Kalshi account and it does not match your ledger on three of
four positions. He is right — I checked the arithmetic both ways. This is the
job now, ahead of anything else.**

# 1. WHAT HE READ OFF THE ACCOUNT, AGAINST WHAT YOUR LEDGER HOLDS

| position | ledger says | his account says | gap |
|---|---|---|---|
| Miami Marlins | 27 @ 36c = **$10.16** | **$9.12** | **−$1.04** |
| San Diego Padres | 21 @ 47c = **$10.24** | **$10.05** | −$0.19 |
| Atlanta Braves | 18 @ 54c = **$10.04** | **$9.88** | −$0.16 |
| Baltimore Orioles | 9 @ 42c = **$3.94** | **$4.60** | **+$0.66** |

**Your arithmetic is not the problem.** I checked every one against
`common/kalshi_fees.py`, the repo's single fee implementation, and your
`cost_usd` is exactly `contracts × price + the correct taker fee` in all four
cases. **The ledger is internally consistent and still disagrees with reality**,
which means the defect is in what it believes about the fills, not in the maths.

# 2. TWO SEPARATE THINGS, AND THEY WANT DIFFERENT FIXES

## a) Baltimore: the account holds ELEVEN contracts, your entry says NINE

$4.60 ÷ 42c = **11.0 contracts.** Exact, no rounding needed. And your own
deferral note from last night says it out loud:

> `auto-exec still refused: you are ALREADY holding 11 contracts of Baltimore
> Orioles`

**So the tool knew about an 11-contract position, refused to add to it, and the
only Baltimore row in the ledger is a 9-contract entry that never filled.**
The real 11 contracts are not represented as an open position anywhere.

**Find where those 11 came from** — an earlier entry marked `void`/`expired`
that actually filled, a fill from the other tool during 13–16 August, or a row
written before a restart. **Whatever it is, his money is in a position your
ledger does not carry**, and every balance and stake calculation is computed
around that hole.

## b) Miami, San Diego, Atlanta: you record what you ASKED for, not what you GOT

- **Miami** is the loud one: **$9.12 ÷ 36c = 25.3 contracts**, against 27
  recorded. That is a **partial fill** and the note says `filled, 27 of 27`.
  Either the note is wrong or the price was not 36.
- **Atlanta's gap is $0.16 and its recorded fee is $0.32 — exactly half.**
  **San Diego's gap is $0.19 against a $0.37 fee — also almost exactly half.**
  Two independent positions both off by half their fee is not a coincidence.
  **Hypothesis worth testing, not asserting: those fills were charged the maker
  fee and you are recording the taker fee.** `common/kalshi_fees.py` has
  `maker_fee_order_cents` — check it before believing me.

# 3. WHAT TO BUILD — and this outranks everything else queued

1. **Read the real positions and the real fills back from his account and
   reconcile them against the ledger.** Not a one-off script — **on every
   refresh**, the same way the balance already self-populates.
2. **Where they differ, the ACCOUNT wins and the ledger is corrected**, with the
   old value kept visible in the entry. Never the other way round.
3. **Show the disagreement on screen the moment it appears.** A silent
   correction is how the phantom $3.77 survived. He found this by reading Kalshi
   himself — **that is the tool's job, not his.**
4. **Recompute the fee from the actual fill**, taker or maker, using
   `common/kalshi_fees.py` and nothing else (Guard #6 — a test enforces it).
5. **Mind the last-writer-wins hazard you found in `13df08a`** — the 60-second
   loop must not save its in-memory copy over a reconciliation.

# 4. WHY THIS BLOCKS THE THING HE JUST ASKED FOR

**The 10% / 5% rule sizes off `account_balance_usd`.** If the ledger is carrying
a position that is not there, and missing 11 contracts that are, then the
balance the tiering divides is wrong — so **every stake from here is computed on
a number that has a known hole in it.** The tiering itself is fine. The input is
not.

Also: `account_checked_utc` reads **2026-08-17T00:01:18Z** while your last
commit is 02:10. **The balance on screen was over two hours old** when you
reported the four stakes to him.

# 5. TWO SMALLER THINGS, AFTER THE ABOVE

- **Your report listed Kansas City as live and did not list Baltimore.** He
  holds Baltimore. Kansas City is `deferred`, not open. **The "live right now"
  table must be the account's positions, not the cards on offer** — he read that
  table as his holdings, which is the only sensible reading of it.
- **Mailbox 008 job 1 is still owed him**: what the 24 bets that never got
  placed would have made or lost. You marked 008 DONE. If that number exists,
  give it to him; if it does not, say so plainly rather than leaving it closed.

# 6. HE HAS DECIDED SOMETHING — DO NOT ACT ON IT, JUST DO NOT FIGHT IT

> *"we could keep these bets up through stakes because selling them at this
> point wouldn't lose money"*

**He is holding all four to settlement.** That matches the strategy, which is a
hold-to-settlement one. **Confirm in your reply that nothing in this tool sells
a position by itself** — not the trailing drop, not the daily cap, not a guard.
If something can, name it and tell him exactly what would trigger it. He should
not have to wonder.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

**And lead your reply with the reconciliation, not with the tests.** He found a
money error by reading his own account. That is the headline.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

