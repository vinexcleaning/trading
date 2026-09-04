# Pre-registration — four new entry strategies for the freed slots

**Written 2026-09-03, BEFORE any of these takes a slot or places a bet.**
Mailbox 028. Registered under `CLAUDE.md` §10.

## ⚠ FOUR, NOT TEN, AND THAT IS THE HONEST YIELD

028 offers ten slots. **I screened eleven candidates, five earned a slot, and one of those five died in the dry run. Four shipped.** I am
not filling the other five, because 028's own warning is the binding one: ten
variations on one idea would re-create exactly the duplicate problem that freed
the slots. **An empty slot costs nothing extra; a fake strategy costs the
denominator and lies about breadth.**

## ⚠ THE SCREEN IS NOT EVIDENCE, AND ITS NUMBERS ARE NOT PREDICTIONS

All eleven were measured on **the same 664–863 archive games**. The best of
eleven on one sample looks good whether or not anything works. **The screen
decided only which ideas earn a slot.** Everything below is judged forward.

## The five, and why each is a different instrument

| # | name | what it backs | why it is not a copy |
|---|---|---|---|
| M6 | `rested` | the better-rested side | **fatigue** — no current strategy reads the schedule at all |
| M7 | `travel` | against a side that has just flown 1,200+ miles | fatigue, and it fires on a different set of games from M6 |
| M8 | `consensus` | `starter`'s pick, only when another strategy is also in that game | converts an **observed** pattern into a forward test |
| M9 | `conviction` | `starter`'s pick, only at ≥3c of edge | a paired refinement, ~4x cheaper to judge |
| M10 | `underdog` | `starter`'s pick, only below 50c | a paired refinement on the other axis |

**M8, M9 and M10 are deliberately paired with `starter`** — 028's point that a
strategy sharing most of its games with an existing one is about **4x cheaper**
to compare, because the game outcome cancels. Measured on our own data:
difference-spread **24.7c** against **49.6c** unpaired.

**M8 is the honest way to handle the consensus pattern.** It has been looked at
repeatedly and never traded. Making it a pre-registered forward bot is how a
looked-at pattern becomes evidence instead of a story.

## Unit of observation

**One game.** Always. A market settles once.

## ⚠ THE DENOMINATOR RISES, AND IT COSTS ANOTHER CHAT

`JOINT_MULTIPLICITY.md` fixes one denominator across this fleet and tennis's.
Adding five hold-only bots takes the repo from **16 + 16 = 32** to **21 + 16 =
37**. Per 028 rule 2 the denominator **rises and does not fall**, so every
previously reported number is recomputed against 37.

**This is not free and it is not only my cost — it raises the bar for the tennis
fleet too, and that chat did not ask for it.** Flagged rather than absorbed
silently. I did not retire the ten duplicate exit bots to make room, because
deleting bots mid-run destroys a running experiment.

## Sample, dates, holdout

Forward only, from the commit of this file. **The archive screen is in-sample
and is never quoted as a result for these five.**

## How many games before any of them can be judged

**60 settled games each**, and for the paired three the count that matters is
**games shared with `starter`**, not games entered.

## What result makes us DROP each of them — registered before looking

- **Under +2 per 100 after 60 games.** The five current strategies sit between
  −15 and +8; a new one that cannot clear +2 is not worth a slot.
- **Overlap above 0.8** with any existing strategy on the divergence check
  below. That would mean the label is decoration, which is the exact failure
  that freed these slots.
- **For M6/M7 specifically: failing to beat "always back the home team".** That
  naive rule returned **−5.5% on 664 archive games** and is the benchmark; a
  fatigue idea that cannot beat it is not an idea.

## The breadth test, published or the claim is unevidenced

Per 028: for each pair of strategies, the share of games both entered **on the
same side**. Tennis's median is **0.149**. **Under 0.5 means genuinely
different instruments; over 0.8 means the labels are decoration.**

**This number is published with the new fleet or the breadth claim does not
stand.** The current five would score near 1.0 against their own duplicates,
which is how this was found.

## What would make me doubt a positive result

M6 and M7 fire on few games (65 and 86 in the screen). **A strategy that fires
rarely reaches 60 games slowly and is easy to over-read early.** And rest and
travel are correlated with each other and with home advantage, so any effect
may be home-field wearing a new name — which is why "always back the home team"
is the registered benchmark rather than zero.

## What is NOT being tested

Umpires · lineup handedness · bullpen usage beyond the existing `bullpen` term ·
weather beyond `park-air` · the first-inning (`KXMLBRFI`) and run-total families
· **any new exit variant** — 028 is right that the exit question is answered
(tennis: holding beat selling in 5 of 5 mentalities; here: every one of 72
stop-loss cells worse than holding) and spending a slot on it again would be
waste.

## ⚠ AMENDED 2026-09-04, BEFORE ANY OF THEM RAN — `rested` is dropped

`rested` (M6) was pre-registered above and **never took a slot.** A dry run
against real briefs showed it declining every game, so I measured why rather
than letting it sit at zero.

**It needs a rest-day GAP of 2 or more between the two sides to clear the cost
bar. Over 2,125 games: gap 0 is 92 in 100, gap 1 is 8 in 100, and a gap of 2 or
more has NEVER OCCURRED.** Baseball teams play daily.

**So it could never fire — the exact `lineup` failure**, an untested hypothesis
wearing the costume of a null. **Caught in a dry run before it took a slot,
which is the only reason this amendment is honest rather than an excuse.**

**NOT fixed by raising `M6_C_PER_REST_DAY` until it fires.** That is choosing
the dial to get the answer, and it is precisely what I refused to do for
`lineup` two weeks ago. The code is kept as dead code with its evidence, because
deleting it is how the same idea gets re-proposed in a month.

**Consequence for the denominator: 20 bots, not 21.** The repo goes 16 + 16 = 32
to **20 + 16 = 36**, not 37.

**And the shipped four are: `travel`, `consensus`, `conviction`, `underdog`** —
one new instrument and three paired refinements of `starter`.
