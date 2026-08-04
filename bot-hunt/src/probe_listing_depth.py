"""How far back does Kalshi's MARKET LISTING actually reach, per series?

This decides whether the South American soccer entry lives or dies, so it gets
its own measurement rather than an inference from one pull.

The distinction matters and has not been drawn anywhere in this repo before:

  * the TRADE TAPE (`/markets/trades`) re-bisected today reaches **71 days**,
    earliest 2026-05-25.
  * the MARKET LISTING (`/markets?series_ticker=...`) is what supplies the
    result, the strikes and the close time — without which a trade is an
    unlabelled price. Its retention is measured here.

If the listing is the shorter of the two, then the listing is the binding
constraint on any backtest, and `WHAT_IS_LEFT.md`'s framing of the tape as
"THE DECAYING ITEM" is pointed at the wrong window.

Four independent ways of asking, because a single negative could be a
parameter the endpoint silently ignores.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "reports"
SERIES = ["KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXMLSGAME", "KXATPMATCH"]


def earliest(items):
    ct = [m.get("close_time") for m in items if m.get("close_time")]
    return (min(ct), max(ct), len(items)) if ct else (None, None, len(items))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {}
    now = int(time.time())
    for s in SERIES:
        print(f"\n=== {s}")
        r = {}

        a = list(V.k_paginate("/markets",
                              {"series_ticker": s, "status": "settled",
                               "limit": 200}, "markets", max_pages=60))
        r["plain_settled"] = earliest(a)
        print(f"  status=settled          n={len(a):>5} earliest="
              f"{str(r['plain_settled'][0])[:10]}")

        # explicit lower bound, far older than any retention claim
        b = list(V.k_paginate("/markets",
                              {"series_ticker": s, "status": "settled",
                               "min_close_ts": now - 365 * 86400,
                               "max_close_ts": now, "limit": 200},
                              "markets", max_pages=60))
        r["min_close_365d"] = earliest(b)
        print(f"  +min_close_ts -365d     n={len(b):>5} earliest="
              f"{str(r['min_close_365d'][0])[:10]}")

        # a window that is ENTIRELY older than the tape boundary
        cutoff = now - 71 * 86400
        c = list(V.k_paginate("/markets",
                              {"series_ticker": s, "status": "settled",
                               "min_close_ts": now - 365 * 86400,
                               "max_close_ts": cutoff, "limit": 200},
                              "markets", max_pages=30))
        r["older_than_tape"] = earliest(c)
        print(f"  window older than tape  n={len(c):>5} earliest="
              f"{str(r['older_than_tape'][0])[:10]}")

        # no status filter at all
        d = list(V.k_paginate("/markets", {"series_ticker": s, "limit": 200},
                              "markets", max_pages=60))
        st = Counter(m.get("status") for m in d)
        r["no_status_filter"] = earliest(d)
        r["status_counts"] = dict(st)
        print(f"  no status filter        n={len(d):>5} earliest="
              f"{str(r['no_status_filter'][0])[:10]}  {dict(st)}")

        # does the EVENTS endpoint reach further than the MARKETS endpoint?
        e = list(V.k_paginate("/events",
                              {"series_ticker": s, "status": "settled",
                               "limit": 200}, "events", max_pages=30))
        ev_ct = [x.get("ticker") for x in e]
        r["events_settled_n"] = len(e)
        print(f"  /events status=settled  n={len(e):>5} "
              f"sample={ev_ct[:2]}")
        rep[s] = r

    (OUT / "listing_depth.json").write_text(json.dumps(rep, indent=1,
                                                       default=str),
                                            encoding="utf-8")
    print("\nwrote reports/listing_depth.json")


if __name__ == "__main__":
    main()
