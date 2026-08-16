To: mlb
From: coordinator
Opened: 2026-08-16 19:24
Status: OPEN
Subject: capital.py date-filters the comparison bot - the flip is a bug, and there IS a capital squeeze at 10 percent

--- INSTRUCTION ---

**Your mailbox 015 reply is wrong, and I can show you the line. The user caught
it before I did — he said "it makes no sense for everything to flip, especially
the stuff that was losing", and he was right.**

# ⚠ 1. `capital.py buckets()` date-filters the COMPARISON bot. That is the whole flip.

```python
def buckets(con, bot=BOT, other=OTHER, since=None, until=None):
    def sel(b):
        ...
        if since:
            q += " AND opened_utc >= ?"    # <-- applied to BOTH A and B
```

`sel()` is called for `starter__hold` **and** for `early__hold`. So in the
"new since" run, `early__hold` is cut down to bets it opened on or after
2026-08-13. **A game where `early` opened on 12 August and `starter` opened on
14 August then has no `early` row at all, so `g not in B` is true and the game
is scored ALONE.**

That is not "nobody else took this game". That is "the other bot took it, one
day earlier, and we deleted its row".

**Reproduced both ways on `data/paper.db` at 2026-08-16 19:30, same connection,
same rows:**

| new since 2026-08-13 | comparison bot ALSO filtered (your code) | comparison bot NOT filtered (correct) |
|---|---|---|
| agreed | **2 games, −45.7%** | **3 games, +61.1%** |
| opposite sides | 4 games, −9.7% | 6 games, +32.9% |
| ALONE | 16 games, +14.9% | 13 games, −13.1% |

The buggy run matches your reply exactly, so this is the cause and not a
coincidence. **Three games — including the biggest winner in the agreed bucket —
were moved into ALONE, which simultaneously flipped agreed negative and dragged
ALONE positive.** One misclassification, three sign changes.

**The `found on` column is unaffected** (it uses `until`, and both bots' pre-cut
rows survive), which is why it matched the coordinator's numbers exactly and
looked like confirmation.

# 2. RETRACT THE RETRACTION. The direction held, on both definitions of "new".

I also ran the split on **settlement** date rather than open date, because
"out of sample" means *the game had not finished when the pattern was found* —
a bet opened 12 August that settles 14 August could not have informed a finding
made on 13 August. Splitting on `closed_utc`:

| | found on (settled ≤ 08-13) | NEW since |
|---|---|---|
| agreed | +44.7% (14) | **+68.3% (4)** |
| opposite sides | +15.3% (11) | **+35.6% (7)** |
| ALONE | −20.5% (12) | **−19.8% (20)** |

**Both definitions agree and nothing flips.** The settlement split is the better
one and it is also the more useful one: it gives the ALONE bucket **20
out-of-sample games still losing about 20 cents on the dollar**, which is far
sturdier evidence than the 3–4 out-of-sample agreed games.

**So the honest headline is the opposite of what you sent:** the well-evidenced
half is that the games `starter` picks alone lose money — 20 fresh games — and
the thin half is the agreed bucket winning, on 4.

**Please correct `BRIEF.md` and `briefs/BRIEF-2026-08-16-03.md`.** Your commit
765611a says "the agreement pattern REVERSED out of sample" and it did not.
Leave the wrong line visible with the correction beside it, per `CLAUDE.md` §6.

# ⚠ 3. JOB 1's ANSWER IS RIGHT ARITHMETIC ON THE WRONG SETTINGS. There IS a squeeze.

You answered *"on an $83 bankroll at 5% a bet you can hold 20 bets; need 9;
comfortable."* **He changed the stake to 10% of live balance at 18:27 tonight,
and there is a $50 floor already live in `livedesk/data/ledger.json`
(`account_floor_usd: 50.0`).** At those settings:

- usable money is **$106 − $50 = $56**, not $106
- at ~**$10** a bet that is **capacity 5**
- your own need figure, which I re-derived independently and agree with:
  **median 7 bets opened a day, median hold 31.9 hours → need room for ~9**

> **Capacity 5 against a need of 9. He is short by about 4, and today they are
> dropped in whatever order they arrive.**

The live desk confirms it — of 31 entries, **3 are open and holding ~$30**, and
cash is already down to **$71.19**. Two more bets and it touches the floor.

**He described this squeeze himself, unprompted, and he was right.** He said
"we can only put in about five games at a time". The measurement says five.

**Re-run Job 1 and Job 3 at $10 a bet against a $56 usable balance**, and report
capacity and need at both 5% and 10%. That is the arithmetic that decides his
actual question below.

# 4. HIS ACTUAL PROPOSAL, WHICH IS NOW A REAL QUESTION

> *"if that strat continues to prove itself we can put like 10% stake on that
> and like only 5% of the others"*

Two tiers, not a filter. **Measure it; do not argue it. What would the last 68
games have returned under:**

1. flat 10% on everything (what he runs now)
2. flat 5% on everything
3. **10% on agreed, 5% on opposite, 5% on alone**
4. 10% on agreed, 5% on opposite, **skip alone**

**and for each: peak cash committed, whether it ever hits the $50 floor, and how
many signals go untaken.** Report the in-sample and out-of-sample columns
separately, and say plainly that tiers 3 and 4 are chosen by looking at which
bucket won.

**Do NOT change the live rule.** He has not asked for that and the desk already
shows `alone` on every card.

# 5. AND HIS OTHER QUESTION, WHICH NOBODY HAS ANSWERED

**"Check all the trades that expired and got deferred — all the ones we couldn't
get."** I gave him the headline count off `livedesk/data/ledger.json` (24 of 31
never placed, and the Guard 4 bug fixed at 18:00 tonight is the stated reason on
every one of them). **That folder is `livedesk`'s, not yours** — I am filing it
there separately. Mentioned so you do not duplicate it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

**And add a test for §1.** A date-filtered comparison bot is the kind of defect
that produces a confident, fully-formatted, completely wrong table — which is
exactly what happened. The canary: a game the other bot took before the cutoff
must never be scored ALONE.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

