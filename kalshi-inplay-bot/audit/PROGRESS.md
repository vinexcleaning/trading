# AUDIT PROGRESS

Read-only audit started 2026-07-30 (session run per `C:\Users\vinig\Downloads\audit_prompt.md`).
Outputs live in `C:\Users\vinig\kalshi\audit\`. Nothing outside this folder is written to.

## Scope
In scope: Kalshi, Polymarket, prediction-market trading, the Discord/trading-server signal
bot, and any bot or backtest built for those. Everything else on the machine ignored.

## Step log

- [x] Read audit prompt.
- [x] Enumerated user-level directories; identified 5 in-scope roots + 1 tool folder.
- [x] Walked git logs of the two in-scope git repos (`kalshi markets` 23 commits,
      `Documents\Codex\weather-market-bot` 14 commits). `kalshi`, `tennis copy trade`,
      `OneDrive\Desktop\kalshi` are NOT git repos — no commit history available for them.
- [x] Read `kalshi markets`: PROGRESS.md, DECISIONS.md, MORNING_REPORT.md (931 lines),
      docs/HYPOTHESIS_LEDGER.md, docs/GO_NO_GO.md.
- [x] Read remaining `kalshi markets` docs + reports JSON (verified 8 result files
      against the prose; found 4 discrepancies).
- [x] Read `C:\Users\vinig\kalshi` (live tennis bot): BACKTEST_RESULTS.md,
      MOVING_TO_LAPTOP.md, bot_state.json, batch files, fee implementations.
- [x] Read `tennis copy trade` HANDOFF.md (12 findings) + follow-list.json.
- [x] Read `weather-market-bot` docs/PHASES.md + docs/DECISIONS.md + git log.
- [x] Read PTIS (`Codex\2026-07-23\…-master-2`) experiment log + 2 backtest reports.
- [x] Confirmed the Discord trading-server export exists (176 messages, 30 Jun–29 Jul)
      and that **no code anywhere reads it**.
- [x] Located every independent fee-formula implementation (9 + 1 buffer model).
- [x] INVENTORY.md
- [x] LEDGER.md — 117 claims (C001–C117) across 6 threads
- [x] FAILURE_MODES.md — 48 instances of the 5 patterns, 16 still live on disk
- [x] GAPS.md — 5 of 6 prompt items confirmed untested, 1 refuted; 8 further gaps
- [x] STATUS.md

## Verification the audit performed itself (not just read)

- Re-read `kalshi markets/reports/arb_log.parquet`: **55 `is_arb` rows but only 2 distinct
  violation ids** — the reported "52 violations" is one KXSOLD violation re-observed 54
  times. Conclusion unaffected, count inflated ~26×.
- Confirmed the arb scanner only ever logged 5 series, all `family_kind='ladder'`, and no
  sports or bucket families at all.
- Confirmed `record_kalshi.py` tier1 and `watchlist_tier2.json` contain **zero sports
  series** — so the "record forward to test the Kalshi longshot bias" plan was not being
  served by the running recorder.
- Confirmed no process is running, no lock file, empty Startup, no scheduled tasks.
- Confirmed `synthetic_control_verdict.json` says `positive_control_detections: 2` where
  two documents say 3.
- Confirmed no script anywhere references the 11 orphan `_*.json` files in `kalshi\`.
- Confirmed no code anywhere reads the Discord export.
- Confirmed there is no `.git` anywhere under `tennis copy trade`.

## Overrides applied (from the invoking instruction)
1. Chat exports (`audit/pro_chats.json`, `audit/max_chats.json`) do not exist on this
   machine — confirmed by search. All chat-only claims are marked `PENDING (chat export)`.
2. Complete git logs of both in-scope repos walked.
3. Fully autonomous; ambiguities resolved conservatively and logged in `DECISIONS.md`.
