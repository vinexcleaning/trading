# STATUS — read this first

Audited 2026-07-30. Read-only; nothing was started, stopped, changed or traded.
Detail in `LEDGER.md` (117 claims), `FAILURE_MODES.md`, `GAPS.md`, `INVENTORY.md`.

## Threads

| Thread | State | One-line reason |
|---|---|---|
| **Kalshi tennis momentum bot** (`C:\Users\vinig\kalshi`) | **ALIVE — and it should not be** | Its own 14,162-market backtest says every variant loses ~9¢/trade against a ~4¢ cost base, and the config it now runs was never backtested (`GAPS.md` G-B) |
| **Polymarket tennis copy trading** (`C:\Users\vinig\tennis copy trade`) | **ALIVE, narrowly** | Thesis closed — 42,652 wallets, 0 BH discoveries at FDR 5%/10%; informed flow dies inside 15 s. One frozen 4-wallet list awaits a forward score |
| **Kalshi exchange-wide scan** (`C:\Users\vinig\kalshi markets`) | **CLOSED — verdict reached** | 116 hypotheses, zero tradeable Kalshi edges. Only `KXTEMPDCH` weather survives, and only as an unmeasured question |
| **Kalshi weather bot** (`Documents\Codex\weather-market-bot`) | **CLOSED 23 Jul** | Model loses to the market ask (Brier 0.205 vs 0.169); every exit policy lost money; forward collector only, no real money permitted |
| **PTIS Polymarket copy trading** (`Codex\2026-07-23\…-master-2`) | **CLOSED 24 Jul** | Leaderboard consensus copying rejected; the control lost $40.17 on $40 |
| **Discord trading-server signals** (`OneDrive\Desktop\kalshi\…rot-trades.json`) | **DORMANT — never started** | 176 messages exported 30 Jul; no code anywhere reads them |

## What is running right now

**Nothing.** Verified: zero `python` processes, no `.recorder.lock`, empty Startup folder,
no scheduled tasks matching kalshi/tennis/bot/record.

Two documents say otherwise and are **stale** — do not trust them:

- `kalshi markets/MORNING_REPORT.md:925` "Still running: Kalshi tiered recorder, external
  recorder, arb scanner." They stopped at **17:32 UTC** (last line of
  `data/recorder_kalshi.log`; arb scanner's last entry is scan 1084 at 16:51 UTC).
- `kalshi markets/data/gaps_report.md` was generated at 09:23 UTC and **understates the
  recorded dataset by ~8 hours**.

## ⚠ What must not be touched

1. **`C:\Users\vinig\kalshi\bot_state.json` — 5 open positions with live Kalshi order ids.**
   Each carries a `take_profit_order_id` for a resting sell at 95¢, opened 2026-07-28. Those
   orders live on Kalshi's servers, not here. The matches are long settled, so they have
   almost certainly resolved — **but that must be confirmed on kalshi.com, not inferred.**
   Do not edit or delete this file; the bot adopts positions from it and would otherwise set
   fresh stops on positions that no longer exist.
2. **`C:\Users\vinig\kalshi\kalshi_private_key.pem`** — places real orders on the live
   account. Not a demo key.
3. **`run_both.bat` and `autostart.bat`** default to `gui.py --live --bankroll 125
   --stake-pct 5`. `autostart.bat` is designed to be shortcut into Startup and auto-resume
   **live trading** after a reboot. It is not currently in Startup. Use `--watch`, which is
   genuinely read-only.
4. **Never run `gui.py` on two machines at once.** Documented in `MOVING_TO_LAPTOP.md`: both
   place orders, both fire stops, and the second sell opens a **short**. `bot_state.json` is
   per-machine and they cannot see each other.
5. **`weather-market-bot`'s final 20% test split is sealed.** Do not open it; it is the only
   untouched evaluation set in the corpus.
6. **`tennis copy trade/data/follow-list.json`** — frozen 2026-07-30 06:01 UTC. Never
   regenerate it to "update" it; freeze a new one. Regenerating destroys the only
   ungameable test anyone has set up.
7. **`kalshi markets/data/raw_empty_books_prefix/`** — quarantined corrupt output, kept
   deliberately as evidence. Not a bug to clean up.

## Data on disk

| Where | Size | Covers |
|---|---|---|
| `tennis copy trade\data` | **6.8 GB** | `best.db` 3.85 GB (71,497 positions, 2.04M price obs), `tape_scan.db` 391 MB (6,937 matches, 1.77M trades, 42,652 wallets), Polymarket tennis **Jul 2025 – Jul 2026** |
| `weather-market-bot\data` | 2.9 GB | 303,396 markets / 60,409 weather; NDFD forecast archive **Jan 9 – May 22 2026**; collector logs to 23 Jul |
| `PTIS\data` | 560 MB | `ptis.sqlite3`, cohort rows **Mar 9 – Jul 24 2026**; 1,467 public trades, 226 first-seen observations |
| `kalshi\backtest\data` | 426 MB | Kalshi tennis 1-min candles, **2026-06-29 → 07-27**, 14,162 settled markets, 4.93M candles |
| `kalshi markets\data` | 314 MB | Settled history for 22 families (`KXBTC15M` 6,271 markets ≈ 66 days); BTC/ETH 1-min candles **2026-05-20 → 07-30** (102,716 each, 100% coverage); live recording **2026-07-30 07:30 → 17:32 UTC** only (~2.03M trades, books from 09:03) |
| `kalshi\` root | ~22 MB | Live recorder tape `tennis_data*.jsonl` **27–28 Jul** (7,170 + 27,083 rows); `paper_trades.jsonl` 31 rows, **all OPEN, none closed — nothing scored**; 11 orphan `_*.json` files |

**Irreplaceable:** the `kalshi markets` live book recording (Kalshi exposes no historical
order book) and the `tennis copy trade` tape databases (~2.5 h to rebuild, ~200 h the
per-wallet way). Everything else is re-pullable.

## The single next action per live thread

**Kalshi tennis bot — decide whether it trades, before anything else.**
The bot's own evidence says the strategy loses and the running config was tuned on 125–137
observations. Either stop it, or first re-run `backtest/high_sweep.py` over the *current*
parameter set on the candle data already on disk. Both are cheap; leaving it armed while
neither is done is the actual risk here. While in there, re-run `high_sweep.py`,
`high_entry.py` and `longshot.py` and **save their output** — four of P1's findings (the
buy-high band economics, the maker-fill result, a caught look-ahead leak, and a Kalshi
tennis calibration measurement) currently exist only in a memory file, and re-running takes
minutes (`LEDGER.md` R6). Separately, confirm on kalshi.com that the 5 positions in
`bot_state.json` and their resting 95¢ sells have resolved.

**Polymarket tennis copy trading — fix defect C082, then score the forward record.**
`0x39f6236ccd16` is one of four frozen wallets and 33.7% of its follower outcomes are
contaminated (the follower is modelled as holding to resolution when the wallet traded out).
The forward verdict is **pooled**, so that one wallet corrupts it. Fix it or restrict copier
metrics to held-to-settlement positions and say so, then run `scripts/forward_record.py`
against the +13.2p search-wide bar. This is the only ungameable test anyone has set up.

**Discord trading-server signals — measure the 174 calls.**
Never attempted, and every method needed is already built and validated in
`tennis copy trade/scripts/`. Fold to one observation per match first. Expect
"underpowered" — 174 calls against a 481-settlement requirement — and treat that as the
finding.

**Before quoting anything from `kalshi markets`:** four retracted results are still stated
as fact in `docs/GO_NO_GO.md` and `docs/shortlist.md` (the 40× depth collapse, the
bucket-by-bucket Kalshi calibration claim, the 8,090-market weather n, and the "seven daily
families clear the capacity bar" framing). `MORNING_REPORT.md` is the corrected document;
the shorter, more quotable files are the stale ones. See `LEDGER.md` R1.
