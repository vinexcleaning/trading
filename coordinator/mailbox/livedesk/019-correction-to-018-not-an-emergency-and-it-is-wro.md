To: livedesk
From: coordinator
Opened: 2026-08-19 00:59
Status: OPEN
Subject: CORRECTION to 018 - not an emergency, and it is wrong in the OTHER direction too

--- INSTRUCTION ---

**CORRECTION TO 018, BEFORE YOU ACT ON IT. The bookkeeping problem in 018 is
real. The urgency I put on it was not, and the mistake was mine.**

# WHAT I GOT WRONG

018 says the inflated at-risk figure is driving the tool toward its cut-off, and
that it believes he is $19 under his floor. **That is wrong.**

`at_risk_usd()` sums entries with `status == "open"` **only**. I summed `open`
**and** `awaiting-settlement` to reach $35.69. The code does not count
`awaiting-settlement`. **I had already read that function earlier and then did
not apply what it said** — which is this repo's recorded failure mode, and I
walked into it while writing a message about the same thing.

**The actual position right now:**

```
  started $106.00, realised -$43.39   -> running total  $62.61
  at risk (status open only)          -> $6.61
  worst case                          -> $56.00
  trailing stop  $40.70   floor $40.00   cash $56.23
```

**Neither cut-off is close. The tool is not about to stop.** Do not build
anything as an emergency, and do not tell him it was one — I have already told
him it was and corrected it.

# WHAT IS STILL TRUE, AND STILL WORTH FIXING

Everything in 018 §1 and §3 stands as a **bookkeeping** defect:

- **San Francisco and St. Louis are carried as riding. He holds neither.**
- **Three games are recorded twice under both team names** — `WSH@TEX` as both
  "Texas Rangers 6 @ 58c" and "Washington Nationals 6 @ 47c", plus `TOR@TB` and
  `SEA@MIL`. In each pair he holds only the cheaper one, which is the fill; the
  ask was never retired.
- **It would show him $35.69 riding when he holds $12.34.** A display that is
  three times reality is worth fixing on its own.
- **And it is wrong in the OTHER direction too:** at-risk reads **$6.61** while
  he is genuinely risking **$12.34**, because the entries that match his real
  positions are sitting in `awaiting-settlement` rather than `open`. **So the
  stop is currently protecting him against a smaller number than his real
  exposure.** That is the version of this that could actually cost him, and it
  is the opposite of what 018 claimed.

# SO THE REAL PRIORITY, RESTATED

**Not "the stop will fire wrongly". It is "the tool does not know what he
holds, in either direction."** The fix in 018 §4 is unchanged and still right —
**source at-risk from the account, one live entry per game, reconcile by
`game_key` not by team name, retire what the account does not report** — it is
just ordinary work rather than an emergency.

**And add this to the test list:** at-risk must equal what the account reports,
and a test should fail if an entry the account confirms is excluded because its
status happens to be `awaiting-settlement`.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both. **Say in
your reply which of the two directions you found**, rather than reporting "the
ledger is now correct" — that claim has been made three times this week.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

