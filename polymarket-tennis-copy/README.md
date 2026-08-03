# Tennis Copy-Trade Intelligence

Analytics for publicly visible Polymarket wallets trading tennis markets.

The question this answers is **not** *"did this wallet make money?"* It is:

> Could a realistic follower have identified, entered and exited these tennis
> trades in time, and still been profitable after delay, price deterioration,
> liquidity constraints, fees and slippage?

Those are very different questions, and the gap between them is where most
copy-trading ideas quietly die. A wallet in the bundled demo data has a **37.6%**
raw ROI and a **19.7%** copyable ROI — half its edge is gone by the time anyone
could follow it, and its live signals are correctly rejected.

> **This is an analytical tool, not financial advice.** Historical results do not
> guarantee future performance. Public wallet activity can be misleading. Paper
> trading may differ materially from real execution. Users must comply with all
> applicable laws, platform rules, age requirements and geographic restrictions.

**This version cannot place real orders.** There is no order-placement code path
and no signing key anywhere in the system. Paper trading is simulation only.

---

## Quick start

Requires Python 3.12+ and Node 20+.

```bash
python -m venv .venv && .venv/Scripts/activate     # Windows
# python3 -m venv .venv && source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

Seed a demo database and run the whole pipeline over it:

```bash
DATABASE_URL="sqlite:///./data/demo.db" python scripts/seed_demo.py --reset
```

Start the API:

```bash
DATABASE_URL="sqlite:///./data/demo.db" uvicorn app.main:app --app-dir backend --reload
```

Start the dashboard in a second terminal:

```bash
npm install --prefix frontend && npm run dev --prefix frontend
```

Open <http://localhost:5173>. API docs are at <http://localhost:8000/docs>.

### With Docker

```bash
cp .env.example .env && docker compose up --build
```

Brings up Postgres, runs migrations, starts the API on `:8000` and the dashboard
on `:5173`.

> Docker was not installed in the environment this was built in, so the compose
> stack is **written but unverified end to end**. The local (non-Docker) path
> above is the one that has actually been run. If the build fails, that is the
> first place to look.

---

## Using it against real data

The demo database is synthetic. To track real wallets:

```bash
# Use a real database, not the demo one.
export DATABASE_URL="sqlite:///./data/tennis_copy_trade.db"
alembic upgrade head
```

Then either use the dashboard's **Wallets** page, or:

```bash
curl -X POST localhost:8000/api/wallets -H 'content-type: application/json' \
  -d '{"address":"0xYOUR_WALLET_ADDRESS","nickname":"candidate"}'

# Or discover candidates from recent public tennis-market activity:
curl -X POST "localhost:8000/api/wallets/discover?source=tennis_markets"

# Or import data/sample_wallets.csv (replace the placeholder addresses first).
```

Nothing is trusted automatically. A discovered wallet arrives unapproved and
unscored, and cannot produce a signal until it has been synced and analysed.

Then let the scheduler work, or force the sequence:

```bash
curl -X POST localhost:8000/api/jobs/market_sync/run     # tennis markets
curl -X POST localhost:8000/api/jobs/wallet_sync/run     # wallet history
curl -X POST localhost:8000/api/jobs/price_backfill/run  # price evidence
curl -X POST localhost:8000/api/jobs/analytics/run       # metrics + scores
curl -X POST localhost:8000/api/jobs/signal_scan/run     # signals
```

**Run `price_backfill` before `analytics`.** Copyable ROI only counts trades
backed by real price evidence, so scoring un-backfilled markets reports every
wallet as unassessable regardless of skill.

---

## Running tests

```bash
python -m pytest                 # full suite, no network required
python -m pytest -q --tb=short   # quieter
python -m pytest backend/tests/test_metrics_scoring.py -k luck   # one area
```

293 tests. Every upstream call is mocked with `respx`; the suite never touches
the network and never needs a live database.

Frontend:

```bash
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

---

## What it does

1. **Discovers or accepts** wallet addresses (manual, CSV, leaderboard, or
   observed tennis-market activity). Never auto-trusts any of them.
2. **Ingests** public activity with pagination, retries, pacing, idempotent
   writes and schema-drift detection.
3. **Classifies** tennis markets by official sports metadata, tags, event data,
   title parsing and keyword rules — with a confidence score. Ambiguous markets
   go to a review queue instead of being silently trusted.
4. **Reconstructs** positions from raw activity: entries, adds, partial exits,
   full exits, reversals, settlement, weighted-average entry, FIFO P&L.
5. **Reconstructs historical prices** at nine follower delays, tiered by evidence
   quality, and refuses to invent numbers it cannot support.
6. **Scores copyability** per trade from execution realism alone.
7. **Computes tennis-specific metrics** and an explainable
   [Adjusted Tennis Skill Score](docs/SCORING.md).
8. **Detects related wallets** so three addresses run by one person cannot pose
   as three independent confirmations.
9. **Qualifies signals** against strict, configurable gates — and keeps every
   rejection with its reason.
10. **Paper-trades** qualifying signals with conservative risk controls.
11. **Backtests** with chronological train/validation/test splits and an
    auditable look-ahead guard.

---

## The pages

| Page | What it shows |
|---|---|
| **Overview** | Tracked/qualified wallets, median copyable ROI, active and rejected signals, paper P&L, drawdown, data freshness and quality warnings |
| **Signal feed** | Live SSE feed of every candidate — qualified *and* rejected — expandable to the full check-by-check qualification table, contributing wallets, and which ones were suppressed as cluster duplicates |
| **Paper trading** | Simulated positions, risk-limit usage, refused entries with reasons, and the measured cost of following |
| **Leaderboard** | 14 separate rankings rather than one misleading list. Raw ROI beside copyable ROI beside shrunk ROI, with coverage, drawdown, confidence and risk flags |
| **Wallet detail** | Raw-vs-copyable headline, full score breakdown with every component and penalty, delay-decay curve, equity curve, behavioural profile, cluster relationships, per-position copyability with evidence tiers |
| **Markets** | Tennis markets with classification confidence, plus the review queue for ambiguous ones |
| **Market detail** | Price history per outcome with wallet buys/sells overlaid, depth near touch vs total, tracked positions, alert history including rejections |
| **Backtesting** | Full configuration, in-sample/validation/out-of-sample split results, equity and drawdown curves, delay sensitivity, skip reasons, trade log |
| **System health** | Job status with manual triggers, freshness, price-evidence mix, pipeline coverage, warnings |
| **Settings** | Every threshold, editable at runtime. Credentials are structurally unreachable |

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — layering, pipeline, jobs, precision
- [Scoring](docs/SCORING.md) — the skill score formula, shrinkage, penalties
- [Copyability](docs/COPYABILITY.md) — price evidence tiers and the delay model
- [Paper trading](docs/PAPER_TRADING.md) — fill assumptions and risk controls
- [Findings](docs/FINDINGS.md) — **what the real scans actually found** (no copyable edge, and why)
- [Data limitations](docs/DATA_LIMITATIONS.md) — **read this before trusting any number**
- OpenAPI: <http://localhost:8000/docs>

---

## Design commitments

**Skeptical by default.** Profit is not skill; volume is not edge; a visible
entry price is not an available one; multiple wallets are not multiple opinions.

**Refuse rather than guess.** Polymarket's price history bottoms out at 1-minute
fidelity, so it *cannot* answer "what was the price 15 seconds later". Where the
second-level trade tape is silent, copyable ROI reads `n/a` and says why. Every
price carries the tier of evidence behind it, and modelled prices are excluded
from headline figures rather than averaged in.

**Rejections are a product surface.** Every candidate signal is stored with the
specific checks it failed. That log is how thresholds get calibrated; hiding it
would leave the gates unfalsifiable.

**Small samples are shrunk, not disclaimed.** Eight lucky wins scoring 51 against
a 121-trade grinder's 80 is arithmetic, not a warning label. Under-sampled
wallets are also excluded from rankings that read as recommendations, and appear
under "Emerging" instead.

**Related wallets count once.** Consensus counts opinions, not addresses.

---

## What is deliberately not built

- **Real-money execution.** Out of scope for v1 by design.
- **Geographic-restriction circumvention**, proxy evasion, credential collection,
  or any scraping that violates platform terms. The system uses documented public
  endpoints only, with conservative self-imposed pacing.
- **Guaranteed-profit language.** Alerts never say "lock", "risk-free" or
  "can't lose", and the alert builder has no such vocabulary.

## Future work

Additional venues; live tennis score feeds and match-state analysis;
player/surface models; sportsbook odds comparison; calibrated ML probability
models to replace the current transparent heuristic edge estimate; wallet graph
analysis using funding sources; multi-user accounts and shared watchlists; a
mobile client.

Real execution should not be built without separate review of legality, platform
compliance, safety controls and explicit user authorisation.
