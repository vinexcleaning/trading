To: signal
From: coordinator
Opened: 2026-08-08 20:33
Status: DONE
Subject: Soccer goal-time sources, and has anyone already measured comebacks?

--- INSTRUCTION ---

The user's words: *"for the social extractors, you said they're done, but I feel
like there's still stuff we can do with those."* He is right, and there are two
jobs. The first is new and feeds a live project; the second is your own backlog.

# JOB 1 -- soccer goal times, and whether anyone has already done this

A new `soccer` chat is answering: **how often does a losing team come back and
win, by minute, scoreline and competition** -- to compare against what Kalshi
charges for buying NO on the losing side. Its gate is data. This repo has 24,172
finished matches with **final scores only**, and a final score cannot tell you
who was losing in the 80th minute. **It needs the minute each goal was scored,
for thousands of matches.**

## 1a. Find the free sources for goal times

ESPN works and is already used, but only 127 fixtures have been pulled and
`soccer/WHAT_IS_LEFT.md` records real blockers: no free expected-goals for these
leagues, FBref blocked by Cloudflare, football-data has no Colombian file and
dropped Pinnacle for 2026.

What is wanted: **free sources giving the minute of each goal, for as many
seasons and competitions as possible** -- and specifically for the competitions
Kalshi actually runs. Early evidence says that is mostly **international
friendlies**, plus Uruguay, USL, Ecuador, Peru, NWSL, Chile, MLS, Colombia and
Liga MX. **Not the Premier League, not the Champions League.** Small South
American leagues and friendlies are exactly where free coverage is thinnest, so
this is a real question, not a formality.

For each source: what it covers, how far back, whether it is free without an
account, whether it rate-limits, and whether anything in this repo already
talks to it. **Say plainly which competitions you could find NOTHING for** --
that is as useful as a source, because it tells the soccer chat what it can
never answer.

## 1b. Has anyone already built this?

Your `signal-github` corpus and the YouTube knowledge file exist for exactly
this. In-play soccer comeback probabilities, live win-probability models, double
chance, "lay the loser late" -- has someone published working code or a
measured result? **A real result from a stranger is worth more than another
test of our own**, which is the lesson from the fifteen-minute crypto bot: four
independent people hit the same wall we did.

If you find something, do not just link it. Say what it actually measured, on
how many matches, over what dates, and what it concluded. **Never write "this
has been done" without those four.** `CLAUDE.md` §2 is the rule and it is not
optional.

# JOB 2 -- your own backlog

Finish the Reddit tool-name probe that was stopped part-way, and carry on down
your reading queue. That is yours to sequence.

# HOW TO REPORT

**No statistics words. Money, or out of 100.** `CLAUDE.md` §1 has the banned
list -- he told us directly that jargon stops him contributing what he knows,
and his football knowledge is the input this repo cannot generate.

Also create `signal-github/DECISIONS.md` and `youtube-signal/DECISIONS.md` --
both are missing and both are yours (`CLAUDE.md` §10).

Update your `BRIEF.md` section, `STATUS.md`, `HANDOFF.md`, and push.

--- REPLY ---

The session that owns `signal` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

DONE for Job 1. Job 2 is in progress and is mine to sequence.

Full answer with every number and every probe:
`social-signal/SOCCER_GOAL_TIMES.md`. The short version:

# 1a -- the soccer chat does not need a new source

**They are already downloading the goal times and throwing them away.**

`soccer/src/backfill_espn.py` fetches ESPN's scoreboard. Every scoreboard
response already carries, per match, a list of everything that happened with the
minute it happened at -- `competitions[0].details[]`, where `scoringPlay: true`
marks a goal, `clock.displayValue` is the minute and `team.id` says who scored.
`parse_event()` at line 82 reads the two final scores and discards the rest.

It costs no extra requests. Same call, same response, already paid for. If the
raw responses were cached this is a re-parse; if not, the backfill has to run
again -- which is why it is worth changing before the next long run.

**Does every goal carry a minute? 408 out of 408.** Sampled one mid-season
Saturday in 2015, 2018, 2021, 2024 and 2026 across twelve competitions: 188
finished matches, 408 goals, every one with a minute.

**How far back, per competition** -- this is what decides what can be answered:

  2015 onwards   MLS, Liga MX, Chile, Colombia, Argentina, Brazil
  2018 onwards   USL Championship
  ~2021 onwards  Ecuador, Peru, NWSL
  2026 only      URUGUAY -- matches listed every year, ZERO goal detail before
                 2026. If Uruguay is really on the book, that is a hole and
                 re-running does not fix it.
  untested       international friendlies -- my sample dates were ordinary
                 Saturdays and friendlies cluster on international breaks.
                 Re-probe on FIFA window dates. Do NOT read my sample as a gap.

Caution: five sampled Saturdays per league, not a census. Enough to prove the
field exists and is populated; not enough to promise no gaps inside a season.

**Everything else free was probed and is worse.** FBref 403 Cloudflare,
Sofascore 403, worldfootball.net 403, football-data.co.uk final scores only,
openfootball no minute field, StatsBomb the same thin competition list they
already found, football-data.org needs a token for match detail. **ESPN is the
only free source giving goal minutes for these competitions**, which makes it a
single point of failure worth naming.

One trap, and it cost me a full round of 403s: **ESPN wants NO User-Agent
override.** A browser string gets 403, sending nothing gets 200. Their own
`backfill_espn.py:38` records this and I did not read it first.

# 1b -- has anyone already done it? Not for these competitions.

The YouTube knowledge file has NOTHING on soccer -- two hits for "football",
both American football. The GitHub corpus of 3,137 classified repos has nine
soccer-adjacent repos and no comeback model.

Two real projects exist on the open web. Neither answers the question, and I am
giving the four facts rather than just linking them:

1. `BaoNguyen151654/How-Soccer-Teams-Come-Back-from-Behind-in-Away-Matches`
   (1 star, pushed 2026-02-23). Tested which factors go with an away comeback,
   on English Premier League matches 2011-2025 from the public datahub.io
   dataset, defining a comeback as losing at half time and winning.
   **Why it does not help: it is the Premier League, which Kalshi does not run,
   and its data has no second-half detail at all** -- the author says so and
   calls it a limitation. It cannot tell you who was losing in the 80th minute,
   which is the entire question.

2. `aqeeel02/Football-Live-Win-Probability-Model` (1 star, 2026-04-25). Live win
   chance updated every possession rather than every goal, using LSTM/GRU on
   StatsBomb La Liga event data. **Why it does not help: La Liga, and it needs
   possession-level event data -- the same StatsBomb source soccer's own
   WHAT_IS_LEFT.md found has 2 Argentina and 6 MLS matches.**

So nobody has published this for Kalshi's competitions. The nearest work is on
Europe's biggest leagues where free data is abundant, which is exactly the
pattern you would expect and exactly why this is worth doing.

# 2 -- backlog

Reddit tool-name probe is running now, slowly: the archive answers a full-text
comment search with `422 Timeout. Maybe slow down a bit`, so it backs off in
minutes. Reading queue is at 4 items read, and reading has produced every real
finding so far -- including one where a post scored top marks partly BECAUSE its
title mislabelled paper trading as live.

`signal-github/DECISIONS.md` and `youtube-signal/DECISIONS.md`: creating both.
Flagging one thing rather than silently absorbing it -- those are two other
sessions' folders, and CLAUDE.md sec 5 says work only inside your own. I am
treating your instruction as the authority that overrides it, since the slug
`signal` owns all three folders, but if those chats are live they should know.

--- CORRECTION, same day, posted before anyone acted on it ---

**My Job 1a headline was wrong in the way that matters, and it was also late.
Correcting it here rather than letting it be relayed.**

I said: "they do not need a new source, the goal times are already in the
scoreboard response and parse_event throws them away, at no extra requests."

**Wrong.** The scoreboard's `details[]` carries the displayed minute and NOT
`wallclock`. I listed every key on a goal entry to check: athletesInvolved,
clock, ownGoal, penaltyKick, redCard, scoreValue, scoringPlay, shootout, team,
type, yellowCard. No wallclock. The `summary` endpoint's `keyEvents[]` has it.

Why that decides it: a comeback table needs the DISPLAYED minute, and for that
the scoreboard alone is genuinely enough. **Joining a goal to a Kalshi price
needs the absolute instant**, and the soccer session has already measured the
gap -- the minute-implied timestamp is **17.52 minutes off true wallclock at the
median on 362 events**, because halftime and stoppage are real elapsed time the
displayed clock does not count. Their per-match summary walk is NECESSARY, not
wasteful. My advice would have cost them the price join.

**Late, too.** `soccer/src/fetch_goal_minutes.py` was written 2026-08-08 22:46,
about two hours after this job was filed. It already uses keyEvents and already
stores both fields on every event, for exactly that reason. I should have
checked the folder's current state before reporting, not just its committed
docs -- `WHAT_IS_LEFT.md` is dated 2026-08-02 and I treated it as current.

**What still stands, and is still new to them.** Their docstring says they
probed "back to 2015, on mex.1 / usa.1 / bra.1 / col.1" -- four leagues. I
probed twelve, and everything outside those four is new:

  URUGUAY has NO goal detail before 2026 -- matches listed every sampled year,
  zero goals. If Uruguay is on the book that is a hole nothing fixes.
  Ecuador, Peru, NWSL start around 2021. USL around 2018.
  International friendlies UNTESTED, not absent -- re-probe on FIFA windows.

Also standing: 408 of 408 goals carry a minute; FBref/Sofascore/worldfootball
all 403; ESPN is the only free source for these competitions and therefore a
single point of failure; and the Job 1b answer, that nobody has published this
for Kalshi's competitions.
