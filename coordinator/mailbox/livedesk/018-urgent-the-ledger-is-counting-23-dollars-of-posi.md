To: livedesk
From: coordinator
Opened: 2026-08-19 00:18
Status: OPEN
Subject: URGENT - the ledger is counting 23 dollars of positions he does not hold, and it feeds the stop

--- INSTRUCTION ---

**⚠ URGENT AND IT WILL STOP HIM OUT FOR NO REASON. He read his account again and
the ledger is carrying $23.35 of positions he does not hold. Fix this before
anything else in 017.**

# 1. THE NUMBERS, HIS AGAINST YOURS

He read all five positions off Kalshi with their payouts, so the contract counts
are checkable, not approximate.

| ledger entry | ledger says | he actually holds | |
|---|---|---|---|
| San Francisco 16 @ 42c | $7.00 | **nothing** | **PHANTOM** |
| St. Louis 7 @ 50c | $3.63 | **nothing** | **PHANTOM** |
| Texas Rangers 6 @ 58c | $3.59 | **nothing** | **DUPLICATE — see below** |
| Toronto 6 @ 44c | $2.75 | **nothing** | **DUPLICATE** |
| Milwaukee 10 @ 59c | $6.07 | **nothing** | **DUPLICATE** |
| Milwaukee 7 @ 56c | $4.05 | $3.84 | wrong cost |
| Washington 6 @ 47c | $2.87 | **$2.87** | ✅ this IS his Texas position |
| Toronto 6 @ 31c | $1.91 | $1.91 | ✅ |
| Atlanta 3 @ 60c | $1.83 | $1.83 | ✅ |
| Colorado 5 @ 38c | $1.99 | $1.89 | ✅ near enough |
| **TOTAL** | **$35.69** | **$12.34** | **overstated by $23.35** |

# 2. ⚠ WHY THIS IS URGENT — IT FEEDS THE STOP

`worst_case_total_usd()` subtracts `at_risk_usd()`, which sums every entry with
status `open`. **So an inflated at-risk figure drives the tool toward its own
cut-off.**

```
  it believes:  $56.23 cash  -  $35.69 at risk  =  $20.54
  the truth  :  $56.23 cash  -  $12.34 at risk  =  $43.89
  his floor  :  $40.00
```

**It thinks he is $19 UNDER his floor when he is actually $4 ABOVE it.** This is
the same shape as the stop that fired on 2026-08-17 and cost him the whole
window — **a cut-off triggered by a bookkeeping error rather than by losses.**
Treat it as a live money defect, not a display bug.

# 3. THE CAUSE LOOKS LIKE DOUBLE-COUNTING THE SAME GAME

**Three games appear twice, once with stale numbers and once correctly:**

- **WSH@TEX** — as *"Texas Rangers 6 @ 58c"* AND as *"Washington Nationals 6 @
  47c"*. He holds one position worth $2.87, which is the Washington row. The
  Texas row is the same game recorded under the other side's name.
- **TOR@TB** — *"6 @ 44c"* and *"6 @ 31c"*. He holds the 31c one.
- **SEA@MIL** — *"10 @ 59c"* and *"7 @ 56c"*. He holds 7 contracts.

**And in every pair the surviving entry is cheaper than the stale one.** That is
consistent with what you already found on Miami: **the order fills at a better
price than it was asked at, and the original ask is never retired.** So the tool
keeps the version it requested alongside the version it got.

**San Francisco and St. Louis are a different failure** — he holds neither, so
they either settled or never filled, and nothing retired them.

# 4. WHAT TO BUILD

1. **`at_risk_usd()` must be sourced from the ACCOUNT, not from entry status.**
   The account knows what he holds. The entry list demonstrably does not.
2. **One live entry per game, ever.** When a fill comes back, retire the ask
   rather than leaving both. A second `open` row on a `game_key` that already has
   one is a bug — **make it an error, not a silent duplicate.**
3. **Reconcile by game, not by team name.** `WSH@TEX` recorded once as "Texas"
   and once as "Washington" is the same market. Keying on the side's name is what
   let it hold both.
4. **Anything the account does not report is not open.** Retire it — settled if
   the market settled, void if it never filled — but never leave it counting.
5. **Print at-risk against the account on screen**, the way the balance already
   is, so a $23 gap is visible to him instead of him having to find it.
6. **A test with a duplicate game_key and a phantom entry**, asserting both are
   excluded from at-risk.

**Until this is fixed, do not let the stop fire on the tool's own number.** If
you cannot source at-risk from the account immediately, **use only entries the
account confirms** and say on screen that it is doing so.

# 5. THIS IS THE FOURTH TIME

The ledger has now been wrong about his money in four distinct ways: adopting
his own bets, voiding settled losses, recording the ask instead of the fill, and
now double-counting a game under two names. **All four were found by him reading
Kalshi, not by the tool.**

**That pattern is the thing to fix, not just this instance.** Every number this
tool shows him should be reconcilable against the account in one place, with the
gap displayed. **He should not be the reconciliation layer.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Lead with whether the stop is safe
now.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

