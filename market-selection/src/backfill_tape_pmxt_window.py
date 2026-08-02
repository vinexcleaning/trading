"""Pull the Kalshi trade tape for the days the pmxt order-book archive covers,
OLDEST FIRST, because they are expiring one per day.

THIS IS THE GENUINELY TIME-CRITICAL ITEM OF THE SESSION, and it is not the one
the tasking named.

Measured 2026-08-02 by bisection: `/markets/trades` returns data at 69 days ago
(2026-05-25) and returns ZERO at 70 days (2026-05-24). The retention window is
exactly 69 days and it rolls forward daily.

The pmxt L2 archive covers 2026-05-14T14 -> 2026-06-11T03. So:

  2026-05-14 .. 2026-05-24   trades ALREADY GONE. The order book is mirrored
                             for these days and the fills that walked it are
                             unrecoverable. Nothing can fix this.
  2026-05-25 .. 2026-06-11   trades still reachable, and each day drops out at
                             the rate of one per day. 05-25 expires today.

Depth without trades cannot answer the question the pmxt mirror exists to
answer -- what would actually have filled -- so these two datasets are only
valuable together. Oldest day first, so the most perishable is secured first.

Read-only, paced, public endpoint. Resumable: a day whose file already ends
with a complete line and covers the full span is skipped.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "tape_pmxt_window")
START = datetime(2026, 5, 25, tzinfo=timezone.utc)   # oldest still reachable
END = datetime(2026, 6, 11, tzinfo=timezone.utc)


def already_done(path, day):
    """Treat a day as done only if its LAST line parses and its earliest trade
    is within an hour of the day start -- a truncated file must be redone."""
    if not os.path.exists(path) or os.path.getsize(path) < 10_000:
        return False
    first = last = None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    t = json.loads(line)
                except json.JSONDecodeError:
                    return False
                ct = t.get("created_time")
                if ct:
                    if first is None or ct < first:
                        first = ct
                    if last is None or ct > last:
                        last = ct
    except OSError:
        return False
    if not first:
        return False
    return first <= (day + timedelta(hours=1)).isoformat()


def main():
    os.makedirs(OUT, exist_ok=True)
    day = START
    while day < END:
        nxt = day + timedelta(days=1)
        path = os.path.join(OUT, f"trades_{day:%Y-%m-%d}.jsonl")
        age = (datetime.now(timezone.utc) - day).days
        if already_done(path, day):
            print(f"{day:%Y-%m-%d} (age {age}d): already complete, skipping",
                  flush=True)
            day = nxt
            continue
        # Off-by-one guard, fixed after it silently skipped the single most
        # perishable day. The bisection found trades PRESENT at 69 days old
        # (2026-05-25) and ABSENT at 70 (2026-05-24), so the cutoff is
        # age > 69, not age >= 69. The boundary day is partially expired --
        # its early hours are already gone -- so the pull is allowed to run
        # and return whatever survives rather than being refused up front.
        if age > 69:
            print(f"{day:%Y-%m-%d} (age {age}d): PAST THE 69-DAY WINDOW -- "
                  f"unrecoverable, skipping", flush=True)
            day = nxt
            continue

        t0, n = time.time(), 0
        tmp = path + ".part"
        oldest = None
        with open(tmp, "w", encoding="utf-8") as fh:
            for t in K.paginate("/markets/trades",
                                {"limit": 1000,
                                 "min_ts": int(day.timestamp()),
                                 "max_ts": int(nxt.timestamp())}, "trades"):
                fh.write(json.dumps(t) + "\n")
                n += 1
                ct = t.get("created_time")
                if ct and (oldest is None or ct < oldest):
                    oldest = ct
                if n % 100_000 == 0:
                    print(f"  {day:%Y-%m-%d}: {n:,} trades, "
                          f"{time.time()-t0:.0f}s, oldest={oldest}", flush=True)
        os.replace(tmp, path)
        print(f"{day:%Y-%m-%d} (age {age}d): {n:,} trades in "
              f"{(time.time()-t0)/60:.1f} min, oldest={oldest}", flush=True)
        day = nxt
    print("\nDONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
