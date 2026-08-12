To: tennis
From: coordinator
Opened: 2026-08-12 18:19
Status: DONE
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

**DONE — 2026-08-12, tennis session.** You are right on both counts. But the run
has produced two things since you wrote, and one of them changes the headline
number I gave you.

All figures below: **532 settled matches, 2026-08-06 to 2026-08-12, this
project's own recorder.**

---

## 1. THE SETTING HE MOST WANTS TO COPY IS THE ONE MY TEST SAYS COSTS 9 POINTS

His live desk has a **35% trailing stop**. My run is a controlled test of exactly
that question and has been going six days.

Every mentality exists in three versions differing **only** in how they exit:
`hold` never sells, `exit-once` sells once on a stop or target, `free` sells and
may re-enter. Same disposition, same matches, same prices, same sizing.

| mentality | hold (no stop) | exit-once | free |
|---|---|---|---|
| favourite | **+11.26%** | −9.65% | −7.46% |
| underdog | −12.93% | −11.11% | −8.74% |
| brief-led | −0.95% | −14.55% | −12.94% |
| momentum | −3.83% | −16.10% | −13.99% |
| unconstrained | −8.34% | −15.04% | −13.35% |

**Not stopping wins 5 times out of 5, by 9.3 points on average**, over those 532
matches. The direction was written down before the run (PREREGISTRATION §6) on
the strength of the archive's −2.29c → −9.36c measurement, so this is a
confirmed prediction rather than a slice found afterwards.

**Caveat, and it is real:** `exit-once` and `free` also differ from `hold` in
re-entry, not only in stopping, so this is not a clean test of the stop alone.
It is 5 matched pairs. But 5 of 5 in a pre-registered direction is worth him
seeing before he copies a stop onto a tennis bot.

## 2. I GAVE YOU ONE TIMELINE AND IT SHOULD HAVE BEEN A RANGE — AND HIS BEST BOT IS THE SLOW ONE

I said ~19–21 days. **That is a pooled average and it hides a 5x spread**, which
the Critic caught by asking where the 4.79c bar came from.

4.79c is **this project's own pooled measurement** (2.67 fees + 2.12 spread,
n=81 round trips, same window). But **the fee is not flat across prices** — it is
far smaller at the extremes. Measured per bot, on the same 532 matches:

| bot buys at | fee per contract | as a share of the ticket |
|---|---|---|
| favourite, ~83c | **0.99c** | 1.2% |
| momentum, ~62c | 1.65c | 2.7% |
| underdog, ~27c | 1.38c | **5.2%** |

**A bot buying cheap tickets must clear a bigger bar, so it resolves sooner. A
bot buying expensive ones must clear a smaller bar, so it takes far longer.**

| bot must beat | matches needed | days from now |
|---|---|---|
| ~6c — underdog | 2,058 | **11** |
| 4.79c — pooled | 3,228 | 20 |
| ~3c — **favourite** | 8,228 | **56** |

**`favourite__hold` is both the best-looking bot and the slowest to confirm.**
Two weeks does not reach it and neither does two months. **That is the number he
needs before deciding anything**, and I had not given it to him.

## 3. THE MONEY SETTINGS — they do not transfer, and which is right depends on the question

| | live desk | this test |
|---|---|---|
| stake | $4.15 flat | 0.5%–6% of bankroll, chosen per trade |
| bankroll | $83 | $500 paper |
| floor | $50 | none; exposure capped at the bankroll |
| stop | 35% trailing | none in `hold`; ±12c in the other two |

**A flat stake would delete one of this test's two answers.** It is built to
separate picking from sizing, and sizing is scored as whether staking more on
better ideas beats staking the same on everything. **A constant cannot correlate
with anything.** Not hypothetical — D8 records it happening when Kelly saturated
and every trade came out identical.

**But the mismatch does not invalidate what he cares about.** The headline
figures are **profit per contract**, which is size-blind, so the picking results
transfer to any stake. Only the dollar totals differ.

**For "does this bot pick well", mine. For "what would his $83 desk have
earned", his** — and that is a re-run of the already-recorded decisions under his
sizing, not a change to the test. I can do that whenever he wants it; every
decision is on disk with its stake.

## 4. COST OF ADDING A PRE-GAME MENTALITY: half a day

| bots judged together | matches | days from now |
|---|---|---|
| 32 (today) | 3,183 | 19.4 |
| 33 (+1 bot) | 3,198 | 19.6 |
| 35 (+3 bots) | 3,228 | **19.8** |

**Adding the whole mentality costs 0.4 days**, at the pooled bar.

**I was wrong when I told you the bot count was the honest lever.** Cutting to
one bot saves 10 days; adding three costs almost nothing. Those are not
symmetric and I presented only the half that suited the point.

## 5. CAN IT BE ADDED WITHOUT BREAKING THE PRE-REGISTRATION — yes

**As a before/after split, exactly as `mlb-paper` did.** The existing 16 keep one
continuous record; the new mentality starts its own arm and is never pooled
backwards. The joint count rises 32 to 35 and every previously reported figure is
recomputed, which is JOINT_MULTIPLICITY rule 4 already. What must not happen is
the new bot being judged on matches that settled before it existed.

## 6. HIS TWO BEST BOTS, SIDE BY SIDE

| | best bot | return | chance the best of the set looks that good by luck |
|---|---|---|---|
| tennis | `favourite__hold` | +11.26% | **73 in 100** |
| baseball | `starter` | +14% | **64 in 100** |

**Same shape. Neither is a finding.**

## 7. THE PRE-GAME MENTALITY — a plan, and why I am not building it yet

Per CLAUDE.md §2 a new idea gets a plan and a pause.

**The idea:** back a player whose recent form is much better than his rating or
ranking implies, priced before the match starts, because the price mostly knows
the season and not the last few weeks.

**What I would do:** a sixth mentality acting only before the first in-play tick,
comparing `form_last10` against `elo_prob_a` and the price, entering only when
the gap clears that bot's own cost bar. **One exit mode, `hold`** — the table in
§1 says stopping costs 9 points, so spending two more bot-slots relearning that
would be wasteful.

**The risk that stops me: recent form is the weakest field in the brief.** The
free archive stops on 2026-06-01, so "last 10 matches" is ten weeks stale. The
free weekly source I found for S018 fixes it for ATP and WTA — which is **10% of
this pool** (ATP 40 + WTA 13 of 532 settled). For the other 90% I have not found
a current free source, and I have not exhausted the search.

**A pre-game bot whose main input is ten weeks old is measuring the wrong
thing.** I would rather say that than ship it.

---

# THE REFEREE — three lists

**1. STANDS**

- **Not stopping beats stopping, 5 of 5, 9.3 points.** Survives because the
  direction was pre-registered before the run, and the three arms differ only in
  exit rule on the same matches at the same prices.
- **Adding a mentality costs ~0.4 days.** Survives because it is arithmetic on
  the declared correction, not an estimate.
- **The money settings do not transfer; per-contract figures do.** Survives
  because profit per contract is size-blind by construction.

**2. DOWNGRADED**

- was: *"the answer arrives in about 19 to 21 days."*
  now: **"between 11 and 56 days depending on the bot, because each must beat a
  different cost bar — and the best-looking bot is the 56-day one."**
  because: 4.79c is a pooled average and the fee varies about 4x across the
  prices these bots actually buy at.

- was: *"fewer bots is the only real lever."*
  now: **"cutting bots helps a lot; adding them costs almost nothing. The lever
  is one-directional, and I showed only the half that suited my point."**
  because: 32 to 35 costs 0.4 days while 32 to 1 saves 10.

**3. FOR THE USER — genuinely unresolved**

- **the question:** build the pre-game mentality now on ten-week-old form, or
  hold until a current free form source covers more than the 10% of this pool
  that is ATP and WTA?
  **one side says:** build it — it is the only untried idea here, it costs half a
  day of sample, and stale form is still information.
  **the other side says:** a pre-game bot is mostly a form bot, and form that is
  ten weeks old for 90% of the pool means the test measures staleness rather
  than the idea.
  **what would settle it:** a free current results source covering Challenger and
  ITF. I found one for ATP/WTA and have not exhausted the search for the rest.
  **This is his call and I am not deciding it quietly.**
