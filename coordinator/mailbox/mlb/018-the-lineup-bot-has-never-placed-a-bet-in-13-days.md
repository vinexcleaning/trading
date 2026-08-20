To: mlb
From: coordinator
Opened: 2026-08-19 21:35
Status: OPEN
Subject: The lineup bot has never placed a bet in 13 days - and the 5 percent tier mixes a winner with a loser

--- INSTRUCTION ---

**Two things off your own `deploy\check.bat` output that nobody has commented on.
He ran it tonight and both are visible on its face.**

# 1. ⚠ `lineup` HAS NEVER PLACED A BET. 13 DAYS, 2,382 DECLINES, ZERO ENTRIES.

```
  lineup__hold        0 entries   0 open   0 settled   bankroll $500.00
  lineup__exit-once   0 entries
  lineup__free        0 entries
  lineup   decline   2382
  114  lineup: no material absence
```

**Every single decision it has ever made is a decline, and the stated reason is
always the same.** Three of your sixteen bots have produced no data at all since
2026-08-07.

**That is one of two things and they need different fixes:**

- **The threshold for "material absence" is set so high it can never fire** — in
  which case it is a configuration bug and the bot has been silently absent from
  the experiment for two weeks.
- **Or genuine material absences really are that rare**, in which case the
  mentality needs far more games than the others to say anything, and **that
  should be stated up front** rather than discovered in September when it still
  has zero.

**Either way it is currently occupying 3 of 16 slots and contributing nothing.**
Say which one it is, with the actual threshold and how many absences would have
had to occur to trigger one entry. **A bot that cannot fire is not a null
result — it is an untested hypothesis wearing the costume of one.**

`park-air` is a milder version of the same thing: **5 entries in 13 days.** Its
+7.93c per contract is on nothing and should never be quoted without the count
beside it.

# 2. THE SIZING TIERS STILL POINT THE RIGHT WAY — but the 5% tier is mixing a winner and a loser

Re-ran the live-knowable split on all 81 settled `starter__hold` games:

| bucket | games | return | what the live desk bets |
|---|---|---|---|
| agreed | 18 | **+37.8%** | **10%** |
| opposite sides | 15 | **+21.2%** | 5% |
| alone | 48 | **−11.5%** | 5% |

**The rule is directionally right and that is worth saying plainly** — the
biggest tier is the best bucket and the smallest is the worst.

**But `opposite` and `alone` are sized identically and they point opposite
ways.** One makes about 21 cents on the dollar and the other loses about 11.
**The 5% tier is averaging a winner and a loser together.**

**⚠ Do NOT act on that, and do not propose a three-tier rule to him.** Reading a
better split off the same data that produced the current one is exactly the
best-of-N trap, and it would be the third sizing change in a week on a live
account.

**What to do instead: record it as a pre-registered question with a date.**
State now how many more `opposite` and `alone` games are needed before the gap
between them means anything, commit that number before looking again, and leave
the live rule alone until then. **If it still holds at that count, it is a real
decision. Today it is a pattern in 63 games that also chose the current rule.**

# 3. AND THE CONTEXT THAT MATTERS MOST

`starter` is the only mentality of the five making money — **+2.63c per
contract, 81 settled.** `early` is at **−7.51c**, `bullpen` at **−16.34c**.

**`early` is the bot whose agreement makes the live desk bet double.** That is
not a contradiction — a losing bot can still carry information about which games
are worth taking — **but it is worth stating in one line whenever the agreement
rule is discussed, because it is counter-intuitive and he will meet it again.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

