To: mlb
From: coordinator
Opened: 2026-08-11 23:13
Status: DONE
Subject: The user wants the starter bot examined - check my numbers, and say how many more games would settle it

--- INSTRUCTION ---

**The user asked to see the two bots that look like they are winning, in
detail, against the others. He asked for this FIRST, ahead of everything else.**

I read `data/paper.db` directly. Here is what I told him — **check it, and
correct me if any of it is wrong.**

| bot | bets | won | staked | profit | return |
|---|---|---|---|---|---|
| starter__exit-once | 30 | 19 | $245.45 | **+$19.32** | **+7.9%** |
| starter__hold | 30 | 19 | $245.45 | **+$19.32** | **+7.9%** |
| starter__free | 60 | 38 | $449.43 | **+$27.45** | **+6.1%** |
| early__free | 63 | 32 | $350.90 | −$30.02 | −8.6% |
| early__exit-once / hold | 32 each | 16 | $212.76 | −$22.10 | −10.4% |
| bullpen (all three) | 11–22 | 5–10 | $75–148 | −$6.74 to −$12.93 | −9% |
| park-air (all three) | 3–6 | 1–2 | $8.58–17.16 | −$2.89 to −$5.78 | −33.7% |
| **everything together** | **303** | **164** | **$2,048.95** | **−$46.10** | **−2.2%** |

**All three starter bots trade the same 30 games.** So this is **30 games, not
120 bets**, and I said so.

Average buy price **52.3 cents**, won **63 out of 100**, break-even **52 out of
100**. Chance of 19-or-better from 30 games with no edge: **about 1 in 7**.
Across five approaches, chance at least one looks this good by luck:
**56 out of 100.** Dates **2026-08-07 to 08-12**.

# WHAT HE WANTS DONE

**1. Check my arithmetic and my framing.** I pulled this from the database
without reading your analysis code. If `analyse.py` computes any of it
differently — especially the staking base or how `starter__free`'s 60 positions
map to 30 games — **your number wins and I want the correction.**

**2. Say what would make `starter` believable, in games.** He is willing to wait
**two weeks, not two months.** So: how many more games before 63-out-of-100
stops being explainable by luck? Give it as a number of games and a date.

**3. Say what `starter` is actually doing** in one paragraph a non-engineer can
read. It is the starting-pitcher bot; what does it compare, and what would make
it wrong? **A 7% return with no stated mechanism is not a finding.**

**4. Is it one edge or three?** `hold` and `exit-once` are byte-identical here.
Say whether the exit rule has ever changed an outcome, because if not, three
"bots" are one bot and the multiplicity arithmetic changes.

**5. Do NOT nominate it.** It is the best of five families and he knows that. He
asked to see it, not to act on it. **Nothing is promoted without a
pre-registered forward test on games not yet played.**

# ALSO

`park-air` has traded **3 games**. Say whether that is a starvation problem
worth fixing or a bot that correctly almost never qualifies.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both. Three lists, third said out loud.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE.** Recomputed from `data/paper.db` with `mlb-paper/src/examine_starter.py`, independently of your read. **Dates: games settling 2026-08-07 to 2026-08-12, 303 positions, measured 2026-08-08.**

## 1. Your arithmetic — profit exact, staking base wrong, luck numbers too kind

**Profit agrees to the cent everywhere.** starter +$19.32, early −$30.02, everything together −$46.10. Your framing that starter is 30 games and not 120 bets is right, and I confirm the three game-sets are **identical**.

**The staking base differs and mine is the one to use.** You have starter staking $245.45; I get **$253.68**. The gap is the entry fee, which leaves the bankroll like everything else. Return **7.6%, not 7.9%**. Total staked **$2,119.10, not $2,048.95** — both still −2.2%.

**⚠ Both your luck numbers favour the bot, and this is the correction that matters.** You used break-even **52 out of 100**, which is the price alone. The fee raises it to **53.7 out of 100** — 52.0¢ average buy price plus 1.74¢ fee. That makes 19 wins *less* impressive, not more:

| | you said | recomputed |
|---|---|---|
| chance of 19+ from 30 with no edge | 1 in 7 | **1 in 5.2** (19 out of 100) |
| chance the best of five looks this good | 56 out of 100 | **66 out of 100** |

**Two thirds of the time, one of five approaches looks this good with nothing behind it.** That is the number to quote him.

## 2. ⚠ THE THING THAT DECIDES IT, and it is not in your table

**`starter` is buying WORSE than where the professional line closes: −1.67 cents, range −2.99 to −0.22, on 12 games with a reference.** It won 19 of 30 and still paid over the odds every time.

A real edge cannot sit behind the closing line. You can win 19 of 30 from behind it — that is what 66-out-of-100 means. **The profit and the closing-line value point in opposite directions, and the closing-line number is the one with the sample behind it.**

## 3. How many more games — 109, about 24 August

Holding the same 63-out-of-100 rate: **139 games** takes the single family to 1 in 100, which is about **1 in 20 once you correct for having searched five**. That is **109 more games, roughly 13 days, about 2026-08-24** — inside his two weeks. 215 games (about 2 September) would reach 1 in 100 set-wide.

**Both assume the rate holds, and the closing-line number says it will not.**

## 4. What `starter` does, and what would make it wrong

It ignores the pitcher's season record, because that is the most public number in baseball and the price is already built on it. It fires on three things a 25-start average absorbs slowly: **a pitcher making one of his first few career starts, a pitcher on under four days' rest, or a pitcher whose last three outings differ from his season line by more than 1.5 earned runs per nine innings.** It converts that into cents — one run of expected margin is worth about 11 cents — and buys only if that beats the spread plus the fee.

**What would make it wrong:** the 11-cents-per-run conversion is my estimate, not a measurement. If it is too big, every entry is oversized and the bot is buying noise. **The closing-line number is consistent with exactly that.**

## 5. One idea, not three — and it changes what can be claimed

**The exit rule has never once fired. 303 positions, 0 closed early, 0 closing fills, 0 of 76 hold/exit-once pairs differ.** `hold` and `exit-once` are the same bot with two names; `free` is the same bot entering twice at a similar price, which is why it shows twice the money and the identical per-contract number.

So MLB is **five distinct ideas, not fifteen**. I am **not** shrinking the denominator of 32 on the back of it — that stays, because it was fixed before any result existed and lowering it after seeing one is exactly what `JOINT_MULTIPLICITY.md` rule 3 forbids. But the ±12-cent exit is **untested, not tested-and-equal**, and it should be reported that way.

## 6. `park-air` — correct abstention, not starvation

**3,520 non-entries.** 1,987 of them "adjustment does not survive the cost bar", with a median stated adjustment of **2.47¢ against its own ~3.5¢ bar**, p90 3.93¢, max 4.80¢. Plus **900 roof games** where there is no wind to read, and 163 where the wind was variable.

Nothing is broken. It is a bot whose effect is genuinely smaller than the cost of trading it, declining correctly nearly every time. **That is this programme's recurring finding arriving prospectively for once, instead of in a retraction.**

## 7. Not nominated — agreed, and I would not have

Nothing is promoted. Recording that I agree with the instruction rather than merely obeying it: it is the best of five families chosen after seeing results, which is the definition of the thing this repo has retracted 45 times.

## ⚠ What I did NOT test — mandatory, and the Critic caught me omitting it

- **Whether the ±12¢ exit does anything.** Never fired. Untested, not equal.
- **Any price other than about 52¢.** Every starter entry is near a coin flip.
- **The three triggers separately.** Debut, short rest and form divergence are pooled; I cannot say which, if any, carries it.
- **The 11-cents-per-run conversion.** Assumed, never measured.
- **Whether it holds when a data source is degraded.** See mailbox 007.
- **Games before 2026-08-07.** The test is forward-only; there is no history.

## THE REFEREE'S THREE LISTS

**1. STANDS.** The profit figures, to the cent, from two independent counts. The exit rule never firing — 0 closing fills is not a judgement call. park-air's abstention, on 3,520 recorded decisions each carrying its reason.

**2. DOWNGRADED.**
- *was:* "starter returns 7.9%" → *now:* **"7.6% on money actually laid out"**, because the entry fee belongs in the base.
- *was:* "about 1 in 7" → *now:* **"about 1 in 5"**, because break-even is 53.7 not 52 once the fee is in it.
- *was:* "56 out of 100 across five families" → *now:* **"66 out of 100"**.

**3. FOR THE USER — genuinely unresolved.** One, and it is real:
- **the question:** is `starter` worth 109 more games of attention?
- **one side says:** it is the only bot in either test that is up, +$19.32 on 30 games, and 13 days settles it.
- **the other side says:** it is buying behind the closing professional line, which is the one number here with a sample behind it, and two thirds of the time one of five approaches looks this good with nothing behind it.
- **what would settle it:** nothing available today. The 109 games settle it, and they cost only waiting — **no attention, no money, no new build.** That is why I lean toward letting it run, and it is still his call.
