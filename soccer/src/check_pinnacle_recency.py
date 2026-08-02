"""Is the free Pinnacle closing line populated for RECENT matches?

This decides whether the top shortlist item is testable now or only on history.

The dataset build found 53 matched fixtures carrying a final score from
football-data but ZERO carrying PSCH. Both come from the same row, so the
odds columns specifically are blank on those rows. If the Pinnacle close is
only present on the back-catalogue and not on the last ~10 weeks, then the
"cheapest test on the list" cannot be run over the window where Kalshi prices
exist -- which would be a material change to the plan.

Retries with backoff: the site 503s under repeated fetching.
"""
import csv
import io
import os
import time
from collections import Counter
from datetime import datetime

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
KALSHI_WINDOW_START = datetime(2026, 5, 24)


def fetch(code, tries=6):
    for i in range(tries):
        try:
            r = requests.get(f"https://www.football-data.co.uk/new/{code}.csv",
                             headers=UA, timeout=90)
        except requests.RequestException as e:
            print(f"  {code}: net {type(e).__name__}, retry {i+1}")
            time.sleep(10 * (i + 1))
            continue
        if r.status_code == 200 and len(r.content) > 5000 and \
                b"," in r.content[:200]:
            return r
        print(f"  {code}: http {r.status_code} bytes {len(r.content)} "
              f"-- backing off {15*(i+1)}s")
        time.sleep(15 * (i + 1))
    return None


for code in ["MEX", "ARG", "BRA", "USA"]:
    r = fetch(code)
    if r is None:
        print(f"{code}: UNAVAILABLE after retries")
        continue
    rows = list(csv.reader(io.StringIO(r.text)))
    hdr, body = rows[0], rows[1:]
    ix = {c.strip().lstrip("﻿"): i for i, c in enumerate(hdr)}
    if "PSCH" not in ix or "Date" not in ix:
        print(f"{code}: unexpected columns {hdr[:8]}")
        continue
    by_year, with_psch, with_avg, with_max = Counter(), Counter(), Counter(), Counter()
    recent = []
    for x in body:
        if len(x) < len(hdr):
            continue
        try:
            d = datetime.strptime(x[ix["Date"]].strip(), "%d/%m/%Y")
        except ValueError:
            continue
        by_year[d.year] += 1
        if x[ix["PSCH"]].strip():
            with_psch[d.year] += 1
        if "AvgCH" in ix and x[ix["AvgCH"]].strip():
            with_avg[d.year] += 1
        if "MaxCH" in ix and x[ix["MaxCH"]].strip():
            with_max[d.year] += 1
        if d >= KALSHI_WINDOW_START:
            recent.append((d, x))
    print(f"\n=== {code} ===")
    for y in sorted(by_year)[-5:]:
        print(f"  {y}: {by_year[y]:5d} rows | PSCH {with_psch[y]:5d} "
              f"({100*with_psch[y]/by_year[y]:5.1f}%) | AvgCH {with_avg[y]:5d} "
              f"| MaxCH {with_max[y]:5d}")
    n = len(recent)
    npsch = sum(1 for _, x in recent if x[ix["PSCH"]].strip())
    navg = sum(1 for _, x in recent
               if "AvgCH" in ix and x[ix["AvgCH"]].strip())
    print(f"  IN THE KALSHI WINDOW (>= 2026-05-24): {n} rows, "
          f"PSCH on {npsch} ({100*npsch/max(n,1):.1f}%), "
          f"AvgCH on {navg} ({100*navg/max(n,1):.1f}%)")
    if recent:
        recent.sort(key=lambda t: t[0])
        for d, x in recent[-3:]:
            avg = x[ix["AvgCH"]] if "AvgCH" in ix else "?"
            print(f"    {d.date()} {x[ix['Home']][:18]:18s} "
                  f"PSCH={x[ix['PSCH']]!r} AvgCH={avg!r}")
    time.sleep(3)
