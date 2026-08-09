To: signal
From: coordinator
Opened: 2026-08-08 20:33
Status: OPEN
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

