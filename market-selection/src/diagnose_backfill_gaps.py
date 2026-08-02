"""Which hour is missing from 2026-05-28 and 2026-06-04, and why?

Both days show first=00:00:00, last=23:59:59 but only 23 distinct hours. On an
exchange doing 3-4 M trades a day, an hour with genuinely zero trades is
implausible, so the likely causes are (a) a pagination gap, or (b) a real
exchange-wide outage. Those have very different consequences and the difference
is checkable: if the hour is truly empty at the source, a direct re-query for
that hour returns nothing too.
"""
import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

DIR = os.path.join(os.path.dirname(__file__), "..", "data", "tape_pmxt_window")

for day in ("2026-05-28", "2026-06-04"):
    path = os.path.join(DIR, f"trades_{day}.jsonl")
    hours = Counter()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ct = json.loads(line).get("created_time") or ""
            except json.JSONDecodeError:
                continue
            if len(ct) >= 13:
                hours[ct[11:13]] += 1
    present = set(hours)
    missing = [f"{h:02d}" for h in range(24) if f"{h:02d}" not in present]
    print(f"\n=== {day} ===")
    print(f"  hours present: {len(present)}   MISSING: {missing}")
    for h in sorted(hours):
        bar = "#" * max(1, hours[h] // 20000)
        print(f"    {h}:00  {hours[h]:8,d} {bar}")

    for mh in missing:
        start = datetime.fromisoformat(f"{day}T{mh}:00:00+00:00")
        end = start + timedelta(hours=1)
        r = K.get("/markets/trades", {"limit": 1000,
                                      "min_ts": int(start.timestamp()),
                                      "max_ts": int(end.timestamp())})
        n = len(r.json().get("trades", [])) if r and r.status_code == 200 else None
        print(f"  RE-QUERY {day} {mh}:00-{mh}:59 -> "
              f"http={getattr(r,'status_code','ERR')} trades={n}")
        if n:
            ts = sorted(t["created_time"] for t in r.json()["trades"])
            print(f"    the hour is NOT empty at the source: {ts[0]} .. {ts[-1]}")
            print("    => the backfill has a PAGINATION GAP for this hour")
        elif n == 0:
            print("    the hour is genuinely empty at the source "
                  "(exchange-wide quiet or outage) -- not a backfill defect")
