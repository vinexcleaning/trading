# Questions only he can answer — European soccer

**Batched, never one at a time** (`CLAUDE.md` §2). **Nothing waits on these.**
The recorder is running, the specs are written, and the screening engine is
being built regardless. These change what the *next* soccer specs look like, not
whether work happens.

**Why these and not "what do you think about soccer":** `coordinator` mailbox
003 carries his own answer to what he knows — *"I know the most about soccer. I
know how it works, I know where the best players are, I know the best teams. Not
the crazy specific stuff, but everything Europe related, I know."* A general
question wastes that. A specific one turns it into a variable that can be
recorded and tested.

**Each question below is written so that his answer becomes a column in the
tape.** If he cannot answer one, that is a real answer too and it gets written
down as "he does not know this either", not left blank.

---

## The six

**1. Rotation before a European tie.** A club plays a league match three or four
days before a Champions League tie that matters to them. Do they hold players
back — and if so, is it the *big* clubs who do it, or the ones scraping through?
**Which is it, and how many days before does it start?**

*Why it matters:* it would mean a top-third side is sometimes not fielding a
top-third team, and SF018 reads team strength off the league table. If rotation
is real and predictable, the strength variable is wrong on exactly the matches
this trades.

**2. A team that is already through, or already out.** Group stage, final round,
nothing left to play for. **Does that change how they play — and does it change
it more for the team that is through, or the team that is out?**

*Why it matters:* it is the clearest case where the football stops predicting
the result, and it happens on a known date every year.

**3. Going one goal up early — does a big club see it out differently?** SF018
buys a side that leads between the 20th and 35th minute. **Is "sees the game
out" a real thing that separates clubs, or does everyone defend a one-goal lead
the same way and it is just that better teams have better players?**

*Why it matters:* those are different mechanisms and they predict different
things. If it is game management, the effect should be bigger for the same
squad quality in a knockout tie than in a league match.

**4. Which competitions behave differently, and how.** He said Europe. **Inside
that — is there a league where the favourite means something different from what
it means in the Premier League?** More draws, more late goals, weaker away
sides, anything.

*Why it matters:* the whole method is general first, then specific. This is the
list of slices worth cutting, from someone who knows rather than from a
computer trying every combination.

**5. What time of day, and what news.** **Is there a moment before a European
match when the price should move for a reason that is not the game — team news,
a line-up announcement, a press conference?** How long before kickoff?

*Why it matters:* the recorder can be pointed at that window specifically, and
if there is nothing there, that is worth knowing before building a strategy
around it.

**6. One he might say no to, and no is useful.** **Is there anything about
European soccer that you think the betting markets get wrong, that you have
never seen anyone else mention?** Even if it sounds silly.

*Why it matters:* three of the four idea sources are code reading other code.
This is the only one that can produce something not already in the training data
or the repo.

---

## And one thing to say back to him, once

He was straight about baseball — **"literally close to nothing"**. That is worth
saying back plainly, because of where the money is:

> **The live desk trades baseball.** Every other market this project touches has
> a safety net where he can look at a bet and say *"that is obviously wrong"*.
> **Baseball does not have that, and nobody else on the project does either.**

Not an argument to stop. It is a missing check that everything else has, and he
should know it exists as a gap rather than find out through a loss.
