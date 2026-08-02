"""TASK 2 / dimension A — THE KILL SWITCH. Does a counterparty exist?

Pulls the exchange-wide public trade tape backwards over a window and
aggregates by series. This is the measurement that decides everything else: a
prior study found weather markets with perfect free settlement data and ZERO
fills. No counterparty means no trade at any edge size.

Unit of observation is the TRADE, but the number that matters per family is
trades per day and distinct markets traded per day -- 5,000 trades in one
market is not the same market as 5,000 trades across 500.

Read-only, paced, public endpoint. No credentials.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 48


def main():
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=HOURS)
    min_ts, max_ts = int(start.timestamp()), int(end.timestamp())
    print(f"pulling exchange-wide tape {start:%Y-%m-%d %H:%M} .. {end:%Y-%m-%d %H:%M} UTC")

    path = os.path.join(DATA, f"kalshi_trades_{HOURS}h.jsonl")
    n, pages, t0 = 0, 0, time.time()
    oldest, newest = None, None
    with open(path, "w", encoding="utf-8") as fh:
        for t in K.paginate("/markets/trades",
                            {"limit": 1000, "min_ts": min_ts, "max_ts": max_ts},
                            "trades"):
            fh.write(json.dumps(t) + "\n")
            n += 1
            ct = t.get("created_time")
            if ct:
                oldest = ct if oldest is None or ct < oldest else oldest
                newest = ct if newest is None or ct > newest else newest
            if n % 25000 == 0:
                pages = n // 1000
                print(f"  {n} trades, {pages} pages, {time.time()-t0:.0f}s, "
                      f"oldest={oldest}", flush=True)
    print(f"\ntrades pulled: {n}  elapsed {time.time()-t0:.0f}s")
    print(f"actual span in data: {oldest} .. {newest}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
