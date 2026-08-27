To: mlb
From: coordinator
Opened: 2026-08-26 21:13
Status: OPEN
Subject: Run bullpen inverted as the 17th bot - and his opposite-bucket observation is correct

--- INSTRUCTION ---

**Two jobs from him, and the second is his own observation, which is correct and
is the strongest signal currently in this project.**

# JOB 1 — RUN `bullpen` INVERTED AS A 17TH PAPER BOT

**His words:** *"go ahead and run bullpen as the seventeenth bot."*

## Why this one and not the other losers — his reasoning, and it is right

> *"We need to take away bad strategies that are bad because of the fees... but
> if we find a purely bad strategy that isn't just getting killed by the fees,
> pretty much what that's telling us is that this site is picking the wrong
> side. So we just pick the other side."*

**That is a real and computable distinction and it holds up.** Measured, buying
the opposite side with real fees at three spread assumptions:

| bot | as-is | flipped @1c | @2c | @4c |
|---|---|---|---|---|
| **`bullpen__free`** | −34.3% | **+25.8%** | **+23.4%** | **+18.9%** |
| `bullpen__hold` | −35.2% | +26.7% | +24.3% | +19.8% |
| `early__free` | −14.9% | +5.1% | +3.3% | **−0.3%** |
| `early__hold` | −15.4% | +5.7% | +3.8% | +0.3% |

**`early` is the control case that proves the distinction is real:** it loses
about what it costs to trade, so flipping it gains almost nothing and dies
entirely at a 4-cent spread. **`bullpen` loses far more than trading costs,
which means it is actively selecting the wrong side rather than leaking fees.**

## ⚠ AND THE REASON THIS IS NOT YET A FINDING

**32 games, and it was chosen as the worst of 16 bots.**

| | |
|---|---|
| a bot landing this badly by pure chance | 2 in 100 |
| **at least one of 16 doing so with no skill anywhere** | **28 in 100** |

**Selecting the worst of sixteen and inverting it is the same selection effect
as promoting the best of sixteen, in a mirror.** He knows this — he raised the
large-sample requirement himself.

Also: `bullpen__free` is **64 bets across 32 GAMES**. Report games.

## WHAT TO BUILD

- **A 17th bot, paper only, that takes the opposite side of every `bullpen`
  signal.** Same entry timing, same sizing rule, real ask on the side it buys.
- **`PREREGISTRATION_INVERSE.md` committed before it starts**, stating: how many
  GAMES before it can be judged, and **what result drops it.** He specifically
  warned that a good first week will be tempting and will mean nothing — write
  the number down first.
- **Run the inversion over the existing history as the in-sample figure**, and
  label it as in-sample. The forward run is the only thing that counts.
- **A placebo**: invert a bot that is merely fee-losing (`early`) and one that is
  flat. If inverting those also looks good, the machinery is finding noise.

**No money. No change to `livedesk`.**

# ⚠ JOB 2 — HIS OWN OBSERVATION, AND IT IS THE STRONGEST THING WE HAVE

> *"The top one flipped... the opposite one didn't flip, though. The opposite one
> stayed positive. I think it was a little less, but it still stayed positive.
> And then the single one actually flipped. So I wanna look more into the
> opposite games."*

**He is right on all three counts, and one of them nobody had noticed.**

| bucket | built on (81 games) | since (24 games) | flipped? |
|---|---|---|---|
| agreed | +37.8% | **−28.6%** | **yes** |
| **opposite sides** | **+21.2%** | **+35.6%** | **NO — and it improved** |
| alone | −10.1% | **+39.0%** | **yes** |

**And on all settled games, each bucket against its OWN no-skill range:**

| bucket | games | return | luck range | beaten by luck |
|---|---|---|---|---|
| agreed | 26 | +18.7% | −38.1% to +30.9% | 15 in 100 — inside |
| **opposite** | **25** | **+32.6%** | **−37.2% to +30.2%** | **4 in 100 — OUTSIDE** |
| alone | 63 | −0.8% | −24.9% to +18.0% | 42 in 100 — inside |

> **`opposite` is the only bucket in this project sitting outside its own
> no-skill range, AND the only one that did not reverse out of sample.**

**That combination is what makes it worth work.** Everything else here has had
one or the other and never both.

## What to actually do with it — and the discipline that applies

1. **Attack it first.** Three buckets were examined, so a 4-in-100 result on one
   of them is roughly **12 in 100** before you are impressed. **Say that number
   out loud in the report.**
2. **What IS the opposite bucket, mechanically?** It is games where the pitcher
   model and the early model take **different sides**. Someone has to say what
   that means: is `starter` right and `early` wrong, or does disagreement itself
   mark a game where the price is unusually wrong? **Those predict different
   things and they are separable** — check whether `early`'s side loses by more
   than its own cost bar on exactly these games, which is Job 1's test applied
   to a subset.
3. **Segment it**: entry price, favourite status, how far apart the two models
   were, time between the two entries.
4. **Pre-register a count and a date** before looking again.
5. **Do NOT propose a live sizing change.** The tiering was withdrawn eight days
   ago because it reversed. **This bucket has 25 games.**

# ONE THING TO SAY BACK TO HIM PLAINLY

He wrote: *"we have a seven percent edge on that, but it's only on a very small
sample of games, which makes me think that it's literally only like that because
of luck."*

**He is right and it is already measured.** `starter__hold` is **104 bets at
+9.2%**, and a no-skill bot on the same bets beats that **11 times in 100** — it
sits inside the range. **Confirm it in one line.** He reached the correct
conclusion about his own bot unprompted and should be told so rather than having
it softened.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Report games, never bets.**

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

