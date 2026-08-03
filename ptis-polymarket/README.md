# Polymarket Trader Intelligence and Shadow Copy System

PTIS is a research-only system for testing whether public Polymarket trades can
be copied profitably after realistic delay, spread, fees, slippage, liquidity,
and small-bankroll constraints.

It does **not** place orders, manage private keys, or recommend real-money
trading. The initial phase only collects public data and creates paper-trading
evidence.

## Current status

Phase 0/1 is complete. The first ingestion slice creates a SQLite database,
downloads public leaderboard candidates, and archives current order books with
both source timestamps and ingestion timestamps.

## Quick start

Use Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
ptis init-db
ptis discover --limit 50
ptis snapshot-book --token-id TOKEN_ID
```

The database defaults to `data/processed/ptis.sqlite3`. Raw responses are saved
under `data/raw/` and are never silently overwritten.

## Commands

- `ptis init-db` — create the database schema.
- `ptis discover` — save a point-in-time leaderboard candidate cohort.
- `ptis ingest-trades --wallet 0x...` — archive a bounded, overlap-safe public
  trade history for one candidate.
- `ptis snapshot-book --token-id ...` — save a public CLOB order-book snapshot.
- `ptis ingest-markets` — resolve traded conditions, outcomes, and current fee schedules.
- `ptis rebuild-positions --wallet 0x...` — reconstruct observed inventory.
- `ptis assess-trader --wallet 0x...` — calculate a behavior-only preliminary score.
- `ptis validate-data` — save automated data-quality findings.
- `ptis shadow-scan` — run a bounded current-market paper scan; never places orders.
- `ptis report` — generate the current research status report.
- `ptis monitor --wallet 0x...` — baseline a wallet, detect genuinely new
  public trades on later polls, measure first-seen delay, and paper-evaluate
  each signal once.
- `ptis settle-paper` — settle open paper positions after an archived official
  market outcome becomes available.
- `ptis evaluate-pending` — resume bounded paper evaluation of prospectively
  observed trades not yet included in any completed run.
- `ptis prepare-history --wallet 0x...` — archive bounded market-wide trade
  tapes for the selected one-week replay.
- `ptis backtest-week --wallet 0x...` — run the 0/5/15/60-second and
  0/1/2-cent sensitivity matrix with hold-to-resolution settlement.
- `ptis prepare-consensus --category CRYPTO` — archive a category-leader
  cohort, its public histories, and bounded trade tapes for shared outcomes.
- `ptis backtest-consensus --category CRYPTO` — run the specialist-consensus
  matrix with equal wallet votes, a past-only directional gate, conflicting
  outcome rejection, and delayed stressed paper fills.

## Data sources

- Gamma API: markets, events, tags, and resolution metadata.
- Data API: public trades, positions, activity, holders, and leaderboards.
- CLOB API: current order books, prices, spreads, and sampled price history.
- CLOB market WebSocket: future live order-book and trade-event collection.

All collected records identify their source and UTC ingestion time. Current
leaderboards must never be used to select wallets in an earlier historical
backtest.

## Important limitations

Official sampled price history is not historical level-2 order-book history.
It cannot prove the price or depth a follower could have executed against after
a past signal. Realistic tests therefore require order books collected
prospectively, or a separately licensed historical source that is validated
against official data.

Public wallet activity cannot reveal off-platform hedges, every related wallet,
or a person's full strategy. Leaderboard P&L is a discovery signal, not proof of
skill or copyability.

## Legal and platform restrictions

This project is educational research and paper trading only. Do not bypass age,
identity, location, or platform restrictions. No real-money execution component
is included.
