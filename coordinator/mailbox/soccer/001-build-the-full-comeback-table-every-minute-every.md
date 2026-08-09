To: soccer
From: coordinator
Opened: 2026-08-08 20:32
Status: OPEN
Subject: Build the full comeback table: every minute, every score, every Kalshi competition

--- INSTRUCTION ---

You are a NEW chat. Your folder is `soccer/`, which already exists with data
scripts from a session on 2026-08-02. Read `soccer/WHAT_IS_LEFT.md` and
`soccer/dataset.md` before anything else. Create `soccer/README.md`,
`soccer/HANDOFF.md` and `soccer/DECISIONS.md` this session -- none exist.

# THE QUESTION

Late in a match, one team is ahead. You buy NO on the losing team, which pays
if the leading team wins OR it ends level. On Kalshi that is around 97 cents to
make 3 cents. The whole bet reduces to one number:

  **How often does the losing team actually come back and win?**

Fewer than 3 times in 100 and the bet makes money. More than 3 and it loses.

# WHAT THE USER ASKED FOR, AND IT IS A LOOKUP TABLE, NOT A SEARCH

He wants the full picture first, before any strategy: **every minute, every
scoreline, every Kalshi-bettable competition.** Out of 100 games in that exact
state, how often does the losing side come back and win -- and what does Kalshi
charge for it at that moment.

**Build this as a DESCRIPTIVE TABLE for a human to read. It is explicitly NOT a
hunt for the best-looking cell.** If you slice minute x scoreline x league you
will produce thousands of cells and the best of them will look excellent purely
by chance. That is not a hypothetical: `LEDGER.md` B023 ran 2,008 pre-registered
cells in this repo and found LESS than its own shuffled-data null. Do not
report a winner. Report the table.

The user will read it and choose where to go deep using football knowledge you
do not have. **That choice is his and it is the point of the exercise.** Only
then does a real test get pre-registered on data you have held back.

# WHAT HE TOLD ME, IN HIS OWN WORDS, THAT CHANGES THE DESIGN

**Team strength matters as much as the scoreline.** His example: if the 1st
place team is 1-0 down to the 20th place team in the 80th minute, he would not
bet against the 1st place team. A blanket comeback rate hides that completely.
So **team strength has to be a dimension of the table from the start**, not an
afterthought -- league position, or the pre-match price, or both.

**He expects the overall number to show no edge, and he is probably right.** He
said so himself. His argument is that the general rate averages away the
pockets, and the pockets are the point. Treat a flat overall result as the
expected outcome, not a failure, and make sure the table is fine-grained enough
that a pocket could still be visible.

**His starting parameter, if you need one to sanity-check the machinery:**
1-0 up in the 80th minute, buy NO against the losing team.

# A MEASURED TRAP IN YOUR OWN FOLDER

`soccer/reports/inplay_analysis.txt`: the displayed match minute differs from
real wallclock time by about **17.5 minutes at the median**, on 362 events, and
by more than 5 minutes in 55% of cases. **A minute-based join is wrong by a
quarter of an hour.** ESPN's `wallclock` field removes it and the existing study
used it. Any table you build keyed on the displayed minute is fiction.

# THE DATA PROBLEM, WHICH IS YOUR FIRST JOB

`soccer/reports/model_vs_market.txt` shows **24,172 completed matches with a
final score** across Mexico, Argentina, Brazil and USA. **Final scores alone
cannot answer this** -- you need the MINUTE each goal was scored to know who was
losing in the 80th.

ESPN publishes goal times and `soccer/src/` already fetches them, but it has
only been run on 127 fixtures. `WHAT_IS_LEFT.md` says roughly ten years per
league is reachable. **Getting goal times for a few thousand matches is the
gate on everything else.** Do that first, report how many you actually got, and
say plainly which competitions you could NOT get.

# WHAT IS ACTUALLY BETTABLE ON KALSHI -- CHECK, DO NOT ASSUME

Two documents in this repo disagree. `soccer/dataset.md` says Liga MX,
Argentina, Copa do Brasil, Colombia and MLS. `soccer/reports/tape_soccer_scan.json`
shows a different set: mostly **international friendlies** (139 of 210 tickers),
plus Uruguay, USL, Ecuador, Peru, NWSL, Chile, MLS, Colombia and Liga MX.

**Neither mentions the Premier League or the Champions League.** The `devig`
chat has been asked for the definitive list and the liquidity. Do not wait for
it -- build the machinery league-agnostic so any competition can be dropped in.

**If it turns out most of the book is international friendlies, say so loudly.**
A friendly is a different sport for this purpose: teams make six substitutions,
league position means nothing, and nobody is trying. That would not kill the
idea -- it might be where a market is most mispriced -- but it changes every
assumption about team strength.

# THE RULES THAT APPLY

`CLAUDE.md` is the contract; §6 is the evidence standard and §9b lists four
things not to re-open. In particular:

- **The unit of observation is the match.** Not the minute, not the market.
- **Hold back data you do not look at.** Split by time, not at random.
- **Report the naive benchmark** next to anything you find.
- **Paper only. No money, no keys, no order-placing code.** Copy
  `mlb-paper/tests/test_paper_only.py` into your folder before your first
  feature.
- **Pre-register anything that becomes a real test** as
  `soccer/PREREGISTRATION_COMEBACK.md`, committed before the first result
  exists, and it must say what result would make you drop the idea.

# HOW TO REPORT BACK

He is not an engineer and reads on a phone. **No statistics words at all** --
no "pp", no "confidence interval", no "n=". Say it in money, or say it out of
100. "Out of 100 games where a team was 1-0 down at 80 minutes, they came back
and won 4 times" is the right register. Every number gets bigger-is-better or
bigger-is-worse attached. `CLAUDE.md` §1 has the banned word list.

Write your section of `BRIEF.md` with
`py -3 coordinator\brief.py write soccer --file <a file>`, update `STATUS.md`,
write `HANDOFF.md`, and push.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

