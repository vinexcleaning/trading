# CLOSED.md — the comeback idea, and why it stops here

**Closed 2026-08-11.** The user agreed with the recommendation to stop.

This file exists so that a reader arriving cold gets the answer, the reason, and
**the list of what was never tested** — because a dead idea with no such list
looks completely dead, and this repo has already killed a live idea that way.

---

## The idea, and the answer

Late in a match one team is ahead. You bet against the team that is behind,
which pays if the leader wins or if it finishes level. On Kalshi that looked
like about 97 cents to make 3 — the price the idea assumed, and the one that
turned out not to exist late in a match — so the whole thing reduced to one
number: **how often does the losing team actually come back and win?**

**The football answer is solid.** On 56,927 matches across 26 competitions,
2015–2024: a team one goal down comes back and wins **9.8 times in 100 at half
time, 4.0 at the 70th minute, 2.3 at the 80th, 0.4 at the 89th.**

**The answer to the idea is no, and not because of the price.**

## Why it stops — the mechanism

**Kalshi stops quoting the losing side exactly when the match becomes
near-certain**, which is the state the idea wanted to buy. Measured with one
reading per match, so nothing is counted twice:

| minute | came back, where you COULD bet | where you COULD NOT |
|---|---|---|
| 60 | **7.1 per 100** | 0.0 |
| 70 | 5.7 | 0.0 |
| 80 | 4.0 | 0.4 |
| 85 | 2.6 | 0.0 |

The bet was *"pay about 97 cents for something almost certain."* **The market
does not quote almost-certain.** Every price that exists is a price on a match
still in doubt — where the team behind comes back about 7 times in 100, not the
1 or 2 the idea was aimed at.

**The trade is not mispriced. It is absent by construction.** That is a fact
about how market makers behave, not about which league, so a deeper book in
September would not have created it. `reports/selection_canary.txt`, SO041.

**This was predicted in writing before it was run** — the prediction is in the
header of `src/selection_canary.py` and in the git history, which is the only
place a prediction counts.

---

## ⚠ WHAT WAS NOT TESTED

**Required by `CLAUDE.md` §9c step 7.** These are untested, not disproved. If
this idea ever reopens, it reopens here.

1. **The reverse trade.** Backing a side to hold on or to come back — a cheap
   contract instead of a 97-cent one. **This is the live descendant** and it has
   its own section below.
2. **The Premier League and the Champions League group stage.** Qualifying was
   measured; the group stage was not. `KXEPLGAME` has 200 settled events but the
   most recent is 2026-05-24, so **zero** fall inside Kalshi's ~69-day candle
   window — nothing could be measured, and that is a venue limit.
3. **Team strength taken from domestic form.** Strength here is a rolling
   within-competition measure, so European qualifiers mostly have none — **120
   of 572** Champions League qualifying matches got a reading on both sides.
   Fixing it needs each club's domestic-league form, a new source per country.
4. **Whether the market over-reacts to a weak team's goal.** The sharpest
   version of the idea and **this window could not answer it**: requiring a
   price you could actually act on left **8 to 18 goals per strength group**.
5. **The two teams' identities.** The table has strength *tiers*, never clubs.
   "Atlético at home protecting a 1-0" is a different bet and was never asked.
6. **Whether a team has thrown away leads before.** The user named this
   explicitly. The data to build it is in `data/goal_minutes.jsonl`. Not built.
7. **Red cards as a dimension.** Collected on every match, used in nothing.
8. **Home versus away for the leading side.**
9. **Competition stage** — knockout, group or league. A knockout tie where a
   draw sends someone through is a different match and was scored as one.
10. **Formation, tactics, and anything said online.** Three of the user's own
    listed parameters, none attempted.
11. **The other two legs.** Only the trailing team's NO was priced; the draw leg
    and the leading team's YES move too.
12. **Uruguay and the half-covered competitions** — Ecuador, Peru, Copa do
    Brasil, NWSL. Uruguay lost **99.0%** of its ESPN timelines (measured
    2026-08-09: 30 usable of ~3,300) and Kalshi lists it.
13. **2025 and 2026.** Deliberately unopened. **They stay shut.**

### Why the held-out years stay shut

They were never looked at, and the pre-registered test never ran because its
premise failed first. **Opening them now to "just have a look" would spend the
only untouched data on a question already answered by mechanism.** If this
reopens, those unlooked-at years are what would make the reopening worth
anything.

---

## The one live descendant: the reverse trade

**What it is.** Not betting against the team that is behind, but backing a side
to hold on or to come back. A cheap contract rather than a 97-cent one.

**Why it is not killed by anything here.** The mechanism that killed the
original is *"nobody quotes a near-certainty."* The reverse trade buys the
**uncertain** side, which is precisely where quotes do exist — 93 in 100 at the
15th minute. It also has the opposite risk shape: **the loss is capped at what
you paid**, instead of many small wins and one loss that eats thirty.

**What is already known and does not need redoing.** A side that goes one goal
up between the 20th and 35th minute wins **72.6 times in 100 if it is a
top-third team (1,562 matches)** and **59.6 if it is bottom-third (944)**. That
half is solid.

**What would be needed to test it, and it is a real list:**

1. **Prices on the cheap side**, which `price_by_minute.jsonl` already stores —
   both sides' bid and ask at every minute. No new download for what is in the
   window.
2. **A deeper book than this window had.** The binding constraint is that
   requiring a tradeable price cut the sample to 8–18 goals per group. The
   Premier League and Champions League group stage would fix that, and only
   those.
3. **Strength from domestic form** (item 3 above), because the whole hypothesis
   is about strong sides being underpriced to hold on.
4. **A fresh pre-registration**, on the years nobody has looked at, stating
   what result would drop it. `PREREGISTRATION_COMEBACK.md` does **not** cover this — it is a different
   bet in the opposite direction and reusing it would be dishonest.
5. **The fee at the cheap end, which is where this bet lives and is much bigger
   than at 97 cents.** Computed from `common/kalshi_fees.py`, the repo's only
   fee implementation, on 2026-08-11: **1.74 cents at a price of 53, against
   0.20 cents at 97** — nearly nine times as much, on a contract with less to
   win per trade.

**Nothing here supports the reverse trade and nothing here rules it out.** That
is the honest position, and it is why this is a handover rather than a finding.

---

## What this work produced that outlives it

**The mechanism is not about soccer** and has been filed outside this folder:
`GUARDS.md` #24 and `LEDGER.md`. The short form:

> **The market does not quote near-certainties. Any strategy whose shape is
> "buy the thing that is 97% to happen, cheaply" fails on availability, not on
> price** — and measuring only where a quote exists silently conditions the
> sample on the event still being uncertain.

**Also reusable:** `src/clock_map.py` places any displayed match minute at a
real instant to a median of 8 seconds (leave-one-out on 24,159 anchors), and
`src/fixture_join.py` joins a venue's event to a data provider's fixture with
the second-side check that made it trustworthy — **57 of 57 settled results
agreed, 0 disagreed.**

---

## The corrections this session made to itself

Recorded because the count matters more than any single number, and because
this repo's directional prior is that **every correction shrinks an effect**:

- **"Four times in five there is no market"** → measured only on prices two
  minutes after a late goal; it is true of the last twenty minutes and was
  reported as though it were true of the whole match.
- **"1.7 comebacks per 100 at the 80th minute"** → a ten-year average; the
  modern number is **2.3**, which halves the margin against break-even.
- **"The price sample contains no European league"** → **false**, caught by the
  Critic before publication. Three separate defects were hiding 63 Champions
  League matches, each reporting "no fixture".
- **The over-reaction test** → its first version averaged quotes of 100 and 0 as
  though they were prices and produced a tidy, well-calibrated-looking table. An
  artifact.

**41 claims, SO001–SO041, in `LEDGER_SOCCER.md`.** The folder stays where it is.
A dormant folder is not a dead claim.
