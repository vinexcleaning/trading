# INVENTORY — every in-scope project folder

Audit date 2026-07-30. Read-only. Out-of-scope folders (games, media, Vinex-OS, the
Meta-ads Codex job, `.codex` session state) were classified from directory listings and
never opened.

---

## The eight in-scope projects

| # | Path | What it is | Live/dormant | Git | Duplicates |
|---|---|---|---|---|---|
| P1 | `C:\Users\vinig\kalshi` | **The live money bot.** Kalshi tennis momentum trader + recorder + paper bot + a 14k-market backtest | **Dormant but armed** — no process running, 5 open positions and 5 resting take-profit orders in `bot_state.json` | **No repo** | P4 is an older copy of its core files |
| P2 | `C:\Users\vinig\kalshi markets` | Exchange-wide Kalshi edge scan, one session 2026-07-30. Recorders, arb scanner, 116 hypotheses | Dormant — recorders stopped ~17:32 UTC 30 Jul despite docs saying "still running" | **Yes, 23 commits**, clean tree | Its Phase 6 re-analyses P3's `tape_scan.db` |
| P3 | `C:\Users\vinig\tennis copy trade` | Polymarket tennis copy-trading analytics: ingestion, tape sweep, wallet screening, dashboard | Dormant. A frozen forward-test list is waiting to be scored | **No repo** | Shares `tape_scan.db` with P2 |
| P4 | `C:\Users\vinig\OneDrive\Desktop\kalshi` | Snapshot of P1 as of 26 Jul + the Discord trades export | Dormant, stale | No repo | **Yes — duplicate of P1** (older, smaller files) |
| P5 | `C:\Users\vinig\Documents\Codex\weather-market-bot` | Kalshi weather/temperature bot: NDFD forecasts, probability model, backtests, forward paper collector | Dormant since 23 Jul | **Yes, 14 commits** | P8 is its staging twin |
| P6 | `…\Codex\2026-07-23\files-mentioned-by-the-user-master-2` | **PTIS** — Polymarket Trader Intelligence System. Copy-trade discovery, execution sim, consensus backtest | Dormant since 24 Jul | No commits (`.git` present but empty) | Same problem domain as P3, independent codebase |
| P7 | `…\Codex\2026-07-23\files-mentioned-by-the-user-master\outputs\polymarket-shadow-copy` | Early Polymarket shadow-copy skeleton, superseded by P6 | Dormant | No commits | **Subsumed by P6** |
| P8 | `…\Codex\2026-07-22\…-untrusted\work\weather-market-bot-staging` | Staging copy of P5 | Dormant | No commits | **Duplicate of P5** |

Supporting, not a project:
`C:\Users\vinig\Downloads\DiscordChatExporter.win-x64` — the tool that produced the
trading-server export now sitting in P4.

---

## Data on disk

| Location | Size | Files | What |
|---|---|---|---|
| `tennis copy trade\data` | **6,774 MB** | 15 | `best.db` 3.85 GB, `real.db` 776 MB, `tape_scan.db` 391 MB, `best.db.bak-before-backfill` 1.93 GB |
| `weather-market-bot\data` | 2,927 MB | 4,179 | `weather_market_bot.db` 399 MB + NDFD raw archive + collector logs |
| `PTIS\data` | 560 MB | 921 | `ptis.sqlite3` 267 MB + raw API captures |
| `kalshi\backtest\data` | 426 MB | 10 | `views.pkl` 329 MB, `candles.parquet` 57 MB, per-tour candle files |
| `kalshi markets\data` | 314 MB | 4,489 | `markets_open.parquet` 181 MB, settled history 22 families, 8.5 h of raw recording |
| `kalshi markets\reports` | 19 MB | 42 | analysis outputs |
| `kalshi` (root) | ~22 MB | — | `tennis_data*.jsonl` recorder tape, `paper_trades.jsonl`, 11 orphan `_*.json` files |

`kalshi markets\data\raw` partition sizes: kalshi_trades 83.9 MB (1,313 files),
kalshi_book_tier1 18.1 MB, tier2 7.9 MB, spot 4.9 MB, perp 3.3 MB, deribit_chain 2.8 MB,
status 1.5 MB, deribit 0.7 MB, nws 0.4 MB.

---

## Duplicated logic — the fee formula

**Nine independent implementations of the Kalshi/Polymarket fee across five codebases.**
Only two of them are numerically correct.

| # | File | Form | Float-dust guard |
|---|---|---|---|
| 1 | `kalshi\backtest\engine.py:101` | `ceil(round(0.07*C*p*(1-p)*100, 9))/100` | **YES** — comment names the exact `175.00000000000003` bug |
| 2 | `kalshi markets\src\kalshi_research\fees.py:17` | `Decimal` + `ROUND_CEILING` | **YES** — comment names the same bug |
| 3 | `kalshi\tennis_engine.py:240` | `ceil(rate*C*p*(1-p)*100)/100` | **NO** |
| 4 | `kalshi\paper_bot.py:85` | `ceil(0.07*n*p*(1-p)*100)/100` | **NO** |
| 5 | `kalshi\backtest\longshot.py:31` | same | **NO** |
| 6 | `kalshi\backtest\high_entry.py:28` | same | **NO** |
| 7 | `kalshi\backtest\high_sweep.py:37` | same | **NO** |
| 8 | `OneDrive\Desktop\kalshi\tennis_engine.py:123` | same | **NO** (stale copy of #3) |
| 9 | `PTIS\src\ptis\execution.py:33` | `shares*rate*p*(1-p)`, Polymarket, **no ceil at all** | n/a — different venue rule |

Plus a tenth cost model that is not a fee formula at all:
`weather-market-bot` uses flat cent buffers (`ENTRY_COST_BUFFER = 0.01`,
`EXIT_COST_BUFFER = 0.03`, `PER_LEG_COST_BUFFER = 0.03`) and never computes the
quadratic Kalshi fee. Its backtest P&L is therefore not fee-accurate in either
direction.

**The same bug was independently discovered and fixed twice (#1, #2) and left unfixed in
six places.** Two of the unfixed ones — `tennis_engine.py` and `paper_bot.py` — are in
the live-trading path.

---

## Other duplicated logic

- **Kalshi API client:** `kalshi\kalshi_client.py` (16 KB), `OneDrive\Desktop\kalshi\kalshi_client.py`
  (5 KB, stale), `kalshi markets\src\kalshi_research\api.py`,
  `weather-market-bot\src\weather_market_bot\markets\kalshi_client.py`. Four clients.
- **Polymarket wallet/copy-trade analysis:** P3 and P6 are two full independent
  implementations of the same research question, built four days apart, with no
  cross-reference in either direction.
- **Weather modelling for Kalshi temperature markets:** P5 (Jul 22–23, NDFD forecast
  model, scored against market asks) and P2's `scripts/weather_model.py` (Jul 30,
  persistence model, scored against climatology). **Neither cites the other, and they
  reach opposite-facing conclusions about whether the market is beatable.** See
  `LEDGER.md` C-041/C-042 and `GAPS.md`.
- **Backtest harness:** `kalshi\backtest\engine.py`, `weather-market-bot\backtest\engine.py`,
  `PTIS\src\ptis\backtest.py` — three separate engines, three separate execution models.

---

## Git status

| Repo | Commits | Branch/tree | Notes |
|---|---|---|---|
| `kalshi markets` | 23 | clean | All 2026-07-30, 02:42–13:26 EDT. Last two commits are self-corrections |
| `weather-market-bot` | 14 | clean | All 2026-07-22/23 |
| everything else | — | **not a repo** | P1, P3, P4, P6, P7, P8 have no version history at all |

P1 (`kalshi`) holding live-trading code with no version control is the most
consequential of these: there is no record of what the strategy looked like on any past
date, so no past live result can be attributed to a known code state.
