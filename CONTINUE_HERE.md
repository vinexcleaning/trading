# CONTINUE_HERE.md — paste this into a fresh chat to resume

**Read this file first, then `HANDOFF.md`, `GUARDS.md`, `LEDGER.md`,
`market-selection/SHORTLIST.md`.** Working directory `C:\Users\gianf\trading`.
The shell cwd resets between calls — use absolute paths.

Python: `C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe`
Git: `C:\Program Files\Git\cmd\git.exe`. Repo pushes to `origin/main`.

---

## Where the project stands (one paragraph)

We are hunting a tradeable edge on Kalshi. Tennis, crypto and Polymarket
copy-trading were all killed in earlier sessions. Market selection picked
soccer; soccer has now **failed its gate** — a model built from free features
was significantly WORSE than the bookmaker (+0.02170 Brier, CI
[+0.01626,+0.02750], n=2,875), almost exactly reproducing the tennis result
(T006, +0.01922). **We have now switched to MLB.**

## Why MLB, specifically

Soccer failed largely because the predictive data (xG) does not exist free for
those leagues. **In baseball it does** — pitch-level Statcast, free, a decade
deep. That is the one genuine difference against a long losing streak.

**The target is `KXMLBRFI` — "will a run be scored in the first inning".**
It is the only MLB family found with a deep book (301,578 contracts at the
touch) and **no free bookmaker price beside it** (34 DraftKings prop types
scanned via ESPN, none first-inning). Everything else on Kalshi's MLB board
has a free DK price to copy, which is why the game-winner is efficient to
within 0.37¢.

**Also approved for testing: the first-5-innings markets** (`KXMLBF5`,
`KXMLBF5TOTAL`, `KXMLBF5SPREAD`). These DO have a free DK line, so they are
expected to be efficient — testing them is a cheap check on whether "MLB side
markets are soft" is true at all.

---

## The agreed plan (user-approved)

1. **Confirm the target — KILL POINT.** Verify hard that no free RFI line
   exists anywhere. Measure RFI market count/day, spread, depth, settlement
   rate. *Kill immediately if a free RFI price turns up.*
2. **Join Kalshi ↔ MLB StatsAPI.** Build and TEST the team-name matcher first
   — the last two joins broke here (MLB 0/76, soccer 49%).
3. **Backfill ~10 seasons** of games, first-inning outcomes, Statcast.
4. **Features**: starting pitcher first-inning splits/form/pitch mix, top-3
   batters due up, park, weather, umpire, lineups.
5. **The gate**: no bookmaker exists for RFI, so **the model must beat
   Kalshi's own price** (~69 days, ~2,600 markets), plus calibration on the
   full history. Controls: peek-at-answer + scrambled labels.
6. **Only if step 5 passes**: run through `common/backtest.py` for real fills
   and fees.

### Three risks the user was told up front
- Kalshi's fee **peaks at 50¢** and RFI is near a coin flip, so these sit at
  the most expensive point. Need roughly **2.3% edge to break even**.
- Kalshi keeps only **~69 days** of price history (~2,600 RFI markets),
  growing ~38/day.
- Tennis lost, soccer lost, crypto lost. The prior is bad.

---

## Standing rules for this project (do not violate)

- **Read-only, public endpoints. No orders, no credentials, nothing live.**
- **Do not touch PIDs 17892 or 24756** (pre-existing recorders) or any
  running recorder listed below.
- Paced, single-threaded per host; back off on 429.
- **Verify by fetching, not by finding a link.** Two sources in this project
  were 404s described as available.
- **Content-validate recorders per row, never by row count.** Row counts have
  twice hidden empty writes.
- **Never mark at the mid** — fill at the ask buying, the bid selling.
- **Count events, not rows** for any interval.
- Commit and push after each completed task.
- **Run heavy work as background scripts, not inline in chat** — the user is
  usage-constrained. Write results to files; read back only summaries.

---

## What is running right now

| Process | What | Where it writes |
|---|---|---|
| PID 17892 | tennis depth recorder (pre-existing, DO NOT TOUCH) | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\` |
| PID 24756 | crypto 15m opens (pre-existing, DO NOT TOUCH) | `C:\Users\gianf\crypto\data\btc15m_opens\` |
| `record_depth_broad.py` | Kalshi depth, 85 families, 20 levels | `market-selection/data/depth_broad/` |
| `record_prematch.py` | soccer lineups/referee/odds, 10-min cycle | `soccer/data/prematch/` |
| heartbeat Monitor | content check every 30 min, **logs to file, reports only failures** | `market-selection/data/heartbeat.log` |

**Check they are alive on resume:**
`Get-CimInstance Win32_Process -Filter "Name='python.exe'"`

---

## Assets already on disk (do not re-pull)

| What | Where | Size |
|---|---|---|
| pmxt L2 order-book archive, **662/662 files, content-validated** | `market-selection/data/pmxt/` | 63 GB |
| Kalshi trade tape, 2026-05-25→06-11 **contiguous, 73,545,969 trades** | `market-selection/data/tape_pmxt_window/` | 24 GB |
| Kalshi 24h exchange-wide tape, 8,867,978 trades | `market-selection/data/kalshi_trades_24h.jsonl` | |
| Full Kalshi open-market universe, 419,828 markets | `market-selection/data/kalshi_markets_open.jsonl` | 1.4 GB |
| ESPN soccer history, 24,307 matches 2015–2026 | `soccer/data/espn_history/matches.jsonl` | |
| Soccer features, leak-free, 24,307 rows | `soccer/data/features.jsonl` | |

## Reusable code written for this (use it, do not rewrite)

| File | What it gives you |
|---|---|
| `common/costbar.py` | exact-Decimal fees both venues, asserted at import |
| `common/backtest.py` | **the scorekeeper.** `fill_price` (no mid path), `settle` (decomposition asserted), `clustered_bootstrap` (cluster arg required), `run_controls` (null + planted edge). Controls pass. |
| `common/leakguard.py` | three-valued selection canary PASS/FAIL/**UNTESTABLE** |
| `market-selection/src/kalshi_api.py` | paced Kalshi client. **`orderbook()` — reads `orderbook_fp.yes_dollars`; there is NO `orderbook` key** |
| `soccer/src/teammatch.py` | roster-resolution matcher + dead-alias check — **copy this pattern for MLB** |
| `soccer/src/build_features.py` | leak-free-by-construction feature builder — **copy this pattern** |
| `soccer/src/backfill_espn.py` | resumable windowed backfill — **copy this pattern** |

---

## Hard-won facts that will save you hours

1. **Kalshi legacy price fields are null on 100% of markets.** Use
   `*_dollars` / `*_fp`. `yes_bid`, `last_price`, `volume` etc. are all None.
2. **Order-book depth IS free**, 20 levels a side, via
   `orderbook_fp.{yes,no}_dollars`. Two prior sessions concluded otherwise;
   both read a key that does not exist.
3. **`tick_size` does not exist** on the market object. The tick is
   `price_level_structure` ∈ {linear_cent 1¢, deci_cent 0.1¢,
   tapered_deci_cent}.
4. **Kalshi's tape retains exactly 69 days** and rolls daily.
5. **Kalshi has a weekly Thursday maintenance window ~07:00–09:00 UTC** —
   hour 08 is empty at the source. Not a bug in your code.
6. **ESPN `site.api.espn.com` is free, unkeyed, and rich.** Its `/summary`
   gives a UTC `wallclock` on every event, lineups with starter flags,
   formation, referee, odds, standings, form, head-to-head.
7. **ESPN scoreboard caps its response** regardless of `limit` — use ≤7-day
   windows.
8. **football-data.co.uk serves WRONG-COUNTRY files on HTTP 200.**
   COL≡POL, KOR≡NOR, CHL≡CHN, byte-identical. Check the `League` column.
9. **Pinnacle is gone from football-data's 2026 data** (0 of 139 rows).
10. **Kalshi candlesticks**: `/series/{s}/markets/{t}/candlesticks`,
    `period_interval` 1 or 60, **max 5000 candles per request**.

---

## Immediate next actions when you resume

1. Verify the running processes above are still alive.
2. Read `mlb/` for whatever progress exists (`mlb/PROGRESS.md` if present).
3. Continue the plan from wherever `mlb/PROGRESS.md` says.
4. `git log --oneline -10` shows exactly what has landed.

---

## Tone the user asked for

Explain results in **plain English**, not jargon. They are relaying findings
and need to understand what worked, what failed, and what is next — without
decoding statistics vocabulary. Lead with the answer.
