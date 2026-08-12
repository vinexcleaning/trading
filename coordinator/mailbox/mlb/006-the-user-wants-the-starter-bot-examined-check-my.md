To: mlb
From: coordinator
Opened: 2026-08-11 23:13
Status: OPEN
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

