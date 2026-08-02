# mlb/PROGRESS.md — where the MLB thread stands

Updated 2026-08-02 ~22:15 UTC. Read with `../CONTINUE_HERE.md`.

## Step 1 — KILL POINT: PASSED (with a caveat that matters more)

**No free first-inning line found anywhere.** Searched:

| Source | Result |
|---|---|
| ESPN, **every** odds provider, **9,802 prop entries**, 34 distinct types | no first-inning type. Inning-related types present are only `1st 5 Innings Moneyline / Run Line / Total Runs` |
| Action Network free scoreboard API | only `period = event`; bet types are moneyline/spread/total/team_score. The `rfi` substring hit was a false positive |
| Covers.com, ScoresAndOdds | no RFI market |
| the-odds-api, BettingPros | 401 / 403 — need keys |
| RotoWire YRFI page | 404 |

**KXMLBRFI survives.** This is absence of evidence, not proof — re-check if a
new source appears.

## ⚠ But: the depth claim that justified RFI was a snapshot

`market-selection/SHORTLIST.md` called KXMLBRFI "the deepest book on the list"
on one measurement. Re-measured:

| KXMLBRFI | spread | at touch | cost bar @50¢ |
|---|---|---|---|
| 2026-08-02 **08:00 UTC** | 1.0¢ | **301,578** | 2.24¢ |
| 2026-08-02 **20:00 UTC** (pre-game) | **8.0¢** | **19** | **5.75¢** |

That is LEDGER **S012/S013** again — a single window quoted as a property.
There the retraction went "thin book" → actually fine; here the flattering
number was the snapshot. **A recorder is now running to measure depth across
the full daily cycle** (`src/record_mlb_depth.py`, 464 markets, 4-min cycles,
8 series). At 22:06 UTC, once games began: 100% non-empty, 95% two-sided.

**Do not use the 301,578 figure again until the recorder settles it.**

## The first-5-innings families look poor

Measured 2026-08-02 20:00 UTC, busiest 20 markets each:

| Series | open | 2-sided | median spread | at touch | cost bar @50¢ |
|---|---|---|---|---|---|
| KXMLBF5TOTAL | 70 | 65% | 3.0¢ | 473 | 3.25¢ |
| KXMLBF5 | 30 | 85% | **17.0¢** | 3.7 | 10.25¢ |
| KXMLBF5SPREAD | 40 | 80% | **50.0¢** | 10 | 26.75¢ |
| *(KXMLBGAME, reference)* | 62 | 100% | 1.0¢ | 41,054 | 2.25¢ |

And all three **do** have a free DraftKings line, so they are expected to be
efficient like the game-winner (0.37¢). F5SPREAD and F5 are additionally
killed on cost. **F5TOTAL is the only one worth a cheap check.**

## Step 2 data — all verified by pulling

| Item | Status |
|---|---|
| **The RFI label itself** | **free and direct.** `statsapi.mlb.com/api/v1/game/{pk}/linescore` gives per-inning runs for both teams |
| StatsAPI history | 91 games in a 2015 sample week, 99 in 2026 — full decade |
| Batting order + pitchers | `/boxscore` gives `battingOrder` (9) and `pitchers` |
| **Probable pitchers** | available **a day ahead** — 7 of 8 games for tomorrow |
| **Lineups** | **0 of 8 games for tomorrow → LIVE-ONLY**, post ~2–4 h before first pitch |
| Statcast | 2,923 pitches × 119 cols for one day, with `inning`, `pitcher`, `batter`, `estimated_woba_using_speedangle`, `launch_speed` |
| Baseball-Reference, Retrosheet, pybaseball | reachable |
| FanGraphs | **403** |
| Reddit JSON API | **403 on all subreddits** — blocked unauthenticated |

## What the community has already built — and the number that matters

Six repos target first-inning prediction. The useful one:

**`lucasreydman/sharprfi`** publishes an honest backtest — **1,344 games,
2026-03-26 → 2026-07-05**:

| Variant | Brier | Calibration gap |
|---|---|---|
| **Blend Poisson + Monte Carlo** | **0.2447** | +1.2% |
| Sim alone | 0.2463 | +3.5% |
| Poisson alone | 0.2476 | −1.1% |
| Sim + streak factors | 0.2538 | +7.8% |
| Original contributed script | 0.2577 | −10.3% |

**Read this carefully.** A first-inning run is roughly a coin flip, so simply
predicting the base rate scores about **0.2475–0.25**. Their best engine —
Statcast barrel and hard-hit rates, weather, a batter-level Monte Carlo —
scores **0.2447**. That is an improvement over guessing the base rate of about
**0.003 Brier**.

Two things follow:
1. A serious first-inning model is only marginally better than the base rate.
2. They compare to the base rate, **not to a market price**. Our gate is
   harder: beat Kalshi.

**`phatcobra/nrfi-predictor`** (MIT, LightGBM, Retrosheet + pybaseball) is the
most methodologically careful. Its `build_features.py` docstring:

> *"Leakage-safe set-based feature construction… Per-game windows use only rows
> strictly before `game_date`. Missing observations remain missing; they are
> never converted into zero-valued outcomes or included in rate denominators."*

It also ships `guards.py` (fail-closed market usability, odds staleness),
`grade_nightly.py` (Brier, log-loss, calibration, market movement, drift) and
`audit_monthly.py`. **Worth mirroring their missing-data rule** — my soccer
feature builder defaulted missing features to 0.0, which they explicitly
refuse to do, and they are right.

`dbasley/NRFI_Project` ships `statcast_2023_first_inning.csv` and
`statcast_2024_first_inning.csv` — pre-filtered first-inning Statcast.

## Recorders running for MLB

| Process | What | Where |
|---|---|---|
| `record_mlb_depth.py` | 464 markets across 8 MLB series, 20 levels, 4-min cycles | `mlb/data/depth/<date>/<hh>/depth.jsonl` |

**Still to start: an MLB lineup recorder.** Lineups are live-only (0 of 8 games
have them a day ahead) and cannot be backfilled.

## Next actions

1. **Start the lineup recorder** — live-only, losing data every hour it is not
   running.
2. **Backfill StatsAPI**: ~10 seasons of games + per-inning linescores → the
   RFI label. Copy `soccer/src/backfill_espn.py`.
3. **Team-name matcher for Kalshi↔StatsAPI**, tested, before any join.
4. Features: starting pitcher first-inning splits from Statcast, top-3
   batters, park, weather, umpire. **Missing stays missing.**
5. The gate: model vs **Kalshi's own RFI price** (~69 days), plus calibration
   on the full history, with the null and peek controls.
