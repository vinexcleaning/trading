"""Sweep every resolved tennis market's trade tape and score every wallet in it.

The discovery script scanned 160 markets and kept the top 60 wallets it saw. The
database holds **10,834** tennis markets, 6,937 of them resolved with a known
winner, so the previous search covered under 2% of the available evidence and
the leaderboard was built from 36 measurable wallets. That is the bottleneck --
not the ranking maths.

This inverts the approach. Fetching each wallet's full history takes minutes per
wallet and cannot scale to five figures. But a market's trade tape names every
wallet that bet in it, the price each paid, and which side they took -- and the
market record says who won. So one request per market scores every participant
at once, and the cost is per *market* rather than per wallet.

What is measured, precisely: for every BUY, did the outcome bought go on to win,
and what price was paid. Aggregated per wallet that gives the user's metric --
win rate minus average price paid, in points.

Two honest limits, both of which make this a FUNNEL rather than a verdict:

* It scores entries held to resolution. A wallet that sold early gets judged on
  a result it did not actually take. For hold-to-settlement traders (the best
  candidate found so far holds every position to resolution) it is exact; for
  scalpers it is not.
* It uses the price the WALLET paid, not the price a follower pays after copy
  delay. Copier edge still needs the deep backfill, which is why the output of
  this script is a shortlist to backfill, not a follow list.

Resumable: progress is kept in its own database, so interrupting and re-running
picks up where it stopped and never re-fetches a market.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/sweep_tennis_tape.py
    ... scripts/sweep_tennis_tape.py --limit 500 --max-pages 2
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import session_scope  # noqa: E402
from app.models import Market, Outcome  # noqa: E402
from app.providers import PolymarketProvider  # noqa: E402

STARTED = time.time()
DEFAULT_STORE = REPO_ROOT / "data" / "tape_scan.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS scanned_markets (
    condition_id TEXT PRIMARY KEY,
    trades       INTEGER NOT NULL,
    buys         INTEGER NOT NULL,
    scanned_at   INTEGER NOT NULL,
    error        TEXT
);
CREATE TABLE IF NOT EXISTS tape_bets (
    wallet       TEXT    NOT NULL,
    condition_id TEXT    NOT NULL,
    ts           INTEGER NOT NULL,
    price        REAL    NOT NULL,
    size         REAL    NOT NULL,
    won          INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tape_wallet ON tape_bets(wallet);
CREATE INDEX IF NOT EXISTS ix_tape_ts ON tape_bets(ts);
"""


def log(message: str) -> None:
    print(f"[{time.time() - STARTED:8.1f}s] {message}", flush=True)


def open_store(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    # Durability matters less than throughput here: the scan is resumable and
    # re-fetching a handful of markets after a crash costs seconds.
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.commit()
    return conn


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", type=Path, default=DEFAULT_STORE)
    p.add_argument("--limit", type=int, help="stop after this many markets")
    p.add_argument("--max-pages", type=int, default=3, help="tape pages per market")
    args = p.parse_args()

    store = open_store(args.store)
    done = {r[0] for r in store.execute("SELECT condition_id FROM scanned_markets")}

    with session_scope() as session:
        # Resolved markets only -- an unresolved one has no winner to score
        # against. Newest first so an interrupted run still covers current form.
        markets = session.execute(
            select(Market.id, Market.condition_id, Market.winning_outcome_index)
            .where(
                Market.is_tennis.is_(True),
                Market.resolved.is_(True),
                Market.winning_outcome_index.is_not(None),
                Market.condition_id.is_not(None),
            )
            .order_by(Market.id.desc())
        ).all()
        # token_id -> outcome_index, so a tape row can be scored even when the
        # provider omits outcomeIndex.
        token_index = {
            t: i
            for t, i in session.execute(select(Outcome.token_id, Outcome.outcome_index)).all()
        }

    pending = [m for m in markets if m[1] not in done]
    if args.limit:
        pending = pending[: args.limit]

    log(
        f"{len(markets)} resolved tennis markets | {len(done)} already scanned | "
        f"{len(pending)} to go"
    )
    if not pending:
        log("Nothing to do. Rank with: python scripts/rank_tape.py")
        return 0

    provider = PolymarketProvider()
    total_bets = 0
    errors = 0
    try:
        for index, (_mid, condition_id, winner_idx) in enumerate(pending, start=1):
            try:
                trades = provider.get_market_trades(
                    condition_id, limit=1000, max_pages=args.max_pages
                )
            except Exception as exc:  # noqa: BLE001
                errors += 1
                store.execute(
                    "INSERT OR REPLACE INTO scanned_markets VALUES (?,?,?,?,?)",
                    (condition_id, 0, 0, int(time.time()), str(exc)[:200]),
                )
                store.commit()
                continue

            rows = []
            for t in trades:
                # Only entries. A SELL is an exit, and scoring it as a fresh bet
                # would double-count the position and invert its result.
                if (t.side or "").upper() != "BUY":
                    continue
                if not t.wallet_address:
                    continue
                idx = t.outcome_index
                if idx is None:
                    idx = token_index.get(t.token_id)
                if idx is None:
                    continue
                price = float(t.price)
                # Prices outside (0,1) are data errors, not free money.
                if not 0.0 < price < 1.0:
                    continue
                rows.append((
                    t.wallet_address, condition_id, t.timestamp, price,
                    float(t.size or 0), 1 if idx == winner_idx else 0,
                ))

            if rows:
                store.executemany(
                    "INSERT INTO tape_bets VALUES (?,?,?,?,?,?)", rows
                )
            store.execute(
                "INSERT OR REPLACE INTO scanned_markets VALUES (?,?,?,?,?)",
                (condition_id, len(trades), len(rows), int(time.time()), None),
            )
            store.commit()
            total_bets += len(rows)

            if index % 50 == 0 or index == len(pending):
                wallets = store.execute(
                    "SELECT COUNT(DISTINCT wallet) FROM tape_bets"
                ).fetchone()[0]
                rate = index / max(1e-9, time.time() - STARTED)
                eta = (len(pending) - index) / rate / 60 if rate > 0 else 0
                log(
                    f"{index}/{len(pending)} markets | {total_bets:,} bets | "
                    f"{wallets:,} wallets | {errors} errors | ~{eta:.0f} min left"
                )
    finally:
        provider.close()
        store.commit()
        store.close()

    log(f"done -- {total_bets:,} bets recorded, {errors} markets failed")
    log("Rank with: python scripts/rank_tape.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
