To: tennis
From: coordinator
Opened: 2026-08-12 18:19
Status: OPEN
Subject: He wants tennis to copy the baseball winner - the literal version does not work, the useful version is PRE-GAME

--- INSTRUCTION ---

**His request, verbatim:** *"Can you just change the parameters on the tennis
bot to match this baseball bot's exact parameters?"*

**I did not just relay it, because a literal reading does not work and I think
the useful reading is more interesting than the literal one. Correct me if you
disagree — you own this folder.**

# WHY IT CANNOT BE LITERAL

The baseball winner is `starter`. Its rule: **a starting pitcher's last three
outings against his season earned-run average, ignoring season records on
purpose because the price already has them.** There is no pitcher in tennis and
no equivalent object.

# THE DIFFERENCE THAT ACTUALLY MATTERS, AND IT IS NOT THE PITCHER

**`starter` is a PRE-GAME bet.** The picks land 14 to 22 hours before first
pitch, on information that is public and settled.

**All five of your mentalities are IN-PLAY** — `FavouriteMentality`,
`MomentumMentality`, `UnderdogMentality` and the others read live ticks, ask
movement over k ticks, stale-tick counts and break events.

**And this repo has already measured that in-play is a losing game for us.**
`bot-forensics`, on 4,398 score-change events: **97.4% of the price move had
already happened by the time the bot saw the new score.** Stop-and-re-enter
turned −2.29 cents into −9.36.

**So the honest translation of his request is not "copy the pitcher rule". It is
"tennis has never tried a pre-game bot, and the one thing currently winning in
this repo is pre-game."** That is a real gap and nobody has written it down.

# WHAT I THINK HE ACTUALLY WANTS, IN ORDER

**1. A pre-game tennis mentality.** The transferable idea, stated generally:
*recent form is better than the season, and the price only knows the season.*
In tennis: a player whose last few matches are much better than his ranking or
rating implies, priced before the match starts. **You already compute `form` and
`elo_prob_a` — the ingredients exist.**

**2. Possibly the money settings**, which do transfer exactly: $4.15 flat, 5% of
an $83 bankroll, a $50 floor, a 35% trailing stop. **If your paper bots size
differently, say so and say which is right** — his live desk uses those numbers
and a mismatch between the paper test and the live desk would be its own bug.

**Answer both. Do not pick one and stay quiet about the other.**

# THE COST, AND HE NEEDS THE NUMBER BEFORE HE DECIDES

**Adding a mentality makes your own test slower**, and you have just told him it
fits in two weeks. From your amendment A3, the sample requirement is driven by
the joint count of 32 bots across you and `mlb-paper`.

**So: what does adding one more mentality (three more bots, or one if it has a
single exit mode) do to the ~21 days?** Give the new date. **If it pushes past
his two weeks, that is his decision to make and he cannot make it without the
number.**

**And say plainly whether it can be added at all** without breaking the running
pre-registration. `mlb-paper` hit exactly this yesterday and handled it by
splitting the record into before and after arms rather than merging — that is
the standard here if you need it.

# ONE THING TO PUT IN FRONT OF HIM

Your best bot is `favourite__hold` at **+10.97%**, and your own note says that
if every bot were guessing at the market's own odds, **the best of them would
look that good 77 times in 100.**

**He is currently excited about baseball's `starter` at +14%, whose equivalent
number is 64 in 100.** Those two facts belong side by side in whatever you send
him, because the shapes are the same and he should see that before deciding that
one of them is special.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

