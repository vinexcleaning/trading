"""Map what the PMXT Kalshi archive actually still serves, hour by hour.

**Why this exists, and why it is urgent.** The operator posted on
**2026-07-31** that he had been *asked* to shut `archive.pmxt.dev` down "this
week". Kalshi's own API is a ~69-day window and closed markets 404 for good, so
every hour on that host that we do not copy is **permanently unrecoverable** —
not "re-pullable later".

**The index page cannot be trusted to tell us what is there.** It is a
single-page app that paginates: on 2026-08-11 it listed 2026-06-09 to 06-11,
while the 312 hours we already hold are 2026-05-15 to 05-27. Neither listing
mentions the other. So the only honest inventory is to **ask the file host
directly for each hour**, which is what this does.

Two passes, because probing every hour blind would be 24x more requests than
needed:

  1. one probe per DAY across the range, to find which days exist at all
  2. all 24 hours only for the days that answered

Uses HEAD, so nothing is downloaded. Paced, and it stops on repeated errors
rather than hammering a host whose operator is already under pressure.

    python src/archive_inventory.py --venue kalshi --from 2026-03-01 --to 2026-08-11
    python src/archive_inventory.py --venue polymarket --from 2026-02-01 --to 2026-08-13

**The Polymarket host was found late and by accident**, which is worth
recording. `signal-github/data/github.db` has carried a curated `data_sources`
row all along — *"Polymarket historical L2 order book, free,
https://r2v2.pmxt.dev, hourly archive from 2026-02-21 onward"*. The shutdown
news lived in the Reddit corpus; the host lived in the GitHub corpus; **nobody
joined them.** That join is what the cross-corpus work was built for and it did
not fire, because it matches tool *names*, not hostnames.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.request

VENUES = {
    # verified by fetching on 2026-08-13: both return PAR1 magic bytes
    "kalshi": ("https://r2kalshi.pmxt.dev",
               "kalshi_orderbook_{d}T{h:02d}.parquet"),
    "polymarket": ("https://r2v2.pmxt.dev",
                   "polymarket_orderbook_{d}T{h:02d}.parquet"),
}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (research inventory; contact via github)"}

# Set by main() from --venue. Module-level so the helpers stay simple, but
# never defaulted to one venue -- defaulting is how a Polymarket run would
# silently inventory Kalshi and report a confident wrong answer.
HOST = NAME = HAVE_DIR = OUT = None


def use_venue(venue: str) -> None:
    global HOST, NAME, HAVE_DIR, OUT
    HOST, NAME = VENUES[venue]
    HAVE_DIR = os.path.join(ROOT, "data", f"{venue}_archive")
    OUT = os.path.join(ROOT, "reports", f"ARCHIVE_INVENTORY_{venue}.json")


def head(url: str, timeout: int = 30):
    """Return (status, content-length) without downloading the body."""
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, int(r.headers.get("content-length") or 0)
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception:
        return None, 0


def held_hours() -> set[str]:
    if not os.path.isdir(HAVE_DIR):
        return set()
    out = set()
    for f in os.listdir(HAVE_DIR):
        m = re.search(r"(\d{4}-\d{2}-\d{2})T(\d{2})", f)
        if m:
            out.add(m.group(0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", choices=sorted(VENUES), required=True)
    ap.add_argument("--from", dest="d0", default="2026-03-01")
    ap.add_argument("--to", dest="d1", default="2026-08-11")
    ap.add_argument("--pace", type=float, default=0.35)
    args = ap.parse_args()
    use_venue(args.venue)
    print(f"venue {args.venue}: {HOST}/{NAME.format(d='YYYY-MM-DD', h=0)}\n")

    d0 = dt.date.fromisoformat(args.d0)
    d1 = dt.date.fromisoformat(args.d1)
    have = held_hours()
    print(f"we already hold {len(have)} hours locally\n")

    # pass 1 -- which days exist at all
    print(f"pass 1: probing one hour per day, {d0} .. {d1}")
    live_days, consecutive_err = [], 0
    d = d0
    while d <= d1:
        ds = d.isoformat()
        st, n = head(f"{HOST}/{NAME.format(d=ds, h=12)}")
        if st is None:
            consecutive_err += 1
            if consecutive_err >= 8:
                print("  8 network errors in a row -- stopping, not hammering")
                break
            time.sleep(4)
        else:
            consecutive_err = 0
            if st == 200:
                live_days.append(ds)
                print(f"  {ds}  12:00 present  ({n / 1e6:.0f} MB)")
        d += dt.timedelta(days=1)
        time.sleep(args.pace)

    print(f"\npass 1 found {len(live_days)} days with a midday file")

    # pass 2 -- full hours for the days that answered. Also probe the days
    # either side, because a day can exist with a gap at noon.
    span = set()
    for ds in live_days:
        base = dt.date.fromisoformat(ds)
        for off in (-1, 0, 1):
            span.add((base + dt.timedelta(days=off)).isoformat())
    for ds in sorted({h[:10] for h in have}):
        span.add(ds)

    print(f"\npass 2: all 24 hours for {len(span)} days")
    inv: dict[str, dict] = {}
    for ds in sorted(span):
        hours = []
        for h in range(24):
            key = f"{ds}T{h:02d}"
            if key in have:
                hours.append({"h": h, "status": "HELD"})
                continue
            st, n = head(f"{HOST}/{NAME.format(d=ds, h=h)}")
            if st == 200:
                hours.append({"h": h, "status": "AVAILABLE", "bytes": n})
            time.sleep(args.pace)
        got = [x for x in hours if x["status"] == "AVAILABLE"]
        held = [x for x in hours if x["status"] == "HELD"]
        if got or held:
            inv[ds] = {"available_not_held": len(got), "held": len(held),
                       "bytes": sum(x.get("bytes", 0) for x in got),
                       "hours": hours}
            print(f"  {ds}  held {len(held):>2}  new {len(got):>2}  "
                  f"{sum(x.get('bytes', 0) for x in got) / 1e9:.2f} GB to fetch")

    total_new = sum(v["available_not_held"] for v in inv.values())
    total_gb = sum(v["bytes"] for v in inv.values()) / 1e9
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"host": HOST, "probed_utc": dt.datetime.now(
            dt.timezone.utc).isoformat(), "held": len(have),
            "available_not_held": total_new, "gb": round(total_gb, 2),
            "days": inv}, fh, indent=1)
    print(f"\n  HELD {len(have)} hours | AVAILABLE AND NOT HELD {total_new} "
          f"hours ({total_gb:.1f} GB raw)")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
