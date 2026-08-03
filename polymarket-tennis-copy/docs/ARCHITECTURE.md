# Architecture

## Shape

A single FastAPI process serving the API and running scheduled jobs in-process
via APScheduler, plus a React SPA. No message broker, no worker fleet, no
microservices — this is a single-operator analytics tool, and a Celery broker
would add failure modes without buying anything at this scale.

```
                    ┌─────────────────────────────────────────┐
  Polymarket        │  FastAPI process                        │
  public APIs       │                                         │
  ┌──────────┐      │  ┌───────────┐      ┌────────────────┐  │
  │ Gamma    │─────▶│  │ providers │─────▶│ services       │  │
  │ Data API │      │  │ (HTTP,    │      │ (pure logic)   │  │
  │ CLOB     │      │  │  retries, │      │                │  │
  │ lb-api   │      │  │  pacing)  │      │ classification │  │
  └──────────┘      │  └───────────┘      │ reconstruction │  │
                    │                     │ prices         │  │
                    │  ┌───────────┐      │ copyability    │  │
                    │  │ APScheduler│─────▶│ metrics       │  │
                    │  │ jobs       │     │ scoring        │  │
                    │  └───────────┘      │ clustering     │  │
                    │                     │ signals        │  │
                    │  ┌───────────┐      │ paper          │  │
                    │  │ api/routes│◀────▶│ backtest       │  │
                    │  └───────────┘      └────────┬───────┘  │
                    │        │                     │          │
                    │        │            ┌────────▼───────┐  │
                    │        │            │ SQLAlchemy ORM │  │
                    │        │            └────────┬───────┘  │
                    └────────┼─────────────────────┼──────────┘
                             │                     │
                       React SPA            SQLite / Postgres
                       (Vite, SSE)
```

## Layering rule

The `services/` package contains **pure logic that never touches the database**.
`SignalEngine`, `PaperTradingEngine`, `Backtester`, `TennisClassifier`, the
copyability model and the statistics all take plain dataclasses and return plain
dataclasses.

Two modules exist purely to bridge them to storage:

- `services/monitor.py` — feeds live state to the signal engine and paper engine,
  persists their decisions.
- `services/backtest_runner.py` — loads historical candidates and persists results.

This is why the suite has 286 tests with no network and no fixtures database for
the decision logic: the parts that decide anything are directly unit-testable.

## Pipeline stages

Each stage persists its output, so stages are independently re-runnable and a
failure never leaves a half-computed derived table.

```
ingest ──▶ classify ──▶ reconstruct ──▶ price/copyability
                                              │
                     ┌────────────────────────┘
                     ▼
              metrics ──▶ score ──▶ cluster ──▶ signal ──▶ alert ──▶ paper
```

**Ordering is load-bearing.** Price backfill must precede metrics: copyable ROI
only counts trades with real price evidence, so scoring un-backfilled markets
produces "unassessable" for every wallet regardless of skill.

## Background jobs

| Job | Default interval | Purpose |
|---|---|---|
| `market_sync` | 15 min | Tennis events, markets, outcomes from Gamma |
| `wallet_sync` | 5 min | Incremental wallet activity |
| `signal_scan` | 30 s | Evaluate recent qualified-wallet entries |
| `paper_manage` | 60 s | Mark open simulated positions, apply exit rules |
| `price_backfill` | 15 min | Trade prints and minute bars for held markets |
| `analytics` | 30 min | Reconstruct, score copyability, metrics, scores, clusters |
| `data_quality` | 1 h | Snapshot for the health panel |
| `daily_summary` | 23:55 UTC | Paper-trading summary notification |
| `retention` | 03:15 UTC | Prune raw payloads past retention |

Every job records its own `ingestion_jobs` row with HTTP counters attributed to
that job (deltas, not lifetime totals), swallows its own exceptions, and reports
failures through the notification dispatcher.

## Data-source layer

`MarketDataProvider` is an ABC; `PolymarketProvider` is the only implementation.
Swapping venues means writing one class. The HTTP client provides:

- Self-imposed pacing (Polymarket publishes no rate-limit headers, so the client
  throttles conservatively rather than probing for the ceiling)
- Exponential backoff with full jitter, retrying only transient statuses
- 404 handling that distinguishes "missing, and that's fine" from "missing, and
  that's an error"
- Per-job request/retry/rate-limit counters
- Schema-drift detection on every payload shape

Raw responses are stored alongside normalised rows for reproducibility, subject
to a retention window.

## Precision

Money and prices are `Decimal` end to end. SQLite has no native DECIMAL, so a
custom `SqliteSafeNumeric` stores values as TEXT and parses them back, keeping
P&L exact on both backends. A `UtcDateTime` type guarantees every datetime
leaving the database is timezone-aware UTC — SQLite otherwise returns naive
datetimes, which raise on comparison with aware ones at whichever call site
happens to touch them first.

## Frontend

React 18 + TypeScript + Vite. No component library and no charting dependency —
charts are hand-rolled SVG, which keeps the bundle at ~80 kB gzipped and avoids
styling fights. The live feed uses server-sent events with polling underneath,
so a dropped stream degrades to slower updates rather than a blank page.

## Database

31 tables. SQLite by default (WAL enabled so the scheduler writes while the API
reads), Postgres via `DATABASE_URL`. Alembic migrations are verified in CI-style
tests: a test applies the migration to a temp database and asserts
`compare_metadata` finds zero drift against the models.
