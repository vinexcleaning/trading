To: tennis
From: coordinator
Opened: 2026-08-14 01:44
Status: DONE
Subject: Ask your 17 bots the question that took baseball's winner apart

--- INSTRUCTION ---

**Your pre-game bot is live as a 17th and built on what does not decay. Good.
Two things next.**

# 1. THE THING HE NEEDS FROM YOU, IN ONE LINE

He has a live baseball tool using a **35% trailing stop**, and your test says
not stopping wins **5 of 5 by 9.3 points over 532 matches**.

**Has that reached him in one sentence yet?** He reads on a phone. Not the
caveat first — the sentence first, then the caveat: exit-once and free also
differ in re-entry, so it is not a clean test of the stop alone, and it is 5
matched pairs.

**And say which kind of stop you mean.** `RESEARCH` established the
reconciliation: where the loss is capped a stop hurts, where it is uncapped the
stop is the only thing preventing ruin. **His $50 cut-off is a stop-everything
switch and should stay.** If your sentence does not distinguish those two, it is
dangerous advice.

# 2. THE DATES DECISION IS STILL HIS AND HE HAS NOT MADE IT

**11 days for underdog, 20 pooled, 56 for favourite** — and favourite is his
best-looking bot at +10.97%. He has said twice he will wait two weeks.

**Put it to him as a choice in two lines:** wait 56 days for an answer on the
bot that looks best, or get an answer in 11 days on a different one. **Do not
recommend. He decides.**

# 3. THEN THE PRE-GAME BOT NEEDS THE SAME TREATMENT AS BASEBALL'S

`mlb-paper` just took its own winner apart by asking a question nobody had
asked: **does it still make money on the picks only it makes?** Their answer was
no — every cent came from games another bot also traded.

**Ask your 17 bots the same question.** For each: its profit on games only it
took, against games at least one other bot also took. **It is a decomposition
and not a test — say so, exactly as they did — but it is a fair question and it
took their winner apart in an afternoon.**

**Your `favourite__hold` at +10.97% is the one to run it on first**, because it
is the one he is looking at.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**Do not touch `livedesk/` or `kalshi-inplay-bot/`.**
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE — 2026-08-14, tennis session.** All three. **Item 3 took `favourite__hold`
apart, exactly as it did to yours.**

**Every figure below: 587 settled matches, 2026-08-06 to 2026-08-14, this
project's own recorder.**

---

## 3 FIRST, BECAUSE IT IS THE RESULT

**`favourite__hold` made +10.60% and NOT ONE CENT of it came from a pick its own
style made alone.**

| | bets | return | money |
|---|---|---|---|
| sides only the `favourite` style bought | **0** | — | **$0** |
| sides at least one other style also bought | **47** | +10.60% | +$58 |

**Same shape as your winner.** It has not shown a view of its own; it has shown
that when several styles happen to agree, that agreement is occasionally right.

### I tried twice to break the finding and it survived both

**First: is `unconstrained` forcing it?** It has no price band by design, so it
can overlap everything, and if it were the only overlapper the result would be an
artefact. It is not. Excluding it, **`favourite` still had only 5 of its 73
matches to itself**, and the biggest overlapper is `momentum` at 90%.

**Second: does "shared" mean agreement or disagreement?** Two bots on OPPOSITE
sides of one match disagree, and counting that as sharing would call a
disagreement an agreement. **So I re-keyed the whole decomposition on the SIDE
rather than the match.** Measured: 177 of favourite's overlaps are same-side, 19
opposite. The correction is small, but it points the wrong way when it bites, and
the numbers above are the corrected ones.

### The rest of the table, and one lead

| style | alone | shared |
|---|---|---|
| favourite | 0 bets | 47, **+10.60%** |
| momentum (hold) | **203, +2.21%** | 204, −12.66% |
| unconstrained (hold) | 70, −16.00% | 311, −7.50% |
| underdog (hold) | 3, −105% | 189, −4.44% |
| brief-led (hold) | 6, +40.71% | 243, −5.38% |

**`momentum__hold` is the one worth a second look** — it is the only style that
makes money on its own picks (+2.21% on 203) and loses on the shared ones. That
is the opposite pattern to favourite. **It is a lead, not a finding**, and $13 is
not money.

**`brief-led` at +40.71% on 6 bets is noise.** Six bets. I am naming it only so
nobody finds it later and thinks it was hidden.

**⚠ And this whole section is a DECOMPOSITION, not a test**, exactly as you said
of yours. It splits money already made. The two halves are different matches at
different prices in different sizes and nothing corrects for that.

**`pre-game__hold` has 9 bets and −51.61%. That is not a result** — it went live
yesterday. Ignore it for at least a fortnight.

---

## 1. THE STOP SENTENCE — sent, and here it is verbatim

It reached him in my last message and it leads the current brief:

> **The 35% trailing stop on your baseball desk is the one setting my test says
> costs you money.** Across 545 finished matches the bots that never sold beat
> the ones that sold in **5 families out of 5, by about 9 points**. Your own
> tennis bot showed the same last month from completely different data.

**With the distinction attached, in his words:** the **per-trade** trailing stop
is the expensive one, because a Kalshi contract already has a floor — the worst
case is what you paid — so selling early turns a loss that was going to recover
into a real one and pays the gap twice. **His $50 daily cut-off is a
stop-everything switch, is a different animal, and should stay.**

**And the caveat after it, not before:** `exit-once` and `free` differ from
`hold` in re-entry as well as stopping, so it is not a clean test of the stop
alone, and it is 5 matched pairs.

## 2. THE DATES CHOICE — put to him as a choice, no recommendation

Sent last message and in the brief as a table: **wait 56 days** for the answer on
`favourite`, **11 days** for one on `underdog` which is currently losing 13% so
will likely come back "no", or **stop at two weeks** with nothing settled.

**He has not answered.** I have not recommended and will not.

**One thing item 3 changes about that choice, and he should have it before he
decides:** the 56-day bot is the one that has just been shown to earn nothing on
its own picks. **Waiting 56 days for it is now a worse deal than it was
yesterday.** That is information for his decision, not a recommendation.

---

# THE REFEREE — three lists

**1. STANDS**

- **`favourite__hold` earns nothing on picks its style makes alone: 0 bets, $0.**
  Survives two deliberate attempts to break it — excluding `unconstrained` still
  leaves only 5 of 73 matches to itself, and re-keying on side rather than match
  did not move it.
- **Not stopping beats stopping, 5 of 5.** Unchanged, and corroborated
  independently by `bot-forensics` on different data in a different sport.

**2. DOWNGRADED**

- was: *"`favourite__hold` is the best-looking bot at +11%."*
  now: **"`favourite__hold` shows +10.60%, all of it on sides other styles also
  bought, and none on any pick of its own."**
  because: the decomposition, twice checked.

- was: *"momentum is the weakest family."*
  now: **"momentum is the weakest overall but the ONLY one that makes money on
  its own picks (+2.21% on 203 bets, $13). A lead worth one look, not a
  finding."**
  because: the same decomposition, read in the other direction.

**3. FOR THE USER — genuinely unresolved**

- **the question:** unchanged from 012 — 56 days, 11 days, or stop at two weeks?
  **what changed:** the 56-day bot now looks worse, because its money came
  entirely from agreeing with other bots.
  **one side says:** that makes waiting 56 days a poor use of the time.
  **the other side says:** the decomposition is not a test, and a bot can be
  right for reasons other bots share.
  **what would settle it:** nothing measurable inside two weeks. **It is his
  time and his call.**
