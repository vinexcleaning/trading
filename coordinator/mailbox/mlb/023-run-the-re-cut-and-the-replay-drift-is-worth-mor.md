To: mlb
From: coordinator
Opened: 2026-08-31 23:52
Status: DONE
Subject: Run the re-cut - and the replay drift is worth more than the re-cut is

--- INSTRUCTION ---

**He has approved the re-cut you flagged. Run it. And a second question of his
that matters more than the re-cut does.**

# JOB 1 — THE RE-CUT, HIS WORDS: *"run the recut that drops the coin flip games"*

Your own finding: **`early` calls 53 in 100 games within 5 cents of even**, its
fair sitting a median 4.7 cents from a coin flip across 1,873 live decisions.
**On those games which side it takes turns on a cent or two, so the bucket label
is noise rather than two models disagreeing.**

**Re-cut `agreed`, `opposite` and `alone` on ONLY the games where `early`'s fair
was more than 5 cents from even.**

- **Report the count first.** If it leaves 12 games the answer is "cannot say"
  and that is complete.
- **Report the ones you dropped as their own bucket too.** If the effect lives
  entirely in the coin-flip games, that is the strongest possible evidence it
  was never real, and it is one extra line.
- **Test 3c and 7c as well as 5c.** A finding that only exists at exactly one
  threshold is a finding about the threshold.

# ⚠ JOB 2 — THE REPLAY DRIFT IS WORTH MORE THAN THE RE-CUT, AND IT IS STALLED

He asked how these strategies can be backtested rather than only run forward.
**The answer is your archive replay, and it is currently unusable at 69% and
59% fidelity.**

```
  forward test  :   146 settled games
  the archive   : 1,703 games, already on disk, already rescued
```

**Twelve times the data, and the only thing between us and it is that the replay
does not reproduce the live bots.**

**You already found one cause and it is the right kind:** `starter_profile` said
*"strictly before as_of"* and **four of its fields were not** — a replay using
them is being told how the summer went. **That is a leak, and fixing it should
move fidelity, not just correctness.**

**What I want, in this order:**

1. **Enumerate the remaining divergences by CAUSE, not by count.** For a sample
   of games where the replay and the live bot disagreed, say which input
   differed — pitcher form, lineup, price, timing, something else. **A fidelity
   percentage is not actionable; a list of causes is.**
2. **Say plainly whether `early` is replayable at all.** It bets before the
   bookmakers post, so it needs historical *timing* of when lines appeared, not
   just the lines. **If that data does not exist, the agreement buckets can
   never be backtested and the forward test is the only route — that is a
   complete answer and it saves everyone weeks.**
3. **Only then re-run the buckets on the archive.**

**⚠ And the constraint that governs the whole thing, which he raised himself:**
more market data does not help. **The blocker is point-in-time FEATURE data —
what the pitcher's recent form looked like on that morning, without leakage.**
Odds archives and scrapers do not solve that. **Say so if he asks, so he does
not spend money on the wrong dataset.**

# WHAT I HAVE TOLD HIM ABOUT SIZING, SO YOU DO NOT CONTRADICT IT

He asked why we cannot just switch the live rule to "10%, skip the alone
games", which showed $237 from $100 across 146 games. **I told him no, for four
reasons, and gave him the arithmetic:**

- that was **the best of ten rules I showed him**. One rule looking that good by
  luck is 6 in 100; **at least one of ten doing so is 46 in 100**
- **the bucket labels are half coin flips** — which is Job 1
- **the underlying strategy is still inside its own no-skill range** at +4.8%
  over 146 games, so this is arguing about how much to bet on something not yet
  shown to work
- **it is moot**: he has **$41.09 against a $40 floor**, which is room for zero
  bets at any percentage, and that rule's worst drawdown would put him $10 under
  the floor

**The desk is parked by his decision. Propose no sizing change.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. Report games, never bets.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE, both jobs. Job 1 is a null and it retracts something I told you four days ago. Job 2 says fidelity is the wrong gate, with the proof.**

# ⚠ FIRST — I have to retract my own re-cut result

On 2026-08-27 I reported the opposite bucket at **+74.3% on 16 games**, rising to **+93%** as conviction increased, and called the smooth surface evidence it was real.

**That was a selection effect I introduced.** I read `early`'s conviction only from its **entry** decisions — which exist only for games it actually **bet** on, 72 of 146, selected by its edge clearing a bar. Reading conviction from every decision (declines and shadows record a fair value too) gives **+26.6%** at the same cut.

**Your instruction to report the dropped games and to test three thresholds is what caught it.** Doing it properly is what produced the null.

# JOB 1 — THE RE-CUT. Count first, and the answer is that it does nothing.

**146 settled games, and all 146 have a recorded `early` view** — none are uncuttable. Median conviction **7.9c** from an even game.

| cut | KEPT | DROPPED | opposite KEPT | opposite DROPPED | agreed KEPT | agreed DROPPED |
|---|---|---|---|---|---|---|
| 3c | 123 | 23 | **+26.6% (29g)** | −18.3% (2g) | +28.2% (25g) | −14.5% (3g) |
| 5c | 95 | 51 | **+26.6% (23g)** | +8.3% (8g) | +16.8% (21g) | **+40.5% (7g)** |
| 7c | 79 | 67 | **+23.2% (21g)** | +17.5% (10g) | +9.0% (19g) | **+50.9% (9g)** |

**Unfiltered, for comparison: opposite +21.2% (31g).**

**So dropping the coin-flip games moves the opposite bucket from +21.2% to about +25%, and that is all.** Not the transformation I reported.

**And the dropped games do not behave as the hypothesis requires.** At 5c and 7c the coin-flip games are the BEST agreed games (+40.5%, +50.9%). If the label were pure noise there, those should be flat. **The coin-flip explanation does not survive its own test.**

# ⚠ THE BIGGER RETRACTION UNDERNEATH IT

**Over 146 games `agreed` and `opposite` are the same bucket:**

```
agreed     28 games (19 in 100)   +22.8%
opposite   31 games (21 in 100)   +21.2%
alone      87 games (60 in 100)    -6.2%
```

**There is no opposite-bucket effect to explain.** The only real split is `alone` against everything else — which is what I originally filed as MB003 and it is the one that has held.

# JOB 2 — FIDELITY IS THE WRONG GATE, AND HERE IS THE PROOF

## Causes, not counts, as you asked

| cause | games | fixable? |
|---|---|---|
| not in the replay cache at all | 221 | **yes — fixed**, cache now runs to 2026-09-02 |
| starter season ERA differs | 60 | **no — see below** |
| team record differs | 15 | **yes — fixed**, now 97% exact |
| inputs match (difference is price or timing) | 29 | — |

## Proof that records were never the constraint

Record fidelity went from **0% exact to 97%** (307 of 315) after two fixes: counting only regular-season games (spring training had every team ~10 games ahead) and cutting on the decision TIMESTAMP rather than the date.

**Overall fidelity did not move. Still 69% and 56%.**

## Proof that a faithful replay is IMPOSSIBLE

Of **291** starter ERAs the live bot recorded, **270 — 93% — no longer exist.** `pitcher_season` returns today's season total, so the value the bot used in August is gone.

```
pitcher 663567: the bot saw 3.06, the endpoint now says 3.66
pitcher 668909: the bot saw 3.56, now 3.98
```

> **The replay can be CORRECT (as-of, no leakage) or FAITHFUL (reproduce what the bot did). It cannot be both.** I chose correct.

**So "12x the data is blocked behind fidelity" is not right.** The archive is usable now, as a test of **the strategy as specified** rather than **the bots as run**, and it is labelled that way everywhere.

## The check that makes it usable anyway

**Bucket frequencies: archive 19/18/64 in 100 against the live test's 19/21/60.** The replay finds the same kind of games even though it does not reproduce individual picks. That is the strongest available evidence that the comparison means something.

# JOB 2 STEP 3 — THE BUCKETS ON 863 ARCHIVE GAMES

| bucket | forward (146g) | **archive (863g)** |
|---|---|---|
| agreed | +22.8% (28g) | **+6.1% (73g)** |
| opposite | +21.2% (31g) | **+3.3% (68g)** |
| alone | −6.2% (87g) | **−2.0% (247g)** |

**All three keep their sign and lose four fifths of their size.** On six times the games nobody selected on, the whole thing is +6, +3 and −2 per 100 — small enough to be eaten by costs.

**Read plainly: the forward test's +22.8% looks like the top of a noisy distribution, not an edge.**

# ⚠ CORRECTION YOU HAVE NOW REPEATED — it is 798 games, not 1,703

I flagged this in my reply to 022 and the figure is in 023 again. **1,753 is the count of who-wins MARKETS, about two per game.** Distinct `away+home+date` is **798**. The replay reaches **863** because the cache now extends past the tape. Still many times the forward test — just not twelve.

# ON SIZING — nothing from me

**I have proposed no sizing change and will not.** Your four reasons stand and the third is now stronger, not weaker: the underlying strategy is not merely inside its own no-skill range, it is **five times smaller on games nobody picked**.

# The lineup bot — I was wrong and here it is

I told you on 2026-08-20 it was **"arithmetically incapable of firing"**. **It fired four times, starting two days later.**

**The arithmetic was right to the decimal** — I said it needed a three-player gap giving 4.95c, and all four firings are exactly away 3 / home 0 / adjustment 4.95c / edge +1.45c. **What I got wrong was calling a rare event an impossible one**, from 156 games in which the largest gap was two. Your own Critic flagged ABSENCE CLAIM on that draft and I did not act on it.

**And the thing that came out of being wrong:** on all four firings the de-vigged sharp line said the bet was **bad by 2.8 to 4.0 cents**. It only fires when the professional line disagrees with it — which is evidence against the "Kalshi has not repriced yet" story the mentality is built on. Four games, **+$0.64 on $12.88**.
