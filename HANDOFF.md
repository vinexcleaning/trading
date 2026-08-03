# HANDOFF.md — Kalshi edge search, concluded 2026-08-03

Working directory: **`C:\Users\gianf\trading`** (the repo itself).
Everything below is committed. Read `FINDINGS.md` for the answer,
`CONTINUE_HERE.md` to resume, `GUARDS.md` for the reusable checks.

---

## ⚠ ALL RECORDERS ARE DEAD, INCLUDING THE TWO PROTECTED ONES

Verified 2026-08-03: the only `python.exe` processes on this box belong to
other sessions (`youtube-signal`, `wallet-copy-study`). Every recorder is gone:

| PID | What | Status |
|---|---|---|
| **17892** | `record_depth.py` — tennis depth, **protected by STATUS.md** | **NOT RUNNING** |
| **24756** | `record_15m_opens_v2.py` — crypto 15m opens, **protected** | **NOT RUNNING** |
| 6340 | `record_depth_broad.py` — Kalshi depth, 85 families | not running |
| 26060 | `record_mlb_depth.py` — MLB depth incl. RFI | not running |
| 30428 | `record_lineups.py` — MLB lineups | not running |
| 22780 | `record_prematch.py` — soccer lineups/referee | not running |

**I did not stop 17892 or 24756.** They were alive and untouched throughout my
work. They died when the previous Claude Code process exited — a task
notification confirmed background tasks from that session were marked stopped
with no completion record. Detached `Start-Process` recorders did not survive.

**Consequence:** depth accrual stopped. That data cannot be backfilled (Kalshi
publishes no historical order book). Everything recorded up to the stop is
intact on disk. Given the project concluded with seven nulls, this costs
little — but if anyone intends to resume, the recorders must be restarted
manually and the gap is permanent.

---

## The result

**Seven independent tests, seven nulls.** Kalshi is efficiently priced
wherever a counterparty exists.

| # | Market | Mechanism | Result |
|---|---|---|---|
| 1 | Tennis (prior) | model vs bookmakers | worse, +0.01922 Brier, n=2,645 |
| 2 | Crypto ladders (prior) | model vs the mid | no model beats it, n=250 |
| 3 | Polymarket copy (prior) | follow skilled wallets | +0.937pp < 1.0pp spread |
| 4 | Soccer, 5 leagues | model vs closing line | worse, +0.02170, n=2,875 |
| 5 | MLB first innings | model vs Kalshi's price | +0.00237 [−0.00072,+0.00553], n=771 |
| 6 | MLB in-play | beat the market to news | market reprices in **2.2s** |
| 7 | MLB + 846,343 Statcast pitches | model vs Kalshi's price | +0.00212 [−0.00099,+0.00520] |

**The decisive diagnostic (test 7):** test 5's model could barely tell games
apart — probabilities varying **1.89pp** against Kalshi's **~6.5pp**. Adding a
decade of real pitch quality moved that to **2.89pp**, and the improvement over
guessing the base rate went **+0.00033 → +0.00034**. So the market's advantage
is *not* pitch quality. Further feature work is not warranted.

**Corroboration:** Kalshi matched a sharp reference in all three sports where
one exists — tennis r=0.9878 (MAD 1.95¢), MLB moneyline median **0.37¢**,
soccer r=0.9593 (median 1.12¢).

---

## Ten corrections, every one shrinking a claim

Four in a single day, all initially looking like discoveries:

1. **+17.25¢ edge** on RFI — a filter dropping quotes when the ask hit 100,
   which selected on the outcome
2. **301,578 contracts of depth** — one snapshot; same market showed 19 twelve
   hours later
3. **+51-second trading window** after a run — the median at-bat is 72 seconds;
   I started the clock before the event existed
4. **Crossed order book** (bid 99¢ / ask 22¢) — `delta` is an absolute size,
   not a change

Each was caught by a consistency check, not by inspection.

---

## What is on disk (all gitignored, none re-pullable except where noted)

| What | Where | Size |
|---|---|---|
| pmxt L2 order-book archive, 662/662 files, content-validated | `market-selection/data/pmxt/` | **63 GB** |
| Kalshi trade tape 2026-05-25→06-11, contiguous, 73,545,969 trades | `market-selection/data/tape_pmxt_window/` | 24 GB |
| Kalshi 24h exchange-wide tape, 8,867,978 trades | `market-selection/data/` | |
| Full open-market universe, 419,828 markets | `market-selection/data/` | 1.4 GB |
| MLB games 2016–2026 with first-inning outcomes, 29,785 | `mlb/data/games/` | |
| MLB first-inning Statcast, **846,343 pitches** 2017–2026 | `mlb/data/statcast/` | |
| ESPN soccer history, 24,307 matches 2015–2026 | `soccer/data/espn_history/` | |
| Recorded depth + lineups (partial, now stopped) | `*/data/depth_broad/`, `mlb/data/lineups/`, `soccer/data/prematch/` | |

Untracked and **expected**: all `data/` dirs, `*.parquet`, `*.jsonl`,
`__pycache__/`, and a handful of empty `*.err` files from background jobs.
Nothing untracked is a result.

---

## Reusable machinery — the actual durable output

| File | What it gives you |
|---|---|
| `common/costbar.py` | exact-Decimal fees both venues, reference points asserted at import |
| `common/backtest.py` | fill at the ask never the mid; P&L decomposition asserted; clustered bootstrap; null + planted-edge controls |
| `common/leakguard.py` | three-valued selection canary — PASS / FAIL / **UNTESTABLE** |
| `common/bookreplay.py` | pmxt book reconstruction (see limits below) |
| `market-selection/src/kalshi_api.py` | paced client; `orderbook()` reads the **correct** key |
| `soccer/src/teammatch.py` | roster-resolution name matcher + dead-alias check |
| `mlb/src/model_rfi_v2.py` | the gate, with controls |

---

## Facts that cost hours to learn

1. Kalshi's legacy price fields are **null on 100% of markets** — use
   `*_dollars` / `*_fp`.
2. **Order-book depth is free**, 20 levels a side, via
   `orderbook_fp.{yes,no}_dollars`. There is no `orderbook` key. Two prior
   sessions concluded depth was private; both read a key that does not exist.
3. `tick_size` does not exist; the tick is `price_level_structure`.
4. The tape retains **exactly 69 days**.
5. **Weekly Thursday maintenance window ~07:00–09:00 UTC** — hour 08 is empty
   at the source, not a bug in your code.
6. pmxt `delta` is an **absolute size**. But the replay is only accurate to
   **2–3¢ on 15–20% of trades** — the size of the entire edge being sought —
   so it **cannot support fill simulation**. Descriptive use only.
7. ESPN's free API publishes a **UTC `wallclock` on every event**, plus
   lineups, formations, referee, odds and a decade of history.
8. football-data.co.uk serves **wrong-country files on HTTP 200** —
   COL≡POL, KOR≡NOR, CHL≡CHN. Check the `League` column.
9. **Pinnacle vanished from football-data's 2026 data** (0 of 139 rows) —
   the second Pinnacle feed to disappear mid-project.
10. **No free xG** exists for Liga MX, Argentina, Colombia or MLS.

---

## Recommendation

**Stop.** The evidence is consistent across four sports, three mechanisms and
two venues, and the test-7 diagnostic says more features will not help.

If work resumes, the honest options are, in order:
1. Point the existing apparatus at a genuinely different question — not a
   fifth sport.
2. Use the 63 GB book archive **descriptively** (depth and spread behaviour
   over 662 hours). Real knowledge, not an edge.
3. Restart recorders only if there is a specific question they answer.

---

## For the coordinator

- My work is **entirely inside `C:\Users\gianf\trading`** and fully committed.
- Nothing of mine lives outside the repo. I created no files in
  `C:\Users\gianf\kalshi`; I only *read* `set1_overshoot/src/record_depth.py`
  there to resolve the order-book contradiction.
- `C:\Users\gianf\kalshi\set1_overshoot\` and `C:\Users\gianf\crypto\` are
  still outside the repo and still unbacked-up, as STATUS.md describes. Their
  recorders are now dead, so **the open-file-handle obstacle to moving them no
  longer exists** — but I have not moved anything and will not.
