"""Census the completed Kalshi tennis archive: hours, gaps, matches, coverage.

**Why a census and not a sample.** The first pass over this archive read 26 rows
and concluded the snapshots were empty and the book could not be anchored. A
full census found 92% populated. That mistake is why this file exists: **every
number below is counted over every row, never estimated from a sample.**

**And why "distinct matches" is reported twice.** The archive snapshots markets
that are long settled — a file recorded on 2026-05-27 carries
`KXATPMATCH-26JAN03SACKYP` with an empty book on both sides. Counting every
ticker that appears would inflate the match count with January matches nobody
can trade. So two numbers are reported:

  SEEN        every distinct match whose ticker appears at all
  WITH A BOOK every distinct match that had a real quote at some point

**The second is the one any study should use.** The first is bookkeeping.

    python src/archive_census.py
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

ARCH = os.path.join(db.DATA, "kalshi_archive")
OUT = os.path.join(db.REPORTS, "ARCHIVE_CENSUS.json")
KEY = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2})")
# KXATPMATCH-26JAN03SACKYP-KYP -> match is everything before the final segment,
# which names which side of the match the contract pays on.
MATCH_OF = re.compile(r"^(KX(?:ATP|WTA)MATCH-[^-]+)")


def main():
    import pyarrow.parquet as pq

    files = sorted(f for f in os.listdir(ARCH) if f.endswith(".parquet"))
    print(f"{len(files)} hourly files in {ARCH}\n")

    hours = {f"{m.group(1)}T{m.group(2)}"
             for f in files if (m := KEY.search(f))}
    days = sorted({h[:10] for h in hours})
    print(f"covering {len(days)} days, {days[0]} .. {days[-1]}")

    d0 = dt.datetime.strptime(min(hours), "%Y-%m-%dT%H")
    d1 = dt.datetime.strptime(max(hours), "%Y-%m-%dT%H")
    want, t = [], d0
    while t <= d1:
        want.append(t.strftime("%Y-%m-%dT%H"))
        t += dt.timedelta(hours=1)
    missing = sorted(set(want) - hours)
    print(f"{len(hours)} hours held of {len(want)} in the span "
          f"-> {len(missing)} gap(s)")
    if missing:
        print("  gaps:", missing[:24])

    rows = 0
    seen: set[str] = set()
    with_book: set[str] = set()
    live_per_day: dict[str, set] = collections.defaultdict(set)
    events = collections.Counter()
    series = collections.Counter()
    rows_with_book = 0

    for i, f in enumerate(files, 1):
        day = KEY.search(f).group(1)
        try:
            pf = pq.ParquetFile(os.path.join(ARCH, f))
        except Exception as e:  # noqa: BLE001
            print(f"  !! unreadable: {f}  {type(e).__name__}: {e}")
            continue
        for batch in pf.iter_batches(
                batch_size=200_000,
                columns=["market_ticker", "event_type", "yes_bids", "no_bids"]):
            d = batch.to_pydict()
            tk, ev = d["market_ticker"], d["event_type"]
            yb, nb = d["yes_bids"], d["no_bids"]
            rows += len(tk)
            for j, t_ in enumerate(tk):
                if not t_:
                    continue
                events[ev[j]] += 1
                series[t_.split("-", 1)[0]] += 1
                m = MATCH_OF.match(t_)
                if not m:
                    continue
                key = m.group(1)
                seen.add(key)
                # a real quote on either side counts as a live book
                if (yb[j] and len(yb[j])) or (nb[j] and len(nb[j])):
                    rows_with_book += 1
                    with_book.add(key)
                    live_per_day[day].add(key)
        if i % 150 == 0:
            print(f"  ...{i}/{len(files)} files, {rows:,} rows, "
                  f"{len(with_book):,} matches with a book", flush=True)

    print(f"\n{'=' * 72}")
    print(f"  hourly files                    {len(files):>14,}")
    print(f"  rows                            {rows:>14,}")
    print(f"  distinct matches SEEN           {len(seen):>14,}")
    print(f"  distinct matches WITH A BOOK    {len(with_book):>14,}   "
          f"<- use this one")
    # **The denominator here is SNAPSHOTS, not rows, and getting that wrong
    # produced a scary and meaningless number the first time this ran.**
    # 99.9% of rows are `orderbook_delta`, which carry `price`/`delta`/`side`
    # and leave `yes_bids`/`no_bids` empty by design — the book is rebuilt by
    # applying deltas to the last snapshot. Dividing populated books by ALL
    # rows said "0.1% carry a real quote", which reads as a broken archive and
    # is purely an artifact of counting deltas as if they should hold a book.
    snaps = events.get("orderbook_snapshot", 0)
    print(f"  orderbook snapshots             {snaps:>14,}")
    print(f"  ...of those, with a real book   {rows_with_book:>14,}   "
          f"({rows_with_book / max(snaps, 1) * 100:.1f}%)   <- the real ratio")
    print(f"  event types                     {dict(events)}")
    print(f"  series                          {dict(series)}")
    print(f"{'=' * 72}")
    print("\n  matches with a live book, per day:")
    for d in sorted(live_per_day):
        print(f"    {d}  {len(live_per_day[d]):>4}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({
            "files": len(files), "days": len(days),
            "first_day": days[0], "last_day": days[-1],
            "hours_held": len(hours), "hours_in_span": len(want),
            "gaps": missing, "rows": rows,
            "matches_seen": len(seen), "matches_with_book": len(with_book),
            "rows_with_book": rows_with_book,
            "events": dict(events), "series": dict(series),
            "live_per_day": {k: len(v) for k, v in sorted(live_per_day.items())},
        }, fh, indent=1)
    print(f"\n  wrote {OUT}")


if __name__ == "__main__":
    main()
