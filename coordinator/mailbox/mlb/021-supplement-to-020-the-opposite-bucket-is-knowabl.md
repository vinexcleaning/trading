To: mlb
From: coordinator
Opened: 2026-08-26 21:19
Status: DONE
Subject: Supplement to 020 - the opposite bucket IS knowable at entry, 8 times in 10

--- INSTRUCTION ---

**Supplement to mailbox 020. He asked the two questions that decide whether the
opposite bucket is tradable at all, and both are now measured. Fold these into
that job rather than treating them as new work.**

# 1. HOW OFTEN IT HAPPENS — it is not a rare bucket

All 114 settled games, classified exactly as the live desk would see them:

| bucket | games | share |
|---|---|---|
| agreed | 26 | **23 in 100** |
| **opposite** | **25** | **22 in 100** |
| alone | 63 | 55 in 100 |

**He suspected `agreed` looked good partly because it fired rarely. It does not
— the two buckets fire at almost the same rate.** So frequency is not the
explanation for the difference between them; the explanation is that `agreed`
reversed out of sample and `opposite` did not. **Tell him that plainly, because
he raised it as a possible artefact and it is not one.**

# 2. ⚠ IS IT KNOWABLE AT ENTRY — yes, 8 times in 10, and this is the decisive one

| | games |
|---|---|
| shared games where the other bot was **already in** when `starter` entered | **51** |
| shared games where it arrived **later** | 9 |
| how much later | median **3.7 hours**, worst 23.5 |
| of those 9 late ones, how many turned out opposite | **6** |

**The 25 opposite games in the result are already the entry-knowable ones** —
the classification in 020 uses only what was visible at the bet timestamp, so
late arrivals were counted as `alone`, not as opposite.

> **So the +32.6% figure is achievable as an ENTRY FILTER. No waiting, no
> mid-position reclassification.** That was the open question and it is closed.

**But there is a real cost hiding in it: 6 further games become opposite only
after entry, a median 3.7 hours later.** Those are currently scored as `alone`.
**Measure what they did.** If late-discovered opposites behave like the
entry-known ones, a rule that waits for the flag captures more of the bucket at
the price of a worse fill — and that trade-off is measurable rather than
arguable. **If they behave differently, then "opposite discovered late" is a
different animal and must not be pooled with the other 25.**

# 3. WHAT TO ADD TO THE 020 JOB

- **Report the bucket frequency alongside every return.** A 22-in-100 bucket at
  +32% is a different proposition from a 3-in-100 bucket at +32%, and only one
  of them can carry money.
- **Split `opposite` into entry-known and late-discovered** and report both. Do
  not pool them until they are shown to behave the same.
- **For the late-discovered six: how far had the price moved between `starter`'s
  entry and the moment the flag became true?** He assumes prices drift only a
  few points before first pitch. **Check it against the tape rather than
  accepting it** — if it is small, waiting is cheap; if it is not, the late
  bucket is untradeable and should be said so.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. Report games, never bets.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. The entry-known/late split is measured, and his validation idea works — with the sample caveat stated first.**

# The split you asked for

| | games | return |
|---|---|---|
| opposite, **known at entry** | **26** | +32.6% (your figure, reproduced) |
| opposite, **discovered late** (before first pitch) | **6** | **+33.4%** |
| dropped, flag turned only AFTER first pitch | **0** | — |

**They behave the same.** That is his idea from mailbox 022 working exactly as he intended it to: an independent set of games, nobody selected on, testing the same mechanism, landing in the same place.

**⚠ Six games. That is the honest headline and it goes first.** Six games cannot confirm anything on its own; what it can do is fail to contradict, and it did not. Reported as its own line and never pooled with the 26.

**His constraint was honoured and cost nothing** — I filtered on first pitch and **zero** games were dropped for it. Every late discovery in the current data happened before the game started.

# ⚠ His price assumption — checked against the tape, and he is right

He assumed prices drift only a few points before first pitch, so waiting is cheap.

```
game                    waited   price moved
2026-08-08:CLE@CWS        1.4h        +2c
2026-08-08:NYM@PIT       10.7h        +1c
2026-08-11:BOS@TOR        3.7h        +5c
2026-08-13:KC@LAD         1.2h        +1c
2026-08-14:MIL@LAD        4.1h        +1c
2026-08-25:TEX@CWS        3.2h    no tape (after the archive cutoff)
```

**Median 1 cent, worst 5 cents, over waits of 1 to 11 hours.** Waiting is cheap. **So the late bucket is not untradeable** — the fill barely degrades.

That said, it is moot for a rule: the 26 entry-known games are already available without waiting, so there is no reason to wait. **The late six are worth having as a test, not as a trade** — which is exactly how he framed it.

# Bucket frequency, reported alongside every return from now on

Adopted. And your point stands — `agreed` and `opposite` fire at almost the same rate, so rarity does not explain the difference between them.

# ⚠ BUT — read my reply to 020 before sizing anything on this

I found something that undercuts the bucket labels themselves. **`early` calls 53 in 100 games within 5 cents of even** (1,873 live decisions, its fair sits a median of 4.7 cents from a coin flip). On those games, which side it takes turns on a cent or two of price.

**So "agreed" versus "opposite" is, on roughly half the games, the coin landing differently rather than two models disagreeing.** The +32.6% and the +33.4% may both be partly measuring that.

**The test I want to run next needs no new games:** re-cut both buckets on only the games where `early`'s fair was more than 5 cents from even — where it genuinely had a view. If the effect survives there it is real and much more interesting than it looks now. If it evaporates, the bucket was the coin.
