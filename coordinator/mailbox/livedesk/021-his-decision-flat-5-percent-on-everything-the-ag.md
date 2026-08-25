To: livedesk
From: coordinator
Opened: 2026-08-24 23:55
Status: OPEN
Subject: His decision - flat 5 percent on everything, the agreement rule reversed out of sample

--- INSTRUCTION ---

**His decision, in his own words: "Put five percent flat on everything." This is
a live-money sizing change. Make it, log it, and do not improve on it.**

# 1. THE CHANGE

`livedesk/src/money.py`:

```
STAKE_PCT_AGREED = 10.0   ->   5.0
STAKE_PCT_OTHER  =  5.0   ->   5.0   (unchanged)
```

**Change the numbers only. Do NOT rip out the bucket machinery.**
`bucket_for()`, `stake_pct_for()`, `stake_for_bucket()` and their tests all stay
exactly as they are, and the card keeps showing which bucket a bet is in. Two
reasons: the classification is still the right thing to *record*, and if the
evidence ever comes back this is a one-number change rather than a rebuild.

**Everything else is untouched:** the $40 floor, `MAX_STAKE_USD` $50, the 35%
trailing stop, the pause/resume behaviour, the reconciliation, the alerts.

# 2. WHY — and it is not a preference

Measured on `mlb-paper/data/paper.db`, `starter__hold`, split on **settlement
date**, classified using only what was knowable at bet time:

| bucket | the 81 games the rule was built on | **the 24 games since** |
|---|---|---|
| agreed | **+37.8%** (18) | **−28.6%** (6) |
| opposite | +21.2% (15) | +35.6% (7) |
| alone | **−10.1%** (47) | **+39.0%** (11) |

**All three reversed.** Over all 104 games the `alone` bucket is now **−0.9%** —
the finding that the tiering rested on has dissolved to zero.

**⚠ This is NOT the defect from 2026-08-16.** That reversal was an artefact of
`capital.py` date-filtering the comparison bot. This was computed directly, with
the comparison bot unfiltered and the split on `closed_utc`. **Both of the things
that were wrong last time were checked first.**

# 3. ⚠ WHAT MUST NOT HAPPEN — do not invert the rule

**The obvious move is to bet 10% on `alone` now, because it made 39%. Do not,
and do not propose it.** That is selecting on the newest slice, which is exactly
how the original rule was produced. **A rule that reverses when new data arrives
did not survive; the answer is to stop tiering, not to tier the other way.**

Flat is not a claim that the buckets are identical. It is the honest default
when the thing that distinguished them stopped distinguishing them.

# 4. RECORD IT

`livedesk/DECISIONS.md`, with today's date and his wording — **"Put five percent
flat on everything"** — plus the table above and one line saying what would make
us revisit it. **Suggested trigger, and pre-register it rather than deciding
later: 40 further agreed games.** Write the number down now so that if somebody
looks in a month, the bar was set before the data arrived.

**And leave the previous rule visible** rather than deleting it. The 10%/5% tier
ran from 2026-08-18 to today and its results are part of his record.

# 5. WHAT HE SHOULD SEE

The header currently describes the sizing rule. **It must now say a single
number.** And the card should still name the bucket — *"both approaches like
this one"* — but without implying the stake changes because of it.

**Nothing about open positions changes.** This affects new bets only.

# 6. TESTS

- both tiers return the same stake for the same balance
- a missing/unknown flag still sizes to 5% and never to no-bet
- the floor, the cap and the trailing stop are unchanged
- **and keep the existing bucket tests green** — they are still meaningful

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Tell him plainly that the rule he
approved a week ago has been withdrawn on evidence, and that this is a
simplification rather than a new bet.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

