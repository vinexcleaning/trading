# His soccer knowledge, as variables — recorded 2026-08-19

**His answers to the six questions in `QUESTIONS_FOR_HIM.md`, arriving via
`coordinator` mailbox 004.** This file exists so the answers become *columns in
the tape* rather than a conversation nobody can find in November.

**Two of the six are "I don't know". Those are recorded as answers, not gaps.**

---

## ⚠ THE HEADLINE: the variable is the CLUB, not the league table

Three of his six answers are the same shape, and it is the shape this repo has
already been burned by ignoring.

> *"Real Madrid's the type of team that if they score the first goal, they're
> gonna keep trying to score. But Manchester United, it's very likely that if
> they score the first goal, they're gonna park the bus no matter who they're
> playing against."*
>
> *"You have to analyse the team throughout the entire year, what have they been
> doing. And it's not hard to analyse them, but you're gonna have to figure that
> one out."*

**And the sentence that kills the simple version outright:**

> *"A better team with better players will sometimes park the bus even playing
> against the worst team. Usually they won't, but it depends on the team's
> tactics."*

**So "sees the game out" is real, is per-club, and is NOT predicted by table
position.** It has to be learned from each club's own record of what it did
after going ahead.

**Why this matters more than it looks.** The most expensive recorded mistake in
this repo is a sweep over *price and market features* being used to close a
question about *individual players* — a different variable entirely, and a live
idea died of it. **He has just said the same thing about soccer.** A
league-wide average will show nothing here, and a null reported off one would be
that mistake repeating.

**Direct consequence:** `SF018` was written on top-third / bottom-third of the
domestic table. **That is now amendment A2 of `PREREGISTRATION_HOLDON.md`, made
before any result exists.**

---

## The variables, one per answer

### Q1 — rotation before a European tie. Answer: it depends on the stakes in BOTH games

- *"If Inter Milan is fighting for the Serie A title and they need to win, and
  two days later they have the Champions League final — they're gonna put their
  best teams for both games."*
- *"If it's Nottingham Forest and they're eighth, not fighting for anything, and
  they have Champions League two days later, it's much more likely they're gonna
  put in a weaker team for the game before."*

**⚠ The distinction that changes the measurement, and it is his:**

> *"They might put the same team though. It might not put them at full effort."*

**Rotation is not only personnel.** A club can field its first eleven and not
try. **Any line-up-based variable scores that match as full strength and is
wrong.** Written down now rather than discovered later.

**The one cleanly testable rule in the answer:**

> *"At the beginning of the league, teams usually always come with their A game,
> even if they have an important Champions League final a few days later.
> Towards the end, once the results are kind of defined, then it changes."*

| variable | how it is recorded |
|---|---|
| **matchday number** | from the fixture list; low = early season |
| **is the table still in play for this club** | points gap to the objective (title, top four, relegation) |
| **stakes in the OTHER game** | competition and round of the fixture within 4 days |
| **days since last fixture** | see Q2 |

**Predicted shape, stated in advance:** rotation effects near zero early in the
season, growing as league positions settle. **If that gradient is absent, his
rule is wrong and it is reported as wrong.**

### Q2 — already through, or already out. Answer: NOT the variable. Fixture load is

He warned against the obvious assumption unprompted:

> *"Don't completely rely on this. Basic assumptions say these teams should play
> their weak teams. But usually what these teams are doing is they still play
> their strong teams because they wanna give their teams more practice."*
>
> *"You can assume that most likely if the team's in and you have a lot of
> games, then they're gonna be tired... weaker versions of themselves. Whether
> it's the same players playing weaker, or reserves."*

| variable | note |
|---|---|
| **games played in the last 10 / 14 days** | **the driver**, per him |
| qualification status (through / out / alive) | **secondary flag only** |

**He has effectively told us the naive version of this spec is wrong before it
was written.** That is worth more than a confirmation.

### Q3 — going one goal up early. Answer: per-club, both directions

Named examples, usable as a labelled starting set:

| club | what he says it does after going ahead |
|---|---|
| Real Madrid | keeps pushing for more |
| Manchester United | *"very likely to park the bus no matter who they're playing against"* |
| Nottingham Forest, 1-0 up on Arsenal | *"all their players in the back... Arsenal will more than likely score and win or at least tie"* |

**Variable: a per-club "what happened after this club went 1-0 up" history,
built from that club's own season.** Not table position.

### Q4 — which competitions behave differently. Answer: "I have no idea"

Verbatim: *"I don't know how different these work and why they behave
differently... if there's more draws, more late goals, that statistics, you can
find for yourself."*

**Recorded as answered-with-a-no, and the source is his own sentence quoted
directly above** rather than an inference about what he knows. He is not
withholding it; he said he does not have it and told us to find it. **This one is ours to find in the data and he said so.** It goes on the
work list, not on his.

### Q5 — team news before kickoff. Answer: yes, a few hours, and he flagged his own uncertainty

> *"When they announce the line-up, the price might move... that news usually
> hits a few hours before the game."*

His example: Messi missing from a Barcelona line-up moving the price when the
news lands.

**⚠ He marked this as a guess himself** — *"I'm just giving you what I'm assuming
would happen. That's all stuff you can check better than me."* **So it is a
hypothesis to verify against the tape, not a fact he supplied**, and it is
recorded that way.

**Concrete and measurable this season:** point the full-depth recorder at the
hours before kickoff on European matches and check whether a step in price lines
up with line-up publication.

### Q6 — anything the markets get wrong. Answer: player statistics and team totals

> *"A lot of people bet on actual player statistics — a player to score a goal,
> to shoot three times... Some people bet on a team to score more than one goal,
> less than one goal. All that can be calculated with statistics."*

His own worked rule, which is directly implementable:

> *"Arsenal has scored two goals in the last ten games, especially against teams
> below the top ten. Their next game against Nottingham Forest, twelfth place —
> it's more than likely they'll score more than two."*

**= recent scoring rate, conditioned on opponent quality.** That is `SF021`.

---

## What his answers rule out, and one thing to say back

**He gave a clean "I don't know" twice and hedged his own guesses without being
asked.** That is what makes the rest usable: an expert who marks their own
uncertainty is worth more than one who does not.

**And the uncomfortable one, said once.** He said he knows *"literally close to
nothing"* about baseball, and the live desk trades baseball. Every other market
this project touches has a human who can look at a bet and say *"that is
obviously wrong"*. **Baseball has nobody who can do that** — not him, not this
chat. Not a reason to stop; a missing check that everything else has.
