# mlb-paper

A **paper-only** forward test of five baseball mentalities on Kalshi's MLB
markets. Sixteen bots, one shared game pool, free entry, none forced.

**There is no money in this.** No credential is read, no key file is opened, no
order endpoint is imported. `tests/test_paper_only.py` walks every source file
and fails the build if order-shaped code appears — and it is itself run against
three deliberately planted violations, because a guard nobody has tested against
a real violation is a guard nobody knows still works.

## Read in this order

| file | what it answers |
|---|---|
| [MENTALITIES.md](MENTALITIES.md) | the five mentalities and the evidence behind each |
| [TARGET_CHOICE.md](TARGET_CHOICE.md) | do over/under and first-inning beat moneyline? (no) |
| [PREREGISTRATION.md](PREREGISTRATION.md) | the bar each bot must clear, written before any decision |
| [../JOINT_MULTIPLICITY.md](../JOINT_MULTIPLICITY.md) | one BH denominator of **32** across this test and the tennis one |
| [DECISIONS.md](DECISIONS.md) | every judgement call taken without asking |
| [HANDOFF.md](HANDOFF.md) | where it stands and what is running |
| [deploy/README.md](deploy/README.md) | click-by-click install on the laptop |

## Run it

```bash
cd mlb-paper && deploy\setup.bat
```

Then, to have Windows keep it alive across reboots, right-click
`deploy\install_task.ps1` and choose **Run with PowerShell**.

## Check it — this is the only command you need

```bash
mlb-paper\deploy\check.bat
```

First line is `ALIVE` or `*** STALE ***`. Everything else is detail.

## What it does each tick, in 300 seconds

Reads Kalshi's open MLB markets · fills the previous tick's intentions against
*this* tick's book (that ordering is the latency model) · marks every market
with the de-vigged Pinnacle price beside it, so closing-line value has a series
to close against · manages exits · builds pre-match briefs for games inside a
decision window · lets each mentality decide and writes its full reasoning to
disk **before the game starts** · settles anything final · heartbeats.

## The layout

```
src/     robots_check  the gate; nothing fetches an unchecked host
         kalshi        public read API + the four renamed-field traps
         pinnacle      the sharp reference + the three specials traps
         statsapi      pitchers, bullpens, lineups, form, venue, settlement
         wx            NOAA METAR/TAF, resolved against the park's azimuth
         parkfactor    run environment per venue, this season, regular only
         brief         the pre-match brief, one dict per game
         mentalities   the five decision functions
         engine        bots, fills, exits, sizing, settlement, the schema
         run           the unattended runner
         status        the one command
tests/   paper-only, no-mid-fill, fee-reuse, settlement, martingale refusal
deploy/  setup.bat, install_task.ps1, run_mlb_paper.bat, check.bat
data/    gitignored: paper.db, briefs/, caches, the strike map
reports/ the measured feasibility numbers, committed
```
