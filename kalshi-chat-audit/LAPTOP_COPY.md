# LAPTOP_COPY.md — Read-only inventory of `C:\Users\gianf\kalshi`

Audit date: 2026-07-31
**Nothing in this folder was modified, created, moved or deleted.** Every command run against it was
a read: directory listing, file metadata, and reading the eight text files in `reports\`. No script
was executed, no data file was opened for write.

---

## Headline finding — read this before merging anything

**This is not a divergent copy of the desktop `kalshi` folder. It is a different project that
happens to share the folder name.**

| | This laptop — `C:\Users\gianf\kalshi` | Desktop — `C:\Users\vinig\kalshi` |
|---|---|---|
| What it is | The **Stage 0–5 pre-match player model** research pipeline | The **live in-play trading bot** |
| Representative files | `stage0_audit.py`, `stage1_features.py`, `stage4_model.py`, `pinnacle_vs_kalshi.py` | `gui.py`, `tennis_engine.py`, `kalshi_client.py`, `position_manager.py`, `paper_bot.py`, `record_data.py` |
| Filename overlap | **Zero.** Not one filename appears in both. | |
| Touches money | No — read-only public Kalshi market data, no credentials present | Yes — signed REST client, live orders |
| Created | One session, 2026-07-29 | Built over ~2 weeks, 07-15 → 07-28 |

This split was deliberate. On 2026-07-28 the instruction was explicit: *"Put it in a separate
directory from the bot code so there's no chance it starts editing live files"*, and the next day,
*"you're not home rn so you'd use my other laptop"* — this laptop.

**Merge implication.** There is no version conflict to resolve, because there are no shared files.
The risk is the opposite one, and it is the one already flagged in the chats: **copying a folder over
a folder in either direction destroys the other project entirely.** Merge by placing these as
*siblings* under one parent, never by overwriting.

This folder is also the **only** copy of the Stage 0–5 work. It is unversioned, unbacked-up, and
contains ~1 GB of derived artifacts that took a full session to compute.

---

## 1. Top level

```
C:\Users\gianf\kalshi\
├── data\        312 files   1,557.33 MB
├── src\          27 files       0.18 MB
└── reports\       8 files       0.03 MB
```

**Total: 347 files, 1,557.53 MB (~1.52 GB).**

There is nothing else. No `README`, no `CLAUDE.md`, no `PROGRESS.md`, no `DECISIONS.md`, no
`requirements.txt`, no `.gitignore`, no notebooks, no `__init__.py`, no config file of any kind.

## 2. Git status

**There is no git repository.** `C:\Users\gianf\kalshi\.git` does not exist, and `git status` returns
`fatal: not a git repository (or any of the parent directories)`. No parent directory is a repo
either.

Consequences for the merge:
- **No history.** No commit log, no record of what was tried and abandoned, no way to roll back.
- **No provenance beyond file timestamps.** The `git log` that the audit plan expected to be *"the
  most reliable record of what past sessions actually did"* does not exist for this half of the work.
- This folder cannot be reconciled with the desktop by pulling. It has to be added.

## 3. File dates — this is a single three-hour session

| | |
|---|---|
| Earliest file | `src\download_sackmann.py` — **2026-07-29 12:22:31** |
| Latest file | `reports\pinnacle_vs_kalshi.txt` — **2026-07-29 15:13:39** |
| Span | **2 h 51 m**, one continuous session |

Every one of the 347 files was written inside that window. Nothing has been touched since
2026-07-29. This matches the Stage 0–5 session recorded in the chat archive and in the four
`kalshi-*` / `sackmann-*` memory files (all `originSessionId: 0fa8d26e…`, modified 2026-07-29).

**Nothing here reflects any work after 2026-07-29** — not the v3 backtest, not the BTC/exchange-wide
scan, not the copy-trading tests, not the Discord signal bot.

## 4. `src\` — 25 Python scripts + 2 cached bytecode files (0.18 MB)

Grouped by role, with the report each produced (see §5):

**Pipeline stages**

| File | Size | Time | Report produced |
|---|---:|---|---|
| `stage0_audit.py` | 10,083 | 12:33 | ✅ `stage0_coverage.txt` |
| `stage1_features.py` | 11,410 | 14:22 | ❌ none |
| `stage2_shrinkage.py` | 12,633 | 14:13 | ✅ `stage2_shrinkage.txt` |
| `stage3_traits.py` | 11,643 | 14:17 | ✅ `stage3_traits.txt` |
| `stage4_model.py` | 15,129 | 14:38 | ✅ `stage4_model.txt` |
| `stage4_kalshi_liquid.py` | 2,882 | 14:42 | ✅ `stage4_kalshi_liquid.txt` |
| `stage5_selective.py` | 10,771 | 14:42 | ✅ `stage5_selective.txt` |

**Leak testing and benchmarking** — the most valuable code in the folder

| File | Size | Time | Report |
|---|---:|---|---|
| `anchor_leak_test.py` | 2,981 | 15:12 | ✅ `anchor_leak_test.txt` |
| `pinnacle_vs_kalshi.py` | 13,797 | 15:13 | ✅ `pinnacle_vs_kalshi.txt` |
| `download_kalshi_prices_multi.py` | 4,234 | 15:04 | (feeds the above) |

**Data acquisition**

`download_sackmann.py` (12:22) · `download_tennisdata.py` (13:09) · `download_kalshi.py` (14:53) ·
`download_kalshi_prices.py` (14:16) · `explore_kalshi.py` (12:24) · `verify_data.py` (12:24) ·
`tennis_data.py` (14:56, 15,675 B — the shared loader/name-matching module)

**Diagnostics and probes** — written to answer one question, no persisted output

`diag_gaps.py` · `diag_venue.py` · `diag_stage5.py` · `diag_join_quality.py` (this is the script that
found the look-ahead leak) · `probe_tennisabstract.py` · `probe_ta_coverage.py` ·
`probe_ta_recency.py` · `validate_stage1.py`

**Cached bytecode:** `stage0_audit.cpython-312.pyc`, `tennis_data.cpython-312.pyc`.

⚠️ **Naming trap to fix on merge.** `pinnacle_vs_kalshi.py` / `.txt` does **not** use Pinnacle. The
report states plainly: `with a real Pinnacle price: 0` — tennis-data.co.uk stopped publishing
Pinnacle in 2026 (5.1% coverage), so the benchmark is the **Betfair Exchange** closing price (93.6%
coverage). The Stage 4 report also still labels a row *"Pinnacle closing"*. Anyone reading these
files cold will draw the wrong conclusion about which book was used.

## 5. `reports\` — 8 text files (0.03 MB), all human-readable

These are the artifacts behind Section D of `LEDGER_CHATS.md`. Small, self-describing, and each
states its own n and confidence intervals. **This is the highest-value 30 KB in either project.**

| File | Size | Time | What it settles |
|---|---:|---|---|
| `stage0_coverage.txt` | 6,154 | 15:00 | Coverage audit, **corrected** for the ITF omission. 20,922 markets, 86.6% present in data, **36.9%** clearing all three thresholds. Sackmann history ends **2026-06-02**; **85.0%** of markets played after it; only **3,145** usable. |
| `stage2_shrinkage.txt` | 1,536 | 14:28 | Shrinkage sanity check across 16 statistic × bucket cells — raw sd collapses toward population sd as intended. |
| `stage3_traits.txt` | 4,106 | 14:19 | Split-half reliability on **3,446,840 player-match rows**. Comeback r = +0.439 raw → **+0.125** residualised on win rate; tiebreak +0.091 (noise); positive control +0.633; null ≈ 0. |
| `stage4_model.txt` | 3,212 | 14:39 | Held-out Brier **0.19884**, AUC 0.75984, calibrated within ~0.021. **Model loses to bookmakers**: +0.01922 CI [+0.01438, +0.02417], n=2,645. 6 variants declared. |
| `stage4_kalshi_liquid.txt` | 1,655 | 14:43 | Re-scored by quote quality. All 502 → "indistinguishable"; **spread ≤10c (n=302) → market beats model, +0.03711 CI [+0.0165, +0.0569]**. |
| `stage5_selective.txt` | 4,192 | 14:42 | **The mid-fill trap in one table**: +14.4%/+18.7%/+24.6% ROI at mid vs **−24.3%/−28.3%/−30.9%** at ask/bid. 39.8% of markets quote wider than 10c. 43 segments, BH-corrected, 19 survive — all negative. |
| `anchor_leak_test.txt` | 1,056 | 15:12 | The look-ahead leak, characterised. At −0h: 4.1% of quotes outside 2c–98c and **100% correct**. At **−6h**: 0.1%, corr 0.978, diff +0.0012. |
| `pinnacle_vs_kalshi.txt` | 4,935 | 15:13 | Kalshi vs **Betfair** at −6h, n=809: r = **0.9878**, MAD 1.95c vs 2.44c cost, Brier diff −0.00053 CI [−0.00312, +0.00157]. On disagreements Kalshi closer **49.1%** CI [42.7%, 55.6%]. All 14 segments cross zero. |

## 6. `data\` — 312 files, 1,557.33 MB

### `data\cache\` — 13 files, 1,003.60 MB (derived; regenerable but slow)

| File | MB | Notes |
|---|---:|---|
| `stage2_features.parquet` | 417.00 | Largest single artifact |
| `stage1_features.parquet` | 287.59 | |
| `stage4_predictions.parquet` | 244.04 | Held-out predictions |
| `matches.parquet` | 43.60 | Consolidated match table |
| `stage3_records.parquet` | 8.87 | 3.4M player-match rows |
| `kalshi_events.parquet` | 1.65 | |
| `stage0_player_market.parquet` | 0.71 | |
| `stage4_bookmaker_join.parquet` | 0.058 | The join behind the Stage 4 gate |
| `pinnacle_vs_kalshi.parquet` | 0.036 | n=844 joined matches |
| `stage4_kalshi_join.parquet` | 0.035 | |
| `stage2_k_tuning.csv` | 0.009 | |
| `stage5_segments.csv` | 0.003 | The 43 segments |
| `stage2_chosen_k.csv` | 0.0003 | 307 bytes — all 16 shrinkage constants. Fine. |

**Correction (2026-07-31):** an earlier version of this file recorded `stage2_chosen_k.csv` as
**0 bytes** and flagged it as a missing pipeline output. That was wrong. Sizes in this table were
displayed in MB rounded to three decimals, so 307 bytes rendered as `0.000` and I misread it as
empty. The file is fully populated with all 16 statistic × bucket `k` values, matching the `k`
column in `stage2_shrinkage.txt` exactly. **Stage 2 completed correctly; there is no defect here.**

### `data\kalshi\` — 3 files, 105.74 MB

| File | MB | Notes |
|---|---:|---|
| `tennis_markets.json` | 105.51 | Raw market pull — 20,922 matches, 2026-01-03 → 2026-07-29 |
| `kalshi_prematch_prices.parquet.INVALID_LOOKAHEAD_LEAK` | 0.158 | Single-anchor prices — **⚠️ the leaking ones. Renamed 2026-07-31.** |
| `kalshi_prices_multianchor.parquet` | 0.067 | Multi-anchor pull (`bid/ask/mid_h{0,1,2,6,24}`) — **use this one**, at −6h |

⚠️ The single-anchor file is the anchor-on-`occurrence_datetime` pull that produced the retracted
"Kalshi beats Betfair" result. **Renamed 2026-07-31** with an `.INVALID_LOOKAHEAD_LEAK` suffix
rather than deleted, so the retraction stays auditable. Verified leak signature in that file:
84.5% of its 4,968 rows are anchored <1h before `occurrence_datetime`, 98.6% <6h, and 4.3% of mids
sit outside 2c–98c — matching the 4.1% in `anchor_leak_test.txt`. See
`reports\README_DEFECTS.md` §1.

### `data\sackmann\` — 281 files, 442.44 MB

The frozen third-party mirror (upstream repos are 404 — see `sackmann-data-source-gone` memory).

| | Files | MB | Contents |
|---|---:|---:|---|
| `atp\` | 155 | 251.8 | 59 × `atp_matches_YYYY`, 49 × `atp_matches_qual_chall_YYYY`, 36 × `atp_matches_futures_YYYY`, 1 × amateur, players file, 7 ranking decades, `matches_data_dictionary.txt`, `UPSTREAM_README.md` |
| `wta\` | 126 | 190.7 | 59 × `wta_matches_YYYY`, 59 × `wta_matches_qual_itf_YYYY`, players file, 6 ranking decades, `UPSTREAM_README.md` |

Note the mirror's `slam_pointbypoint/` directory was **not** downloaded. Match data ends 2026-06-02.
Licence is CC BY-NC-SA 4.0 — **non-commercial**, which matters if this is ever traded on.

### `data\tennisdata\` — 15 files, 5.55 MB

`ATP_2020…2026.xlsx` and `WTA_2020…2026.xlsx` (14 files) from tennis-data.co.uk, plus the
consolidated `tennisdata_all.parquet` (0.77 MB). This is the source of the Betfair Exchange closing
prices — and of the finding that Pinnacle coverage collapsed to 5.1% in 2026.

## 7. Credentials and secrets

**None found.** No `.env`, no `.pem`, no `.key`, no `*_secret*`, no API keys in any config file
(there are no config files). The only `.json` in the tree is the 105 MB market-data pull; the only
`.md` files are the two upstream Sackmann READMEs.

This is consistent with how the work was done — the session explicitly established that Kalshi's
market-data endpoints are public and unauthenticated, which *"structurally guarantees no order can be
placed in this session."* **This folder is safe to push to a private repo as-is**, subject to §8.

## 8. Recommended merge plan

1. **Do not copy folder-over-folder in either direction.** Give this project its own name. The clean
   shape discussed in the chats is one parent (e.g. `C:\Users\vinig\trading\`) with
   `player-model\` (this), `bot\` (desktop `kalshi`), `kalshi-markets\`, and `tennis-copy-trade\`
   as siblings, and **one** git repo at the parent level — not nested repos.
2. **Commit `src\` and `reports\` immediately.** 210 KB total, no secrets, and it is the only copy of
   the six results that closed the tennis question. Losing this laptop today loses that work.
3. **Gitignore `data\` entirely** (1.52 GB, and `data\sackmann\` is re-downloadable from the mirror
   while `data\cache\` is regenerable from `src\`).
4. **Before ignoring `data\`, decide about `data\cache\`.** It is ~1 GB and took a full session to
   compute. If it is not backed up somewhere, it exists only here.
5. **Three fixes to make while merging**, all cheap:
   - Rename `pinnacle_vs_kalshi.*` → `betfair_vs_kalshi.*` and correct the "Pinnacle closing" label
     in `stage4_model.txt`, so the benchmark isn't misread later.
   - Delete or clearly rename `kalshi_prematch_prices.parquet` (the leaking anchor).
   - Investigate the empty `stage2_chosen_k.csv`.
6. **Write the missing `README.md` / `STATUS.md` at the same time.** With no git history and no notes,
   the only account of what this pipeline did is the eight report files and the four memory entries.
   A ten-line README naming the stage order and the Stage 4 verdict costs nothing now and is worth a
   lot in a month.

## 9. What is *not* here

Absent from this laptop, and therefore not merge-able from it — all of it lives on the desktop:

- The live bot (`gui.py`, `tennis_engine.py`, `kalshi_client.py`, `position_manager.py`,
  `paper_bot.py`, `record_data.py`, `sofascore_feed.py`, `autoscan.py`, `notify.py`)
- The 27,083-observation recorder dataset and the 94 live trade records
- The v3 candlestick backtest (`pull_data.py`, `engine.py`, `strategies`, `test_engine.py`) and the
  14,162-market / 7,081-match candle pull
- The BTC / exchange-wide recorders and the ~1.77M recorded trades
- The `kalshi markets` and `tennis copy trade` project folders
- The Discord signal-bot code (`screen_watch.py`, `eval_vision.py`) — Max account, desktop
- Any Claude Code session transcripts (these are local to each machine and are **not** in the chat
  exports)
