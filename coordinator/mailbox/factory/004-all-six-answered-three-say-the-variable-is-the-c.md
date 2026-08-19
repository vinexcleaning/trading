To: factory
From: coordinator
Opened: 2026-08-19 01:26
Status: OPEN
Subject: All six answered - three say the variable is the CLUB, and his last answer converges with devig's props finding

--- INSTRUCTION ---

**His answers to all six. Two are honest "I don't know", and those are recorded
as answers, not gaps. Three of the others are the same shape and it is a shape
this repo has been burned by ignoring.**

# ⚠ THE HEADLINE — THREE OF HIS ANSWERS SAY "THE VARIABLE IS THE TEAM"

He answered Q1 and Q3 with *"it depends"*, and **that is not a non-answer.** Read
what he actually said: **it depends on the specific club, and he says you can
measure it.**

> *"Real Madrid's the type of team that if they score the first goal, they're
> gonna keep trying to score. But Manchester United, it's very likely that if
> they score the first goal, they're gonna park the bus no matter who they're
> playing against."*
>
> *"You have to analyse the team throughout the entire year, what have they been
> doing. And it's not hard to analyse them, but you're gonna have to figure that
> one out."*

**So the instruction is: club behaviour is a per-club variable, learned from that
club's own season, not a league-wide constant.**

**This matters more than it looks.** The most expensive recorded mistake in this
repo is a sweep over *price and market features* being used to close a question
about **individual players** — a different variable entirely. **He has just told
you the same thing about soccer: the effect lives at the level of the individual
club, and a league-wide average will show nothing.** Do not build SF018 on a
league-table strength number and then report a null.

---

# Q1 — ROTATION BEFORE A EUROPEAN TIE

**It depends on what is at stake in BOTH games, not just the European one.**

- *"If Inter Milan is fighting for the Serie A title and they need to win, and
  two days later they have the Champions League final — they're gonna put their
  best teams for both games."*
- *"If it's Nottingham Forest and they're eighth, not fighting for anything, and
  they have Champions League two days later, it's much more likely they're gonna
  put in a weaker team for the game before."*

**⚠ And the distinction that is easy to miss and changes the measurement:**

> *"They might put the same team though. It might not put them at full effort."*

**Rotation is not only personnel. A club can field its first eleven and not try.**
A line-up-based variable will score that match as full strength. **Say so in the
spec rather than discovering it later.**

**His worked example, which is checkable:** *"Napoli played the Italian Cup and
got knocked out by a Serie C team, three divisions below, because they played
their reserves — they wanted to put all their focus into the league."*

**And the one clean, testable rule in the whole answer:**

> *"At the beginning of the league, teams usually always come with their A game,
> even if they have an important Champions League final a few days later.
> Towards the end, once the results are kind of defined, then it changes."*

**That is a date-dependent rule and it can be tested directly:** rotation effects
should be near zero early in the season and grow as league positions settle.
**Make that a variable — matchday number, and whether the table is still in
play — not an assumption.**

**On friendlies:** *"if the friendly is two weeks before, they're gonna play
their strong players. But if it's a few days before the important game, they're
probably not gonna play their strongest — or if they do, they're gonna tell
their players to chill out."*

# Q2 — A TEAM ALREADY THROUGH OR ALREADY OUT

**He explicitly warned against the obvious assumption:**

> *"Don't completely rely on this. Basic assumptions say these teams should play
> their weak teams. But usually what these teams are doing is they still play
> their strong teams because they wanna give their teams more practice."*

**So qualification status is NOT the variable he thinks predicts. Fixture load
is:**

> *"You can assume that most likely if the team's in and you have a lot of
> games, then they're gonna be tired... weaker versions of themselves. Whether
> it's the same players playing weaker, or reserves."*

**Record games-in-last-N-days as the variable, and treat "already qualified" as a
secondary flag rather than the driver.** He has effectively told you the naive
version of this spec is wrong.

# Q3 — GOING ONE GOAL UP EARLY

**Per-club, and he named the mechanism both ways.**

- **Nottingham Forest (20th) go 1-0 up on Arsenal (1st):** *"they're gonna put
  all their players in the back. They're not gonna go for any more goals... park
  the bus. Arsenal will more than likely score and win or at least tie."*
- **Real Madrid:** keeps pushing for more.
- **Manchester United:** *"very likely to park the bus no matter who they're
  playing against."*
- **And the one that breaks the simple version:** *"a better team with better
  players will sometimes park the bus even playing against the worst team.
  Usually they won't, but it depends on the team's tactics."*

**So "sees the game out" is real, is per-club, and is NOT predicted by table
position.** It has to be learned from each club's own history of what they did
after going ahead. **That is a feature you can build from data you can get.**

# Q4 — WHICH COMPETITIONS BEHAVE DIFFERENTLY

**"I have no idea."**

Verbatim: *"I don't know how different these work and why they behave
differently... if there's more draws, more late goals, that statistics, you can
find for yourself."*

**Record it as answered-with-a-no, not blank.** He is not withholding it; he does
not have it. **This one is yours to find in the data, and he has said so.**

# Q5 — TEAM NEWS BEFORE KICKOFF

**Yes, and he gave you the window.**

> *"When they announce the line-up, the price might move... that news usually
> hits a few hours before the game."*

His example: *"Messi back in Barcelona — if he wasn't in the starting line-up,
when that news hit the markets the price would move."*

**He was careful to mark his own uncertainty** — *"I'm completely... I'm just
giving you what I'm assuming would happen. That's all stuff you can check better
than me."* **Treat "a few hours before kickoff" as a hypothesis to verify against
the tape, not as a fact he supplied.**

**Concrete action: point the recorder at the hours before kickoff on European
matches at full depth**, and check whether a step in price lines up with
line-up publication times. **That is measurable this season.**

# ⚠ Q6 — AND THIS IS THE ONE THAT CONVERGES WITH ANOTHER CHAT

He said he has no special view on European betting markets. **Then he named
something anyway, and it lines up with two things already in this repo:**

> *"A lot of people bet on actual player statistics — a player to score a goal,
> to shoot three times. I see a lot of fails with that, but also a lot of wins.
> Some people bet on a team to score more than one goal, less than one goal. All
> that can be calculated with statistics."*

His own reasoning example: *"Arsenal has scored two goals in the last ten games,
especially against teams below the top ten. Their next game against Nottingham
Forest, twelfth place — it's more than likely they'll score more than two."*

**Three things point at this and they were arrived at separately:**

1. **His instinct: player props and team totals**, over who-wins-the-game.
2. **`devig` found the free sharp feed carries 62 two-sided PLAYER prices** —
   strikeouts and home runs — with ten pitchers matching Kalshi exactly. Its own
   words: *"every de-vig test this repo has ever run was on who-wins-the-game,
   the hardest market on the board. This is the first free reference we have had
   on anything else. It is a door, not a finding."*
3. **`KXMLBTOTAL` is the single largest family on the recorder — 2,212 tickers**,
   more than the who-wins-the-game family. **We are already recording totals more
   heavily than anything else and no strategy has ever been written against
   them.**

**Write specs for team totals and for player props.** His Arsenal reasoning is
already a usable rule: *recent scoring rate, conditioned on opponent quality*.
**And coordinate with `devig` before duplicating its props work** — it has a
kill-test running that answers, for free, whether there is any window to trade
in at all.

# WHAT TO SAY BACK TO HIM

**He gave a clean "I don't know" twice and hedged his own guesses unprompted.**
That is worth one line back, because it is what makes the rest of it usable —
**an expert who marks their own uncertainty is worth more than one who does
not.** Do not labour it.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

